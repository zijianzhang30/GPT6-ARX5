"""Replace the idle closed-gripper helper without releasing powered hold."""
import os
import json
from pathlib import Path
import select
import signal
import time

from policy_adapter import ROOT
from motion_safety import POLICY_SETTLE_ERROR_DEG, finite, vector


def validate_holder_command(argv, cwd, owner, url):
    if len(argv) < 2:
        raise ValueError('Missing holder command')
    script_index = 2 if argv[1] == '-u' else 1
    script = (Path(cwd) / argv[script_index]).resolve()
    if script != ROOT / 'tools/fast_reset_closed.py':
        raise ValueError('Only the idle fast_reset_closed helper can be replaced')
    options = argv[script_index + 1:]
    expected = {'--url': url, '--paired-client': owner}
    if len(options) != 4 or dict(zip(options[::2], options[1::2])) != expected:
        raise ValueError('Holder URL/owner must match exactly; custom targets are unsupported')


def held_snapshot(robots, *, require_closed=True):
    result = {}
    for side, robot in robots.items():
        state = robot.backend._read(holding=True)
        if state.get('moving') or state.get('policy_trajectory_active'):
            raise ValueError('Cannot adopt an active trajectory')
        closed = robot.settings['gripper']['command_closed_raw']
        if require_closed and abs(state['gripper_command_raw'] - closed) > .01:
            raise ValueError('Helper has not finished closing the empty grippers')
        result[side] = state
    return result


class IdleHoldHandoff:
    snapshot = staticmethod(held_snapshot)

    def __init__(self, pid, owner, url):
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Invalid holder PID')
        self.fd = os.pidfd_open(pid)
        try:
            proc = Path('/proc') / str(pid)
            argv = proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            validate_holder_command(argv, proc.joinpath('cwd').resolve(), owner, url)
        except BaseException:
            self.close()
            raise

    def transfer(self, robots, supervisors):
        # Both new watchdogs must already run before retiring the heartbeat-only
        # helper. Its normal exit sends stop, so it must not run that cleanup.
        for supervisor in supervisors.values():
            supervisor.check()
        before = self.snapshot(robots)
        signal.pidfd_send_signal(self.fd, signal.SIGKILL)
        poller = select.poll()
        poller.register(self.fd, select.POLLIN)
        if not poller.poll(1000):
            raise RuntimeError('Previous holder did not exit; no policy motion is allowed')
        after = self.snapshot(robots)
        for side in robots:
            if (max(abs(a-b) for a, b in zip(before[side]['command_deg'],
                                             after[side]['command_deg'])) > .05
                    or abs(before[side]['gripper_command_raw'] -
                           after[side]['gripper_command_raw']) > .01):
                raise RuntimeError('Targets changed during hold transfer')
        return {'adopted': True, 'released_hold': False,
                'joint_commands_deg': {side: state['command_deg'] for side, state in after.items()}}

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def validate_parked_policy(last, maximum_segments):
    if (last.get('event') != 'device_finish'
            or last.get('result', {}).get('control_state') != 'holding'):
        raise ValueError('Policy has not finished a segment in powered hold')
    terminal = last.get('trigger') in ('done', 'give_up')
    exhausted = (last.get('trigger') in ('budget_exhausted', 'motion_budget_boundary',
                                        'gripper_budget_boundary')
                 and last.get('segment', 0) >= maximum_segments)
    if not (terminal or exhausted):
        raise ValueError('Policy may still automatically continue')


class ParkedPolicyHandoff(IdleHoldHandoff):
    """Adopt a policy after its final segment, including a retained object."""
    def __init__(self, pid, owner, url, directory):
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Invalid policy PID')
        self.fd = os.pidfd_open(pid)
        try:
            proc = Path('/proc') / str(pid)
            argv = proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            index = 2 if argv[1] == '-u' else 1
            if (proc.joinpath('cwd').resolve() / argv[index]).resolve() != ROOT / 'supervised_dual_policy.py':
                raise ValueError('Expected the supervised dual policy host')
            def option(name, default=None):
                return argv[argv.index(name)+1] if name in argv else default
            if option('--paired-client') != owner or option('--url', 'http://127.0.0.1:8768') != url:
                raise ValueError('Policy owner or URL mismatch')
            self.maximum_segments = int(option('--max-segments', '8'))
            self.events = (Path(directory) / 'events.jsonl').resolve()
            if self.events not in [p.resolve() for p in proc.joinpath('fd').iterdir()]:
                raise ValueError('Policy does not own this recording')
            self.contents = self.events.read_bytes()
            validate_parked_policy(json.loads(self.contents.splitlines()[-1]), self.maximum_segments)
        except BaseException:
            self.close()
            raise

    def snapshot(self, robots):
        if self.events.read_bytes() != self.contents:
            raise ValueError('Policy recording changed; do not transfer an active host')
        return held_snapshot(robots, require_closed=False)


