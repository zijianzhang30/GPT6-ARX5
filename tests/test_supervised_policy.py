import unittest
import queue
from unittest.mock import Mock

from supervised_policy import (close_host, guided_budget_renewal, open_empty_gripper,
                               prepare_hold, check_tracking_contract,
                               automatic_budget_renewal, queued_operator_command)
from supervised_policy import wait_for_operator_start
from test_gripper_check import Client
from test_r5_policy_backend import Clock


class PreparationTests(unittest.TestCase):
    def test_service_and_policy_must_use_matching_tracking_tolerances(self):
        valid = {'policy_tracking_limits_deg': {'settle': 2.5, 'hold': 3., 'trajectory': 3.},
                 'policy_step_limits_deg': {'joint': 24., 'norm': 33.}}
        check_tracking_contract(valid)
        for limits in (None, {'joint': 12., 'norm': 16.5}, {'joint': 6., 'norm': 8.25}):
            with self.assertRaisesRegex(ValueError, 'step limits differ'):
                check_tracking_contract({**valid, 'policy_step_limits_deg': limits})
        for state in ({}, {'policy_tracking_limits_deg': {'settle': 1., 'hold': 1., 'trajectory': 3.}}):
            with self.assertRaisesRegex(ValueError, 'tolerances differ'):
                check_tracking_contract(state)

    def setUp(self):
        self.client = Client()
        self.client.current.update(policy_execution_scope='supervised_trial', policy_execution_available=False)
        self.clock = Clock()
        self.cameras = Mock()
        self.log = Mock()
        original = self.client.command

        def command(action, **fields):
            if self.clock.now >= 104 and self.client.current.get('control_state') == 'holding':
                self.client.current['policy_execution_available'] = True
            return original(action, **fields)

        self.client.command = command

    def run_prepare(self):
        return prepare_hold(self.client, self.cameras, self.log,
                            clock=self.clock, sleep=self.clock.sleep)

    def test_qualifies_with_heartbeats_without_movement_target(self):
        state = self.run_prepare()
        self.assertTrue(state['policy_execution_available'])
        self.assertEqual(state['control_state'], 'holding')
        self.assertFalse(any(n in ('target', 'stop') for n, _ in self.client.commands))
        self.assertGreater(sum(n == 'heartbeat' for n, _ in self.client.commands), 60)

    def test_disabled_scope_is_rejected_before_enable(self):
        self.client.current['policy_execution_scope'] = 'disabled'
        with self.assertRaisesRegex(ValueError, 'supervised'):
            self.run_prepare()
        self.assertEqual(self.client.commands, [])

    def test_commissioning_speed_is_set_before_enable_and_hold(self):
        state = prepare_hold(self.client, self.cameras, self.log, speed=.1,
                             clock=self.clock, sleep=self.clock.sleep)
        self.assertEqual(state['control_state'], 'holding')
        self.assertEqual(self.client.commands[0], ('settings', {'mode': 'joint', 'speed': .1}))
        self.assertEqual(sum(n == 'settings' for n, _ in self.client.commands), 1)

    def test_invalid_speed_cannot_enable_the_arm(self):
        for speed in (0, -.1, .31, True, float('nan')):
            with self.subTest(speed=speed), self.assertRaisesRegex(ValueError, 'speed'):
                prepare_hold(self.client, self.cameras, self.log, speed=speed)
        self.assertEqual(self.client.commands, [])

    def test_enable_drift_stops_and_never_runs_model_or_target(self):
        self.client.fault = 'enable_drift'
        with self.assertRaisesRegex(ValueError, 'displacement'):
            self.run_prepare()
        self.assertEqual(self.client.commands[-1][0], 'stop')
        self.assertFalse(any(n == 'target' for n, _ in self.client.commands))

    def enable_with_gripper_recoil(self, recoil):
        original = self.client.command

        def command(action, **fields):
            result = original(action, **fields)
            if action == 'enable':
                self.client.current['gripper_raw'] -= recoil
            return result
        self.client.command = command

    def test_reviewed_empty_gripper_recoil_can_qualify_without_joint_targets(self):
        self.enable_with_gripper_recoil(.036)
        result = prepare_hold(self.client, self.cameras, self.log, enable_gripper_drift_raw=.05,
                              clock=self.clock, sleep=self.clock.sleep)
        self.assertTrue(result['policy_execution_available'])
        self.assertFalse(any(name in ('target', 'stop') for name, _ in self.client.commands))

    def test_larger_gripper_recoil_still_stops(self):
        self.enable_with_gripper_recoil(.06)
        with self.assertRaisesRegex(ValueError, 'gripper=.*0.050000 raw'):
            prepare_hold(self.client, self.cameras, self.log, enable_gripper_drift_raw=.05,
                         clock=self.clock, sleep=self.clock.sleep)
        self.assertEqual(self.client.commands[-1][0], 'stop')

    def test_explicit_opening_preparation_uses_separate_small_gripper_steps(self):
        self.run_prepare()
        result = open_empty_gripper(self.client, self.cameras, 4.5, self.log,
                                    clock=self.clock, sleep=self.clock.sleep)
        targets = [f for n, f in self.client.commands if n == 'target']
        self.assertEqual(len(targets), 2)
        self.assertTrue(all(set(t) == {'gripper_raw'} for t in targets))
        self.assertAlmostEqual(targets[0]['gripper_raw'], 4.4)
        self.assertAlmostEqual(targets[1]['gripper_raw'], 4.5)
        self.assertEqual(result['control_state'], 'holding')

    def test_opening_preparation_rejects_closure_and_stalls(self):
        self.run_prepare()
        with self.assertRaisesRegex(ValueError, 'non-closing'):
            open_empty_gripper(self.client, self.cameras, 4.1, self.log,
                               clock=self.clock, sleep=self.clock.sleep)
        self.assertFalse(any(n == 'target' for n, _ in self.client.commands))
        self.client.fault = 'stall'
        with self.assertRaisesRegex(TimeoutError, 'stalled'):
            open_empty_gripper(self.client, self.cameras, 4.4, self.log,
                               clock=self.clock, sleep=self.clock.sleep)
        self.assertEqual(sum(n == 'target' for n, _ in self.client.commands), 1)

    def test_fast_opening_uses_larger_preparation_steps_without_scaling_endpoint(self):
        self.run_prepare()
        self.client.current.update(gripper_open_speed_multiplier=5.)
        result = open_empty_gripper(self.client, self.cameras, 4.8, self.log,
                                    clock=self.clock, sleep=self.clock.sleep)
        targets = [f for n, f in self.client.commands if n == 'target']
        self.assertEqual(targets, [{'gripper_raw': 4.8}])
        self.assertEqual(result['control_state'], 'holding')
        self.assertAlmostEqual(result['gripper_raw'], 4.7)

    def test_fast_opening_stall_and_unknown_profiles_still_rejected(self):
        self.run_prepare()
        for scale in (True, 2., 10., float('nan')):
            self.client.current['gripper_open_speed_multiplier'] = scale
            with self.subTest(scale=scale), self.assertRaisesRegex(ValueError, 'speed profile'):
                open_empty_gripper(self.client, self.cameras, 4.8, self.log,
                                   clock=self.clock, sleep=self.clock.sleep)
        self.assertFalse(any(n == 'target' for n, _ in self.client.commands))
        self.client.current['gripper_open_speed_multiplier'] = 5.
        self.client.fault = 'stall'
        with self.assertRaisesRegex(TimeoutError, 'stalled'):
            open_empty_gripper(self.client, self.cameras, 4.8, self.log,
                               clock=self.clock, sleep=self.clock.sleep)
        self.assertEqual(sum(n == 'target' for n, _ in self.client.commands), 1)

    def test_fast_preparation_reduces_waits_while_checking_ramped_feedback(self):
        durations, targets = {}, {}
        for scale in (1., 5.):
            clock = Clock()

            class RampedClient(Client):
                checked = 0
                updated_at = clock()

                def command(self, action, **fields):
                    submitted, measured = self.current['gripper_command_raw'], self.current['gripper_raw']
                    super().command(action, **fields)
                    if action == 'target':
                        self.current.update(gripper_command_raw=submitted, gripper_raw=measured)
                    if action == 'heartbeat':
                        self.checked += 1
                        command = min(self.current['gripper_target_raw'],
                                      submitted+.18*scale*(clock()-self.updated_at))
                        self.current.update(gripper_command_raw=command, gripper_raw=command-.1)
                    self.updated_at = clock()
                    return self.state()

            client = RampedClient()
            client.current.update(enabled=True, owner=client.client, control_state='holding',
                                  speed=.3, gripper_raw=.2, gripper_command_raw=.3,
                                  gripper_target_raw=.3, gripper_open_speed_multiplier=scale)
            began = clock()
            result = open_empty_gripper(client, Mock(), 4.8, Mock(), clock=clock, sleep=clock.sleep)
            durations[scale] = clock()-began
            targets[scale] = [f['gripper_raw'] for n, f in client.commands if n == 'target']
            self.assertGreater(client.checked, 100)
            self.assertEqual(result['control_state'], 'holding')
            self.assertAlmostEqual(result['gripper_raw'], 4.7)
        self.assertEqual(len(targets[5.]), 9)
        self.assertEqual(len(targets[1.]), 45)
        self.assertGreater(durations[1.]/durations[5.], 4.)
        self.assertLess(durations[1.]/durations[5.], 6.)

    def test_opening_preparation_accepts_stable_tiny_final_step_without_encoder_progress(self):
        self.run_prepare()
        self.client.current.update(gripper_command_raw=4.3978,
                                   gripper_target_raw=4.3978, gripper_raw=4.2978)
        original = self.client.command

        def command(action, **fields):
            old = self.client.state()
            result = original(action, **fields)
            if (action == 'target'
                    and fields['gripper_raw']-old['gripper_command_raw'] <= .01):
                self.client.current['gripper_raw'] = old['gripper_raw']
                result = self.client.state()
            return result

        self.client.command = command
        result = open_empty_gripper(self.client, self.cameras, 4.5, self.log,
                                    clock=self.clock, sleep=self.clock.sleep)
        self.assertEqual(result['control_state'], 'holding')
        self.assertAlmostEqual(result['gripper_command_raw'], 4.5)
        self.assertAlmostEqual(result['gripper_raw'], 4.3978)
        self.assertEqual(sum(n == 'target' for n, _ in self.client.commands), 2)


