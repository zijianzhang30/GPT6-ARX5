# 第7项：杯间倒珍珠，2026-10-05

第1轮已收尾：左臂抓起源杯并倾倒，右臂辅助观察，源杯受控放回，双臂回位通过。用户验收成功并允许杯底残留；过程存在洒落，未独立核验接收数量，不记为全部转移或零洒落。分类尚未指定。

用户的左右与全局画面左右不同：本轮按杯内物确认源杯在全局右侧，接收杯在全局左侧。第1次试提未抓住，修正前后位置后第2次抓取通过。倾倒期间观察臂有遮挡，调整落点、倾角与高度后仍有残留。用户明确接受本轮结果。

放杯时首次向上撤离仍带起杯子，降回支撑面并继续张爪，随后水平撤离成功；第135、137步及末次观察确认杯子独立稳定。11:21:44 回位核验：左臂实测/指令最大误差1.552°/1.273°，右臂0.699°/0.421°，均在原2.5°容差内；两臂静止、使能保持、错误码为空。健康宿主保留，未用失能或SDK初始化回位。

录像 10:47:08–11:21:44（北京时间），约34分36秒；全局 `top_*.mp4`、左腕 `left_*.mp4`、右腕 `right_*.mp4`，各35段、20757帧，共105个MP4、742267449字节。全部文件首末帧可解码、帧数与manifest一致；未逐帧解码所有原录像。全局/左腕/右腕缺失采样槽分别43/43/42，重复帧25/48/44，原元数据保留，不能称零缺帧。首个 `recording/` 是启动失败证据，正式录像在 `recording02/`。

[本轮记录](analysis/pearl_pouring_trial01_20261005/RUN_RECORD.md)、[状态](analysis/pearl_pouring_trial01_20261005/status.json)、[冻结prompt](analysis/pearl_pouring_trial01_20261005/task_prompt.md)、[计量数据](analysis/pearl_pouring_trial01_20261005/PERFORMANCE_USAGE.json)、[公开对话](analysis/pearl_pouring_trial01_20261005/DIALOGUE.md)。三路MP4见本轮recording02，首个recording为启动失败记录。

[倒珍珠 skill 指南](/home/tuojing/.codex/skills/arx-r5-tabletop-tasks/references/pearl-pouring.md)、[录像验证](analysis/pearl_pouring_trial01_20261005/recording02/validation.json)、[回位核验](analysis/pearl_pouring_trial01_20261005/return_verification.json)。

## 三路完整合成视频

已按拔笔帽案例布局合成：[打开 MP4](analysis/pearl_pouring_trial01_20261005/combined_video/pearl_pouring_full_3view.mp4)，上排左腕/右腕、下排全局。完整原速34分35.7秒，1280×1456、10 fps、H.264，约512 MB；保留等待、重试、洒落、放杯和回位。三路按共同采样帧序号对齐，保留重复/缺失状态。合成时已读取全部源帧，成片20,757帧逐帧解码验证通过。[视频说明与阶段时间索引](analysis/pearl_pouring_trial01_20261005/combined_video/VIDEO.md)。本次离线合成不计入已冻结的实机资源统计。
