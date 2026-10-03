import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from dual_return_pose import (check_idle_pair, check_return_contract, load_reference, load_reference_file,
                              next_return_step, preview, return_plan, return_step_with_renewal, main)
from r5_cartesian import CartesianBackend
from r5_dual_policy import ARMS, DualCartesianBackend
from r5_policy_backend import R5PolicyBackend
from test_r5_cartesian import TimedWorkbench, fixture_profile
from test_r5_policy_backend import Clock


class ReturnTests(unittest.TestCase):
    def setUp(self):
        self.clients, self.robots, self.reference = {}, {}, {'arms': {}}
        for side, channel in zip(ARMS, ('can0', 'can1')):
            client, clock = TimedWorkbench(), Clock()
            client.arm = side
            client.current.update(channel=channel, speed=.3,
                policy_tracking_limits_deg={'settle': 2.5, 'hold': 3., 'trajectory': 3.},
                policy_step_limits_deg={'joint': 12., 'norm': 16.5})
            self.clients[side] = client
            self.robots[side] = CartesianBackend(R5PolicyBackend(client, lambda: None,
                clock=clock, sleep=clock.sleep), fixture_profile(), 'both', 'image_grasp')
            goal = client.current['joints_deg'][:]
            goal[0] += 17
            goal[1] += 18
            self.reference['arms'][side] = {'channel': channel, 'joints_deg': goal}
        self.robot = DualCartesianBackend(self.robots, lambda: None)

    def test_loads_first_observation_and_preserves_physical_side(self):
        profiles = {side: fixture_profile() for side in ARMS}
        row = {'event': 'observation', 'at_s': 100., 'state': {'arms': {
            side: {'raw_state': client.state()} for side, client in self.clients.items()}}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'events.jsonl'
            path.write_text('\n'.join(json.dumps(r) for r in (
                {'event': 'calibration_profiles', 'profiles': profiles}, row,
                {'event': 'observation', 'state': {}})))
            reference, loaded = load_reference(directory)
            self.assertEqual(reference['arms']['left']['joints_deg'], self.clients['left'].current['joints_deg'])
            self.assertEqual(reference['arms']['right']['channel'], 'can1')
            self.assertEqual(loaded, profiles)
            saved = Path(directory)/'reference.json'
            saved.write_text(json.dumps({'reference': reference, 'profiles': profiles}))
            self.assertEqual(load_reference_file(saved), (reference, profiles))
            row['state']['arms']['right']['raw_state']['channel'] = 'can0'
            path.write_text(json.dumps(row))
            with self.assertRaisesRegex(ValueError, 'mapping'):
                load_reference(directory)

    def test_return_uses_fixed_small_caps_on_both_service_versions(self):
        state = self.clients['left'].state()
        for limits in ({'joint': 12., 'norm': 16.5}, {'joint': 24., 'norm': 33.}):
            state['policy_step_limits_deg'] = limits
            plan = return_plan(state, self.reference['arms']['left'], self.robots['left'].planner.limits, 100.)
            q = np.degrees(plan['joint_positions_rad'])
            displacement = q-state['command_deg']
            self.assertLessEqual(np.abs(displacement).max(), 6.+1e-9)
            self.assertLessEqual(np.linalg.norm(displacement, axis=1).max(), 8.25+1e-9)
            velocity = np.diff(np.vstack((state['command_deg'], q)), axis=0)/np.diff(
                [0., *plan['relative_times_s']])[:, None]
            self.assertLessEqual(np.abs(velocity).max(), 9.+1e-6)
            self.assertTrue(np.all(np.diff(plan['relative_times_s']) > 0))
        for limits in (None, {'joint': 5., 'norm': 8.25}, {'joint': 6., 'norm': float('nan')}):
            state['policy_step_limits_deg'] = limits
            with self.assertRaises(ValueError):
                check_return_contract(state)
        state['policy_tracking_limits_deg']['hold'] = 4.
        with self.assertRaisesRegex(ValueError, 'tracking contract'):
            check_return_contract(state)

    def test_right_reference_rejection_prevents_left_movement(self):
        self.reference['arms']['right']['joints_deg'][0] = 999.
        with self.assertRaisesRegex(ValueError, 'limit margin'):
            next_return_step(self.robot, self.reference)
        for client in self.clients.values():
            self.assertFalse(any(action != 'heartbeat' for action, _ in client.commands))

    def test_repeated_return_reaches_both_goals_without_gripper_or_home_commands(self):
        for _ in range(10):
            result = next_return_step(self.robot, self.reference)
            if result['at_reference']:
                break
        self.assertTrue(result['at_reference'])
        for side, client in self.clients.items():
            np.testing.assert_allclose(client.current['joints_deg'],
                                       self.reference['arms'][side]['joints_deg'], atol=2.5, rtol=0)
            self.assertTrue(client.current['enabled'])
            self.assertEqual(client.current['control_state'], 'holding')
            self.assertEqual(client.current['gripper_command_raw'], 4.3)
            self.assertTrue(set(action for action, _ in client.commands) <= {
                'heartbeat', 'resume', 'policy_trajectory', 'pause_hold'})

    def test_command_arrival_does_not_hide_bad_measured_position(self):
        state = self.clients['left'].state()
        state['command_deg'] = self.reference['arms']['left']['joints_deg'][:]
        with self.assertRaisesRegex(ValueError, 'measured joints'):
            return_plan(state, self.reference['arms']['left'], self.robots['left'].planner.limits, 100.)

    def test_reanchored_arrival_does_not_repeat_a_tiny_return(self):
        state = self.clients['left'].state()
        goal = self.reference['arms']['left']['joints_deg']
        state.update(command_deg=[q + 1.4 for q in goal], joints_deg=[q + 1.4 for q in goal])
        self.assertIsNone(return_plan(state, self.reference['arms']['left'],
                                     self.robots['left'].planner.limits, 100.))
        state['command_deg'][0] = goal[0] + 3
        self.assertIsNotNone(return_plan(state, self.reference['arms']['left'],
                                        self.robots['left'].planner.limits, 100.))

    def test_long_return_renews_before_exceeding_the_session_envelope(self):
        for side, client in self.clients.items():
            goal = client.current['joints_deg'][:]
            goal[0] += 50
            self.reference['arms'][side]['joints_deg'] = goal
        events = []
        for _ in range(15):
            result = return_step_with_renewal(self.robot, self.reference,
                                             lambda event, data: events.append(event))
            if result['at_reference']:
                break
        self.assertTrue(result['at_reference'])
        self.assertEqual(events, ['session_budget_renewed'])
        self.assertIsNone(self.robot.fault)
        for side, client in self.clients.items():
            self.assertTrue(client.current['enabled'])
            self.assertIsNone(self.robots[side].backend.guard.failure)
            self.assertLessEqual(abs(client.current['joints_deg'][0]-50.), 2.5)

    def test_preview_is_readonly_and_execution_rejects_an_existing_owner(self):
        states = {side: client.state() for side, client in self.clients.items()}
        result = preview(states, self.reference, self.robots)
        self.assertFalse(result['executed'])
        self.assertGreater(result['arms']['left']['planned_steps'], 1)
        with self.assertRaisesRegex(ValueError, 'old controller'):
            check_idle_pair(states, self.reference)
        for client in self.clients.values():
            self.assertEqual(client.commands, [])

    def test_cli_does_not_stop_an_existing_host_on_admission_failure(self):
        owner = self.clients['left'].client
        self.clients['left'].request = lambda *args: {'paired_policy_client': owner}
        with patch('dual_return_pose.load_reference', return_value=(self.reference, {})), \
             patch('dual_return_pose.ArmWorkbenchClient', side_effect=lambda url, side: self.clients[side]), \
             patch('dual_return_pose.SupervisedCameras') as cameras:
            with self.assertRaisesRegex(ValueError, 'old controller'):
                main(['--run', 'fixture', '--execute', '--supported-supervision', '--paired-client', owner])
        cameras.assert_not_called()
        for client in self.clients.values():
            self.assertEqual(client.commands, [])
            self.assertTrue(client.current['enabled'])


if __name__ == '__main__':
    unittest.main()
