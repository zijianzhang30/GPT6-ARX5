import copy
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from r5_cartesian import CartesianAgent, CartesianBackend
from r5_dual_policy import ARMS, DualCartesianBackend
from r5_policy_backend import R5ExecutionFault, R5PolicyBackend
from r5_policy_deployment import R5DualCameras, run_r5_policy
from record_workbench import RecordingWorkbench
from test_policy_adapter import FakeWorkbench
from test_r5_cartesian import TimedWorkbench, fixture_profile
from test_r5_policy_backend import Clock


class DualTests(unittest.TestCase):
    def setUp(self):
        self.clients, self.robots = {}, {}
        for side in ARMS:
            clock, client = Clock(), TimedWorkbench()
            client.arm = side
            low = R5PolicyBackend(client, lambda: None, clock=clock, sleep=clock.sleep)
            self.clients[side] = client
            self.robots[side] = CartesianBackend(low, fixture_profile(), 'both', 'image_grasp')
        self.robot = DualCartesianBackend(self.robots, lambda: None)
        self.initial = self.robot.state()

    def target(self, side, distance=.0005):
        pose = self.initial['arms'][side]['tcp_command_xyzquat'][:]
        pose[0] += distance
        return {'pose_xyzquat': pose}

    def test_second_arm_rejection_prevents_first_dispatch(self):
        with patch.object(self.robots['right'], 'plan', side_effect=ValueError('unreachable')):
            with self.assertRaisesRegex(ValueError, 'unreachable'):
                self.robot.execute('move_to', {'target': {side: self.target(side) for side in ARMS},
                                               'note': 'Fixture'})
        for client in self.clients.values():
            self.assertFalse(any(action in ('resume', 'target', 'policy_trajectory')
                                 for action, _ in client.commands))

    def test_paired_motion_dispatches_both_and_reports_residuals(self):
        result = self.robot.execute('move_to', {'target': {side: self.target(side) for side in ARMS},
                                               'note': 'Fixture'})
        self.assertEqual(set(result['arms']), set(ARMS))
        for side, client in self.clients.items():
            self.assertEqual(sum(action == 'policy_trajectory' for action, _ in client.commands), 1)
            self.assertEqual(result['arms'][side]['control_state'], 'holding')
        self.assertFalse(result['collision_checked'])
        self.assertFalse(result['grasp_verified'])

    def test_null_side_holds_without_target_or_disable(self):
        result = self.robot.execute('move_to', {'target': {'left': self.target('left'), 'right': None},
                                               'note': 'Fixture'})
        self.assertEqual(result['held_sides'], ['right'])
        self.assertFalse(any(action != 'heartbeat' for action, _ in self.clients['right'].commands))

    def test_check_path_synchronizes_by_slowing_without_dispatch(self):
        result = self.robot.execute('check_path', {'poses': [{'left': self.target('left', .0005),
            'right': self.target('right', .001)}], 'note': 'Fixture'})
        durations = [result['path_check']['arms'][side]['planned_duration_s'] for side in ARMS]
        self.assertAlmostEqual(*durations)
        self.assertFalse(result['path_check']['collision_checked'])
        for client in self.clients.values():
            self.assertFalse(any(action != 'heartbeat' for action, _ in client.commands))

    def test_gripper_pair_preflight_prevents_partial_closure(self):
        budgets = {side: copy.deepcopy(robot.backend.guard.snapshot())
                   for side, robot in self.robots.items()}
        with self.assertRaisesRegex(ValueError, 'right gripper proposal rejected before execution') as error:
            self.robot.execute('set_gripper', {'positions': {'left': .86, 'right': 1.}, 'note': 'Fixture'})
        self.assertNotIn('Session fault latched', str(error.exception))
        self.assertIn('next absolute opening must be within', str(error.exception))
        for client in self.clients.values():
            self.assertFalse(any(action == 'target' for action, _ in client.commands))
        for side, robot in self.robots.items():
            self.assertEqual(robot.backend.guard.snapshot(), budgets[side])
            self.assertIsNone(robot.backend.fault)
            self.assertFalse(robot.backend.consumed)
        result = self.robot.execute('set_gripper', {
            'positions': {'left': .89, 'right': .89}, 'note': 'Smaller opening after rejection'})
        self.assertEqual(set(result['arms']), set(ARMS))
        self.assertIsNone(self.robot.fault)

    def test_paired_grippers_use_respective_endpoints(self):
        result = self.robot.execute('set_gripper', {'positions': {'left': .86, 'right': .87}, 'note': 'Fixture'})
        for side in ARMS:
            expected = .1 + {'left': .86, 'right': .87}[side] * 4.8
            self.assertAlmostEqual(result['arms'][side]['submitted_gripper_raw'], expected)
        self.assertFalse(result['grasp_verified'])

    def test_dispatch_failure_latches_pair_and_stops_both(self):
        def failure(plan, *, dispatch_barrier):
            dispatch_barrier.wait(timeout=1)
            raise RuntimeError('right transport failed')
        with patch.object(self.robots['right'].backend, 'execute_trajectory', side_effect=failure):
            with self.assertRaisesRegex(R5ExecutionFault, 'right transport failed'):
                self.robot.execute('move_to', {'target': {side: self.target(side) for side in ARMS},
                                               'note': 'Fixture'})
        for client in self.clients.values():
            self.assertFalse(client.current['enabled'])
        with self.assertRaises(R5ExecutionFault):
            self.robot.renew_session()

    def test_context_and_validator_use_bimanual_schema(self):
        context = self.robot.context('Pick up ball and cola')
        self.assertIn('physical right R5 on can1', context.instructions)
        self.assertNotIn('Only one arm is controlled', context.instructions)
        self.assertNotIn('calibrated Gemini', context.instructions)
        provider = MagicMock()
        provider.decide.return_value = {'name': 'move_to', 'arguments': {
            'target': {side: self.target(side) for side in ARMS}, 'note': 'Fixture'}}
        result = CartesianAgent(provider, self.robot.catalog, ARMS).decide(None)
        self.assertIn('right', result['arguments']['target'])

    def test_place_task_completion_requires_supported_release(self):
        context = self.robot.context('Put the bottle on the support, return it, then place the ball')
        self.assertNotIn('done requires BOTH assigned objects', context.instructions)
        self.assertIn('observe stability after release', context.instructions)
        self.assertIn('Follow the current task order', context.instructions)

    @patch('policy_adapter.time.sleep')
    def test_original_loop_observes_both_arms_and_keeps_context_across_segments(self, sleep):
        from gpt_policy.recording.trace import RunRecorder
        left, right = DualCameraTests().clients()
        cameras = R5DualCameras(left, right)
        agent = MagicMock()
        agent.decide.side_effect = [
            {'name': 'check_path', 'arguments': {'poses': [{side: self.target(side) for side in ARMS}],
                                                'note': 'Fixture'}},
            {'name': 'done', 'arguments': {'summary': 'Fixture, no physical grasp', 'hindsight': ''}},
        ]
        runtime = SimpleNamespace(max_decisions=1, interface='can0', right_interface='can1',
                                  camera_mode='both', policy_interface='cartesian')
        request = SimpleNamespace(instruction='Pick up both objects', content=())
        supervisor = SimpleNamespace(robot=self.robot, check=self.robot.check, close=lambda: None)
        with tempfile.TemporaryDirectory() as directory:
            recorder = RunRecorder(Path(directory)/'run', {'fixture': True})
            try:
                recorder.segment = 1
                self.assertEqual(run_r5_policy(runtime, request, self.robot, cameras, agent, recorder,
                    supervisor=supervisor, display=MagicMock()), 'budget_exhausted')
                self.robot.renew_session()
                recorder.segment = 2
                self.assertEqual(run_r5_policy(runtime, request, self.robot, cameras, agent, recorder,
                    supervisor=supervisor, display=MagicMock(), start_agent=False), 'completed')
                agent.start.assert_called_once()
                turn = agent.decide.call_args.args[0]
                payload = json.loads(turn.observation)
                self.assertEqual(set(payload['state']), set(ARMS))
                for side in ARMS:
                    self.assertEqual(len(payload['state'][side]['joint_positions_deg']), 6)
                    self.assertEqual(len(payload['state'][side]['gripper_next_opening_bounds']), 2)
                self.assertIn('host_continuation', payload)
                self.assertEqual(len(list(recorder.frames.glob('*.jpg'))), 6)
            finally:
                recorder.close('unreviewed')


