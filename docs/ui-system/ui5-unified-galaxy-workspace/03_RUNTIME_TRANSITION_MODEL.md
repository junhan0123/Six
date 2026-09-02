# UI-5 · Runtime Transition Model — Layered Visibility（03_RUNTIME_TRANSITION_MODEL.md）

> 阶段：UI-5 · Design（仅设计，零代码改动）
> 输入：00_AUDIT.md 四、Q4 根因 2/3/4（ui2.css:930-936 硬切换、#universeView 不透明页）
> 设计原则：① Galaxy=World Layer ② Workspace=Operation Layer ④ Navigation=Capability Focus

---

## 一、运行时现状（问题根因）

`body` 互斥模式类由 `syncNav()`（index.html:1495-1504）推导唯一激活态，再由 `ui2.css:930-936` 做硬显隐：

```
ui2.css:930  .os-shell { z-index: 5; }
ui2.css:931  body:not(.chat-mode) #app { visibility: hidden; }
ui2.css:932  body.chat-mode #osShell { display: none; }          ← Home 整页消失
ui2.css:933  body.universe-mode #osShell,
ui2.css:934  body.universe-mode #app { visibility: hidden; }     ← Home+Chat 整页消失
ui2.css:935  body.universe-mode #solarCanvas { z-index: 29; }
ui2.css:936  #universeView { z-index: 30; }
```

**后果**：任何模式激活即 `display:none`/`visibility:hidden` 其余层 → 三层**永不同屏**，这就是「像多个产品」的运行时真相。

---

## 二、chat-mode 处理（消除页切换）

- **现状**：`openChat()`（index.html:1465）加 `chat-mode` 并移除 `universe-mode`；ui2.css:931-932 令 `#osShell{display:none}`、非 chat 时 `#app{visibility:hidden}`。即「Home 整页消失、legacy .app 整页出现」。
- **目标态**：**废止 `chat-mode` 页切换**。对话不再是独立页面：
  - 对话引擎 `#app`（index.html:257，app.js 逻辑**不动**）重寄宿为 Operation Layer 内的 **Conversation Panel**（或按需抽屉），由 Command Dock 喂入意图。
  - 重寄宿仅改 CSS/HTML 外壳（使 `#app` 以面板/抽屉形态浮于 Operation Layer），**不重写 app.js**。
  - 移除 ui2.css:931-932 的硬显隐；`#app` 与 `#osShell` 自此共存在于 Operation Layer（或 Conversation Panel 与 Operation 主表面共存）。

---

## 三、universe-mode 处理（替换为 Galaxy Focus 浮层）

- **现状**：`openUniverse()`（index.html:1472）→ `universe-mode` + `#universeView.open`；ui2.css:857-861 使 `#universeView` 为 `position:fixed;inset:0;z-index:30;background:var(--bg)` 不透明页，盖住一切。
- **目标态**：
  - `#universeView` 去页化：`background:var(--bg)` 改为半透明空间纱（复用 `galaxy-veil` 语义），`z-index` 高于 `.os-shell`(z5) 但低于浮层（建议 z≈20），`gx-*` 浮在**活 Galaxy**（`solarCanvas`/`.galaxy-veil`）之上。
  - 激活类由 `universe-mode` 改为中性 `zz-galaxy-focus`（**不**触发 ui2.css:933-934 的硬隐藏）。
  - `galaxy-experience.js:_enterCapability`（:50-61）中 `classList.remove('universe-mode')` 同步改为 `remove('zz-galaxy-focus')`（同一处受控改动）。
  - ui2.css:935 的 `body.universe-mode #solarCanvas{z-index:29}` 不再需要（Galaxy 恒为 World Layer，本就 z0 活背景）。

---

## 四、cp-mode 处理（保持浮层，不动）

`cp-mode` + Command Palette 浮层（`ZZCommandPalette.open()`）已是正确「不切页」范式，融合后保持不变，作为 Overlay Layer 成员。

---

## 五、Visibility 模型（三层永远共存）

统一后，`body` 默认态即**三层同屏**：

| 图层 | 元素 | z 轴 | 默认可见性 | Galaxy Focus 时 |
|---|---|---|---|---|
| World Layer | `#solarCanvas`(73) + `.galaxy-veil`(75) | 0 / 1 | 恒可见（opacity 1） | 推前（变焦/提亮） |
| Operation Layer | `#osShell`(78) | 5 | 恒可见（半透毛玻璃） | 推后（dim/blur，不隐藏） |
| Overlay Layer | Palette/Settings/Context/`gx-*` | 20+ | 默认收起 | Galaxy Focus 时 `gx-*` 显 |

**核心规则**：任何焦点态都**不**对 World/Operation 任一层做 `display:none` 或 `visibility:hidden`。仅 Overlay 成员按自身 open 类显隐。

---

## 六、Transition 模型（连续过渡，禁用硬切）

- 沿用既有连续过渡思路（参考 `ui4b-explore-transition.css` 的 opacity/transform 过渡纪律）。
- Galaxy Focus 进入/退出：World Layer 提亮 + Operation Layer `opacity`/`backdrop-filter` 过渡（~200–300ms），`gx-*` 卡 fade/slide。
- 废除所有 `display`/`visibility` 跳变（原 ui2.css:931-936），统一改为 `opacity` + `transform` + `pointer-events` 过渡。
- `prefers-reduced-motion` 已存在（ui2.css:922-925），过渡自动降级。

---

## 七、实现边界与未决项（留待 Implement）

1. `#app` 重寄宿为 Conversation Panel 的**具体容器形态**（右侧常驻面板 vs 底部抽屉）需在 Implement 结合 `app.js` 实测确定；逻辑零改动。
2. Command Dock（`#osDock`，index.html:155）作为 Global AI Intent Entry，其与对话引擎的事件接线（是否经现有 `zz:*` 事件或既有通道）需在 Implement 核对 `zz-command-dock` 实现，本设计仅定架构。
3. `zz-galaxy-focus` / `zz-voice` 为新增 body 类（状态类，非事件），需同步 `syncNav()` 推导与 ui2.css 选择器；属同一处受控改动。

---

## 八、红线符合性

| 红线 | 满足 |
|---|---|
| 不修改 Backend / Agent / AppState / EventBus | ✅ 仅 CSS 显隐 + 导航路由 |
| 不修改 solar-system.js | ✅ 仅消费其 focus 事件 |
| 不新增事件 | ✅ 复用既有通道；新 body 类非事件 |
| 不新增第二套状态 | ✅ body 类 + syncNav 单一推导 |
| 保护 AI Presence 三唯一 | ✅ 只消费 `body[data-presence]` |
| 第一屏 1/5/30s | ✅ 三层恒同屏，Galaxy 恒为背景 |

---

> ▣ **STOP — 本阶段为 Design Only，未修改任何代码。等待 Review 与 Implement 放行。**
