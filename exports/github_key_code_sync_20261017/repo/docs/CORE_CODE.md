# 关键代码入口

本仓库保存 ARX R5 双臂工作台、逐段视觉监督工具和实机任务技能。技能是基于实验记录的监督流程，不是可直接重放的固定坐标策略。

| 模块 | 入口 |
| --- | --- |
| 工作台及设备状态 | `app.py`、`control.py`、`live_control.py`、`worker_control.py`、`robot_worker.py`、`web/` |
| 厂商 SDK 桥接 | `native_live/bridge.cpp`、`native_live/CMakeLists.txt`、`sdk_contract.py` |
| CAN 恢复 | `connect_can.sh`、`tools/rebuild_left_can_bridge.py`、`tools/restart_left_can_bridge.py`、`tools/restore_can.sh` |
| 双臂策略和末端规划 | `r5_dual_policy.py`、`r5_policy_backend.py`、`r5_cartesian.py`、`r5_official_solver.py`、`policy_trajectory.py` |
| 监督、控制交接与回位 | `tools/held_policy_review.py`、`held_policy_handoff.py`、`initial_review_handoff.py`、`reviewed_task_handoff.py`、`reviewed_return.py`、`review_telemetry.py` |
| 相机和三路录像 | `camera_streams.py`、`record_workbench.py`、`tools/record_three_cameras.py` |
| token 和调用次数 | `tools/collect_experiment_usage.py`、[统计口径](EXPERIMENT_USAGE.md) |
| 实验技能 | `skills/arx-r5-tabletop-tasks/`、`skills/jelly-grasp/`、`skills/push-blackboard-eraser/` |
| 离线回归测试 | `tests/` |

## 依赖与现场配置

统计工具只需要 Python 标准库。机器人控制所需依赖、SDK 路径及原生编译说明见根目录 README、`requirements-policy.txt`、`native_live/CMakeLists.txt` 和 `docs/SDK_AUDIT.md`。`vendor/GPT-Policy-main/` 保留既有上游来源与许可证。厂商 SDK 库、相机驱动及本机编译产物需要单独安装；本次源码同步不提供这些二进制。

本机物理左臂为 `2088335E5931 → can0 → 8765`，物理右臂为 `208833765931 → can1 → 8766`；具体前提见[CAN 映射](../skills/arx-r5-tabletop-tasks/references/can-mapping.md)。在其他机器上应核对设备序列号、接线、路径和接口，不能只按旧设备编号启动。SDK 连接可能使能并初始化回零，实际操作须遵循技能中的现场确认与恢复流程。

旧实验坐标配置和本机证据路径仅作历史参考，不代表通用标定或可直接执行的任务脚本。用户本轮 prompt 和新观察决定任务对象、初态与验收标准。

## 源码同步范围

2026-10-17 更新控制交接、CAN 恢复、相应离线测试和任务技能，并增加通用离线统计工具。录像、`analysis/`、`recordings/`、`exports/`、原始会话、安装包和编译输出未加入本次提交。既有仓库历史保留；本次没有重写历史或删除历史资产。
