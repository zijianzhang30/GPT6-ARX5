# Book extraction — new trial 2026-10-20 15:34:09

User corrected the pending pushing task before any motion. The two-black-rectangle setup request is obsolete. This is a newly authorized extraction attempt, not continuation of the completed unsuccessful extraction trial.

Right arm holds the top book steady; left arm extracts the middle book by an additional 5 cm from this trial baseline. Initial protrusion is excluded. Arm travel does not prove book travel. Three original streams, Markdown, and a 90-second composite with upper left/right wrists and lower head view are required.

At trial preparation the existing healthy hold was reused. After its unexpected exit, a new independent host was established following the user's clearance confirmation, as documented below. Initial and inherited immutable return references are saved separately. `control/` now contains this trial's new host output; `previous_host_control` preserves the earlier link. Both hosts subsequently exited; binding files are historical evidence, not live control handles. Prior frozen evidence remains preserved.

Prior trials failed to establish reliable book-following; this trial must establish a new visible grasp geometry before retrying, not replay historic targets. Basic Skill's pushing-specific no-grasp restriction does not apply to this explicitly requested extraction task.

## 先清空和复位的用户指示
用户要求先清空和复位，再执行任务。当前接口不能清空聊天上下文；已询问用户选择在当前会话作为独立实验继续，或等其新建会话。抽书动作与录像尚未开始。

两次只读核验于 2026-10-20T15:36:11.089800+08:00 和 2026-10-20T15:36:51.426230+08:00 均确认两臂已在保存原始关节参考的 2.5° 容差内，静止使能保持，无错误码或活动轨迹。最大实测差：左 1.8359548488994282°，右 0.45898871222485693°；指令也在原容差内。未发送额外复位轨迹，没有将 SDK 初始化或失能当作复位。三路新图确认空爪与书堆分离。此阶段仅静态核验，无录像；不能声称本轮任务已执行。

## 用户选择本会话继续与连接丢失
用户选择本会话继续，并要求清空 session memory。已说明无法清除当前上下文，仅重新建立任务工作状态；原记录保留。15:38:13 的只读状态与三路图像仍正常，两臂 ready/enabled/stationary/holding。

15:38:23 首次录像启动 HTTP 503，recording/manifest.json 为 failed，未生成任何有效录像。再次只读检查发现 arms state 为 null，录像 recording02 同样 failed。15:38:47 核验左右 8765/8766 端口均 connection refused；上游 app、两侧 SDK worker 和保持宿主 PID2213412 均已退出，仅 8768 workbench 仍在。原保持会话退出码1：HTTP Error 503: Service Unavailable; protective stop unconfirmed。原因未确定，不能声称机械臂仍使能保持或已受控复位；先前两次复位核验只适用于各自时间点。

本轮未发送运动、夹爪、使能、失能、SDK重连、服务重启或杀进程指令。录像尝试为只读 HTTP。已暂停后续动作，询问现场两臂支撑/清场及是否断电、关闭程序或改线，等待回复。

## 现场确认后恢复
用户回复“已确认”。仅在确认原上游服务/worker均退出后启动左右 app 状态与相机服务；该启动不连接SDK。三路 recording03 于15:40:20.625779正常开始。分别经8765和8766管理接口连接一次SDK，两侧均验证ready、新鲜RX增长、有限六关节、无错误，连接时未建立保持控制。新唯一监督宿主PID1497365／会话49476于15:42恢复双臂保持；初始化和新鲜状态两次均在继承原参考2.5°内。SDK初始化不作为自主受控回位动作成果。旧control链接已改名previous_host_control，新control为本轮独立日志。服务退出原因尚未确定；系统journal显示15:38:13附近终端scope结束，仅为时间关联。

## 新观察下的接近（约15:43–15:56）
右臂分7段前移、向书堆中心横移并抬高，当前闭合空爪尖端位于顶层封面侧缘上方；尚未核验承力稳定接触。书堆和底盒未观察到新增位移。左臂在原空旷位置分段张开空爪，随后从外侧抬高接近，并开始在空旷处调整为上下夹持方向。尚未闭夹书本或试拉，不能报告5厘米完成。全部实际动作前核验recording03三路新帧、双臂健康、新图，离线规划通过后单独发送。一次姿态候选因离线脚本将list调用tolist而失败，已修正纯离线转换；该错误未向机械臂发命令。过大预算候选均在离线拒绝；只在健康静止且空爪间隙确认后使用既有renew机制。

