# ARX R5 双臂实机初始化与故障恢复手册

更新时间：2026-10-01  
项目目录：`/home/tuojing/arx_r5_control`

本文记录双臂实机从 USB/CAN、SDK 到 8768 代理的初始化顺序，以及本次实际遇到的故障和解决方法。它只描述连接和检查，不代表已经完成任何抓取任务。每次重新插拔设备后都要重新读取状态，不能直接套用历史 PID、关节角或末端坐标。

## 1. 硬件映射

| 物理对象 | 稳定身份 | 软件通道 | 上游服务 | 腕部相机 |
| --- | --- | --- | --- | --- |
| 左臂 | CANable 序列号 `208833765931` | `can0` | `8765` | `CV2C8610015R` |
| 右臂 | CANable 序列号 `2088335E5931` | `can1` | `8766` | `CV2C86100180` |
| 全局相机 | 设备序列号由 CameraHub 管理 | `external` | 8768 转发 | - |
| 双臂代理 | 本机 HTTP | - | `8768` | `gemini`、`gemini_right`、`external` |

`/dev/ttyACM0`、`/dev/ttyACM1`、`/dev/ttyACM2` 会随 USB 插拔变化，不能用它们判断左右；始终使用 `/dev/serial/by-id/` 下的序列号路径。物理左右不能仅凭全局画面中的屏幕左右判断，换线或移动相机后要重新核对。

## 2. 开始前的安全条件

1. 两臂物理支撑稳定，手远离夹指；初始化 SDK 可能使能电机并回零。
2. 回零路径和两臂工作区清空，移走杯子、线缆和其他易碰物品。
3. 关闭旧的自动策略、人工保持宿主和第二个控制窗口；同一个 owner 不能启动两个控制端。
4. 确认两个机械臂本体电源都打开，CANable 的两段线都插紧。
5. 初始化阶段只观察状态，不发送抓取或位置目标；必须等 `ready`、六个有限关节角、空错误码和新鲜 RX 反馈同时成立。

## 3. 只读检查

```bash
cd /home/tuojing/arx_r5_control
ps -eo pid,ppid,etime,stat,args | rg 'robot_worker.py|app.py|record_workbench.py|supervised_.*policy'
ls -l /dev/serial/by-id/
ip -details -statistics link show can0
ip -details -statistics link show can1
```

不要把 `can0 UP`、USB 枚举或 CAN 统计包数量当作电机通信成功。真正的健康条件是：

```text
robot_status=ready
worker_fault_reason=null
error_codes=[]
joints_deg 有 6 个有限数值
rx_age_ms 很小并持续更新
rx_count 在连续读取之间增加
enabled=false、owner=null（初始化完成后再由唯一控制端使能）
```

快速读取两臂状态：

```bash
.venv-policy/bin/python - <<'PY'
from visual_control import ArmWorkbenchClient
import json
for side in ('left', 'right'):
    s = ArmWorkbenchClient('http://127.0.0.1:8768', side).state()
    print(side, json.dumps({k: s.get(k) for k in (
        'robot_status', 'enabled', 'moving', 'owner', 'worker_running',
        'worker_fault_reason', 'error_codes', 'rx_age_ms', 'rx_count',
        'joints_deg', 'gripper_raw', 'message')}, ensure_ascii=False))
PY
```

检查相机时使用超时，避免一台坏相机阻塞全部检查：

```bash
timeout 4 .venv-policy/bin/python - <<'PY'
from visual_control import WorkbenchClient
c = WorkbenchClient('http://127.0.0.1:8768')
for name in ('external', 'gemini', 'gemini_right'):
    try:
        frame, seq, device = c.camera(name)
        print(name, 'ok', seq, device, len(frame))
    except Exception as exc:
        print(name, 'error', type(exc).__name__, exc)
PY
```

相机能返回 JPEG 只说明图像流可读，不能证明机械臂通信或空间标定正确。全局相机必须能同时看到两臂、目标物体和中间放置区域，才能开始双臂任务。

