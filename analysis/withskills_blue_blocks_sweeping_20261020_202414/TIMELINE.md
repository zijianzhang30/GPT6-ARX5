# 控制事件时间线

以下是指令意图及宿主结果，不自动等同物理任务成功。

| 时间 | 事件 | 记录 |
| --- | --- | --- |
| 2026-10-20T20:25:41+08:00 | working_arm_selected | left |
| 2026-10-20T20:27:11+08:00 | request | move_to — Small open empty approach upward and forward; visible clear corridor, right stationary |
| 2026-10-20T20:27:38+08:00 | request | move_to — Raise open left toward handle height with small forward approach; no contact |
| 2026-10-20T20:28:32+08:00 | request | move_to — Bounded forward approach and modest downward finger inclination |
| 2026-10-20T20:29:01+08:00 | request | move_to — Advance empty fingers toward handle above support; retain height and orientation |
| 2026-10-20T20:29:25+08:00 | request | move_to — Raise slightly and approach handle; further incline fingers for overhead grasp |
| 2026-10-20T20:30:24+08:00 | request | move_to — Align above free handle and incline empty jaw for grasp, without touching support |
| 2026-10-20T20:31:33+08:00 | request | move_to — Shift open jaw over handle top with upward clearance before descent |
| 2026-10-20T20:32:09+08:00 | request | move_to — Correct lateral alignment from observed global displacement; remain above brush with open jaw |
| 2026-10-20T20:32:53+08:00 | request | move_to — Center open fingers above handle, preserving vertical clearance and inclining for capture |
| 2026-10-20T20:33:58+08:00 | request | move_to — Advance open jaw toward aligned handle, keep height and lateral alignment |
| 2026-10-20T20:34:58+08:00 | request | move_to — Small approach to free handle below loop; open fingers, avoid box rim |
| 2026-10-20T20:36:05+08:00 | request | move_to — Small lateral correction to place free handle inside open jaw gap; retain height |
| 2026-10-20T20:36:39+08:00 | request | set_gripper — Begin gradual closure around visually centered brush handle; no lifting yet |
| 2026-10-20T20:36:39+08:00 | rejected | A fresh, unconsumed observation is required |
| 2026-10-20T20:36:58+08:00 | request | set_gripper — Gradually close around centered free brush handle; lifting not yet verified |
| 2026-10-20T20:37:24+08:00 | request | set_gripper — Continue gradual closure while centered handle remains independently supported |
| 2026-10-20T20:37:43+08:00 | request | set_gripper — Narrow jaw around free brush handle while monitoring both sides and support |
| 2026-10-20T20:38:18+08:00 | request | set_gripper — Small closure to contact opposite sides of the handle before a lift test |
| 2026-10-20T20:38:41+08:00 | request | move_to — First bounded lift test: check entire brush follows and leaves box/table support |
| 2026-10-20T20:39:29+08:00 | request | move_to — Reposition fingers deeper around supported free handle after first lift showed no grasp |
| 2026-10-20T20:39:50+08:00 | request | set_gripper — Close modestly at the deeper handle position; prepare second short lift verification |
| 2026-10-20T20:40:12+08:00 | request | move_to — Second short lift from deeper jaw engagement; verify whole brush independently follows |
| 2026-10-20T20:44:16+08:00 | working_arm_selected | right |
| 2026-10-20T20:44:29+08:00 | request | move_to — 右臂仅观察：在空通道内先抬高20毫米，左臂保持不动 |
| 2026-10-20T20:45:17+08:00 | request | move_to — 右臂仅观察：小幅抬高及转向，左臂保持 |
| 2026-10-20T20:45:55+08:00 | request | move_to — 右臂仅观察：平移增加观察基线并转向刷柄；左臂保持 |
| 2026-10-20T20:46:25+08:00 | request | move_to — 右臂仅观察：在空域抬高并横移，以看到刷柄和左夹指的侧面 |
| 2026-10-20T20:47:00+08:00 | request | move_to — 右臂仅观察：抬起视线，使刷柄和左夹指完整入画 |
| 2026-10-20T20:47:40+08:00 | working_arm_selected | left |
| 2026-10-20T20:47:46+08:00 | request | move_to — 侧面观察确认夹指仍在柄端上方；张开夹爪沿刷柄方向下探到较低实心柄段，右臂静止观察 |
| 2026-10-20T20:48:08+08:00 | request | set_gripper — 新抓点：较低刷柄段位于两指之间，先小幅闭合观察 |
| 2026-10-20T20:48:29+08:00 | request | set_gripper — 新柄段小步闭合；刷子仍独立支撑，逐段观察双指 |
| 2026-10-20T20:48:49+08:00 | request | set_gripper — 双视角观察新柄段仍在指间，继续小幅闭合至0.4 |
| 2026-10-20T20:49:13+08:00 | request | set_gripper — 较低柄段继续有界闭合；下一步先小幅试提，不执行扫动 |
| 2026-10-20T20:49:38+08:00 | request | move_to — 新抓点首次18毫米试提：只验证整刷跟随和离开支撑 |
| 2026-10-20T20:50:05+08:00 | request | set_gripper — 新抓点试提仍未离开支撑；双视角可见柄段在指间但尚有间隙，小步收窄后仅再验证一次 |
| 2026-10-20T20:50:29+08:00 | request | move_to — 较低抓点第二次18毫米试提，核对整刷与静态背景，不执行扫动 |
| 2026-10-20T20:52:00+08:00 | request | move_to — 收尾：左爪已张开，向后上方撤离刷柄，验证刷子独立支撑 |
| 2026-10-20T20:52:59+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 95.58035584883778, 'command_deg': 94.6478577071872}，at_initial=False |
| 2026-10-20T20:53:19+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 89.96315363390595, 'command_deg': 89.08564276552082}，at_initial=False |
| 2026-10-20T20:53:38+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 84.3240401721167, 'command_deg': 83.52342782385443}，at_initial=False |
| 2026-10-20T20:54:01+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 78.66312474649676, 'command_deg': 77.96121288218805}，at_initial=False |
| 2026-10-20T20:54:22+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 73.13329431142772, 'command_deg': 72.39899794052167}，at_initial=False |
| 2026-10-20T20:54:49+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 68.21550346750519, 'command_deg': 67.5356741496225}，at_initial=False |
| 2026-10-20T20:55:11+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 62.57639000571594, 'command_deg': 61.959910593161325}，at_initial=False |
| 2026-10-20T20:55:30+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 56.9591877907841, 'command_deg': 56.38414703670015}，at_initial=False |
| 2026-10-20T20:55:52+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 51.34193093433889, 'command_deg': 50.80838348023898}，at_initial=False |
| 2026-10-20T20:56:15+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 45.61539105117348, 'command_deg': 45.23261992377781}，at_initial=False |
| 2026-10-20T20:56:33+08:00 | rejected | State changed after return review; capture and review again |
| 2026-10-20T20:56:52+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 39.97633223089759, 'command_deg': 39.65685636731663}，at_initial=False |
| 2026-10-20T20:57:19+08:00 | rejected | State changed after return review; capture and review again |
| 2026-10-20T20:57:39+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 34.73063766530108, 'command_deg': 34.40994479876793}，at_initial=False |
| 2026-10-20T20:58:02+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 29.11343545036923, 'command_deg': 28.843557366638276}，at_initial=False |
| 2026-10-20T20:58:22+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 23.583605015300186, 'command_deg': 23.277169934508617}，at_initial=False |
| 2026-10-20T20:58:43+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 17.96640280036834, 'command_deg': 17.710782502378958}，at_initial=False |
| 2026-10-20T20:59:07+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 12.392859154611216, 'command_deg': 12.144395070249303}，at_initial=False |
| 2026-10-20T20:59:35+08:00 | reviewed_return_step | left，原宿主参考最大误差 {'joints_deg': 6.775656939679369, 'command_deg': 6.578007638119645}，at_initial=False |
| 2026-10-20T21:00:57+08:00 | request | move_to — 空爪回位末段：原参考不变，选J2=0.8度可执行目标，仍以原2.5度容差核验 |
| 2026-10-20T21:01:23+08:00 | working_arm_selected | right |
| 2026-10-20T21:01:34+08:00 | reviewed_return_step | right，原宿主参考最大误差 {'joints_deg': 15.190559280161798, 'command_deg': 14.819172436216753}，at_initial=False |
| 2026-10-20T21:01:52+08:00 | rejected | State changed after return review; capture and review again |
| 2026-10-20T21:02:09+08:00 | reviewed_return_step | right，原宿主参考最大误差 {'joints_deg': 10.819183569840279, 'command_deg': 10.447972172798883}，at_initial=False |
| 2026-10-20T21:02:29+08:00 | rejected | State changed after return review; capture and review again |
| 2026-10-20T21:02:47+08:00 | reviewed_return_step | right，原宿主参考最大误差 {'joints_deg': 6.3603814381425945, 'command_deg': 6.076771909381012}，at_initial=False |
| 2026-10-20T21:03:06+08:00 | reviewed_return_step | right，原宿主参考最大误差 {'joints_deg': 2.0545755438531956, 'command_deg': 1.7055716459631414}，at_initial=True |
