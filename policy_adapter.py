#!/usr/bin/env python3
"""Single-R5 HTTP observation and shadow tools for GPT-Policy.

This adapter has no motor-command transport. Accepted proposals are NOT executed.
It never imports a robot SDK, opens CAN, enables motors, or returns the arm home.
"""
import argparse
import base64
import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from io import BytesIO
import json
import math
from pathlib import Path
import sys
import time
import urllib.request
from urllib.parse import urlsplit
import uuid

from PIL import Image
from motion_safety import (ProposalGuard, feedback_issues, finite, vector,
                           JOINT_STEP_DEG, JOINT_STEP_NORM_DEG, GRIPPER_STEP_RAW)


ROOT = Path(__file__).resolve().parent
CAMERAS = {"left": "gemini", "top": "external"}
INSTRUCTIONS = """You are preparing a grasp with one physical ARX R5 arm, J1..J6.
This is SHADOW MODE. Tools only observe or record proposals; they never move it.
Never describe a proposed action as executed or a grasp as accomplished.
left is the Gemini 305 wrist RGB view; top is the fixed external RGB view,
not necessarily overhead. Neither image is depth. Calibration is unavailable.
Joint actions are increments in DEGREES in J1..J6 order, not Cartesian targets.
Gripper targets are vendor raw units 0..5, not metres, mm, or normalized opening.
Opening direction and raw-to-width conversion must be verified, not assumed.
Do not infer torque from currents or fingertip TCP from the workbench pose.
Return one tool selection {"name": ..., "arguments": {...}} at a time.
Use the latest observation_id. Never replay historical proposals as commands.
Propose arm motion separately from gripper closure. Inspect both views for the
ball, fingertips, table, camera housings, cables and clearance. If obstructed or
uncertain, request observation; do not invent metric geometry. Stop proposing
motion on any readiness blocker. Numeric acceptance is not collision checking.
Report evidence and purpose in note. No tools for enable, home, stop, or move_to
are available. Physical execution requires a separately validated controller.
At most 12 degrees per joint, 16.5 degrees combined norm, or 0.1 raw gripper units
per proposal. Session travel budgets and a 2-degree limit margin also apply.
Session faults stay latched; observing again cannot clear a fault or budget.
"""


def object_schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


COMMON = {"observation_id": {"type": "string", "minLength": 1},
          "note": {"type": "string", "minLength": 1, "maxLength": 500}}
TOOL_ARGUMENTS = {
    "observe": object_schema({}),
    "propose_joint_step": object_schema({**COMMON, "joint_delta_deg": {
        "type": "array", "minItems": 6, "maxItems": 6,
        "items": {"type": "number", "minimum": -JOINT_STEP_DEG, "maximum": JOINT_STEP_DEG}}}),
    "propose_gripper": object_schema({**COMMON, "gripper_raw": {
        "type": "number", "minimum": 0, "maximum": 5}}),
}


def protocol():
    tools = [{"type": "function", "function": {
        "name": name, "description": (
            "Read both RGB cameras and robot feedback; no actuation." if name == "observe"
            else "Validate and record a shadow proposal. Never executes motion."),
        "parameters": copy.deepcopy(schema)}} for name, schema in TOOL_ARGUMENTS.items()]
    schema = object_schema({"name": {"type": "string", "enum": list(TOOL_ARGUMENTS)},
                            "arguments": {"anyOf": list(copy.deepcopy(TOOL_ARGUMENTS).values())}})
    return {"instructions": INSTRUCTIONS, "tools": tools, "output_schema": schema,
            "mode": "shadow", "execution_available": False,
            "software_guard": ProposalGuard().snapshot()}


def reject_json_constant(value):
    raise ValueError(f"Invalid JSON number: {value}")


