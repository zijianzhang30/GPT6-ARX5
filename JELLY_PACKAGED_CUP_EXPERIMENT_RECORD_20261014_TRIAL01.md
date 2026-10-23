# 包装果冻杯抓放 · 2026-10-14 第1轮

## 结果

**本轮失败：六次小幅试提均未确认果冻杯离开盒面，未完成5–20厘米抬升和随后放回。** 松爪撤离后物体留在绿色盒面，独立支撑复核通过；左臂分七段返回本轮HOME参考，右臂一直保持原位，两臂最终回位原2.5°容差两次通过。三路录像正常停止并封存。

未观察到本轮双臂碰撞、SDK故障或保护失能。全程复用健康保持宿主，未重新连接SDK或CAN。控制器没有已验证的完整碰撞模型或接触力传感，这一结论限于观察与日志。

## 当前prompt与初态

> Pick up the packaged jelly cup from the green box with the left arm, lift it 5–20 cm, then place it back and release it

用户要求严格按当前prompt并录三路视频、保存Markdown。左臂抓取，右臂原位观察。目标为倒置在青绿色盒面、含黄色果肉的透明杯状物；按用户的包装果冻杯对象执行，未开包装。未独立测定包装材质或密封性，不把视觉外观当作材料/夹持力测试。旧橘子/软果冻任务只用于通用操作和记录流程，没有重放旧坐标、开度或初始姿态。

从实时健康HOME起步，冻结当前六关节保持目标为[return_reference.json](analysis/jelly_packaged_cup_trial01_20261014/return_reference.json)，保存实际初态和来源。不是把宿主早先启动时的人工折叠姿态当作本轮HOME。初始两次核验在13:23:40/43通过。用户本次确认：“已摆放完成并退出，可开始”。确认后未观察到人工摆物或人员进入双臂运动范围；远处背景人员不记为工作区侵入。

固定身份：物理左臂5E5931→can0→8765（全局画面右侧），物理右臂765931→can1→8766（全局左侧）。唯一宿主PID1700471 / PTY39351，owner为dual-policy-acd76c994baa454bb6e13f2323f17676；宿主目录仍为上一轮recovery_control，但本轮事件单独归档。

## 实验过程

| 阶段 | 动作与观察 |
| --- | --- |
| 13:23:39–13:24:07 | 三路录像启动、初始HOME两次核验；选择左臂并健康续段，首次物理动作抬开空爪 |
| 左01–11 | 分段接近盒面，校正横向方向与朝下角度，首次闭爪至0.86；检查整臂、相机和盒沿间隙 |
| 左12–16 | 第1次15 mm试提未离面，降回接触位，分步收至0.70；第2次仍失败，停止该点重复 |
| 左17–27 | 松开并撤离，确认空爪后张开；前移抓点至杯身中部，第3次开度0.80试提失败；降低接触点、收至0.64，第4次仍未离面 |
| 左28–40 | 分步松开、退离并调整空爪角度，再从更低杯身位置接近；第5次0.62、第6次0.50均未验证离面，停止抓取尝试 |
| 左41–45 | 有支撑条件下逐步松开、撤离，确认空爪后张开；物体仍在原盒面，13:38:07/10独立支撑两次复核 |
| 左46–52 | 左臂分七段沿已观察通道回本轮HOME；健康续段时保持原参考不变，右臂未下发移动 |
| 13:40:43/46 | 双臂回位两次通过，最大实测误差左1.102°、右0.380°；最大指令误差左0.00366°、右0° |
| 13:40:49 | 三路STOP封口，进程退出0，54段验证通过；健康控制宿主继续保持 |

### 六次试提

| 次数 | 开始时间（+08:00） | 开度位置 | 指令上升 | 反馈TCP净上升 | 物体结果 |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | 13:28:19 | 0.86 | 15 mm | 11.86 mm | 未验证离面 |
| 2 | 13:29:44 | 0.70 | 15 mm | 10.05 mm | 未验证离面 |
| 3 | 13:31:37 | 0.80 | 10 mm | 12.38 mm | 未验证离面 |
| 4 | 13:33:06 | 0.64 | 15 mm | 11.95 mm | 未验证离面 |
| 5 | 13:35:52 | 0.62 | 20 mm | 12.58 mm | 未验证离面 |
| 6 | 13:36:31 | 0.50 | 20 mm | 12.85 mm | 未验证离面 |

