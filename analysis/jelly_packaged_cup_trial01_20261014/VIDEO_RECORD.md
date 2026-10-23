# 三路原始录像

2026-10-14T13:23:39.073735+08:00 至 2026-10-14T13:40:49.918268+08:00。STOP正常封口，进程退出0。每路10307帧、1030.7秒（17分10.7秒），18个片段；总54个MP4。10 fps、60秒分段、MP4V。

| 视角 | 设备 | 新帧 | 重复 | 缺采样 | 请求错误 |
| --- | --- | ---: | ---: | ---: | ---: |
| top | /dev/video2 | 10272 | 13 | 22 | 0 |
| left | /dev/video20 | 10260 | 25 | 22 | 0 |
| right | /dev/video10 | 10259 | 25 | 23 | 0 |

全部54段元数据、帧数、首末帧解码和共同采样索引核验通过；未做原片逐帧解码。缺采样黑帧和重复标记保留，三路不是硬件曝光同步。录制门禁偶有最近帧不连续，复检通过后才下发动作；没有重启录像。

覆盖初始核验、六次试提、松爪撤离和最终回位。开始时已处于HOME，不包含上轮瓶盖恢复。本轮90秒导出见文末；原片不覆盖后续离线报告编写。

[原片目录](recording/) · [核验结果](recording/validation.json)


## 90秒倍速导出（2026-10-14）

按用户要求另存[三路同屏90秒视频](/home/tuojing/arx_r5_control/exports/jelly_packaged_cup_trial01_20261014_90s/jelly_packaged_cup_trial01_full_3view_90s.mp4)。90.000秒、30 fps、2700帧，约11.45倍速，大小14.19 MiB。左腕/右腕在上，全局在下；覆盖本轮全部54个原片的同一时间轴，包括六次失败试提、松爪撤离和回位，不删去等待阶段。画面标注本轮未抓起及已回位。

成片逐帧解码、首末时刻、三路来源采样对齐及全部原片覆盖检查通过，预览已检查。原录像少量缺采样与重复标记保留；倍速抽帧不能展示每个原始帧，逐帧来源见[映射](/home/tuojing/arx_r5_control/exports/jelly_packaged_cup_trial01_20261014_90s/jelly_packaged_cup_trial01_full_3view_90s_frame_map.jsonl)，核验见[validation.json](/home/tuojing/arx_r5_control/exports/jelly_packaged_cup_trial01_20261014_90s/validation.json)。原始录像及失败结论保持不变。
