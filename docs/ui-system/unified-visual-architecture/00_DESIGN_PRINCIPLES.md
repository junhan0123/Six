# 00 · Xiao6 AI OS 视觉设计原则（Design Principles）

> **文档类型**：统一视觉架构设计 · 原则层（Principle Layer）
> **阶段**：Unified Visual Architecture Design Phase v1.0 · **只设计，不实现**
> **代码改动**：**0**（纯设计文档；不修改任何 CSS / HTML / JS / 后端 / Galaxy / Runtime / AppState / EventBus）
> **生成日期**：2026-08-09
> **本阶段纪律**：完成后 **STOP**，不提交 Git，不进入 Visual Redesign，等待人工 Review。

---

## 0. 文档定位与权威层级

本阶段产出 **Xiao6 AI OS Visual Blueprint v1.0**，是下一阶段 Visual Redesign 的**唯一设计依据**。本文档（`00_DESIGN_PRINCIPLES.md`）是整个蓝图的**原则层**，为后续 6 份分册（布局 / Galaxy 融合 / 面板语言 / 入口导航 / Settings 演化 / 设计系统下一阶段）与最终报告提供不可动摇的约束。

| 层级 | 文档 | 与本蓝图关系 |
|---|---|---|
| **L0 最高** | `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` | 架构冻结红线，**本蓝图不得违反** |
| L1 决策 | `docs/decisions/DECISION_001..006`（含 `DECISION_004_GALAXY_BOUNDARY`） | 不可逾越的设计裁决 |
| 产品真相 | `docs/design/frozen/PRODUCT_CONSTITUTION.md` | 本蓝图为其视觉实现层 |
| 设计真相 | `xiao6-ui/DESIGN.md` | 既有 UI 2.0 约束（§7 Don'ts），本蓝图**上位细化不推翻** |
| **设计语言权威** | `docs/ui-system/UI_SYSTEM_v1.0.md` | 令牌 / 原语 / 主题 / 视觉语言唯一权威；本蓝图在空间与架构层**为其补完**，不重建 |
| **本蓝图（7 分册 + 报告）** | `docs/ui-system/unified-visual-architecture/*` | **空间架构 / 世界观 / 融合方案 / 导航 / Settings 演化**的唯一依据 |
| 证据层 | `docs/ui-system/final-convergence/00_AUDIT.md`、`UI_ELEMENT_INVENTORY.md` | 现状事实输入，不被本蓝图改写 |

> **关键定位**：`UI_SYSTEM_v1.0.md` 管「令牌与原语」（微观设计语言），本蓝图管「空间、世界观、关系与演化路径」（宏观架构）。二者互补，本蓝图**不重定义令牌值**，只规定「这些令牌如何组织成一个 AI OS 空间」。

---

## 1. 设计纪律红线（继承自 L0 / L1 / DESIGN.md / UI_SYSTEM v1.0）

本阶段及下游所有实现**必须**遵守以下红线（凡冲突一律以高层级为准）：

1. **禁止第二 Runtime / Memory / EventBus / Permission System** —— 视觉层绝不引入新状态权威。
2. **禁止绕过 AppState** —— 所有状态变更须经 `applyEvent → reducers`；前端渲染只读投影。
3. **禁止绕过 EventBus** —— 跨模块通信发领域事件。
4. **禁止直接调用 Executor** —— 必经 `PermissionGuard`。
5. **禁止修改 Galaxy 语义** —— 银河本体视觉资产（`solar-system.js`：自转 / 公转 / 星空 / 点击聚焦）**100% 保留**。
6. **禁止 Vision 直接控制电脑** —— OBSERVATION ONLY。
7. **DECISION_004 Galaxy 边界** —— Galaxy = 表现层 + 受控交互层；**不得持有可写状态**、**不得改本体**；所有交互经 `galaxy-overlay` 叠加层；Overlay Runtime 与 Galaxy 渲染解耦。
8. **UI 2.0 Don'ts** —— 禁 `styles.css` 新增 class；禁第二套组件 class；禁内联 `style=` 写视觉；禁改变既有视觉方向；禁硬编码 `rgba`；禁无 `zz-` 前缀通用组件；禁新增功能 / 页面 / 架构 / 通信协议。
9. **Golden State「禁止第二套 Token 体系」** —— 令牌体系只「激活 + 归类 + 补齐」，不「重建」（见 `UI_SYSTEM_v1.0.md` §1.2）。

---

## 2. 产品重新定义：Personal AI Operating System

小6不是聊天软件，不是 ChatGPT clone。它是**本地个人 AI 操作系统**（Local Personal AI Operating System v1.0，冻结于 Golden State）。

用户打开小6，是**进入一个属于自己的 AI 控制空间（AI Control Space）**，而不是「打开一个对话框」。这是本蓝图一切视觉决策的出发点：

