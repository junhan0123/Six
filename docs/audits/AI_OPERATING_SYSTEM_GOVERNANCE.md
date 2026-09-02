# AI OPERATING SYSTEM GOVERNANCE

> **单一治理入口（Single Governance Entry）**
> - 任务：AI Operating System Governance Consolidation / Phase 5
> - 日期：2026-08-04
> - 性质：**本文件不是新规范、不是第二 Constitution、不是第二 Golden State。** 它仅是小6 AI OS 全部已冻结治理的**唯一入口 + 阅读顺序索引**。

## 0. 给新 AI Maintainer / 未来 Agent 的三句话
1. **最高权威** = `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`（Golden State）。任何冲突以它为准。
2. **不要修改任何已冻结治理文档**，除非走 `GOVERNANCE_CHANGE_CONTROL.md` 流程。
3. **本文件只指向，不定义。** 需要规范内容时，去读被指向的原始文件。

## 1. 推荐阅读顺序（Recommended Reading Order）
按以下顺序阅读，约 30 分钟建立完整治理心智模型：

1. `AI_OPERATING_SYSTEM_GOVERNANCE.md`（本文件，入口与地图）
2. `GOVERNANCE_AUTHORITY_HIERARCHY.md` — 谁压谁（L0 Golden State → L6 实现参考）
3. `GOVERNANCE_DOMAIN_MODEL.md` — 8 个治理域
4. `GOVERNANCE_REFERENCE_MAP.md` — 文档引用网络（无孤立）
5. `DOCUMENT_RESPONSIBILITY_MATRIX.md` — 每文档负责 / 不负责
6. **核心规范（按权威层级 L0→L5）**：
   - L0 `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`
   - L1 `docs/decisions/DECISION_001..006` + `AI_CHANGE_REVIEW_TEMPLATE`
   - L2 `docs/frozen/KNOWLEDGE_GOVERNANCE_RULES.md`
   - L3 `ARCHITECTURE_MAP.md` + `docs/frozen/Xiao6-v2-核心架构规范.md` + `docs/frozen/Xiao6-v2-架构升级设计文档.md`
   - L4 `docs/design/KNOWLEDGE_*.md` + `INFORMATION_CLASSIFICATION_MODEL.md`
   - L5 `docs/design/*_BOUNDARY_SPECIFICATION.md` + `COGNITIVE_AUTHORITY_MATRIX.md` + `COGNITIVE_INFORMATION_LIFECYCLE.md` + `COGNITIVE_CONTEXT_BLUEPRINT.md` + `CONTEXT_ASSEMBLY_GOVERNANCE.md`
   - 6b. `docs/design/frozen/` 下 8 份 **Design Canon**（设计解释层 / 索引参考，**非规范、非权威层**；详情见 `DESIGN_CONFLICT_REGISTER.md` 与 `AI_DESIGN_CONTEXT.md`）
7. `GOVERNANCE_LIFECYCLE.md` — 文档生老病死
8. `GOVERNANCE_CHANGE_CONTROL.md` — 如何安全变更
9. `GOVERNANCE_MAINTENANCE_PROTOCOL.md` — AI 维护者职责
10. `GOVERNANCE_FUTURE_ROADMAP.md` — v1.5/v1.6/v1.7 如何进入
11. `GOVERNANCE_INTEGRITY_AUDIT.md` — 本整合自检（无第二治理）
12. `GOVERNANCE_HANDOFF_SIMULATION.md` — 新维护者阅读模拟

