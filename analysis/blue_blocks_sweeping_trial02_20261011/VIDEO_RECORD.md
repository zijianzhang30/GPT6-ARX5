# 三路视频记录 — 扫蓝块第2轮

录像目录：[recording](recording/)。全局top（external，/dev/video2）、左腕left（gemini，/dev/video20）、右腕right（gemini_right，/dev/video10）。

- 开始：2026-10-11T18:06:31.232468+08:00；正常STOP封口：2026-10-11T18:36:34.654673+08:00。
- 三路各1803.3秒（约30分03秒）、18033帧，10 fps、60秒分段、MP4V；共93个MP4。
- 从准备、初始回位、自主拾刷、扫入、工具释放到最终两次回位核验均在此时窗；无手动停录重启。
- 录制进程1255156已退出，manifest=`completed`、stop_reason=`stop_file`。健康机器人保持宿主未停止。

| 路 | 总帧 | 新鲜源帧 | 重复源帧 | 缺采样黑帧 | MP4段数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| top | 18033 | 17972 | 22 | 39 | 31 |
| left | 18033 | 17948 | 47 | 38 | 31 |
| right | 18033 | 17949 | 45 | 39 | 31 |

各路HTTP请求错误为0。缺采样和重复源帧已保留在逐帧JSONL，不声称零缺帧或硬件曝光同步。运动前门检若最近5帧不全fresh则不下发动作，恢复后重新取图审核；包括18:35右臂回位前的一次拒绝。

[validation.json](recording/validation.json)验证93个MP4均可打开，片段序号、帧数、10 fps、共同采样时基及每段首末帧解码通过；本检查不是逐帧全解码。实验封存时尚未生成90秒版；后续用户要求的导出见下文。


## 后续90秒视频导出

按用户后续要求，完整三路同屏视频已导出为[90秒MP4](/home/tuojing/arx_r5_control/exports/blue_blocks_sweeping_trial02_20261011_90s/blue_blocks_sweeping_trial02_full_3view_90s.mp4)。约20.04倍速，90.000秒、2700帧、1280×1152，全部成片帧解码及时间映射通过，93个原始片段均有取样覆盖。原速录像保留，倍速抽帧不替代原速证据。导出记录：[blue_blocks_sweeping_trial02_20261011_90s](/home/tuojing/arx_r5_control/exports/blue_blocks_sweeping_trial02_20261011_90s/README.md)。离线导出资源未追加到冻结实验窗口。
