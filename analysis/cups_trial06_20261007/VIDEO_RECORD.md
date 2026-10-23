# 叠杯第6轮录像记录

全局top、左腕left、右腕right三路MP4于2026-10-07 09:50:19.367（UTC+8）启动，10fps、60秒分段，保存在recording/。首次SDK初始化前已核验进程存活、设备不同、三路新鲜帧递增，核验记录在preflight/recording_gate_before_reconnect.json。

本段录像内容为通信恢复准备，不是叠杯执行或成功视频。第一次只读预检发生在连续录像开始前，只有快照/日志；不声称整个请求窗口全程录像。

本段于09:56:24.608正常STOP封口，21个原始MP4（每路7段），各3651帧，10fps。全局/左腕各3640新鲜帧、5重复、6缺采样；右腕3638新鲜帧、7重复、6缺采样，各路HTTP错误0。缺采样与重复均在元数据和成片中标注，不称零缺帧或相机硬同步。

[三视角准备录像](preparation_video/cups_trial06_preparation_3view.mp4)：6分5.1秒，1280×1456，H.264，70,376,815字节；上排左腕/右腕，下排全局，保留原速及等待。全部21个原始MP4和成片3651帧均逐帧解码通过，布局预览已人工视觉复核。详见[成片清单](preparation_video/manifest.json)、[原始验证](raw_video_validation.json)、[时间映射](preparation_video/timeline.jsonl)。

09:56:24.608之后暂未继续连续录像。后续初始化或任务动作前须另启三路录制，保留两段间缺口，不能把本段称为完整叠杯录像。

追加使能检查段：[recording03](recording03/)，2026-10-07T10:02:30.157438+08:00—2026-10-07T10:03:07.132977+08:00，正常STOP，共3个MP4，各路帧数{'top': 368, 'left': 368, 'right': 368}。全部原始帧解码通过，见[验证](recording03_validation.json)。仅记录原使能入口的前置检查拒绝，没有叠杯动作；与前段之间的录像缺口保留。recording02首帧超时失败无帧，原manifest保留。

新上电后重连段：recording04于10:04:28.921—10:04:49.775正常录制并STOP。每路207帧，均为新鲜采样，重复/缺采样/HTTP错误均0；这只是该段统计，不代表其他段或相机硬同步。[本段三视角同屏视频](reconnect_after_power_cycle_video/cups_trial06_reconnect_after_power_cycle_3view.mp4)长20.7秒、4,211,628字节；3个原始MP4与成片207帧全部解码通过，见[验证](recording04_validation.json)和[成片清单](reconnect_after_power_cycle_video/manifest.json)。本段仅为通信恢复，未执行叠杯。

右USB接口恢复段：[recording05](recording05/)，2026-10-07T10:06:17.823431+08:00—2026-10-07T10:07:14.963706+08:00，正常STOP。共3个原始MP4，全部逐帧解码通过，见[验证](recording05_validation.json)。逐路新鲜/重复/缺失统计见[manifest](recording05/manifest.json)。仅恢复右CAN桥，未初始化SDK或运动；不覆盖10:05:44更早的USB断开瞬间。

右SDK连接恢复段：[recording06](recording06/)，2026-10-07T10:07:58.825917+08:00—2026-10-07T10:08:32.000591+08:00，正常STOP，每路330帧。全部3个原始MP4逐帧解码通过，见[验证](recording06_validation.json)；缺采样/重复按[manifest](recording06/manifest.json)保留。本段右连接恢复成功，没有叠杯动作。

## 任务执行与最终剪辑（补齐归档）

任务三路录制：2026-10-07T10:13:40.216935+08:00—2026-10-07T12:01:48.380043+08:00，正常STOP封口，原片在[recording07/](recording07/)。全局top、左腕left、右腕right，10fps、60秒分段，共327个任务原始MP4，每路64880帧。

[三视角同屏](edited_video/cups_trial06_3view.mp4)：1957.8秒，1280×1456 H.264，196,959,287字节；上排双腕、下排全局。全部任务原片和成片19578帧逐帧解码通过；布局与端点图像已视觉复核。[成片清单](edited_video/manifest.json)、[原片验证](task_raw_video_validation.json)、[帧映射](edited_video/timeline.jsonl)。

| 视角 | 总帧 | 新鲜 | 重复 | 缺采样黑帧 |
| --- | ---: | ---: | ---: | ---: |
| left | 64880 | 64558 | 184 | 138 |
| top | 64880 | 64650 | 92 | 138 |
| right | 64880 | 64567 | 173 | 140 |

逐帧状态在原元数据和成片保留。各路HTTP错误0；软件共同采样不等于硬件曝光同步，也不等于零缺帧。

观看版按用户要求剪去额度中断静止段4530.135779秒（约75分30.136秒），动作原速，原片不删；删除端点与映射见成片清单。左放杯通过、右杯倾倒未套叠，人工重摆和回位证据保留。前文初始化录像是历史阶段记录，其后已另启本任务段，不能将准备段与任务段之间空档称连续录像。
