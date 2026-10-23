# Live two-block sweeping trial — incomplete

Date: 2026-10-18. All times below are Asia/Shanghai (UTC+08:00).

Requested task: the right arm holds the dustpan while the left arm grasps the brush beside the green box and sweeps both blue cubes into the dustpan, then sets both tools down.

The task was stopped after three unsuccessful dustpan grasp approaches and test lifts. **0/2 cubes were swept.** The dustpan was not securely lifted, the brush was never grasped, and the left arm received no task motion or gripper commands. Both tools remained supported by the tabletop; the brush also leaned against the green box. The requested coordinated sweeping and subsequent tool placement were not performed.

## 90 秒三视图合成视频

按后续要求保存：[90 秒合成 MP4](sweep_three_views_90s.mp4)。左上为左腕相机，右上为右腕相机，下方为头部相机（本轮 `external/top` 画面）。原始三路分段录像全部保留。

成片采用 H.264 编码，1280×1080、30 fps，共 2,700 帧，时长 90.0 秒，文件大小 10,865,606 字节（约 10.9 MB）。按真实时间统一约 12.94 倍加速，保留原画面比例、原始时间及缺帧/重复帧标记。原录制中断的 28.603259 秒在成片约 42.37–44.57 秒显示为 2.2 秒黑底缺口提示，没有使用停帧冒充连续录像。

生成参数和逐帧来源分别见 [合成参数](sweep_three_views_90s.json) 与 [帧映射](sweep_three_views_90s_frames.jsonl)；可用本轮 [合成脚本](compose_90s.py) 重现。[独立验证](sweep_three_views_90s_verification.json) 已通过：2,700 帧完整解码、容器时长精确 90.0 秒，抽帧确认布局及缺口提示正确。

## Constraint deviation

The main robot skill was mistakenly opened once before proceeding, contrary to the user's instruction. No further skills, cloud storage, cached calibration profiles, or previous trial records were used. The already running host dispatcher source was inspected solely to establish its current control interface. This report uses only this run's initial state, event logs, recording manifests, and live observations.

## Initial state and control context

- The live scene contained a dustpan, two blue cubes between the tools, and a brush beside/against a green box.
- Physical left was routed through `can0` / port `8765`; physical right through `can1` / port `8766`. The external, left-wrist, and right-wrist views were distinct.
- Both arms initially reported enabled, stationary holding states, with no SDK error codes. The initial feedback is saved in [initial_state.json](initial_state.json).
- The active host did not expose the needed gripper command. A fresh guarded session adopted the current arm state before right-arm movement; event logs record subsequent motion and gripper commands.
- The kinematic model ends at `link6`. The fingertip offset was not verified, so stated Cartesian increments refer to nominal wrist/link6 targets and do not establish fingertip position or actual tool lift height.

## Dustpan grasp approaches

| Approach | Time | Executed actions | Observed result |
| --- | --- | --- | --- |
| 1. Shallow handle-loop approach | 12:50:12–12:54:46 | Raised the empty right gripper for clearance, tilted and aligned it over the loop, opened the jaws, approached, and closed gradually. Issued nominal 10 mm and then 15 mm upward test moves. | Dustpan remained table supported; no secure grasp or retained lift was verified. |
| 2. Deeper handle approach | 12:55:45–12:57:11 | Reopened the jaws, corrected 10 mm forward and 25 mm down, then lowered another 8 mm. Closed incrementally and issued a nominal 12 mm upward test move, followed by small closure adjustments. | Dustpan remained table supported; the second approach did not establish a secure grasp. |
| 3. Steeper solid-neck approach | 12:57:55–13:01:27 | Released incidental contact, raised the empty jaws, changed to a nominal 70-degree pitch, aligned toward the solid handle neck, lowered and re-centered in short steps, and closed incrementally. Issued a nominal 15 mm upward test move. | Dustpan was not securely lifted. Further grasp attempts were stopped. |

The first approach showed shallow, asymmetric contact around the loop in the live wrist view. Later approaches changed both seating depth and approach angle, but the observations did not verify a retained tool lift. The exact contact geometry and cause of failure remain unconfirmed.

