# Book stack pushing and full-turn attempt

**Outcome: incomplete.** The stack was not transferred into the target rectangle, and a complete 360-degree turn was not achieved. Both books remain stacked on the table near the starting rectangle; the upper book is slightly skewed relative to the lower book.

## Request and input restrictions

Use both grippers to push the two stacked books fully from one black rectangle into the other, rotating the stack one full turn along the way. Do not grasp or lift the books. Retain three video streams and Markdown records.

No cloud storage, skills, prior experiment contents, or task caches were accessed. Live local camera feeds, current robot telemetry, and the local robot interface implementation were used. Directory and process listings were used to find the live interface; earlier experiment files were not opened.

## Live scene and execution

The initial external view showed two white books stacked in the rectangle on image-right. The empty destination rectangle was to image-left and closer to the external camera. Both arms initially held still, with no book contact.

The existing local controller remained responsible for powered hold. Commands used the current local controller session and its public control interface. Local feedback was checked before and during short arm movements; each movement ended in powered hold. Commands and measured outcomes are retained in `motions.jsonl`.

The left gripper approached the right side of the stack in small increments. Initial lateral contact moved the upper book more than the lower book. Contact was withdrawn and adjusted lower. The right arm approached the opposite side but did not make a verified pushing contact. Additional height, contact-position, pitch, and wrist-roll adjustments were attempted on the left. These wrist rotations were tool positioning and do not count as rotation of the books. The revised contact eventually showed increasing position residual without visible whole-stack movement. The attempt was ended rather than increasing contact further.

The left gripper was withdrawn laterally before being raised clear. The right gripper was withdrawn and raised clear. Final live telemetry showed both arms enabled, stationary, in holding state, with no reported error codes. No grasp or book lift was commanded or observed. Gripper targets were unchanged throughout: left 0.6828943252563476 raw units; right 0.23542461395263672 raw units.

## Verification limits and recording gap

The initial three MP4 files were recorded at nominal 10 fps, with camera frame identifiers and wall times retained in corresponding `*_frames.jsonl` files. The cameras were not hardware synchronized. Recording stopped unexpectedly before the physical attempt ended. The exact cause is unverified; the recorder exited cleanly and had a signal handler that finalizes video on SIGINT/SIGTERM.

- Physical motion commands: 61 ({'left': 53, 'right': 8}).
- First motion: 2026-10-18 15:56:17 Asia/Shanghai.
- Last motion: 2026-10-18 16:07:06 Asia/Shanghai.
- Initial video coverage: 2026-10-18 15:55:48 to 2026-10-18 16:03:05 Asia/Shanghai.
- Later motion commands without retained continuous video: 29. Live snapshots were inspected during these commands; the earlier overwritten snapshots cannot substitute for retained video.
- A separate brief `final_segment/` records the stationary final scene after the gap was discovered. It does not fill the missing interval.

## Retained artifacts

- `external.mp4`: overview, initial recorded segment.
- `gemini.mp4`: left wrist, initial recorded segment.
- `gemini_right.mp4`: right wrist, initial recorded segment.
- `final_segment/`: three final stationary video streams and timestamp logs.
- `*_initial.jpg`, `*_final.jpg`: initial and final live camera images.
- `motions.jsonl`: executed motion requests, initial telemetry, and final telemetry.
- `final_state.json`: final arm state and camera frame identifiers.
- `video_validation.json`: initial video metadata and beginning/middle/end decode checks.
- `move.py`, `record.py`: code created for this attempt.

## Criteria

| Requirement | Result |
|---|---|
| Both grippers push the stack | Not achieved; only left contact verified |
| Entire stack within destination rectangle | Not achieved |
| Stack rotates 360 degrees | Not achieved |
| Books remain stacked and table-supported | Observed, with upper/lower relative skew |
| No grasping or lifting of books | No such command issued; none observed |
| Three continuous videos throughout execution | Not achieved; recording gap documented |
| Markdown record | Retained in this file |

Final video validation: all three initial streams contain 4,367 frames (436.7 seconds at nominal 10 fps), and beginning, middle, and final frames decode. All three final-segment videos also pass beginning/middle/end decoding. Metadata is retained in each segment’s `video_validation.json`.

## 90 秒三路合成视频

按后续要求生成 `three_cameras_90s.mp4`：上方左侧为左腕部相机，上方右侧为右腕部相机，下方为头部/全景相机（原 external 通道）。分辨率 1280×1200，H.264 编码，30 fps，容器时长严格为 90.000 秒，共 2,700 帧，约 14.1 MB。

已保留片段按约 5.55 倍速播放，并以采集时间戳对齐三路画面。第 78.667–81.667 秒为录像缺失提示卡，明确标注原始录像缺失时段 16:03:05–16:07:45；之后为最终静止画面。原始三路录像均保留。

已检查上左/上右/下方布局、缺失提示及最终画面，并成功逐帧解码全部 2,700 帧。合成参数和校验结果分别见 `three_cameras_90s.json` 与 `three_cameras_90s_validation.json`。
