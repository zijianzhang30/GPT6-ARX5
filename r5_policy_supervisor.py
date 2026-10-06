"""Independent camera and heartbeat workers for the upstream R5 policy loop.

These workers do not enable or initialize hardware. A deployment host must keep
them alive through operator handoff. Closing an owned session requests the
existing protective stop, whose physical limitations still apply.
"""
import copy
import sys
import threading
import time
import traceback
from collections import deque

from r5_policy_backend import R5ExecutionFault, R5PoweredHoldFault
from motion_safety import finite


class CameraBatch(dict):
    def __init__(self, images, descriptions):
        super().__init__(images)
        self.descriptions = copy.deepcopy(descriptions)


class StationaryCameraGate:
    """Keep an already qualified manual hold during a camera-only outage.

    Fresh vision is still mandatory for every command and active movement.
    Hardware/ownership/hold faults retain their existing protective behavior.
    """
    def __init__(self, cameras, backend):
        self.cameras, self.backend = cameras, backend
        self.blocked_reason = None

    def check(self):
        try:
            self.cameras.check()
        except R5ExecutionFault as exc:
            with self.backend.command_lock:
                if self.backend.busy or not self.backend.engaged:
                    raise
                state = self.backend._read(holding=True)
                if state.get('moving') is not False or state.get('policy_trajectory_active') is not False:
                    raise
                self.blocked_reason = str(exc)
            return
        self.blocked_reason = None

    def require_fresh(self):
        try:
            self.cameras.check()
        except R5ExecutionFault as exc:
            raise ValueError('Fresh camera observation required; stationary hold retained: '+str(exc)) from exc

    def snapshot(self):
        try:
            return self.cameras.snapshot()
        except R5ExecutionFault as exc:
            raise ValueError('Cannot observe fresh images; stationary hold retained: '+str(exc)) from exc


class SupervisedCameras:
    def __init__(self, cameras, *, max_age=.5):
        self.source = cameras
        self.max_age = max_age
        self.condition = threading.Condition()
        self.done = threading.Event()
        self.thread = None
        self.batch = None
        self.received_at = None
        self.capture_started_at = None
        self.fault = None

    def start(self):
        if self.thread is not None:
            raise RuntimeError('Camera supervisor cannot be restarted')
        self.thread = threading.Thread(target=self._run, daemon=True, name='r5-policy-cameras')
        self.thread.start()
        return self.snapshot()

    def _run(self):
        try:
            while not self.done.is_set():
                began = time.time()
                images = self.source.snapshot(after=began)
                batch = CameraBatch(images, self.source.describe(images))
                stamps = [item.get('received_monotonic_s') for item in batch.descriptions]
                now = time.monotonic()
                if not stamps or any(not finite(stamp) or not 0 <= now-stamp <= self.max_age
                                     for stamp in stamps):
                    raise R5ExecutionFault('Camera receipt timestamps are stale or invalid')
                with self.condition:
                    self.batch = batch
                    self.capture_started_at = began
                    self.received_at = min(stamps)
                    self.condition.notify_all()
                self.done.wait(.05)
        except Exception as exc:
            with self.condition:
                self.fault = f'Camera supervision failed: {type(exc).__name__}: {exc}'
                self.condition.notify_all()

    def check(self):
        with self.condition:
            if self.done.is_set() or self.fault is not None:
                raise R5ExecutionFault(self.fault or 'Camera supervisor stopped')
            if self.received_at is None or not 0 <= time.monotonic()-self.received_at <= self.max_age:
                raise R5ExecutionFault('Supervised camera frames are stale')

    def snapshot(self, *, after=None):
        deadline = time.monotonic() + self.max_age
        with self.condition:
            while True:
                if self.done.is_set() or self.fault is not None:
                    raise R5ExecutionFault(self.fault or 'Camera supervisor stopped')
                if self.batch is not None and (after is None or self.capture_started_at >= after):
                    self.check()
                    return CameraBatch(self.batch, self.batch.descriptions)
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise R5ExecutionFault('Timed out waiting for new camera frames')
                self.condition.wait(remaining)

    def describe(self, images):
        return copy.deepcopy(images.descriptions)

    def close(self):
        self.done.set()
        with self.condition:
            self.condition.notify_all()
        if self.thread is not None:
            self.thread.join(timeout=1)


class R5PolicySupervisor:
    def __init__(self, robot, *, interval=.05, max_check_age=.3):
        self.robot = robot
        self.interval, self.max_check_age = interval, max_check_age
        self.done = threading.Event()
        self.thread = None
        self.last_check = None
        self.fault = None
        self.check_started_at = None
        self.check_samples = deque(maxlen=32)
        self.stall_diagnostic = None

    def _check_robot(self):
        self.check_started_at = time.monotonic()
        from fault_powered_hold import FaultHold
        try:
            if isinstance(getattr(self.robot, 'fault_hold', None), FaultHold):
                self.robot.supervise()
            else:
                self.robot.check()
        except R5PoweredHoldFault:
            # The arrival thread can latch between dispatch and acquiring its
            # command lock. That transition must not kill the heartbeat worker.
            self.robot.supervise()
        finished = time.monotonic()
        self.check_samples.append({'started_at': self.check_started_at,
                                   'duration_s': finished-self.check_started_at})
        self.last_check = finished
        self.check_started_at = None

    def diagnostics(self):
        return {'last_check': self.last_check, 'check_started_at': self.check_started_at,
                'recent_checks': list(self.check_samples), 'fault': self.fault,
                'stall': self.stall_diagnostic}

    def start(self):
        if self.thread is not None:
            raise RuntimeError('Policy supervisor cannot be restarted')
        self._check_robot()
        self.thread = threading.Thread(target=self._run, daemon=True, name='r5-policy-heartbeat')
        self.thread.start()

    def _run(self):
        try:
            while not self.done.wait(self.interval):
                self._check_robot()
        except Exception as exc:
            self.fault = str(exc)
            self.done.set()

    def check(self):
        if self.thread is None or self.done.is_set() or self.fault is not None:
            raise R5ExecutionFault(self.fault or 'Independent policy supervisor is not running')
        age = None if self.last_check is None else time.monotonic()-self.last_check
        if age is None or age > self.max_check_age:
            # Capture the worker location before abort waits for its command lock.
            # Keep the original timeout and protective-stop path unchanged.
            frame = sys._current_frames().get(self.thread.ident)
            stack = traceback.extract_stack(frame) if frame else []
            try:
                self.robot.abort(f'Independent policy heartbeat stalled: check_age_s={age}, '
                                 f'limit_s={self.max_check_age}, backend_busy={self.robot.busy}')
            finally:
                self.stall_diagnostic = {
                    'check_age_s': age, 'limit_s': self.max_check_age,
                    'arm': getattr(getattr(self.robot, 'client', None), 'arm', None),
                    'worker_stack': traceback.format_list(stack),
                }
        self.robot.vision_check()

    def close(self):
        self.done.set()
        if self.thread is not None:
            self.thread.join(timeout=1)
        if self.robot.engaged:
            try:
                self.robot.abort('Policy host closed before operator takeover')
            except R5ExecutionFault:
                pass
