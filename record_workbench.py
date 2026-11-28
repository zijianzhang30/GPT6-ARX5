#!/usr/bin/env python3
"""Recording workbench that reuses an already running robot service."""
import argparse
import json
import logging
import re
import secrets
import tarfile
import threading
import time
import queue
import urllib.error
import urllib.request
from contextlib import ExitStack
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor

from app import Handler, ROOT, MAX_COMMAND_BYTES, MAX_TRAJECTORY_BYTES, PROXY_HEADER
from demonstrations import Demonstrations
from workbench_arms import ARM_BY_CHANNEL, ARM_CHANNELS
from workbench_timing import (SLOW_REQUEST_S, STAGE_TIMING_ENABLED, TRACE_HEADER, TRACE_ID,
                              log_stages, time_stage, trace_headers, trace_request)


LOGGER = logging.getLogger(__name__)
SLOW_HEARTBEAT_LOG_S = .1


class Upstream:
    def __init__(self, base):
        parsed = urlsplit(base)
        if parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1') or parsed.path not in ('', '/'):
            raise ValueError('Upstream must be a local HTTP workbench.')
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Invalid upstream URL.')
        self.base = base.rstrip('/')
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.recorder = None
        self.refresh_token()

    def refresh_token(self):
        with self.opener.open(self.base + '/', timeout=2) as response:
            match = re.search(rb'<meta name="control-token" content="([^"]+)"', response.read())
        if not match:
            raise ValueError('Upstream has no control token.')
        self.token = match.group(1).decode()

    def snapshot(self):
        try:
            request = urllib.request.Request(self.base + '/api/state', headers=trace_headers())
            with self.opener.open(request, timeout=.25) as response:
                return json.load(response)
        except (OSError, ValueError) as exc:
            raise ValueError(f'原控制服务状态不可用：{exc}') from exc

    def command(self, data):
        at = time.monotonic_ns()
        accepted, error = None, ''
        try:
            for attempt in range(2):
                request = urllib.request.Request(self.base + '/api/command',
                    data=json.dumps(data, allow_nan=False).encode(),
                    headers={'Content-Type': 'application/json', 'X-Control-Token': self.token,
                             PROXY_HEADER: 'record-workbench', **trace_headers()})
                try:
                    with self.opener.open(request, timeout=.25) as response:
                        state = json.load(response)
                    accepted = True
                    return state
                except urllib.error.HTTPError as exc:
                    accepted = False
                    if exc.code == 403 and attempt == 0:
                        exc.close()
                        self.refresh_token()
                        continue
                    try:
                        message = json.load(exc).get('error', str(exc))
                    finally:
                        exc.close()
                    raise ValueError(message) from exc
        except (OSError, ValueError) as exc:
            error = str(exc)
            raise ValueError(f'控制服务：{error}') from exc
        finally:
            if self.recorder:
                self.recorder.command(data, accepted, error, at)

    def get(self, key):
        if key not in ('gemini', 'external'):
            raise KeyError(key)
        try:
            with self.opener.open(self.base + f'/api/cameras/{key}/frame.jpg', timeout=7) as response:
                return response.read(), response.headers.get('X-Frame-Id'), response.headers.get('X-Camera-Device')
        except OSError as exc:
            if isinstance(exc, urllib.error.HTTPError):
                exc.close()
            raise RuntimeError(f'相机暂不可用：{exc}') from exc


class CameraRouter:
    """Keep the shared third-person camera available through the 8768 proxy.

    The two arm hosts can race to open the single USB camera. For the external
    view, remember whichever upstream currently owns it and race both only
    after that owner fails over.
    """
    def __init__(self, sources):
        self.sources = tuple(sources)
        self.lock = threading.Lock()
        self.preferred = None

    def get(self, key):
        if key != 'external' or len(self.sources) == 1:
            return self.sources[0].get(key)
        with self.lock:
            preferred = self.preferred
        if preferred is not None:
            try:
                return preferred.get(key)
            except RuntimeError:
                with self.lock:
                    if self.preferred is preferred:
                        self.preferred = None

        results = queue.Queue()
        def fetch(source):
            try:
                results.put((True, source, source.get(key)))
            except Exception as exc:
                results.put((False, source, exc))
        for source in self.sources:
            threading.Thread(target=fetch, args=(source,), daemon=True).start()
        errors = []
        for _ in self.sources:
            try:
                success, source, value = results.get(timeout=8)
            except queue.Empty:
                break
            if success:
                with self.lock:
                    self.preferred = source
                return value
            errors.append(str(value))
        raise RuntimeError('第三方相机在两个上游均不可用：' + '；'.join(errors))


