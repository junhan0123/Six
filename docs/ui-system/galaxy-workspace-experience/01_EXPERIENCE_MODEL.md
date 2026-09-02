# 01 · 体验模型（Experience Model）
### Xiao6 UI-3B · Galaxy × Workspace Experience Design v1.0

> **阶段**：UI-3B · Design Only（0 代码改动）
> **上游**：`00_CURRENT_STATE_AUDIT.md`（现状基线）· `01_GLOBAL_LAYOUT_ARCHITECTURE.md` · `02_GALAXY_WORKSPACE_INTEGRATION.md` · `GALAXY_INTERACTION_SPEC.md`（DECISION_004）
> **生成日期**：2026-08-09

---

## 0. 设计原则（重申，不可违背）

- **Galaxy = AI OS World Layer**（世界层）：非页面、非菜单、非第二应用。
- **Workspace = AI Operation Layer**（操作层）：非聊天窗口、非第二界面。
- **关系 = AI World + AI Operation = Xiao6 OS**：不是「A 页面 → B 页面」。

> 一切体验决策须服务于「用户始终觉得自己在一个 AI 空间里，而不是在多个 App 间跳转」。

---

## 1. 一秒看到 / 五秒理解 / 三十秒完成（体验时间轴）

### 1s · 看到（Arrival）
- **一屏之内同时看到**：暗化常驻的银河世界层（太阳明亮、轨道与星球可见）+ 前景玻璃操作台（HUD + Command Dock + 右栏上下文抽屉入口）。
- 没有任何模态遮挡整个 OS（消除 onboarding 遮蔽，见 Consolidation Sprint 复盘）。
- AI Presence 状态点在 HUD（如 `IDLE`）。
- **判定标准**：用户 1 秒内能说出「这是一台有世界的 AI 操作系统，不是聊天框」。

### 5s · 理解（Orientation）
- HUD 左侧品牌 + 状态点；右栏时钟 + 主题 + 上下文抽屉入口（`osContextToggle`）。
- 中央银河中**太阳（核心）明亮、轨道（Goal）与星球（能力域）可见**，暗示「状态机宇宙」。
- Command Dock 处于待命，hint 提示「输入指令，或 `Ctrl/Cmd+K` 召唤命令面板」。
- **判定标准**：用户 5 秒内能说清「Galaxy=世界，Dock=主入口，右栏=上下文，Panel=功能」。

### 30s · 完成（Act）
- 用户在 Command Dock 输入第一条指令 → 立即在工作台得到响应（银河不退场，仅保持暗化）。
- 或按 `Ctrl/Cmd+K` → Command Palette 搜索 Memory/Tasks/Goals/Tools/Settings → 功能发现成本 = 一次搜索。
- 或点击银河中一颗星球 → 经 `galaxy-experience` 聚焦 → 进入对应能力面板（DECISION_004 允许交互）。
- **判定标准**：用户 30 秒内能完成「下达指令 / 打开一个功能面板 / 聚焦一个能力域」之一。

---

## 2. 体验心智模型（用户脑中的一句话）

> **「小6是一个活着的 AI 宇宙。银河是它的世界（状态/目标/能力），我面前的操作台是我在其中的工作台，命令是我与它的统一语言，面板是我随时拉开看细节的抽屉。」**

为建立此心智，三条不可妥协的体验规则：

| 规则 | 含义 | 违反现状 |
|---|---|---|
| R1 连续空间 | 不切换「界面」，只调节世界层亮度/操作层透明度 | 现状 S1/S2 硬切换 |
| R2 银河常在 | 任何工作态银河都暗化在场，不消失 | 现状 S1 Workspace 遮盖 |
| R3 单入口 | Command Dock 永驻，是统一主入口 | 现状 S3/S7 双输入 |

---

## 3. 注意力模型（Attention Model，连续而非硬切）

替代现状的「home / chat-mode / universe-mode 三态硬切换」，建立**单一连续空间 + 两档注意力**：

| 态 | 触发 | 世界层（Galaxy） | 操作层（Workspace） | 用途 |
|---|---|---|---|---|
| **操作态 Operate** | 默认 / 输入焦点 / 面板展开 | 暗化 ~30% 亮度（氛围） | 全亮、玻璃悬浮 | 日常指令、执行、阅读 |
| **探索态 Explore** | 聚焦银河手势（点空白宇宙区/专用控件）/ 点击星球 | 提亮 ~80%（细节清晰） | 半透明退后（仍可交互） | 浏览状态世界、理解 AI 的宇宙 |

- 两态间**连续缓动**（`--ease-premium`），无硬切闪烁。
- 探索态**不是**独立视图（取消 `#universeView` 独占），而是对世界层的亮度调节 + 操作层退后。
- 实现方式（仅表现层）：前景玻璃元件透明度/模糊调节 + 世界层遮罩亮度调节 + `body` 加 `explore-mode` 类；**不碰 solar-system.js**。

---

## 4. 信息层级（避免过载的收口法则）

沿用 UI Consolidation 信息层级最终收口，应用到 Galaxy+Workspace 统一空间：

