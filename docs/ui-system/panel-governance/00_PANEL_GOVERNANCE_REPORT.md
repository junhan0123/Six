# Xiao6 Panel Governance Foundation v1.0

> **Type:** Audit + Minimal Governance Implementation — 零代码改动阶段
> **Scope:** Panel 管理边界（Registry / Ownership / State Boundary / Risk / Migration Readiness）
> **Red Lines (冻结):** Panel = Operation Layer Projection；Panel 不持有业务状态；Galaxy → activeContext → Panel 单向关系；Dormant → Attention → Active 为 UI Projection State（非新增 DOMAIN/SYSTEM 事件）。
> **Strictly Forbidden:** 大规模 CSS 修改 / `.zz-panel` 全量迁移 / 生命周期 class 接入 / Panel 动画设计 / 修改 AppState / 修改 EventBus / 修改 DOMAIN-SYSTEM Contract / 修改 Backend / 修改 Agent / 新增第二 Registry。
> **Author:** Senior Frontend Architect / AI OS Governance Engineer
> **Date:** 2026-08-10
> **Status:** ✅ 完成 · 🛑 STOP · 等待 Review（不进入 Panel Visual Migration）

---

## 0. 摘要（TL;DR）

- **A1 Registry Freeze**：`panel-manager.js:91` 的 `REG` 是**唯一 Panel Registry 事实来源**（17 项）。已证实全站**不存在第二 Panel Registry**（`capability-registry.js`、`provider_registry`、测试内 `registry` 均为独立域或 mock）。但 REG 的 `modeClass` 字段仅声明 2 个 body 模式面板，未能覆盖 ~12 个直接写 `body.classList` 的模块——属「状态依赖」记录不全，需在迁移阶段补注，**不构成第二 Registry**。
- **A2 Host Ownership**：17 REG 面板 = 3 `host:true`（共享 `#zz-panel`）+ 12 `overlayId`（经 OverlayManager）+ 2 `modeClass`（改 body）+ 1 逃逸面 `execution-monitor`（自挂载，无宿主/无销毁方/无控制方在 PanelManager 体系内）。
- **A3 State Boundary**：`WorkspaceState` 仅存 UI 状态 + 域引用 id（✓ 红线成立）；Panel 对 `AppState` 仅 `getState/subscribe` 只读，唯一写入口 `applyEvent` 仅由 `event-bridge.js` 调用（后端→前端桥，合法）。**但 `<body>` 作为全局状态被 ~12 个 Panel 模块分散直接写入**，且 `command-palette.js:102` 硬编码一份**不全**的移除清单 → 这是本阶段最关键的治理缺口（见 R7）。
- **A4 execution-monitor**：本质是 `ExecutionChannel.executions`（内存、上限 50、ephemeral）的**只读投影**；因 `mount()` 直接 `appendChild(document.body)` 而逃逸 OverlayManager 管辖。已给出未来纳入 Operation Layer 的明确路径；**按 brief 禁止立即迁移**。
- **Verification**：DOMAIN=71 ✓（数得 `EVENTS` 71 条）、SYSTEM=8 ✓（`SYSTEM_EVENTS` 8 条）、Event Contract 不变 ✓、`AppState` 不变 ✓（均**零代码改动**，本任务未触碰任何源文件）。

---

## 1. Registry（A1 — Registry Freeze）

### 1.1 唯一性确认（禁止第二 Registry）

| 候选 | 位置 | 性质 | 是否属于「第二 Panel Registry」 |
|------|------|------|-------------------------------|
| `REG` | `panel-manager.js:91` | Panel 生命周期 + 入口分发 | **是 — 唯一 Panel Registry** |
| `capability-registry.js` | `xiao6-ui/capability-registry.js:2` | 电脑能力目录 + 风险映射（Phase 7 Order 2） | 否 — 独立域（能力注册，非 Panel） |
| `provider_registry` | 后端 `provider_registry.py`（settings.js:311 注释引用） | LLM Provider 元数据 | 否 — 后端域 |
| `registry` (tests) | `tests/*.frontend.test.js:50/58` | 测试内 DOM 元素 mock | 否 — 测试脚手架 |

**结论：全站仅 `panel-manager.js` 的 `REG` 一个 Panel Registry。A1 禁止新增第二 Registry 的事实前提成立。**

### 1.2 REG 全量事实表（17 项，单一真相源）

字段语义（`panel-manager.js:84-89`）：`module`+`openName`=程序化打开入口；`overlayId`=OverlayManager 栈 id；`modeClass`=以 body class 表达的面板模式；`btnId`=按钮驱动入口；`host:true`=复用共享 `#zz-panel` 宿主。

