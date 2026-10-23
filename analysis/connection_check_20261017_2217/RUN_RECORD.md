# 机器人连接与驱动验证

用户请求：现在请你连接到机器人，确认可以驱动机器人。

2026-10-17 22:14–22:16（Asia/Shanghai）完成真实硬件检查。目录名只是唯一标识，实际时间以事件和录像时间为准。

- CAN 身份已核对：物理左臂 2088335E5931 → can0 → 8765；物理右臂 208833765931 → can1 → 8766。两个接口存在且 RX 持续增长。
- 初态双臂 ready、disabled、无 owner、无错误码，六关节反馈有限且稳定。此前保持宿主已不存在；本轮没有重启 CAN 或 SDK。首次默认 urllib 请求被环境代理返回 502，随后本地直连取得正常反馈，并非机器人服务故障。
- 三路新图确认双臂收拢、空爪、运动邻域无人。先启动三路 MP4，再由标准 start_idle_review / prepare-idle 入口恢复双臂受监督保持，保护阈值未更改。
- 左右逐侧执行空爪 +0.02 归一化开度，再恢复各自使能后的开度，共 4 条动作。每次审阅新图、核验录制及到位反馈。左实测原始开度约 3.4245 → 3.5180 → 3.4279，右约 0.1370 → 0.2308 → 0.1362，均 settled=true。归一化/SDK 原始开度不代表毫米或夹持力。
- 没有下发机械臂关节运动轨迹；本次验证范围为双臂使能保持、实时反馈及两侧夹爪实际驱动，不是全部关节行程或桌面任务验收。
- 22:15:57 与 22:16:00 两次稳定检查通过。双臂 ready/enabled/holding、moving=false、无错误；关节指令未改变，夹爪指令完全恢复。相对使能后初态最大实测漂移左 0°、右 0.02186°。使能前后原始数据另存，未宣称厂商 HOME 或旧任务回位。

唯一健康控制宿主 PID 2552932，工具会话 43408，owner dual-policy-acd76c994baa454bb6e13f2323f17676，当前选中 right，control 日志见本目录。健康保持继续运行，不关闭宿主。后续必须重新核验实时状态与场景，任何新动作需重新启动录像。

三路录像正常 STOP，manifest=completed，6 个 MP4，每路 724 帧 / 72.4 秒 / 10 fps。全部首末帧可解码及帧数/FPS检查通过；未做逐帧解码。每路标记 2 个缺采样时隙，重复帧 top=2、left=1、right=3，无请求错误；不称零缺帧。详见 recording/manifest.json、各路 frames.jsonl 和 video_validation.json。

证据：preflight_0/1.json、state_8765/8766.json、control/initial_state.json、return_reference.json（本次连接验证基线）、control/events.jsonl、final_checks.json、三路 JPEG 与 recording/。保留历史任务参考，不修改历史任务结论。
