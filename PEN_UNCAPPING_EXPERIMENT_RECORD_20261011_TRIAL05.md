# 总第6项 / L2 — 双臂摘笔帽 — 2026-10-11 第5轮

## 故障后恢复补记（2026-10-11 13:40）

用户完成承托检查并确认清场后，已单独录像并恢复到摘笔帽原始参考。左臂保持在容差内，右臂5段回位；两次间隔5.421936秒核验通过。最大实测误差左0.524559°、右0.721268°；最大指令误差左0.284136°、右0.919647°，均在原2.5°内。当前两臂ready/enabled/holding，空爪；笔带帽留在蓝色盒上。原摘帽任务仍失败，未自动重试。

恢复另存12个三路MP4，已STOP封存、首末帧及帧数核验通过；原45个视频与原失败保留。健康宿主PID2382330/PTY36494继续运行，不关闭；旧宿主1348849已退出。

详见[恢复记录](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/recovery/RUN_RECORD.md)。以下的13:34故障结论保留为当时快照。

## 原任务结果（13:34故障时）

**失败：初始位姿恢复通过，未抓起笔、未摘帽；末段撤离触发到位超时，双臂保护失能，最终受控回位未完成。**

13:34归档时只读快照：两臂SDK为ready、disabled、owner为空、反馈新鲜、错误码为空；不能称当前仍在健康保持，也不能把SDK ready或失能后的姿态变化记为回位。原宿主PID1348849/PTY4208已因R5ExecutionFault退出，未重启或清故障。故障后新图右臂仍伸在桌面，笔带帽留在桌上；用户现场承托检查确认尚待回复。恢复需另行新图与状态检查、重新录像，不自动重试摘帽。

## 协议与初态

- 用户要求：先恢复摘笔帽初始位姿，建立与此前任务一致的Markdown和三路视频，然后执行一轮摘笔帽。
- 本轮真实初态：带帽粗记号笔平放桌面，双臂空爪张开。历史第4轮为人工预置、松帽后的分离；本轮没有人工预置夹持或已确认松帽，另记为桌面自主取笔变体，不能继承旧成功结论。
- CAN已交换：物理左2088335E5931→can0→8765，物理右208833765931→can1→8766。物理左位于全局图右侧，腕相机角色未交换。
- 原始关节参考继承10月3日第4轮（来源第2轮），[pen_uncapping_trial05_20261011/return_reference.json](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/return_reference.json)不可改写。历史右爪持笔开度未复制；两爪全程保持空爪开度，没有闭爪指令。
- 可执行目标单独保存；仅为J2/J3保留原规划余量，并始终以未修改原参考及2.5°容差验证。保留心跳、相机、速度、跟踪、到位、关节与预算保护。

## 过程与里程碑

| 阶段 | 上海时间 | 结果 |
| --- | --- | --- |
| 用户任务边界 | 2026-10-11T13:19:09.511000+08:00 | 冻结prompt、保存初态、读取skill与历史记录 |
| 开始三路MP4 | 13:20:01.979 | 10fps、60秒分段；PID1855759 |
| 清场复核 | 首次动作前 | 最初左腕图有人手，用户回复“已退出，可继续”后，重新审图并执行 |
| 初始位姿恢复 | 13:25:33—13:27:48 | 先左5段、后右5段，一次一臂，空爪 |
| 两次原位核验 | 13:27:48 / 13:27:55 | 间隔7.039824秒；实测最大误差左1.8141°、右1.1147°；指令左1.6196°、右0.9202°，均小于2.5° |
| 桌面取笔接近 | 13:28:04起 | 右臂抬离底座，逐段接近；左臂保持初位 |
| 姿态调整 | 13:30—13:33 | 抬开后逐段改为上方夹取姿态，没有闭爪或抓起证据 |
| 首段录像退出 | 13:30:19.913 | SIGTERM，来源未知；运动前PID检查拦下08候选，未发送 |
| 三路续录 | 13:30:28.507 | PID2223269，缺口8.594196秒，无新运动下发 |
| 笔被碰动 | 13:33:30.820 | 18接近后，全局图笔向前移、印字方向变化；记录为夹指接触推移，未形成夹持 |
| 抬高撤离19 | 13:33:38—13:33:47 | 名义上抬35mm，原到位保护超时，宿主退出并导致双臂失能 |
| 录像停止封存 | 13:34:06.397 | 续录STOP正常退出0；所有45个MP4首末帧验证通过 |

