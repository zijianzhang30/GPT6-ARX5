# 资源与耗时

实机录像窗口：2026-10-05T15:35:11.005990+08:00 至 2026-10-05T15:54:24.401736+08:00，共 **1153.396 秒**。含观察、规划、工具往返、等待、运动、放置和回位，不是纯机械运动时间。录像帧时长与墙钟窗口因采样边界稍有差别。

| 项目 | 数值 |
| --- | ---: |
| 去重 response 数 | 110 |
| 输入 token | 16,195,476 |
| 其中缓存输入 | 15,772,160 |
| 非缓存输入 | 423,316 |
| 输出 token | 48,543 |
| 其中推理输出 | 18,366 |
| 总 token（输入+输出） | **16,244,019** |
| 缓存写入 token | 0 |
| 客户端 Reasoning 条目生命周期累计 | 94.682 秒 |
| 主机命令处理累计 | 443.567 秒 |
| 命令之间等待 | 686.356 秒 |
| 首条前/末条后时间 | 23.473 秒 |

命令范围 135–255，121 个条目，结果 {'completed': 120, 'rejected': 1}。条目包括观察、选择工作臂、续段和动作。命令处理包括规划、执行、到位和采图；客户端各类条目时长可能重叠，不与墙钟或主机时间相加。

每个 response 的重复输入上下文均计入；缓存输入已包含于输入，推理输出已包含于输出。以上为本地 usage 元数据，不是费用账单。纯服务器推理时长、TTFT、生成速度均未知，保持 null，不用客户端条目时长冒充。

累计快照复核：16,008,576 + 235,443 = 16,244,019，与逐 response 去重一致。原因：Context-compaction response recorded separately but not added to cumulative token_count snapshots. 详见 [USAGE_RECONCILIATION.json](USAGE_RECONCILIATION.json)。快照与逐条总量是两种复核口径，不能再次相加。

原始汇总：[PERFORMANCE_USAGE.json](PERFORMANCE_USAGE.json)；[逐 response 记录](response_usage.jsonl)；[客户端计时](client_item_timings.jsonl)；[主机计时](COMMAND_TIMING.json)。只导出用量与时间元数据，不导出内部推理文本。准备和视频合成/文档整理不属于此实机窗口。

录像结束后、下一任务请求前的归档窗口单列于[ARCHIVE_USAGE.json](ARCHIVE_USAGE.json)。之后的合成验证与新任务准备重叠，归入下一任务准备统计，不与本轮实机用量混合。
