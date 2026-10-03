import copy
import math
import unittest
from unittest.mock import patch

from r5_policy_backend import R5ExecutionFault, R5PolicyBackend
from test_policy_adapter import measured_state


class Clock:
    def __init__(self):
        self.now = 100.

    def __call__(self):
        return self.now

    def sleep(self, duration):
        self.now += duration


class Workbench:
    client = "policy-test"

    def __init__(self):
        self.current = measured_state()
        self.current.update(enabled=True, owner=self.client, hold_available=True,
                            worker_protocol_version=2,
                            policy_execution_available=True, control_state="holding",
                            mode="joint", speed=.1, gripper_command_raw=4.3,
                            command_deg=self.current["joints_deg"][:],
                            hold_target_deg=self.current["joints_deg"][:])
        self.commands = []
        self.stall = False
        self.timeout = None

    def state(self):
        return copy.deepcopy(self.current)

    def command(self, action, **fields):
        self.commands.append((action, fields))
        if action == "resume":
            self.current["control_state"] = "active"
        elif action == "target":
            if "joints_deg" in fields:
                self.current["command_deg"] = fields["joints_deg"][:]
                if not self.stall:
                    self.current["joints_deg"] = fields["joints_deg"][:]
            if "gripper_raw" in fields:
                self.current["gripper_target_raw"] = fields["gripper_raw"]
                self.current["gripper_command_raw"] = fields["gripper_raw"]
                if not self.stall:
                    self.current["gripper_raw"] = fields["gripper_raw"]-.1
        elif action == "pause_hold":
            self.current["control_state"] = "holding"
            self.current["hold_target_deg"] = self.current["command_deg"][:]
        elif action == "stop":
            self.current.update(enabled=False, owner=None)
        elif action != "heartbeat":
            raise AssertionError("Unexpected command: " + action)
        if self.timeout == action:
            raise TimeoutError("Response lost after command was accepted")
        return self.state()


