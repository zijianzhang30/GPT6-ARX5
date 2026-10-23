# 推两本叠书跨黑框并旋转整圈：实验目录核查

核查时间：2026-10-20T21:44:59+08:00（Asia/Shanghai）。

识别任务：

> Use both grippers to push the two stacked books from one black rectangle fully into the other, rotating the stack one full turn along the way. Keep the books stacked on the table without grasping or lifting them.

核查结果：6个原始任务目录，其中4个有执行记录、2个仅准备。另有1个归档副本目录及同名ZIP、1个兼容软链接、15:05轮内的2个回位子目录、分段录像和派生视频目录。副本、链接、回位与视频续段不重复计为新实验。

**路径已更新：10月18日的3个旋转推书目录已按用户要求恢复到 `/home/tuojing/` 下的原路径。**恢复完成时间：`2026-10-20T21:54:06.999000+08:00`。共633个文件，同一文件系统内移动，前后文件标识、大小及时间属性核验一致。此前回收站记录的删除时间为 `2026-10-20T21:24:49`；原回收站元数据已保存至[恢复记录](</home/tuojing/rotation_books_restore_20261020.json>)，对应回收站条目已清理。

## 1. 六个原始任务目录

| 时间 | 当前真实目录 | 记录阶段 | 主记录 |
|---|---|---|---|
| 2026-10-18 15:01（目录名1500） | [/home/tuojing/book_stack_push_20261018_1500](</home/tuojing/book_stack_push_20261018_1500>) | 仅准备、未下发动作 | [execution.md](</home/tuojing/book_stack_push_20261018_1500/execution.md>) |
| 2026-10-18 15:05 | [/home/tuojing/book_stack_push_20261018_1505](</home/tuojing/book_stack_push_20261018_1505>) | 已执行；记录结果未完成 | [execution.md](</home/tuojing/book_stack_push_20261018_1505/execution.md>) |
| 2026-10-18 15:55 | [/home/tuojing/book_stack_run_20261018_155501](</home/tuojing/book_stack_run_20261018_155501>) | 已执行；记录结果未完成 | [record.md](</home/tuojing/book_stack_run_20261018_155501/record.md>) |
| 2026-10-20 11:36 | [/home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632](</home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632>) | 已执行；记录结果未完成 | [RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632/RUN_RECORD.md>) |
| 2026-10-20 12:36 | [/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629>) | 已执行；记录结果未完成 | [RUN_RECORD.md](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629/RUN_RECORD.md>) |
| 2026-10-20 15:29 | [/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_152926](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_152926>) | 仅准备；15:34改成抽书，无动作、无录像 | [RUN_RECORD.md](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_152926/RUN_RECORD.md>) |

4份执行记录都将任务结果记为未完成；这是记录中的结论，本次没有重新逐帧复评所有视频。

## 2. 归档副本、兼容路径及临时准备

- 11:36归档目录：[/home/tuojing/robot_runs/双爪推叠书并旋转一圈-20261020_113632-withskills-b460d8d0](</home/tuojing/robot_runs/双爪推叠书并旋转一圈-20261020_113632-withskills-b460d8d0>)。
- 同次实验ZIP：[/home/tuojing/robot_runs/双爪推叠书并旋转一圈-20261020_113632-withskills-b460d8d0.zip](</home/tuojing/robot_runs/双爪推叠书并旋转一圈-20261020_113632-withskills-b460d8d0.zip>)。
- 原始目录与归档的对应依据：[/home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632/NAMED_ARCHIVE.json](</home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632/NAMED_ARCHIVE.json>)。归档记录记载复制核验通过，本次没有重新重算全部文件哈希。
- 12:36兼容软链接：[/home/tuojing/.codex/robot_runs/book_stack_turn_20261020_1236](</home/tuojing/.codex/robot_runs/book_stack_turn_20261020_1236>) → [/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629>)。
- 12:36历史中间名：`/home/tuojing/robot_runs/双爪推叠书并旋转一圈-20261020_123629-skills-第2次`；该名称当前不存在，已改为上述 `withskills_book_stack_turn_20261020_123629`。
- 临时准备目录：[/tmp/book_stack_new_preflight](</tmp/book_stack_new_preflight>)；4个文件与15:29轮 `preflight/` 逐字节相同，属于同次准备。

相关路径指针（文本文件，不是实验目录）：

