import copy
import unittest
from unittest.mock import Mock

from gripper_check import JOINT_DRIFT_LIMIT_DEG, verify
from test_policy_adapter import measured_state
from test_r5_policy_backend import Clock


class Client:
    client = "gripper-test"

    def __init__(self):
        self.current = measured_state()
        self.current.update(mode="joint", speed=.1, hold_available=True, worker_protocol_version=2,
                            command_deg=self.current['joints_deg'][:], gripper_command_raw=4.3)
        self.commands = []
        self.fault = None
        self.enable_drift_deg = 2.

    def state(self):
        return copy.deepcopy(self.current)

    def command(self, action, **fields):
        self.commands.append((action, fields))
        if action == "settings":
            self.current.update(fields)
        elif action == "enable":
            self.current.update(enabled=True, owner=self.client,
                                gripper_command_raw=self.current['gripper_raw']+.1,
                                gripper_target_raw=self.current["gripper_raw"]+.1)
            if self.fault == "enable_timeout":
                raise TimeoutError("enable acknowledgment lost")
            if self.fault == "enable_drift":
                self.current["joints_deg"][0] += self.enable_drift_deg
        elif action == "target":
            if set(fields) != {"gripper_raw"}:
                raise AssertionError("No joint commands allowed")
            self.current["gripper_target_raw"] = fields["gripper_raw"]
            self.current['gripper_command_raw'] = fields['gripper_raw']
            if self.fault != "stall":
                self.current["gripper_raw"] = fields["gripper_raw"]-.1
            if self.fault == "target_timeout":
                raise TimeoutError("target acknowledgment lost")
        elif action == "heartbeat":
            if self.fault == "joint_drift":
                self.current["joints_deg"][2] += .6
            if self.fault == "takeover":
                self.current["owner"] = "human"
            if self.fault == 'hold_drift' and self.current.get('control_state') == 'holding':
                self.current['hold_target_deg'][0] += .01
        elif action == 'pause_hold':
            self.current.update(control_state='holding', hold_target_deg=self.current['command_deg'][:])
        elif action == 'resume':
            self.current['control_state'] = 'active'
        elif action == "stop":
            self.current.update(enabled=False, owner=None)
        return self.state()


