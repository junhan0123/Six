# 07 · DOM 迁移蓝图（DOM MIGRATION BLUEPRINT）

> **阶段**：UI-v3 Clean Reconstruction · Phase A-0（Bridge Design Only，不写代码）
> **身份**：Senior Frontend Architect
> **依赖**：`00_UI_V3_AUDIT_FINAL.md`（当前 DOM 三分类）、`01`（四层架构）、`06`（Phase A–G 实施）
> **目的**：把"设计意图"翻译为"可落地的 DOM 迁移清单"——当前树 → 目标树 → 节点映射 → 隐藏/复用/新增 → 风险。全程不写 HTML/CSS/JS。

---

## 0. 桥接原则（三条铁律）

1. **替换而非叠加**：v3 首页 = 一个新容器 `.v3-presence` 承载存在界面；旧 `.os-shell` 在 `body.v3-home` 下整体 `display:none`，不在其骨架上改。
2. **隐藏而非删除**：所有被红线禁止的旧节点，首屏 `display:none`，DOM/JS/功能一律保留（chat / universe / settings 视图不受影响）。
3. **能力复用**：`#osCoreCanvas`、`#osDock`、状态通道、三个 API、`avatar-state`、`zz-events` 事件、`galaxy-state` 关系、既有 Overlay 管理器——直接复用，不复制。

---

## 1. 当前 DOM 树（实测 · index.html）

**背景层（首屏顶部）**

```
<body>
├─ <canvas #solarCanvas .solar-canvas>        (80)  3D 星系背景（world 层）
├─ <div .galaxy-veil>                         (82)  星系叙事纱
```

**OS 首页（`.os-shell` · 85–197）**

```
└─ <section .os-shell #osShell>
   ├─ <nav .os-nav #osNav>                    (88)  【左侧导航】
   │   ├─ .os-nav-brand                        (89)
   │   └─ .os-nav-items ×5                    (92–98) 工作台/指令/星图/语音/设置
   ├─ <header .os-hud>                        (101) 【HUD】
   │   ├─ .os-brand                            (102)
   │   ├─ .os-state (#osState)                (103)
   │   ├─ .os-tools                            (105)
   │   │   ├─ #osContextToggle                 (107) 上下文抽屉入口
   │   │   └─ .os-theme-picker (#osThemePicker)(110) 9 色主题
   │   └─ .os-clock (#osClock)                (122)
   ├─ <div .os-core #osCore>                  (126) AI 核心（角落英雄区）
   │   ├─ <canvas #osCoreCanvas>              (127) 【复用】Avatar 画布
   │   ├─ .os-core-state (#osCoreStateText)   (128) 【复用】状态通道
   │   └─ .os-hero                             (129)
   │       ├─ .os-hero-eyebrow                 (130)
   │       ├─ h1 .os-hero-title                (131)
   │       ├─ .os-core-summary (#csGoals/...)  (134) 能力摘要（P1 加）
   │       ├─ .os-hero-desc                    (141)
   │       └─ .os-hero-actions ×3              (142) 对话/指令/星图
   ├─ <aside .os-side>                        (151) 【右侧双面板】
   │   ├─ .os-panel.grow (#osMatrix)           (152) 能力矩阵
   │   └─ .os-panel.grow (#osInsight)          (156) 主动洞察
   ├─ <div .os-bottom>                        (163) 【底部双面板】
   │   ├─ .os-panel.os-timeline (#osTimeline)  (164) 执行时间线
   │   └─ .os-panel.os-dock                     (168)
   │       ├─ .os-dock-console-head            (169) 【移除】"Intent Console"外壳
   │       └─ <div #osDock .zz-command-dock>   (174) 【复用】意图输入渲染目标
   └─ <div .os-readout #osReadout>            (180) P0-B 状态条（NOW/MEMORY/KNOWLEDGE）
```

**其他心智（不属 v3 首页范围，本蓝图不碰）**

```
├─ <div .app>                                 (259+) 三栏聊天软件（独立心智）
└─ <div #universeView>                        (200)   太阳系开发者视图（独立心智）
```

