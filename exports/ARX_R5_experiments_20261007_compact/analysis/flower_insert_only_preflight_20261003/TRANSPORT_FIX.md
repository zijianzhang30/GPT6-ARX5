# 2026-10-03 本机代理连接排队修复

第4轮12:05故障诊断栈停在连接本机8768代理的 `socket.connect`；HTTP请求超时，随后0.3秒心跳保护触发。检查发现代理监听队列为5。这里只确认并修复一个可复现的连接拥塞机制，不声称它是所有历史故障的唯一原因。

`record_workbench.py` 的 `RecordingWorkbench.request_queue_size` 改为64。0.25秒HTTP超时、0.3秒监督期限、CAN/相机新鲜度、跟踪、限位、速度和动作预算均未放宽。

验证结果：

- 隔离TCP复现：12客户端同时连接、服务端延迟50毫秒接收、客户端仍用0.25秒超时。队列5时6/12成功；队列64时12/12成功。
- 原代理只读接口60次突发请求：12次超时，最长约253.668毫秒。
- 新代理相同60次请求：0错误，最长9.871毫秒。
- 三路相机各10Hz、两侧状态各20Hz的45.045秒只读检查：3148请求、0错误；状态请求最长6.375毫秒，相机最长5.709毫秒。
- 新增 `tests/test_proxy_connection_burst.py`；与 `test_dual_workbench`、`test_http`、`test_r5_dual_policy`、`test_r5_policy_supervisor` 联合运行通过（退出码0）。

部署前核实两臂disabled/unowned/stationary，页面无活跃episode。原代理正常退出，新代理PID2995139、工具会话81218、端口8768；底层8765/8766服务未重启，不执行SDK重连或回零。底层服务监听队列未改。

随后第5轮左臂带电保持经静止观察后才开始运动。此修复不是断电防回落硬件认证；后续真实故障仍需按原保护处理。

原始证据：`offline_backlog_reproduction.json`、`proxy_burst_before.json`、`proxy_burst_after.json`、`post_restart_readonly_load.json`。旧代码备份在 `transport_fix_backup/record_workbench.py`。
