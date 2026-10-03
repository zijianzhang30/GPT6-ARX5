from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from held_policy_handoff import (IdleHoldHandoff, held_snapshot, validate_holder_command,
                                 validate_parked_policy, validate_completed_reset, CompletedResetHandoff,
                                 ObservingPolicyHandoff, SingleReviewHandoff)
from held_policy_handoff import CompletedReviewHandoff, validate_completed_review
from policy_adapter import ROOT


class HeldHandoffTests(unittest.TestCase):
    def completed_review(self):
        initial = {s: {'channel': c, 'joints_deg': [0.] * 6}
                   for s, c in (('left', 'can0'), ('right', 'can1'))}
        saved = {s: {'channel': initial[s]['channel'], 'enabled': True, 'moving': False,
                    'control_state': 'holding', 'policy_trajectory_active': False,
                    'error_codes': [], 'joints_deg': [0.] * 6, 'command_deg': [0.] * 6,
                    'gripper_command_raw': 4.48} for s in initial}
        events = [{'event': n} for n in ('left_placement_visually_verified',
                  'left_return_complete', 'right_phase_authorized',
                  'stack_release_and_withdrawal_visually_verified', 'right_return_complete')]
        events.append({'event': 'observation', 'state': {'arms': {
            s: {'raw_state': saved[s]} for s in initial}}})
        return initial, saved, events

    def test_new_trial_requires_complete_order_and_both_returns(self):
        import copy
        initial, saved, events = self.completed_review()
        self.assertEqual(validate_completed_review(initial, events), saved)
        for i in range(5):
            with self.subTest(missing_stage=i), self.assertRaises(ValueError):
                validate_completed_review(initial, events[:i]+events[i+1:])
        for key, value in [('enabled', False), ('moving', True),
                           ('policy_trajectory_active', True), ('joints_deg', [3.] * 6),
                           ('command_deg', [3.] * 6), ('gripper_command_raw', 3.5),
                           ('channel', 'can0'), ('error_codes', [2])]:
            bad = copy.deepcopy(events)
            bad[-1]['state']['arms']['right']['raw_state'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_completed_review(initial, bad)
        with self.assertRaisesRegex(ValueError, 'resumed activity'):
            validate_completed_review(initial, events[:-1]+[{'event': 'request'}, events[-1]])

    def test_failed_trial_handoff_requires_matching_recovery_observation_and_unchanged_hold(self):
        import copy
        initial, saved, success_events = self.completed_review()
        observed = {**success_events[-1], 'at_s': 20.}
        events = [{'event': 'request', 'at_s': 10.}, observed]
        failed = {'status': 'failed_recovered_holding', 'reported_success': False,
                  'program_verified_success': False, 'both_at_initial_verified': True,
                  'right_phase_started': False, 'task_failure_at_s': 11.,
                  'recovery_finished_at_s': 20.}
        self.assertEqual(validate_completed_review(initial, events, failed), saved)
        for change in ({'reported_success': True}, {'program_verified_success': True},
                       {'both_at_initial_verified': False}, {'right_phase_started': True},
                       {'recovery_finished_at_s': 19.}, {'task_failure_at_s': 21.}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_completed_review(initial, events, {**failed, **change})
        with self.assertRaises(ValueError):
            validate_completed_review(initial, events+[{'event': 'request'}, observed], failed)
        bad = copy.deepcopy(events)
        bad[-1]['state']['arms']['left']['raw_state']['joints_deg'] = [3.] * 6
        with self.assertRaises(ValueError):
            validate_completed_review(initial, bad, failed)

    @patch('held_policy_handoff.time.sleep')
    @patch('held_policy_handoff.select.poll')
    @patch('held_policy_handoff.signal.pidfd_send_signal')
    def test_completed_review_handoff_preserves_targets_and_freezes_old_host(self, kill, poll, sleep):
        import json
        import signal
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            initial, saved, events = self.completed_review()
            handoff = object.__new__(CompletedReviewHandoff)
            handoff.fd, handoff.proc = 10, Path(d)
            task = Path(d)/'task'/'1'; task.mkdir(parents=True)
            (task/'stat').write_text('1 (review) T 0 0')
            handoff.events = Path(d)/'events.jsonl'
            handoff.contents = ('\n'.join(json.dumps(e) for e in events)+'\n').encode()
            handoff.events.write_bytes(handoff.contents)
            handoff.saved = validate_completed_review(initial, events)
            robots = self.robots()
            for side in robots:
                robots[side].backend._read.return_value = dict(saved[side])
            poll.return_value.poll.return_value = [(10, 1)]
            result = handoff.transfer(robots, {'left': Mock(), 'right': Mock()})
            self.assertFalse(result['released_hold'])
            self.assertEqual([c.args[1] for c in kill.call_args_list], [signal.SIGSTOP, signal.SIGKILL])
            robots['right'].backend._read.return_value['command_deg'] = [1.] * 6
            with self.assertRaisesRegex(ValueError, 'targets changed'):
                handoff.snapshot(robots)
            handoff.events.write_bytes(handoff.contents+b'changed')
            with self.assertRaisesRegex(ValueError, 'recording changed'):
                handoff.snapshot(robots)

    def test_only_exact_idle_helper_and_owner_are_allowed(self):
        argv = ['python', '-u', 'tools/fast_reset_closed.py', '--url', 'http://localhost',
                '--paired-client', 'owner']
        validate_holder_command(argv, ROOT, 'owner', 'http://localhost')
        for bad in (argv[:2] + ['supervised_dual_policy.py'] + argv[3:],
                    argv[:-1] + ['other-owner'], argv + ['--closed-raw', '2']):
            with self.assertRaises(ValueError):
                validate_holder_command(bad, ROOT, 'owner', 'http://localhost')

    def robots(self):
        state = dict(moving=False, policy_trajectory_active=False,
                     gripper_command_raw=.23, command_deg=[0.] * 6)
        return {side: SimpleNamespace(backend=SimpleNamespace(_read=Mock(return_value=dict(state))),
                    settings={'gripper': {'command_closed_raw': .23}})
                for side in ('left', 'right')}

    def test_active_motion_and_unfinished_closure_are_rejected(self):
        for change in ({'moving': True}, {'policy_trajectory_active': True},
                       {'gripper_command_raw': 2.}):
            robots = self.robots()
            robots['left'].backend._read.return_value.update(change)
            with self.assertRaises(ValueError):
                held_snapshot(robots)

    def test_policy_handoff_keeps_object_opening_but_rejects_auto_continuation(self):
        robots = self.robots()
        robots['left'].backend._read.return_value['gripper_command_raw'] = 3.8
        self.assertEqual(held_snapshot(robots, require_closed=False)['left']['gripper_command_raw'], 3.8)
        event = {'event': 'device_finish', 'result': {'control_state': 'holding'},
                 'trigger': 'budget_exhausted', 'segment': 9}
        validate_parked_policy(event, 6)
        for bad in ({**event, 'segment': 5}, {**event, 'event': 'observation'},
                    {**event, 'result': {'control_state': 'active'}}):
            with self.assertRaises(ValueError):
                validate_parked_policy(bad, 6)

    def test_reset_handoff_requires_closed_stationary_completion_and_unchanged_targets(self):
        from pathlib import Path
        import tempfile
        states = {side: {'enabled': True, 'moving': False, 'control_state': 'holding',
                         'error_codes': [], 'command_deg': [0.] * 6, 'gripper_command_raw': .23}
                  for side in ('left', 'right')}
        last = {'event': 'close_empty_gripper', 'control_state': 'holding'}
        validate_completed_reset(states, last)
        with self.assertRaises(ValueError):
            validate_completed_reset(states, {'event': 'return_step'})
        with tempfile.TemporaryDirectory() as d:
            handoff = object.__new__(CompletedResetHandoff)
            handoff.events = Path(d)/'events.jsonl'
            handoff.events.write_bytes(b'complete')
            handoff.contents, handoff.saved = b'complete', states
            robots = self.robots()
            handoff.snapshot(robots)
            robots['left'].backend._read.return_value['command_deg'][0] = 1.
            with self.assertRaisesRegex(ValueError, 'targets changed'):
                handoff.snapshot(robots)
            handoff.events.write_bytes(b'new action')
            with self.assertRaisesRegex(ValueError, 'resumed activity'):
                handoff.snapshot(robots)

    @patch('held_policy_handoff.signal.pidfd_send_signal')
    def test_old_holder_is_not_retired_before_both_watchdogs_are_healthy(self, kill):
        handoff = object.__new__(IdleHoldHandoff)
        handoff.fd = 10
        supervisors = {'left': Mock(), 'right': Mock()}
        supervisors['right'].check.side_effect = RuntimeError('watchdog unavailable')
        with self.assertRaisesRegex(RuntimeError, 'watchdog'):
            handoff.transfer(self.robots(), supervisors)
        kill.assert_not_called()

    @patch('held_policy_handoff.select.poll')
    @patch('held_policy_handoff.signal.pidfd_send_signal')
    def test_transfer_preserves_targets_without_stop_enable_or_motion(self, kill, poll):
        poll.return_value.poll.return_value = [(10, 1)]
        handoff = object.__new__(IdleHoldHandoff)
        handoff.fd = 10
        robots = self.robots()
        result = handoff.transfer(robots, {'left': Mock(), 'right': Mock()})
        self.assertFalse(result['released_hold'])
        kill.assert_called_once()
        for robot in robots.values():
            self.assertEqual(robot.backend._read.call_count, 2)

    @patch('held_policy_handoff.time.sleep')
    @patch('held_policy_handoff.select.poll')
    @patch('held_policy_handoff.signal.pidfd_send_signal')
    def test_observing_transfer_freezes_before_verifying_and_retiring(self, kill, poll, sleep):
        import json
        import signal
        from pathlib import Path
        import tempfile
        for cls in (ObservingPolicyHandoff, SingleReviewHandoff):
            with self.subTest(cls=cls), tempfile.TemporaryDirectory() as d:
                handoff = object.__new__(cls)
                handoff.fd = 10
                handoff.proc = Path(d)
                task = Path(d)/'task'/'1'
                task.mkdir(parents=True)
                (task/'stat').write_text('1 (review host) T 0 0')
                handoff.events = Path(d)/'events.jsonl'
                handoff.events.write_text(json.dumps({'event': 'observation'})+'\n')
                robots = self.robots()
                robots['left'].backend._read.return_value['gripper_command_raw'] = 3.8
                supervisors = {'left': Mock(), 'right': Mock()}
                poll.return_value.poll.return_value = [(10, 1)]
                kill.reset_mock()
                sleep.reset_mock()
                result = handoff.transfer(robots, supervisors)
                self.assertFalse(result['released_hold'])
                self.assertEqual([call.args[1] for call in kill.call_args_list],
                                 [signal.SIGSTOP, signal.SIGKILL])
                self.assertEqual(robots['left'].backend._read.call_count, 9)
                self.assertEqual(sleep.call_count, 6)

    @patch('held_policy_handoff.signal.pidfd_send_signal')
    def test_inference_handoff_rejects_activity_or_unhealthy_watchdog_before_freeze(self, kill):
        import json
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            handoff = object.__new__(ObservingPolicyHandoff)
            handoff.fd = 10
            handoff.events = Path(d)/'events.jsonl'
            handoff.events.write_text(json.dumps({'event': 'request'})+'\n')
            supervisors = {'left': Mock(), 'right': Mock()}
            with self.assertRaisesRegex(ValueError, 'observing'):
                handoff.transfer(self.robots(), supervisors)
            handoff.events.write_text(json.dumps({'event': 'observation'})+'\n')
            robots = self.robots()
            robots['left'].backend._read.return_value['moving'] = True
            with self.assertRaisesRegex(ValueError, 'active trajectory'):
                handoff.transfer(robots, supervisors)
            supervisors['right'].check.side_effect = RuntimeError('watchdog failed')
            with self.assertRaisesRegex(RuntimeError, 'watchdog failed'):
                handoff.transfer(self.robots(), supervisors)
            kill.assert_not_called()

    @patch('held_policy_handoff.signal.pidfd_send_signal')
    def test_late_target_change_blocks_retirement_after_freeze(self, kill):
        import json
        import signal
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            handoff = object.__new__(ObservingPolicyHandoff)
            handoff.fd = 10
            handoff.proc = Path(d)
            task = Path(d)/'task'/'1'
            task.mkdir(parents=True)
            (task/'stat').write_text('1 (review) T 0 0')
            handoff.events = Path(d)/'events.jsonl'
            handoff.events.write_text(json.dumps({'event': 'observation'})+'\n')
            robots = self.robots()
            before = dict(robots['left'].backend._read.return_value)
            after = {**before, 'command_deg': [1.] * 6}
            robots['left'].backend._read.side_effect = [before, after]
            with self.assertRaisesRegex(RuntimeError, 'Targets changed'):
                handoff.transfer(robots, {'left': Mock(), 'right': Mock()})
            kill.assert_called_once_with(10, signal.SIGSTOP)


if __name__ == '__main__':
    unittest.main()
