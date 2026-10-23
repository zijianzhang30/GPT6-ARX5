# 具身实验结果路径索引（主归档之外）

核查时间：2026-10-20T19:42:31+08:00（Asia/Shanghai）。

范围：本机已确认的历史实验目录、报告、导出包和原始采集。不展开 `/home/tuojing/robot_runs` 主归档；仅列出相关软链接的目标。未访问云端、技能内容或缓存；未执行机器人控制操作，未移动或修改原始结果。

目录数不是实验成功次数。记录中包含失败、取消、准备及回位过程；MP4 文件数包含分段录像和合成片。按文件元数据整理，未重新解码或验证所有视频。目录统计不跟随软链接，且不将嵌入技能与软件缓存计入分析目录大小；各层级及导出副本有重叠，大小不可直接相加。

## 1. 主要保存位置

| 路径 | 保存内容 |
|---|---|
| [/home/tuojing/arx_r5_control/analysis](</home/tuojing/arx_r5_control/analysis>) | 历史任务执行、视频、截图及分析；110 个归类为任务执行的顶级目录，另有诊断、控制会话和汇总目录。 |
| [/home/tuojing/arx_r5_control/experiments](</home/tuojing/arx_r5_control/experiments>) | 4 个推书、扫块实验目录。 |
| [/home/tuojing/arx_r5_control/exports](</home/tuojing/arx_r5_control/exports>) | 系列报告包、ZIP、副本、90 秒成片及本地发布整理稿。 |
| [/home/tuojing/arx_r5_control/recordings](</home/tuojing/arx_r5_control/recordings>) | 11 个早期逐帧采集目录，JPG 和 JSON/JSONL；不是三路 MP4。 |
| [/home/tuojing/arx_r5_control](</home/tuojing/arx_r5_control>) 下的 `*_EXPERIMENT_RECORD_*.md` | 单项实验报告，另有两份系列总报告。 |
| [/home/tuojing](</home/tuojing>) 下的 6 个 `book*` 目录 | 2026-10-18 分散保存的推书实验及回位证据。 |
| [/home/tuojing/Documents/book_push_20261018_104906](</home/tuojing/Documents/book_push_20261018_104906>) | 单独保存的一次推书实验。 |
| [/home/tuojing/.codex/outputs/sweep_live_20261018_1638](</home/tuojing/.codex/outputs/sweep_live_20261018_1638>) | 2026-10-18 扫两个蓝块记录。 |
| [/home/tuojing/.codex/robot_runs/withskills_blue_blocks_sweeping_20261020_175900](</home/tuojing/.codex/robot_runs/withskills_blue_blocks_sweeping_20261020_175900>) | 2026-10-20 扫三个蓝块记录及三视角成片。 |

## 2. 系列总报告入口

- [/home/tuojing/arx_r5_control/REAL_ROBOT_EXPERIMENT_REPORT_20261006.md](</home/tuojing/arx_r5_control/REAL_ROBOT_EXPERIMENT_REPORT_20261006.md>)
- [/home/tuojing/arx_r5_control/REAL_ROBOT_EXPERIMENT_REPORT_20261007.md](</home/tuojing/arx_r5_control/REAL_ROBOT_EXPERIMENT_REPORT_20261007.md>)
- [/home/tuojing/arx_r5_control/REAL_ROBOT_EXPERIMENT_REPORT_20261006.html](</home/tuojing/arx_r5_control/REAL_ROBOT_EXPERIMENT_REPORT_20261006.html>)
- [/home/tuojing/arx_r5_control/REAL_ROBOT_EXPERIMENT_REPORT_20261007.html](</home/tuojing/arx_r5_control/REAL_ROBOT_EXPERIMENT_REPORT_20261007.html>)
- [/home/tuojing/arx_r5_control/analysis/real_robot_report_20261006/BUNDLE_DELIVERY.md](</home/tuojing/arx_r5_control/analysis/real_robot_report_20261006/BUNDLE_DELIVERY.md>)
- [/home/tuojing/arx_r5_control/analysis/real_robot_report_20261007/BUNDLE_DELIVERY.md](</home/tuojing/arx_r5_control/analysis/real_robot_report_20261007/BUNDLE_DELIVERY.md>)
- [/home/tuojing/arx_r5_control/exports/LATEST_BUNDLE.md](</home/tuojing/arx_r5_control/exports/LATEST_BUNDLE.md>)

## 3. `analysis` / `experiments` 的任务系列

以下分组列出实际目录。各系列名称按目录及记录归类；文件数量与结果判定分开。

### 推黑板擦入框

- [/home/tuojing/arx_r5_control/analysis/blackboard_eraser_push_trial01_20261011](</home/tuojing/arx_r5_control/analysis/blackboard_eraser_push_trial01_20261011>) — 任务执行记录（含未完成尝试）；MP4 141 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/blackboard_eraser_push_trial01_20261011/EXPERIMENT_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/blackboard_eraser_push_trial02_20261014](</home/tuojing/arx_r5_control/analysis/blackboard_eraser_push_trial02_20261014>) — 任务执行记录（含未完成尝试）；MP4 3 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/blackboard_eraser_push_trial02_20261014/EXPERIMENT_RECORD.md>)

### 擦黑板

- [/home/tuojing/arx_r5_control/analysis/blackboard_wiping_trial01_20261006](</home/tuojing/arx_r5_control/analysis/blackboard_wiping_trial01_20261006>) — 任务执行记录（含未完成尝试）；MP4 73 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/blackboard_wiping_trial01_20261006/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/blackboard_wiping_trial02_20261006](</home/tuojing/arx_r5_control/analysis/blackboard_wiping_trial02_20261006>) — 任务执行记录（含未完成尝试）；MP4 94 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/blackboard_wiping_trial02_20261006/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/blackboard_wiping_trial03_20261006](</home/tuojing/arx_r5_control/analysis/blackboard_wiping_trial03_20261006>) — 任务执行记录（含未完成尝试）；MP4 79 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/blackboard_wiping_trial03_20261006/RUN_RECORD.md>)

### 推蓝块入三角区域

- [/home/tuojing/arx_r5_control/analysis/blue_block_triangle_push_trial01_20261006](</home/tuojing/arx_r5_control/analysis/blue_block_triangle_push_trial01_20261006>) — 任务执行记录（含未完成尝试）；MP4 121 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/blue_block_triangle_push_trial01_20261006/RUN_RECORD.md>)

### 扫蓝色方块

- [/home/tuojing/arx_r5_control/analysis/blue_blocks_sweeping_trial01_20261006](</home/tuojing/arx_r5_control/analysis/blue_blocks_sweeping_trial01_20261006>) — 任务执行记录（含未完成尝试）；MP4 70 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/blue_blocks_sweeping_trial01_20261006/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/blue_blocks_sweeping_trial02_20261011](</home/tuojing/arx_r5_control/analysis/blue_blocks_sweeping_trial02_20261011>) — 任务执行记录（含未完成尝试）；MP4 93 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/blue_blocks_sweeping_trial02_20261011/EXPERIMENT_RECORD.md>)

### 旋螺栓

- [/home/tuojing/arx_r5_control/analysis/bolt_screwing_trial01_20261005](</home/tuojing/arx_r5_control/analysis/bolt_screwing_trial01_20261005>) — 任务执行记录（含未完成尝试）；MP4 70 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/bolt_screwing_trial01_20261005/RUN_RECORD.md>)

### 旋出螺栓

- [/home/tuojing/arx_r5_control/analysis/bolt_unscrewing_trial01_20261011](</home/tuojing/arx_r5_control/analysis/bolt_unscrewing_trial01_20261011>) — 任务执行记录（含未完成尝试）；MP4 132 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/bolt_unscrewing_trial01_20261011/RUN_RECORD.md>)

### 抽书

- [/home/tuojing/arx_r5_control/analysis/book_extraction_trial01_20261006](</home/tuojing/arx_r5_control/analysis/book_extraction_trial01_20261006>) — 任务执行记录（含未完成尝试）；MP4 67 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/book_extraction_trial01_20261006/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/book_extraction_trial02_20261006](</home/tuojing/arx_r5_control/analysis/book_extraction_trial02_20261006>) — 任务执行记录（含未完成尝试）；MP4 157 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/book_extraction_trial02_20261006/RUN_RECORD.md>)

### 双爪推叠书入框

