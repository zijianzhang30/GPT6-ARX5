# 资源与耗时 · 夹取果冻第2轮

冻结执行窗口：2026-10-12 19:34:02.469–19:58:15（UTC+8），约1452.531秒。含故障信息确认、SDK恢复、观察、工具往返、抓取和回位；不是纯机械运动时间。后续离线文档和技能更新不计入。

按response ID去重的本机元数据：185条；input 23,658,514、其中cached 23,212,416、uncached 446,098；output 69,516、其中reasoning output 14,365；total 23,728,030。cached属于input、reasoning属于output，不能重复相加；反复携带上下文按每次请求计数。此统计不是账单。完整统计和独立累计快照交叉校验见PERFORMANCE_USAGE.json。

宿主已完成125个复核命令（含observe/renew/选择侧，并非全是动作），命令处理合计377.814秒，命令前等待合计885.421秒。等待含人工阅读、工具往返及调度，不能称纯推理。客户端reasoning条目生命周期不完整，不据此计算模型推理耗时或tokens/s；服务端推理耗时、TTFT不可取得。视频各视角合计1324.7秒与墙钟窗口不同，缺录和停录后回位单列。

文件：metrics_baseline.json、metrics_end.json、response_usage.jsonl、client_item_timings.jsonl、DIALOGUE.md。仅导出公开对话与用量/时间元数据，不导出内部推理文字。
