# Xiao6 Panel Architecture Audit v1.0

> **Type:** Design + Audit Only — 零代码改动阶段
> **Scope:** 当前所有 Panel / Overlay / Surface 的事实盘点
> **Red Lines (冻结):** Panel 不成为第二 Runtime；Panel 仅是 Operation Layer Projection；不修改 CSS/HTML/JS/PanelManager/EventBus/AppState/Backend；不添加 lifecycle class；不进入 UI-4B-2B Implementation。
> **Author:** Senior Product Designer / Frontend Architecture Engineer
> **Date:** 2026-08-09

---

## 0. 摘要（TL;DR）

- 当前受 **PanelManager 统一管控的面板 = 17 个**（REG 注册表，单一真相源）。
- 另有 **4 处非 REG 的 Operation Layer surface**：`execution-monitor`（自挂载、逃逸管辖）、`osMatrix` / `osInsight` / `osTimeline`（Workspace 常驻 Projection）。
- **无独立 Goal Panel** —— Goal 状态经 `execution-timeline` 投影（符合 "Panel 只是 Projection"）。
- **三处高风险**：① memory 双实现（JZMemory / ZZMemory）；② sysmon / terminal 的 `modeClass` 改 `body` class（全局副作用）；③ `execution-monitor` 自挂载逃逸 OverlayManager 管辖。
- **视觉语言**：已有 `--panel-*` 令牌 + `.zz-panel` / `.glass-panel` 单一来源，但全站仍存 ~15 套 Modal/Panel 重复实现、3 套 Toast、16+ 去中心化 ESC 监听（历史债，本阶段只记录不修）。
- **状态持有红线成立**：WorkspaceState 仅持 UI 状态 + 域引用 id，域真相在 AppState / 后端，Panel 不持有域状态。

---

## 1. 审计方法与读盘范围

### 1.1 已读权威文件（零修改）

| 文件 | 行数 | 作用 |
|------|------|------|
| `xiao6-ui/panel-manager.js` | 291 | Panel 生命周期与入口分发唯一真相源（REG） |
| `xiao6-ui/overlay-manager.js` | 526 | 中央浮层栈 / 中央 ESC / FocusManager / Toast 统一 |
| `xiao6-ui/execution-channel.js` | 196 | 执行监控（emergent 自挂载 panel） |
| `xiao6-ui/execution-timeline.js` | 146 | 执行时间线（Workspace 常驻 Projection） |
| `xiao6-ui/insight-panel.js` | 142 | 主动洞察（信息类 surface） |
| `xiao6-ui/hud-context.js` | 90 | 背景轮询（**非 Panel**，背景层） |
| `xiao6-ui/tasks.js` | 147 | 任务弹窗（zz-task panel） |
| `xiao6-ui/capabilities-view.js` | ≥199 | 能力矩阵 domain panel |
| `xiao6-ui/index.html` | — | Panel DOM 宿主定位 |
| `xiao6-ui/DESIGN.md` | — | Panel 视觉语言与令牌定义 |
| `xiao6-ui/ui2.css` | — | `--panel-*` 令牌、`.zz-panel` / `.glass-panel` 单一来源 |

### 1.2 模块 → 源文件映射（Grep `window.<ZZ*>=`）

| 模块 | 源文件:行 |
|------|-----------|
| ZZCapabilities | capabilities-view.js:199 |
| ZZPanel | app.js:2499 |
| ZZDoc | doc.js:152 |
| ZZHotspot | hotspot.js:1874 |
| ZZMap | map.js:134 |
| ZZMemory | memory-panel.js:204 |
| JZMemory | memory.js:627 |
| ZZMemoryQuery | memory-query.js:136 |
| ZZReview | review.js:63 |
| ZZSysmon | sysmon.js:237 |
| ZZVideo | video.js:87 |
| ZZTerminal | terminal-stream.js:97 |
| ZZSettings | settings.js:1098 |
| ZZTasks | tasks.js:146 |
| ZZSysPrompt | sysprompt.js:51 |

---

## 2. Panel 全景清单（受 PanelManager 管控 · REG 17 项）

