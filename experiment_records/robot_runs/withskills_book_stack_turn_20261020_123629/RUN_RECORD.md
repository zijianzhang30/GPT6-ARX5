# Two-book push and full-turn trial — 2026-10-20

Status: unsuccessful; execution ended and both empty arms returned within the
original 2.5° tolerance. The books did not complete a full turn or enter the
destination rectangle. Three-view recordings and raw evidence are retained.

The requested protocol is frozen in [task_prompt.md](task_prompt.md).
The two books initially occupy the rectangle on image-right; the empty rectangle
is image-left and nearer the overview camera. Both books are initially stacked
and table-supported.

## Preparation

Initial read at 12:38:27 Asia/Shanghai: both arms ready, disabled, stationary,
unowned, with finite joint feedback and no reported error codes. The prior
morning trial is separate; its outcomes are not claimed for this trial.
The existing Basic Skill and tabletop skill were read along with relevant
book-pushing records. No historic trajectory was replayed.

Current CAN identification agrees with the exchanged mapping:
left 2088335E5931 → can0 → 8765; right 208833765931 → can1 → 8766.
Camera identifiers are external /dev/video2, left gemini /dev/video20,
right gemini_right /dev/video10. Initial/repeated states and images are in
[preflight](preflight/) and [before_enable](before_enable/).

Three-camera MP4 recording began at 12:38:56.674704 Asia/Shanghai.
The recorder's manifest and increasing fresh-frame counts were verified before
enable and repeatedly during execution. The standard supervised hold host
started with one working arm at a time, 3.5° additional planning reserve,
2° minimum Cartesian command step, and optional arrival-fault quarantine.
Existing hardware, camera, heartbeat, tracking, settling, and budget guards
remain active. No SDK reconnect or CAN restart was needed.

The immutable [return_reference.json](return_reference.json) was copied from
the new host's initial powered-hold state. Budget renewals do not modify it.

## Execution

The left empty gripper approached through clear space, then pitched downward
in two 8° increments outside the book footprint. The right arm moved to a
separate observation position to expose both book layers and the left finger.
The left arm then descended outside the book side in bounded segments, with
images reviewed between segments. Jaw openings remained fixed.

Several proposed large movements and one stale observation were rejected
before dispatch. Smaller newly reviewed segments followed; thresholds were
not relaxed. Successful controller settling is not evidence of collision
clearance or object movement.

The first inward contact moved the upper layer more than the lower. Lateral
motion was stopped, the left tool withdrew, and its approach was changed
toward SDK pitch 45° and inward yaw −45° while clear. A second approach kept
the broad crossbar farther outside the book outline. Following 20 mm and
15 mm downward segments in side clearance, 15 mm and 12 mm inward approaches
brought the fingertip to the side.

At 12:59:37 and 13:00:06, two bounded 12 mm lateral push tests visibly shifted
the stacked books leftward and produced a small change of orientation.
No complete turn or destination containment has been established. Both books
remain stacked and table-supported; small relative offset is visible and
precise rigid coupling has not been measured. No book grasp or lift has been
commanded; jaw commands stayed fixed throughout.

The recorder received an unexpected SIGTERM and closed at 13:00:30.229599.
The next motion proposal was blocked offline as stale, and the recording
check then detected completion. No movement was dispatched in the recording
gap. Three-stream recording restarted into `recording02` at
13:01:03.274137, a manifest-to-manifest gap of 33.044538 seconds. All three
fresh streams were checked before the next movement. The cause of SIGTERM
has not been established.

At 13:01:28 the left gripper withdrew 25 mm laterally, leaving the books
undisturbed. The right arm then began a clear-space approach for a different
side contact, with 40 mm forward motion and two 10° orientation segments.
The right gripper had not yet pushed the stack at this point.

The additional offline `plan.py` check now reproduces the live anchor and
travel budget and checks a 3.5° reserve inside the 40° session excursion.
It was added after noticing an earlier clear-space target within the runtime
40° limit but beyond this extra reserve; a healthy stationary renewal was
used. Runtime limits were never loosened. Offline import/initialization
errors were corrected without dispatching motion.

## Evidence

- [control/events.jsonl](control/events.jsonl): raw commands, results, rejection
  reasons, observations, and budget renewals.
- [control](control/): timestamped three-view JPEGs and state snapshots.
- [recording](recording/): original three-stream MP4 segments, per-frame metadata,
  and recorder manifest. Shared software sampling is not hardware exposure sync.
- [recording02](recording02/): restarted three-stream MP4 recording after the
  stationary gap described above.

## Final contact attempt and result

The left gripper withdrew a further 40 mm to open clearance. The right gripper
approached with approximately SDK pitch 45° and yaw +45°, advanced through
clear space, and descended outside the stack in bounded segments. Subsequent
20 mm, 20 mm and 13 mm inward approach segments brought its fingertip near
the lower book edge. A 13 mm push test dispatched at 13:10:19 did not produce
clear stack motion. The edge occluded the contact, so effective contact with
the lower book could not be established. Two-dimensional overlap is not
proof that a finger entered a gap.

Further inward motion stopped. The right gripper withdrew 25 mm at 13:11:14
and another 40 mm at 13:12:28; the stack remained undisturbed. No book grasp,
jaw closure or lifting action was commanded. The final images show the two
books stacked on the table with a small relative offset. The stack is still
mostly over the source rectangle and clearly not fully inside the destination.
Only a small translation and orientation change were observed; no calibrated
cumulative angle or full 360° rotation is claimed. Both grippers attempted
side contact, but effective pushing by both was not verified.

