"""Image-space feedback for the policy, never a depth estimator or motion planner."""
import copy
import json
import math

from motion_safety import finite, vector


class WristFeedback:
    def __init__(self):
        self.previous = None

    @staticmethod
    def _sample(state, descriptions):
        camera = next((c for c in descriptions if c.get("name") == "left"), {})
        detection = camera.get("ball_detection", {})
        candidate = detection.get("ball_candidate")
        width, height = camera.get("width"), camera.get("height")
        if (detection.get("candidate_count") != 1 or not isinstance(candidate, dict)
                or not all(finite(v) and v > 0 for v in (width, height))):
            return None
        center, axes = candidate.get("center_px"), candidate.get("axes_px")
        if (not isinstance(center, list) or len(center) != 2
                or not isinstance(axes, list) or len(axes) != 2
                or not all(finite(v) for v in center+axes) or min(axes) <= 0):
            return None
        # A clipped candidate cannot support a meaningful apparent-size comparison.
        radius = max(axes)/2
        if not (radius < center[0] < width-radius and radius < center[1] < height-radius):
            return None
        q = state.get("raw_state", {}).get("joints_deg")
        grip = state.get("gripper_raw")
        if not vector(q) or not finite(grip):
            return None
        return {"observation_id": state["observation_id"], "device": camera.get("device"),
                "sequence": camera.get("sequence"), "size": [width, height],
                "center_px": center, "diameter_px": math.sqrt(axes[0]*axes[1]),
                "joints_deg": q, "gripper_raw": grip}

    def update(self, state, descriptions, previous_result=None):
        sample = self._sample(state, descriptions)
        old, self.previous = self.previous, copy.deepcopy(sample)
        result = {"status": "candidate" if sample else "missing_ambiguous_or_clipped",
                  "metric_position_available": False, "clearance_verified": False,
                  "grasp_verified": False,
                  "note": "Colour/shape candidate only. Verify identity in images. Image changes do not prove approach, contact or lift."}
        if sample is None:
            return result
        result.update(center_px=sample["center_px"], diameter_px=sample["diameter_px"])
        if not old or not previous_result:
            return result
        previous = json.loads(previous_result)
        execution = previous.get("result", {})
        if (previous.get("tool") not in ("move_joints", "move_joint_step")
                or execution.get("source_observation_id") != old["observation_id"]
                or execution.get("settle", {}).get("settled") is not True
                or not sample["device"] or sample["device"] != old["device"]
                or sample["sequence"] == old["sequence"] or sample["size"] != old["size"]
                or not vector(execution.get("measured_joints_deg"))
                or max(abs(a-b) for a, b in zip(sample["joints_deg"], execution["measured_joints_deg"])) > .5):
            return result
        delta = [a-b for a, b in zip(sample["joints_deg"], old["joints_deg"])]
        pixels = [a-b for a, b in zip(sample["center_px"], old["center_px"])]
        ratio = sample["diameter_px"]/old["diameter_px"]
        result["after_motion"] = {"from_observation_id": old["observation_id"],
                                  "center_delta_px": pixels, "apparent_diameter_ratio": ratio,
                                  "measured_joint_delta_deg": delta,
                                  "association": "unverified colour/shape match; inspect both images"}
        dominant = max(range(6), key=lambda i: abs(delta[i]))
        if (abs(delta[dominant]) >= .2 and all(abs(v) <= .1 for i, v in enumerate(delta) if i != dominant)
                and abs(sample["gripper_raw"]-old["gripper_raw"]) <= .03
                and .8 <= ratio <= 1.25
                and math.hypot(*pixels) <= .15*min(sample["size"])):
            result["local_response_candidate"] = {
                "joint": dominant+1, "pixels_per_measured_degree": [v/delta[dominant] for v in pixels],
                "requires_visual_confirmation": True,
                "note": "One local sample, not calibration. Object/camera motion can invalidate it; do not extrapolate to another pose."}
        return result
