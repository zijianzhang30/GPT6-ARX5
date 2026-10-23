# Book extraction trial — 2026-10-20

Task: right arm holds top book steady; left arm extracts middle book 5 cm.
Mode: withskills. Consulted tabletop skill, common execution, book extraction, CAN mapping and records/evidence references; project initialization runbook, current controller/recorder source, previous October 6 extraction notes and October 20 controller records. Basic Skill and geometry lessons read from `/home/tuojing/robot_runs/book_stack_push_20261018_140735/github_submission/skills/arx-r5-basic/`. Its book-pushing-specific no-grasp restrictions do not apply to this explicitly requested extraction task.

## Initial state
At 13:55:54 both arms ready/disabled, stationary, owner null, fresh feedback, no error codes. Prior host PID3865515 disappeared during read-only preparation; cause not established. No commands had been sent in this trial. CAN identities and RX growth verified, no SDK/CAN restart. Cameras show books supported on blue box, empty grippers folded clear, no person in work area.

Standard prepare-idle host launched after all three MP4 streams were recording and fresh-frame growth verified. One arm at a time, existing 3.5 degree tracking reserve, 2 degree Cartesian minimum and all supervision retained.

Frozen inherited return reference copied from previous run (13:31 return verified there); new initial state retained separately. This run's work must use current images and feedback.

## Outcome
**Final: 5 cm extraction not achieved.** Three short grip tests did not establish reliable middle-book following. Right-arm load-bearing stabilization was not independently verified. Both arms subsequently returned within the original 2.5° tolerance; stack independently stable. Earlier checkpoints below are historical.

## Personnel clearance pause
At approximately 14:04:35, after a completed left free-space approach, a dark sleeve/person became visible at the upper-left edge of the left wrist image. New motion paused and an explicit clearance confirmation requested. Right holds over the top-book region without verified contact; left remains clear of the book. No grasp or extraction has yet occurred. Three recordings continue.

At 14:06:41 both arms remained ready/enabled/holding, stationary and without errors. Nine bounded approach moves completed; no gripper closure or book pull requested. Personnel confirmation is still pending. Recorder remains active.

Directory renamed to use original user-task start time 13:54:43 according to robot_runs/AGENTS.md. Original controller output path ending 135554 remains a compatibility symlink; controller and recorder were not stopped or restarted.

## Resume after clearance confirmation
User said "continue" at the next turn; treated as the requested confirmation that everyone is outside both arms' movement range. At 14:24:10 both arms remained ready/enabled/holding, stationary with fresh feedback and no errors; the same host PID2213412 and recorder PID2209753 remained alive. Recording remained active through the stationary wait. Fresh images reviewed before resuming.

Recorder received SIGTERM and closed at 2026-10-20T14:26:02.066897+08:00. Restarted recording02 at 2026-10-20T14:26:29.705780+08:00. Stationary gap 27.638883 seconds; no new motion dispatched during gap. Cause of SIGTERM is not established.

### First grip test after clearance resume
- 2026-10-20T14:39:40.690590 local: left closed in bounded steps to normalized 0.1 at the protruding middle edge. A single in-plane TCP command (-9,+9,0) mm (12.7 mm norm) did not show the middle book following. This is not a measured book displacement and does not satisfy the 5 cm goal. No visible top-book/box movement or page deformation. Left withdrew another (-20,+20,0) mm along the clear approach. Right remained fixed, its stabilizing force still unverified.

### Second grip test
- Empty left gripper withdrew, reopened outside stack, and lowered TCP 10 mm before a fresh two-segment approach. Closure to normalized 0.2 showed possible slight edge motion, but a single (-9,+9,0) mm TCP test again did not establish the middle book following the gripper. Top book and box appeared stationary. No further pulling or tightening of this grip; release and change approach along the side edge. Neither 12.7 mm TCP test is counted as book extraction.

### Third grip test and end of extraction attempts
- After a clear-space wrist roll/yaw change, approached the exposed side edge in two lateral increments. The first yaw-only plan was rejected offline at the unchanged J6 tracking reserve; no motion occurred for that plan. Revised roll/yaw passed.
- Closed 0.6 → 0.4 → 0.35 with separate fresh visual reviews. A single +15 mm y TCP test did not establish book-following; the fingers withdrew from the book. Top book and box appeared stationary, no visible page bending.
- Extraction goal NOT ACHIEVED. No verified added book extraction, no 5 cm measurement. Right arm maintained a fixed near-cover pose, but load-bearing stabilization was not verified. Stop advancement after observed slip under the book-extraction skill; do not compensate with tighter closure or harder pulling. Proceed with release, clear withdrawal and controlled return.

