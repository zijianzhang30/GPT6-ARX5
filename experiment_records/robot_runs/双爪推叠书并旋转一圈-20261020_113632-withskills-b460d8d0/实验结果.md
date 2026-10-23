# 双爪推叠书并旋转一圈-20261020_113632-withskills-b460d8d0

实验 ID：`b460d8d0`  
实验时间：2026-10-20 11:36:32（Asia/Shanghai，采用本轮原始证据目录时间）  
归档时间：2026-10-20T12:27:41.841061+08:00

## 实验结果

**任务未完成。** CAN 和两臂 SDK 恢复成功；书堆未完成转移或 360° 旋转，两本书仍在原框内叠放，未抓取或抬书。两臂已通过两次原始参考回位核验，误差均在 2.5° 内（最终实测最大误差：左 1.64°、右 1.92°）。

停止原因：多次接近未产生有效推移，下探时实测高度响应不足，无法可靠确认爪尖与桌面间隙。详细过程和未完成项目保留在原记录中。

## 内容索引

- [完整实验记录](RUN_RECORD.md)
- [结构化结果](status.json)
- [原始任务](PROMPT.txt)
- [公开对话原始导出](DIALOGUE.md)
- [补全后的公开对话](公开对话.md)
- [实验结束答复](实验结束答复.md)
- [恢复阶段三路视频：21 个 MP4](recording_recovery02/)
- [后续执行及回位三路视频：63 个 MP4](recording_task03/)
- [视频检查结果](video_validation.json)
- [录像间隔记录](recording_gap.json)
- [控制日志](control/events.jsonl)
- [首次回位核验](return_check_1.json)、[第二次回位核验](return_check_2.json)
- [最终全局图](final_top.jpg)、[左腕图](final_left.jpg)、[右腕图](final_right.jpg)
- [执行计时与计数](execution_metrics.json)
- [使用的技能快照](skills/arx-r5-tabletop-tasks/SKILL.md)
- [归档清单](归档清单.json)、[SHA-256 校验清单](SHA256SUMS)

视频合计 84 个，三路每路原始片段累计 1661.7 秒。所有原片保持原样。两段录制之间有 35.482 秒间隔；首段因 SIGTERM 结束，续录通过 STOP 正常封存。已有视频验证覆盖帧数、FPS 和首末帧解码，不表示全帧解码。

本目录为完整证据副本，原始目录保留在 `/home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632`。归档过程中仅处理文件，未发送机器人控制命令。原始文件中的绝对路径及历史判断保留；此索引使用相对链接。技能文件为本次归档时的快照。
