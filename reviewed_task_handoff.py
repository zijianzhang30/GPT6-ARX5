"""Resume an explicitly reviewed task after a cancelled precision diagnostic.

This preserves the failed diagnostic record and every ordinary task protection.
It never handles hardware/software faults, reconnects, enables, homes, reanchors
or submits targets. The caller must review task geometry before each new action.
"""
import hashlib
import json
import os
from pathlib import Path

from camera_hold_recovery import CameraHoldHandoff, require_unchanged_targets
from initial_review_handoff import validate_saved_review_hold
from motion_safety import finite, vector
from policy_adapter import ROOT


TASK_CRITERIA = {'settle_deg': 2.5, 'hold_deg': 3., 'trajectory_deg': 3.,
                 'minimum_progress': .4, 'reverse_deadband_deg': .3}


def result_hash(result):
    return hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()


def validate_reviewed_diagnostic(events, owner, review):
    indices = [i for i,e in enumerate(events) if e.get('event') == 'joint_diagnostic_result']
    if len(indices) != 1 or any(e.get('event') in ('host_terminated', 'host_quarantined',
                                                'empty_probe_result') for e in events):
        raise ValueError('Exactly one completed joint diagnostic without host fault required')
    index = indices[0]
    result = events[index]
    if (result.get('passed') is not False or result.get('stationary') is not True
            or result.get('motion_locked') is not True or result.get('failed_target_cancelled') is not True
            or result.get('control_state') != 'holding' or not vector(result.get('held_joints_deg'))):
        raise ValueError('Only a stationary failed measurement with cancelled target can be reviewed')
    if (review.get('schema_version') != 1 or review.get('source_result_sha256') != result_hash(result)
            or review.get('task_criteria') != TASK_CRITERIA
            or review.get('user_authorization') != '可以的 继续把 启动一下这个任务 录制视频之类的 类似之前的那些操作'
            or review.get('precision_diagnostic_is_not_task_gate') is not True):
        raise ValueError('Explicit task request and review of this exact diagnostic are required')
    tail = events[index+1:]
    if (len(tail) < 5 or tail[0].get('event') != 'observation'
            or tail[1].get('event') != 'review_command_finished'
            or tail[1].get('command') != 'diagnose-empty-left-j3'
            or tail[1].get('outcome') != 'completed' or (len(tail)-2) % 3):
        raise ValueError('Completed diagnostic followed by fresh observation required')
    for start, observation, end in zip(tail[2::3],tail[3::3],tail[4::3]):
        if (start.get('event') != 'review_command_started' or start.get('command') != 'observe'
                or observation.get('event') != 'observation'
                or end.get('event') != 'review_command_finished' or end.get('outcome') != 'completed'
                or start.get('command_index') != end.get('command_index')):
            raise ValueError('No new target, rejection, or pending command may follow the diagnostic')
    saved = validate_saved_review_hold(tail[-2], owner)
    require_unchanged_targets(validate_saved_review_hold(tail[0], owner), saved)
    if (max(abs(a-b) for a,b in zip(saved['left']['command_deg'],result['held_joints_deg'])) > .05
            or not 4.79 <= saved['left']['gripper_command_raw'] <= 4.81):
        raise ValueError('Original cancelled left target and empty-open gripper must be retained')
    return saved


class ReviewedTaskHandoff(CameraHoldHandoff):
    def __init__(self, pid, owner, url, directory, tracking_reserve_deg,
                 minimum_cartesian_command_step_deg, review_path):
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Invalid reviewed diagnostic PID')
        self.fd = os.pidfd_open(pid)
        self.proc = Path('/proc')/str(pid)
        try:
            argv = self.proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            index = 2 if argv[1] == '-u' else 1
            cwd = self.proc.joinpath('cwd').resolve()
            def option(name, default=None):
                return argv[argv.index(name)+1] if name in argv else default
            if ((cwd/argv[index]).resolve() != ROOT/'tools/held_policy_review.py'
                    or '--one-empty-left-joint-diagnostic' not in argv
                    or not option('--from-measured-probe-pid')
                    or option('--working-arm') != 'left'
                    or option('--paired-client') != owner
                    or option('--url','http://127.0.0.1:8768') != url):
                raise ValueError('Only the original isolated joint-diagnostic source is eligible')
            for flag,value,floor in [('--tracking-reserve-deg',tracking_reserve_deg,3.5),
                    ('--minimum-cartesian-command-step-deg',minimum_cartesian_command_step_deg,2.)]:
                old = float(option(flag,'0'))
                if not finite(old) or not finite(value) or value < max(old,floor):
                    raise ValueError('Original ordinary planning protections must remain unchanged')
            directory = Path(directory).resolve()
            if directory != (cwd/option('--output')).resolve():
                raise ValueError('Source diagnostic directory mismatch')
            self.events = directory/'events.jsonl'
            if self.events not in [p.resolve() for p in self.proc.joinpath('fd').iterdir()]:
                raise ValueError('Source does not own its event log')
            self.contents = self.events.read_bytes()
            self.review_path = Path(review_path).resolve()
            self.review_bytes = self.review_path.read_bytes()
            review = json.loads(self.review_bytes)
            evidence = directory.parent/'ERROR_REVIEW.md'
            if (review.get('source_run') != str(directory)
                    or review.get('evidence_sha256') != hashlib.sha256(evidence.read_bytes()).hexdigest()):
                raise ValueError('Review must reference the source run and unchanged error analysis')
            self.saved = validate_reviewed_diagnostic(
                [json.loads(line) for line in self.contents.splitlines()],owner,review)
            self.expected_devices = json.loads(
                (directory.parent/'recording/manifest.json').read_text())['camera_devices']
            if (set(self.expected_devices) != {'top','left','right'}
                    or len(set(self.expected_devices.values())) != 3
                    or not all(isinstance(v,str) and v for v in self.expected_devices.values())):
                raise ValueError('Three original camera identities required')
            self.qualified_at = None
        except BaseException:
            self.close()
            raise

    def require_transfer_ready(self):
        if self.review_path.read_bytes() != self.review_bytes:
            raise ValueError('Task review changed during qualification')
        super().require_transfer_ready()
