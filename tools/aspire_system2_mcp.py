#!/usr/bin/env python3
"""Serve a local stdio MCP session for the attended ARX R5 host."""
import argparse
import base64
import json
from pathlib import Path
import queue
import socket
import sys
from urllib.request import ProxyHandler, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aspire_review import (ARM_FRAMES, CAMERAS, HOST_TIMEOUT_S, MAX_REQUEST_BYTES, MOTION_TOOLS,
                           MOTION_WIRE_PREFIX, AspireRequest, failure, native_command, review_socket)
from workbench_arms import ARM_CHANNELS, PROFILE_WORKBENCH_ARM

PROTOCOL_VERSIONS = ('2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05')
TASK_INSTRUCTION = ('Use the selected workbench arm to sweep three blocks into the fixed dustpan. '
                    'Verify the channel and frame in live feedback. Use the three live RGB views '
                    'and verify the final result visually with the brush withdrawn.')
TOOL_DESCRIPTIONS = {
    'r5_task': 'Read the L3-04 task and physical arm roles.',
    'get_capability_graph': 'Read available tools and station capabilities.',
    'observe': 'Read fresh RGB views, measured TCP poses and gripper telemetry.',
    'cap_move_to_pose': 'Request one reviewed TCP pose for the active arm, in its base frame, metres and WXYZ.',
    'cap_set_gripper': 'Request one bounded normalized opening for the active arm. Use its next-opening bounds.',
}


def schema(properties, required=()):
    return {'type': 'object', 'properties': properties, 'required': list(required),
            'additionalProperties': False}


def vector_schema(length):
    return {'type': 'array', 'items': {'type': 'number'}, 'minItems': length, 'maxItems': length}


def list_tools(allow_motion, active_arm=None):
    text = {'type': 'string', 'minLength': 1}
    arm_schema = {'const': active_arm} if active_arm else {'enum': list(ARM_CHANNELS)}
    frame_schema = {'const': ARM_FRAMES[active_arm]} if active_arm else {'enum': list(ARM_FRAMES.values())}
    shared = {'arm': arm_schema, 'note': text, 'observation_id': text}
    inputs = {
        'observe': schema({'cameras': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                       'items': {'type': 'string', 'enum': list(CAMERAS)}}}),
        'r5_task': schema({}),
        'get_capability_graph': schema({}),
        'cap_move_to_pose': schema({**shared, 'target_pose': schema({
            'position': vector_schema(3), 'quaternion_wxyz': vector_schema(4),
            'frame': frame_schema}, ('position', 'quaternion_wxyz', 'frame'))},
            ('arm', 'note', 'observation_id', 'target_pose')),
        'cap_set_gripper': schema({**shared, 'position': {'type': 'number', 'minimum': 0, 'maximum': 1}},
                                  ('arm', 'note', 'observation_id', 'position')),
    }
    return [{'name': name, 'description': TOOL_DESCRIPTIONS[name], 'inputSchema': contract}
            for name, contract in inputs.items() if allow_motion or name not in MOTION_TOOLS]


def host_call(path, tool, args):
    request = json.dumps({'tool': tool, 'arguments': args}, allow_nan=False).encode() + b'\n'
    if len(request) > MAX_REQUEST_BYTES:
        raise ValueError('Request exceeds the review socket limit')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(HOST_TIMEOUT_S + 5)
        try:
            conn.connect(str(path))
        except OSError as exc:
            return failure('not_dispatched', f'Review socket unavailable: {exc}')
        try:
            conn.sendall(request)
            with conn.makefile('rb') as stream:
                return json.loads(stream.readline(1024 * 1024))
        except (OSError, ValueError):
            return failure('outcome_unknown', 'Review response unavailable. Inspect host state before issuing another action.')


def tool_result(data, cameras):
    observation = data.get('observation')
    frames = []
    if observation:
        paths = observation.pop('images')
        for name in cameras:
            try:
                jpeg = Path(paths[name]).read_bytes()
                if not jpeg.startswith(b'\xff\xd8'):
                    raise ValueError('not a JPEG')
            except (KeyError, OSError, ValueError):
                data['observation'] = None
                data['observation_error'] = f'Unable to read fresh {name}; request another observation.'
                frames = []
                break
            frames.extend([{'type': 'text', 'text': 'camera: ' + name},
                           {'type': 'image', 'mimeType': 'image/jpeg',
                            'data': base64.b64encode(jpeg).decode('ascii')}])
    data['image_cameras'] = [f['text'][8:] for f in frames if f['type'] == 'text']
    content = [{'type': 'text', 'text': json.dumps(data, ensure_ascii=False)}, *frames]
    return {'content': content, 'structuredContent': data,
            'isError': not data.get('ok') or 'observation_error' in data}


