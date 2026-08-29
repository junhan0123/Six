# AI OS Experience Sprint v2.0 — Unified Workspace（统一工作空间）

> 身份：Senior Frontend Architect + Senior Product Architect + AI Operating System Chief Engineer
> 任务等级：LONG RUNNING IMPLEMENTATION TASK（Audit → Plan → Implement → Verify → Document → STOP）
> 类型：UI 组织收口，**不是新增能力 / 不是新增页面 / 不是重构 Runtime**

## 1. Sprint Goal

把小6 AI OS **已有能力组织成统一工作空间（Unified Workspace）**：

- **统一入口** — 任意代码路径打开能力均经 `PanelManager.openCapability(id)` 单一分发器。
- **统一布局** — 六层信息架构（Primary / Secondary / Assistant / Context / Background / Overlay）清晰分类，不新增页面。
- **统一状态** — `WorkspaceState`（UI-only）持有当前工作区 / 聚焦面板 / 固定面板 / 最近面板 / 活动上下文引用。
- **统一生命周期** — `PanelManager` 统一 Open / Close / Hide / Restore / Focus / Pin / Unpin / Collapse / Expand。

## 2. 最高纪律

**禁止（红线，违反即回退）**
- 新增任何业务能力 / Tool / API / Runtime / Memory / Knowledge / Planner / Workflow / Electron / Mobile / Voice。
- 修改 Prompt 行为 / Agent 决策 / 数据库结构 / Permission / EventBus / Capability Registry / Product Constitution。
- 进入 Galaxy Runtime / Desktop Shell / Planner / Workflow / Perception / Automation。

**允许**
- UI 收口 / Workspace 重组 / 组件统一 / 状态同步 / 交互一致性 / 性能优化（仅 UI）/ 删除重复 UI 实现（保持行为一致）。
- 复用既有 `OverlayManager` / `FocusManager` / `KeyboardManager` / `CapabilityExposure`，仅做 v1 基础设施小扩展。

**权威文档（强制前置阅读，已通读）**
Golden State · Governance · 13 份 Product Constitution · Domain Model · AI OS Architecture · Execution Platform · Knowledge Platform · Capability Platform（Inventory/EntryMap/Duplicate）· AI OS Experience Sprint v1（7 份）。

## 3. Sprint 清单（#617–#626）

| # | Sprint | 交付 |
|---|--------|------|
| #617 | Workspace Audit | Workspace Inventory（本文档 01） |
| #618 | Workspace Layout | 六层信息架构（02） |
| #619 | Panel Governance | 统一生命周期管理器（03） |
| #620 | Workspace State | UI-only 工作区状态（04） |
| #621 | Navigation Consistency | 唯一推荐入口（05） |
| #622 | Context Persistence | 活动上下文统一恢复（06） |
| #623 | Workspace Performance | 仅 UI 性能（07） |
| #624 | Workspace UX Polish | Loading/Empty/Skeleton/Transition（08） |
| #625 | Regression | 回归验证（09） |
| #626 | Documentation | 本文档集 + 最终 5 项输出（99） |

## 4. Verify（10 项，详见 99_FINAL_REPORT）

Workspace 唯一状态 / Panel 唯一生命周期 / Navigation 唯一推荐入口 / Overlay 未回退 / Keyboard 未回退 / Companion 职责未扩张 / Capability Exposure 符合 T0–T4 / Architecture 未违反 / Product Constitution 未违反 / Golden State 未违反。

## 5. 最终输出 5 项

① 完成摘要 ② 修改文件统计 ③ Workspace 收益 ④ 风险 ⑤ 后续建议 —— 见 `99_FINAL_REPORT.md`。

---

**STOP 纪律：** 全部 Sprint 完成后 STOP，等人工 Review；禁止进入 Galaxy Runtime / Desktop Shell / Planner / Workflow / Electron / Voice / Mobile / Perception / Automation。
