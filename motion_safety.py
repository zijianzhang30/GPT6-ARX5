"""Software-only proposal limits. No actuation, braking, or collision guarantee."""
import math


JOINT_STEP_DEG = 24.0
JOINT_STEP_NORM_DEG = 33.0
JOINT_MARGIN_DEG = 2.0
GRIPPER_STEP_RAW = 0.1
GRIPPER_CLOSE_STEP_RAW = 1.0
GRIPPER_OPEN_SPEED_MULTIPLIER = 5.0
EMPTY_GRIPPER_OPEN_STEP_RAW = 0.5
SUPERVISED_SPEED = 0.3
# Settling leaves headroom for feedback variation during the transition to hold.
POLICY_SETTLE_ERROR_DEG = 2.5
POLICY_HOLD_ERROR_DEG = 3.0
POLICY_TRACKING_ERROR_DEG = 3.0
POLICY_REVERSE_DEADBAND_DEG = .3
SESSION_EXCURSION_DEG = 40.0
SESSION_JOINT_TRAVEL_DEG = 120.0
SESSION_GRIPPER_TRAVEL_RAW = 5.0
SESSION_PROPOSALS = 20


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def gripper_step_limit(target, reference):
    # This R5's verified raw direction is increasing=open, decreasing=close.
    return GRIPPER_CLOSE_STEP_RAW if target < reference else GRIPPER_STEP_RAW


def vector(value):
    return isinstance(value, (list, tuple)) and len(value) == 6 and all(finite(x) for x in value)


def feedback_issues(state, *, require_gripper_target=True):
    """Common numeric telemetry checks; callers handle mode and ownership."""
    if not isinstance(state, dict):
        return ["Missing robot state"]
    issues = []
    for key in ("joints_deg", "lower_deg", "upper_deg", "tracking_error_deg"):
        if not vector(state.get(key)):
            issues.append(f"Invalid {key}")
    if all(vector(state.get(key)) for key in ("joints_deg", "lower_deg", "upper_deg")):
        if any(not lo < hi or not lo <= q <= hi for q, lo, hi in zip(
                state["joints_deg"], state["lower_deg"], state["upper_deg"])):
            issues.append("Feedback is outside joint limits or limits are invalid")
    for key in ("feedback_age_ms", "rx_age_ms"):
        if not finite(state.get(key)) or not 0 <= state[key] <= 150:
            issues.append(f"{key} is stale or invalid")
    gripper_fields = ('gripper_raw', 'gripper_target_raw') if require_gripper_target else ('gripper_raw',)
    for key in gripper_fields:
        if not finite(state.get(key)) or not 0 <= state[key] <= 5:
            issues.append(f"Invalid {key}; expected vendor units 0..5")
    if state.get("tracking_limited") is not False:
        issues.append("Tracking limit reached or status unavailable")
    if vector(state.get("tracking_error_deg")) and max(map(abs, state["tracking_error_deg"])) > 3.05:
        issues.append("Joint tracking error exceeds 3.05 degrees")
    return issues


