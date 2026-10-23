# 三路录像

60个MP4，每路累计1099.1秒。第一段SIGTERM封口，第二段及回位段正常STOP；相邻段无新运动缺口为[19.811443, 8.979079]秒。

[第一段](recording/) · [第二段](recording_resume01/) · [回位段](recording_return/) · [118秒成片](video/flower_transfer_trial01_three_views_118s.mp4) · [校验](video_validation.json) · [完整说明](RUN_RECORD.md#三路视频)


## 两分钟以内剪辑交付

[三视角118秒MP4](video/flower_transfer_trial01_three_views_118s.mp4)，960×1134、20fps、2360帧，12.79MiB。删除部分等待后保留557.7秒源时间，约4.726倍速压缩；三路共用原始采样帧，完整任务动作、回位动作、释放失败和人工扶花保留。两处停录间隔见上文。

成片所有2360帧以及60个源MP4的全部帧已解码验证通过；此逐帧检查范围高于初次原片首末帧检查。输出每帧到源目录/帧号/现场时间的映射见[时间映射](video/timeline.jsonl)，其余验证见[成片元数据](video/manifest.json)和[原片全帧验证](video/source_validation_full.json)。三路画面顺序为上排左腕/右腕，下排全局。