def state_blockers(state, *, require_gripper_target=True):
    if not isinstance(state, dict):
        return ["Missing robot state"]
    issues = feedback_issues(state, require_gripper_target=require_gripper_target)
    for key, expected in (("simulation", False), ("worker_running", True),
                          ("model_ready", True), ("enabled", False), ("moving", False)):
        if state.get(key) is not expected:
            issues.append(f"{key} must be {expected}")
    if state.get("robot_status") != "ready":
        issues.append("Robot is not ready")
    if state.get("error_codes") != []:
        issues.append("SDK errors present or unavailable")
    if state.get("owner") is not None:
        issues.append("Another controller owns the arm")
    return issues


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Workbench redirects are not allowed")


class ReadOnlyWorkbench:
    """Allowlisted GETs only, without control tokens, proxies, or redirects."""
    def __init__(self, url):
        parsed = urlsplit(url)
        if (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost")
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or parsed.username is not None or parsed.password is not None):
            raise ValueError("Use a plain local workbench URL")
        self.base = url.rstrip("/")
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def get(self, path):
        allowed = {"/api/state", *(f"/api/cameras/{key}/frame.jpg" for key in CAMERAS.values())}
        if path not in allowed:
            raise ValueError("Endpoint is not read-only allowlisted")
        request = urllib.request.Request(self.base + path, method="GET")
        with self.opener.open(request, timeout=8) as response:
            data = response.read(8_000_001)
            if len(data) > 8_000_000:
                raise ValueError("Oversized workbench response")
            return data, response.headers

    def state(self):
        data, _ = self.get("/api/state")
        state = json.loads(data, parse_constant=reject_json_constant)
        if not isinstance(state, dict):
            raise ValueError("State must be an object")
        return state

    def camera(self, key):
        data, headers = self.get(f"/api/cameras/{key}/frame.jpg")
        return data, headers.get("X-Frame-Id"), headers.get("X-Camera-Device")


@dataclass(frozen=True)
class PolicyImage:
    data: bytes
    width: int
    height: int
    mime_type: str = "image/jpeg"
    rgb_data: bytes | None = None

    def data_url(self):
        return "data:image/jpeg;base64," + base64.b64encode(self.data).decode("ascii")


def read_camera(client, key):
    """Read an advancing, bounded JPEG without opening the camera device."""
    _, before, device_before = client.camera(key)
    time.sleep(.08)
    data, after, device = client.camera(key)
    received_at = time.monotonic()
    if (not before or not after or before == after or not device
            or device != device_before):
        raise ValueError("Camera sequence did not advance or device changed")
    with Image.open(BytesIO(data)) as image:
        if image.format != "JPEG" or image.width * image.height > 16_000_000:
            raise ValueError("Expected a bounded JPEG frame")
        image.load()
        width, height = image.size
    return PolicyImage(data, width, height), {
        "source": key, "sequence": after, "device": device,
        "width": width, "height": height, "sequence_advanced": True,
        "received_monotonic_s": received_at,
        "capture_timestamp": None, "synchronized": False}