`panel-manager.js:91` 定义 `REG = {…}`，17 项。字段语义（L84–87）：`overlayId` = OverlayManager 栈 id；`modeClass` = 以 `body` class 表达的面板模式；`host:true` = 共享 `#zz-panel` 宿主；`btnId` = 直接绑定的入口按钮；`module`+`openName` = 模块打开方法。

| # | Panel ID | 类型 | 模块 | 源文件 | DOM 宿主 | 入场方式 | JS 控制者 | 视觉语言 | Operation Layer |
|---|----------|------|------|--------|----------|----------|-----------|----------|-----------------|
| 1 | weather | domain?→info | (app.js 按钮驱动) | app.js | `#zzPanel`/`#zzPanelBody` | host:true + btnId `wxOpenBtn` | app.js | `.zz-panel` 共享宿主 | 是 |
| 2 | briefing | info | (app.js 按钮驱动) | app.js | `#zzPanel`/`#zzPanelBody` | host:true + btnId `btnBriefing` | app.js | `.zz-panel` 共享宿主 | 是 |
| 3 | memory | domain | JZMemory | memory.js:627 | `#memPanel`/`#memBacklinksPanel`，overlayId `jz-memory` | overlayId | JZMemory | 独立实现（非 `.zz-panel`） | 是 |
| 4 | ai-memory | domain | ZZMemory | memory-panel.js:204 | overlayId `memory` | overlayId | ZZMemory | 独立实现 | 是 |
| 5 | memory-query | domain | ZZMemoryQuery | memory-query.js:136 | overlayId `memory-query` | overlayId | ZZMemoryQuery | 独立实现 | 是 |
| 6 | settings | settings | ZZSettings | settings.js:1098 | `#settingsOverlay`/`#settingsPanel` | overlayId | ZZSettings | `.settings-panel`（feature 专属） | 是 |
| 7 | hotspot | domain | ZZHotspot | hotspot.js:1874 | overlayId `hotspot` | overlayId | ZZHotspot | 独立实现 | 是 |
| 8 | sysmon | execution | ZZSysmon | sysmon.js:237 | modeClass `sysmon-mode` | modeClass（改 body） | ZZSysmon | 独立实现 | 是 ⚠️ 全局副作用 |
| 9 | terminal | execution | ZZTerminal | terminal-stream.js:97 | modeClass `term-mode` | modeClass（改 body） | ZZTerminal | 独立实现 | 是 ⚠️ 全局副作用 |
| 10 | doc | domain | ZZDoc | doc.js:152 | overlayId `doc` | overlayId | ZZDoc | 独立实现 | 是 |
| 11 | map | domain | ZZMap | map.js:134 | overlayId `map` | overlayId | ZZMap | 独立实现 | 是 |
| 12 | capabilities | domain | ZZCapabilities | capabilities-view.js:199 | `#capOverlay`/`#capPanel` | overlayId | ZZCapabilities | 独立实现 + ExecutionChannel/AppState 派生 | 是 |
| 13 | sysprompt | domain | ZZSysPrompt | sysprompt.js:51 | `#sysPromptOverlay`/`#sysPromptPanel` | overlayId | ZZSysPrompt | 独立实现 | 是 |
| 14 | review | domain | ZZReview | review.js:63 | overlayId `review` | overlayId | ZZReview | 独立实现 | 是 |
| 15 | video | info | ZZVideo | video.js:87 | overlayId `video` | overlayId | ZZVideo | 独立实现 | 是 |
| 16 | tasks | execution | ZZTasks | tasks.js:146 | overlayId `zz-task`（ensureRoot 自建 `.zz-task-overlay`） | overlayId + `OverlayManager.track` | ZZTasks | 独立实现 | 是 |
| 17 | agent-profile | domain | ZZPanel | app.js:2499 | `#zzPanel`/`#zzPanelBody` | host:true + module `ZZPanel.profile` | ZZPanel | `.zz-panel` 共享宿主 | 是 |

**子模式分布（17 = 3 + 2 + 12）：**
- `host:true`（3，共享 `#zz-panel` 宿主）：weather、briefing、agent-profile。
- `modeClass`（2，改 `body` class）：sysmon、terminal。
- `overlayId`（12）：其余面板，经 OverlayManager 栈管理。

