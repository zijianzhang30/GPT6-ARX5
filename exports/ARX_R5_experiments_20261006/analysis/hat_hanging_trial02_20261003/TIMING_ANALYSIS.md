# 挂帽第 2 轮：耗时统计

更新：2026-10-03T17:38:18.413011+08:00

范围：第 2 轮冷启动保持宿主已结束的命令；不包含前置准备和导出时尚未结束的等待。命令计数包含 observe、切换工作臂、预算续段及被拒绝请求，不能当作运动次数。

统计区间合计 52.69 分钟，其中等待下一指令 48.50 分钟（92.0%），宿主命令处理 251.60 秒。
最近 20 条命令：等待 413.33 秒，命令处理 35.95 秒；每条命令前等待中位数 16.83 秒。

| 操作 | 次数 | 命令处理合计（秒） | 结果 |
| --- | ---: | ---: | --- |
| observe | 37 | 1.633 | {'completed': 37} |
| set_gripper | 11 | 12.754 | {'completed': 9, 'rejected': 2} |
| move_to | 46 | 233.347 | {'completed': 45, 'rejected': 1} |
| select-right | 4 | 0.331 | {'completed': 4} |
| select-left | 4 | 0.354 | {'completed': 4} |
| renew | 11 | 3.176 | {'completed': 11} |

图像抓取：111 次，中位数 0.042 秒，最大 0.059 秒。它已包含在命令处理时间中，不重复相加。
拒绝原因及次数：{'A fresh, unconsumed observation is required': 1, 'Trajectory preview rejected before execution: Trajectory exhausts session joint travel budget; no motion or budget consumed; live session is not fault-latched. Adjust the target for a step-limit rejection; a session-budget boundary requires host renewal.': 1, "'note' is a required property\n\nFailed validating 'required' in schema:\n    {'additionalProperties': False,\n     'properties': {'note': {'type': 'string'},\n                    'positions': {'additionalProperties': False,\n                                  'properties': {'left': {'anyOf': [{'type': 'number'},\n                                                                    {'type': 'null'}]},\n                                                 'right': {'anyOf': [{'type': 'number'},\n                                                                     {'type': 'null'}]}},\n                                  'required': ['left', 'right'],\n                                  'type': 'object'}},\n     'required': ['positions', 'note'],\n     'type': 'object'}\n\nOn instance:\n    {'positions': {'left': 0.1072773820044713, 'right': None}}": 1}。动作前拒绝没有实际运动。

## 为什么慢，以及可验证的改进

- 主要时间位于动作间的审阅循环。读取新图、判断夹持和深度、离线规划、工具往返、对话、故障排查和文档整理混在这个区间，现有日志无法把它们精确拆成模型推理或人工等待。
- 观察臂改变观察位置、挂钩附近的短步对齐及逐步松爪增加了循环次数；这类几何不确定性需要改进视角和定位，而不是直接提高电机速度。
- 原 30 秒观察有效期仍启用，过期请求须重取图。采用先离线规划、再获取并审阅新图、及时下发的顺序，减少重复读取；不放宽期限。
- 控制器仍以原低速、到位及监督限制运行。命令处理包含实际运动和等待稳定，不能全部称为电机运动耗时。
- 进行中只保留机器事件日志和必要检查点，公开对话与完整 MD 放到结束后整理。录像检查继续保留。
- 后续优化需要增加独立的模型/工具阶段计时，再比较同一初态下的总时间、动作数、失败数与成功率；本轮统计不能推广为前四个任务的精确耗时。

原始数值及逐条命令见 [TIMING_ANALYSIS.json](TIMING_ANALYSIS.json)；运行 `summarize_timing.py` 可刷新快照。