- [/home/tuojing/arx_r5_control/experiments/book_stack_push_20261017_234402](</home/tuojing/arx_r5_control/experiments/book_stack_push_20261017_234402>) — 任务执行记录（含未完成尝试）；MP4 12 个；[TASK.md](</home/tuojing/arx_r5_control/experiments/book_stack_push_20261017_234402/TASK.md>)
- [/home/tuojing/arx_r5_control/experiments/book_stack_push_20261017_235904](</home/tuojing/arx_r5_control/experiments/book_stack_push_20261017_235904>) — 任务执行记录（含未完成尝试）；MP4 5 个；[TASK.md](</home/tuojing/arx_r5_control/experiments/book_stack_push_20261017_235904/TASK.md>)
- [/home/tuojing/arx_r5_control/experiments/book_stack_push_20261018_110748](</home/tuojing/arx_r5_control/experiments/book_stack_push_20261018_110748>) — 任务执行记录（含未完成尝试）；MP4 15 个；[README.md](</home/tuojing/arx_r5_control/experiments/book_stack_push_20261018_110748/README.md>)

### 推叠书并旋转一圈

- [/home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632](</home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632>) — 任务执行记录（含未完成尝试）；MP4 84 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/book_stack_push_turn_20261020_113632/RUN_RECORD.md>)

### 双臂旋瓶盖

- [/home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial01_20261005](</home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial01_20261005>) — 任务执行记录（含未完成尝试）；MP4 16 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial01_20261005/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial02_20261005](</home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial02_20261005>) — 任务执行记录（含未完成尝试）；MP4 84 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial02_20261005/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial03_20261005](</home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial03_20261005>) — 任务执行记录（含未完成尝试）；MP4 61 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial03_20261005/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial04_20261014](</home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial04_20261014>) — 任务执行记录（含未完成尝试）；MP4 30 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial04_20261014/EXPERIMENT_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial05_20261014](</home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial05_20261014>) — 任务执行记录（含未完成尝试）；MP4 51 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/bottle_unscrewing_trial05_20261014/EXPERIMENT_RECORD.md>)

### 刷子扫块

- [/home/tuojing/arx_r5_control/analysis/brush_sweep_live_20261017_223120](</home/tuojing/arx_r5_control/analysis/brush_sweep_live_20261017_223120>) — 任务执行记录（含未完成尝试）；MP4 40 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/brush_sweep_live_20261017_223120/RUN_RECORD.md>)

### 充电器插接

- [/home/tuojing/arx_r5_control/analysis/charger_trial01_20261001](</home/tuojing/arx_r5_control/analysis/charger_trial01_20261001>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/charger_trial01_20261001/status.json>)
- [/home/tuojing/arx_r5_control/analysis/charger_trial02_20261001](</home/tuojing/arx_r5_control/analysis/charger_trial02_20261001>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/charger_trial02_20261001/status.json>)
- [/home/tuojing/arx_r5_control/analysis/charger_trial03_20261001](</home/tuojing/arx_r5_control/analysis/charger_trial03_20261001>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/charger_trial03_20261001/status.json>)
- [/home/tuojing/arx_r5_control/analysis/charger_trial04_20261001](</home/tuojing/arx_r5_control/analysis/charger_trial04_20261001>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/charger_trial04_20261001/status.json>)
- [/home/tuojing/arx_r5_control/analysis/charger_trial05_20261001](</home/tuojing/arx_r5_control/analysis/charger_trial05_20261001>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/charger_trial05_20261001/status.json>)
- [/home/tuojing/arx_r5_control/analysis/charger_trial06_20261002](</home/tuojing/arx_r5_control/analysis/charger_trial06_20261002>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/charger_trial06_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/charger_trial07_20261002](</home/tuojing/arx_r5_control/analysis/charger_trial07_20261002>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/charger_trial07_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/charger_trial08_20261002](</home/tuojing/arx_r5_control/analysis/charger_trial08_20261002>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/charger_trial08_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/charger_trial09_20261002](</home/tuojing/arx_r5_control/analysis/charger_trial09_20261002>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/charger_trial09_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/charger_trial10_20261002](</home/tuojing/arx_r5_control/analysis/charger_trial10_20261002>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/charger_trial10_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/charger_trial11_20261005](</home/tuojing/arx_r5_control/analysis/charger_trial11_20261005>) — 任务执行记录（含未完成尝试）；MP4 61 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/charger_trial11_20261005/RUN_RECORD.md>)

### 充电器对准插接

- [/home/tuojing/arx_r5_control/analysis/charger_alignment_trial01_20261016](</home/tuojing/arx_r5_control/analysis/charger_alignment_trial01_20261016>) — 任务执行记录（含未完成尝试）；MP4 99 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/charger_alignment_trial01_20261016/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/charger_alignment_trial02_20261016](</home/tuojing/arx_r5_control/analysis/charger_alignment_trial02_20261016>) — 任务执行记录（含未完成尝试）；MP4 124 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/charger_alignment_trial02_20261016/RUN_RECORD.md>)

### 仅插充电器

- [/home/tuojing/arx_r5_control/analysis/charger_insert_only_trial01_20261005](</home/tuojing/arx_r5_control/analysis/charger_insert_only_trial01_20261005>) — 任务执行记录（含未完成尝试）；MP4 319 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/charger_insert_only_trial01_20261005/RUN_RECORD.md>)

### charger_insertion

- [/home/tuojing/arx_r5_control/analysis/charger_insertion_trials_20261001](</home/tuojing/arx_r5_control/analysis/charger_insertion_trials_20261001>) — 任务系列索引；MP4 0 个

### 叠杯

- [/home/tuojing/arx_r5_control/analysis/cups_resume_20261001_1740](</home/tuojing/arx_r5_control/analysis/cups_resume_20261001_1740>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/cups_resume_20261001_1740/status.json>)
- [/home/tuojing/arx_r5_control/analysis/cups_task_20261001](</home/tuojing/arx_r5_control/analysis/cups_task_20261001>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/cups_task_20261001/status.json>)
- [/home/tuojing/arx_r5_control/analysis/cups_trial02_20261001](</home/tuojing/arx_r5_control/analysis/cups_trial02_20261001>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/cups_trial02_20261001/status.json>)
- [/home/tuojing/arx_r5_control/analysis/cups_trial03_20261001](</home/tuojing/arx_r5_control/analysis/cups_trial03_20261001>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/cups_trial03_20261001/status.json>)
- [/home/tuojing/arx_r5_control/analysis/cups_trial04_20261001](</home/tuojing/arx_r5_control/analysis/cups_trial04_20261001>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/cups_trial04_20261001/status.json>)
- [/home/tuojing/arx_r5_control/analysis/cups_trial05_20261001](</home/tuojing/arx_r5_control/analysis/cups_trial05_20261001>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/cups_trial05_20261001/status.json>)
- [/home/tuojing/arx_r5_control/analysis/cups_trial06_20261007](</home/tuojing/arx_r5_control/analysis/cups_trial06_20261007>) — 任务执行记录（含未完成尝试）；MP4 363 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/cups_trial06_20261007/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/cups_trial07_20261007](</home/tuojing/arx_r5_control/analysis/cups_trial07_20261007>) — 任务执行记录（含未完成尝试）；MP4 127 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/cups_trial07_20261007/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/cups_trials_20261001](</home/tuojing/arx_r5_control/analysis/cups_trials_20261001>) — 任务系列索引；MP4 0 个

### 抽屉推拉

- [/home/tuojing/arx_r5_control/analysis/drawer_push_pull_trial01_20261005](</home/tuojing/arx_r5_control/analysis/drawer_push_pull_trial01_20261005>) — 任务执行记录（含未完成尝试）；MP4 37 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/drawer_push_pull_trial01_20261005/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/drawer_push_pull_trial02_20261005](</home/tuojing/arx_r5_control/analysis/drawer_push_pull_trial02_20261005>) — 任务执行记录（含未完成尝试）；MP4 57 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/drawer_push_pull_trial02_20261005/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/drawer_push_pull_trial03_20261017](</home/tuojing/arx_r5_control/analysis/drawer_push_pull_trial03_20261017>) — 任务执行记录（含未完成尝试）；MP4 79 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/drawer_push_pull_trial03_20261017/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/drawer_push_pull_trial04_20261017](</home/tuojing/arx_r5_control/analysis/drawer_push_pull_trial04_20261017>) — 任务执行记录（含未完成尝试）；MP4 37 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/drawer_push_pull_trial04_20261017/RUN_RECORD.md>)

### 固定瓶左爪旋盖

