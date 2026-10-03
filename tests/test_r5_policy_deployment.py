import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from r5_policy_deployment import R5Cameras, ValidatedAgent, agent_context, run_r5_policy, motion_budget_headroom
from r5_policy_backend import R5ExecutionFault, R5PolicyBackend
from r5_policy_supervisor import R5PolicySupervisor
from test_policy_adapter import FakeWorkbench
from test_r5_policy_backend import Clock, Workbench


class Agent:
    def __init__(self, decisions=2):
        self.turns = []
        self.decisions = decisions

    def start(self, context):
        self.context = context

    def decide(self, turn):
        self.turns.append(turn)
        state = json.loads(turn.observation)["state"]
        if len(self.turns) == self.decisions:
            return {"name": "done", "arguments": {"summary": "Fixture result only", "hindsight": ""}}
        target = state["joint_positions_rad"][:]
        target[0] += .01
        return {"name": "move_joints", "arguments": {"positions": target,
                "observation_id": state["observation_id"], "note": "Fixture action"}}


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.client = Workbench()
        self.robot = R5PolicyBackend(self.client, lambda: None, clock=self.clock, sleep=self.clock.sleep)
        self.supervisor = R5PolicySupervisor(self.robot)
        self.addCleanup(self.supervisor.close)
        self.camera_client = FakeWorkbench()
        self.cameras = R5Cameras(self.camera_client)
        self.agent = Agent()
        self.runtime = SimpleNamespace(max_decisions=2, interface="existing-r5-worker", right_interface="")
        self.request = SimpleNamespace(instruction="Pick up the tennis ball", content=())
        self.display = MagicMock()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        from gpt_policy.recording.trace import RunRecorder
        self.recorder = RunRecorder(Path(self.temp.name)/"run", {"fixture": True})
        self.addCleanup(lambda: self.recorder.close("unreviewed"))
        sleep = patch("policy_adapter.time.sleep")
        sleep.start()
        self.addCleanup(sleep.stop)

    def run_loop(self):
        self.supervisor.start()
        return run_r5_policy(self.runtime, self.request, self.robot, self.cameras,
                             self.agent, self.recorder, supervisor=self.supervisor, display=self.display)

    def test_original_loop_executes_feedback_then_done_without_home(self):
        result = self.run_loop()
        self.assertEqual(result, "completed")
        self.assertEqual(len(self.agent.turns), 2)
        previous = json.loads(self.agent.turns[1].observation)["previous_result"]
        self.assertEqual(previous["tool"], "move_joints")
        self.assertEqual(previous["result"]["control_state"], "holding")
        self.assertFalse(previous["result"]["grasp_verified"])
        events = [json.loads(line) for line in self.recorder.events.read_text().splitlines()]
        self.assertIn("execution_result", [e["event"] for e in events])
        self.assertIn("device_finish", [e["event"] for e in events])
        self.assertNotIn("return_home", [e["event"] for e in events])
        self.assertEqual(len(list(self.recorder.frames.glob("*.jpg"))), 4)
        self.assertTrue(self.client.current["enabled"])

    def test_budget_exhaustion_keeps_hold(self):
        self.agent.decisions = 99
        self.runtime.max_decisions = 1
        self.assertEqual(self.run_loop(), "budget_exhausted")
        self.assertEqual(self.client.current["control_state"], "holding")
        self.assertFalse(any(name in ("stop", "home", "enable") for name, _ in self.client.commands))

    def test_paired_budget_headroom_detects_either_side_without_consuming_budget(self):
        left = self.robot.state()
        right = self.robot.state()
        self.assertEqual(motion_budget_headroom({'arms': {'left': left, 'right': right}}), {})
        right['motion_budget']['proposed_joint_travel_deg'] = 115.2465
        before = self.robot.guard.snapshot()
        headroom = motion_budget_headroom({'arms': {'left': left, 'right': right}})
        self.assertEqual(set(headroom), {'right'})
        self.assertAlmostEqual(headroom['right']['remaining_deg'], 4.7535)
        self.assertEqual(self.robot.guard.snapshot(), before)
        self.assertEqual(self.client.commands, [])

    def test_excursion_and_proposal_headroom_but_no_renewal_of_latched_fault(self):
        state = self.robot.state()
        state['raw_state']['joints_deg'][0] += 39.1
        self.assertEqual(motion_budget_headroom(state)['arm']['reason'], 'joint_excursion')
        state['raw_state']['joints_deg'][0] -= 39.1
        state['motion_budget']['accepted_proposals'] = 20
        self.assertEqual(motion_budget_headroom(state)['arm']['reason'], 'proposal_count')
        state['motion_budget']['fault_latched'] = 'Feedback fault'
        self.assertEqual(motion_budget_headroom(state), {})

    def test_budget_renewal_keeps_agent_history_and_previous_images(self):
        self.agent.decisions = 99
        self.runtime.max_decisions = 1
        self.recorder.segment = 1
        with patch.object(self.agent, "start", wraps=self.agent.start) as start:
            self.assertEqual(self.run_loop(), "budget_exhausted")
            original = {path: path.read_bytes() for path in self.recorder.frames.glob("*.jpg")}
            self.robot.renew_session()
            self.recorder.segment = 2
            result = run_r5_policy(self.runtime, self.request, self.robot, self.cameras,
                                  self.agent, self.recorder, supervisor=self.supervisor,
                                  start_agent=False)
            self.assertEqual(result, "budget_exhausted")
            start.assert_called_once()
        self.assertEqual(len(self.agent.turns), 2)
        self.assertEqual(len(list(self.recorder.frames.glob("*.jpg"))), 4)
        for path, data in original.items():
            self.assertEqual(path.read_bytes(), data)
        events = [json.loads(line) for line in self.recorder.events.read_text().splitlines()]
        self.assertEqual([event["segment"] for event in events
                          if event["event"] == "observation"], [1, 2])

    def test_live_capability_blocks_before_agent_start(self):
        self.client.current["policy_execution_available"] = False
        with self.assertRaises(R5ExecutionFault):
            self.run_loop()
        self.assertEqual(self.agent.turns, [])
        self.assertFalse(hasattr(self.agent, "context"))
        self.assertEqual(self.client.commands, [])

    def test_state_error_does_not_reuse_old_feedback_or_retry_forever(self):
        with patch.object(self.robot, "state", side_effect=R5ExecutionFault("missing feedback")):
            with self.assertRaisesRegex(R5ExecutionFault, "missing feedback"):
                self.run_loop()
        self.assertEqual(self.agent.turns, [])

    def test_camera_devices_and_no_calibration_are_preserved(self):
        images = self.cameras.snapshot()
        self.assertEqual(set(images), {"left", "top"})
        self.assertEqual(images["left"].data, self.camera_client.jpeg)
        descriptions = self.cameras.describe(images)
        self.assertTrue(all(item["intrinsics"] is None for item in descriptions))
        self.assertEqual(descriptions[1]["role"], "external RGB (may move)")
        self.camera_client.frozen = True
        with self.assertRaises(ValueError):
            self.cameras.snapshot()
        self.camera_client.frozen = False
        with self.assertRaises(RuntimeError):
            self.cameras.snapshot()

    def test_terminal_and_nonfinite_decisions_are_validated(self):
        agent = MagicMock()
        wrapped = ValidatedAgent(agent)
        for decision in ({"name": "done", "arguments": {}},
                         {"name": "home", "arguments": {}},
                         {"name": [], "arguments": {}},
                         {"name": "set_gripper", "arguments": {"gripper_raw": float("nan")}}):
            agent.decide.return_value = decision
            with self.assertRaises(Exception):
                wrapped.decide(None)

    def test_wrist_only_loop_does_not_read_or_send_external_images(self):
        self.camera_client.missing = "external"
        self.cameras = R5Cameras(self.camera_client, camera_mode="wrist")
        self.runtime.camera_mode = "wrist"
        self.assertEqual(self.run_loop(), "completed")
        self.assertNotIn("external", self.camera_client.calls)
        self.assertIn("ONLY the left wrist", self.agent.context.instructions)
        for turn in self.agent.turns:
            self.assertEqual([i["name"] for i in json.loads(turn.observation)["images"]], ["left"])
        self.assertEqual(len(list(self.recorder.frames.glob("*.jpg"))), 2)

    def test_wrist_only_still_latches_camera_failure(self):
        self.cameras = R5Cameras(self.camera_client, camera_mode="wrist")
        self.cameras.snapshot()
        self.camera_client.frozen = True
        with self.assertRaises(ValueError):
            self.cameras.snapshot()
        self.camera_client.frozen = False
        with self.assertRaises(RuntimeError):
            self.cameras.snapshot()

    def test_tool_context_does_not_claim_metric_gripper_or_tcp(self):
        context = agent_context()
        names = {tool["function"]["name"] for tool in context.tools}
        self.assertEqual(names, {"observe", "check_joint_step", "move_joint_step",
                                 "move_joints", "set_gripper", "done", "give_up"})
        self.assertIn("RADIANS", context.instructions)

    def test_original_loop_preview_recovery_relative_step_and_reobserve(self):
        class Corrections(Agent):
            def decide(self, turn):
                self.turns.append(turn)
                state = json.loads(turn.observation)["state"]
                step = len(self.turns)
                args = {"observation_id": state["observation_id"], "note": "Fixture correction"}
                if step in (1, 2, 3):
                    args["delta_rad"] = [1 if step == 1 else .01, 0, 0, 0, 0, 0]
                    return {"name": "move_joint_step" if step == 3 else "check_joint_step", "arguments": args}
                if step == 4:
                    return {"name": "observe", "arguments": args}
                return {"name": "give_up", "arguments": {"reason": "Fixture budget", "hindsight": ""}}

        self.agent = Corrections()
        self.runtime.max_decisions = 5
        self.assertEqual(self.run_loop(), "give_up")
        previous = [json.loads(t.observation).get("previous_result") for t in self.agent.turns]
        self.assertFalse(previous[1]["result"]["accepted"])
        self.assertTrue(previous[2]["result"]["accepted"])
        self.assertTrue(previous[3]["result"]["settle"]["settled"])
        self.assertFalse(previous[4]["result"]["executed"])
        self.assertEqual(self.robot.guard.proposals, 1)
        self.assertEqual(sum(n == "target" for n, _ in self.client.commands), 1)
        self.assertEqual(len(list(self.recorder.frames.glob("*.jpg"))), 10)
        self.assertEqual(self.client.current["control_state"], "holding")

    def test_upstream_default_finish_still_homes(self):
        from gpt_policy.runtime.runner import _finish_run
        robot, recorder, display = MagicMock(), MagicMock(), MagicMock()
        robot.return_home.return_value = {}
        _finish_run(robot, recorder, 0, "done", display, None)
        robot.return_home.assert_called_once()


if __name__ == "__main__":
    unittest.main()
