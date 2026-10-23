# 本轮任务与用户更正

## 用户最终确认的有效prompt

> Pick up the  jelly from the green box with the left arm, lift it 5–20 cm, then place it back and release it.

以下保留原输入和更正过程供追溯，以此最终句为准。

原文：
> Pick up the packaged jelly cup from the green box with the left arm, lift it 5–20 cm, then place it back and release it

本轮用户更正：
> 删除cup，没有包装杯

据此，本轮对象为绿色盒面上的裸果冻。左臂夹起，抬升5–20厘米，放回原盒面并松开。其余目标不变；不执行拆包装或开杯。右臂默认保持原位。

成功须有果冻随爪离开支撑的可见证据、5–20厘米抬升的反馈估计与视觉复核、放回释放并撤爪后的两次独立稳定观察。开度是位置而非夹持力测量，形变滑脱时重新观察，不将末端运动当成物体被抓起。

新建单轮实验；历史坐标、开度和橘子初态不重放。现有SDK正常但双臂失能，按标准入口建立保持，实际本轮初态和回位参考在恢复保持后冻结。用户已确认检查承托/清场/可急停；未提供断电或改线的具体说明，本轮不需要SDK或CAN重连。

三路MP4采用全局external、左腕gemini、右腕gemini_right，10fps共同软件采样网格，不是曝光硬同步。目录沿用创建时的packaged_cup命名，仅作为标识；报告以本次更正后的裸果冻为准。

用户追加：先恢复默认初始位姿，然后再开始录视频并且进行任务。默认采用此前厂商HOME六关节零位；本段回位不录制，正式三路另起recording_task。
