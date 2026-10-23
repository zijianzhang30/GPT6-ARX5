# 三路视频 — 推黑板擦第1轮

- 目录：[recording](recording/)。全局top：external /dev/video2；左腕left：gemini /dev/video20；右腕right：gemini_right /dev/video10。
- 起止：2026-10-11T20:32:22.926157+08:00 至 2026-10-11T21:18:50.001275+08:00，正常STOP、stop_reason=stop_file；PID1444205已退出。机器人保持宿主继续运行。
- 10 fps、60秒分段MP4；每路2786.9秒（约46分27秒），各47段，共141个MP4。
- 覆盖初始核验、左臂推送、右臂观察、撤爪成功复核及最终双臂回位。没有手动停录重启。

| 路 | 总帧 | 新鲜源帧 | 重复源帧 | 缺采样黑帧 | 段数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| right | 27869 | 27742 | 68 | 59 | 47 |
| top | 27869 | 27778 | 31 | 60 | 47 |
| left | 27869 | 27744 | 63 | 62 | 47 |

HTTP请求错误均为0。缺采样和重复源帧保留在逐帧JSONL；共同软件采样时基不等于曝光硬同步。运动前检查最近5个采样必须全部fresh；回位第7段前一次门检未通过，保持静止，恢复后继续，未放宽检查。

[validation.json](recording/validation.json)检查全部141个MP4的序号、帧数、fps、共同采样时基及首末帧解码，均通过；不是每帧全解码。用户后续要求的90秒版本见下节。

## 后续90秒视频导出

[90秒三路同屏视频](/home/tuojing/arx_r5_control/exports/blackboard_eraser_push_trial01_20261011_90s/blackboard_eraser_push_trial01_full_3view_90s.mp4)：90.000秒，三路同屏，约30.96倍速，覆盖本次完整录制时段（每路2786.9秒）。全部2700帧解码、三路同采样索引与141个原片覆盖检查通过；原片保留，未剪去等待或局部调整。

[导出说明与验证](/home/tuojing/arx_r5_control/exports/blackboard_eraser_push_trial01_20261011_90s/README.md)。离线导出不计入冻结的实验执行资源统计。
