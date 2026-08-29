# Xiao6 Beta 1.1 — Real World Review Report

> **身份**：Senior Developer（高级开发工程师）
> **阶段**：Beta 1.1 Review — Real World Verification
> **执行模式**：Observe → Record → Verify → Report
> **纪律红线（全程遵守）**：禁止新增 Runtime / EventBus / Memory / State / API / Tool / Agent / UI；禁止修改任何代码；禁止优化任何模块。本阶段唯一动作是 Review、记录、分类、编号，等待统一迭代。

---

## 0. 沙箱能力与诚实边界（必读）

本 Review 在**无显示器、无真实 Electron GUI、无法连续办公**的沙箱环境中执行。因此：

- **✅ 静态可验（CODE）**：代码/资产/链路核查——确认实现存在、纪律合规、逻辑自洽。
- **⚠️ 真实世界待验（LIVE）**：GUI 渲染、缩放/多显示器、焦点、长按办公体感——**必须由老板在本机运行 `start-xiao6.bat` 连续使用 3~5 天验证**。本文件不模拟、不脚本、不人为构造任何 GUI 行为。
- 凡标注 LIVE 的项，均为**待验证假设**，非已确认结论。

---

## 1. 纪律合规复核（Review 前提）

对 Beta 1.1 改动做了禁项扫描：

| 禁项 | 是否新增 | 说明 |
|------|---------|------|
| Runtime / EventBus / Memory / State | ❌ 否 | 全部复用既有 AppState / ExecutionChannel / ZZSSE / AvatarRenderer |
| API（业务） | ❌ 否 | 未新增 `/api/`。Companion 经既有 `bridge.action` → 主窗 `handleCompanionAction` → `ZZChat.send` 复用执行链路 |
| Agent / Tool / Timeline | ❌ 否 | 未触碰； proactive 复用 Phase 9 既有引擎 |
| UI 组件（新业务界面） | ❌ 否 | 仅 Presentation Layer：命令气泡（复用既有聊天输入范式）、通知执行按钮（复用 bridge.action） |
| 代码修改 | ❌ 本阶段 0 修改 | Review 仅读不改 |

**新增的仅是 Electron IPC 桥（窗口几何 / 鼠标路由 / DND 代理），属 Presentation/Shell 层，不引入业务能力**：
`companion:set-clickthrough`、`companion:sync-dnd`、`companion:get-dnd`、`companion:context-menu`、`companion:drag-*`、`companion:main-visible`（广播）。**纪律合规：通过。**

---

## 2. Companion 验证清单（13 项）

| # | 验证项 | 实现机制（CODE 确认） | 静态结论 | 真实世界状态 |
|---|--------|----------------------|---------|-------------|
| 1 | 点击穿透 | `main.js` `setIgnoreMouseEvents` + 120ms 轮询 `getCursorScreenPoint()`，命中矩形→接收、离开→穿透；菜单/气泡打开 `setClickthrough(false)` 强制接收 | ✅ 逻辑自洽、矩形实时刷新（拖拽后 `getPosition()` 重算） | ⚠️ **LIVE 待验**（缩放/多显示器坐标空间，见 R1） |
| 2 | 左键 | 280ms 定时器区分单击（开快捷菜单）/双击（开主窗）；Root Cause A 已修（菜单开即关） | ✅ 实现到位 | ⚠️ LIVE 双击误判菜单概率待观察 |
| 3 | 右键 | `companion:context-menu` → 主进程原生 `Menu.popup`（打开主窗/隐藏/退出） | ✅ 独立事件流，不触碰 AppState | ✅ CODE / ⚠️ LIVE 交互手感 |
| 4 | Hover | `mouseenter/leave` 触发气泡 + 缩放；轮询使其接收鼠标后渲染进程收到 `mouseenter` | ✅ 链路通 | ⚠️ LIVE 气泡信息量/遮挡（120ms 轮询微延迟，R3） |
| 5 | ESC | `keyup` ESC 关闭菜单/命令气泡 | ✅ 实现到位 | ✅ CODE |
| 6 | DND | `syncDnd` → IPC → 主进程 `_proxyProactiveDnd` → 后端 `NotificationPolicy`（Phase 9 既有） | ✅ 链路通，Companion 不直连 `/api/` | ⚠️ LIVE 后端裁决是否真静默待确认 |
| 7 | 自动隐藏 | `IDLE_HIDE_MS=45000` 硬编码，IDLE 满 45s 隐藏 | ✅ 实现 | ❌ **B5 已知缺口**（不可配置，P3） |
| 8 | 自动恢复 | 主动消息 / 通知到达时 `showCompanion()` 恢复显示 | ✅ 实现 | ✅ CODE / ⚠️ LIVE 恢复节奏 |
| 9 | 多显示器 | `displayForWindow()` 用 `screen.getAllDisplays()` 选正确屏 `workArea` 吸附 | ✅ 取屏逻辑正确 | ⚠️ LIVE 跨屏拖动/穿透坐标空间（R1） |
| 10 | DPI | 窗口 200×500 逻辑像素；穿透用 `getCursorScreenPoint` vs `getPosition` | ⚠️ **坐标空间一致性存疑**（设备像素 vs 逻辑像素，见 R1） | ⚠️ LIVE 150% 缩放必须验 |
| 11 | 焦点 | 透明置顶 `skipTaskbar`；交互（点击/拖拽/聚焦输入框）使窗获 OS 焦点 | ✅ 显式 show 才 `.focus()`（无自动抢焦） | ⚠️ LIVE 交互抢焦点是否打扰（R2） |
| 12 | 拖动 | `drag-start/move/end` IPC + 实时 `setPosition`；拖动中 `companionDragActive=true` 强制接收 | ✅ 矩形不陈旧、不中断 | ✅ CODE / ⚠️ LIVE 手感 |
| 13 | 吸附 | `drag-end` 取 `minH/minV` 仅修正单轴 | ❌ **B6 已知缺口**（仅单轴，P3） | ❌ B6 |