At 13:01:53 the session recorded the decision to end grasp attempts and prepare withdrawal. The right jaws were reopened to release incidental contact, followed by a nominal 30 mm clearance lift of the visibly empty gripper and withdrawal through elevated waypoints observed during this run. The right arm then returned to the initial commanded joint reference, and its original gripper command was restored. Final checks are recorded below.

## Three-view MP4 recordings and interruption

Recordings are stored in [video/](video/) and [video_02/](video_02/). Each recording uses the external/top, left-wrist, and right-wrist views at a nominal 10 fps, with 60-second MP4 segments. The manifests describe a shared software sampling grid using HTTP receive timestamps, not synchronized hardware exposure. Missing sampling slots and duplicate frames are represented in the recording metadata; continuous fresh-frame coverage is not claimed.

- First recording: [video/manifest.json](video/manifest.json), started at `2026-10-18T12:45:58.278215+08:00` and ended at `2026-10-18T12:55:06.292240+08:00`. The manifest reports `completed` with stop reason `SIGTERM`; the origin of that signal was not established.
- Recording gap: **28.603259 seconds**, from that end timestamp to `2026-10-18T12:55:34.895499+08:00`. Both arms were held stationary. The next renewal command was rejected by the recorder health check before movement, and no task motion was issued during the gap.
- Second recording: [video_02/manifest.json](video_02/manifest.json), started at `2026-10-18T12:55:34.895499+08:00` and ended at `2026-10-18T13:05:22.772603+08:00`, after withdrawal and the final stationary checks. The finalized manifest reports `completed` with stop reason `stop_file` and 5,877 frames per view.

All 60 MP4 segments passed full-frame decoding: 34,071 frames across the three views, with 11,357 frames and 1,135.7 seconds of video per view across the two recording periods. See [part 1 validation](video_verification_part1.md) and [part 2 validation](video_verification_part2.md). The retained MP4s total 385,756,139 bytes.

| Period | View | Frames | Missing-slot placeholders | Duplicate frames | Request errors |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | External/top | 5,480 | 11 | 6 | 0 |
| 1 | Left wrist | 5,480 | 10 | 18 | 0 |
| 1 | Right wrist | 5,480 | 10 | 10 | 0 |
| 2 | External/top | 5,877 | 14 | 9 | 0 |
| 2 | Left wrist | 5,877 | 12 | 11 | 0 |
| 2 | Right wrist | 5,877 | 13 | 18 | 0 |

## Evidence and limits

- [session_events.jsonl](session_events.jsonl): initial session adoption.
- [session_3942822_events.jsonl](session_3942822_events.jsonl): first approach and test lifts.
- [session_4120407_events.jsonl](session_4120407_events.jsonl): subsequent approaches, test lift, release, and withdrawal.
- [initial_state.json](initial_state.json): initial arm feedback and control state.
- [images/](images/): this run's saved camera observations.

Command acceptance and settling do not prove a grasp or collision clearance. The logs explicitly retain `grasp_verified: false` and `collision_checked: false`; reported holding states are not a validated physical safety stop. The result is an incomplete manipulation trial, not a successful sweep or successful tool-placement sequence.

## Final retreat verification

Two final checks at approximately 13:05:16 and 13:05:17 found both arms enabled and holding, with no active trajectory or reported SDK error codes. Relative to their initial commanded joint references, the maximum measured joint error was 0.0571 degrees for the left arm and 0.6994 degrees for the right arm; both were within the 2.5-degree settling tolerance. Both gripper command targets matched their initial values. See [verification results](final_verification.json), [first feedback snapshot](final_state_1.json), and [second feedback snapshot](final_state_2.json).

The final [external view](images/final_2_external.jpg), [left-wrist view](images/final_2_gemini.jpg), and [right-wrist view](images/final_2_gemini_right.jpg) show the retracted arms, dustpan and brush still on the tabletop, and both blue cubes outside the dustpan. No successful tool placement is claimed because neither tool was securely picked up.

The current-run control host (PID 4120407, `session.py`) remains running to maintain both arms' guarded hold and heartbeat. A read-only [post-recording state check](active_hold.json) at 13:06:53 confirmed that the host existed and both arms were stationary, enabled, and holding without reported faults or active trajectories. Recording has ended; the robot remains enabled. This holding state is not a validated safety stop.
