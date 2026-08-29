# UI-5 · Unified Galaxy Workspace Reconstruction — Audit（00_AUDIT.md）

> **阶段**：UI-5 · Audit（仅审查，零代码改动）
> **身份**：Senior Product Designer + Frontend Architect
> **目标**：将「新 Home Workspace」与「旧 Galaxy/Solar System Workspace」融合为**一个统一 AI OS 空间**
> **纪律红线**：不修改 Backend / Agent Runtime / AppState / EventBus / solar-system.js 核心逻辑 / 不新增事件 / 不新增第二套状态
> **本文件结论**：回答审计 Q1–Q5，全部基于 `index.html` / `ui2.css` / `galaxy-experience.js` 真实行号证据，**未改动任何代码**。

---

## 〇、审计方法（Method）

| 项 | 说明 |
|---|---|
| 范围 | `G:/xiao6/xiao6-ui/`：`index.html`、`ui2.css`、`ui4b-*` / `ui4c-*` / `ui4d-*` CSS、`galaxy-experience.js`；`solar-system.js` 仅引用不读核心逻辑 |
| 方式 | 全仓 Grep + 定点 Read，逐条带 `文件:行号` 锚点 |
| 约束 | 纯静态分析；模型不可读截图，故结论**全部来自 DOM/CSS/JS 文本证据**，无 GUI 推断 |
| 未做 | 未运行服务、未截图、未改任何文件（符合 brief「只输出 Audit 文档」） |

**核心结构事实（全仓唯一真相）**：

- `index.html:78` `<section class="os-shell" id="osShell">` —— 新 Home Workspace（AI OS 首页操作层）
- `index.html:161` `<div id="universeView" data-view="developer">` —— 旧 Galaxy/Universe 独占视图
- `index.html:257` `<div class="app" id="app">` —— 更旧的 legacy 聊天工作台
- 三者由 `body` 的互斥类 `chat-mode` / `universe-mode` / `cp-mode` / `os-context-open` 切换显隐（`index.html:1495-1504` `syncNav()`）

**关键发现（先于 Q1–Q5）**：系统实际存在 **三个** 独立「页面」概念，而非 brief 所述的「两个」——多出的第三者是 legacy `.app` 聊天工作台。这解释了用户「像两个产品」的体感来源。

---

## 一、Q1：当前所有进入 Galaxy（Universe 视图）的入口

Galaxy/Universe 视图由 `body.universe-mode` + `#universeView.open` 共同激活（`index.html:1472` `openUniverse()`）。全部入口如下：

| # | 入口 | 位置（文件:行） | 触发机制 | 目标 |
|---|---|---|---|---|
| 1 | **左导航「星图」按钮** | `index.html:88` `data-nav="galaxy"` → `index.html:1519-1520` | 点击 → `closeChat(); openUniverse()` | 进入 universe-mode |
| 2 | **首屏 Hero「星图」芯片** | `index.html:130` `os-hero-chip[data-nav="galaxy"]` → `index.html:1520` | 点击 → 同上 `openUniverse()` | 进入 universe-mode |
| 3 | **键盘 Ctrl/Cmd+U** | `index.html:1475-1479` | 快捷键 toggle：`universe-mode ? closeUniverse() : openUniverse()` | 进入/退出 universe-mode |
| 4 | **Universe 内「关闭」按钮** | `index.html:162` `#uvClose` → `index.html:1474` `closeUniverse()` | 点击 → 移除 `universe-mode` + `#universeView.open` | 退出 |
| 5 | **Esc 键** | `index.html:1480-1483` | `universe-mode` 下 Esc（且浮层栈空）→ `closeUniverse()` | 退出 |

**Galaxy 节点交互（进入 Universe 后）**：`solar-system.js` 点击星球 → 写 `AppState.focus` → `galaxy-experience.js:_render()`（`galaxy-experience.js:78-123`）更新 `gx-card`。「进入」按钮（`galaxy-experience.js:50-61` `_enterCapability`）会**移除 `universe-mode`** 并调用 `PanelManager.openCapability()` / `ZZCapabilities.open()` —— 即「Galaxy Node → Operation Panel」模式**已在设计中**，只是当前被锁在独立 Universe 页内。

