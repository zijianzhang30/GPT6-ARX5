# L1 / L2 记录与证据

> **执行前提：左右 CAN 已交换（2026-10-11 用户确认）。** 物理左臂使用 `2088335E5931 → can0 → 8765`；物理右臂使用 `208833765931 → can1 → 8766`。左右任务角色及腕部相机归属不交换。每次先核对当前接线、实时反馈和唯一保持宿主；旧序列号映射及硬编码恢复脚本不能直接套用。详见[统一 CAN 前提](can-mapping.md)。

## 来源索引

所有原始任务保留，用户现在把前四项和挂帽子统称 **L1：第一层任务验证**。这是试验分类，不是认证等级或已通过标记。

| 任务 | 原始 MD | 重点证据 |
| --- | --- | --- |
| 叠杯 | [CUP_STACKING_EXPERIMENT_RECORD_20261001.md](/home/tuojing/arx_r5_control/CUP_STACKING_EXPERIMENT_RECORD_20261001.md) | `analysis/cups_trial03_20261001/`历史完整流程；[10月7日第6/7轮补测](/home/tuojing/arx_r5_control/CUP_STACKING_EXPERIMENT_RECORD_20261007.md)含三路视频与资源 |
| 插笔 | [历史记录](/home/tuojing/arx_r5_control/PEN_INSERTION_EXPERIMENT_RECORD_20261002.md)、[10月7日第9轮补测](/home/tuojing/arx_r5_control/PEN_INSERTION_EXPERIMENT_RECORD_20261007.md) | 第9轮粗笔入杯及回位通过、全程无场景介入；三路录像及资源，31.699秒保持缺口单列；旧1—8轮无连续录像/独立token，细笔变体分开 |
| 插座 | [历史记录](/home/tuojing/arx_r5_control/CHARGER_INSERTION_EXPERIMENT_RECORD_20261001.md)、[10月5日第11轮](/home/tuojing/arx_r5_control/CHARGER_INSERTION_EXPERIMENT_RECORD_20261005.md) | 第7轮受控放回；第9、10轮故障证据；第11轮未抓起、左臂回位通过；未验证插入 |
| 预置充电头后插入 | [第1轮](/home/tuojing/arx_r5_control/CHARGER_INSERT_ONLY_EXPERIMENT_RECORD_20261005.md) | 三次局部尝试；夹持未验证、小步预览拒绝，末段代理丢失后失能下落；未插入、未受控回位，录像含约148.4秒缺图 |
| 插花 | [10 月 2 日](/home/tuojing/arx_r5_control/FLOWER_INSERTION_EXPERIMENT_RECORD_20261002.md)、[10 月 3 日](/home/tuojing/arx_r5_control/FLOWER_INSERTION_EXPERIMENT_RECORD_20261003.md)、[10月7日第6轮补测](/home/tuojing/arx_r5_control/FLOWER_INSERTION_EXPERIMENT_RECORD_20261007.md) | 第5轮最终纸杯变体成功；第6轮进入杯内后释放倾倒，完整目标未通过；视频及逐轮资源另存 |
| 挂帽 | [历史1—3轮](/home/tuojing/arx_r5_control/HAT_HANGING_EXPERIMENT_RECORD_20261003.md)、[10月7日第4轮](/home/tuojing/arx_r5_control/HAT_HANGING_EXPERIMENT_RECORD_20261007.md) | 第4轮人工预置、重新摆帽和移架后挂稳，释放撤爪与双臂回位通过；三路视频、逐response资源另存，不等同自主取帽或无干预成功 |
| 倒珍珠（第7项，分类待定） | [PEARL_POURING_EXPERIMENT_RECORD_20261005.md](/home/tuojing/arx_r5_control/PEARL_POURING_EXPERIMENT_RECORD_20261005.md) | 用户验收成功、允许残留；有洒落；抓取/放回/双臂回位通过，接收数量未独立核验 |
| 橘瓣抓放（第8项，分类待定） | [ORANGE_PICK_PLACE_EXPERIMENT_RECORD_20261005.md](/home/tuojing/arx_r5_control/ORANGE_PICK_PLACE_EXPERIMENT_RECORD_20261005.md) | 第4次局部抓取成功，抬升约9厘米、放回原支撑、独立稳定及双臂回位通过；对象为剥皮单瓣 |
| 抽屉拉出与推回（第9项，分类待定） | [DRAWER_PUSH_PULL_EXPERIMENT_RECORD_20261005.md](/home/tuojing/arx_r5_control/DRAWER_PUSH_PULL_EXPERIMENT_RECORD_20261005.md) | 两轮未抓稳、无5厘米行程；第1轮故障落桌，第2轮双臂受控回位通过，录像中断约40.59秒后续录 |
| 果冻抓放（第10项，分类待定） | [JELLY_PICK_PLACE_EXPERIMENT_RECORD_20261005.md](/home/tuojing/arx_r5_control/JELLY_PICK_PLACE_EXPERIMENT_RECORD_20261005.md) | 第1轮两次空提；第2轮换平台后三次试提仍未抓稳，无5厘米抓放；两轮双臂受控回位通过 |
| 双臂旋瓶盖（第11项，分类待定） | [BOTTLE_UNSCREWING_EXPERIMENT_RECORD_20261005.md](/home/tuojing/arx_r5_control/BOTTLE_UNSCREWING_EXPERIMENT_RECORD_20261005.md) | 第1轮故障失能落桌；第2轮暂停后续行完成放瓶/回位；第3轮对向布局及6°试转未完成退丝，瓶子放稳、双臂回位通过；均未完成3–5厘米分离 |
| 固定瓶身、左臂旋盖 | [10月5日前两轮](/home/tuojing/arx_r5_control/FIXED_BOTTLE_LEFT_CAP_EXPERIMENT_RECORD_20261005.md)、[10月6日第3轮](/home/tuojing/arx_r5_control/FIXED_BOTTLE_LEFT_CAP_EXPERIMENT_RECORD_20261006.md) | 三轮未退丝/分离；第2轮闭合进度超时失能下落；第3轮上方斜夹、抬高重夹仍单侧脱开，无运行故障，双臂受控回位通过 |
| 左臂旋螺母入螺栓（分类待定） | [BOLT_SCREWING_EXPERIMENT_RECORD_20261005.md](/home/tuojing/arx_r5_control/BOLT_SCREWING_EXPERIMENT_RECORD_20261005.md) | 第1轮72°试转指令、滑移及重夹接触；未验证3圈，回位未完成；末段有人工操作与保持丢失，因果未确认；三路录像含两处明确缺口 |
| 左臂抽取中间书本（分类待定） | [BOOK_EXTRACTION_EXPERIMENT_RECORD_20261006.md](/home/tuojing/arx_r5_control/BOOK_EXTRACTION_EXPERIMENT_RECORD_20261006.md) | 第1轮未完成5厘米；第2轮放宽标准后角部及中段仍未验证抽出，最终双臂回位通过；人工拿书与录像末段恢复/尾部缺失分别记录 |
| 左臂擦黑板（分类待定） | [BLACKBOARD_WIPING_EXPERIMENT_RECORD_20261006.md](/home/tuojing/arx_r5_control/BLACKBOARD_WIPING_EXPERIMENT_RECORD_20261006.md) | 前两轮软布未验证擦除；第3轮硬质板擦完成有接触的短擦（含现场确认），放置及双臂回位通过；人工预置、早期右SDK故障/左臂下落及录像结束后再次故障各自记录，当前双臂失能；视频验证以该轮VIDEO_RECORD.md为准 |
| 左臂扫蓝色方块入簸箕 | [BLUE_BLOCKS_SWEEPING_EXPERIMENT_RECORD_20261006.md](/home/tuojing/arx_r5_control/BLUE_BLOCKS_SWEEPING_EXPERIMENT_RECORD_20261006.md) | 第1轮人工预置扫帚，2/2全部扫入且撤刷后稳定、用户验收；扫帚释放后倾倒平放稳定，左臂受控回位及右臂原位核验通过；录像后再现SDK故障/失能单列；视频见该轮VIDEO_RECORD.md |

