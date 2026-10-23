# 19:00:09 双臂失能与下沉

本轮机械任务失败。控制宿主PID1286212因R5ExecutionFault退出（code 1），故障后只读取相机和状态，没有发送动作、重新使能、恢复或重启。

最后请求于2026-10-20T19:00:03.546214+08:00开始，左臂持刷移动到后排两块外侧；相对前一命令规划位置约dx=-15、dy=-25、dz=-30毫米，保持当时刷头方向。右臂自18:39:39后仅保持观察姿态。本段不应重新播放。

终止时间：2026-10-20T19:00:09.169863+08:00。终止信息：

`enabled must be True; policy_execution_available must be True; An explicitly assigned control owner is required; A completed powered hold is required`

右臂事件“暂停保持反馈异常或跟随超限，已请求 SDK 保护模式”和左臂事件“已请求 SDK 保护模式；这不是物理急停”均在19:00:09。日志时间粒度不能确定同秒内完整因果顺序。根因未定位。

## 保留证据

- [故障前后29.9秒三视角视频](三视角视频/故障前后_三视角.mp4)，覆盖约19:00:00—19:00:30。
- [19:00:08.517全局帧](fault_frames/top_16.8.jpg)、[同刻右腕帧](fault_frames/right_16.8.jpg)及fault_frames内后续帧。
- [第一次故障后只读状态](fault_live01/arms.json)、[第二次只读状态](fault_live02/arms.json)；各目录保留三路原图。
- [最终全局图](fault_live02/external.jpg)、[机器可读故障摘要](incident.json)和[原始控制日志](control/events.jsonl)。

两次观察均显示双臂下沉，刷子落靠桌面/左夹爪；三块仍在簸箕外，固定簸箕和绿色盒仍可见。右腕故障后画面有左臂连杆近距离遮挡；不能凭图像排除接触，也不能据此确认碰撞是起因。

两臂均enabled=false、control_state=disabled、owner=null、policy_execution_available=false；error_codes为空不表示控制健康。左J5反馈约-90.54°，超出接口配置的-85°下限，是故障后状态，未尝试带该状态恢复。

## 未完成项

0/3入仓；受控放刷未完成；双臂原参考回位未完成。刷子和机械臂的重力下落不是这些步骤的成功证据。需要现场检查/承托后重新评估，不能自动重启旧宿主或重复失败目标。