## 4. CAN 初始化

### 4.1 正常情况下

已有健康的 `can0`/`can1` 时不要重复运行桥接命令。左侧旧入口如下，只在 `can0` 确实不存在且没有左 SDK worker 时使用：

```bash
cd /home/tuojing/arx_r5_control
./connect_can.sh
```

右侧没有等价的一键脚本。只有在 `can1` 不存在、右 SDK worker 已退出、适配器 by-id 路径确认正确时才手动建立：

```bash
sudo slcand -o -f -s8 \
  /dev/serial/by-id/usb-Openlight_Labs_CANable2_b158aa7_github.com_normaldotcom_canable2.git_2088335E5931-if00 \
  can1
sudo ip link set can1 up
ip -details -statistics link show can1
```

`-s8` 是当前 CANable 的 1 Mbit/s 配置。不要在 SDK worker 仍运行时拔 USB、替换桥接或运行恢复脚本。

### 4.2 `can0` 不存在时的标准恢复

项目提供的 `tools/restore_can.sh` 只恢复固定序列号的左 CANable，不初始化 SDK、不回零：

```bash
cd /home/tuojing/arx_r5_control
sudo ./tools/restore_can.sh
```

脚本会拒绝以下情况：预期适配器不存在、`can0` 已存在、左 `robot_worker.py` 仍在运行、旧桥进程参数发生变化、适配器被其他程序占用。遇到拒绝时先读进程和状态，不要改脚本绕过检查。

本次真实故障就是旧 `slcand` 进程还在，但 `can0` 内核接口已经消失。表现为：

```text
candump can0 -> Device does not exist
robot.log -> Unable to transmit: Socket not open
left joints_deg -> null
left rx_count -> 0
```

处理顺序是：

1. 通过 8768 对左臂发送 `disconnect`，等待左 worker 退出；不要直接 `kill -9`。
2. 运行 `sudo ./tools/restore_can.sh`，确认输出 `CAN interface restored`。
3. 重新检查 `ip -details ... can0`，再从上游 8765 连接左 SDK。
4. 等待左侧 `ready` 和真实关节反馈，不能因为接口变成 `UP` 就继续。

如果 `can0` 存在但 RX 为 0、关节仍为 null，优先检查左臂本体电源、机械臂端 CAN 插头、CANable 到机械臂的线缆/焊点以及左右适配器是否接反。`can1` 有包而 `can0` 无包时，问题不在 GPT 推理或 IK。

## 5. 启动上游服务与 SDK

若 8765/8766 已经运行且只是短暂断开，优先复用服务；不需要为了启动策略而重启 SDK。冷启动时分别在两个终端运行：

```bash
# 终端 A：左臂
cd /home/tuojing/arx_r5_control
./start.sh --live --no-browser --supervised-policy \
  --port 8765 --can can0 --wrist-serial CV2C8610015R
```

```bash
# 终端 B：右臂
cd /home/tuojing/arx_r5_control
./start.sh --live --no-browser --supervised-policy \
  --port 8766 --can can1 --wrist-serial CV2C86100180
```

也可以使用项目当前等价的 `python3 app.py --live ...` 命令。打开各自页面点击连接，或在已认证的本地客户端发送：

```python
client.command('connect', acknowledge_initialization=True)
```

`connect` 不是只读操作：厂商 SDK 构造包含电机初始化/回零，务必在工作区清空、机械臂支撑和操作者在旁时执行。连接后逐侧等待 `robot_status=ready`，不要同时点击两个连接按钮，也不要在 8768 的成对 owner 中发送 `connect`；8768 的成对接口只负责已连接设备的监督控制。

## 6. 启动 8768 双臂代理

冷启动且没有旧代理时生成一次新的成对 owner：

```bash
cd /home/tuojing/arx_r5_control
R5_PAIRED_CLIENT="$(python3 -c 'import uuid; print("dual-policy-" + uuid.uuid4().hex)')"
.venv-policy/bin/python record_workbench.py \
  --upstream http://127.0.0.1:8765 \
  --right-upstream http://127.0.0.1:8766 \
  --port 8768 --paired-policy-client "$R5_PAIRED_CLIENT"
```

