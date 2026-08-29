# Xiao6 Panel Migration Plan v1.0

> **Type:** Design + Audit Only — 规划文档（**非实现**）
> **前置：** `00_PANEL_AUDIT.md`（事实）、`01_PANEL_LIFECYCLE_MODEL.md`（三态模型）
> **Red Lines：** 不修改 CSS/HTML/JS/PanelManager/EventBus/AppState/Backend；不添加 lifecycle class；不进入 UI-4B-2B Implementation；Panel 仅 Operation Layer Projection。
> **Date:** 2026-08-09

---

## 0. 摘要

本文档给出 Panel 治理收敛的 **Phase A / B / C** 路线图与风险等级，并逐条回答 brief 要求的 **6 问**。本阶段为规划，**不执行任何代码改动**，完成后 STOP 等待 Review。

---

## 1. 必须回答的 6 问（brief 硬要求）

### Q1. 当前有多少 Panel？
- **受 PanelManager 管控：17 个**（REG 注册表，单一真相源）。
- **非 REG 的 Operation Layer surface：4 个** —— `execution-monitor`（自挂载逃逸）、`osMatrix` / `osInsight` / `osTimeline`（Workspace 常驻 Projection）。
- 合计 **21 个可见面板 surface**。
- **不计为 Panel：** Command Dock、Command Palette（入口）、hud-context（背景轮询）。
- **无独立 Goal Panel**（Goal 经 osTimeline 投影）。

### Q2. 哪些可优先迁移？
按"收口收益 / 风险比"排序：
1. **3 个共享 `zz-panel` 宿主**（weather / briefing / agent-profile）—— 统一生命周期与样式收口，收益高、风险中。
2. **12 个 overlayId-based 面板** —— 已走 OverlayManager 标准路径，主要工作是视觉令牌统一（`.zz-panel` + `--panel-*`）。
3. **`execution-monitor` 逃逸** —— 必须 `track` 进 OverlayManager（高优先，见 R3）。
4. **`osMatrix` / `osInsight` / `osTimeline`** —— 常驻 Projection，补 `activeContext` 引用投影与空闲折叠统一。

### Q3. 哪些风险最高？
| 风险 | 说明 | 等级 |
|------|------|------|
| **R1 memory 双实现** | JZMemory(memory.js) 与 ZZMemory(memory-panel.js) 并存，两套内存 UI，潜在状态/数据分歧 | 🔴 高 |
| **R2 modeClass 全局副作用** | sysmon/terminal 改 `body` class，影响全局样式，无集中回收保证 | 🔴 高 |
| **R3 execution-monitor 逃逸** | 自 appendChild 到 body，无 track/register，z-index/ESC/焦点失管 | 🔴 高 |
| R4 共享宿主串态 | weather/briefing/agent-profile 共用 `#zzPanelBody`，切换易互覆盖 | 🟡 中 |
| R5 重复 Modal/Toast/ESC | ~15 套 Panel、3 套 Toast、16+ ESC 监听 | 🟡 中 |
| R6 状态 observability 弱 | 无统一面板状态投影，红线难持续验证 | 🟢 低 |

### Q4. Panel 是否需要统一组件？
**是，且已有基础，需落地而非新建体系。**
- 现有 **`.zz-panel`（官方语义基准）+ `.glass-panel`（令牌化视觉基准）** 为单一来源；`--panel-*` 令牌已定义（radius 16px、title 18px Orbitron accent 等）。
- **不强制合并** `.os-panel` / `.settings-panel` / `.onb-card`（feature 专属保留）。
- 建议：所有 domain/execution/info panel 收敛到 `.zz-panel` 容器原语 + `--panel-*` 令牌；OverlayManager 已统一 z-index/ESC/焦点/Toast，逐步淘汰 15 套自绘 Modal 与 3 套 Toast。

### Q5. Panel 与 Galaxy Node 如何关联？
- **Galaxy = World Layer**（域真相锚点：knowledge / memory / task / tool / intent 节点）。
- **Panel = Operation Layer Projection**，经 `activeContext` 引用 id（goalId/conversationId/knowledgeNodeId/memoryId/toolName）投影对应域实体。
- **方向单向**：Galaxy 反映 Operation Layer 当前焦点（高亮 activeContext 所指 Node），不反向强制开关 Panel。
- 例：点 Galaxy knowledge node → 设 `activeContext.knowledgeNodeId` → doc/capabilities/insight 聚焦加载该节点；agent 执行 tool → `execution-monitor`/`osTimeline` 投影 `toolName` 进度。

