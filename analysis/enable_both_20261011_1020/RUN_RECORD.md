# 双臂重新上电后使能前检查（2026-10-11 10:20–10:23）

用户重新接入电源并请求使能两臂。本轮只执行了使能前的通信、图像和 SDK 连接检查，**未使能任一机械臂，未发送任务目标或回位命令**。

## 现场与历史依据

- 用户确认两臂有稳固承托、回零路径和桌面工作区清空、人员远离，并可立即操作电源或急停。首次新图仍见手在桌面，故暂停实机连接；用户随后确认已移开，[新全局图](clearance/external.jpg)不再见手。
- 本机 [初始化手册](../../MACHINE_INITIALIZATION_RUNBOOK.md) 与 [共用执行流程](/home/tuojing/.codex/skills/arx-r5-tabletop-tasks/references/common-execution.md)要求真实 ready、六关节有效、空错误码、新鲜且增长的 RX，之后才可由唯一监督宿主使能。先前 [左侧诊断](../left_can_diagnosis_20261010/DIAGNOSIS.md)与 [23:20重试](../left_sdk_ready_attempt_20261010_2320/RUN_RECORD.md)均记录左侧零远端回包。
- 固定映射仍为左 CANable `208833765931` → `can0`、右 `2088335E5931` → `can1`；两个接口均 UP。首次检查左 `can0` RX=0，右 `can1` 有大量收包。无活动监督控制宿主或录像进程。

## 本轮操作与结果

1. 三路新图来自不同设备（全局 `/dev/video2`、左腕 `/dev/video20`、右腕 `/dev/video10`）。首次录像冷启动超时，保留[失败 manifest](recording/manifest.json)；预热三路后，[第二次录像](recording02/manifest.json)正常，开始时间 10:22:35，首次实机连接前已录制且三路 `fresh_frames` 连续增长。
2. 右上游原有 `SDK motor fault` worker 仍运行、失能无 owner，六关节为空。通过原上游 8766 发送 `disconnect`，确认 worker 退出；再发送一次 `connect(acknowledge_initialization=True)`。右臂达到 `ready`，六关节有效，错误码为空，`rx_age_ms` 小且 `rx_count` 持续增长。本轮最终右臂 `ready`、`enabled=false`、无 owner、worker 运行；两次状态读取间 `rx_count` 增加 830。
3. 左上游原为 `fault`、失能无 owner、无 worker。通过原上游 8765 发送一次 `connect(acknowledge_initialization=True)`；随即报 `CAN feedback timeout or invalid age`，`rx_count=0`、六关节均为空、错误码非空。通过上游正常 `disconnect`，确认故障 worker 退出。最终左 `can0` 主机累计 TX=14,787 帧、RX=0；右 `can1` 持续收包。网页“已收到实机反馈”提示只表示收到 worker 消息，不代表收到电机帧。
4. 最终状态保存在 [左臂状态](final_left_state.json)、[右臂状态](final_right_state.json)，CAN 接口统计保存在 [can0](can0_final.txt)和 [can1](can1_final.txt)。两臂均失能、静止、无 owner；左臂 `fault`，右臂 `ready`。成对监督代理要求两侧都 ready，未启动控制宿主，未尝试使能右臂单侧。

## 录像与结论

[三路录像](recording02/)在 10:23:40 通过 STOP 正常结束，64.807 秒，每路 647 帧、两段 MP4；全局 644 新帧，左右腕各 642 新帧，各路 2 个采样缺口，无 HTTP 请求错误。六个 MP4 的首末帧均可解码，检查见 [playability_check.json](recording02/playability_check.json)；未逐帧检查所有画面。

重新上电没有恢复左侧电机反馈，故不能将左 SDK `fault` 改为 `ready`，也不能使能双臂。`can0 UP` 和 TX 增长只证明主机侧接口及发送，不能证明左电机收到指令或回包。下一步须由现场人员在**断电并保持可靠承托**后检查左臂本体供电与保护器件、CANable 至底座的 CAN_H/CAN_L/GND、插头针脚与终端配置，并按厂家方法隔离适配器与臂内总线；故障条件未改变前不再循环 SDK 连接。
