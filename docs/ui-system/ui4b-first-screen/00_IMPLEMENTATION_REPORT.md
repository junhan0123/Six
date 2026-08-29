# UI-4B-1 · First Screen Fusion — Implementation Report v1.0

> **身份**：Senior Frontend Engineer / AI OS Experience Engineer
> **阶段**：Implement → Verify → Document（Audit #823 / Design #824 已完成，本文件为 Implement 收口）
> **状态**：✅ 实施完成 · 真实渲染验证全绿 · **STOP（等 Review，不进 UI-4B-2，不 git commit）**
> **验证方法**：Chrome headless（`--headless=new --remote-debugging-port=9222`）+ CDP `Runtime.evaluate`(getComputedStyle) + `Page.captureScreenshot`；像素度量用自写最小 PNG 解码器（`_png.mjs`）。一切判定以结构事实与像素事实为准，不以「读源码推断」。

---

## 1 · Before / After

### 1.1 问题根因（Audit 结论，非推测）
首屏「两个页面」感的真实根因**不是布局**，而是**操作层卡片平铺**：

- `.os-nav` / `.os-hud` / `.os-core` / `.os-panel(timeline,dock)` / `.os-side` 五类容器，各自持有
  `border:1px solid var(--border)` + `backdrop-filter: blur(26px) saturate(180%)`（`--glass-3`）。
- 五层毛玻璃合起来把整个视口铺满一层「帘子」，把位于正中央的 Galaxy **用 26px 模糊糊掉**。
- 结果：首屏读作「一个深色 Web Dashboard」，而不是「一个连续的 AI OS 空间」。

World Layer（Galaxy）本身已由 `spatial-runtime.css` 暗化常驻（`--world-brightness:0.72`），但被中央的模糊卡片遮蔽，存在感归零。

### 1.2 After（本阶段交付）
把中央舞台由「矩形卡片」拆为 **World Window**（无边框 / 无填充模糊 / 无投影 / 背景径向场在触边前归零），并把唯一最强玻璃留给 Command Dock 输入条、其辉光绑定 AI Presence。首屏变为：

- **中央**：Galaxy 清晰透出（World Window），意识核心以「光晕」而非「卡片」承载可读性。
- **四周**：导航脊柱 / HUD 退为半透明浮空 HUD（Peripheral Presence），Galaxy 经间隙连续贯通。
- **底部**：Command Dock 输入条成为屏幕上唯一的「强玻璃对象」，随 AI 状态呼吸 —— 读作「AI 的意图入口」，而非聊天框。

| 维度 | Before | After（UI-4B-1） |
|---|---|---|
| 中央舞台 | `.os-core` 卡片（border+blur26） | World Window（border 透明 / blur none / 径向场） |
| 玻璃强度阶梯 | 5 容器皆 glass-3（无主次） | **唯一 glass-3 = Dock 输入条**；其余 glass-2 |
| Galaxy 中央存在感 | 被 26px 模糊糊掉 | 透出（像素 stdDev 升 35.19→37.10） |
| 矩形硬边 | `.os-core` 1px 边框连续硬边 | 顶边硬边台阶 21.53→**0.32**（67× 坍缩） |
| Dock 语义 | 卡中卡 + 静态 `--accent` 辉光 | 去卡壳 + `--presence-color` 绑定呼吸 |
| Attention Budget | 未强制执行 | Primary=1 / Secondary≤2 / Peripheral 无限（玻璃+presence 两级强表达） |

---

## 2 · Layout Changes

**零布局改动**：所有四模式网格（ui2 既有）原样保留，本阶段**不改任何 HTML、不重写 Workspace 结构、不新增容器**。
变化仅发生在既有容器的「视觉待遇」上：

- **B1 布局融合**：`.os-core` 不再是矩形面板，而是承载 Galaxy 的「窗口」——其背景改为两层 `radial-gradient` 且**均在触及元素边缘前归零**，视觉上不存在任何矩形边界。
- **B2 周边退场**：`.os-nav` / `.os-hud` 由实心卡片降为浮空 HUD（半透明 + 弱玻璃），让 Galaxy 经 `.os-shell` 的 gap 与中央连续贯通。
- **B3 预算强制**：用「玻璃强度（glass-2 / glass-3）+ presence 绑定」两级阶梯硬性表达 Attention Budget，不靠新增 DOM。
- **B4 入口强化**：`.os-dock` 外壳透明化（去「卡中卡」），输入条本身成为屏幕对象；标题降级为轻量说明。

