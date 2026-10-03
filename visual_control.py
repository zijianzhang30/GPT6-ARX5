#!/usr/bin/env python3
"""Observe -> bounded joint/gripper action -> observe, supervised through JSON stdin.

No camera calibration or pixel-to-metre conversion is assumed. The caller selects
each action after inspecting both images; this is not an autonomous grasp policy.
"""
import argparse
import json
import queue
import re
import threading
import time
import urllib.request
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

import cv2
import numpy as np
from motion_safety import (ProposalGuard, feedback_issues, finite, vector, JOINT_STEP_DEG,
                           JOINT_STEP_NORM_DEG, JOINT_MARGIN_DEG, gripper_step_limit)


def detect_ball(jpeg):
    image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('Invalid camera JPEG')
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (30, 40, 70), (85, 255, 255))
    for operation, size in ((cv2.MORPH_OPEN, 5), (cv2.MORPH_CLOSE, 9)):
        mask = cv2.morphologyEx(mask, operation, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size)))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if len(contour) < 5 or area < 300:
            continue
        (x, y), (a, b), angle = cv2.fitEllipse(contour)
        if min(a, b) < 15 or max(a, b) / min(a, b) > 1.8:
            continue
        fill = area / (np.pi*a*b/4)
        if not .65 <= fill <= 1.25 or not (0 <= x < image.shape[1] and 0 <= y < image.shape[0]):
            continue
        candidates.append({'center_px': [round(x, 2), round(y, 2)],
                           'axes_px': [round(a, 2), round(b, 2)],
                           'area_px': round(area), 'ellipse_fill': round(fill, 3)})
    candidates.sort(key=lambda item: item['area_px'], reverse=True)
    return {'width': image.shape[1], 'height': image.shape[0],
            'ball_candidate': candidates[0] if candidates else None,
            'candidate_count': len(candidates),
            'note': 'Colour/shape candidate only; not a depth, contact, or clearance measurement.'}


def check_state(state):
    issues = feedback_issues(state)
    if issues:
        raise ValueError('; '.join(issues))
    q = np.asarray(state['joints_deg'], dtype=float)
    if state.get('simulation') is not False:
        raise ValueError('This session expects measured live feedback, not simulation')
    if state.get('robot_status') != 'ready':
        raise ValueError('Robot is not ready')
    if state.get('error_codes') != []:
        raise ValueError('SDK reported an error')
    return q


def validate_action(state, action):
    current = check_state(state)
    allowed = {'action', 'joint_delta_deg', 'joints_deg', 'gripper_raw'}
    if (not isinstance(action, dict) or set(action) - allowed
            or action.get('action', 'step') != 'step'):
        raise ValueError('Unknown motion fields or action')
    if not set(action) & {'joint_delta_deg', 'joints_deg', 'gripper_raw'}:
        raise ValueError('An explicit joint or gripper target is required')
    if 'gripper_raw' in action and set(action) & {'joint_delta_deg', 'joints_deg'}:
        raise ValueError('Arm motion and gripper motion must be separate steps')
    if 'joint_delta_deg' in action:
        if 'joints_deg' in action:
            raise ValueError('Use absolute joints or a relative step, not both')
        if not vector(action['joint_delta_deg']):
            raise ValueError('Supply six finite relative joint angles')
        delta = np.asarray(action['joint_delta_deg'], dtype=float)
        target = current + delta
    else:
        if 'joints_deg' in action and not vector(action['joints_deg']):
            raise ValueError('Supply six finite joint angles in degrees')
        target = np.asarray(action.get('joints_deg', current), dtype=float)
    if target.shape != (6,) or not np.isfinite(target).all():
        raise ValueError('Supply six finite joint angles in degrees')
    if np.max(np.abs(target-current)) > JOINT_STEP_DEG + 1e-9:
        raise ValueError(
            f'At most {JOINT_STEP_DEG:g} degrees per joint per observed step'
        )
    if np.linalg.norm(target-current) > JOINT_STEP_NORM_DEG + 1e-9:
        raise ValueError('Combined joint step is too large')
    lower = np.asarray(state['lower_deg']) + JOINT_MARGIN_DEG
    upper = np.asarray(state['upper_deg']) - JOINT_MARGIN_DEG
    if np.any(current < lower) or np.any(current > upper) or np.any(target < lower) or np.any(target > upper):
        raise ValueError('Current or target angles enter the 2-degree joint limit margin')
    output = {'joints_deg': target.tolist()}
    if 'gripper_raw' in action:
        grip = action['gripper_raw']
        reference = state['gripper_target_raw']
        if not finite(grip) or not 0 <= grip <= 5:
            raise ValueError('Gripper target must be finite and within 0..5 SDK units')
        limit = gripper_step_limit(grip, reference)
        if abs(grip-reference) > limit + 1e-9:
            raise ValueError(f'Gripper step exceeds {limit:g} SDK units in this direction')
        output['gripper_raw'] = grip
    return output


