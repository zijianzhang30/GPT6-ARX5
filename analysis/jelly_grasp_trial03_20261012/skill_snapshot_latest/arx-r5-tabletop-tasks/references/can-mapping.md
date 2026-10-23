# 统一 CAN 接线前提

2026-10-11，用户明确确认两只 CANable 已在左右机械臂之间交换，并要求所有实机任务沿用这一前提。当天已用真实关节反馈与使能保持验证两侧正常。

| 物理机械臂 | 当前 CANable 序列号 | 接口 | SDK 服务 | 腕部相机 |
| --- | --- | --- | --- | --- |
| 左臂 | 2088335E5931（原右） | can0 | 8765 | CV2C8610015R / gemini |
| 右臂 | 208833765931（原左） | can1 | 8766 | CV2C86100180 / gemini_right |

任务中的“左臂执行、右臂观察”等分工仍指物理机械臂；不交换任务坐标、关节数据、标定文件、腕部相机或 TCP 配置。ttyACM 编号会变化，必须使用 by-id 身份并核对现有 slcand 参数、实时 SDK 反馈和控制宿主。用户若再次调整接线，以新的明确确认与实时检查更新记录，不能按旧表盲发命令。

2026-10-12已将本机`/home/tuojing/arx_r5_control`中的`tools/restore_can.sh`、`rebuild_left_can_bridge.py`及`restart_left_can_bridge.py`修复为当前左序列号`2088335E5931`。这是本机版本的记录，当前Git检出中的脚本可能仍绑定旧序列号；使用前须检查实际源码和实时接线，不能依据技能文字跳过核对。离线保护测试与当前桥接只读检查通过，是否实际重建及电机恢复仍以当次记录为准。接口和保持健康时直接复用，不能为套用脚本而改回映射或重启。接口缺失时先按实际物理连接检查对应侧失能、无 owner、SDK 已退出等条件，再恢复正确通道；不得触碰另一侧健康保持。

[双臂恢复证据](/home/tuojing/arx_r5_control/analysis/right_enable_swapped_adapter_20261011_1043/RUN_RECORD.md)；[初始化手册](/home/tuojing/arx_r5_control/MACHINE_INITIALIZATION_RUNBOOK.md)。其中 PID、会话和状态均为历史快照，后续必须读实时状态。
