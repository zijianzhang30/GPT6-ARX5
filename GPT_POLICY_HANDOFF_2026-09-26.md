# R5 + GPT-Policy 抓网球：修改记录与启动方法

记录日期：2026-09-26。项目目录：`/home/tuojing/arx_r5_control`。

**当日晚间更新：当前启动命令和步幅以第 9 节为准；第 3 节的 6°/8.25° 是此前版本的记录。**

这份文档用于接续本轮开发，重点是已经修了什么、如何启动刚刚运行的版本，以及下次应先处理什么。历史测试结果与本次收尾时重新检查的实机状态分开记录。

## 1. 目前实现到哪里

已经跑通：双相机实时图像和关节反馈 -> GPT-Policy 原版决策循环 -> GPT 输出末端目标 -> R5 官方运动学解算和连续 IK 修正 -> 定时关节轨迹 -> 现有 SDK worker 执行 -> 读取实测反馈和新图像 -> 下一次决策。

- 任务：抓取网球。
- 本轮配置和运行日志记录的模型：`gpt-6-astra`。
- 控制入口：`supervised_policy.py`，使用 `cartesian` 接口、`image_grasp` 阶段。
- 两路相机：`left` 是 Gemini 手腕 RGB，`top` 是外部全局 RGB，名字不代表它一定在正上方。
- GPT 能看到实测关节角、命令关节角、跟踪误差、关节范围、TCP、夹爪状态、图像和上一动作结果。
- 实机已连续完成多段接近和姿态调整，单独夹爪闭合/张开测试也已完成。
- **尚未验证成功抓住并抬起网球。最后这轮没有模型闭爪动作，不能把接近成功写成抓取成功。**

这是沿用 GPT-Policy 决策循环、工具调用和反馈流程，再适配 R5 硬件；相机、TCP 估计、夹爪单位和执行监督仍是本项目的适配内容，不等于原测评环境完全一致。

## 2. 已修复的 bug 和行为问题

### 2.1 接入官方 R5 解算，处理坐标原点和 IK 分支

涉及：`r5_official_solver.py`、`r5_cartesian.py`、`tests/test_r5_official_solver.py`。

- 改用厂商原生 `KinematicSolver` 提供 FK/IK，并接入上游 `ContinuousIK` 修正。
- 单独加载解算库，不实例化机械臂，不因为离线解算而连接 CAN 或回零。
- 官方独立解算器的 FK 扣除了零位平移；适配器恢复这个偏移，再处理 link6 到 TCP 的变换，避免不同坐标原点混用。
- 偏移由零位 FK 计算；此前核对值约为 `[0.0977, 0.0000495592, 0.1635000004]` 米。
- 官方 IK 没有 seed 参数或明确成功状态，因此增加有限数检查、角度周期对齐、关节范围和分支距离检查。
- 用多个姿态比较官方 FK 与项目 URDF，启动时检查坐标约定是否一致。

官方模型来源：`https://github.com/ARXroboticsX/R5`，配置记录的 revision 为 `e87d09c11edb65f6ae672abc7a41fe2277a2f12f`。详见 `r5_cartesian_profile.json`。

此前完成过 12 个动作的离线回放核对。官方和旧解算在已核对目标上的差异很小，不能把此前所有抖动或偏差都归因于旧 IK。

### 2.2 修复不同层跟踪容差不一致，减少小偏差导致的停止

涉及：`motion_safety.py`、`live_control.py`、`policy_hold_gate.py`、`r5_policy_backend.py`、`visual_control.py`、`supervised_policy.py`。

原问题：执行层已经接受动作，但后续保持或恢复检查仍按更小的容差拒绝，容易出现刚走完又停止。

- 动作完成残差上限统一为 `2.5°`；保持和轨迹跟踪上限统一为 `3°`。
- 服务通过 `policy_tracking_limits_deg` 公布实际容差，策略启动前检查双方一致，避免只更新脚本、旧服务却仍运行。
- 仍要求新鲜反馈、稳定采样和实际运动进展；不是超时后无条件认为动作完成。
- 续段重新建立保持参考时标记 backend 为 busy，避免监督线程把短暂恢复状态误判为保持失败。
- 保持阶段仍检查命令与保持目标一致，错误日志打印具体残差。

CAN 超时、SDK 错误、无效关节反馈等故障没有被当成普通位置偏差放行。

### 2.3 取消固定 4 mm 的任务步幅，并明确命令/实测坐标用途

涉及：`r5_cartesian.py`、`r5_tennis_wrist_policy_context.json`、`policy_trajectory.py`。

- 不再要求每个末端目标只移动 4 mm；GPT 根据当前画面和反馈选择绝对 TCP 目标或多个 waypoint。
- 增量规划使用完整 `tcp_command_xyzquat` 作参考，实测 TCP 用于判断实际进展；提示词禁止混拼实测位置和命令姿态。
- 通过官方 IK、连续路径修正和 Ruckig 时间参数化执行，仍有每步关节变化及会话行程限制。
- GPT 仍可能自行选择 2～5 mm 等小动作。这不代表固定 4 mm 限制还存在。

### 2.4 夹爪闭合步幅扩大 10 倍，修复较长动作超时

涉及：`motion_safety.py`、`visual_control.py`、`r5_cartesian.py`、`r5_policy_backend.py`、`gripper_cycle_trial.py`。

- 已实测确认：raw 增大是张开，raw 减小是闭合。
- 闭合单步上限由 `0.1 raw` 增加到 `1.0 raw`；张开单步仍为 `0.1 raw`。
- 每段夹爪累计行程预算为 `5.0 raw`。
- 这是放大允许的闭合增量，不是把绝对目标值乘以 10；raw 也不是毫米。
- 归一化接口分别向模型提供张开和闭合步幅上限。
- 夹爪执行等待时间按行程和速度计算，避免 1 raw 的闭合动作被旧的固定 5 秒等待误判为超时。
- 夹爪驱动速度没有乘以 10；当前 speed=0.3 时，约为 `0.18 raw/s`，1 raw 的命令行程约需 5.6 秒。

