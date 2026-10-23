# 挂帽第9轮三路视频

`recording/`：首次启动首帧超时，`manifest.json` 状态 `failed`；未生成有效 MP4，保留原失败记录。

`recording02/`：2026-10-10 23:26:14.794–23:26:26.826 CST，12.032 秒，10 fps，MP4/mp4v。全局、左腕、右腕设备分别 `/dev/video2`、`/dev/video20`、`/dev/video10`；各 120 帧全部为新鲜源帧，缺失、重复、请求错误均为 0。三路文件首帧与第 120 帧均经 OpenCV 解码通过。

- [全局](recording02/top_0000.mp4)
- [左腕](recording02/left_0000.mp4)
- [右腕](recording02/right_0000.mp4)
- [录制清单](recording02/manifest.json)

本轮没有机器人动作，视频只能作为摆位与准备状态证据，不能标为挂帽执行视频。相机位姿未发生受控恢复；录制期间相机设备身份稳定。