class GripperCheckTests(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        self.clock = Clock()
        self.vision = Mock()
        self.events = []

    def run_check(self):
        return verify(self.client, self.vision, self.events.append,
                      clock=self.clock, sleep=self.clock.sleep)

    def test_bounded_response_and_protect_cleanup(self):
        result = self.run_check()
        self.assertEqual(result["status"], "response_observed")
        self.assertTrue(result["stop_confirmed"])
        self.assertAlmostEqual(result["observed_gripper_change_raw"], .1)
        self.assertEqual(result["max_active_joint_drift_deg"], 0)
        self.assertFalse(result["hold_validated"])
        targets = [fields for name, fields in self.client.commands if name == "target"]
        self.assertEqual(len(targets), 1)
        self.assertEqual(set(targets[0]), {"gripper_raw"})
        self.assertEqual(self.client.commands[-1][0], "stop")

    def test_occupied_robot_no_commands(self):
        self.client.current.update(owner="human", enabled=True)
        self.assertEqual(self.run_check()["status"], "aborted")
        self.assertEqual(self.client.commands, [])

    def test_stale_vision_no_commands(self):
        self.vision.check.side_effect = ValueError("camera stale")
        self.assertEqual(self.run_check()["status"], "aborted")
        self.assertEqual(self.client.commands, [])

    def test_enable_drift_rejects_gripper_target(self):
        self.client.fault = "enable_drift"
        result = self.run_check()
        self.assertEqual(result["status"], "aborted")
        self.assertTrue(result["stop_confirmed"])
        self.assertFalse(any(n == "target" for n, _ in self.client.commands))
        inspections = [e for e in self.events if e['event'] == 'inspection']
        self.assertAlmostEqual(inspections[-1]['state']['joints_deg'][0], 2.)
        self.assertIn('J1',result['reason'])

    def test_small_enable_transient_no_longer_aborts(self):
        self.client.fault = "enable_drift"
        self.client.enable_drift_deg = .525
        result = self.run_check()
        self.assertEqual(result["status"], "response_observed")
        self.assertAlmostEqual(result["joint_drift_limit_deg"], JOINT_DRIFT_LIMIT_DEG)
        self.assertAlmostEqual(result["max_active_joint_drift_deg"], .525)

    def test_diagnostic_boundary(self):
        for drift, expected in ((JOINT_DRIFT_LIMIT_DEG, "response_observed"),
                                (JOINT_DRIFT_LIMIT_DEG + .001, "aborted"),
                                (-JOINT_DRIFT_LIMIT_DEG - .001, "aborted")):
            with self.subTest(drift=drift):
                self.setUp()
                self.client.fault = "enable_drift"
                self.client.enable_drift_deg = drift
                self.assertEqual(self.run_check()["status"], expected)

    def test_opening_beyond_command_range_sends_no_commands(self):
        self.client.current["gripper_raw"] = 4.896238803863525
        result = self.run_check()
        self.assertEqual(result["status"], "aborted")
        self.assertEqual(self.client.commands, [])

    def test_stationary_check_near_open_limit_sends_no_motion_target(self):
        self.client.current['gripper_raw'] = 4.896238803863525
        result = verify(self.client, self.vision, self.events.append, mode='stationary',
                        clock=self.clock, sleep=self.clock.sleep)
        self.assertEqual(result['status'], 'stationary_enable_observed')
        self.assertTrue(result['joint_feedback_stable'])
        self.assertFalse(result['target_sent'])
        self.assertFalse(result['hold_validated'])
        self.assertFalse(any(n == 'target' for n, _ in self.client.commands))
        self.assertEqual(self.client.commands[-1][0], 'stop')

    def test_stationary_enable_accepts_no_previous_target_on_new_connection(self):
        self.client.current['gripper_target_raw'] = None
        result = verify(self.client, self.vision, self.events.append, mode='stationary',
                        clock=self.clock, sleep=self.clock.sleep)
        self.assertEqual(result['status'], 'stationary_enable_observed')
        self.assertFalse(result['target_sent'])
        self.assertTrue(result['stop_confirmed'])

    def test_powered_hold_resume_cycle_does_not_send_motion_targets(self):
        result = verify(self.client, self.vision, self.events.append, mode='hold',
                        clock=self.clock, sleep=self.clock.sleep)
        self.assertEqual(result['status'], 'powered_hold_observed')
        self.assertTrue(result['powered_hold_observed'])
        self.assertTrue(result['stop_confirmed'])
        self.assertFalse(result['hold_validated'])
        names = [name for name, _ in self.client.commands]
        self.assertNotIn('target', names)
        self.assertEqual(names.count('pause_hold'), 2)
        self.assertEqual(names.count('resume'), 1)

    def test_hold_checks_deployment_and_fixed_target(self):
        self.client.current['hold_available'] = False
        result = verify(self.client, self.vision, self.events.append, mode='hold',
                        clock=self.clock, sleep=self.clock.sleep)
        self.assertEqual(result['status'], 'aborted')
        self.assertEqual(self.client.commands, [])
        self.setUp()
        self.client.fault = 'hold_drift'
        result = verify(self.client, self.vision, self.events.append, mode='hold',
                        clock=self.clock, sleep=self.clock.sleep)
        self.assertEqual(result['status'], 'aborted')
        self.assertIn('latched', result['reason'])
        self.assertTrue(result['stop_confirmed'])

    def test_stationary_check_catches_gripper_motion_and_joint_instability(self):
        for fault in ('gripper', 'joints'):
            with self.subTest(fault=fault):
                self.setUp()
                original = self.client.command
                count = 0

                def command(action, **fields):
                    nonlocal count
                    if action == 'heartbeat':
                        count += 1
                        if fault == 'gripper':
                            self.client.current['gripper_raw'] += .04
                        else:
                            self.client.current['joints_deg'][0] = .2*(count % 2)
                    return original(action, **fields)

                self.client.command = command
                result = verify(self.client, self.vision, self.events.append, mode='stationary',
                                clock=self.clock, sleep=self.clock.sleep)
                self.assertEqual(result['status'], 'aborted' if fault == 'gripper' else 'inconclusive')
                self.assertTrue(result['stop_confirmed'])
                self.assertFalse(any(n == 'target' for n, _ in self.client.commands))

    def test_drift_or_timeouts_stop_without_retries(self):
        for fault in ("enable_timeout", "target_timeout", "joint_drift"):
            self.setUp()
            self.client.fault = fault
            result = self.run_check()
            self.assertEqual(result["status"], "aborted", fault)
            self.assertTrue(result["stop_confirmed"])
            self.assertLessEqual(sum(n == "target" for n, _ in self.client.commands), 1)

    def test_stall_is_inconclusive(self):
        self.client.fault = "stall"
        result = self.run_check()
        self.assertEqual(result["status"], "inconclusive")
        self.assertTrue(result["stop_confirmed"])

    def test_does_not_stop_new_owner(self):
        self.client.fault = "takeover"
        result = self.run_check()
        self.assertEqual(result["status"], "stop_unconfirmed")
        self.assertFalse(any(n == "stop" for n, _ in self.client.commands))

    def test_interrupt_still_requests_protect(self):
        self.clock.sleep = Mock(side_effect=KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            self.run_check()
        self.assertEqual(self.client.commands[-1][0], "stop")


if __name__ == "__main__":
    unittest.main()