> 旧代码里还存在的 Overlay 基础设施（`overlay-manager.js` / `focus-manager.js` / `keyboard-manager.js` / `command-dock.js` / `galaxy-state.js` / `avatar-state.js`）全部保留复用，详见 §5。

---

## 2. v3 目标 DOM 树（新增 `.v3-presence`）

v3 首页是**一个**新增容器，挂在 `<body>` 直接子级（与 `.os-shell` 同级），由 `body.v3-home` 类控制显隐。旧 `.os-shell` 在 `v3-home` 下 `display:none`。

```
<body class="v3-home">
│
├─ (旧 #solarCanvas / .galaxy-veil → display:none，不再作背景)
│
├─ <div class="v3-presence" id="v3Presence" aria-label="小6存在界面">
│  │
│  ├─ <div class="v3-core" id="v3Core">              ← Presence Layer（AI Core）
│  │   ├─ <canvas id="osCoreCanvas">                【复用】Avatar 画布（重定位到中心）
│  │   ├─ <div class="v3-core-meta">                ← 文字层（不抢画布）
│  │   │   ├─ <div class="v3-core-id">小6</div>    身份（常量）
│  │   │   ├─ <div class="v3-core-status" id="v3CoreStatus">
│  │   │   │      <span class="v3-dot"></span><span id="v3CoreStatusText">在线</span>
│  │   │   │   </div>                                【复用】#osCoreStateText 通道升级
│  │   │   ├─ <div class="v3-core-doing" id="v3CoreDoing">正在：—</div>  正在处理（/api/goals 首条）
│  │   │   └─ <div class="v3-core-next" id="v3CoreNext">告诉我你的目标</div> 下一步建议
│  │   └─ (点击原地展开浮层 → 复用既有 Overlay 机制，不新增结构)
│  │
│  ├─ <div class="v3-context" id="v3Context">       ← Context Layer（环绕，非面板）
│  │   ├─ <div class="v3-ctx-block v3-ctx-doing" id="v3CtxDoing">  正在处理流（active goals）
│  │   ├─ <div class="v3-ctx-block v3-ctx-memory" id="v3CtxMemory"> 记住了（最近记忆）
│  │   └─ <div class="v3-ctx-block v3-ctx-know" id="v3CtxKnow">     知道（知识语义摘要）
│  │
│  ├─ <div class="v3-intent" id="v3Intent">         ← Intent Layer（唯一输入）
│  │   └─ <div id="osDock" class="zz-command-dock">  【复用】输入框本体（移除 console-head 外壳）
│  │
│  └─ <div class="v3-ambient" id="v3Ambient">       ← Ambient Navigation（≤3 微点）
│      ├─ <button class="v3-ambient-dot" data-overlay="world">理解网络</button>  (⌘4)
│      ├─ <button class="v3-ambient-dot" data-overlay="context">上下文</button>  (⌘ 抽屉)
│      └─ <button class="v3-ambient-dot" data-overlay="settings">设置</button>   (⌘,)
│
├─ <div class="v3-overlay" id="v3WorldOverlay" data-overlay="world">  ← Overlay Layer（⌘4 理解网络，2D）
│      (节点/边来自 galaxy-state 关系 + 三个 API；复用 overlay-manager 唤起/关闭)
│
├─ (旧 .os-shell → display:none，旧 .app / #universeView 不变)
```

> **说明**：设置(`⌘,`)、上下文抽屉(`⌘`)、指令面板(`⌘K`)复用既有 Overlay 系统（overlay-manager/focus-manager/keyboard-manager），**不新增 DOM 结构**；v3 仅新增「理解网络」这一个 Overlay 容器（`#v3WorldOverlay`），因其是 Galaxy 降级的新产物。

---

## 3. 节点映射（旧 → v3 命运）