| # | Panel ID | Owner Module | host | overlayId | modeClass | lifecycle candidate | state dependency |
|---|----------|--------------|------|-----------|-----------|---------------------|------------------|
| 1 | weather | app.js（按钮驱动） | ✅ | `zz-panel` | — | host 内容切换（Dormant↔Active） | 无域状态；仅 `WorkspaceState.focus` |
| 2 | briefing | app.js（按钮驱动） | ✅ | `zz-panel` | — | host 内容切换 | 同上 |
| 3 | memory | JZMemory (`memory.js:627`) | — | `jz-memory` | — | overlay open/close | 读 `AppState.memory`（投影）；无写 |
| 4 | ai-memory | ZZMemory (`memory-panel.js:204`) | — | `memory` | — | overlay open/close | 读 `AppState.memory`（投影）；无写 |
| 5 | memory-query | ZZMemoryQuery (`memory-query.js:136`) | — | `memory-query` | — | overlay open/close | 读 `AppState.memory`（投影）；无写 |
| 6 | settings | ZZSettings (`settings.js:1098`) | — | `settings` | — | overlay open/close | 读/写 `localStorage` 偏好（非域真相） |
| 7 | hotspot | ZZHotspot (`hotspot.js:1874`) | — | `hotspot` | — | overlay open/close | 读 `AppState`/domain；无写 |
| 8 | sysmon | ZZSysmon (`sysmon.js:237`) | — | — | `sysmon-mode` | body class toggle | **改 `<body>` 全局 class（副作用）** |
| 9 | terminal | ZZTerminal (`terminal-stream.js:97`) | — | — | `term-mode` | body class toggle | **改 `<body>` 全局 class（副作用）** |
| 10 | doc | ZZDoc (`doc.js:152`) | — | `doc` | — | overlay open/close | 读 domain；无写 |
| 11 | map | ZZMap (`map.js:134`) | — | `map` | — | overlay open/close | 读 domain；无写 |
| 12 | capabilities | ZZCapabilities (`capabilities-view.js:199`) | — | `capabilities-view` | — | overlay open/close | 读 `AppState`+`ExecutionChannel`（投影） |
| 13 | sysprompt | ZZSysPrompt (`sysprompt.js:51`) | — | `sysprompt` | — | overlay open/close | 读 domain；无写 |
| 14 | review | ZZReview (`review.js:63`) | — | `review` | — | overlay open/close | 读 domain；无写 |
| 15 | video | ZZVideo (`video.js:87`) | — | `video` | — | overlay open/close | 读 domain；无写 |
| 16 | tasks | ZZTasks (`tasks.js:146`) | — | `zz-task` | — | overlay open/close（经 `OverlayManager.track`） | 读 domain；无写 |
| 17 | agent-profile | ZZPanel (`app.js:2499`) | ✅ | `zz-panel` | — | host 内容切换 | 读 `activeContext`（投影）；无写 |

**子模式分布（17 = 3 + 12 + 2）：** `host:true` ×3（weather/briefing/agent-profile，共享 `#zz-panel`）、`overlayId` ×12、`modeClass` ×2（sysmon/terminal）。

### 1.3 Registry 覆盖度缺口（治理发现，非第二 Registry）

REG 的 `modeClass` 字段仅声明 sysmon/term 两个面板，但**实际直接写 `body.classList` 的 Panel 模块有 ~12 个**（见 §3.3）。REG 作为「状态依赖」真相源**未记录这 12 个 body 模式写者**。这是 Registry 的**文档/覆盖度缺口**，应在迁移阶段以 `bodyMode` 字段回填，**不视为新增第二 Registry**。

---

## 2. Ownership（A2 — Host Ownership Mapping）

### 2.1 创建 / 销毁 / 控制方映射

**A. `host:true`（3 项，共享 `#zz-panel` 宿主）**

| Panel | 创建方 | 销毁方 | 控制方 | 备注 |
|-------|--------|--------|--------|------|
| weather | `app.js` 按钮 `wxOpenBtn` 点击 | `OverlayManager.close('zz-panel')` | app.js + PanelManager | 内容写入 `#zzPanelBody`，互斥 |
| briefing | `app.js` 按钮 `btnBriefing` 点击 | `OverlayManager.close('zz-panel')` | app.js + PanelManager | 同上 |
| agent-profile | `ZZPanel.profile()`（`app.js:2499`） | `OverlayManager.close('zz-panel')` | ZZPanel + PanelManager | 同上 |

**B. `overlayId`（12 项，经 OverlayManager 栈）**