## 2. 治理文档总索引（按域，一句话职责）
- **Project**：`PROJECT_STATUS` / `CURRENT_PHASE` / `CURRENT_STATE` / `DEVELOPMENT_PROGRESS` / `AI_BOOTSTRAP` / `README`
- **Architecture**：`XIAO6_GOLDEN_STATE_v1.0` / `ARCHITECTURE_MAP` / `Xiao6-v2-核心架构规范` / `Xiao6-v2-架构升级设计文档`
- **Knowledge**：`KNOWLEDGE_GOVERNANCE_RULES` / `KNOWLEDGE_UNIT_SYSTEM` / `KNOWLEDGE_METADATA_SCHEMA` / `KNOWLEDGE_AUTHORITY_SYSTEM` / `KNOWLEDGE_CONTEXT_INTEGRATION` / `KNOWLEDGE_RANKING_MODEL` / `KNOWLEDGE_RETRIEVAL_STRATEGY` / `HYBRID_KNOWLEDGE_RETRIEVAL` / `INFORMATION_CLASSIFICATION_MODEL`
- **Boundary**：`MEMORY_BOUNDARY_SPECIFICATION` / `WORLD_MODEL_BOUNDARY_SPECIFICATION` / `KNOWLEDGE_SYSTEM_BOUNDARY_SPECIFICATION` / `COGNITIVE_SYSTEM_CURRENT_STATE_AUDIT` / `COGNITIVE_AUTHORITY_MATRIX` / `COGNITIVE_INFORMATION_LIFECYCLE` / `COGNITIVE_CONTEXT_BLUEPRINT` / `CONTEXT_ASSEMBLY_GOVERNANCE`
- **Decision**：`DECISION_001..006` / `AI_CHANGE_REVIEW_TEMPLATE`
- **Documentation**：`DOCUMENT_INVENTORY` / `DOCUMENT_MIGRATION_REPORT` / `CONTRIBUTING`
- **Task**：`FUTURE_TASK_QUEUE` / `AI_HANDOFF_PROTOCOL`
- **AI Maintenance**：`AI_ONBOARDING_TEST` / `CODE_REVIEW_CHECKLIST` / `GOVERNANCE_MAINTENANCE_PROTOCOL`（本任务）
- **整合层（本任务新增，索引/关系，非规范）**：`GOVERNANCE_BASELINE_AUDIT` / `GOVERNANCE_DOMAIN_MODEL` / `GOVERNANCE_AUTHORITY_HIERARCHY` / `DOCUMENT_RESPONSIBILITY_MATRIX` / `GOVERNANCE_REFERENCE_MAP` / `GOVERNANCE_LIFECYCLE` / `GOVERNANCE_CHANGE_CONTROL` / `GOVERNANCE_MAINTENANCE_PROTOCOL` / `GOVERNANCE_FUTURE_ROADMAP` / `GOVERNANCE_INTEGRITY_AUDIT` / `GOVERNANCE_HANDOFF_SIMULATION` / 本文件

## 3. Single Source Rule（铁律）
- 任何已有冻结规范：**只引用 / 统一入口 / 建立索引 / 建立关系**。
- **禁止**：重定义、复制规范内容、产生第二份定义、第二 Constitution、第二 Golden State、第二 Authority。
- 本整合新增的 `GOVERNANCE_*.md` 与本文档均属于"治理层（整合/索引）"，不创造业务权威。

## 4. 红线（来自 Golden State，不可违反）
- 无第二 Runtime / Memory / EventBus / Permission。
- Vision 绝不控制；PolicyEngine 唯一权限；AppState 唯一写入口。
- 任何冲突以 `GOLDEN_STATE` 优先。

## 5. 当前状态
- 仓库最高权威：**Golden State（L0）**。设计层 Constitution / Redesign 意图已以 **Design Canon（设计解释层，8 份，落盘于 `docs/design/frozen/`）** 形式落盘；其定位为**解释/索引层，非权威层**，不覆盖 Golden State / Decision / Governance。
- 审计基线（Stage A 后）：**PROBLEMS:0 / WARNS:18**。

## 6. 终态
本整合在终报（`AI_OS_GOVERNANCE_CONSOLIDATION_REPORT.md`）完成后，全部 `GOVERNANCE_*.md` 进入 **Frozen** 态。此后一切治理入口均经本文件。
