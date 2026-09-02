# UI-5D · First Screen Product Polish v1.0 — Audit（00_AUDIT.md）

> 任务身份：**UI-5D · First Screen Product Polish v1.0**
> 上游：UI-5C-1（Conversation Core Integration，已 STOP）/ UI-4D-1（AI OS Home Experience）/ UI-4C-2（Unified Home Fusion）/ UI-4B-2A（Explore Transition）/ UI-5 · 02_NAVIGATION_RECONSTRUCTION
> 执行日期：2026-08-10
> 工作流纪律：**Audit → Design → Minimal Implement → Verify → STOP**
> 状态：**Audit 完成 · 零代码改动 · 进入 Design**

---

## 0. 元信息与红线

| 项 | 内容 |
|---|---|
| 唯一允许改动 | CSS（新增 ADDITIVE 层 `ui5d-first-screen-polish.css`）；必要时 index.html 标签/类微调（不新增功能） |
| 禁止触碰 | Backend / Agent / AppState / EventBus / DOMAIN / SYSTEM EVENTS / `solar-system.js` / `galaxy-experience.js` |
| 不新增功能 | 仅表现层收口，不改导航/输入/星图 的 JS 行为 |
| 必须保持 | World Layer / Operation Layer / Overlay Layer 三层；UI-5C-1 成果（`chat-mode` 规则）零回退 |
| 现有 ADDITIVE 层栈（加载末序，index.html:8–24） | styles→premium→runtime-viz→execution-channel→**ui2**(令牌权威)→spatial-runtime→ui4b-first-screen→ui4b-explore-transition→ui4c-visible-upgrade→ui4c-unified-home→**ui4d-home-experience**(当前最高权威) |
| 本任务落点 | 新建 `ui5d-first-screen-polish.css` 加载于 `ui4d-home-experience.css` 之后（最终权威覆盖） |

**红线自检（先行）**：本 Audit 阶段 0 行代码改动；下文全部为真实读盘 file:line 取证。

---

## 1. 首屏三层结构现状（World / Operation / Overlay）

DOM 物理分层（`index.html`）：
- **World Layer**：`#solarCanvas`（L73，`data-spatial-layer="world"`）+ `.galaxy-veil`（L75，world）。始终在场的背景环境。
- **Operation Layer**：`#osShell`（L78，operation）含 左导航(L81) / 顶部 HUD(L94) / 意识核心(L119) / 右栏(L136) / 底部(时间线+Command Dock)(L148) + `#universeView`(L161，operation，Ctrl+U 开发者视图) + `#app`(L257，legacy 聊天台，chat-mode 承载)。
- **Overlay Layer**：Command Palette / Settings / Toast / 各类浮层（z 60–9000，由各自系统管理）。

`chat-mode` 规则（UI-5C-1 成果，`ui2.css:941-970`）已使 OS Home 在对话态全程可见可交互、聊天层透明穿透——**本任务严禁回退**。

---

## 2. D1 · 顶部 HUD 现状（需「收敛」）

**DOM**（`index.html:94-116`）：
```
<header class="os-hud">                         (L94)
  <span class="os-brand">小6 · <b>本地个人 AI 副驾</b></span>   (L95)  ← 与 os-core 英雄名「小6」重复
  <span class="os-state" id="osState">…待命…</span>             (L96)  ← UI-4D-1 已 glass+presence 化
  <span class="os-spacer"></span>                              (L97)
  <div class="os-tools">                                        (L98)
     <button id="osContextToggle">…</button>                    (L100) 上下文入口
     <div class="os-theme-picker" id="osThemePicker">           (L103) 9 个主题色板按钮
        …9× <button class="t-*" data-theme="…">…</button>       (L104-112)
     </div>
  </div>
  <span class="os-clock" id="osClock">--:--</span>              (L115)
</header>
```

**CSS**（`ui2.css:584-617`）：`.os-hud` 为 flex 行：`brand / state / spacer / tools(上下文+9色板) / clock`。玻璃卡（`--surface`+`--border`+`--glass-3`）。

**收敛点（Audit 发现）**：
1. **品牌文案冗余**：HUD `os-brand`「小6 · 本地个人 AI 副驾」与首屏英雄区 `os-hero-title`「小6」（`index.html:124`）+ `os-hero-sub`「你的本地个人 AI 操作系统」（L125）内容重叠，首屏出现三处「小6」身份表述，信息层级发散。
2. **主题色板 9 按钮占据 HUD 右侧 1/3**：`os-theme-picker` 9 个实心色板（`ui2.css:895-911`）常驻展开，视觉权重高、与「AI 当前状态/意图入口」主轴无关，属二级设置。
3. **HUD 元素平铺无主次**：brand(身份) / state(状态) / tools(设置簇) / clock(时间) 等同权排布，未体现「AI 状态 > 意图入口 > 环境信息」的层次。

