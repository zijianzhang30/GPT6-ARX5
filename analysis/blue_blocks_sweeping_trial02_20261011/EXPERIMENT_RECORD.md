# 左臂自主拾刷后扫蓝色方块 — 2026-10-11 第2轮

## 结果

**本轮物理任务及完整流程通过（逐段图像监督核验）。** 左臂自主夹取绿色盒旁刷柄，2/2蓝块扫入灰色簸箕并撤刷后稳定；刷子放回绿色盒旁、空爪撤离后独立稳定；左臂五段、右臂两段受控回位，原2.5°容差两次通过。双臂仍由原唯一宿主健康保持。三路93段MP4正常封口，记录已验证。

本结论是一轮监督试验结果；本轮未取得用户另行成功验收，不将其写为用户验收或固定策略成功率。清场后无人工摆放、扶臂或接管；未观察到双臂碰撞。数值接口仍标记collision_checked=false，视觉复核不等同完整自动碰撞检测保证。

## 协议与初态

用户要求先将skill改为“先用左臂夹住放在绿色盒子旁边的刷子的把手，然后其余和原先的保持一致”。两份skill均在执行前更新，旧第1轮人工预置持刷证据保留。场景为绿色盒、靠盒刷子、两个蓝块、灰色簸箕；物理左臂为全局图右侧。

本轮18:08:36用户确认“已摆放完成并退出，可开始”。沿用健康保持宿主PID2752446 / PTY55489 / owner dual-policy-acd76c994baa454bb6e13f2323f17676，无SDK重连或重新使能。当前交换后的CAN：左2088335E5931→can0→8765；右208833765931→can1→8766。参见[task_prompt.md](task_prompt.md)、[initial_state.json](initial_state.json)。

初始/最终回位参考逐字节继承10月6日扫块第1轮[return_reference.json](return_reference.json)；[executable_return_goal.json](executable_return_goal.json)为关节规划余量把两侧J2定为0.8°，仍按原参考和2.5°容差验收，未修改参考或放宽容差。初始两次核验左实测/指令最大1.661°/1.816°，右1.268°/1.180°，见initial_return_check1/2.json。

## 关键阶段（UTC+08:00）

| 里程碑 | 新观察时间 | 证据和结果 |
| --- | --- | --- |
| 初始回位完成 | 2026-10-11T18:08:55.771+08:00 | 随后18:09:00和18:09:14双臂原2.5°核验通过；[top](control_archive/1791713335740834663_top.jpg) / [left](control_archive/1791713335740834663_left.jpg) / [right](control_archive/1791713335740834663_right.jpg) |
| 首次试提未建立跟随 | 2026-10-11T18:15:15.776+08:00 | 开度0.16，15毫米指令试提不计抓取成功；[top](control_archive/1791713715740540875_top.jpg) / [left](control_archive/1791713715740540875_left.jpg) / [right](control_archive/1791713715740540875_right.jpg) |
| 第二次试提 | 2026-10-11T18:15:47.603+08:00 | 开度0.05，18毫米试提看到整刷跟随；[top](control_archive/1791713747569723260_top.jpg) / [left](control_archive/1791713747569723260_left.jpg) / [right](control_archive/1791713747569723260_right.jpg) |
| 自主拾刷复核 | 2026-10-11T18:16:06.813+08:00 | 再抬30毫米，整刷脱离支撑、绿色盒不随动；[top](control_archive/1791713766777797427_top.jpg) / [left](control_archive/1791713766777797427_left.jpg) / [right](control_archive/1791713766777797427_right.jpg) |
| 2/2扫入 | 2026-10-11T18:28:11.361+08:00 | 前角补扫后两个蓝块均进入簸箕；[top](control_archive/1791714491325736005_top.jpg) / [left](control_archive/1791714491325736005_left.jpg) / [right](control_archive/1791714491325736005_right.jpg) |
| 抬刷检查 | 2026-10-11T18:28:34.460+08:00 | 两块仍在簸箕内；[top](control_archive/1791714514414048177_top.jpg) / [left](control_archive/1791714514414048177_left.jpg) / [right](control_archive/1791714514414048177_right.jpg) |
| 撤刷检查 | 2026-10-11T18:28:50.891+08:00 | 两块留在内部、簸箕未见移位；[top](control_archive/1791714530853884904_top.jpg) / [left](control_archive/1791714530853884904_left.jpg) / [right](control_archive/1791714530853884904_right.jpg) |
| 工具释放复核一 | 2026-10-11T18:33:17.871+08:00 | 刷子靠盒支撑，空爪撤开后工具未跟随；[top](control_archive/1791714797829145148_top.jpg) / [left](control_archive/1791714797829145148_left.jpg) / [right](control_archive/1791714797829145148_right.jpg) |
| 工具释放复核二 | 2026-10-11T18:33:45.200+08:00 | 进一步空爪上撤，刷子仍稳定；[top](control_archive/1791714825162693975_top.jpg) / [left](control_archive/1791714825162693975_left.jpg) / [right](control_archive/1791714825162693975_right.jpg) |
| 左臂回位完成 | 2026-10-11T18:35:27.208+08:00 | 五段回位；参考未随renew改写；[top](control_archive/1791714927170527498_top.jpg) / [left](control_archive/1791714927170527498_left.jpg) / [right](control_archive/1791714927170527498_right.jpg) |
| 右臂回位完成 | 2026-10-11T18:36:18.481+08:00 | 两段回位；观察姿态已恢复；[top](control_archive/1791714978450189132_top.jpg) / [left](control_archive/1791714978450189132_left.jpg) / [right](control_archive/1791714978450189132_right.jpg) |