---

## 二、Q2：旧聊天页面入口

聊天页 = legacy `.app`（`index.html:257`），由 `body.chat-mode` 激活（`index.html:1465` `openChat()` → 加 `chat-mode` 并**移除 `universe-mode`**）。全部入口：

| # | 入口 | 位置（文件:行） | 触发机制 | 行为 |
|---|---|---|---|---|
| 1 | **右下浮动「聊天」FAB** | `index.html:184` `#osChatFab` → `index.html:1467` | 点击 → `openChat()` | 首页常驻聊天按钮（z-index:24，`ui2.css:881`） |
| 2 | **左导航「工作台」按钮** | `index.html:86` `data-nav="workspace"` → `index.html:1512-1513` | 点击 → `closeUniverse(); openChat(); navVoice=false` | 进入 chat-mode |
| 3 | **左导航「语音助理」按钮** | `index.html:89` `data-nav="assistant"` → `index.html:1514-1516` | 点击 → `closeUniverse(); openChat(); navVoice=true` + 派发 `zz:voice-toggle` | 进入 chat-mode（语音态） |
| 4 | **首屏 Hero「对话」芯片** | `index.html:128` `os-hero-chip[data-nav="workspace"]` → `index.html:1513` | 点击 → 同上 `openChat()` | 进入 chat-mode |

**重要**：`ui2.css:869-888` 定义的 `.os-chat-drawer`（聊天抽屉）**是死代码**——全仓 HTML/JS 无任何引用（仅 `index.html:184` 的 FAB 与 `ui2.css:881` 的 `.os-chat-fab` 是活的）。也就是说「聊天降级为抽屉」是**未接线的计划**，用户实际得到的是 **`chat-mode` 全页硬切换**（`ui2.css:931-932`：`body:not(.chat-mode) #app{visibility:hidden}` + `body.chat-mode #osShell{display:none}`），即 Home 整页消失、legacy `.app` 整页出现。

---

## 三、Q3：左侧导航每个按钮实际行为

导航脊柱 = `index.html:81-92`（brand `home` + 5 个 `os-nav-btn`）。处理器见 `index.html:1505-1526`，高亮推导见 `index.html:1495-1504` `syncNav()`。

| 按钮 | data-nav | 实际行为（文件:行） | 是否打开旧页面 |
|---|---|---|---|
| 小6徽标（brand） | `home` | `closeChat(); closeUniverse(); navVoice=false` + 关 Settings/CommandPalette（`1508-1511`） | 否（回首页） |
| 工作台 | `workspace` | `closeUniverse(); openChat()`（`1512-1513`） | **是 → 打开 legacy `.app` 聊天页（chat-mode 全页切换）** |
| 指令中心 | `command` | `ZZCommandPalette.open()`（`1517-1518`） | 否（浮层，不切页） |
| 星图 | `galaxy` | `closeChat(); openUniverse()`（`1519-1520`） | **是 → 打开 Universe 独占页（universe-mode）** |
| 语音助理 | `assistant` | `closeUniverse(); openChat(); navVoice=true` + `zz:voice-toggle`（`1514-1516`） | **是 → 打开 legacy `.app` 聊天页（语音态）** |
| 设置 | `settings` | `ZZSettings.open()`（`1521-1522`） | 否（浮层） |

**首屏 Hero 3 芯片**（`index.html:128-130`）：`对话`(workspace→chat) / `指令`(command→palette) / `星图`(galaxy→universe) —— 与左导航同源，进一步强化了「对话=聊天页」「星图=宇宙页」的双页心智。

**结论**：左导航中有 **3/6** 按钮（`workspace`/`assistant`/`galaxy`）会触发**整页切换式旧页面**，这正是「两个/三个产品」体感的直接操作来源。仅 `home`/`command`/`settings` 维持单页操作层。