→ D1「收敛」= 在保持信息完整前提下，降低 HUD 视觉噪音、建立主次（身份/状态轻量化、主题选择降级为可收起、清理品牌冗余）。

---

## 3. D2 · 左导航现状（需 App→Capability）

**DOM**（`index.html:81-92`）：品牌(home) + 5 按钮：
```
workspace 对话 (L86)  · command 指令中心 (L87)  · galaxy 星图 (L88)
assistant 语音助理 (L89)  · settings 设置 (L90)
```
仅图标 + `title` 工具提示，**无可见能力名标签**，读起来是「应用图标栏」。

**CSS**（`ui2.css:394-431`）：`.os-nav` 竖排胶囊卡；`.os-nav-btn` 46×46 图标按钮；`.active` 左侧 accent 指示条。

**既有收敛（UI-4C-2 H4，`ui4c-unified-home.css:88-98`）**：`galaxy` 按钮已降权为次级「环境」入口（`opacity:.5` + 虚线描边），功能簇（对话/指令/助理/设置）保持满权——已部分迈向 Capability 语义。

**设计词汇（02_NAVIGATION_RECONSTRUCTION.md）**：Navigation = Capability Focus（不切页）；按钮应表达「在统一空间调整焦点」而非「打开页面」。完整重构需改 `syncNav()`/`app.js`（废止 `universe-mode`、改 `zz-galaxy-focus`、工作台改聚焦 Dock）——但：
- 该行为改写会触碰红线纪律「不新增功能」与 UI-5A 已定决策（保留 `universe-mode`/`chat-mode` 类、仅 CSS 重表达）；
- 本次为「Product Polish」，可接受子集 = **视觉/文案层表达 Capability Focus**，不改 JS 行为。

→ D2「Capability Navigation」= 给左导航按钮补**可见能力名标签**（对话/指令/星图/语音/设置），并把导航语义从「应用启动器」重述为「能力脊柱」；行为与既有 body 类体系不变（保护 UI-5C-1/UI-5A）。

---

## 4. D3 · Command Dock 现状（需 输入框→AI Intent Console 精炼升级）

**DOM/JS**（`command-dock.js:26-36`）：`#osDock` 内 `.os-dock-bar` 含 语音/输入(`#osDockInput`)/文件/截图/快捷/发送 五按钮 + `.os-dock-hint`（L36）。

**CSS**（`ui2.css:829-854`）：`.os-dock` 竖排；`.os-dock-bar` 输入条（surface-2 卡）；`.os-dock input` 透明输入；`.os-dock-btn` 38×38 工具按钮；`.send` accent 实心。

**既有升级（UI-4D-1 D2，`ui4d-home-experience.css:77-107`）**：
- 面板标题 CSS 改名「AI Intent Console · 意图控制台」（L80-88）；
- 输入条随 presence 反应内描边+软光（L92-98）；
- hint 下追加「用自然语言下达意图…」（L101-107）。

**待精炼（Audit 发现，本任务 D3 目标）**：
1. 输入条仍是「文本框 + 一排按钮」的**工具条形态**，未充分表达「意图控制台」的**控制台气质**（如：意图语义前缀、聚焦态辉光、与 AI Presence 更强的绑定）。
2. 五按钮（语音/文件/截图/快捷/发送）平铺，与「Intent Console」的高端感不匹配，可作次级化/收起。
3. 输入条在 home 态与 conversation 态（UI-5C-1 `chat-mode`）是同一组件双形态——精炼需同时照顾两态一致性。

→ D3「精炼升级」= 在 UI-4D-1 基础上，强化「AI Intent Console」视觉表达：意图前缀/占位符语义升级、聚焦态 presence 辉光增强、工具按钮次级化、与 AI Presence 三唯一更紧绑定；**零 JS 行为改动**。

---

## 5. D4 · Galaxy 现状（需 默认环境化 + 探索态增强）

**默认（Home）Galaxy**（`ui4c-unified-home.css:23-41`，UI-4C-2 H2）：
```
#solarCanvas  brightness(0.46) saturate(0.6) contrast(0.95)   (L23-24)  ← 偏暗，偏「死寂背景」
.galaxy-veil   opacity: 0.5                                 (L28-29)
.galaxy-veil::after  径向渐晕(中心通透/四周沉入 bg)          (L32-41)
```
**环境化不足**：默认 `brightness(0.46)` 使 Galaxy 偏暗、近乎「壁纸」而非「活的环境」；渐晕把四周压入 bg，中心虽通透但整体缺乏「身处星系之中」的包裹感。