实机独立开合记录：`analysis/gripper-cycle-7d604c8bd7c1/events.jsonl`。

| 项目 | 实测/记录值 |
| --- | --- |
| 初始命令 | 3.850286 raw |
| 初始反馈 | 3.750286 raw |
| 闭合后反馈 | 2.750439 raw |
| 重新张开后反馈 | 3.748760 raw |
| 最终命令 | 3.850286 raw |
| 是否修改机械臂关节目标 | 否 |
| 是否属于成功抓球测试 | 否，仅开合测试 |

### 2.5 修复预算拒绝污染状态，以及续段卡在相同拒绝上的问题

涉及：`r5_policy_backend.py`、`policy_trajectory.py`、`r5_policy_deployment.py`、`supervised_policy.py`。

- 先在 guard 副本上预检查预算，拒绝的动作不再直接污染正在使用的 guard、造成后续一直 fault。
- 模型决策前检查已知的会话边界，避免反复让模型生成必然被同一预算拒绝的动作。
- 识别夹爪预算耗尽和符合条件的运动预算边界，允许在有人看护的模式下保持当前位置、续开下一段预算。
- `--auto-renew-guided` 不会无条件清除硬件故障，也不是任何失败都自动续跑。

### 2.6 修复模型超时后的恢复流程

涉及：`supervised_policy.py`，以及 `vendor/GPT-Policy-main/src/gpt_policy/` 下的 `harness/errors.py`、`harness/waiting.py`、`harness/providers/codex.py`、`runtime/runner.py`。

- 单次决策设约 25 秒 deadline，监督和心跳在等待模型期间继续运行。
- 内层等待继承上层健康检查和 deadline，避免内层等待绕过超时约束。
- 超时后丢弃本次未完成决策，重建模型传输会话；恢复已完成历史，重新采集观测后再决策。
- 有界恢复：最多 20 次重试、总恢复窗口 300 秒；不回放过期动作。

因此偶尔等待二三十秒不一定是死锁；但目前还是“观察 -> 推理 -> 执行 -> 保持 -> 再观察”的逐步闭环，不是连续实时视觉伺服。本轮常见推理等待约 16～21 秒，叠加执行、稳定确认和偶发重试，运动看起来仍是一段一段的。

### 2.7 区分标定验证阶段和图像抓取阶段，强化双视角输入

涉及：`r5_cartesian.py`、`r5_policy_deployment.py`、`r5_tennis_wrist_policy_context.json`。

- `motion` 等验证阶段与 `image_grasp` 分开，修复图像抓取仍被“必须先有完整标定”提示卡住的问题。
- `image_grasp` 允许依据双视角、关节反馈和已观察到的局部响应进行有人看护的图像引导修正。
- 全局视角优先判断接近距离、高度、桌面间隙；手腕视角辅助横向对中和球在指间的位置。
- 不能因为腕视图里球居中、变大，就直接判定已经到达抓取位置。

当前 TCP 仍采用原厂未改夹指、约 8 cm 的估计。`r5_cartesian_profile.json` 中 `kinematics_verified=false`，相机内参/手眼外参没有完成标定。官方解算正确加载不等于这些物理参数已经实测准确。

## 3. 当前关键参数

参数来源：`motion_safety.py`。下表是本轮收尾时的值。

| 参数 | 值 | 含义 |
| --- | --- | --- |
| `JOINT_STEP_DEG` | 6.0 | 每步单关节变化上限，度 |
| `JOINT_STEP_NORM_DEG` | 8.25 | 每步联合关节变化范数上限，度 |
| `JOINT_MARGIN_DEG` | 2.0 | 距关节限位的余量，度 |
| `SUPERVISED_SPEED` | 0.3 | 当前监督执行速度比例 |
| `POLICY_SETTLE_ERROR_DEG` | 2.5 | 完成判定残差上限 |
| `POLICY_HOLD_ERROR_DEG` | 3.0 | 保持残差上限 |
| `POLICY_TRACKING_ERROR_DEG` | 3.0 | 轨迹跟踪残差上限 |
| `GRIPPER_STEP_RAW` | 0.1 | 单步张开上限 |
| `GRIPPER_CLOSE_STEP_RAW` | 1.0 | 单步闭合上限 |
| `SESSION_EXCURSION_DEG` | 20.0 | 会话相对起点偏移限制 |
| `SESSION_JOINT_TRAVEL_DEG` | 60.0 | 会话累计关节行程预算 |
| `SESSION_GRIPPER_TRAVEL_RAW` | 5.0 | 会话累计夹爪行程预算 |
| `SESSION_PROPOSALS` | 20 | 会话动作建议预算 |

## 4. 怎么启动刚刚这套推理

下面命令均在项目根目录执行。它们用于下次启动；写本记录时没有重新启动机械臂。

### 4.1 检查 CAN 和现有服务

```bash
cd /home/tuojing/arx_r5_control
ip -brief link show can0
curl --fail --silent --show-error --max-time 3 http://127.0.0.1:8765/api/state
```

USB 重新插拔后，若 can0 不存在或未启动，再运行：

```bash
./connect_can.sh
```

不要照抄旧对话里的 PID 去 kill 进程。脚本启动 CAN 接口不等于 SDK 已恢复正常，仍要检查状态。

### 4.2 启动控制服务并连接硬件

已有健康的同版本服务时复用它；不要同时开第二个 SDK 控制同一机械臂。需要重新启动服务时，在终端 A 执行：