class StartGateTests(unittest.TestCase):
    def test_wait_maintains_health_without_actuation_and_requires_start(self):
        robot, log = Mock(), Mock()
        commands = queue.Queue()
        commands.put('continue')
        cycles = []

        def sleep(duration):
            cycles.append(duration)
            commands.put('start')

        self.assertTrue(wait_for_operator_start(robot, commands, log, sleep=sleep))
        self.assertEqual(cycles, [.05])
        self.assertGreaterEqual(robot.check.call_count, 3)
        self.assertTrue(all(call[0] == 'check' for call in robot.method_calls))

    def test_stop_wins_over_start_and_fault_cannot_start_motion(self):
        commands = queue.Queue()
        commands.put('start')
        commands.put('stop')
        self.assertFalse(wait_for_operator_start(Mock(), commands, Mock()))
        robot = Mock()
        robot.check.side_effect = RuntimeError('health fault')
        commands.put('start')
        with self.assertRaisesRegex(RuntimeError, 'health fault'):
            wait_for_operator_start(robot, commands, Mock())


class CleanupTests(unittest.TestCase):
    def test_provider_or_state_error_cannot_skip_other_cleanup(self):
        supervisor, client, cameras, agent, log = (Mock() for _ in range(5))
        supervisor.close.side_effect = RuntimeError('Fixture supervisor failure')
        client.state.side_effect = TimeoutError('Fixture state timeout')
        agent.close.side_effect = RuntimeError('Fixture provider failure')
        errors = close_host(supervisor, client, cameras, agent, log)
        self.assertEqual([e['resource'] for e in errors], ['supervisor', 'owned_control', 'agent'])
        cameras.close.assert_called_once()
        agent.close.assert_called_once()
        self.assertEqual(log.call_count, 3)

    def test_cleanup_stops_only_its_own_enabled_control(self):
        for owner, expected in (('ours', True), ('human', False)):
            supervisor, client, cameras, agent, log = (Mock() for _ in range(5))
            client.client = 'ours'
            client.state.return_value = {'enabled': True, 'owner': owner}
            self.assertEqual(close_host(supervisor, client, cameras, agent, log), [])
            self.assertEqual(client.command.called, expected)


