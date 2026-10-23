# 第3轮目录移至回收站导致准备中断

Trash info显示：第2轮目录于19:53:29移至回收站，第3轮目录于19:53:40移至回收站。来源操作人尚未确认。录像因manifest.tmp父目录不存在停止。双臂仅完成保持准备，没有任务动作；宿主进入软件异常静止保持，原保护持续。

原日志末项：{"event": "host_quarantined", "reason": "[Errno 2] No such file or directory: '/home/tuojing/robot_runs/withskills_blue_blocks_sweeping_20261020_195257/control/initial_state.json'", "exception_type": "FileNotFoundError", "new_commands_blocked": true}

在项目analysis目录保存恢复记录；不会通过恢复文件伪造原宿主为可接收动作状态。

19:55:20只读检查双臂均ready但disabled、无owner。原保持宿主已退出，终端报告 Camera supervision failed: OSError: broken data stream when reading image file；具体故障帧未保存，不能确定相机源。未自动重连或使能。恢复初段MP4到本目录并保留原manifest，封口状态与帧数属于离线恢复，不称正常STOP。
