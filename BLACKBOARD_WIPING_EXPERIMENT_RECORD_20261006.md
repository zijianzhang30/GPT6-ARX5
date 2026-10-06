# 擦黑板实验记录 — 2026-10-06

第1轮未验证字迹擦除。左臂夹住预置软布并带动，经过两种接触形态、3次短擦后字迹仍明显；主要观察到布尾悬垂和折叠，未形成有效平整擦拭面。已放布并验证独立稳定，左臂六段回位、右臂原位核验通过，无本轮运行故障。

- [完整记录](analysis/blackboard_wiping_trial01_20261006/RUN_RECORD.md)
- [三视角视频](analysis/blackboard_wiping_trial01_20261006/combined_video/blackboard_wiping_trial01_full_3view.mp4)
- [录像说明](analysis/blackboard_wiping_trial01_20261006/VIDEO_RECORD.md)
- [耗时及token](analysis/blackboard_wiping_trial01_20261006/PERFORMANCE.md)
- [关键图证据](analysis/blackboard_wiping_trial01_20261006/EVIDENCE.md)
- [公开对话](analysis/blackboard_wiping_trial01_20261006/DIALOGUE.md)
- [对应skill](/home/tuojing/.codex/skills/arx-r5-tabletop-tasks/references/blackboard-wiping.md)

旧宿主14:04保持异常早于本任务；用户确认曾人工挪动左臂，具体触发仍不能唯一归因。新宿主健康保持，不为停止录像或归档而关闭。


## 第2轮软布：未验证擦除，用户切换任务

[完整记录](analysis/blackboard_wiping_trial02_20261006/RUN_RECORD.md)；[三视角完整视频](analysis/blackboard_wiping_trial02_20261006/combined_video/blackboard_wiping_trial02_full_3view.mp4)。两次前后短擦字迹仍明显；布的随爪运输包含搭挂，稳定对夹不确定。张爪并撤离后完全释放、两次独立稳定核验通过。新折边抓取尚未闭爪即有人工调布、换板擦；左臂撤离并回位一段后，用户取消剩余回位、原位续行新任务，故未完成左臂回位。右臂保持原位，原误差容差内。无本轮运行故障。

执行31分09.314秒，去重token 14,263,545（含缓存输入，详细口径见PERFORMANCE.md）。三路录像30分12.3秒正常封口，93个原始MP4及18123帧同屏全部解码通过；保留缺采样/重复帧。归档与下一轮准备交错，未虚报独占归档耗时/token。

## 第3轮硬质板擦：按“有擦拭动作”标准通过

[完整记录](analysis/blackboard_wiping_trial03_20261006/RUN_RECORD.md)、[视频与验证](analysis/blackboard_wiping_trial03_20261006/VIDEO_RECORD.md)、[资源与耗时](analysis/blackboard_wiping_trial03_20261006/PERFORMANCE.md)、[关键证据](analysis/blackboard_wiping_trial03_20261006/EVIDENCE.md)。人工预置板擦后左臂夹持运输，右臂辅助观察；短擦有可见板面相对运动，用户现场确认擦垫接触黑板。按本轮v2无需擦除字迹的标准通过，不等同自主取物或擦除成功。

板擦已释放并两次确认独立稳定；左臂六段、右臂五段回到恢复时保存的参考，两次原2.5°容差检查通过，实测最大误差左1.4207°、右0.7868°。准备阶段曾右SDK错误32、左臂下落；新承托确认、一次标准右SDK重连及受检控制交接单列，根因未知，不能称整轮无故障。

执行窗口15:16:07.101—15:42:07.391，共26分00.290秒；去重执行token 25,552,789（含缓存输入，详见资源记录）。三路录像15:16:24.912—15:42:07.718正常STOP，时长25分42.7秒；同屏全帧验证状态以VIDEO_RECORD.md为准。物理任务结束时双臂已受控回位并健康保持。

**结束后新故障：15:43:28右SDK再次异常，宿主退出、双臂失能，未自动重连或重新使能。** 异常晚于录像结束80.43秒，没有对应连续录像；新静帧仍见板擦放稳、两臂在回位附近。回位通过是此前已保存的验证结果，不代表当前健康。详见[故障证据](analysis/blackboard_wiping_trial03_20261006/post_task_fault/INCIDENT.md)。一次重连只恢复了当时反馈，没有证明底层问题已经解决。
