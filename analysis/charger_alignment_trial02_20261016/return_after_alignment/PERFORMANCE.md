# 收尾资源与耗时

总墙钟1502.980秒；续费等待1048.642秒；宿主处理128.242秒。不是纯推理时间。

```json
{
  "window_start": "2026-10-16T21:17:16.319+08:00",
  "window_end": "2026-10-16T21:42:19.299+08:00",
  "wall_elapsed_s": 1502.9797809123993,
  "unique_model_response_records": 87,
  "top_level_tool_calls": 87,
  "tool_calls_by_name": {
    "exec": 87
  },
  "task_json_commands": 24,
  "task_json_commands_by_tool": {
    "move_to": 20,
    "set_gripper": 4
  },
  "host_review_commands": 39,
  "host_review_commands_by_name": {
    "renew": 10,
    "tool_json": 24,
    "select-left": 1,
    "observe": 4
  },
  "host_outcomes": {
    "completed": 39
  },
  "host_command_wall_s": 128.24232777627185,
  "token_totals": {
    "input_tokens": 11034709,
    "cached_input_tokens": 10881920,
    "cache_write_input_tokens": 0,
    "output_tokens": 23242,
    "reasoning_output_tokens": 2630,
    "total_tokens": 11057951
  },
  "pure_server_inference_s": null,
  "nested_tool_calls": null,
  "notes": [
    "Return window only; original alignment statistics remain frozen.",
    "Counting categories overlap; cached input is part of input, reasoning is part of output.",
    "Host time includes planning, transport, settling and capture, not pure inference.",
    "Local response/call IDs deduplicated; post-window archival excluded.",
    "Wall time includes 1048.642 seconds of stationary subscription renewal waiting; not robot motion or pure model inference."
  ]
}
```