def validate_completed_reset(saved, last):
    if (set(saved) != {'left', 'right'}
            or last.get('event') != 'close_empty_gripper'
            or last.get('control_state') != 'holding'):
        raise ValueError('No completed closed-gripper reset record')
    for state in saved.values():
        if (state.get('enabled') is not True or state.get('moving') is not False
                or state.get('control_state') != 'holding' or state.get('error_codes') != []):
            raise ValueError('Reset record does not show both arms held and ready')


class CompletedResetHandoff(IdleHoldHandoff):
    """Adopt only the closed, stationary completion of held_dual_reset."""
    def __init__(self, pid, owner, url):
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Invalid reset PID')
        self.fd = os.pidfd_open(pid)
        try:
            proc = Path('/proc') / str(pid)
            argv = proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            index = 2 if argv[1] == '-u' else 1
            cwd = proc.joinpath('cwd').resolve()
            if (cwd / argv[index]).resolve() != ROOT / 'tools/held_dual_reset.py':
                raise ValueError('Expected the held dual reset host')
            def option(name, default=None):
                return argv[argv.index(name)+1] if name in argv else default
            if option('--paired-client') != owner or option('--url', 'http://127.0.0.1:8768') != url:
                raise ValueError('Reset owner or URL mismatch')
            directory = (cwd / option('--output')).resolve()
            self.events = directory / 'events.jsonl'
            if self.events not in [p.resolve() for p in proc.joinpath('fd').iterdir()]:
                raise ValueError('Reset process does not own this recording')
            marker = directory / 'reset_complete_state.json'
            self.contents = self.events.read_bytes()
            self.saved = json.loads(marker.read_text())
            validate_completed_reset(self.saved, json.loads(self.contents.splitlines()[-1]))
            if marker.stat().st_mtime_ns < self.events.stat().st_mtime_ns:
                raise ValueError('Reset completion record predates latest motion')
        except BaseException:
            self.close()
            raise

    def snapshot(self, robots):
        if self.events.read_bytes() != self.contents:
            raise ValueError('Reset resumed activity; cannot adopt')
        states = held_snapshot(robots)
        for side, state in states.items():
            if (max(abs(a-b) for a, b in zip(state['command_deg'], self.saved[side]['command_deg'])) > .05
                    or abs(state['gripper_command_raw']-self.saved[side]['gripper_command_raw']) > .01):
                raise ValueError('Held targets changed since reset completion')
        return states


class ObservingPolicyHandoff(IdleHoldHandoff):
    """Retire an inferring host only while its actuators remain stationary.

    Replacement watchdogs run first. Freeze all old host threads before the
    second snapshot so a late model response cannot race the transfer.
    """
    def __init__(self, pid, owner, url, directory):
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Invalid policy PID')
        self.fd = os.pidfd_open(pid)
        self.proc = Path('/proc') / str(pid)
        try:
            argv = self.proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            index = 2 if argv[1] == '-u' else 1
            if (self.proc.joinpath('cwd').resolve()/argv[index]).resolve() != ROOT/'supervised_dual_policy.py':
                raise ValueError('Expected the supervised dual policy host')
            def option(name, default=None):
                return argv[argv.index(name)+1] if name in argv else default
            if option('--paired-client') != owner or option('--url', 'http://127.0.0.1:8768') != url:
                raise ValueError('Policy owner or URL mismatch')
            self.events = (Path(directory)/'events.jsonl').resolve()
            if self.events not in [p.resolve() for p in self.proc.joinpath('fd').iterdir()]:
                raise ValueError('Policy does not own this recording')
        except BaseException:
            self.close()
            raise

    def snapshot(self, robots):
        return held_snapshot(robots, require_closed=False)

    def require_transfer_ready(self):
        if json.loads(self.events.read_bytes().splitlines()[-1]).get('event') != 'observation':
            raise ValueError('Wait until the policy is observing/inferencing')

    def transfer(self, robots, supervisors):
        for supervisor in supervisors.values():
            supervisor.check()
        self.require_transfer_ready()
        before = self.snapshot(robots)
        signal.pidfd_send_signal(self.fd, signal.SIGSTOP)
        deadline = time.monotonic() + 1
        while True:
            states = [p.joinpath('stat').read_text().rsplit(')', 1)[1].split()[0]
                      for p in self.proc.joinpath('task').iterdir()]
            if states and all(s in ('T', 't') for s in states):
                break
            if time.monotonic() > deadline:
                raise RuntimeError('Old host did not freeze; keep replacement supervision')
            time.sleep(.01)
        # Also reject a request that reached the server just before freezing.
        for _ in range(6):
            after = self.snapshot(robots)
            for side in robots:
                if (max(abs(a-b) for a, b in zip(before[side]['command_deg'], after[side]['command_deg'])) > .05
                        or abs(before[side]['gripper_command_raw']-after[side]['gripper_command_raw']) > .01):
                    raise RuntimeError('Targets changed while freezing the policy')
            for supervisor in supervisors.values():
                supervisor.check()
            time.sleep(.05)
        return super().transfer(robots, supervisors)