class R5PolicyAdapter:
    def __init__(self, client, directory, instruction="Pick up the tennis ball."):
        self.client = client
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=False)
        self.instruction = instruction
        self.latest = None
        self.images = {}
        self.observed_at = None
        self.consumed = False
        self.guard = ProposalGuard()
        self._save("protocol.json", protocol())

    def _save(self, name, value):
        with (self.directory / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")

    def _log(self, event):
        with (self.directory / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")

    def _camera(self, key):
        return read_camera(self.client, key)

    def observe(self):
        # Invalidate the previous frame even if this observation fails partway.
        self.latest, self.images, self.observed_at = None, {}, None
        identifier = uuid.uuid4().hex
        started_at = time.monotonic()
        issues, cameras = [], {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {name: pool.submit(self._camera, key) for name, key in CAMERAS.items()}
            for name, future in futures.items():
                try:
                    image, metadata = future.result()
                    filename = f"{identifier}-{name}.jpg"
                    with (self.directory / filename).open("xb") as stream:
                        stream.write(image.data)
                    self.images[name] = image
                    cameras[name] = {**metadata, "image": str(self.directory / filename)}
                except Exception as exc:
                    issues.append(f"Camera {name}: {exc}")
                    cameras[name] = {"source": CAMERAS[name], "error": str(exc)}
        try:
            state = self.client.state()
            issues.extend(state_blockers(state))
        except Exception as exc:
            state = None
            issues.append(f"State unavailable: {exc}")
        completed_at = time.monotonic()
        if (cameras["left"].get("device") is not None
                and cameras["left"].get("device") == cameras["top"].get("device")):
            issues.append("Both logical cameras resolve to the same device")
        for name, metadata in cameras.items():
            stamp = metadata.get("received_monotonic_s")
            if stamp is not None and completed_at - stamp > 1:
                issues.append(f"Camera {name}: frame receipt is more than 1 second old")
        if issues:
            self.guard.latch("; ".join(issues))
        try:
            self.guard.check_state(state)
            self.guard.check_cameras(cameras)
        except ValueError as exc:
            issues.append(str(exc))
        q = state.get("joints_deg") if state else None
        observation = {
            "observation_id": identifier, "instruction": self.instruction,
            "mode": "shadow", "execution_available": False,
            "received_monotonic_s": completed_at,
            "collection_duration_s": completed_at - started_at,
            "cameras": cameras, "raw_state": state,
            "state": {"joint_pos_rad": [math.radians(x) for x in q] if vector(q) else None,
                      "joint_units": "degrees in raw_state; radians in joint_pos_rad",
                      "gripper_units": "vendor_raw_0_to_5",
                      "tcp_pose": None, "joint_torque_nm": None, "gripper_width_m": None},
            "calibration": {"intrinsics": None, "extrinsics": None, "tcp": None,
                            "depth_available": False},
            "proposal_ready": not issues, "blockers": issues,
            "software_guard": self.guard.snapshot(),
        }
        self._save(f"{identifier}-observation.json", observation)
        self._log({"event": "observation", **observation})
        self.latest = copy.deepcopy(observation)
        self.observed_at = completed_at
        self.consumed = False
        return observation

    def _propose(self, name, arguments):
        self.guard.require_healthy()
        latest = self.latest
        if latest is None or arguments["observation_id"] != latest["observation_id"]:
            raise ValueError("Proposal must reference the latest observation")
        if self.consumed or time.monotonic() - self.observed_at > 30:
            raise ValueError("Observation consumed or expired; observe again")
        if not latest["proposal_ready"]:
            raise ValueError("Observation blocked: " + "; ".join(latest["blockers"]))
        state = self.client.state()
        issues = state_blockers(state)
        if issues:
            self.guard.fail("Fresh state blocked: " + "; ".join(issues))
        previous = latest["raw_state"]
        if (max(abs(a - b) for a, b in zip(state["joints_deg"], previous["joints_deg"])) > .5
                or abs(state["gripper_raw"] - previous["gripper_raw"]) > .15
                or abs(state["gripper_target_raw"] - previous["gripper_target_raw"]) > .01):
            raise ValueError("Robot changed since observation; observe again")
        target = {}
        if name == "propose_joint_step":
            delta = arguments["joint_delta_deg"]
            if not vector(delta) or max(map(abs, delta)) > JOINT_STEP_DEG or math.hypot(*delta) > JOINT_STEP_NORM_DEG:
                raise ValueError("Joint increment exceeds 2 deg/joint or 3 deg norm")
            # Keep the target anchored to what the model actually observed.
            q = [a + b for a, b in zip(previous["joints_deg"], delta)]
            fresh_delta = [a - b for a, b in zip(q, state["joints_deg"])]
            if max(map(abs, fresh_delta)) > JOINT_STEP_DEG or math.hypot(*fresh_delta) > JOINT_STEP_NORM_DEG:
                raise ValueError("Step exceeds limits relative to fresh feedback")
            if any(not lo <= x <= hi for x, lo, hi in zip(q, state["lower_deg"], state["upper_deg"])):
                raise ValueError("Target exceeds joint limits")
            target["joints_deg"] = q
        else:
            grip = arguments["gripper_raw"]
            if not finite(grip) or abs(grip - state["gripper_target_raw"]) > GRIPPER_STEP_RAW + 1e-9:
                raise ValueError("Gripper step exceeds 0.1 vendor raw units")
            target["gripper_raw"] = grip
        budget = self.guard.accept(state, target)
        self.consumed = True
        return {"accepted": True, "executed": False, "execution_available": False,
                "collision_checked": False, "observation_id": latest["observation_id"],
                "proposed_target": target, "note": arguments["note"],
                "software_guard": budget,
                "next": "Observe again; do not replay this as a hardware command."}

    def handle(self, decision):
        from jsonschema import Draft202012Validator
        logged_decision = decision
        try:
            try:
                json.dumps(decision, allow_nan=False)
            except (ValueError, TypeError):
                logged_decision = repr(decision)
                raise ValueError("Decision must be finite JSON") from None
            if not isinstance(decision, dict) or set(decision) != {"name", "arguments"}:
                raise ValueError("Expected exactly name and arguments")
            name = decision["name"]
            if not isinstance(name, str) or name not in TOOL_ARGUMENTS:
                raise ValueError("Unsupported tool; motion execution is not available")
            errors = list(Draft202012Validator(TOOL_ARGUMENTS[name]).iter_errors(decision["arguments"]))
            if errors:
                raise ValueError(errors[0].message)
            if name == "observe":
                return self.observe()
            result = self._propose(name, decision["arguments"])
        except (ValueError, TypeError, KeyError, OSError) as exc:
            result = {"accepted": False, "executed": False, "error": str(exc)}
        result["software_guard"] = self.guard.snapshot()
        self._log({"event": "tool_result", "decision": logged_decision, "result": result})
        return result

    def agent_context(self):
        """Actual upstream types; no upstream hardware or runtime imports."""
        from gpt_policy.harness.models import AgentContext
        spec = protocol()
        return AgentContext(spec["instructions"], spec["tools"], spec["output_schema"])

    def agent_turn(self, observation, previous_result=None):
        from gpt_policy.harness.models import AgentTurn
        payload = {**observation, "previous_result": previous_result}
        return AgentTurn(json.dumps(payload, ensure_ascii=False, allow_nan=False), dict(self.images))

    def shadow_once(self, agent):
        """One upstream AgentSession decision, deliberately without execution.

        The caller owns agent construction/start/close and any provider access.
        A failed preflight does not invoke the model at all.
        """
        observation = self.observe()
        if not observation["proposal_ready"]:
            return {"accepted": False, "executed": False, "blockers": observation["blockers"]}
        decision = agent.decide(self.agent_turn(observation))
        # Upstream providers add _wire metadata; it is not a tool argument.
        normalized = ({key: value for key, value in decision.items() if key != "_wire"}
                      if isinstance(decision, dict) else decision)
        return self.handle(normalized)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("protocol", "observe", "serve"))
    parser.add_argument("--url", default="http://127.0.0.1:8768")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "analysis" / ("policy-" + uuid.uuid4().hex[:12]))
    parser.add_argument("--task", default="Pick up the tennis ball.")
    args = parser.parse_args()
    if args.mode == "protocol":
        print(json.dumps(protocol(), indent=2))
        return
    adapter = R5PolicyAdapter(ReadOnlyWorkbench(args.url), args.output, args.task)
    result = adapter.observe()
    print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
    if args.mode == "observe":
        return 0 if result["proposal_ready"] else 2
    for line in sys.stdin:
        try:
            decision = json.loads(line)
            # Also rejects NaN, including in fields later rejected by the schema.
            json.dumps(decision, allow_nan=False)
            result = adapter.handle(decision)
        except (ValueError, TypeError) as exc:
            result = {"accepted": False, "executed": False, "error": str(exc)}
        print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
    # EOF and Ctrl+C have no homing, opening, enable, or stop side effects.


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
