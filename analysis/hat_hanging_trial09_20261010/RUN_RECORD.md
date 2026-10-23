# 挂帽第9轮逐段记录

时间均为 2026-10-10 CST。阶段：恢复前检查；任务动作未启动。

| 时间 | 阶段 | 观察与结果 |
| --- | --- | --- |
| 23:22:57 | 用户目标 | 恢复挂帽初始位姿、按原 skill 录制三路视频并执行左臂自主取帽挂最低挂点。 |
| 约23:23 | 控制前置 | 左 `fault/disabled/worker_running=false`，六关节 `null`、`rx_count=0`；右 `ready/disabled`、反馈增长。`can0` UP 但自 23:22 重建后未收到电机回包。 |
| 23:24:30 | 三路只读观察 | 全局、左腕、右腕均返回 JPEG；设备分别 `/dev/video2`、`/dev/video20`、`/dev/video10`。帽子在盒上、木架在旁，画面未见人员侵入。 |
| 23:25:13 | 录像尝试1 | `recording/manifest.json` 为 `failed`，相机首帧超时；未产生有效 MP4，失败证据保留。 |
| 23:25:31 | 相机预热 | 三路取得不同的新帧，身份不变；左反馈仍为故障、0 回包。 |
| 23:26:14–23:26:26 | 录像尝试2 | `recording02/` 三路 MP4 正常封存，各 120/120 新鲜帧，0 缺失、0 重复、0 请求错误，首末帧可解码。只有静止布置与准备过程。 |
| 收尾 | 停止点 | 无新 SDK 连接、无使能、无初态恢复、无帽子操作；左臂继续失能、不可回位；右臂原位失能。 |
| 23:33:51 | 中断后续行复核 | 报告与录像文件已写入并复核；左侧仍`fault/disabled`、worker退出、`rx_count=0`、六关节`null`，`can0`重建后RX/TX仍为0；右侧`ready/disabled`、反馈增长。未重新初始化或运动。 |

成功判定：未评价。自主取帽、最低挂点独立承托、松爪撤离、双臂回位均未发生。`can0 UP` 与三路录像正常不能替代六关节实测反馈。

本轮用户已有执行授权；阻断原因是左侧 CAN 接收为 0 且多次历史初始化未恢复，不是缺少许可。原任务技能要求在此症状下停止重复初始化。独立记录 [主报告](../../HAT_HANGING_EXPERIMENT_RECORD_20261010_TRIAL09.md)、[视频](VIDEO_RECORD.md)、[资源](PERFORMANCE.md)。

初态只读快照见 [initial_state.json](initial_state.json)；[return_reference.json](return_reference.json) 明确标为无效，不可用于运动。三路预检图片在 `preflight_images/`。