The decision to stop followed unresolved contact geometry and lack of progress.
The [tabletop SKILL.md](/home/tuojing/.codex/skills/arx-r5-tabletop-tasks/SKILL.md:53)
states: “软件/相机故障、可疑碰撞、卡滞或连续无进展时停止发送新动作，保留现场和失败证据”.
Its [common execution reference](/home/tuojing/.codex/skills/arx-r5-tabletop-tasks/references/common-execution.md)
also says: “证据仍不足时保留未完成结果和具体阻碍，不连续试探同一接触”.
These instructions apply here because reliable lower-book contact was still
unresolved after bounded approaches and a right-side test with no clear motion.
This is an unsuccessful trial, not a claim that the task is impossible.

## Withdrawal and return

After clearing the books, the right arm returned first and the left arm
second through individually reviewed joint segments, with the other arm
holding. Offline checks used the actual current anchor/travel budget and
3.5° additional joint/session reserve. Healthy stationary renewals retained
the immutable original return reference. State-change rejections during
return triggered a fresh observation and review, not relaxed thresholds.

The last left-arm intermediate pose had a 2.67° measured error and did not
meet the return criterion. The exact saved J2 target (−0.9726°) falls below
the extra planning margin (−0.2296°), so a nearby executable target was used
within the unchanged original 2.5° tolerance. J2 was targeted to 0° and J4
to −12.7°; the latter also made the correction exceed the existing 2°
minimum Cartesian command step. The 7-element Cartesian target was checked
offline and dispatched at 13:30:52. The saved reference and all runtime limits
were unchanged. A temporary offline 6-element pose conversion was corrected
before any dispatch.

Two subsequent observations at 13:31:00.507 and 13:31:25.079, separated by
24.572 seconds, passed the original tolerance for measured and commanded
joints on both arms:

| Arm | Check 1 measured / command max error | Check 2 measured / command max error |
| --- | --- | --- |
| Left | 1.8141° / 2.0229° | 1.8141° / 2.0229° |
| Right | 0.7650° / effectively 0° | 0.7868° / effectively 0° |

Both arms were ready, enabled, stationary, holding, and reported no error
codes. Both empty grippers were clear of the books and the books remained
independently supported. Evidence:
[check 1](final_return_check_1.json), [check 2](final_return_check_2.json),
[raw state 1](final_return_state_1.json), [raw state 2](final_return_state_2.json).
The original reference is byte-for-byte identical to `control/initial_state.json`.
The healthy control host remains alive; stopping video did not disable either arm.

## Recording closure and verification

`recording02/STOP` was created after the two return checks. The recorder
exited with code 0 and manifest status `completed` at 13:31:34.873504,
with stop reason `stop_file`. The first recorder also sealed its files and
reported `completed`, but its unexpected SIGTERM is retained as an interruption.

| Recording | View | MP4 segments | Frames | Fresh | Duplicate | Missing |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| recording | top | 22 | 12,936 | 12,896 | 14 | 26 |
| recording | left | 22 | 12,936 | 12,881 | 30 | 25 |
| recording | right | 22 | 12,936 | 12,885 | 24 | 27 |
| recording02 | top | 31 | 18,314 | 18,252 | 24 | 38 |
| recording02 | left | 31 | 18,314 | 18,240 | 34 | 40 |
| recording02 | right | 31 | 18,314 | 18,234 | 39 | 41 |

All six stream parts report zero request errors. Missing slots are retained
as labeled black frames and duplicated source frames remain labeled. Each
view contains 31,250 frames total, corresponding to 3,125.0 seconds of
encoded video at 10 fps, excluding the 33.044538-second stationary gap.

All 159 MP4 segments passed first/last-frame decoding, frame-count,
10 fps, dimensions, contiguous segment numbering and per-frame metadata
checks. This is endpoint decoding, not a full-frame decode. The recorder
adds a 32-pixel status footer (640×512 overview; 848×512 wrists); the validator's
initial source-height assumption was corrected from the recorder source.
No original video was modified.

- [Video index with all three streams](VIDEO_INDEX.md)
- [Detailed validation](recording_validation.json)
- [First manifest](recording/manifest.json)
- [Second manifest](recording02/manifest.json)

## Time, resources and limitations

The host's first hold preparation was at 12:39:21.750925 and the final return
review finished at 13:31:25.109543 (Asia/Shanghai), an elapsed 3,123.359 seconds.
Video spans 12:38:56.674704–13:31:34.873504, including the recorded gap described
above. This elapsed time includes observation, review, planning, tool round
trips, motion and waiting; it is not pure mechanical motion time.

There were 171 host review commands (162 completed and 9 rejected), 57 JSON
requests (56 `move_to`, 1 `check_path`), 53 Cartesian motion results and
34 executed reviewed joint-return segments. Additional offline planning
rejections are separate from these host counts. The nine host rejections
were two stale/consumed-observation rejections, two trajectory-envelope
rejections, and five state-change-after-return-review rejections.
They were pre-dispatch refusals, not reported robot runtime faults.

Host command processing totaled 309.183 seconds, including planning,
execution, settling and capture. Recorded input wait before commands totaled
2,805.897 seconds and includes attended review and tool latency. Pure server
inference time and attributed token usage were not measured. MP4 files total
985,357,324 bytes. Details are in [metrics.json](metrics.json).

The controlling workflow did not provide verified full-scene collision
detection or contact force measurement. No robot runtime fault was reported;
this does not resolve the ambiguous right-side contact. No user success
acceptance or execution-time manual scene adjustment was recorded.

Final machine-readable conclusions are in [status.json](status.json);
available public dialogue is in [DIALOGUE.md](DIALOGUE.md). The task remains
unsuccessful, with return and evidence preservation completed.

Post-recording read-only check at 13:34:18 confirmed both arms still ready,
enabled, stationary and holding with no error codes, and still within the
original return tolerance. [State and camera evidence](post_recording_hold/)
is retained. No motion was sent after recording stopped.