新增：[左爪边缘推蓝块入红三角](/home/tuojing/arx_r5_control/BLUE_BLOCK_TRIANGLE_PUSH_EXPERIMENT_RECORD_20261006.md)。第1轮1个蓝块侧推及后侧补推进入区域，用户验收成功，撤开后稳定；左臂受控回位与右臂原位核验通过。右腕原位辅助观察、未夹取；初始一次右SDK恢复、两段录像SIGTERM结束及43.43秒缺口分别记录。视频、资源及公开对话见该轮目录。

插花新增：[10月10日第7轮](/home/tuojing/arx_r5_control/FLOWER_INSERTION_EXPERIMENT_RECORD_20261010.md)。从源杯自动取花、杆端入含填充物纸杯已验证；相机挤压经现场确认解除，但释放独立稳定未验证，末段左SDK故障、双臂失能下落、未受控回位。三路共87个MP4已封存，准备使能缺录与中间静止缺口单列；资源窗口及故障后的诊断/归档分开。

连接/初始化用 [MACHINE_INITIALIZATION_RUNBOOK.md](/home/tuojing/arx_r5_control/MACHINE_INITIALIZATION_RUNBOOK.md)，录像用 [THREE_CAMERA_RECORDING.md](/home/tuojing/arx_r5_control/THREE_CAMERA_RECORDING.md)。花任务 HTTP 连接拥塞修复见 [TRANSPORT_FIX.md](/home/tuojing/arx_r5_control/analysis/flower_insert_only_preflight_20261003/TRANSPORT_FIX.md)，不据此宣称所有历史超时原因已查明或全部消除。

