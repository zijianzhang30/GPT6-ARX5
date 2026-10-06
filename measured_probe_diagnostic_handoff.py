"""Transfer a cancelled stationary failed probe only into a one-shot diagnosis.

Never clears the old outcome, grants ordinary motion, enables or homes. A fresh
user-requested diagnostic round is required. No source from this new diagnostic
mode is eligible, preventing chains of repeated attempts.
"""
import json
import os
from pathlib import Path

from camera_hold_recovery import CameraHoldHandoff, require_unchanged_targets
from initial_review_handoff import validate_saved_review_hold
from motion_safety import finite, vector
from policy_adapter import ROOT


def validate_failed_probe_for_diagnosis(events, owner):
    results = [i for i,e in enumerate(events) if e.get('event') == 'empty_probe_result']
    if len(results) != 1 or any(e.get('event') in ('host_terminated', 'host_quarantined',
                                                'joint_diagnostic_result') for e in events):
        raise ValueError('Exactly one completed non-faulted Cartesian probe is required')
    index = results[0]
    result = events[index]
    if (result.get('passed') is not False or result.get('stationary') is not True
            or result.get('motion_locked') is not True
            or result.get('failed_target_cancelled') is not True
            or result.get('control_state') != 'holding'
            or not vector(result.get('held_joints_deg'))):
        raise ValueError('Only a failed stationary measurement with cancelled target is eligible')
    tail = events[index+1:]
    if (len(tail) < 5 or tail[0].get('event') != 'observation'
            or tail[1].get('event') != 'review_command_finished'
            or tail[1].get('command') != 'probe-empty-up-3mm'
            or tail[1].get('outcome') != 'completed' or (len(tail)-2) % 3):
        raise ValueError('Source probe must be finished, followed only by fresh observation')
    for start, observation, end in zip(tail[2::3], tail[3::3], tail[4::3]):
        if (start.get('event') != 'review_command_started' or start.get('command') != 'observe'
                or observation.get('event') != 'observation'
                or end.get('event') != 'review_command_finished' or end.get('outcome') != 'completed'
                or start.get('command_index') != end.get('command_index')):
            raise ValueError('Only completed observe commands may follow the cancelled probe')
    saved = validate_saved_review_hold(tail[-2], owner)
    original = validate_saved_review_hold(tail[0], owner)
    require_unchanged_targets(original, saved)
    if (max(abs(a-b) for a,b in zip(saved['left']['command_deg'], result['held_joints_deg'])) > .05
            or not 4.79 <= saved['left']['gripper_command_raw'] <= 4.81):
        raise ValueError('Cancelled left target and open empty gripper must remain unchanged')
    return saved


class MeasuredProbeDiagnosticHandoff(CameraHoldHandoff):
    def __init__(self, pid, owner, url, directory, tracking_reserve_deg,
                 minimum_cartesian_command_step_deg):
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Invalid diagnostic source PID')
        self.fd = os.pidfd_open(pid)
        self.proc = Path('/proc')/str(pid)
        try:
            argv = self.proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            index = 2 if argv[1] == '-u' else 1
            cwd = self.proc.joinpath('cwd').resolve()
            def option(name, default=None):
                return argv[argv.index(name)+1] if name in argv else default
            if ((cwd/argv[index]).resolve() != ROOT/'tools/held_policy_review.py'
                    or '--one-empty-left-probe' not in argv or not option('--from-healthy-probe-pid')
                    or '--one-empty-left-joint-diagnostic' in argv
                    or option('--working-arm') != 'left'
                    or option('--paired-client') != owner
                    or option('--url', 'http://127.0.0.1:8768') != url):
                raise ValueError('Source must be the original single Cartesian-probe host')
            for flag,value,floor in [('--tracking-reserve-deg',tracking_reserve_deg,3.5),
                    ('--minimum-cartesian-command-step-deg',minimum_cartesian_command_step_deg,2.)]:
                old = float(option(flag,'0'))
                if not finite(old) or not finite(value) or value < max(old,floor):
                    raise ValueError('All original ordinary planning protections must be retained')
            directory = Path(directory).resolve()
            if directory != (cwd/option('--output')).resolve():
                raise ValueError('Source diagnostic directory mismatch')
            self.events = directory/'events.jsonl'
            if self.events not in [p.resolve() for p in self.proc.joinpath('fd').iterdir()]:
                raise ValueError('Source does not own its event log')
            self.contents = self.events.read_bytes()
            self.saved = validate_failed_probe_for_diagnosis(
                [json.loads(line) for line in self.contents.splitlines()],owner)
            self.expected_devices = json.loads(
                (directory.parent/'recording/manifest.json').read_text())['camera_devices']
            if (set(self.expected_devices) != {'top','left','right'}
                    or len(set(self.expected_devices.values())) != 3
                    or not all(isinstance(v,str) and v for v in self.expected_devices.values())):
                raise ValueError('Three original distinct camera identities required')
            self.qualified_at = None
        except BaseException:
            self.close()
            raise
