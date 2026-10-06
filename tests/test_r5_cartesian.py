import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from control import ROOT, URDF
from r5_cartesian import CartesianBackend, CalibratedCameras, profile_issues
from r5_policy_backend import R5PolicyBackend, R5ExecutionFault
from r5_policy_deployment import R5Cameras, run_r5_policy
from r5_policy_supervisor import R5PolicySupervisor
from supervised_policy import main
from test_policy_adapter import FakeWorkbench
from test_r5_policy_backend import Clock, Workbench


def fixture_profile():
    """Synthetic test geometry only, never written to the live calibration file."""
    identity = np.eye(4).tolist()
    tcp = np.eye(4)
    tcp[2, 3] = .02
    return {'version': 1, 'robot_model': 'R5', 'kinematics_verified': True,
            'measurement_record': 'synthetic fixture, not real measurements',
            'urdf_sha256': hashlib.sha256(URDF.read_bytes()).hexdigest(),
            'calibration': {'link6_from_sdk_eef': identity, 'link6_from_tcp': tcp.tolist(),
                            'link6_from_camera': {'left': identity}, 'base_from_camera': {}},
            'vision': {'camera_intrinsics': {'left': [[100, 0, 16], [0, 100, 12], [0, 0, 1]]},
                       'distortion_coefficients': {'left': [0]*5}, 'image_sizes': {'left': [32, 24]},
                       'device_ids': {'left': '/dev/gemini'}, 'mount_record': 'fixture'},
            'gripper': {'command_closed_raw': .1, 'command_open_raw': 4.9,
                        'feedback_closed_raw': 0., 'feedback_open_raw': 4.8},
            'scene': {'safety_notes': ['Synthetic test scene only.']}}


