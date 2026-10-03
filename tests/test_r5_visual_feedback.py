import copy
import json
import unittest

from r5_visual_feedback import WristFeedback


class WristFeedbackTests(unittest.TestCase):
    def sample(self, identifier, x=400, y=200, q=None):
        return ({"observation_id": identifier, "gripper_raw": 4.7,
                 "raw_state": {"joints_deg": q or [0]*6}},
                [{"name": "left", "device": "/dev/wrist", "sequence": identifier,
                  "width": 848, "height": 480,
                  "ball_detection": {"candidate_count": 1, "ball_candidate": {
                      "center_px": [x, y], "axes_px": [100, 100]}}}])

    def executed(self, source="before", q=None, tool="move_joint_step"):
        return json.dumps({"tool": tool, "result": {"source_observation_id": source,
                          "measured_joints_deg": q or [0, 1, 0, 0, 0, 0],
                          "settle": {"settled": True}}})

    def test_measured_step_produces_only_image_space_response(self):
        feedback = WristFeedback()
        feedback.update(*self.sample("before"))
        result = feedback.update(*self.sample("after", y=190, q=[0, 1, 0, 0, 0, 0]), self.executed())
        self.assertEqual(result["after_motion"]["center_delta_px"], [0, -10])
        self.assertEqual(result["local_response_candidate"]["joint"], 2)
        self.assertEqual(result["local_response_candidate"]["pixels_per_measured_degree"], [0, -10])
        self.assertTrue(result["local_response_candidate"]["requires_visual_confirmation"])
        for key in ("metric_position_available", "clearance_verified", "grasp_verified"):
            self.assertFalse(result[key])

    def test_preview_observe_or_unmatched_action_never_establish_direction(self):
        for previous in (self.executed(tool="observe"), self.executed(tool="check_joint_step"),
                         self.executed(source="unrelated"), json.dumps({"tool": "move_joint_step", "error": "rejected"})):
            feedback = WristFeedback()
            feedback.update(*self.sample("before"))
            result = feedback.update(*self.sample("after", y=180, q=[0, 1, 0, 0, 0, 0]), previous)
            self.assertNotIn("after_motion", result)

    def test_ambiguous_lost_or_clipped_candidate_breaks_comparison(self):
        for count, x in ((0, 400), (2, 400), (1, 10)):
            feedback = WristFeedback()
            feedback.update(*self.sample("before"))
            state, cameras = self.sample("middle", x=x)
            cameras[0]["ball_detection"]["candidate_count"] = count
            self.assertEqual(feedback.update(state, cameras)["status"], "missing_ambiguous_or_clipped")
            result = feedback.update(*self.sample("after", q=[0, 1, 0, 0, 0, 0]), self.executed())
            self.assertNotIn("after_motion", result)

    def test_camera_change_stale_sequence_or_unexpected_motion_blocks_comparison(self):
        base_state, base_cameras = self.sample("after", q=[0, 1, 0, 0, 0, 0])
        for changed in ("device", "size", "sequence", "pose"):
            state, cameras = copy.deepcopy((base_state, base_cameras))
            if changed == "device":
                cameras[0]["device"] = "/dev/another"
            elif changed == "size":
                cameras[0]["width"] = 640
            elif changed == "sequence":
                cameras[0]["sequence"] = "before"
            else:
                state["raw_state"]["joints_deg"][0] += 1
            feedback = WristFeedback()
            feedback.update(*self.sample("before"))
            self.assertNotIn("after_motion", feedback.update(state, cameras, self.executed()))

    def test_multiple_joints_or_large_candidate_jump_cannot_label_joint_direction(self):
        for q, x in (([1, 1, 0, 0, 0, 0], 400), ([0, 1, 0, 0, 0, 0], 600)):
            feedback = WristFeedback()
            feedback.update(*self.sample("before"))
            result = feedback.update(*self.sample("after", x=x, q=q), self.executed(q=q))
            self.assertIn("after_motion", result)
            self.assertNotIn("local_response_candidate", result)


if __name__ == "__main__":
    unittest.main()
