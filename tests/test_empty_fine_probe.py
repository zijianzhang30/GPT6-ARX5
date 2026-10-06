import copy
import unittest

import numpy as np

from empty_fine_probe import EmptyFineProbeBackend, probe_metrics
from r5_cartesian import CartesianBackend
from r5_policy_backend import R5ExecutionFault
from test_r5_cartesian import TimedWorkbench, fixture_profile
from test_r5_policy_backend import Clock


class ResponseWorkbench(TimedWorkbench):
    response = 1.
    def command(self, action, **fields):
        initial = self.current['joints_deg'][:]
        result = super().command(action, **fields)
        if action == 'policy_trajectory':
            self.current['joints_deg'] = (np.array(initial)+self.response*
                (np.array(fields['points_deg'][-1])-initial)).tolist()
        return result


class EmptyFineProbeTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.client = ResponseWorkbench()
        self.client.current.update(gripper_raw=4.7, gripper_target_raw=4.8, gripper_command_raw=4.8)
        self.low = EmptyFineProbeBackend(self.client, lambda: None,
            clock=self.clock, sleep=self.clock.sleep, minimum_cartesian_command_step_deg=2.)
        self.robot = CartesianBackend(self.low, fixture_profile(), tracking_reserve_deg=3.5)
        self.low.state()
        self.plan = self.make_plan(.003)

    def make_plan(self, dz, dx=0):
        pose = self.robot.state()['tcp_command_xyzquat'][:]
        pose[0] += dx
        pose[2] += dz
        return self.robot.plan([{'pose_xyzquat': pose}], 'Offline open empty probe fixture')

    def test_ordinary_path_still_rejects_small_step_without_any_commands(self):
        with self.assertRaisesRegex(ValueError, 'below this session minimum 2'):
            self.low.execute_trajectory(self.plan)
        self.assertEqual(self.client.commands, [])
        self.assertFalse(self.low.probe_attempted)
        self.assertEqual(self.low.guard.proposals, 0)

    def test_real_progress_passes_once_but_never_qualifies_contact_or_grasp(self):
        result = self.low.execute_probe(self.robot, self.plan)
        self.assertTrue(result['passed'])
        self.assertFalse(result['failed_target_cancelled'])
        self.assertFalse(result['contact_motion_qualified'])
        self.assertFalse(result['grasp_verified'])
        self.assertTrue(self.client.current['enabled'])
        self.assertIsNone(self.low.fault)
        self.assertEqual(self.low.minimum_cartesian_command_step_deg, 2.)
        self.assertNotIn('stop', [x[0] for x in self.client.commands])
        self.assert_locked()

    def assert_locked(self):
        for call in (lambda: self.low.execute_probe(self.robot, self.plan),
                     self.low.renew_session,
                     lambda: self.low.execute_trajectory(self.plan),
                     lambda: self.low.execute('set_gripper', {})):
            before = copy.deepcopy(self.client.commands)
            with self.assertRaises(ValueError):
                call()
            self.assertEqual(before, self.client.commands)
        self.low.check()  # Lock prohibits motion, but must not kill healthy supervision.
        self.assertEqual(self.client.current['control_state'], 'holding')
        self.assertTrue(self.client.current['enabled'])

    def test_stall_and_partial_progress_fail_cancel_target_and_keep_healthy_hold(self):
        for response in (0., .07, .4, .79):
            with self.subTest(response=response):
                self.setUp()
                self.client.response = response
                result = self.low.execute_probe(self.robot, self.plan)
                self.assertFalse(result['passed'])
                self.assertTrue(result['stationary'])
                self.assertTrue(result['failed_target_cancelled'])
                self.assertAlmostEqual(result['projected_progress'], response)
                self.assertLessEqual(max(abs(a-b) for a,b in zip(
                    self.client.current['command_deg'], self.client.current['joints_deg'])), .05)
                self.assertEqual(self.client.current['gripper_command_raw'], 4.8)
                self.assertIsNone(self.low.fault)
                self.assertNotIn('stop', [x[0] for x in self.client.commands])
                self.assert_locked()

    def test_wrong_direction_or_large_excursion_still_stops(self):
        for response in (-.5, 2.):
            with self.subTest(response=response):
                self.setUp(); self.client.response = response
                with self.assertRaises(R5ExecutionFault):
                    self.low.execute_probe(self.robot, self.plan)
                self.assertFalse(self.client.current['enabled'])

    def test_lost_ack_stops_and_does_not_retry(self):
        for command in ('resume', 'policy_trajectory', 'pause_hold', 'target'):
            with self.subTest(command=command):
                self.setUp(); self.client.response = .1; self.client.timeout = command
                with self.assertRaises(R5ExecutionFault):
                    self.low.execute_probe(self.robot, self.plan)
                self.assertFalse(self.client.current['enabled'])
                self.assertLessEqual([x[0] for x in self.client.commands].count('policy_trajectory'), 1)

    def test_preflight_bounds_reject_without_commands_or_consumption(self):
        for case in ('closed', 'residual', 'reserve', 'sideways', 'down', 'long', 'expired'):
            with self.subTest(case=case):
                self.setUp()
                if case == 'closed':
                    self.client.current['gripper_command_raw'] = 1.
                    self.client.current['gripper_target_raw'] = 1.
                elif case == 'residual':
                    self.client.current['joints_deg'][1] += .1
                elif case == 'reserve':
                    self.robot.tracking_reserve_deg = 3.4
                elif case == 'sideways':
                    self.plan = self.make_plan(.003, dx=.001)
                elif case == 'down':
                    self.plan = self.make_plan(-.003)
                elif case == 'long':
                    self.plan = self.make_plan(.006)
                elif case == 'expired':
                    self.clock.sleep(31)
                with self.assertRaises(ValueError):
                    self.low.execute_probe(self.robot, self.plan)
                self.assertEqual(self.client.commands, [])
                self.assertFalse(self.low.consumed)
                self.assertFalse(self.low.probe_attempted)

    def test_stale_health_owner_tracking_and_vision_faults_during_probe_still_stop(self):
        for case in ('feedback_age_ms', 'owner', 'tracking_limited', 'vision'):
            with self.subTest(case=case):
                self.setUp()
                original = self.client.command
                def command(action, **fields):
                    result = original(action, **fields)
                    if action == 'policy_trajectory':
                        if case == 'vision':
                            def fail(): raise R5ExecutionFault('Camera stale')
                            self.low.vision_check = fail
                        else:
                            self.client.current[case] = {
                                'feedback_age_ms': 5000, 'owner': 'lost', 'tracking_limited': True}[case]
                    return result
                self.client.command = command
                with self.assertRaises(R5ExecutionFault):
                    self.low.execute_probe(self.robot, self.plan)
                self.assertIsNotNone(self.low.fault)
                if case != 'owner':
                    self.assertFalse(self.client.current['enabled'])

    def test_stability_samples_do_not_allow_a_single_good_endpoint_to_pass(self):
        initial = {'joints_deg': [0.]*6, 'command_deg': [0.]*6}
        target = [.6, 0, 0, 0, 0, 0]
        samples = [(i*.05, np.array(target)) for i in range(13)]
        self.assertTrue(probe_metrics(initial, target, samples, .6)['passed'])
        for bad in (samples[-1:], samples[:4]+samples[8:],
                    [(t, q+(.2 if i%2 else 0)) for i,(t,q) in enumerate(samples)]):
            self.assertFalse(probe_metrics(initial, target, bad, .6)['passed'])
        self.assertFalse(probe_metrics(initial, target, samples, .9)['passed'])

    def test_persistent_oscillation_cannot_use_stationary_failure_hold(self):
        original = self.client.state
        submitted = False
        command = self.client.command
        def dispatch(action, **fields):
            nonlocal submitted
            result = command(action, **fields)
            if action == 'policy_trajectory': submitted = True
            return result
        def state():
            result = original()
            if submitted:
                result['joints_deg'][1] += .11 if int(self.clock()*20)%2 else -.11
            return result
        self.client.command = dispatch
        self.client.state = state
        with self.assertRaisesRegex(R5ExecutionFault, 'did not become stationary'):
            self.low.execute_probe(self.robot, self.plan)
        self.assertFalse(self.client.current['enabled'])


if __name__ == '__main__':
    unittest.main()
