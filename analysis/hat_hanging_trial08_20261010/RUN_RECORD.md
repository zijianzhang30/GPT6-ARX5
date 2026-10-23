# 挂帽第8轮：重新调整接线后的恢复试验

**左侧通信仍未恢复，挂帽任务没有开始。** 用户重新调整接线并要求再试；随后确认调整已结束、工作区清空且会保持空出。以前的清场未被拿来代替此次确认。

| 北京时间 | 操作与证据 |
| --- | --- |
| 约22:02—22:06 | 左固定CANable重新枚举为ttyACM2，旧slcand进程仍在而can0消失。左SDK已故障退出、失能且无owner；右SDK ready但失能。原`restore_can.sh`退出旧桥并创建can0 index41，未初始化SDK。 |
| 22:07:29—22:09:30 | 三路准备录像正常封口；新画面见帽子与木架，无手和工具。等待这次接线调整后的明确清场确认，因此尚未执行SDK连接。 |
| 22:11后 | 用户确认接线调整结束、清场。新三路画面复核，左接口仍UP、固定序列号正确。`recording02`冷启动超时失败，未做硬件动作；预热相机后另起`recording03`，三路新鲜帧增长。 |
| 22:12:43 | 经左上游8765仅发一次`connect`（可能初始化回零），录像持续。SDK随即报`CAN feedback timeout or invalid age`，连续11份状态均`rx_count=0`、六关节null。can0累计TX 24,312、RX 0；右臂持续ready且失能。 |
| 22:13:15后 | 经上游`disconnect`退出故障左worker，复核左失能/无owner/worker退出，右仍ready/失能。未发送enable、回位或任何挂帽目标。`recording03`正常封口。 |

此次接线调整并未恢复左侧电机反馈。can0存在和主机TX增长不能证明总线实收；在同一条件下不循环SDK初始化。该轮属于恢复阶段设备通信故障，不计入正式挂帽动作成功率。

- [任务定义](task_prompt.md)、[最终状态](status.json)、[连接命令](sdk_connect/connect_request.json)与[故障状态](sdk_connect/left_state_10.json)
- [录像与验证](VIDEO_RECORD.md)、[资源消耗](PERFORMANCE.md)、[执行前skill快照](skill_snapshot/SKILL.md)
- [左侧故障诊断](../left_can_diagnosis_20261010/DIAGNOSIS.md)