- [/home/tuojing/arx_r5_control/analysis/fixed_bottle_left_cap_trial01_20261005](</home/tuojing/arx_r5_control/analysis/fixed_bottle_left_cap_trial01_20261005>) — 任务执行记录（含未完成尝试）；MP4 91 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/fixed_bottle_left_cap_trial01_20261005/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/fixed_bottle_left_cap_trial02_20261005](</home/tuojing/arx_r5_control/analysis/fixed_bottle_left_cap_trial02_20261005>) — 任务执行记录（含未完成尝试）；MP4 43 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/fixed_bottle_left_cap_trial02_20261005/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/fixed_bottle_left_cap_trial03_20261006](</home/tuojing/arx_r5_control/analysis/fixed_bottle_left_cap_trial03_20261006>) — 任务执行记录（含未完成尝试）；MP4 79 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/fixed_bottle_left_cap_trial03_20261006/RUN_RECORD.md>)

### 插花

- [/home/tuojing/arx_r5_control/analysis/flower_trial01_20261002](</home/tuojing/arx_r5_control/analysis/flower_trial01_20261002>) — 任务执行记录（含未完成尝试）；MP4 60 个；[status.json](</home/tuojing/arx_r5_control/analysis/flower_trial01_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/flower_trial02_20261002](</home/tuojing/arx_r5_control/analysis/flower_trial02_20261002>) — 任务执行记录（含未完成尝试）；MP4 66 个；[status.json](</home/tuojing/arx_r5_control/analysis/flower_trial02_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/flower_trial03_20261002](</home/tuojing/arx_r5_control/analysis/flower_trial03_20261002>) — 任务执行记录（含未完成尝试）；MP4 99 个；[status.json](</home/tuojing/arx_r5_control/analysis/flower_trial03_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/flower_trial04_20261003](</home/tuojing/arx_r5_control/analysis/flower_trial04_20261003>) — 任务执行记录（含未完成尝试）；MP4 537 个；[status.json](</home/tuojing/arx_r5_control/analysis/flower_trial04_20261003/status.json>)
- [/home/tuojing/arx_r5_control/analysis/flower_trial05_20261003](</home/tuojing/arx_r5_control/analysis/flower_trial05_20261003>) — 任务执行记录（含未完成尝试）；MP4 441 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/flower_trial05_20261003/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/flower_trial06_20261007](</home/tuojing/arx_r5_control/analysis/flower_trial06_20261007>) — 任务执行记录（含未完成尝试）；MP4 43 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/flower_trial06_20261007/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/flower_trial07_20261010](</home/tuojing/arx_r5_control/analysis/flower_trial07_20261010>) — 任务执行记录（含未完成尝试）；MP4 93 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/flower_trial07_20261010/RUN_RECORD.md>)

### 转移插花

- [/home/tuojing/arx_r5_control/analysis/flower_transfer_trial01_20261016](</home/tuojing/arx_r5_control/analysis/flower_transfer_trial01_20261016>) — 任务执行记录（含未完成尝试）；MP4 61 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/flower_transfer_trial01_20261016/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/flower_transfer_trial02_20261017](</home/tuojing/arx_r5_control/analysis/flower_transfer_trial02_20261017>) — 任务执行记录（含未完成尝试）；MP4 61 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/flower_transfer_trial02_20261017/RUN_RECORD.md>)

### 挂帽

- [/home/tuojing/arx_r5_control/analysis/hat_hanging_trial01_20261003](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial01_20261003>) — 任务执行记录（含未完成尝试）；MP4 258 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial01_20261003/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/hat_hanging_trial02_20261003](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial02_20261003>) — 任务执行记录（含未完成尝试）；MP4 168 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial02_20261003/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/hat_hanging_trial03_20261003](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial03_20261003>) — 任务执行记录（含未完成尝试）；MP4 108 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial03_20261003/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/hat_hanging_trial04_20261007](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial04_20261007>) — 任务执行记录（含未完成尝试）；MP4 49 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial04_20261007/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/hat_hanging_trial05_20261010](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial05_20261010>) — 任务执行记录（含未完成尝试）；MP4 33 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial05_20261010/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/hat_hanging_trial06_20261010](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial06_20261010>) — 任务执行记录（含未完成尝试）；MP4 3 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial06_20261010/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/hat_hanging_trial07_20261010](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial07_20261010>) — 任务执行记录（含未完成尝试）；MP4 3 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial07_20261010/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/hat_hanging_trial08_20261010](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial08_20261010>) — 任务执行记录（含未完成尝试）；MP4 15 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial08_20261010/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/hat_hanging_trial09_20261010](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial09_20261010>) — 任务执行记录（含未完成尝试）；MP4 3 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial09_20261010/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/hat_hanging_trial10_20261011](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial10_20261011>) — 任务执行记录（含未完成尝试）；MP4 21 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial10_20261011/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/hat_hanging_trial11_20261011](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial11_20261011>) — 任务执行记录（含未完成尝试）；MP4 12 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial11_20261011/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/hat_hanging_trial12_20261011](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial12_20261011>) — 任务执行记录（含未完成尝试）；MP4 90 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial12_20261011/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/hat_hanging_trial13_20261011](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial13_20261011>) — 任务执行记录（含未完成尝试）；MP4 222 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/hat_hanging_trial13_20261011/RUN_RECORD.md>)

### 包装果冻抓放

- [/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012](</home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012>) — 任务执行记录（含未完成尝试）；MP4 69 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/EXPERIMENT_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial02_20261012](</home/tuojing/arx_r5_control/analysis/jelly_grasp_trial02_20261012>) — 任务执行记录（含未完成尝试）；MP4 69 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/jelly_grasp_trial02_20261012/EXPERIMENT_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial03_20261012](</home/tuojing/arx_r5_control/analysis/jelly_grasp_trial03_20261012>) — 任务执行记录（含未完成尝试）；MP4 150 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/jelly_grasp_trial03_20261012/EXPERIMENT_RECORD.md>)

### 包装果冻杯抓放

- [/home/tuojing/arx_r5_control/analysis/jelly_packaged_cup_trial01_20261014](</home/tuojing/arx_r5_control/analysis/jelly_packaged_cup_trial01_20261014>) — 任务执行记录（含未完成尝试）；MP4 54 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/jelly_packaged_cup_trial01_20261014/EXPERIMENT_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/jelly_packaged_cup_trial02_20261014](</home/tuojing/arx_r5_control/analysis/jelly_packaged_cup_trial02_20261014>) — 任务执行记录（含未完成尝试）；MP4 141 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/jelly_packaged_cup_trial02_20261014/EXPERIMENT_RECORD.md>)

### 果冻抓放

- [/home/tuojing/arx_r5_control/analysis/jelly_pick_place_trial01_20261005](</home/tuojing/arx_r5_control/analysis/jelly_pick_place_trial01_20261005>) — 任务执行记录（含未完成尝试）；MP4 46 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/jelly_pick_place_trial01_20261005/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/jelly_pick_place_trial01_20261016](</home/tuojing/arx_r5_control/analysis/jelly_pick_place_trial01_20261016>) — 任务执行记录（含未完成尝试）；MP4 55 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/jelly_pick_place_trial01_20261016/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/jelly_pick_place_trial02_20261005](</home/tuojing/arx_r5_control/analysis/jelly_pick_place_trial02_20261005>) — 任务执行记录（含未完成尝试）；MP4 43 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/jelly_pick_place_trial02_20261005/RUN_RECORD.md>)

### 左爪旋瓶盖

- [/home/tuojing/arx_r5_control/analysis/left_cap_unscrewing_trial01_20261014](</home/tuojing/arx_r5_control/analysis/left_cap_unscrewing_trial01_20261014>) — 任务执行记录（含未完成尝试）；MP4 18 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/left_cap_unscrewing_trial01_20261014/EXPERIMENT_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/left_cap_unscrewing_trial02_20261014](</home/tuojing/arx_r5_control/analysis/left_cap_unscrewing_trial02_20261014>) — 任务执行记录（含未完成尝试）；MP4 45 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/left_cap_unscrewing_trial02_20261014/EXPERIMENT_RECORD.md>)

### 橘子抓放