运行中的代理先通过 `/api/arms` 读取当前 `paired_policy_client`，不要照抄旧会话 ID。只有这个 owner 可以同时控制左右两臂；普通网页控制仍有单臂互锁。8768 不是物理防碰撞系统，双臂路径仍须人工观察。

## 7. 连接后检查与任务顺序

以本次 2026-10-01 恢复后的状态为例：左右均为 `ready`、`enabled=false`、`owner=null`、错误码为空，左 `can0` 和右 `can1` RX 都在增长。记录在：

`analysis/cups_task_20261001/connected_left_state.json`  
`analysis/cups_task_20261001/connected_right_state.json`

开始“左杯放中间、右杯叠放”前，按以下顺序：

1. 保存三路相机和两臂状态快照，确认两个杯子、放置中心和双臂路径都可见。
2. 只启动一个双臂监督宿主，先建立两臂带电保持；另一控制端不能占用 owner。
3. 左臂先抓第一只杯子，分开核验接触、抬起和运输；把杯子放到中间并松爪，确认杯底稳定后再退离。
4. 重新观察全局图，右臂再抓第二只杯子；不要沿用左臂的绝对坐标或正负方向。
5. 右臂下降到第一只杯子上方，保持垂直和低速，确认叠放稳定后才松爪并退离。
6. 每个阶段都保存 `top`、对应腕图和状态；夹爪目标/反馈不能单独证明杯子已抓牢或站稳。

## 8. 常见故障表

| 现象 | 典型原因 | 处理 |
| --- | --- | --- |
| `can0` 不存在 | USB 重插后旧 SLCAN 桥残留/消失 | 退出左 worker，运行 `sudo ./tools/restore_can.sh` |
| `can0 UP` 但 RX=0、关节为 null | 左臂供电、CAN 线、焊点、适配器映射或物理端口问题 | 查物理链路；不要使能，不要发送目标 |
| `can1` 有包、`can0` 无包 | 故障集中在左臂链路 | 保持右臂失能，单独修左侧 |
| `SDK motor fault` 或错误码重复 | 电机未响应、初始化失败或 SDK 保护模式 | 断开故障 worker，检查电源/线缆，恢复后重新初始化 |
| `Unable to transmit: Socket not open` | worker 仍引用已经消失的 CAN socket | 断开 worker，重建对应 SLCAN 接口，再连接 SDK |
| 相机超时 | USB 相机/CameraHub 卡住或设备被占用 | 只读重试；检查 `/dev/video*`/USB；不要把旧图当新观察 |
| `ready` 但关节角为空 | 上游状态缓存或 worker 尚未产生有效反馈 | 等待 RX 增长；仍为空就断开，不能移动 |
| 代理拒绝 `connect/home` | 8768 成对 owner 设计上禁止底层初始化 | 在 8765/8766 上逐臂连接，完成后再由 8768 接管 |

## 9. 日志与证据

- SDK/worker 日志：`/home/tuojing/arx_r5_control/robot.log`
- 本次 CAN 恢复记录：`analysis/cups_task_20261001/reconnect_attempt_20261001.json`
- 本次初始化状态：`analysis/cups_task_20261001/connected_left_state.json`、`connected_right_state.json`
- 本次杯子任务状态：`analysis/cups_task_20261001/status.json`
- 总交接文档：`PROJECT_HANDOVER.md`

不要把 sudo 密码、控制 token 或旧 owner 写进文档。执行日志只记录故障现象和处理命令，不记录凭据。

## 10. 当前快照

本次 CAN 重建和 SDK 重连后，左右两臂都已经恢复为 `ready`，但仍是失能、无 owner、未执行任何杯子动作。下一次开始实验前仍要重新做第 3 节检查；如果相机再次超时，先解决相机采集，不要继续使用过期图像。
