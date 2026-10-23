# 第2轮三路录像

录制 2026-10-06T14:45:54.871365+08:00 — 2026-10-06T15:16:07.314580+08:00，三路各18123帧，10fps，共1812.3秒。原录像正常STOP封口，原录制进程已退出；控制保持宿主未停止。

原始录像recording/；同屏[完整三视角视频](combined_video/blackboard_wiping_trial02_full_3view.mp4)，保留等待、人工调整及原速。上排左右腕，下排全局，按共同软件采样索引对齐，不是曝光硬同步。采样缺失黑帧、重复帧保留。

逐路统计：

```json
{
  "left": {
    "frames": 18123,
    "fresh_frames": 18039,
    "duplicate_frames": 46,
    "missing_frames": 38,
    "request_errors": 0
  },
  "right": {
    "frames": 18123,
    "fresh_frames": 18032,
    "duplicate_frames": 52,
    "missing_frames": 39,
    "request_errors": 0
  },
  "top": {
    "frames": 18123,
    "fresh_frames": 18055,
    "duplicate_frames": 30,
    "missing_frames": 38,
    "request_errors": 0
  }
}
```

验证状态：全部93个原始MP4及18123帧同屏视频已全帧解码通过。
