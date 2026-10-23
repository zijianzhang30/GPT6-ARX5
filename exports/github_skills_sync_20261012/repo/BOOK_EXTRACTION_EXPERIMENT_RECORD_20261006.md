# 左臂抽取中间书本 — 2026-10-06

目标：左臂将中间书抽出约5厘米，其他书保持稳定；右臂仅辅助观察。三本书平叠在蓝色盒子上，中间书初始已经有突出边缘。

第1轮未通过：分段夹持后执行一次10毫米末端平移试拉，中间书有小幅随动，上方书也轻微移动，停止继续抽取。实际书本位移未可靠量测，未执行到5厘米。松爪撤离后书堆独立稳定，双臂受控回位两次核验通过；无运行故障、失能下落或观察到的双臂接触。

- [完整实验记录](analysis/book_extraction_trial01_20261006/RUN_RECORD.md)
- [关键三视角证据](analysis/book_extraction_trial01_20261006/EVIDENCE.md)
- [三路原始录像](analysis/book_extraction_trial01_20261006/recording)
- [公开对话](analysis/book_extraction_trial01_20261006/DIALOGUE.md)
- [资源与耗时](analysis/book_extraction_trial01_20261006/PERFORMANCE.md)
- [对应任务 skill](/home/tuojing/.codex/skills/arx-r5-tabletop-tasks/references/book-extraction.md)

视频合成和验证状态以本轮 status.json 与 RUN_RECORD.md 为准。

## 第2轮：右臂尝试抵住上书，随后放宽目标并改抓中段

本轮未验证抽出。初始要求中间书约5厘米、其他书稳定；之后用户放宽为抽出一些、允许其他书轻微随动。左臂先角部一次、再中段两次12毫米TCP指令试拉，均未建立可靠夹持和书本跟随证据，不能合计为书的36毫米位移。右臂初始可靠承力没有核实，后段仅辅助观察。此结果不证明拉力不足或任务不可能。

双臂已受控回位，两次原2.5°核验通过；期间人工拿书后按新清场继续回位，人工动作不计任务成功。无运行故障/失能下落或观察到的双臂接触。健康保持宿主保留。

三路录像末段未正常封口，原件保留并制作恢复副本；回位核验后尾部缺失左0.2秒、右0.9秒、全局1.5秒已逐路标黑。50分44.1秒同屏及153个派生分段全帧解码通过。执行51分48.290秒、20,310,185 tokens；归档恢复另计。skill已更新。

- [第2轮完整MD](analysis/book_extraction_trial02_20261006/RUN_RECORD.md)
- [第2轮三路合成视频](analysis/book_extraction_trial02_20261006/combined_video/book_extraction_trial02_full_3view.mp4)
- [证据](analysis/book_extraction_trial02_20261006/EVIDENCE.md) · [录像恢复说明](analysis/book_extraction_trial02_20261006/VIDEO_RECORD.md)
- [耗时与token](analysis/book_extraction_trial02_20261006/PERFORMANCE.md) · [公开对话](analysis/book_extraction_trial02_20261006/DIALOGUE.md)
