# 左臂自主抓板擦擦除白板GPT6 · 2026-10-13 第1轮

## 结果

**擦除任务失败：GPT6字迹仍清晰。自主抓取、放回释放和双臂回位通过。**

| 里程碑 | 时间（Asia/Shanghai） | 结果与证据 |
| --- | --- | --- |
| 准备与恢复 | 19:33—19:56 | 左SDK首次无CAN反馈；本机sudo重建左桥后，逐臂SDK恢复及使能 |
| 默认初始位姿 | 19:58:33 / 36 | 推异形块对应的原推蓝块参考，两次原2.5°核验通过 |
| 自主抓取 | 20:11—20:15 | 夹蓝色硬壳两侧；首试提不确定，收至0.7后第二次试提及抬升通过，见grasp_verified/ |
| 两次短擦 | 20:22 / 20:25 | 各25毫米Y指令，调整接触后仍无擦除，第二次工具轻微转动 |
| 放回及释放 | 20:29—20:38 | 逐步松爪至0.81，板擦独立留在空白处；两阶段图及final_scene复核 |
| 双臂回位 | 20:43:07 / 10 | 左7段、右3段，实测最大误差1.989° / 0.984°，指令也在原2.5°内 |
| 录像结束 | 20:43:21.841 | 三路165个MP4，帧数与首末解码通过；两处缺口明确保留 |

## 协议与执行

用户要求默认初始位姿、左臂自主抓硬质板擦、擦掉GPT-6；右腕可辅助观察，双臂不得干涉。画面字迹为GPT6。默认沿用用户此前定义“推异形块”的原推蓝块参考，逐字节冻结及SHA256见reference_provenance.json。可执行终点J2设0.8°以保留规划余量，对原参考仍使用2.5°，未把SDK初始化或新会话anchor当回位参考。

当前物理左臂在全局画面右侧：5E5931→can0→8765；物理右臂在画面左侧：765931→can1→8766。右臂仅观察并回位，没有碰板或协助抓持。清场确认后未观察到人工接管工具。

左臂从桌面自主对夹蓝色硬壳，黑色擦垫朝下。开度1→0.9→0.8，首个12毫米试提实测TCP仅约2.3毫米，未据此算抓起；收至0.7后第二次12毫米试提与后续25毫米抬升（实测约20.8毫米）配合多视角跟随/离面证据验证抓取。开度数值不是夹持力。

两次25毫米短擦未擦去数字6，抬开、移开遮挡后仍完整。第二次有工具轻微滑转，复核后终止擦除尝试，未持续加深下压。有效擦垫接触面积和压力没有被独立量化，原因仍未确定，不能将此记录成成功擦字策略。末端运动距离不等同擦垫实际滑动距离。

## 恢复、拒绝与录像边界

初次左SDK无回包及掉线日志保留；sudo非交互执行被认证阻挡，用户本机完成桥接后核验PID/接口变化，再逐臂恢复。没有改fault文字伪装ready、循环重连或放宽保护。恢复成功不代表根因已永久修复。

三次实时观察过期请求被拒绝，另有只读IK、步幅、预算和规划余量候选拒绝；未当作执行动作。记录文件存在不证明执行，动作以control_archive/events.jsonl和action_summary.json为准。

recording、recording02、recording03保存全部原片。首段STOP等待本机sudo；02收到来源未知的SIGTERM并自行封口，下一段被录制门禁拦下，宿主保持正常；03恢复后覆盖抓取、擦除尝试和最终回位，正常STOP。缺口、缺采样、重复及验证范围见VIDEO_RECORD.md。

## 文件入口

- [运行记录](analysis/whiteboard_wiping_trial01_20261013/RUN_RECORD.md) · [冻结协议](analysis/whiteboard_wiping_trial01_20261013/task_prompt.md)
- [三路视频与缺口](analysis/whiteboard_wiping_trial01_20261013/VIDEO_RECORD.md) · [资源和耗时](analysis/whiteboard_wiping_trial01_20261013/PERFORMANCE.md) · [公开对话](analysis/whiteboard_wiping_trial01_20261013/DIALOGUE.md)
- [原初始参考](analysis/whiteboard_wiping_trial01_20261013/return_reference.json) · [最终两次核验](analysis/whiteboard_wiping_trial01_20261013/final_reference_verification.json)
- [抓取证据](analysis/whiteboard_wiping_trial01_20261013/grasp_verified/) · [放置复核](analysis/whiteboard_wiping_trial01_20261013/placement_verified02/) · [最终画面](analysis/whiteboard_wiping_trial01_20261013/final_scene/)
- [冻结控制日志](analysis/whiteboard_wiping_trial01_20261013/control_archive/) · [动作摘要](analysis/whiteboard_wiping_trial01_20261013/action_summary.json)

收尾时两臂ready/enabled/holding、空爪，宿主PID1720232 / PTY3700仍保持；录像已停止。实时状态可能随后变化，下次动作必须重新读取。技能已更新两份本地镜像，未提交远程仓库。