---

## 3 · CSS Changes

### 3.1 新增文件 `xiao6-ui/ui4b-first-screen.css`（287 行，纯 ADDITIVE 表现层）
加载顺序末位（权威覆盖，但权威范围仅限本文件显式声明的选择器）：
`styles.css → premium.css → runtime-viz.css → execution-channel.css → ui2.css → spatial-runtime.css → ui4b-first-screen.css`

全部规则限定 `body:not(.chat-mode):not(.universe-mode)`（仅首屏操作态；chat/universe 模式自动回退 ui2 原值，见 §5 作用域护栏）。

### 3.2 关键规则
| 范围 | 选择器 | 核心声明 |
|---|---|---|
| **B1** | `.os-core` | `border-color:transparent; backdrop-filter:none; box-shadow:none; isolation:isolate;` + 双 `radial-gradient`（presence 场 + 阅读遮罩，均触边归零） |
| **B1** | `.os-hero-eyebrow/.os-hero-sub` | `text-shadow`（`color-mix` 自 `--bg` 派生，保 WCAG 对比度） |
| **B1** | `.os-hero-title` | `filter:drop-shadow(...)` —— 因 ui2:675-679 是**渐变裁切文字**（`color:transparent`），`text-shadow` 会脏字，必须用 `drop-shadow`（见 3.4） |
| **B2** | `.os-nav/.os-hud` | `background:color-mix(--surface 55%)`；`border-color:color-mix(--border 55%)`；`backdrop-filter:var(--glass-2)`；`:hover/:focus-within` 恢复满强度 |
| **B3** | `.os-side .os-panel` / `.os-panel.os-timeline` | 中性玻璃 `glass-2`；`background:color-mix(--surface 72%)`；`box-shadow:none`；**不含 `.os-dock`**（B4 在后胜出） |
| **B3** | `body.os-context-open .os-side .os-panel` | 恢复 ui2 抬升投影（Secondary 与背景分离，仍非 Primary） |
| **B4** | `.os-dock`（外壳） | `background:transparent; border-color:transparent; backdrop-filter:none; padding:0`（去卡壳） |
| **B4** | `.os-dock > h3` | `font-size:var(--fs-11); opacity:.72`（轻量说明，presence 点保留） |
| **B4** | `.os-dock .os-dock-bar` | 全首屏**唯一 glass-3**；`border-color:color-mix(--presence-color 42%,--border)`；`background:color-mix(--surface-2 88%,--presence-color)`；双层 `box-shadow`（含 presence 辉光）；`:focus-within` 加强 |
| 响应式 | `@media(max-width:1199px)` / `(max-width:980px)` | 仅微调径向场几何（窄屏 chrome 恢复 78% 强度，避免糊成一片） |

### 3.3 纪律红线（已静态校验，见 §5）
- **零裸色值**：全部颜色经 `color-mix(in srgb, var(--x) …)` 从 ui2 既有令牌派生。静态扫描：**裸 hex/rgb = 0**。
- **零令牌重定义**：本文件不定义任何 `--token`。静态扫描：`--x:` 定义 = **0**。
- **不触碰 presence 色权威**（P8 三唯一）：本文件**只消费** `body[data-presence] → --presence-color`，不写入、不派生新状态机。静态扫描：`--presence-color` 重定义 = **false**。
- 括号平衡：16/16 起止、min=0 —— **OK**。
- 不接线探索态：`.zz-explore` 钩子保持未接线（留待 UI-4B-2，见 §6）。

### 3.4 已修复的自审/探针缺陷（本会话）
1. **B3 注释内部矛盾**：重写注释为「Primary 唯一 glass-3 + 唯一 presence 绑定；Secondary/Peripheral 共用 glass-2（刻意），靠背景不透明度 72% vs 55% 区分」，并显式注释「本规则不含 `.os-dock`，B4 在后胜出」。
2. **`.os-core-label` 孤儿选择器污染**：初始 B1 文字光晕规则含该选择器，grep 确认 DOM/JS 均无此元素（ui2 既有孤儿）→ 移除，避免新增死代码。
3. **`.os-hero-title` 渐变裁切文字 + `text-shadow` 脏字**（9 主题探针触发）：computed `color:rgba(0,0,0,0)`；对其用 `text-shadow` 会把阴影画在渐变字面之上 → 改为 `filter:drop-shadow()`（作用于渲染结果，阴影落于字形之后）。

