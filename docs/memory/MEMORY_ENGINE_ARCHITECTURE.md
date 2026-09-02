# Xiao6 AI OS — Unified Memory Architecture (UMA) v1.0

> **Sprint**: AI OS Phase · Sprint 1 — Memory Architecture Design v1.0
> **Mode**: Audit → Architecture → Design → Verify → Report → STOP
> **Discipline**: 纯架构/文档/接口/数据流设计。本 Sprint **不修改任何代码**、不新增功能、不触碰 Runtime/Agent/Planner/Tool/UI/数据库。
> **Status**: 设计稿（待 Review）

---

## 0. 本档定位

本文档是 Unified Memory Architecture（UMA）的**权威架构定义**。它回答三件事：

1. 当前记忆为何碎片化（问题事实，来自 Sprint 审计）。
2. 10 层统一记忆架构如何收敛这些碎片。
3. **Obsidian 如何作为知识层（Knowledge Layer），而非被当数据库用**——这是本 Sprint 的重点。

配套文档：
- `MEMORY_DATAFLOW.md` — 数据流与同步桥。
- `MEMORY_LIFECYCLE.md` — 生命周期状态机与衰减/蒸馏策略。
- `MEMORY_GOVERNANCE.md` — 边界、权限、审计、红线。
- `MEMORY_IMPLEMENTATION_PLAN.md` — 分阶段落地（设计阶段，无编码）。
- `AI_OS_PHASE1_SUMMARY.md` — Sprint 总览与 STOP 点。

---

## 1. 问题陈述（审计事实）

Sprint 审计以只读方式确认了记忆的实际分叉。DECISION_003 规定 `memory.py` 为**唯一记忆系统**，但现实已漂移：

| 来源（当前实现） | 存储位置 | 类型 | 问题 |
|---|---|---|---|
| `memory.py` | `profile` / `memory_summary` / `learnings` / `reminders` / `chat_log` | SQLite 表 | 用户态与对话态混放 |
| `cognitive/user_model.py` | `user_model` 表 | SQLite 表 | **与 `profile` 双用户态源并存冲突** |
| `personalization.py` | `habits.json` **文件** | 文件系统 | **第 3 个用户态存储**，与 DB 三足鼎立 |
| `cognitive/episodic.py` | `episodes` 表 | SQLite 表 | 情节记忆独立表 |
| `memory_distiller.py` | `memories` 表 | SQLite 表 | 长期事实另立表 |
| `knowledge.py` | `knowledge_docs` / `knowledge_chunks` + `mem_vectors(scope='knowledge')` | SQLite+向量 | 项目知识 RAG |
| `notes.py` | `notes` 表（含 `[[wikilinks]]` / `#tags` / 图谱） | SQLite 表 | **在 SQLite 内重造 Obsidian = 反模式** |
| `context/` 包 | 内存管线 | 内存 | Context Engine 骨架，仅 `MemorySource` 接入 |
| `eventbus.py` | `TOPIC_SSE` 扇出 | 内存 | 已含 `MEMORY_*` 领域事件 |
| `db.py` | 13+ 记忆相关表 | SQLite | 证实分叉严重 |

**三大核心矛盾**：
1. **用户态三源并存**：`profile`（memory.py）+ `user_model`（cognitive）+ `habits.json`（personalization）。
2. **Obsidian 被当数据库**：`notes.py` 在 SQLite 内用 `[[链接]]`/`#标签`/图谱模拟 Obsidian，失去真 Obsidian vault 的人类可读、双向链接、图谱浏览价值。
3. **抽象缺失**：各模块直接读写各自表，无统一记忆抽象层，导致检索/治理/生命周期无法统一。

---

## 2. 设计原则

1. **Single Logical Source（逻辑单一来源）**：尊重 DECISION_003 精神——只有一个记忆抽象层（Memory Engine API），底层可有多存储后端，但对外只有一套接口。
2. **Layered Abstraction（分层抽象）**：按认知层次（会话→工作→项目→知识→长期→语义→反思→检索→生命周期→治理）分层，每层单一职责。
3. **Obsidian = Knowledge Layer, NOT Database（重点）**：Obsidian vault 是**语义化知识组织层**（人类可读 `.md`、双向链接、图谱检索）；SQLite/向量库仅作**持久化后端**。二者通过**同步桥（Sync Bridge）**一致。
4. **Event-Driven（事件驱动）**：所有记忆写操作经 `eventbus` 发 `MEMORY_*` 领域事件，下游（Context Engine、RuntimeViz、ProactiveEngine）只读订阅。
5. **No-Code-Change Discipline（本 Sprint 红线）**：本文档只定义架构/接口/数据流，不改动任何现有代码、表结构、Runtime。

