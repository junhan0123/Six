# UI-5 · Unified Space Model — Single Space Architecture（01_UNIFIED_SPACE_MODEL.md）

> 阶段：UI-5 · Design（仅设计，零代码改动）
> 身份：Senior Product Designer + Frontend Architect
> 输入：00_AUDIT.md（Q1–Q5 真实行号证据）
> 纪律红线：不修改 Backend / Agent Runtime / AppState / EventBus / solar-system.js / 不新增事件 / 不新增第二套状态
> 设计原则：① Galaxy=World Layer（非页）② Workspace=Operation Layer（非首页）③ Chat 入 Command Dock（非独立入口）④ Navigation=Capability Focus（不切页）

---

## 一、目标与纪律

将 `osShell Home`、`universeView Galaxy`、`legacy .app Chat` 三个平级 DOM 树（审计根因 1）合并为**一个连续、分层、永不合页的 AI OS 空间**。设计全程基于 00_AUDIT.md 的真实 file:line 证据，不重建任何子系统，不新增状态机。

---

## 二、现状事实（来自审计，非假设）

| DOM 树 | 锚点 | 当前语义 | 当前激活方式 |
|---|---|---|---|
| `#solarCanvas` + `.galaxy-veil` | `index.html:73` / `index.html:75` | 太阳系 + 星空，**世界背景** | 常驻（z0 / z=--z-ground+1，低于 os-shell） |
| `#osShell` `.os-shell` | `index.html:78` | 新 Home Workspace | `body` 默认态（z5） |
| `#universeView` | `index.html:161` | 旧 Galaxy 独立页 | `body.universe-mode` + `#universeView.open`（z30，`background:var(--bg)` 不透明，ui2.css:857-861） |
| `#osChatFab` | `index.html:184` | 聊天浮动按钮 | 点击 → `openChat()` |
| `.app` `#app` | `index.html:257` | legacy 聊天工作台 | `body.chat-mode`（`ui2.css:931-932` 令 `#osShell{display:none}`） |

**硬切换根因**（ui2.css:930-936）：任意模式激活即 `visibility:hidden` / `display:none` 其余两树 → 三者**永不同屏**（审计根因 3、4）。

---

## 三、统一空间核心命题（Single Space Thesis）

> 小6 AI OS 不是「几个页面之间的切换器」，而是**一个始终存在的空间（Space）**，由若干**永远共存的图层（Layer）**叠加而成。导航 = 调整图层焦点（Focus），而非替换整页。

统一空间的三个图层（z 轴由低到高）：

1. **World Layer（世界层）** — 持久存在的 Galaxy 空间背景。
2. **Operation Layer（操作层）** — 浮于世界之上的功能性表面（HUD、Hero、侧栏、Timeline、Command Dock）。
3. **Overlay Layer（浮层）** — 瞬时、可解散的叠加（Command Palette、Settings、Context Drawer、Galaxy Focus 卡、Voice）。

这三层**永远同时存在于 DOM**，仅靠透明度/变焦/模糊区分焦点，永不 `display:none` 彼此。

---

## 四、World Layer 定义（Galaxy 不是页面）

- **事实锚点**：Galaxy 已是首页背景 —— `solarCanvas`（`index.html:73`）+ `galaxy-veil`（`index.html:75`）常驻于 `.os-shell`(z5) 之下。它**本来就是世界**，问题在于 `#universeView` 把它「重做成一页」（ui2.css:858 `background:var(--bg)`，z30 盖住一切）。
- **设计定义**：World Layer = 活的 Galaxy（太阳系演化、节点聚焦）。它**不拥有自己的页面**，只作为所有操作的「空间语境」。
- **去页化**：`#universeView` 从「不透明独立页」降级为「Galaxy Focus 浮层」（见 03 文档）——半透明、浮在活 Galaxy 之上、不隐藏 Operation Layer。

---

## 五、Operation Layer 定义（Workspace 不是首页）

- **事实锚点**：`#osShell`（index.html:78）当前被当作「首页」，但其内容实为**操作表面**：HUD(94)、Hero(119)、侧栏 Capability Matrix+Insight(136)、底部 Timeline(149)+Command Dock(153)。
- **设计定义**：Operation Layer = 用户与 AI 协作的功能表面，浮于 World Layer 之上。它**不是入口页**，而是「在空间里做事的地方」。
- **与 World 的关系**：Operation Layer 默认半透明/毛玻璃浮于 Galaxy 之上，使用户**始终看见世界**；进入 Galaxy Focus 时 Operation Layer 仅变暗（不消失），世界被推到前台。