---

## 四、Q4：哪些代码导致两个（实为三个）UI 分裂

### 根因 1 — 三棵互相排斥的 DOM 树
`os-shell#osShell`(`index.html:78`) / `#universeView`(`index.html:161`) / `.app#app`(`index.html:257`) 三者在 HTML 中是**平级兄弟节点**，各自独立渲染、各自持有一套布局与交互，从未共享一个「世界」。

### 根因 2 — `body` 互斥模式类做硬页切换（`index.html:1495-1504`）
`syncNav()` 用 `universe-mode`/`cp-mode`/`chat-mode`/`settingsOpen()` 把界面切成**唯一激活态**。任一模式激活即意味着其余模式被隐藏——这是「换页」而非「分层」。

### 根因 3 — `ui2.css` 的可见性硬切换（真正「两个产品」的代码点）
```
ui2.css:930  .os-shell { z-index: 5; }
ui2.css:931  body:not(.chat-mode) #app { visibility: hidden; pointer-events: none; }
ui2.css:932  body.chat-mode #osShell { display: none; }          ← Home 整页消失
ui2.css:933  body.universe-mode #osShell,
ui2.css:934  body.universe-mode #app { visibility: hidden; pointer-events: none; }
ui2.css:935  body.universe-mode #solarCanvas { z-index: 29; opacity: 1; }
ui2.css:936  #universeView { z-index: 30; }
```
- `chat-mode` 下 `#osShell{display:none}`（**整页删除 Home**）。
- `universe-mode` 下 `#osShell` 与 `#app` 同时 `visibility:hidden`（**整页删除 Home 与 Chat**）。
- 三者**永远不可能同屏**——这是「像两个产品」的 CSS 级根因。

### 根因 4 — `#universeView` 是不透明独立页面（而非叠加层）
```
ui2.css:857  #universeView {
ui2.css:858    position: fixed; inset: 0; z-index: 30; background: var(--bg);   ← 不透明实底
ui2.css:859    display: none;
ui2.css:861  #universeView.open { display: block; }
```
`background: var(--bg)` 使其成为**盖住一切的不透明页**（z30 高于 promoted 的 `solarCanvas` z29）。Galaxy（太阳系画布）本已是首页背景，但宇宙视图却把它「重做成一页」而非「浮在其上」，造成上下文断裂。

### 根因 5 — Galaxy 已是持久背景，却被重复「实例化」
- 首页：`solarCanvas`（z0）+ `galaxy-veil`（`index.html:75`，`z = --z-ground+1`）始终在 `.os-shell`(z5) **之下**作为世界背景。
- 宇宙模式：`ui2.css:935` 又把同一 `solarCanvas` 提到 z29——即**同一个 Galaxy 被两套定位逻辑重复表达**，加剧了「这是另一个地方」的认知。

### 根因 6 — 死代码制造未兑现的承诺
`.os-chat-drawer`（`ui2.css:869-888`）标注「聊天降级为抽屉」却从未接线，与活的 `openChat()` 全页切换矛盾，说明融合意图**早有萌芽但未落地**。

---

## 五、Q5：最小融合方案（设计级提案，待 Design 阶段细化）

> 以下为 Audit 阶段的**最小融合方向建议**，非实现方案。须待 Design Review 通过后按红线推进。

### 核心洞察（决定方案走向）
**Galaxy 已经是统一 AI OS 空间的「世界背景」**（`solarCanvas` + `galaxy-veil` 常驻于 `.os-shell` 之下）。问题**不是** Galaxy 不存在，而是：
1. 它的「节点信息/操作」被锁在不透明独立页 `#universeView` 里；
2. 用户被 `workspace`/`assistant`/`galaxy` 三个按钮反复「换页」赶进旧页面。

因此最小融合 = **不重建 Galaxy，而是把它的交互层从「独立页」降为「叠加在持久 Galaxy 上的操作层」**，并堵住左导航的换页出口。

