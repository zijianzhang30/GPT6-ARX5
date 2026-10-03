import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from policy_adapter import R5PolicyAdapter
from policy_runner import main, run_decisions, upstream_config
from test_policy_adapter import FakeWorkbench


class FakeAgent:
    def __init__(self):
        self.turns = []
        self.closed = False

    def start(self, context):
        self.context = context

    def decide(self, turn):
        self.turns.append(turn)
        observation = json.loads(turn.observation)
        return {"name": "propose_joint_step", "arguments": {
            "observation_id": observation["observation_id"],
            "joint_delta_deg": [0, 0, 1, 0, 0, 0], "note": "Review approach"},
            "_wire": {"provider_metadata": True}}

    def close(self):
        self.closed = True


class RunnerTests(unittest.TestCase):
    def setUp(self):
        upstream_config()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.client = FakeWorkbench()
        self.adapter = R5PolicyAdapter(self.client, Path(self.temp.name) / "run")
        self.agent = FakeAgent()
        self.factory = Mock(return_value=self.agent)
        sleep = patch("policy_adapter.time.sleep")
        sleep.start()
        self.addCleanup(sleep.stop)

    def test_upstream_settings_preserved(self):
        original = json.loads((Path(__file__).resolve().parents[1] /
                              "vendor/GPT-Policy-main/configs/agents/codex.json").read_text())
        config = upstream_config()
        for key in ("model", "effort", "live_image_window"):
            self.assertEqual(getattr(config, key), original[key])

    def test_provider_initialization_failure_closes_created_process(self):
        from gpt_policy.harness.codex import CodexAppServer
        with patch("gpt_policy.harness.codex.shutil.which", return_value="/mock/codex"), \
                patch("gpt_policy.harness.codex.subprocess.Popen"), \
                patch("gpt_policy.harness.codex.threading.Thread"), \
                patch.object(CodexAppServer, "_request", side_effect=TimeoutError()), \
                patch.object(CodexAppServer, "close") as close:
            with self.assertRaises(TimeoutError):
                CodexAppServer("gpt-6-astra")
        close.assert_called_once()

    def test_two_turns_real_contract_feedback_images_no_commands(self):
        result = run_decisions(self.adapter, self.factory, 2)
        self.assertEqual(result["status"], "shadow_decision")
        self.assertFalse(result["executed"])
        self.assertTrue(self.agent.closed)
        self.assertEqual(len(self.agent.turns), 2)
        first, second = (json.loads(t.observation) for t in self.agent.turns)
        self.assertNotEqual(first["observation_id"], second["observation_id"])
        self.assertTrue(second["previous_result"]["accepted"])
        self.assertFalse(second["previous_result"]["executed"])
        self.assertEqual(set(self.agent.turns[0].images), {"left", "top"})
        self.assertNotIn("_wire", result["decision"])

    def test_blocked_preflight_does_not_start_model(self):
        self.client.current["enabled"] = True
        result = run_decisions(self.adapter, self.factory)
        self.assertEqual(result["status"], "blocked")
        self.factory.assert_not_called()

    def test_invalid_decision_ends_session(self):
        self.agent.decide = Mock(return_value={"name": "home", "arguments": {}})
        result = run_decisions(self.adapter, self.factory, 3)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(self.agent.decide.call_count, 1)
        self.assertTrue(self.agent.closed)

    def test_exception_and_interrupt_close_without_motion(self):
        for error in (RuntimeError("secret-transport-details"), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                adapter = R5PolicyAdapter(self.client, Path(self.temp.name) / type(error).__name__)
                self.agent.decide = Mock(side_effect=error)
                result = run_decisions(adapter, self.factory)
                self.assertIn(result["status"], ("error", "interrupted"))
                self.assertNotIn("secret-transport-details", json.dumps(result))
                self.assertTrue(self.agent.closed)

    def test_slow_result_never_dispatched(self):
        original = self.agent.decide

        def delayed(turn):
            result = original(turn)
            clock.return_value = 126
            return result

        self.agent.decide = delayed
        with patch("policy_runner.time.monotonic", return_value=100) as clock:
            result = run_decisions(self.adapter, self.factory)
        self.assertEqual(result["status"], "error")
        self.assertFalse(self.adapter.consumed)

    def test_cleanup_failure_is_reported(self):
        self.agent.close = Mock(side_effect=OSError())
        result = run_decisions(self.adapter, self.factory)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["cleanup_error_type"], "OSError")

    def test_live_not_exposed(self):
        with self.assertRaises(SystemExit), patch("policy_runner.ReadOnlyWorkbench") as client:
            main(["live"])
        client.assert_not_called()

    def test_bad_budget_rejected_before_observation(self):
        for turns in (0, 11, True, 1.2):
            with self.assertRaises(ValueError):
                run_decisions(self.adapter, self.factory, turns)
        self.assertEqual(self.client.calls, [])


if __name__ == "__main__":
    unittest.main()
