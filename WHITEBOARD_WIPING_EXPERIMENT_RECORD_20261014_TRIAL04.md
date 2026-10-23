# 左臂自主抓板擦擦白板 · 2026-10-14 第4轮

## 结果

**整体擦除未完成，按完整任务标准记失败；自主抓取、放稳板擦和双臂回位通过。** 数字6部分笔画擦掉，仍有残迹；G、P、T及下划线未清除。没有把划动或遮挡算作擦除成功。

## 本轮协议

> Pick up the board eraser with the left arm and erase the writing on the whiteboard.

用户取消误输入的推红区任务，确认“已摆放完成并退出，可立即急停”。本轮左臂从桌面自主抓蓝色板擦、擦除银色边框白板上的GPT6；右臂只改变观察角度。继承三路MP4和实验Markdown要求。误输入的推任务零硬件动作，记录独立保留，不混入本轮录像。

默认初始位姿使用用户刚确认的厂商HOME：六关节反馈零位，参考[return_reference.json](analysis/whiteboard_wiping_trial04_20261014/return_reference.json)，源自factory_home_restore_20261014。未将旧推异形块偏转姿态、SDK重连或新会话锚点当作HOME。

## 执行与证据

| 阶段 | 结果与证据 |
| --- | --- |
| 初始核验 | 11:40:37/41，双臂实测与指令均在原2.5°内，见initial_home_verified.json |
| 录像开始 | 11:41:11.710，三路通过新帧门禁后才执行首个动作 |
| 自主抓取 | 左01–15接近、竖直方向夹蓝色外壳；0.72开度首次试提不明确，改0.64后试提及25毫米续提有稳定随动和离桌证据，见pickup_verified/ |
| 观察与运输 | 左16–20移到白板，右01在底座附近转向观察；一次只动一臂，查看整臂、工具及边框间隙 |
| 部分擦除 | 左21纵向25毫米指令试擦，左22–23抬开观察，数字6部分笔画消失，见first_erase_effect/ |
| 后续尝试 | 左24–28横向短擦未见T明显变化；左29空中调整约5°倾角、左30接近、左31横向及左32纵向短擦后再次抬离检查，T仍清晰，见wiping_end/ |
| 结束擦拭 | 按连续无进展停止条件结束接触；擦垫有效接触面积和压力未量化，不能据此归因于墨水或擦具材料 |
| 放置 | 左35–42移到白板右侧空桌面并逐段降低；左43–47每次增加0.02开度至0.74，左48–49抬爪撤离 |
| 独立稳定 | release_check1/及release_check2/相隔约10秒，板擦留在桌面、未随空爪移动 |
| 回位 | 左50–55六段、右02一段受控回到HOME；12:00:43/46两次核验通过，见final_home_verified.json |
| 停录 | 12:00:47.718正常STOP，60个MP4验证通过，见VIDEO_RECORD.md |

末次两次HOME核验：左最大实测误差1.103759°、指令0.002824°；右最大实测0.688483°、指令0.001871°。两臂ready/enabled/holding、无错误码。左空爪开度0.74，右约0.00242；本轮回位核验为六关节，不要求夹爪回原开度。

## 边界与限制

全程复用唯一健康宿主PID1720232 / PTY3700；原始live目录仍为whiteboard_wiping_trial01_20261013/control。本轮片段按起止字节冻结到[control_archive/](analysis/whiteboard_wiping_trial04_20261014/control_archive/)，含对应观察图、状态和边界哈希。CAN沿用已交换映射：物理左5E5931→can0→8765，物理右765931→can1→8766。未重启SDK、未改保护阈值，未观察到运行故障或两臂碰撞。

只读候选中存在IK、关节余量和预算拒绝；文件存在不代表执行。8毫米下探候选未执行；两个同编号替代候选亦未执行。一次在前段仍移动时的只读规划被状态断言拒绝，等待正常完成后重算，没有运行故障。门禁两次暂缓等待新帧。实际57个硬件动作以[action_summary.json](analysis/whiteboard_wiping_trial04_20261014/action_summary.json)及原始事件为准。

这里的毫米数是TCP指令，未校准为擦垫实际位移；归一化开度不是夹持力。观察到6的局部擦除不等于可靠擦净整块白板。需要重新建立能覆盖笔画的有效擦垫接触，不能直接复播本轮轨迹作为成功策略。

## 文件

- [三路原始MP4](analysis/whiteboard_wiping_trial04_20261014/recording/) · [录像统计与验证范围](analysis/whiteboard_wiping_trial04_20261014/VIDEO_RECORD.md)
- [详细运行记录](analysis/whiteboard_wiping_trial04_20261014/RUN_RECORD.md) · [公开对话](analysis/whiteboard_wiping_trial04_20261014/DIALOGUE.md)
- [资源与耗时](analysis/whiteboard_wiping_trial04_20261014/PERFORMANCE.md) · [最终场景](analysis/whiteboard_wiping_trial04_20261014/final/)
- [不可变HOME参考](analysis/whiteboard_wiping_trial04_20261014/return_reference.json) · [两次最终核验](analysis/whiteboard_wiping_trial04_20261014/final_home_verified.json)

录像已停止，健康保持宿主继续运行。后续新任务仍需读取实时状态和新图。

## 用户追加：90秒三视角导出

[播放90秒三视角视频](/home/tuojing/arx_r5_control/exports/whiteboard_wiping_trial04_20261014_90s/whiteboard_wiping_trial04_full_3view_90s.mp4)。上排为左腕/右腕，下排为全局；1280×1152、30 fps、2700帧，准确90秒，约13.06倍速。覆盖本轮全部录制时段，包括抓取、擦拭、放置与最终回位，不剪去等待；原速60个MP4保留。视频标注本轮未完整擦除，不改写失败结论。

全部2700帧解码、时间轴首尾、三路共同采样索引以及60个原始片段均有覆盖的检查通过。倍速浏览会抽帧，短暂接触仍应查原速文件；输出帧来源映射、缺采样/重复状态及验证保存在[导出目录](/home/tuojing/arx_r5_control/exports/whiteboard_wiping_trial04_20261014_90s)。文件大小15,901,565字节。

擦白板技能及证据索引已更新并同步两份本地技能目录，格式检查通过；更新后快照存于本轮`skill_snapshot_after/`。