- [/home/tuojing/arx_r5_control/analysis/orange_pick_place_trial01_20261005](</home/tuojing/arx_r5_control/analysis/orange_pick_place_trial01_20261005>) — 任务执行记录（含未完成尝试）；MP4 49 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/orange_pick_place_trial01_20261005/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/orange_pick_place_trial02_20261011](</home/tuojing/arx_r5_control/analysis/orange_pick_place_trial02_20261011>) — 任务执行记录（含未完成尝试）；MP4 99 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/orange_pick_place_trial02_20261011/RUN_RECORD.md>)

### 杯间倒珍珠

- [/home/tuojing/arx_r5_control/analysis/pearl_pouring_trial01_20261005](</home/tuojing/arx_r5_control/analysis/pearl_pouring_trial01_20261005>) — 任务执行记录（含未完成尝试）；MP4 106 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/pearl_pouring_trial01_20261005/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/pearl_pouring_trial02_20261011](</home/tuojing/arx_r5_control/analysis/pearl_pouring_trial02_20261011>) — 任务执行记录（含未完成尝试）；MP4 87 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/pearl_pouring_trial02_20261011/RUN_RECORD.md>)

### 插笔

- [/home/tuojing/arx_r5_control/analysis/pen_insertion_trial01_20261002](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial01_20261002>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial01_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/pen_insertion_trial02_20261002](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial02_20261002>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial02_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/pen_insertion_trial03_20261002](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial03_20261002>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial03_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/pen_insertion_trial04_20261002](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial04_20261002>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial04_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/pen_insertion_trial05_20261002](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial05_20261002>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial05_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/pen_insertion_trial06_20261002](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial06_20261002>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial06_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/pen_insertion_trial07_20261002](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial07_20261002>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial07_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/pen_insertion_trial08_20261002](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial08_20261002>) — 任务执行记录（含未完成尝试）；MP4 0 个；[status.json](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial08_20261002/status.json>)
- [/home/tuojing/arx_r5_control/analysis/pen_insertion_trial09_20261007](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial09_20261007>) — 任务执行记录（含未完成尝试）；MP4 67 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial09_20261007/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/pen_insertion_trial10_20261016](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial10_20261016>) — 任务执行记录（含未完成尝试）；MP4 52 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/pen_insertion_trial10_20261016/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/pen_insertion_trials_20261002](</home/tuojing/arx_r5_control/analysis/pen_insertion_trials_20261002>) — 任务系列索引；MP4 0 个

### 拔笔帽

- [/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial01_20261003](</home/tuojing/arx_r5_control/analysis/pen_uncapping_trial01_20261003>) — 任务执行记录（含未完成尝试）；MP4 261 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/pen_uncapping_trial01_20261003/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial02_20261003](</home/tuojing/arx_r5_control/analysis/pen_uncapping_trial02_20261003>) — 任务执行记录（含未完成尝试）；MP4 21 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/pen_uncapping_trial02_20261003/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial03_20261003](</home/tuojing/arx_r5_control/analysis/pen_uncapping_trial03_20261003>) — 任务执行记录（含未完成尝试）；MP4 12 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/pen_uncapping_trial03_20261003/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial04_20261003](</home/tuojing/arx_r5_control/analysis/pen_uncapping_trial04_20261003>) — 任务执行记录（含未完成尝试）；MP4 209 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/pen_uncapping_trial04_20261003/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011](</home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011>) — 任务执行记录（含未完成尝试）；MP4 57 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/pen_uncapping_trial05_20261011/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/pen_uncapping_trial06_20261011](</home/tuojing/arx_r5_control/analysis/pen_uncapping_trial06_20261011>) — 任务执行记录（含未完成尝试）；MP4 252 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/pen_uncapping_trial06_20261011/RUN_RECORD.md>)

### 双工具扫方块

- [/home/tuojing/arx_r5_control/experiments/sweep_live_20261018_124546](</home/tuojing/arx_r5_control/experiments/sweep_live_20261018_124546>) — 任务执行记录（含未完成尝试）；MP4 61 个；[README.md](</home/tuojing/arx_r5_control/experiments/sweep_live_20261018_124546/README.md>)

### 网球遥操示范分析

- [/home/tuojing/arx_r5_control/analysis/20260924T133550_3e5009566926](</home/tuojing/arx_r5_control/analysis/20260924T133550_3e5009566926>) — 示范分析报告；MP4 0 个；[report.md](</home/tuojing/arx_r5_control/analysis/20260924T133550_3e5009566926/report.md>)

### 擦白板

- [/home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial01_20261013](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial01_20261013>) — 任务执行记录（含未完成尝试）；MP4 165 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial01_20261013/EXPERIMENT_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial02_20261013](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial02_20261013>) — 任务执行记录（含未完成尝试）；MP4 3 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial02_20261013/EXPERIMENT_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial03_20261013](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial03_20261013>) — 任务执行记录（含未完成尝试）；MP4 3 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial03_20261013/EXPERIMENT_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial04_20261014](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial04_20261014>) — 任务执行记录（含未完成尝试）；MP4 60 个；[EXPERIMENT_RECORD.md](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial04_20261014/EXPERIMENT_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial05_20261017](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial05_20261017>) — 任务执行记录（含未完成尝试）；MP4 52 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial05_20261017/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial06_20261017](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial06_20261017>) — 任务执行记录（含未完成尝试）；MP4 43 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial06_20261017/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial07_20261017](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial07_20261017>) — 任务执行记录（含未完成尝试）；MP4 64 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial07_20261017/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial08_20261017](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial08_20261017>) — 任务执行记录（含未完成尝试）；MP4 36 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial08_20261017/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial09_20261017](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial09_20261017>) — 任务执行记录（含未完成尝试）；MP4 154 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial09_20261017/RUN_RECORD.md>)
- [/home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial10_20261017](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial10_20261017>) — 任务执行记录（含未完成尝试）；MP4 100 个；[RUN_RECORD.md](</home/tuojing/arx_r5_control/analysis/whiteboard_wiping_trial10_20261017/RUN_RECORD.md>)

## 4. 主目录 / Documents 中的 7 个推书目录

| 实际路径 | Markdown 入口 | MP4 数 | 大小 |
|---|---|---:|---:|
| [/home/tuojing/book_push_20261018_0318](</home/tuojing/book_push_20261018_0318>) | [README.md](</home/tuojing/book_push_20261018_0318/README.md>) | 13 | 708.8 MiB |
| [/home/tuojing/book_push_20261018_105627](</home/tuojing/book_push_20261018_105627>) | [record.md](</home/tuojing/book_push_20261018_105627/record.md>) | 7 | 159.5 MiB |
| [/home/tuojing/book_stack_push_20261018](</home/tuojing/book_stack_push_20261018>) | [execution.md](</home/tuojing/book_stack_push_20261018/execution.md>) | 3 | 247.1 MiB |
| [/home/tuojing/book_stack_push_20261018_1500](</home/tuojing/book_stack_push_20261018_1500>) | [execution.md](</home/tuojing/book_stack_push_20261018_1500/execution.md>) | 3 | 16.6 MiB |
| [/home/tuojing/book_stack_push_20261018_1505](</home/tuojing/book_stack_push_20261018_1505>) | [result.md](</home/tuojing/book_stack_push_20261018_1505/result.md>) | 15 | 555.2 MiB |
| [/home/tuojing/book_stack_run_20261018_155501](</home/tuojing/book_stack_run_20261018_155501>) | [record.md](</home/tuojing/book_stack_run_20261018_155501/record.md>) | 7 | 149.0 MiB |
| [/home/tuojing/Documents/book_push_20261018_104906](</home/tuojing/Documents/book_push_20261018_104906>) | [record.md](</home/tuojing/Documents/book_push_20261018_104906/record.md>) | 3 | 51.5 MiB |

`book_stack_push_20261018_1500` 主要为任务前准备记录；`book_stack_push_20261018_1505` 还含 `restore_initial/` 与 `restore_initial_02/` 两次回位记录。

## 5. `.codex` 中的真实结果与软链接

- [/home/tuojing/.codex/robot_runs/withskills_blue_blocks_sweeping_20261020_175900](</home/tuojing/.codex/robot_runs/withskills_blue_blocks_sweeping_20261020_175900>) — MP4 147 个，1.12 GiB。
  - [README.md](</home/tuojing/.codex/robot_runs/withskills_blue_blocks_sweeping_20261020_175900/README.md>)
  - [RUN_RECORD.md](</home/tuojing/.codex/robot_runs/withskills_blue_blocks_sweeping_20261020_175900/RUN_RECORD.md>)
  - [VIDEO_RECORD.md](</home/tuojing/.codex/robot_runs/withskills_blue_blocks_sweeping_20261020_175900/VIDEO_RECORD.md>)
