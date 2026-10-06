import copy
from contextlib import nullcontext
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from review_telemetry import ReviewTimer, review_packet
from r5_policy_backend import R5ExecutionFault, R5PoweredHoldFault


def arm_state(side='left'):
    return {
        'observation_id': side+'-fresh', 'tcp_command_xyzquat': [0., 0., .2, 0., 0., 0., 1.],
        'tcp_xyzquat': [0., 0., .199, 0., 0., 0., 1.],
        'gripper_command_normalized': .9, 'gripper_next_opening_bounds': [.68, .92],
        'raw_state': dict(robot_status='ready', enabled=True, moving=False,
                          control_state='holding', owner='test-owner', error_codes=[],
                          policy_trajectory_active=False, joints_deg=[.2]*6, command_deg=[0.]*6),
        'motion_budget': {'accepted_proposals': 3, 'proposed_joint_travel_deg': 11.,
                          'proposed_gripper_travel_raw': .4,
                          'limits': {'session_proposals': 20,
                                     'session_joint_travel_deg': 120.,
                                     'session_gripper_travel_raw': 5.}},
    }


class ReviewTelemetryTests(unittest.TestCase):
    def test_monotonic_clock_separates_input_wait_from_command_wall_time(self):
        now = [100.]
        timer = ReviewTimer(lambda: now[0])
        timer.ready()
        now[0] += 14.
        started = timer.begin('move_to')
        self.assertEqual(started['input_wait_before_s'], 14.)
        now[0] += 3.5
        result = timer.finish('completed')
        self.assertEqual(result['command_wall_s'], 3.5)
        self.assertEqual(result['totals']['input_wait_before_commands_s'], 14.)
        now[0] += 5.
        timer.begin('invalid')
        now[0] += .1
        rejected = timer.finish('rejected')
        self.assertEqual(rejected['outcome'], 'rejected')
        self.assertEqual(timer.summary()['input_wait_before_commands_s'], 19.)
        self.assertAlmostEqual(timer.summary()['completed_command_wall_s'], 3.6)
        now[0] += 1000.
        self.assertEqual(timer.summary()['input_wait_before_commands_s'], 19.)

    def test_nested_timing_is_rejected_without_overwriting_pending_command(self):
        timer = ReviewTimer(lambda: 1.)
        timer.begin('observe')
        with self.assertRaises(RuntimeError):
            timer.begin('renew')
        self.assertEqual(timer.finish('failed')['command'], 'observe')
        with self.assertRaises(RuntimeError):
            timer.finish('completed')

    def test_packet_preserves_measured_and_commanded_poses_and_budget(self):
        state = {'arms': {side: arm_state(side) for side in ('left', 'right')}}
        before = copy.deepcopy(state)
        initial = {side: {'joints_deg': [0.]*6} for side in state['arms']}
        packet = review_packet(state, {'top': '/run/123_top.jpg'}, 123, initial=initial)
        left = packet['arms']['left']
        self.assertNotEqual(left['tcp'], left['measured_tcp'])
        self.assertEqual(left['budget_remaining'],
                         {'actions': 17, 'joint_travel_deg': 109., 'gripper_travel_raw': 4.6})
        self.assertEqual(left['return_error_deg'], {'joints_deg': .2, 'command_deg': 0.})
        self.assertFalse(packet['physical_success_verified'])
        self.assertFalse(packet['collision_checked'])
        self.assertEqual(state, before)


