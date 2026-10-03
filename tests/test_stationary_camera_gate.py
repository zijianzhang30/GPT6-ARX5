import unittest
from unittest.mock import Mock, patch

from r5_policy_backend import R5ExecutionFault, R5PolicyBackend
from r5_policy_supervisor import StationaryCameraGate
from test_r5_policy_backend import Workbench


class StationaryCameraGateTests(unittest.TestCase):
    def setUp(self):
        self.client = Workbench()
        self.client.current['policy_trajectory_active'] = False
        self.cameras = Mock()
        self.backend = R5PolicyBackend(self.client, self.cameras.check)
        self.gate = StationaryCameraGate(self.cameras, self.backend)
        self.backend.vision_check = self.gate.check
        self.backend.check()
        self.cameras.check.side_effect = R5ExecutionFault('Supervised camera frames are stale')

    def test_stale_idle_camera_keeps_targets_heartbeats_and_rejects_new_work(self):
        before = self.client.state()
        for _ in range(3):
            self.backend.check()
        self.assertIn('stale', self.gate.blocked_reason)
        with self.assertRaisesRegex(ValueError, 'stationary hold retained'):
            self.gate.require_fresh()
        self.cameras.snapshot.side_effect = R5ExecutionFault('No new images')
        with self.assertRaisesRegex(ValueError, 'Cannot observe'):
            self.gate.snapshot()
        self.assertTrue(self.client.current['enabled'])
        self.assertEqual(self.client.current['command_deg'], before['command_deg'])
        self.assertEqual(self.client.current['gripper_command_raw'], before['gripper_command_raw'])
        self.assertTrue(all(action == 'heartbeat' for action, _ in self.client.commands))
        self.assertIsNone(self.backend.fault)

    def test_active_motion_still_faults_and_requests_stop(self):
        self.backend.busy = True
        with self.assertRaisesRegex(R5ExecutionFault, 'stale'):
            self.backend.check()
        self.assertFalse(self.client.current['enabled'])
        self.assertEqual(self.client.commands[-1][0], 'stop')

    def test_not_stationary_or_unhealthy_feedback_cannot_keep_hold(self):
        for changes in ({'moving': True}, {'policy_trajectory_active': True},
                        {'feedback_age_ms': 300}, {'control_state': 'active'}):
            with self.subTest(changes=changes):
                self.setUp()
                self.client.current.update(changes)
                with self.assertRaises(R5ExecutionFault):
                    self.backend.check()
                self.assertFalse(self.client.current['enabled'])

    def test_camera_recovery_allows_fresh_checks_without_changing_targets(self):
        self.backend.check()
        self.cameras.check.side_effect = None
        self.gate.require_fresh()
        self.backend.check()
        self.assertIsNone(self.gate.blocked_reason)
        self.assertTrue(self.client.current['enabled'])
        self.assertTrue(all(action == 'heartbeat' for action, _ in self.client.commands))

    def test_camera_loss_after_resume_blocks_trajectory_dispatch(self):
        self.cameras.check.side_effect = None
        state = self.client.state()
        start = state['command_deg'][:]
        end = start[:]
        end[0] += 1
        original = self.client.command

        def command(action, **fields):
            result = original(action, **fields)
            if action == 'resume':
                self.cameras.check.side_effect = R5ExecutionFault('Supervised camera frames are stale')
            return result

        self.client.command = command
        inputs = ([end], {}, state, {'joints_deg': end}, start, start)
        with patch.object(self.backend, '_trajectory_inputs', return_value=inputs):
            with self.assertRaisesRegex(R5ExecutionFault, 'stale'):
                self.backend.execute_trajectory({})
        self.assertFalse(any(action == 'policy_trajectory' for action, _ in self.client.commands))
        self.assertEqual(self.client.commands[-1][0], 'stop')


if __name__ == '__main__':
    unittest.main()
