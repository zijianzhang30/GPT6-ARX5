# 中间书本抽取第2轮：录像与恢复

录制起点2026-10-06 13:00:16.419810+08；最后采样13:51:00.419810+08。三路10fps、每路30,441条时间索引，派生视频时长3,044.1秒。左腕、右腕和全局按软件采样索引对齐，不是硬件曝光同步。任务准备早于录制，实际任务运动在录制启动后。

13:51:00.432467写入STOP；随后原录像进程退出，manifest仍为recording、ended_at为空，最后心跳13:51:00.353173。没有退出日志，不能确认退出原因，不能写成正常封口。153个原始MP4中前150个正常；各路第0050段缺少moov，未完成写盘。原文件和manifest保持原状。

恢复程序仅离线读取损坏文件的现存mdat，使用前一健康分段匹配的MPEG4解码配置，丢弃最后一个可能不完整VOP，再解码及重编码尾段。left/right/top分别恢复439/432/426帧；各自剩余2/9/15个时间索引标为缺失并用黑帧明确标注。共对应0.2/0.9/1.5秒，全部晚于13:50:44.8108最终回位图。程序没有生成或推测缺失现场内容；解码警告及校验结果保存在recovery.log，首尾恢复图已人工查看。原损坏文件哈希见 [恢复报告](RECORDING_RECOVERY.json)。

`recording_recovered/manifest.json`的completed仅表示离线派生文件完成，其artifact_kind明确标注为恢复副本，不代表原录像正常完成。前150个分段通过符号链接引用原文件，末3个为恢复重编码版本。原始采样缺帧/重复帧与尾部缺失均保留在逐帧状态中。

| 视角 | 新鲜帧 | 重复帧 | 缺失帧（含尾部） | 其中损坏尾部缺失 |
| --- | ---: | ---: | ---: | ---: |
| left | 30,287 | 89 | 65 | 2 |
| right | 30,292 | 75 | 74 | 9 |
| top | 30,319 | 45 | 77 | 15 |

同屏输出：H.264，1280×1456，10fps，30,441帧，50分44.1秒，603,055,793字节。保留原速等待、阶段目标变化和人工介入标记。恢复副本的153个MP4在合成期间逐帧解码，合成后所有30,441帧再次解码通过；这不等于三个损坏原始末段可解码。验证中的raw_mp4_count是派生输入分段数。

- [原始录像与时间索引](recording/index.html)
- [可播放恢复副本](recording_recovered/index.html)
- [三路合成视频](combined_video/book_extraction_trial02_full_3view.mp4)
- [合成manifest](combined_video/manifest.json) · [输入逐帧验证](raw_video_validation.json)
- [合成逐帧时间轴](combined_video/timeline.jsonl) · [阶段标签](video_phases.json)
- [首帧布局](combined_video/layout_preview.jpg) · [最后一帧](combined_video/last.jpg)
- [恢复脚本](recover_recording_tail.py) · [恢复日志](recovery.log)

恢复脚本按本次mp4v分段格式编写，不能无检查用于其他编码或不同采样结构。
