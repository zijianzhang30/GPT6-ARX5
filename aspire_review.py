"""Local command transport for the existing attended dual-arm review host."""
from concurrent.futures import Future, TimeoutError
from contextlib import contextmanager
from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
from socketserver import StreamRequestHandler, ThreadingUnixStreamServer
from threading import Lock, Thread

CAMERAS = {'overview': 'top', 'left_wrist': 'left', 'right_wrist': 'right'}
PORTABLE_FRAME = 'left_base'
MOTION_TOOLS = ('cap_move_to_pose', 'cap_set_gripper')
HOST_TIMEOUT_S = 175
MAX_REQUEST_BYTES = 16384


@dataclass
class AspireRequest:
    tool: str
    arguments: dict
    reply: Future = field(default_factory=Future)


def failure(status, reason):
    return {'ok': False, 'status': status, 'message': reason}


def read_request(stream):
    data = stream.readline(MAX_REQUEST_BYTES + 1)
    if not data or len(data) > MAX_REQUEST_BYTES or not data.endswith(b'\n'):
        raise ValueError('Expected a single bounded JSON request line')
    message = json.loads(data)
    if (not isinstance(message, dict) or set(message) != {'tool', 'arguments'}
            or not isinstance(message['tool'], str) or not isinstance(message['arguments'], dict)):
        raise ValueError('Expected a tool name and arguments object')
    return AspireRequest(message['tool'], message['arguments'])


def validate_socket_path(path):
    path = Path(path).expanduser().absolute()
    parent = path.parent.stat()
    if parent.st_uid != os.getuid() or parent.st_mode & 0o077:
        raise ValueError('Create the socket in a directory owned by you with mode 0700')
    if os.path.lexists(path):
        raise ValueError('Socket path already exists; choose a fresh path')
    if len(os.fsencode(path)) > 100:
        raise ValueError('Socket path is too long; use a shorter private directory')
    return path


@contextmanager
def review_socket(path, commands):
    """Queue on the existing owning host; the socket thread never calls hardware."""
    path = validate_socket_path(path)
    in_flight = Lock()

    class Server(ThreadingUnixStreamServer):
        daemon_threads = True

    class Handler(StreamRequestHandler):
        def handle(self):
            self.request.settimeout(5)
            if in_flight.acquire(blocking=False):
                try:
                    answer = self.submit()
                finally:
                    in_flight.release()
            else:
                answer = failure('not_dispatched', 'Another review request is still pending')
            try:
                self.wfile.write(json.dumps(answer, allow_nan=False).encode() + b'\n')
            except OSError:
                pass  # The requester disconnected. The host owns any in-flight action.

        def submit(self):
            try:
                request = read_request(self.rfile)
            except (ValueError, OSError) as exc:
                return failure('rejected', str(exc))
            commands.put(request)
            try:
                return request.reply.result(timeout=HOST_TIMEOUT_S)
            except TimeoutError:
                cancelled = request.reply.cancel()
                return failure('not_dispatched' if cancelled else 'outcome_unknown',
                               'Host response timed out. Inspect the current host and obtain a fresh observation.')

    server = Server(os.fspath(path), Handler)
    thread = None
    try:
        path.chmod(0o600)
        thread = Thread(target=server.serve_forever, args=(.1,), daemon=True)
        thread.start()
        yield path
    finally:
        if thread is not None:
            server.shutdown()
            thread.join()
        server.server_close()
        path.unlink(missing_ok=True)


def vector(value, length):
    try:
        if (isinstance(value, list) and len(value) == length
                and all(type(number) in (int, float) and math.isfinite(number) for number in value)):
            return value
    except OverflowError:
        pass
    raise ValueError(f'Expected a list of {length} finite numbers')


def native_command(request):
    args = request.arguments
    note = args.get('note')
    if args.get('arm', 'left') != 'left' or not isinstance(note, str) or not note.strip():
        raise ValueError('Provide arm=left and a note describing the observed clearance or contact')
    if request.tool == 'cap_move_to_pose':
        if set(args) - {'arm', 'note', 'observation_id', 'target_pose'}:
            raise ValueError('Unsupported pose arguments')
        pose = args.get('target_pose')
        if (not isinstance(pose, dict) or set(pose) != {'position', 'quaternion_wxyz', 'frame'}
                or pose['frame'] != PORTABLE_FRAME):
            raise ValueError('Use position, quaternion_wxyz and frame=left_base')
        xyz = vector(pose['position'], 3)
        w, x, y, z = vector(pose['quaternion_wxyz'], 4)
        if abs(math.hypot(w, x, y, z) - 1) > 1e-3:
            raise ValueError('The quaternion must have unit length')
        return {'tool': 'move_to', 'arguments': {
            'target': {'left': {'pose_xyzquat': [*xyz, x, y, z, w]}, 'right': None}, 'note': note}}
    if request.tool == 'cap_set_gripper':
        if set(args) - {'arm', 'note', 'observation_id', 'position'}:
            raise ValueError('Unsupported gripper arguments')
        opening = vector([args.get('position')], 1)[0]
        if not 0 <= opening <= 1:
            raise ValueError('Use a normalized opening between 0 and 1')
        return {'tool': 'set_gripper', 'arguments': {
            'positions': {'left': opening, 'right': None}, 'note': note}}
    raise ValueError('Unsupported motion tool')


def public_observation(packet):
    arms = {}
    for name, arm in packet['arms'].items():
        x, y, z, qx, qy, qz, qw = arm['measured_tcp']
        arms[name] = {
            'frame': f'{name}_base', 'tcp_position_m': [x, y, z],
            'tcp_quaternion_wxyz': [qw, qx, qy, qz], 'joints_deg': arm['joints_deg'],
            'gripper_measured_normalized': arm['measured_opening'],
            'gripper_command_normalized': arm['opening'],
            'gripper_next_opening_bounds': arm['bounds'],
        }
    return {
        'observation_id': str(packet['observation']), 'timestamp_s': packet['observation'] / 1e9,
        'state': arms, 'camera_mode': 'rgb', 'images': {
            name: packet['images'][key] for name, key in CAMERAS.items()
        },
    }


class AspireReview:
    """Translate System 2 requests into one supervised command per fresh observation."""
    def __init__(self, allow_motion):
        self.allow_motion = allow_motion
        self.current = None

    def observe(self, capture):
        self.current = None
        state = public_observation(capture())
        self.current = state['observation_id']
        return state

    def dispatch(self, request, capture, execute, working_side):
        if request.tool == 'observe':
            if request.arguments:
                raise ValueError('Host observe takes no arguments')
            return {'ok': True, 'status': 'observed', 'observation': self.observe(capture)}
        if not self.allow_motion or working_side != 'left':
            raise ValueError('Motion requires the left working arm and explicit host motion enablement')
        command = native_command(request)
        if not self.current or request.arguments.get('observation_id') != self.current:
            raise ValueError('Read a fresh observation and use its observation_id')
        self.current = None
        result = execute(command)
        # Capture may fail after dispatch, so surface an unknown outcome in that case.
        try:
            observation = self.observe(capture)
        except Exception as exc:
            raise RuntimeError('Post-action observation failed; inspect the host before another command') from exc
        arm = result['arms']['left']
        return {'ok': True, 'status': 'review_completed', 'observation': observation,
                'receipt': {'control_state': arm['control_state'], 'settle': arm['settle'],
                            'tracking_residual_deg': arm.get('tracking_residual_deg'),
                            'collision_checked': False, 'grasp_verified': False}}
