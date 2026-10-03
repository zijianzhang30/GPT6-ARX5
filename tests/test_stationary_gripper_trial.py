import unittest

from stationary_gripper_trial import StationaryGripperBackend, check_reference
from r5_policy_backend import R5ExecutionFault
from test_r5_policy_backend import Clock, Workbench


class StationaryGripperTests(unittest.TestCase):
    def setUp(self):
        self.client, self.clock = Workbench(), Clock()
        self.robot = StationaryGripperBackend(self.client, lambda: None,
            clock=self.clock, sleep=self.clock.sleep)
        self.robot.anchor()

    def test_close_moves_gripper_without_any_joint_target_or_reopening(self):
        result = self.robot.step('close 0.2')
        targets = [fields for name, fields in self.client.commands if name == 'target']
        self.assertEqual(len(targets), 1)
        self.assertEqual(set(targets[0]), {'gripper_raw'})
        self.assertAlmostEqual(targets[0]['gripper_raw'], 4.1)
        self.assertAlmostEqual(result['measured_gripper_raw'], 4.0)
        self.assertEqual(result['control_state'], 'holding')
        self.assertNotIn('stop', [name for name, _ in self.client.commands])

    def test_arm_actions_and_budget_reanchor_are_unavailable(self):
        for name in ('move_joints', 'move_joint_step'):
            with self.assertRaises(ValueError):
                self.robot.execute(name, {})
        with self.assertRaises(ValueError):
            self.robot.execute_trajectory({})
        with self.assertRaises(ValueError):
            self.robot.renew_session()
        self.assertEqual(self.client.commands, [])

    def test_out_of_range_or_invalid_commands_do_not_actuate(self):
        for command in ('close 1.01', 'open 0.11', 'close nan', 'close -1', 'move 1', 'close'):
            with self.assertRaises(ValueError):
                self.robot.step(command)
        self.assertEqual(self.client.commands, [])

    def test_joint_drift_blocks_gripper_and_supervisor_requests_stop(self):
        self.client.current['joints_deg'][0] += 1.8
        with self.assertRaises(R5ExecutionFault):
            self.robot.step('close 0.2')
        self.assertFalse(any(name == 'target' for name, _ in self.client.commands))
        self.robot.engaged = True
        with self.assertRaises(R5ExecutionFault):
            self.robot.check()
        self.assertEqual(self.client.commands[-1][0], 'stop')

    def test_changed_arm_command_is_rejected_even_with_consistent_hold(self):
        for key in ('command_deg', 'hold_target_deg', 'joints_deg'):
            self.client.current[key][0] += .1
        with self.assertRaisesRegex(R5ExecutionFault, 'arm command changed'):
            self.robot.step('close 0.2')
        self.assertEqual(self.client.commands, [])

    def test_saved_reference_is_checked_without_replaying_it(self):
        initial = self.client.state()
        check_reference(initial, {'measured_joints_deg': initial['joints_deg'][:]})
        with self.assertRaisesRegex(ValueError, 'no automatic pose restoration'):
            check_reference(initial, {'measured_joints_deg': [80]*6})
        self.assertEqual(self.client.commands, [])
