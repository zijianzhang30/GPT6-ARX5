"""Explicit replacement of a camera-faulted, stationary review host.

The old camera fault is never cleared. Fresh replacement supervision must be
qualified before the existing freeze/verify powered-hold transfer is used.
This module does not enable, home, release a gripper, or submit trajectories.
"""
import json
import os
from pathlib import Path
import time

from held_policy_handoff import ObservingPolicyHandoff, held_snapshot
from motion_safety import finite, vector
from policy_adapter import ROOT


CAMERA_REJECTION = ('Fresh camera observation required; stationary hold retained: '
                    'Camera supervision failed: ValueError: '
                    'Camera sequence did not advance or device changed')
CAMERA_TIMEOUT_REJECTION = ('Fresh camera observation required; stationary hold retained: '
                            'Camera supervision failed: URLError: '
                            '<urlopen error timed out>')
CAMERA_DECODE_REJECTION = ('Fresh camera observation required; stationary hold retained: '
                           'Camera supervision failed: OSError: '
                           'broken data stream when reading image file')


def validate_camera_hold_log(events):
    """Only completed observation followed exclusively by rejected camera work."""
    indices = [i for i, e in enumerate(events) if e.get('event') == 'observation']
    if not indices:
        raise ValueError('Missing pre-fault observation')
    i = indices[-1]
    tail = events[i+1:]
    if not tail or tail[0].get('event') != 'review_command_finished' or tail[0].get('outcome') != 'completed':
        raise ValueError('Last observation must belong to a completed command')
    tail = tail[1:]
    if not tail or len(tail) % 3:
        raise ValueError('Camera rejection must finish without pending work')
    for start, rejected, finish in zip(tail[0::3], tail[1::3], tail[2::3]):
        if (start.get('event') != 'review_command_started'
                or rejected.get('event') != 'rejected'
                or rejected.get('reason') not in (CAMERA_REJECTION, CAMERA_TIMEOUT_REJECTION,
                                                CAMERA_DECODE_REJECTION)
                or finish.get('event') != 'review_command_finished'
                or finish.get('outcome') != 'rejected'
                or start.get('command_index') != finish.get('command_index')):
            raise ValueError('Only stationary camera rejections may follow the saved hold')
    saved = {}
    for side, channel in [('left', 'can0'), ('right', 'can1')]:
        raw = events[i].get('state', {}).get('arms', {}).get(side, {}).get('raw_state', {})
        if (raw.get('channel') != channel or raw.get('enabled') is not True
                or raw.get('moving') is not False or raw.get('control_state') != 'holding'
                or raw.get('policy_trajectory_active') is not False
                or raw.get('robot_status') != 'ready' or raw.get('error_codes') != []
                or not vector(raw.get('command_deg'))
                or not finite(raw.get('gripper_command_raw'))):
            raise ValueError('Last observation must show both arms in healthy stationary hold')
        saved[side] = raw
    return saved


def require_unchanged_targets(saved, states):
    if set(states) != {'left', 'right'}:
        raise ValueError('Both held arms are required')
    for side, state in states.items():
        if (not vector(state.get('command_deg')) or not finite(state.get('gripper_command_raw'))
                or state.get('owner') != saved[side].get('owner')
                or max(abs(a-b) for a, b in zip(state['command_deg'], saved[side]['command_deg'])) > .05
                or abs(state['gripper_command_raw']-saved[side]['gripper_command_raw']) > .01):
            raise ValueError('Held targets or owner changed since last valid observation')


class CameraHoldHandoff(ObservingPolicyHandoff):
    def __init__(self, pid, owner, url, directory, tracking_reserve_deg):
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Invalid review PID')
        self.fd = os.pidfd_open(pid)
        self.proc = Path('/proc')/str(pid)
        try:
            argv = self.proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            index = 2 if argv[1] == '-u' else 1
            cwd = self.proc.joinpath('cwd').resolve()
            def option(name, default=None):
                return argv[argv.index(name)+1] if name in argv else default
            if ((cwd/argv[index]).resolve() != ROOT/'tools/held_policy_review.py'
                    or option('--paired-client') != owner or option('--url', 'http://127.0.0.1:8768') != url
                    or not (option('--from-single-review-pid') or option('--from-camera-review-pid'))
                    or not option('--working-arm') or '--left-return-before-right' in argv):
                raise ValueError('Expected a matching stationary-gated dual review host')
            old_reserve = float(option('--tracking-reserve-deg', '0'))
            if not finite(tracking_reserve_deg) or tracking_reserve_deg < max(3.5, old_reserve):
                raise ValueError('Recovery must retain the source tracking reserve, at least 3.5 degrees')
            directory = Path(directory).resolve()
            if directory != (cwd/option('--output')).resolve():
                raise ValueError('Review output directory mismatch')
            self.events = directory/'events.jsonl'
            if self.events not in [p.resolve() for p in self.proc.joinpath('fd').iterdir()]:
                raise ValueError('Source host does not own the recording')
            self.contents = self.events.read_bytes()
            self.saved = validate_camera_hold_log([json.loads(x) for x in self.contents.splitlines()])
            if any(s.get('owner') != owner for s in self.saved.values()):
                raise ValueError('Saved hold owner mismatch')
            # Use the original recording's device identities, not newly discovered devices.
            reference = directory.parent/'recording'/'manifest.json'
            if reference.exists():
                manifest = json.loads(reference.read_text())
            else:
                manifest = json.loads((directory.parent/'recording_stop_deletion_summary.json').read_text())['manifest']
            self.expected_devices = manifest['camera_devices']
            if (set(self.expected_devices) != {'top', 'left', 'right'}
                    or len(set(self.expected_devices.values())) != 3
                    or not all(isinstance(v, str) and v for v in self.expected_devices.values())):
                raise ValueError('Three distinct original camera identities are required')
            self.qualified_at = None
        except BaseException:
            self.close()
            raise

    def require_transfer_ready(self):
        if self.events.read_bytes() != self.contents:
            raise ValueError('Source recording changed; requalify recovery')
        if self.qualified_at is None or not 0 <= time.monotonic()-self.qualified_at <= 5:
            raise ValueError('Fresh replacement-camera qualification is required')

    def snapshot(self, robots):
        if self.events.read_bytes() != self.contents:
            raise ValueError('Source recording changed; no transfer')
        states = held_snapshot(robots, require_closed=False)
        require_unchanged_targets(self.saved, states)
        return states

    def qualify(self, cameras, robots):
        """Read-only: >=2 seconds of advancing original devices and unchanged hold."""
        start = time.monotonic()
        previous = None
        samples = 0
        while True:
            batch = cameras.snapshot(after=time.time())
            descriptions = cameras.describe(batch)
            devices = {d['name']: d['device'] for d in descriptions}
            sequences = {d['name']: int(d['sequence']) for d in descriptions}
            if devices != self.expected_devices or len(descriptions) != 3:
                raise ValueError('Replacement camera identities differ from original trial')
            if previous is not None and any(sequences[s] <= previous[s] for s in sequences):
                raise ValueError('Replacement cameras are not continuously advancing')
            cameras.check()
            self.snapshot(robots)
            previous = sequences
            samples += 1
            if time.monotonic()-start >= 2 and samples >= 5:
                break
        self.qualified_at = time.monotonic()
        return {'duration_s': self.qualified_at-start, 'batches': samples,
                'devices': devices, 'last_sequences': sequences,
                'hardware_commands_sent': False}
