# 第3轮三路录像

2026-10-06T15:16:24.912204+08:00 — 2026-10-06T15:42:07.718162+08:00，10fps，三路各15427帧（1542.7秒）。正常STOP封口，当时控制宿主仍保持。15:43:28归档期间右SDK再次故障、双臂失能，发生在录像结束约80.43秒之后；本视频没有覆盖该次异常，另见[结束后故障记录](post_task_fault/INCIDENT.md)。

[完整三视角视频](../../OMITTED_FILES.html#bf3e2932ddfb2040)。上排左右腕、下排全局，保留原速、人工等待、故障下落、重连、恢复、擦拭、释放及回位。原始分段位于recording/；共同软件采样索引对齐，不是曝光硬同步。缺采样黑帧和重复帧均保留并标注。

全部78个原始MP4和15427帧同屏均已完整解码通过。

```json
{
  "left": {
    "frames": 15427,
    "fresh_frames": 15343,
    "duplicate_frames": 46,
    "missing_frames": 38,
    "request_errors": 0
  },
  "right": {
    "frames": 15427,
    "fresh_frames": 15340,
    "duplicate_frames": 46,
    "missing_frames": 41,
    "request_errors": 0
  },
  "top": {
    "frames": 15427,
    "fresh_frames": 15362,
    "duplicate_frames": 28,
    "missing_frames": 37,
    "request_errors": 0
  }
}
```

映射见combined_video/timeline.jsonl，完整验证见combined_video/manifest.json和raw_video_validation.json。
