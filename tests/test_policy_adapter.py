import copy
from io import BytesIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from jsonschema import Draft202012Validator

from policy_adapter import (ReadOnlyWorkbench, R5PolicyAdapter, NoRedirect,
                            protocol, state_blockers)


def measured_state():
    return {"simulation": False, "worker_running": True, "model_ready": True,
            "enabled": False, "moving": False, "owner": None,
            "robot_status": "ready", "feedback_age_ms": 10, "rx_age_ms": 2,
            "error_codes": [], "joints_deg": [0, 20, 30, -15, 0, 0],
            "lower_deg": [-170, -5, -5, -73, -85, -100],
            "upper_deg": [150, 200, 170, 73, 85, 100],
            "gripper_raw": 4.2, "gripper_target_raw": 4.3,
            "tracking_limited": False, "tracking_error_deg": [0] * 6,
            "currents": [1] * 7, "pose": [1] * 6}


class FakeWorkbench:
    def __init__(self):
        self.current = measured_state()
        self.count = {"gemini": 0, "external": 0}
        self.frozen = False
        self.missing = None
        self.calls = []
        stream = BytesIO()
        Image.new("RGB", (32, 24), "green").save(stream, "JPEG")
        self.jpeg = stream.getvalue()

    def state(self):
        self.calls.append("state")
        return copy.deepcopy(self.current)

    def camera(self, key):
        self.calls.append(key)
        if key == self.missing:
            raise OSError("Camera disconnected")
        if not self.frozen:
            self.count[key] += 1
        return self.jpeg, str(self.count[key]), "/dev/" + key

    def command(self, *args, **kwargs):
        raise AssertionError("The shadow adapter must never send commands")


class PolicyAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.client = FakeWorkbench()
        self.adapter = R5PolicyAdapter(self.client, Path(self.temp.name) / "run")
        self.sleep = patch("policy_adapter.time.sleep")
        self.sleep.start()

    def tearDown(self):
        self.sleep.stop()
        self.temp.cleanup()

    def decision(self, **fields):
        return {"name": "propose_joint_step", "arguments": {
            "observation_id": self.adapter.latest["observation_id"],
            "note": "Inspect approach direction", "joint_delta_deg": [0, 0, 2, 0, 0, 0],
            **fields}}

    def test_observation_mapping_units_and_unknown_geometry(self):
        observation = self.adapter.observe()
        self.assertTrue(observation["proposal_ready"])
        self.assertEqual(set(observation["cameras"]), {"left", "top"})
        self.assertEqual(observation["cameras"]["left"]["source"], "gemini")
        self.assertEqual(observation["cameras"]["top"]["source"], "external")
        self.assertAlmostEqual(observation["state"]["joint_pos_rad"][2], .5235987756)
        for key in ("tcp_pose", "joint_torque_nm", "gripper_width_m"):
            self.assertIsNone(observation["state"][key])
        self.assertFalse(observation["execution_available"])
        for camera in observation["cameras"].values():
            self.assertTrue(Path(camera["image"]).is_file())
            self.assertIsNone(camera["capture_timestamp"])
            self.assertFalse(camera["synchronized"])

    def test_blocked_telemetry_is_reported_without_fabricating_numbers(self):
        self.client.current.update(robot_status="fault", joints_deg=[None] * 6,
                                   error_codes=[2, 12], gripper_raw=-1.3, model_ready=False)
        observation = self.adapter.observe()
        self.assertFalse(observation["proposal_ready"])
        self.assertIsNone(observation["state"]["joint_pos_rad"])
        self.assertIn("Invalid joints_deg", observation["blockers"])
        self.assertFalse(self.adapter.handle(self.decision())["accepted"])

    def test_all_bad_states_fail_closed(self):
        for key, value in (("simulation", True), ("worker_running", None),
                           ("model_ready", False), ("enabled", True), ("moving", True),
                           ("owner", "human"), ("robot_status", "fault"),
                           ("error_codes", None), ("feedback_age_ms", float("nan")),
                           ("rx_age_ms", -1), ("feedback_age_ms", 151),
                           ("joints_deg", [True] * 6), ("upper_deg", [None] * 6),
                           ("lower_deg", [100] * 6), ("gripper_raw", -1.3),
                           ("gripper_target_raw", float("inf"))):
            with self.subTest(key=key, value=value):
                state = measured_state()
                state[key] = value
                self.assertTrue(state_blockers(state))

    def test_frozen_missing_or_corrupt_images_block_proposals(self):
        for mode in ("frozen", "missing", "corrupt"):
            with self.subTest(mode=mode):
                self.client.frozen = mode == "frozen"
                self.client.missing = "external" if mode == "missing" else None
                if mode == "corrupt":
                    self.client.jpeg = b"invalid"
                self.assertFalse(self.adapter.observe()["proposal_ready"])
                self.assertFalse(self.adapter.handle(self.decision())["accepted"])

    def test_valid_proposal_never_executes_or_replays(self):
        self.adapter.observe()
        result = self.adapter.handle(self.decision())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["proposed_target"]["joints_deg"], [0, 20, 32, -15, 0, 0])
        self.assertFalse(result["executed"])
        self.assertFalse(result["collision_checked"])
        self.assertFalse(self.adapter.handle(self.decision())["accepted"])
        self.assertTrue(set(self.client.calls) <= {"state", "gemini", "external"})

    def test_invalid_joint_actions_and_unknown_fields_are_rejected(self):
        self.adapter.observe()
        for delta in ([0] * 5, [True] * 6, [24.1, 0, 0, 0, 0, 0], [24, 24, 0, 0, 0, 0],
                      [float("nan")] * 6, [float("inf")] * 6):
            self.assertFalse(self.adapter.handle(self.decision(joint_delta_deg=delta))["accepted"])
        self.assertFalse(self.adapter.handle(self.decision(speed=1))["accepted"])
        for name in ("move_to", "enable", "home", "stop", "set_gripper"):
            self.assertFalse(self.adapter.handle({"name": name, "arguments": {}})["accepted"])
        for value in (None, [], {"name": []}, {"name": [], "arguments": {}}):
            self.assertFalse(self.adapter.handle(value)["accepted"])

    def test_out_of_range_target_is_rejected(self):
        self.client.current["joints_deg"][0] = 149
        self.adapter.observe()
        self.assertFalse(self.adapter.handle(self.decision(joint_delta_deg=[2, 0, 0, 0, 0, 0]))["accepted"])

    def test_small_drift_cannot_expand_joint_step_limit(self):
        self.adapter.observe()
        self.client.current["joints_deg"][0] = -.4
        result = self.adapter.handle(self.decision(joint_delta_deg=[24, 0, 0, 0, 0, 0]))
        self.assertFalse(result["accepted"])
        self.assertIn("fresh feedback", result["error"])

    def test_duplicate_devices_and_old_frame_receipts_are_blocked(self):
        original = self.adapter._camera
        def duplicate(key):
            image, metadata = original(key)
            metadata["device"] = "/dev/same"
            return image, metadata
        with patch.object(self.adapter, "_camera", side_effect=duplicate):
            result = self.adapter.observe()
            self.assertFalse(result["proposal_ready"])
            self.assertIn("Both logical cameras resolve to the same device", result["blockers"])
        def stale(key):
            image, metadata = original(key)
            metadata["received_monotonic_s"] -= 2
            return image, metadata
        with patch.object(self.adapter, "_camera", side_effect=stale):
            self.assertFalse(self.adapter.observe()["proposal_ready"])

    def test_http_requests_have_no_command_token_or_body(self):
        client = ReadOnlyWorkbench("http://127.0.0.1:8768")
        class Response(BytesIO):
            headers = {}
        def opened(request, timeout):
            self.assertEqual(request.get_method(), "GET")
            self.assertIsNone(request.data)
            self.assertEqual(request.headers, {})
            self.assertEqual(request.full_url, "http://127.0.0.1:8768/api/state")
            return Response(json.dumps(measured_state()).encode())
        with patch.object(client.opener, "open", side_effect=opened):
            self.assertEqual(client.state()["joints_deg"], measured_state()["joints_deg"])

    def test_gripper_is_separate_bounded_vendor_raw_target(self):
        self.adapter.observe()
        decision = {"name": "propose_gripper", "arguments": {
            "observation_id": self.adapter.latest["observation_id"],
            "note": "Review gripper change", "gripper_raw": 4.2}}
        for value in (0.0, 5.1, float("nan"), True):
            bad = copy.deepcopy(decision)
            bad["arguments"]["gripper_raw"] = value
            self.assertFalse(self.adapter.handle(bad)["accepted"])
        result = self.adapter.handle(decision)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["proposed_target"], {"gripper_raw": 4.2})

    def test_expiry_old_id_and_changed_state_are_rejected(self):
        self.adapter.observe()
        old = self.decision()
        self.adapter.observe()
        self.assertFalse(self.adapter.handle(old)["accepted"])
        self.adapter.observed_at -= 31
        self.assertFalse(self.adapter.handle(self.decision())["accepted"])
        for key, value in (("joints_deg", [1, 20, 30, -15, 0, 0]),
                           ("gripper_raw", 3.9), ("gripper_target_raw", 4.0),
                           ("error_codes", [2]), ("enabled", True)):
            self.client.current = measured_state()
            self.adapter.observe()
            self.client.current[key] = value
            self.assertFalse(self.adapter.handle(self.decision())["accepted"])

    def test_observation_does_not_leak_mutable_internal_state(self):
        observation = self.adapter.observe()
        observation["raw_state"]["joints_deg"][0] = 100
        self.assertEqual(self.adapter.latest["raw_state"]["joints_deg"][0], 0)

    def test_json_logs_and_no_overwrite(self):
        self.adapter.observe()
        self.adapter.handle(self.decision())
        lines = (self.adapter.directory / "events.jsonl").read_text().splitlines()
        self.assertEqual([json.loads(line)["event"] for line in lines], ["observation", "tool_result"])
        with self.assertRaises(FileExistsError):
            R5PolicyAdapter(self.client, self.adapter.directory)

    def test_read_only_transport_rejects_commands_and_redirects(self):
        client = ReadOnlyWorkbench("http://127.0.0.1:8768/")
        for path in ("/api/command", "/api/recording/start", "/", "http://example.com"):
            with self.assertRaises(ValueError):
                client.get(path)
        for url in ("https://127.0.0.1:8768", "http://example.com", "http://localhost/?x=1",
                    "http://user@localhost:8768", "http://localhost:8768/#x"):
            with self.assertRaises(ValueError):
                ReadOnlyWorkbench(url)
        with self.assertRaises(ValueError):
            NoRedirect().redirect_request(None, None, 302, "", {}, "http://example.com")
        self.assertFalse(hasattr(client, "command"))

    def test_protocol_schema_and_matching_tool_validation(self):
        spec = protocol()
        Draft202012Validator.check_schema(spec["output_schema"])
        self.adapter.observe()
        Draft202012Validator(spec["output_schema"]).validate(self.decision())
        # The outer union is insufficient: dispatch must validate the named tool.
        decision = self.decision()
        decision["name"] = "observe"
        self.assertFalse(self.adapter.handle(decision)["accepted"])

    def test_actual_upstream_agent_contract_with_fake_decision_provider(self):
        source = Path(__file__).resolve().parents[1] / "vendor/GPT-Policy-main/src"
        if not source.exists():
            self.skipTest("Local evaluation source is not present")
        with patch.object(sys, "path", [str(source), *sys.path]):
            from gpt_policy.harness.models import AgentContext, AgentTurn
            self.assertIsInstance(self.adapter.agent_context(), AgentContext)
            class Agent:
                def decide(inner, turn):
                    self.assertIsInstance(turn, AgentTurn)
                    self.assertEqual(set(turn.images), {"left", "top"})
                    self.assertTrue(turn.images["left"].data_url().startswith("data:image/jpeg;base64,"))
                    observation = json.loads(turn.observation)
                    return {"name": "propose_joint_step", "arguments": {
                        "observation_id": observation["observation_id"], "note": "Shadow only",
                        "joint_delta_deg": [0, 0, 2, 0, 0, 0]}, "_wire": {}}
            result = self.adapter.shadow_once(Agent())
            self.assertTrue(result["accepted"])
            self.assertFalse(result["executed"])
        self.assertNotIn("arx5_interface", sys.modules)
        self.assertNotIn("gpt_policy.hardware.robot", sys.modules)

    def test_fault_blocks_before_calling_model(self):
        class Agent:
            def decide(self, turn):
                raise AssertionError("Must not call model with faulted hardware")
        self.client.current["robot_status"] = "fault"
        result = self.adapter.shadow_once(Agent())
        self.assertFalse(result["accepted"])

    def test_observe_cannot_reset_proposal_budget(self):
        for _ in range(20):
            self.assertTrue(self.adapter.observe()['proposal_ready'])
            result = self.adapter.handle(self.decision())
            self.assertTrue(result['accepted'])
        self.adapter.observe()
        result = self.adapter.handle(self.decision())
        self.assertFalse(result['accepted'])
        self.assertIn('count exhausted', result['error'])
        self.assertFalse(self.adapter.observe()['proposal_ready'])
        self.assertEqual(self.adapter.guard.proposals, 20)

    def test_camera_recovery_does_not_automatically_resume_session(self):
        self.adapter.observe()
        self.client.missing = 'external'
        self.assertFalse(self.adapter.observe()['proposal_ready'])
        self.client.missing = None
        restored = self.adapter.observe()
        self.assertFalse(restored['proposal_ready'])
        self.assertIn('Camera disconnected', restored['software_guard']['fault_latched'])

    def test_fresh_state_fault_remains_latched_after_recovery(self):
        self.adapter.observe()
        self.client.current['error_codes'] = [12]
        self.assertFalse(self.adapter.handle(self.decision())['accepted'])
        self.client.current['error_codes'] = []
        self.assertFalse(self.adapter.observe()['proposal_ready'])


if __name__ == "__main__":
    unittest.main()
