import unittest
from unittest.mock import patch

import numpy as np

from control import START, LOWER, UPPER
from live_control import LiveController
from motion_safety import ProposalGuard
from policy_trajectory import (PolicyTrajectory, debit_trajectory, preview_trajectory,
                               check_tracking_reserve)
from test_policy_adapter import measured_state


class TrajectoryTests(unittest.TestCase):
    def test_tracking_reserve_rejects_path_that_barely_passes_old_margin(self):
        state = measured_state()
        state['command_deg'] = state['joints_deg'][:]
        state['command_deg'][3] = -66
        target = state['command_deg'][:]
        target[3] = state['lower_deg'][3]+2.0423
        with self.assertRaisesRegex(ValueError, 'J4'):
            check_tracking_reserve(state, [target], 3.5)
        target[3] = state['lower_deg'][3]+6
        result = check_tracking_reserve(state, [target], 3.5)
        self.assertEqual(result['requested_total_margin_deg'], 5.5)

    def test_tracking_reserve_checks_intermediate_path_and_both_limits(self):
        state = measured_state()
        state['command_deg'] = state['joints_deg'][:]
        for joint, edge in ((3, state['lower_deg'][3]+3),
                            (5, state['upper_deg'][5]-3)):
            turn = state['command_deg'][:]
            turn[joint] = edge
            with self.subTest(joint=joint), self.assertRaisesRegex(ValueError, 'reserve rejected'):
                check_tracking_reserve(state, [turn, state['command_deg']], 3.5)

    def test_tracking_reserve_allows_only_inward_escape_from_near_limit_start(self):
        state = measured_state()
        state['command_deg'] = state['joints_deg'][:]
        state['command_deg'][1] = state['lower_deg'][1]+4
        inward = state['command_deg'][:]
        inward[1] += 2
        self.assertTrue(check_tracking_reserve(state, [inward], 3.5)
                        ['held_start_inside_extra_reserve'][1])
        outward = state['command_deg'][:]
        outward[1] -= .01
        with self.assertRaisesRegex(ValueError, 'J2'):
            check_tracking_reserve(state, [outward], 3.5)
        state['command_deg'][1] = state['lower_deg'][1]+1
        with self.assertRaisesRegex(ValueError, 'existing joint limit'):
            check_tracking_reserve(state, [inward], 3.5)

    def test_tracking_reserve_rejects_invalid_values(self):
        state = measured_state()
        state['command_deg'] = state['joints_deg'][:]
        for value in (-1, float('nan'), True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                check_tracking_reserve(state, [state['command_deg']], value)

    def test_preview_rejection_does_not_claim_or_create_live_fault(self):
        state, guard = measured_state(), ProposalGuard()
        q = state['joints_deg'][:]
        q[0] += 24.1
        with self.assertRaisesRegex(ValueError, 'preview rejected before execution') as caught:
            preview_trajectory(guard, state, [q])
        self.assertNotIn('Session fault latched;', str(caught.exception))
        self.assertIsNone(guard.failure)
        self.assertEqual(guard.proposals, 0)
        q[0] -= 23.1
        preview_trajectory(guard, state, [q])
        self.assertEqual(guard.proposals, 0)

    def test_preview_preserves_a_real_latched_fault(self):
        state, guard = measured_state(), ProposalGuard()
        guard.latch('feedback missing')
        with self.assertRaisesRegex(ValueError, 'Session fault latched;'):
            preview_trajectory(guard, state, [state['joints_deg']])
        self.assertEqual(guard.failure, 'feedback missing')

    def plan(self, times=None, points=None):
        start = np.degrees(START).tolist()
        end = start[:]
        end[0] += 1
        return PolicyTrajectory(start, points or [end], times or [.5],
                                np.degrees(LOWER).tolist(), np.degrees(UPPER).tolist(), 100.)

    def test_timed_interpolation_and_late_tick_rejection(self):
        p = self.plan()
        q, v, done = p.sample(100.1)
        self.assertAlmostEqual(q[0], np.degrees(START[0])+.2)
        self.assertAlmostEqual(v[0], 2.)
        self.assertFalse(done)
        with self.assertRaisesRegex(ValueError, 'deadline'):
            p.sample(100.4)
        p = self.plan()
        for t in (100.1, 100.2, 100.3, 100.4, 100.5):
            q, v, done = p.sample(t)
        self.assertTrue(done)
        self.assertTrue(np.all(v == 0))

    def test_speed_bad_timestamps_and_whole_path_envelope(self):
        with self.assertRaises(ValueError):
            self.plan(times=[.01])
        with self.assertRaises(ValueError):
            self.plan(times=[-1])
        with self.assertRaises(ValueError):
            self.plan(times=[31])
        start = np.degrees(START).tolist()
        end = start[:]
        end[0] += 24.1
        with self.assertRaisesRegex(ValueError, 'envelope'):
            self.plan(times=[2], points=[end])

    def test_larger_step_is_accepted_but_speed_and_combined_envelope_remain(self):
        start = np.degrees(START).tolist()
        end = start[:]
        end[0] += 24
        self.plan(times=[3], points=[end])
        with self.assertRaisesRegex(ValueError, 'speed'):
            self.plan(times=[.5], points=[end])
        end[1] += 17
        self.plan(times=[3], points=[end])
        end[2] += 17
        with self.assertRaisesRegex(ValueError, 'envelope'):
            self.plan(times=[3], points=[end])

    def test_path_budget_counts_reversals_as_one_action(self):
        state = measured_state()
        guard = ProposalGuard()
        q = state['joints_deg'][:]
        turn = q[:]
        turn[0] += 1
        debit_trajectory(guard, state, [turn, q])
        self.assertEqual(guard.proposals, 1)
        self.assertAlmostEqual(guard.joint_travel, 2)
        guard.joint_travel = 119
        with self.assertRaisesRegex(ValueError, 'budget'):
            debit_trajectory(guard, state, [turn, q])
        self.assertEqual(guard.proposals, 1)

    def test_intermediate_excursion_cannot_hide_behind_nearby_endpoint(self):
        state, guard = measured_state(), ProposalGuard()
        start = state['joints_deg'][:]
        turn = start[:]
        turn[0] += 24.1
        with self.assertRaisesRegex(ValueError, 'envelope'):
            PolicyTrajectory(start, [turn, start], [3., 6.],
                             state['lower_deg'], state['upper_deg'], 100.)
        with self.assertRaisesRegex(ValueError, 'envelope'):
            preview_trajectory(guard, state, [turn, start])
        self.assertEqual(guard.joint_travel, 0)
        self.assertEqual(guard.proposals, 0)
        self.assertIsNone(guard.failure)


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.
        self.clock = patch('live_control.time.monotonic', side_effect=lambda: self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.c = LiveController(supervised_policy=True)
        self.c.clock = lambda: self.now
        self.sent = []
        self.c.send = self.sent.append
        self.c.q = START.copy()
        self.c.command_q = START.copy()
        self.c.target = START.copy()
        self.c.enabled = True
        self.c.owner = 'test'
        self.c.robot_status = 'ready'
        self.c.feedback_at = self.now
        self.c.last_tick = self.c.last_beat = self.now
        self.c.rx_age = 0
        self.c.raw_target = self.c.last_grip = .8
        self.c.gripper_raw = .7
        self.c.speed = .3
        self.c.policy_gate.qualified_owner = 'test'

    def command(self, action, **fields):
        self.c.command({'action': action, 'client': 'test', **fields})

    def submit(self):
        start = np.degrees(START).tolist()
        end = start[:]
        end[0] += 1
        self.command('policy_trajectory', start_deg=start, points_deg=[end], times_s=[.5], issued_at=self.now)

    def advance(self, seconds=.02):
        self.now += seconds
        self.c.feedback_at = self.now
        self.command('heartbeat')
        self.c.tick()

    def test_playback_uses_timed_samples_and_stop_cancels_remaining_path(self):
        self.submit()
        self.advance(.1)
        self.assertAlmostEqual(np.degrees(self.c.command_q[0]-START[0]), .2)
        np.testing.assert_array_equal(self.c.q, START)
        self.assertEqual(self.sent[-1]['grip'], .8)
        self.command('stop')
        self.assertIsNone(self.c.policy_trajectory)
        self.assertEqual(self.sent[-1], {'action': 'pause'})
        self.assertFalse(self.c.enabled)

    def test_live_transport_accepts_larger_path_with_original_speed_limit(self):
        start = np.degrees(START).tolist()
        end = start[:]
        end[0] += 24
        with self.assertRaisesRegex(ValueError, 'speed'):
            self.command('policy_trajectory', start_deg=start, points_deg=[end],
                         times_s=[1.], issued_at=self.now)
        self.assertIsNone(self.c.policy_trajectory)
        self.command('policy_trajectory', start_deg=start, points_deg=[end],
                     times_s=[3.], issued_at=self.now)
        self.advance(.1)
        self.assertAlmostEqual(np.degrees(self.c.command_q[0]-START[0]), .8)
        self.assertEqual(self.c.snapshot()['policy_step_limits_deg'], {'joint': 24., 'norm': 33.})

    def test_bounded_hold_residual_does_not_jump_command_to_measured_position(self):
        self.c.q[0] += np.radians(2.8)
        self.submit()
        self.advance(.02)
        self.assertAlmostEqual(np.degrees(self.c.command_q[0]-START[0]), .04)
        self.assertAlmostEqual(np.degrees(self.c.q[0]-START[0]), 2.8)
        self.command('stop')
        self.c.q[0] = START[0]+np.radians(3.1)
        self.c.command_q = START.copy()
        self.c.enabled, self.c.owner = True, 'test'
        self.c.policy_gate.qualified_owner = 'test'
        with self.assertRaisesRegex(ValueError, 'Qualified supervised joint control'):
            self.submit()

    def test_pause_cancels_path_and_resume_cannot_restart_it(self):
        self.submit()
        self.advance(.1)
        self.command('pause_hold')
        self.assertIsNone(self.c.policy_trajectory)
        for _ in range(5):
            self.advance()
        self.command('resume')
        self.assertIsNone(self.c.policy_trajectory)

    def test_late_tick_requests_stop_instead_of_catching_up(self):
        self.submit()
        self.advance(.2)
        self.assertFalse(self.c.enabled)
        self.assertEqual(self.sent[-1], {'action': 'pause'})
        self.assertFalse(any(item['action'] == 'target' for item in self.sent))

    def test_unqualified_owner_stale_request_and_overlapping_targets_rejected(self):
        self.c.policy_gate.reset()
        with self.assertRaises(ValueError):
            self.submit()
        self.c.policy_gate.qualified_owner = 'test'
        self.submit()
        with self.assertRaises(ValueError):
            self.command('target', joints_deg=np.degrees(START).tolist())
        with self.assertRaises(ValueError):
            self.command('heartbeat', jog=[1,0,0,0,0,0])
        with self.assertRaises(ValueError):
            self.c.command({'client': 'other', 'action': 'policy_trajectory'})


if __name__ == '__main__':
    unittest.main()