| Panel | 创建方（open） | 销毁方（close） | 控制方 | 备注 |
|-------|----------------|------------------|--------|------|
| memory | `JZMemory.open()` | `JZMemory.close()` / `OverlayManager.close('jz-memory')` | JZMemory | |
| ai-memory | `ZZMemory.open()` | `ZZMemory.close()` / `OverlayManager.close('memory')` | ZZMemory | |
| memory-query | `ZZMemoryQuery.open()` | 同上 | ZZMemoryQuery | |
| settings | `ZZSettings.open()` | 同上 | ZZSettings | |
| hotspot | `ZZHotspot.open()` | 同上 | ZZHotspot | |
| doc | `ZZDoc.open()` | 同上 | ZZDoc | |
| map | `ZZMap.open()` | 同上 | ZZMap | |
| capabilities | `ZZCapabilities.open()` | 同上 | ZZCapabilities | |
| sysprompt | `ZZSysPrompt.open()` | 同上 | ZZSysPrompt | |
| review | `ZZReview.open()` | 同上 | ZZReview | |
| video | `ZZVideo.open()` | 同上 | ZZVideo | |
| tasks | `ZZTasks.open()`（自建 `.zz-task-overlay` 经 `OverlayManager.track`） | `ZZTasks.close()` / `OverlayManager.close('zz-task')` | ZZTasks | |

**C. `modeClass`（2 项，改 `<body>` class）**

| Panel | 创建方（open，加 body class） | 销毁方（close，去 body class） | 控制方 | 备注 |
|-------|-------------------------------|--------------------------------|--------|------|
| sysmon | `ZZSysmon`（`sysmon.js:208` `toggle('sysmon-mode', on)`） | `panel-manager.js:191` `remove('sysmon-mode')` **+** `command-palette.js:102` 清理列表 | ZZSysmon **与** PanelManager **双重** | ⚠️ sysmon-mode 被两处控制 |
| terminal | `ZZTerminal.open()`（加 `term-mode`） | `panel-manager.js:191` `remove('term-mode')` **+** `command-palette.js:102` 清理列表 | ZZTerminal **与** PanelManager **双重** | |

**D. 逃逸面（1 项，不在 REG）**

| Surface | 创建方 | 销毁方 | 控制方 | 备注 |
|---------|--------|--------|--------|------|
| `execution-monitor` | `execution-channel.js mount()`（`L140` `appendChild(document.body)`） | **无**（自挂载，无 `OverlayManager.close` / `PanelManager.close` 路径） | execution-channel.js 自管 | ⚠️ z-index / ESC / 焦点 / 栈全失管（详见 §4 R3、§5 A4） |

### 2.2 入口所有权歧义（次要发现）

`panel-manager.js:156` 在 `init()` 中**额外**为 `hsOpenBtn→hotspot`、`btnMem→memory`、`settingsOpenBtn→settings` 绑定 `click → _recordOpen`，而这三个面板在 REG 中已以 `module` 形式被 `open()` 包裹记录。结果是 `_recordOpen` 在「按钮点击」与「模块 open 包裹」两条路径上**都**会被调用——逻辑幂等（仅更新 `recentPanelIds`），但反映出入口所有权边界模糊（按钮驱动 vs 模块驱动未明确单一归属）。建议迁移阶段明确：每个面板**恰好一个**权威入口（REG 的 `btnId` **或** `module`，不双绑）。

---

## 3. State Boundary（A3 — State Boundary Audit）

### 3.1 WorkspaceState（UI-only）✓ 红线成立

`panel-manager.js:21-81` 的 `WorkspaceState` 仅存：
- `workspace` / `focusedPanelId` / `pinnedPanelIds` / `recentPanelIds`
- `activeContext: { goalId, conversationId, knowledgeNodeId, memoryId, toolName }` —— **仅存引用 id，不存域实体**

Panel 经 `activeContext` 引用 id 投影域真相，不持有、不写域状态。符合「Panel 只是 Operation Layer Projection」红线。

### 3.2 AppState 写边界 ✓ Panel 全只读

| 检查项 | 结果 |
|--------|------|
| 唯一写入口 | `app-state.js:703 applyEvent`（single write entry，合约外事件静默忽略 L707-709） |
| 谁调用 `applyEvent` | 仅 `event-bridge.js:28`（后端 SSE → `applyEvent` 写入统一状态核心，合法桥接） |
| Panel 模块是否调用 `applyEvent` | **否**。所有 Panel（memory/memory-panel/doc/map/hotspot/review/video/settings/tasks/sysmon/terminal/capabilities 等）对 `AppState` 仅 `getState()/subscribe()`（只读投影） |
| 结论 | Panel 不写业务状态、不保存业务真相到 AppState ✓ |

