# 第10轮资源统计

统计窗口：2026-10-11T02:48:51.765Z 至 2026-10-11T02:56:20.688680+00:00。按去重response汇总，截止后的回复或恢复不计入。

- response记录：76
- 输入token：8150867，其中缓存 7972736
- 输出token：31753，其中推理输出 6635
- 合计token：8182620

缓存包含在输入内，推理输出包含在输出内，不能再次相加。客户端item生命周期与命令间等待不等于纯推理耗时；服务端纯推理、TTFT不可得。资源元数据不是费用账单。

详情见PERFORMANCE_USAGE.json、response_usage.jsonl、client_item_timings.jsonl。公开对话见DIALOGUE.md，不导出内部推理文字。
