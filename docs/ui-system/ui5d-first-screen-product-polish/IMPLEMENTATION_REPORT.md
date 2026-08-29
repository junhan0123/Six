# UI-5D · First Screen Product Polish v1.0 — Implementation Report（实现报告）

> 承接：`00_AUDIT.md`（真实 file:line 取证）+ `01_DESIGN.md`（D1–D4 最小改造方案）
> 纪律：`Audit → Design → Minimal Implement → Verify → STOP`
> 状态：**Implement + Verify 完成 · Report 落盘 · 🛑 STOP 等 Review（不提交 Git）**
> 范围：纯表现层 ADDITIVE 收口。**0 JS / 0 DOM 结构 / 0 事件 / 0 令牌重定义**。

---

## 0. 元信息与红线守约

| 项 | 内容 |
|---|---|
| 任务编号 | #887 Audit / #888 Design / #889 Implement / #890 Verify / #891 Report+STOP |
| 核心交付物 | `G:/xiao6/xiao6-ui/ui5d-first-screen-polish.css`（新建，9,815 字节） |
| 注册位置 | `G:/xiao6/xiao6-ui/index.html` 第 25–26 行（位于 `ui4d-home-experience.css` 之后，成为最终权威层） |
| 验证手段 | Chrome Headless(151) + CDP 真实探针（`_5d_shoot.mjs` / `_5d_themes.mjs`），非静态推断 |
| 加载层栈 | styles→premium→runtime-viz→execution-channel→**ui2.css**(令牌权威)→spatial-runtime→ui4b-first-screen→ui4b-explore-transition→ui4c-visible-upgrade→ui4c-unified-home→**ui4d**(前最高)→**ui5d**(本任务，最终权威) |

**红线守约结论（逐项 ✅）**：
- ✅ Backend / Agent / AppState / EventBus / DOMAIN / SYSTEM EVENTS — **零触碰**
- ✅ `solar-system.js` / `galaxy-experience.js` — D4 仅 CSS filter/opacity/transform，零 JS
- ✅ 不新增功能 — 导航/输入/星图 JS 行为零改动
- ✅ World/Operation/Overlay 三层 — 仅消费既有 `data-spatial-layer` 语义，未新定义第二套
- ✅ UI-5C-1 成果 — 不覆盖 `chat-mode` 规则（实测零回退）
- ✅ AI Presence 三唯一 — 仅消费 `body[data-presence]` 与 `--presence-color`，未重定义/未新增脉动
- ✅ 新增视觉语言/令牌/事件 — **0 新增**

---

## 1. Audit 摘要映射（承 00_AUDIT.md）

| 问题域 | Audit 发现的真实问题 | 决策 |
|---|---|---|
| HUD | 「小6·本地个人 AI 副驾」与首屏英雄区三重身份表述；9 实心色板常驻权重过高；HUD 平铺无主次 | D1 收敛（去冗余/降级/主次） |
| 左导航 | `index.html:81-92` 5 图标按钮无标签，语义停留在「App Navigation」 | D2 转为 Capability Navigation（图标+能力名竖排） |
| Command Dock | UI-4D-1 已初版（标题改名+presence 内描边+hint），但「控制台」气质不足 | D3 强化 presence 辉光 + 工具次级化 |
| Galaxy | 默认 `brightness(0.46)` 偏暗如壁纸；探索态退后不足 | D4 环境化提亮 + 探索态增强 |

---

## 2. Design 决策清单（承 01_DESIGN.md，D1–D4 全部落地）

### D1 · 顶部 HUD 收敛
- **D1-a 品牌轻量化**：首页态 `.os-brand { font-size:11px; letter-spacing:.10em; color:var(--text-dim); opacity:.7; font-weight:600; }`
- **D1-b 主题选择降级**：`.os-theme-picker { gap:var(--sp-4); padding:var(--sp-2); opacity:.55; transition:…; }` + `:hover/:focus-within{opacity:1}` + `button{width:20px;height:20px}`（32→20）
- **D1-c 主次明确**：`.os-state{box-shadow:0 0 16px -6px color-mix(in srgb,var(--presence-color) 50%,transparent)}` + `.os-clock{opacity:.7}`

### D2 · 左导航 Capability Navigation
- **D2-a 按钮竖排**：`.os-nav-btn{flex-direction:column; min-height:46px; padding:var(--sp-6) 0; gap:5px}` + `svg{width:20px;height:20px}`（76px 列宽内成立，不改网格）
- **D2-b 能力名标签**（按 `data-nav` 注入 `::after`）：`workspace→"对话" / command→"指令" / galaxy→"星图" / assistant→"语音" / settings→"设置"`，`font-size:11px; color:var(--text-dim)`，`hover/active→var(--text)`
- **D2-c 品牌锚点**：`.os-nav-brand::after{content:"小6"}`（与能力按钮同构「标识+名」脊柱）
- **D2-d galaxy 次级保留**：`[data-nav="galaxy"]::after{opacity:.7}`（沿用 UI-4C-2，不回退）

