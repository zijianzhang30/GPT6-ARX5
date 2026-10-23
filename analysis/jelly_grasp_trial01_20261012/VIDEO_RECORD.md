# 夹取果冻 · 三路录像封存

四阶段共 **69个MP4**，每路累计1207.5秒，10fps、60秒分段。全部manifest completed；第3阶段收到SIGTERM后正常封口，发送者未确认，其余由STOP正常结束。当前无本轮活动录像。

| 阶段 | 时间（+08:00） | 每路时长 | MP4数 | 结束方式 |
| --- | --- | --- | --- | --- |
| [首次左SDK恢复失败](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/recording) | 18:33:08.357–18:34:37.155 | 88.6s | 6 | stop_file |
| [检查后第二次左SDK恢复失败](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/recovery02/recording) | 18:36:57.125–18:37:20.669 | 23.4s | 3 | stop_file |
| [桥接恢复、双臂使能、抓放及回位第1段](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/bridge_recovery03/recording) | 18:38:51.821–18:55:06.280 | 974.5s | 51 | SIGTERM |
| [回位第2–6段及最终核验](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/final_return04/recording) | 18:55:36.295–18:57:37.397 | 121.0s | 9 | stop_file |

三路固定对应top=/dev/video2、left=/dev/video20、right=/dev/video10。每段元数据、连续采样索引、共同软件时基与首末帧解码通过，各目录validation.json为证。未执行原片全帧解码，软件时基也不等于曝光硬同步。

## 缺口与缺采样

| 阶段 | 缺采样 top/left/right | 重复 top/left/right | HTTP错误 |
| --- | --- | --- | --- |
| recording | 2/2/2 | 2/1/4 | 0 |
| recovery02/recording | 1/1/1 | 0/1/1 | 0 |
| bridge_recovery03/recording | 20/22/22 | 10/26/24 | 0 |
| final_return04/recording | 2/3/2 | 2/4/4 | 0 |

阶段间没有MP4的区间分别为139.970秒, 91.151秒, 30.015秒，详见[机器可读汇总](recording_summary.json)。前两处位于恢复准备阶段，无抓放/回位轨迹。第三处为18:55:06.281–18:55:36.296：回位第1段已完成，未下发move_to或set_gripper；18:55:27执行过健康静止renew，包含以实测关节重锚保持目标，因此不能声称该缺口没有任何控制操作，也不能声称全流程连续录像。对应新图、原始状态和事件保留在control及冻结快照中。

发现第3阶段结束后，暂停下一段回位，另目录启动第4阶段。录制门控最初因仍使用旧进程累计帧数而拒绝；保存旧计数，读取新进程计数作为基线后，连续增长与新鲜帧检查通过，才执行回位第2段。没有放宽录制检查阈值。后续新进程应按身份分开维护增长基线，renew前也应先检查录像。

缺采样以黑帧保留，重复源帧有标注；没有删去失败、侧倒或等待来伪装成功。原始停录时未导出倍速版；后续按用户要求另存的90秒版本见下节。


## 后续90秒视频导出（2026-10-12T19:14:54.410051+08:00）

[90秒三路同屏视频](/home/tuojing/arx_r5_control/exports/jelly_grasp_trial01_20261012_90s/jelly_grasp_trial01_full_3view_90s.mp4)：90.000秒、30fps、约16.32倍速，完整来源时间范围均匀压缩，保留四阶段准备/恢复、失败尝试、成功抓放及回位，三处缺录显示提示。2700帧全帧解码、三路采样对齐及69个原始片段覆盖检查通过。原片保留；导出资源不计入冻结执行窗口。

[导出说明、映射与验证](/home/tuojing/arx_r5_control/exports/jelly_grasp_trial01_20261012_90s/README.md)。
