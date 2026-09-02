# 00 · UI-v3 当前状态终审（AUDIT FINAL）

> **阶段**：UI-v3 Clean Reconstruction · Phase 1（Design Only，不写代码）
> **身份**：Senior Product Designer + Frontend Architect
> **目的**：对当前小6首页 DOM / CSS / JS 做精确分类——**可复用**（作为能力来源）、**必须隐藏**（首页不显示但保留代码）、**必须废弃**（视觉层不带入 v3）。
> 本文是后续 6 份设计文档的事实基础。所有结论均来自对磁盘真实文件的读取（index.html / avatar-state.js / command-dock.js / server.py 路由），非推测。

---

## 0. 一句话结论

当前首页是一个**「AI 控制台 + Dashboard + 三栏聊天 + 3D 星系」四件套的物理缝合体**：`os-shell`（AI OS 首页）、`.app`（三栏聊天软件）、`#universeView`（太阳系视图）并存于同一文档，靠 `body.chat-mode / universe-mode / cp-mode` 互斥类切换。这正是 v2 审计判定的「三个软件拼在一起」。

v3 的重建不是给这套缝合体再加一层 CSS，而是**以"小6存在界面"为第一性原理重新定义首页**，旧代码只提供"能力来源"（真实数据 API、8 态色板、意图发送逻辑、关系投影），**不继承其结构**。

---

## 1. 当前首页 DOM 实况（index.html 78–197 行）

```
<body>
├─ <canvas #solarCanvas>            ← 3D 星系背景（全屏唯一背景，world 层）
├─ <div .galaxy-veil>              ← 星系叙事纱（纯表现）
├─ <section .os-shell #osShell>    ← AI OS 首页（home 视图）
│   ├─ <nav .os-nav #osNav>        ← 【左侧导航脊柱】
│   │   ├─ .os-nav-brand           ← 品牌星标
│   │   └─ .os-nav-items ×5        ← 工作台/指令/星图/语音/设置 五个按钮
│   ├─ <header .os-hud>            ← 【HUD】
│   │   ├─ .os-brand               ← "小6 · 本地个人 AI 副驾"
│   │   ├─ .os-state               ← 状态点 + 文本
│   │   ├─ .os-tools               ← 上下文抽屉按钮 + 主题选择器
│   │   ├─ .os-theme-picker        ← 【9 色主题选择器】（Dashboard HUD 装饰）
│   │   └─ .os-clock               ← 时钟
│   ├─ <div .os-core #osCore>      ← AI 核心（英雄区）
│   │   ├─ <canvas #osCoreCanvas>  ← Avatar 渲染目标（可复用）
│   │   ├─ .os-core-state          ← 在线状态
│   │   └─ .os-hero                ← 标题/副标/能力摘要/描述/三按钮
│   │       ├─ .os-hero-eyebrow
│   │       ├─ h1 .os-hero-title   ← "小6"
│   │       ├─ .os-core-summary    ← 能力摘要（csGoals/csMemory/csKnowledge）
│   │       ├─ .os-hero-actions ×3 ← 对话/指令/星图（多入口）
│   ├─ <aside .os-side>            ← 【右侧双面板】能力矩阵 + 主动洞察
│   ├─ <div .os-bottom>            ← 【底部双面板】执行时间线 + 指令坞
│   │   ├─ .os-timeline
│   │   └─ .os-dock                ← 指令坞（#osDock 渲染目标，可复用）
│   └─ <div .os-readout #osReadout>← P0-B 状态条（NOW/MEMORY/KNOWLEDGE）
├─ <div .app>                      ← 三栏聊天软件（259–467 行，独立心智）
└─ <div #universeView>             ← 太阳系视图（163–183 行，独立心智）
```

**与六条红线对照（当前已违规）**：

| 红线 | 当前状态 |
|---|---|
| 一个空间、一个 AI、一个入口 | ✗ 三视图并存（home/chat/universe）+ 多入口（nav 5 项 + hero 3 按钮 + dock） |
| 不允许 Dashboard 心智 | ✗ `.os-side` 双面板 + `.os-bottom` 双面板 + `.os-readout` 状态条 |
| 不允许左侧导航 | ✗ `.os-nav` 左侧导航脊柱 |
| 不允许 HUD | ✗ `.os-hud`（品牌/状态/9 色选择器/时钟） |
| 不允许 Galaxy 首页 | ✗ `#solarCanvas` 全屏星系为 home 背景 |
| AI Core 为唯一视觉中心 | ✗ Galaxy 占中央舞台，AI Core 推到角落英雄区 |

---

## 2. 可复用部分（作为能力来源，保留并重新挂载）

这些是 v3 **要保留并用起来的真实能力**，不是结构。

### 2.1 后端真实数据 API（server.py，已实现，零改动）
| 端点 | 内容 | v3 用途 |
|---|---|---|
| `GET /api/goals?status=active` | 真实 Goal 列表（`to_dict()`） | NOW / 当前目标 |
| `GET /api/goals/<id>` | 单条 Goal | 目标详情 |
| `GET /api/memories?limit=10` | 真实记忆 | 记住了 / 最近活动 |
| `GET /api/memories/graph` | 记忆节点边 | 理解网络候选 |
| `GET /api/knowledge` | 46 篇文档 + stats | 知识库状态（语义化摘要） |

