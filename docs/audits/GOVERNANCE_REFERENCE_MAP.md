# GOVERNANCE REFERENCE MAP

- **任务**：AI Operating System Governance Consolidation / Phase 4
- **日期**：2026-08-04
- **纪律**：Governance Single Source Rule（仅绘制关系，禁复制）

## 引用网络（ASCII）

```
                                    Golden State (L0)
                                         │ 约束
                                         ├─ DECISION_001..006 (L1) ── 记录 Architecture 决策
                                         │
Architecture Spec (L3) ── ARCHITECTURE_MAP, v2-核心架构规范, v2-架构升级
                                         │ 定义边界
                                         ├─ Boundary Spec (L5)
                                         │     MEMORY / WORLD_MODEL / KNOWLEDGE_SYSTEM_BOUNDARY_SPEC
                                         │     COGNITIVE_AUTHORITY_MATRIX / INFORMATION_LIFECYCLE / CONTEXT_BLUEPRINT / CONTEXT_ASSEMBLY_GOVERNANCE
                                         │
Knowledge Governance Rules (L2) ── KNOWLEDGE_GOVERNANCE_RULES
                                         │ 约束
                                         ├─ Knowledge Spec (L4)
                                               KNOWLEDGE_UNIT / METADATA / AUTHORITY / CONTEXT_INTEGRATION
                                               RANKING / RETRIEVAL_STRATEGY / HYBRID_RETRIEVAL / INFORMATION_CLASSIFICATION_MODEL
                                         │
AI_HANDOFF_PROTOCOL ── FUTURE_TASK_QUEUE
                                         │
AI_OPERATING_SYSTEM_GOVERNANCE (入口, 新建)
     └─ 指向以上全部 + DOCUMENT_INVENTORY + 本任务 GOVERNANCE_*.md
```

## 无孤立治理规范（验证）
- 全部 L0–L6 文档均可经入口或彼此引用到达。
- `docs/DOCUMENT_INVENTORY.md` 提供完整路径索引（既有，引用不复制）。
- 本 Consolidation 新增 `GOVERNANCE_*.md` 均引用既有文件，**未创建独立权威**。

## 引用纪律
- 跨域引用一律指向**原始冻结文件**（如边界以 `*_BOUNDARY_SPECIFICATION.md` 为准）。
- 禁止"摘要式复制"——任何文档需要规范内容时，链接原文而非内联副本。
- 入口文档（Phase 5）是唯一的"索引根"，避免多入口分裂。

## Single Source Rule 遵守声明
本文件仅**绘制关系图**；未复制任何规范内容。