---

## 3. 十层 Unified Memory Architecture

层级编号 L1–L10，自上而下由"近"（会话）到"远"（治理）。

### L1 — Session Memory（会话记忆）
- **职责**：单次会话内的瞬时状态（当前对话、临时草稿、未落库的中间态）。
- **当前映射**：`chat_log`、`conversation_memories`、`prefetch_cache`、`prefetch_tasks`。
- **生命周期**：会话级，会话结束即收敛（压缩入 L5 / 归档入 L3）。
- **不存**：稳定用户态、长期知识、Goal（禁存域见 GOVERNANCE）。

### L2 — Working Memory（工作记忆）
- **职责**：AI 当前推理所需的"活动上下文"——即拼装好、待注入系统提示词的内容。
- **当前映射**：`context/` 包（`facade.build_context_prompt` → `LegacyContextBuilder` 五阶段：Collect→Rank→Budget→Bundle→Build）；`memory.build_system_prompt` 的上下文前缀（ACI 预判：时间/待办/焦点/任务/热点/预取）。
- **边界**：Working Memory **不产生权威**，只汇编（L10 治理保证不覆盖更高权威）。

### L3 — Project Memory（项目记忆）
- **职责**：项目/会话相关的持久知识（归档的对话、项目文档、领域资料）。
- **当前映射**：`knowledge.py`（`knowledge_docs`/`knowledge_chunks`，`source='chat:<session>'` 归档）、`notes.extract_daily_note()`（每日笔记）。
- **与 L4 关系**：L3 偏向"本项目/本会话"的资料；L4 偏向"跨项目可复用"的知识。归档对话先落 L3，经治理六步可升 L4。

### L4 — Knowledge Memory（知识记忆）★ Obsidian 知识层
- **职责**：跨项目可复用的**语义化知识**。这是 Obsidian vault 作为**知识层**的落点。
- **架构定位（重点）**：
  - **Obsidian vault（`.md` 文件）= 知识组织层**：人类可读、双向 `[[链接]]`、`#标签`、图谱浏览、反向链接。
  - **SQLite + `mem_vectors` = 持久化后端**：机器检索、向量语义检索的存储。
  - **Sync Bridge（同步桥）= 一致性机制**：AI 写知识 → 落 vault `.md` → 索引入 SQLite/向量；人类在 vault 编辑 → 桥检测变更 → 重新索引。**obsidian 不是数据库，是知识的表现/组织面。**
- **当前反模式修正**：`notes.py` 把 Obsidian 当数据库（链接/标签/图谱全存 SQLite）——重构后，这些语义关系归 vault，SQLite 只存正文本+向量+索引指针。
- **检索增强**：图谱（graph）作为检索入口之一（L8 检索管线支持"图谱邻域展开"）。

### L5 — Long-term Memory（长期记忆）
- **职责**：稳定的用户/智能体事实（用户画像、习惯、偏好、重要事件、学习经验）。
- **当前映射（需收敛）**：`profile`（memory.py）+ `user_model`（cognitive）+ `habits.json`（personalization）+ `memories`（memory_distiller）+ `learnings`（memory.py）+ `reminders`（memory.py）。
- **统一抽象（关键设计）**：三者收敛为**单一 User-State 服务**：
  - 逻辑接口 `UserModelService`：`load()` / `upsert(delta)` / `render_block()`。
  - 物理后端选其一（建议 `user_model` 表为唯一后端，`profile` 与 `habits.json` 经适配器退役）。
  - 收敛后消除"三源并存"冲突，恢复 DECISION_003 单一来源精神。

### L6 — Semantic Memory（语义记忆）
- **职责**：向量/嵌入子层，为 L3/L4/L5/L7 提供语义检索底座。
- **当前映射**：`mem_vectors`（scope=`knowledge`/`episodic`）、`embed.py`（本地 ONNX 向量）。
- **边界**：纯存储/检索原语，不含业务语义；被 L8 检索管线调用。

### L7 — AI Reflection Memory（反思记忆）
- **职责**：智能体的自我改进经验（蒸馏出的经验、情节记忆、复盘）。
- **当前映射**：`learnings`（memory.py，经 `_distill_learnings`）、`episodes`（cognitive/episodic，重要性+近因检索）、`memories`（memory_distiller 的 `habit/preference/important_event/relationship`）。
- **与 L5 关系**：L7 是"AI 从经验中学到的"，L5 是"关于用户/世界的稳定事实"。二者经 EventBus 解耦，但 L7 经验可经治理升 L5。