### D3 · Command Dock → AI Intent Console
- **D3-a 占位符语义**：`.os-dock input::placeholder{color:var(--text-dim)}`
- **D3-b 聚焦态 presence 辉光增强**：`.os-dock-bar:focus-within{box-shadow:0 0 0 3px color-mix(in srgb,var(--presence-color) 45%,transparent), 0 0 36px -8px color-mix(in srgb,var(--presence-color) 40%,transparent); border-color:color-mix(in srgb,var(--presence-color) 55%,var(--border))}`
- **D3-c 工具按钮次级化**：`.os-dock-btn:not(.send){background:transparent; border-color:transparent; color:var(--text-dim); width:34px; height:34px}` + `:hover{background:var(--surface-2); color:var(--text)}`
- **D3-d/e** 标题态沿用 UI-4D-1；conversation 态 Dock 已被 UI-5C-1 隐藏，D3 仅作用于首页态

### D4 · Galaxy 默认环境化 + 探索态增强
- **D4-a 默认环境化（Home）**：`#solarCanvas{filter:brightness(0.56) saturate(0.72) contrast(1.0)}` + `.galaxy-veil{opacity:0.42}` + `.galaxy-veil::after` 重写渐晕（中心更开、边缘更柔）
- **D4-b 探索态增强（universe-mode / zz-explore）**：`#solarCanvas{filter:brightness(1.02) saturate(1.08) contrast(1.02); transform:scale(1.03)}` + `.galaxy-veil{opacity:0}` + `#osShell,#app{filter:blur(9px); transform:scale(.984); opacity:.30}`（**修正写法，见 §4 已知修复**）
- **D4-c 持久背景不变**：`chat-mode` 下 Galaxy 仍按 UI-5C-1/ui4c 既有权威 `brightness(0.46)` 保持

---

## 3. 实现清单

| # | 文件 | 动作 | 说明 |
|---|---|---|---|
| 1 | `xiao6-ui/ui5d-first-screen-polish.css` | **新建** | 31 对花括号平衡（Node 校验 `31/31 BALANCED`），9,815 字节，纯 ADDITIVE 层 |
| 2 | `xiao6-ui/index.html` | 编辑（第 25–26 行追加 `<link>`） | `<link rel="stylesheet" href="ui5d-first-screen-polish.css?v=20260810d5" />` 位于 `ui4d-home-experience.css`(L24) 之后，成为最终权威层 |
| 3 | `docs/ui-system/ui5d-first-screen-product-polish/_5d_shoot.mjs` | 新建 | CDP 验证脚本，`ZZ_PHASE=before/after` 双相，5 场景（home-1920/1440/720、conversation-1920[+chat-mode]、explore-1920[+universe-mode]） |
| 4 | `docs/ui-system/ui5d-first-screen-product-polish/_5d_themes.mjs` | 新建 | 9 主题横滚回归，点击 `.os-theme-picker button[data-theme]` 切换并探针 `scrollWidth>innerWidth+1` |
| 5 | `shots-before/`(5 PNG) + `shots-after/`(5 PNG) + `shots-themes/`(9 PNG) | 生成 | Before/After/主题 三组 GUI 截图 |
| 6 | `_probe_before.json` / `_probe_after.json` / `_probe_themes.json` | 生成 | 结构化 computedStyle 探针证据 |

**作用域护栏（实现中严守）**：
- 首页态规则统一限定 `body:not(.chat-mode):not(.universe-mode)`
- 探索态规则显式 `body.universe-mode, body.zz-explore`
- 绝不覆盖 UI-5C-1 的 `chat-mode` 规则

---

## 4. 验证结果（真实 CDP 探针数值对照）

> 全部数值来自 `:8000/index.html` 真实渲染 + Chrome Headless(151) 探针，**非推断**。Before = 摘除 ui5d link 的 UI-4D-1 基线；After = 含 ui5d。

### 4.1 D1 HUD 收敛

| 指标 | Before | After | 断言 |
|---|---|---|---|
| `.os-brand` opacity / font-size | 1 / 13px | **.7 / 11px** | ✅ 轻量化 |
| `.os-theme-picker` opacity | 1 | **.55**（hover→1） | ✅ 可收起感 |
| `.os-theme-picker button` width | 26px | **20px** | ✅ 色板缩小 |
| `.os-state` box-shadow | `…/0.42… 0 0 14px -6px` | `…/0.50… 0 0 16px -6px` | ✅ presence 50% 辉光为 HUD 焦点 |
| `.os-clock` opacity | 1 | **.7** | ✅ 环境信息次级 |

