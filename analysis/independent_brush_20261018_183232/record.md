# Independent brush sweep

Requested: left arm picks up brush beside green box, sweeps three blue blocks into fixed dustpan, then sets brush down. Right arm is observation only.

Evidence source: live local robot and camera service. No skills, cloud storage, or prior run files consulted.

## Outcome — incomplete

The left arm picked up the brush, performed several supervised short sweeping strokes, and set the brush down resting on the table against the green box. The right arm remained stationary and was used only for camera observation. No blocks were verified inside the dustpan.

During the last lip-crossing attempt, bent bristles released and displaced one blue block toward the far front-left edge of the table. Sweeping was stopped after that uncontrolled displacement. Final external images show three blocks outside the dustpan: one at the far front-left edge and two nearer the middle of the table. The dustpan remained in place. The green box shifted slightly during brush handling.

The edge block was judged outside a safe continuation path for the left arm from this arrangement. This was a visual safety assessment, not an inverse-kinematics reach proof; no attempt was made to reach across the table edge. Recovery requires a scene reset or a separately planned recovery.

The left arm returned to its initial resting joint configuration and control was disabled. Both arms reported disabled, stationary, unowned, and no error codes at final readback.

| Arm | Maximum difference from initial joint feedback |
|---|---:|
| left | 0.3278 degrees |
| right | 0.0219 degrees |

## Retained evidence

| Stream | Video | Frames | Encoded duration | Size | Decode validation |
|---|---|---:|---:|---:|---|
| external | [external.mp4](external.mp4) | 6286 | 628.6 s | 81.9 MiB | first / middle / last: [True, True, True] |
| left_wrist | [left_wrist.mp4](left_wrist.mp4) | 6286 | 628.6 s | 56.2 MiB | first / middle / last: [True, True, True] |
| right_wrist | [right_wrist.mp4](right_wrist.mp4) | 6286 | 628.6 s | 44.4 MiB | first / middle / last: [True, True, True] |

Each stream was captured at nominal 10 fps from the live local camera service, with reception times and frame IDs retained in corresponding `*_frames.jsonl` files. This is host-time alignment, not hardware synchronization. `video_validation.json` records capture errors, duplicate frames, wall duration and decode results.

Additional evidence: `initial_state.json`, `final_state.json`, `commands.jsonl`, `telemetry.jsonl`, `*_grasp_verified.jpg`, `*_failure_event.jpg`, `*_brush_released.jpg`, and `*_final.jpg`. All output was created for this run. No cloud storage, pre-existing run files, local cache, or skills were used as task evidence. Live service endpoints sometimes included past event fields; those fields were not used for planning and were excluded from retained state records.

The first attempted grip failed its 30 mm test lift. The second grip lifted the brush successfully. One requested wrist pose was rejected as unreachable; the service stated that the target was unchanged. The later lower pose was accepted.

## Live execution log

