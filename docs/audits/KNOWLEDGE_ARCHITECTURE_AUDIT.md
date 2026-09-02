# Knowledge Architecture Audit — Xiao6 v1.3

> 知识体系现状审计 | Project Intelligence System v1.3 · Phase 1
> 任务等级：LONG RUNNING KNOWLEDGE INTELLIGENCE FOUNDATION TASK
> 执行模式：Audit → Analysis → Design → Documentation → Verify → Report
> 纪律：仅文档 / 治理 / 审计 / 知识结构设计；不修改业务代码、Runtime、Agent Loop、Memory 实现、Context Engine 实现、Event Contract、Policy；不引入 Vector DB / Embedding / Chroma / Milvus / FAISS；不进入 Phase 9 实现；不新增用户功能。

---

## 0. 审计范围与基准

- **审计对象**：`G:/xiao6` 全量权威文档（根目录 9 个 `.md` + `docs/` 六类目录，合计 84 个权威文档，见 `docs/DOCUMENT_INVENTORY.md` v1.2 复核版）。
- **权威基线**：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`（FROZEN，唯一最高权威锚点）。
- **关联主轴**：`docs/reference/PROJECT_KNOWLEDGE_GRAPH.md`（v1.2 实例化知识图）。
- **前置治理成果**：v1.1 文档生命周期 + v1.2 治理增强（Golden State / Drift Check / Change Review / Knowledge Graph / Onboarding Test / Consistency Report / Handoff Simulation）。
- **本审计目的**：在 v1.3 设计 Knowledge Unit / Metadata Schema / Authority System / Relation Graph / Retrieval / Ranking / Context Integration 之前，先客观刻画「当前知识从哪来、谁更权威、有什么问题、往哪改」。

> 本文件属 `docs/audits/`，类型 AUDIT。它是 v1.3 后续 12 个 Phase 的事实起点；不替代任何冻结基线，不修改 GOLDEN_STATE。

---

## 1. Knowledge Sources（知识来源盘点）

按 `DOCUMENT_INVENTORY.md` 的 84 文档，当前知识来源可归为 **8 类**。每类标注：载体、权威性质、当前角色。

### 1.1 根目录治理与状态（9 个，#1–9）

| 文档 | 角色 | 权威性质 |
|------|------|----------|
| `README.md` | 项目入口说明 | 描述性（ACTIVE） |
| `AI_BOOTSTRAP.md` | AI 启动引导 | 操作性（ACTIVE） |
| `AI_HANDOFF_PROTOCOL.md` | AI 交接/维护规范（v1.2 升级） | 约束性（ACTIVE，含永久禁止清单） |
| `ARCHITECTURE_MAP.md` | 系统结构图 | 描述性（ACTIVE，区别于知识图） |
| `CHANGELOG_AI.md` | AI 变更记录（含 Reason/Impact） | 记录性（ACTIVE） |
| `CURRENT_PHASE.md` | 当前阶段指针 | 状态性（ACTIVE） |
| `CURRENT_STATE.md` | 当前状态快照 | 状态性（ACTIVE） |
| `DEVELOPMENT_PROGRESS.md` | 开发进度 | 记录性（ACTIVE） |
| `PROJECT_STATUS.md` | 项目状态总览 | 状态性（ACTIVE） |

**性质**：项目「运行态」知识——描述此刻系统是什么、在哪、怎么接手。无显式权威等级字段，靠约定（CURRENT_*/AI_HANDOFF 优先）。

### 1.2 冻结基线（4 个，#10–13）

| 文档 | 角色 | 权威性质 |
|------|------|----------|
| `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` | 黄金基线（最高权威锚点） | **FROZEN，最高优先** |
| `docs/frozen/Phase8_Perception_Intelligence_Specification_v1.0.md` | Phase 8 感知智能规范 | FROZEN |
| `docs/frozen/Xiao6-v2-架构升级设计文档.md` | v2 架构升级（前瞻） | FROZEN 但**前瞻方向** |
| `docs/frozen/Xiao6-v2-核心架构规范.md` | v2 核心架构规范（前瞻） | FROZEN 但**前瞻方向** |

**性质**：系统「正确态」知识。GOLDEN_STATE 携带显式优先条款（"任何冲突以本基线优先"）；v2 两份虽在 frozen 目录，但内容为**未来方向**，与 v1.0 冻结核心存在语义张力（见 §3.4）。

### 1.3 架构决策（7 个，#14–20）

| 文档 | 角色 | 权威性质 |
|------|------|----------|
| `docs/decisions/AI_CHANGE_REVIEW_TEMPLATE.md` | 变更评审模板 | 约束性（ACTIVE） |
| `docs/decisions/DECISION_001_EVENTBUS.md` | EventBus 单一来源 | 决策性（ACTIVE） |
| `docs/decisions/DECISION_002_NO_SECOND_RUNTIME.md` | 无第二 Runtime | 决策性（ACTIVE） |
| `docs/decisions/DECISION_003_MEMORY_SINGLE_SOURCE.md` | Memory 单一来源 | 决策性（ACTIVE） |
| `docs/decisions/DECISION_004_GALAXY_BOUNDARY.md` | Galaxy 边界 | 决策性（ACTIVE） |
| `docs/decisions/DECISION_005_PERMISSION_POLICY.md` | Permission 唯一权限 | 决策性（ACTIVE） |
| `docs/decisions/DECISION_006_LANGCHAIN_POSITION.md` | LangChain 借鉴不引入 | 决策性（ACTIVE） |

**性质**：系统「为什么这样」知识。DECISION_001–006 是知识关联主轴的根节点（`PROJECT_KNOWLEDGE_GRAPH` 主轴 `Decision → ...`）。权威仅次于 GOLDEN_STATE。

### 1.4 审计与一致性报告（27 个，#21–47）

含 v1.2 新增（AI_HANDOFF_SIMULATION_REPORT / ARCHITECTURE_DRIFT_CHECK / GOVERNANCE_CONSISTENCY_REPORT / PROJECT_INTELLIGENCE_v1.2_FINAL_REPORT）及 23 个历史审计报告。

**性质**：系统「验证态」知识——派生性、描述性，权威低于其审计对象（基线/决策）。

### 1.5 设计文档（26 个，#48–73）

含 `01-overview`~`04-roadmap`、`DEV-PLAN`、`PLAN`、多个 v2 设计方案、`agent_runtime_design`、聊天窗口相关、代码质量/团队提升、小6 vs 白龙马对比等。

**性质**：系统「可能态」知识——前瞻/提案，未冻结，权威最低；但与 §1.2 的 v2 冻结文档概念重叠（见 §3.2）。

### 1.6 参考与自测（7 个，#74–80）

`AI_ONBOARDING_TEST`（32 题）、`CODE_REVIEW_CHECKLIST`、`CONTRIBUTING`、`PROJECT_KNOWLEDGE_GRAPH`、`README`（参考）、打包与部署说明、离线能力说明。

**性质**：系统「操作手册」知识——供 AI/人执行，描述性。v1.2 已将状态归一为 `ACTIVE`。

### 1.7 归档（2 个，#81–82）

`overview-2026-07-27-settings`、`overview`（早版总览）。

**性质**：系统「历史态」知识——已失效，但仍在磁盘，无显式失效链接（见 §3.5）。

### 1.8 文档根索引（2 个，#83–84）

`DOCUMENT_INVENTORY.md`（总索引）、`DOCUMENT_MIGRATION_REPORT.md`（迁移记录）。

**性质**：知识「地图」——索引性，权威取决于其指向的文档。

### 1.9 来源盘点结论

- **来源分散但可索引**：84 文档分 8 类，有总索引（`DOCUMENT_INVENTORY`），有结构图（`ARCHITECTURE_MAP`）与知识图（`PROJECT_KNOWLEDGE_GRAPH`）。
- **权威分层存在但隐式**：仅 GOLDEN_STATE 有显式优先条款；其余靠目录约定（frozen > decisions > design）与文档性质推断，无机器可读的权威等级。
- **粒度在文档级**：知识以「整篇文档」为最小单位，无法定位到文档内的原子事实（如某条红线、某事件数）。

---

## 2. Authority Ranking（当前权威排序，事实刻画）

> 本节**刻画现状**，不定义新体系。正式 Authority System（L100–L30）由 v1.3 Phase 4 设计。

### 2.1 现状事实排序（高 → 低）

| 层级 | 来源 | 现状依据 |
|------|------|----------|
| **T0 最高** | `XIAO6_GOLDEN_STATE_v1.0.md` | 显式条款「任何冲突以本基线优先」；FROZEN |
| **T1 高** | `DECISION_001`–`DECISION_006` | 架构决策根节点；红线源头；ACTIVE |
| **T1 高** | `AI_HANDOFF_PROTOCOL.md` 永久禁止清单 | 约束性；ACTIVE |
| **T2 中高** | `Phase8_Perception_Intelligence_Specification_v1.0.md` | FROZEN 规范 |
| **T2 中** | `ARCHITECTURE_DRIFT_CHECK.md` / `AI_CHANGE_REVIEW_TEMPLATE.md` | 检测/评审机制 |
| **T3 中** | 其余 audits / consistency / handoff 报告 | 派生描述 |
| **T3 中** | `PROJECT_KNOWLEDGE_GRAPH.md` / `ARCHITECTURE_MAP.md` | 关联/结构图 |
| **T4 低** | design 文档（`01-overview`~`04-roadmap`、v2 方案、聊天窗口等） | 前瞻/提案，未冻结 |
| **T4 低（前瞻张力）** | v2 冻结文档（`Xiao6-v2-*`） | FROZEN 目录但内容为未来方向 |
| **T5 最低** | `docs/archive/*` | 已失效 |

### 2.2 现状权威机制的三个缺陷

1. **仅 1 处显式优先条款**：除 GOLDEN_STATE 外，没有任何文档声明自己的权威等级或对其它文档的覆盖关系。排序是「靠约定推断」，非「靠元数据强制」。
2. **时间不保证权威**：v1.2 已记录「禁止时间优先」原则（新文档不自动覆盖旧基线），但现状无字段承载此规则，纯靠人工记忆。
3. **覆盖方向缺失**：当 design 文档（T4）的某条主张与 DECISION（T1）冲突时，现状**无自动裁决机制**——只能靠 AI 读 GOLDEN_STATE 时的人工判断。

---

## 3. Current Problems（当前问题，知识架构视角）

> 在 v1.2 §7「发现的问题」基础上，从**知识架构**（而非仅文档治理）视角扩展。每条标注：现象 / 风险 / 影响面。

### 3.1 权威隐式、不可机读（源自 §2.2）

- **现象**：84 文档中仅 GOLDEN_STATE 带显式优先条款；其余无 authority 字段。
- **风险**：AI 在上下文组装时无法按权威自动过滤/排序，易把低权威 design 提案当事实。
- **影响**：Context Engine（Phase 9）未来消费知识时缺权威维度。

### 3.2 来源重叠 / 无单一来源原则（Single Source Violation）

- **现象**：v2 概念在 **frozen 目录（#12–13）** 与 **design 目录（#54–73）** 多处出现，且彼此措辞不一；同一结论（如「能力目录升级」）在 DECISION_006 与多个 v2 设计稿中重复表述。
- **风险**：同一知识点多副本 → 修改一处置另一处过期 → 漂移。
- **影响**：违反 Single Source Principle；与 GOLDEN_STATE 红线「禁止第二 Runtime/Memory/EventBus」精神同源（知识也该单一权威源）。

### 3.3 孤儿规范 / 意图-实体错位（来自 v1.2 §7）

- **现象**：记忆与决策中引用的「九级参考体系」（constitution / IA / galaxy-interaction / design-system / interaction-system / experiential-prototype / implementation-readiness 等）在磁盘**不存在**，仅为设计意图。
- **风险**：审计/交接文档指向不存在的文件 → dangling reference；新 AI 按记忆找文件会落空。
- **影响**：权威引用链断裂；v1.3 须明确「引用不存在即不引用」或补建（补建不在本任务范围，见 §4）。

### 3.4 v2 前瞻 vs v1.0 冻结基线混淆（来自 v1.2 §7）

- **现象**：`Xiao6-v2-*` 两份在 frozen 目录，但内容为前瞻方向，与 GOLDEN_STATE 的 v1.0 冻结核心语义不同；design 目录另有大量 v2 提案稿。
- **风险**：AI 可能把 v2 前瞻当「当前正确态」，误改 v1.0 冻结核心（触发 Drift）。
- **影响**：高——直接威胁 GOLDEN_STATE 红线。

### 3.5 归档漂移 / 失效知识未断链

- **现象**：`docs/archive/*`（#81–82）为早版总览，已失效，但无显式「DEPRECATED / 被 X 替代」链接。
- **风险**：陈旧主张可能经索引或 AI 误读重新进入上下文。
- **影响**：中——污染知识正确性。

### 3.6 状态词表不一致（来自 v1.2 §7）

- **现象**：v1.2 发现 `REFERENCE` 不在 6 值图例，已归一为 `ACTIVE`；但更广的状态词表（ACTIVE / FROZEN / AUDIT / DESIGN / REFERENCE / ARCHIVE / DEPRECATED）仍无统一定义文档。
- **风险**：状态含义靠约定，新文档易用错状态标签。
- **影响**：低–中——影响审计脚本判定。

### 3.7 知识粒度在文档级，无原子单元

- **现象**：知识最小单位是整篇文档；无法定位「某条红线」「某事件数」「某决策理由」为独立可检索单元。
- **风险**：Context Engine 组装上下文时只能整篇塞入，浪费 token、引入噪声。
- **影响**：高——制约未来 Cognitive Context 质量（见 Phase 11）。

### 3.8 关系类型未形式化

- **现象**：`PROJECT_KNOWLEDGE_GRAPH.md` 是**实例化示例图**（6 个 DECISION 节点 + 叙述性关联），不是带类型的关系模式（如 `Decision → Architecture`、`Document → Decision` 等可查询关系）。
- **风险**：关系不可机读、不可遍历、不可校验「新模块是否挂到 Decision」。
- **影响**：中——知识图目前是文档，不是图数据库/模式。

### 3.9 无检索/排序/上下文集成策略

- **现象**：现状无「何时需要知识 → 如何检索 → 如何按权威过滤 → 如何组装进 LLM 上下文」的定义。Context Engine（Phase 9）尚未设计知识消费路径。
- **风险**：即使 v1.3 建好 KU/Metadata/Authority/Relation，仍无「被用起来」的通道说明。
- **影响**：高——知识架构若不接 Context Engine 即空中楼阁（本任务只设计不实现）。

---

## 4. Improvement Direction（改进方向，映射到 v1.3 后续 Phase）

> 本节给出方向性映射；每个方向由对应 Phase 产出正式规范文档。全部为**设计/规范**，不含实现。

| # | 问题（§3） | 改进方向 | v1.3 Phase | 交付物 |
|---|-----------|----------|-----------|--------|
| 1 | §3.7 粒度 | 建立原子知识单元 KU（id/title/type/authority/status/source/tags/relations/created/updated/content） | Phase 2 | `docs/design/KNOWLEDGE_UNIT_SYSTEM.md` |
| 2 | §3.6/§3.1 元数据 | 定义 KU 元数据 Schema（id/type/status/authority/source/domain/tags/relations/version/created/updated；status 继承 6 值） | Phase 3 | `docs/design/KNOWLEDGE_METADATA_SCHEMA.md` |
| 3 | §3.1/§3.2 权威 | 形式化 Authority System（L100/L90/L80/L70/L50/L30；高覆盖低，禁止时间优先） | Phase 4 | `docs/design/KNOWLEDGE_AUTHORITY_SYSTEM.md` |
| 4 | §3.8 关系 | 定义**类型化**关系图（Decision→Architecture→Module→Event→Test→Memory、Document→Decision）；与 v1.2 实例化图区分 | Phase 5 | `docs/reference/KNOWLEDGE_RELATION_GRAPH.md` |
| 5 | §3.9 检索 | 定义 Retrieval Strategy（User Request→Intent→Knowledge Need→Retrieve→Authority Filter→Context Assembly→LLM） | Phase 6 | `docs/design/KNOWLEDGE_RETRIEVAL_STRATEGY.md` |
| 6 | §3.9 混合 | 吸收 RAG/Graph RAG 思想定义 Hybrid Retrieval（Keyword+Semantic+Relationship），**不实现** | Phase 7 | `docs/design/HYBRID_KNOWLEDGE_RETRIEVAL.md` |
| 7 | §3.9 排序 | 定义 Ranking Model（Authority/Relevance/Freshness/Usage/Dependency），**不实现评分** | Phase 8 | `docs/design/KNOWLEDGE_RANKING_MODEL.md` |
| 8 | §3.9 集成 | 定义 Context Integration（Knowledge Layer 服务 Context Engine，不替代 Memory/World Model） | Phase 9 | `docs/design/KNOWLEDGE_CONTEXT_INTEGRATION.md` |
| 9 | §3.2/§3.5 治理 | 定义 Governance Rules（Create→Review→Classify→Assign Authority→Link Relations→Freeze；禁止无来源知识进核心上下文） | Phase 10 | `docs/frozen/KNOWLEDGE_GOVERNANCE_RULES.md` |
| 10 | §3.7/§3.9 未来 | 定义 Cognitive Context Blueprint（Knowledge/Memory/World Model/Context Engine/Reflection 关系），**不实现** | Phase 11 | `docs/design/COGNITIVE_CONTEXT_BLUEPRINT.md` |
| 11 | 全局校验 | 最终审计：检查重复 Memory 概念 / 第二知识源 / 违反 Single Source / 影响架构冻结 | Phase 12 | `docs/audits/KNOWLEDGE_INTELLIGENCE_REVIEW.md` |
| 12 | 收尾 | 最终报告：7 节（执行前状态/新增体系/RAG 吸收/Graph 吸收/未来 Cognitive Context 输入/风险/后续建议） | Phase 13 | `docs/audits/PROJECT_INTELLIGENCE_v1.3_FINAL_REPORT.md` |

### 4.1 与现有基线的边界（防 Drift）

- **不触碰** GOLDEN_STATE 的 6 条红线、Event Contract、Runtime、Memory、Policy、State 实现。
- **不替代** `PROJECT_KNOWLEDGE_GRAPH.md`（v1.2 实例化图）；v1.3 Phase 5 仅补充**类型化关系模式**，二者并存（实例化图 = 示例，关系模式 = 规范）。
- **不替代** `AI_HANDOFF_PROTOCOL.md`；v1.3 Phase 10 治理规则为**补充**，知识治理维度，不重复交接流程。
- **不引入** 任何数据库 / 向量检索 / Embedding；全部为 Markdown 规范 + 概念模型。

### 4.2 明确不在本任务范围

- 九级参考体系补建（§3.3）：仅记录为风险，不补建。
- v2 文档加边界声明（§3.4）：建议在 v1.3 收尾的库存更新中标注，但不修改 v2 文档正文。
- Phase 9 实现 / Knowledge Retrieval 实现 / 任何新功能：明确禁止。

---

## 5. 审计结论

当前 Xiao6 知识资产**治理完整、可索引、有最高权威锚点（GOLDEN_STATE）**，但存在三类结构性缺口：

1. **权威不可机读**（仅 1 处显式优先条款；无权威字段）。
2. **知识未原子化**（文档级粒度；关系未类型化；无单一来源原则强制）。
3. **无消费通道**（检索/排序/上下文集成策略缺失，知识尚未接 Context Engine）。

v1.3 的 12 个后续 Phase 正是针对这三类缺口做**设计层补全**，且严格不触碰冻结基线、不实现检索。本审计为后续 Phase 的事实基准。

> 审计完成。下一步：Phase 2 设计 Knowledge Unit System（任务 #182）。
