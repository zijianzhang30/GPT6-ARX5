"""R5 plug-ins for the original GPT-Policy loop and supervised_policy host."""
from concurrent.futures import ThreadPoolExecutor
import json
import sys
import time

from jsonschema import Draft202012Validator

from motion_safety import finite, vector
from policy_adapter import ROOT, CAMERAS, object_schema, read_camera
from r5_visual_feedback import WristFeedback
from visual_control import detect_ball


SOURCE = ROOT / "vendor" / "GPT-Policy-main" / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

COMMON = {"observation_id": {"type": "string", "minLength": 1},
          "note": {"type": "string", "minLength": 1, "maxLength": 500}}
ARGUMENTS = {
    "observe": object_schema(COMMON),
    "check_joint_step": object_schema({**COMMON, "delta_rad": {
        "type": "array", "minItems": 6, "maxItems": 6, "items": {"type": "number"}}}),
    "move_joint_step": object_schema({**COMMON, "delta_rad": {
        "type": "array", "minItems": 6, "maxItems": 6, "items": {"type": "number"}}}),
    "move_joints": object_schema({**COMMON, "positions": {
        "type": "array", "minItems": 6, "maxItems": 6, "items": {"type": "number"}}}),
    "set_gripper": object_schema({**COMMON, "gripper_raw": {
        "type": "number", "minimum": 0, "maximum": 5}}),
    "done": object_schema({"summary": {"type": "string", "minLength": 1},
                            "hindsight": {"type": "string"}}),
    "give_up": object_schema({"reason": {"type": "string", "minLength": 1},
                               "hindsight": {"type": "string"}}),
}
INSTRUCTIONS = """Control a single ARX R5 using fresh images and measured feedback.
left is the Gemini wrist RGB camera; top is an external RGB camera, not
necessarily overhead or fixed. The operator may hold or reposition it; do not
attribute external image shifts to robot motion without measured feedback.
Neither provides depth. Camera calibration and validated
TCP are unavailable; do not invent metric geometry or torque.
raw_state.pose/points/frames are unvalidated URDF visualization data, not a
calibrated fingertip TCP or evidence of physical workspace clearance.
Use one structured tool selection at a time. move_joints.positions contains six
absolute angles in RADIANS, J1..J6 order. Host limits are 12 degrees per joint,
16.5 degrees combined change, 2 degrees inside joint limits and session budgets.
move_joint_step.delta_rad contains six relative joint increments in RADIANS,
anchored to the latest observed measured joint pose. Prefer it for small local
corrections; it is NOT a Cartesian displacement or a direction inferred from pixels.
check_joint_step accepts the same delta_rad and checks numeric limits without
moving or spending motion budget. Acceptance is not a clearance/collision check.
observe requests a fresh view/state without movement. Observation and planning
still consume decision turns; neither resets motion budgets or latched faults.
set_gripper.gripper_raw uses vendor 0..5 units, NOT normalized opening or metres.
Use verified opening-direction evidence from the supplied setup context when
present; do not discard observed calibration as unknown. Physical ball clearance
must still be judged from current images. Never infer metric width from raw units.
Copy observation_id from the latest state for every motion. Never replay old
actions. Arm and gripper movements must be separate. Inspect ball, fingertips,
table, camera bodies, cables and clearance in the available views before every step.
The local controller holds the last submitted targets while you deliberate.
Requested, submitted and measured positions differ. A settled command, gripper
stall or your done message does not prove grasp/contact. Request done only with
current visual evidence of a stable lifted ball; a human labels final success.
Closed-loop grasp sequence: observe, approach/align in one supported small step,
inspect the fresh image and measured result, then correct. Do not require the
entire grasp trajectory or exact object depth before a contact-free correction
whose direction and clearance are established. Do not guess joint directions.
Use reviewed action examples or observed local responses as direction evidence,
checking that the pose and camera mounting still apply. Historical examples are
not trajectories to replay or proof of current clearance. Keep gripper opening
unchanged during approach. Close separately only after alignment and clearance
are established; then lift in a separately verified step and inspect retention.
The visual_feedback field contains a colour/shape candidate and image changes,
not depth or proof of approach/contact. Check the actual images. A larger ball
or smaller pixel error alone does not establish safe approach or task success.
After each step, compare expected and measured joint/image changes; do not repeat
an ineffective or wrong-direction step blindly. Consider a smaller correction,
another supported direction, or a fresh observation before declaring failure.
Persistence follows GPT-Policy: uncertainty about the eventual grasp, a rejected
numeric preview, or one missed alignment does not alone establish impossibility.
Use check_joint_step for uncertain numeric alternatives and observe for transient
occlusion; do not repeat identical observations indefinitely. Do not call give_up
while a reasonable supported safe continuation remains. If every continuation
lacks direction/clearance evidence, or feedback is missing/faulted, stop and
report the specific evidence and alternatives considered. Never use exploratory
motion to bypass an unresolved collision risk, reset budgets or infer calibration.
Completion keeps hold for operator handoff;
it never automatically homes the arm or opens the gripper.
"""