### L8 — Retrieval Pipeline（检索管线）
- **职责**：统一的记忆获取与排序抽象，供 L2 Working Memory 与所有下游消费。
- **当前映射**：`context/ranker.py` + `builder.py` + `sources.py`（SourceRegistry 逐源采集隔离）、`memory_query.py`、`episodic.recall_episodes`、`knowledge.semantic_query`、`memory.build_memory_block`。
- **统一接口**：`retrieve(query, scope[], budget) → ranked_blocks`。各源（Memory/Weather/Conversation/System/Knowledge/Episode）实现统一 `Source` 接口，由管线统一排序与预算截断（GOVERNANCE 保底顺序）。

### L9 — Memory Lifecycle（记忆生命周期）
- **职责**：记忆的创建→蒸馏→归档→衰减→升级/降级状态机。
- **当前映射**：`memory.compress_memory` / `_distill_learnings`、`knowledge.archive_conversation`、`notes.extract_daily_note`、`WORLD_MODEL_BOUNDARY` 的"观察态→稳定知识"升级纪律。
- **状态**：`RAW → ACTIVE → DISTILLED → ARCHIVED → (PROMOTED↑ / DECAYED↓)`。详见 `MEMORY_LIFECYCLE.md`。

### L10 — Memory Governance（记忆治理）
- **职责**：边界、权限、审计、红线、事件治理。
- **当前映射**：`MEMORY_BOUNDARY_SPECIFICATION`、`DECISION_003`、`CONTEXT_ASSEMBLY_GOVERNANCE`、`WORLD_MODEL_BOUNDARY_SPECIFICATION`、`tool_audit` 表、`eventbus` 的 `MEMORY_*` 事件。
- **权威层级**：L100 红线最高 > 用户态 > 通用默认。详见 `MEMORY_GOVERNANCE.md`。

---

## 4. 层级 → 当前实现映射总表

