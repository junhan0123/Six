# 01 · 全局布局架构（Global Layout Architecture）

> **文档类型**：统一视觉架构设计 · 布局层
> **阶段**：Unified Visual Architecture Design Phase v1.0 · 只设计，不实现 · **0 代码改动**
> **上游依据**：`00_DESIGN_PRINCIPLES.md` · `DESIGN.md` §5 · `INFORMATION_ARCHITECTURE.md` · `UI_SYSTEM_v1.0.md`
> **生成日期**：2026-08-09

---

## 0. 本章目标

定义小6 AI OS 的**全局空间架构**：七大 Surface（Galaxy / Workspace / Command Dock / Panel System / Settings / Overlay / AI Presence）之间的关系、层级、共存方式，以及**用户打开小6后的「第一分钟体验」**。

本章不规定令牌值（见 `06`），只规定**空间关系与结构**。

---

## 1. 七大 Surface 与它们的角色

| Surface | 角色 | 层级（z） | 状态来源 | 是否可写 |
|---|---|---|---|---|
| **Galaxy（银河世界层）** | 系统状态的活体可视化；常驻「世界」 | `--z-ground`(0) → `--z-stage`(2-4) | GalaxyState（只读投影） | ❌ 只读投影（DECISION_004） |
| **Workspace（工作操作层）** | 用户操作的主体 Surface；面板与内容承载 | `--z-content`(18) | AppState 只读投影 | ❌ 只读投影 |
| **Command Dock（统一输入层）** | 文本/语音/文件/截图/快捷 五合一输入 | `--z-content`(18) / bottom | 用户输入事件 | 仅发事件 |
| **Panel System（面板系统）** | 领域上下文（Memory/Tasks/Goals/…）的玻璃容器 | `--z-panel`(81) / drawer(95) | AppState 只读投影 | ❌ 只读投影 |
| **AI Presence（常驻意识层）** | Avatar 状态 / HUD 状态点 / Insight；AI 在场感 | `--z-hud`(20) / `--z-companion`(9999) | avatar-state.js 派生 | ❌ 纯投影 |
| **Command Palette（瞬时能力层）** | Ctrl/Cmd+K 唤起，搜索一切能力 | `--z-command`(90) | 命令注册表 | 仅发事件 |
| **Settings / Overlay（配置层）** | 系统配置中心；模态/遮罩 | `--z-overlay`(60-83) / `--z-modal-mask`(9000) | 配置事件 | 仅发事件 |

**核心关系**：Galaxy 是「世界」，Workspace 是「操作台」，二者共享同一空间语法、前后叠放、由**注意力模型**调节显隐（见 `02`）；Command Dock / Palette / AI Presence / Panel / Settings 是悬浮于这个世界之上的「控制台元件」。

---

## 2. 空间模型：单一连续空间（Single Continuous Space）

**决策**：小6采用**单一连续空间模型**，而非「多个切换界面」。

- **世界层（World Layer）** = Galaxy（常驻、暗化、可被聚焦）。
- **操作层（Operation Layer）** = Workspace + Command Dock + Panels + AI Presence（前景玻璃元件）。
- 两层**共存于同一屏幕**，通过共享的 depth / glass / grid / glow / motion 语法形成「一个空间」的连续感。
- 用户**不切换 App**，而是**调节对世界的注意力**（聚焦银河 ↔ 聚焦工作），详见 `02`。

这与 INFORMATION_ARCHITECTURE 的「三支柱共生」一致：左栏 rail（常驻能力）+ 命令面板（瞬时能力）+ 银河（状态可视化）共存，聊天仅为平级入口。

---

## 3. 全局布局结构（继承并强化 .os-shell）

继承 `DESIGN.md` §5 的 `.os-shell` 三区 grid，并在**空间语义**上强化：

```
┌──────────────────────────────────────────────────────────────┐
│  HUD (56px)  ··· 品牌 · AI Presence 状态点 · 时钟 · 工具簇      │  --z-hud(20)
├──────────┬───────────────────────────────────────┬───────────┤
│ LEFT RAIL│   WORKSPACE（操作层）                   │  RIGHT    │
│ (常驻能力 │   · 银河世界层（暗化常驻于其后）         │  PANEL /  │
│  chip-row)│   · 主舞台内容（Insight / 上下文）       │  CONTEXT  │
│ --z-rail │   · Command Dock（底部五合一输入）        │  --z-panel│
│ (5)      │                                        │ (81)      │
├──────────┴───────────────────────────────────────┴───────────┤
│  BOTTOM · Execution Timeline（时空条目，空闲折叠） + Command Dock│
└──────────────────────────────────────────────────────────────┘
   Galaxy 世界层：z 0 → 4（始终在 Workspace 之后，可被注意力机制提亮）
```