- 2026-10-18T18:32:58: Enable left arm at measured resting pose; command `{"action": "enable"}`.
- 2026-10-18T18:32:58: settings; command `{"action": "settings", "speed": 0.12}`.
- 2026-10-18T18:32:58: Lift left gripper clear of table before approach; command `{"action": "target", "pose": [93, 5, 220, -3, 11, 3]}`.
- 2026-10-18T18:33:09: Approach above brush side with clearance; command `{"action": "target", "pose": [180, 60, 280, 0, 40, 0]}`.
- 2026-10-18T18:33:29: Advance toward brush handle above green box edge; command `{"action": "target", "pose": [250, 30, 270, 0, 55, 0]}`.
- 2026-10-18T18:33:31: Initial external view confirms three separate blue blocks, empty dustpan, and brush leaning on green box. Left arm is image-right; right arm remains stationary and is used only for its camera. All three streams have live frame IDs.
- 2026-10-18T18:33:44: Shift above handle using wrist-camera alignment; command `{"action": "target", "pose": [250, -20, 290, 0, 55, 0]}`.
- 2026-10-18T18:34:01: Advance above handle to resolve depth alignment; command `{"action": "target", "pose": [290, -20, 290, 0, 55, 0]}`.
- 2026-10-18T18:34:14: Center brush handle loop between open fingertips; command `{"action": "target", "pose": [320, -5, 310, 0, 55, 0]}`.
- 2026-10-18T18:34:26: Fine lateral alignment of handle loop; command `{"action": "target", "pose": [320, -13, 310, 0, 55, 0]}`.
- 2026-10-18T18:34:29: Close left gripper around brush handle; command `{"action": "target", "gripper_raw": 1.25}`.
- 2026-10-18T18:34:35: Moderate gripper closing rate while arm is stationary; command `{"action": "settings", "speed": 0.2}`.
- 2026-10-18T18:34:51: Test brush grasp with a 30 mm vertical lift; command `{"action": "target", "pose": [320, -13, 340, 0, 55, 0]}`.
- 2026-10-18T18:35:02: Reopen after test lift showed no secure grasp; command `{"action": "target", "gripper_raw": 2.8}`.
- 2026-10-18T18:35:04: First 30 mm test lift did not lift the brush. Brush remained leaning on the box; reopened to correct grasp depth. No sweeping performed yet.
- 2026-10-18T18:35:05: settings; command `{"action": "settings", "speed": 0.12}`.
- 2026-10-18T18:35:05: Lower open gripper along handle approach direction; command `{"action": "target", "pose": [335, -13, 290, 0, 55, 0]}`.
- 2026-10-18T18:35:16: settings; command `{"action": "settings", "speed": 0.2}`.
- 2026-10-18T18:35:16: Close around brush handle shaft at corrected depth; command `{"action": "target", "gripper_raw": 0.6}`.
- 2026-10-18T18:35:39: Second test lift: raise brush 30 mm; command `{"action": "target", "pose": [335, -13, 320, 0, 55, 0]}`.
- 2026-10-18T18:35:55: Lift brush clear of box and table; command `{"action": "target", "pose": [335, -13, 380, 0, 55, 0]}`.
- 2026-10-18T18:35:57: Second test lift succeeded: brush handle and bristles rose with left gripper; wrist view maintains shaft between jaws. Preparing sweep alignment.
- 2026-10-18T18:36:07: Carry brush leftward into clear space above the blue blocks; command `{"action": "target", "pose": [335, -140, 380, 0, 55, 0]}`.
- 2026-10-18T18:36:21: settings; command `{"action": "settings", "speed": 0.12}`.
- 2026-10-18T18:36:21: Position brush beside rear right blue block above table; command `{"action": "target", "pose": [255, -110, 300, 0, 55, 0]}`.
- 2026-10-18T18:36:39: Lower bristles to table beside rear right block; command `{"action": "target", "pose": [255, -110, 285, 0, 55, 0]}`.
- 2026-10-18T18:36:42: Short diagonal sweep of rear right blue block toward dustpan approach; command `{"action": "target", "pose": [280, -150, 285, 0, 55, 0]}`.
- 2026-10-18T18:36:52: Continue guiding first block toward dustpan mouth; command `{"action": "target", "pose": [325, -220, 285, 0, 55, 0]}`.
- 2026-10-18T18:37:07: Lift brush to adjust sweep angle without dragging blocks; command `{"action": "target", "pose": [325, -220, 360, 0, 55, 0]}`.
- 2026-10-18T18:37:15: Firm the brush shaft grasp after observed twist; command `{"action": "target", "gripper_raw": 0.3}`.
- 2026-10-18T18:37:24: Use lower reachable hover for angled sweep; command `{"action": "target", "pose": [325, -220, 335, 0, 55, 20]}`.
- 2026-10-18T18:37:37: Set angled bristles beside first block for alignment stroke; command `{"action": "target", "pose": [300, -220, 295, 0, 55, 20]}`.
- 2026-10-18T18:37:47: Align first block in front of dustpan lip; command `{"action": "target", "pose": [340, -265, 295, 0, 55, 20]}`.
- 2026-10-18T18:38:04: Lift and reposition brush to level its bristle edge; command `{"action": "target", "pose": [300, -180, 330, 0, 55, 0]}`.
- 2026-10-18T18:38:13: Pitch wrist to level brush bristles over table; command `{"action": "target", "pose": [300, -180, 305, 0, 75, 0]}`.
- 2026-10-18T18:38:32: Reorient brush at safe height to improve full-width bristle contact; command `{"action": "target", "pose": [300, -180, 340, 0, 30, 0]}`.
- 2026-10-18T18:38:54: Position low bristle edge just outside first block; command `{"action": "target", "pose": [250, -270, 320, 0, 30, 0]}`.
- 2026-10-18T18:39:06: Lower bristle tip to table on the outside of first block; command `{"action": "target", "pose": [250, -235, 280, 0, 30, 0]}`.
- 2026-10-18T18:39:16: Sweep first block laterally toward dustpan lip; command `{"action": "target", "pose": [250, -280, 280, 0, 30, 0]}`.
- 2026-10-18T18:39:29: Move bristle contact point toward block at a lower measured height; command `{"action": "target", "pose": [200, -225, 250, 0, 30, 0]}`.
- 2026-10-18T18:39:40: Descend 20 mm to establish bristle contact beside first block; command `{"action": "target", "pose": [200, -225, 230, 0, 30, 0]}`.
- 2026-10-18T18:39:50: Verify block contact with a 25 mm sweep; command `{"action": "target", "pose": [200, -250, 230, 0, 30, 0]}`.
- 2026-10-18T18:40:01: Set bristle tips through block height for positive contact; command `{"action": "target", "pose": [200, -250, 215, 0, 30, 0]}`.
- 2026-10-18T18:40:04: Sweep first block toward the lip with bristles engaged; command `{"action": "target", "pose": [200, -285, 215, 0, 30, 0]}`.
- 2026-10-18T18:40:17: Lift and reset brush beyond the two forward blocks; command `{"action": "target", "pose": [270, -220, 300, 0, 30, 0]}`.
- 2026-10-18T18:40:25: Lower brush so its bristle span covers the forward blocks; command `{"action": "target", "pose": [270, -220, 220, 0, 30, 0]}`.
- 2026-10-18T18:40:39: Sweep the front pair leftward toward dustpan; command `{"action": "target", "pose": [270, -265, 220, 0, 30, 0]}`.
- 2026-10-18T18:40:51: Continue controlled sweep toward dustpan entry; command `{"action": "target", "pose": [270, -325, 220, 0, 30, 0]}`.
- 2026-10-18T18:41:03: Push first block over dustpan lip; command `{"action": "target", "pose": [270, -355, 220, 0, 30, 0]}`.
- 2026-10-18T18:41:22: Stop sweeping and lift brush clear after block was displaced toward table edge; command `{"action": "target", "pose": [270, -355, 310, 0, 30, 0]}`.
- 2026-10-18T18:41:23: Failure event: first block at dustpan lip was abruptly displaced by releasing bent bristles, ending near far front-left table edge (approximately external-image pixel 54,460). Dustpan remains empty in live right-wrist view. Other two blocks remain on table. Sweeping stopped to avoid further uncontrolled block motion; proceeding to supported brush placement.
- 2026-10-18T18:41:30: Carry brush back above its starting position beside green box; command `{"action": "target", "pose": [335, -13, 385, 0, 55, 0]}`.
- 2026-10-18T18:41:50: Lower brush back onto support beside green box; command `{"action": "target", "pose": [335, -13, 300, 0, 55, 0]}`.
- 2026-10-18T18:42:01: Release brush resting on table against green box; command `{"action": "target", "gripper_raw": 2.8}`.
- 2026-10-18T18:42:08: Withdraw open left gripper after supported brush release; command `{"action": "target", "pose": [335, -13, 380, 0, 55, 0]}`.
- 2026-10-18T18:42:17: Retract empty left arm above clear table; command `{"action": "target", "pose": [180, 0, 280, 0, 40, 0]}`.
- 2026-10-18T18:42:28: Brush set down with bristles on table and handle supported by green box. Gripper opened and withdrawn; external view confirms brush remains in place without gripper support.
- 2026-10-18T18:42:36: Retract to pre-approach pose; command `{"action": "target", "pose": [93, 5, 220, -3, 11, 3]}`.
- 2026-10-18T18:42:53: Restore left arm to initial measured resting joints; command `{"action": "target", "joints_deg": [3.0053378763, -1.0381887538, 1.6501737035, -13.1906798912, -0.1857811454, -2.8741982443]}`.
- 2026-10-18T18:43:04: Disable left control after resting pose confirmed; command `{"action": "stop"}`.

## 三路合成 90 秒视频

按用户指定布局生成 [three_camera_90s.mp4](three_camera_90s.mp4)：上方左侧为左腕部相机，上方右侧为右腕部相机，下方为头部（全局）相机。三路均保留完整画幅，以黑边适配布局，并添加相机标签。

完整运行的约 629.07 秒按采集时间同步、约 6.990 倍加速，输出严格为 90.00 秒，1280 × 960，30 fps，H.264，共 2700 帧。原始三路视频保留。全部 2700 帧已逐帧解码验证。详细信息见 `three_camera_90s_validation.json`；输入与输出帧对应关系见 `three_camera_90s_frame_map.csv`。