| 层 | 逻辑职责 | 当前实现（待收敛） | 收敛方向 |
|---|---|---|---|
| L1 Session | 会话瞬时态 | chat_log / conversation_memories / prefetch_* | 保持，明确会话边界 |
| L2 Working | 活动上下文 | context/ 包 + memory.build_system_prompt | 以 context/ 为唯一入口 |
| L3 Project | 项目资料 | knowledge.py(chat归档) / notes.daily | 归档对话归 L3 |
| L4 Knowledge | 跨项目知识 | **notes.py(SQLite 伪 Obsidian)** | **→ 真 Obsidian vault + Sync Bridge** |
| L5 Long-term | 用户/世界稳定事实 | profile + user_model + habits.json + memories + learnings + reminders | **UserModelService 单一后端** |
| L6 Semantic | 向量底座 | mem_vectors + embed.py | 保持，统一 scope 管理 |
| L7 Reflection | 自我改进经验 | learnings + episodes + memories | 保持，明确定义升 L5 路径 |
| L8 Retrieval | 检索排序 | context/* + memory_query + recall + semantic_query | 统一 Source 接口 |
| L9 Lifecycle | 状态机 | compress/distill/archive/extract | 状态机化 |
| L10 Governance | 边界/审计 | 4 份规范 + tool_audit + eventbus | 保持，补 UMA 红线 |

---

## 5. Obsidian 作为知识层（核心设计）

### 5.1 反模式（现状）
`notes.py` 在 SQLite 内用 `parse_md_links()`/`parse_md_tags()`/`get_graph()` 重造 Obsidian 的 `[[链接]]`/`#标签`/图谱。结果：
- 人类无法用 Obsidian 直接浏览/编辑这些"笔记"。
- 图谱、反向链接等 Obsidian 原生能力被低效重造。
- 失去 Markdown 作为人类可读知识面的价值。

### 5.2 目标架构：Vault + Backend + Bridge
```
┌─────────────────────────────────────────────┐
│  Obsidian Vault (Knowledge Layer / 组织面)    │
│  ├─ 用户知识/项目知识 .md                       │
│  ├─ [[双向链接]] #标签 反向链接 图谱            │
│  └─ 人类可读、可手动编辑、可图谱浏览            │
└───────────────┬─────────────────────────────┘
                │  Sync Bridge（双向同步 + 变更检测）
┌───────────────▼─────────────────────────────┐
│  Persistence Backend (存储后端, 非"数据库即知识")│
│  ├─ SQLite: notes 正文 + 索引指针 + metadata    │
│  └─ mem_vectors(scope='knowledge'): 向量        │
└─────────────────────────────────────────────┘
```
- **Vault = 知识层**：语义关系（链接/标签/图谱）是知识的一等公民，存于 `.md`。
- **Backend = 存储**：仅存正文文本、向量、索引指针、metadata；**不重造链接/标签/图谱逻辑**。
- **Bridge = 一致性**：UUID 关联 vault 文件 ↔ SQLite 行 ↔ 向量；编辑任一侧触发对侧重索引。

### 5.3 Sync Bridge 契约（逻辑接口，非代码）
- `bridge.sync_from_vault()`: 扫描 vault 变更（mtime/哈希）→ 更新 SQLite 正文 + 重算向量 + 重建图谱索引。
- `bridge.sync_to_vault(record)`: AI 新建/更新知识 → 写 `.md`（含 `[[链接]]`/`#标签`）→ 索引入后端。
- `bridge.resolve_backlinks(note_id)`: 图谱邻域查询，供 L8 检索"邻域展开"。
- 冲突策略：vault 人类编辑优先（人类是知识的最终权威），机器生成内容标 `generated:true` 元数据。

### 5.4 为何不是数据库
- 数据库（SQLite）擅长**结构化存储与查询**；Obsidian 擅长**语义组织与人类协作**。
- 把 Obsidian 当数据库 = 用 SQLite 字段模拟链接/标签/图谱 → 丧失人类可读性与 Obsidian 生态。
- 正确分工：SQLite 做"存储后端"，Obsidian vault 做"知识层"——各司其职。

---

## 6. 统一用户态抽象（L5 收敛）

### 6.1 问题
`profile`（memory.py）/`user_model`（cognitive）/`habits.json`（personalization）三源并存，违反 DECISION_003 单一来源。

### 6.2 收敛方案
- 定义逻辑服务 `UserModelService`：
  - `load() → UserModel`（合并 identity/expertise/communication_style/preferences/recurring_projects/values/feedback/habits）。
  - `upsert(delta)`：浅合并 + 数组去重 + confidence 累加（沿用 `user_model.py` 现有逻辑）。
  - `render_block() → str`：硬上限约 350 token（沿用现有渲染）。
- 物理后端：**`user_model` 表为唯一权威后端**；`profile` 与 `habits.json` 经适配器逐步退役（读适配，写重定向至 `user_model`）。
- 不改代码前提下，本 Sprint 仅确定该抽象与迁移路径（见 IMPLEMENTATION_PLAN）。

---

## 7. 接口契约（逻辑，非代码）

| 接口 | 职责 | 备注 |
|---|---|---|
| `MemoryEngine.write(layer, record)` | 写记忆，触发 `MEMORY_*` 事件 | 所有写经此 |
| `MemoryEngine.retrieve(query, scope[], budget)` | 统一检索 | 委托 L8 |
| `UserModelService.load/upsert/render` | 用户态单一接口 | L5 收敛 |
| `KnowledgeVault.sync_from/to/sync` | Obsidian 同步桥 | L4 |
| `Lifecycle.transition(record, state)` | 状态机迁移 | L9 |
| `Governance.check(op, actor)` | 边界/权限校验 | L10 |

---

## 8. 边界图（与其他系统）

```
Goal System ──┐
World Model ──┼──(硬边界, 不互存)──► Memory Engine (L1-L10)
Knowledge ────┘                         │
Context Engine ◄──(只读订阅 L2/L8)──────┘
EventBus ◄──(MEMORY_* 事件扇出)─────────┘
RuntimeViz / ProactiveEngine ◄──(只读)──┘
```
- **硬边界**：Goal、World Model、实时态势**不存**入 Memory（见 GOVERNANCE 禁存域）。
- **观察态→稳定知识**：World Model 观察态升级为 L4 知识须走治理六步，禁止静默冻结。

---

## 9. 开放问题（待 Review 决策）

1. **UserModelService 后端选型**：`user_model` 表 vs `profile` 表？建议 `user_model`。
2. **Sync Bridge 触发时机**：文件监听 vs 定时轮询？资源受限本地环境建议轮询 + mtime 短路。
3. **向量 scope 统一**：当前 `knowledge`/`episodic` 两 scope，是否引入 `user`/`reflection` scope？
4. **图谱检索权重**：L8 邻域展开在排序中的权重系数待标定。
5. **迁移节奏**：是否允许"读适配并行"双跑过渡期？建议允许，降低风险。

---
*本档为设计稿，未改动任何代码。STOP — 待 Review。*
