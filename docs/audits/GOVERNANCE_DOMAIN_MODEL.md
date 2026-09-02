# GOVERNANCE DOMAIN MODEL

- **任务**：AI Operating System Governance Consolidation / Phase 1
- **日期**：2026-08-04
- **纪律**：Governance Single Source Rule（仅分类 / 引用，禁重定义）

## 治理领域（8 域）

### 1. Project Governance（项目治理）
- **范围**：项目状态、阶段、进展、启动的权威来源。
- **文档**：`PROJECT_STATUS.md`、`CURRENT_PHASE.md`、`CURRENT_STATE.md`、`DEVELOPMENT_PROGRESS.md`、`AI_BOOTSTRAP.md`、`README.md`
- **消费者**：AI Maintainer、未来 Agent、所有实现阶段。

### 2. Architecture Governance（架构治理）
- **范围**：系统架构、运行时、组件依赖、不可变红线。
- **文档**：`XIAO6_GOLDEN_STATE_v1.0.md`、`ARCHITECTURE_MAP.md`、`Xiao6-v2-核心架构规范.md`、`Xiao6-v2-架构升级设计文档.md`
- **消费者**：所有实现；被 Boundary / Knowledge 域引用。

### 3. Knowledge Governance（知识治理）
- **范围**：知识单元、元数据、权威、检索、排名、分类规范。
- **文档**：`KNOWLEDGE_GOVERNANCE_RULES.md`、`KNOWLEDGE_UNIT_SYSTEM`、`KNOWLEDGE_METADATA_SCHEMA`、`KNOWLEDGE_AUTHORITY_SYSTEM`、`KNOWLEDGE_CONTEXT_INTEGRATION`、`KNOWLEDGE_RANKING_MODEL`、`KNOWLEDGE_RETRIEVAL_STRATEGY`、`HYBRID_KNOWLEDGE_RETRIEVAL`、`INFORMATION_CLASSIFICATION_MODEL`
- **消费者**：Knowledge 系统实现、Context Assembly。

### 4. Boundary Governance（边界治理）
- **范围**：跨系统边界与信息的唯一归属。
- **文档**：`MEMORY_BOUNDARY_SPECIFICATION`、`WORLD_MODEL_BOUNDARY_SPECIFICATION`、`KNOWLEDGE_SYSTEM_BOUNDARY_SPECIFICATION`、`COGNITIVE_SYSTEM_CURRENT_STATE_AUDIT`、`COGNITIVE_AUTHORITY_MATRIX`、`COGNITIVE_INFORMATION_LIFECYCLE`、`COGNITIVE_CONTEXT_BLUEPRINT`、`CONTEXT_ASSEMBLY_GOVERNANCE`
- **消费者**：所有认知系统实现、AI Maintenance。

### 5. Decision Governance（决策治理）
- **范围**：不可逆架构决策的事实记录。
- **文档**：`DECISION_001..006`、`AI_CHANGE_REVIEW_TEMPLATE`
- **消费者**：架构变更评审、未来设计。

### 6. Documentation Governance（文档治理）
- **范围**：文档清单、迁移、贡献规范（治理"文档本身"，不定义业务规范）。
- **文档**：`DOCUMENT_INVENTORY.md`、`DOCUMENT_MIGRATION_REPORT.md`、`CONTRIBUTING.md`、本 Consolidation 全部 `GOVERNANCE_*.md`
- **消费者**：AI Maintainer、贡献者。

### 7. Task Governance（任务治理）
- **范围**：任务队列、依赖、交接协议。
- **文档**：`FUTURE_TASK_QUEUE.md`、`AI_HANDOFF_PROTOCOL.md`
- **消费者**：AI Maintainer、Future Roadmap。

### 8. AI Maintenance Governance（AI 维护治理）
- **范围**：AI 维护者如何阅读 / 验证 / 维护 / 审计治理（执行者，非新权威）。
- **文档**：`AI_ONBOARDING_TEST.md`、`CODE_REVIEW_CHECKLIST.md`、`GOVERNANCE_MAINTENANCE_PROTOCOL.md`（新建）、`AI_OPERATING_SYSTEM_GOVERNANCE.md`（新建入口）
- **消费者**：新 AI Maintainer、未来 Agent。

## 域间关系
- **Architecture > Knowledge / Boundary**：架构定义边界，边界约束知识系统。
- **Decision** 记录 Architecture 的不可逆选择（高于普通规范，低于 Golden State）。
- **Documentation** 治理"文档本身"，不定义业务规范内容。
- **AI Maintenance** 消费所有域，是治理的"执行者"而非"新权威"。

## Single Source Rule 遵守声明
本文件仅**分类既有文档**，未新增规范、未重定义任何内容。