- [/tmp/current_book_stack_trial_path](</tmp/current_book_stack_trial_path>) → `/home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632`
- [/tmp/current_book_stack_turn_run](</tmp/current_book_stack_turn_run>) → `/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_152926`

## 3. 回位、录像与合成视频的子目录

15:05轮的两次回位目录：

- [/home/tuojing/book_stack_push_20261018_1505/restore_initial](</home/tuojing/book_stack_push_20261018_1505/restore_initial>)；记录：[execution.md](</home/tuojing/book_stack_push_20261018_1505/restore_initial/execution.md>)
- [/home/tuojing/book_stack_push_20261018_1505/restore_initial_02](</home/tuojing/book_stack_push_20261018_1505/restore_initial_02>)；记录：[execution.md](</home/tuojing/book_stack_push_20261018_1505/restore_initial_02/execution.md>)

以下列出所有已确认原始目录及11:36归档内存放MP4的目录。文件数包含分段、回位和合成片，不是相机路数或实验次数。

| MP4所在目录 | 文件数 |
|---|---:|
| [/home/tuojing/book_stack_push_20261018_1500](</home/tuojing/book_stack_push_20261018_1500>) | 3 |
| [/home/tuojing/book_stack_push_20261018_1505](</home/tuojing/book_stack_push_20261018_1505>) | 3 |
| [/home/tuojing/book_stack_push_20261018_1505/video_segment_03](</home/tuojing/book_stack_push_20261018_1505/video_segment_03>) | 3 |
| [/home/tuojing/book_stack_push_20261018_1505/restore_initial_02/recordings](</home/tuojing/book_stack_push_20261018_1505/restore_initial_02/recordings>) | 3 |
| [/home/tuojing/book_stack_push_20261018_1505/video_segment_02](</home/tuojing/book_stack_push_20261018_1505/video_segment_02>) | 3 |
| [/home/tuojing/book_stack_push_20261018_1505/restore_initial/recordings](</home/tuojing/book_stack_push_20261018_1505/restore_initial/recordings>) | 3 |
| [/home/tuojing/book_stack_run_20261018_155501](</home/tuojing/book_stack_run_20261018_155501>) | 4 |
| [/home/tuojing/book_stack_run_20261018_155501/final_segment](</home/tuojing/book_stack_run_20261018_155501/final_segment>) | 3 |
| [/home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632/recording_recovery02](</home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632/recording_recovery02>) | 21 |
| [/home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632/recording_task03](</home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632/recording_task03>) | 63 |
| [/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629/recording02](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629/recording02>) | 93 |
| [/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629/three_view_exports](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629/three_view_exports>) | 2 |
| [/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629/recording](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629/recording>) | 66 |
| [/home/tuojing/robot_runs/双爪推叠书并旋转一圈-20261020_113632-withskills-b460d8d0/三视角视频](</home/tuojing/robot_runs/双爪推叠书并旋转一圈-20261020_113632-withskills-b460d8d0/三视角视频>) | 2 |
| [/home/tuojing/robot_runs/双爪推叠书并旋转一圈-20261020_113632-withskills-b460d8d0/recording_recovery02](</home/tuojing/robot_runs/双爪推叠书并旋转一圈-20261020_113632-withskills-b460d8d0/recording_recovery02>) | 21 |
| [/home/tuojing/robot_runs/双爪推叠书并旋转一圈-20261020_113632-withskills-b460d8d0/recording_task03](</home/tuojing/robot_runs/双爪推叠书并旋转一圈-20261020_113632-withskills-b460d8d0/recording_task03>) | 63 |

12:36轮三视角成片：

- [/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629/three_view_exports/three_views_full.mp4](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629/three_view_exports/three_views_full.mp4>)
- [/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629/three_view_exports/three_views_90s.mp4](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629/three_view_exports/three_views_90s.mp4>)

## 4. 路径历史与任务证据

### book_stack_push_20261018_1500