```
核心存在（AI Presence / 银河核心）> 操作（Command Dock）> 当前任务（Execution Timeline）
> 状态（HUD 状态点 / 右栏上下文）> 上下文（Panel 抽屉）> 辅助信息（Capability Matrix/Insight）
```

- **默认密度低**：首屏只亮核心存在 + 操作台 + 1 条状态点；Matrix/Insight 默认收起为右栏抽屉（Consolidation 已做）。
- **按需展开**：Panel 仅在用户主动打开时浮现，不抢占世界层。
- **银河不堆数据**：状态节点保持克制（占位中性色，Order 8 颜色映射属专项，UI-3B 不强制）；流星仅作主动推送轻提示。

---

## 5. 七问体验应答（面向用户的终态定义）

1. **默认看到什么** → Galaxy 暗化世界层 + 前景玻璃操作台（HUD/Dock/右栏入口），无模态遮挡。
2. **何时看到 Galaxy** → 永远在场；操作时暗化氛围，探索时提亮。不再需要「进入宇宙视图」。
3. **何时进入 Workspace** → 没有「进入」动作；启动即在工作台。输入指令即操作，银河不退场。
4. **Command Dock 是否永驻** → 是。贯穿 Home 与 Workspace（探索态下可半透明退后但仍可达）。
5. **Panel 如何浮现** → 经 PanelManager 的 OverlayManager 浮层，用户主动唤起（导航/快捷键/点星球），浮于世界层之上。
6. **AI Presence 在哪个层** → `--z-companion`(9999) 最高层，常驻所有态，独立于 Galaxy/Workspace。
7. **如何避免信息过载** → 单一连续空间 + 两档注意力 + 信息层级收口 + 默认低密度 + 按需展开 Panel。

---

## 6. 成功指标（可用于 UI-4 实现验收）

| 指标 | 现状 | 目标 |
|---|---|---|
| 启动即见银河（暗化） | 是（Home）但 Workspace 下否 | 所有工作态均可见 |
| 下达指令后银河是否消失 | 是（chat-mode 遮盖） | 否（仅暗化） |
| 看银河是否需离开工作 | 是（universe-mode 硬切） | 否（探索态连续调节） |
| Command Dock 永驻 | 否 | 是 |
| 单入口感知 | 割裂 | 统一 |
| 功能发现步数 | 多页面跳 | ≤1 次搜索/点击 |

## 7. Attention Budget Principle（注意力预算原则）

为把「AI OS 世界感」在长时间使用中守住（而非被功能堆叠淹没），UI-3B 冻结一套**注意力预算**约束，作为未来 UI-4 实现时的硬性资源上限——注意力是有限的屏幕认知资源，像内存一样需要预算。

| 焦点等级 | 同时允许数量 | 含义 | 典型承载 |
|---|---|---|---|
| **Primary Focus（主焦点）** | **1**（唯一） | 用户当前唯一应被引导注意的对象 | 激活的 Panel / 正在执行的任务 / 展开的对话焦点 |
| **Secondary Focus（次焦点）** | **≤ 2** | 可并行感知但不抢主焦点的对象 | Execution Timeline / 右栏上下文抽屉 / 至多两个唤起态 Panel |
| **Peripheral（边缘感知）** | **无限** | 始终在场但不消耗主动注意力的环境信号 | Galaxy 暗化世界层 / HUD 状态点 / AI Presence Companion / Dock 待命 |

### 7.1 约束细则
- **Primary 唯一**：任一时刻至多 1 个 Primary Focus。若有第二个对象想升为 Primary，必须先回收当前的 Primary（关闭或降至 Secondary）。
- **Secondary ≤ 2**：超过 2 个的对象不得进入 Secondary，必须降级为 Peripheral 或 Dormant（面板生命周期见 04 §13）。
- **Peripheral 不限额但有限制**：Peripheral 元素可以很多，但每个都必须是「存在即可、不需主动注意」的（如银河暗化、状态点色）——它们不得包含需阅读的文字块或需点击的密集控件，否则实质占用注意力，违反预算。
- **预算与态无关**：注意力预算在「操作态」与「探索态」下都生效；探索态提亮银河世界层，但银河仍处于 Peripheral（它不是 Primary/ Secondary，只是亮度更高）。

### 7.2 设计用途
- 作为 Panel Lifecycle（04 §13）的硬约束：Active（激活）面板消耗 Primary/Secondary 预算，Dormant 不消耗。
- 作为首启/回流第一屏信息密度的上限（03 §6/§7）：任何第一屏的「非 Peripheral 元素」总数不得超过 1 Primary + 2 Secondary。
- 作为未来任何新功能上第一屏的准入门槛：新功能若想占用 Primary/Secondary，必须先证明它回收了等量的既有预算。

> **🔒 FROZEN**：注意力预算是 UI-3B 冻结的体验红线之一，UI-4 及以后实现不得突破（1 Primary / ≤2 Secondary / 无限 Peripheral）。

> **🛑 STOP 声明**：本章为纯体验设计，0 代码改动，待 Review。