class GuidedBudgetRenewalTests(unittest.TestCase):
    def test_explicit_budget_mode_renews_decisions_and_motion_without_a_guide(self):
        robot = Mock(fault=None)
        for status in ('budget_exhausted', 'motion_budget_boundary', 'gripper_budget_boundary'):
            renewal = automatic_budget_renewal(status, robot, all_budgets=True,
                                              guided=False, segment=1, limit=16)
            self.assertEqual(renewal['reason'], status)

    def test_automatic_renewal_never_restarts_terminal_fault_or_exhausted_run(self):
        robot = Mock(fault=None)
        for status in ('done', 'completed', 'give_up', 'failed', 'interrupted'):
            self.assertIsNone(automatic_budget_renewal(status, robot,
                all_budgets=True, guided=True, segment=1, limit=16))
        self.assertIsNone(automatic_budget_renewal('budget_exhausted', robot,
            all_budgets=True, guided=True, segment=16, limit=16))
        robot.fault = 'CAN timeout'
        self.assertIsNone(automatic_budget_renewal('budget_exhausted', robot,
            all_budgets=True, guided=True, segment=1, limit=16))

    def test_plain_decision_budget_still_waits_without_explicit_auto_mode(self):
        robot = Mock(fault=None, last_plan_rejection=None, last_budget_rejection=None)
        self.assertIsNone(automatic_budget_renewal('budget_exhausted', robot,
            all_budgets=False, guided=True, segment=1, limit=16))

    def test_queued_stop_takes_precedence_over_continue(self):
        for values in (('stop', 'continue'), ('continue', 'stop'), ('stop',)):
            commands = queue.Queue()
            for value in values:
                commands.put(value)
            self.assertEqual(queued_operator_command(commands), 'stop')
            self.assertTrue(commands.empty())
        self.assertIsNone(queued_operator_command(queue.Queue()))

    def test_gripper_budget_renews_without_an_unfinished_approach_guide(self):
        robot = Mock(last_budget_rejection='Session gripper travel budget exhausted')
        self.assertEqual(guided_budget_renewal(robot)['reason'], 'gripper_budget_boundary')

    def robot(self, rejection, guide=None):
        robot = Mock()
        robot.last_plan_rejection = rejection
        robot.last_plan_rejection_guide = guide
        return robot

    def test_returns_unfinished_guide_for_session_envelope(self):
        guide = {'reached': False, 'remaining_joint_delta_deg': [1.] * 6}
        robot = self.robot('Trajectory leaves session envelope', guide)
        self.assertIs(guided_budget_renewal(robot), guide)

    def test_returns_unfinished_guide_for_joint_travel_budget(self):
        guide = {'reached': False}
        robot = self.robot('Trajectory exceeds session joint travel budget', guide)
        self.assertIs(guided_budget_renewal(robot), guide)

    def test_does_not_renew_non_budget_rejection(self):
        robot = self.robot('Measured joint tracking error is too large', {'reached': False})
        self.assertIsNone(guided_budget_renewal(robot))

    def test_does_not_renew_reached_or_missing_guide(self):
        self.assertIsNone(guided_budget_renewal(
            self.robot('Trajectory leaves session envelope', {'reached': True})))
        self.assertIsNone(guided_budget_renewal(
            self.robot('Trajectory leaves session envelope')))
