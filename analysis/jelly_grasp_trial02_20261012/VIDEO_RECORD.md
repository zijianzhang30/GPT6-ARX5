# 三路视频 · 夹取果冻第2轮

已停止录制。全部为MP4、10fps、60秒分段；共同软件采样时基，不是曝光硬同步。

| 目录 | 范围 | 各路帧数/视频时长 | 片段数 | 状态与验证 |
| --- | --- | --- | --- | --- |
| recording | 初次冷相机启动 | 0 | 0 | failed manifest保留 |
| recording02 | 19:35:03.122727–19:35:53.247375 | 500 / 50秒 | 3 | 正常completed，元数据与首末帧通过 |
| recording03 | 19:36:23.760142–最后采样约19:57:38.36 | 12747 / 1274.7秒 | 66 | 用户19:57:38停止；进程已退出，返回143、manifest未完成；所有文件帧数与日志相符、首末帧通过 |

总计69个MP4，每视角合计1324.7秒。原始manifest未修改，退出后状态见active_recording.json和user_stop_recording.json，检查见recording03/validation_after_exit.json。原manifest状态不等于仍有进程；已确认PID1476089不存在。退出码成因未确认，不称正常completed，也未重录或补造结束画面。

| 目录/视角 | fresh | duplicate | missing |
| --- | ---: | ---: | ---: |
| recording02/top | 498 | 0 | 2 |
| recording02/left | 496 | 2 | 2 |
| recording02/right | 497 | 1 | 2 |
| recording03/top | 12701 | 19 | 27 |
| recording03/left | 12694 | 26 | 27 |
| recording03/right | 12688 | 33 | 26 |

recording02结束至recording03开始约30.51秒缺录，期间没有硬件动作；recording03各路HTTP请求错误为0。missing/duplicate均保留原标签与采样日志。首末帧检查不等于全帧解码。

全部抓取尝试与左臂回位、右臂第一段回位在recording03内。用户明确停录后，右臂最后约2.51°修正及最终核验未录像，只有监督图与控制日志。未为本轮生成90秒成片；上一轮90秒成片不能作为本轮结果。
