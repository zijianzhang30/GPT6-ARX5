# R5 控制接口核对记录

核对日期：2026-09-22。机械臂已拔下，全程离线。检查对象为下载的 ARXroboticsX/R5 master 包及本机已编译的 Python 包。

## 确认的自由度

六个 revolute 关节；另有第七个夹爪电机位置通道。夹爪两指联动，占一个独立开合自由度。

- `set_joint_positions(positions)` 输入 **6 个弧度值**。Python 包设置状态 5（POSITION_CONTROL）；底层循环只写索引 0..5。
- `set_ee_pose_xyzrpy(xyzrpy)` 输入米、弧度的六维位姿，封装成 `[x,y,z,qw,qx,qy,qz]`，设置状态 4（END_CONTROL）。此 SDK 的末端控制参考系有初始化约定，不能直接假定等于可视化的绝对 URDF 基座系。新离线程序自己的 FK/IK 始终使用 URDF 基座系。
- `set_catch_pos(pos)` 调用 `set_catch(double)`，写第七个目标通道。官方键盘示例增加为张开，减少为闭合。参数不是毫米。
- `get_joint_positions()` 返回 **7 个数值**；第七个包含夹爪反馈。过去「没有夹爪反馈」的说法不正确。
- Python `SingleArm` 初始化会创建控制器并调用 `arx_x`，不能把创建这个对象称为纯只读检测。
- Python 对带夹爪从臂的官方示例使用 **type=0**；ROS2 single_arm.yaml 的 arm_end_type 也为 0。旧程序曾错误地使用 1，现已移除。

## 六关节软件边界

从版本固定的本地 SDK 构造器和 `statePositionControl` 限幅逻辑读取；不是 URDF 的通用 ±10 rad，也不是对用户实际机械臂机械端点的测量。

| 关节 | 下限 rad | 上限 rad | 约合角度 |
|---|---:|---:|---|
| J1 | -3.14 | 2.618 | -179.9° … 150.0° |
| J2 | -0.1 | 3.6 | -5.7° … 206.3° |
| J3 | -0.1 | 3.0 | -5.7° … 171.9° |
| J4 | -1.29 | 1.29 | -73.9° … 73.9° |
| J5 | -1.483529864 | 1.483529864 | -85° … 85° |
| J6 | -1.745329252 | 1.745329252 | -100° … 100° |

这些边界应用于所有模拟关节目标与逆运动学。速度和加速度限制减少突变，但不能代替碰撞检测。

## 夹爪单位：纠正此前推断

官方 Python 单臂手册给出夹持开口 **0–80 mm**，但未给出适用于本机设备的毫米到 `set_catch_pos` 数值映射。

ROS2 主从控制的回调把**主臂**的第七个反馈乘 5 后发给从臂。这是遥操作中的映射，不能据此推断同一夹爪的 `反馈 × 5 = 命令`。

本机 Python SDK 的二进制 `getJointPositons()` 逐项返回位置减初始化偏置，没有对第七项除以 5。`CatchPositionCtrl()` 还包含自己的位置偏置和控制逻辑，因此不能假设原始反馈直接等于零误差命令。

新适配器分别接受四个标定端点：闭合/张开命令、闭合/张开反馈；不硬编码倍率 5。模拟采用独立的 0–80 mm 开口状态，只有重新接入实际设备验证后才能建立真实毫米映射。夹持力、扭矩模式不增加自由度；本次界面不提供未经验证的力控制。

## 可重现证据

`python3 tools/audit_sdk.py` 会先校验 SHA-256，再读取 SDK 构造器常量并核对 URDF 关节数。二进制变化时脚本拒绝沿用旧偏移。

SHA-256：`30239795532e0d440842405f02092c85f95b5f4b0813c2bdf95b22d89960fa18`

符号检查：`ControllerThread::setJointPositions`、`ControllerThread::setCatch`、`ControllerThread::getJointPositons`、`ControllerBase::statePositionControl`。

原始资料：

- [官方 R5 仓库](https://github.com/ARXroboticsX/R5)
- [Python SingleArm 封装](https://github.com/ARXroboticsX/R5/blob/master/py/ARX_R5_python/bimanual/script/single_arm.py)
- [官方键盘示例](https://github.com/ARXroboticsX/R5/blob/master/py/ARX_R5_python/test_keyboard.py)
- 仓库内 `00-readme/01-python-单臂R5-SDK.pdf`：夹爪开口及控制参考系说明。
- 仓库内 `ROS2/R5_ws/src/ARX_R5_ros2_V7/arx_r5_controller/src/R5Controller.cpp`：主从映射与第七个反馈的用途。

已通过的是软件与离线仿真测试。未完成真实机械臂的零位、物理限位、夹爪映射、通信新鲜度、停机/退出行为和碰撞验证。

## 实机后端更新

已增加 `native_live` / `robot_worker.py` / `live_control.py`。默认网页为实机模式，连接按钮才会初始化 SDK。反馈角度驱动 URDF 模型，SDK 错误码和 CAN 远端接收监控用于拒绝过期控制。原始夹爪目标使用 SDK 0–5 范围；慢速夹爪控制中 0.1 的偏置仅用于相对点动起点，不作为毫米标定。实机初始化/运动测试仍待实际执行，不能把软件测试当成硬件验证。