---

## 3. 非 REG 的 Operation Layer Surface

这些 surface 出现在 Workspace / body，但**未注册进 PanelManager.REG**，属生命周期治理盲区。

| Surface | 位置 | 控制者 | 入场 | 状态 | Operation Layer |
|---------|------|--------|------|------|-----------------|
| `execution-monitor` | `document.body`（#execution-monitor .exec-monitor） | execution-channel.js `mount()` | 自挂载（L140 appendChild） | ⚠️ **逃逸 OverlayManager 管辖**：无 `track`、无 `register`、无 REG、z-index/ESC/焦点失管 | 是（emergent panel） |
| `osMatrix` | `#osMatrix`（`.os-panel.grow`，Workspace 常驻） | index.html + JS | Workspace 常驻 | 常驻 Projection | 是 |
| `osInsight` | `#osInsight`（`.os-panel.grow`，Workspace 常驻） | insight-panel.js `init(#osInsight)` | Workspace 常驻 | 常驻 Projection（MAX 6 同屏） | 是 |
| `osTimeline` | `#osTimeline`（`.os-panel.os-timeline`，Workspace 常驻） | execution-timeline.js `init(#osTimeline)` | Workspace 常驻 | 常驻 Projection（空闲折叠一行） | 是 |

**非 Panel（明确排除，避免误计）：**
- `osDock`（Command Dock，`#osDock`）：Operation Layer **入口**，非 Panel。
- `command-dock.js` / `command-palette.js`：全局 AI 意图入口，仅派发事件 / fetch，**非 Panel**。
- `hud-context.js`：每 20s 背景轮询 `/api/focus/app` 等，仅变化才 `ZZGlance.update()`，**非 Panel**（背景层）。

---

## 4. 按 brief 分类清单

### 4.1 Domain Panels（8）
memory(JZMemory)、ai-memory(ZZMemory)、memory-query(ZZMemoryQuery)、doc(ZZDoc)、map(ZZMap)、hotspot(ZZHotspot)、capabilities(ZZCapabilities)、agent-profile(ZZPanel)。
> 注：review / sysprompt 偏"审阅/提示词"但也归 domain 投影；sysprompt 列于 domain，review 亦可归入。本报告按 REG 字段不强行二分。

### 4.2 Settings Panels（1）
settings(ZZSettings)，feature 专属 `.settings-panel` 容器。

### 4.3 Execution Panels（3）
- `execution-monitor`（execution-channel.js，自挂载逃逸 ⚠️）
- `osTimeline` / execution-timeline（Workspace 常驻 Projection）
- `tasks` / ZZTasks（zz-task 滑入弹窗，经 OverlayManager.track）

### 4.4 Goal Panels（0）
**无独立 Goal Panel。** Grep `goal.?panel|GoalPanel|zz-goal|osGoal|goal-panel` → 无匹配。Goal 状态经 `execution-timeline` 投影（符合 "Panel = Projection" 红线）。

### 4.5 Information Panels（3）
- `insight`（insight-panel.js → #osInsight，Workspace 常驻）
- `video`（ZZVideo → overlayId `video`）
- `hud-context`（hud-context.js，**背景轮询，非 Panel**）

### 4.6 入口非 Panel（2，明确排除）
- Command Dock（`command-dock.js`）
- Command Palette（`command-palette.js`，Ctrl/Cmd+K）

---

## 5. Panel 视觉语言现状

### 5.1 单一来源（已有，优先复用）
- **容器原语：** `.zz-panel`（官方语义基准）+ `.glass-panel`（令牌化视觉基准）。二者均合法，不强制合并。
- **令牌（`ui2.css` L139–172）：** `--panel-radius`(16px)、`--panel-border`、`--panel-header-pad-y/x`(14/18)、`--panel-header-divider`、`--panel-title-font:'Orbitron'`、`--panel-title-size:18px`、`--panel-title-color:var(--accent)`、`--panel-content-pad-y/x`(16/18)、`--panel-footer-pad-y/x`(12/18)、`--panel-toolbar-gap`、`--panel-scrollbar`、`--panel-solid:var(--bg-2)`。
- **毛玻璃：** `.glass-panel`/`.onb-card` blur(28px)+1px 内高光+glow；`.os-panel` 经 `--blur-glass`=26px（与 `.glass-panel` 字面 28px 的 2px 偏差如实保留，不强制统一）。
- **不强制合并：** `.os-panel` / `.settings-panel` / `.onb-card` 为不同类型容器，feature 专属保留。