| 旧节点（行） | 旧角色 | v3 命运 | 处理 |
|---|---|---|---|
| `#solarCanvas` (80) | 星系背景 | **隐藏**（首屏不再作背景） | `display:none` @ `body.v3-home` |
| `.galaxy-veil` (82) | 叙事纱 | **隐藏** | `display:none` |
| `.os-shell #osShell` (85) | 旧首页 | **隐藏**（v3 用 `.v3-presence` 取代其首屏角色） | `display:none` @ `v3-home` |
| `.os-nav #osNav` (88) | 左侧导航 | **隐藏**（能力转 ⌘ / Ambient 微点） | `display:none` |
| `.os-hud` (101) | HUD | **隐藏**（状态入 Core，主题/时钟入 Overlay） | `display:none` |
| `#osCoreCanvas` (127) | Avatar 画布 | **复用 + 重定位** → `.v3-core` 中心 | 移入新容器 |
| `.os-core-state` (128) | 状态通道 | **复用** → `#v3CoreStatusText` | 文案升级 |
| `.os-hero*` (129–146) | 营销文案/三按钮 | **隐藏**（Core 仅留身份+状态+两句话） | `display:none` |
| `.os-side` (151) | 双面板 | **隐藏** → ⌘ 上下文抽屉 Overlay | `display:none` |
| `.os-bottom .os-timeline` (164) | 底部面板 | **隐藏** → Context「正在处理」流 | `display:none` |
| `.os-dock-console-head` (169) | 面板外壳 | **移除**（冗余标题） | v3 文档中不出现 |
| `#osDock` (174) | 输入框渲染目标 | **复用 + 重定位** → `.v3-intent` 底部居中 | 移入新容器 |
| `.os-readout #osReadout` (180) | 状态条 | **隐藏**（信息并入 Context） | `display:none` |
| `.app` (259+) | 聊天软件 | **不变**（独立心智，v3 不碰） | — |
| `#universeView` (200) | 星系开发者视图 | **不变**（独立心智，v3 不碰） | — |

---

## 4. 隐藏节点清单（首屏范围，不删代码）

> **作用域**：仅当 `<body class="v3-home">` 时生效。判据：用 `body.v3-home .os-shell { display:none }` 等**作用域选择器**，绝不用全局 `display:none` 误伤 `.app` / `#universeView`。

| 选择器 | 隐藏方式 | 备注 |
|---|---|---|
| `body.v3-home .os-shell` | `display:none` | 旧首页整体退场 |
| `body.v3-home #solarCanvas` | `display:none` | 停止 3D 星系首屏渲染（性能红利） |
| `body.v3-home .galaxy-veil` | `display:none` | 叙事纱关闭 |
| `body.v3-home .os-nav` | `display:none` | 无左侧导航 |
| `body.v3-home .os-hud` | `display:none` | 无 HUD |
| `body.v3-home .os-core .os-hero` | `display:none` | 隐藏营销文案/三按钮（画布与状态通道保留） |
| `body.v3-home .os-side` | `display:none` | 无 Dashboard 侧栏 |
| `body.v3-home .os-bottom .os-timeline` | `display:none` | 无底部面板 |
| `body.v3-home .os-dock-console-head` | `display:none` | 移除外壳（#osDock 本身留） |
| `body.v3-home .os-readout` | `display:none` | 无独立状态条 |

**关键纪律**：以上**只隐藏、不删除**。去掉 `body.v3-home` 类，旧首页即时满血恢复（回滚开关）。

---

## 5. 复用节点清单（能力来源，零复制）

| 复用节点 / 资产 | 新位置 | 复用方式 |
|---|---|---|
| `#osCoreCanvas` | `.v3-core` 内 | 保留画布，CSS 重定位到视口中心；`avatar-renderer.js` 不动 |
| `#osCoreStateText`（升级为 `#v3CoreStatusText`） | `.v3-core-status` | 既有在线状态通道，文案由 `agent_state` 驱动 |
| `#osDock` | `.v3-intent` 内 | 保留输入框；`command-dock.js::sendText` **完全不改**，仅 CSS 重定位 |
| `#osContextToggle` | 入口并入 `.v3-ambient` 微点 | 上下文抽屉触发器保留 |
| `#osThemePicker` | 移入 `⌘,` 设置 Overlay | 功能保留，入口迁移 |
| `avatar-state.js` META | `.v3-core` 状态色 | 8 态色板**逐字复用**，v3 不新造颜色 |
| `zz-events.js` `agent_state` | 全部组件订阅 | 既有事件，不新增 |
| `ui-data-adapter.js` 模式 | 新 v3 适配器借鉴 | fetch+render 隔离模式复用（展示层全新） |
| `galaxy-state.js` `relations` | `#v3WorldOverlay` | 取关系数据，弃 3D 渲染 |
| `overlay-manager / focus-manager / keyboard-manager` | Overlay Layer | 复用既有唤起/关闭/快捷键机制 |
| 三个 API（`/api/goals|memories|knowledge`） | Context / Core / World | 直接调用，零新增数据源 |

