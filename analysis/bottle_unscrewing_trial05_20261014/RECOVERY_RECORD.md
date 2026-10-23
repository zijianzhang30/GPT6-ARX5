# 第5轮停录后恢复与视频导出

更新：2026-10-14T13:16:33.807401+08:00

## 结果

原旋瓶盖任务仍记失败，未夹盖、未退丝、未提离。用户要求停录、导出90秒视频并回初始位姿；停录后恢复作为独立阶段，未覆盖原故障或改写任务耗时统计。

用户回复“确认可以”后，新图显示两臂已人工折回，空爪且瓶子单独放在桌面，关节回到原控制范围。人工折回不是受控回位；两侧SDK与CAN保持健康，未重启SDK或桥接。标准入口恢复唯一保持后，左右各执行两段有界运动，先到约[0,6,6,0,0,0]度，再回本轮冻结的厂商HOME六关节零位。每段单臂运动、另一臂保持，原跟踪/到位/预算/相机保护保留。

左臂完成后发现桌面新出现黑色小车状物，暂停右臂回位，收到新的清场确认并复核图像后续行。四段动作均通过原到位检查；恢复期间未观察到两臂碰撞，不将此表述为形式化碰撞检测通过。回位全程无MP4录制，仅保存三路静帧、状态和事件。

## 原HOME两次核验

时间：2026-10-14T13:16:27.160342+08:00 与 2026-10-14T13:16:30.178568+08:00；原容差2.5度。

| 臂 | 最大实测关节误差 | 最大指令关节误差 |
| --- | ---: | ---: |
| 左 | 1.103759° | 0.005672° |
| 右 | 0.404347° | 0.005673° |

两次均ready、enabled、holding、stationary、无错误、原owner、反馈新鲜。当前唯一保持宿主PID 1700471 / PTY 39351继续运行，工作臂right。新宿主初态为人工折回姿态，不能使用其原生return-working-step替代原HOME参考。下一任务仍须核验实时状态和新图。

## 导出与证据

- [90秒三视角视频](/home/tuojing/arx_r5_control/exports/bottle_unscrewing_trial05_20261014_90s/bottle_unscrewing_trial05_full_3view_90s.mp4)：完整录制时间线约11.33倍速，90.0秒、2700帧、30fps，H.264，1280×1152；51个原片均有覆盖，失败结尾保留，原片未改动。
- [视频全帧核验](/home/tuojing/arx_r5_control/exports/bottle_unscrewing_trial05_20261014_90s/validation.json)：解码、时间端点、三路共同采样索引通过；不包含停录后恢复。
- [两次HOME核验](/home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial05_20261014/recovery_final_home_verified.json)、[最终三路静帧与状态](/home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial05_20261014/recovery_final)。
- [恢复事件与图像](/home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial05_20261014/recovery_control)、[结构化结果](/home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial05_20261014/RECOVERY_RESULT.json)。

CAN仍为物理左5E5931→can0→8765、右765931→can1→8766。恢复与导出的资源窗口独立于原任务PERFORMANCE.md，不把等待用户、编码或恢复时间写成任务推理耗时。