class ProfileTests(unittest.TestCase):
    def test_missing_calibration_blocks_before_any_device_or_model_access(self):
        with patch('supervised_policy.WorkbenchClient') as client, patch('supervised_policy.new_agent') as agent:
            self.assertEqual(main(['--check', '--camera-mode', 'wrist']), 2)
            client.assert_not_called()
            agent.assert_not_called()
        profile = json.loads((ROOT/'r5_cartesian_profile.json').read_text())
        self.assertTrue(profile_issues(profile, 'wrist'))

    def test_measured_profile_requires_rigid_transforms_and_matching_robot_hash(self):
        self.assertEqual(profile_issues(fixture_profile()), [])
        for field in ('hash', 'reflection', 'intrinsics', 'gripper'):
            p = fixture_profile()
            if field == 'hash':
                p['urdf_sha256'] = 'wrong'
            elif field == 'reflection':
                p['calibration']['link6_from_tcp'][0][0] = -1
            elif field == 'intrinsics':
                p['vision']['camera_intrinsics']['left'][0][0] = 0
            else:
                p['gripper']['command_closed_raw'] = 4.9
            self.assertTrue(profile_issues(p))

    def test_estimated_tcp_cannot_be_enabled_by_robot_model_verification_alone(self):
        p = fixture_profile()
        p['calibration']['tcp_validation'] = {'status': 'estimated', 'physical_validation_record': None}
        for stage in ('motion', 'vision', 'grasp'):
            self.assertIn('TCP transform is an estimate; physical validation record is required',
                          profile_issues(p, stage=stage))
        p['calibration']['tcp_validation']['status'] = 'verified'
        self.assertTrue(profile_issues(p, stage='motion'))
        p['calibration']['tcp_validation']['physical_validation_record'] = 'Synthetic test evidence'
        self.assertEqual(profile_issues(p, stage='motion'), [])

    def test_commissioning_allows_estimates_but_not_invalid_geometry_or_grasp(self):
        p = fixture_profile()
        p['kinematics_verified'] = False
        p['measurement_record'] = None
        p['calibration']['tcp_validation'] = {'status': 'estimated'}
        self.assertEqual(profile_issues(p, stage='motion', commissioning=True), [])
        self.assertTrue(profile_issues(p, commissioning=True))
        self.assertTrue(profile_issues(p, stage='motion'))
        p['calibration']['link6_from_tcp'] = None
        self.assertTrue(profile_issues(p, stage='motion', commissioning=True))

    def test_calibrated_camera_mismatch_is_rejected(self):
        client = FakeWorkbench()
        source = R5Cameras(client, camera_mode='wrist')
        cameras = CalibratedCameras(source, fixture_profile())
        with patch('policy_adapter.time.sleep'):
            self.assertEqual(set(cameras.snapshot()), {'left'})
            cameras.settings['vision']['image_sizes']['left'] = [640, 480]
            with self.assertRaisesRegex(ValueError, 'differs'):
                cameras.snapshot()

    def test_motion_stage_does_not_require_camera_or_gripper_calibration(self):
        p = fixture_profile()
        p['calibration']['link6_from_camera']['left'] = None
        p['vision']['camera_intrinsics']['left'] = None
        p['vision']['mount_record'] = None
        p['gripper'] = {}
        self.assertEqual(profile_issues(p, stage='motion'), [])
        self.assertTrue(profile_issues(p, stage='vision'))
        self.assertTrue(profile_issues(p, stage='grasp'))
        p['kinematics_verified'] = False
        self.assertTrue(profile_issues(p, stage='motion'))

    def test_vision_stage_does_not_enable_unmeasured_gripper(self):
        p = fixture_profile()
        p['gripper'] = {}
        self.assertEqual(profile_issues(p, stage='vision'), [])
        self.assertTrue(profile_issues(p))
        self.assertTrue(profile_issues(p, stage='unknown'))

    def test_motion_cli_checks_partial_profile_without_hardware_and_requires_explicit_task(self):
        p = fixture_profile()
        p['vision']['camera_intrinsics']['left'] = None
        p['gripper'] = {}
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory)/'partial.json'
            filename.write_text(json.dumps(p))
            args = ['--cartesian-stage', 'motion', '--calibration-profile', str(filename)]
            with patch('supervised_policy.WorkbenchClient') as client, patch('supervised_policy.new_agent') as agent:
                self.assertEqual(main([*args, '--check']), 0 if importlib.util.find_spec('ruckig') else 2)
                if importlib.util.find_spec('ruckig'):
                    with self.assertRaises(SystemExit):
                        main([*args, '--supported-supervision'])
                    with self.assertRaises(SystemExit):
                        main([*args, '--supported-supervision', '--task', 'Contact-free test',
                              '--open-gripper-to', '4.8'])
                client.assert_not_called()
                agent.assert_not_called()


class TimedWorkbench(Workbench):
    def __init__(self):
        super().__init__()
        self.current.update(policy_trajectory_protocol=1, policy_trajectory_active=False,
                            velocity_deg=[0]*6)

    def command(self, action, **fields):
        if action != 'policy_trajectory':
            return super().command(action, **fields)
        self.commands.append((action, copy.deepcopy(fields)))
        self.current['command_deg'] = fields['points_deg'][-1][:]
        if not self.stall:
            self.current['joints_deg'] = fields['points_deg'][-1][:]
        self.current['policy_trajectory_active'] = False
        if self.timeout == action:
            raise TimeoutError('Response lost after path submission')
        return self.state()