- [/home/tuojing/.codex/outputs/sweep_live_20261018_1638](</home/tuojing/.codex/outputs/sweep_live_20261018_1638>) — MP4 3 个，76.8 MiB。
  - [record.md](</home/tuojing/.codex/outputs/sweep_live_20261018_1638/record.md>)

以下只是软链接，不应重复计为另一份实验数据：

- [/home/tuojing/.codex/robot_runs/book_stack_turn_20261020_1236](</home/tuojing/.codex/robot_runs/book_stack_turn_20261020_1236>) → [/home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629](</home/tuojing/robot_runs/withskills_book_stack_turn_20261020_123629>)

## 6. `exports` 导出和副本

此处保存本地导出产物；目录名中的发布平台不代表本次访问过云端。源码/技能同步目录不列作实验结果。

- [/home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261006](</home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261006>) — 18类协议变体、21份主记录、原始及派生视频等；大小来自包内清单（48.58 GiB）
  - [README_使用说明.md](</home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261006/README_使用说明.md>)
  - [index.html](</home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261006/index.html>)
- [/home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261006.zip](</home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261006.zip>) — 同名导出目录的压缩交付版本（47.41 GiB）
- [/home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261006.zip.sha256](</home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261006.zip.sha256>) — 对应ZIP的SHA-256校验文本（0.0 MiB）
- [/home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261007_compact](</home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261007_compact>) — 18个150秒三视角成片、25份主记录；连续原片留在源目录；大小为排除范围后的下限（500.5 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261007_compact/README.md>)
  - [index.html](</home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261007_compact/index.html>)
- [/home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261007_compact.zip](</home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261007_compact.zip>) — 同名导出目录的压缩交付版本（297.3 MiB）
- [/home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261007_compact.zip.sha256](</home/tuojing/arx_r5_control/exports/ARX_R5_experiments_20261007_compact.zip.sha256>) — 对应ZIP的SHA-256校验文本（0.0 MiB）
- [/home/tuojing/arx_r5_control/exports/LATEST_BUNDLE.md](</home/tuojing/arx_r5_control/exports/LATEST_BUNDLE.md>) — 指向20261007精简包及ZIP（0.0 MiB）
- [/home/tuojing/arx_r5_control/exports/blackboard_eraser_push_trial01_20261011_90s](</home/tuojing/arx_r5_control/exports/blackboard_eraser_push_trial01_20261011_90s>) — 由原始录像生成的倍速合成片，1 个；大小仅统计根目录文件（16.5 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/blackboard_eraser_push_trial01_20261011_90s/README.md>)
- [/home/tuojing/arx_r5_control/exports/blue_blocks_sweeping_trial02_20261011_90s](</home/tuojing/arx_r5_control/exports/blue_blocks_sweeping_trial02_20261011_90s>) — 由原始录像生成的倍速合成片，1 个；大小仅统计根目录文件（16.3 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/blue_blocks_sweeping_trial02_20261011_90s/README.md>)
- [/home/tuojing/arx_r5_control/exports/bolt_unscrewing_trial01_20261011_90s](</home/tuojing/arx_r5_control/exports/bolt_unscrewing_trial01_20261011_90s>) — 由原始录像生成的倍速合成片，1 个；大小仅统计根目录文件（16.2 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/bolt_unscrewing_trial01_20261011_90s/README.md>)
- [/home/tuojing/arx_r5_control/exports/bottle_unscrewing_trial05_20261014_90s](</home/tuojing/arx_r5_control/exports/bottle_unscrewing_trial05_20261014_90s>) — 由原始录像生成的倍速合成片，1 个；大小仅统计根目录文件（17.2 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/bottle_unscrewing_trial05_20261014_90s/README.md>)
- [/home/tuojing/arx_r5_control/exports/feishu_jelly_grasp_20261012](</home/tuojing/arx_r5_control/exports/feishu_jelly_grasp_20261012>) — 本地报告、表格或回执材料；没有访问在线文档（0.3 MiB）
- [/home/tuojing/arx_r5_control/exports/feishu_real_robot_20261011](</home/tuojing/arx_r5_control/exports/feishu_real_robot_20261011>) — 本地报告、表格或回执材料；没有访问在线文档（0.0 MiB）
  - [real_robot_draft.docx](</home/tuojing/arx_r5_control/exports/feishu_real_robot_20261011/real_robot_draft.docx>)
  - [real_robot_draft.html](</home/tuojing/arx_r5_control/exports/feishu_real_robot_20261011/real_robot_draft.html>)
- [/home/tuojing/arx_r5_control/exports/feishu_real_robot_filled_20261011](</home/tuojing/arx_r5_control/exports/feishu_real_robot_filled_20261011>) — 本地报告、表格或回执材料；没有访问在线文档（0.4 MiB）
  - [real_robot_rows.csv](</home/tuojing/arx_r5_control/exports/feishu_real_robot_filled_20261011/real_robot_rows.csv>)
  - [real_robot_rows.html](</home/tuojing/arx_r5_control/exports/feishu_real_robot_filled_20261011/real_robot_rows.html>)
- [/home/tuojing/arx_r5_control/exports/jelly_grasp_trial01_20261012_90s](</home/tuojing/arx_r5_control/exports/jelly_grasp_trial01_20261012_90s>) — 由原始录像生成的倍速合成片，1 个；大小仅统计根目录文件（14.7 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/jelly_grasp_trial01_20261012_90s/README.md>)
- [/home/tuojing/arx_r5_control/exports/jelly_grasp_trial03_20261012_90s](</home/tuojing/arx_r5_control/exports/jelly_grasp_trial03_20261012_90s>) — 由原始录像生成的倍速合成片，1 个；大小仅统计根目录文件（15.7 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/jelly_grasp_trial03_20261012_90s/README.md>)
- [/home/tuojing/arx_r5_control/exports/jelly_packaged_cup_trial01_20261014_90s](</home/tuojing/arx_r5_control/exports/jelly_packaged_cup_trial01_20261014_90s>) — 由原始录像生成的倍速合成片，1 个；大小仅统计根目录文件（16.3 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/jelly_packaged_cup_trial01_20261014_90s/README.md>)
- [/home/tuojing/arx_r5_control/exports/jelly_pick_place_trial02_20261014_90s](</home/tuojing/arx_r5_control/exports/jelly_pick_place_trial02_20261014_90s>) — 由原始录像生成的倍速合成片，1 个；大小仅统计根目录文件（15.6 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/jelly_pick_place_trial02_20261014_90s/README.md>)
- [/home/tuojing/arx_r5_control/exports/left_cap_unscrewing_trial02_20261014_90s](</home/tuojing/arx_r5_control/exports/left_cap_unscrewing_trial02_20261014_90s>) — 由原始录像生成的倍速合成片，1 个；大小仅统计根目录文件（15.2 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/left_cap_unscrewing_trial02_20261014_90s/README.md>)
- [/home/tuojing/arx_r5_control/exports/orange_pick_place_trial02_20261011_90s](</home/tuojing/arx_r5_control/exports/orange_pick_place_trial02_20261011_90s>) — 由原始录像生成的倍速合成片，1 个；大小仅统计根目录文件（15.9 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/orange_pick_place_trial02_20261011_90s/README.md>)
- [/home/tuojing/arx_r5_control/exports/pearl_pouring_trial02_20261011_90s](</home/tuojing/arx_r5_control/exports/pearl_pouring_trial02_20261011_90s>) — 由原始录像生成的倍速合成片，1 个；大小仅统计根目录文件（17.1 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/pearl_pouring_trial02_20261011_90s/README.md>)
- [/home/tuojing/arx_r5_control/exports/task_replays_20261011_90s](</home/tuojing/arx_r5_control/exports/task_replays_20261011_90s>) — 由原始录像生成的倍速合成片，2 个；大小仅统计根目录文件（41.3 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/task_replays_20261011_90s/README.md>)
- [/home/tuojing/arx_r5_control/exports/whiteboard_wiping_trial04_20261014_90s](</home/tuojing/arx_r5_control/exports/whiteboard_wiping_trial04_20261014_90s>) — 由原始录像生成的倍速合成片，1 个；大小仅统计根目录文件（17.3 MiB）
  - [README.md](</home/tuojing/arx_r5_control/exports/whiteboard_wiping_trial04_20261014_90s/README.md>)

