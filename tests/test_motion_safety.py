import copy
import unittest

from motion_safety import ProposalGuard, feedback_issues


def state():
    return {'joints_deg': [0, 20, 30, -15, 0, 0],
            'lower_deg': [-170, -5, -5, -73, -85, -100],
            'upper_deg': [150, 200, 170, 73, 85, 100],
            'feedback_age_ms': 10, 'rx_age_ms': 2,
            'gripper_raw': 4.2, 'gripper_target_raw': 4.3,
            'tracking_limited': False, 'tracking_error_deg': [0]*6}


class MotionSafetyTests(unittest.TestCase):
    def test_missing_and_nonfinite_feedback_fails_closed(self):
        original = state()
        for key in original:
            sample = copy.deepcopy(original)
            sample.pop(key)
            with self.subTest(missing=key):
                self.assertTrue(feedback_issues(sample))
        for key, bad in (('rx_age_ms', float('nan')), ('feedback_age_ms', -1),
                         ('rx_age_ms', True), ('rx_age_ms', '2'),
                         ('upper_deg', [float('nan')]*6), ('joints_deg', [True]*6),
                         ('tracking_error_deg', [float('nan')]*6),
                         ('tracking_error_deg', [3.1]*6), ('tracking_limited', True),
                         ('gripper_target_raw', float('inf'))):
            sample = copy.deepcopy(original)
            sample[key] = bad
            self.assertTrue(feedback_issues(sample))

    def test_two_degree_limit_margin_is_enforced(self):
        sample = state()
        sample['joints_deg'][0] = 148
        guard = ProposalGuard()
        guard.check_state(sample)
        target = sample['joints_deg'].copy()
        target[0] = 148.1
        with self.assertRaisesRegex(ValueError, 'margin'):
            guard.accept(sample, {'joints_deg': target})
        self.assertIsNotNone(guard.failure)

    def test_small_steps_cannot_walk_out_of_session_envelope(self):
        guard, sample = ProposalGuard(), state()
        for _ in range(10):
            target = sample['joints_deg'].copy()
            target[0] += 4
            guard.accept(sample, {'joints_deg': target})
            sample['joints_deg'] = target
        target = sample['joints_deg'].copy()
        target[0] += .1
        with self.assertRaisesRegex(ValueError, 'session envelope'):
            guard.accept(sample, {'joints_deg': target})
        self.assertEqual(guard.proposals, 10)

    def test_reversals_spend_travel_budget(self):
        guard, sample = ProposalGuard(), state()
        for index in range(15):
            target = sample['joints_deg'].copy()
            sign = 1 if index % 2 == 0 else -1
            target[0] += 4*sign
            target[1] += 4*sign
            guard.accept(sample, {'joints_deg': target})
            sample['joints_deg'] = target
        self.assertEqual(guard.joint_travel, 120)
        target = sample['joints_deg'].copy()
        target[0] -= 4
        target[1] -= 4
        with self.assertRaisesRegex(ValueError, 'travel budget'):
            guard.accept(sample, {'joints_deg': target})
        self.assertEqual(guard.joint_travel, 120)

    def test_proposal_count_includes_noops(self):
        guard, sample = ProposalGuard(), state()
        for _ in range(20):
            guard.accept(sample, {'joints_deg': sample['joints_deg']})
        with self.assertRaisesRegex(ValueError, 'count exhausted'):
            guard.accept(sample, {'joints_deg': sample['joints_deg']})

    def test_gripper_budget_counts_reversals(self):
        guard, sample = ProposalGuard(), state()
        guard.gripper_travel = 4.
        for index in range(10):
            target = 4.2 if index % 2 == 0 else 4.3
            guard.accept(sample, {'gripper_raw': target})
            sample['gripper_target_raw'] = target
        self.assertAlmostEqual(guard.gripper_travel, 5)
        with self.assertRaises(ValueError):
            guard.accept(sample, {'gripper_raw': 4.2})

    def test_sensor_recovery_does_not_clear_latched_fault(self):
        guard, sample = ProposalGuard(), state()
        guard.check_state(sample)
        bad = copy.deepcopy(sample)
        bad['rx_age_ms'] = 151
        with self.assertRaises(ValueError):
            guard.check_state(bad)
        with self.assertRaisesRegex(ValueError, 'latched'):
            guard.check_state(sample)
        self.assertEqual(guard.proposals, 0)

    def test_camera_replacement_requires_new_review(self):
        guard = ProposalGuard()
        cameras = {'left': {'device': '/dev/video10'}, 'top': {'device': '/dev/video2'}}
        guard.check_cameras(cameras)
        changed = copy.deepcopy(cameras)
        changed['left']['device'] = '/dev/video12'
        with self.assertRaisesRegex(ValueError, 'device changed'):
            guard.check_cameras(changed)
        with self.assertRaises(ValueError):
            guard.check_cameras(cameras)

    def test_changed_limits_and_measured_excursion_latch_fault(self):
        for change in ('limits', 'measured'):
            guard, sample = ProposalGuard(), state()
            guard.check_state(sample)
            if change == 'limits':
                sample['upper_deg'][0] += 1
            else:
                sample['joints_deg'][0] += 40.1
            with self.assertRaises(ValueError):
                guard.check_state(sample)

    def test_separate_tools_and_step_caps(self):
        for target in ({'gripper_raw': 4.2, 'joints_deg': state()['joints_deg']},
                       {'gripper_raw': 3.2}, {'gripper_raw': 4.5},
                       {'joints_deg': [20.0, 40.0, 50.0, -15, 0, 0]},
                       {'joints_deg': [24.1, 20, 30, -15, 0, 0]}):
            guard = ProposalGuard()
            with self.assertRaises(ValueError):
                guard.accept(state(), target)
            self.assertEqual(guard.proposals, 0)

    def test_larger_single_step_still_debits_the_full_travel(self):
        guard, sample = ProposalGuard(), state()
        target = sample['joints_deg'][:]
        target[0] += 24
        guard.accept(sample, {'joints_deg': target})
        self.assertEqual(guard.joint_travel, 24)
        self.assertEqual(guard.proposals, 1)

    def test_snapshot_does_not_claim_physical_protection(self):
        snapshot = ProposalGuard().snapshot()
        for key in ('execution_available', 'physical_stop_validated', 'collision_checked'):
            self.assertIs(snapshot[key], False)

    def test_one_full_closing_stroke_fits_budget_without_scaling_targets(self):
        guard, sample = ProposalGuard(), state()
        sample['gripper_target_raw'] = 4.8
        for target in (3.8, 2.8, 1.8, .8, .2):
            guard.accept(sample, {'gripper_raw': target})
            sample['gripper_target_raw'] = target
        self.assertAlmostEqual(guard.gripper_travel, 4.6)
        self.assertEqual(guard.proposals, 5)


if __name__ == '__main__':
    unittest.main()