def agent_context(camera_mode="both"):
    from gpt_policy.harness.models import AgentContext
    if camera_mode not in ("both", "wrist"):
        raise ValueError("Unknown camera mode")
    instructions = INSTRUCTIONS
    if camera_mode == "wrist":
        instructions += """
This run supplies ONLY the left wrist RGB camera. No external/top image is
available. Do not assume a second view or infer hidden clearance from its absence.
Monocular pixels do not establish depth or table height. Use give_up when the
available view cannot establish clearance for the proposed movement.
"""
    descriptions = {
        "observe": "Acquire fresh images and feedback without actuator targets.",
        "check_joint_step": "Read-only numeric preview of relative joint radians; no collision check.",
        "move_joint_step": "Execute one bounded relative joint step, then hold and observe.",
    }
    tools = [{"type": "function", "function": {"name": name,
              "description": descriptions.get(name, name.replace("_", " ")), "parameters": schema}}
             for name, schema in ARGUMENTS.items()]
    return AgentContext(instructions, tools, object_schema({
        "name": {"type": "string", "enum": list(ARGUMENTS)},
        "arguments": {"anyOf": list(ARGUMENTS.values())}}))


class ValidatedAgent:
    def __init__(self, agent):
        self.agent = agent

    def __getattr__(self, name):
        return getattr(self.agent, name)

    def decide(self, turn):
        decision = self.agent.decide(turn)
        json.dumps(decision, allow_nan=False)
        if (not isinstance(decision, dict) or set(decision) - {"name", "arguments", "_wire"}
                or not isinstance(decision.get("name"), str) or decision["name"] not in ARGUMENTS):
            raise ValueError("Unsupported R5 model decision")
        Draft202012Validator(ARGUMENTS[decision["name"]]).validate(decision.get("arguments"))
        return decision


class R5ToolExecutor:
    def __init__(self, robot):
        self.robot = robot

    def is_terminal(self, name):
        return name in ("done", "give_up")

    def execute(self, name, arguments, state, history):
        if name not in ("observe", "check_joint_step", "move_joint_step", "move_joints", "set_gripper"):
            raise ValueError("Unsupported R5 motion tool")
        Draft202012Validator(ARGUMENTS[name]).validate(arguments)
        if arguments["observation_id"] != state["observation_id"]:
            raise ValueError("Tool does not reference the current observation")
        if name == "observe":
            self.robot.check()
            return {"executed": False, "next_observation": "fresh images and measured state",
                    "grasp_verified": False}
        if name == "check_joint_step":
            return self.robot.check_joint_step(arguments)
        return self.robot.execute(name, arguments)