def call_tool(path, name, arguments, allow_motion):
    if name in ('r5_task', 'get_capability_graph'):
        if arguments:
            raise ValueError(f'{name} takes no arguments')
        host = host_call(path, 'capabilities', {})
        arm = host.get('motion_arm')
        connected = (host.get('ok') is True and host.get('protocol') == 2
                     and arm in ARM_CHANNELS and host.get('motion_frame') == ARM_FRAMES[arm])
        motion = connected and allow_motion and host.get('motion_enabled') is True
        if name == 'r5_task':
            return tool_result({'ok': True, 'task': 'L3-04', 'station': 'physical_arx_r5',
                                'instruction': TASK_INSTRUCTION,
                                'manipulation_arms': [arm] if motion else []}, ())
        return tool_result({'ok': True, 'station': 'physical_arx_r5', 'camera_mode': 'rgb',
                            'host_connected': connected, 'motion_tools_exposed': motion,
                            'motion_arm': arm if motion else None,
                            'motion_frame': ARM_FRAMES[arm] if motion else None,
                            'arm_channels': ARM_CHANNELS, 'arm_frames': ARM_FRAMES,
                            'depth_backprojection': False, 'collision_checked': False,
                            'tools': list_tools(motion, arm if motion else None), 'programs': [],
                            'configured_providers': {'ik': ['arx_r5'], 'segmentation': [], 'pose_planning': ['arx_r5']}}, ())
    if name == 'observe':
        cameras = arguments.get('cameras', list(CAMERAS))
        if (set(arguments) - {'cameras'} or not isinstance(cameras, list) or not cameras
                or any(not isinstance(v, str) or v not in CAMERAS for v in cameras)
                or len(cameras) != len(set(cameras))):
            raise ValueError('Select a nonempty list of distinct camera names')
        data = host_call(path, name, {})
        if data.get('ok') and not valid_observation(data.get('observation')):
            data = failure('rejected', 'Observation does not identify each arm channel and base frame')
        return tool_result(data, cameras)
    if name not in MOTION_TOOLS or not allow_motion:
        raise ValueError('Tool is not available in this session')
    arm = arguments.get('arm')
    if not isinstance(arm, str) or arm not in ARM_CHANNELS:
        raise ValueError('Explicit arm=left or arm=right is required')
    data = host_call(path, MOTION_WIRE_PREFIX + name, arguments)
    if data.get('ok') and not valid_observation(data.get('observation')):
        data = failure('outcome_unknown', 'Post-action observation does not identify each arm channel and base frame')
    return tool_result(data, list(CAMERAS))


def valid_observation(observation):
    state = observation.get('state') if isinstance(observation, dict) else None
    return isinstance(state, dict) and set(state) == set(ARM_CHANNELS) and all(
        isinstance(state[arm], dict) and state[arm].get('channel') == channel
        and state[arm].get('frame') == ARM_FRAMES[arm]
        for arm, channel in ARM_CHANNELS.items())


