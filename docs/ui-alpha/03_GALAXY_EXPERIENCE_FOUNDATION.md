# 03_GALAXY_EXPERIENCE_FOUNDATION — Galaxy 体验基础

> AI OS UI Alpha Program v1.0 · Phase 3
> 身份：Senior Product Designer + Three.js Experience Designer + AI OS Interaction Architect
> 执行模式：Audit → Design → Implement → Verify → Document → STOP
> 日期：2026-08-07
> 状态：✅ 完成（纯表现 + 受控交互层）· 🛑 STOP 等 Review

---

## 1. 当前分析（Audit）

### 1.1 Galaxy 在小6中的现实定位（经代码实证）

| 维度 | 当前承担 | 证据 | 结论 |
|---|---|---|---|
| **背景** | ✅ 是 | `solar-canvas` 固定全屏 `z-index:var(--z-ground)`，`data-ws-layer="background"` | 默认就是全屏唯一背景层 |
| **导航** | ⚠️ 部分（仅"宇宙视图"内） | `Ctrl/⌘+U` → `body.universe-mode` 把太阳系提到前台（`z-index:29`），但仅作"Developer View"；日常以背景存在 | 用户**不知道** Galaxy 是空间入口 |
| **状态** | ⚠️ 有数据投影但不可见 | `GalaxyState`（AppState 只读投影）→ `GalaxyRuntime`（渲染模型）→ `solar-system.js` 渲染动态节点；聚焦时经 `FOCUS_CHANGED` 事件写 `AppState.focus` | 状态数据链完整，但**无 UI 层展示节点信息**，用户看不到"这颗星球是 Goal X 在运行" |
| **装饰** | ✅ 是（最大现状） | 首屏 `galaxy-veil` 缺位，银河以纯星空+自转呈现，无叙事、无标签、无聚焦反馈 | **当前 Galaxy 更像"科技壁纸"而非"AI OS 空间入口"** |

### 1.2 关键治理边界（硬约束，本 Phase 必须遵守）

- **L0 红线-5**（Golden State）：禁止修改 Galaxy 语义，银河本体视觉资产 100% 保留。
- **DECISION_004**（Galaxy 边界）：Galaxy = 表现层 + 受控交互层；状态权威永远在 `AppState`；Galaxy 经 `GalaxyState`（只读投影）订阅渲染；任何交互须经叠加层，**不改 `solar-system.js` 本体 / 不持有可写状态 / 不改 Galaxy 数据结构 / 节点模型 / 事件协议 / 导航协议 / 不新增 Capability**。
- 实测确认：`solar-system.js` 已实现受控聚焦（点击行星→`focusOn`→`_publishFocus`→`FOCUS_CHANGED`→`AppState.focus`），并在 `universe-mode` 下把银河提至前台。本 Phase **复用**该既有契约，不改动。

### 1.3 既有资产盘点

- 数据链：`app-state.js`（focus `{capability,id}`）→ `galaxy-state.js`（节点投影，只读）→ `galaxy-runtime.js`（渲染模型）→ `solar-system.js`（Three.js 渲染）。
- 视图壳：`#universeView`（默认 `display:none`，`universe-mode` 显现）+ `#solarCanvas`（背景层）。
- 既有提示：`.uv-tip`（底部居中 Esc 提示）+ `.uv-close`（关闭）。

---

## 2. 体验目标（Design）

> **让 Galaxy 从"背景装饰"升为"小6 AI OS 的空间入口"**——用户一眼理解：
> 太阳 = 小6核心 · 轨道 = Goal · 星球 = 能力域 · 卫星 = Agent · 环 = Memory · 流星 = 主动推送。

具体目标：
1. **叙事化**：背景不再是裸星空，加一层轻叙事纱，让"这是你的 AI 宇宙"被感知。
2. **可读态**：聚焦任意领域节点时，展示其**类型 / 名称 / 生命周期态 / 一句话语义**，让状态可视化。
3. **可进入**：聚焦后提供"进入 / 查看"动作，经既有能力面板唯一入口跳转（**不新增 Capability**）。
4. **统一视觉**：GEL 的颜色 / 字体 / 标签 / 卡片 / 提示与 Phase 2 统一后的 Workspace + Panel 体系**完全一致**（同一套 ui2.css 令牌）。

---

## 3. 允许修改范围（本 Phase 红线清单）

