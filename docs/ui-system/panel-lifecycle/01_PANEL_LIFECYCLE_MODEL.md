# Xiao6 Panel Lifecycle Model v1.0

> **Type:** Design + Audit Only — 零代码改动阶段
> **前置：** `00_PANEL_AUDIT.md`（事实基线）
> **Red Lines：** Panel 不成为第二 Runtime；Panel 仅是 Operation Layer Projection；不添加 lifecycle class、不修改 Panel 行为、不进入 Implementation。
> **Date:** 2026-08-09

---

## 0. 摘要

定义 Panel 的三态生命周期模型 **Dormant → Attention → Active**，并锚定两条不可逾越的红线：

1. **Panel = Operation Layer Projection**：Galaxy = World Layer（域真相），Panel = 其在 Operation Layer 的操作面投影。
2. **Panel 经 `activeContext` 引用 id 关联 Galaxy Node**：Galaxy Node 是域实体的可视化锚点，Panel 借引用 id 投影对应内容，不持有域真相。

模型明确：**三态是 UI 投影状态，不是新增的 DOMAIN/SYSTEM 事件**，不扩张事件契约（71 DOMAIN + 8 SYSTEM 冻结）。

---

## 1. 双图层空间模型（冻结基线）

| 图层 | 代表 | z 轴 | 职责 | 域真相归属 |
|------|------|------|------|-----------|
| **World Layer** | Galaxy | z0–4 | 域实体的空间化可视化（节点 = 知识/记忆/任务/工具/意图） | AppState / 后端（唯一真相） |
| **Operation Layer** | Workspace + Command Dock + Panels + HUD | z18+ | 对域真相的操作、观察、投影 | 投影自 World Layer，不持真相 |

Panel 位于 Operation Layer 顶部，是 **World Layer 域真相的"操作投影面"**，不是独立运行时。

---

## 2. 三态生命周期定义

```
        ┌─────────────┐  focus / open / 用户意图
        │   DORMANT   │ ───────────────────────────┐
        └─────────────┘                            │
               │ 触发 Attention 信号                ▼
               │ (proactive / 高 importance / 引用变化)   ┌──────────────┐
               ▼                                          │   ACTIVE     │
        ┌─────────────┐  click / 输入 / 停留              │ (用户操作中) │
        │  ATTENTION  │ ───────────────────────────────►  └──────────────┘
        └─────────────┘                                   │  close / blur
               │ 超时无交互 / 信号消退                     ▼
               └────────────────────────────────►  ┌──────────────┐
                                                   │  DORMANT     │
                                                   └──────────────┘
```

### 2.1 Dormant（休眠态）
- **定义：** Panel 存在（DOM 已就位或按需可建），但不抢占注意力，不弹、不闪、不改变 World Layer 焦点。
- **触发进入：** 初始状态；Active 关闭后；Attention 超时无交互后。
- **Operation Layer 表现：** 入口按钮可见；常驻 Projection（osMatrix/osInsight/osTimeline）仅显示折叠/空闲态；无 `data-presence` 脉动。
- **不持有：** 不订阅高成本轮询；不写域状态。
- **Galaxy 关联：** 无激活的 `activeContext` 引用，或引用指向 dormant 节点。

### 2.2 Attention（关注态）
- **定义：** Panel 发出"建议关注"信号，提示用户但**不强制打断**。
- **触发进入：** 来自 World Layer 的 `proactive(kind, content, importance)` 信号（importance = high/critical）；`activeContext` 引用变化；后台状态越过阈值。
- **Operation Layer 表现：** 轻微视觉提示（徽标 / 边框微光 / 角标计数），**不自动打开、不抢焦点、不自动弹层**。
- **轮询纪律：** 仅 `hud-context` 等背景层可在此态轻量轮询（20s 节流），变化才提示。
- **Galaxy 关联：** 信号携带 `knowledgeNodeId` / `memoryId` / `toolName` 等引用 id，Panel 预载引用但不展开。

### 2.3 Active（激活态）
- **定义：** 用户正在操作该 Panel（打开 / 聚焦 / 输入 / 拖拽）。
- **触发进入：** 用户 click 入口 / Command Dock 派发 / `PanelManager.open(id)` / `OverlayManager.open` 栈顶。
- **Operation Layer 表现：** 进入 OverlayManager 栈（overlayId）或激活 modeClass；FocusManager 焦点陷阱；z-index 由 `--z-dialog-mask`(82) 起统一管理；可 pin（pinnedPanelIds）常驻。
- **Galaxy 关联：** 写入 `activeContext.{goalId,conversationId,knowledgeNodeId,memoryId,toolName}` 引用 id（由 PanelManager.setActiveContext 唯一写入口），Galaxy 可据以高亮对应 Node（World Layer 单向反映 Operation Layer 当前焦点，**不反向控制**）。
- **不持有：** 域内数据仍走 AppState / 后端；Panel 仅投影。

