import unittest
from r5_sequential_trial import LeftReturnGate, WorkingArmGate, require_idle, renew_sequential_segment
from unittest.mock import Mock
from contextlib import nullcontext


class SequentialTrialTests(unittest.TestCase):
    def test_working_arm_rejects_paired_wrong_side_and_malformed_targets(self):
        gate = WorkingArmGate('right')
        good = {'target': {'left': None, 'right': {}}}
        gate.check_action('move_to', good)
        for name, args in [
                ('move_to', {'target': {'left': {}, 'right': {}}}),
                ('move_to', {'target': {'left': {}, 'right': None}}),
                ('move_to', {'target': {'left': None, 'right': None}}),
                ('move_to', {}), ('move_to', []),
                ('set_gripper', {'positions': {'left': .9, 'right': .9}}),
                ('check_path', {'poses': [{'left': None, 'right': {}}, {'left': {}, 'right': None}]}),
                ('move_eef_chunk', {'poses': None})]:
            with self.subTest(name=name, args=args), self.assertRaises(ValueError):
                gate.check_action(name, args)

    def test_switch_requires_two_stationary_holds_and_renew_preserves_other_arm(self):
        good = {**self.state(), 'policy_trajectory_active': False}
        gate = WorkingArmGate('right')
        for change in ({'moving': True}, {'enabled': False}, {'policy_trajectory_active': True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.select('left', {'left': good, 'right': {**good, **change}})
            self.assertEqual(gate.side, 'right')
        with self.assertRaises(ValueError):
            gate.select('left', {})
        gate.select('left', {'left': good, 'right': good})
        robot = Mock(); robot.operation_lock = nullcontext()
        robot.robots = {'left': Mock(), 'right': Mock()}
        for arm in robot.robots.values():
            arm.backend._read.return_value = good
        gate.renew(robot)
        robot.robots['left'].renew_session.assert_called_once()
        robot.robots['right'].renew_session.assert_not_called()
        robot.check.side_effect = RuntimeError('health fault')
        with self.assertRaises(RuntimeError):
            gate.renew(robot)
        self.assertEqual(robot.robots['left'].renew_session.call_count, 1)

    def test_renewal_does_not_reanchor_inactive_arm(self):
        gate = LeftReturnGate([0.] * 6)
        robot = Mock()
        robot.operation_lock = nullcontext()
        robot.robots = {'left': Mock(), 'right': Mock()}
        renew_sequential_segment(robot, gate)
        robot.robots['left'].renew_session.assert_called_once()
        robot.robots['right'].renew_session.assert_not_called()
        gate.right_started = True
        robot.robots['left'].renew_session.reset_mock()
        renew_sequential_segment(robot, gate)
        robot.robots['left'].renew_session.assert_not_called()
        robot.robots['right'].renew_session.assert_called_once()
        robot.check.side_effect = RuntimeError('unhealthy')
        with self.assertRaises(RuntimeError):
            renew_sequential_segment(robot, gate)
        self.assertEqual(robot.robots['right'].renew_session.call_count, 1)

    def state(self):
        return {'enabled': True, 'moving': False, 'control_state': 'holding',
                'joints_deg': [0.] * 6, 'command_deg': [0.] * 6}

    def test_idle_preparation_rejects_owned_or_enabled_arm(self):
        good = dict(robot_status='ready', enabled=False, moving=False, owner=None)
        require_idle({'left': good, 'right': good})
        for change in ({'enabled': True}, {'owner': 'active'}, {'robot_status': 'fault'}, {'moving': True}):
            with self.assertRaises(ValueError):
                require_idle({'left': good, 'right': {**good, **change}})

    def test_return_and_explicit_visual_phase_marker_both_required(self):
        gate = LeftReturnGate([0.] * 6)
        with self.assertRaises(ValueError):
            gate.begin_right(self.state())
        gate.placement_verified = True
        for key in ('joints_deg', 'command_deg'):
            with self.assertRaises(ValueError):
                gate.begin_right({**self.state(), key: [3., 0, 0, 0, 0, 0]})
        for change in ({'moving': True}, {'enabled': False}, {'joints_deg': [float('nan')] * 6}):
            with self.assertRaises(ValueError):
                gate.begin_right({**self.state(), **change})
        gate.begin_right(self.state())
        self.assertTrue(gate.right_started)

    def test_all_right_target_forms_blocked_until_phase_transition(self):
        gate = LeftReturnGate([0.] * 6)
        commands = [('move_to', {'target': {'left': None, 'right': {}}}),
                    ('set_gripper', {'positions': {'left': None, 'right': 0.}}),
                    ('move_eef_chunk', {'poses': [{'left': {}, 'right': None}, {'left': None, 'right': {}}]}),
                    ('check_path', {'poses': [{'left': None, 'right': {}}]})]
        for name, args in commands:
            with self.subTest(name=name), self.assertRaises(ValueError):
                gate.check_action(name, args, self.state())
        gate.check_action('move_to', {'target': {'left': {}, 'right': None}}, self.state())

    def test_right_phase_rechecks_left_return_and_rejects_left_motion(self):
        gate = LeftReturnGate([0.] * 6)
        gate.placement_verified = True
        gate.begin_right(self.state())
        args = {'target': {'left': None, 'right': {}}}
        gate.check_action('move_to', args, self.state())
        with self.assertRaises(ValueError):
            gate.check_action('move_to', args, {**self.state(), 'joints_deg': [4.] * 6})
        with self.assertRaises(ValueError):
            gate.check_action('move_to', {'target': {'left': {}, 'right': None}}, self.state())

    def test_right_return_requires_stack_verification_and_left_still_returned(self):
        gate = LeftReturnGate([0.] * 6)
        gate.placement_verified = True
        with self.assertRaises(ValueError):
            gate.verify_stack(self.state())
        gate.begin_right(self.state())
        with self.assertRaises(ValueError):
            gate.require_right_return(self.state())
        gate.verify_stack(self.state())
        gate.require_right_return(self.state())
        with self.assertRaises(ValueError):
            gate.require_right_return({**self.state(), 'joints_deg': [4.] * 6})