## 每轮最少保存

- 冻结 `task_prompt.md`，记录目标、道具/容器、分工、试次数和成功标准；中途变化另记版本与用户原话。
- `initial_state.json`、`return_reference.json`、关键阶段多视角图、原始事件 JSONL。连续复用宿主时写明宿主日志位置、开始/结束时间与命令边界，结束时冻结本轮片段，不覆盖上一轮事件。
- `RUN_RECORD.md` 和 `status.json`：分别记录抓起、插入/挂放、释放、独立稳定、两臂回位；未发生的里程碑用 null/未完成。物理任务结果与完整流程结果分开。
- `recording/` 三路 MP4、逐帧元数据、manifest 和文件验证结果。说明提前停止、缺口、重复/缺帧及验证范围，不把历史只有照片或 AVI 的轮次改写成三路 MP4 全程录像。
- 创建STOP后仍须核验封口；进程消失但manifest仍为recording时，保留原状态并记录异常，不能改成正常completed。恢复副本另存，记录原文件哈希、可解码范围、缺失采样和重编码情况；恢复后的导出完成不等于原录制正常结束。抽书第2轮的末段恢复脚本仅适用于其已核验的MP4V结构，不通用重播。
- `DIALOGUE.md`：任务结束后统一导出可取得的公开用户/助手消息及公开询问，保留当时判断与后续更正；不导出内部推理、系统/开发者信息。工具证据另留原日志，不编造未取得的对话。终端粘贴中的疑似凭据脱敏，注明范围与截止时间。
- 用户要求资源记录时，保存任务起止边界、按 response ID 去重的 token 用量、缓存细分、可取得的客户端条目时长及机器人命令耗时。缓存包含于输入，推理输出包含于输出；客户端条目时长、工具等待与服务器纯推理时间分别标注，未知的服务端指标留空。本轮实现范例见倒珍珠目录的 `collect_metrics.py` / `PERFORMANCE.md`。

## 按需剪辑三视角证据

用户要求同屏剪辑时，参照当前网页布局；本机双臂页面为上排左腕/右腕、下排全宽全局。三路按原录像共同采样帧索引使用相同时窗，不能各自寻找动作起点后错位拼接。核心版可去除等待，但动作保留原速、画面注明剪辑且保存输出帧到原帧/现场时间的映射；连续版和原始录像保留作复核。缺帧、重复帧和人工调整不掩盖，不称硬件曝光同步。逐帧解码验证成片；首末帧检查只能支持原录像端点可解码。

### 用户要求倍速精简包时

可另做每任务1—3分钟的倍速浏览版；这是用户指定的浏览用途，不覆盖原速证据。三路保持同一时间轴，画面标注倍率、来源试次及结果，保存输出时间到来源视频时间的映射。若来源本身已剪去等待或仅为选段，继续保留其剪辑映射与范围说明；历史缺录、人工介入和失败不能因压缩而消失。

