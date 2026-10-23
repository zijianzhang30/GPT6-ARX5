# 两侧转接器对调后，右臂及双臂使能成功（2026-10-11 10:43–10:45）

用户请求使能重新接好的右臂，确认两侧CANable已对调，并确认右臂承托、清场与急停条件。本轮右臂恢复真实ready并使能；左臂经明确授权短暂失能后重新使能。最终两臂由同一监督宿主维持静止带电保持，无任务运动。

## 接线与恢复

| 实际机械臂 | 当前适配器序列号 | 通道 | 上游 |
| --- | --- | --- | --- |
| 左臂 | 2088335E5931（原右） | can0 | 8765 |
| 右臂 | 208833765931（原左） | can1 | 8766 |

10:42:14内核重新枚举`765931`到ttyACM0，但can1不存在。初始左臂ready/enabled/holding，原单臂宿主PID778998有效；右侧旧SDK仍fault、反馈陈旧、失能无owner。

在三路录像中，通过右上游正常disconnect退出旧右worker。使用本轮 [restore_right_interface.py](restore_right_interface.py) 经只读检查与管理员认证，只建立右can1（index49）；左can0（index48）、owner与健康保持状态均保留。脚本只允许已确认的对调身份、右SDK已退出且can1缺失、左侧健康保持，没有修改通用恢复脚本。

## 从单臂切换到双臂

当前record_workbench代理会在另一臂initializing时拒绝心跳，非成对owner也不允许两臂并行使能；原左单臂入口不能直接无失能切换。检查此约束后，用户明确答复“允许，左臂也已稳固承托”，允许左臂暂时失能并在右侧检查后恢复。

10:44:48之前向原单臂宿主的会话59394发送stop，宿主正常退出；左SDK仍ready、失能、无owner。原日志由记录器移至 [live-policy-6680e54320fb_interrupted](../live-policy-6680e54320fb_interrupted/)。不是异常心跳丢失，也不算受控回位。

10:44:48通过右上游仅发送一次connect（已确认初始化可能回零）。约4秒后右侧ready、六关节有效、错误码为空、RX新鲜且增长；左右均通过原state_blockers检查。状态见 [右连接结果](right_after_connect.json)、[双臂使能前状态](before_dual_hold.json)。

随后运行项目已有`tools/held_policy_review.py --prepare-idle --working-arm right --tracking-reserve-deg 3.5`，由唯一成对owner逐侧完成原prepare_hold检查，约10:45:13两侧均进入holding。没有发送任务命令或目标，没有放宽反馈、心跳、相机、跟踪、稳定保持及关节限制。

## 最终状态与续行

当前唯一宿主PID931514、会话74089，目录 [dual_hold](dual_hold/)；两侧ready、enabled=true、moving=false、holding、同一owner、错误码为空、无worker故障。四次连续采样约3秒内，左RX增加4182、右增加4209，反馈年龄0–2ms。见 [双臂核验](both_holding_verification.json)与 [新全局图](holding_external.jpg)。

后续先重新读取实时状态与新图，再复用或受检交接此宿主；不要操作已退役的59394会话。新任务运动前重新录像并核验工作通道。本轮初始状态由宿主保存于`dual_hold/initial_state.json`；未执行任务回位验证。

## 录像和诊断意义

[三路录像](recording/)从10:44:01至10:45:34，93.211秒，每路931帧、两段MP4。全局928新帧、左腕926、右腕925；每路2个采样缺口，无HTTP请求错误。通过STOP正常封存，六个MP4首末帧均可解码，见 [核验](recording/playability_check.json)，未逐帧检查所有画面。保持程序继续运行。

两只原适配器在当前对调接线下均能正常工作。此次恢复不能单独定位此前零回包的原始根因，也不能据此宣称原左CANable损坏。最新接线、宿主和状态已同步到初始化手册、交接文档及skill共用流程。