```bash
cd /home/tuojing/arx_r5_control
./start.sh --live --no-browser --supervised-policy --port 8765
```

打开 `http://127.0.0.1:8765`，通过工作台连接机械臂。**SDK 连接初始化可能回零**，先清空回零路径并在旁观察。故障恢复后应看到 `robot_status=ready`、`error_codes=[]`、六个有效关节值、新鲜 CAN 反馈。

正常策略启动前机械臂应没有其他控制者占用；`prepare_hold` 会建立使能、心跳和稳定保持。未使能时 `policy_execution_available=false` 本身不一定是故障；策略准备阶段需连续验证约 3 秒稳定保持后才获准执行。

### 4.3 离线配置检查

在终端 B 执行：

```bash
cd /home/tuojing/arx_r5_control
.venv-policy/bin/python supervised_policy.py \
  --check \
  --policy-interface cartesian \
  --camera-mode both \
  --cartesian-stage image_grasp \
  --calibration-profile r5_cartesian_profile.json
```

这个检查不连接硬件、不调用模型。期待当前选择的阶段显示 `configuration_ready`；其他依赖完整标定的阶段仍可能列出 blockers，不要因此误换掉 `image_grasp`。

### 4.4 启动双相机 GPT-Policy 实机抓取

这是刚刚使用的启动方式，明确写全端口、相机和阶段，避免落到脚本默认的其他配置：

```bash
cd /home/tuojing/arx_r5_control
.venv-policy/bin/python supervised_policy.py \
  --supported-supervision \
  --url http://127.0.0.1:8765 \
  --policy-interface cartesian \
  --camera-mode both \
  --cartesian-stage image_grasp \
  --calibration-profile r5_cartesian_profile.json \
  --input-json r5_tennis_wrist_policy_context.json \
  --auto-renew-guided \
  --max-guided-segments 16 \
  --max-decisions 20
```

- 使用已有 `.venv-policy`，其中有 Ruckig 和解算依赖。
- 任务“抓取网球”和示范上下文来自 `r5_tennis_wrist_policy_context.json`。
- 模型通过 `policy_runner.upstream_config()` 加载 `vendor/GPT-Policy-main/configs` 下的 Codex 配置；看启动输出的 `model` 和日志确认实际选择，不能只改输入 JSON 就认为模型已切换。
- 启动后会打印新的 `analysis/live-policy-...` 日志目录。
- 如果夹爪起初闭合且确认为空，可在启动命令末尾加 `--open-gripper-to 4.8` 做张开准备。它会真实驱动夹爪，不是只改参数；刚刚这轮运行时夹爪已经张开。
- 模型等待期间策略进程负责心跳、相机监督和保持，不要关闭终端当作“暂停”。

### 4.5 续跑和退出的实际语义

看到 `holding_for_operator` 后，在策略终端输入：

```text
continue
```

表示在当前带电保持位置续开预算、继续自主推理；**不等于立即发一个闭爪命令**。

```text
stop
```

表示结束控制并清理。当前实现只在一段 `run_r5_policy` 返回后处理这些输入，不是实时动作中断接口。运行中的紧急情况不能依赖排队的 `stop` 字符串。

`Ctrl+C` 也会进入清理并请求停止。现场曾观察到停止/失使能后机械臂下垂或回落，不能把退出脚本当成保持当前位置。断开再连接 SDK 还可能回零。

**当前旧进程没有“暂停模型但保持使能，然后插入一次手动闭爪”的运行时入口。** 不要启动第二个控制客户端冒用 owner 并发发夹爪命令。这个入口是下次待实现项。

## 5. 本轮结束状态与剩余问题

### 5.1 最后一次运行的真实结果

最终目录：`analysis/live-policy-114f09e0170d_unreviewed/`。

- `status.json`：`state=failed`、`error=R5ExecutionFault`、`physical_success_verified=false`。
- 整轮约 1727 秒，日志记录 90 次模型决策：31 次 `move_eef_chunk`、45 次 `move_to`、13 次 `check_path`、1 次 `give_up`。这些是决策计数，不代表全部通过并执行。
- 自动续段 10 次，随后有一次人工 `continue`。
- 没有模型闭爪决策。
- 模型曾因画面中人手进入夹指区域、拿起球而 `give_up`，当时保持张开和带电保持。
- 随后确认手离开、球放回桌面，输入了 `continue`。模型只又执行了一个小幅下降动作，尚未闭爪。
- 接着出现 CAN 接收反馈过期，监督层报错并退出。工作台状态为 `enabled=false`、`moving=false`、`owner=null`、`robot_status=fault`，worker 报 `SDK motor fault`，关节反馈为 null，并有多项 SDK 错误码。
- 最后一个已完成动作的最大关节残差约 `0.302°`。随后故障不能直接解释成超过 3° 的普通跟踪误差；需要检查硬件/CAN/SDK 原因。

记录时策略进程已退出，没有后台继续抓取。工作台服务仍能响应 HTTP，但这不表示机械臂健康；明天先恢复连接和有效反馈，不要直接续发旧目标。没有确认该故障是断电、拔线还是其他硬件原因。

### 5.2 为什么还不闭爪

当前闭爪条件主要是模型对图像中夹持位置、桌面间隙和障碍的判断，没有一个固定的“距离小于多少厘米就闭合”的已标定阈值。

目前提示词过于强调全局视角必须确认两侧夹持，近侧夹指挡住球或远侧接触面不可见时，模型容易反复微降、后退、抬高和转腕，而不进入试闭合。这是目前需要改进的策略问题；夹爪命令链路本身已经通过独立开合测试。