---

## 4 · Files Changed

| 文件 | 变更 | 说明 |
|---|---|---|
| `xiao6-ui/ui4b-first-screen.css` | **新增**（287 行） | 本阶段唯一核心交付物（纯表现层） |
| `xiao6-ui/index.html` | **编辑**（+1 link） | 在 `spatial-runtime.css?v=20260809a1` 之后新增 `ui4b-first-screen.css?v=20260809b1` |
| `docs/ui-system/ui4b-first-screen/_probe_4b1.mjs` / `.json` | 新增 | 三视口 + 作用域护栏 + Context + Presence 结构探针 |
| `docs/ui-system/ui4b-first-screen/_probe_theme.mjs` / `.json` | 新增 | 9 主题兼容抽查 |
| `docs/ui-system/ui4b-first-screen/_png.mjs` | 新增 | 最小 PNG 解码器（decodePNG/lum/regionStats/hProfile/maxStep） |
| `docs/ui-system/ui4b-first-screen/_probe_fusion.mjs` / `.json` | 新增（本会话） | 启用/禁用本层两态像素融合度量 |
| `docs/ui-system/ui4b-first-screen/shots/*.png` | 新增 | 人眼复核归档（含 `fusion_on/off.png`） |

**明确零改动（已验证，红线保护）**：
`solar-system.js` · Three.js renderer · Galaxy 数据 · `AppState` · `EventBus` · Backend · Agent ·
`ui2.css`（只读复核）· `spatial-runtime.css`（只读复核）· `command-dock.js`（node --check OK，行为零改动）·
`panel-manager.js`（node --check OK，零改动）· `avatar-state.js`（P8 测试 20/0，零改动）·
`DESIGN.md`（未触碰）。**Event Contract 未扩张（DOMAIN=71 / SYSTEM=8 不变）。**

---

## 5 · Regression Test

### 5.1 三视口结构验证（1920×1080 / 1440×900 / 720×1280）
全部 **PASS**（数据来自 `_probe_4b1.json`）：

| 检查项 | 1920×1080 | 1440×900 | 720×1280 |
|---|---|---|---|
| **B1** `.os-core` backdrop-filter | `none` | `none` | `none` |
| **B1** `.os-core` border-top | `rgba(0,0,0,0)` | 同 | 同 |
| **B1** `.os-core` box-shadow | `none` | `none` | `none` |
| **B1** `.os-core` isolation | `isolate` | `isolate` | `isolate` |
| **B2** `#solarCanvas` filter / display | `brightness(0.72)` / `block` | 同 | 同 |
| **B2** `.os-nav` / `.os-hud` backdrop | `blur(14px) saturate(1.6)` (glass-2) | 同 | 同（窄屏 78%） |
| **B3** glass-3 唯一对象数 | **1** → `.os-dock .os-dock-bar` | **1** | **1** |
| **B3** timeline backdrop | `blur(14px) saturate(1.6)` (glass-2) | 同 | 同 |
| **B4** dock-bar backdrop | `blur(26px) saturate(1.8)` (glass-3) | 同 | 同 |
| **B4** dock 输入条 width | 774px | 774px | 434px（未禁用） |
| **B4** dock 模态按钮数 / hint | 5 / 正常 | 5 / 正常 | 5 / 正常 |
| 回归 `canScrollX`（F-01 保持） | **0** | **0** | **0** |
| 回归 `#osShell` display | `grid` / visible | 同 | 同 |
| 回归 JS 运行时错误 | **0** | **0** | **0** |

### 5.2 作用域护栏（chat / universe 模式必须完全让位）
`_probe_4b1.json · scopeGuard` 证实：
- `chat-mode`：`.os-core` 回退 ui2 原值（`blur(26px) saturate(1.8)` + 原 `background-image` + 原 `box-shadow`），`#osShell` `display:none`。
- `universe-mode`：`.os-core` 同样回退，`#osShell` `visibility:hidden`。
- 本层在两种模式下**零视觉影响**，已正确让位。

### 5.3 Context 抽屉展开（Secondary #2）
`contextOpen`：`sidePanelShadow` 恢复抬升投影、`sideTransform:none`、`sideOpacity:1`、`canScrollX=0` —— Secondary 展开正确，不抢占预算、不溢出。

