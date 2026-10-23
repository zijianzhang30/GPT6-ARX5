# 实验 token 与调用次数统计

`tools/collect_experiment_usage.py` 是从既有实验归档脚本抽取的离线工具，仅使用 Python 标准库；不访问机械臂、相机、模型 API 或网络。适用于包含 `token_usage_record` 的本机 Codex rollout JSONL。仿真若使用其他日志格式，需要按下述字段转换，不能直接把仿真动作轮数当成模型响应数。

## 使用

```bash
python3 tools/collect_experiment_usage.py \
  --session-log /path/to/rollout.jsonl \
  --start 2026-10-17T15:44:34.092+08:00 \
  --end 2026-10-17T16:16:35.727+08:00 \
  --robot-events /path/to/final_events.jsonl \
  --output /tmp/experiment-usage-new
```

起止时间是示例，必须替换为本轮记录的实际边界。`--session-log` 可重复指定，跨文件仍按 ID 去重；机器人事件文件可省略。可用 `--task-end` 指定任务核验结束时刻，将机器人请求分成任务期间与其后收尾两部分，不根据命令备注猜测“回位”。收尾可能还包含放置、撤离等操作。

输出目录内创建：

- `USAGE_SUMMARY.json`：时间窗口、分项 token、不同层级的次数、缺失字段和解析诊断。
- `response_usage.jsonl`：响应 ID、记录时间和用量计数。
- `tool_calls.jsonl`：顶层工具调用 ID、名称、类型和时间。

工具拒绝覆盖已有输出；复算请换一个输出目录。不会导出对话、内部推理、工具参数或结果，也不会复制源日志。不要将含凭据或对话的完整 rollout 上传 GitHub。

## 统计口径

| 字段 | 来源及含义 |
| --- | --- |
| `unique_model_response_records` | 窗口内 `token_usage_record.payload.response_id` 去重数量。是可取得的本地响应记录，不是已对账的服务端请求或计费尝试次数 |
| `top_level_tool_calls` | `response_item` 中 `function_call` / `custom_tool_call` 按 `call_id`（缺失时 `id`）去重 |
| `nested_tool_calls` | 保留 `null`；不从 `functions.exec` 的代码文本猜测内部调用次数 |
| `robot.json_requests` | ARX 事件中的 `request` 数，包括执行前被拒绝的请求；不等同于完成动作数 |
| `robot.host_finished_commands` | `review_command_finished` 数，含观察、续期、空爪准备等；结果另按 `outcome` 分类 |
| `robot.empty_gripper_internal_targets` | 空爪准备程序内部目标数，单列，不加到模型调用或任务动作数 |

不同层级可能描述同一个操作，不能相加。机器人事件文件须是单份原始日志或按字节边界冻结的片段；工具不把重复拼接的机器人事件当成多个独立动作。

token 求和使用去重的逐响应 `usage`。重复且用量相同的 ID 只计一次；同 ID 数据冲突时停止并要求核对。`token_count` 的累计快照只记出现次数，不求和、不与逐响应总量叠加。

- 总 token = 输入 + 输出。重复上下文每次请求都会计入。
- 缓存输入属于输入，推理输出属于输出，都不能重复相加。
- 非缓存输入 = 输入 − 缓存读取输入；其中仍可包含缓存写入。
- 普通输入 = 输入 − 缓存读取 − 缓存写入。
- 缺失字段为 `null`，不冒充 0；没有逐响应记录时，不能从“记录数为 0”推断没有模型调用。
- 不计算真实费用。不同模型、服务档位、缓存类别的费率不同；本地计数不是账单。

## 时间窗口与边界限制

时间按时区解析后比较，包含起止端点，按日志记录时间归属；跨边界请求和延迟到达的 usage 可能不完整。不用请求开始时间或截图时间冒充响应计费时间。机器人已停止不代表最新 usage 已全部写入，应待本轮日志稳定后另存复算结果。

`wall_elapsed_s` 是两个给定边界的差。控制命令时长包含规划、执行、稳定等待和抓图，不是纯运动或纯推理；本工具不提供服务端 TTFT 或推理速度。工具执行和模型等待可能重叠，不能随意将耗时相加。

## 真机与仿真比较

先对齐任务 prompt、对象、验收标准、模型、推理强度、输入信息和统计范围。记录实际 `service_tier`；不能用当前配置证明历史请求的速度档位。建议分别报告成功次数/总轮数、输入/缓存/输出 token、实际总时长、人工干预及终止原因，调用次数用于解释流程。

准备、初始化、任务、回位、剪辑归档应有明确边界；两边统一范围后再比较。不要事后删除失败重试的用量。独立会话可减少跨任务历史差异；旧长会话数据保留原始口径。

## 验证

```bash
python3 -m unittest discover -s tests -p 'test_collect_experiment_usage.py' -v
```

测试覆盖去重、跨文件重复、冲突用量、时区边界、缓存包含关系、缺失数据、累计快照隔离以及机器人拒绝与收尾分项。另用本机冻结实验日志复算对照旧归档，不将这些原始日志随源码发布。
