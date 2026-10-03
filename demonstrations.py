"""Local demonstration capture; this module never sends robot commands."""
import json
import queue
import re
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

CAMERAS = {'gemini': 'wrist', 'external': 'third_person'}
PHASES = ('approach', 'grasp', 'lift', 'release', 'note')
RESULTS = ('unspecified', 'success', 'failed', 'partial')
STATE_KEYS = ('simulation', 'enabled', 'moving', 'mode', 'frame', 'speed',
              'joints_deg', 'target_deg', 'command_deg', 'velocity_deg',
              'pose', 'gripper_raw', 'gripper_target_raw', 'gripper_mm',
              'gripper_target_mm', 'currents', 'error_codes', 'robot_status',
              'feedback_age_ms', 'rx_age_ms', 'rx_count', 'tracking_error_deg',
              'tracking_limited', 'owner', 'message')


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


class Episode:
    def __init__(self, root, name, snapshot, cameras, initial):
        self.id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_') + uuid.uuid4().hex[:12]
        self.path = root / self.id
        self.path.mkdir(parents=True)
        for camera in CAMERAS:
            (self.path / camera).mkdir()
        self.snapshot, self.cameras = snapshot, cameras
        self.started = time.monotonic_ns()
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        self.done = threading.Event()
        self.pending = queue.Queue(maxsize=256)
        self.meta = {
            'schema_version': 1, 'id': self.id, 'name': name, 'started_at': utc_now(),
            'start_monotonic_ns': self.started, 'status': 'recording', 'result': 'unspecified',
            'simulation': initial['simulation'], 'duration_s': 0, 'error': '',
            'rates_requested_hz': {'state': 20, 'each_camera': 10},
            'clock': 'host monotonic; timestamps mark receipt, not camera exposure; cameras are not hardware synchronized',
            'cameras': CAMERAS, 'units': {'joints': 'degrees', 'pose': 'URDF mm and degrees, not calibrated TCP',
                                      'gripper_raw': 'SDK units, not mm', 'currents': 'uncalibrated SDK units'},
            'limits': {'duration_s': 900, 'bytes': 2_000_000_000},
            'counts': {'states': 0, 'valid_states': 0, 'commands': 0, 'rejected_commands': 0,
                       'gemini': 0, 'external': 0, 'capture_errors': 0},
            'bytes': 0, 'markers': [], 'action_counts': {},
            'joint_ranges_deg': [], 'gripper_range_raw': None,
            'first_joints_deg': None, 'last_joints_deg': None,
        }
        write_json(self.path / 'manifest.json', self.meta)
        self.writer = threading.Thread(target=self._write, daemon=True)
        self.writer.start()
        threading.Thread(target=self._states, daemon=True).start()
        for key in CAMERAS:
            threading.Thread(target=self._frames, args=(key,), daemon=True).start()

    def submit(self, kind, data, frame=None, at=None):
        with self.lock:
            if self.stopping.is_set() or (at is not None and at < self.started):
                return False
            event = {'type': kind, 't_ns': (at or time.monotonic_ns()) - self.started, **data}
            try:
                self.pending.put_nowait((event, frame))
                return True
            except queue.Full:
                self.meta['error'] = 'Recording queue full; capture stopped to avoid silent data loss.'
                self.stopping.set()
                return False

    def _states(self):
        while not self.stopping.is_set():
            before = time.monotonic()
            try:
                state = self.snapshot()
                self.submit('state', {'state': {key: state.get(key) for key in STATE_KEYS}})
            except Exception as exc:
                self.submit('capture_error', {'source': 'state', 'error': str(exc)})
            self.stopping.wait(max(0.001, .05 - (time.monotonic() - before)))

    def _frames(self, key):
        previous = None
        while not self.stopping.is_set():
            before = time.monotonic()
            try:
                frame, sequence, device = self.cameras.get(key)
                if sequence != previous:
                    self.submit('frame', {'camera': key, 'sequence': sequence, 'device': device}, frame)
                    previous = sequence
            except Exception as exc:
                self.submit('capture_error', {'source': key, 'error': str(exc)})
                self.stopping.wait(.5)
            self.stopping.wait(max(.001, .1 - (time.monotonic() - before)))

    def _aggregate(self, event):
        counts = self.meta['counts']
        kind = event['type']
        if kind == 'state':
            counts['states'] += 1
            state = event['state']
            valid = state['simulation'] or (state['robot_status'] == 'ready'
                    and state['feedback_age_ms'] is not None and state['feedback_age_ms'] <= 300
                    and state['rx_age_ms'] is not None and state['rx_age_ms'] <= 500)
            joints = state['joints_deg']
            if valid and joints and all(isinstance(q, (float, int)) for q in joints):
                counts['valid_states'] += 1
                if self.meta['first_joints_deg'] is None:
                    self.meta['first_joints_deg'] = joints
                    self.meta['joint_ranges_deg'] = [[q, q] for q in joints]
                self.meta['last_joints_deg'] = joints
                for limits, value in zip(self.meta['joint_ranges_deg'], joints):
                    limits[0], limits[1] = min(limits[0], value), max(limits[1], value)
                value = state['gripper_raw']
                if value is not None:
                    limits = self.meta['gripper_range_raw'] or [value, value]
                    self.meta['gripper_range_raw'] = [min(limits[0], value), max(limits[1], value)]
        elif kind == 'command':
            counts['commands'] += 1
            if event['accepted'] is not True:
                counts['rejected_commands'] += 1
            action = str(event['command'].get('action', 'unknown'))
            actions = self.meta['action_counts']
            actions[action] = actions.get(action, 0) + 1
        elif kind == 'marker':
            self.meta['markers'].append(event)
        elif kind == 'capture_error':
            counts['capture_errors'] += 1
        elif kind == 'frame':
            counts[event['camera']] += 1

    def _write(self):
        last_manifest = time.monotonic()
        try:
            with (self.path / 'timeline.jsonl').open('w', encoding='utf-8', buffering=1) as timeline:
                while not self.stopping.is_set() or not self.pending.empty():
                    try:
                        event, frame = self.pending.get(timeout=.1)
                    except queue.Empty:
                        event, frame = None, None
                    if event is not None:
                        if frame is not None:
                            relative = f"{event['camera']}/{event['t_ns']:016d}.jpg"
                            (self.path / relative).write_bytes(frame)
                            event['path'] = relative
                        line = json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n'
                        timeline.write(line)
                        with self.lock:
                            self._aggregate(event)
                            self.meta['bytes'] += len(line.encode()) + (len(frame) if frame else 0)
                    now = time.monotonic()
                    if now - last_manifest >= 2:
                        with self.lock:
                            self.meta['duration_s'] = round((time.monotonic_ns()-self.started)/1e9, 3)
                            if self.meta['duration_s'] >= 900 or self.meta['bytes'] >= 2_000_000_000:
                                self.meta['error'] = 'Recording reached the 15 minute / 2 GB limit.'
                                self.stopping.set()
                            elif shutil.disk_usage(self.path).free < 512_000_000:
                                self.meta['error'] = 'Less than 512 MB disk space remains.'
                                self.stopping.set()
                            progress = json.loads(json.dumps(self.meta))
                        write_json(self.path / 'manifest.json', progress)
                        last_manifest = now
        except Exception as exc:
            with self.lock:
                self.meta['error'] = f'Writing failed: {exc}'
            self.stopping.set()
        finally:
            with self.lock:
                self.stopping.set()
                self.meta['status'] = 'error' if self.meta['error'] else 'saved'
                self.meta['ended_at'] = utc_now()
                self.meta['duration_s'] = round((time.monotonic_ns()-self.started)/1e9, 3)
                try:
                    write_json(self.path / 'manifest.json', self.meta)
                except OSError as exc:
                    self.meta['status'] = 'error'
                    self.meta['error'] = f'Manifest could not be finalized: {exc}'
                self.done.set()

    def status(self):
        with self.lock:
            result = json.loads(json.dumps(self.meta))
            if not self.done.is_set():
                result['status'] = 'saving' if self.stopping.is_set() else 'recording'
                result['duration_s'] = round((time.monotonic_ns()-self.started)/1e9, 3)
            return result

    def stop(self, result):
        if result not in RESULTS:
            raise ValueError('无效示范结果')
        with self.lock:
            if not self.stopping.is_set():
                self.meta['result'] = result
                self.stopping.set()
        self.done.wait(5)
        return self.status()