### 方案 A（推荐 · 纯表现层最小改动）
1. **`#universeView` 去独立页化**：`ui2.css:858` 去掉 `background: var(--bg)`，改为半透明空间纱（复用 `galaxy-veil` 语义）；`gx-card`/`gx-status`/`gx-hint` 改为浮在**活的 Galaxy** 之上（`z-index` 高于 `.os-shell` 但低于必要浮层）。
2. **`galaxy` 导航不再换页**：`index.html:1519-1520` 的 `openUniverse()` 改为「Galaxy 聚焦叠加层开关」——`os-shell` **保持可见**，仅显隐 `gx-*` 交互层，`body` 不再加 `universe-mode`（或新增中性 `zz-galaxy-focus` 类，不复用会硬隐藏 Home 的 `universe-mode`）。
3. **`ui2.css:933-934` 硬隐藏解除**：移除 `universe-mode` 对 `#osShell`/`#app` 的 `visibility:hidden`，改由叠加层透明度过渡（参考已存在的 `ui4b-explore-transition.css` 连续过渡思路）。
4. **左导航去「聊天页」心智**：`workspace`/`assistant`（`index.html:1512-1516`）不再 `openChat()` 全页切换；改路由到 **Command Dock（Global AI Intent Entry）** 聚焦输入（UI-4D-1 已将其语义化为「意图控制台」），语音按钮改派 `zz:voice-toggle` 而不切页。
5. **能力唯一表达通道落地**：Galaxy Node 点击 → `galaxy-experience.js:_enterCapability`（`galaxy-experience.js:50-61`）已正确导向 `PanelManager.openCapability` —— 保留并强化此路径，使「Galaxy Node + Operation Panel」成为**唯一**能力表达通道。

### 方案 B（更激进 · 暂不在审计范围）
彻底拆除 `#universeView` 独立节点，把 `gx-*` 交互直接挂到首页 Galaxy 叠加层。代价更大、回归面更广，**不建议**作为最小融合首选。

### 红线符合性预检（方案 A）
| 红线 | 是否满足 |
|---|---|
| 不修改 Backend / Agent Runtime / AppState / EventBus | ✅ 仅改 CSS 显隐 + 导航 JS 路由，不动数据层 |
| 不修改 `solar-system.js` 核心逻辑 | ✅ 仅消费其已存在的 focus 事件，不改渲染 |
| 不新增事件 | ✅ 复用既有 `zz:voice-toggle` / `AppState.focus` / `PanelManager` API |
| 不新增第二套状态 | ✅ 用既有 `body` 类 + 面板 open 类单一推导（与 `syncNav` 现有纪律一致） |
| 保护 AI Presence 三唯一 | ✅ 纯表现层只消费 `body[data-presence]`，不重定义 |
| 第一屏 1/5/30 秒目标 | ✅ Galaxy 恒为背景 → 1 秒见世界；Hero 文案（UI-4D-1）保留 → 5 秒理解；Command Dock 常驻 → 30 秒首意 |

---

## 六、审计结论（Verdict）

1. **分裂根因明确且可定位**：`ui2.css:931-936` 的互斥可见性硬切换 + `#universeView` 不透明独立页（`ui2.css:858`）+ 三棵平级 DOM 树，是「像多个产品」的代码级真相。
2. **Galaxy 已是世界背景**，融合的工程量比「重建」小得多——核心是**把 Universe 从独立页降为叠加层** + **堵住左导航的换页出口**。
3. **最小融合方案可行且符合全部红线**（方案 A），关键改动落在 CSS 显隐与导航路由两处，数据层零触碰。
4. **附带清理项**：`.os-chat-drawer` 死代码（`ui2.css:869-888`）与未接线的「聊天抽屉」承诺，可在融合时一并收敛。

**下一步**：进入 **Design** 阶段，将方案 A 细化为带具体行号/选择器的最终设计，再经 Implement → Verify → Document → STOP。

---

> ▣ **STOP — 本阶段为 Audit Only，未修改任何代码。等待 Review 与 Design 放行。**