## 局部调整、拒绝与异常

1. 开度0.16的第一次15毫米试提未建立整刷跟随；调整至0.05后18毫米和30毫米试提建立跟随，再横向运输复核。开度是位置，不是夹持力。
2. 早期扫动刷毛高度未建立有效接触，蓝块不动；停止重复该路线，右臂独立抬升、平移和J1转向20°取得观察，左臂期间保持。随后右臂静止，左臂从新观察修正刷头高度和方向。
3. 一块先进入、另一块从入口前角滑出。抬刷绕到外侧后斜向短扫，两块全部进入；未改为右臂接触簸箕。TCP指令高度不代表刷毛物理高度或接触力。
4. 18:10:38一次在线动作前拒绝：Robot changed during Cartesian planning，未执行该目标；新观察后重新规划短目标通过。另有离线会话范围/预算候选拒绝，及录像最近采样非fresh时暂停下发；均未关闭保护或把拒绝写为运行故障。
5. 空爪撤离前逐步打开至0.15；刷子轻微落靠支撑，随后两段撤离和回位观察均稳定。记录为靠盒放置，不称精确平放。
6. 本轮无运行故障、保护失能或人工介入。一次仅移动一臂，保留速度、关节余量、跟踪、相机、到位与预算保护；健康静止时renew续段，原始回位参考不变。

## 最终回位

| 核验 | 时间 | 左最大实测 / 指令误差° | 右最大实测 / 指令误差° | 结果 |
| --- | --- | ---: | ---: | --- |
| 第1次 | 2026-10-11T18:36:21.674105+08:00 | 1.989 / 1.817 | 1.158 / 0.943 | 通过 |
| 第2次 | 2026-10-11T18:36:29.502036+08:00 | 1.989 / 1.817 | 1.158 / 0.943 | 通过 |

详见[final_return_check1.json](final_return_check1.json)、[final_return_check2.json](final_return_check2.json)。两侧ready、enabled、stationary、holding、错误码空，真实反馈新鲜。右臂工作选择保留；左夹爪目标0.15、右约−0.003675均为空爪。宿主startup return_error基于旧任务，不能替代本轮核验。

## 录像、资源和归档

- [VIDEO_RECORD.md](VIDEO_RECORD.md)：2026-10-11T18:06:31.232468+08:00至2026-10-11T18:36:34.654673+08:00，三路各1803.3秒、31段，共93个MP4；首末帧与元数据验证通过。缺采样和重复帧分别保留，非零缺帧。
- [PERFORMANCE.md](PERFORMANCE.md)：冻结总窗口1898.468秒，包含准备、等待及审核，不是纯运动时间。
- [DIALOGUE.md](DIALOGUE.md)：仅公开消息，无内部推理。
- [control_archive](control_archive/)：复用倒珍珠宿主日志的本轮独立片段，原始字节[17074949,23203324)，443事件和288张观察图；[归档清单](control_archive/archive_manifest.json)保存来源和SHA256。
- [keyframes.json](keyframes.json)、[status.json](status.json)、执行前skill快照保留。未关闭健康保持宿主；后续任务必须读新状态，不直接回放本轮坐标。


## 后续90秒视频导出

按用户后续要求，完整三路同屏视频已导出为[90秒MP4](/home/tuojing/arx_r5_control/exports/blue_blocks_sweeping_trial02_20261011_90s/blue_blocks_sweeping_trial02_full_3view_90s.mp4)。约20.04倍速，90.000秒、2700帧、1280×1152，全部成片帧解码及时间映射通过，93个原始片段均有取样覆盖。原速录像保留，倍速抽帧不替代原速证据。导出记录：[blue_blocks_sweeping_trial02_20261011_90s](/home/tuojing/arx_r5_control/exports/blue_blocks_sweeping_trial02_20261011_90s/README.md)。离线导出资源未追加到冻结实验窗口。
