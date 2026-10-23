# 夹取果冻实验记录 · 2026-10-12 · 新协议第1轮

## 结果与范围

**第3次局部夹取成功，反馈FK估算净抬升约5.8厘米；已放回原盒面、释放并撤爪，双臂最终回位两次通过。** 当前双臂ready/enabled/holding，无故障码；健康保持宿主保留。三路录像已停止并封存，共69个MP4，存在三处录制间隔，不能称全程连续录像。

本轮对象是带封膜的包装果冻杯，初始竖放在绿色盒面；最后侧放在同一盒面。抓取接触包含杯肩/口沿附近及对侧白色杯身，未实现纯中部杯身对夹；没有把单纯勾膜计为成功。目视未见破裂或洒漏，未做密封测试、力测量或外部精密位移测量。旧软果冻两轮失败独立保留，不与本次包装杯混算成功率。

## 协议、初态和分工

用户指定以果冻替代橘子，其余按抓取橘子流程：左臂抓取→低幅试提→抬升5–20厘米→放回→释放/独立稳定→双臂回原初始参考，右臂可辅助观察且不得干涉。本轮右臂仅原位提供腕部观察，未下发右臂任务轨迹。逐段检查三路画面，未观察到双臂碰撞；规划器并非完整几何碰撞认证。

原始参考来自橘子第1轮（经第2轮字节相同副本），见[来源](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/reference_provenance.json)、[冻结参考](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/return_reference.json)，SHA256 `7ddefce84720da32eb66bea24cce68e317f6f17f266ac4758c078ad2fee01529`。本轮真实初态另外保存。可执行目标将J2设为0.8°以保留关节余量，原参考及2.5°容差均未改动。18:40:25.031及18:40:28.485两次初始核验通过，无需增加回位轨迹；SDK初始化本身不被记作受控回位。

通信映射：物理左臂2088335E5931→can0→8765，物理右臂208833765931→can1→8766；相机与任务角色未交换。后续每次仍需核验实时身份。

## 执行经过

| 时段（+08:00） | 过程与证据 |
| --- | --- |
| 18:32–18:39 | 双SDK旧fault、无有效反馈；用户重新上电及检查后，两次左重连仍无回包。失败worker断开，未抓取；随后修复旧CAN序列号脚本，用户本机sudo重建桥接。 |
| 18:39–18:40 | 左SDK恢复真实RX和关节反馈，右SDK逐侧恢复；唯一宿主使能保持，两次原参考核验通过。 |
| 18:40:53–18:47 | 左空爪接近；第一次闭爪至归一化0.5，15+10毫米试提未稳定离面。放回松爪时杯子侧倒，第一次失败。 |
| 18:47–18:50:30 | 抬离后分段调整向下姿态和抓点，接近中杯子有转动；第二次闭爪0.5、15毫米试提仍未带起。 |
| 18:50:49–18:52:36 | 回落，依据夹面间隙闭至0.4；第三次20毫米试提及再20毫米抬升确认杯子随动、盒不动；调整姿态6°保留腕部余量，续段后再升35毫米，稳定持物两次复核。 |
| 18:52:41–18:54:36 | 两段下降各25毫米指令；逐步松爪0.42至0.52，独立侧向支撑后完全张开，空爪上撤35毫米指令；两次新观察间隔8.015秒确认独立稳定。 |
| 18:54:42–18:57:23 | 左空爪6段回位，健康静止时按真实预算提前renew；右臂保持原位。第1、2段间录制结束并恢复，缺口另记。 |
| 18:57:26.557 / 18:57:33.269 | 实测、指令、静止、健康和owner双次回位核验通过。 |
| 18:57:37.398 | STOP结束末段录像；所有原片端点及元数据核验通过，保留健康双臂保持。 |

第三次抓取前实测TCP z=0.192459362m，峰值z=0.250444627m，差值5.799cm。上行平移指令合计75毫米，但含姿态调整、反馈残差及重锚，不能把75毫米写成真实物体抬升。5.8厘米为FK估算，杯子真实离面由图像确认。见[抬升证据](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/grasp_lift_evidence/milestones.json)及该目录两组多视角图。