**已讨论但尚未实现的改进：** 联合全局高度/间隙与腕视指间位置，避免要求全局无遮挡地看到所有接触面；条件合理时允许小幅试闭合，执行后重新观察。保留人手、桌面和线缆冲突检查。试闭合不等于抓取成功，还需要后续独立抬升并确认球跟随。

### 5.3 明天建议按这个顺序继续

1. 恢复 CAN/SDK 健康反馈，确认双相机位置和画面；必要重连时先清空回零路径。
2. 补上单一控制 owner 内的操作员闭爪入口：暂停/结束当前推理，在保持状态获取新鲜观测，执行单次受限夹爪动作，再保持并反馈。避免退出掉电或多个控制者抢命令。
3. 调整闭爪判定提示词，解决已经靠近却因遮挡反复对齐的问题；这项修改需要新运行加载，不能只改磁盘文件就声称旧进程已生效。
4. 先验证从当前合适位置小幅闭爪及反馈，再重新运行完整接近、闭合、抬升流程。
5. 后续改进日志帧命名：当前自动续段 step 编号重置，可能覆盖上一段同名图片；图片不能当作整轮无缺失视频。

## 6. 验证记录与后续回归命令

本轮前续开发记录中，相关完整测试曾达到 129 tests + 31 subtests 通过；最近一次阶段/提示词修改后，相关 Cartesian/deployment 的 32 项测试通过。本次写文档重新核对了代码、参数、运行日志和实机状态，没有重新运行整套测试，也没有重新启动运动。

文档收尾时实际执行了第 4.3 节的离线配置检查，结果为 `configuration_ready`、`image_grasp` 的 `blockers=[]`、`hardware_accessed=false`、`model_called=false`；同时核对了关键引用路径均存在。这个结果只证明配置检查通过，不代表收尾时处于故障状态的实机已经恢复。

下次改代码后的相关离线回归命令：

```bash
cd /home/tuojing/arx_r5_control
.venv-policy/bin/python -m pytest -q \
  tests/test_r5_official_solver.py \
  tests/test_r5_cartesian.py \
  tests/test_r5_policy_backend.py \
  tests/test_r5_policy_deployment.py \
  tests/test_r5_loop_recovery.py \
  tests/test_policy_trajectory.py \
  tests/test_policy_hold_gate.py \
  tests/test_motion_safety.py \
  tests/test_gripper_cycle_trial.py \
  tests/test_supervised_policy.py
```

独立夹爪实机开合脚本是 `gripper_cycle_trial.py`，会真实执行“闭合再张开”，不适合作为已经夹住球后的默认验证，也不要和自主策略同时运行。

## 7. 接手时优先看的文件

| 文件/目录 | 用途 |
| --- | --- |
| `supervised_policy.py` | 实机策略主入口、保持准备、超时、续段、清理 |
| `r5_policy_deployment.py` | 双相机观测、上游 run loop 接入、状态输入 |
| `r5_cartesian.py` | Cartesian 工具、TCP/夹爪映射、阶段提示词 |
| `r5_official_solver.py` | R5 官方 FK/IK 适配 |
| `r5_policy_backend.py` | 动作执行、预算、等待反馈、保持 |
| `policy_trajectory.py` | 定时轨迹和轨迹预算 |
| `live_control.py`、`robot_worker.py` | 工作台控制和 SDK worker |
| `motion_safety.py`、`policy_hold_gate.py` | 参数与保持资格检查 |
| `r5_tennis_wrist_policy_context.json` | 抓网球任务、历史示范、当前双视角规则 |
| `r5_cartesian_profile.json` | 官方模型来源、TCP 估计、未标定项、夹爪映射 |
| `vendor/GPT-Policy-main/` | 原版循环及本地超时恢复修改 |
| `analysis/live-policy-114f09e0170d_unreviewed/` | 最后一轮事件、状态、推理与图片 |
| `analysis/gripper-cycle-7d604c8bd7c1/` | 独立开合实机证据 |
| `analysis/operator-grasp-check-20260926/` | 人工闭爪请求前后额外采集的双视图 |

明天继续时可直接说明：先读本文件，恢复 CAN/SDK 健康状态，补单次闭爪入口和近距离闭爪判断，再用第 4.4 节命令启动双相机 `image_grasp` 推理。

## 8. 2026-09-26 上午恢复记录

- 操作员调整了全局相机位置；已在 `r5_tennis_wrist_policy_context.json` 明确记录视角改变，要求依据新图像重新判断，不复用旧全局像素方向或外参。
- 重新上电后，仅重连 SDK 仍没有 CAN 回包。主机 can0 的发送计数增长、接收计数不变。
- 关闭故障 SDK worker 后，重新建立对应 CANable2 的 slcand/can0 通道，再连接 SDK，反馈恢复。
- 恢复检查：`robot_status=ready`、`error_codes=[]`、`rx_age_ms=1`，六个有效关节角；初始化后的夹爪反馈约 `0.138094 raw`，接近闭合。
- 证据保存在 `analysis/power-reconnect-20260926/`；新全局视角首次采集在 `analysis/camera-reposition-20260926-102126/`。
- 此时尚未重新启动抓取策略：初始化后的画面中白色线缆横穿夹爪前方，正在等待操作员移开，再检查画面并启动。

## 9. 晚间更新：自动续段和更大单次动作范围

用户要求继续验证抓球，并减少每次推理只走很小一段、20 次决策后等待的问题。本次修改：

