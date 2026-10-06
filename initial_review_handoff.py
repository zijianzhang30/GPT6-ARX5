"""Recover a healthy initial review whose stdin is /dev/null.

Only a cold-prepared host with no accepted input is eligible. Reuse the existing
fresh-camera qualification and freeze/verify transfer; never enable or move here.
"""
import json
import os
from pathlib import Path

from camera_hold_recovery import CameraHoldHandoff
from motion_safety import finite, vector
from policy_adapter import ROOT


def validate_initial_review_log(events, owner, working_arm):
    allowed = {'hold_preparation', 'planning_configuration', 'observation',
               'working_arm_selected'}
    if (not events or any(e.get('event') not in allowed for e in events)
            or [e.get('event') for e in events[-3:]] != [
                'planning_configuration', 'observation', 'working_arm_selected']
            or any(e.get('event') != 'hold_preparation' for e in events[:-3])
            or {e.get('arm') for e in events[:-3]} != {'left', 'right'}
            or events[-3].get('one_arm_at_a_time') is not True
            or events[-1].get('source') != 'startup'
            or events[-1].get('arm') != working_arm):
        raise ValueError('Only initial prepared review with no input or actions is eligible')
    return validate_saved_review_hold(events[-2], owner)


def validate_saved_review_hold(observation, owner):
    """Validate the actual saved dual-arm observation, without log-envelope assumptions."""
    saved = {}
    for side, channel in [('left', 'can0'), ('right', 'can1')]:
        raw = observation.get('state', {}).get('arms', {}).get(side, {}).get('raw_state', {})
        if (raw.get('channel') != channel or raw.get('owner') != owner
                or raw.get('enabled') is not True or raw.get('moving') is not False
                or raw.get('control_state') != 'holding'
                or raw.get('policy_trajectory_active') is not False
                or raw.get('policy_execution_available') is not True
                or raw.get('robot_status') != 'ready' or raw.get('error_codes') != []
                or raw.get('worker_fault_reason') is not None
                or not vector(raw.get('command_deg'))
                or not finite(raw.get('gripper_command_raw'))):
            raise ValueError('Both arms must be healthy in the saved initial hold')
        saved[side] = raw
    return saved


class InitialReviewInputHandoff(CameraHoldHandoff):
    """No camera fault recovery: inherit only checked stationary transfer methods."""
    def __init__(self, pid, owner, url, directory, tracking_reserve_deg,
                 minimum_cartesian_command_step_deg):
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Invalid initial review PID')
        self.fd = os.pidfd_open(pid)
        self.proc = Path('/proc') / str(pid)
        try:
            argv = self.proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            index = 2 if argv[1] == '-u' else 1
            cwd = self.proc.joinpath('cwd').resolve()
            def option(name, default=None):
                return argv[argv.index(name)+1] if name in argv else default
            if ((cwd / argv[index]).resolve() != ROOT/'tools/held_policy_review.py'
                    or '--prepare-idle' not in argv or '--left-return-before-right' in argv
                    or option('--working-arm') not in ('left', 'right')
                    or option('--paired-client') != owner
                    or option('--url', 'http://127.0.0.1:8768') != url
                    or self.proc.joinpath('fd/0').resolve() != Path('/dev/null')):
                raise ValueError('Expected matching cold-prepared review with null stdin')
            for name, value, floor in [('--tracking-reserve-deg', tracking_reserve_deg, 3.5),
                    ('--minimum-cartesian-command-step-deg', minimum_cartesian_command_step_deg, 2.)]:
                old = float(option(name, '0'))
                if not finite(old) or not finite(value) or value < max(old, floor):
                    raise ValueError('Input recovery must retain source planning protections')
            directory = Path(directory).resolve()
            if directory != (cwd / option('--output')).resolve():
                raise ValueError('Initial review directory mismatch')
            self.events = directory/'events.jsonl'
            if self.events not in [p.resolve() for p in self.proc.joinpath('fd').iterdir()]:
                raise ValueError('Initial review does not own the event log')
            self.contents = self.events.read_bytes()
            self.saved = validate_initial_review_log(
                [json.loads(x) for x in self.contents.splitlines()], owner, option('--working-arm'))
            manifest = json.loads((directory.parent/'recording/manifest.json').read_text())
            self.expected_devices = manifest['camera_devices']
            if (set(self.expected_devices) != {'top', 'left', 'right'}
                    or len(set(self.expected_devices.values())) != 3
                    or not all(isinstance(v, str) and v for v in self.expected_devices.values())):
                raise ValueError('Three distinct original camera identities required')
            self.qualified_at = None
        except BaseException:
            self.close()
            raise