## 15:58:56 第二次连接故障与停止
右侧app进程1474788退出，PTY41964退出码143（SIGTERM）；发信来源/原因未确定。保持宿主于15:58:56.749报告HTTP400后退出；右监督诊断为HTTP503且protective stop unconfirmed。最后成功任务动作是15:58:33左爪空载调整至上下夹持方向。下一条左臂+40毫米X/-15毫米Y候选仅离线规划通过，宿主故障先于发送尝试；events中无该请求，未执行。

15:59:47只读检查：左臂disabled、owner=null，右臂state=null。头部新图显示两臂下落、上书倾斜，左关节4实测78.4118°；不得直接重新使能、重新连接或回放轨迹。右腕HTTP503，其他两路仍更新。此变化不是机器人任务抽取成果，未验证右臂承力稳定、没有闭夹书本或试拉、5厘米未完成、最终受控回位未完成。已停止动作并请求新的现场支撑/清场确认。

录像保留故障前后：recording03 STOP标记用于正常封口；三视角合成将明确标示右腕源缺失，不用前帧冒充实时画面。停录不向机械臂发送任何指令，不终止仍存活的上游服务。

## 最终归档与结果

| 里程碑 | Asia/Shanghai时间 | 结果 |
| --- | --- | --- |
| 本轮任务更正／独立边界 | 15:34:09.265 | 抽书prompt，允许技能，未执行错误推书任务 |
| 两次原参考静态核验 | 15:36:11、15:36:51 | 当时两臂均在2.5°容差内；没有额外复位轨迹 |
| 首次服务丢失 | 15:38附近 | 尚无任务移动，前两次录像启动失败 |
| 用户确认后恢复录像 | 15:40:20.626 | recording03三路开始 |
| 新宿主保持准备 | 15:42附近 | 恢复后原参考检查通过；SDK初始化不计自主回位 |
| 首次任务移动 | 15:44:50.359 | 右臂接近开始 |
| 最后成功移动后观察 | 15:58:33.876 | 左爪空载完成上下夹持方向 |
| 宿主故障终止 | 15:58:56.749 | HTTP400；右侧503，右app SIGTERM退出 |
| 故障后新观察 | 15:59:47.893 | 左disabled，右state=null；两臂下落、上书倾斜 |
| 录像正常封口 | 16:00:28.138 | 共63个MP4，21段／路 |
| 合成全帧核验 | 16:02:30.703 | 2700帧，30fps，90.0秒，1280×960通过 |

新宿主完成右7段／左8段接近与空载调姿，另有左空爪张开10个内部目标。右臂与封面的承力接触未验证，没有建立左爪夹书和书随爪移动证据，没有试拉。**任务结果：未完成；最终受控回位：未完成。** 初始书本突出不计新增抽取；故障后的书本倾斜也不计任务成果。

原片`recording03/`各12074帧，采样时间轴1207.4秒。全部63个MP4首末帧、帧数及10fps检查通过；这是端点检查，不声称逐帧检查原片。头部缺27／重复17帧，左腕缺28／重复30帧，右腕缺935／重复21帧。右腕最后有效采样在15:58:56.626，随后连续91.3秒缺图，含在935缺采样内。详细状态及连续区间见`recording_quality.json`。失败启动的`recording/`和`recording02/`没有视频，仅保留manifest。

90秒成片保留完整有效录像批次时间轴，约13.42倍，上方物理左腕／右腕、下方头部，等比例缩放留边。三路同一原始采样索引，输出到原片逐帧映射完整；缺采样保留黑帧，重复帧标记。全2700帧解码、90.0秒容器时长与2700条来源映射核验通过，见`三视角视频/validation.json`。

[实验入口](README.md) · [90秒视频](三视角视频/抽书实验_三视角_90秒.mp4) · [公开对话](DIALOGUE.md) · [时间与资源](PERFORMANCE.md)。执行统计窗口在故障终止时冻结；后续录像封存、合成与核验时间分列。第二次故障后没有发送恢复、重新使能或回位指令，等待新现场确认；SIGTERM来源仍未知。