class R5BackendTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.client = Workbench()
        self.vision_fault = False

        def vision():
            if self.vision_fault:
                raise RuntimeError("Camera fault")

        self.backend = R5PolicyBackend(self.client, vision, clock=self.clock, sleep=self.clock.sleep)

    def action(self, name="move_joints"):
        state = self.backend.state()
        arguments = {"observation_id": state["observation_id"], "note": "Test step"}
        if name == "move_joints":
            arguments["positions"] = state["joint_positions_rad"][:]
            arguments["positions"][0] += math.radians(1)
        else:
            arguments["gripper_raw"] = 4.4
        return arguments

    def test_constructor_does_not_touch_hardware(self):
        self.assertEqual(self.client.commands, [])

    def test_hold_allows_bounded_residual_but_reports_larger_error(self):
        self.client.current['joints_deg'][0] += 2.8
        self.backend.state()
        self.client.current['joints_deg'][0] += .3
        with self.assertRaisesRegex(R5ExecutionFault, 'measured_error_deg=3.100000'):
            self.backend.state()

    def test_hold_does_not_tolerate_changed_command_within_measured_tolerance(self):
        self.client.current['command_deg'][0] += .06
        with self.assertRaisesRegex(R5ExecutionFault, 'command_error_deg=0.060000'):
            self.backend.state()

    def test_renew_session_reanchors_only_at_healthy_powered_hold(self):
        state = self.client.state()
        target = state["joints_deg"][:]
        target[0] += 1
        self.backend.guard.accept(state, {"joints_deg": target})
        self.client.current["joints_deg"] = target[:]
        self.client.current["command_deg"] = target[:]
        self.client.current["hold_target_deg"] = target[:]

        result = self.backend.renew_session()

        self.assertEqual(result["anchor_joints_deg"], target)
        self.assertEqual(self.backend.guard.proposals, 0)
        self.assertEqual(self.client.commands, [])
        self.client.current["control_state"] = "active"
        with self.assertRaisesRegex(R5ExecutionFault, "powered hold"):
            self.backend.renew_session()

    def test_renew_session_reanchors_tracking_residual_during_active_transition(self):
        measured = self.client.current["joints_deg"][:]
        submitted = measured[:]
        submitted[0] += .5
        self.client.current["command_deg"] = submitted
        self.client.current["hold_target_deg"] = submitted[:]

        result = self.backend.renew_session()

        self.assertEqual(result["anchor_joints_deg"], measured)
        self.assertEqual(self.client.current["control_state"], "holding")
        self.assertEqual(self.client.current["command_deg"], measured)
        commands = [name for name, _ in self.client.commands]
        self.assertEqual(commands[0:2], ["resume", "target"])
        self.assertIn("pause_hold", commands)
        self.assertNotIn("stop", commands)
        self.assertFalse(self.backend.busy)

    def test_renew_session_reanchors_accepted_residual_above_observation_threshold(self):
        measured = self.client.current["joints_deg"][:]
        submitted = measured[:]
        submitted[2] += 1.2
        self.client.current["command_deg"] = submitted
        self.client.current["hold_target_deg"] = submitted[:]
        self.client.current["tracking_error_deg"][2] = -1.2

        result = self.backend.renew_session()

        self.assertEqual(result["anchor_joints_deg"], measured)
        self.assertEqual(self.client.current["command_deg"], measured)
        self.assertEqual(self.client.current["control_state"], "holding")

    def test_hold_with_pending_gripper_target_is_rejected(self):
        self.client.current["gripper_target_raw"] = 4.5
        with self.assertRaisesRegex(R5ExecutionFault, "pending target"):
            self.backend.state()
        self.assertEqual(self.client.commands, [])

    def test_no_capability_or_owner_never_enables(self):
        for key, value in (("policy_execution_available", False), ("hold_available", False),
                           ("enabled", False), ("owner", "human"), ("control_state", "active")):
            with self.subTest(key=key):
                old = self.client.current[key]
                self.client.current[key] = value
                with self.assertRaises(R5ExecutionFault):
                    self.backend.state()
                self.assertEqual(self.client.commands, [])
                self.client.current[key] = old

    def test_old_worker_is_rejected_before_motion(self):
        self.client.current.pop('worker_protocol_version')
        with self.assertRaisesRegex(R5ExecutionFault, 'Worker protocol 2'):
            self.backend.state()
        self.assertEqual(self.client.commands, [])

    def test_joint_step_converts_radians_and_holds_without_protect(self):
        result = self.backend.execute("move_joints", self.action())
        self.assertTrue(result["settle"]["settled"])
        self.assertAlmostEqual(result["measured_joints_deg"][0], 1.)
        self.assertEqual(result["control_state"], "holding")
        self.assertFalse(result["grasp_verified"])
        commands = [action for action, _ in self.client.commands]
        self.assertEqual(commands[0:2], ["resume", "target"])
        self.assertIn("pause_hold", commands)
        self.assertNotIn("stop", commands)
        self.assertNotIn("enable", commands)
        self.assertNotIn("home", commands)

    def test_raw_grip_preserves_arm_command_and_distinguishes_feedback(self):
        arguments = self.action("set_gripper")
        result = self.backend.execute("set_gripper", arguments)
        target = next(fields for name, fields in self.client.commands if name == "target")
        self.assertEqual(target, {"gripper_raw": 4.4})
        self.assertAlmostEqual(result["submitted_gripper_raw"], 4.4)
        self.assertAlmostEqual(result["measured_gripper_raw"], 4.3)
        self.assertEqual(result["submitted_joints_deg"], [0, 20, 30, -15, 0, 0])

    def test_relative_step_anchors_to_observation_and_reports_measured_delta(self):
        observed = self.backend.state()
        self.client.current["joints_deg"][0] = .2
        result = self.backend.execute("move_joint_step", {
            "observation_id": observed["observation_id"], "delta_rad": [math.radians(1), 0, 0, 0, 0, 0],
            "note": "Fixture relative correction"})
        self.assertAlmostEqual(result["requested"]["joints_deg"][0], 1.)
        self.assertAlmostEqual(result["measured_joint_delta_deg"][0], .8)
        self.assertEqual(result["source_observation_id"], observed["observation_id"])

    def test_preview_rejection_does_not_move_consume_debit_or_latch(self):
        observed = self.backend.state()
        args = {"observation_id": observed["observation_id"], "delta_rad": [1, 0, 0, 0, 0, 0],
                "note": "Fixture preview"}
        before = self.backend.guard.snapshot()
        self.assertFalse(self.backend.check_joint_step(args)["accepted"])
        self.assertEqual(self.backend.guard.snapshot(), before)
        self.assertFalse(self.backend.consumed)
        self.assertEqual(self.client.commands, [])
        args["delta_rad"][0] = math.radians(.5)
        preview = self.backend.check_joint_step(args)
        self.assertTrue(preview["accepted"])
        self.assertFalse(preview["clearance_verified"])
        self.assertEqual(self.backend.guard.snapshot(), before)
        self.assertEqual(self.client.commands, [])
        self.backend.execute("move_joint_step", args)
        self.assertEqual(self.backend.guard.proposals, 1)

    def test_preview_cannot_bypass_budget_or_authorize_later_drift(self):
        args = {"observation_id": self.backend.state()["observation_id"],
                "delta_rad": [math.radians(.5), 0, 0, 0, 0, 0], "note": "Preview"}
        self.assertTrue(self.backend.check_joint_step(args)["accepted"])
        self.client.current["joints_deg"][0] += .6
        with self.assertRaisesRegex(ValueError, "changed after observation"):
            self.backend.execute("move_joint_step", args)
        self.assertEqual(self.client.commands, [])
        self.client.current["joints_deg"][0] = 0
        self.backend.guard.proposals = 20
        self.assertFalse(self.backend.check_joint_step(args)["accepted"])
        self.assertEqual(self.backend.guard.proposals, 20)
        self.assertEqual(self.client.commands, [])

    def test_gripper_settles_with_existing_stable_joint_residual(self):
        self.client.current['joints_deg'][0] = .5
        result = self.backend.execute('set_gripper', self.action('set_gripper'))
        self.assertTrue(result['settle']['settled'])
        self.assertEqual(result['submitted_joints_deg'][0], 0)
        self.assertEqual(result['measured_joints_deg'][0], .5)

    def test_joint_step_accepts_small_secondary_deadband_with_main_progress(self):
        original = self.client.command

        def with_deadband(action, **fields):
            result = original(action, **fields)
            if action == 'target' and 'joints_deg' in fields:
                self.client.current['joints_deg'][1] -= .15
                result = self.client.state()
            return result

        self.client.command = with_deadband
        args = self.action()
        args['positions'][0] = math.radians(6)
        args['positions'][1] += math.radians(.2)
        result = self.backend.execute('move_joints', args)
        self.assertTrue(result['settle']['settled'])
        self.assertAlmostEqual(result['measured_joints_deg'][1], 20.05)

    def test_joint_step_still_rejects_stall_or_reverse_secondary_joint(self):
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                self.setUp()
                original = self.client.command
                initial = self.client.current['joints_deg'][:]

                def wrong_motion(action, **fields):
                    result = original(action, **fields)
                    if action == 'target' and 'joints_deg' in fields:
                        if reverse:
                            self.client.current['joints_deg'][1] = initial[1]-.3
                        else:
                            self.client.current['joints_deg'] = initial[:]
                        result = self.client.state()
                    return result

                self.client.command = wrong_motion
                args = self.action()
                args['positions'][0] = math.radians(2)
                args['positions'][1] += math.radians(.2)
                with self.assertRaisesRegex(R5ExecutionFault, 'did not settle'):
                    self.backend.execute('move_joints', args)
                self.assertEqual(self.client.commands[-1][0], 'stop')

    def test_cartesian_timeout_cannot_accept_oscillating_endpoint(self):
        initial = self.client.state()
        target = initial['command_deg'][:]
        target[0] += 1
        self.client.current['command_deg'] = target[:]
        samples = 0

        def oscillating():
            nonlocal samples
            samples += 1
            state = self.client.state()
            state['joints_deg'][0] = target[0] - (.2 if samples % 2 else .5)
            return state

        with patch.object(self.backend, 'check'), patch.object(self.backend, '_read', oscillating):
            with self.assertRaisesRegex(R5ExecutionFault, 'did not settle'):
                self.backend._settle(initial, {'joints_deg': target},
                                     command_relative=True, min_progress=.4)

    def test_stale_and_consumed_observations_cannot_be_replayed(self):
        arguments = self.action()
        self.clock.sleep(31)
        with self.assertRaises(ValueError):
            self.backend.execute("move_joints", arguments)
        self.assertEqual(self.client.commands, [])
        arguments = self.action()
        self.backend.execute("move_joints", arguments)
        count = len(self.client.commands)
        with self.assertRaises(ValueError):
            self.backend.execute("move_joints", arguments)
        self.assertEqual(len(self.client.commands), count)

    def test_gripper_stall_is_not_contact_or_success(self):
        self.client.stall = True
        with self.assertRaisesRegex(R5ExecutionFault, "settle"):
            self.backend.execute("set_gripper", self.action("set_gripper"))
        self.assertEqual(self.client.commands[-1][0], "stop")

    def test_resume_state_fault_records_samples_and_never_sends_target(self):
        for changed in ('joints_deg', 'command_deg', 'gripper_command_raw'):
            with self.subTest(changed=changed):
                self.setUp()
                original = self.client.command

                def drifting_resume(action, **fields):
                    result = original(action, **fields)
                    if action == 'resume':
                        if changed == 'gripper_command_raw':
                            self.client.current[changed] += .02
                        else:
                            self.client.current[changed][0] += .06
                    return result

                self.client.command = drifting_resume
                with self.assertRaisesRegex(R5ExecutionFault, 'State changed while resuming hold') as caught:
                    self.backend.execute('set_gripper', self.action('set_gripper'))
                for field in ('measured_before=', 'measured_after=', 'command_before=',
                              'command_after=', 'gripper_command_before=', 'gripper_command_after='):
                    self.assertIn(field, str(caught.exception))
                commands = [name for name, _ in self.client.commands]
                self.assertNotIn('target', commands)
                self.assertEqual(commands[-1], 'stop')

    def test_small_open_with_encoder_bias_keeps_hold_without_claiming_grasp(self):
        self.client.current.update(gripper_raw=3.23, gripper_command_raw=3.2,
                                   gripper_target_raw=3.2)
        args = self.action('set_gripper')
        args['gripper_raw'] = 3.29
        result = self.backend.execute('set_gripper', args)
        self.assertTrue(result['settle']['settled'])
        self.assertAlmostEqual(result['measured_gripper_raw'], 3.19)
        self.assertAlmostEqual(result['submitted_gripper_raw'], 3.29)
        self.assertFalse(result['grasp_verified'])
        self.assertEqual(result['control_state'], 'holding')
        self.assertNotIn('stop', [action for action, _ in self.client.commands])

    def test_small_open_already_within_tolerance_does_not_require_encoder_motion(self):
        self.client.current['gripper_raw'] = 4.38
        self.client.stall = True
        result = self.backend.execute('set_gripper', self.action('set_gripper'))
        self.assertTrue(result['settle']['settled'])
        self.assertAlmostEqual(result['measured_gripper_raw'], 4.38)
        self.assertFalse(result['grasp_verified'])

    def test_small_open_still_requires_submitted_target(self):
        self.client.current['gripper_raw'] = 4.38
        original = self.client.command

        def pending_target(action, **fields):
            result = original(action, **fields)
            if action == 'target' and 'gripper_raw' in fields:
                self.client.current['gripper_command_raw'] = 4.3
                result = self.client.state()
            return result

        self.client.command = pending_target
        with self.assertRaisesRegex(R5ExecutionFault, 'gripper_command_raw=4.3'):
            self.backend.execute('set_gripper', self.action('set_gripper'))

    def test_small_open_still_rejects_unstable_feedback_within_tolerance(self):
        initial = self.client.state()
        initial.update(gripper_raw=3.23, gripper_command_raw=3.2,
                       gripper_target_raw=3.2)
        samples = 0

        def oscillating():
            nonlocal samples
            samples += 1
            state = copy.deepcopy(initial)
            state['gripper_command_raw'] = 3.29
            state['gripper_raw'] = 3.19 if samples % 2 else 3.24
            return state

        with patch.object(self.backend, 'check'), patch.object(self.backend, '_read', oscillating):
            with self.assertRaisesRegex(R5ExecutionFault, 'did not settle'):
                self.backend._settle(initial, {'gripper_raw': 3.29})

    def test_small_open_still_rejects_large_reverse_encoder_motion(self):
        self.client.current.update(gripper_raw=3.42, gripper_command_raw=3.22,
                                   gripper_target_raw=3.22)
        args = self.action('set_gripper')
        args['gripper_raw'] = 3.32
        with self.assertRaisesRegex(R5ExecutionFault, 'did not settle'):
            self.backend.execute('set_gripper', args)
        self.assertEqual(self.client.commands[-1][0], 'stop')

    def test_large_close_stall_still_fails_with_gripper_diagnostics(self):
        self.client.stall = True
        args = self.action('set_gripper')
        args['gripper_raw'] = 3.3
        with self.assertRaisesRegex(R5ExecutionFault, 'gripper_target_raw=3.3'):
            self.backend.execute('set_gripper', args)
        self.assertEqual(self.client.commands[-1][0], 'stop')

    def test_large_gripper_close_is_one_exact_target_and_no_joint_target(self):
        args = self.action('set_gripper')
        args['gripper_raw'] = 3.3
        result = self.backend.execute('set_gripper', args)
        self.assertAlmostEqual(result['submitted_gripper_raw'], 3.3)
        targets = [fields for name, fields in self.client.commands if name == 'target']
        self.assertEqual(targets, [{'gripper_raw': 3.3}])

    def test_gripper_budget_rejection_keeps_live_guard_and_hold_healthy(self):
        args = self.action('set_gripper')
        self.backend.guard.gripper_travel = 4.99
        with self.assertRaisesRegex(ValueError, 'rejected before execution'):
            self.backend.execute('set_gripper', args)
        self.assertIsNone(self.backend.guard.failure)
        self.assertEqual(self.backend.last_budget_rejection, 'Session gripper travel budget exhausted')
        self.assertEqual(self.client.current['control_state'], 'holding')
        self.assertEqual(self.client.commands, [])
        self.backend.state()
        self.backend.renew_session()
        self.assertIsNone(self.backend.last_budget_rejection)

    def test_large_close_allows_worker_ramp_longer_than_five_seconds(self):
        initial = self.client.state()
        initial['speed'] = .3
        start = self.clock.now
        target = initial['gripper_command_raw']-1.

        def ramp():
            state = copy.deepcopy(initial)
            command = max(target, initial['gripper_command_raw']-.18*(self.clock.now-start))
            state['gripper_command_raw'] = command
            state['gripper_raw'] = command-.1
            return state

        with patch.object(self.backend, 'check'), patch.object(self.backend, '_read', ramp):
            settled = self.backend._settle(initial, {'gripper_raw': target})
        self.assertGreater(self.clock.now-start, 5.5)
        self.assertLess(self.clock.now-start, 8.)
        self.assertAlmostEqual(settled['gripper_command_raw'], target)

    def test_target_timeout_latches_and_does_not_retry(self):
        arguments = self.action()
        self.client.timeout = "target"
        with self.assertRaises(R5ExecutionFault):
            self.backend.execute("move_joints", arguments)
        self.assertEqual(sum(n == "target" for n, _ in self.client.commands), 1)
        self.assertEqual(self.client.commands[-1][0], "stop")
        with self.assertRaises(R5ExecutionFault):
            self.backend.state()

    def test_vision_failure_before_resume_sends_no_command(self):
        arguments = self.action()
        self.vision_fault = True
        with self.assertRaises(RuntimeError):
            self.backend.execute("move_joints", arguments)
        self.assertEqual(self.client.commands, [])

    def test_rejects_cartesian_normalized_and_gain_tools(self):
        for name in ("move_to", "home", "set_gain", "damping", "set_torque"):
            with self.assertRaises(ValueError):
                self.backend.execute(name, {})
        with self.assertRaises(ValueError):
            self.backend.execute("set_gripper", {"gripper": .8})
        self.assertEqual(self.client.commands, [])

    def test_finish_retains_ownership_without_home_or_gripper_change(self):
        result = self.backend.finish("done")
        self.assertTrue(result["operator_handoff_required"])
        self.assertFalse(result["returned_home"])
        self.assertEqual(self.client.current["owner"], self.client.client)
        self.assertEqual(self.client.commands, [("heartbeat", {})])

    def test_real_controller_defaults_never_advertise_execution(self):
        from live_control import LiveController
        for experimental in (False, True):
            controller = LiveController(experimental_hold=experimental)
            self.assertFalse(controller.snapshot()["policy_execution_available"])


if __name__ == "__main__":
    unittest.main()