class LegacyReview:
    """Present the new convention while the v1 host retains its stationary hold."""

    profile = 'left'  # The v1 socket only allowed this profile to move.
    arm = PROFILE_WORKBENCH_ARM[profile]

    def __init__(self, path, allow_motion):
        self.path = path
        self.allow_motion = allow_motion
        self.current = None
        verified = self.convert(host_call(path, 'observe', {}))
        if not verified.get('ok'):
            raise ValueError(verified.get('message', 'Legacy observation failed'))
        opener = build_opener(ProxyHandler({}))
        with opener.open('http://127.0.0.1:8768/api/arms', timeout=2) as response:
            live_arms = {arm['id']: arm for arm in json.load(response)['arms']}
        for name, reported in verified['observation']['state'].items():
            live = live_arms[name]['state']
            if (live.get('channel') != reported['channel'] or live.get('moving') is not False
                    or live.get('control_state') != 'holding'
                    or any(abs(a-b) > .3 for a, b in zip(live['joints_deg'], reported['joints_deg'], strict=True))):
                raise ValueError(f'Legacy {name} observation does not match stationary {reported["channel"]}')

    @staticmethod
    def convert(response):
        if not response.get('ok'):
            return response
        observation = response['observation']
        state = observation['state']
        if set(state) != set(PROFILE_WORKBENCH_ARM) or any(
                arm.get('frame') != f'{profile}_base' or 'channel' in arm for profile, arm in state.items()):
            raise ValueError('Expected the original legacy host observation format')
        observation['state'] = {
            name: {**state[profile], 'channel': ARM_CHANNELS[name], 'frame': ARM_FRAMES[name]}
            for profile, name in PROFILE_WORKBENCH_ARM.items()
        }
        images = observation['images']
        observation['images'] = {
            'overview': images['overview'], 'left_wrist': images['right_wrist'],
            'right_wrist': images['left_wrist'],
        }
        return response

    def dispatch(self, request):
        tool, args = request.tool, request.arguments
        if tool in ('capabilities', 'observe'):
            if args:
                raise ValueError(f'{tool} takes no socket arguments')
            if tool == 'capabilities':
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
                    conn.settimeout(1)
                    try:
                        conn.connect(str(self.path))
                    except OSError as exc:
                        return failure('not_dispatched', f'Legacy review socket unavailable: {exc}')
                return {'ok': True, 'protocol': 2, 'motion_arm': self.arm,
                        'motion_frame': ARM_FRAMES[self.arm], 'motion_enabled': self.allow_motion}
            self.current = None
            result = self.convert(host_call(self.path, 'observe', {}))
            if result.get('ok'):
                self.current = result['observation']['observation_id']
            return result
        name = tool.removeprefix(MOTION_WIRE_PREFIX)
        if not self.allow_motion or name == tool or name not in MOTION_TOOLS:
            raise ValueError('Use an updated ASPIRE client with motion enabled')
        native_command(AspireRequest(name, args), self.profile)
        if not self.current or args.get('observation_id') != self.current:
            raise ValueError('Read a fresh observation through this socket')
        self.current = None
        legacy = {**args, 'arm': self.profile}
        if name == 'cap_move_to_pose':
            legacy['target_pose'] = {**args['target_pose'], 'frame': f'{self.profile}_base'}
        result = host_call(self.path, name, legacy)
        if result.get('ok'):
            try:
                result = self.convert(result)
                result['receipt'].update(arm=self.arm, channel=ARM_CHANNELS[self.arm], frame=ARM_FRAMES[self.arm])
                self.current = result['observation']['observation_id']
            except (KeyError, TypeError, ValueError):
                return failure('outcome_unknown', 'The legacy host action returned without a usable observation')
        return result


def serve_legacy(source, destination, allow_motion):
    bridge = LegacyReview(source, allow_motion)
    commands = queue.Queue()
    with review_socket(destination, commands):
        while True:
            request = commands.get()
            if not request.reply.set_running_or_notify_cancel():
                continue
            try:
                response = bridge.dispatch(request)
            except (ValueError, KeyError, TypeError) as exc:
                response = failure('rejected', str(exc))
            request.reply.set_result(response)


def rpc(message, path, allow_motion):
    method = message.get('method')
    if 'id' not in message and isinstance(method, str) and method.startswith('notifications/'):
        return None
    reply = {'jsonrpc': '2.0', 'id': message.get('id')}
    params = message.get('params', {})
    if message.get('jsonrpc') != '2.0' or not isinstance(params, dict):
        return {**reply, 'error': {'code': -32600, 'message': 'Invalid request'}}
    if method == 'initialize':
        version = params.get('protocolVersion')
        result = {'protocolVersion': version if version in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                  'capabilities': {'tools': {}}, 'serverInfo': {'name': 'arx-r5-aspire-system2', 'version': '0.2.0'}}
    elif method == 'ping':
        result = {}
    elif method == 'tools/list':
        result = {'tools': list_tools(allow_motion)}
    elif method == 'tools/call':
        name, arguments = params.get('name'), params.get('arguments', {})
        try:
            if not isinstance(arguments, dict):
                raise ValueError('Tool arguments must be an object')
            result = call_tool(path, name, arguments, allow_motion)
        except ValueError as exc:
            result = tool_result(failure('rejected', str(exc)), ())
    else:
        return {**reply, 'error': {'code': -32601, 'message': 'Method not found'}}
    return {**reply, 'result': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--socket', type=Path, required=True)
    parser.add_argument('--allow-motion', action='store_true', help='Expose motion tools when the host also enables them')
    parser.add_argument('--bridge-legacy-to', type=Path,
                        help='Serve the new convention in front of a running v1 review socket')
    args = parser.parse_args()
    socket_path = args.socket.expanduser().absolute()
    if args.bridge_legacy_to:
        serve_legacy(socket_path, args.bridge_legacy_to.expanduser().absolute(), args.allow_motion)
        return
    for line in sys.stdin:
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError('Expected a JSON-RPC object')
        except ValueError:
            response = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Invalid JSON-RPC message'}}
        else:
            response = rpc(message, socket_path, args.allow_motion)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
