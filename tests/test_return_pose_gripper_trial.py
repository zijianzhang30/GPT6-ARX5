import math
import unittest

from return_pose_gripper_trial import ReturnThenGripBackend, return_target
from test_r5_policy_backend import Clock, Workbench


class ReturnGripTests(unittest.TestCase):
    def test_large_return_is_bounded_and_does_not_overshoot(self):
        for goal in ([100, 60, -30, 20, 10, 0], [100]*6, [2, 0, 0, 0, 0, 0]):
            target = return_target([0]*6, goal)
            self.assertLessEqual(max(map(abs, target)), 6.000001)
            self.assertLessEqual(math.hypot(*target), 8.250001)
            self.assertTrue(all(min(0, b) <= a <= max(0, b) for a, b in zip(target, goal)))
        self.assertIsNone(return_target([0]*6, [.5]*6))

    def test_requires_arrival_then_permanently_locks_arm(self):
        client, clock = Workbench(), Clock()
        goal = client.current['joints_deg'][:]
        robot = ReturnThenGripBackend(client, lambda: None,
            reference={'measured_joints_deg': goal}, clock=clock, sleep=clock.sleep)
        with self.assertRaises(ValueError):
            robot.step('close 0.2')
        robot.reference['measured_joints_deg'] = [q+20 for q in goal]
        with self.assertRaises(ValueError):
            robot.lock_arm()
        self.assertIsNone(robot.arm_reference)
        self.assertEqual(client.commands, [])
        robot.reference['measured_joints_deg'] = goal
        robot.lock_arm()
        with self.assertRaises(ValueError):
            robot.next_step()
        with self.assertRaises(ValueError):
            robot.renew_session()
        robot.step('close 0.2')
        targets = [fields for name, fields in client.commands if name == 'target']
        self.assertTrue(targets)
        self.assertTrue(all(set(fields) == {'gripper_raw'} for fields in targets))

    def test_return_step_only_moves_arm_and_keeps_powered_hold(self):
        client, clock = Workbench(), Clock()
        goal = client.current['joints_deg'][:]
        goal[0] += 5
        robot = ReturnThenGripBackend(client, lambda: None,
            reference={'measured_joints_deg': goal}, clock=clock, sleep=clock.sleep)
        result = robot.next_step()
        targets = [fields for name, fields in client.commands if name == 'target']
        self.assertEqual(len(targets), 1)
        self.assertEqual(set(targets[0]), {'joints_deg'})
        self.assertEqual(result['control_state'], 'holding')
