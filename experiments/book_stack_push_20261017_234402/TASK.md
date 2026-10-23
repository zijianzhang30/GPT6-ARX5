# Cooperative book stack push — incomplete

## Requested task

> Use the edges of both the left and right grippers to cooperatively push both books together as a single stack fully inside the black rectangular outline, keeping them stacked throughout and without grasping them.

Retain three video streams and Markdown records.

## Outcome

**Not completed.** The books remain stacked outside the black rectangular outline. No successful coordinated push or full containment was observed. No gripper closing command or grasp was requested. The gripper openings were maintained during all positioning steps.

Live visual inspection showed two white books stacked before the trial. Both arms made bounded positioning movements with pauses and three-camera observations. The intended contact at the rear edge of both book layers was never confirmed. The stack appeared essentially unchanged in the final external view. Small inter-book offsets are visible; exact alignment and absence of damage are not certified by these images.

## Stop and final robot state

At rear12, the right arm exceeded the 2.5-degree endpoint settling criterion (approximately 2.74 degrees at joint 4). Both arms were held. A bounded reversal toward the preceding right-arm target was attempted. At 23:51:16 local time, the right controller reported **Timed trajectory tracking limit reached** and disabled. The recording supervisor then requested stop for the other arm. Both arms changed pose after control was disabled; this was not a commanded return to their initial poses.

The captured post-stop right joint 5 reading was approximately 89.49 degrees, beyond its reported software upper bound of 85 degrees. No re-enable, limit change, forced retry, or automatic homing was attempted. Both controllers were verified disabled at finalization. Local inspection and supported recovery are needed before another motion attempt. Return to the initial pose was **not** completed.

## Method and evidence scope

Only the supplied task, fresh live camera/telemetry observations, and the active local robot-control software and kinematic model were used. No skills, prior experiment records, cloud storage, or local task caches were read. A second agent reviewed only images created during this run; it issued no robot commands.

Three local camera streams were recorded at a nominal 10 fps: external overview, can0/left wrist (`gemini`), and can1/right wrist (`gemini_right`). The external image reverses the apparent arm positions: can0 is at image-right and can1 at image-left.

Initial camera fetching via an inherited HTTP proxy failed; direct localhost access succeeded before any enabling. A first preflight recording captured stationary hold qualification. The recorder was then restarted after correcting the trajectory timestamp clock, with all preflight clips retained. There is an unrecorded gap between these two recorder sessions while both arms were disabled; the complete videos concatenate the two segments and do not represent an uninterrupted wall-clock timeline. Task positioning occurred in the second recording session.

An initial trajectory dispatch returned HTTP 400 after hold re-anchoring. No intended approach displacement was observed; the exact error response body was not captured. Subsequent segments used the controller's held command as the trajectory start, preserving the existing timing, speed, joint-range, and tracking checks. No protection limits were changed.

## Videos

All original segments are retained. Each complete file was decoded through its final frame after concatenation. Detailed frame counts, sizes, and SHA-256 hashes are in [video_validation.json](video_validation.json).

| Stream | Complete recording | Resolution | Frames | Encoded duration |
| --- | --- | --- | --- | --- |
| external | [external_complete.mp4](external_complete.mp4) | 640×480 | 3980 | 398.0 s |
| gemini | [gemini_complete.mp4](gemini_complete.mp4) | 848×480 | 3980 | 398.0 s |
| gemini_right | [gemini_right_complete.mp4](gemini_right_complete.mp4) | 848×480 | 3980 | 398.0 s |

## Observation timeline

Times use the machine's local timezone (Asia/Shanghai). Full commands and current-run telemetry are retained in [events.jsonl](events.jsonl) and [motions.jsonl](motions.jsonl).

| Local timestamp | Observation |
| --- | --- |
| 2026-10-17T23:44:59+08:00 | preflight |
| 2026-10-17T23:45:12+08:00 | enabled |
| 2026-10-17T23:45:23+08:00 | final |
| 2026-10-17T23:45:29+08:00 | preflight |
| 2026-10-17T23:45:43+08:00 | enabled |
| 2026-10-17T23:46:14+08:00 | approach01 |
| 2026-10-17T23:46:44+08:00 | approach02 |
| 2026-10-17T23:47:06+08:00 | approach03 |
| 2026-10-17T23:47:23+08:00 | approach04 |
| 2026-10-17T23:47:50+08:00 | approach05 |
| 2026-10-17T23:48:18+08:00 | align06 |
| 2026-10-17T23:48:36+08:00 | align07 |
| 2026-10-17T23:48:55+08:00 | align08 |
| 2026-10-17T23:49:39+08:00 | align09 |
| 2026-10-17T23:50:11+08:00 | rear10 |
| 2026-10-17T23:50:30+08:00 | rear11 |
| 2026-10-17T23:50:49+08:00 | rear12 |

## Key artifacts

- [Initial external view](external_initial.jpg)
- [Last held external view](rear12_external.jpg)
- [Post-stop external view](fault_external.jpg)
- [Post-stop left wrist](fault_gemini.jpg)
- [Post-stop right wrist](fault_gemini_right.jpg)
- [Post-stop telemetry](fault_state.json)
- [Final controller state](final_state.json)

No success claim is made from tool-command acceptance. The physical placement criterion was not met.

Final independent visual review agreed that the outlined region remained empty and the books remained stacked. No gross separation or major damage was visible; minor damage cannot be assessed from the available images. Each of the three complete MP4s contains 3,980 decoded frames (398.0 seconds at nominal 10 fps).

## 后续用户请求：恢复初始位姿

用户随后要求双臂恢复初始位姿。经现场处理右臂越界、分段自动回位和最终核验，双臂已回到本轮初始位姿附近并解除使能。最大关节偏差为左臂 1.049°、右臂 0.372°。恢复期间出现上层书封面受夹爪边缘干涉、现场人员整理的情况，详见 [恢复记录](recovery_20261017_235250/RECOVERY.md) 及新增三路视频。原推书任务仍未完成。