class RecordingWorkbench(ThreadingHTTPServer):
    daemon_threads = True
    # Three camera readers, recording and both arm watchdogs open independent
    # short HTTP connections. The default backlog of 5 drops simultaneous
    # connects before handlers run, even when each handler is fast. Leave all
    # request/watchdog deadlines unchanged; admit these bounded local bursts.
    request_queue_size = 64

    def __init__(self, address, upstream, directory, right_upstream=None, paired_policy_client=None):
        if right_upstream and right_upstream.rstrip('/') == upstream.rstrip('/'):
            raise ValueError('Left and right upstreams must differ.')
        self.upstream = Upstream(upstream)
        self.recording_arm = ARM_BY_CHANNEL['can0']
        self.secondary_arm = ARM_BY_CHANNEL['can1']
        self.arms = {self.recording_arm: self.upstream}
        if right_upstream:
            self.arms[self.secondary_arm] = Upstream(right_upstream)
        if paired_policy_client and (not right_upstream or not re.fullmatch(r'dual-policy-[a-f0-9]{32}', paired_policy_client)):
            raise ValueError('Paired policy needs two upstreams and a unique dual-policy client ID')
        self.paired_policy_client = paired_policy_client
        self.controller = self.upstream
        self.cameras = CameraRouter(list(self.arms.values()))
        self.lock = threading.RLock()  # Also used by the legacy /api/state handler.
        self.command_locks = {arm: threading.Lock() for arm in self.arms}
        self.token = secrets.token_urlsafe(32)
        self.recorder = Demonstrations(directory, self.upstream.snapshot, self.cameras)
        self.upstream.recorder = self.recorder
        super().__init__(address, RecordingHandler)

    def arm_snapshot(self, arm):
        return self._validate_arm_snapshot(arm, self.arms[arm].snapshot())

    @staticmethod
    def _validate_arm_snapshot(arm, state):
        if not isinstance(state, dict):
            raise ValueError(f'{arm} upstream returned an invalid state')
        expected = ARM_CHANNELS[arm]
        if state.get('simulation') is not True and state.get('channel') != expected:
            raise ValueError(f'{arm} upstream must use {expected}; command routing blocked')
        return state

    def arm_command(self, arm, data):
        action = data.get('action')
        paired = bool(self.paired_policy_client and data.get('client') == self.paired_policy_client)
        paired_heartbeat = paired and action == 'heartbeat' and data.keys() == {'action', 'client'}
        # Only the reserved owner's plain keepalive can run alongside its peer.
        # Other commands take both locks in the same order for atomic peer checks.
        if paired_heartbeat:
            command_locks = (self.command_locks[arm],)
        else:
            command_locks = (self.lock, *self.command_locks.values())
        timings = {} if paired_heartbeat else None
        started = time.monotonic() if paired_heartbeat else None
        heartbeat_ok = False
        try:
            with ExitStack() as locks:
                with time_stage(timings, 'lock_wait'):
                    for lock in command_locks:
                        locks.enter_context(lock)
                with time_stage(timings, 'selected_state'):
                    current = self.arm_snapshot(arm)
                if action not in ('stop', 'disconnect'):
                    if paired:
                        self.check_paired_command(data, current)
                    with time_stage(timings, 'peer_state'):
                        for other in self.arms:
                            if other == arm:
                                continue
                            state = self.arm_snapshot(other)
                            if paired and (state.get('robot_status') != 'ready'
                                           or state.get('error_codes') != []
                                           or state.get('enabled') and state.get('owner') != self.paired_policy_client):
                                raise ValueError('Paired peer is not ready or belongs to another controller')
                            if (state.get('enabled') and not paired) or state.get('robot_status') == 'initializing':
                                raise ValueError('另一只机械臂正在使能或初始化；当前工作台一次只控制一只臂')
                    episode = self.recorder.status().get('episode')
                    if arm != self.recording_arm and episode and episode.get('status') in ('recording', 'saving'):
                        raise ValueError('当前录制仅包含右臂（can0）。请先完成录制再控制左臂（can1）。')
                with time_stage(timings, 'upstream_command'):
                    response = self.arms[arm].command(data)
                if paired_heartbeat:
                    state = self._validate_arm_snapshot(arm, response)
                    heartbeat_ok = True
                    return state
                return self.arm_snapshot(arm)
        finally:
            if paired_heartbeat:
                elapsed = time.monotonic() - started
                threshold = SLOW_REQUEST_S if STAGE_TIMING_ENABLED else SLOW_HEARTBEAT_LOG_S
                level = logging.WARNING if elapsed >= threshold or not heartbeat_ok else logging.DEBUG
                LOGGER.log(level, 'R5 paired heartbeat arm=%s trace_id=%s start_mono=%.6f ok=%s total_ms=%.2f stages_ms=%s',
                           arm, TRACE_ID.get(), started, heartbeat_ok, elapsed * 1000, timings)

    def check_paired_command(self, data, state):
        from motion_safety import finite, SUPERVISED_SPEED
        action = data.get('action')
        allowed = {
            'enable': set(), 'resume': set(), 'pause_hold': set(), 'heartbeat': set(),
            'settings': {'mode', 'speed'}, 'target': {'gripper_raw', 'joints_deg'},
            'policy_trajectory': {'start_deg', 'points_deg', 'times_s', 'issued_at'},
        }
        if action not in allowed or set(data) - {'action', 'client'} - allowed[action]:
            raise ValueError('Paired policy forbids homing, jogging and uncoordinated commands')
        if state.get('robot_status') != 'ready' or state.get('error_codes') != []:
            raise ValueError('Paired arm is not ready')
        if action == 'settings' and (data.get('mode') != 'joint' or not finite(data.get('speed'))
                                      or not 0 < data['speed'] <= SUPERVISED_SPEED):
            raise ValueError('Paired policy requires supervised joint settings')
        if action == 'target':
            fields = set(data) - {'action', 'client'}
            if fields == {'joints_deg'}:
                # Segment renewal may re-anchor to encoders; all new motion uses timed paths.
                from motion_safety import vector
                if (not vector(data['joints_deg']) or not vector(state.get('joints_deg'))
                        or max(abs(a-b) for a, b in zip(data['joints_deg'], state['joints_deg'])) > .05):
                    raise ValueError('Paired joint target is only allowed for a measured hold re-anchor')
            elif fields != {'gripper_raw'}:
                raise ValueError('Paired gripper and arm changes must be separate')

    def server_close(self):
        self.recorder.close()
        # The existing service owns the hardware and its watchdogs.
        super().server_close()


