# 09 · 组件职责边界（COMPONENT BOUNDARY）

> **阶段**：UI-v3 Clean Reconstruction · Phase A-0（Bridge Design Only）
> **依赖**：`01`（四层架构）、`02`（AI Core）、`03`（Intent Line）、`04`（World Understanding）、`07`（DOM 容器）、`08`（CSS 边界）
> **目的**：定义 v3 首页五大组件（AI Core / Context Layer / Intent Line / Ambient Navigation / Overlay Layer）的职责边界——每个组件**拥有什么 DOM、可读什么、绝不做别人的事**。防止实现阶段职责泄漏导致的"新三软件拼接"。
> **身份**：Senior Frontend Architect

---

## 0. 边界总纲（一条心法）

> **一个空间、一个 AI、一个入口。**

- 五大组件共存于**同一个 `.v3-presence` 表面**，无独立页面。
- 组件之间**只通过 AppState / `zz-events` 既有事件通信**，禁止跨组件直接操作对方 DOM。
- 每个组件"只读自己需要的数据，只渲染自己的容器"。

---

## 1. AI Core（Presence Layer）

**DOM 所有权**：`.v3-core` 及其子节点（`#osCoreCanvas`、`.v3-core-meta` 全部子节点、点击展开浮层）。

**职责**：
- 承载小6的**身份**（常量"小6"）、**当前状态**（订阅 `agent_state` → `avatar-state` 8 态色/标签）、**正在处理**（当前活跃 Goal 标题）、**下一步建议**（上下文生成的一句话）。
- 作为首页**唯一视觉中心**，视觉权重最高。

**可读**：
- 事件：`zz-events` 既有 `agent_state`（状态/颜色/标签）。
- API：`GET /api/goals?status=active` 首条（正在处理）。
- 资产：`#osCoreCanvas`（avatar-renderer 绘制目标，不归 Core 改，只归 Core 持有显示）。

**绝不**：
- ✗ 不拥有输入/发送（那是 Intent Line 的事）。
- ✗ 不渲染导航/设置/上下文抽屉入口（那是 Ambient / Overlay）。
- ✗ 不新造状态颜色（必须来自 `avatar-state`）。
- ✗ 不触发 `body.chat-mode/universe-mode/cp-mode` 等模式类（点击展开浮层用既有 Overlay 机制）。

---

## 2. Context Layer（语境层）

**DOM 所有权**：`.v3-context` 及其三个 `.v3-ctx-block`（doing / memory / know）。

**职责**：
- 以**氛围流**形式呈现"小6知道/在做的事"：正在处理（active goals 流）、记住了（最近记忆微提示）、知道（知识语义化摘要一行）。
- 低对比、随状态淡入，**不争夺中心**。

**可读**：
- API：`GET /api/goals?status=active`（doing）、`GET /api/memories?limit=1`（memory）、`GET /api/knowledge`（know 语义摘要）。
- 事件：`GOAL_*` / `MEMORY_*` 既有领域事件（轻量刷新，不新增契约）。

**绝不**：
- ✗ 不做成三个并排面板 / 卡片网格（Dashboard 心智红线）。
- ✗ 不拥有输入（Intent Line 专属）。
- ✗ 不渲染导航/HUD/设置（那些归 Ambient / Overlay）。
- ✗ 不缓存/修改后端数据；只投影快照。

---

## 3. Intent Line（Intent Layer）

**DOM 所有权**：`.v3-intent` 及其内 `#osDock` 输入框本体。**不含** `.os-dock-console-head`（已移除外壳）。

**职责**：
- 全屏**唯一**意图输入入口。用户说一句话 → `command-dock.js::sendText` → `dispatchEvent('zz:command')`。
- 占位符文案 / 输入线颜色随 `agent_state` 四态（IDLE/THINKING/EXECUTING/ERROR）切换（仅视觉/文案层）。

**可读**：
- 事件：`agent_state`（决定占位符文案与线色）。
- 复用：`#osDock` 渲染目标、`command-dock.js` 发送逻辑（**完全不改**）。

**绝不**：
- ✗ 不生成 Chat 页面（对话历史属 `.app` / Overlay，不常驻首屏）。
- ✗ 不复制导航入口（nav 指令按钮 / hero 对话按钮已隐藏）。
- ✗ 不新增事件、不改发送逻辑、不改 `command-dock.js` 一行。
- ✗ 不把输入做成"搜索框 + 结果下拉"的独立软件感（查东西走 ⌘K Overlay）。