20261006 的完整导出目录和同名 ZIP、20261007 的精简目录和同名 ZIP，分别是对应同一导出包的目录版与压缩版。目录版又整理了源实验内容，不能计为新增实验；本次未对所有副本逐文件哈希比对。

## 7. 早期逐帧采集目录

| 目录 | manifest 中的名称 | 记录时长 |
|---|---|---:|
| [/home/tuojing/arx_r5_control/recordings/20260924T133332_f8c705711ec6](</home/tuojing/arx_r5_control/recordings/20260924T133332_f8c705711ec6>) | 连接验证 静止采集 | 0.606 秒 |
| [/home/tuojing/arx_r5_control/recordings/20260924T133550_3e5009566926](</home/tuojing/arx_r5_control/recordings/20260924T133550_3e5009566926>) | 抓取网球 | 154.967 秒 |
| [/home/tuojing/arx_r5_control/recordings/20260924T135057_6a0ba0ea260b](</home/tuojing/arx_r5_control/recordings/20260924T135057_6a0ba0ea260b>) | Autonomous J3 +0.5 deg probe | 0.856 秒 |
| [/home/tuojing/arx_r5_control/recordings/20260924T135159_002c9db867d6](</home/tuojing/arx_r5_control/recordings/20260924T135159_002c9db867d6>) | Enable hold baseline - no joint target change | 0.855 秒 |
| [/home/tuojing/arx_r5_control/recordings/20260924T135243_10d933b7b83a](</home/tuojing/arx_r5_control/recordings/20260924T135243_10d933b7b83a>) | 抓取网球 | 263.902 秒 |
| [/home/tuojing/arx_r5_control/recordings/20260924T145652_08f81a0ff6cf](</home/tuojing/arx_r5_control/recordings/20260924T145652_08f81a0ff6cf>) | Supervised visual grasp session | 5.313 秒 |
| [/home/tuojing/arx_r5_control/recordings/20260924T150728_f82b93623111](</home/tuojing/arx_r5_control/recordings/20260924T150728_f82b93623111>) | Supervised visual grasp session | 37.727 秒 |
| [/home/tuojing/arx_r5_control/recordings/20260924T151143_1b53282ec423](</home/tuojing/arx_r5_control/recordings/20260924T151143_1b53282ec423>) | Supervised visual grasp session | 5.313 秒 |
| [/home/tuojing/arx_r5_control/recordings/20260924T152451_55f3f8e924ae](</home/tuojing/arx_r5_control/recordings/20260924T152451_55f3f8e924ae>) | Supervised visual grasp session | 45.242 秒 |
| [/home/tuojing/arx_r5_control/recordings/20260924T152803_a3cd62267b30](</home/tuojing/arx_r5_control/recordings/20260924T152803_a3cd62267b30>) | Supervised visual grasp session | 20.426 秒 |
| [/home/tuojing/arx_r5_control/recordings/20261018T025643_5b301ab97a36](</home/tuojing/arx_r5_control/recordings/20261018T025643_5b301ab97a36>) | cooperative_three_book_stack_push_no_grasp | 82.705 秒 |

这些目录均记录 `gemini` 与 `external` 两路相机；入口为 `manifest.json`，时间线为 `timeline.jsonl`。

## 8. 工程根目录的实验报告文件

