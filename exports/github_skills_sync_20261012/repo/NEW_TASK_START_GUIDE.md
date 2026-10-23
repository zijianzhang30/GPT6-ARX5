# 新对话与新任务启动指南：ARX R5 双臂桌面实验

整理日期：2026-10-05。项目目录：`/home/tuojing/arx_r5_control`。

这份文档用于在新的对话中接续已有实验方法，或启动下一项桌面任务。**先读取文件、核对现场和服务，再启动一轮任务。** 仅要求整理文档、分析录像时，不启动录像或机械臂。

## 1. 用户在新对话里怎么说

打开能够访问本机项目目录、终端和图像的新对话，复制下面内容，填写任务与真实现场状态即可。不需要粘贴之前整段聊天。

```text
请先读取：
/home/tuojing/arx_r5_control/NEW_TASK_START_GUIDE.md
/home/tuojing/arx_r5_control/PROJECT_HANDOVER.md 的最新条目
/home/tuojing/.codex/skills/arx-r5-tabletop-tasks/SKILL.md

使用 $arx-r5-tabletop-tasks，沿用之前桌面实验的流程，执行下面一轮任务：

任务名称：填写名称
目标物体和初态：填写物体、原支撑，以及是否已预置在夹爪中
具体目标：填写从哪里到哪里、动作、距离/高度、最终放置状态
主操作臂：左臂；右臂可辅助观察（需要双臂操作时明确分工）
完成判据：填写什么实际现象算完成，是否允许残留、倾斜等
任务分类：未指定（需要时由我明确指定L1或L2）
当前现场状态：填写“已摆好并清场，可以执行”或“尚未清场，先只读检查”

先核对当前连接、三路新图和唯一控制宿主。健康保持时优先复用；
需要重连或冷启动时按现有手册检查，不照抄历史PID、owner和坐标。
在首次硬件动作前开启本轮独立的全局、左腕、右腕MP4，并持续核验录像。
自主用三路画面判断抓点、深度、路径和结果；必要时移动空的观察臂。
已有效确认的条件不要反复询问；新的人或工具进入、人工调整、
或确实无法通过传感器知道的必要条件，再简短核实。
保留全部原有保护，分段执行。失败先检查新证据，不无限重复同一接触。
记录实验MD、公开对话、原始动作与反馈、token用量及可取得的耗时。
正常结束后核验物体独立稳定，两臂按本轮保存的初始参考受控回位，
停止并验证三路录像，合成上排双腕、下排全局的同屏MP4。
补充本任务skill经验，分别报告任务结果、回位结果和所有保存路径。
```

现场尚未清场时如实填写，不把上一轮的清场确认当作下一轮已完成。目标涉及插座等特殊物体时，还应提供不能由图像确认的必要状态，例如是否已与市电断开。

只想先准备、不运动，可把“执行下面一轮任务”改成：“先做只读检查和方案准备，暂不使能、重连或发送运动目标。”

## 2. 之前的实验是怎样执行的

采用“取得新图和反馈 → 判断几何与接触 → 离线规划一小段 → 由监督宿主执行 → 停稳后看新图”的循环。任务skill保存流程和经验；启动宿主后显示 `HOLDING` 只说明已建立保持，任务还需要逐步决策与下发。

机械臂通常一次只动一侧，另一侧保持。右臂辅助观察也要检查连杆、相机和线缆的整个运动通道。抓取靠试提证明，放置靠松爪、撤离后的独立稳定证明，回位靠本轮固定参考和真实关节反馈证明。关节到位或图像投影重叠，均不能单独证明任务成功。

截至整理日期，已有以下10项记录。前5项由用户定义为L1，第6项为L2，其余未指定分类；分类不代表成功。