- 当前路径：[/home/tuojing/book_stack_push_20261018_1500](</home/tuojing/book_stack_push_20261018_1500>)
- 任务依据：[/home/tuojing/book_stack_push_20261018_1500/execution.md](</home/tuojing/book_stack_push_20261018_1500/execution.md>)，第 5 行。
- 原文：User task: Use both grippers to push two stacked books from one black rectangle completely into the other, rotating the stack 360 degrees along the way. Maintain table contact; no grasping or lifting. Retain three videos and Markdown records.
- 已恢复原路径：`/home/tuojing/book_stack_push_20261018_1500`（当前存在）。
- 历史回收站元数据已备份至[恢复记录](</home/tuojing/rotation_books_restore_20261020.json>)；原条目删除时间 `2026-10-20T21:24:49`，恢复后已清理对应 `.trashinfo`。

### book_stack_push_20261018_1505

- 当前路径：[/home/tuojing/book_stack_push_20261018_1505](</home/tuojing/book_stack_push_20261018_1505>)
- 任务依据：[/home/tuojing/book_stack_push_20261018_1505/execution.md](</home/tuojing/book_stack_push_20261018_1505/execution.md>)，第 3 行。
- 原文：任务：两只夹爪仅以推动接触，将两本叠放的书从右侧黑框完整移入左侧黑框，途中累计旋转360度，全程保持叠放及桌面支撑，不夹取、不抬升。
- 已恢复原路径：`/home/tuojing/book_stack_push_20261018_1505`（当前存在）。
- 历史回收站元数据已备份至[恢复记录](</home/tuojing/rotation_books_restore_20261020.json>)；原条目删除时间 `2026-10-20T21:24:49`，恢复后已清理对应 `.trashinfo`。

### book_stack_run_20261018_155501

- 当前路径：[/home/tuojing/book_stack_run_20261018_155501](</home/tuojing/book_stack_run_20261018_155501>)
- 任务依据：[/home/tuojing/book_stack_run_20261018_155501/record.md](</home/tuojing/book_stack_run_20261018_155501/record.md>)，第 7 行。
- 原文：Use both grippers to push the two stacked books fully from one black rectangle into the other, rotating the stack one full turn along the way. Do not grasp or lift the books. Retain three video streams and Markdown records.
- 已恢复原路径：`/home/tuojing/book_stack_run_20261018_155501`（当前存在）。
- 历史回收站元数据已备份至[恢复记录](</home/tuojing/rotation_books_restore_20261020.json>)；原条目删除时间 `2026-10-20T21:24:49`，恢复后已清理对应 `.trashinfo`。

### book_stack_push_turn_20261020_113632

- 当前路径：[/home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632](</home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632>)
- 任务依据：[/home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632/PROMPT.txt](</home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632/PROMPT.txt>)，第 1 行。
- 原文：Use both grippers to push the two stacked books from one black rectangle fully into the other, rotating the stack one full turn along the way. Keep the books stacked on the table without grasping or lifting them.

### withskills_book_stack_turn_20261020_123629

- 当前路径：[/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629>)
- 任务依据：[/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629/task_prompt.md](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629/task_prompt.md>)，第 3 行。
- 原文：User instruction: Use both grippers to push the two stacked books from one black rectangle fully into the other, rotating the stack one full turn along the way. Keep the books stacked on the table without grasping or lifting them. During execution, retain three video streams and Markdown records.

### withskills_book_stack_turn_20261020_152926

- 当前路径：[/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_152926](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_152926>)
- 任务依据：[/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_152926/task_prompt.md](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_152926/task_prompt.md>)，第 4 行。
- 原文：Use both grippers to push the two stacked books from one black rectangle fully into the other, rotating the stack one full turn along the way. Keep the books stacked on the table without grasping or lifting them.

## 5. 已核对但不属于整圈旋转任务的近似目录

这些目录可能含“书”“旋转”或回位、合成模板引用；按原始任务要求排除。