- `motion_safety.py`：单步单关节范围从 6° 改为 12°，联合变化范数从 8.25° 改为 16.5°。官方 IK、轨迹预检和执行层共享这些参数。
- `live_control.py`：服务增加 `policy_step_limits_deg`；`supervised_policy.py` 启动前核对参数，防止新策略配旧服务。
- `r5_cartesian.py`：提示词按实际常量显示限制，并鼓励在两视图确认路径净空的粗接近阶段选择有意义的厘米级进展或短 waypoint 路径。近球、桌面、线缆及接触不明时仍缩小动作；没有固定要求每次都走多少厘米。
- `supervised_policy.py`：新增 `--auto-renew-budgets`，允许决策额度、关节行程和夹爪行程边界自动续段，无需依赖旧示范目标尚未到达。每段仍最多 20 次决策，16 段合计最多 320 次；提前触发行程边界时总决策数可能更少。
- 自动续段不会重新启动 `done`、`give_up` 或故障结果，到达总段数上限后仍等待操作员。
- 修复段结束时先自动续跑、后检查已排队 stop 的顺序问题：现在先检查操作员队列，stop 优先。此修复没有新增实时动作中断功能。
- 关节速度比例仍为 0.3，跟踪容差仍为完成 2.5°、保持/轨迹 3°，夹爪开合步幅未在这次变更中调整。

相关回归：`148 passed, 40 subtests passed`。覆盖较大步幅通过、超速/联合范围超限仍拒绝、新旧服务参数不一致拒绝启动、预算自动续段、完成/故障不续段，以及排队停止优先。

旧策略 `analysis/live-policy-61a259c918ed_failed/` 实际尝试过闭爪，随后重新张开校正，没有确认抓起。其最后一段原本因为 20 次决策用完保持等待，后来又因反馈中断退出。

部署时已重启服务，重新建立 CANable2/slcand 通道并重连 SDK，确认六关节反馈、SDK 无错误和 `policy_step_limits_deg={"joint":12.0,"norm":16.5}`。证据：`analysis/larger-step-restart-20260926/`。

当前启动方式：

```bash
cd /home/tuojing/arx_r5_control
.venv-policy/bin/python supervised_policy.py \
  --supported-supervision \
  --url http://127.0.0.1:8765 \
  --policy-interface cartesian \
  --camera-mode both \
  --cartesian-stage image_grasp \
  --calibration-profile r5_cartesian_profile.json \
  --input-json r5_tennis_wrist_policy_context.json \
  --open-gripper-to 4.8 \
  --auto-renew-budgets \
  --max-guided-segments 16 \
  --max-decisions 20
```

`--open-gripper-to 4.8` 适用于本次初始化后的空夹爪，实际夹持物体时不要直接使用。控制服务仍需 `./start.sh --live --no-browser --supervised-policy --port 8765`，不要重复启动已有服务。

本次新实验启动目录：`analysis/live-policy-53a8c6e38336/`（结束后目录可能附加状态后缀）。是否完成抓取须看实际反馈和视觉证据，启动成功不代表已抓到。

启动后的实际验证：首轮模型请求出现 3 次 25 秒 deadline 重试，随后返回动作。约 15 mm 的首次前进目标仍因整条路径关节范围被拒绝；模型先执行约 5 mm 的校正，下一次 `move_eef_chunk` 成功执行约 10 mm 前进，最大关节残差约 0.984°。说明扩大后的范围确实允许更大的接近动作，但不保证任意姿态每次都能走固定厘米数。该检查时仍在接近阶段，没有确认抓取成功；自动续段逻辑已通过测试，尚未在这条新运行中实际走到首个 20 次边界。

## 10. 固定机械臂、仅测试夹爪

随后实机已验证自动续段，并完成多次闭爪和抬升尝试，但没有确认网球被抬离支撑面。操作者要求停止自主运动、保存当前位置，并将球垫高后专测夹爪。

- 自主策略已返回 `give_up`，原因是观察到操作者的手进入夹指区域；宿主仍带电保持并等待操作员，未自动续跑。
- 保存的姿态：`analysis/stationary-grasp-reference-20260926-213219/reference.json`；最新参考指针：`analysis/stationary-grasp-reference-latest.json`。
- 参考分别记录实测关节角、保持命令角、TCP 估计和夹爪状态，不将实测误差掩盖成命令已精确到达。保存前后保持命令变化为 0°，实测变化为 0°。
- 球垫高后的画面：`analysis/raised-ball-check-20260926-213257/`。
- 新增 `stationary_gripper_trial.py`：只允许 `close RAW_DELTA` / `open RAW_DELTA`，拒绝关节动作、轨迹和预算重锚；监督阶段检查关节命令变化和实测漂移，执行后保留带电保持。不会自动抬升、重开夹爪或恢复旧姿态。
- 测试：`51 passed, 5 subtests passed`，覆盖仅发夹爪目标、禁止关节运动、越界拒绝、漂移故障及参考姿态检查。
- **这项代码还没有接管实机。** 已运行的旧宿主不支持热加载单独闭爪命令。退出旧宿主会释放保持；必须先有机械支撑，才能切换新程序，不能冒用旧 owner 并发发动作。

仅在旧宿主已退出、机械臂得到支撑、无其他 owner 且实际姿态仍在参考容差内时启动：

```bash
cd /home/tuojing/arx_r5_control
.venv-policy/bin/python stationary_gripper_trial.py \
  --supported-supervision \
  --url http://127.0.0.1:8765 \
  --reference analysis/stationary-grasp-reference-20260926-213219/reference.json
```

启动只建立保持并等待输入。新鲜画面确认手已撤离后，可输入 `close 0.2` 做一次小幅闭合，检查反馈和照片再决定后续动作。`open 0.1` 是一次小幅张开，`status` 查询状态；`stop` 退出会释放保持，不能把它当成冻结位置。关节命令固定不保证关节在负载下绝对无误差；实测漂移超过约 1.72° 时会故障停止。

### 本次切换结果

