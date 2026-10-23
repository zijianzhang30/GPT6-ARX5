# 双臂旋瓶盖 · 2026-10-14 第4轮

## 目标与验收

> Hold the bottle steady with the left arm, unscrew the cap with the right arm, then lift the cap 3–5 cm away from the bottle opening.

左臂固定较低瓶身，右臂夹住并旋下瓶盖；验证盖已退丝后提离瓶口3–5厘米。记录三路MP4及本实验Markdown。不能以右腕转角替代瓶盖实际旋转、不能以夹爪抬高代替盖瓶分离。逐臂分段动作，检查两臂、相机、线缆及旋盖/松爪/退出全程间隙。

## 当前阶段：故障后只读准备，尚未使能或执行

12:21现场为桌面单只透明瓶、白色旋盖。两侧SDK均ready、disabled、stationary、owner为空，关节反馈有效，CAN计数增长；映射仍物理左5E5931/can0/8765、右765931/can1/8766。原保持宿主PID1720232已退出。

旧宿主日志显示12:10:32.900出现 `Camera supervision failed: OSError: broken data stream when reading image file`。这发生在上轮12:00:47停录以后、此次任务之前，不归因于旋瓶盖动作。只读新图可解码；尚不能确定单帧损坏的底层原因，也没有失能瞬间视频。左J4约−11.27°、右J4约−13.34°，已偏离上轮核验的HOME，不能沿用上轮健康保持快照。

已按技能请求本次检查承托、线缆/间隙、退出运动范围及可急停确认，并询问是否断电或改线。待回复后仍须核验新图、实时反馈、三路录像，再通过现有标准入口恢复保持。当前未重连SDK、未下发运动。回位参考继承用户确认的厂商HOME（六关节零位），保存于return_reference.json；当前偏离不修改参考。

## 证据

- `task_prompt.md`：冻结prompt与验收。
- `preflight/`：本轮初态、三路图、两侧CAN状态。
- `prior_host_termination.json`：前一保持宿主的终止证据。
- `skill_snapshot.md`：旋盖流程快照。
- 任务结果：未执行；固定瓶身、夹盖、退丝、3–5厘米分离、最终释放与回位均未验证。
