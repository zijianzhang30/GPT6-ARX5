# Video evidence

All three views retained: top/external, physical left wrist/gemini, physical right wrist/gemini_right.
213 MP4 files, 71 per view; each view has 41,916 encoded frames at 10 FPS (4,191.6 seconds).
All first/last frames, FPS and frame totals match the manifests. This is endpoint validation, not a full-frame decode.

| Batch | Started / ended (Asia/Shanghai) | MP4s | Closure |
| --- | --- | ---: | --- |
| [recording/](recording/) | 2026-10-20T13:56:32.930500+08:00 / 2026-10-20T14:26:02.066897+08:00 | 90 | SIGTERM |
| [recording02/](recording02/) | 2026-10-20T14:26:29.705780+08:00 / 2026-10-20T14:56:09.589312+08:00 | 90 | stop_file |
| [recording03/](recording03/) | 2026-10-20T14:56:10.088101+08:00 / 2026-10-20T15:06:52.993448+08:00 | 33 | stop_file |

Two manifest-to-manifest gaps: 27.638883 s after the first recorder received SIGTERM (cause unknown), and 0.498789 s during the controlled singleton-recorder rollover. Both arms were stationary, with no task/return motion dispatched during either interval. These gaps mean the recordings are not fully continuous. Sampling misses and duplicated frames remain in the manifests and per-frame JSONL; no concealment or recovery rewrite was performed.

See [detailed validation](video_validation.json), [first gap](recording_gap.json), [rollover](recording_rollover.json), and [final images](final_scene/).

## 用户指定的 90 秒合成版

[90 秒三视角合成视频](三视角视频/抽书实验_三视角_90秒.mp4)。上方左腕／右腕，下方头部相机；1280×960、30 FPS、严格 90.000 秒。全部 2700 帧与同轴来源映射验证通过。约 46.89 倍速，原片保留，两处录像间隔在画面和记录中标注。详见[合成说明](三视角视频/README.md)及[验证](三视角视频/validation.json)。