def step_settled(target, initial, samples, now, *, command_initial=None, min_progress=.7,
                 aggregate_progress=False, max_residual_deg=1.0, reverse_deadband_deg=0.):
    """Bounded residual plus observed progress; stability alone can be a stall."""
    if not finite(min_progress) or not 0 < min_progress <= 1:
        return False
    if not finite(max_residual_deg) or max_residual_deg <= 0:
        return False
    if not finite(reverse_deadband_deg) or not 0 <= reverse_deadband_deg <= min(.5, max_residual_deg):
        return False
    if not finite(now) or any(not finite(stamp) or stamp > now + 1e-9 for stamp, _ in samples):
        return False
    recent = [(stamp, q) for stamp, q in samples if now-stamp <= .65]
    if len(recent) < 5 or recent[-1][0]-recent[0][0] < .5:
        return False
    stamps = np.array([stamp for stamp, _ in recent])
    values = np.array([q for _, q in recent])
    if now-stamps[-1] > .15 or np.any(np.diff(stamps) <= 0) or np.max(np.diff(stamps)) > .15:
        return False
    if not np.isfinite(values).all() or np.max(np.ptp(values, axis=0)) > .1:
        return False
    requested = np.array(target['joints_deg'])
    delta = requested-(initial if command_initial is None else command_initial)
    changed = np.abs(delta) > .1
    if np.max(np.abs(values[-1]-requested)) > max_residual_deg:
        return False
    if not np.any(changed):
        return True
    progress = (values[-1]-initial)[changed] / delta[changed]
    if aggregate_progress:
        moved = (values[-1]-initial)[changed]
        requested_move = delta[changed]
        projected = float(np.dot(moved, requested_move) / np.dot(requested_move, requested_move))
        # Existing tracking error can put an encoder beyond the new target.
        # Returning toward that target is not a reversed actuator response.
        measured_remaining = (requested-initial)[changed]
        residual_recovery = ((measured_remaining*requested_move < 0)
                             & (moved*measured_remaining >= 0)
                             & (np.abs(moved) <= np.abs(measured_remaining)))
        # Tiny secondary encoder changes must not outweigh useful net progress.
        bounded_reverse = moved*np.sign(requested_move) >= -reverse_deadband_deg
        return bool(projected >= min_progress
                    and np.all((progress >= -.1) | residual_recovery | bounded_reverse))
    return bool(np.all(progress >= min_progress))


class WorkbenchClient:
    def __init__(self, base):
        parsed = urlsplit(base)
        if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.path not in ('', '/'):
            raise ValueError('Use a local workbench URL')
        self.base = base.rstrip('/')
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.client = 'visual-step-' + uuid.uuid4().hex
        self.token = None

    def request(self, path, data=None, timeout=.25):
        headers = {}
        if data is not None:
            if self.token is None:
                with self.opener.open(self.base+'/', timeout=1) as response:
                    self.token = re.search(rb'<meta name="control-token" content="([^"]+)"', response.read()).group(1).decode()
            headers = {'Content-Type': 'application/json', 'X-Control-Token': self.token}
        request = urllib.request.Request(self.base+path,
            data=None if data is None else json.dumps(data, allow_nan=False).encode(), headers=headers)
        with self.opener.open(request, timeout=timeout) as response:
            return json.load(response)

    def state(self):
        return self.request('/api/state')

    def command(self, action, **fields):
        return self.request('/api/command', {'action': action, 'client': self.client, **fields})

    def camera(self, key):
        with self.opener.open(self.base+f'/api/cameras/{key}/frame.jpg', timeout=1) as response:
            return response.read(), response.headers.get('X-Frame-Id'), response.headers.get('X-Camera-Device')


class ArmWorkbenchClient(WorkbenchClient):
    """Route one arm's state, commands, and wrist images through the same proxy."""

    def __init__(self, base, arm):
        if arm not in ('left', 'right'):
            raise ValueError('Explicit left or right arm required')
        super().__init__(base)
        self.arm = arm

    def state(self):
        return self.request(f'/api/arms/{self.arm}/state')

    def command(self, action, **fields):
        return self.request(f'/api/arms/{self.arm}/command',
                            {'action': action, 'client': self.client, **fields})

    def camera(self, key):
        return super().camera('gemini_right' if key == 'gemini' and self.arm == 'right' else key)


