import unittest
from unittest.mock import patch

from joint_drive_trial import ArmClient, trial_targets


class JointDriveTrialTests(unittest.TestCase):
    def test_each_axis_returns_before_the_next_axis_and_reference_is_unchanged(self):
        reference = [0, 20, 30, -15, 0, 0]
        targets = list(trial_targets(reference))
        self.assertEqual(len(targets), 12)
        for i in range(6):
            joint, direction, target = targets[2*i]
            self.assertEqual((joint, direction), (i, 'out'))
            self.assertEqual([q-p for q, p in zip(target, reference)],
                             [2 if j == i else 0 for j in range(6)])
            self.assertEqual(targets[2*i+1], (i, 'return', reference))
        self.assertEqual(reference, [0, 20, 30, -15, 0, 0])

    def test_right_client_routes_state_commands_and_camera_explicitly(self):
        client = ArmClient('http://127.0.0.1:8768', 'right')
        with patch.object(client, 'request') as request:
            client.state()
            self.assertEqual(request.call_args.args[0], '/api/arms/right/state')
            client.command('stop')
            self.assertEqual(request.call_args.args[0], '/api/arms/right/command')
        with patch('visual_control.WorkbenchClient.camera') as camera:
            client.camera('gemini')
            camera.assert_called_once_with('gemini_right')
            client.camera('external')
            self.assertEqual(camera.call_args.args, ('external',))

    def test_invalid_arm_or_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            ArmClient('http://127.0.0.1:8768', 'both')
        with self.assertRaises(ValueError):
            list(trial_targets([0, 0, 0, 0, 0, float('nan')]))

    def test_selected_axis_test_keeps_other_commands_fixed(self):
        reference = [1, 2, 3, 4, 5, 6]
        self.assertEqual(list(trial_targets(reference, 3., [3])), [
            (2, 'out', [1, 2, 6, 4, 5, 6]), (2, 'return', reference)])
        for step, joints in ((4., [3]), (3., [3, 3]), (3., [0]), (3., [])):
            with self.subTest(step=step, joints=joints), self.assertRaises(ValueError):
                list(trial_targets(reference, step, joints))
