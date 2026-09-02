# 04 · 功能入口与导航重设计（Entry & Navigation）

> **文档类型**：统一视觉架构设计 · 导航层
> **阶段**：Unified Visual Architecture Design Phase v1.0 · 只设计，不实现 · **0 代码改动**
> **上游依据**：`00_DESIGN_PRINCIPLES.md` · `INFORMATION_ARCHITECTURE.md`（三支柱共生）· `DESIGN.md` §4.5/§9 · `UI_SYSTEM_v1.0.md`
> **生成日期**：2026-08-09

---

## 0. 问题陈述

用户 7 大问题之四：「功能入口分散」。当前 Memory / Tasks / Goals / Search / Tools / Settings / Agent 状态分散在各处，发现成本高，且「聊天框」容易成为唯一被注意的入口，强化「这是聊天软件」的误读。

本章基于 **INFORMATION_ARCHITECTURE 三支柱共生模型**重设计入口与发现机制，使「这是一个 AI OS」的心智自然成立。

---

## 1. 三支柱导航模型（已冻结，采纳）

| 支柱 | 角色 | 交互 | 适合场景 |
|---|---|---|---|
| **左栏 rail（chip-row）** | 常驻能力入口 | 点击 → 侧栏/面板滑出 | 高频、需常驻的功能 |
| **命令面板（Ctrl/Cmd+K）** | 瞬时能力 | 唤起 → 模糊搜索一切 | 一次性、深度、跨域操作 |
| **银河（Galaxy）** | 状态可视化 | 点击行星 → 能力面板（经 overlay） | 理解系统状态、探索能力域 |

**关键澄清（INFORMATION_ARCHITECTURE §2）**：聊天**仅是左栏/面板平级入口之一**，不独占中央区。中央是「你的 AI 空间」，不是聊天框。

---

## 2. 功能发现矩阵（用户如何找到每一项）

| 功能 | 常驻入口（rail） | 命令面板 | 银河 | 上下文面板 |
|---|---|---|---|---|
| **Memory（记忆）** | 🧠 chip | `记忆` / `memory` | 记忆环（Memory Ring） | 右侧 Memory 面板 |
| **Tasks（任务）** | ✅ chip | `任务` / `task` | — | Execution Timeline |
| **Goals（目标）** | 🎯 chip | `目标` / `goal` | **轨道（Orbit）** | Goal 面板 |
| **Search（搜索）** | 🔍 chip | `搜索` / `search` | — | 搜索结果面板 |
| **Tools（工具）** | 🛠 chip | `工具` / `tool` | **星球（能力域）** | 能力域面板 |
| **Settings（设置）** | ⚙ chip（HUD 工具簇） | `设置` / `settings` | — | Configuration Center |
| **Agent 状态** | AI Presence 状态点（HUD） | `状态` / `status` | **太阳（核心）** | Insight 面板 |

**设计意图**：每一项功能都**至少两条发现路径**（常驻 + 搜索），核心状态项还有银河可视化路径。发现成本 = 一次点击或一次搜索。

---

## 3. 左栏 rail 重设计（常驻能力，统一语言）

当前左栏是 chip-row（如 🧠 画像）。本章统一为**「能力导航 rail」**：

- **结构**：图标 + 标签（收起时仅图标，hover/展开显示标签），符合 32×32 触控目标（DESIGN.md §8）。
- **分组**（视觉分组，非菜单嵌套）：
  - 认知：`Memory` · `Goals` · `Tasks`
  - 操作：`Search` · `Tools`
  - 系统：`Settings` · `Agent 状态`（或并入 AI Presence）
- **交互**：点击 → 对应 Panel 从 `--z-panel`(81) 滑出；空态友好提示（INTERACTION_SYSTEM_SPEC「侧栏滑出」模式）。
- **视觉**：chip 走统一 `.zz-*` / 玻璃语法，消除当前 chip 与系统面板不同调的问题（Final Convergence §6-2）。

> 不新增功能，只把**已有能力**组织成清晰的「AI OS 导航」。

---

## 4. 命令面板（Command Palette）重设计

- **唤起**：`Ctrl/Cmd+K`（INTERACTION_SYSTEM_SPEC 已冻结模式）。
- **能力**：模糊搜索跨 Memory / Tasks / Goals / Search / Tools / Settings / Agent 状态；可直达、可触发动作。
- **角色**：本蓝图定义其为**「统一能力目录」**——用户无需记住入口位置，一次搜索即达。这是降低「入口分散」感知的核心机制。
- **视觉**：走 `--z-command`(90) + 玻璃卡片 + `--font-mono` 结果元信息（tabular-nums），复用 `03` 面板语言。

---

## 5. 银河作为导航（状态即入口）

依据 DECISION_004 允许交互 + `02` 的双层空间模型：
- 点击**行星（能力域）** → `galaxy-overlay` 展开该 Tools/能力域面板。
- 点击**轨道（Goal）** → Goal 面板。
- 点击**太阳（核心）** → Agent 状态 / Insight。
- 点击**记忆环** → Memory 面板。
- 这使得「浏览状态」本身就成为一种**导航方式**，强化 AI OS 世界观。

---

## 6. 主入口心智：Command Dock 不是聊天框

- 底部 **Command Dock** 是五合一统一输入（文本/语音/文件/截图/快捷），是「**主行动入口**」，不是「聊天输入框」。
- 明示 micro-hint：「输入指令，或 `Ctrl/Cmd+K` 召唤命令面板」——引导用户把小6当作「操作系统」而非「聊天软件」。
- 聊天窗口默认收起为底部细触发条（INFORMATION_ARCHITECTURE §2 正确态），不抢占中央。

---

## 7. 导航设计纪律（红线）

- ❌ 不新建 Runtime / EventBus / 通信协议（Golden State）。
- ❌ 不改 AppState 子树（状态经只读投影）。
- ❌ 不新增功能，只**重组已有能力的入口呈现**。
- ✅ 所有新入口元件走 `--z-*` + `zz-` 前缀 + 面板语言（`03`）。
- ✅ 键盘可达：`focus-visible` 环 + 命令面板快捷键（WCAG AA）。

---

## 8. 对齐声明

- 严格采纳 INFORMATION_ARCHITECTURE「三支柱共生 + 聊天平级」—— 不把聊天提为中央。
- 承接 Final Convergence §6-2（rail/面板不同调）→ §3 统一语言要求。
- 与 `01` 第一分钟体验（10–30s 落到 Command Dock + 命令面板）一致。

> **🛑 STOP 声明**：本章为纯导航设计，0 代码改动，待 Review。