### Controlled recording rollover
- Singleton recorder rejected an overlapping recorder before launch. With both arms holding stationary, recording02 closed via STOP at 2026-10-20T14:56:09.589312+08:00; recording03 began at 2026-10-20T14:56:10.088101+08:00. Manifest-to-manifest stationary interval 0.498789 s. No task/return motion dispatched during this interval.

## Final outcome and return

- Three tested grasps: first corner approach, adjusted-height corner approach, revised roll/yaw side-edge approach. Test TCP commands were 12.7 mm, 12.7 mm and 15 mm respectively. None is counted as actual book displacement. Initial protrusion is excluded. No verified 5 cm extraction or successful middle-book grip.
- Right arm maintained its fixed near-cover pose through the tests. Contact/load-bearing support was not proven. No visible top-book or box movement during the tests or withdrawal; subtle unmeasured displacement cannot be excluded.
- Stopped further extraction after repeated lack of progress/slip, under [the task skill](/home/tuojing/.codex/skills/arx-r5-tabletop-tasks/SKILL.md:53): “连续无进展时停止发送新动作”, and its [book-extraction guidance](/home/tuojing/.codex/skills/arx-r5-tabletop-tasks/references/book-extraction.md). Did not compensate by tightening a slipping grip or pulling harder.
- Released/withdrew the empty left hand, raised it in a clear corridor, then completed 20 reviewed left return segments and one planned final Cartesian correction. Original left J2 reference is outside the extra planning margin, so the executable final target used J2=0°, J4=-12.7°, still inside the unchanged original tolerance.
- Lifted right fingertips away from the cover and completed 17 reviewed right return segments. Both arms remained powered and supervised. No runtime robot fault, observed arm collision, or uncontrolled drop.
- Return check 1: 2026-10-20T15:06:14.599956+08:00; check 2: 2026-10-20T15:06:39.843729+08:00. Both passed. Left worst measured error 1.836°, command error 2.023°; right worst measured error 0.459°, command error 0.852°, against the preserved inherited reference. New host initial reference also retained.
- Final images show the books supported on the box with both hands clear. The holding host remains running; ending recording did not disable the robot.
- No manual book repositioning was observed during this trial. Personnel-clearance pause and user's “continue” remain recorded separately.

## Timing, resources and archive

- Task preparation began 2026-10-20T13:54:43.215000+08:00; first task move 2026-10-20T13:58:02.971388+08:00; physical work/second return verification ended 2026-10-20T15:06:39.843729+08:00. Elapsed 4316.629 s, including preparation, review, tools, approximately 19 min 35 s personnel wait and return.
- 56 JSON requests (40 move_to, 16 set_gripper), 55 successful JSON results, 37 reviewed return segments, 27 internal empty-opening targets. Observation/selection/renewal/rejected commands are separate; do not sum these as equivalent physical movements.
- 5 host pre-dispatch rejections (stale review or state changed after review). Offline step, reserve and budget rejections did not execute. Budgets were renewed only during healthy stationary clear holds; runtime thresholds were unchanged.
- Controller command wall time 404.264 s includes planning, settling and capture, not pure motion. Detailed execution-window token/tool metrics and limitations: [metrics.json](metrics.json).
- Three recording batches, 213 MP4s: all endpoint/FPS/frame-count checks passed. Two stationary recording intervals are disclosed; see [VIDEO_RECORD.md](VIDEO_RECORD.md). Sampling duplicates/misses are retained.
- [Public dialogue](DIALOGUE.md), [final status](status.json), [frozen controller events](control_events_frozen.jsonl), [first return check](final_return_check_1.json), [second return check](final_return_check_2.json).

Complete physical task result: **unsuccessful**. Controlled withdrawal, independent support, return and evidence preservation: **completed**.

## User stop/save confirmation
2026-10-20T15:15:02.186746+08:00 — User: “停止，保存为三路视频”. All three recording batches were already completed; 213 original MP4 segments retained (71 per view), endpoint/frame-count validation passed. No further robot motion or recording started.

## 用户要求的三视角 90 秒视频导出

2026-10-20T15:22:12.190455+08:00 — 用户要求“下面是头部相机的视频，上面分别是左腕部和右腕部的视频，压缩为90s视频”。已生成 [90 秒三视角合成视频](三视角视频/抽书实验_三视角_90秒.mp4)，布局核对通过，全部 2700 帧逐帧解码及来源映射校验通过，容器时长 90.000 秒。原片、间隔说明、失败结论和原始执行统计保留。仅做离线文件处理，未再发送机器人动作。详见[后期处理记录](三视角视频/README.md)。
