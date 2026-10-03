from unittest.mock import Mock, patch
import unittest

from tools.held_policy_review import adopt_single_then_prepare_other


class ObserverHandoffTests(unittest.TestCase):
    def setup_hosts(self):
        events = []
        clients = {s: Mock(name=s) for s in ('left', 'right')}
        for client in clients.values():
            client.state.return_value = dict(robot_status='ready', enabled=False,
                                             moving=False, owner=None, gripper_raw=4.0)
        robots = {s: Mock() for s in clients}
        supervisors = {s: Mock() for s in clients}
        for side, supervisor in supervisors.items():
            supervisor.start.side_effect = lambda s=side: events.append('start_'+s)
        handoff = Mock()
        handoff.transfer.side_effect = lambda r, s: events.append('transfer') or {'adopted': True}
        handoff.close.side_effect = lambda: events.append('retire_handle')
        return events, clients, robots, supervisors, handoff

    @patch('tools.held_policy_review.prepare_hold')
    def test_observer_never_enables_before_source_retirement(self, prepare):
        events, clients, robots, supervisors, handoff = self.setup_hosts()
        prepare.side_effect = lambda *a, **k: events.append('prepare_right')
        adopt_single_then_prepare_other('left', clients, robots, supervisors,
                                       handoff, Mock(), Mock())
        self.assertEqual(events, ['start_left', 'transfer', 'retire_handle', 'prepare_right', 'start_right'])
        handoff.transfer.assert_called_once_with({'left': robots['left']}, {'left': supervisors['left']})
        self.assertIs(prepare.call_args.args[0], clients['right'])
        clients['left'].command.assert_not_called()

    @patch('tools.held_policy_review.prepare_hold')
    def test_bad_observer_or_failed_transfer_cannot_enable_observer(self, prepare):
        for condition in ('observer_busy', 'handoff_failed', 'observer_changed', 'gripper_outside_enable_range'):
            with self.subTest(condition=condition):
                events, clients, robots, supervisors, handoff = self.setup_hosts()
                if condition == 'observer_busy':
                    clients['right'].state.return_value['enabled'] = True
                elif condition == 'handoff_failed':
                    handoff.transfer.side_effect = RuntimeError('no transfer')
                elif condition == 'gripper_outside_enable_range':
                    clients['right'].state.return_value['gripper_raw'] = 4.901
                else:
                    idle = dict(clients['right'].state.return_value)
                    clients['right'].state.side_effect = [idle, {**idle, 'owner': 'unexpected'}]
                with self.assertRaises((ValueError, RuntimeError)):
                    adopt_single_then_prepare_other('left', clients, robots, supervisors,
                                                   handoff, Mock(), Mock())
                prepare.assert_not_called()
                supervisors['right'].start.assert_not_called()

    @patch('tools.held_policy_review.prepare_hold', side_effect=ValueError('observer preparation failed'))
    def test_observer_failure_does_not_close_adopted_watchdog(self, prepare):
        events, clients, robots, supervisors, handoff = self.setup_hosts()
        with self.assertRaises(ValueError):
            adopt_single_then_prepare_other('left', clients, robots, supervisors,
                                           handoff, Mock(), Mock())
        supervisors['left'].close.assert_not_called()
        clients['left'].command.assert_not_called()

    def test_failed_observer_recovery_rejects_motion_or_changed_log(self):
        import json
        import tempfile
        from pathlib import Path
        from held_policy_handoff import ObserverPreparationHoldHandoff
        with tempfile.TemporaryDirectory() as directory:
            handoff = object.__new__(ObserverPreparationHoldHandoff)
            handoff.arm = 'left'
            handoff.events = Path(directory)/'events.jsonl'
            handoff.require_other_idle = Mock()
            adopted = dict(event='powered_hold_adopted', adopted=True, released_hold=False,
                           joint_commands_deg={'left': [0.]*6})
            failed = dict(event='observer_preparation_failed')
            def record(events):
                handoff.contents = ('\n'.join(json.dumps(e) for e in events)+'\n').encode()
                handoff.events.write_bytes(handoff.contents)
            record([adopted, failed])
            handoff.require_transfer_ready()
            handoff.require_other_idle.assert_called_once()
            for events in ([failed], [adopted, {'event':'observation'}],
                           [adopted, {'event':'request'}, failed]):
                record(events)
                with self.assertRaises(ValueError):
                    handoff.require_transfer_ready()
            record([adopted, failed])
            handoff.events.write_bytes(handoff.contents+b'changed')
            with self.assertRaises(ValueError):
                handoff.require_transfer_ready()
