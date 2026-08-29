# NEXT_ITERATION_PLAN — Beta 1.2 Companion Evolution（待办汇总）

> **来源**：Beta 1.1 Real World Review（2026-08-05）。执行模式 Observe → Record → Verify → Report。
> **纪律**：本文件仅**记录与分类**，不含任何代码修改或现场修复。所有项等待统一进入 **Beta 1.2 Companion Evolution** 后由 PM/老板拍板执行。
> **标记**：`LIVE`=需老板本机真机验证；`P3`=已知可选缺口；`R`=Review 新识别风险。

---

## 0. 进入 Beta 1.2 前置真机确认（最高优先）

以下三项必须在 Beta 1.2 动手前由老板本机运行 `start-xiao6.bat` 连续验证，决定下一步方向：

| 编号 | 项 | 为什么关键 |
|------|----|-----------|
| R1 | 150% 缩放 / 多显示器下点击穿透坐标空间 | 决定 B2 是否真解决；坐标空间不一致会令穿透误判 |
| R2 | 交互抢 OS 焦点是否打扰 | 决定桌宠交互是否会打断用户当前工作 |
| B2-LIVE | 桌宠覆盖区点击是否真穿透 | P0 核心命题「桌宠是否影响工作」的真机裁决 |

---

## 1. Companion 真机验收项（LIVE）

- [ ] 点击穿透：覆盖区点击落到下方应用（R1 关联）
- [ ] 左键：双击开主窗 vs 单击开菜单误判率；Root Cause A 修复是否稳固
- [ ] 右键：原生菜单手感
- [ ] Hover：气泡信息量 / 是否遮挡视线（R3 轮询微延迟观察）
- [ ] ESC：关菜单 / 命令气泡
- [ ] DND：后端 `NotificationPolicy` 是否真静默（不打扰）
- [ ] 自动隐藏 45s 节奏（B7）
- [ ] 自动恢复：主动/通知触发恢复是否顺
- [ ] 多显示器：跨屏拖动 / 吸附落点
- [ ] 焦点：点击/拖拽后焦点是否回归原应用（R2）
- [ ] 拖动 / 吸附：手感与落点预期（B6 单轴缺口观察）

## 2. Avatar 真机确认（LIVE）

- [ ] 呼吸（Idle 核心/环）目测
- [ ] 眨眼：偶发、自然
- [ ] 嘴型：执行时轻动
- [ ] Thinking / Executing / Completed / Error / Idle 八态切换真实可见
- [ ] `transform-box: fill-box` 在老板 Electron Chromium 版本渲染正常（兼容性低风险，仍待目测）

## 3. 主界面布局合理性（LIVE）

- [ ] 中 AI Core / 左 Capability Matrix / 右 Execution Timeline / 底 Command Dock / 右下 Avatar / Insight / Universe View 布局是否舒适
- [ ] P2 生命周期展示（启动/退出真实态）是否直观；是否需更强提示（不新增组件前提下）

## 4. AI 行为价值（LIVE · 连续 3~5 天）

- [ ] 一天主动建议次数 / 相关性
- [ ] 真被执行 vs 被忽略，忽略原因
- [ ] 时机是否恰当（不打断专注）
- [ ] 误触发 / 无意义建议占比
- [ ] 相比手动，是否更快、省操作

## 5. 连续办公观察项（LIVE · 采集模板见 REAL_WORLD_REVIEW_REPORT §6）

- [ ] 卡顿（风扇/发热/掉帧/虚拟桌面停渲染）
- [ ] 误操作（双击误菜单/吸附落点/菜单混淆）
- [ ] 崩溃（主/渲染进程；Electron 日志）
- [ ] Agent 卡死（Goal 无 `proactive_result`）
- [ ] 执行失败（`execute-suggestion` 未达成）
- [ ] 通知打扰（单位时间数/打断次数）
- [ ] 理解错误（状态色/Timeline 阶段名）

## 6. 已知 P3 缺口（下迭代精修，不阻塞 Beta 1.2 启动）

| 编号 | 项 | 建议（不现场改） |
|------|----|----------------|
| B5 | 自动隐藏 45s 不可配 | 纳入 Companion 偏好（`companion.json`），选项 15/30/45/关闭 |
| B6 | 边缘吸附仅单轴 | 角落双轴吸附（纯窗口几何） |
| R3 | Hover 120ms 轮询微延迟 | 可选：用渲染进程 `mousemove` 辅助或降轮询间隔（性能权衡） |
| R4 | = B5/B6 | 合并处理 |

---

## 7. Beta 1.2 Companion Evolution 范围建议（待 PM 拍板，本阶段不执行）

> 以下为**建议方向**，非已批准任务。待 R1/R2/B2-LIVE 真机结论回来后由 PM 定稿。

1. **若 R1 命中（穿透坐标空间问题）**：在 `pollCompanionCT` 引入 `screen.getPrimaryDisplay().scaleFactor` 归一化 `getCursorScreenPoint` 与窗口矩形到同一坐标空间（纯 Shell 层修正，不触碰业务）。
2. **若 R2 命中（焦点打扰）**：评估交互后焦点归还策略（如交互结束 `mainWindow`/原应用 `.focus()` 或保持桌宠不抢焦）；需权衡「命令气泡输入需焦点」与「不打断工作」。
3. **B5/B6 精修**：偏好可配 + 双轴吸附。
4. **Companion 表现层打磨**（Beta 1.2 主题）：状态色图例/tooltip（UX 报告第四节已指出无图例）、Hover 气泡信息密度、通知节奏可调。
5. **纪律红线延续**：Beta 1.2 仍禁新增 Runtime/EventBus/Memory/State/API/Agent/Tool/Timeline；Companion 始终 Presentation Layer。

---

*本文件为迭代计划，不含任何代码修改。STOP — 等待统一进入 Beta 1.2 Companion Evolution。*