---

## 3. 状态转换的唯一写入口

- **`PanelManager`** 是面板生命周期与入口分发的唯一真相源（REG 17 项）。
- `activeContext` 引用 id 的写入口 = `PanelManager.setActiveContext(...)`（经 WorkspaceState）。
- 栈 / ESC / 焦点 / z-index = **OverlayManager** 统一管理（外部浮层经 `track()` 交出治理权）。
- **禁止**：Panel 自行写 AppState、自建 ESC、自管 z-index（R3 逃逸即违反此纪律）。

---

## 4. 红线：Panel = Operation Layer Projection

```
┌──────────────────────────────────────────────────────────┐
│  World Layer (Galaxy)          域真相 · AppState · 后端    │
│      ● knowledge node                                     │
│      ● memory node            ← 引用 id (activeContext)   │
│      ● task/goal node             │                       │
│      ● tool node                  │ 投影（只读引用）        │
└──────────────────────────────────┼───────────────────────┘
                                    │  reference id only
┌──────────────────────────────────┼───────────────────────┐
│  Operation Layer (Panel)     投影面 · 不持真相 · 可操作    │
│      ┌────────────────────────────┴──────────────────┐   │
│      │ weather / briefing / agent-profile (zz-panel)  │   │
│      │ memory×2 / doc / map / hotspot / capabilities  │   │
│      │ settings / sysprompt / review / video / tasks  │   │
│      │ execution-monitor / osTimeline / osInsight /   │   │
│      │ osMatrix (非 REG surface)                      │   │
│      └───────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

- Panel **不持有**域状态：WorkspaceState 仅存 UI 状态 + `activeContext` 引用 id。
- Panel **不写**域真相：写经 AppState `applyEvent` → reducers（Single Source Rule）。
- Panel **不成为**第二 Runtime：无独立 EventBus / Memory / Permission / 状态权威。

---

## 5. Panel 与 Galaxy Node 的关联机制

**关联不是"绑定"，而是"引用投影"。**

1. **Galaxy Node = World Layer 的域实体锚点**（knowledge / memory / task / tool / intent）。
2. **Panel 经 `activeContext` 引用 id 投影该实体**：
   - 例：用户在 Galaxy 点击某个 knowledge node → 设置 `activeContext.knowledgeNodeId` → 对应 Panel（如 doc / capabilities / insight）聚焦并加载该节点内容。
   - 例：agent 执行某 tool → `execution-channel` 推送 `tool_start` → `execution-monitor`/`osTimeline` 投影工具进度（引用 `toolName`）。
3. **方向单向**：Galaxy 反映 Operation Layer 当前焦点（高亮 activeContext 所指 Node），**Galaxy 不反向强制打开/关闭 Panel**，避免 World Layer 越权控制 Operation Layer。
4. **无独立 Goal Panel**：Goal 状态经 `osTimeline` 投影（5 阶段 understand/plan/tool/execute/done 来自 AppState(intent/goal/agent) + ExecutionChannel）。

---

## 6. 模型对审计风险的约束

| 审计风险 | 本模型如何约束 |
|----------|----------------|
| R1 memory 双实现 | 两实现应投影同一 `memoryId` 引用，收敛为单一 Projection 契约 |
| R2 modeClass 全局副作用 | Active 态经 OverlayManager 栈而非 body class；modeClass 改为可选 overlay 模式 |
| R3 execution-monitor 逃逸 | Active 态必须 `OverlayManager.track` / `PanelManager.register`，取缔自挂载 |
| R4 共享宿主串态 | Dormant/Active 态显式切换 `activeContext`，宿主内容按引用 id 隔离 |

---

## 7. 结论

- 三态（Dormant/Attention/Active）是 **UI 投影状态**，不新增事件契约、不引入运行时。
- 关联机制 = `activeContext` 引用 id 投影，Galaxy Node 为 World Layer 锚点，单向反映。
- 本模型为后续 `02_PANEL_MIGRATION_PLAN.md` 的 Phase A/B/C 提供判定准则：任何迁移不得破坏"Panel = Operation Layer Projection"红线。

> **Design + Audit Only** —— 本文件不修改任何代码，不进入 Implementation。