> v3 不新增任何数据源。所有首页信息来自上述既有端点。

### 2.2 AI Core 渲染目标（DOM + 资产）
- **`#osCoreCanvas`**：`avatar-renderer.js` 的绘制目标。v3 保留作 AI Core 化身画布（光核/呼吸环）。
- **`#osCoreStateText` / `.os-core-state`**：既有在线状态通道，v3 升级为 Presence 文案源。

### 2.3 AI Core 8 态色板（avatar-state.js，纯函数、不持状态）
```
IDLE      #5fb3c8   待命        WAITING   #f0b35e   等待指令
THINKING  #8b9bff   思考中      PLANNING  #c08bff   规划中
EXECUTING #56d364   执行中      COMPLETED #56d3a0   已完成
ERROR     #ff6b6b   异常        OFFLINE   #8a93a6   离线
```
> 这是 AI Core 状态机的**唯一权威色板**，v3 直接复用，不新造颜色。

### 2.4 Intent 发送逻辑（command-dock.js，仅复用、不改）
- `sendText(text)` → `dispatchEvent(new CustomEvent('zz:command', {detail:{text}}))`
- Enter 键 + 发送按钮均调用 `sendText`；附带语音/文件/截图快捷键。
> v3 把 `#osDock` 作为 **Intent Line** 渲染目标，保留 `sendText`，只重定位于外观。发送语义完全不动。

### 2.5 关系投影数据（galaxy-state.js）
- 既有关系投影（`collect(planets,'goal')` 等）虽被错误渲染为灰蓝小球，但其**数据层**是真实资产。
- v3 取其关系数据（goals/agents/memories/knowledge 之间的 `relations`），重渲为 2D 理解网络（见 04 文档）。
> 不使用 Three.js / solar-system.js，仅用其数据。

### 2.6 事件契约（zz-events.js）
- `agent_state` 事件（既有）是 Presence 驱动源；`zz:command` 是意图输入事件。
- v3 只**订阅**既有事件，不新增事件契约。

### 2.7 数据投影模式（ui-data-adapter.js 的 fetch+render 模式）
- 其"REST 快照 → DOM、不碰 AppState"的隔离模式可复用为 v3 的 UI Data Adapter 基础（逻辑可借鉴，但 v3 的展示层全新）。

---

## 3. 必须隐藏部分（首页不显示，但代码保留，供其他视图/模式使用）

v3 首页 = **单一存在界面**。以下元素在 home 上**视觉隐藏**，但**不删除代码**（设置/语音/对话/星图等能力仍通过 Overlay / 快捷键可达，不在首屏常驻）。

| 元素 | 当前位置 | 隐藏理由 | 替代可达方式 |
|---|---|---|---|
| `.os-nav`（左侧导航） | 88–99 行 | 红线：不允许左侧导航 | ⌘ 快捷键 + 右侧 Ambient 微点 + Overlay |
| `.os-hud` 整体 | 101–123 行 | 红线：不允许 HUD | 状态并入 AI Core；上下文入 Overlay |
| `.os-theme-picker`（9 色） | 110–120 行 | Dashboard HUD 装饰，分散注意力 | 移入设置 Overlay（保留功能） |
| `.os-clock` | 122 行 | HUD 装饰 | 移出首屏（非核心） |
| `.os-side`（能力矩阵+洞察） | 151–160 行 | Dashboard 多面板 | ⌘ 上下文抽屉 Overlay（已有 `osContextToggle` 入口） |
| `.os-bottom .os-timeline` | 164–167 行 | Dashboard 面板 | 融入 Context Layer「正在处理」流 |
| `.os-hero-actions`（对话/指令/星图 3 按钮） | 142–146 行 | 多入口 = Dashboard 心智 | 唯一入口 = Intent Line |
| `.os-readout`（P0-B 状态条） | 180–196 行 | 独立状态条 = Dashboard 观感 | 信息并入 Context Layer（非独立条） |
| `#solarCanvas` + `.galaxy-veil` | 80–82 行 | 红线：不允许 Galaxy 首页 | 降级为 ⌘4 理解网络 Overlay（见 04） |
| `.os-hero-desc` / `.os-hero-eyebrow` | 130–141 行 | 营销文案，非存在界面 | 收为 AI Core 内一行微文案 |

> **关键纪律**：隐藏 = `display:none` / `opacity:0` / 移出首屏语境层，**不删 DOM、不改 JS、不删功能**。其他视图（chat / universe / settings）仍按各自逻辑工作。

---

## 4. 必须废弃的视觉层（不带入 v3）

这些是「五代 CSS 叠加」的化妆层 + 旧聊天/通道视觉，**v3 首页不加载、不继承**。

