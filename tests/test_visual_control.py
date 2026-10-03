import copy
import time
import threading
import unittest

import cv2
import numpy as np

from visual_control import detect_ball, validate_action, step_settled, StepSession


def measured_state():
    return {'simulation': False, 'robot_status': 'ready', 'feedback_age_ms': 10,
            'rx_age_ms': 2, 'error_codes': [], 'joints_deg': [0, 20, 30, -15, 0, 0],
            'lower_deg': [-170, -5, -5, -73, -85, -100],
            'upper_deg': [150, 200, 170, 73, 85, 100],
            'gripper_raw': 4.2, 'gripper_target_raw': 4.3,
            'owner': None, 'enabled': False, 'tracking_limited': False,
            'mode': 'joint', 'speed': .1,
            'tracking_error_deg': [0]*6}


class VisualControlTests(unittest.TestCase):
    def test_dual_trial_minor_reverse_component_does_not_mask_net_progress(self):
        initial = np.array([-28.512379, 44.161927, 7.223717, 26.326664, -32.905611, 1.825081])
        target = np.array([-28.837847, 49.132695, 9.192561, 30.580103, -32.798375, 2.023628])
        measured = np.array([-28.774658, 49.079772, 8.229121, 30.217194, -32.927468, 1.650174])

        def settled(q, deadband=.3):
            return step_settled({'joints_deg': target}, initial,
                [(i*.05, q.copy()) for i in range(13)], .6,
                command_initial=initial, min_progress=.4, aggregate_progress=True,
                max_residual_deg=2.5, reverse_deadband_deg=deadband)

        self.assertFalse(settled(measured, 0.))
        self.assertTrue(settled(measured))
        self.assertFalse(settled(initial))
        reverse = measured.copy()
        reverse[5] = initial[5]-.31
        self.assertFalse(settled(reverse))
        inaccurate = measured.copy()
        inaccurate[2] = target[2]-2.51
        self.assertFalse(settled(inaccurate))
        for deadband in (-.1, .51, float('nan')):
            self.assertFalse(settled(measured, deadband))

    def test_relaxed_policy_residual_still_requires_progress_and_stability(self):
        initial = np.zeros(6)
        target = {'joints_deg': [4, 0, 0, 0, 0, 0]}
        def settled(q):
            return step_settled(target, initial,
                [(i*.05, np.array(q)) for i in range(13)], .6,
                command_initial=initial, min_progress=.4, aggregate_progress=True,
                max_residual_deg=2.5)
        self.assertTrue(settled([2, 0, 0, 0, 0, 0]))
        self.assertFalse(settled([0]*6))
        self.assertFalse(settled([-2, 0, 0, 0, 0, 0]))
        self.assertFalse(settled([2, 2.6, 0, 0, 0, 0]))

    def test_command_relative_settle_requires_actual_progress_despite_hold_residual(self):
        initial = np.array([.5, 20., 30., -15., 0., 0.])
        command = initial.copy()
        command[0] = 0.
        target = command.copy()
        target[0] = .2
        stamps = np.linspace(10., 10.6, 13).tolist()
        moved = initial.copy()
        moved[0] += .2
        self.assertTrue(step_settled({'joints_deg': target}, initial,
                                    [(t, moved) for t in stamps], 10.6, command_initial=command))
        self.assertFalse(step_settled({'joints_deg': target}, initial,
                                     [(t, initial) for t in stamps], 10.6, command_initial=command))
        wrong = initial.copy()
        wrong[0] -= .2
        self.assertFalse(step_settled({'joints_deg': target}, initial,
                                     [(t, wrong) for t in stamps], 10.6, command_initial=command))

    def test_explicit_cartesian_progress_threshold_still_rejects_stalls(self):
        initial = np.zeros(6)
        target = [1, 0, 0, 0, 0, 0]
        stamps = np.linspace(10., 10.6, 13).tolist()
        moved = np.array([.5, 0, 0, 0, 0, 0])
        self.assertTrue(step_settled({'joints_deg': target}, initial,
                                    [(t, moved) for t in stamps], 10.6,
                                    command_initial=initial, min_progress=.4))
        self.assertFalse(step_settled({'joints_deg': target}, initial,
                                     [(t, initial) for t in stamps], 10.6,
                                     command_initial=initial, min_progress=.4))

    def test_cartesian_aggregate_progress_allows_coupled_partial_tracking(self):
        initial = np.zeros(6)
        target = np.array([.83, 0, 0, .90, 0, 0])
        stamps = np.linspace(10., 10.6, 13).tolist()
        moved = np.array([.50, 0, 0, .35, 0, 0])
        samples = [(t, moved) for t in stamps]
        self.assertFalse(step_settled({'joints_deg': target}, initial, samples, 10.6,
                                      command_initial=initial, min_progress=.4))
        self.assertTrue(step_settled({'joints_deg': target}, initial, samples, 10.6,
                                     command_initial=initial, min_progress=.4,
                                     aggregate_progress=True))
        wrong = np.array([-.50, 0, 0, .90, 0, 0])
        self.assertFalse(step_settled({'joints_deg': target}, initial,
                                      [(t, wrong) for t in stamps], 10.6,
                                      command_initial=initial, min_progress=.4,
                                      aggregate_progress=True))

    def test_cartesian_settle_recognizes_recovery_toward_target_from_existing_residual(self):
        initial = np.array([-12.316361, -.557343, 1.234898, -10.589689, -3.005338, 1.475321])
        command = np.array([-12.316361, -.601057, .994476, -11.048678, -3.027194, 1.497177])
        target = np.array([-14.363956, 8.972297, 1.102725, -1.610795, -5.043427, 1.159328])
        measured = np.array([-14.261654, 8.862963, 1.213042, -1.912508, -4.797580, 1.256755])

        def settled(q):
            return step_settled({'joints_deg': target}, initial,
                [(i*.05, q.copy()) for i in range(13)], .6,
                command_initial=command, min_progress=.4, aggregate_progress=True,
                max_residual_deg=2.5)

        self.assertTrue(settled(measured))
        self.assertFalse(settled(initial))
        overshot = measured.copy()
        overshot[2] = target[2]-.2
        self.assertFalse(settled(overshot))
        reverse = measured.copy()
        reverse[4] = initial[4]+.5
        self.assertFalse(settled(reverse))

    def test_stable_noop_target_settles_without_dividing_by_zero(self):
        target = np.array([1., 2., 3., 4., 5., 6.])
        stamps = np.linspace(10., 10.6, 13).tolist()
        samples = [(stamp, target.copy()) for stamp in stamps]
        self.assertTrue(step_settled({'joints_deg': target}, target, samples, 10.6,
                                     command_initial=target, aggregate_progress=True))

    def test_corrupt_telemetry_cannot_bypass_numeric_checks(self):
        for key, value in (('feedback_age_ms', float('nan')), ('rx_age_ms', -1),
                           ('error_codes', None), ('tracking_error_deg', [float('nan')]*6),
                           ('lower_deg', [float('nan')]*6), ('upper_deg', [True]*6),
                           ('gripper_raw', float('inf')), ('gripper_target_raw', None)):
            sample = measured_state()
            sample[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_action(sample, {'joint_delta_deg': [1, 0, 0, 0, 0, 0]})

    def test_extra_fields_mixed_actuators_and_booleans_are_rejected(self):
        for action in ({}, {'joints_deg': [True]*6}, {'joint_delta_deg': ['1']*6},
                       {'gripper_raw': True}, {'gripper_raw': 4.2, 'joint_delta_deg': [0]*6},
                       {'speed': 1, 'gripper_raw': 4.2}, {'action': 'enable', 'gripper_raw': 4.2}):
            with self.assertRaises(ValueError):
                validate_action(measured_state(), action)

    def test_enable_timeout_and_pre_send_changes_do_not_send_target(self):
        for scenario in ('timeout', 'drift', 'vision', 'speed'):
            class Client:
                client = 'test'
                def __init__(self):
                    self.current = measured_state()
                    self.calls = []
                def state(self):
                    return copy.deepcopy(self.current)
                def request(self, *args, **kwargs):
                    return {'episode': {'status': 'recording'}}
                def command(self, action, **fields):
                    self.calls.append(action)
                    if action == 'enable':
                        self.current.update(enabled=True, owner=self.client)
                        if scenario == 'timeout':
                            raise TimeoutError('Acknowledgment lost')
                        if scenario == 'drift':
                            self.current['joints_deg'][0] += .6
                        if scenario == 'vision':
                            session.last_vision = 0
                        if scenario == 'speed':
                            self.current['speed'] = 1
                    if action == 'stop':
                        self.current.update(enabled=False, owner=None)
                    return self.state()
            client = Client()
            session = StepSession(client, None)
            session.last_vision = time.monotonic()
            with self.subTest(scenario=scenario), self.assertRaises((ValueError, TimeoutError)):
                session.apply({'joint_delta_deg': [1, 0, 0, 0, 0, 0]})
            self.assertNotIn('target', client.calls)
            self.assertEqual(client.calls[-1], 'stop')
            self.assertFalse(session.active)
            self.assertIsNotNone(session.failure)

    def test_camera_fault_is_latched_before_any_commands(self):
        class Client:
            def state(self):
                raise AssertionError('Should fail before HTTP access')
        session = StepSession(Client(), None)
        session.vision_failure = 'Camera identity changed'
        session.last_vision = time.monotonic()
        with self.assertRaisesRegex(ValueError, 'identity changed'):
            session.apply({'joint_delta_deg': [1, 0, 0, 0, 0, 0]})
        session.vision_failure = None
        with self.assertRaisesRegex(ValueError, 'halted'):
            session.apply({'joint_delta_deg': [1, 0, 0, 0, 0, 0]})

    def test_invalid_sample_clocks_never_establish_settling(self):
        samples = [(i*.05, np.array([0, 0, 2.3, 0, 0, 0])) for i in range(13)]
        target = {'joints_deg': [0, 0, 3, 0, 0, 0]}
        for stamp in (float('nan'), 1., .1):
            bad = samples.copy()
            bad[8] = (stamp, bad[8][1])
            self.assertFalse(step_settled(target, np.zeros(6), bad, .6))

    def test_relative_step_uses_fresh_feedback_for_unchanged_joints(self):
        state = measured_state()
        state['joints_deg'][1] = 3.617
        target = validate_action(state, {'joint_delta_deg': [0, 0, 2, 0, 0, 0]})
        self.assertEqual(target['joints_deg'], [0, 3.617, 32, -15, 0, 0])
        for delta in ([0, 0, 24.1, 0, 0, 0], [0]*5, [float('nan')]*6):
            with self.assertRaises(ValueError):
                validate_action(state, {'joint_delta_deg': delta})
        with self.assertRaises(ValueError):
            validate_action(state, {'joint_delta_deg': [0]*6, 'joints_deg': state['joints_deg']})

    def test_stable_residual_requires_progress_and_bounded_error(self):
        initial = np.zeros(6)
        target = {'joints_deg': [0, 0, 3, 0, 0, 0]}
        def samples(q):
            return [(i*.05, np.array(q, dtype=float)) for i in range(13)]
        self.assertTrue(step_settled(target, initial, samples([0, 0, 2.295, 0, 0, 0]), .6))
        for q in ([0]*6, [0, 0, -2.3, 0, 0, 0], [0, 0, 1.99, 0, 0, 0],
                  [0, 0, 4.01, 0, 0, 0], [1.01, 0, 2.295, 0, 0, 0]):
            self.assertFalse(step_settled(target, initial, samples(q), .6))
        small = {'joints_deg': [0, 0, .5, 0, 0, 0]}
        self.assertFalse(step_settled(small, initial, samples([0]*6), .6))

    def test_unstable_sparse_or_stale_feedback_never_settles(self):
        initial = np.zeros(6)
        target = {'joints_deg': [0, 0, 3, 0, 0, 0]}
        samples = [(i*.05, np.array([0, 0, 2.3, 0, 0, 0])) for i in range(13)]
        self.assertFalse(step_settled(target, initial, samples[-3:], .6))
        self.assertFalse(step_settled(target, initial, samples, 1.))
        self.assertFalse(step_settled(target, initial, samples[:3]+samples[8:], .6))
        samples[5][1][0] = .2
        self.assertFalse(step_settled(target, initial, samples, .6))

    def test_ball_candidate_is_pixels_not_position(self):
        image = np.full((480, 640, 3), (90, 120, 150), dtype=np.uint8)
        cv2.circle(image, (320, 210), 45, (80, 220, 160), -1)
        jpeg = cv2.imencode('.jpg', image)[1].tobytes()
        observation = detect_ball(jpeg)
        self.assertEqual(observation['candidate_count'], 1)
        np.testing.assert_allclose(observation['ball_candidate']['center_px'], [320, 210], atol=2)
        self.assertNotIn('position_mm', observation)

    def test_missing_ball_and_corrupt_frame(self):
        jpeg = cv2.imencode('.jpg', np.zeros((480, 640, 3), np.uint8))[1].tobytes()
        self.assertIsNone(detect_ball(jpeg)['ball_candidate'])
        with self.assertRaises(ValueError):
            detect_ball(b'not a jpeg')

    def test_joint_and_gripper_limits_are_enforced(self):
        state = measured_state()
        action = validate_action(state, {'joints_deg': [0, 20, 32, -15, 0, 0]})
        self.assertEqual(action['joints_deg'][2], 32)
        self.assertEqual(validate_action(state, {'gripper_raw': 4.2})['gripper_raw'], 4.2)
        for invalid in ({'joints_deg': [0, 20, 54.1, -15, 0, 0]},
                        {'joints_deg': [20, 40, 50, -15, 0, 0]},
                        {'joints_deg': [0, 20, float('nan'), -15, 0, 0]},
                        {'gripper_raw': 3.2}, {'gripper_raw': 4.5}, {'gripper_raw': float('inf')}):
            with self.assertRaises(ValueError):
                validate_action(state, invalid)
        state['joints_deg'][0] = 149
        with self.assertRaises(ValueError):
            validate_action(state, {'joints_deg': [151, 20, 30, -15, 0, 0]})

    def test_stale_faulted_or_simulated_feedback_blocks_action(self):
        for key, value in (('feedback_age_ms', 151), ('rx_age_ms', None),
                           ('error_codes', [12]), ('simulation', True), ('robot_status', 'fault')):
            state = measured_state()
            state[key] = value
            with self.assertRaises(ValueError):
                validate_action(state, {})

    def test_busy_owner_or_stale_camera_never_sends_command(self):
        class Client:
            client = 'test'
            def state(self):
                return copy.deepcopy(self.current)
            def command(self, *args, **kwargs):
                raise AssertionError('Must not send a command')
        client = Client()
        client.current = measured_state()
        session = StepSession(client, None)
        with self.assertRaises(ValueError):
            session.apply({})
        session.last_vision = time.monotonic()
        client.current.update(enabled=True, owner='human')
        with self.assertRaises(ValueError):
            session.apply({})

    def test_halted_session_cannot_reenable(self):
        session = StepSession(None, None)
        session.failure = 'Camera failure'
        with self.assertRaises(ValueError):
            session.apply({})

    def test_missed_joint_target_stops_instead_of_waiting_indefinitely(self):
        class Client:
            client = 'test'
            def __init__(self):
                self.current = measured_state()
                self.calls = []
            def state(self):
                return copy.deepcopy(self.current)
            def request(self, *args, **kwargs):
                return {'episode': {'status': 'recording'}}
            def command(self, action, **fields):
                self.calls.append(action)
                if action == 'enable':
                    self.current.update(enabled=True, owner=self.client)
                if action == 'stop':
                    self.current.update(enabled=False, owner=None)
                return self.state()
        client = Client()
        session = StepSession(client, None)
        session.emit = lambda event: None
        session.last_vision = time.monotonic()
        session.apply({'joints_deg': [0, 20, 32, -15, 0, 0]})
        target, initial, _ = session.pending
        session.pending = target, initial, time.monotonic()-1
        thread = threading.Thread(target=session.heartbeat)
        thread.start()
        try:
            deadline = time.monotonic()+1
            while session.failure is None and time.monotonic()<deadline:
                time.sleep(.01)
            self.assertIn('did not settle', session.failure)
            self.assertFalse(client.current['enabled'])
            self.assertEqual(client.calls[-1], 'stop')
        finally:
            session.done.set()
            thread.join()

    def test_halt_does_not_stop_new_human_owner(self):
        class Client:
            client = 'test'
            def state(self):
                return {'owner': 'human', 'enabled': True}
            def command(self, *args, **kwargs):
                raise AssertionError('New owner must be left in control')
        session = StepSession(Client(), None)
        session.active = True
        session.halt('ownership changed')
        self.assertFalse(session.active)


if __name__ == '__main__':
    unittest.main()