### 3.3 `<body>` 全局状态边界 ⚠️ **核心治理缺口（R7）**

`<body>` 的 `classList` 是事实上的**全局状态**，但**不被 REG 拥有、不被 PanelManager 集中治理**。直接写 `body.classList` 的 Panel 模块（grep `body.classList` 实测）：

| 模块 | 写入的 class | REG 是否记录 |
|------|--------------|--------------|
| `doc.js:132,140` | `doc-mode` | ❌ 未记录 |
| `hotspot.js:682` | `hotspot-mode` | ❌ 未记录 |
| `map.js:116,124` | `map-mode` | ❌ 未记录 |
| `memory-panel.js:186,194` | `memory-mode` | ❌ 未记录 |
| `memory-query.js:118,127` | `memq-mode` | ❌ 未记录 |
| `memory.js:563,589` | `mem-open` | ❌ 未记录 |
| `review.js:45,53` | `review-mode` | ❌ 未记录 |
| `weather.js:461,473` | `weather-mode` | ❌ 未记录（REG 仅记 `btnId`，未记 body-mode） |
| `video.js:64,72` | `video-mode` | ❌ 未记录 |
| `tasks.js:66,86` | `zz-task-mode` | ❌ 未记录 |
| `sysmon.js:208,226` | `sysmon-mode` | ⚠️ 部分（REG 记 `modeClass`，但**模块自身也写**，双重权威） |
| `settings.js:207,210` | `reduced-motion`（偏好，非面板模式） | ❌ 未记录 |

**三重失控表现：**
1. **无集中权威**：12 个面板各自写 `body` class，REG 仅覆盖 2 个 `modeClass`（且 sysmon 还双重控制）。
2. **`command-palette.js:102` 硬编码移除清单**：`['hotspot','weather','sysmon','term','doc','memory','map','memq']` 每个 `+'-mode'`。该清单**漏列** `mem-open`(memory.js)、`review-mode`、`video-mode`、`zz-task-mode`、`reduced-motion` → 打开命令面板时这些 body 模式**不会被清理，发生泄漏**。
3. **sysmon-mode 双重权威**：`sysmon.js:208` 自管 `toggle` **且** `panel-manager.js:191` 在 `close()` 中 `remove` **且** `command-palette.js:102` 也 `remove` → 同一全局状态的写权分散在 3 处。

> 这与前序 audit 的 R2（sysmon/term modeClass 全局副作用）同源但范围更广：**问题不是「2 个 modeClass 面板」，而是「`<body>` 作为全局状态完全没有单一所有权」**。

---

## 4. Risk Items（风险清单）

| ID | 风险 | 现状 | 严重度 | 归属 |
|----|------|------|--------|------|
| R1 | **memory 双实现** | `JZMemory`(memory.js, REG `memory`, overlayId `jz-memory`) 与 `ZZMemory`(memory-panel.js, REG `ai-memory`, overlayId `memory`) 并存，两套内存 UI，潜在状态/数据分歧 | 🔴 高 | State Boundary / Ownership |
| R2 | **modeClass 全局副作用** | `sysmon`/`terminal` 经 body class 切换影响全局样式与布局，无集中回收保证 | 🔴 高 | State Boundary |
| R3 | **execution-monitor 逃逸** | `execution-channel.js mount()` 自 `appendChild(document.body)`，未经 `OverlayManager.track` / `PanelManager.register`，z-index/ESC/焦点/栈全失管 | 🔴 高 | Ownership / A4 |
| **R7** | **`<body>` 模式控制权分散**（本阶段新发现） | ~12 面板模块直接写 `body.classList`；`command-palette.js:102` 硬编码**不全**的移除清单（漏 `mem-open`/`review-mode`/`video-mode`/`zz-task-mode`）；sysmon-mode 三重控制 | 🔴 高 | State Boundary / Registry |
| R4 | **3 共享宿主 `#zz-panel`** | weather/briefing/agent-profile 共用 `#zzPanelBody`，切换时内容互覆盖，生命周期状态易串 | 🟡 中 | Ownership |
| R5 | **重复 Modal/Toast/ESC** | ~15 套 Panel、3 套 Toast、16+ ESC 监听，治理分散（历史债，本阶段只记录） | 🟡 中 | Ownership |
| R6 | **状态 observability 弱** | 无统一面板状态投影，迁移中守红线需补可观测性 | 🟢 低 | State Boundary |

---

## 5. Migration Readiness（迁移就绪度）

### 5.1 A4 — execution-monitor 专项