| 报告 | 标题 |
|---|---|
| [BLACKBOARD_ERASER_PUSH_EXPERIMENT_RECORD_20261011_TRIAL01.md](</home/tuojing/arx_r5_control/BLACKBOARD_ERASER_PUSH_EXPERIMENT_RECORD_20261011_TRIAL01.md>) | 推黑板擦 — 2026-10-11 第1轮 |
| [BLACKBOARD_ERASER_PUSH_EXPERIMENT_RECORD_20261014_TRIAL02.md](</home/tuojing/arx_r5_control/BLACKBOARD_ERASER_PUSH_EXPERIMENT_RECORD_20261014_TRIAL02.md>) | 左夹爪边缘推黑板擦入红区 — 2026-10-14 第2轮 |
| [BLACKBOARD_WIPING_EXPERIMENT_RECORD_20261006.md](</home/tuojing/arx_r5_control/BLACKBOARD_WIPING_EXPERIMENT_RECORD_20261006.md>) | 擦黑板实验记录 — 2026-10-06 |
| [BLUE_BLOCKS_SWEEPING_EXPERIMENT_RECORD_20261006.md](</home/tuojing/arx_r5_control/BLUE_BLOCKS_SWEEPING_EXPERIMENT_RECORD_20261006.md>) | 左臂扫蓝色方块入簸箕 — 2026-10-06 |
| [BLUE_BLOCKS_SWEEPING_EXPERIMENT_RECORD_20261011_TRIAL02.md](</home/tuojing/arx_r5_control/BLUE_BLOCKS_SWEEPING_EXPERIMENT_RECORD_20261011_TRIAL02.md>) | 左臂自主拾刷后扫蓝色方块 — 2026-10-11 第2轮 |
| [BLUE_BLOCK_TRIANGLE_PUSH_EXPERIMENT_RECORD_20261006.md](</home/tuojing/arx_r5_control/BLUE_BLOCK_TRIANGLE_PUSH_EXPERIMENT_RECORD_20261006.md>) | 蓝块推入红色三角区域 — 2026-10-06 |
| [BOLT_SCREWING_EXPERIMENT_RECORD_20261005.md](</home/tuojing/arx_r5_control/BOLT_SCREWING_EXPERIMENT_RECORD_20261005.md>) | 左臂旋螺母入右臂螺栓：2026-10-05，第1轮未成功 |
| [BOLT_UNSCREWING_EXPERIMENT_RECORD_20261011.md](</home/tuojing/arx_r5_control/BOLT_UNSCREWING_EXPERIMENT_RECORD_20261011.md>) | 双臂拧螺丝 — 自主拾柱并旋下六边形螺帽 — 2026-10-11 第1轮 |
| [BOOK_EXTRACTION_EXPERIMENT_RECORD_20261006.md](</home/tuojing/arx_r5_control/BOOK_EXTRACTION_EXPERIMENT_RECORD_20261006.md>) | 左臂抽取中间书本 — 2026-10-06 |
| [BOTTLE_UNSCREWING_EXPERIMENT_RECORD_20261005.md](</home/tuojing/arx_r5_control/BOTTLE_UNSCREWING_EXPERIMENT_RECORD_20261005.md>) | 双臂旋瓶盖（总第11项，分类未指定） |
| [BOTTLE_UNSCREWING_EXPERIMENT_RECORD_20261014_TRIAL04.md](</home/tuojing/arx_r5_control/BOTTLE_UNSCREWING_EXPERIMENT_RECORD_20261014_TRIAL04.md>) | 双臂旋瓶盖 · 2026-10-14 第4轮 |
| [BOTTLE_UNSCREWING_EXPERIMENT_RECORD_20261014_TRIAL05.md](</home/tuojing/arx_r5_control/BOTTLE_UNSCREWING_EXPERIMENT_RECORD_20261014_TRIAL05.md>) | 双臂旋瓶盖 · 2026-10-14 第5轮 |
| [CHARGER_ALIGNMENT_EXPERIMENT_RECORD_20261016.md](</home/tuojing/arx_r5_control/CHARGER_ALIGNMENT_EXPERIMENT_RECORD_20261016.md>) | 左臂适配器对齐 — 2026-10-16 |
| [CHARGER_INSERTION_EXPERIMENT_RECORD_20261001.md](</home/tuojing/arx_r5_control/CHARGER_INSERTION_EXPERIMENT_RECORD_20261001.md>) | 任务 02：手机充电器插入插线板实验记录 |
| [CHARGER_INSERTION_EXPERIMENT_RECORD_20261005.md](</home/tuojing/arx_r5_control/CHARGER_INSERTION_EXPERIMENT_RECORD_20261005.md>) | 插座实验 — 2026-10-05，第11轮 |
| [CHARGER_INSERT_ONLY_EXPERIMENT_RECORD_20261005.md](</home/tuojing/arx_r5_control/CHARGER_INSERT_ONLY_EXPERIMENT_RECORD_20261005.md>) | 人工预置充电头后插入 — 2026-10-05 |
| [CUP_STACKING_EXPERIMENT_RECORD_20261001.md](</home/tuojing/arx_r5_control/CUP_STACKING_EXPERIMENT_RECORD_20261001.md>) | 任务 01：双臂叠杯实验记录 |
| [CUP_STACKING_EXPERIMENT_RECORD_20261007.md](</home/tuojing/arx_r5_control/CUP_STACKING_EXPERIMENT_RECORD_20261007.md>) | 双臂叠杯真机实验补测 — 2026-10-07 |
| [DRAWER_PUSH_PULL_EXPERIMENT_RECORD_20261005.md](</home/tuojing/arx_r5_control/DRAWER_PUSH_PULL_EXPERIMENT_RECORD_20261005.md>) | 第9项：抽屉拉出与推回 — 2026-10-05 第1轮 |
| [DRAWER_PUSH_PULL_EXPERIMENT_RECORD_20261017.md](</home/tuojing/arx_r5_control/DRAWER_PUSH_PULL_EXPERIMENT_RECORD_20261017.md>) | 抽屉拉出与推回 — 2026-10-17 第3轮 |
| [EXPERIMENT_EVIDENCE_GAPS_20261007.md](</home/tuojing/arx_r5_control/EXPERIMENT_EVIDENCE_GAPS_20261007.md>) | 历史任务视频与资源记录缺口 — 2026-10-07 |
| [FAULT_POWERED_HOLD_20261005.md](</home/tuojing/arx_r5_control/FAULT_POWERED_HOLD_20261005.md>) | 到位失败后的有条件带电保持 |
| [FIXED_BOTTLE_LEFT_CAP_EXPERIMENT_RECORD_20261005.md](</home/tuojing/arx_r5_control/FIXED_BOTTLE_LEFT_CAP_EXPERIMENT_RECORD_20261005.md>) | 固定瓶身、左臂旋盖实验 — 2026-10-05 |
| [FIXED_BOTTLE_LEFT_CAP_EXPERIMENT_RECORD_20261006.md](</home/tuojing/arx_r5_control/FIXED_BOTTLE_LEFT_CAP_EXPERIMENT_RECORD_20261006.md>) | 固定瓶身左臂旋盖实验 — 2026-10-06 |
| [FLOWER_INSERTION_EXPERIMENT_RECORD_20261002.md](</home/tuojing/arx_r5_control/FLOWER_INSERTION_EXPERIMENT_RECORD_20261002.md>) | 任务04：左臂插花入左侧瓶子，右臂辅助观察 |
| [FLOWER_INSERTION_EXPERIMENT_RECORD_20261003.md](</home/tuojing/arx_r5_control/FLOWER_INSERTION_EXPERIMENT_RECORD_20261003.md>) | 插花实验记录：2026-10-03 |
| [FLOWER_INSERTION_EXPERIMENT_RECORD_20261007.md](</home/tuojing/arx_r5_control/FLOWER_INSERTION_EXPERIMENT_RECORD_20261007.md>) | 插花真机补测记录 — 2026-10-07，第6轮 |
| [FLOWER_INSERTION_EXPERIMENT_RECORD_20261010.md](</home/tuojing/arx_r5_control/FLOWER_INSERTION_EXPERIMENT_RECORD_20261010.md>) | 插花真机实验 — 2026-10-10 第7轮 |
| [FLOWER_INSERTION_EXPERIMENT_RECORD_20261017_TRIAL02.md](</home/tuojing/arx_r5_control/FLOWER_INSERTION_EXPERIMENT_RECORD_20261017_TRIAL02.md>) | 插花自动转移 — 2026-10-17 第2轮 |
| [FLOWER_TRANSFER_EXPERIMENT_RECORD_20261016_TRIAL01.md](</home/tuojing/arx_r5_control/FLOWER_TRANSFER_EXPERIMENT_RECORD_20261016_TRIAL01.md>) | 左杯取花→右杯插入释放 — 2026-10-16 第1轮 |
| [HAT_HANGING_EXPERIMENT_RECORD_20261003.md](</home/tuojing/arx_r5_control/HAT_HANGING_EXPERIMENT_RECORD_20261003.md>) | L1 — 左臂挂帽子 — 2026-10-03 |
| [HAT_HANGING_EXPERIMENT_RECORD_20261007.md](</home/tuojing/arx_r5_control/HAT_HANGING_EXPERIMENT_RECORD_20261007.md>) | L1 挂帽真机实验记录 — 2026-10-07，第4轮 |
| [HAT_HANGING_EXPERIMENT_RECORD_20261010.md](</home/tuojing/arx_r5_control/HAT_HANGING_EXPERIMENT_RECORD_20261010.md>) | 挂帽真机实验 — 2026-10-10 第5轮 |
| [HAT_HANGING_EXPERIMENT_RECORD_20261010_TRIAL06.md](</home/tuojing/arx_r5_control/HAT_HANGING_EXPERIMENT_RECORD_20261010_TRIAL06.md>) | 挂帽真机实验 — 2026-10-10 第6轮 |
| [HAT_HANGING_EXPERIMENT_RECORD_20261010_TRIAL07.md](</home/tuojing/arx_r5_control/HAT_HANGING_EXPERIMENT_RECORD_20261010_TRIAL07.md>) | 挂帽真机实验 — 2026-10-10 第7轮 |
| [HAT_HANGING_EXPERIMENT_RECORD_20261010_TRIAL08.md](</home/tuojing/arx_r5_control/HAT_HANGING_EXPERIMENT_RECORD_20261010_TRIAL08.md>) | 挂帽真机实验 — 2026-10-10 第8轮 |
| [HAT_HANGING_EXPERIMENT_RECORD_20261010_TRIAL09.md](</home/tuojing/arx_r5_control/HAT_HANGING_EXPERIMENT_RECORD_20261010_TRIAL09.md>) | 挂帽真机实验 — 2026-10-10 第9轮准备记录 |
| [HAT_HANGING_EXPERIMENT_RECORD_20261011.md](</home/tuojing/arx_r5_control/HAT_HANGING_EXPERIMENT_RECORD_20261011.md>) | 挂帽实验第10轮（2026-10-11） |
| [HAT_HANGING_EXPERIMENT_RECORD_20261011_TRIAL11.md](</home/tuojing/arx_r5_control/HAT_HANGING_EXPERIMENT_RECORD_20261011_TRIAL11.md>) | 挂帽实验第11轮（2026-10-11） |
| [HAT_HANGING_EXPERIMENT_RECORD_20261011_TRIAL12.md](</home/tuojing/arx_r5_control/HAT_HANGING_EXPERIMENT_RECORD_20261011_TRIAL12.md>) | 挂帽实验第12轮（2026-10-11） |
| [HAT_HANGING_EXPERIMENT_RECORD_20261011_TRIAL13.md](</home/tuojing/arx_r5_control/HAT_HANGING_EXPERIMENT_RECORD_20261011_TRIAL13.md>) | 挂帽实验第13轮（2026-10-11）— 失败，已回位 |
| [JELLY_GRASP_EXPERIMENT_RECORD_20261012_TRIAL01.md](</home/tuojing/arx_r5_control/JELLY_GRASP_EXPERIMENT_RECORD_20261012_TRIAL01.md>) | 夹取果冻实验记录 · 2026-10-12 · 新协议第1轮 |
| [JELLY_GRASP_EXPERIMENT_RECORD_20261012_TRIAL02.md](</home/tuojing/arx_r5_control/JELLY_GRASP_EXPERIMENT_RECORD_20261012_TRIAL02.md>) | 夹取果冻 · 新协议第2轮 · 2026-10-12 |
| [JELLY_GRASP_EXPERIMENT_RECORD_20261012_TRIAL03.md](</home/tuojing/arx_r5_control/JELLY_GRASP_EXPERIMENT_RECORD_20261012_TRIAL03.md>) | 夹取果冻 · 第3轮 · 2026-10-12 |
| [JELLY_PACKAGED_CUP_EXPERIMENT_RECORD_20261014_TRIAL01.md](</home/tuojing/arx_r5_control/JELLY_PACKAGED_CUP_EXPERIMENT_RECORD_20261014_TRIAL01.md>) | 包装果冻杯抓放 · 2026-10-14 第1轮 |
| [JELLY_PICK_PLACE_EXPERIMENT_RECORD_20261005.md](</home/tuojing/arx_r5_control/JELLY_PICK_PLACE_EXPERIMENT_RECORD_20261005.md>) | 果冻抓取、抬升与放回（总第10项） |
| [JELLY_PICK_PLACE_EXPERIMENT_RECORD_20261014_TRIAL02.md](</home/tuojing/arx_r5_control/JELLY_PICK_PLACE_EXPERIMENT_RECORD_20261014_TRIAL02.md>) | 裸果冻抓放 · 2026-10-14 第2轮 |
| [JELLY_PICK_PLACE_EXPERIMENT_RECORD_20261016_TRIAL01.md](</home/tuojing/arx_r5_control/JELLY_PICK_PLACE_EXPERIMENT_RECORD_20261016_TRIAL01.md>) | 裸果冻抓放 — 2026-10-16 第1轮 |
| [LEFT_CAP_UNSCREWING_EXPERIMENT_RECORD_20261014_TRIAL01.md](</home/tuojing/arx_r5_control/LEFT_CAP_UNSCREWING_EXPERIMENT_RECORD_20261014_TRIAL01.md>) | 左臂旋瓶盖并抬离 · 2026-10-14 · 本协议第1轮 |
| [LEFT_CAP_UNSCREWING_EXPERIMENT_RECORD_20261014_TRIAL02.md](</home/tuojing/arx_r5_control/LEFT_CAP_UNSCREWING_EXPERIMENT_RECORD_20261014_TRIAL02.md>) | 左臂旋瓶盖并抬离 · 2026-10-14 · 本协议第2轮 |
| [ORANGE_PICK_PLACE_EXPERIMENT_RECORD_20261005.md](</home/tuojing/arx_r5_control/ORANGE_PICK_PLACE_EXPERIMENT_RECORD_20261005.md>) | 第8项：橘瓣抓取、抬升与放回，2026-10-05 |
| [ORANGE_PICK_PLACE_EXPERIMENT_RECORD_20261011_TRIAL02.md](</home/tuojing/arx_r5_control/ORANGE_PICK_PLACE_EXPERIMENT_RECORD_20261011_TRIAL02.md>) | 橘瓣抓放 — 2026-10-11 第2轮 |
| [PEARL_POURING_EXPERIMENT_RECORD_20261005.md](</home/tuojing/arx_r5_control/PEARL_POURING_EXPERIMENT_RECORD_20261005.md>) | 第7项：杯间倒珍珠，2026-10-05 |
| [PEARL_POURING_EXPERIMENT_RECORD_20261011_TRIAL02.md](</home/tuojing/arx_r5_control/PEARL_POURING_EXPERIMENT_RECORD_20261011_TRIAL02.md>) | 倾倒小球（杯间倒珍珠）— 2026-10-11 第2轮 |
| [PEN_INSERTION_EXPERIMENT_RECORD_20261002.md](</home/tuojing/arx_r5_control/PEN_INSERTION_EXPERIMENT_RECORD_20261002.md>) | 任务03：左臂把笔插入笔筒 |
| [PEN_INSERTION_EXPERIMENT_RECORD_20261007.md](</home/tuojing/arx_r5_control/PEN_INSERTION_EXPERIMENT_RECORD_20261007.md>) | 插笔真机补测 — 2026-10-07 |
| [PEN_INSERTION_EXPERIMENT_RECORD_20261016.md](</home/tuojing/arx_r5_control/PEN_INSERTION_EXPERIMENT_RECORD_20261016.md>) | 粗记号笔放入宽口杯 — 2026-10-16 |
| [PEN_UNCAPPING_EXPERIMENT_RECORD_20261003.md](</home/tuojing/arx_r5_control/PEN_UNCAPPING_EXPERIMENT_RECORD_20261003.md>) | 总第6项 / L2 — 双臂拔笔帽 — 2026-10-03 |
| [PEN_UNCAPPING_EXPERIMENT_RECORD_20261011_TRIAL05.md](</home/tuojing/arx_r5_control/PEN_UNCAPPING_EXPERIMENT_RECORD_20261011_TRIAL05.md>) | 总第6项 / L2 — 双臂摘笔帽 — 2026-10-11 第5轮 |
| [PEN_UNCAPPING_EXPERIMENT_RECORD_20261011_TRIAL06.md](</home/tuojing/arx_r5_control/PEN_UNCAPPING_EXPERIMENT_RECORD_20261011_TRIAL06.md>) | 总第6项 / L2 — 摘笔帽 — 2026-10-11 第6轮 |
| [REAL_ROBOT_EXPERIMENT_REPORT_20261006.md](</home/tuojing/arx_r5_control/REAL_ROBOT_EXPERIMENT_REPORT_20261006.md>) | 通用大模型接触密集型任务测试报告 |
| [REAL_ROBOT_EXPERIMENT_REPORT_20261007.md](</home/tuojing/arx_r5_control/REAL_ROBOT_EXPERIMENT_REPORT_20261007.md>) | 通用大模型接触密集型任务测试报告 |
| [WHITEBOARD_WIPING_EXPERIMENT_RECORD_20261013_TRIAL01.md](</home/tuojing/arx_r5_control/WHITEBOARD_WIPING_EXPERIMENT_RECORD_20261013_TRIAL01.md>) | 左臂自主抓板擦擦除白板GPT6 · 2026-10-13 第1轮 |
| [WHITEBOARD_WIPING_EXPERIMENT_RECORD_20261013_TRIAL02.md](</home/tuojing/arx_r5_control/WHITEBOARD_WIPING_EXPERIMENT_RECORD_20261013_TRIAL02.md>) | 白板GPT6擦除 · 2026-10-13 第2轮 |
| [WHITEBOARD_WIPING_EXPERIMENT_RECORD_20261013_TRIAL03.md](</home/tuojing/arx_r5_control/WHITEBOARD_WIPING_EXPERIMENT_RECORD_20261013_TRIAL03.md>) | 带框白板GPT6擦除 · 2026-10-13 第3轮 |
| [WHITEBOARD_WIPING_EXPERIMENT_RECORD_20261014_TRIAL04.md](</home/tuojing/arx_r5_control/WHITEBOARD_WIPING_EXPERIMENT_RECORD_20261014_TRIAL04.md>) | 左臂自主抓板擦擦白板 · 2026-10-14 第4轮 |
| [WHITEBOARD_WIPING_EXPERIMENT_RECORD_20261017_TRIAL05.md](</home/tuojing/arx_r5_control/WHITEBOARD_WIPING_EXPERIMENT_RECORD_20261017_TRIAL05.md>) | 擦白板 — 2026-10-17 第5轮 |
| [WHITEBOARD_WIPING_EXPERIMENT_RECORD_20261017_TRIAL07.md](</home/tuojing/arx_r5_control/WHITEBOARD_WIPING_EXPERIMENT_RECORD_20261017_TRIAL07.md>) | 擦白板第7轮实验 |

