# 左臂 CAN 连接重试（2026-10-10 22:58–23:00）

用户报告已调整左侧 CANable 终端电阻开关；开关最终 ON/OFF 位置未报告。用户随后确认现场调整结束、左臂承托稳固、回零路径清空、人员远离且可操作电源或急停。本次仅进行一次左 SDK 连接检查，不使能、不发送位置目标、不尝试回位。

## 前置状态

- 固定左 CANable 序列号 `208833765931` 映射到 `can0`，接口 UP；左上游 `fault`、`disabled`、无 owner、无 worker，六关节值为空，`rx_count=0`。右上游 `ready`、失能、反馈新鲜。
- 三路新画面来自 `/dev/video2`、`/dev/video20`、`/dev/video10`，连接前图片及状态保存在 [`preconnect`](preconnect/)。第一次录像冷启动因取帧超时失败并保留 [`recording/manifest.json`](recording/manifest.json)；预热三路相机后，新目录 [`recording02`](recording02/) 从 22:58:37 起正常录制。

## 连接与结果

- 22:59:45 经原 8765 上游接口发送一次 `connect`，承认 SDK 初始化可能回零。连接返回 `initializing`，未发送使能或目标。
- 约 22:59:48 起上游为 `fault`，`worker_fault_reason=CAN feedback timeout or invalid age`；持续观察约 18 秒，左 `rx_count=0`，六关节仍为空。故障前 `can0` 内核统计：TX 33,307 帧，RX 0 帧；见 [`can0_before_disconnect.txt`](can0_before_disconnect.txt)。网页事件出现“已收到实机反馈”，但它不代表真实电机帧，见 `rx_count=0` 与故障状态。
- 23:00:09 经上游 `disconnect` 正常结束故障 worker。最终左 `fault`、`disabled`、无 owner、worker 已退出；右 `ready`、失能、反馈持续增长。连接前后画面保存在 [`preconnect`](preconnect/) 与 [`postconnect`](postconnect/)；没有进行受控回位或挂帽任务。

## 录像与边界

[`recording02`](recording02/) 以 STOP 正常结束，共 111.284 秒、六个 MP4、36,736,643 字节。每个文件的首末帧均可解码；各路 1,111 帧，分别有 2 个采样缺口及 2–5 个重复源帧，不称完整零缺帧。未逐帧检查全部图像。

终端电阻开关调整后仍无电机回包，不能单凭这一轮定位适配器总线侧、线束、臂内供电或驱动。没有新的物理测量结果前不重复 SDK 初始化。