| 类别 | 允许 | 禁止 |
|---|---|---|
| 渲染 | ❌ | 修改 `solar-system.js` 本体（L0 红线-5）|
| 数据 | ❌ | 改 Galaxy 数据结构 / 节点模型（GalaxyState/GalaxyRuntime）|
| 协议 | ❌ | 改事件协议（`FOCUS_CHANGED`）/ 导航协议（`universe-mode`）|
| 能力 | ❌ | 新增 Capability |
| 表现+交互层 | ✅ 视觉包装、状态提示、节点信息展示、Focus/Hover 反馈、进入/退出反馈、UI Overlay、光效配置 | — |
| 后端/运行时/Agent/EventBus/Mobile | ❌ | 全部禁止 |

**实际落地范围**：仅 `ui2.css`（新增 GEL 令牌化样式块）、`index.html`（新增 GEL DOM 节点 + 一个纯表现 JS 模块）、新增 `galaxy-experience.js`（只读 `AppState.focus` / `GalaxyState.getNode`，路由到既有 `PanelManager.openCapability`）。**零改动** `solar-system.js` / `galaxy-state.js` / `galaxy-runtime.js` / `app-state.js` / `overlay-runtime.js`。

---

## 4. 设计方案（Design）

### 4.1 Galaxy 与四者的关系（DECISION_004 隐喻，仅展示映射，不改语义）

| 关系 | 设计表达 |
|---|---|
| **Galaxy ↔ Workspace** | Galaxy 是 Workspace 的"空间隐喻层"：Workspace 是操作台，Galaxy 是该操作台所管理的"目标/能力宇宙"。背景纱在首屏淡入、在 universe 模式淡出，切换自然。 |
| **Galaxy ↔ Capability** | 星球 = 能力域投影；聚焦星球 → GEL 卡片"查看能力"→ 路由到既有 `capabilities` 面板（唯一入口），不新增 Capability。 |
| **Galaxy ↔ Goal** | 轨道 = Goal 投影；聚焦 Goal 节点 → 卡片"查看目标"。 |
| **Galaxy ↔ AI Presence** | 流星 = 主动推送（已在 solar-system 实现）；GEL 状态提示的"运行中/思考中/等待中"色点，与 Phase 8 AI Presence 一致。本 Phase 先建"状态可读"基础，Phase 8 再统一 Presence 语言。 |

### 4.2 Galaxy Experience Layer（GEL）组件

| 组件 | 位置 | 作用 | 数据源 |
|---|---|---|---|
| `galaxy-veil` | 全屏固定（`z-index:z-ground+1`，pointer-events:none） | 背景叙事纱：上下渐隐，让星空"有纵深、有存在感"；universe 模式淡出突出星系 | 纯 CSS |
| `gx-status` | universe 视图左上 | 状态提示：就绪 / 已聚焦某节点 | `AppState.focus` + `GalaxyState` 只读 |
| `gx-card` | universe 视图底部居中 | 节点信息卡：类型标签 / 标题 / 生命周期色点+中文态 / 一句话语义 / 进入动作 | `AppState.focus` + `GalaxyState.getNode` 只读 |
| `gx-hint` | universe 视图底部 | 交互提示：点击星球聚焦 · Esc 返回（聚焦卡片打开时淡出，避免与卡片重叠） | 纯文案 |
| Focus/Hover 反馈 | 复用 solar-system 既有 `focusOn` 缩放 1.25× + 暂停自转 | 进入/退出反馈由既有本体提供，GEL 仅消费其写入的 `AppState.focus` | `FOCUS_CHANGED` 事件 |

### 4.3 视觉统一（与 Phase 2 同源令牌）

GEL 全部使用 ui2.css 既有令牌：`--surface`/`--surface-2`/`--bg`/`--bg-2`/`--border`/`--text`/`--text-dim`/`--accent`/`--accent-2`/`--ok`/`--warn`/`--danger`/`--muted`/`--glow`/`--radius-md`/`--elev-2`/`--elev-3`/`--blur-glass`/`--font-ui`/`--dur-*`/`--ease-*`。卡片玻璃质感（`backdrop-filter: blur + color-mix`）、圆角、阴影、动效曲线与 Phase 2 统一后的 Panel 体系一致。

---

## 5. 实现内容（Implement）

| 文件 | 改动 | 性质 |
|---|---|---|
| `ui2.css` | 新增 `Galaxy Experience Layer (GEL)` 样式块（~70 行，纯令牌化）：`galaxy-veil` / `gx-status` / `gx-card` / `gx-hint` 及状态色点；`universe-mode` 下纱淡出、聚焦卡片打开时提示淡出 | 表现层（additive） |
| `index.html` | ① `#solarCanvas` 后新增 `<div class="galaxy-veil">`；② `#universeView` 内新增 `gx-status` / `gx-card`（含 kind/title/state/desc/enter/close）/ `gx-hint`；③ 末尾新增 `<script src="galaxy-experience.js">` | DOM（表现层） |
| `galaxy-experience.js`（新） | 纯表现控制器：缓存 DOM → 订阅 `AppState.subscribe('*')` + `GalaxyState.onNodeChange` → 读 `AppState.focus`/`getNode` 渲染卡片；"进入"经 `PanelManager.openCapability('capabilities')` 路由；含容错（DOM 缺失静默退出） | 受控交互层（只读） |

