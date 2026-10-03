"""Offline only: deterministic clock, simulated encoders, and captured SDK messages."""
import math
import time
import unittest

import numpy as np

from control import Controller, LEASE, LOWER, UPPER, START, PauseProfile
from live_control import LiveController


class Clock:
    def __init__(self):
        self.now = 0.

    def __call__(self):
        return self.now


class ProfileTests(unittest.TestCase):
    def test_monotonic_bounded_deceleration_and_exact_fixed_endpoint(self):
        velocity = np.radians([30, -30, 10, -5, 0, 1])
        profile = PauseProfile(START, velocity)
        expected = START + velocity*np.abs(velocity)/(2*math.radians(120))
        previous_q, previous_v = START, velocity
        for elapsed in np.arange(.01, .5, .01):
            q, v = profile.sample(float(elapsed))
            self.assertTrue(np.all(np.abs(v) <= np.abs(previous_v)+1e-12))
            self.assertTrue(np.all((q-previous_q)*np.sign(velocity) >= -1e-12))
            self.assertTrue(np.all(np.abs(v-previous_v) <= math.radians(120)*.01+1e-12))
            previous_q, previous_v = q, v
        np.testing.assert_allclose(profile.goal, expected)
        np.testing.assert_allclose(profile.sample(1)[0], expected)
        np.testing.assert_array_equal(profile.sample(1)[1], np.zeros(6))

    def test_invalid_or_out_of_limits_profiles_are_rejected(self):
        for q, v in ((UPPER, np.ones(6)), (LOWER, -np.ones(6)),
                     (START, [float('nan')]*6), ([float('inf')]*6, [0]*6)):
            with self.assertRaises(ValueError):
                PauseProfile(q, v)
        profile = PauseProfile(START, np.zeros(6))
        for elapsed in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                profile.sample(elapsed)


class SimulatedHoldTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.c = Controller(self.clock)
        self.command('enable')

    def command(self, action, **fields):
        self.c.command({'client': 'operator', 'action': action, **fields})

    def advance(self, count=1):
        for _ in range(count):
            self.command('heartbeat')
            self.clock.now += .02
            self.c.tick()

    def start_moving(self):
        self.command('settings', speed=1.)
        self.command('target', joints_deg=np.degrees(START+.3).tolist(), gripper_mm=80)
        self.advance(10)

    def test_pause_decelerates_cancels_arm_and_gripper_targets(self):
        self.start_moving()
        old_target = self.c.target.copy()
        grip = self.c.grip
        self.command('pause_hold')
        self.assertEqual(self.c.control_state, 'pausing')
        held_target = self.c.target.copy()
        self.assertFalse(np.array_equal(old_target, held_target))
        with self.assertRaises(ValueError):
            self.command('resume')
        self.advance(20)
        self.assertEqual(self.c.control_state, 'holding')
        self.assertTrue(self.c.enabled)
        self.assertEqual(self.c.owner, 'operator')
        np.testing.assert_allclose(self.c.q, held_target)
        self.assertEqual(self.c.grip, grip)
        self.assertEqual(self.c.grip_target, grip)
        self.assertFalse(self.c.motion)
        self.command('resume')
        self.advance(30)
        self.assertEqual(self.c.control_state, 'active')
        np.testing.assert_allclose(self.c.q, held_target)
        self.assertEqual(self.c.grip, grip)
        self.command('target', joints_deg=np.degrees(held_target+.02).tolist())
        self.advance(10)
        self.assertGreater(self.c.q[0], held_target[0])

    def test_pause_blocks_motion_settings_and_implicit_enable_atomically(self):
        self.command('pause_hold')
        q, target = self.c.q.copy(), self.c.target.copy()
        for action, fields in [('target', {'joints_deg': np.degrees(START+.1).tolist()}),
                               ('enable', {}), ('settings', {'speed': 1.}),
                               ('heartbeat', {'jog': [1, 0, 0, 0, 0, 0]}),
                               ('heartbeat', {'gripper': 1})]:
            with self.assertRaises(ValueError):
                self.command(action, **fields)
            np.testing.assert_array_equal(self.c.q, q)
            np.testing.assert_array_equal(self.c.target, target)
            self.assertEqual(self.c.control_state, 'holding')
        self.assertEqual(self.c.speed, .25)

    def test_repeat_pause_does_not_capture_drift_or_restart_deceleration(self):
        self.start_moving()
        self.command('pause_hold')
        self.advance(2)
        goal, elapsed = self.c.target.copy(), self.c.pause_elapsed
        self.c.q += .001
        self.command('pause_hold')
        np.testing.assert_array_equal(self.c.target, goal)
        self.assertEqual(self.c.pause_elapsed, elapsed)

    def test_ownership_stop_and_no_auto_reenable(self):
        self.command('pause_hold')
        for action in ('pause_hold', 'resume', 'heartbeat', 'enable'):
            with self.assertRaises(ValueError):
                self.c.command({'action': action, 'client': 'other'})
        self.c.command({'action': 'stop', 'client': 'other'})
        self.assertEqual(self.c.control_state, 'disabled')
        self.assertIsNone(self.c.pause_profile)
        self.command('heartbeat')
        for action in ('pause_hold', 'resume'):
            with self.assertRaises(ValueError):
                self.command(action)
        self.assertFalse(self.c.enabled)

    def test_lease_expiry_still_stops_and_discards_hold(self):
        self.command('pause_hold')
        self.clock.now += LEASE+.01
        self.c.tick()
        self.assertFalse(self.c.enabled)
        self.assertIsNone(self.c.pause_profile)
        self.assertIsNone(self.c.owner)

    def test_impossible_deceleration_stops_instead_of_continuing_old_target(self):
        self.c.q = UPPER.copy()
        self.c.velocity[:] = .1
        with self.assertRaises(ValueError):
            self.command('pause_hold')
        np.testing.assert_array_equal(self.c.target, self.c.q)
        self.assertIsNone(self.c.pause_profile)
        self.assertFalse(self.c.enabled)


