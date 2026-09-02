# DOCUMENT RESPONSIBILITY MATRIX

- **任务**：AI Operating System Governance Consolidation / Phase 3
- **日期**：2026-08-04
- **纪律**：Governance Single Source Rule（仅描述职责，禁重定义）

## 职责矩阵

| 文档 | 负责 | 不负责 | 被谁引用 | 不可替代性 |
|---|---|---|---|---|
| `XIAO6_GOLDEN_STATE_v1.0` | 运行时 / 权限 / 单一来源红线 | 业务逻辑 / UI | 全部文档 | 唯一最高权威，无替代 |
| `DECISION_001..006` | 不可逆架构决策记录 | 新功能设计 | Architecture / Boundary | 决策事实，不可被规范推翻 |
| `KNOWLEDGE_GOVERNANCE_RULES` | 知识治理规则 | 具体检索实现 | Knowledge Spec | 知识域规则源 |
| `ARCHITECTURE_MAP` | 模块 / 依赖地图 | 边界语义 | 全部实现 | 架构导航基准 |
| `INFORMATION_CLASSIFICATION_MODEL` | 信息分类与归属 | 存储实现 | Boundary / Knowledge | 分类唯一基准 |
| `MEMORY_BOUNDARY_SPECIFICATION` | Memory 边界 | 其他系统边界 | Boundary / AI Maintenance | Memory 边界唯一源 |
| `WORLD_MODEL_BOUNDARY_SPECIFICATION` | World Model 边界 | 其他系统边界 | Boundary / AI Maintenance | WM 边界唯一源 |
| `KNOWLEDGE_SYSTEM_BOUNDARY_SPECIFICATION` | Knowledge 边界 | 其他系统边界 | Boundary / AI Maintenance | KM 边界唯一源 |
| `FUTURE_TASK_QUEUE` | 任务队列与依赖 | 实现细节 | Task / AI Maintenance | 队列唯一源 |
| `AI_HANDOFF_PROTOCOL` | 交接协议 | 业务规范 | AI Maintenance | 交接唯一源 |
| `DOCUMENT_INVENTORY` | 文档清单 | 规范内容 | Documentation | 清单唯一源 |
| `AI_OPERATING_SYSTEM_GOVERNANCE`（新建） | 治理单一入口 + 阅读顺序 | 任何规范内容 | 新 AI Maintainer | 入口，非规范 |
| `GOVERNANCE_*.md`（本任务） | 治理整合 / 索引 / 关系 | 业务规范 | AI Maintenance | 治理层，非业务规范 |

## 关键原则
1. **入口文档只指向，不定义**：`AI_OPERATING_SYSTEM_GOVERNANCE.md` 不承载任何规范内容。
2. **规范内容以原始冻结文件为准**：本矩阵仅描述职责，不复制规范。
3. **不可方便替代**：不得因"更方便"用一份文档替代另一份的权威。
4. **新建治理文档定位**：本任务新增的 `GOVERNANCE_*.md` 与入口文档均属于"治理层（L-Governance）"，位于所有业务规范之上、Golden State 之下，仅做整合/索引，不创造业务权威。

## Single Source Rule 遵守声明
本文件仅**描述既有文档职责**；未重定义、未复制规范内容。
