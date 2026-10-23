# 挂帽第7轮 — 2026-10-10

本轮针对用户再次插拔左CANable后运行`rebuild_left_can_bridge.py`报错。该脚本仅接受旧桥和can0都仍存在；新现场因USB重新枚举至ttyACM1而缺失can0，故预检拒绝，未动接口。左SDK故障worker已退出，右臂ready/disabled。

| 阶段（北京时间） | 事实与结果 |
| --- | --- |
| 约21:40 | 左固定CANable重枚举ttyACM1，can0消失，旧slcand仍在。 |
| 约21:42 | 使用适用的原`restore_can.sh`退出旧桥、恢复can0 index40；脚本未连接SDK或运动。 |
| 连接前 | 用户确认左本体上电、手与工具清场并保持空出。三路新图无手进入，左右SDK状态分别为fault/ready，均失能、无owner。 |
| 2026-10-10T21:45:22.745307+08:00 | 启动本轮三路MP4，三视角新帧增长、设备身份正确。 |
| 录像中 | 仅连接一次左SDK；出现CAN feedback timeout，六关节null、SDK rx_count=0。can0累计TX29,074包、RX0；右臂继续ready/disabled。 |
| 故障后 | 经8765正常disconnect退出故障左worker；没有显式使能、回位或抓帽/挂放命令。 |
| 2026-10-10T21:46:08.464502+08:00 | STOP正常封口，三片MP4首末帧可解码。 |

`rebuild_left_can_bridge.py`报错已改成明确提示缺失can0时用restore_can.sh；Python编译和只读`--check`通过。初始化手册也已更新。恢复接口成功不等于电机通信恢复；在CAN RX仍为0的条件下不继续重复初始化。

- [任务定义](task_prompt.md)与[冻结的历史初位姿](restore_target_reference.json)
- [录像](VIDEO_RECORD.md)、[资源](PERFORMANCE.md)、[当前状态](status.json)
- [三路初态图](reconnect_precheck/)、[SDK请求与故障状态](sdk_connect/)