---

## 六、Galaxy ↔ Panel 关系（唯一能力通道）

- **已有桥梁**：`galaxy-exam-experience.js:_enterCapability`（`galaxy-experience.js:50-61`）已正确实现「Galaxy Node → Operation Panel」：点击节点「进入」→ 移除 `universe-mode` + `uv.open` → `PanelManager.openCapability('capabilities')` 或 `ZZCapabilities.open()`。
- **只读渲染**：`galaxy-experience.js:_render`（:78-123）仅消费 `AppState.focus` + GalaxyState 只读投影，**绝不写状态**（符合红线）。
- **设计收口**：Galaxy Node → GEL 卡（`gx-card`）→ 「进入」→ Operation Layer 能力面板，成为**唯一**能力表达通道。融合只是把这条通道从「独立宇宙页内」搬到「活 Galaxy 之上」，通道逻辑（`_enterCapability`）**原样保留**。

---

## 七、三页面合并方案（方案 A 细化）

| # | 动作 | 现状锚点 | 目标态 | 改动性质 |
|---|---|---|---|---|
| 1 | `#universeView` 去页化 | ui2.css:857-861（不透明页） | 半透明 Galaxy Focus 浮层（复用 `galaxy-veil` 语义，z 高于 os-shell 但低于浮层） | CSS 显隐 |
| 2 | `galaxy` 导航不再换页 | index.html:1519-1520 `openUniverse()` | 改为「Galaxy Focus 开关」：os-shell **保持可见**，仅显隐 `gx-*` 层；用中性类 `zz-galaxy-focus` 替代会硬隐藏 Home 的 `universe-mode` | 导航 JS 路由 |
| 3 | 解除 ui2.css:933-934 硬隐藏 | ui2.css:933-934（universe-mode 隐藏 osShell/#app） | 改为叠加层透明度过渡，Operation Layer 不 `visibility:hidden` | CSS |
| 4 | 聊天去独立页 | index.html:1512-1516 `openChat()` 全页切换 | `workspace`/`assistant` 不再 `openChat()` 换页；统一路由到 **Command Dock**（Global AI Intent Entry）；`assistant` 仅派 `zz:voice-toggle` | 导航 JS 路由 |
| 5 | `#app` 重寄宿 | index.html:257 `.app`（chat-mode 全页） | 对话引擎保留，重寄宿为 Operation Layer 内的「Conversation Panel」（或按需抽屉），由 Command Dock 喂入；`chat-mode` 页切换**消除** | CSS/HTML 重壳（逻辑不动） |
| 6 | 清理死代码 | ui2.css:869-888 `.os-chat-drawer` | 与未接线「聊天抽屉」承诺一并收敛（实现阶段） | CSS 清理 |

> 注：`_enterCapability`（`galaxy-experience.js:50-61`）中 `document.body.classList.remove('universe-mode')` 需随第 2 条改为移除 `zz-galaxy-focus`，属同一处受控改动。

---

## 八、红线符合性

| 红线 | 满足 |
|---|---|
| 不修改 Backend / Agent Runtime / AppState / EventBus | ✅ 仅 CSS 显隐 + 导航路由 |
| 不修改 solar-system.js 核心逻辑 | ✅ 仅消费其已存在 focus 事件 |
| 不新增事件 | ✅ 复用 `zz:voice-toggle` / `AppState.focus` / `PanelManager` |
| 不新增第二套状态 | ✅ 沿用既有 `body` 类 + 面板 open 类单一推导（syncNav 纪律） |
| 保护 AI Presence 三唯一 | ✅ 纯表现层只消费 `body[data-presence]` |
| 第一屏 1/5/30s | ✅ Galaxy 恒为背景→1s 见世界；Hero 文案(UI-4D-1)→5s 理解；Command Dock 常驻→30s 首意 |

---

> ▣ **STOP — 本阶段为 Design Only，未修改任何代码。等待 Review 与 Implement 放行。**
