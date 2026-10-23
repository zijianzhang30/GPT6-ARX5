# 推黑板擦 — 2026-10-11 第1轮

## 结果

**物理任务与完整流程通过（逐段视觉监督核验）。** 左臂沿桌面将黑板擦推入红色方格，空爪撤离后，两次新观察确认底部支撑轮廓在框内且独立稳定。右臂仅辅助观察和让位，没有接触黑板擦。双臂最终受控回原参考、原2.5°容差两次通过；三路141个MP4正常封口并完成端点验证。

这是本轮目视核验，未取得用户另行成功验收，未测量边界的毫米间隙，不作为固定策略成功率。本轮清场后无人工摆物、扶臂或接管；未观察到双臂碰撞。接口collision_checked=false仍保留，数值规划没有完整已验证的碰撞模型或接触力控。

## 协议、初态与技能

用户目标：“使用左臂把黑板擦推入桌面上的红色方格中，右臂可以自由选择是否辅助观察，注意不要发生碰撞”；要求新增“推黑板擦”skill、实验Markdown及三路视频。用户澄清默认初始位姿为“推异形块的初始位姿”。现存记录对应10月6日推蓝块入红三角原参考，此对应已在准备时说明。原位已满足，无额外初始回位运动；20:33:04、20:33:18两次核验通过。左最大实测/指令1.727°/1.795°，右1.137°/0.943°。

20:34:30记录用户清场确认“已就绪，可开始”。中途用户再次允许另一臂在不干涉前提下辅助观察，已纳入本轮记录。没有要求改成抓取或搬运，全程夹爪开度目标不变、没有闭爪或提起擦体。

新技能[推黑板擦](/home/tuojing/.codex/skills/push-blackboard-eraser/SKILL.md)已在执行前创建，项目镜像同步，显示名“推黑板擦”；结束后补充本轮实际证据。继承共用逐段新图审阅、三路录制、故障与回位核验规则。

复用唯一健康宿主PID2752446、PTY55489、owner dual-policy-acd76c994baa454bb6e13f2323f17676，未重连或重复使能SDK。左右CAN交换映射：左2088335E5931→can0→8765；右208833765931→can1→8766。物理左臂在全局图右侧。

参见[task_prompt.md](task_prompt.md)、[initial_state.json](initial_state.json)、[return_reference.json](return_reference.json)、[reference_provenance.json](reference_provenance.json)。原参考逐字节继承；可执行目标仅将两侧J2置0.8°满足规划余量，最终仍与原参考按2.5°比较；未随renew改写参考。

## 关键阶段（UTC+08:00）

| 阶段 | 后续新观察时间 | 证据与结果 |
| --- | --- | --- |
| 首次运动 | 2026-10-11T20:34:49.784+08:00 | 空爪抬离并接近；初始参考本来已在容差内；[top](control_archive/1791722089753878619_top.jpg) / [left](control_archive/1791722089753878619_left.jpg) / [right](control_archive/1791722089753878619_right.jpg) |
| 首次确认擦体位移 | 2026-10-11T20:41:56.721+08:00 | 侧面接触后擦体实际向目标方向平移；[top](control_archive/1791722516689728290_top.jpg) / [left](control_archive/1791722516689728290_left.jpg) / [right](control_archive/1791722516689728290_right.jpg) |
| 擦体转向约直角 | 2026-10-11T20:44:02.944+08:00 | 推送同时发生转向，不能只平移到目标中心；[top](control_archive/1791722642904638474_top.jpg) / [left](control_archive/1791722642904638474_left.jpg) / [right](control_archive/1791722642904638474_right.jpg) |
| 停止下探并抬开 | 2026-10-11T20:53:52.763+08:00 | 37/38下降响应不足，抬开后残差减小；接触原因未确认；[top](control_archive/1791723232703486871_top.jpg) / [left](control_archive/1791723232703486871_left.jpg) / [right](control_archive/1791723232703486871_right.jpg) |
| 右臂外移让位 | 2026-10-11T21:00:07.632+08:00 | 两段各8° J1外转，左臂期间保持；[top](control_archive/1791723607591900267_top.jpg) / [left](control_archive/1791723607591900267_left.jpg) / [right](control_archive/1791723607591900267_right.jpg) |
| 有效侧推转向 | 2026-10-11T21:06:03.927+08:00 | 长边靠后一端侧推开始产生所需转向；[top](control_archive/1791723963876681275_top.jpg) / [left](control_archive/1791723963876681275_left.jpg) / [right](control_archive/1791723963876681275_right.jpg) |
| 长边基本对齐 | 2026-10-11T21:07:37.915+08:00 | 继续分段侧推转向，擦体保持桌面支撑；[top](control_archive/1791724057870268315_top.jpg) / [left](control_archive/1791724057870268315_left.jpg) / [right](control_archive/1791724057870268315_right.jpg) |
| 前侧左端补推 | 2026-10-11T21:12:08.510+08:00 | 修正偏心接触，底部轮廓目视进入红框；[top](control_archive/1791724328465347425_top.jpg) / [left](control_archive/1791724328465347425_left.jpg) / [right](control_archive/1791724328465347425_right.jpg) |
| 空爪撤离 | 2026-10-11T21:13:28.915+08:00 | 完整全局轮廓露出，擦体未跟随；[top](control_archive/1791724408875452030_top.jpg) / [left](control_archive/1791724408875452030_left.jpg) / [right](control_archive/1791724408875452030_right.jpg) |
| 右臂回位及辅助核验 | 2026-10-11T21:14:19.568+08:00 | 右腕取得完整物体视图；右臂回到原参考附近；[top](control_archive/1791724459520094161_top.jpg) / [left](control_archive/1791724459520094161_left.jpg) / [right](control_archive/1791724459520094161_right.jpg) |
| 左臂回位 | 2026-10-11T21:18:28.997+08:00 | 8段受控回位完成，随后双臂两次核验；[top](control_archive/1791724708964405043_top.jpg) / [left](control_archive/1791724708964405043_left.jpg) / [right](control_archive/1791724708964405043_right.jpg) |

