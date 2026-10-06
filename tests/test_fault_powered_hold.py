import copy
import math
import time
import unittest
from unittest.mock import Mock, patch

from fault_powered_hold import require_stationary_arrival
from r5_policy_backend import R5PolicyBackend, R5ExecutionFault, R5PoweredHoldFault
from r5_policy_supervisor import R5PolicySupervisor
from r5_dual_policy import DualCartesianBackend, DualSupervisor
from r5_cartesian import CartesianBackend
from policy_trajectory import PolicyTrajectory
from test_r5_policy_backend import Workbench, Clock
from test_r5_cartesian import fixture_profile, TimedWorkbench


class FaultHoldTests(unittest.TestCase):
    def make_arm(self, side='left', enabled=True):
        clock, client = Clock(), Workbench()
        client.arm = side
        client.current.update(velocity_deg=[0.]*6, policy_trajectory_active=False,
                              policy_trajectory_protocol=PolicyTrajectory.protocol)
        vision = Mock()
        low = R5PolicyBackend(client, vision, clock=clock, sleep=clock.sleep,
                              retain_settle_fault_hold=enabled)
        low.check()
        args = {'positions': low.state()['joint_positions_rad'][:],
                'observation_id': low.observation['observation_id'], 'note': 'Offline stalled joint'}
        args['positions'][0] += math.radians(1.)
        client.stall = True
        return low, client, clock, vision, args

    def fault(self, low, args):
        with self.assertRaises(R5PoweredHoldFault):
            low.execute('move_joints', args)

    def test_opt_in_stable_failure_latches_task_without_disabling(self):
        low, client, clock, vision, args = self.make_arm()
        self.fault(low, args)
        self.assertTrue(client.current['enabled'])
        self.assertEqual(low.fault_hold.phase, 'holding')
        self.assertIn('Action did not settle', low.fault)
        self.assertEqual(low.guard.failure, low.fault)
        self.assertEqual([a for a, _ in client.commands if a != 'heartbeat'],
                         ['resume', 'target', 'pause_hold'])
        self.assertEqual(client.current['gripper_command_raw'], 4.3)
        before = copy.deepcopy(low.guard.snapshot())
        for _ in range(10):
            clock.sleep(.05)
            low.supervise()
        self.assertEqual(low.guard.snapshot(), before)
        mark = len(client.commands)
        for operation in (low.check, low.state, low.renew_session,
                          lambda: low.finish('done'),
                          lambda: low._command('target', gripper_raw=4.),
                          lambda: low.execute('move_joints', args)):
            with self.assertRaises((ValueError, R5ExecutionFault)):
                operation()
        self.assertEqual(len(client.commands), mark)
        self.assertTrue(client.current['enabled'])

    def test_default_keeps_previous_failure_response(self):
        low, client, _, _, args = self.make_arm(enabled=False)
        with self.assertRaises(R5ExecutionFault):
            low.execute('move_joints', args)
        self.assertFalse(client.current['enabled'])
        self.assertIsNone(low.fault_hold)

    def test_unqualified_stationarity_or_gripper_never_retains_hold(self):
        cases = [dict(velocity_deg=[1.]*6), dict(velocity_deg=[float('nan')]*6),
                 dict(moving=True), dict(policy_trajectory_active=True),
                 dict(gripper_target_raw=4.4)]
        for changes in cases:
            with self.subTest(changes=changes):
                low, client, _, _, args = self.make_arm()
                client.current.update(changes)
                with self.assertRaises(R5ExecutionFault):
                    low.execute('move_joints', args)
                # An observation drift rejection is intentionally non-actuating.
                if low.fault is not None:
                    self.assertFalse(client.current['enabled'])
                self.assertIsNone(low.fault_hold)
                self.assertNotIn('pause_hold', [a for a, _ in client.commands])

    def test_hardware_camera_and_transport_faults_do_not_take_hold_path(self):
        for fault in ('camera', 'rx', 'worker', 'transport', 'tracking'):
            with self.subTest(fault=fault):
                low, client, _, vision, args = self.make_arm()
                if fault == 'camera':
                    vision.side_effect = RuntimeError('Camera offline')
                elif fault == 'transport':
                    client.timeout = 'target'
                else:
                    original = client.command
                    def command(action, _fault=fault, **fields):
                        result = original(action, **fields)
                        if action == 'target':
                            client.current.update({'rx': {'rx_age_ms': 151},
                                'worker': {'robot_status': 'fault'},
                                'tracking': {'tracking_limited': True}}[_fault])
                        return result
                    client.command = command
                with self.assertRaises(R5ExecutionFault):
                    low.execute('move_joints', args)
                self.assertIsNone(low.fault_hold)
                self.assertFalse(client.current['enabled'])
                self.assertNotIn('pause_hold', [a for a, _ in client.commands])

    def test_gripper_stall_is_not_a_joint_arrival_failure(self):
        low, client, _, _, _ = self.make_arm()
        args = {'observation_id': low.observation['observation_id'], 'gripper_raw': 3.5,
                'note': 'Offline gripper stall'}
        with self.assertRaises(R5ExecutionFault):
            low.execute('set_gripper', args)
        self.assertIsNone(low.fault_hold)
        self.assertFalse(client.current['enabled'])

    def test_hold_failure_or_lost_ack_falls_back_and_keeps_original_reason(self):
        for failure in ('lost_ack', 'never_holds'):
            with self.subTest(failure=failure):
                low, client, _, _, args = self.make_arm()
                if failure == 'lost_ack':
                    client.timeout = 'pause_hold'
                else:
                    original = client.command
                    def command(action, **fields):
                        result = original(action, **fields)
                        if action == 'pause_hold':
                            client.current['control_state'] = 'pausing'
                        return result
                    client.command = command
                with self.assertRaises(R5ExecutionFault):
                    low.execute('move_joints', args)
                self.assertFalse(client.current['enabled'])
                self.assertIn('Action did not settle', low.fault)
                self.assertIsNotNone(low.fault_hold_failure)

    def test_later_hold_health_failure_stops_and_does_not_reset_fault(self):
        cases = [dict(rx_age_ms=151), dict(error_codes=[1]), dict(tracking_limited=True),
                 dict(hold_target_deg=[0.]*6), dict(gripper_command_raw=4.0),
                 dict(control_state='active'), dict(velocity_deg=[1.]*6)]
        for changes in cases:
            with self.subTest(changes=changes):
                low, client, _, _, args = self.make_arm()
                self.fault(low, args)
                reason = low.fault
                client.current.update(changes)
                with self.assertRaises(R5ExecutionFault):
                    low.supervise()
                self.assertFalse(client.current['enabled'])
                self.assertEqual(low.fault, reason)
                self.assertIsNone(low.fault_hold)

    def test_owner_loss_never_sends_to_new_owner(self):
        low, client, _, _, args = self.make_arm()
        self.fault(low, args)
        mark = len(client.commands)
        client.current['owner'] = 'someone-else'
        with self.assertRaises(R5ExecutionFault):
            low.supervise()
        self.assertEqual(len(client.commands), mark)

    def test_abort_and_watchdog_close_still_stop_a_fault_hold(self):
        low, client, _, _, args = self.make_arm()
        self.fault(low, args)
        R5PolicySupervisor(low).close()
        self.assertFalse(client.current['enabled'])
        self.assertEqual(sum(a == 'stop' for a, _ in client.commands), 1)

    def test_watchdog_continues_and_handles_transition_race(self):
        low, client, _, _, args = self.make_arm()
        sup = R5PolicySupervisor(low)
        self.fault(low, args)
        # Force check() dispatch just before the latch becomes visible.
        with patch('fault_powered_hold.FaultHold', type('OtherHold', (), {})):
            sup._check_robot()
        sup.start()
        try:
            mark = len(client.commands)
            time.sleep(.16)
            sup.check()
            self.assertGreater(len(client.commands), mark)
            self.assertTrue(sup.thread.is_alive())
        finally:
            sup.close()

    def test_original_heartbeat_deadline_and_camera_check_still_apply(self):
        for failure in ('deadline', 'camera'):
            with self.subTest(failure=failure):
                low, client, _, vision, args = self.make_arm()
                self.fault(low, args)
                sup = R5PolicySupervisor(low)
                sup.start()
                try:
                    with self.assertRaises(R5ExecutionFault):
                        if failure == 'deadline':
                            sup.last_check = time.monotonic()-.31
                            sup.check()
                        else:
                            vision.side_effect = R5ExecutionFault('Camera unavailable')
                            low.supervise()
                    self.assertFalse(client.current['enabled'])
                    self.assertIsNone(low.fault_hold)
                    self.assertIn('Action did not settle', low.fault)
                finally:
                    sup.close()

    def test_timed_cartesian_arrival_uses_same_latched_path(self):
        client, clock = TimedWorkbench(), Clock()
        client.arm = 'left'
        low = R5PolicyBackend(client, Mock(), clock=clock, sleep=clock.sleep,
                              retain_settle_fault_hold=True)
        arm = CartesianBackend(low, fixture_profile(), 'both', 'image_grasp')
        pose = arm.state()['tcp_command_xyzquat'][:]
        pose[2] += .003
        plan = arm.plan([{'pose_xyzquat': pose}], 'Offline Cartesian stall')
        client.stall = True
        with self.assertRaises(R5PoweredHoldFault):
            low.execute_trajectory(plan)
        self.assertTrue(client.current['enabled'])
        self.assertIsNotNone(low.fault_hold)
        self.assertIn('policy_trajectory', [a for a, _ in client.commands])
        self.assertNotIn('stop', [a for a, _ in client.commands])

    def test_stationary_history_rejects_gaps_drift_and_wrong_command(self):
        low, client, clock, _, args = self.make_arm()
        self.fault(low, args)
        saved = copy.deepcopy(low.last_execution_feedback)
        for failure in ('old', 'gap', 'drift', 'target', 'gripper'):
            with self.subTest(failure=failure):
                low.last_execution_feedback = copy.deepcopy(saved)
                trace = low.last_execution_feedback
                if failure == 'old':
                    for sample in trace['samples']:
                        sample['at_s'] -= 1
                elif failure == 'gap':
                    trace['samples'] = trace['samples'][:-4] + trace['samples'][-1:]
                elif failure == 'drift':
                    trace['samples'][-1]['joints_deg'][0] += .2
                elif failure == 'target':
                    trace['samples'][-1]['command_deg'][0] += .2
                else:
                    trace['samples'][-1]['checks']['grip_ok'] = False
                with self.assertRaises(R5ExecutionFault):
                    require_stationary_arrival(low, client.state())

    def make_pair(self):
        fixtures = {s: self.make_arm(s) for s in ('left', 'right')}
        robots = {s: CartesianBackend(v[0], fixture_profile(), 'both', 'image_grasp')
                  for s, v in fixtures.items()}
        return DualCartesianBackend(robots, Mock()), fixtures

    def test_pair_keeps_stationary_companion_and_rejects_new_tasks(self):
        pair, f = self.make_pair()
        low, client, _, _, args = f['left']
        with self.assertRaises(R5PoweredHoldFault):
            pair._parallel({'left': lambda barrier: low.execute('move_joints', args, dispatch_barrier=barrier)})
        self.assertTrue(pair.fault_hold)
        for side in f:
            self.assertTrue(f[side][1].current['enabled'])
            self.assertIsNotNone(f[side][0].fault_hold)
        with self.assertRaises(R5PoweredHoldFault):
            pair.renew_session()
        with self.assertRaises(R5PoweredHoldFault):
            pair.check()
        self.assertNotIn('pause_hold', [a for a, _ in f['right'][1].commands])

    def test_unsafe_companion_aborts_both(self):
        for failure in ('busy', 'moving', 'rx'):
            with self.subTest(failure=failure):
                pair, f = self.make_pair()
                self.fault(f['left'][0], f['left'][4])
                if failure == 'busy':
                    f['right'][0].busy = True
                else:
                    f['right'][1].current.update({'moving': {'moving': True}, 'rx': {'rx_age_ms': 151}}[failure])
                with self.assertRaises(R5ExecutionFault):
                    pair.retain_stationary_faults('Offline arrival fault')
                self.assertTrue(all(not v[1].current['enabled'] for v in f.values()))

    def test_fault_hold_mode_rejects_simultaneous_targets_before_dispatch(self):
        pair, f = self.make_pair()
        pair.state()
        with self.assertRaisesRegex(ValueError, 'one moving arm'):
            pair.execute('set_gripper', {'positions': {'left': .86, 'right': .86}, 'note': 'Both'})
        self.assertTrue(all(not any(a in ('target', 'resume') for a, _ in v[1].commands)
                            for v in f.values()))

    def test_dual_watchdog_propagates_hold_health_failure_to_both(self):
        pair, f = self.make_pair()
        self.fault(f['left'][0], f['left'][4])
        pair.retain_stationary_faults(f['left'][0].fault)
        individual = {s: R5PolicySupervisor(arm) for s, arm in pair.robots.items()}
        supervisor = DualSupervisor(pair, individual)
        try:
            for worker in individual.values():
                worker.start()
            supervisor.start()
            f['right'][1].current['rx_age_ms'] = 151
            self.assertTrue(individual['right'].done.wait(1.))
            supervisor.thread.join(1.)
            self.assertFalse(supervisor.thread.is_alive())
            self.assertTrue(all(not v[1].current['enabled'] for v in f.values()))
        finally:
            supervisor.close()

    def test_quarantine_does_not_return_to_dispatch_and_logs_health_loss(self):
        from tools.held_policy_review import quarantine_arrival_fault
        pair, f = self.make_pair()
        self.fault(f['left'][0], f['left'][4])
        log, supervisor = Mock(), Mock()
        def lose_health(_):
            f['left'][1].current['rx_age_ms'] = 151
        with self.assertRaises(R5ExecutionFault):
            quarantine_arrival_fault(pair, supervisor, R5PoweredHoldFault(f['left'][0].fault),
                                     log, sleep=lose_health)
        self.assertEqual([c.args[0] for c in log.call_args_list],
                         ['arrival_fault_hold', 'arrival_fault_hold_ended'])
        self.assertTrue(log.call_args_list[0].args[1]['new_commands_blocked'])
        self.assertFalse(log.call_args_list[0].args[1]['task_completion_verified'])


if __name__ == '__main__':
    unittest.main()
