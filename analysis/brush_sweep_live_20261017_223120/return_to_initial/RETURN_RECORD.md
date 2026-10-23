# 机械臂回位记录

用户要求：恢复机械臂初始位姿。

已完成 13 段左臂运动，双臂静止并保持使能，无故障。初始参考为本次任务保存的 initial_left.json 和 initial_right.json。

左臂最大实测关节偏差 1.661°，右臂 0.000°，均在现有 2.5° 回位容差内。左臂初始 J2 位于当前规划保护余量外，直接返回方案被保护检查拦截，未执行。保留全部保护设置，将最后目标 J2 调整为 +0.5°，其余关节以初始值为目标；通过路径预检后执行。另一次因观测后微小沉降而拒绝的请求，在重新观察后处理。未修改控制保护参数。

夹爪为空，回位期间保持夹爪目标；刷子和两块蓝色方块位置稳定。右臂未下发运动。两次终态采样核验通过。控制宿主继续保持双臂，未断电或停止心跳。

三路录像已正常结束，并逐帧解码验证：

- top: [top_0000.mp4](/home/tuojing/arx_r5_control/analysis/brush_sweep_live_20261017_223120/return_to_initial/recording/top_0000.mp4)，230.8 秒，2308 帧。
- left: [left_0000.mp4](/home/tuojing/arx_r5_control/analysis/brush_sweep_live_20261017_223120/return_to_initial/recording/left_0000.mp4)，230.8 秒，2308 帧。
- right: [right_0000.mp4](/home/tuojing/arx_r5_control/analysis/brush_sweep_live_20261017_223120/return_to_initial/recording/right_0000.mp4)，230.8 秒，2308 帧。

详情见 result.json；回位前后全局及腕部照片保存在本目录。