class R5Cameras:
    def __init__(self, client, *, camera_mode="both"):
        if camera_mode not in ("both", "wrist"):
            raise ValueError("Unknown camera mode")
        self.client = client
        self.sources = dict(CAMERAS) if camera_mode == "both" else {"left": CAMERAS["left"]}
        self.clients = {name: client for name in self.sources}
        self.metadata = {}
        self.devices = None
        self.failure = None

    def snapshot(self, *, after=None):
        from gpt_policy.hardware.camera import CapturedImage
        if self.failure:
            raise RuntimeError(self.failure)
        try:
            with ThreadPoolExecutor(max_workers=len(self.sources)) as pool:
                futures = {name: pool.submit(read_camera, self.clients[name], key)
                           for name, key in self.sources.items()}
                samples = {name: future.result() for name, future in futures.items()}
            devices = tuple(samples[name][1]["device"] for name in self.sources)
            if len(set(devices)) != len(self.sources) or self.devices is not None and self.devices != devices:
                raise ValueError("Camera identities are duplicated or changed")
            now = time.monotonic()
            if any(not 0 <= now-metadata["received_monotonic_s"] <= 1 for _, metadata in samples.values()):
                raise ValueError("Camera receipts are stale")
            self.devices = devices
            self.metadata = {name: metadata for name, (_, metadata) in samples.items()}
            self.metadata["left"]["ball_detection"] = detect_ball(samples["left"][0].data)
            # Upstream captured_at is a host receipt, never a sensor exposure timestamp.
            return {name: CapturedImage(name, image.data, image.mime_type, image.width,
                                       image.height, time.time(), source_timestamp_s=None,
                                       source_clock=None) for name, (image, _) in samples.items()}
        except Exception as exc:
            self.failure = str(exc)
            raise

    def describe(self, images):
        return [{"name": name, "role": "wrist RGB" if name in ("left", "right") else "external RGB (may move)",
                 **self.metadata[name], "intrinsics": None, "extrinsics": None}
                for name in images]


class R5DualCameras(R5Cameras):
    """Three-view input for a coordinated policy; does not enable either arm."""

    def __init__(self, left_client, right_client):
        if getattr(left_client, 'arm', None) != 'left' or getattr(right_client, 'arm', None) != 'right':
            raise ValueError('Dual views require explicitly routed left and right arm clients')
        super().__init__(left_client)
        self.sources = {'left': 'gemini', 'right': 'gemini', 'top': 'external'}
        self.clients = {'left': left_client, 'right': right_client, 'top': left_client}


def observation(instruction, state, cameras, previous=None, step=0):
    # The upstream default formatter drops raw gripper units and observation IDs.
    return json.dumps({"instruction": instruction, "state": state, "images": cameras,
                       "previous_result": json.loads(previous) if previous else None,
                       "env_step": step}, allow_nan=False)


def cartesian_state_details(state):
    raw = state['raw_state']
    return dict(tcp_command_xyzquat=state['tcp_command_xyzquat'],
                motion_budget=state['motion_budget'],
                gripper_step_limit_normalized=state['gripper_step_limit_normalized'],
                gripper_open_step_limit_normalized=state['gripper_open_step_limit_normalized'],
                gripper_next_opening_bounds=state.get('gripper_next_opening_bounds'),
                demonstrated_pregrasp_guide=state.get('demonstrated_pregrasp_guide'),
                joint_positions_deg=raw['joints_deg'], joint_command_deg=raw['command_deg'],
                joint_tracking_error_deg=raw['tracking_error_deg'],
                joint_lower_deg=raw['lower_deg'], joint_upper_deg=raw['upper_deg'],
                joint_limit_margin_deg=[min(q-lo, hi-q) for q, lo, hi in zip(
                    raw['joints_deg'], raw['lower_deg'], raw['upper_deg'])],
                near_singular=raw.get('near_singular'))