### 4.2 D2 Capability Nav

| 指标 | Before | After |
|---|---|---|
| `navLabels.workspace` | `""` | **"对话"** |
| `navLabels.command` | `""` | **"指令"** |
| `navLabels.galaxy` | `""` | **"星图"** |
| `navLabels.assistant` | `""` | **"语音"** |
| `navLabels.settings` | `""` | **"设置"** |
| `navLabels.brand` | `""` | **"小6"** |

✅ 5 能力名 + 品牌名全部经 `::after` 注入可见；按钮为「图标(20)+标签(2字)」竖排，76px 列宽内成立；`data-nav` 与 `syncNav()` 行为不变（未重写点击逻辑）。

### 4.3 D3 Intent Console

| 指标 | Before | After |
|---|---|---|
| `.os-dock-bar:focus-within` box-shadow | `…/0.28… 0 0 0 1px, …/0.7… 0 22px 60px -24px` | **`…/0.45… 0 0 0 3px, …/0.4… 0 0 36px -8px`** |
| 非发送工具按钮背景 | `rgba(34,211,238,0.05)` | **`rgba(0,0,0,0)`**（透明次级化） |

✅ 聚焦时 presence 辉光（45%/40% color-mix）明显强于 UI-4D-1 基础态；语音/文件/截图/快捷降为透明次级工具，发送(.send) 保持 accent 主行动。

### 4.4 D4 Galaxy

| 指标 | 阶段 | Before | After |
|---|---|---|---|
| Home `#solarCanvas` filter | — | `brightness(0.46) saturate(0.6) contrast(0.95)` | **`brightness(0.56) saturate(0.72) contrast(1)`** |
| Home `.galaxy-veil` opacity | — | 0.5 | **0.42** |
| Explore(universe-mode) `#solarCanvas` filter+transform | — | `brightness(1)` / 无 scale | **`brightness(1.02) saturate(1.08) contrast(1.02)` + `scale(1.03)`** |
| Explore(universe-mode) `.galaxy-veil` | — | 0 | 0（保持淡出） |
| Explore(universe-mode) `#osShell` | — | `blur(7px) op .35 scale(.984)` | **`blur(9px) op .30 scale(.984)`** |

✅ 默认态更「活」仍弱于 Operation Layer（环境层级成立）；探索态世界层上浮、操作层更干净沉入。

### 4.5 UI-5C-1 保护验证（关键护栏）

| 指标 | conversation-1920（`chat-mode`）Before | conversation-1920（`chat-mode`）After |
|---|---|---|
| `.os-brand` opacity / font-size | 1 / 13px | **1 / 13px（零回退）** |
| `.os-theme-picker` opacity | 1 | 1 |
| `navLabels` 全字段 | `""` | `""`（chat-mode 下导航规则未注入，符合护栏） |
| `#solarCanvas` filter | `brightness(0.46)…` | **`brightness(0.46)…`（UI-5C-1 成果零回退）** |
| Dock | 隐藏（UI-5C-1 `.dock{display:none}`） | 隐藏（保持一致） |

✅ UI-5C-1 的 `chat-mode` 规则（ui2.css:941-970）未被覆盖/回退。

### 4.6 9 主题横滚回归（真实切换）

| 主题 | horizOverflow | navLabel | bg |
|---|---|---|---|
| dark / quantum / midnight / dark-cyan / dark-green / dark-purple / dark-amber / dark-rose / light | **全 False** | **全 "对话"** | 各自正常（如 dark-cyan `#060a0f`、light `#eef2f7`） |

✅ 9 主题零横向滚动、能力标签正常、0 异常。

### 4.7 三轮 JS 异常计数

- `before` 阶段 errors：`[]`
- `after` 阶段 errors：`[]`
- `themes` 阶段 errors：`[]`

✅ 全程 **0 个 JS 运行时异常**。

---

## 5. 红线校验（Implement 阶段自检）

| 红线 | 实测 | 结论 |
|---|---|---|
| JS 改动 | `git diff` 前端 JS 零改动；仅新增 1 CSS + 1 `<link>` | ✅ 0 JS |
| DOM 结构改动 | 未增删任何元素/属性 | ✅ 0 DOM |
| 新增事件 | 无 | ✅ 0 事件 |
| 令牌重定义 | 未 `:root`/`:*` 新定义任何 `--*` | ✅ 0 令牌重定义 |
| 第二视觉语言 | 仅消费 ui2 令牌 + `color-mix` 派生 | ✅ 0 新增 |
| solar-system.js / galaxy-experience.js | 未读未改 | ✅ 隔离 |
| AI Presence | 仅消费 `--presence-color` | ✅ 三唯一保护 |