**探索态（universe-mode / zz-explore）**（`ui4b-explore-transition.css:68-120`，UI-4B-2A）：
```
操作层 #osShell/#app  opacity→.35 + blur(7px) + scale(.984) 退后   (L68-81)
.galaxy-veil          opacity:0（淡出）                          (L85-89)
#universeView         40% 半透明空间纱                            (L108-113)
```
`.solar-canvas` 提亮由 `spatial-runtime.css` 处理（`brightness→1`）。
**增强空间**：探索态 Galaxy 已能上浮，但可进一步强化「沉浸感」——更明显提亮/饱和、轻微景深推近（scale）、去除操作层残留噪点；`zz-explore` 钩子预留未接线（UI-4B-2A 刻意不接线，本任务亦不接线，仅增强其 CSS 表现，使其与 `universe-mode` 同构更完整）。

→ D4「默认环境化 + 探索态增强」= 默认态把 Galaxy 从「暗壁纸」调为「活的氛围环境」（略提亮+更通透的渐晕+细微景深）；探索态强化沉浸（更亮/更饱和/轻微推近/操作层更干净退后）。**纯 CSS，零 galaxy-experience.js/solar-system.js 触碰**。

---

## 6. UI-5C-1 成果保护确认（不可回退）

`ui2.css:941-970`（UI-5C-1 实现）必须保持：
- `body.chat-mode #osShell { opacity:1; filter:none; pointer-events:auto }`（L941）
- `body.chat-mode #app { visibility:visible; pointer-events:none; z-index:50 }`（L942）
- 壳层隐藏 `.rail/.tele/.hud-bar/.dock`（L955-958）、`.chat-history` 常驻（L964-970）

本任务新增 CSS 层作用域限定 `body:not(.chat-mode):not(.universe-mode)`（首页态）或显式 `body.universe-mode/zz-explore`（探索态），**绝不**覆盖 `chat-mode` 上述规则。如确需微调 chat-mode 下 Dock 表达，仅在 UI-5C-1 同选择器内追加、不删不改其既有声明。

---

## 7. 关键约束与冲突点（Design 阶段须裁决）

1. **命名重叠**：UI-4D-1 的 D1–D4 标签与本任务 D1–D4 同名但侧重不同（UI-4D-1 是「AI Presence 成为首页核心身份」，本任务是「产品视觉收口」）。本任务 D1=HUD 收敛（UI-4D-1 未做）、D2=左导航 Capability（UI-4D-1 未碰）、D3=Dock 精炼（UI-4D-1 已做初版）、D4=Galaxy 环境化（UI-4D-1 未做）。→ 本任务在 UI-4D-1 之上叠加精炼，不重复造轮子。
2. **`zz-explore` 未接线**：D4 探索态增强同时作用于 `universe-mode`（真实 Ctrl+U 路径）与 `zz-explore`（预留钩子）。仅增强 CSS，不补触发 JS（避免触碰 galaxy-experience.js / 新增功能）。
3. **三层保护**：所有规则限定 World/Operation/Overlay 既有令牌与 data-spatial-layer 语义，不新增第二套视觉语言/令牌/事件。
4. **AI Presence 三唯一**：仅消费 `body[data-presence]` 与 `--presence-color`，不重定义。

---

## 8. Audit 结论

| 焦点 | 当前状态 | 本任务最小改造方向 | 红线安全 |
|---|---|---|---|
| D1 HUD | 品牌冗余 + 9 色板常驻 + 无主次 | 收敛：品牌轻量化/去冗余、主题选择可收起、建立主次 | ✅ 纯 CSS |
| D2 左导航 | 图标栏无标签、galaxy 已降级 | 补可见能力名标签 + 重述「能力脊柱」语义 | ✅ CSS（不碰 syncNav/app.js） |
| D3 Dock | UI-4D-1 初版 Intent Console | 精炼：意图前缀/聚焦辉光/工具次级化/presence 绑定 | ✅ 纯 CSS |
| D4 Galaxy | 默认 0.46 偏暗、探索态可更沉浸 | 默认环境化（提亮+通透渐晕+景深）、探索态增强 | ✅ 纯 CSS（不碰 galaxy JS） |

→ **进入 Design 阶段**，产出 D1–D4 最小 CSS 改造清单与验收映射。🛑 STOP（Audit 仅读）。
