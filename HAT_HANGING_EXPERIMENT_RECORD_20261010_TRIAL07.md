# 挂帽真机实验 — 2026-10-10 第7轮

**初始位姿尚未恢复，正式挂帽未开始。** 用户重新插拔左CANable后，`rebuild_left_can_bridge.py`因旧`can0`消失而在预检阶段拒绝。该脚本要求旧桥与`can0`同时存在；`restore_can.sh`才适用于此时的缺失接口。已运行后者恢复can0 index40，并修正前者的错误提示与初始化手册。

用户确认左本体上电、清场。三路录像开始后仅对左SDK连接一次，仍CAN反馈超时、六关节值为空，can0 TX29,074包、RX0。故障左worker已退出，右臂ready/disabled；未发送使能、初位姿回位或挂帽动作。接口已恢复，但左侧电机通信仍未恢复，具体物理部位未确认。

本轮属于恢复阶段故障，不计入正式挂帽成功率。三路MP4共3片、约13.9MiB，正常封口且首末帧可解码；资源窗口已冻结。

- [逐段记录](analysis/hat_hanging_trial07_20261010/RUN_RECORD.md)、[状态](analysis/hat_hanging_trial07_20261010/status.json)
- [视频](analysis/hat_hanging_trial07_20261010/VIDEO_RECORD.md)、[资源](analysis/hat_hanging_trial07_20261010/PERFORMANCE.md)
- [静态位姿目标](analysis/hat_hanging_trial07_20261010/restore_target_reference.json)
- [左臂 CAN/SDK 后续只读诊断](analysis/left_can_diagnosis_20261010/DIAGNOSIS.md)