精简包可为每类任务选代表试次，但所有已取得的主实验MD、成功与失败记录、资源口径和skill仍须可查。清单区分“本包未收录原片/高频日志”与“历史未录制/原文件缺失”，原片留本机；使用相对链接及离线HTML入口。验收实际包大小、各片时长、成片全帧解码和ZIP完整性。倍速片长不计作实验耗时，离线剪辑/报告资源不追加入冻结的执行窗口。

2026-10-07实例：[报告与精简包构建目录](/home/tuojing/arx_r5_control/analysis/real_robot_report_20261007/)，含来源清单、倍速映射及验证结果；仅为离线整理脚本，不触发机器人动作。

## 计时与结论模板

```markdown
# L1 — <任务> — <日期/试次>

协议/变体：
用户目标与分工：
初态/回位参考来源：
录像目录及起止：
控制日志位置及本轮边界：

| 里程碑 | 时间（含时区） | 证据/结果 |
| --- | --- | --- |
| 开始保持准备或健康宿主进入本轮 | | |
| 首次物理动作 | | |
| 抓起（预置持物写不适用） | | |
| 放置/插入/挂放 | | |
| 完全释放及独立稳定复核 | | |
| 左臂/右臂回位 | | |
| 任务结束 / 录像结束 | | |

局部重试、拒绝、运行故障与人工介入：
物理任务结果 / 完整流程结果：
总用时及口径：
录像验证与公开对话链接：
未解决问题：
```

开始时间为本轮保持准备/续行边界；准备等待与运动阶段分别注明。总用时包括观察、审核、工具往返、等待和收尾，不能称纯机械运动或纯模型推理时间。用户判定、图像监督核验和无人工场景介入结果分别统计；不同初态/目标/保护版本不混成固定策略成功率。

拧螺丝新增：[10月11日旋下第1轮](/home/tuojing/arx_r5_control/BOLT_UNSCREWING_EXPERIMENT_RECORD_20261011.md)。右臂自主拾近端、左夹六边形螺帽逆时针旋下的新协议；准备时右SDK重连报电机2故障类型12并退出，首段未回初始位姿、未拾取/旋下；右电源重插后恢复，原初始位姿两次核验、右臂第2次局部拾取通过，左爪接近时触盒，撤开后续抬升到位超时失能，人工调整；未旋下/最终受控回位。三段三路132个MP4正常封存，90秒三视角倍速另存，缺采样原样保留；旧旋入三圈试验独立保留。

倾倒小球新增：[10月11日第2轮](/home/tuojing/arx_r5_control/PEARL_POURING_EXPERIMENT_RECORD_20261011_TRIAL02.md)。初始回位及首次抓杯通过，源杯目视空、接收杯内有小球；接收数量未核验。用户停录时仍夹杯，未释放或最终回位。三路81段正常封存，完整原速及90秒三视角另存。

第2轮17:16收尾更新：用户要求导出后续行、回位不录像。源杯释放及侧向撤离后独立稳定两次通过；人工移杯换下一任务道具后重新清场，最终双臂受控回原参考两次通过（原2.5°）。90秒视频只覆盖首次停录前，后续证据见该轮final_return_after_video；接收数量未核验仍保留。


橘瓣抓放新增：[10月11日第2轮](/home/tuojing/arx_r5_control/ORANGE_PICK_PLACE_EXPERIMENT_RECORD_20261011_TRIAL02.md)。人工转向后第6次局部夹取成功，FK抬升约6.1厘米、放回释放/独立稳定通过，用户验收；停录后双臂受控回原参考两次通过，回位按用户要求未录像。三路99个MP4正常封存，90秒三视角倍速已全帧验证；早期失败、人工介入、缺采样和重复帧单列。


扫蓝块新增：[10月11日第2轮](/home/tuojing/arx_r5_control/BLUE_BLOCKS_SWEEPING_EXPERIMENT_RECORD_20261011_TRIAL02.md)。左臂自主拾绿色盒旁刷柄、2/2扫入并撤刷稳定、工具靠盒释放独立稳定、双臂原2.5°回位两次通过；右臂只辅助观察、未接触簸箕，清场后无人工介入，未观察到双臂碰撞。三路93个MP4正常封存，采样缺失与重复单列；早期未抓稳/刷毛偏高/角部漏扫与动作前拒绝保留。