class SingleReviewHandoff(ObservingPolicyHandoff):
    """Adopt a stationary single-arm review host without releasing its hold."""
    def __init__(self, pid, owner, url, arm):
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Invalid review PID')
        self.fd = os.pidfd_open(pid)
        self.proc = Path('/proc') / str(pid)
        try:
            argv = self.proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            index = 2 if argv[1] == '-u' else 1
            cwd = self.proc.joinpath('cwd').resolve()
            if (cwd/argv[index]).resolve() != ROOT/'tools/single_policy_review.py':
                raise ValueError('Expected the single-arm review host')
            def option(name, default=None):
                return argv[argv.index(name)+1] if name in argv else default
            if (option('--paired-client') != owner or option('--arm') != arm
                    or option('--url', 'http://127.0.0.1:8768') != url):
                raise ValueError('Review arm, owner or URL mismatch')
            self.events = (cwd/option('--output')/'events.jsonl').resolve()
            if self.events not in [p.resolve() for p in self.proc.joinpath('fd').iterdir()]:
                raise ValueError('Review host does not own its recording')
        except BaseException:
            self.close()
            raise


class ObserverPreparationHoldHandoff(ObservingPolicyHandoff):
    """Recover a retained single-arm hold after observer preparation was rejected."""
    def __init__(self, pid, owner, url, arm, require_other_idle):
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Invalid observer holder PID')
        self.fd = os.pidfd_open(pid)
        self.proc = Path('/proc') / str(pid)
        self.require_other_idle = require_other_idle
        self.arm = arm
        try:
            argv = self.proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            index = 2 if argv[1] == '-u' else 1
            cwd = self.proc.joinpath('cwd').resolve()
            def option(name, default=None):
                return argv[argv.index(name)+1] if name in argv else default
            if ((cwd/argv[index]).resolve() != ROOT/'tools/held_policy_review.py'
                    or option('--paired-client') != owner or option('--adopt-arm') != arm
                    or option('--url', 'http://127.0.0.1:8768') != url
                    or not option('--from-single-review-pid')):
                raise ValueError('Expected the matching observer preparation host')
            self.events = (cwd/option('--output')/'events.jsonl').resolve()
            if self.events not in [p.resolve() for p in self.proc.joinpath('fd').iterdir()]:
                raise ValueError('Observer host does not own its recording')
            self.contents = self.events.read_bytes()
            self.require_transfer_ready()
        except BaseException:
            self.close()
            raise

    def require_transfer_ready(self):
        if self.events.read_bytes() != self.contents:
            raise ValueError('Observer holder recording changed')
        events = [json.loads(x) for x in self.contents.splitlines()]
        if (not events or events[-1].get('event') != 'observer_preparation_failed'
                or not any(e.get('event') == 'powered_hold_adopted'
                           and e.get('adopted') is True and e.get('released_hold') is False
                           and set(e.get('joint_commands_deg', {})) == {self.arm} for e in events)
                or any(e.get('event') == 'request' for e in events)):
            raise ValueError('No inactive observer preparation failure with retained hold')
        self.require_other_idle()

    def snapshot(self, robots):
        if set(robots) != {self.arm}:
            raise ValueError('Only the retained working arm can be adopted')
        self.require_transfer_ready()
        return held_snapshot(robots, require_closed=False)