**Companion 小结**：P0-1/P0-3 交互闭环代码级完整；B1–B4 已解决。真实可用性集中在 **R1（DPI/多显示器穿透）、R2（焦点）、B2 LIVE** 三项需老板真机确认。

---

## 3. Avatar 验证清单（8 态）

| 态 | 实现机制（CODE 确认） | 静态结论 | 真实世界状态 |
|----|----------------------|---------|-------------|
| 呼吸（Idle 核心/环） | CSS 包裹动画（core/ring/光环） | ✅ | ⚠️ LIVE 目测 |
| 眨眼 | `.av-eye` + `@keyframes av-blink-idle` `transform: scaleY` | ✅ 语义类+transform 契约修复（原 `height` 对 SVG 无效） | ⚠️ LIVE 目测 |
| 嘴型 | `.av-mouth` + `av-effort` `scaleX/scaleY` | ✅ | ⚠️ LIVE 目测 |
| Thinking | `.av-eye--l/r` + `av-think-l/r/av-think-bob` | ✅ | ⚠️ LIVE 目测 |
| Executing | `av-focus`(眼) + `av-effort`(嘴) | ✅ | ⚠️ LIVE 目测 |
| Completed | 专属 SVG + 状态色 | ✅ | ⚠️ LIVE 目测 |
| Error | 专属 SVG（红线眼）+ 红态色 | ✅ | ⚠️ LIVE 目测 |
| Idle | 默认态 + 呼吸 + 偶发眨眼/观察 | ✅ | ⚠️ LIVE 目测 |

**Avatar 小结**：P0-2 根因（SVG 无语义类 + `height` 对 SVG 几何无效）已修复为 `transform` 基契约，8 态动画代码级可见。**「全部真实可见」属 LIVE 待老板目测**（沙箱无法渲染 Chromium GUI）。`transform-box: fill-box` 在现代 Electron Chromium 受支持，兼容性风险低。

---

## 4. 主界面验证清单

| 模块 | 存在性（CODE） | 布局合理性 | 说明 |
|------|---------------|-----------|------|
| 中 AI Core（consciousness-core） | ✅ | ⚠️ LIVE | 限帧 ~30fps、隐藏停 rAF（Phase 10.2 #364） |
| 左 Capability Matrix | ✅ | ⚠️ LIVE | 组件存在 |
| 右 Execution Timeline | ✅ | ⚠️ LIVE | 5 段自然语言映射，禁显原始事件名 |
| 底 Command Dock | ✅ | ⚠️ LIVE | 组件存在 |
| 右下 Avatar | ✅ | ⚠️ LIVE | 复用 AvatarRenderer |
| Insight | ✅ | ⚠️ LIVE | 主动洞察面板 |
| Universe View | ✅ | ⚠️ LIVE | 独立页存在 |

**P2 生命周期展示**：后端 `backend-launcher.js` 已有真实启动/重连/离线态并经 `backend:status` 推送前端；前端复用既有源**未新建展示组件**（守红线，避免触碰 Golden State/新增 UI）。真实「启动/退出状态」随主窗状态条呈现，LIVE 待老板观察是否足够直观。

**主界面小结**：七大模块静态均存在，布局合理性**纯 LIVE 项**，无代码可判。

---

## 5. AI 行为验证