### 4.1 五代叠加 CSS（ADDITIVE 化妆层，已证实治不了结构病灶）
- `ui4b-first-screen.css` / `ui4b-explore-transition.css`
- `ui4c-visible-upgrade.css` / `ui4c-unified-home.css`
- `ui4d-home-experience.css`
- `ui5d-first-screen-polish.css`
> 这些是 v2 审计判定的「化妆品」：每代诊断对了（三心智/天文噪音/后台感），但被禁止动结构，只能调暗/加标签。v3 不继承它们——首页改用**单一新样式表**（`ui-v3.css`，替换而非叠加）。

### 4.2 v3 之前的增量补丁（P0-B / P1 的叠加层）
- `ui-v2-readout.css`（P0-B 状态条样式）
- `ui-v2-workspace.css`（P1 视觉收敛）
> 其内容（能力摘要、意图控制台头、Galaxy 降级）在 v3 中以**全新形式**重新表达，不作为一个个叠加文件延续。避免叠加债务再次累积。

### 4.3 旧聊天 / 通道视觉层（与 home 无关，不带入）
- `styles.css` / `premium.css`（原始聊天后台皮肤）
- `runtime-viz.css` / `execution-channel.css`（通道可视化，属 chat 视图）
> 若 chat 视图独立保留，它们仍由 `.app` 加载；**不在 os-shell 首页加载**。

### 4.4 具体视觉语言债务（在 v3 样式表中反向定义）
- 玻璃卡片（`backdrop-filter` + 阴影的 `.os-panel`）
- 重边框 / 多卡片网格
- 9 色主题选择器
- 星图入口权重
- `os-shell` 的三行 Grid（nav / core+side / bottom）布局范式

### 4.5 `ui2.css` 的处理（分层对待）
- **保留**：其 Design Token 体系（270 个 token、14 级 z-index 阶梯、5 级圆角、统一缓动）——这是健康基础设施。
- **不继承**：其中 `.os-shell` / `.os-nav` / `.os-hud` / `.os-side` / `.os-panel` 的**布局与外观规则**（属旧结构）。
- **做法**：v3 新建 `ui-v3.css`，可复用 `ui2.css` 的 **token 命名与值**，但首页不再链接五代叠加文件；`ui2.css` 仅作为 token 提供方（或将其 token 提炼进 `ui-v3.css`），旧布局规则通过"不在 v3 文档中使用这些类名"自然失效。

---

## 5. 能力来源 → v3 映射总表

| v3 需求 | 取自旧代码（仅能力） | 复用方式 |
|---|---|---|
| 真实目标数据 | `GET /api/goals` | 直接调用 |
| 真实记忆数据 | `GET /api/memories` | 直接调用 |
| 知识语义摘要 | `GET /api/knowledge` | 直接调用 |
| AI Core 化身 | `#osCoreCanvas` + `avatar-renderer.js` | 保留画布 |
| AI Core 状态色 | `avatar-state.js` META | 直接复用色板 |
| Presence 文案 | `agent_state` 事件 + `#osCoreStateText` | 订阅驱动 |
| 意图输入 | `#osDock` + `command-dock.js::sendText` | 仅重定位外观 |
| 理解网络数据 | `galaxy-state.js` 关系投影 | 取数据，弃 3D 渲染 |
| 数据投影隔离 | `ui-data-adapter.js` 模式 | 借鉴 fetch+render 隔离 |

> **核心原则**：旧代码是"能力的仓库"，不是"结构的模板"。v3 首页的 DOM 结构、布局、视觉语言**全部重新设计**，仅从上方仓库提取真实能力。

---

## 6. 红线合规自检（本文产出后，v3 设计须达成）

| 红线 | v3 设计承诺 |
|---|---|
| 一个空间、一个 AI、一个入口 | 单一 `.os-presence` 表面；AI Core 唯一中心；Intent Line 唯一输入 |
| 不允许 Dashboard 心智 | 无侧栏双面板 / 无底部双面板 / 无独立状态条 |
| 不允许左侧导航 | 无 `.os-nav`；导航走快捷键 + Ambient 微点 + Overlay |
| 不允许 HUD | 无 `.os-hud`；品牌/时钟/主题选择器移出首屏 |
| 不允许 Galaxy 首页 | `#solarCanvas` 降级；理解网络仅 ⌘4 Overlay |
| AI Core 唯一视觉中心 | 光核居中、占主视觉权重，其余信息环绕 |

---

## 7. 终审结论

1. **当前首页结构必须整体弃用**为 v3 首页的布局模板——它不是"优化对象"，是"能力来源清单"。
2. **真实能力已齐备**：三个数据 API + 8 态色板 + 意图发送 + 关系投影 + 事件契约，**v3 无需新增任何后端/运行时/事件**。
3. **视觉层清零重来**：五代叠加 + P0-B/P1 补丁 + 玻璃卡片 + 9 色选择器，全部不带入 v3；改用单一 `ui-v3.css`（替换范式）。
4. **隐藏而非删除**：所有被红线禁止的元素（nav/hud/side/bottom/readout/galaxy）在首屏隐藏，代码与功能保留供其他视图。

→ 下一文档 `01` 据此定义 v3 全新信息架构（Presence / Context / Intent / Overlay 四层）。
