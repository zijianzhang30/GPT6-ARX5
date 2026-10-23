# 挂帽第8轮三路视频

准备段[recording](recording/)：2026-10-10T22:07:29.937538+08:00—2026-10-10T22:09:30.841478+08:00，三路各1208帧，9个MP4，39,058,760字节。仅覆盖接口恢复后的场景和等待清场，不含SDK动作。

首次续段[recording02](recording02/)：相机冷启动请求超时，manifest=`failed`，没有进行SDK初始化；失败证据保留。

初始化段[recording03](recording03/)：2026-10-10T22:11:53.487038+08:00—2026-10-10T22:13:37.758274+08:00，三路各1041帧，6个MP4，32,813,295字节；完整覆盖一次SDK连接、零回包故障和驱动退出。两段有效视频共71,872,055字节（约68.5MiB）。全部15个MP4仅验证首末帧可解码，未逐帧检查。准备段和初始化段分开记录，中间时间不声称有录像；每路少量缺采样/重复源帧见manifest，10fps共同软件采样不是曝光硬同步。

- [准备段manifest](recording/manifest.json)、[准备段验证](recording_validation.json)
- [失败启动manifest](recording02/manifest.json)
- [初始化段manifest](recording03/manifest.json)、[初始化段验证](recording03_validation.json)
