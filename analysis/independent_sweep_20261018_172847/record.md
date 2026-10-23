# 左臂持刷扫块实验记录

日期：2026-10-18，时区：Asia/Shanghai。

## 任务与结果

- 左臂抓取绿盒旁的刷子，将两块蓝色方块扫入固定簸箕：完成。抬起刷子后，通过头部相机与右腕相机确认两块均在簸箕内部。
- 刷子放回初始位置：已放回绿盒旁的原始放置区域，恢复靠在盒边、刷毛落桌的姿态。松爪后撤离左臂，再次确认刷子稳定。位置依据本次初始与最终画面核对，未进行毫米级定位测量。
- 右臂仅辅助观察：全程未向右臂发送控制指令，使用其腕部相机观察。
- 左臂已回到初始停放关节目标并停用。最终两臂均报告 `enabled=false`、`moving=false`，无错误码。

## 视频交付

[90 秒三路合成视频](sweep_90s_three_views.mp4)

布局：左上为左腕相机，右上为右腕相机，下方为头部相机。保留画面比例；三路按各帧实际采集时间同步，对共同录制区间均匀加速，不删去中间操作。

合成规格：1280 × 960，30 fps，2700 帧，**90.000 秒**，MP4；共同源时长 706.353 秒，加速约 7.848 倍，文件大小 70.09 MB。

| 原始视频 | 相机 | 帧数 | 标称帧率 | 采集错误 |
|---|---|---:|---:|---:|
| [gemini.mp4](gemini.mp4) | 左腕 | 7058 | 10 fps | 0 |
| [gemini_right.mp4](gemini_right.mp4) | 右腕 | 7058 | 10 fps | 0 |
| [external.mp4](external.mp4) | 头部 | 7058 | 10 fps | 0 |

三路均从 17:28:56 录制至 17:40:42，覆盖抓取前初态、全部操作和最终回位。原始视频按固定 10 fps 写入，逐帧实际时间保存在对应的 `*_frames.jsonl` 文件中；合成视频按这些时间戳同步。

验证：三个原始文件的帧数均与时间戳记录一致；合成视频帧数与帧率确认时长恰为 90 秒；首帧、中间帧和末帧均解码成功，并已人工视觉核对三路布局及最终画面。

## 执行经过与观察

1. 根据实时图像确认刷子、绿盒、两块蓝色方块和簸箕的位置。只控制左臂。
2. 夹住刷柄并短距离试提，确认刷子随夹爪移动后抬起。
3. 先扫较近方块。早期短扫存在刷毛边缘擦过方块的情况，调整刷头居中和高度后，将其扫过簸箕前缘。
4. 处理较远方块，先向前调整以避开簸箕侧壁，再扫过入口。抬起刷子后确认两块均已入盘。
5. 用户要求刷子放回初始位置后，撤回尚未松爪的中间平放尝试，将刷子送回绿盒旁；靠稳、松爪、抬升撤离，确认其保持稳定。
6. 左臂沿空中路径回到初始停放目标，然后停用；保存最终图像与状态，结束录像。

抓取分离时绿盒发生了小幅位移。最终刷子回到同一原始放置区域，保持靠盒姿态；簸箕未被操纵。中间平放尝试出现高度跟随偏差后未继续下降，随后撤离；该处没有释放刷子。遥测共 9408 条，未出现错误码或 worker fault；72 次记录的控制指令均未返回命令错误。

最终左臂各关节相对初始实测值的最大差为 0.809°；右臂最大读数差为 0.022°。夹爪最终为空。停用前发出夹爪收拢目标，但未把夹爪完全回到初始开度作为完成条件。

## 图像与原始记录

- [初始头部画面](external_initial.jpg)
- [两块均入盘、刷子抬起后的画面](brush_clear_after_success_external.jpg)
- [右腕确认两块入盘](brush_clear_after_success_gemini_right.jpg)
- [刷子松开后撤离的画面](released_clear_external.jpg)
- [最终头部画面](external_final.jpg)
- [合成视频最终帧](composite_preview_2699.jpg)
- [左臂初态](left_initial.json)、[左臂终态](left_final.json)、[右臂初态](right_initial.json)、[右臂终态](right_final.json)
- [指令日志](commands.jsonl)、[遥测日志](telemetry.jsonl)、[合成元数据](composite_metadata.json)

## 使用范围

本次依据用户指令、机器人当前服务状态与本轮实时图像执行。未访问云存储、既有本地任务缓存或技能文件。代码、录像、图像与记录均保存在本轮新建目录。机器人控制指令仅发送到左臂。

## 当时追加的过程记录

# Independent brush sweep

User task: Left arm picks up the brush next to the green box, sweeps both blue blocks into the fixed dustpan, and sets down the brush. Right arm for observation only.

Only task instructions and live service observations used. No cloud storage, historical cache, or skills accessed.

## Live session

- 17:29:00 Initial views confirm brush beside green box, two blue blocks on table, dustpan fixed to left in external view. Three MP4 streams recording. Right arm remains stationary for observation.

- 17:30:31 Brush gripped at handle with left arm. Short test lift visibly moved brush with gripper; bristles rotated toward vertical. Green box shifted slightly during separation. No contact by right arm.

- 17:32:30 First (initially nearer) blue block swept across dustpan lip and visibly fully inside tray in external and right-wrist views. Earlier edge catches corrected by centering block under bristle row and lowering sweep height.

- 17:37:17 Both blue blocks visibly inside fixed dustpan. Second block was first moved forward to clear the raised side, then swept inward across the lip. Preparing brush set-down; right arm has remained stationary and observation-only.

- 17:39:21 User updated deliverables: one 90-second composite, left wrist upper-left, right wrist upper-right, head/global camera below. User also specified returning brush to its initial location beside the green box. Returning brush there; no release occurred during the intermediate flat set-down approach.

- 17:40:42 Both blocks verified fully inside dustpan. Brush released beside green box in initial area and remained stable after left arm withdrew. Left arm returned to initial parked joint target and was disabled; right arm was never commanded.
