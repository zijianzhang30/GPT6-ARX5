# 三路录像记录

全部MP4首末帧可解码，文件帧数与各路manifest一致；未逐帧完整解码。软件共同采样，不是硬件曝光同步。

|目录|MP4数|每路总帧数|结束原因|
|---|---:|---:|---|
|recording|12|2191|SIGTERM|
|recording_continuation01|57|11038|SIGTERM|
|recording_continuation02|18|3139|SIGTERM|
|recording_continuation03|66|12725|SIGTERM|
|recording_continuation04|42|8262|SIGTERM|
|recording_continuation05|21|3713|stop_file|

静止缺口（秒）：14.822474, 47.597193, 21.051087, 32.416832, 26.743877。缺口期间无任务运动。SIGTERM来源未知；缺采样与重复帧计数保留在VIDEO_VALIDATION.json中。
