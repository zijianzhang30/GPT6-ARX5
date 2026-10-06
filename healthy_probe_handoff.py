"""Narrow handoff of an idle healthy review into a one-shot empty-probe host.

Not a reset, camera-fault recovery, or a way to clear a probe result/lock. Reuses
the existing advancing-camera qualification and freeze/verify hold transfer.
"""
import json
import os
from pathlib import Path

from camera_hold_recovery import CameraHoldHandoff
from initial_review_handoff import validate_saved_review_hold
from motion_safety import finite
from policy_adapter import ROOT


def validate_healthy_probe_source(events, owner):
    if len(events) < 3 or [e.get('event') for e in events[-3:]] != [
            'review_command_started', 'observation', 'review_command_finished']:
        raise ValueError('Source must end with a completed fresh observe command')
    start, observation, finish = events[-3:]
    if (start.get('command') != 'observe' or finish.get('outcome') != 'completed'
            or start.get('command_index') != finish.get('command_index')
            or any(e.get('event') in ('host_terminated', 'empty_probe_result',
                                     'joint_diagnostic_result') for e in events)):
        raise ValueError('Active, failed or previously probed source is ineligible')
    selections = [e for e in events if e.get('event') == 'working_arm_selected']
    if not selections or selections[-1].get('arm') != 'left':
        raise ValueError('Source must already select the empty left arm')
    saved = validate_saved_review_hold(observation, owner)
    if not 4.79 <= saved['left']['gripper_command_raw'] <= 4.81:
        raise ValueError('Empty left probe requires the left gripper already fully open')
    return saved


class HealthyProbeHandoff(CameraHoldHandoff):
    def __init__(self, pid, owner, url, directory, tracking_reserve_deg,
                 minimum_cartesian_command_step_deg):
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Invalid source review PID')
        self.fd = os.pidfd_open(pid)
        self.proc = Path('/proc')/str(pid)
        try:
            argv = self.proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            index = 2 if argv[1] == '-u' else 1
            cwd = self.proc.joinpath('cwd').resolve()
            def option(name, default=None):
                return argv[argv.index(name)+1] if name in argv else default
            if ((cwd/argv[index]).resolve() != ROOT/'tools/held_policy_review.py'
                    or not option('--working-arm') or '--left-return-before-right' in argv
                    or any(flag in argv for flag in ('--from-camera-review-pid',
                        '--from-single-review-pid', '--from-healthy-probe-pid', '--one-empty-left-probe',
                        '--from-measured-probe-pid', '--one-empty-left-joint-diagnostic'))
                    or option('--paired-client') != owner
                    or option('--url', 'http://127.0.0.1:8768') != url):
                raise ValueError('Expected a matching healthy ordinary dual review host')
            for flag, value, floor in [('--tracking-reserve-deg', tracking_reserve_deg, 3.5),
                    ('--minimum-cartesian-command-step-deg', minimum_cartesian_command_step_deg, 2.)]:
                old = float(option(flag, '0'))
                if not finite(old) or not finite(value) or value < max(floor, old):
                    raise ValueError('Probe host must retain source ordinary planning protections')
            directory = Path(directory).resolve()
            if directory != (cwd/option('--output')).resolve():
                raise ValueError('Source review directory mismatch')
            self.events = directory/'events.jsonl'
            if self.events not in [p.resolve() for p in self.proc.joinpath('fd').iterdir()]:
                raise ValueError('Source does not own this event log')
            self.contents = self.events.read_bytes()
            self.saved = validate_healthy_probe_source(
                [json.loads(line) for line in self.contents.splitlines()], owner)
            self.expected_devices = json.loads(
                (directory.parent/'recording/manifest.json').read_text())['camera_devices']
            if (set(self.expected_devices) != {'top', 'left', 'right'}
                    or len(set(self.expected_devices.values())) != 3
                    or not all(isinstance(v, str) and v for v in self.expected_devices.values())):
                raise ValueError('Three distinct original camera identities required')
            self.qualified_at = None
        except BaseException:
            self.close()
            raise