数值仅为每次试提前后同口径反馈FK的TCP高度差，含跟踪残差和未标定工具偏置影响，不是果冻杯高度。相机中物体持续受盒面支撑并相对夹指滑移；局部有形状/朝向变化，不能称完全未扰动。没有明显整体倾倒或掉下盒面，但未检测密封或内部损伤。开度0.50等是本轮位置目标，不是力度值，也不是以后固定参数。

## 检查、拒绝与限制

保持原相机新鲜度、30秒观察有效期、心跳、速度、关节边界、到位及预算保护；离线轨迹另留3.5°跟踪/会话余量。每段取图和依赖该图的动作分开调用。六次试提按三个接触布局进行，每点最多两次，之后依据新视角重新判断或结束。右臂全程原位观察，没有以观察为由靠近工作臂。

本轮53条JSON命令均有正常result（{'move_to': 34, 'set_gripper': 19}），正常控制返回不等于抓取成功；另4次已确认空爪的张开准备。未发生运行故障或实时命令拒绝。离线曾遇到候选平移长度/关节包络/预算不满足而缩短候选；一次辅助模块缺失在动作前补齐；几次提前规划读到尚未完成的动作状态，断言拒绝后等待到位再规划。left13_deepen_cup_contact.json仅为未下发候选，不算实际动作。录制门禁遇到非连续新帧时暂缓，复检通过再动，没有放宽阈值。

## 证据

- [三路MP4目录](analysis/jelly_packaged_cup_trial01_20261014/recording) · [录像说明](analysis/jelly_packaged_cup_trial01_20261014/VIDEO_RECORD.md) · [验证结果](analysis/jelly_packaged_cup_trial01_20261014/recording/validation.json)
- [试提前后数值及图片索引](analysis/jelly_packaged_cup_trial01_20261014/lift_evidence.json) · [逐条动作](analysis/jelly_packaged_cup_trial01_20261014/ACTIONS.md) · [结构化动作记录](analysis/jelly_packaged_cup_trial01_20261014/action_summary.json)
- [松爪后支撑复核1](analysis/jelly_packaged_cup_trial01_20261014/support_verified_1) · [支撑复核2](analysis/jelly_packaged_cup_trial01_20261014/support_verified_2) · [最终状态与三视角](analysis/jelly_packaged_cup_trial01_20261014/final_state)
- [初始HOME核验](analysis/jelly_packaged_cup_trial01_20261014/initial_home_verified.json) · [最终HOME核验](analysis/jelly_packaged_cup_trial01_20261014/final_home_verified.json) · [固定返回参考](analysis/jelly_packaged_cup_trial01_20261014/return_reference.json)
- [本轮控制事件及204张观察图](analysis/jelly_packaged_cup_trial01_20261014/control_archive)：字节1784637–7519388，不混入上轮瓶盖回位
- [公开对话](analysis/jelly_packaged_cup_trial01_20261014/DIALOGUE.md) · [耗时与可取得用量](analysis/jelly_packaged_cup_trial01_20261014/PERFORMANCE.md) · [结果状态](analysis/jelly_packaged_cup_trial01_20261014/status.json)

每路录像17分10.7秒，54段全部通过首末帧、元数据和采样索引核验，非原片全帧解码。少量重复/缺采样保留。执行统计窗口1021.829秒，含观察及等待，不是纯机械动作时间。本轮90秒视频见文末导出记录。


## 90秒倍速导出（2026-10-14）

按用户要求另存[三路同屏90秒视频](/home/tuojing/arx_r5_control/exports/jelly_packaged_cup_trial01_20261014_90s/jelly_packaged_cup_trial01_full_3view_90s.mp4)。90.000秒、30 fps、2700帧，约11.45倍速，大小14.19 MiB。左腕/右腕在上，全局在下；覆盖本轮全部54个原片的同一时间轴，包括六次失败试提、松爪撤离和回位，不删去等待阶段。画面标注本轮未抓起及已回位。

成片逐帧解码、首末时刻、三路来源采样对齐及全部原片覆盖检查通过，预览已检查。原录像少量缺采样与重复标记保留；倍速抽帧不能展示每个原始帧，逐帧来源见[映射](/home/tuojing/arx_r5_control/exports/jelly_packaged_cup_trial01_20261014_90s/jelly_packaged_cup_trial01_full_3view_90s_frame_map.jsonl)，核验见[validation.json](/home/tuojing/arx_r5_control/exports/jelly_packaged_cup_trial01_20261014_90s/validation.json)。原始录像及失败结论保持不变。
