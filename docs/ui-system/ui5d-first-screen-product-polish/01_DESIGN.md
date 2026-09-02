# UI-5D · First Screen Product Polish v1.0 — Design（01_DESIGN.md）

> 承接：00_AUDIT.md（真实 file:line 取证）
> 纪律：**Design Only（本阶段零代码改动）**；下一步 Minimal Implement 仅新增 `ui5d-first-screen-polish.css`
> 状态：**Design 完成 · 等待 Implement 放行**

---

## 0. 设计原则（承接冻结架构）

1. **ADDITIVE 最高权威层**：新建 `ui5d-first-screen-polish.css`，加载于 `ui4d-home-experience.css`（index.html:24）之后；仅本文件显式选择器生效，不改 ui2.css / 任何既有层。
2. **作用域护栏**：首页态规则限定 `body:not(.chat-mode):not(.universe-mode)`；探索态规则显式 `body.universe-mode, body.zz-explore`；**绝不**覆盖 UI-5C-1 的 `chat-mode` 规则。
3. **零裸色值**：全部颜色经 `color-mix()` 从 ui2 令牌（`--accent/--presence-color/--surface*/--border/--text*/--muted/--bg/--glow`）派生。
4. **令牌不重定义**：不新定义 `--*` 令牌；复用既有 `--dur-*/--ease-*/--sp-*/--radius-*/--glass-*`。
5. **AI Presence 三唯一**：仅消费 `body[data-presence]` 与 `--presence-color`；不重定义、不新增脉动（复用 `vitPulse`）。
6. **三层保护**：World/Operation/Overlay 语义与 `data-spatial-layer` 不变；不新增第二套视觉语言/事件/状态。
7. **不新增功能**：导航/输入/星图 JS 行为零改动；仅表现层收口。

---

## 1. D1 · 顶部 HUD 收敛

**目标**：降低 HUD 视觉噪音、建立「AI 状态 > 身份 > 环境信息」主次，清理品牌冗余。

**现状问题**（Audit §2）：`os-brand`「小6 · 本地个人 AI 副驾」与首屏英雄区「小6/你的本地个人 AI 操作系统」三重身份表述；`os-theme-picker` 9 实心色板常驻、权重过高；HUD 元素平铺无主次。

**最小改造（纯 CSS，首页态）**：

- **D1-a · 品牌轻量化（去冗余）**
  `body:not(.chat-mode):not(.universe-mode) .os-hud .os-brand { font-size:11px; letter-spacing:.10em; color:var(--text-dim); opacity:.7; font-weight:600; }`
  → 把 HUD 品牌降为次级身份标记（首屏英雄区已承担主身份），消除三重「小6」的视觉竞争。
- **D1-b · 主题选择降级（可收起感）**
  `body:not(.chat-mode):not(.universe-mode) .os-hud .os-theme-picker { gap:var(--sp-4); padding:var(--sp-2); opacity:.55; transition:opacity var(--dur-base); }`
  `… .os-theme-picker:hover, … .os-theme-picker:focus-within { opacity:1; }`
  `… .os-theme-picker button { width:20px; height:20px; }`（由 32→20 缩小色板）
  → 9 色板缩为低调小点，悬停/聚焦才满权；移除「彩色方块阵列」的视觉重量，仍完全可用。
- **D1-c · 主次明确**
  `… .os-hud .os-state { /* UI-4D-1 已 glass+presence；此处确保为 HUD 焦点 */ box-shadow:0 0 16px -6px color-mix(in srgb,var(--presence-color) 50%,transparent); }`
  `… .os-hud .os-clock { opacity:.7; }`（环境信息次级）
  → 状态药丸为 HUD 主焦点，时钟/品牌次级。

**不改**：HUD 结构、工具按钮功能、clock 逻辑。

---

## 2. D2 · 左导航 Capability Navigation

**目标**：把「应用图标栏」重述为「能力脊柱」——补可见能力名标签，语义从「打开页面」转为「调用能力」；JS 行为（syncNav/app.js）零改动。

**现状**（Audit §3）：`index.html:81-92` 5 图标按钮无标签；`ui4c-unified-home.css:88-98` 已把 galaxy 降为次级环境入口。网格 `grid-template-columns:76px 1fr 380px`（ui2.css:375），**nav 列固定 76px**。

**最小改造（纯 CSS，首页态；不改网格列宽）**：

- **D2-a · 按钮竖排 图标+标签**
  `body:not(.chat-mode):not(.universe-mode) .os-nav-btn { width:auto; height:auto; min-height:46px; padding:var(--sp-6) 0; flex-direction:column; gap:5px; }`
  `… .os-nav-btn svg { width:20px; height:20px; }`（图标略缩以容纳标签）
  → 76px 列宽内「图标(20)+标签(2字)」竖排成立，无需改网格。