---

## 4. Ambient Navigation（环境导航）

**DOM 所有权**：`.v3-ambient` 及其 ≤3 个 `.v3-ambient-dot` 微点。

**职责**：
- 提供**极轻量**的"深入入口"：每个微点 `data-overlay` 指向一个既有 Overlay（world / context / settings）。
- 是"导航即探索"的具象，不构成左侧导航栏。

**可读**：
- 复用：既有 Overlay 系统（`overlay-manager.js` / `focus-manager.js` / `keyboard-manager.js`）。
- 复用：`#osContextToggle`（上下文抽屉触发器语义）、`#osThemePicker`（设置 Overlay 内）。
- 快捷键：`⌘K` / `⌘4` / `⌘,` / `⌘`（既有 keyboard-manager 已注册）。

**绝不**：
- ✗ 不形成常驻左侧/顶部导航栏（红线）。
- ✗ 不复制 Intent Line 的输入职能。
- ✗ 不自己渲染 Overlay 内容（只触发，内容归 Overlay Layer）。
- ✗ 微点数量 >3（保持极简，避免回到图标墙）。

---

## 5. Overlay Layer（覆盖层）

**DOM 所有权**：既有 Overlay 容器（`overlay-manager.js` 管理的栈）+ v3 新增 `#v3WorldOverlay`（理解网络）。

**职责**：
- 按需深视某件事，覆盖于 `.v3-presence` 之上，关闭即回存在界面。
- 成员：`⌘K` 指令面板、`⌘4` 理解网络（2D 关系图）、`⌘,` 设置（含主题选择器）、`⌘` 上下文抽屉（能力矩阵 + 洞察）。
- 理解网络数据取自 `galaxy-state.js` 关系投影 + 三 API，**不加载 Three.js / 天文贴图**。

**可读**：
- 既有：`overlay-manager` / `focus-manager` / `keyboard-manager` 接口。
- 数据：`galaxy-state` 关系、`/api/goals|memories|knowledge`。

**绝不**：
- ✗ 不常驻首屏（不在 `.v3-presence` 常态流中）。
- ✗ 不成为"离开首页去另一个软件"——关闭即回小6面前。
- ✗ 不恢复 Galaxy 首页心智（理解网络永远是按需 Overlay，非首屏目的地）。
- ✗ 不新增运行时；理解网络用轻量 2D 渲染替代 `solar-system.js`。

---

## 6. 跨组件通信契约

| 通信方向 | 通道 | 禁止 |
|---|---|---|
| 用户输入 → 系统 | `#osDock` → `sendText` → `zz:command` | 禁止组件直接调用彼此方法 |
| 状态变化 → 所有组件 | `agent_state` 事件（`zz-events`） | 禁止组件轮询彼此 DOM |
| 数据刷新 → Context/Core | REST 快照 + 既有 `GOAL_*`/`MEMORY_*` 事件 | 禁止组件写 AppState / 后端 |
| 导航触发 → Overlay | Ambient 微点 `data-overlay` → `overlay-manager` | 禁止 Ambient 自己渲染 Overlay 内容 |
| Core 展开 → 浮层 | 既有 Overlay 机制 | 禁止 Core 触发旧模式类 |

**铁律**：任何组件需要"别人的信息"，要么订阅同一事件/读同一 API，要么经由 AppState；**绝不** `document.querySelector` 跨组件改 DOM。

---

## 7. 边界违规自检表（实现阶段 Code Review 卡点）

| 检查项 | 合规标准 |
|---|---|
| AI Core 是否含输入框 | ✗ 无（输入只在 Intent Line） |
| Context 是否为三面板/卡片 | ✗ 否（氛围流，无边框卡片） |
| Intent Line 是否生成 Chat 页 | ✗ 否 |
| `command-dock.js` 是否被改 | ✗ 零改动 |
| Ambient 是否成导航栏 / >3 微点 | ✗ 否 |
| Overlay 是否常驻首屏 | ✗ 否（按需唤起） |
| 是否新增事件/Runtime | ✗ 否 |
| 组件间是否直接改彼此 DOM | ✗ 否（只经事件/AppState） |
| 是否出现 `.os-nav/.os-hud/.os-side` 于首屏 | ✗ 否（已隐藏） |

→ 三份桥接文档（07/08/09）完成，配合 `00`–`06`，构成 v3 从设计到实施的完整蓝图。