- **不是「用软件」**，而是「**进入一个空间**」。
- **不是「和机器人说话」**，而是「**与一个常驻的 AI 意识共处、协作**」。
- **不是「功能列表」**，而是「**一个可探索、可操作的认知宇宙**」。

这一世界观直接回应了当前 7 大问题中的「AI OS 世界观未形成」「主界面视觉普通」「Galaxy 与主界面割裂」。

---

## 3. AI OS 设计哲学（Design Philosophy）

本蓝图以 5 条相互支撑的哲学原则统领全部视觉决策：

### P1 · 空间即操作系统（Space is the OS）
整个屏幕不是一个「网页」，而是用户 AI 伙伴的**认知空间**。银河（Galaxy）是这台「机器」的常驻世界层，工作区（Workspace）是操作面，命令坞（Command Dock）是统一输入，命令面板（Command Palette）是瞬时能力，AI Presence 是常驻意识。它们共享**同一套空间语法**，构成一个连续、可进入的 AI OS。

### P2 · 银河为常驻世界，非背景图（Galaxy as Living World, not Backdrop）
银河不是装饰性背景，而是**系统状态的活体可视化**（太阳=核心、轨道=Goal、星球=能力域、卫星=Agent、环=Memory、流星=主动推送）。它始终在场、可被聚焦、可交互（经 overlay），从而把「状态」变成用户**可感知、可探索的世界**，而非藏在菜单里的数字。

### P3 · 玻璃拟态的精密秩序（Precise Glass Order）
以深空基底承载高密度信息面板；玻璃拟态（毛玻璃 + 顶部 1px 内高光 + 强调色 glow）让面板**悬浮于星空之上**；网格与宽字距营造「控制台」式的秩序感。层级靠**透明度与 blur** 区分，而非重投影或纯扁平。

### P4 · 克制而明确的动效（Restrained, Intentional Motion）
动效是「注意力与状态的语言」，不是炫技。微位移、缓动曲线（`--ease-premium`）、状态脉动（thinking / planning / executing）传达 AI 的「生命感」；`prefers-reduced-motion` / `body.reduced-motion` 全量降级。

### P5 · 意识核心可见（Visible Consciousness Core）
AI 不是「一个按钮」，而是一个**在场、可感、人格一致**的存在。AI Presence（Avatar 状态、HUD 状态点、Insight 面板）把「AI 正在想 / 计划 / 执行」显式呈现，强化「和意识共处」的世界观。

---

## 4. 核心视觉关键词（Core Visual Keywords）

本蓝图的全部视觉决策须可追溯到以下关键词（设计评审的「词典」）：

| 维度 | 关键词 |
|---|---|
| 整体气质 | 深空 · 玻璃拟态 · 精密 · 冷静 · 略带未来主义 |
| 空间隐喻 | 控制甲板（Command Deck）· 认知宇宙 · 可进入的空间 |
| 色彩 | 深空基底 · 青蓝强调（`--accent` / `--accent-2`）· 类太阳系暖色点缀（太阳/星球本体，非 UI 色） |
| 材质 | 毛玻璃（blur 26）· 1px 描边 · 顶部内高光 · 强调 glow |
| 秩序 | 网格 · 宽字距分区标题 · tabular-nums 数字 · 8px 节奏 |
| 动效 | 微动效 · 缓动曲线 · 状态脉动 · 克制 |
| 信息 | 高密度 · 有序 · 面板网格承载 · 不压缩留白 |
| 世界感 | 银河常驻 · AI 在场 · 状态可视化 · 可探索 |

---

## 5. 我们做什么 / 不做什么（Scope）

### 5.1 本蓝图**做**（设计层）
- 定义 AI OS 的空间架构（Galaxy / Workspace / Command Dock / Panel / Settings / Overlay / AI Presence 的关系）。
- 给出 Galaxy ↔ Workspace 融合的**方案比较与推荐**（符合 DECISION_004）。
- 规定面板系统的**统一空间语言**（规则，非 CSS）。
- 重设计功能入口与导航（发现 Memory / Tasks / Goals / Search / Tools / Settings / Agent 状态）。
- 规划 Settings 从「Legacy 页面」到「AI OS Configuration Center」的**演化路径**（非重写）。
- 规定设计系统下一阶段的补充方向（Color / Typography / Motion / Depth / Spatial / Component）。
- 定义「用户第一分钟体验」（First-Minute Experience）。

### 5.2 本蓝图**不做**（纪律边界）
- ❌ 不写 / 不改任何 CSS / HTML / JS / 组件 / 布局代码。
- ❌ 不改 Galaxy / Three.js / solar-system.js / Backend / Agent / 功能。
- ❌ 不提交 Git；不进入 Visual Redesign 实现。
- ❌ 不新建设计令牌值（只引用 / 规划激活既有 `--*` 体系）。
- ❌ 不创造与 Golden State / DECISION_004 / DESIGN.md / UI_SYSTEM v1.0 冲突的概念。
- ❌ 不推翻已冻结的产品身份、事件契约、Runtime / Memory / EventBus 架构。