- **D2-b · 能力名标签（按 data-nav 注入）**
  ```
  [data-nav="workspace"]::after { content:"对话"; }
  [data-nav="command"]  ::after { content:"指令"; }
  [data-nav="galaxy"]   ::after { content:"星图"; }
  [data-nav="assistant"]::after { content:"语音"; }
  [data-nav="settings"] ::after { content:"设置"; }
  ```
  `… .os-nav-btn::after { font-size:11px; letter-spacing:.08em; color:var(--text-dim); }`
  `… .os-nav-btn:hover::after, … .os-nav-btn.active::after { color:var(--text); }`
  → 导航读作「对话/指令/星图/语音/设置」能力清单，明确 Capability Focus 语义。
- **D2-c · 品牌锚点补「小6」标签（一致性）**
  `… .os-nav-brand::after { content:"小6"; display:block; margin-top:4px; font-size:11px; color:var(--text-dim); }`
  `… .os-nav-brand { flex-direction:column; gap:4px; height:auto; }`
  → 品牌与能力按钮同构为「标识 + 名」脊柱。
- **D2-d · galaxy 次级环境入口保持**（沿用 UI-4C-2，本任务不回退）
  `… .os-nav-btn[data-nav="galaxy"] { /* 维持 opacity:.5 + 虚线描边（ui4c 已定） */ }`
  `… .os-nav-btn[data-nav="galaxy"]::after { opacity:.7; }`（标签也次级化）

**红线安全**：仅 CSS `content` 注入 + 布局微调；`data-nav` 属性与 `syncNav()` 行为不变；UI-5C-1 的 `chat-mode` 导航（工作台=对话进入）不受影响。

---

## 3. D3 · Command Dock → AI Intent Console（精炼升级）

**目标**：在 UI-4D-1 初版（标题改名+presence 内描边+意图 hint）之上，强化「控制台」气质；零 JS 行为改动。

**现状**（Audit §4）：`command-dock.js:26-36` 五按钮 + hint；`ui4d:80-107` 已初版。

**最小改造（纯 CSS）**：

- **D3-a · 意图前缀 / 占位符语义升级**（首页态）
  `body:not(.chat-mode):not(.universe-mode) .os-dock input::placeholder { color:var(--text-dim); }`
  （占位符文本由 JS 固定「向小6下达指令，或拖入文件 / 截图…」——保留；视觉仅确保与控制台调性一致，不强改文案）
- **D3-b · 聚焦态 presence 辉光增强**
  `body:not(.chat-mode):not(.universe-mode) .os-dock .os-dock-bar:focus-within { box-shadow:0 0 0 3px color-mix(in srgb,var(--presence-color) 45%,transparent), 0 0 36px -8px color-mix(in srgb,var(--presence-color) 40%,transparent); border-color:color-mix(in srgb,var(--presence-color) 55%,var(--border)); }`
  → 输入即「意图」，聚焦时控制台随 AI 态发光，比 UI-4D-1 基础态更明显。
- **D3-c · 工具按钮次级化**
  `… .os-dock .os-dock-btn:not(.send) { background:transparent; border-color:transparent; color:var(--text-dim); width:34px; height:34px; }`
  `… .os-dock .os-dock-btn:not(.send):hover { background:var(--surface-2); color:var(--text); }`
  → 语音/文件/截图/快捷 降为低调次级工具，发送(.send) 保持 accent 主行动；凸显「意图控制台」而非「工具条」。
- **D3-d · 面板标题态（沿用 UI-4D-1「AI Intent Console · 意图控制台」）**
  不重复改名；仅确保 `body[data-presence]` 下标题描边随态（复用 UI-4D-1 机制，本任务不重定义）。
- **D3-e · conversation 态（UI-5C-1）一致性**
  在 `body.chat-mode` 下 Dock 已隐藏（ui2.css:958 `.dock{display:none}`），故 D3 仅作用于首页态；如 Dock 在 conversation 态仍有可见形态（视 UI-5C-1 隐藏范围），追加 `body.chat-mode` 同源规则确保一致——**不改动 UI-5C-1 既有声明**。

---

## 4. D4 · Galaxy 默认环境化 + 探索态增强

**目标**：默认态 Galaxy 从「暗壁纸」调为「活的氛围环境」；探索态强化沉浸；纯 CSS，不碰 galaxy-experience.js / solar-system.js。

**现状**（Audit §5）：默认 `brightness(0.46)`+veil 0.5+渐晕（ui4c:23-41）；探索态操作层退后+世界层提亮（ui4b-explore:68-120）。