成功核验分别见[verification1](verification1/assessment.json)及[verification2](verification2/assessment.json)，对应新观察21:14:19.520、21:14:43.221，相隔23.701秒；左爪已撤开，擦体未移动。阶段照片与[关键帧索引](keyframes.json)均保留。

## 局部调整与未解决问题

1. 早期推点偏高，空爪移动未带动擦体；改用新的侧面高度依据后，左14首次确认真实位移。后续推送导致擦体转为前后向，不能仅靠目标中心重合判成功。
2. 左37/38下探时J2实测近乎不变、目标残差增大，不能排除桌面接触；停止继续下探，左39抬开后跟随与残差恢复。未触发运行故障，但根因未确认，保留为未解决接触/跟踪现象；不得由到位通过推断接触力安全。
3. 后侧端面推送主要平移，停止沿同一接触重复推。改为长边靠后端侧推，左54–58形成有效转向。最后前侧推点偏右造成反向偏转，撤开并改变姿态/推点后，左68从前侧左端补推完成。
4. 右01/02各向外转8°让位，左臂保持；左爪撤离后，右03/04逐段回位，同时恢复完整目标视角。一次只运动一臂；没有接触式双臂协同。
5. 20:50:10一次在线观察过期拒绝，未执行该请求；刷新并审核后续行。离线IK、关节余量、步长、会话范围/预算拒绝均未下发；录像近期采样非fresh时保持静止并重新检查。没有更改相机、速度、关节余量、到位、跟踪或预算保护。
6. 所有运动段结束时两侧SDK保持健康，无运行故障、保护失能或CAN恢复。TCP模型高度与到位容差不代表夹指物理高度或毫米级定位精度；现场判断使用擦体相对桌纹与红线的位移。全程没有闭爪指令。

## 最终回位

左臂8段、右臂2段回位（右臂两段亦用于辅助最终观察）。核验实测和指令六关节，原容差2.5°：

| 次数 | 时间 | 左最大实测 / 指令误差° | 右最大实测 / 指令误差° | 结果 |
| --- | --- | ---: | ---: | --- |
| 1 | 2026-10-11T21:18:33.787394+08:00 | 1.989 / 1.796 | 0.896 / 0.942 | 通过 |
| 2 | 2026-10-11T21:18:39.698660+08:00 | 1.989 / 1.796 | 0.896 / 0.942 | 通过 |

[final_return_check1.json](final_return_check1.json)、[final_return_check2.json](final_return_check2.json)。两臂ready、enabled、stationary、holding、错误码空、反馈新鲜。工作臂选择为left；左开度目标0.15、右约−0.003675均为空爪。健康保持宿主仍运行，未为收尾停止或失能。宿主startup return_error来自旧任务，不作本轮验收依据。

## 录像、资源和原始证据

- [VIDEO_RECORD.md](VIDEO_RECORD.md)：2026-10-11T20:32:22.926157+08:00 至 2026-10-11T21:18:50.001275+08:00，每路2786.9秒、47段，共141个MP4；元数据及首末帧解码通过。缺采样/重复如实保留。
- [PERFORMANCE.md](PERFORMANCE.md)：冻结总窗口2930.429秒；132条审核命令、83个完成运动段；准备和视觉审核等待单列，不称纯运动时间。
- [DIALOGUE.md](DIALOGUE.md)：公开对话；无内部推理导出。
- [control_archive](control_archive/)：从长期保持宿主事件字节[23228032,31161834)冻结本轮591事件、131次观察、393张图；[archive_manifest.json](control_archive/archive_manifest.json)含来源和SHA256。
- [status.json](status.json)、[RUN_RECORD.md](RUN_RECORD.md)、执行前后技能快照保留。下一轮须重新看实时状态与摆放，不回放本轮坐标。

## 后续90秒视频导出

[90秒三路同屏视频](/home/tuojing/arx_r5_control/exports/blackboard_eraser_push_trial01_20261011_90s/blackboard_eraser_push_trial01_full_3view_90s.mp4)：90.000秒，三路同屏，约30.96倍速，覆盖本次完整录制时段（每路2786.9秒）。全部2700帧解码、三路同采样索引与141个原片覆盖检查通过；原片保留，未剪去等待或局部调整。

[导出说明与验证](/home/tuojing/arx_r5_control/exports/blackboard_eraser_push_trial01_20261011_90s/README.md)。离线导出不计入冻结的实验执行资源统计。