class RecordingHandler(Handler):
    def do_GET(self):
        path = urlsplit(self.path).path
        try:
            if path == '/api/arms':
                def snapshot(arm):
                    try:
                        state, error = self.server.arm_snapshot(arm), None
                    except (ValueError, OSError) as exc:
                        state, error = None, str(exc)
                    channel = ARM_CHANNELS[arm]
                    return {'id': arm, 'channel': channel, 'state': state, 'error': error,
                            'command_path': f'/api/arms/{arm}/{channel}/command',
                            'wrist_camera_path': f'/api/arms/{arm}/camera/frame.jpg'}
                with ThreadPoolExecutor(max_workers=2) as pool:
                    ids = (arm for arm in ARM_CHANNELS if arm in self.server.arms)
                    arms = list(pool.map(snapshot, ids))
                return self.send(200, {'arms': arms, 'control_mode': (
                                       'reserved_paired_policy' if self.server.paired_policy_client else 'one_arm_at_a_time'),
                                       'paired_policy_client': self.server.paired_policy_client,
                                       'recording_arm': self.server.recording_arm})
            parts = path.split('/')
            if path == '/api/cameras/gemini_right/frame.jpg':
                # Preserve the historical camera alias for existing recordings.
                camera_arm = self.server.secondary_arm
            elif len(parts) == 6 and parts[1:3] == ['api', 'arms'] and parts[4:] == ['camera', 'frame.jpg']:
                camera_arm = parts[3]
            else:
                camera_arm = None
            if camera_arm is not None:
                source = self.server.arms.get(camera_arm)
                if source is None:
                    return self.send(404, {'error': '未配置该机械臂的腕相机'})
                frame, sequence, device = source.get('gemini')
                return self.send(200, frame, 'image/jpeg',
                                 {'X-Frame-Id': sequence, 'X-Camera-Device': device})
            if len(parts) == 5 and parts[1:3] == ['api', 'arms'] and parts[4] == 'state':
                if parts[3] not in self.server.arms:
                    return self.send(404, {'error': '未知机械臂'})
                with trace_request(self.headers.get(TRACE_HEADER)), log_stages(f'proxy GET {path}') as timings:
                    with time_stage(timings, 'upstream_state'):
                        state = self.server.arm_snapshot(parts[3])
                    with time_stage(timings, 'response'):
                        return self.send(200, state)
            if path == '/api/recording/status':
                return self.send(200, self.server.recorder.status())
            if path == '/api/recordings':
                return self.send(200, self.server.recorder.history())
            parts = path.split('/')
            if len(parts) in (4, 5) and parts[1:3] == ['api', 'recordings']:
                meta = self.server.recorder.read(parts[3])
                if len(parts) == 4:
                    return self.send(200, meta)
                if parts[4] == 'download':
                    if meta['status'] in ('recording', 'saving'):
                        return self.send(409, {'error': '请先停止录制并等待保存完成'})
                    folder = self.server.recorder.episode_path(parts[3])
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/x-tar')
                    self.send_header('Content-Disposition', f'attachment; filename="{parts[3]}.tar"')
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    try:
                        with tarfile.open(fileobj=self.wfile, mode='w|') as archive:
                            for file in sorted(folder.rglob('*')):
                                if file.is_file() and not file.is_symlink():
                                    archive.add(file, arcname=str(Path(parts[3]) / file.relative_to(folder)), recursive=False)
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                    return
            return super().do_GET()
        except (ValueError, OSError, RuntimeError) as exc:
            self.send(503, {'error': str(exc)})

    def do_POST(self):
        path = urlsplit(self.path).path
        parts = path.split('/')
        arm_route = len(parts) in (5, 6) and parts[1:3] == ['api', 'arms'] and parts[-1] == 'command'
        legacy_command = path == '/api/command'
        if not path.startswith('/api/recording/') and not arm_route and not legacy_command:
            return super().do_POST()
        origin = self.headers.get('Origin')
        if origin and origin != f'http://{self.headers.get("Host")}':
            return self.send(403, {'error': '不允许跨站操作'})
        if not secrets.compare_digest(self.headers.get('X-Control-Token', ''), self.server.token):
            return self.send(403, {'error': '请刷新控制页面'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            limit = MAX_TRAJECTORY_BYTES if arm_route or legacy_command else MAX_COMMAND_BYTES
            if not 0 < size <= limit:
                raise ValueError('请求过大或为空')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('无效请求')
            if arm_route or legacy_command:
                self.record_command_action(data)
                if size > MAX_COMMAND_BYTES and data.get('action') != 'policy_trajectory':
                    raise ValueError('请求过大')
                arm = parts[3] if arm_route else self.server.recording_arm
                if arm not in self.server.arms:
                    return self.send(404, {'error': '未知机械臂'})
                if arm_route and (len(parts) != 6 or parts[4] != ARM_CHANNELS[arm]):
                    return self.send(409, {'error': '机械臂 ID 与 CAN 通道必须匹配。请使用 /api/arms 公布的 command_path。'})
                with trace_request(self.request_trace_id), log_stages(f'proxy POST {path}') as timings:
                    with time_stage(timings, 'arm_command'):
                        state = self.server.arm_command(arm, data)
                    with time_stage(timings, 'response'):
                        return self.send(200, state)
            recorder = self.server.recorder
            if path == '/api/recording/start':
                other = self.server.secondary_arm
                if other in self.server.arms:
                    state = self.server.arm_snapshot(other)
                    if state.get('enabled') or state.get('robot_status') == 'initializing':
                        raise ValueError('左臂（can1）正在控制。当前示范录制仅包含右臂（can0）。')
                result = recorder.start(data.get('name', ''))
            elif path == '/api/recording/stop':
                result = recorder.stop(data.get('result', 'unspecified'))
            elif path == '/api/recording/marker':
                result = recorder.marker(data.get('phase'), data.get('note', ''))
            else:
                return self.send(404, {'error': '接口不存在'})
            self.send(200, result)
        except (ValueError, TypeError, OSError) as exc:
            self.send(400, {'error': str(exc)})


def main():
    parser = argparse.ArgumentParser(description='Local R5 demonstration recording workbench')
    parser.add_argument('--port', type=int, default=8768)
    parser.add_argument('--upstream', default='http://127.0.0.1:8765')
    parser.add_argument('--right-upstream', help='Optional second upstream on can1 (public arm ID: left)')
    parser.add_argument('--paired-policy-client', help='Reserve concurrent control for one attended dual-policy owner')
    parser.add_argument('--recordings', type=Path, default=ROOT / 'recordings')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s %(message)s')
    if any(url and urlsplit(url).port == args.port for url in (args.upstream, args.right_upstream)):
        parser.error('Recording and upstream ports must differ.')
    server = RecordingWorkbench(('127.0.0.1', args.port), args.upstream, args.recordings.resolve(),
                                right_upstream=args.right_upstream, paired_policy_client=args.paired_policy_client)
    print(f'Recording workbench: http://127.0.0.1:{server.server_port} -> {args.upstream}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