| 目录 | 排除理由 |
|---|---|
| [/home/tuojing/.local/share/Trash/files/book_push_20261018_0318](</home/tuojing/.local/share/Trash/files/book_push_20261018_0318>) | 普通推书入单黑框，无整圈旋转要求 |
| [/home/tuojing/.local/share/Trash/files/book_push_20261018_105627](</home/tuojing/.local/share/Trash/files/book_push_20261018_105627>) | 普通推书入单黑框，无整圈旋转要求 |
| [/home/tuojing/.local/share/Trash/files/book_stack_push_20261018](</home/tuojing/.local/share/Trash/files/book_stack_push_20261018>) | 普通推书入单黑框，无整圈旋转要求 |
| [/home/tuojing/.local/share/Trash/files/book_stack_push_20261018_133814](</home/tuojing/.local/share/Trash/files/book_stack_push_20261018_133814>) | 普通推书入单黑框，无整圈旋转要求 |
| [/home/tuojing/.local/share/Trash/files/book_stack_push_20261018_134347](</home/tuojing/.local/share/Trash/files/book_stack_push_20261018_134347>) | 普通推书入单黑框，无整圈旋转要求 |
| [/home/tuojing/.local/share/Trash/files/book_stack_push_20261018_1405](</home/tuojing/.local/share/Trash/files/book_stack_push_20261018_1405>) | 普通推书入单黑框，无整圈旋转要求 |
| [/home/tuojing/.local/share/Trash/files/book_stack_push_20261018_140735](</home/tuojing/.local/share/Trash/files/book_stack_push_20261018_140735>) | 普通推书入单黑框，无整圈旋转要求 |
| [/home/tuojing/arx_r5_control/experiments/book_stack_push_20261017_234402](</home/tuojing/arx_r5_control/experiments/book_stack_push_20261017_234402>) | Pure cooperative push into one outline; no full-turn requirement. |
| [/home/tuojing/arx_r5_control/experiments/book_stack_push_20261017_235904](</home/tuojing/arx_r5_control/experiments/book_stack_push_20261017_235904>) | Pure cooperative push into one outline; small orientation adjustment during execution is not a full-turn task. |
| [/home/tuojing/arx_r5_control/experiments/book_stack_push_20261018_110748](</home/tuojing/arx_r5_control/experiments/book_stack_push_20261018_110748>) | Three-book push into one outline; no full-turn requirement. Later manual book rotation is not task execution. |
| [/home/tuojing/Documents/book_push_20261018_104906](</home/tuojing/Documents/book_push_20261018_104906>) | 推两本书入单黑框，无整圈旋转要求 |
| [/home/tuojing/robot_runs/book_stack_return_20261018_135236](</home/tuojing/robot_runs/book_stack_return_20261018_135236>) | 属于13:43普通推书轮的回位或交接等待，非整圈旋转任务 |
| [/home/tuojing/robot_runs/book_stack_return_20261018_143834](</home/tuojing/robot_runs/book_stack_return_20261018_143834>) | 属于13:43普通推书轮的回位或交接等待，非整圈旋转任务 |
| [/home/tuojing/robot_runs/book_stack_return_20261018_135236/recheck_20261018_140540](</home/tuojing/robot_runs/book_stack_return_20261018_135236/recheck_20261018_140540>) | 属于13:43普通推书轮的回位或交接等待，非整圈旋转任务 |
| [/home/tuojing/robot_runs/withskills_book_extraction_20261020_135443](</home/tuojing/robot_runs/withskills_book_extraction_20261020_135443>) | Book extraction, not full-turn pushing. Turn-task mentions occur as video-layout source references or explicit task rejection. |
| [/home/tuojing/robot_runs/withskills_book_extraction_20261020_153409](</home/tuojing/robot_runs/withskills_book_extraction_20261020_153409>) | Book extraction, not full-turn pushing. Turn-task mentions occur as video-layout source references or explicit task rejection. |
| [/home/tuojing/robot_runs/withskills_book_extraction_20261020_161503](</home/tuojing/robot_runs/withskills_book_extraction_20261020_161503>) | Book extraction, not full-turn pushing. Turn-task mentions occur as video-layout source references or explicit task rejection. |

`book_stack_push_20261018_140735` 虽记录推入框成功，但没有整圈旋转要求，不能据此判定本任务成功。

## 6. 核查范围与方法

核查 `/home/tuojing/robot_runs`、工程 `analysis` / `experiments`、工程根报告与旧导出包根清单、`.codex/robot_runs` / `.codex/outputs`、主目录与Documents、回收站book目录以及相关 `/tmp` 准备材料。按文件名、任务原文和结果记录交叉核对；未访问云端、技能内容、应用缓存或会话历史。其他任务目录仅引用推书视频模板的情况不计作新实验。容器存储层不在此任务结果盘点范围内。

本清单已同步到恢复后的路径；其他普通推书目录仍按原核查状态列入排除清单。

结构化索引：[/home/tuojing/rotation_book_experiment_paths_20261020.json](</home/tuojing/rotation_book_experiment_paths_20261020.json>)
