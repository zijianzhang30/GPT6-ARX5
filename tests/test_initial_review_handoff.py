import copy
import json
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import Mock, patch

from initial_review_handoff import InitialReviewInputHandoff, validate_initial_review_log


class InitialReviewTests(unittest.TestCase):
    def events(self):
        raw = {s: dict(channel=c, owner='owner', enabled=True, moving=False,
                      control_state='holding', policy_trajectory_active=False,
                      policy_execution_available=True, robot_status='ready',
                      error_codes=[], worker_fault_reason=None, command_deg=[0.] * 6,
                      gripper_command_raw=1.02)
               for s, c in [('left', 'can0'), ('right', 'can1')]}
        return [dict(event='hold_preparation', arm='left'),
                dict(event='hold_preparation', arm='right'),
                dict(event='planning_configuration', one_arm_at_a_time=True),
                dict(event='observation', state={'arms': {
                    s: {'raw_state': a} for s, a in raw.items()}}),
                dict(event='working_arm_selected', arm='right', source='startup')]

    def test_accepts_only_healthy_initial_hold_before_any_input(self):
        self.assertEqual(set(validate_initial_review_log(self.events(), 'owner', 'right')),
                         {'left', 'right'})
        for event in ('request', 'result', 'rejected', 'review_command_started',
                      'review_command_finished', 'host_terminated', 'observation'):
            for position in (0, 2, 5):
                es = self.events(); es.insert(position, dict(event=event))
                with self.subTest(event=event, position=position), self.assertRaises(ValueError):
                    validate_initial_review_log(es, 'owner', 'right')
        for key, value in [('owner', 'different'), ('enabled', False), ('moving', True),
                           ('control_state', 'disabled'), ('policy_trajectory_active', True),
                           ('policy_execution_available', False), ('channel', 'can1'),
                           ('error_codes', [1]), ('worker_fault_reason', 'stalled'),
                           ('command_deg', [float('nan')] * 6)]:
            es = self.events(); es[-2]['state']['arms']['left']['raw_state'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_initial_review_log(es, 'owner', 'right')

    @patch('held_policy_handoff.time.sleep')
    @patch('held_policy_handoff.select.poll')
    @patch('held_policy_handoff.signal.pidfd_send_signal')
    def test_transfer_preserves_loaded_grip_and_rejects_changed_targets(self, signals, poll, sleep):
        with tempfile.TemporaryDirectory() as d:
            h = object.__new__(InitialReviewInputHandoff)
            h.fd, h.proc = 123, Path(d)
            task = Path(d)/'task/1'; task.mkdir(parents=True)
            (task/'stat').write_text('1 (host) T 0')
            h.events = Path(d)/'events.jsonl'
            h.contents = ('\n'.join(json.dumps(e) for e in self.events())+'\n').encode()
            h.events.write_bytes(h.contents)
            h.saved = validate_initial_review_log(self.events(), 'owner', 'right')
            robots = {s: Mock() for s in ('left', 'right')}
            for s, r in robots.items():
                r.settings = {'gripper': {'command_closed_raw': .2}}
                r.backend._read.return_value = copy.deepcopy(h.saved[s])
            supervisors = {s: Mock() for s in robots}
            poll.return_value.poll.return_value = [(123, 1)]
            h.qualified_at = 9.
            with patch('camera_hold_recovery.time.monotonic', return_value=10.):
                result = h.transfer(robots, supervisors)
            self.assertFalse(result['released_hold'])
            self.assertEqual([c.args[1] for c in signals.call_args_list],
                             [signal.SIGSTOP, signal.SIGKILL])
            for r in robots.values():
                r.backend._read.assert_called_with(holding=True)
                r.backend._command.assert_not_called()
                r.backend.client.command.assert_not_called()
            for key, value in [('owner', 'other'), ('command_deg', [1.] * 6),
                               ('gripper_command_raw', .2)]:
                robots['right'].backend._read.return_value = {**h.saved['right'], key: value}
                with self.subTest(key=key), self.assertRaises(ValueError):
                    h.snapshot(robots)
            h.events.write_bytes(h.contents+b'changed')
            with self.assertRaises(ValueError):
                h.snapshot(robots)

    def check_host_qualifies_before_new_watchdogs_and_never_reenables(self, adopted=False):
        from tools import held_policy_review as module
        for failed in (False, True):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as d:
                calls = []
                client = Mock()
                client.request.return_value = {'paired_policy_client': 'owner'}
                camera, handoff = Mock(), Mock()
                camera.start.side_effect = lambda: calls.append('cameras')
                def qualify(*args):
                    calls.append('qualify')
                    if failed:
                        raise RuntimeError('unhealthy cameras')
                    return {'hardware_commands_sent': False}
                handoff.qualify.side_effect = qualify
                handoff.transfer.side_effect = lambda *args: calls.append('transfer') or {}
                supervisors = [Mock(), Mock()]
                for side, supervisor in zip(('left', 'right'), supervisors):
                    supervisor.start.side_effect = lambda s=side: calls.append(s)
                    supervisor.diagnostics.return_value = {}
                dual = Mock()
                dual.start.side_effect = RuntimeError('test stops before input loop')
                arms = [Mock(), Mock()]
                for arm in arms:
                    arm.backend.last_execution_feedback = None
                with patch.object(module, 'ArmWorkbenchClient', return_value=client), \
                     patch.object(module, 'R5DualCameras'), \
                     patch.object(module, 'SupervisedCameras', return_value=camera), \
                     patch.object(module, 'CartesianBackend', side_effect=arms), \
                     patch.object(module, 'DualCartesianBackend'), \
                     patch.object(module, 'R5PolicySupervisor', side_effect=supervisors), \
                     patch.object(module, 'DualSupervisor', return_value=dual), \
                     patch.object(module, 'AdoptedReviewInputHandoff' if adopted else 'InitialReviewInputHandoff', return_value=handoff), \
                     patch.object(module, 'prepare_hold') as prepare, \
                     patch.object(module.sys, 'argv', ['review', '--from-adopted-review-pid' if adopted else '--from-initial-review-pid', '123',
                         '--run', d, '--output', str(Path(d)/'new'), '--working-arm', 'right',
                         '--paired-client', 'owner', '--tracking-reserve-deg', '3.5',
                         '--minimum-cartesian-command-step-deg', '2']):
                    with self.assertRaises(RuntimeError):
                        module.main()
                self.assertEqual(calls, ['cameras', 'qualify'] if failed else
                                 ['cameras', 'qualify', 'left', 'right', 'transfer'])
                prepare.assert_not_called()
                client.command.assert_not_called()

    def test_host_qualifies_before_new_watchdogs_and_never_reenables(self):
        self.check_host_qualifies_before_new_watchdogs_and_never_reenables()

    def test_adopted_host_qualifies_and_never_reenables(self):
        self.check_host_qualifies_before_new_watchdogs_and_never_reenables(adopted=True)


if __name__ == '__main__':
    unittest.main()