@unittest.skipUnless(importlib.util.find_spec('ruckig'), 'Run with .venv-policy/bin/python for original planner tests')
class CartesianTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.client = TimedWorkbench()
        self.low = R5PolicyBackend(self.client, lambda: None, clock=self.clock, sleep=self.clock.sleep)
        self.robot = CartesianBackend(self.low, fixture_profile())

    def target(self):
        state = self.robot.state()
        pose = state['tcp_xyzquat'][:]
        pose[0] += .0005
        return {'pose_xyzquat': pose}

    def test_planning_reserve_rejection_precedes_dispatch_and_preserves_session(self):
        self.robot.tracking_reserve_deg = 3.5
        target = self.target()
        for tool, args in [('move_to', {'target': target}),
                           ('check_path', {'poses': [target]})]:
            with self.subTest(tool=tool), patch('r5_cartesian.check_tracking_reserve',
                    side_effect=ValueError('Planning tracking reserve rejected')) as guard:
                before = len(self.client.commands)
                with self.assertRaisesRegex(ValueError, 'tracking reserve'):
                    self.robot.execute(tool, {**args, 'note': 'Fixture reserve rejection'})
                guard.assert_called_once()
                self.assertEqual(len(self.client.commands), before)
                self.assertIsNone(self.low.guard.failure)
                self.assertEqual(self.low.guard.proposals, 0)

    def test_right_context_uses_its_channel_and_generic_target(self):
        self.client.arm = 'right'
        robot = CartesianBackend(self.low, fixture_profile(), 'both', 'image_grasp')
        text = robot.context('Pick up the cola can.').instructions
        self.assertIn('Controlled physical arm: right, interface can1', text)
        self.assertIn('wrist image key remain left', text)
        self.assertIn('surfaces actually straddle the target', text)
        self.assertNotIn('straddle the ball', text)
        self.assertIn('24 degrees/joint, 33 degrees joint norm', text)
        self.assertIn('20 accepted actions, 40 degrees excursion, 120 degrees total joint travel', text)
        self.assertIn('prefer one longer continuous planned path', text)

    def test_demonstrated_pregrasp_guide_stays_on_reference_ik_branch(self):
        profile = fixture_profile()
        start_deg = self.client.current['command_deg']
        goal_deg = (np.asarray(start_deg)+np.asarray([2., 20., 5., 12., -1., -2.])).tolist()
        profile['demonstrated_pregrasp'] = {'joints_deg': goal_deg, 'source': 'fixture'}
        robot = CartesianBackend(self.low, profile)

        guide = robot.state()['demonstrated_pregrasp_guide']
        step = np.asarray(guide['next_joints_deg'])-np.asarray(start_deg)
        self.assertLessEqual(np.max(np.abs(step)), 3.5+1e-9)
        self.assertLessEqual(np.linalg.norm(step), 4.5+1e-9)
        plan = robot.plan([{'pose_xyzquat': guide['next_tcp_xyzquat']}], 'Fixture guide')
        np.testing.assert_allclose(np.degrees(plan['joint_positions_rad'][-1]),
                                   guide['next_joints_deg'], atol=.01)

    def test_budget_boundary_requires_renewal_before_another_plan(self):
        self.robot.last_plan_rejection = 'Trajectory exhausts session joint travel budget'
        with self.assertRaisesRegex(ValueError, 'Session renewal required'):
            self.robot.plan([self.target()], 'Fixture retry')

    def test_low_remaining_budget_returns_to_host_before_model_give_up(self):
        self.low.guard.joint_travel = 119.716146
        self.low.guard.proposals = 5
        agent = MagicMock()
        agent.decide.return_value = {'name': 'give_up', 'arguments': {
            'reason': 'Fixture: no supported approach remains', 'hindsight': ''}}
        supervisor = R5PolicySupervisor(self.robot)
        self.addCleanup(supervisor.close)
        supervisor.start()
        cameras = CalibratedCameras(R5Cameras(FakeWorkbench(), camera_mode='wrist'), fixture_profile())
        runtime = SimpleNamespace(max_decisions=1, interface='can0', right_interface='',
                                  policy_interface='cartesian', camera_mode='wrist', auto_renew_budgets=True)
        from gpt_policy.recording.trace import RunRecorder
        with tempfile.TemporaryDirectory() as directory, patch('policy_adapter.time.sleep'):
            recorder = RunRecorder(Path(directory)/'run', {'fixture': True})
            try:
                request = SimpleNamespace(instruction='Fixture grasp', content=())
                result = run_r5_policy(runtime, request, self.robot, cameras, agent, recorder,
                                       supervisor=supervisor, display=MagicMock())
                self.assertEqual(result, 'motion_budget_boundary')
                agent.decide.assert_not_called()
                self.assertTrue(self.client.current['enabled'])
                self.assertEqual(self.client.current['control_state'], 'holding')
                self.assertFalse(any(name in ('target', 'policy_trajectory', 'stop', 'home')
                                     for name, _ in self.client.commands))
                self.robot.renew_session()
                result = run_r5_policy(runtime, request, self.robot, cameras, agent, recorder,
                                       supervisor=supervisor, display=MagicMock(), start_agent=False)
                self.assertEqual(result, 'give_up')
                agent.decide.assert_called_once()
                agent.start.assert_called_once()
            finally:
                recorder.close('unreviewed')

    def test_proactive_budget_boundary_requires_host_opt_in(self):
        self.low.guard.joint_travel = 119.716146
        agent = MagicMock()
        agent.decide.return_value = {'name': 'give_up', 'arguments': {
            'reason': 'Fixture operator handoff', 'hindsight': ''}}
        supervisor = R5PolicySupervisor(self.robot)
        self.addCleanup(supervisor.close)
        supervisor.start()
        cameras = CalibratedCameras(R5Cameras(FakeWorkbench(), camera_mode='wrist'), fixture_profile())
        runtime = SimpleNamespace(max_decisions=1, interface='can0', right_interface='',
                                  policy_interface='cartesian', camera_mode='wrist')
        from gpt_policy.recording.trace import RunRecorder
        with tempfile.TemporaryDirectory() as directory, patch('policy_adapter.time.sleep'):
            recorder = RunRecorder(Path(directory)/'run', {'fixture': True})
            try:
                result = run_r5_policy(runtime, SimpleNamespace(instruction='Fixture', content=()),
                    self.robot, cameras, agent, recorder, supervisor=supervisor, display=MagicMock())
                self.assertEqual(result, 'give_up')
                agent.decide.assert_called_once()
            finally:
                recorder.close('unreviewed')

    def test_real_upstream_planner_preserves_tcp_and_readonly_check_sends_nothing(self):
        target = self.target()
        before = self.low.guard.snapshot()
        checked = self.robot.execute('check_path', {'poses': [target], 'note': 'Fixture path'})
        self.assertTrue(checked['path_check']['accepted'])
        self.assertFalse(checked['path_check']['collision_checked'])
        self.assertEqual(self.client.commands, [])
        self.assertEqual(self.low.guard.snapshot(), before)
        plan = self.robot.plan([target], 'Fixture path')
        self.assertEqual(plan['result']['timing'], 'ruckig_scalar_path_parameterization')
        self.assertTrue(np.all(np.diff(plan['relative_times_s']) > 0))
        final = self.robot.frames.sdk_to_tcp(self.robot.solver.forward_kinematics(plan['joint_positions_rad'][-1]))
        np.testing.assert_allclose(final[:3], target['pose_xyzquat'][:3], atol=2e-5)

    def test_execute_keeps_upstream_samples_and_times_then_holds(self):
        target = self.target()
        result = self.robot.execute('move_to', {'target': target, 'note': 'Fixture move'})
        commands = [fields for name, fields in self.client.commands if name == 'policy_trajectory']
        self.assertEqual(len(commands), 1)
        np.testing.assert_allclose(commands[0]['points_deg'], np.degrees(result['trajectory']['_trace']['joint_waypoints_rad']))
        self.assertEqual(commands[0]['times_s'], result['trajectory']['_trace']['relative_times_s'])
        self.assertEqual(self.low.guard.proposals, 1)
        self.assertEqual(result['control_state'], 'holding')
        self.assertFalse(result['grasp_verified'])
        self.assertFalse(any(name in ('home', 'enable', 'connect') for name, _ in self.client.commands))

    def test_session_small_step_filter_rejects_before_any_command_or_budget_debit(self):
        self.low.minimum_cartesian_command_step_deg = 2.
        plan = self.robot.plan([self.target()], 'Small step fixture')
        before = self.low.guard.snapshot()
        for operation in (self.low.preview_timed_trajectory, self.low.execute_trajectory):
            with self.assertRaisesRegex(ValueError, 'below this session minimum'):
                operation(plan)
            self.assertEqual(self.client.commands, [])
            self.assertEqual(self.low.guard.snapshot(), before)
            self.assertFalse(self.low.consumed)
            self.assertIsNone(self.low.fault)
            self.assertTrue(self.client.current['enabled'])
            self.assertEqual(self.client.current['control_state'], 'holding')

    def test_session_step_filter_preserves_larger_target_and_stall_protection(self):
        from r5_cartesian import rpy_to_quaternion
        self.low.minimum_cartesian_command_step_deg = 2.
        self.robot.state()
        q = np.radians(self.client.current['command_deg'])
        q[0] += np.radians(3.)
        pose = self.robot.frames.sdk_to_tcp(self.robot.solver.forward_kinematics(q))
        target = {'pose_xyzquat': [*pose[:3], *rpy_to_quaternion(pose[3:])]}
        plan = self.robot.plan([target], 'Larger step fixture')
        self.low.preview_timed_trajectory(plan)
        self.assertEqual(self.client.commands, [])
        self.client.stall = True
        with self.assertRaisesRegex(R5ExecutionFault, 'did not settle'):
            self.low.execute_trajectory(plan)
        submitted = next(fields for action, fields in self.client.commands if action == 'policy_trajectory')
        np.testing.assert_allclose(submitted['points_deg'][-1], np.degrees(q), atol=.01)
        self.assertEqual(self.client.commands[-1][0], 'stop')

    def test_lost_trajectory_ack_latches_stop_without_resubmission(self):
        target = self.target()
        self.client.timeout = 'policy_trajectory'
        with self.assertRaises(R5ExecutionFault):
            self.robot.execute('move_to', {'target': target, 'note': 'Fixture lost ack'})
        self.assertEqual(sum(n == 'policy_trajectory' for n, _ in self.client.commands), 1)
        self.assertEqual(self.client.commands[-1][0], 'stop')

    def test_held_residual_preserves_command_start_without_faking_measured_pose(self):
        self.client.current['joints_deg'][0] += .2
        target = self.target()
        plan = self.robot.plan([target], 'Fixture residual')
        np.testing.assert_allclose(np.degrees(plan['start_joint_positions_rad']), self.client.current['command_deg'])
        np.testing.assert_allclose(np.degrees(plan['planning_measured_joint_positions_rad']), self.client.current['joints_deg'])
        self.assertEqual(self.client.commands, [])
        self.client.current['command_deg'][0] += .1
        self.client.current['hold_target_deg'][0] += .1
        with self.assertRaisesRegex(ValueError, 'Held command'):
            self.low.execute_trajectory(plan)
        self.assertEqual(self.client.commands, [])
        self.assertEqual(self.low.guard.proposals, 0)

    def test_measured_drift_during_planning_is_still_rejected(self):
        target = self.target()
        plan = self.robot.plan([target], 'Fixture planning')
        self.client.current['joints_deg'][0] += .1
        with self.assertRaisesRegex(ValueError, 'changed during Cartesian planning'):
            self.low.execute_trajectory(plan)
        self.assertEqual(self.client.commands, [])

    def test_huge_target_rejected_before_dense_ik_or_motion(self):
        target = self.target()
        target['pose_xyzquat'][0] = 1000
        with patch.object(self.robot.planner, 'plan') as planner:
            with self.assertRaisesRegex(ValueError, 'sample capacity'):
                self.robot.execute('move_to', {'target': target, 'note': 'Fixture bad units'})
            planner.assert_not_called()
        self.assertEqual(self.client.commands, [])

    def test_upstream_normalized_gripper_maps_to_measured_endpoints(self):
        state = self.robot.state()
        value = (4.4-.1)/4.8
        result = self.robot.execute('set_gripper', {'gripper': value, 'note': 'Fixture gripper'})
        self.assertAlmostEqual(result['submitted_gripper_raw'], 4.4)
        self.assertAlmostEqual(state['gripper_normalized'], 4.2/4.8)
        self.assertAlmostEqual(state['gripper_step_limit_normalized'], 1./4.8)
        self.assertAlmostEqual(state['gripper_open_step_limit_normalized'], .1/4.8)

    def test_next_gripper_bounds_follow_command_not_lagging_feedback(self):
        for raw in (.1, 1.06, 4.9):
            with self.subTest(raw=raw):
                self.client.current.update(gripper_raw=raw-.1, gripper_command_raw=raw,
                                           gripper_target_raw=raw)
                state = self.robot.state()
                lower, upper = state['gripper_next_opening_bounds']
                self.assertAlmostEqual(lower, max(0., (raw-1.-.1)/4.8))
                self.assertAlmostEqual(upper, min(1., (raw+.1-.1)/4.8))
                self.assertLessEqual(lower, state['gripper_command_normalized'])
                self.assertGreaterEqual(upper, state['gripper_command_normalized'])

    def test_motion_stage_executes_original_path_without_inventing_gripper_feedback(self):
        p = fixture_profile()
        p['calibration']['link6_from_camera']['left'] = None
        p['vision']['camera_intrinsics']['left'] = None
        p['gripper'] = {}
        self.robot = CartesianBackend(self.low, p, stage='motion')
        context = self.robot.context('Validate a contact-free translation')
        names = {t['function']['name'] for t in context.tools}
        self.assertEqual(names, {'move_to', 'move_eef_chunk', 'check_path', 'done', 'give_up'})
        self.assertIn('uncalibrated visual observations', context.instructions)
        self.assertIsNone(self.robot.state()['gripper_normalized'])
        with self.assertRaisesRegex(ValueError, 'not enabled'):
            self.robot.execute('set_gripper', {'gripper': 0., 'note': 'Must reject'})
        with self.assertRaisesRegex(ValueError, 'not enabled'):
            self.robot.executor().execute('locate_point', {}, {}, {})
        result = self.robot.execute('move_to', {'target': self.target(), 'note': 'Fixture move'})
        self.assertEqual(result['control_state'], 'holding')
        self.assertTrue(all(v is None for v in result['trajectory']['_trace']['gripper_waypoints_normalized']))
        self.assertFalse(any(name == 'target' for name, _ in self.client.commands))

    def test_vision_stage_preserves_localizer_but_disables_gripper(self):
        p = fixture_profile()
        p['gripper'] = {}
        robot = CartesianBackend(self.low, p, stage='vision')
        names = {t['function']['name'] for t in robot.context('Validate localization').tools}
        self.assertIn('locate_point', names)
        self.assertNotIn('set_gripper', names)
        result = robot.executor().execute('locate_point', {'camera': 'left', 'pixel_xy': [16, 12]},
                                          robot.state(), {})
        self.assertFalse(result['metric_position_available'])
        self.assertEqual(self.client.commands, [])

    def test_commissioning_rejects_large_moves_rotation_model_and_second_motion(self):
        p = fixture_profile()
        p['kinematics_verified'] = False
        p['calibration']['tcp_validation'] = {'status': 'estimated'}
        self.robot = CartesianBackend(self.low, p, stage='motion', commissioning=True)
        with self.assertRaisesRegex(ValueError, 'no model'):
            self.robot.context('Must not start a model')
        target = self.target()
        target['pose_xyzquat'][0] += .0041
        with self.assertRaisesRegex(ValueError, '4 mm'):
            self.robot.execute('move_to', {'target': target, 'note': 'Too large'})
        target = self.target()
        target['pose_xyzquat'][3:] = [0., 0., 0., 1.]
        with self.assertRaisesRegex(ValueError, 'fixed orientation'):
            self.robot.execute('move_to', {'target': target, 'note': 'Must not rotate'})
        with self.assertRaisesRegex(ValueError, 'one move_to'):
            self.robot.execute('set_gripper', {'gripper': 0., 'note': 'Must hold'})
        self.assertEqual(self.client.commands, [])
        self.robot.execute('move_to', {'target': self.target(), 'note': 'Fixture validation'})
        with self.assertRaisesRegex(ValueError, 'one move_to'):
            self.robot.execute('move_to', {'target': self.target(), 'note': 'Must not repeat'})
        self.assertEqual(sum(n == 'policy_trajectory' for n, _ in self.client.commands), 1)

    def test_catalog_and_original_loop_use_cartesian_tools_and_fresh_feedback(self):
        names = {t['function']['name'] for t in self.robot.context('抓取网球').tools}
        self.assertEqual(names, {'move_to', 'move_eef_chunk', 'check_path', 'set_gripper', 'locate_point', 'done', 'give_up'})
        target = self.target()

        class Agent:
            def __init__(self): self.turns = []
            def start(self, context): self.context = context
            def decide(self, turn):
                self.turns.append(turn)
                step = len(self.turns)
                if step == 1:
                    return {'name': 'check_path', 'arguments': {'poses': [target], 'note': 'Check fixture'}}
                if step == 2:
                    return {'name': 'move_to', 'arguments': {'target': target, 'note': 'Move fixture'}}
                if step == 3:
                    return {'name': 'locate_point', 'arguments': {'camera': 'left', 'pixel_xy': [16, 12],
                            'reference_step': None, 'reference_pixel_xy': None, 'note': 'Fixture ray'}}
                return {'name': 'done', 'arguments': {'summary': 'Fixture only', 'hindsight': 'Not a grasp'}}

        agent = Agent()
        supervisor = R5PolicySupervisor(self.robot)
        self.addCleanup(supervisor.close)
        supervisor.start()
        cameras = CalibratedCameras(R5Cameras(FakeWorkbench(), camera_mode='wrist'), fixture_profile())
        from gpt_policy.recording.trace import RunRecorder
        with tempfile.TemporaryDirectory() as directory, patch('policy_adapter.time.sleep'):
            recorder = RunRecorder(Path(directory)/'run', {'fixture': True})
            try:
                result = run_r5_policy(SimpleNamespace(max_decisions=4, interface='can0', right_interface='',
                                                       policy_interface='cartesian', camera_mode='wrist'),
                                       SimpleNamespace(instruction='抓取网球', content=()), self.robot, cameras,
                                       agent, recorder, supervisor=supervisor, display=MagicMock())
                self.assertEqual(result, 'completed')
                last = json.loads(agent.turns[-1].observation)
                self.assertFalse(last['previous_result']['result']['metric_position_available'])
                self.assertIn('tcp_pose_xyzquat', last['state'])
                self.assertIn('motion_budget', last['state'])
                self.assertEqual(len(last['state']['joint_positions_deg']), 6)
                self.assertEqual(len(last['state']['joint_command_deg']), 6)
                self.assertEqual(len(last['state']['joint_tracking_error_deg']), 6)
                self.assertEqual(len(last['state']['joint_limit_margin_deg']), 6)
                self.assertIn('near_singular', last['state'])
                self.assertEqual(self.low.guard.proposals, 1)
                self.assertEqual(len(list(recorder.frames.glob('*.jpg'))), 4)
            finally:
                recorder.close('unreviewed')


if __name__ == '__main__':
    unittest.main()
