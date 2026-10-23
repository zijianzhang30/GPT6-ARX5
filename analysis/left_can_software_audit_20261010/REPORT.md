# 左臂 CAN/SDK 软件链路复查（2026-10-10 22:23–22:31 CST）

本次按“硬件暂视为正常”的假设，逐层检查主机接口、桥接脚本、SDK 进程和状态展示。没有连接左臂 SDK、使能或发送电机/CAN 动作帧。左臂保持失能且 SDK worker 已退出；右臂保持原有失能状态。

## 复查结果

| 层 | 实测/代码证据 | 判定 |
| --- | --- | --- |
| USB 设备身份 | 左 CANable 固定序列号 `208833765931` → `/dev/ttyACM2`；右 `2088335E5931` → `/dev/ttyACM0`。`journalctl -k` 显示左侧在 22:02:07 重新枚举。 | 当前左右映射正确；不能用会变化的 ttyACM 编号作持久映射。 |
| 左串口命令通道 | 暂停唯一的左 `slcand`，仅发送 SLCAN `V` 查询，返回 `16e7497-dirty github.com/normaldotcom/canable2.git`；随即用原 `restore_can.sh` 恢复 `can0`，右 `can1` ifindex 仍为 32。 | PC→左 CANable 的 USB/串口命令通道可用；**不证明** CANable→电机总线可收发。原查询脚本最初误把 USB 产品名的 `b158aa7` 当作必需固件版本，退出码 1；原始返回有效，脚本验证规则已修正，未重复查询。 |
| 桥接 | 左唯一 `slcand -o -f -s8 <左固定 by-id> can0`，右相同参数但使用右 by-id 和 `can1`。`restore_can.sh` 成功重建左接口，当前 `can0` UP。`slcand` 源码表明 `-s8` 启动时发 `C`、`S8`，然后 `O`；不需要增加 `-c` 才能设 1 Mbps。 | 未发现通道串接或漏设速率；`can0 UP` 只证明虚拟接口已建立。 |
| 启动脚本边界 | `connect_can.sh` 只检查左 by-id 是否存在、创建/抬起 `can0`；`restore_can.sh` 还检查左 worker、旧桥接进程与接口状态。`rebuild_left_can_bridge.py` 只适用于旧桥和 `can0` 均仍存在。 | 这些脚本都不验证电机回包；本次不能把它们的成功退出当作 SDK 恢复。 |
| SocketCAN 接收 | 22:12:43–22:13:15 的第 8 轮左 SDK 初始化期间，`can0` TX 24,312、RX 0；六关节为空，SDK 报反馈超时。第 8 轮 worker 退出后 TX 停止增长；本次桥接重建后计数归零。右 `can1` RX 持续增长，右 worker 有真实关节反馈。 | 故障边界在左侧 CAN 回包到达内核之前；不是单纯网页解析或 AI 策略问题。TX 计数并不等于电机已接收。 |
| SDK/接口 | 左、右使用同一个 `robot_worker.py`、同一 `r5_live_sdk` 模块及同一构造方式，仅 CAN 通道参数不同；左 worker 当前已退出，右 worker 正常。`robot_worker.py` 的本地回显过滤不会解释内核层 `can0 RX=0`。 | 暂无左侧专属 SDK 配置错误证据；不能据此排除适配器固件、总线参数或下游通信问题。 |
| 控制网页 | `live_control.py` 原先把第一条 worker 采样标为“已收到实机反馈”，即使 `rx_count=0` 且同一条采样随后判故障；连接新 worker 时也未清掉旧的收包数和错误码。 | 已修正显示/状态判定，避免误报就绪；它不是本次零回包的根因。运行中的 8765 服务尚未重启，所以旧进程仍会显示历史提示；修改在下次计划内重启时生效。 |

## 修改与验证

- 新增 `query_adapter_version.py`：在两臂失能、无人占用且左 worker 退出时，查询左适配器 `V` 响应并恢复原桥接；不会创建 SDK 或发 CAN 动作帧。原始查询输出保留在 `adapter_version_result.json`，其中 `firmware_response_valid:false` 是初版验证规则的误判，不能作为固件无响应的证据。
- `live_control.py`：新连接清除旧 RX 诊断字段；只有收到有效 CAN 回包且反馈无故障时才进入 `ready` 并显示“已收到实机反馈”。
- `tests/test_live.py`：增加零回包故障采样回归测试。`.venv-policy/bin/python -m unittest tests.test_live`：21 项通过。
- 重建后的 `can0` UP、RX/TX 均为 0（未再连接 SDK）；右 `can1` RX 继续增长。没有因为本次软件审查而重新初始化电机。
- 末态见 [`state_snapshot.json`](state_snapshot.json)：左 `fault/disabled/worker_running=false/rx_count=0`，右 `ready/disabled/worker_running=true`。

## 当前结论与下一分界

按现有证据，USB 枚举、固定序列号映射、主机串口命令通道、桥接创建、SDK 通道参数都可核对为正常或无异常；**左电机响应仍未恢复，也不能在硬件正常的假设下直接认定是 SDK 代码故障**。下一个能区分的检查是验证左 CANable 到总线的真实位速率、收发/错误状态，以及电机是否在总线上应答；只有拿到新的总线证据，才值得再做一次可能回零的 SDK 初始化。现有任务 skill 要求“仍无反馈时停止重复初始化”，所以本次没有循环连接或使能。

参考：第 8 轮[实验记录](../../HAT_HANGING_EXPERIMENT_RECORD_20261010_TRIAL08.md)、[初始化手册](../../MACHINE_INITIALIZATION_RUNBOOK.md)、[共用执行流程](/home/tuojing/.codex/skills/arx-r5-tabletop-tasks/references/common-execution.md)。