**实测边界合规**：`solar-system.js` / `galaxy-state.js` / `galaxy-runtime.js` / `app-state.js` / `overlay-runtime.js` / 后端 / 运行时 / Agent / EventBus / Mobile **零改动**（git diff 已确认 Galaxy 核心未触碰）。

---

## 6. Verify

| 检查项 | 结果 |
|---|---|
| `ui2.css` 花括号平衡 | ✅ 254 / 254 BALANCED |
| `galaxy-experience.js` 语法 | ✅ `node --check` 通过 |
| GEL 令牌引用全部解析（无 typo） | ✅ 14 个令牌均在 ui2.css 定义 |
| `#universeView` 内 GEL 元素 id 与 JS 引用一一对应 | ✅ 10/10 存在 |
| Galaxy 核心文件未改动 | ✅ git diff 确认 `solar-system/galaxy-state/galaxy-runtime` 零改动 |
| 未新增 Capability / 未改导航协议 | ✅ "进入"复用既有 `PanelManager.openCapability('capabilities')` |
| 背景叙事纱与 universe 模式淡出生效 | ✅ CSS `body.universe-mode .galaxy-veil{opacity:0}` |
| 提示重叠规避 | ✅ `gx-hint` 在 `gx-active` 时淡出，原有 `uv-tip`（Esc 提示）保留 |
| 红线自检（Runtime/Backend/Agent/EventBus/Galaxy本体/Mobile/Capability） | ✅ 全部未触碰 |

> 注：本环境为本地浏览器 + http.server 模型，无运行服务；交互行为经代码逻辑 + 选择器/事件链核对验证，未在实时浏览器截图（截图需人工 Review 时本地启动 `start-xiao6.bat` 验证）。

---

## 7. 风险

| 等级 | 风险 | 缓解 |
|---|---|---|
| 🟢 低 | GEL 卡片在 `universe-mode` 才显现，首屏背景态用户仍可能"只见星空" | 背景纱 + 后续（可选）P9 在首屏 HUD 加"星图"入口说明，强化"空间入口"认知；不阻塞本 Phase。 |
| 🟢 低 | `galaxy-veil` 为全屏 `pointer-events:none`，不影响银河拖拽/点击（已确认）。 | — |
| 🟡 中 | 节点信息卡依赖 `AppState.galaxyNodes` 已有数据；若某节点 `metadata.title` 缺失，卡片显示 `node.id`。 | 已用 `meta.title || meta.name || node.id` 兜底；属展示降级，不阻塞。 |
| 🟢 低 | "进入"动作关闭 universe 视图回到工作台打开能力面板——若未来希望"在宇宙内嵌展示"，需独立提案（超出本 Phase 受控交互层）。 | 当前符合 DECISION_004"经叠加层、不改本体"；留作后续。 |

---

## 8. 红线与移交

- **本 Phase 红线零违反**：未改 Galaxy 本体 / 数据结构 / 节点模型 / 事件协议 / 导航协议 / Capability / Runtime / Backend / Agent / EventBus / Mobile。
- **移交 Phase 8（AI Presence）**：GEL 状态色点已与 Presence 态语（运行/思考/等待）收敛，Phase 8 可统一"AI 一直感觉在但不会吵"的 Presence 语言到同一套色 + 文案。
- **移交 P9（Release Polish）**：可评估在首屏 HUD 增加"这是你的 AI 宇宙 · 星图入口"的轻提示，强化空间入口心智。

---

## 9. 完成摘要

Phase 3 在**不改银河本体**的硬约束下，建立了 Galaxy 作为"小6 AI OS 空间入口"的体验基础：
- 背景加叙事纱，让星空从壁纸变为"有纵深的 AI 宇宙"；
- Focus 任意领域节点 → 实时信息卡（类型/名称/生命周期态/语义/进入动作），让 Galaxy 的**状态与导航意义可见**；
- 所有视觉与 Phase 2 统一后的 Workspace + Panel 体系同源（同一套 ui2.css 令牌）；
- "进入"动作经既有能力面板唯一入口，不新增任何 Capability。

**🛑 Phase 3 完成，STOP 等 Review。**