放置证据见[独立支撑核验](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/placement_evidence/verification.json)与两组图片。杯子侧放是可见结果，未还原初始竖放姿态。

## 最终回位

| 核验 | 左实测/指令最大误差 | 右实测/指令最大误差 |
| --- | --- | --- |
| 2026-10-12T18:57:26.556755+08:00 | 0.546° / 0.353° | 1.355° / 1.355° |
| 2026-10-12T18:57:33.268793+08:00 | 0.546° / 0.353° | 1.355° / 1.355° |

两臂均ready、enabled、stationary、holding、无错误，新鲜反馈及owner一致。LEFT空爪完全打开，RIGHT空爪保持原小开度；本次原参考针对六关节，不要求复制旧橘子夹爪开度。原始核验文件为[第1次](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/final_return_check1.json)和[第2次](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/final_return_check2.json)。

## 异常、恢复与未验证项

- 旧脚本把左桥接预期仍写成765931，引发Unexpected left bridge arguments保护拒绝；三份桥接脚本已改为当前5E5931并保留失能、无owner、worker退出、身份及接口检查。9项离线测试、bash语法和只读检查通过。sudo交互认证由用户在终端完成，无密码进入记录。证据见[脚本差异与验证](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/bridge_mapping_update)。
- 桥接恢复后双臂有效反馈及使能成功；这不等于已经查明此前所有左RX为0的底层原因。两次失败连接保留在原记录。
- 一次开爪0.58请求在动作前因Robot changed after observation被拒绝；没有绕过或原样重试。接近/松爪时杯子发生倾斜、侧倒及转动，前两次失败保留；不能把整个接近称为无接触。
- 抓放和最终回位期间未发生控制运行故障；保持相机、心跳、到位、跟踪、速度和预算保护。归一化开度是位置量，不等于测得夹持力。
- 第3录像阶段SIGTERM来源未确认。第3处缺录中未下发新轨迹，但有一次健康renew保持目标重锚，不能声称所有控制操作都有MP4覆盖。完整缺口与缺帧明细见录像记录。
- 操作前已有用户清场与急停确认。抓放阶段图像未见新的人工摆物或接管；准备阶段用户重新上电、检查和运行桥接脚本单列，不包装成无人工参与的冷启动。

## 文件与用量

| 阶段 | 时间（+08:00） | 每路时长 | MP4数 | 结束方式 |
| --- | --- | --- | --- | --- |
| [首次左SDK恢复失败](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/recording) | 18:33:08.357–18:34:37.155 | 88.6s | 6 | stop_file |
| [检查后第二次左SDK恢复失败](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/recovery02/recording) | 18:36:57.125–18:37:20.669 | 23.4s | 3 | stop_file |
| [桥接恢复、双臂使能、抓放及回位第1段](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/bridge_recovery03/recording) | 18:38:51.821–18:55:06.280 | 974.5s | 51 | SIGTERM |
| [回位第2–6段及最终核验](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/final_return04/recording) | 18:55:36.295–18:57:37.397 | 121.0s | 9 | stop_file |

- [三路录像、缺口和逐片验证](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/VIDEO_RECORD.md)；每路累计1207.5秒。
- [原始运行记录](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/RUN_RECORD.md)、[状态](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/status.json)、[冻结控制日志](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/control_final_snapshot/events.jsonl)、[请求索引](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/request_index.json)。
- [公开对话](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/DIALOGUE.md)、[资源与耗时](/home/tuojing/arx_r5_control/analysis/jelly_grasp_trial01_20261012/PERFORMANCE.md)：冻结窗口25.49分钟，去重输入34,869,449、输出88,432token；缓存输入包含于输入。窗口包含恢复准备，非纯运动或纯推理时间。
- [新技能](/home/tuojing/.codex/skills/jelly-grasp/SKILL.md)与项目镜像已更新本轮证据及适用边界；原始技能快照保留在skill_snapshot_start。