### Q6. Panel 是否持有状态？
- **否。** 红线成立：WorkspaceState 仅持 UI 状态 + `activeContext` 引用 id；域真相在 AppState / 后端。
- `execution-channel` 内存缓存上限 50 为 ephemeral，非域权威。
- Panel 不写域状态（写经 AppState `applyEvent` → reducers，Single Source Rule）；不引入第二 Runtime / EventBus / Memory。

---

## 2. 迁移路线图（Phase A / B / C）

> 所有 Phase 均为**后续 Implementation 阶段的计划**，本审核阶段不执行。Phase 启动前须先 Design Review 通过。

### Phase A — 治理收口（Governance Convergence）· 高优先
**目标：** 消除三处高风险（R1/R2/R3），把面板纳入统一生命周期。
- A1. `execution-monitor` 改为经 `OverlayManager.track(...)` 登记，取缔自挂载（解 R3）。
- A2. `sysmon` / `terminal` 由 `modeClass`（body class）迁移为 overlay 模式（解 R2）。
- A3. 收敛 memory 双实现：统一为单一 Projection 契约，按 `memoryId` 引用投影（解 R1）。
- **验收：** 全站浮层经 OverlayManager 或 PanelManager.REG 管辖，无 body appendChild 逃逸；无 body class 面板模式。

### Phase B — 视觉与令牌统一（Visual Token Unification）· 中优先
**目标：** 落地 `--panel-*` 令牌 + `.zz-panel` 容器原语，淘汰重复实现。
- B1. 12 个 overlayId 面板迁移到 `.zz-panel` + `--panel-*`；保留 `.settings-panel`/`.onb-card` feature 专属。
- B2. 3 个共享 `zz-panel` 宿主按 `activeContext` 引用隔离内容（解 R4）。
- B3. 淘汰 3 套 Toast → `#zzToastRoot`；收敛 16+ ESC 到 OverlayManager 中央 ESC（解 R5）。
- **验收：** 全站面板视觉语言一致；CSS Lint 无新增 class / 第二套 class / 内联 style（遵循 DESIGN.md §7 Don'ts）。

### Phase C — 生命周期投影与 Observability（Lifecycle Projection）· 低优先
**目标：** 把三态模型落地为可观测的 UI 投影状态，强化红线守护。
- C1. 给各 Panel 接入 `activeContext` 引用投影（Dormant/Attention/Active 三态驱动）。
- C2. 常驻 Projection（osMatrix/osInsight/osTimeline）统一空闲折叠与 Attention 信号纪律。
- C3. 补统一面板状态投影（解 R6），使"Panel 不持域状态"可验证。
- **验收：** 三态切换无域状态写；Galaxy 单向反映 activeContext；回归 P8 AI Presence 20/0、CSS 平衡、9 主题一致。

---

## 3. 风险等级总表

| Phase | 任务 | 风险 | 阻断项 |
|-------|------|------|--------|
| A1 | execution-monitor track 化 | 中（需保持现有投影行为） | 不得改 execution-channel 数据流 |
| A2 | modeClass → overlay | 高（全局样式回归） | 须回归全站主题 |
| A3 | memory 双实现收敛 | 高（数据/状态分歧） | 须确认无功能回退 |
| B1–B3 | 视觉令牌统一 | 中 | 遵循 DESIGN.md Don'ts |
| C1–C3 | 三态投影 | 低 | 不新增事件契约 |

---

## 4. STOP 与下一步

- 本阶段（UI-4B-2B-0）= **Design + Audit Only**，已交付 `00/01/02` 三份文档，**零代码改动**。
- **不进入 UI-4B-2B Implementation**，不执行 Phase A/B/C。
- **不 git commit**。
- 等待 Review 决策：是否批准进入 Implementation，以及 Phase 优先级（建议 A 先行）。

---

## 5. 交付物清单

| 文件 | 内容 |
|------|------|
| `docs/ui-system/panel-lifecycle/00_PANEL_AUDIT.md` | 17 REG + 4 非 REG surface 全量盘点、分类、视觉语言、风险、状态红线核查 |
| `docs/ui-system/panel-lifecycle/01_PANEL_LIFECYCLE_MODEL.md` | Dormant/Attention/Active 三态模型、Panel=Projection 红线、Galaxy Node 关联机制 |
| `docs/ui-system/panel-lifecycle/02_PANEL_MIGRATION_PLAN.md` | 6 问答 + Phase A/B/C 路线图 + 风险等级 + STOP |

> **Design + Audit Only — 已完成，STOP 等待 Review。**