---

## 6. 新增容器需求

### 6.1 容器清单（实现阶段新建）

| 容器 | 层级 | 必须属性 | 内容来源 |
|---|---|---|---|
| `.v3-presence #v3Presence` | 总表面 | `body.v3-home` 下 `display:grid/flex` 居中 | 包含以下全部 |
| `.v3-core #v3Core` | Presence | 视口几何中心 | `#osCoreCanvas` + `.v3-core-meta` |
| `.v3-core-meta` 子节点 | — | `v3-core-id / v3-core-status / v3-core-doing / v3-core-next` | 身份常量 / agent_state / /api/goals / 本地逻辑 |
| `.v3-context #v3Context` | Context | 环绕 Core，低对比 | 3 个 `.v3-ctx-block` |
| `.v3-intent #v3Intent` | Intent | 底部居中，max-width≈720px | `#osDock` |
| `.v3-ambient #v3Ambient` | Ambient Nav | ≤3 微点 | `data-overlay` 触发既有 Overlay |
| `#v3WorldOverlay` | Overlay | `data-overlay="world"` | galaxy-state 关系 + 三 API（2D） |

### 6.2 新增脚本需求（仅规格，本阶段不写）

- **`ui-v3-adapter.js`**（或并入 `ui-data-adapter.js` 重写）：REST 快照 → `.v3-context` / `.v3-core-doing` 渲染；**隔离约束同旧 adapter**（不碰 AppState、不新增事件）。
- **`ui-v3.css`**：单一样式表（见 `08`）。
- **`body.v3-home` 开关**：回滚用，见 `06` §3。

---

## 7. 迁移风险

| 风险 | 触发点 | 缓解（桥接层） |
|---|---|---|
| 隐藏误伤其他视图 | `display:none` 写全局 | 全部用 `body.v3-home` 作用域选择器；`.app`/`#universeView` 明确不在作用域内 |
| `#osDock` 重定位破坏发送 | CSS 改动 | `command-dock.js` 零改动；仅 CSS 定位；出问题回退 CSS 即恢复旧 dock |
| `#osCoreCanvas` 重定位破坏渲染 | 画布尺寸/坐标 | 仅 CSS 重定位；`avatar-renderer.js` 不动；保留旧 `.os-core` 作为非 v3-home 时的回退 |
| 旧 CSS 泄漏到复用元素 | ui2/ui4*/ui5d 命中 `#osCoreCanvas`/`#osDock` | `ui-v3.css` 链接置于**最后**，对复用元素用 `body.v3-home` 作用域覆盖；Phase G 再清旧链接 |
| token 命名冲突 | ui2 与 v3 同名变量 | v3 用独立 token 集（复制 ui2 值、自命名），不与旧 token 混用（见 `08` §3） |
| `scale()` 伪响应式残留 | 旧 body transform | v3 用 `clamp()`/媒体查询；显式复位 `body { transform:none }` @ `v3-home` |
| FOUC / 主题闪烁 | 同旧机制 | 复用既有 `<head>` 内联脚本设 `data-theme`；v3 新增 `body.v3-home` 亦由内联脚本或早期类设置 |
| Overlay 管理器与 v3 容器冲突 | `#v3WorldOverlay` 与既有 overlay 栈 | 复用 `overlay-manager.js` 的注册接口挂载新 overlay，不另起炉灶 |

→ 下一文档 `08_CSS_REPLACEMENT_STRATEGY.md` 定义样式表替换与 token 继承。
→ 再下一文档 `09_COMPONENT_BOUNDARY.md` 定义五组件职责边界。