| 序号 | 任务与记录 | 实际可复用的结论 |
| --- | --- | --- |
| 1 | [叠杯](CUP_STACKING_EXPERIMENT_RECORD_20261001.md) | 有左臂放杯/回位、右臂套叠/回位的完整监督案例 |
| 2 | [插笔](PEN_INSERTION_EXPERIMENT_RECORD_20261002.md) | 粗笔放入宽口杯有成功案例；不等同细笔插小孔 |
| 3 | [插座](CHARGER_INSERTION_EXPERIMENT_RECORD_20261001.md) | 抓取、运输和失败收尾有证据；插入未验证成功 |
| 4 | [插花](FLOWER_INSERTION_EXPERIMENT_RECORD_20261003.md) | 人工预置持花后放入纸杯、回位完成；自主取花和窄口瓶方案未完成 |
| 5 | [挂帽子](HAT_HANGING_EXPERIMENT_RECORD_20261003.md) | 有夹持/运输及释放经验，尚未独立挂稳 |
| 6 | [双臂拔笔帽](PEN_UNCAPPING_EXPERIMENT_RECORD_20261003.md) | 人工预置、松帽和调整后分离成功，双臂回位通过；不是原紧帽全自主完成 |
| 7 | [倒珍珠](PEARL_POURING_EXPERIMENT_RECORD_20261005.md) | 用户验收成功，允许残留；有洒落，接收数量未独立核验 |
| 8 | [橘瓣抓放](ORANGE_PICK_PLACE_EXPERIMENT_RECORD_20261005.md) | 第4次局部抓取成功，抬升约9厘米、放回及回位通过；对象为剥皮单瓣 |
| 9 | [抽屉拉推](DRAWER_PUSH_PULL_EXPERIMENT_RECORD_20261005.md) | 两轮均未抓稳、无5厘米拉推；第1轮故障落桌，第2轮受控回位通过 |
| 10 | [果冻抓放](JELLY_PICK_PLACE_EXPERIMENT_RECORD_20261005.md) | 两次空提，局部修正后仍未抓稳；物体留在支撑，双臂受控回位通过 |

新任务只选相近任务参考，重新判断现场。历史坐标、开度、PID、设备节点和命令文件均不能直接重播。

## 3. 新对话先读哪些文件

1. 本文：整体启动路径与交接注意事项。
2. [PROJECT_HANDOVER.md](PROJECT_HANDOVER.md)：最新带时间的现场快照与活动宿主线索。
3. [任务skill](/home/tuojing/.codex/skills/arx-r5-tabletop-tasks/SKILL.md)及其[共用流程](/home/tuojing/.codex/skills/arx-r5-tabletop-tasks/references/common-execution.md)，再选本次相关任务参考。
4. 需要连接/恢复时读[初始化手册](MACHINE_INITIALIZATION_RUNBOOK.md)；录像读[三路录像说明](THREE_CAMERA_RECORDING.md)；收尾读[受检回位说明](REVIEWED_RETURN.md)和[记录要求](/home/tuojing/.codex/skills/arx-r5-tabletop-tasks/references/records-and-evidence.md)。

L1任务现成提示词见[L1_TASK_PROMPTS.md](L1_TASK_PROMPTS.md)，拔笔帽见[L2_TASK_PROMPTS.md](L2_TASK_PROMPTS.md)。新任务可以使用第1节通用模板。

**截至2026-10-05 13:10的最后已知状态：**果冻第1轮已结束，双臂受控回位，三路录像和同屏视频已归档，健康保持宿主被保留。宿主线索在总交接文档；果冻命令109–206已单独冻结。本文整理时未重新检查实机，因此这不是下一轮可直接执行的状态保证。

## 4. 最重要的分支：沿用保持，还是冷启动

| 新检查结果 | 下一步 |
| --- | --- |
| 两臂健康、静止、enabled/holding，存在有效owner和唯一宿主 | 检查宿主、日志与输入通道是否匹配，沿用健康保持；不重复使能或另起竞争控制端 |
| 两臂ready、disabled、无owner，有新鲜反馈，且没有旧控制宿主 | 三路录像先准备好，再从idle建立唯一监督宿主 |
| 服务、CAN或SDK连接缺失 | 按初始化手册逐层恢复，先确认身份与实际反馈；重连可能初始化/回零 |
| SDK错误、无CAN回包、监督故障锁存或未知接触 | 保存故障与现场证据，定位问题；不能把重开对话当成清故障或重播理由 |

初始化手册中“关闭旧宿主”等步骤适用于经过检查的冷启动条件，**不应用于仍在健康保持的机械臂**。同样，README中的早期“结束前断开”说明不能代替当前任务的受控收尾流程。

### 新对话与旧终端的关系

- 本机PID、日志文件和FIFO是系统对象；对话工具返回的终端会话编号不保证在新对话中仍可使用。不要仅凭旧编号发送命令。
- 若已有有效FIFO输入通道，核验当前PID、打开的输入、owner、活动日志目录和末条完成事件后，才复用该通道。倒珍珠曾使用 `commands.fifo`；这不是每个宿主自动具备的接口。
- 若旧宿主只接收原PTY输入，而新对话没有该PTY访问能力，保留旧宿主，先核对受检交接入口是否适用。不要通过杀进程、重复启动或往旧设备文件盲写来接管。
- 当前 `--from-review-pid` 适用于特定顺序任务交接；`--from-initial-review-pid` 仅适用于未接收过任务命令、stdin为`/dev/null`的初始宿主；其他恢复入口也各有条件。它们不是通用“接管任意健康宿主”开关。
- 在新对话确认可用输入通道前保留原控制终端。下一次真正冷启动时可评估采用已验证的持久FIFO方式，但本指南没有为现有PTY宿主新增热切换功能。

