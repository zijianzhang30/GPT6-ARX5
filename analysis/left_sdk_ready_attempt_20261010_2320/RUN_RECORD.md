# 左 SDK ready 再核验（2026-10-10 23:19–23:20）

用户再次要求将左 SDK 的 `fault` 改为 `ready`。上次连接结束后，`can0` 内核累计 RX 从 0 增至 45 帧，但左 SDK 仍 `fault`、失能、无 owner、无 worker，六关节为空。空闲被动监听 4 秒无新帧。用户在前一轮确认的现场条件下，新三路画面与此前基本一致；连接前状态、画面见 [`preconnect`](preconnect/)。本轮不改状态字段，只验证真实反馈能否令 SDK 进入 `ready`。

[`recording`](recording/) 于 23:19:29 开始正常录制。23:19:49 经左上游 8765 仅发送一次 `connect`，未使能或发送运动目标。SDK 随即为 `fault`，`worker_fault_reason=CAN feedback timeout or invalid age`；观察约 10 秒，左 `rx_count=0`、六关节角全为空。`can0` TX 从 32,200 增至 61,767 帧，RX 保持 45 帧；独立被动监听同期记录 18,219 个本机发送回显、**0 个远端帧**，见 [`remote_can_frames.jsonl`](remote_can_frames.jsonl) 与 [`can0_before_disconnect.txt`](can0_before_disconnect.txt)。原累计 45 帧没有持续反馈，不能作为 `ready` 依据。

23:20:09 经上游 `disconnect` 正常结束故障 worker。最终左 `fault`、失能、无 owner、无 worker；右 `ready`、失能、反馈新鲜。连接后画面见 [`postconnect`](postconnect/)。没有执行回位或任务运动。

三路录像于 23:20:26 以 STOP 正常结束，57.447 秒、三个 MP4、18,951,234 字节。各路 573 帧，每文件首末帧可解码；全局和左腕各有 2 个采样缺口、1 个重复源帧，右腕有 3 个采样缺口。未逐帧检查全部图像。

没有持续的远端电机帧或有效关节值，`ready` 条件未满足；不能手工把 `fault` 改为 `ready`。需要新的物理供电/CAN 链路测量结果才可继续定位。