| 维度 | 静态（CODE） | 真实世界（LIVE） |
|------|-------------|-----------------|
| 是否真正主动 | ✅ `proactive.py` 真实产出 `proactive(kind,content,importance)` + `proactive_result`；前端 Toast/通知呈现 | ⚠️ 相关性/误触发率待 3-5 天观察 |
| 是否真正有价值 | ✅ 桌宠现可就地「执行」（B3）、双提示去重（B4）、命令气泡就地下达 | ⚠️ 价值须老板真实任务验证 |
| 是否打扰用户 | ✅ DND/quiet/importance 由后端 `NotificationPolicy` 裁决；主窗可见去重（B4） | ⚠️ 真机静默效果待确认 |
| 建议是否合理 | ✅ 决策层仅判 IGNORE/SUGGEST/NOTIFY/CREATE_GOAL，不执行 | ⚠️ 时机/合理性 LIVE |

**AI 行为小结**：机制链完整、纪律合规；**价值验证尚未发生**，属本 Review 最高优先 LIVE 项。

---

## 6. 连续办公（3~5 天）采集模板

> 沙箱无法执行。以下为交付给老板的真机采集框架，**不预填**。

| 维度 | 记录要点 |
|------|---------|
| 卡顿 | 桌宠常驻 1h 风扇/发热；长对话 Hover 气泡掉帧；切虚拟桌面核心是否停渲染 |
| 误操作 | 双击误弹菜单；拖拽吸附落点；右键/左键菜单混淆 |
| 崩溃 | 主进程/渲染进程崩溃；Electron 日志（`app.getPath('logs')`） |
| Agent 卡死 | 某 Goal 长期无 `proactive_result`；Executor 无后续 |
| 执行失败 | `execute-suggestion` 经 `ZZChat.send` 后未达成；后端报错 |
| 通知打扰 | 单位时间建议数；被忽略占比；打断专注次数 |
| 理解错误 | 状态色误读（红=异常？灰=离线？）；Timeline 阶段名模糊 |

---

## 7. Review 发现与风险编号（R 系列）

| 编号 | 标题 | 优先级 | 证据 | 状态 | 说明 |
|------|------|--------|------|------|------|
| R1 | 缩放/多显示器下点击穿透坐标空间一致性 | P1 | CODE（分析 `getCursorScreenPoint` vs `getPosition` 坐标空间） | ⚠️ LIVE | 若 `getCursorScreenPoint` 返回设备像素而 `getPosition` 返回逻辑像素，150% 缩放下 `inside` 判定失真 → 穿透误判。**真机首验项**。 |
| R2 | 交互使透明置顶窗抢占 OS 焦点 | P2 | CODE（点击/拖拽需接收鼠标→窗获焦点；`cmdInput.focus()`） | ⚠️ LIVE | 交互固有行为；需确认是否打断用户当前应用（如打字中发指令丢焦点）。无自动焦点归还。 |
| R3 | Hover 依赖 120ms 轮询微延迟 | P3 | CODE（`pollCompanionCT` 间隔 120ms） | ⚠️ LIVE | 光标进出矩形有 ≤120ms 迟滞，通常无感；极端场景可观察。 |
| R4 | 自动隐藏阈值不可配 + 吸附仅单轴 | P3 | CODE（即 B5/B6） | ❌ 已知缺口 | 合并至既有 B5/B6，下迭代精修。 |

> 注：R1/R2 为本次 Review **新识别**的真实世界风险；R3/R4 与既有 B5/B6 同源。均**不现场修复**（纪律）。

---

## 8. 结论

1. **代码级完成度：达成。** Beta 1.1「产品完成度打磨、零新增能力」目标已实现——B1 生命感、B2 点击穿透、B3 主动执行、B4 双提示全部 CODE 解决；P0-1 命令气泡、P0-2 统一 Avatar、P0-3 点击穿透状态机、B4 主窗去重均到位；纪律红线全程守住。
2. **真实可用性：未验证。** 所有 GUI 渲染、DPI/多显示器、焦点、长按办公体感均 **LIVE 待老板本机 3~5 天验证**。沙箱无显示，本 Review 已诚实标注，未模拟。
3. **进入 Beta 1.2 前最高优先真机确认项**：**R1（缩放/多显示器穿透）、R2（焦点抢占）、B2 LIVE（覆盖区点击穿透）**。这三者直接决定「桌宠是否像伙伴而非障碍物」的核心命题。
4. **建议**：本阶段 STOP，等待统一进入 **Beta 1.2 Companion Evolution**，按 `NEXT_ITERATION_PLAN.md` 分类推进。

---

*本文件为 Review 记录，不含任何代码修改。所有 LIVE 项由老板在日常使用中填写。*
