import unittest
from unittest.mock import Mock

from gripper_cycle_trial import run_cycle
from r5_policy_backend import R5PolicyBackend
from test_r5_policy_backend import Clock, Workbench


class GripperCycleTests(unittest.TestCase):
    def test_cycle_closes_once_and_reopens_without_any_joint_command(self):
        client, clock = Workbench(), Clock()
        robot = R5PolicyBackend(client, lambda: None, clock=clock, sleep=clock.sleep)
        result = run_cycle(robot, Mock(), Mock())
        targets = [fields for name, fields in client.commands if name == 'target']
        self.assertEqual(len(targets), 11)
        self.assertTrue(all(set(fields) == {'gripper_raw'} for fields in targets))
        self.assertAlmostEqual(targets[0]['gripper_raw'], 3.3)
        self.assertAlmostEqual(targets[-1]['gripper_raw'], 4.3)
        self.assertFalse(result['grasp_attempted'])
        self.assertEqual(client.current['control_state'], 'holding')
        self.assertFalse(any(name == 'stop' for name, _ in client.commands))

    def test_insufficient_travel_cannot_turn_into_a_clamped_test(self):
        client, clock = Workbench(), Clock()
        client.current.update(gripper_command_raw=.5, gripper_target_raw=.5, gripper_raw=.4)
        robot = R5PolicyBackend(client, lambda: None, clock=clock, sleep=clock.sleep)
        with self.assertRaisesRegex(ValueError, 'Insufficient closing travel'):
            run_cycle(robot, Mock(), Mock())
        self.assertEqual(client.commands, [])