**现状确认**：`execution-monitor` 是 `ExecutionChannel.executions`（内存数组、上限 50、ephemeral、非域权威）的**只读投影**，本身不写任何业务状态、不触碰 AppState/EventBus——符合「Panel = Projection」精神，问题仅在**生命周期逃逸**。

**未来纳入 Operation Layer 的推荐路径（仅规划，不执行）**：
1. 在 `panel-manager.js` 的 `REG` 中新增 `execution-monitor` 条目（如 `{ module:'ExecutionChannel', openName:'mount', overlayId:'execution-monitor' }`），使其成为受管面板。
2. `mount()` 改为经 `OverlayManager.track('execution-monitor', panel)` 登记，纳入中央浮层栈 / 中央 ESC / 焦点 / z-index 治理（复用既有 `OverlayManager`，**不新建第二套**）。
3. 保留其只读投影本质：仍消费 `ExecutionChannel` 订阅，**不新增任何事件、不写 AppState**。
4. 回归验证：DOMAIN=71 / SYSTEM=8 / Event Contract / AppState 四项不变。

> **按 brief 禁止立即迁移**——本阶段仅确认方案，落地留待后续 Phase。

### 5.2 各面板迁移就绪度评分

| Panel | 路径 | 就绪度 | 阻塞项 |
|-------|------|--------|--------|
| 12 个 `overlayId` 面板 | 已受 OverlayManager 治理 | 🟢 Ready | 无（视觉层另议） |
| 3 个 `host:true` 面板 | 共享宿主，逻辑已收口 | 🟡 Ready* | R4（内容互斥串台） |
| sysmon / terminal | body modeClass | 🔴 Blocked | R2 + R7（需先解决 `<body>` 模式集中治理） |
| execution-monitor | 逃逸面 | 🔴 Blocked | R3 + A4（需先注册 + track） |
| memory / ai-memory | 双实现 | 🔴 Blocked | R1（需先解决双 memory 收敛） |

**迁移前置条件（三大 gate）：**
- **Gate-1（R7）**：为 `<body>` 模式建立单一权威——要么将 12 个面板模式收口进 REG（`bodyMode` 字段 + PanelManager 集中 add/remove），要么废弃 body-mode 改用 OverlayManager 栈态。必须消除 `command-palette.js:102` 的硬编码清单。
- **Gate-2（R3/A4）**：注册 `execution-monitor` 并经 `OverlayManager.track`。
- **Gate-3（R1）**：收敛 JZMemory / ZZMemory 双实现（或明确二者语义边界为不同域）。

---

## 6. Verification（brief 强制项）

本任务为 Audit + Minimal Governance Implementation，**零代码改动**。以下四项均经读盘复核确认未变：

| 验证项 | 结果 | 证据 |
|--------|------|------|
| DOMAIN = 71 不变 | ✅ | `zz-events.js` `EVENTS` 对象逐条计数 = **71**（L14-91） |
| SYSTEM = 8 不变 | ✅ | `zz-events.js` `SYSTEM_EVENTS` 对象计数 = **8**（L176-186） |
| Event Contract 不变 | ✅ | `zz-events.js` 未经任何修改；`isEvent`/`isSystemEvent` 单一来源逻辑完好 |
| AppState 不变 | ✅ | `app-state.js` 未经任何修改；`applyEvent` 唯一写入口（L703）与 `AppState` 契约 intact；Panel 仍仅只读 |

**结论：四项冻结契约全部保持，符合 brief 验收要求。**

---

## 7. 结论与 STOP

- **A1 Registry Freeze**：`REG`（panel-manager.js:91）确认为唯一 Panel Registry，17 项全量事实已记录；无第二 Registry；但 `modeClass` 字段对 `<body>` 模式写者的覆盖不全（R7 的 Registry 侧表现）。
- **A2 Host Ownership**：3 host + 12 overlay + 2 modeClass 的所有权映射已厘清；`execution-monitor` 为无宿主/无销毁方/无控制方的逃逸面；存在按钮/模块双绑的入口歧义。
- **A3 State Boundary**：`WorkspaceState` 仅 UI + 引用 id（✓）；Panel 对 `AppState` 全只读（✓）；但 `<body>` 全局状态被 ~12 面板分散写、`command-palette` 硬编码不全清单（R7 🔴）。
- **A4 execution-monitor**：确认其为只读投影、逃逸管辖；给出注册 + `OverlayManager.track` 的未来路径；**不立即迁移**。
- **Verification**：DOMAIN=71 / SYSTEM=8 / Event Contract / AppState 全部不变，零代码改动。

> 🛑 **STOP — 等待 Review。不进入 Panel Visual Migration，不修改任何代码、CSS、HTML、AppState、EventBus、Backend、Agent。**