## 5. 只读预检：每轮都做

以下命令用于读取，不会使能、回零或提交目标。

```bash
cd /home/tuojing/arx_r5_control
ps -eo pid,ppid,etime,stat,args | rg 'app.py|record_workbench.py|robot_worker.py|held_policy_review.py|single_policy_review.py|record_three_cameras.py'
ls -l /dev/serial/by-id/
ip -details -statistics link show can0
ip -details -statistics link show can1
```

连续读取状态和相机元数据，检查接收计数、相机序号是否推进：

```bash
.venv-policy/bin/python - <<'PY'
import json
import time
from visual_control import ArmWorkbenchClient, WorkbenchClient

c = WorkbenchClient('http://127.0.0.1:8768')
for sample in range(2):
    for side in ('left', 'right'):
        s = ArmWorkbenchClient(c.base, side).state()
        keys = ('channel', 'robot_status', 'enabled', 'moving', 'control_state',
                'owner', 'worker_fault_reason', 'error_codes', 'rx_age_ms',
                'feedback_age_ms', 'rx_count', 'joints_deg', 'command_deg',
                'gripper_raw', 'gripper_command_raw')
        print(sample, side, json.dumps({k: s.get(k) for k in keys}, ensure_ascii=False))
    for key in ('external', 'gemini', 'gemini_right'):
        data, seq, device = c.camera(key)
        print(sample, key, 'sequence=', seq, 'device=', device, 'bytes=', len(data))
    if sample == 0:
        time.sleep(0.5)
PY
```

这只是初筛，还需打开三路新图审阅现场，并检查宿主的实时监督状态。任一读取报错应先定位，不能把部分输出当全部通过。

本机常用映射如下，设备重插后需重新核实身份：

| 对象 | 入口/通道 | 图像键 |
| --- | --- | --- |
| 物理左臂，历史全局画面右侧 | 8765 / can0 | gemini → left |
| 物理右臂，历史全局画面左侧 | 8766 / can1 | gemini_right → right |
| 双臂代理与网页 | http://127.0.0.1:8768 | external → top（全局） |

`can0 UP`和适配器在线不等于电机回包正常。两臂需要有效六关节值、新鲜反馈、RX持续增长与空错误码；左右基坐标独立，图像左右也不等于基坐标正负。

## 6. 本轮目录、录像和控制入口

### 6.1 建立唯一试次目录

由执行agent为本轮确定任务名和试次号，例如：

```bash
cd /home/tuojing/arx_r5_control
R5_TASK_DIR="analysis/new_task_trial01_$(date +%Y%m%d_%H%M%S)"
mkdir "$R5_TASK_DIR"
```

将实际目录记入本轮MD；其他终端使用**同一个实际目录值**，不要各自重新生成时间戳。保存任务prompt、初始状态及不可变的`return_reference.json`。保存前说明“最初位置”来自本轮还是明确继承的旧参考；`renew`或交接不得覆盖它。

### 6.2 先启动三路MP4

在独立可追踪终端运行；运行中的旧录像先核对所属任务，不能盲停：

```bash
.venv-policy/bin/python -u tools/record_three_cameras.py \
  --base http://127.0.0.1:8768 \
  --output "$R5_TASK_DIR/recording" --format mp4
```

脚本默认格式可能是AVI，因此显式写`--format mp4`。默认10fps、60秒分段。确认manifest为`recording`、进程及心跳有效、三路设备不同、各路`fresh_frames`连续增长且无新增请求错误。每次硬件操作前持续核验；录像不能替代控制侧新鲜图像检查。

### 6.3 已有健康宿主：直接走接续分支

确认可用输入通道后，使用当前宿主取得新观察，保存新任务初态和日志起点。记录`active_host_review`与本轮独立归档目录，避免把复制来的旧图片当实时画面。先核对上条命令已终结、两臂健康静止，再按新目标规划。**不要执行下一节的idle启动命令。**

### 6.4 已连接且双臂idle：建立监督宿主