操作者确认机械支撑到位、手已撤离后，旧宿主收到 `stop` 并退出，记录目录为 `analysis/live-policy-53a8c6e38336_unreviewed/`。退出释放了关节保持，实际姿态发生较大变化。夹爪专用程序在使能前的参考检查中拒绝启动：`Arm moved away from saved reference; no automatic pose restoration`，失败记录为 `analysis/stationary-gripper-7e79c2903e6e/`。本次没有发送闭爪命令，也没有恢复旧关节姿态。

后续只读检查保存在 `analysis/stationary-handoff-check-20260926/`。最后一组实测关节角约为 `[-2.743, -0.623, 0.841, -10.918, -5.825, -16.294]` 度；第二关节保存时约为 97.318 度，不能把差异当成容许的小漂移。短时三次采样中角度不变，但这不构成带电保持或机械支撑有效性的证明。服务为 `enabled=false`、`owner=null`，CAN 正常。

最新双视图中网球位于黑色支撑物上，在夹爪前方，尚未进入夹指间。下一步需要操作者重新布置球与夹爪的相对位置；若选择当前姿态做测试，应明确采用新参考并另外保存，不覆盖旧参考或放宽容差来跳过检查。当前没有运行中的夹爪测试宿主。

## 11. 返回保存姿态并执行闭爪（当晚后续）

操作者随后明确授权关节返回保存位置并尝试抓球，原参考文件中的 `automatic_pose_replay_authorized=false` 保留为当时的记录。夹爪反馈曾为 5.199，超过使能范围；最新检查恢复为 3.881 后才开始使能。没有扩大夹爪范围或跳过启动检查。

新增 `return_pose_gripper_trial.py`，复用现有后端和双相机监督。在同一宿主中逐步返回，再锁定关节做夹爪测试，避免切换宿主释放保持。每个 `next` 最多 6 度/关节、8.25 度联合范数，执行后等待下一条命令，需检查最新画面；`renew` 只在锁定前可续预算；`lock` 必须在保存姿态约 1.72 度容差内，锁定后拒绝关节动作和预算重锚。启动不会自动返回，也不会自动闭爪。

```bash
cd /home/tuojing/arx_r5_control
.venv-policy/bin/python return_pose_gripper_trial.py \
  --supported-supervision --restore-saved-pose \
  --reference analysis/stationary-grasp-reference-20260926-213219/reference.json \
  --url http://127.0.0.1:8765
```

本次不是 GPT 自主推理：目标取自操作者授权的保存姿态，由人工逐步检查照片后发 `next`；夹爪也通过明确命令测试。已有运行中的宿主时不要再启动第二份。`stop` 仍会释放保持；该程序没有抬升或解除锁定入口。

首轮 `analysis/return-grip-1a950491c0b9/` 的第一步实际移动后超时：第五关节请求约 0.20 度，实际约 0.09 度，原直接关节动作要求每个变化超过 0.1 度的关节分别完成 70%，因此即使主要关节到位仍会超时。修复 `r5_policy_backend.py` 的直接关节动作，采用轨迹执行已使用的、相对已提交命令的整体投影进度判定；直接动作仍要求整体进度至少 70%，保留稳定采样、完成残差 2.5 度、反向运动和卡死检查。夹爪完成判定没有改变。新增次要关节死区、卡死和反向运动回归，相关验证为 `65 passed, 7 subtests passed`。

修复后的实机记录：`analysis/return-grip-489170062138/`。

- 完成 17 个返回步骤、5 次预算续段，到达保存姿态的参考容差内并锁定关节。
- 依次执行 `close 0.2`、三次 `close 0.4`、`close 0.2`，共 5 次闭爪；目标从 3.981 降到 2.381，实测从 3.881 降到约 2.302。
- 闭爪期间没有发新的关节目标；最新实测约 `[-3.005, 97.034, 37.015, 50.500, -3.289, -5.563]` 度，原保持命令不变。
- 夹爪电流绝对值上升，最终样本约 0.31--0.32（SDK 原始电流字段，不能直接当夹持力）。接触部位部分遮挡，未确认接触的是球还是支撑物；没有继续加压，也没有抬升验证，不能标记抓取成功。
- 检查结束时 `enabled=true`、`control_state=holding`、`error_codes=[]`，宿主保留保持，无排队的新动作。结果与末次照片见该目录 `result-summary.json`、`final-check-states.json`、`final-external.jpg`、`final-gemini.jpg`。

### 第二次回位与闭爪尝试

上一轮宿主在后续等待时因 `Stationary gripper test: arm drift exceeded limit` 退出，随后检查发现机械臂未使能且已回到初始附近；不能把上一轮末次保持状态当作持续有效。操作者再次要求重试后，启动 `analysis/return-grip-c2a1f3118f79/`。过程中因人员伸手进入腕部区域、以及新增纸箱/高支架靠近路径，分别暂停下发后续步骤，保持宿主运行；操作者要求继续且新画面确认障碍移开后才恢复。

本轮共完成 17 次返回步骤，再次到达保存姿态，锁定时最大参考偏差约 0.74 度。随后执行 `close 0.4`、`close 0.4`、`close 0.2`；夹爪实测从约 3.750 降至 2.796，末次命令为 2.848。最新夹爪电流字段约 -0.690，相比空夹爪保持时约 -0.031 明显增加，但不能据此区分接触网球还是黑色支撑物，也不能推断已抓牢。停止追加闭爪指令，没有抬升，球仍在支撑物上。

末次状态为 `enabled=true`、`control_state=holding`、`error_codes=[]`。本轮结果见 `analysis/return-grip-c2a1f3118f79/result-summary.json`；闭爪前后双图为该目录 `028-*`、`029-*`、`030-*`，末次状态照片 `031-after-top.jpg`、`031-after-left.jpg`。宿主等待下一条命令，无排队动作；后续继续前仍须查询新鲜状态。