def validate_completed_review(initial, events, failed_result=None):
    """Require either completed stacking or an explicitly failed, recovered trial."""
    required = ('left_placement_visually_verified', 'left_return_complete',
                'right_phase_authorized', 'stack_release_and_withdrawal_visually_verified',
                'right_return_complete')
    stage = 0
    completed = None
    for i, event in enumerate(events):
        if stage < len(required) and event.get('event') == required[stage]:
            stage += 1
            if stage == len(required):
                completed = i
    if completed is None and failed_result is not None:
        # Failure recovery must remain distinct from successful placement/stacking.
        # Its marker references an actual observation in this host's owned log.
        result = failed_result
        recovery_at = result.get('recovery_finished_at_s')
        if (result.get('status') != 'failed_recovered_holding'
                or result.get('reported_success') is not False
                or result.get('program_verified_success') is not False
                or result.get('both_at_initial_verified') is not True
                or result.get('right_phase_started') is not False
                or not finite(recovery_at)
                or not finite(result.get('task_failure_at_s'))
                or result['task_failure_at_s'] >= recovery_at
                or any(e.get('event') == 'right_phase_authorized' for e in events)):
            raise ValueError('An explicitly failed and recovered pre-right-phase trial is required')
        completed = next((i for i, e in enumerate(events)
            if e.get('event') == 'observation' and e.get('at_s') == recovery_at), None)
    if completed is None or not events or events[-1].get('event') != 'observation':
        raise ValueError('Completed sequential review and final observation required')
    if any(e.get('event') != 'observation' for e in events[completed+1:]):
        raise ValueError('Review resumed activity after completion')
    saved = {}
    for side, channel in (('left', 'can0'), ('right', 'can1')):
        goal = initial.get(side, {}).get('joints_deg')
        state = events[-1].get('state', {}).get('arms', {}).get(side, {}).get('raw_state', {})
        if (not vector(goal) or initial[side].get('channel') != channel
                or state.get('channel') != channel or state.get('enabled') is not True
                or state.get('moving') is not False or state.get('control_state') != 'holding'
                or state.get('policy_trajectory_active') is not False
                or state.get('error_codes') != []):
            raise ValueError('Both arms must be healthy, stationary and at recorded initial poses')
        for key in ('joints_deg', 'command_deg'):
            if (not vector(state.get(key)) or
                    max(abs(a-b) for a, b in zip(state[key], goal)) > POLICY_SETTLE_ERROR_DEG):
                raise ValueError('Both arms must have returned to recorded initial poses')
        if not finite(state.get('gripper_command_raw')) or not 4 <= state['gripper_command_raw'] <= 5:
            raise ValueError('Completed cup review requires open empty grippers; visually verify emptiness')
        saved[side] = state
    return saved


class CompletedReviewHandoff(ObservingPolicyHandoff):
    """Use the existing freeze/verify transfer after a completed sequential review."""
    def __init__(self, pid, owner, url, directory):
        if pid <= 1 or pid == os.getpid():
            raise ValueError('Invalid review PID')
        self.fd = os.pidfd_open(pid)
        self.proc = Path('/proc') / str(pid)
        try:
            argv = self.proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
            index = 2 if argv[1] == '-u' else 1
            cwd = self.proc.joinpath('cwd').resolve()
            if (cwd/argv[index]).resolve() != ROOT/'tools/held_policy_review.py':
                raise ValueError('Expected the dual-arm review host')
            def option(name, default=None):
                return argv[argv.index(name)+1] if name in argv else default
            if (option('--paired-client') != owner
                    or option('--url', 'http://127.0.0.1:8768') != url
                    or '--left-return-before-right' not in argv):
                raise ValueError('Sequential review owner, URL or mode mismatch')
            directory = Path(directory).resolve()
            if (cwd/option('--output')).resolve() != directory:
                raise ValueError('Review recording directory mismatch')
            self.events = directory/'events.jsonl'
            if self.events not in [p.resolve() for p in self.proc.joinpath('fd').iterdir()]:
                raise ValueError('Review process does not own this recording')
            self.contents = self.events.read_bytes()
            initial = json.loads((directory/'initial_state.json').read_text())
            result_path = directory.parent/'status.json'
            failed_result = json.loads(result_path.read_text()) if result_path.exists() else None
            self.saved = validate_completed_review(initial,
                [json.loads(line) for line in self.contents.splitlines()], failed_result)
        except BaseException:
            self.close()
            raise

    def snapshot(self, robots):
        if self.events.read_bytes() != self.contents:
            raise ValueError('Review recording changed; do not transfer an active host')
        states = held_snapshot(robots, require_closed=False)
        for side, state in states.items():
            if (max(abs(a-b) for a, b in zip(state['command_deg'], self.saved[side]['command_deg'])) > .05
                    or abs(state['gripper_command_raw']-self.saved[side]['gripper_command_raw']) > .01):
                raise ValueError('Held targets changed since review completion')
        return states
