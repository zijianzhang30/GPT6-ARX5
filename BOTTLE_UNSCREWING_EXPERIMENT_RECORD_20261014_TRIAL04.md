# 双臂旋瓶盖 · 2026-10-14 第4轮

## 12:34回位补记（最新状态）

**三路录像已停止；双臂已受控回到本轮默认初始位姿，即厂商HOME六关节零位。** 用户完成故障后检查并确认退出后，恢复保持、左右各两段回位，12:34:21/24两次原2.5°核验通过；最大实测误差左1.104°、右0.382°。健康保持宿主PID570881 / PTY59455继续运行。回位按用户要求没有录像，保留静帧和日志。任务失败结果不变；未重新尝试旋盖。

详见[恢复记录](analysis/bottle_unscrewing_trial04_20261014/RECOVERY_RECORD.md)及[两次回位核验](analysis/bottle_unscrewing_trial04_20261014/final_home_verified.json)。以下是停录时的原实验记录，原故障及当时未回位状态按时间保留。

## 停录时结果与状态（12:31）

**任务失败：未验证可靠持瓶，未执行右臂夹盖、退丝或提离3–5厘米。** 左爪调整夹点后的闭合发生到位超时，双臂保护失能，左臂下落、瓶子倒在桌面；未完成最终受控回位。12:30:46只读快照中两侧SDK仍ready、有反馈，但均disabled、无owner；不能把SDK ready当作机械臂已使能。

本轮三路录像已正常停止并保存。已请求新的承托/线缆/瓶子检查和清场确认，等待回复；本轮结束后的恢复须另行记录，不能覆盖此次故障。

## 协议、分工与参考

> Hold the bottle steady with the left arm, unscrew the cap with the right arm, then lift the cap 3–5 cm away from the bottle opening.

左臂固定较低瓶身，右臂旋盖；完全退丝后提离瓶口3–5厘米。所有动作逐臂执行并检查连杆、夹爪、相机和线缆间隙。桌面为单只透明瓶及带红色标线的白盖。CAN保持用户已交换后的映射：物理左5E5931→can0→8765，物理右765931→can1→8766。

初始/最终参考继承用户确认的厂商HOME六关节零位，见[return_reference.json](analysis/bottle_unscrewing_trial04_20261014/return_reference.json)。不是新宿主启动时的回落姿态。12:23:31/34初始HOME两次原2.5°核验通过：左最大实测1.104°、右0.688°，指令最大约0.0057°。最终回位未完成，这不撤销已记录的初始核验。

## 过程

| 阶段 | 事实及判定 |
| --- | --- |
| 旧故障检查 | 旧白板宿主12:10:32发生JPEG解码监督故障并退出，早于本轮；左右腕偏离HOME。旧故障无该时刻视频，证据另存prior_host_termination.json |
| 本轮确认 | 用户“已检查并退出，可立即急停；未断电或改线”。两侧SDK健康、CAN计数增长，未重连SDK |
| 录像与恢复 | 2026-10-14T12:22:00.656504+08:00开始录像；三轮PIL解码/新帧检查通过，标准入口逐侧恢复保持。宿主PID285557/PTY24573；左右各两段受控回初始HOME |
| 左03–12 | 分段接近。初始位置偏向瓶肩，瓶子出现偏转，撤开重新对齐更低瓶身；对齐后改变约20°俯角。疑似指侧接触与偏转保留，不称全程无接触 |
| 左13–16 | 开度0.58后12毫米指令试提不明确；右03仅在基座附近换观察位。左开度0.45后第二次12毫米指令试提仍未获得明确离面证据；指令位移不能等同实物抬升 |
| 左17–23 | 停止同点重复试提。下调支撑、以0.02增量松至0.55，随后15毫米前移/10毫米下调指令调整夹点；期间瓶子倾斜，未把松爪目标当作独立释放验证 |
| 左24 | 0.55→0.40闭合，到位超时，触发双臂保护失能；不能把堵转当作抓稳 |
| 故障后 | 12:30:46新图显示左臂下落、瓶子横倒、盖仍在瓶上。右臂也已失能，未旋盖。故障录像保留，请求新的现场检查 |
| 停录 | 2026-10-14T12:31:06.074931+08:00正常STOP，30段原片通过元数据/首末帧与索引核验 |

## 故障依据与限制

故障时最后检查为arm_ok=true、command_ok=true、grip_ok=false。左爪原始读数由2.69703到2.37888，目标2.05965，绝对残差0.31923超过原0.15容差；闭合进度约46.4%，低于原50%要求。约5.806秒到位窗口后失败，见[FAULT_ANALYSIS.json](analysis/bottle_unscrewing_trial04_20261014/FAULT_ANALYSIS.json)。现场表现与物体接触限制闭合相符，但没有测得夹持力，不能据此确定硬件根因。此为动作到位故障，不是本轮SDK断联或相机故障。

启动保留了原跟踪、到位、相机、心跳、关节和预算保护。配置了已有的到位故障保持选项，但本次夹爪故障实际仍传播为失能，不能称该选项防止了下落，未修改任何保护阈值。唯一宿主已退出，无竞争控制器。最后左J4约78.46°，后续先检查当前关节范围和承托，禁止盲目重新使能。

规划阶段有步幅、会话行程和余量拒绝；无不明接触且健康静止时按原规则续段。左08首次下发因Robot changed after observation被拒，刷新后重算执行。未执行的候选不计作动作。正常动作、拒绝及故障逐项见[action_summary.json](analysis/bottle_unscrewing_trial04_20261014/action_summary.json)。未观察到两臂相互碰撞，但确有左臂下落和瓶子倾倒。

## 文件

- [三路MP4](analysis/bottle_unscrewing_trial04_20261014/recording) · [录像说明](analysis/bottle_unscrewing_trial04_20261014/VIDEO_RECORD.md)
- [原始控制归档](analysis/bottle_unscrewing_trial04_20261014/control_archive) · [故障后状态与三视角](analysis/bottle_unscrewing_trial04_20261014/after_gripper_fault)
- [初始HOME两次核验](analysis/bottle_unscrewing_trial04_20261014/initial_home_verified.json) · [故障抽帧](analysis/bottle_unscrewing_trial04_20261014/fault_frames)
- [公开对话](analysis/bottle_unscrewing_trial04_20261014/DIALOGUE.md) · [资源与耗时](analysis/bottle_unscrewing_trial04_20261014/PERFORMANCE.md)

录像共9分05.3秒/路，原片保留少量缺采样与重复帧；不是硬件曝光同步，也未宣称全帧解码。此报告仅截至本轮停录，恢复回位仍待新的现场检查。