## 9. 临时素材、辅助目录与重复计数说明

- `/tmp/book_stack_new_preflight/`：3 张相机 JPG 与 `cameras.json`，仅任务准备快照。
- `/tmp/r5-flower-prep/`：插花准备临时目录。
- `/tmp/r5-current-run/`：本次核查时为空。
- `/tmp/current_*_run`、`/tmp/current_*_path`：保存当前结果路径的文本指针，不是录像目录。
- `arx_r5_control/Log/` 与 `.qa/`：运行日志和检查产物，不作为实验结果归档。
- `analysis` 内有 375 个顶级目录；按排除规则统计 374 个。其中 110 个归类为任务执行，其余包括准备、标定、控制会话和汇总等，不能说成 375 次实验。
- `analysis/book_extraction_trial02_20261006/recording_recovered/` 的 150 个视频链接以及 `analysis/drawer_push_pull_trial03_20261017/recording_recovered/` 的 60 个视频链接均引用同次实验的原文件，不另占一套原始视频。
- `analysis/hat_hanging_trial03_20261003/live_review` 指向 `analysis/hat_hanging_trial02_20261003/review`。
- 先前已核实的 `analysis/book_stack_push_turn_20261020_113632/` 是上午推书实验的原始目录；主归档中的 `双爪推叠书并旋转一圈-20261020_113632-withskills-b460d8d0/` 是其归档副本，并非另一次实验。

## 10. 完整可筛选索引

- [CSV 索引](</home/tuojing/embodied_result_paths_20261020.csv>)：每个任务目录、诊断目录、导出项、报告和采集目录一行。
- [JSON 索引](</home/tuojing/embodied_result_paths_20261020.json>)：相同条目及统计来源说明。

补充核查了 Documents、Desktop、Videos、Downloads、Pictures 的文件名；除上述 Documents 推书记录，未发现其他明确匹配的具身实验结果。本索引是已核查本机位置的清单，不声称覆盖其他磁盘、远端机器或云端。
