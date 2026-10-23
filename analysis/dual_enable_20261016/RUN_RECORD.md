# 双臂使能恢复记录 — 2026-10-16

## 请求与确认

用户要求先使能双臂，随后准备一个任务并测试两次。收到当日通电、承托、初始化路径清空、人员退出及可急停确认“都可以了”。用户未进一步说明此前断电或 CAN 改线细节；本轮依据当前固定序列号和实时状态核验，不推断历史改动。

## 检查与执行

- 初检：两侧 SDK motor fault、disabled、六关节 null；旧保持宿主已退出，两侧无 owner。CAN 接口存在、RX 增长；物理左臂 2088335E5931 → can0 → 8765，物理右臂 208833765931 → can1 → 8766。
- 三路相机身份分别为全局 /dev/video2、左腕 /dev/video20、右腕 /dev/video10；新图无手进入初始化路径。先启动三路 MP4，再执行硬件恢复。
- 第一次左侧调用在硬件操作前因观察超过 30 秒被拒绝；刷新并实际审阅新图后继续，未放宽观察时限。
- 左、右各执行一次原上游 SDK disconnect/connect，逐侧验证 ready、有限六关节、空错误码、新鲜且增长的 RX。未重建 CAN 桥、未强改 fault 标记。
- 新图复核后启动唯一 held_policy_review --prepare-idle，逐侧建立带电保持；心跳、相机、到位、关节及预算保护保留。
- 两次稳定保持核验相隔 21.22 秒，均 ready/enabled/holding、无错误码、无运动；未观察到双臂干涉。

## 结果

2026-10-16T19:58:46.295879+08:00：双臂使能恢复成功。未执行取物或任务轨迹；两个正式测试均未开始，待用户提供当前完整 prompt。SDK 初始化不算受控回位，本次未验收厂商 HOME。return_reference.json 仅记录使能后的实测基线。

唯一保持宿主 PID 1426458 / PTY 6058，owner `dual-policy-acd76c994baa454bb6e13f2323f17676`，工作侧 left，日志 `control/`。收尾时保留健康保持宿主，不关闭或重连健康 SDK。

## 证据

- `preflight/`、`before_left2/`、`before_right/`、`before_enable/`：新图与状态。
- `left_reconnect_result.json`、`right_reconnect_result.json`及对应SDK日志。
- `control/initial_state.json`、`enabled_check1/`、`enabled_check2/`、`enable_verified.json`、`final_state.json`。
- `recording/`：2026-10-16T19:54:12.938257+08:00 至 2026-10-16T19:58:46.153039+08:00，三路 MP4 正常封存，共 15 段；统计详见 manifest.json。
- `video_validation.json`：全部 MP4 帧数及首末帧解码通过；不宣称逐帧验证或曝光硬同步。
