import copy
import json
import unittest
from unittest.mock import patch

import test_dual_return_pose as fixtures
from reviewed_return import ReviewedReturn
from r5_policy_backend import R5ExecutionFault


class ReviewedReturnTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.ReturnTests()
        fixture.setUp()
        self.clients, self.robot = fixture.clients, fixture.robot
        self.initial = fixture.reference['arms']
        self.session = ReviewedReturn(self.initial)

    def review(self, side='left'):
        state = self.robot.state()['arms'][side]
        return {'observation_id': state['observation_id'], 'empty_gripper': True,
                'path_clear': True, 'recording_active': True,
                'note': 'Synthetic reviewed empty-arm corridor'}

    def assert_no_motion(self):
        for client in self.clients.values():
            self.assertFalse(any(a in ('enable', 'resume', 'target', 'policy_trajectory')
                                 for a, _ in client.commands))

    def test_only_selected_arm_moves_and_remains_enabled_at_reference(self):
        for _ in range(10):
            result = self.session.step(self.robot, 'left', self.review())
            json.dumps(result, allow_nan=False)
            if result['at_initial']:
                break
        self.assertTrue(result['at_initial'])
        self.assertEqual(result['control_state'], 'holding')
        self.assertFalse(result['fault_recovery'])
        self.assertFalse(result['collision_checked'])
        for client in self.clients.values():
            self.assertTrue(client.current['enabled'])
            self.assertEqual(client.current['gripper_command_raw'], 4.3)
            self.assertFalse(any(a in ('enable', 'home', 'stop', 'target') for a, _ in client.commands))
        self.assertTrue(all(a == 'heartbeat' for a, _ in self.clients['right'].commands))

    def test_reference_is_not_changed_by_caller_mutation(self):
        expected = copy.deepcopy(self.initial['left'])
        self.initial['left']['joints_deg'][0] = 999
        result = self.session.step(self.robot, 'left', self.review())
        self.assertEqual(result['reference'], expected)

    def test_missing_or_false_visual_evidence_never_moves(self):
        for key in ('empty_gripper', 'path_clear', 'recording_active'):
            for value in (False, None, 'true', 1):
                with self.subTest(key=key, value=value):
                    review = self.review()
                    review[key] = value
                    with self.assertRaises(ValueError):
                        self.session.step(self.robot, 'left', review)
                    self.assert_no_motion()

    def test_observation_must_be_recent_and_current(self):
        review = self.review()
        self.robot.state()
        with self.assertRaisesRegex(ValueError, 'fresh'):
            self.session.step(self.robot, 'left', review)
        review = self.review()
        self.robot.robots['left'].backend.clock.sleep(31)
        with self.assertRaisesRegex(ValueError, 'fresh'):
            self.session.step(self.robot, 'left', review)
        self.assert_no_motion()

    def test_even_noop_at_reference_requires_new_review_each_time(self):
        current = {s: c.state() for s, c in self.clients.items()}
        session = ReviewedReturn(current)
        review = self.review()
        self.assertTrue(session.step(self.robot, 'left', review)['at_initial'])
        with self.assertRaisesRegex(ValueError, 'fresh'):
            session.step(self.robot, 'left', review)
        self.assert_no_motion()

    def test_latched_fault_or_busy_arm_never_starts_return(self):
        for field, value in (('fault', 'Original execution fault'), ('busy', True)):
            with self.subTest(field=field):
                self.setUp()
                review = self.review()
                low = self.robot.robots['right'].backend
                setattr(low, field, value)
                with self.assertRaisesRegex(ValueError, 'Faulted or moving'):
                    self.session.step(self.robot, 'left', review)
                self.assertEqual(getattr(low, field), value)
                self.assert_no_motion()

    def test_disabled_or_unhealthy_feedback_never_enables_or_returns(self):
        for key, value in (('enabled', False), ('owner', 'other-client'),
                           ('rx_age_ms', 1000), ('error_codes', [12])):
            with self.subTest(key=key):
                self.setUp()
                review = self.review()
                self.clients['left'].current[key] = value
                with self.assertRaises(R5ExecutionFault):
                    self.session.step(self.robot, 'left', review)
                self.assert_no_motion()

    def test_drift_after_review_is_rejected_before_motion(self):
        for key in ('joints_deg', 'command_deg', 'gripper_raw'):
            with self.subTest(key=key):
                self.setUp()
                review = self.review()
                if key == 'gripper_raw':
                    self.clients['left'].current[key] += .02
                else:
                    self.clients['left'].current[key][0] += .06
                    if key == 'command_deg':
                        self.clients['left'].current['hold_target_deg'][0] += .06
                with self.assertRaisesRegex(ValueError, 'State changed'):
                    self.session.step(self.robot, 'left', review)
                self.assert_no_motion()

    def test_tracking_reserve_and_budget_rejection_do_not_renew_or_move(self):
        review = self.review()
        arm = self.robot.robots['left']
        arm.tracking_reserve_deg = 3.5
        with patch('reviewed_return.check_tracking_reserve', side_effect=ValueError('reserve')):
            with self.assertRaisesRegex(ValueError, 'reserve'):
                self.session.step(self.robot, 'left', review)
        arm.backend.guard.proposals = 20
        with self.assertRaises(ValueError):
            self.session.step(self.robot, 'left', review)
        self.assertEqual(arm.backend.guard.proposals, 20)
        self.assert_no_motion()

    def test_camera_fault_prevents_dispatch_and_is_not_reinterpreted_as_return(self):
        review = self.review()
        self.robot.vision_check = lambda: (_ for _ in ()).throw(RuntimeError('camera fault'))
        with self.assertRaisesRegex(R5ExecutionFault, 'camera fault'):
            self.session.step(self.robot, 'left', review)
        self.assert_no_motion()

    def test_execution_fault_has_one_attempt_and_never_reenables(self):
        review = self.review()
        self.clients['left'].timeout = 'policy_trajectory'
        with self.assertRaises(R5ExecutionFault):
            self.session.step(self.robot, 'left', review)
        commands = [a for a, _ in self.clients['left'].commands]
        self.assertEqual(commands.count('policy_trajectory'), 1)
        self.assertIn('stop', commands)
        self.assertNotIn('enable', commands)
        self.assertIsNotNone(self.robot.robots['left'].backend.fault)


if __name__ == '__main__':
    unittest.main()