---

## 6. 已知修复（Verify 阶段发现并修正）

**D4-b 探索态 `filter` 非法（本回合发现的关键 bug，已修复）**

- 初版误写：`body.universe-mode #osShell, … #app { filter:blur(9px) scale(.984); opacity:.30; }`
- 根因：`scale()` 是 **transform 函数，不是 filter 函数**；整条 `filter` 声明因含非法函数被浏览器整体丢弃，回退到 `ui4b-explore-transition.css:74` 的 `filter:blur(7px)`（`opacity:.30` 因是独立属性仍生效）。
- 证据（初次 after 探针 scene 05-explore-1920）：`osShell { opacity:"0.3", filter:"blur(7px)", transform:matrix(0.984,…) }` —— blur 卡在 7px 未达 9px。
- 修复：拆为合法写法 `filter:blur(9px); transform:scale(.984); opacity:.30;`（`transform:scale(.984)` 沿用 ui4b 既有轻微退后，仅加深 blur）。
- 重跑 after 确认：`osShell { opacity:"0.3", filter:"blur(9px)", transform:matrix(0.984,0,0,0.984,0,0) }` ✅。

---

## 7. 响应式与窄屏

- `@media (max-width: 980px)`：`ui2.css` 将 `.os-nav` 转 `flex-direction:row` 横排；D2 列向按钮在窄屏仍为「图标在上标签在下」紧凑单元，不破坏横排。
- 实测 720×900（narrow）场景：D1–D4 全部断言与 1920/1440 一致，`navLabels` 正常、`os-brand` 收敛、Galaxy 环境化生效。✅

---

## 8. 已知限制（如实披露，非缺陷）

1. **D2 为视觉/文案层 Capability 表达**：仅通过 CSS `::after content` 注入能力名标签，未改动 `syncNav` JS 的路由逻辑；导航「调用能力」语义由视觉层呈现，行为层仍为 UI-5C-1 既有跳转。若后续需「能力→对应 Workspace 面板」的真实路由，属独立任务，不在本 Phase 范围。
2. **`zz-explore` 钩子仍预留未接线**：D4-b 同时覆盖 `body.zz-explore`，但当前前端未实际打该 class（探索态走 `universe-mode`）；规则已就位，待后续探索入口接线时自动生效，无副作用。
3. **主题切换依赖既有 `.os-theme-picker button[data-theme]`**：D1-b 仅做视觉降级，未改主题切换逻辑；点击行为沿用 UI-4D-1/UI-5C-1。

---

## 9. 交付物清单

```
docs/ui-system/ui5d-first-screen-product-polish/
├── 00_AUDIT.md                     # 真实 file:line 取证审计
├── 01_DESIGN.md                    # D1–D4 最小改造方案（Design Only）
├── IMPLEMENTATION_REPORT.md        # 本报告（#891）
├── _5d_shoot.mjs                   # CDP before/after 双相验证脚本
├── _5d_themes.mjs                  # 9 主题横滚回归脚本
├── _probe_before.json              # 基线探针（UI-4D-1）
├── _probe_after.json               # 含 ui5d 探针
├── _probe_themes.json              # 9 主题回归探针
├── shots-before/  (01–05 PNG)      # UI-4D-1 基线截图
├── shots-after/   (01–05 PNG)      # UI-5D 截图
└── shots-themes/  (9 PNG)          # 9 主题截图

xiao6-ui/
├── ui5d-first-screen-polish.css    # 核心交付物（31/31 括号平衡，9,815 B）
└── index.html                      # L25–26 追加 ui5d <link>（最终权威层）
```

---

## 10. 验收结论

| 维度 | 结果 |
|---|---|
| D1 HUD 收敛 | ✅ 品牌 .7/11px、色板 .55/20px、state 为焦点 |
| D2 Capability Nav | ✅ 对话/指令/星图/语音/设置/小6 全部注入 |
| D3 Intent Console | ✅ presence 辉光增强、工具次级化 |
| D4 Galaxy | ✅ Home 环境化 .56、Explore blur(9px)/op .30（已修 bug） |
| UI-5C-1 保护 | ✅ chat-mode 零回退 |
| 9 主题 / 响应式 | ✅ 0 横滚、720/1440/1920 一致 |
| 红线 | ✅ 0 JS / 0 DOM / 0 事件 / 0 令牌重定义 |
| JS 异常 | ✅ 三轮均为 0 |

> ▣ **🛑 STOP — UI-5D 全部阶段（Audit → Design → Implement → Verify → Report）完成。不提交 Git，等待主人 Review。**
