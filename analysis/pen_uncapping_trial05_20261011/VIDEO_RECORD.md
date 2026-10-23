## 三路录像

共45个MP4，3路分别为全局/dev/video2、左腕/dev/video20、右腕/dev/video10，全部使用既有HTTP图像流；未另开相机设备。

| 目录 | 起止 | 每路帧数 | 文件数 | 结束方式 |
| --- | --- | --- | --- | --- |
| [recording](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/recording) | 13:20:01.979—13:30:19.913 | 6178 | 33 | SIGTERM，来源未知 |
| [recording_continuation01](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/recording_continuation01) | 13:30:28.507—13:34:06.397 | 2177 | 12 | stop_file，退出0 |

8.594196秒缺口期间没有下发运动；缺帧和重复帧统计原样保留，不能称全程连续、零缺帧或硬件曝光同步。所有MP4首末帧可解码、各路帧数总和与manifest相符；未逐帧解码全部原片。见[验证结果](/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/video_verification.json)。