class ProposalGuard:
    """Session-scoped budget for *unexecuted* suggestions, with latched faults.

    Travel is the sum of absolute proposed increments, including reversals. It
    is not measured motor travel. Observation cannot reset this budget or fault.
    """
    def __init__(self):
        self.anchor = None
        self.limits = None
        self.devices = None
        self.failure = None
        self.joint_travel = 0.0
        self.gripper_travel = 0.0
        self.proposals = 0

    def latch(self, reason):
        if self.failure is None:
            self.failure = reason

    def require_healthy(self):
        if self.failure is not None:
            raise ValueError("Session fault latched; inspect before a new session: " + self.failure)

    def fail(self, reason):
        self.latch(reason)
        self.require_healthy()

    def check_state(self, state, *, require_gripper_target=True):
        self.require_healthy()
        issues = feedback_issues(state, require_gripper_target=require_gripper_target)
        if issues:
            self.fail("; ".join(issues))
        q = state["joints_deg"]
        bounds = (tuple(state["lower_deg"]), tuple(state["upper_deg"]))
        if self.anchor is None:
            self.anchor = tuple(q)
            self.limits = bounds
        if bounds != self.limits:
            self.fail("Joint limits changed during the session")
        if max(abs(a - b) for a, b in zip(q, self.anchor)) > SESSION_EXCURSION_DEG:
            self.fail("Measured joints left the session envelope")
        self._check_margin(q)

    def check_cameras(self, cameras):
        self.require_healthy()
        devices = tuple(cameras[name].get("device") for name in ("left", "top"))
        if not all(devices) or devices[0] == devices[1]:
            self.fail("Camera identities are missing or duplicated")
        if self.devices is None:
            self.devices = devices
        elif devices != self.devices:
            self.fail("Camera device changed during the session")

    def _check_margin(self, q):
        lower, upper = self.limits
        if any(not lo + JOINT_MARGIN_DEG <= angle <= hi - JOINT_MARGIN_DEG
               for angle, lo, hi in zip(q, lower, upper)):
            self.fail("Joint position enters the 2-degree software limit margin")

    def accept(self, state, target):
        """Validate and debit a proposal atomically; never clamp silently."""
        self.check_state(state)
        if not isinstance(target, dict) or set(target) not in ({"joints_deg"}, {"gripper_raw"}):
            self.fail("Separate arm and gripper proposals are required")
        joint_cost = gripper_cost = 0.0
        if "joints_deg" in target:
            q = target["joints_deg"]
            if not vector(q):
                self.fail("Invalid joint target")
            delta = [a - b for a, b in zip(q, state["joints_deg"])]
            if max(map(abs, delta)) > JOINT_STEP_DEG + 1e-9 or math.hypot(*delta) > JOINT_STEP_NORM_DEG + 1e-9:
                self.fail(
                    f"Step exceeds {JOINT_STEP_DEG:g} deg/joint or "
                    f"{JOINT_STEP_NORM_DEG:g} deg norm"
                )
            self._check_margin(q)
            if max(abs(a - b) for a, b in zip(q, self.anchor)) > SESSION_EXCURSION_DEG:
                self.fail("Proposed target leaves the session envelope")
            joint_cost = sum(map(abs, delta))
        else:
            grip = target["gripper_raw"]
            if not finite(grip) or not 0 <= grip <= 5:
                self.fail("Invalid gripper target")
            gripper_cost = abs(grip - state["gripper_target_raw"])
            limit = gripper_step_limit(grip, state['gripper_target_raw'])
            if gripper_cost > limit + 1e-9:
                self.fail(f"Gripper step exceeds {limit:g} vendor raw units in this direction")
        if self.proposals >= SESSION_PROPOSALS:
            self.fail("Session proposal count exhausted")
        if self.joint_travel + joint_cost > SESSION_JOINT_TRAVEL_DEG + 1e-9:
            self.fail("Session joint travel budget exhausted")
        if self.gripper_travel + gripper_cost > SESSION_GRIPPER_TRAVEL_RAW + 1e-9:
            self.fail("Session gripper travel budget exhausted")
        self.joint_travel += joint_cost
        self.gripper_travel += gripper_cost
        self.proposals += 1
        return self.snapshot()

    def snapshot(self):
        return {"fault_latched": self.failure, "anchor_joints_deg": self.anchor,
                "accepted_proposals": self.proposals,
                "proposed_joint_travel_deg": self.joint_travel,
                "proposed_gripper_travel_raw": self.gripper_travel,
                "limits": {"joint_step_deg": JOINT_STEP_DEG,
                           "joint_step_norm_deg": JOINT_STEP_NORM_DEG,
                           "joint_margin_deg": JOINT_MARGIN_DEG,
                           "gripper_step_raw": GRIPPER_STEP_RAW,
                           "gripper_close_step_raw": GRIPPER_CLOSE_STEP_RAW,
                           "session_excursion_deg": SESSION_EXCURSION_DEG,
                           "session_joint_travel_deg": SESSION_JOINT_TRAVEL_DEG,
                           "session_gripper_travel_raw": SESSION_GRIPPER_TRAVEL_RAW,
                           "session_proposals": SESSION_PROPOSALS},
                "physical_stop_validated": False, "collision_checked": False,
                "execution_available": False}