class FakeSDKHoldTests(unittest.TestCase):
    def setUp(self):
        self.c = LiveController(experimental_hold=True)
        self.sent = []
        self.c.send = self.sent.append
        self.c.robot_status = 'ready'
        self.c.q = START.copy()
        self.c.command_q = START.copy()
        self.c.gripper_raw = .7
        self.c.rx_age = 0.
        self.c.feedback_at = time.monotonic()
        self.command('enable')

    def command(self, action, **fields):
        self.c.command({'client': 'operator', 'action': action, **fields})

    def tick(self):
        self.c.feedback_at = time.monotonic()
        self.c.last_beat = self.c.clock()
        self.c.last_tick = self.c.clock()-.02
        self.c.tick()

    def test_live_is_disabled_by_default_and_cannot_be_enabled_by_request(self):
        c = LiveController()
        c.send = lambda _: self.fail('No hardware commands allowed')
        self.assertFalse(c.snapshot()['hold_available'])
        with self.assertRaises(ValueError):
            c.command({'action': 'pause_hold', 'client': 'operator', 'experimental_hold': True})
        self.assertFalse(c.enabled)

    def test_fixed_command_does_not_chase_encoder_drift_and_preserves_grip(self):
        self.c.raw_target = 2.
        last_grip = self.c.last_grip
        self.command('pause_hold')
        goal = self.c.target.copy()
        self.c.q += .005
        measured = self.c.q.copy()
        for _ in range(20):
            self.tick()
        np.testing.assert_array_equal(self.c.q, measured)
        np.testing.assert_allclose(self.sent[-1]['q'], goal)
        self.assertEqual(self.sent[-1]['grip'], last_grip)
        self.assertEqual(self.c.raw_target, last_grip)
        self.assertEqual(self.c.control_state, 'holding')
        self.command('pause_hold')
        np.testing.assert_array_equal(self.c.target, goal)
        self.command('resume')
        self.tick()
        np.testing.assert_allclose(self.sent[-1]['q'], goal)

    def test_profile_starts_at_command_not_lagging_measured_position(self):
        self.c.command_q = START+.005
        self.c.velocity = np.array([.05, -.05, 0, 0, 0, 0])
        initial_command = self.c.command_q.copy()
        self.command('pause_hold')
        np.testing.assert_array_equal(self.c.pause_profile.origin, initial_command)
        for _ in range(5):
            self.tick()
        self.assertEqual(self.c.control_state, 'holding')
        np.testing.assert_array_equal(self.c.q, START)
        self.assertTrue(all(message['action'] == 'target' for message in self.sent))

    def test_unhealthy_entry_cancels_old_motion_using_original_protection(self):
        cases = [('rx_age', .2), ('rx_age', float('nan')), ('error_codes', [1]),
                 ('robot_status', 'fault'), ('tracking_limited', True),
                 ('feedback_at', time.monotonic()-1),
                 ('command_q', START+np.radians(3.1))]
        for key, value in cases:
            self.setUp()
            setattr(self.c, key, value)
            with self.assertRaises(ValueError, msg=key):
                self.command('pause_hold')
            self.assertIsNone(self.c.pause_profile)
            self.assertFalse(self.c.enabled)
            self.assertEqual(self.sent, [{'action': 'pause'}])

    def test_small_residual_can_enter_hold_and_resume_without_resetting_target(self):
        self.c.command_q[0] += np.radians(2.8)
        commanded = self.c.command_q.copy()
        self.command('pause_hold')
        for _ in range(5):
            self.tick()
        self.command('resume')
        self.assertTrue(self.c.enabled)
        np.testing.assert_allclose(self.c.command_q, commanded)
        np.testing.assert_allclose(self.c.q, START)
        self.assertFalse(any(m['action'] == 'pause' for m in self.sent))

    def test_feedback_error_drift_or_lease_loss_uses_original_protection(self):
        for fault in ('stale', 'can', 'sdk', 'drift', 'lease'):
            with self.subTest(fault=fault):
                self.setUp()
                self.command('pause_hold')
                if fault == 'stale':
                    self.c.feedback_at -= .2
                elif fault == 'can':
                    self.c.rx_age = .2
                elif fault == 'sdk':
                    self.c.error_codes = [11]
                elif fault == 'drift':
                    self.c.q += np.radians(3.1)
                else:
                    self.c.last_beat -= 1
                self.c.tick()
                self.assertEqual(self.sent, [{'action': 'pause'}])
                self.assertFalse(self.c.enabled)
                self.assertIsNone(self.c.pause_profile)
                with self.assertRaises(ValueError):
                    self.command('resume')

    def test_resume_rejects_stale_feedback_and_enable_cannot_bypass_hold(self):
        self.command('pause_hold')
        grip_target = self.c.raw_target
        with self.assertRaises(ValueError):
            self.command('enable')
        self.assertEqual(self.c.raw_target, grip_target)
        self.assertEqual(self.c.control_state, 'holding')
        self.c.feedback_at -= 1
        with self.assertRaises(ValueError):
            self.command('resume')
        self.assertFalse(self.c.enabled)
        self.assertEqual(self.sent[-1], {'action': 'pause'})

    def test_deceleration_cannot_silently_clip_hold_target_to_tracking_limit(self):
        self.c.velocity[:] = math.radians(30)
        self.command('pause_hold')
        for _ in range(15):
            self.tick()
            if not self.c.enabled:
                break
        self.assertFalse(self.c.enabled)
        self.assertEqual(self.sent[-1], {'action': 'pause'})
        self.assertIsNone(self.c.pause_profile)

    def test_explicit_stop_and_disconnect_preserve_original_behavior(self):
        self.command('pause_hold')
        self.command('stop')
        self.assertEqual(self.sent, [{'action': 'pause'}])
        self.assertFalse(self.c.enabled)
        self.setUp()
        self.command('pause_hold')
        self.command('disconnect')
        self.assertEqual(self.sent, [{'action': 'pause'}, {'action': 'shutdown'}])
        self.assertFalse(self.c.enabled)


if __name__ == '__main__':
    unittest.main()
