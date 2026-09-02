# Knowledge Retrieval Strategy — Xiao6 v1.3

> 知识检索策略 | Project Intelligence System v1.3 · Phase 6
> 任务等级：LONG RUNNING KNOWLEDGE INTELLIGENCE FOUNDATION TASK
> 纪律：仅设计/规范检索**流程**；不实现检索、不引入向量库/Embedding、不修改 Context Engine。

---

## 1. 目的

Phase 1 §3.9：当前无「何时需要知识 → 如何检索 → 如何按权威过滤 → 如何组装进 LLM 上下文」的定义。本 Phase 设计**检索策略管道**——一条端到端的概念流程，描述知识如何被「需要、找到、过滤、组装」。

> ⚠️ 本策略是**流程规范**，不是代码。v1.3 不实现检索（禁止清单明确）。Phase 9 Context Integration 将消费本管道的概念，但本 Phase 只定义「应该怎么做」。

---

## 2. 检索管道（7 阶段）

```
[1] User Request
        ↓
[2] Intent Analysis        （理解用户意图/任务类型）
        ↓
[3] Knowledge Need Detection （判断是否需要知识、需要哪类）
        ↓
[4] Retrieval             （按 domain/tags/type 检索候选 KU）
        ↓
[5] Authority Filtering   （按 L100–L30 过滤/降权）
        ↓
[6] Context Assembly      （去冲突 + 排序 + 截断，组装上下文块）
        ↓
[7] LLM                   （带知识上下文推理）
```

---

## 3. 各阶段规范

### 3.1 User Request
- 输入：用户自然语言请求（或 Agent 内部任务）。
- 不改动：与现有聊天/命令面板入口一致。

### 3.2 Intent Analysis
- 目标：归类请求到任务类型（如「改代码」「查架构」「问状态」「决策咨询」）。
- 输出：`intent` 标签，用于驱动后续知识需求检测。
- 注意：本阶段**不消费知识**，仅做路由。

### 3.3 Knowledge Need Detection
- 判定：是否真需要项目知识？
  - 纯闲聊 / 通用知识 → 跳过检索，直连 LLM。
  - 涉及「本项目的架构/红线/事件/阶段/决策」→ 进入检索。
- 判定依据：intent + 关键词（runtime/event/redline/phase/decision…）命中 `tags`/`domain`。
- 产出：需要的 `domain` 候选集 + `type` 候选集。

### 3.4 Retrieval（候选集）
- 检索维度（基于 Phase 3 元数据）：
  - `domain` 匹配（强）
  - `tags` 匹配（中）
  - `type` 匹配（中）
- 检索方式（概念，非实现）：关键字索引（文档级已具备 `DOCUMENT_INVENTORY`）+ KU 元数据过滤。
- **不要求语义向量检索**：v1.3 仅定义流程，Hybrid Retrieval 的语义部分在 Phase 7 仅作思想吸收，不实现。

### 3.5 Authority Filtering
- 应用 Phase 4 规则：
  - `status = ARCHIVE/DEPRECATED` → 剔除（Phase 3 §4）。
  - `authority = L30`（前瞻设计）→ 默认**降权**，不直接入核心上下文，除非无更高等级候选。
  - 同事实冲突 → 高等级胜（Phase 4 §3.1），低等级标记 `superseded`。
- 输出：过滤后候选 KU 列表（带 authority 标注）。

### 3.6 Context Assembly
- 去冲突：应用 Phase 5 `supersedes`/`contradicts` 边，保留高权威版。
- 排序：按 Phase 8 Ranking Model（Authority 主权重 + Relevance + Freshness…）。
- 截断：按上下文预算（token 上限）截取 Top-K，保留 FROZEN/红线优先。
- 成型：知识上下文块（结构化，带 KU id + source 引用，便于 LLM 溯源）。

### 3.7 LLM
- 将知识上下文块注入系统提示/上下文，LLM 基于「已过滤、已排序、可溯源」的知识推理。
- 溯源：每条知识带 `source`，LLM 引用时可回溯到权威文档。

---

## 4. 与现有系统的边界

| 现有系统 | 关系 |
|----------|------|
| Context Engine（Phase 9） | 本管道的**消费者**；v1.3 不实现，仅预留接口概念 |
| Memory（memory.py） | 知识上下文**不替代** Memory；二者并列（Phase 9 详述） |
| EventBus | 检索不触发事件；纯只读知识访问 |
| PolicyEngine | 无关；权威过滤是知识层，非执行权限 |

---

## 5. 本 Phase 不做的事（明确禁止）

❌ 不实现检索代码 / 不建索引服务。
❌ 不引入 Vector DB / Embedding / Chroma / Milvus / FAISS。
❌ 不修改 Context Engine / Agent Loop。
❌ 不把知识检索变成用户可见功能。

---

## 6. 与后续 Phase 衔接

| Phase | 衔接点 |
|-------|--------|
| Phase 7 Hybrid Retrieval | 扩展 §3.4 为 Keyword+Semantic+Relationship（思想吸收） |
| Phase 8 Ranking Model | 为 §3.6 排序提供多维权衡公式 |
| Phase 9 Context Integration | 把本管道接入 Context Engine（设计层） |
| Phase 10 Governance | 保证进入检索的 KU 都有合法 source/authority |

---

## 7. 设计纪律确认

✅ 仅定义检索流程，未实现、未引数据库。
✅ 明确不替代 Memory / 不碰 Context Engine 实现。
✅ 与 Phase 4 Authority / Phase 5 Relation / Phase 3 Metadata 联动。
✅ 不触碰冻结基线。

> Phase 6 完成。下一步：Phase 7 吸收 RAG/Graph RAG 思想定义 Hybrid Retrieval（任务 #185）。