仅在第4节idle条件、清场和三路录像检查通过后使用。先从当前代理读取owner，不能填旧聊天中的值：

```bash
R5_TASK_OWNER="$(
  .venv-policy/bin/python -c 'from visual_control import WorkbenchClient; import re; p=WorkbenchClient("http://127.0.0.1:8768").request("/api/arms")["paired_policy_client"]; assert re.fullmatch(r"dual-policy-[a-f0-9]{32}", p or ""); print(p)'
)"

.venv-policy/bin/python -u tools/start_idle_review.py \
  --url http://127.0.0.1:8768 \
  --working-arm left \
  --paired-client "$R5_TASK_OWNER" \
  --tracking-reserve-deg 3.5 \
  --minimum-cartesian-command-step-deg 2 \
  --output "$R5_TASK_DIR/review"
```

这是沿用近期试次设置的模板；若当前配置更严格，保留更严格值。启动器检查双臂idle、预热相机，再进入`held_policy_review.py --prepare-idle`建立保持，属于会改变硬件状态的步骤。右臂需要辅助观察时使用双臂宿主的`--working-arm left`；`--arm left`是另一种单臂模式，不能混用。

用真实持续终端/PTY运行宿主，保留其stdin。不要用执行到结尾就消失的heredoc、`/dev/null`或不可追踪的后台命令启动它；heredoc只适合上面的只读查询。建立保持后先发`observe`，核对图像、状态及日志确实响应，然后才规划抓取。

### 6.5 服务或SDK尚未启动

仅对缺失服务操作，不复制整套覆盖仍健康的实例。完整恢复条件见[初始化手册](MACHINE_INITIALIZATION_RUNBOOK.md)。常用服务命令如下，各自占用持续终端：

```bash
# 左服务：确认8765未被有效服务占用
./start.sh --live --no-browser --supervised-policy \
  --port 8765 --can can0 --wrist-serial CV2C8610015R

# 右服务：确认8766未被有效服务占用
./start.sh --live --no-browser --supervised-policy \
  --port 8766 --can can1 --wrist-serial CV2C86100180

# 双臂代理：仅在没有有效8768代理时生成新的成对owner
R5_PROXY_OWNER="$(python3 -c 'import uuid; print("dual-policy-" + uuid.uuid4().hex)')"
.venv-policy/bin/python record_workbench.py \
  --upstream http://127.0.0.1:8765 \
  --right-upstream http://127.0.0.1:8766 \
  --port 8768 --paired-policy-client "$R5_PROXY_OWNER"
```

先确保相机路由与录像可用，再在清场条件下通过上游8765/8766逐侧连接SDK；每侧等待ready及有效反馈后再进行下一侧。`connect`可能包含初始化/回零，不是只读；8768成对owner不用于底层初始化。如果道具占用回零通道，应先完成初始化再摆放，摆放后重新确认清场。之后返回第5节检查，再执行6.4。

CAN故障分开处理：`can0`缺失时按条件使用`tools/restore_can.sh`；已有失效桥时先阅读`tools/rebuild_left_can_bridge.py`并运行其`--check`。只有满足脚本前置条件才重建；需要本机sudo认证时由用户在本机完成，不收集或记录密码。`can0 already exists`不能靠反复运行restore解决。

## 7. 任务执行、暂停和回位

每次只处理一条经过审阅的有界动作：

1. 确认录像、唯一宿主、反馈和三路新图；检查任务物体、支撑、人、工具、连杆和线缆。
2. 选择当前工作臂；离线规划，检查当前预算、指令残差和原限制。预览不是碰撞检测认证。
3. 在观察有效期内发送一条命令，等待对应`command_index`的`review_command_finished`，核对outcome。
4. 查看动作后的新图和真实物体响应，再决定下一步。命令超时但结果未知时先查事件和反馈，禁止盲目重发。

`observe`取新图，`select-left/right`切换后续工作臂。`renew`仅用于符合条件的健康静止续段，它会重锚预算/指令参考；随后重新规划。`open-empty-left/right`只能在已确认空爪或物体独立支撑、释放路径明确时使用，不能对未知持物状态直接全开。工具JSON需按当前schema提供完整字段，包括`note`；不提供可复制的旧运动JSON。

同一抓点连续两次试提失败后停止重复闭爪/提升，换视角检查深度和支撑；取得新的可行证据才局部重试。这不代表“两次失败就认定任务永远做不了”。遇到监督故障、未知接触或无新证据时，保存实际结果并说明阻碍。