def motion_budget_headroom(state):
    """Identify a nearly spent software segment before asking for another action."""
    boundaries = {}
    for side, arm in state.get('arms', {'arm': state}).items():
        budget = arm.get('motion_budget', {})
        limits = budget.get('limits', {})
        if budget.get('fault_latched'):
            continue
        travel = limits.get('session_joint_travel_deg')
        used = budget.get('proposed_joint_travel_deg')
        if finite(travel) and travel > 0 and finite(used) and used >= .95*travel:
            boundaries[side] = {'reason': 'joint_travel', 'remaining_deg': travel-used}
            continue
        count, accepted = limits.get('session_proposals'), budget.get('accepted_proposals')
        if finite(count) and count > 0 and finite(accepted) and accepted >= count:
            boundaries[side] = {'reason': 'proposal_count', 'remaining': count-accepted}
            continue
        anchor = budget.get('anchor_joints_deg')
        measured = arm.get('raw_state', {}).get('joints_deg')
        excursion = limits.get('session_excursion_deg')
        if finite(excursion) and excursion > 1 and vector(anchor) and vector(measured):
            remaining = excursion-max(abs(a-b) for a, b in zip(anchor, measured))
            if remaining <= 1.:
                boundaries[side] = {'reason': 'joint_excursion', 'remaining_deg': remaining}
    return boundaries


def run_r5_policy(runtime, run_input, robot, cameras, agent, recorder, *, supervisor,
                  display=None, start_agent=True):
    """Use the original loop, not the earlier standalone shadow runner.

    The host retains the agent and device supervisor after return for operator
    handoff. It must not stop heartbeats merely because the model finishes.
    """
    from gpt_policy.runtime.runner import run_loop
    from gpt_policy.harness.waiting import monitor_health
    feedback = WristFeedback()
    cartesian = getattr(runtime, 'policy_interface', 'joint') == 'cartesian'

    def segment_boundary():
        if getattr(robot, 'last_budget_rejection', None) == 'Session gripper travel budget exhausted':
            return 'gripper_budget_boundary'
        rejection = getattr(robot, 'last_plan_rejection', None)
        if isinstance(rejection, str) and any(text in rejection for text in (
                'session envelope', 'session joint travel budget')):
            return 'motion_budget_boundary'
        if getattr(runtime, 'auto_renew_budgets', False) is True:
            boundaries = motion_budget_headroom(robot.state())
            if boundaries:
                recorder.write('motion_budget_headroom', {'arms': boundaries})
                return 'motion_budget_boundary'
        return None

    def format_observation(instruction, state, descriptions, previous=None, step=0):
        if cartesian:
            from gpt_policy.harness.protocol import observation as upstream_observation
            payload = json.loads(upstream_observation(instruction, state, descriptions, previous, step))
            if 'arms' in state:
                for side, arm_state in state['arms'].items():
                    payload['state'][side].update(cartesian_state_details(arm_state))
            else:
                payload['state'].update(cartesian_state_details(state))
            payload['host_segment'] = getattr(recorder, 'segment', 0)
            if not start_agent and step == 0:
                payload['host_continuation'] = (
                    'The host renewed this attended segment at measured powered hold. '
                    'Keep prior action/image direction evidence from this same arm and scene; '
                    'the budget renewal does not reverse coordinate axes or erase prior outcomes. '
                    'Use the fresh command pose and images for the next action.')
            return json.dumps(payload, allow_nan=False)
        state["visual_feedback"] = feedback.update(state, descriptions, previous)
        return observation(instruction, state, descriptions, previous, step)
    if supervisor.robot is not robot:
        raise ValueError('Supervisor must own this policy backend')
    try:
        supervisor.check()
        robot.check()
        if start_agent:
            with monitor_health(supervisor.check, deadline=time.monotonic() + 15):
                agent.start(robot.context(run_input.instruction) if cartesian else
                            agent_context(getattr(runtime, "camera_mode", "both")))
        supervisor.check()
        if cartesian:
            from r5_cartesian import CartesianAgent
            validated = CartesianAgent(agent, robot.catalog, getattr(robot, 'active_arms', ('left',)))
            executor = robot.executor()
        else:
            validated, executor = ValidatedAgent(agent), R5ToolExecutor(robot)
        return run_loop(runtime, run_input, robot, cameras, cameras, validated,
                        executor, recorder, observation_fn=format_observation,
                        health_check=supervisor.check, display=display,
                        finish_fn=robot.finish, fail_on_state_error=True,
                        segment_boundary=segment_boundary if cartesian else None)
    except BaseException:
        supervisor.close()
        raise
