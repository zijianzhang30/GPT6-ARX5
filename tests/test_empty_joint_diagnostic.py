import copy
import unittest

import numpy as np

from empty_joint_diagnostic import EmptyJointDiagnosticBackend, joint_diagnostic_plan
from r5_cartesian import CartesianBackend
from r5_policy_backend import R5ExecutionFault
from test_empty_fine_probe import ResponseWorkbench
from test_r5_cartesian import fixture_profile
from test_r5_policy_backend import Clock


class EmptyJointDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.client = ResponseWorkbench()
        self.client.current.update(channel='can0', gripper_raw=4.7,
                                   gripper_target_raw=4.8, gripper_command_raw=4.8)
        self.low = EmptyJointDiagnosticBackend(self.client, lambda: None,
            clock=self.clock, sleep=self.clock.sleep, minimum_cartesian_command_step_deg=2.)
        self.robot = CartesianBackend(self.low, fixture_profile(), tracking_reserve_deg=3.5)
        self.low.state()
        self.plan = joint_diagnostic_plan(self.client.current)

    def test_pass_or_stall_is_one_attempt_only_keeps_hold_and_gripper(self):
        for response in (0., .4, 1.):
            with self.subTest(response=response):
                self.setUp()
                self.client.response = response
                initial = self.client.current['joints_deg'][:]
                result = self.low.execute_probe(self.robot, self.plan)
                self.assertEqual(result['passed'], response == 1.)
                self.assertTrue(result['motion_locked'])
                self.assertFalse(result['contact_motion_qualified'])
                self.assertEqual(result['failed_target_cancelled'], response != 1.)
                self.assertTrue(self.client.current['enabled'])
                self.assertEqual(self.client.current['control_state'], 'holding')
                self.assertEqual(self.client.current['gripper_command_raw'], 4.8)
                np.testing.assert_allclose(np.delete(self.client.current['joints_deg'], 2),
                                           np.delete(initial, 2))
                before = copy.deepcopy(self.client.commands)
                for call in (self.low.renew_session,
                             lambda: self.low.execute_probe(self.robot, self.plan),
                             lambda: self.low.execute_trajectory(self.plan)):
                    with self.assertRaises(ValueError): call()
                self.assertEqual(before, self.client.commands)
                self.assertNotIn('stop', [c[0] for c in before])
                self.low.check()

    def test_exact_path_and_start_restrictions_reject_before_send(self):
        for case in ('wrong_joint', 'negative', 'larger', 'faster', 'nan', 'short',
                     'closed', 'wrong_arm', 'residual', 'reserve', 'expired'):
            with self.subTest(case=case):
                self.setUp()
                if case == 'wrong_joint': self.plan['joint_positions_rad'][-1, 1] += .001
                elif case == 'negative':
                    start = self.plan['start_joint_positions_rad']
                    self.plan['joint_positions_rad'] = 2*start-self.plan['joint_positions_rad']
                elif case == 'larger': self.plan['joint_positions_rad'][-1, 2] += .001
                elif case == 'faster': self.plan['relative_times_s'][-1] = 1.
                elif case == 'nan': self.plan['joint_positions_rad'][0, 2] = float('nan')
                elif case == 'short': self.plan['joint_positions_rad'] = self.plan['joint_positions_rad'][:-1]
                elif case == 'closed':
                    self.client.current['gripper_command_raw'] = 1.
                    self.client.current['gripper_target_raw'] = 1.
                elif case == 'wrong_arm': self.client.current['channel'] = 'can1'
                elif case == 'residual': self.client.current['joints_deg'][1] += .1
                elif case == 'reserve': self.robot.tracking_reserve_deg = 3.4
                elif case == 'expired': self.clock.sleep(31)
                with self.assertRaises(ValueError): self.low.execute_probe(self.robot, self.plan)
                self.assertEqual(self.client.commands, [])
                self.assertFalse(self.low.probe_attempted)

    def test_ordinary_minimum_is_retained(self):
        with self.assertRaisesRegex(ValueError, 'below this session minimum 2'):
            self.low.execute_trajectory(self.plan)
        self.assertEqual(self.client.commands, [])

    def test_reanchor_budget_is_bounded(self):
        self.low.renew_session()
        self.low.renew_session()
        before = copy.deepcopy(self.client.commands)
        with self.assertRaises(ValueError): self.low.renew_session()
        self.assertEqual(before, self.client.commands)

    def test_wrong_direction_and_transport_failure_preserve_original_stops(self):
        for case in ('reverse', 'ack'):
            with self.subTest(case=case):
                self.setUp()
                if case == 'reverse': self.client.response = -.5
                else: self.client.timeout = 'policy_trajectory'
                with self.assertRaises(R5ExecutionFault): self.low.execute_probe(self.robot, self.plan)
                self.assertFalse(self.client.current['enabled'])
                self.assertEqual([c[0] for c in self.client.commands].count('policy_trajectory'), 1)
