# GOVERNANCE AUTHORITY HIERARCHY

- **任务**：AI Operating System Governance Consolidation / Phase 2
- **日期**：2026-08-04
- **纪律**：Governance Single Source Rule（仅索引 / 引用，禁重定义）

## 权威层级（高 → 低）

| 层级 | 名称 | 文档 | 说明 |
|---|---|---|---|
| **L0** | Golden State | `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` | 绝对最高权威。运行时 / 权限 / 单一来源红线。任何冲突以 Golden State 优先。 |
| **L1** | Decision Records | `docs/decisions/DECISION_001..006` | 不可逆架构决策。高于普通规范，低于 Golden State。 |
| **L2** | Governance Rules | `docs/frozen/KNOWLEDGE_GOVERNANCE_RULES.md` | 知识治理规则，约束 Knowledge 域规范。 |
| **L3** | Architecture Spec | `ARCHITECTURE_MAP.md`、`docs/frozen/Xiao6-v2-*.md` | 系统架构与组件规范。 |
| **L4** | Knowledge Spec | `docs/design/KNOWLEDGE_*.md`、`INFORMATION_CLASSIFICATION_MODEL.md` | 知识系统与信息分类规范。 |
| **L5** | Boundary Spec | `docs/design/*_BOUNDARY_SPECIFICATION.md`、`COGNITIVE_*.md` | 跨系统边界与唯一归属规范。 |
| **L6** | Implementation Reference | `docs/audits/*`、`docs/reference/*`、tests | 实现参考 / 验证报告 / 图谱。最低权威，可随实现更新。 |
| 解释层（非权威） | Design Canon | `docs/design/frozen/`（8 份） | 设计解释/索引层；不覆盖 Golden State；不计入 L0–L6 |

## 冲突解决规则
1. 任一冲突，**高层级覆盖低层级**。
2. 同层级冲突 → 以"更新且已 Frozen"者为准；仍歧义 → 升级至 Golden State（L0）。
3. **Golden State 不可被任何下游文档推翻。**
4. 禁止任何文档声称"高于 Golden State"或"替代 Golden State"。

## 红线（来自 Golden State，不可违反，详见原文）
- 无第二 Runtime / Memory / EventBus / Permission。
- Vision 绝不控制。
- PolicyEngine 唯一权限；AppState 唯一写入口。
- 任何冲突以 `GOLDEN_STATE` 优先。

## 重要澄清（2026-08-04 核实，2026-08-04 修订）
设计层文档已于 **2026-08-04** 以 **「设计解释层（Design Interpretation Layer）」** 定位落盘于 `docs/design/frozen/`（共 8 份：PRODUCT_CONSTITUTION / AI_OS_DESIGN_PRINCIPLES / INFORMATION_ARCHITECTURE / GALAXY_INTERACTION_SPEC / INTERACTION_SYSTEM_SPEC / DESIGN_SYSTEM_SPEC / EXPERIENTIAL_PROTOTYPE_SPEC / DOMAIN_MODEL）。
**关键定位**：Design Canon **不属于本权威层级（L0–L6）**，是独立的解释/索引层；每份均显式声明「**不覆盖、不替代** Golden State / Decision / Governance」。本仓库**实际最高权威仍为 Golden State（L0）**，Design Canon 不改变任何权威判定。
若未来 Design Canon 被提升为正式权威层，须经 Golden State 冲突校验并按 `GOVERNANCE_CHANGE_CONTROL.md` 修订本文件后重新冻结。

## Single Source Rule 遵守声明
本层级为"索引与引用"；Golden State 原文在 `docs/frozen/`，未重定义任何规范内容。