def observe(client, directory):
    directory.mkdir(parents=True, exist_ok=True)
    start = time.monotonic_ns()
    with ThreadPoolExecutor(max_workers=3) as pool:
        state_future = pool.submit(client.state)
        futures = {key: pool.submit(client.camera, key) for key in ('gemini', 'external')}
        state = state_future.result()
        cameras = {}
        for key, future in futures.items():
            jpeg, sequence, device = future.result()
            path = directory / f'{start}-{key}.jpg'
            path.write_bytes(jpeg)
            cameras[key] = dict(detect_ball(jpeg), image=str(path.resolve()), sequence=sequence, device=device)
    return {'observed_monotonic_ns': start, 'state': {key: value for key, value in state.items()
            if key not in ('frames', 'points', 'events', 'poses')}, 'cameras': cameras,
            'calibration': {'intrinsics': None, 'extrinsics': None, 'depth_available': False}}


class StepSession:
    """Only an explicitly submitted step enables control; stdin waits are bounded."""
    def __init__(self, client, directory):
        self.client, self.directory = client, directory
        self.lock = threading.Lock()
        self.active = False
        self.failure = None
        self.last_request = time.monotonic()
        self.last_vision = 0.
        self.vision_failure = None
        self.pending = None
        self.envelope = None
        self.done = threading.Event()
        self.latest = None
        self.episode = None
        self.log = None
        self.step_samples = deque(maxlen=32)
        self.guard = ProposalGuard()

    def emit(self, event):
        line = json.dumps(event, ensure_ascii=False, allow_nan=False)
        if self.log:
            self.log.write(line+'\n')
            self.log.flush()
        print(line, flush=True)

    def halt(self, reason):
        with self.lock:
            if self.active:
                try:
                    try:
                        current = self.client.state()
                    except Exception:
                        current = None
                    if current is None or current.get('owner') == self.client.client:
                        self.client.command('stop')
                finally:
                    self.active = False
            self.pending = None
            self.failure = reason
            self.guard.latch(reason)

    def heartbeat(self):
        while not self.done.wait(.05):
            try:
                with self.lock:
                    if not self.active:
                        continue
                    if self.vision_failure:
                        raise ValueError(self.vision_failure)
                    if time.monotonic()-self.last_request > 30:
                        raise ValueError('No supervised observation/action for 30 seconds')
                    if time.monotonic()-self.last_vision > 1:
                        raise ValueError('Camera frames stopped updating')
                    state = self.client.command('heartbeat')
                    q = check_state(state)
                    if not state['enabled'] or state['owner'] != self.client.client:
                        self.active = False
                        raise ValueError('Control was stopped or transferred')
                    if state.get('mode') != 'joint' or not finite(state.get('speed')) or not 0 < state['speed'] <= .1:
                        raise ValueError('Control mode or speed changed during the session')
                    self.guard.check_state(state)
                    self.latest = state
                    if self.envelope is not None and np.max(np.abs(q-self.envelope)) > 7:
                        raise ValueError('Measured displacement exceeded the step envelope')
                    if state.get('tracking_limited') or np.max(np.abs(state['tracking_error_deg'])) > 3.05:
                        raise ValueError('Joint tracking reached the existing lead limit')
                    if self.pending:
                        target, initial, deadline = self.pending
                        now = time.monotonic()
                        self.step_samples.append((now, q.copy()))
                        if now > deadline:
                            if not step_settled(target, initial, self.step_samples, now):
                                residual = (np.array(target['joints_deg'])-q).tolist()
                                raise ValueError(f'Joint target did not settle within the step window; residual_deg={residual}')
                            self.pending = None
                            self.emit({'event': 'step_window_ended', 'requested': target, 'measured': q.tolist(),
                                       'gripper_raw': state['gripper_raw'], 'instruction': 'Inspect images before another action.'})
            except Exception as exc:
                try:
                    self.halt(str(exc))
                except Exception:
                    pass
                self.emit({'event': 'halted', 'reason': str(exc)})

    def vision(self):
        sequences = {}
        devices = {}
        fresh = {key: 0. for key in ('gemini', 'external')}
        while not self.done.wait(.1):
            try:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = {key: pool.submit(self.client.camera, key) for key in fresh}
                    for key, future in futures.items():
                        jpeg, sequence, device = future.result()
                        if not device or key in devices and device != devices[key]:
                            raise ValueError('Camera identity changed or is unavailable')
                        devices[key] = device
                        if sequence is not None and key in sequences and sequence != sequences[key]:
                            detect_ball(jpeg)  # Reject undecodable camera data.
                            fresh[key] = time.monotonic()
                        sequences[key] = sequence
                if len(set(devices.values())) != 2:
                    raise ValueError('Both cameras resolve to one device')
                self.last_vision = min(fresh.values())
            except Exception as exc:
                self.last_vision = 0.
                self.vision_failure = f'Camera fault latched: {exc}'
                return

    def apply(self, action):
        try:
            self._apply(action)
        except Exception as exc:
            try:
                self.halt(str(exc))
            except Exception as stop_error:
                self.emit({'event': 'stop_unconfirmed', 'reason': str(stop_error)})
            raise

    def _apply(self, action):
        with self.lock:
            if self.failure:
                raise ValueError('Session halted; inspect the cause before starting a new session')
            if self.vision_failure:
                raise ValueError(self.vision_failure)
            if self.pending:
                raise ValueError('Wait for the current step window to end')
            state = self.client.state()
            target = validate_action(state, action)
            if state['enabled'] and state['owner'] != self.client.client:
                raise ValueError('Another controller owns the arm')
            if time.monotonic()-self.last_vision > .5:
                raise ValueError('Both cameras must provide fresh frames')
            budget_target = {'gripper_raw': target['gripper_raw']} if 'gripper_raw' in target else target
            self.guard.accept(state, budget_target)
            if not self.active:
                recording = self.client.request('/api/recording/status', timeout=1).get('episode')
                if not recording or recording['status'] not in ('recording', 'saving'):
                    self.episode = self.client.request('/api/recording/start',
                        {'name': 'Supervised visual grasp session'}, timeout=2)['id']
                elif recording['status'] == 'saving':
                    raise ValueError('Wait until the previous recording has been saved')
                self.client.command('settings', speed=.1, mode='joint')
                # An enable timeout can occur after the server accepted it.
                self.active = True
                enabled = self.client.command('enable')
                if enabled.get('owner') != self.client.client or not enabled.get('enabled'):
                    raise ValueError('Control ownership was not acquired')
            fresh = self.client.state()
            q = check_state(fresh)
            if (not fresh.get('enabled') or fresh.get('owner') != self.client.client
                    or fresh.get('mode') != 'joint' or not finite(fresh.get('speed'))
                    or not 0 < fresh['speed'] <= .1):
                raise ValueError('Control ownership, mode or speed is not valid')
            if (time.monotonic()-self.last_vision > .5
                    or np.max(np.abs(q-np.asarray(state['joints_deg']))) > .5
                    or abs(fresh['gripper_raw']-state['gripper_raw']) > .15):
                raise ValueError('State or vision changed before target submission')
            validate_action(fresh, budget_target)
            self.client.command('target', **target)
            self.envelope = np.array(state['joints_deg'])
            self.pending = (target, np.array(state['joints_deg']), time.monotonic()+5)
            self.step_samples.clear()
            self.last_request = time.monotonic()
            self.emit({'event': 'action_sent', 'joints_deg': target['joints_deg'],
                       'initial_joints_deg': state['joints_deg'],
                       'gripper_raw': target.get('gripper_raw', state['gripper_target_raw']), 'speed': .1})

    def run(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        self.log = (self.directory/'session.jsonl').open('x', encoding='utf-8')
        self.emit({'event': 'observation', **observe(self.client, self.directory)})
        inbox = queue.Queue()
        def read_stdin():
            import sys
            for line in sys.stdin:
                inbox.put(line)
            inbox.put(None)
        threading.Thread(target=read_stdin, daemon=True).start()
        workers = [threading.Thread(target=function, daemon=True) for function in (self.heartbeat, self.vision)]
        for worker in workers:
            worker.start()
        try:
            while True:
                try:
                    line = inbox.get(timeout=.2)
                except queue.Empty:
                    if self.failure:
                        break
                    continue
                if line is None:
                    break
                request = json.loads(line)
                self.last_request = time.monotonic()
                kind = request.get('action')
                if kind == 'stop':
                    break
                if kind == 'observe':
                    self.emit({'event': 'observation', **observe(self.client, self.directory)})
                elif kind == 'step':
                    self.apply(request)
                else:
                    raise ValueError('Use action observe, step, or stop')
        finally:
            try:
                self.halt('Session finished')
            finally:
                self.done.set()
                for worker in workers:
                    worker.join(timeout=2)
                try:
                    if self.episode:
                        current = self.client.request('/api/recording/status', timeout=1).get('episode')
                        if current and current['id'] == self.episode:
                            self.client.request('/api/recording/stop', {'result': 'partial'}, timeout=6)
                finally:
                    self.log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('observe', 'session'))
    parser.add_argument('--url', default='http://127.0.0.1:8768')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent/'analysis'/('visual-'+uuid.uuid4().hex[:10]))
    args = parser.parse_args()
    client = WorkbenchClient(args.url)
    if args.mode == 'observe':
        print(json.dumps(observe(client, args.output), ensure_ascii=False, indent=2))
    else:
        StepSession(client, args.output).run()


if __name__ == '__main__':
    main()