28条运动请求获得到位结果，其中10条初位恢复、18条取笔接近/姿态调整；1条运动预算拒绝、1条末段运动运行失败，共30条请求。离线IK/单步范围失败没有下发，另外保留；空爪且健康静止时进行了11次原续段操作。未执行夹爪闭合、轴向拉拔或共同持笔。图像中没有观察到双臂相互碰撞；系统没有经过物理验证的完整碰撞检测器，数值到位不代表碰撞验证。

## 故障复核

末段完整反馈包含68条样本。所有样本command_ok和grip_ok为真，arm_ok为假。最终目标残差最大0.831948°，整体投影进展89.288%，但J2指令变化−1.516024°，实测相对动作前变化+0.305992°，超过原0.3°反向容许量；该项使原到位条件持续未通过，5秒settle超时。这解释本次软件保护触发条件，不能由此推断电机完全不动、CAN中断、整机新硬件故障或任务物理不可能。未修改阈值，未重放失败轨迹。

接近18已碰动笔，不能掩盖这次接触；随后撤离虽有明显关节运动，也不能把它记为通过到位或成功撤离。保护失能后右臂J2等姿态发生变化，不能算受控回位。详见[故障数值](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/FAULT_DIAGNOSIS.json)、[完整原反馈](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/fault_execution_feedback.json)、[故障后状态](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/fault_state.json)、[故障全局图](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/fault_top.jpg)。

## 三路录像

共45个MP4，3路分别为全局/dev/video2、左腕/dev/video20、右腕/dev/video10，全部使用既有HTTP图像流；未另开相机设备。

| 目录 | 起止 | 每路帧数 | 文件数 | 结束方式 |
| --- | --- | --- | --- | --- |
| [recording](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/recording) | 13:20:01.979—13:30:19.913 | 6178 | 33 | SIGTERM，来源未知 |
| [recording_continuation01](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/recording_continuation01) | 13:30:28.507—13:34:06.397 | 2177 | 12 | stop_file，退出0 |

8.594196秒缺口期间没有下发运动；缺帧和重复帧统计原样保留，不能称全程连续、零缺帧或硬件曝光同步。所有MP4首末帧可解码、各路帧数总和与manifest相符；未逐帧解码全部原片。见[验证结果](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/video_verification.json)。

## 时间与资源

执行记录窗口896.885515秒，包含准备、清场等待、运动、审图与故障收尾。48条宿主命令（含observe/select/renew）处理198.540979秒；命令间等待627.954671秒，已排除第一条跨任务空闲。等待不能计为纯模型推理时间。

75个去重response：输入8,700,268 tokens（缓存8,514,432，非缓存185,836）；输出28,973（其中推理输出10,203）；合计8,729,241。缓存包含在输入中，推理输出包含在输出中。基于本地日志，非账单；服务端纯推理耗时未知。执行窗口冻结在录像停止时，后续归档或恢复不混入。

## 证据与下一步

[冻结prompt](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/task_prompt.md) · [初位核验](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/initial_pose_verification.json) · [状态](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/status.json) · [原始事件](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/events.jsonl) · [资源](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/PERFORMANCE_USAGE.json) · [公开对话](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/DIALOGUE.md)

原控制日志位于analysis/hat_hanging_trial11_20261011/recovery/control，按本轮control_boundary.json与control_final_boundary.json冻结事件片段，138张观察图片复制到review/。当前不保留任何自动待执行目标。按skill已请求故障后承托、线缆/笔未卡住、人员退出及可立即急停的确认，收到后只能依据新状态排查与恢复；不会直接续发19或再尝试摘帽。