## 12. 场景重新布置后的 GPT-Policy 重启准备

约 22:36 操作者表示已换位置并要求重新抓取。只读证据在 `analysis/new-position-check-20260926-223643/`：全局视角改变，出现两台机械臂；当前受控机械臂在全局画面左侧，带白色手腕相机，球在中央黑色支撑物上，已不在受控夹爪之间。此时旧回位/夹爪宿主仍带电保持，不能直接并发启动新宿主。

新增独立配置，保留原文件：

- `r5_tennis_repositioned_policy_context.json`：新场景任务、受控臂辨认、另一台机械臂作为障碍物、黑色支撑物与网球接触区分；保留已验证的开合方向和双视角控制原则，不带历史示范照片。
- `r5_repositioned_cartesian_profile.json`：保留硬件/求解参数，删除 `demonstrated_pregrasp`，替换旧场景方向说明，避免新球位置继续受旧姿态引导。
- 配置检查 `image_grasp` 无阻碍，输入清单解析正常，模型配置为 `gpt-6-astra`；检查没有访问硬件或调用模型。仍是未完成相机标定的实验模式，不能描述为完成标定。

准备的启动命令（截至本记录尚未执行）：

```bash
cd /home/tuojing/arx_r5_control
.venv-policy/bin/python supervised_policy.py \
  --supported-supervision --url http://127.0.0.1:8765 \
  --policy-interface cartesian --camera-mode both --cartesian-stage image_grasp \
  --calibration-profile r5_repositioned_cartesian_profile.json \
  --input-json r5_tennis_repositioned_policy_context.json \
  --open-gripper-to 4.8 --auto-renew-budgets \
  --max-guided-segments 16 --max-decisions 20
```

切换仍需要旧宿主退出，而该操作释放保持、可能回落。场景已重新布置，需要当前机械支撑到位后再切换，重新检查退出后的实际姿态和两路画面。`--open-gripper-to 4.8` 仅在新鲜图像确认空夹爪时使用。此时没有停止旧宿主，没有 SDK 重连/回零，也没有启动新模型推理。

### 断电重启后的实际启动

操作者随后自行重启。旧宿主因反馈中断退出；22:42 检查时虽有 CAN 回包，但旧 SDK 六关节角均无效，存在重复错误码，处于未使能故障状态。关闭旧 SDK worker 并重新连接（初始化可能回零）后恢复：六个有限关节角、`robot_status=ready`、`error_codes=[]`、`rx_age_ms=3`。未重新建立 CAN 通道。证据在 `analysis/environment-restart-20260926-224242/`。

`supervised_policy.py` 新增 `--wait-for-start`：先建立带电保持，持续检查反馈、相机和发送心跳，等待 `start`，收到后才准备张爪并创建模型会话；`stop` 或输入结束退出，仍会释放保持。这样接管保持和开始自主动作可以分开。相关回归 `56 passed, 7 subtests passed`，包含等待时不发动作、start/stop 同时排队时 stop 优先、健康检查失败不开始。

本轮实际启动目录 `analysis/live-policy-f9cbe226c28e/`，使用本节命令并增加 `--wait-for-start`。建立保持后检查新鲜外部画面，确认手已撤离、夹爪为空，再发送 `start`，开始分段张爪至 4.8，随后按新场景的双相机 GPT-Policy 运行。模型配置 `gpt-6-astra`。后续结果应查询该运行的新鲜日志，启动不代表已抓取成功。

启动验证：张爪达到命令 4.8、实测约 4.694；模型前两条较大 `move_to` 被整段轨迹关节范围检查拒绝，未执行。第 2、4、6 步的较小末端目标通过官方 IK 和轨迹检查并实际执行，均结束于保持；首次动作最大关节残差约 0.814 度。此时仍在接近阶段，未闭爪、未确认抓取成功，策略继续运行。

### 模型回复 JSON 异常导致退出及修复

上述运行后续自动续段到第 6 段，22:55:17 因模型决策解析抛出 `JSONDecodeError: Expecting ',' delimiter: line 1 column 426 (char 425)` 而退出，最终目录为 `analysis/live-policy-f9cbe226c28e_failed/`。这次退出不是 CAN 或 IK 故障。清理流程释放了带电保持，机械臂回落到初始附近；本轮没有确认抓取成功。

`supervised_policy.py` 的 `DeadlineAgent.decide()` 现在捕获决策边界的 `json.JSONDecodeError`，重置模型传输会话、再次检查监督状态，再抛出带 `invalid_decision_json` 标记的可重试模型异常。上游循环按原有有限重试机制重新读取图像与状态，不修补坏掉的动作参数、不重放旧动作。真实硬件异常仍直接传播；持续无效回复仍会耗尽重试次数，不能理解为保证永不退出。

新增回归覆盖格式错误后重新观察并仅执行有效动作、持续格式错误耗尽重试且不执行动作、恢复过程中硬件故障不被掩盖。相关五组测试合计 `66 passed, 7 subtests passed`。

恢复前检查见 `analysis/json-recovery-check-20260926-225827/` 和 `analysis/json-recovery-restart-20260926-230209/`：CAN 正常、无错误码、未使能且无 owner，姿态稳定、夹爪为空，双视图中无手。新宿主 `analysis/live-policy-96fb6998ea97/` 使用本节命令加 `--wait-for-start`，从当前姿态建立保持后再开始；没有重放旧保存姿态，也没有 SDK 重连或回零。运行是否仍在执行及是否抓取成功必须检查最新状态和照片。

该次重启在张爪准备阶段因 `Opening step stalled; no retry or force increase` 退出，目录变为 `analysis/live-policy-96fb6998ea97_failed/`，没有调用 GPT。实测夹爪已约 4.690，重新使能的参考约 4.790，到准备目标 4.8 仅差约 0.010；反馈几乎不变，未满足准备步骤的最小进展条件。没有放宽堵转检查或增加开合力度。