**与现状的差异（设计意图，非实现）**：
- 当前「主界面视觉普通」「Galaxy 割裂」的根因是：Galaxy 被当作「背景图」、Workspace 是「另一个界面」、二者语法不同。
- 本蓝图要求：**Galaxy 始终在场并共享语法**，Workspace 是其前景操作台——通过 `02` 的注意力模型与 `03` 的统一面板语言，使二者读起来是「一个 AI 空间」。

---

## 4. 第一分钟体验（First-Minute Experience）

设计「用户从启动到进入状态」的 60 秒旅程，**世界观在此刻形成**：

### 0–3s · 抵达（Arrival）
- 启动完成，用户**直接进入 AI 空间**：银河世界层已暗化常驻于后，HUD 就位，Command Dock 处于待命。
- 无「登录页 / 欢迎弹窗遮挡整个 OS」（消除 onboarding 遮蔽问题，参见 Consolidation Sprint 复盘）。
- AI Presence 显示「在线 / 待命」状态点（如 `IDLE`）。

### 3–10s ·  orient（Orientation）
- HUD 左侧品牌 + 核心状态点；右侧时钟 + 工具簇（含 Settings 入口）。
- 左栏 rail 以**图标 + 标签**呈现常驻能力（Memory / Tasks / Goals / Search / Tools / Agent / Settings），让用户一眼看到「这是一个有结构的 AI OS，不是聊天框」。
- 银河中**太阳（核心）明亮、轨道（Goal）与星球（能力域）可见**，暗示「这是一台有世界的状态机」。

### 10–30s · 行动（Act）
- 用户自然落在 **Command Dock**（底部五合一输入）——这是「主入口」，不是聊天框。
- 提示（非阻塞 micro-hint）：「输入指令，或按 `Ctrl/Cmd+K` 召唤命令面板」。
- 若用户按 `Ctrl/Cmd+K` → Command Palette 唤起，可搜索 Memory / Tasks / Goals / Tools / Settings / Agent 状态——**功能发现成本降至一次搜索**。

### 30–60s · 探索（Explore）
- 用户点击银河中一颗行星（能力域）→ 经 `galaxy-overlay` 展开该能力域面板（DECISION_004 允许交互）。
- 或点击左栏 rail 的 Memory → 右侧 Panel 滑出上下文。
- 此刻用户已建立心智：「**Galaxy 是状态世界，Workspace 是操作台，命令是统一入口，面板是上下文**」——AI OS 世界观成立。

---

## 5. Surface 共存规则（不冲突的叠放纪律）

1. **Galaxy 永远在最底（z 0–4）**，作为世界层；任何前景 Surface 不得覆盖银河的「存在感」（暗化但不消失）。
2. **前景玻璃元件（Panel / Dock / HUD / Palette）一律走 `--z-*` 令牌**，禁止裸数字（DESIGN.md §6.3 纪律）。
3. **Overlay / Modal / Settings 走 `--z-overlay`(60) → `--z-modal-mask`(9000)**，且必须 `inert` / `visibility` 管理，消除当前 29 个焦点陷阱（UI_SYSTEM v1.0 §1.9）。
4. **Companion（AI Presence 化身）最高层 `--z-companion`(9999)**，常驻但非阻塞。
5. **任何新浮层**引用既有 `--z-*` 语义档，不新增层级；提层须经 GUI 验收（DESIGN.md §6.3）。

---

## 6. 响应式下的空间收缩（继承 DESIGN.md §8）

| 断点 | 行为 | 空间语义保持 |
|---|---|---|
| `> 980px` | 三区 grid（`1fr 380px` / `56px 1fr 188px`） | 完整「控制甲板」 |
| `≤ 980px` | 单列：hud → core → side → bottom；侧栏限高 46vh | 银河退为氛围层，操作层单列重排；**空间语法不变** |

**设计纪律**：小屏不缩放字号（用固定 `--fs-*`），靠布局重排适配；银河在小屏降为「氛围背景」，不抢占操作层。

---

## 7. 与既有架构的对齐

- 继承 `.os-shell` 三区结构与 8px 间距基数（DESIGN.md §5），**不改布局代码**，只在空间语义上强化。
- 采纳 INFORMATION_ARCHITECTURE「聊天仅平级入口」—— 中央区不独占为聊天。
- 采纳 DECISION_004「Galaxy 只读投影」—— 世界层零可写状态。
- 承接 UI_SYSTEM v1.0 §1.9 焦点陷阱问题 —— §5 规则 3 要求 `inert` 治理。

> **🛑 STOP 声明**：本章为纯布局设计，0 代码改动，待 Review。