class DualCameraTests(unittest.TestCase):
    def clients(self):
        class CameraClient(FakeWorkbench):
            def __init__(self, side):
                super().__init__()
                self.arm = side
                self.device_prefix = side

            def camera(self, key):
                image, sequence, device = super().camera(key)
                return image, sequence, self.device_prefix + device
        return CameraClient('left'), CameraClient('right')

    @patch('policy_adapter.time.sleep')
    def test_three_views_and_mislabeled_device_failure(self, sleep):
        left, right = self.clients()
        cameras = R5DualCameras(left, right)
        images = cameras.snapshot()
        self.assertEqual(set(images), {'left', 'right', 'top'})
        self.assertNotIn('external', right.calls)
        descriptions = {item['name']: item for item in cameras.describe(images)}
        self.assertEqual(descriptions['right']['role'], 'wrist RGB')
        self.assertNotIn('ball_detection', descriptions['right'])
        right.device_prefix = 'left'
        with self.assertRaisesRegex(ValueError, 'duplicated or changed'):
            cameras.snapshot()
        right.device_prefix = 'right'
        with self.assertRaises(RuntimeError):
            cameras.snapshot()

    def test_reversed_clients_rejected(self):
        left, right = self.clients()
        with self.assertRaises(ValueError):
            R5DualCameras(right, left)