**最小改造（纯 CSS）**：

- **D4-a · 默认环境化（Home）**
  `body:not(.chat-mode):not(.universe-mode) #solarCanvas { filter:brightness(0.56) saturate(0.72) contrast(1.0); }`
  （由 0.46→0.56：更「活」但仍弱于 Operation Layer，维持环境层级）
  `… .galaxy-veil { opacity:0.42; }`（略减遮罩，更通透）
  `… .galaxy-veil::after { /* 重写渐晕：中心更开、边缘更柔，增强包裹感 */
     background:radial-gradient(130% 125% at 50% 42%, transparent 42%, color-mix(in srgb,var(--bg) 38%,transparent) 80%, color-mix(in srgb,var(--bg) 60%,transparent) 100%); }`
  → Galaxy 读起来「身处其中」而非「背后壁纸」。
- **D4-b · 探索态增强（universe-mode / zz-explore）**
  `body.universe-mode #solarCanvas, body.zz-explore #solarCanvas { filter:brightness(1.02) saturate(1.08) contrast(1.02); transform:scale(1.03); transform-origin:center; transition:filter var(--dur-slow) var(--ease-soft), transform var(--dur-slow) var(--ease-soft); }`
  （提亮+轻微推近，沉浸感）
  `body.universe-mode .galaxy-veil, body.zz-explore .galaxy-veil { opacity:0; }`（已淡出，保持）
  `body.universe-mode #osShell, body.universe-mode #app, body.zz-explore #osShell, body.zz-explore #app { filter:blur(9px); opacity:.30; }`
  （在 ui4b-explore 基础 blur(7)/op .35 上略增退后，操作层更干净沉入）
  → 探索态 =「世界层上浮为焦点、操作层彻底退后」，单一空间的注意力迁移更强烈。
- **D4-c · 持久背景不变**
  chat-mode 下 Galaxy 仍按 UI-5C-1/ui4c 既有权威（`brightness(0.46)`）保持；本任务 D4-a 仅覆盖 Home 默认，D4-b 仅覆盖探索态，不触 chat-mode。

---

## 5. 验收映射（Design → Verify）

| 任务 | 验收断言（CDP 探针 / 截图） |
|---|---|
| D1 HUD 收敛 | `.os-brand` font-size<原 13 / opacity≈.7；`.os-theme-picker` 按钮 width≈20、默认 opacity≈.55、hover→1；`.os-state` 为 HUD 视觉焦点 |
| D2 Capability Nav | 5 按钮 `::after` content = 对话/指令/星图/语音/设置 均可见；按钮为图标+标签竖排；`data-nav` 行为不变（点击仍触发 syncNav） |
| D3 Intent Console | `.os-dock-bar:focus-within` 出现 presence 辉光；非发送工具按钮次级化（透明/小）；标题仍为「AI Intent Console · 意图控制台」 |
| D4 Galaxy | Home：`#solarCanvas` brightness≈.56、veil≈.42；Explore(universe-mode)：brightness≈1.02、scale≈1.03、操作层 blur≈9/op≈.30 |
| 三层保持 | World(`#solarCanvas`/`.galaxy-veil`)/Operation(`#osShell`)/Overlay 选择器与 `data-spatial-layer` 不变 |
| UI-5C-1 保护 | `body.chat-mode` 规则（ui2.css:941-970）未被覆盖/回退；conversation 态 Dock 仍按 UI-5C-1 隐藏 |
| 红线 | 0 JS / 0 DOM 结构 / 0 事件 / 0 令牌重定义；仅新增 1 个 ADDITIVE CSS 文件 |
| 9 主题 / 响应式 | 在 dark-cyan 等 9 主题 + 1920/1440/720 尺寸下无布局崩坏、无横向滚动 |

---

## 6. 红线符合性（Design 自检）

| 红线 | 满足 |
|---|---|
| Backend / Agent / AppState / EventBus / DOMAIN / SYSTEM EVENTS | ✅ 仅 CSS |
| `solar-system.js` / `galaxy-experience.js` | ✅ D4 仅 CSS filter/opacity/transform，零 JS |
| 不新增功能 | ✅ 导航/输入/星图 行为不变 |
| World/Operation/Overlay 三层 | ✅ 仅消费既有 data-spatial-layer 语义 |
| UI-5C-1 成果 | ✅ 不覆盖 chat-mode 规则 |
| AI Presence 三唯一 | ✅ 仅消费 --presence-color |
| 新增视觉语言/令牌/事件 | ✅ 0 新增 |

> ▣ **STOP — Design Only，未修改任何代码。等待 Implement 放行。**