class Demonstrations:
    def __init__(self, root, snapshot, cameras):
        self.root, self.snapshot, self.cameras = Path(root), snapshot, cameras
        self.lock = threading.Lock()
        self.current = None

    def start(self, name):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
            raise ValueError('请输入 1–120 个字符的示范名称')
        with self.lock:
            if self.current and not self.current.done.is_set():
                raise ValueError('已有示范正在录制或保存')
            initial = self.snapshot()
            if not initial['simulation'] and not initial.get('model_ready'):
                raise ValueError('请先在控制界面连接机械臂并取得实机反馈')
            self.root.mkdir(parents=True, exist_ok=True)
            if shutil.disk_usage(self.root).free < 512_000_000:
                raise ValueError('磁盘剩余空间不足 512 MB')
            self.current = Episode(self.root, name.strip(), self.snapshot, self.cameras, initial)
            return self.current.status()

    def status(self):
        return {'directory': str(self.root), 'episode': self.current.status() if self.current else None}

    def command(self, command, accepted, error='', at=None):
        current = self.current
        if current:
            current.submit('command', {'command': command, 'accepted': accepted, 'error': error}, at=at)

    def marker(self, phase, note):
        if phase not in PHASES or not isinstance(note, str) or len(note) > 500:
            raise ValueError('无效阶段或备注过长')
        current = self.current
        if not current or not current.submit('marker', {'phase': phase, 'note': note}):
            raise ValueError('当前没有正在录制的示范')
        return current.status()

    def stop(self, result='unspecified'):
        if not self.current:
            raise ValueError('当前没有示范')
        return self.current.stop(result)

    def episode_path(self, episode_id):
        if not re.fullmatch(r'\d{8}T\d{6}_[a-f0-9]{12}', episode_id):
            raise ValueError('无效示范编号')
        path = self.root / episode_id
        if path.is_symlink() or not path.is_dir():
            raise ValueError('示范不存在')
        return path

    def read(self, episode_id):
        if self.current and self.current.id == episode_id:
            return self.current.status()
        data = json.loads((self.episode_path(episode_id) / 'manifest.json').read_text(encoding='utf-8'))
        if data['status'] in ('recording', 'saving'):
            data['status'] = 'interrupted'
            data['error'] = 'Service exited before recording was finalized; available files are retained.'
        return data

    def history(self):
        result = []
        for path in sorted(self.root.glob('*/manifest.json'), reverse=True)[:50]:
            try:
                result.append(self.read(path.parent.name))
            except (ValueError, OSError):
                continue
        return result

    def close(self):
        if self.current and not self.current.done.is_set():
            self.current.stop('partial')