正常收尾：让物体获得独立支撑 → 分步释放 → 空爪撤离 → 两次相隔数秒的新观察核验稳定 → 两臂分别沿可见路径回本轮参考 → 核对实测和指令误差、静止及反馈。原回位容差为2.5°，不能为了通过而修改参考或放宽容差。

`reviewed-return-step`绑定的是**宿主初始参考**。跨任务沿用宿主时必须比较其参考与本轮`return_reference.json`；不同就按本轮参考另行受检规划，不把旧入口返回“完成”当作新任务回位完成。健康保持宿主不能为了停录像、换对话或整理文件而直接退出；失能、断电和重力回落均不算受控回位。

## 8. 停录像、保存MD、合成视频

完成任务收尾后，在另一个终端指定本轮实际目录：

```bash
touch "$R5_TASK_DIR/recording/STOP"
```

等待录像进程正常结束、manifest=`completed`，检查三路片段数量、帧数和首末帧可解码。停止录像与退出控制宿主是两件事。若用户提前要求停录像，按要求停止，并明确此后是否存在未录制动作。

建议的本轮档案内容：

```text
analysis/<任务_试次_时间>/
  task_prompt.md               # 本轮协议、初态、目标和分工
  initial_state.json
  return_reference.json         # 固定参考，不随renew重写
  status.json                   # 活动宿主/日志线索、命令边界与结果
  review/                       # 本轮事件、反馈、逐阶段三路新图
  recording/                    # 三路MP4、manifest、逐帧元数据、验证报告
  final_check_1.json
  final_check_2.json
  return_verification.json
  RUN_RECORD.md
  DIALOGUE.md                   # 公开对话，保留当时判断及更正
  metrics_baseline.json
  metrics_end.json
  PERFORMANCE.md
  PERFORMANCE_USAGE.json
  response_usage.jsonl
  client_item_timings.jsonl
  combined_video/               # 同屏MP4、源帧映射、验证报告、VIDEO.md
```

若沿用旧宿主，结束时按本轮起止命令编号冻结事件与图片，并写明原日志位置；不能把旧任务全部事件复制后当新任务。完整MD和公开对话在结束后集中整理，控制过程中只记必要检查点。对话记录不包含内部推理正文；保留公开判断、动作依据、传感器证据和可取得的用量元数据。

资源记录从启动时就设边界：找到**当前对话**的实际日志，保存起始时间/累计快照，结束后按response ID去重统计。缓存输入包含在输入中，reasoning输出计数包含在输出中；模型服务端纯推理时间、TTFT或费用没有数据就留空。区分命令处理、抓图、观察/工具等待，不能把全部等待称为GPT推理。

同屏采用上排左腕/右腕、下排全局；三路按共同源采样帧索引对齐，保留duplicate/missing状态。连续版保留等待；若另剪核心片段，动作原速并保存输出到源帧的映射。逐帧解码验证成片，记录录像中断和续录缺口。

可参考[果冻完整档案](analysis/jelly_pick_place_trial01_20261005/RUN_RECORD.md)、[资源记录](analysis/jelly_pick_place_trial01_20261005/PERFORMANCE.md)、[同屏说明](analysis/jelly_pick_place_trial01_20261005/combined_video/VIDEO.md)及[倒珍珠档案](analysis/pearl_pouring_trial01_20261005/RUN_RECORD.md)。其中`plan_step.py`、`watch_review.py`、`send_review.py`、`collect_metrics.py`、`render_full_video.py`是**试次脚本范例**：路径、宿主、日志、阶段编号和会话来源可能写死，必须检查并适配后才使用，尤其不能直接运行旧发送脚本。

最终补充相应任务skill和实验总记录，更新`PROJECT_HANDOVER.md`的最新带时间条目，并向用户给出：实际完成了什么、未完成什么、双臂回位结果、录像/同屏/MD/耗时文件路径。

## 9. 下次切换对话前的交接清单

- 本轮是否已经结束，是否仍持物；两臂是否真正受控回位。
- 哪个宿主还在保持，活动日志和输入通道是什么；哪些目录只是冻结档案。
- 最后一条已完成命令编号、待处理命令是否为空、有没有故障锁存。
- 录像是在录还是已停止；是否存在缺口；源片和同屏视频在哪里。
- 下一轮目标与现场状态要重新填写；新对话先读文件和实时状态，再确定启动分支。

本文提供操作与交接方法；执行命令前仍以当前源码、现有保护和新鲜实机证据为准。
