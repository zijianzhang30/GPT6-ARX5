# 三路视频记录（已封存）

全局external、左腕gemini、右腕gemini_right；同一软件采样网格10 fps、约60秒分段，不是硬件曝光同步。

| 目录 | 状态 | 开始（北京时间） | 结束 | MP4数 | 全部首末帧可解码 |
| --- | --- | --- | --- | ---: | --- |
| [recording](recording/) | completed | 2026-10-10T19:18:13.739429+08:00 | 2026-10-10T19:19:07.485658+08:00 | 3 | True |
| [recording02](recording02/) | failed | 未开始 | 2026-10-10T19:21:55.799559+08:00 | 0 | False |
| [recording03](recording03/) | completed | 2026-10-10T19:22:14.557392+08:00 | 2026-10-10T19:40:23.593521+08:00 | 57 | True |
| [recording04](recording04/) | completed | 2026-10-10T19:40:54.265770+08:00 | 2026-10-10T19:49:21.970143+08:00 | 27 | True |

共87个MP4，约484.6 MiB。全部已存在MP4首末帧检查通过；没有对原片声称逐帧解码验证。recording02无视频，“False”表示该次录像启动失败，不能理解为其他87个文件损坏。

- recording：top 536帧，缺2、重复1、请求错误0；right 536帧，缺2、重复0、请求错误0；left 536帧，缺2、重复1、请求错误0。
- recording03：top 10889帧，缺22、重复14、请求错误0；right 10889帧，缺22、重复37、请求错误0；left 10889帧，缺23、重复23、请求错误0。
- recording04：top 5076帧，缺10、重复7、请求错误0；left 5076帧，缺11、重复13、请求错误0；right 5076帧，缺10、重复11、请求错误0。

recording02启动超时后编排仍继续使能准备，故该阶段缺录；后续抓取/运输/插入均在recording03验证后执行。recording03于19:40:23.594收到SIGTERM，来源未知，早于19:40:41的STOP；至recording04于19:40:54.266启动之间约30.672秒，仅静止观察/归档，没有新运动。recording04覆盖右臂解压、撤离、逐步释放和19:48:26后的故障下落，并于19:49:21.970正常STOP结束。

[文件验证明细](closed_recordings_validation.json) · [故障关键帧来源索引](fault_1948/video_frames_mapping.json)。缺采样保留为带标注黑帧，重复帧保留统计；不声称整轮无缺口，不删除失败或静止原片。

## 完整连续播放版（离线解码/转码）

应用户要求，将本轮所有已保存片段按原速和共同时间轴合并，每路31分08.1秒，缺录处显示说明并保留等待时长。

- [全局完整视频](full_video/flower_trial07_full_top.mp4)
- [左腕完整视频](full_video/flower_trial07_full_left.mp4)
- [右腕完整视频](full_video/flower_trial07_full_right.mp4)
- [来源、时间映射与缺录说明](full_video/FULL_VIDEO.md)
- [全帧解码验证](full_video/validation.json)

这次离线导出已逐帧读取全部87个原始MP4，各文件读取帧数均与声明帧数一致；三路H.264成片又通过ffmpeg严格逐帧解码，每路18,681帧。原始文件和原始验证日志保持不变。解码导出不补造历史未录画面，也不将人工复位写成受控回位。

## 90秒倍速浏览版

按用户要求将三路完整视频统一加速约20.76倍，各90秒。原速文件保留；缺录提示保留，三路相同时间轴。全部成片2700帧已通过完整解码验证。

- [全局90秒](full_video/preview_90s/flower_trial07_top_90s.mp4)
- [左腕90秒](full_video/preview_90s/flower_trial07_left_90s.mp4)
- [右腕90秒](full_video/preview_90s/flower_trial07_right_90s.mp4)
- [倍率与来源映射](full_video/preview_90s/VIDEO_90S.md)