---

## 6. 视觉原则清单（12 条可评审原则）

以下 12 条原则用于评审本蓝图及下游所有视觉实现。每条标注其权威/事实依据。

1. **单一空间，非多 App**（依据：产品重定义 + IA 三支柱共生）—— 银河 / 工作区 / 命令 / 面板是一个连续空间，不是切换的多个界面。
2. **银河纯可视化，零可写状态**（依据：DECISION_004 + 红线-5）—— 银河只投影，不持有；交互经 overlay。
3. **聊天仅为平级入口**（依据：INFORMATION_ARCHITECTURE §2）—— 不独占中央区；中央是「你的 AI 空间」，不是聊天框。
4. **共享空间语法**（依据：DESIGN.md §5/§6 + UI_SYSTEM v1.0 §4）—— 所有 Surface 共用 depth / glass / grid / glow / motion 语法，消除视觉分叉。
5. **玻璃悬浮，非扁平非重投影**（依据：DESIGN.md §1/§6）—— blur 26 + 1px border + 内高光 + glow。
6. **令牌唯一源 = ui2.css**（依据：DESIGN.md + UI_SYSTEM v1.0 §0）—— 改视觉先改令牌；禁硬编码 rgba。
7. **zz- 前缀唯一组件体系**（依据：DESIGN.md §4/§9）—— 缺失组件仅命名不实现；禁第二套 class。
8. **状态四态强制**（依据：UI_SYSTEM v1.0 §1.7）—— hover / focus-visible / disabled / loading / error 为组件契约强制项，键盘可达（WCAG AA）。
9. **注意力模型调节银河显隐**（依据：本蓝图 §2 P2 + DECISION_004）—— 用「聚焦 / 收敛」注意力机制连通银河与工作区，而非硬切模式。
10. **意识核心可见**（依据：EXPERIENTIAL_PROTOTYPE_SPEC + Phase 8 AI Presence）—— AI Presence 显式呈现在场 / 思考 / 计划 / 执行。
11. **信息密度靠网格，不靠压缩留白**（依据：DESIGN.md §5）—— 面板内 22px 留白 + 面板网格承载密度。
12. **离线优先，禁 CDN**（依据：DESIGN.md §3.1 + JARVIS 零密钥优先）—— 字体 / 资源自托管，无网络回落系统字体。

---

## 7. 本阶段产出地图（Output Map）

| 文件 | 主题 | 核心交付 |
|---|---|---|
| `00_DESIGN_PRINCIPLES.md`（本文） | 原则层 | 纪律红线 / 哲学 / 关键词 / 12 原则 |
| `01_GLOBAL_LAYOUT_ARCHITECTURE.md` | 全局布局 | 七大 Surface 关系 + 第一分钟体验 |
| `02_GALAXY_WORKSPACE_INTEGRATION.md` | Galaxy 融合 | 方案 A–D 比较 + 推荐（符合 DECISION_004） |
| `03_PANEL_VISUAL_LANGUAGE.md` | 面板语言 | 层级 / 深度 / 玻璃 / 边框 / glow / 动效 / 密度规则 |
| `04_ENTRY_AND_NAVIGATION.md` | 入口导航 | 功能发现重设计（Memory/Tasks/Goals/Search/Tools/Settings/Agent） |
| `05_SETTINGS_EVOLUTION.md` | Settings 演化 | Legacy → AI OS Configuration Center 演化路径 |
| `06_DESIGN_SYSTEM_NEXT_STAGE.md` | 设计系统下一阶段 | Color / Typography / Motion / Depth / Spatial / Component 补充 |
| `EXECUTIVE_SUMMARY.md` | 最终报告 | 10 节规定章节，Blueprint v1.0 总览 |

---

## 8. 本蓝图与既有架构的对齐声明

- **不违反 Golden State**：本蓝图 0 行代码，且所有方案均限定在「表现层 + 受控交互层」内；Galaxy 融合方案明确「永不可写状态 / 永不改 solar-system.js」。
- **不推翻 DESIGN.md**：本蓝图是 DESIGN.md 的上位细化（空间与架构层），视觉令牌值完全继承自 ui2.css / DESIGN.md。
- **不重建令牌体系**：严格遵守 Golden State「禁第二套 Token」—— 下一阶段只「激活死令牌 + 补齐缺失原语」。
- **尊重 IA 三支柱**：聊天非中央、三支柱共生、状态经 AppState 只读投影，本蓝图全部采纳。
- **承接 Final Convergence 审计**：F1（缺 `.zz-input`）、F8（Settings 硬编码色）等发现直接转化为 `03` / `05` / `06` 的设计要求。

> **🛑 STOP 声明**：本文件为纯设计原则文档，0 代码改动，待人工 Review 后进入 Visual Redesign 阶段。
