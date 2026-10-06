"""Restore input for a freshly adopted dual hold with null stdin and no inputs.

No enable, release or trajectory operations. Existing camera qualification,
unchanged-target checks and supervised freeze/verify transfer remain mandatory.
"""
import json
import os
from pathlib import Path

from camera_hold_recovery import CameraHoldHandoff
from initial_review_handoff import validate_saved_review_hold
from motion_safety import finite, vector
from policy_adapter import ROOT


def validate_adopted_initial_log(events, owner, adopted_arm, working_arm):
    other = 'right' if adopted_arm == 'left' else 'left'
    if adopted_arm not in ('left', 'right') or working_arm not in ('left', 'right'):
        raise ValueError('Explicit valid adopted and working arms required')
    if len(events) < 5:
        raise ValueError('Incomplete adopted startup')
    first = events[0]
    if (first.get('event') != 'powered_hold_adopted' or first.get('adopted') is not True
            or first.get('released_hold') is not False
            or set(first.get('joint_commands_deg', {})) != {adopted_arm}
            or not vector(first['joint_commands_deg'][adopted_arm])):
        raise ValueError('Expected one preserved single-arm adoption')
    if (any(e.get('event') != 'hold_preparation' or e.get('arm') != other
            for e in events[1:-3])
            or [e.get('event') for e in events[-3:]] != [
                'planning_configuration', 'observation', 'working_arm_selected']
            or events[-3].get('one_arm_at_a_time') is not True
            or events[-3].get('retain_settle_fault_hold') is not False
            or events[-3].get('one_empty_left_probe') is not False
            or events[-3].get('one_empty_left_joint_diagnostic') is not False
            or events[-1].get('source') != 'startup'
            or events[-1].get('arm') != working_arm):
        raise ValueError('Only completed adopted startup with no input or actions is eligible')
    saved = validate_saved_review_hold(events[-2], owner)
    if max(abs(a-b) for a, b in zip(first['joint_commands_deg'][adopted_arm],
                                    saved[adopted_arm]['command_deg'])) > .05:
        raise ValueError('Adopted arm target changed during startup')
    return saved


class AdoptedReviewInputHandoff(CameraHoldHandoff):
    def __init__(self, pid, owner, url, directory, tracking_reserve_deg,
                 minimum_cartesian_command_step_deg):
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Invalid adopted review PID')
        self.fd = os.pidfd_open(pid)
        self.proc = Path('/proc') / str(pid)
        try:
            argv = self.proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            index = 2 if argv[1] == '-u' else 1
            cwd = self.proc.joinpath('cwd').resolve()
            def option(name, default=None):
                return argv[argv.index(name)+1] if name in argv else default
            if ((cwd/argv[index]).resolve() != ROOT/'tools/held_policy_review.py'
                    or not option('--from-single-review-pid')
                    or option('--adopt-arm') not in ('left', 'right')
                    or option('--working-arm') not in ('left', 'right')
                    or '--left-return-before-right' in argv
                    or option('--paired-client') != owner
                    or option('--url', 'http://127.0.0.1:8768') != url
                    or self.proc.joinpath('fd/0').resolve() != Path('/dev/null')):
                raise ValueError('Expected matching freshly adopted review with null stdin')
            for name, value, floor in [('--tracking-reserve-deg', tracking_reserve_deg, 3.5),
                    ('--minimum-cartesian-command-step-deg', minimum_cartesian_command_step_deg, 2.)]:
                old = float(option(name, '0'))
                if not finite(old) or not finite(value) or value < max(old, floor):
                    raise ValueError('Input recovery must retain source planning protections')
            directory = Path(directory).resolve()
            if directory != (cwd/option('--output')).resolve():
                raise ValueError('Adopted review directory mismatch')
            self.events = directory/'events.jsonl'
            if self.events not in [p.resolve() for p in self.proc.joinpath('fd').iterdir()]:
                raise ValueError('Source review does not own its log')
            self.contents = self.events.read_bytes()
            self.saved = validate_adopted_initial_log(
                [json.loads(x) for x in self.contents.splitlines()], owner,
                option('--adopt-arm'), option('--working-arm'))
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
