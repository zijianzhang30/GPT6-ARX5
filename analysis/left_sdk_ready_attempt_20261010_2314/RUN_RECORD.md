# 左 SDK 恢复 ready 尝试（2026-10-10 23:14）

用户要求将左 SDK 从 `fault` 恢复到 `ready`。`ready` 以真实电机反馈为条件，没有手工改状态字段。左 CANable 固定序列号 `208833765931` 的桥接在 23:12 已成功重建，`can0` 为 UP；左 SDK 此前 `fault`、失能、无 owner、无 worker，右 SDK `ready`、失能且反馈新鲜。用户确认本次现场调整结束、左臂承托、回零路径清空、人员远离且可操作电源或急停。三路连接前新画面及状态见 [`confirmed_preconnect`](confirmed_preconnect/)。

[`recording`](recording/) 于 23:14:30 开始，三路设备独立且新帧增长。23:14:41 经左上游 8765 仅发送一次 `connect`，未使能、未发送位置目标。约 23:14:45 起左 SDK 为 `fault`，`worker_fault_reason=CAN feedback timeout or invalid age`；持续观察期间 `rx_count=0`，六个关节角均为空。`can0` 内核统计 TX 32,128 帧、RX 0 帧，见 [`can0_after_connect.txt`](can0_after_connect.txt)。网页事件“已收到实机反馈”是收到 worker 消息，不能替代真实 CAN 回包。

23:15:04 经原上游 `disconnect` 正常结束故障 worker。最终左 `fault`、失能、无 owner、无 worker；右 `ready`、失能、反馈新鲜。没有达到 `ready` 条件，因此未手工改为 `ready`。连接后画面见 [`postconnect`](postconnect/)。

三路录像于 23:15:14 以 STOP 正常结束，44.112 秒、三个 MP4、14,928,939 字节；各路 440 帧，每文件首末帧可解码。各路有 2 个采样缺口及 1–2 个重复源帧，未逐帧检查全部图像。没有执行回位或任务运动。
