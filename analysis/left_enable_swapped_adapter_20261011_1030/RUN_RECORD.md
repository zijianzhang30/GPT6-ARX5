# 原右侧转接器改接左臂：使能成功（2026-10-11 10:30–10:32）

用户重新连接左臂电源与连接线，并确认将原右侧CANable改接物理左臂，只要求使能左臂。本轮**左臂成功恢复ready并使能，保持静止带电holding**；未提交任务目标，未向右侧SDK发送管理或控制命令。

后续状态更新：10:44用户明确允许左臂在稳固承托下短暂失能以初始化右臂，原单臂宿主正常退出，日志移至`analysis/live-policy-6680e54320fb_interrupted`；10:45两臂已由新双臂宿主统一使能保持。当前状态以[后续记录](../right_enable_swapped_adapter_20261011_1043/RUN_RECORD.md)为准，本文下述PID/会话为历史。

## 接口与连接

内核日志显示10:28:10原右USB断开、10:28:23原左USB断开，can1/can0均注销；10:29:06仅序列号`2088335E5931`重新枚举为ttyACM2。用户确认其现在连接的是物理左臂，因此不能继续套用旧的序列号左右分配。

原左脚本固定`208833765931`，不适用于这次换接。新增本轮专用 [restore_borrowed_adapter.py](restore_borrowed_adapter.py)，默认只读检查；检查两侧失能无owner、两个CAN接口不存在、无左worker、适配器身份正确且未占用，并只允许旧桥接的精确参数。经只读预检和管理员认证后，以pidfd正常退出两条USB拔除后遗留的slcand，再将借用适配器绑定为can0（index48、1Mbit/s）。没有重建can1或改变通用脚本的永久配置。

用户重新确认接线结束、左臂可靠承托、回零路径清空、人员退出且可立即操作电源或急停；[新图](clearance/external.jpg)已无桌边人员。三路录像正常且帧数持续增长后，10:31:15通过左上游8765仅发送一次SDK connect。约4秒后真实ready，错误码为空，六关节有效；后续连续读取RX为9481、10190、10897，反馈年龄1–2ms，状态检查无阻断。见 [连接后状态](after_connect.json)和 [使能前状态](before_enable.json)。

## 单臂使能保持

10:31:38启动项目已有 `supervised_policy.py --supported-supervision --wait-for-start --policy-interface joint --camera-mode both --arm left`，使用独立单臂owner经8768操作物理左臂。10:31:42完成原prepare_hold的健康、漂移与稳定保持检查，进入`holding_waiting_for_start`。程序继续维持原反馈、相机和心跳检查；未发送start，没有调用模型执行任务或提交任务运动目标。

当时宿主日志现归档于：[live-policy-6680e54320fb_interrupted](../live-policy-6680e54320fb_interrupted/)，原PID778998、工具会话59394已结束。停止录像与停止保持是两件事；该宿主后续退出有上述明确的用户授权。

四次连续核验均为`ready`、`enabled=true`、`control_state=holding`、`moving=false`、空错误码、无worker故障；约3秒RX增加4141，反馈年龄0–3ms。记录见 [holding_verification.json](holding_verification.json)、[使能后全局图](holding_external.jpg)、[can0统计](can0_holding.txt)。左臂使能后的微小稳定偏差仍在原检查范围内，不构成任务运动或受控回位验证。

## 录像与诊断边界

[三路MP4](recording/)覆盖10:31:07–10:32:01，54.540秒，每路544帧；全局542新帧、左腕540、右腕541，各有2个采样缺口，无HTTP请求错误。通过STOP正常结束，三个MP4首末帧均可解码，见 [核验](recording/playability_check.json)。未逐帧检查全部画面；录像结束后健康保持宿主继续运行。

左臂在替换后的通信链路上工作正常，此前同日上午原配置仍为零回包。这是新的隔离排查证据，但换接过程同时涉及适配器、线缆/接点与重新上电，不能单独确认原CANable损坏或原线缆损坏。当前接线例外已写入初始化手册和交接文档，后续不能按旧映射操作右臂。