class PairedProxyTests(unittest.TestCase):
    def setUp(self):
        self.server = object.__new__(RecordingWorkbench)
        self.server.lock = threading.RLock()
        self.owner = 'dual-policy-' + 'a'*32
        self.server.paired_policy_client = self.owner
        self.server.recorder = MagicMock()
        self.server.recorder.status.return_value = {}
        self.server.arms = {side: MagicMock() for side in ARMS}
        self.states = {side: {'enabled': True, 'owner': self.owner, 'robot_status': 'ready',
                             'error_codes': [], 'joints_deg': [0]*6} for side in ARMS}
        self.server.arm_snapshot = lambda side: copy.deepcopy(self.states[side])

    def test_reserved_pair_heartbeats_are_allowed(self):
        for side in ARMS:
            self.server.arm_command(side, {'action': 'heartbeat', 'client': self.owner})
            self.server.arms[side].command.assert_called_once()

    def test_manual_client_stays_interlocked_and_jog_is_blocked(self):
        for data in ({'action': 'enable', 'client': 'manual'},
                     {'action': 'heartbeat', 'client': self.owner, 'jog': [1]*6},
                     {'action': 'connect', 'client': self.owner},
                     {'action': 'target', 'client': self.owner, 'joints_deg': [2]*6}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.server.arm_command('left', data)
        self.server.arms['left'].command.assert_not_called()

    def test_foreign_or_faulted_peer_blocks_paired_enable_but_not_stop(self):
        for update in ({'owner': 'manual'}, {'robot_status': 'fault'}, {'error_codes': [5]}):
            original = copy.deepcopy(self.states['right'])
            self.states['right'].update(update)
            with self.assertRaises(ValueError):
                self.server.arm_command('left', {'action': 'enable', 'client': self.owner})
            self.server.arm_command('left', {'action': 'stop', 'client': 'manual'})
            self.states['right'] = original


if __name__ == '__main__':
    unittest.main()