### 5.2 历史债（只记录，本阶段不修）
- 全站约 **15 套 Modal/Panel 重复实现**，各自 z-index / 关闭逻辑。
- **3 套 Toast**（统一到 `#zzToastRoot` MAX_TOASTS=4 为 OverlayManager 一方）。
- **16+ 去中心化 ESC 监听**（OverlayManager 中央 ESC 为一方）。
- 多数 domain panel 未采用 `.zz-panel` + `--panel-*` 令牌，自绘样式。

---

## 6. 关键风险发现（供迁移规划参考）

| ID | 风险 | 现状 | 严重度 |
|----|------|------|--------|
| R1 | **memory 双实现** | `JZMemory`(memory.js, REG `memory`, overlayId `jz-memory`, DOM `#memPanel`) 与 `ZZMemory`(memory-panel.js, REG `ai-memory`, overlayId `memory`) 并存，两套内存 UI，潜在状态/数据分歧 | 🔴 高 |
| R2 | **modeClass 全局副作用** | `sysmon`/`terminal` 经 `document.body.classList.add/remove('sysmon-mode'|'term-mode')` 切换，影响全局样式与潜在布局，无集中回收保证 | 🔴 高 |
| R3 | **execution-monitor 逃逸** | `execution-channel.js mount()` 自 appendChild 到 `document.body`，未经 `OverlayManager.track` / `PanelManager.register`，z-index/ESC/焦点/栈全失管 | 🔴 高 |
| R4 | **3 共享宿主 zz-panel** | weather/briefing/agent-profile 共用 `#zzPanelBody`，切换时内容互覆盖，生命周期状态易串 | 🟡 中 |
| R5 | **重复 Modal/Toast/ESC** | ~15 套 Panel、3 套 Toast、16+ ESC 监听，治理分散 | 🟡 中 |
| R6 | **状态持有核查** | 见 §7，红线目前成立，但 observability 弱（无统一面板状态投影） | 🟢 低 |

---

## 7. 状态持有核查（红线验证）

**结论：WorkspaceState 不持有域状态，红线成立。**

`panel-manager.js` 的 `WorkspaceState` 仅存：
- `workspace` / `focusedPanelId` / `pinnedPanelIds` / `recentPanelIds`
- `activeContext: { goalId, conversationId, knowledgeNodeId, memoryId, toolName }` —— **只存引用 id，不存域实体**

域真相归属：
- **AppState**（前端域真相，11 子树 + 4 只读投影）。
- **后端 / EventBus**（唯一状态写入口 `applyEvent` → reducers，Single Source Rule）。
- `execution-channel.js` 的 `executions` 内存缓存上限 50，**ephemeral 非域权威**。

→ Panel 经 `activeContext` 引用 id 投影域真相，不持有、不写域状态。符合 "Panel 只是 Operation Layer Projection" 红线。

---

## 8. 结论

- Panel 数量：**17 受管控 + 4 非注册 surface（含 1 逃逸）= 21 个可见面板 surface**；入口 2 个、背景层 1 个不计。
- 治理现状：PanelManager.REG 是面板入口与生命周期的**唯一真相源**，但 `execution-monitor` 逃逸、modeClass 全局副作用、memory 双实现构成三大治理缺口。
- 视觉：令牌与容器原语已就位，缺统一落地。
- 状态：红线成立，但需补 observability（统一面板状态投影）以在迁移中守住红线。

> 本文档为 **Design + Audit Only** 产物。下一步进入 `01_PANEL_LIFECYCLE_MODEL.md`（三态建模）与 `02_PANEL_MIGRATION_PLAN.md`（Phase A/B/C + 6 问答）。**不修改任何代码，不进入 Implementation。**