随后重新确认空夹爪已张开、两路画面无手，启动 `analysis/live-policy-b97821628382/`：使用本节命令加 `--wait-for-start`，**省去 `--open-gripper-to 4.8`**，直接采用当前已张开的夹爪。保持检查通过后发送 `start`。这只适用于当前已确认张开的空夹爪；闭爪或夹持物体时不能套用该前提。启动前双图在新目录 `pre-start-external.jpg`、`pre-start-gemini.jpg`。

### 命令与实测残差导致的反向运动误判

`b97821628382` 的第 3 步实际执行后报 `Action did not settle`，宿主退出并释放保持，目录变为 `analysis/live-policy-b97821628382_failed/`。末次最大目标残差约 0.302 度，但第三关节旧命令约 0.994 度、动作前实测 1.235 度、新目标 1.103 度、动作后实测 1.213 度：实测在向新目标回调，命令增量却为正，原完成判定错误地认定反向运动。

修复 `visual_control.step_settled()` 的整体进度分支：仅当初始实测已在新目标另一侧，且该关节正在回调、尚未越过目标时，允许这种残差恢复。保留整体投影进度门槛、稳定窗口、最大残差及其他关节的反向检测，没有修改速度或运动限幅。回归使用本次六关节实测数据，并确认完全不动、恢复越过目标及真正反向运动仍被拒绝。六组测试 `88 passed, 19 subtests passed`。

操作者再次要求启动后，使用同一双相机配置、`--wait-for-start` 且省去重复张爪准备，启动 `analysis/live-policy-f989232c1deb/`。保持通过、最新双图确认无手且夹爪为空后发送 `start`。当前启动不代表抓取已成功，须查询新鲜日志。

本轮启动验证：第 0 步较大目标被轨迹包络拒绝；第 1 步较小 `move_to` 已实际执行并正常返回，轨迹规划时长约 1.856 秒，最大关节残差约 0.370 度，`settled=true`。随后进入第 3 次模型决策；此时 `enabled=true`、`control_state=holding`、`error_codes=[]`，夹爪仍张开，尚未确认抓取成功。

## 13. 当晚收工状态（23:21）

操作者关闭电源后曾要求重新使能，随后明确表示今晚结束、明天继续。仅进行了状态和日志检查，**未重新使能、未重连 SDK、未重新启动抓取**。

- 最后一轮最终目录：`analysis/live-policy-f989232c1deb_failed/`。共完成 5 次接近动作，最近一次在 23:15:50；没有确认抓球或抬离支撑物。
- 第 3 段开始后连续出现模型 25 秒决策 deadline 超时，记录到第 6 次重试；因此后半段等待主要发生在模型回复阶段，不能据此断言 API 服务端故障或仅凭猜测提高电机速度。
- 断电后宿主检测反馈过期并退出，最终异常为 `R5ExecutionFault`。末次服务检查：`enabled=false`、`owner=null`、`robot_status=fault`，六关节反馈为 null，CAN 接收已过期，旧 SDK 报电机故障。没有运行中的该轮自主策略，也没有带电保持。
- 明天先检查供电、CAN、新鲜有效关节反馈及双相机当前场景。必要时按第 12 节的断电恢复流程重建 SDK；初始化可能回零，先核对当时环境与路径。不要把今天的姿态、球位置或相机画面当成明天的有效证据。
- 恢复正常后使用新场景配置和 `--wait-for-start` 建立保持，再根据新鲜画面启动。是否使用 `--open-gripper-to 4.8` 取决于当时夹爪状态：当前已张开的空夹爪无需重复张爪；断电初始化后的闭合夹爪不能照搬省略步骤。先观察模型请求能否及时返回，再继续抓取实验。

### 收工后的使能/失能测试请求

操作者随后要求使能后再失能，并确认机械臂在初始位置。证据目录 `analysis/enable-disable-check-20260926-232450/`。双图确认初始附近、空夹爪；CAN 接口为 UP，但旧 SDK 接收持续过期、六关节均为 null。重建 SDK 连接并等待 18 秒后仍没有有效回包，关节仍无效，电机错误码仍存在，因此没有发送 enable、运动目标或抓取指令，没有完成使能测试。随后关闭该故障 SDK 连接，最终状态以目录 `final.json` 为准。恢复前需要确认电机供电及 CAN/USB 链路，不能靠初始位置正常来跳过反馈检查。

### 重新供电后恢复连接成功（当晚最终状态）

操作者明确重新插上电源后再次连接，初次仍无回包。主机检查确认 CANable USB 正常枚举，旧 `can0` 接收计数不增长、发送计数增长。先关闭 SDK worker，再经系统管理员认证，核对旧 `slcand` PID 4050 的完整命令和转接器身份后退出该桥接进程；旧接口消失后运行 `tools/restore_can.sh` 重建通道。没有修改波特率配置或运动限幅。

重新连接 SDK 后恢复正常：`robot_status=ready`、六个有效关节角、`error_codes=[]`、最新 `rx_age_ms=0`、`feedback_age_ms=5`。证据在 `analysis/enable-disable-powered-20260926-232820/`，特别是 `can-restored-connected.json`。SDK 初始化后夹爪原始读数约 0.138，不能继续沿用此前“夹爪已张开”的状态。

操作者随后明确“能连接上机械臂就行”，因此没有执行使能/失能测试，也没有启动抓取推理。最终 SDK 保持连接、worker 运行，`enabled=false`、`owner=null`、`control_state=disabled`。明天先重新检查实时状态与画面；此记录的旧故障状态已被本次成功连接取代。