class ReviewHostSmokeTests(unittest.TestCase):
    """Run the actual stdin dispatch loop with fake hardware and cameras."""
    def run_host(self, commands, *, motion_fault=False, working_arm=None, feedback=None,
                 return_handler=None, arrival_hold=False):
        spec = importlib.util.spec_from_file_location('review_host_under_test',
            Path(__file__).resolve().parents[1]/'tools/held_policy_review.py')
        host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(host)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root/'run'
            for side in ('left', 'right'):
                (root/f'r5_{side}_image_grasp_20260927_profile.json').write_text('{}')
            clients = {}
            def client_factory(url, side):
                client = Mock()
                client.arm = side
                client.state.return_value = dict(robot_status='ready', enabled=False,
                                                  moving=False, owner=None, joints_deg=[0.]*6)
                client.request.return_value = {'paired_policy_client': 'test-owner'}
                clients[side] = client
                return client
            def prepare(client, *args, **kwargs):
                client.state.return_value = arm_state(client.arm)['raw_state']
            cameras = Mock()
            cameras.snapshot.return_value = {k: SimpleNamespace(data=b'fake-jpeg')
                                               for k in ('top', 'left', 'right')}
            robot = Mock()
            robot.operation_lock = nullcontext()
            robot.robots = {side: Mock() for side in ('left', 'right')}
            for side, arm in robot.robots.items():
                arm.backend.last_execution_feedback = copy.deepcopy((feedback or {}).get(side))
                arm.backend.fault_hold_failure = None
                arm.backend._read.return_value = arm_state(side)['raw_state']
                arm.backend.state.return_value = arm_state(side)
                arm.renew_session.return_value = {'renewed': True}
            robot.state.side_effect = lambda: {'arms': {s: arm_state(s) for s in ('left', 'right')}}
            robot.renew_session.return_value = {'renewed': True}
            robot.execute.return_value = {'arms': {}, 'trajectories': {}, 'collision_checked': False}
            if motion_fault:
                fault = (motion_fault if isinstance(motion_fault, BaseException)
                         else RuntimeError('simulated execution failure'))
                robot.execute.side_effect = fault
            supervisor = Mock()
            individual = Mock()
            individual.diagnostics.return_value = {'fault': None, 'stall': None}
            command_queue = Mock()
            command_queue.get.side_effect = [*commands, KeyboardInterrupt('test-end')]
            argv = ['held_policy_review.py', '--prepare-idle', '--output', str(output),
                    '--paired-client', 'test-owner']
            if working_arm:
                argv += ['--working-arm', working_arm]
            if arrival_hold:
                argv += ['--retain-settle-fault-hold']
                robot.retain_stationary_faults.return_value = {
                    side: arm_state(side)['raw_state'] for side in ('left', 'right')}
            quarantine = host.quarantine_arrival_fault
            def run_quarantine(*args):
                return quarantine(*args, sleep=Mock(
                    side_effect=R5ExecutionFault('fixture quarantine health failure')))
            sleep_context = (patch.object(host, 'quarantine_arrival_fault', side_effect=run_quarantine)
                             if arrival_hold else nullcontext())
            return_factory = (host.ReviewedReturn if return_handler is None
                              else Mock(return_value=return_handler))
            with patch.multiple(host, ROOT=root,
                    ArmWorkbenchClient=client_factory, prepare_hold=prepare,
                    R5DualCameras=Mock(), SupervisedCameras=Mock(return_value=cameras),
                    CartesianBackend=Mock(side_effect=list(robot.robots.values())),
                    R5PolicyBackend=Mock(), R5PolicySupervisor=Mock(return_value=individual), return_plan=Mock(return_value=None),
                    ReviewedReturn=return_factory,
                    DualCartesianBackend=Mock(return_value=robot),
                    DualSupervisor=Mock(return_value=supervisor)), \
                 patch.object(host.queue, 'Queue', return_value=command_queue), \
                 patch.object(host.threading, 'Thread'), \
                 patch.object(host.sys, 'argv', argv), patch('sys.stdout', new_callable=io.StringIO), sleep_context:
                expected = R5ExecutionFault if arrival_hold else type(fault) if motion_fault else KeyboardInterrupt
                with self.assertRaises(expected):
                    host.main()
            events = [json.loads(x) for x in (output/'events.jsonl').read_text().splitlines()]
            packet = json.loads((output/'review_packet.json').read_text())
            timing = json.loads((output/'review_timing.json').read_text())
            self.assertTrue(all(Path(p).is_file() for p in packet['images'].values()))
            self.assertFalse((output/'review_packet.tmp').exists())
            supervisor.close.assert_called_once()
            cameras.close.assert_called_once()
            return events, packet, timing, robot

    def test_arrival_fault_enters_quarantine_without_dispatching_queued_action(self):
        command = json.dumps({'tool': 'move_to', 'arguments': {
            'target': {'left': {'pose_xyzquat': [0, 0, .2, 0, 0, 0, 1]}, 'right': None},
            'note': 'Offline left-only arrival fault'}})
        events, _, timing, robot = self.run_host(
            [command, 'renew', command], working_arm='left', arrival_hold=True,
            motion_fault=R5PoweredHoldFault('Action did not settle'))
        self.assertEqual(timing['outcome'], 'failed')
        self.assertEqual(events[-2]['event'], 'arrival_fault_hold')
        self.assertEqual(events[-1]['event'], 'arrival_fault_hold_ended')
        self.assertTrue(events[-2]['new_commands_blocked'])
        self.assertFalse(events[-2]['task_completion_verified'])
        robot.execute.assert_called_once()
        robot.renew_session.assert_not_called()
        robot.retain_stationary_faults.assert_called_once()

    def test_first_command_observe_rejection_renew_and_motion_complete(self):
        command = json.dumps({'tool': 'move_to', 'arguments': {'target': {}, 'note': 'test'}})
        events, packet, timing, robot = self.run_host(['observe', '{}', 'renew', command])
        finished = [e for e in events if e['event']=='review_command_finished']
        self.assertEqual([e['outcome'] for e in finished],
                         ['completed', 'rejected', 'completed', 'completed'])
        self.assertEqual(timing['totals']['completed_commands'], 4)
        self.assertEqual(packet['arms']['left']['observation_id'], 'left-fresh')
        robot.execute.assert_called_once()
        robot.renew_session.assert_called_once()

    def test_execution_fault_is_timed_and_propagates_to_existing_cleanup(self):
        command = json.dumps({'tool': 'move_to', 'arguments': {}})
        events, packet, timing, robot = self.run_host([command], motion_fault=True)
        self.assertEqual(timing['outcome'], 'failed')
        self.assertEqual(events[-1]['event'], 'host_terminated')
        self.assertEqual(events[-1]['exception_type'], 'RuntimeError')
        robot.execute.assert_called_once()

    def test_motion_fault_persists_feedback_and_still_terminates(self):
        command = json.dumps({'tool': 'move_to', 'arguments': {}})
        feedback = {'left': {'target': {'joints_deg': [1.]*6},
                            'samples': [{'at_s': 100., 'joints_deg': [.5]*6,
                                         'checks': {'arm_ok': False, 'command_ok': True,
                                                    'grip_ok': True}}]},
                    'right': None}
        events, packet, timing, robot = self.run_host(
            [command], motion_fault=R5ExecutionFault('Action did not settle'), feedback=feedback)
        self.assertEqual(timing['outcome'], 'failed')
        self.assertEqual(events[-1]['event'], 'host_terminated')
        self.assertEqual(events[-1]['exception_type'], 'R5ExecutionFault')
        self.assertEqual(events[-1]['last_execution_feedback'], feedback)
        self.assertFalse(any(e['event'] == 'host_quarantined' for e in events))
        self.assertFalse(events[-1]['task_completion_verified'])
        robot.execute.assert_called_once()

    def test_single_arm_mode_switch_renew_and_return_in_real_dispatch_loop(self):
        def motion(side):
            return json.dumps({'tool': 'move_to', 'arguments': {
                'target': {s: {} if s==side else None for s in ('left', 'right')}, 'note': 'test'}})
        commands = [motion('left'), 'open-empty-left', motion('right'), 'select-left',
                    'renew', motion('left'), 'return-working-step']
        events, packet, timing, robot = self.run_host(commands, working_arm='right')
        outcomes = [e['outcome'] for e in events if e['event']=='review_command_finished']
        self.assertEqual(outcomes, ['rejected', 'rejected', 'completed', 'completed',
                                    'completed', 'completed', 'completed'])
        self.assertEqual(robot.execute.call_count, 2)
        self.assertEqual(packet['working_arm'], 'left')
        self.assertTrue(any(e['event']=='left_return_complete' for e in events))
        robot.renew_session.assert_not_called()
        robot.robots['left'].renew_session.assert_called_once()
        robot.robots['right'].renew_session.assert_not_called()

    def test_reviewed_return_dispatches_one_selected_segment_and_records_it(self):
        review = {'observation_id': 'left-fresh', 'empty_gripper': True, 'path_clear': True,
                  'recording_active': True, 'note': 'Reviewed fixture'}
        handler = Mock()
        handler.step.return_value = {'arm': 'left', 'at_initial': False, 'control_state': 'holding'}
        events, packet, timing, robot = self.run_host(
            ['reviewed-return-step '+json.dumps(review)], working_arm='left', return_handler=handler)
        handler.step.assert_called_once_with(robot, 'left', review)
        self.assertEqual(timing['outcome'], 'completed')
        recorded = [e for e in events if e['event'] == 'reviewed_return_step']
        self.assertEqual(len(recorded), 1)
        self.assertFalse(recorded[0]['at_initial'])
        robot.execute.assert_not_called()

    def test_reviewed_return_needs_working_arm_and_failure_uses_original_cleanup(self):
        command = 'reviewed-return-step {}'
        handler = Mock()
        events, packet, timing, robot = self.run_host([command], return_handler=handler)
        self.assertEqual(timing['outcome'], 'rejected')
        handler.step.assert_not_called()
        fault = R5ExecutionFault('Return feedback lost')
        handler.step.side_effect = fault
        events, packet, timing, robot = self.run_host(
            [command], working_arm='left', return_handler=handler, motion_fault=fault)
        self.assertEqual(timing['outcome'], 'failed')
        self.assertEqual(events[-1]['event'], 'host_terminated')
        handler.step.assert_called_once()


if __name__ == '__main__':
    unittest.main()