### 5.4 AI Presence 联动（B4 关键主张：入口随 AI 状态呼吸）
`presenceBinding` 四态实测，dock-bar 边框色随 `--presence-color` 实时变化：
`IDLE #5fb3c8` → `THINKING #8b9bff` → `EXECUTING #56d364` → `ERROR #ff6b6b`。**证实「Global AI Intent Entry 随 AI 状态呼吸」，且未新增状态机/事件。**

### 5.5 P8 AI Presence 回归
`tests/phase8-ai-presence.frontend.test.js` 运行结果：**PASS（passed=20, failed=0）**。
色权威（[B]）、单一写入点（[C]）、表面接线（[D]）、Anti-Noise（[E]）、跨窗口同源（[F]）全绿 —— **本文件未破坏 P8 三唯一**。

### 5.6 9 主题兼容（`_probe_theme.json`）
dark / quantum / midnight / dark-cyan / dark-green / dark-purple / dark-amber / dark-rose / light **全绿**：
每主题 `.os-core` `backdrop-filter:none` + 含 `radial-gradient` + `border` 透明；`.os-dock-bar` glass-3；Galaxy `brightness(0.72)`；`canScrollX=0`。

### 5.7 像素级融合度量（本会话新增，`_probe_fusion.json`）
同一首屏、1920×1080，对比「启用 / 禁用 ui4b-first-screen.css」两态：

| 指标 | 启用(ON) | 禁用(OFF) | 结论 |
|---|---|---|---|
| **A · World Window**（中央区亮度 stdDev，越高=Galaxy 越清晰透出） | **37.10** | 35.19 | ✅ PASS · Galaxy 透出更清晰（ON > OFF） |
| **B · 无矩形硬边**（`.os-core` 顶边 60 列垂直穿越均值台阶） | **0.322** | 21.527 | ✅ PASS · 顶边无连续硬矩形边（ON 67× 坍缩） |

- Metric A 证明 World Window 让 Galaxy 在首屏中央真正透出（不再是糊成一片的玻璃面）。
- Metric B 用「沿顶边 60 列均值」隔离了连续边框（被保留）与稀疏星点（被稀释），干净证明矩形卡片硬边已消失 —— 把「融合」从主观描述转为可测像素事实。

### 5.8 静态纪律与语法
- 括号平衡 OK；裸色值 0；令牌定义 0；`--presence-color` 重定义 false。
- 消费 13 个令牌全部已在 ui2 / spatial-runtime / premium / styles 定义。
- `command-dock.js` / `panel-manager.js` / `avatar-state.js` `node --check` 语法 OK。

---

## 6 · UI-4B-2 Preparation

### 6.1 本阶段刻意「不做」的事（明确留待 UI-4B-2）
以下在 `ui4b-first-screen.css` 文件尾注释已登记，本阶段**不触碰**，避免半接线态：
1. **不接线 `body.zz-explore` 触发控件** —— Progressive Discoverability 的实际触发源未接。
2. **不给 `#osShell` 加 `.zz-operation-surface` 类** —— 探索态退后动画因此仍无目标（既定状态，非缺陷；触发与类挂载须同批进行）。
3. **不处置 `#universeView`(z30, `background:var(--bg)`) 的硬切残留（S2）**。
4. **不迁移 Panel 三态到 `.panel-lifecycle-*`**（PanelManager 打标属 UI-4B-2）。

### 6.2 UI-4B-2 建议承接顺序
- 先定 Explore Mode 触发源（复用既有状态，禁新增 Event Contract），再**同批**完成 `body.zz-explore` 钩子接线 + `#osShell.zz-operation-surface` 类挂载，避免半接线。
- 随后处置 `#universeView` 硬切（S2）与 Panel 三态迁移，使 World/Operation 双层在「聚焦 / 探索 / 独占」三态间平滑过渡。

### 6.3 发布闸口（本阶段 STOP）
- ✅ 代码实施完成；✅ 三视口 + 9 主题 + 作用域护栏 + Presence 联动真实渲染验证全绿；✅ P8 20/0；✅ 像素融合度量 PASS。
- 🛑 **STOP**：等待 Review，**不进入 UI-4B-2**，**不进行 git commit**。
- 待 Review 通过后，再决定是否进 UI-4B-2 或提交。
