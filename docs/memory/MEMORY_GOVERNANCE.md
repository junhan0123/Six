# Xiao6 AI OS — Memory Governance v1.0

> **Sprint**: AI OS Phase · Sprint 1 — Memory Architecture Design v1.0
> **配套**: `MEMORY_ENGINE_ARCHITECTURE.md` (L10)
> **Discipline**: 纯设计，无代码改动。
> **Status**: 设计稿（待 Review）

---

## 0. 范围

本文档固化 UMA 的**治理规则**：边界、权限、审计、红线。它把现有 4 份规范（`DECISION_003`、`MEMORY_BOUNDARY_SPECIFICATION`、`CONTEXT_ASSEMBLY_GOVERNANCE`、`WORLD_MODEL_BOUNDARY_SPECIFICATION`）与 UMA 十层对齐，并补入 Obsidian 知识层与统一用户态的治理条款。

---

## 1. 权威层级（不可覆盖）

```
L100 冻结红线 (Golden State / Constitution)  ← 最高，不可覆盖
  ▼
用户态 (User Model / 显式指令)              ← 优先于通用默认
  ▼
通用默认 (Memory Engine 默认行为)
```
- Context Engine 汇编（L2）**不得覆盖**更高权威（CONTEXT_ASSEMBLY_GOVERNANCE）。
- 预算截断保底顺序：Goal → Memory → World Model → Knowledge。

---

## 2. Memory 负责域 vs 禁存域

### 2.1 负责域（可存）
- 用户画像 / 用户模型（L5，经 UserModelService）。
- 对话摘要 / 近期对话记忆（L1/L5）。
- 历史经验 / 自我学习（L7）。
- 提醒 / 待办（L5 `reminders`）。
- 跨项目知识（L4，Obsidian 层）。
- 项目资料归档（L3）。

### 2.2 禁存域（硬边界，不存 Memory）
1. **项目知识**（应走 Knowledge L4，非 Memory 自由态）。
2. **决策记录**（走 DECISION 文档体系，非记忆表）。
3. **实时态势**（World Model 观察态，不落 Memory）。
4. **Goal**（Goal System 独立，禁存记忆）。
5. **会话中间态**（L1 瞬时，结束即收敛，不落长期）。
6. **未治理洞察**（须走治理六步升 L4，禁止静默冻结）。

---

## 3. 单一来源纪律（DECISION_003）

- `memory.py` → UMA 的 `MemoryEngine` 为**唯一记忆抽象层**。
- **禁止** `memory2.py` 或平行记忆存储。
- **禁止** 第二 RAG（Knowledge 复用同一向量底座 mem_vectors）。
- **本 Sprint 修正**：`profile` / `user_model` / `habits.json` 三源并存违反此精神 → 收敛为 `UserModelService` 单后端（见 ARCHITECTURE §6）。

---

## 4. 权限模型（Permission）

| 操作 | 允许者 | 校验 |
|---|---|---|
| 写 L1/L5/L7 | Memory Engine（内部） | 经 `eventbus` 事件 |
| 写 L4（知识） | Knowledge 模块 + Sync Bridge | 治理六步（升级时） |
| 人类编辑 vault | 用户（Obsidian） | 人类优先，标 `generated:false` |
| 删（purge） | 用户显式请求 / 治理 | `Governance.check` + `tool_audit` |
| 读（retrieve） | Context Engine / 下游（只读） | 预算截断保底顺序 |

- 所有写经 `MemoryEngine.write` → 保证治理校验与事件扇出不被绕过。
- Policy Engine（Phase 7）为唯一权限裁决；UMA 不自建第二权限。

---

## 5. 审计（Audit）

- `tool_audit` 表记录所有记忆写/删操作（actor / op / layer / ts）。
- 事件信封：`{"xiao6_event": name, "payload":..., "ts":...}`（eventbus）。
- 领域事件（`MEMORY_CREATED/UPDATED/STORED/LINKED/ARCHIVED`）经 `TOPIC_SSE` 扇出；系统事件独立，不进 AppState。
- 互斥约束：领域事件进 AppState 写入口，系统事件独立监听；未命名事件抛 ValueError。

---

## 6. Obsidian 知识层治理（新增）

1. **Vault 是人类知识权威面**：人类在 vault 的编辑优先于机器生成内容。
2. **后端不重造语义**：SQLite/向量只存正文+向量+指针+metadata；链接/标签/图谱归 vault。
3. **生成内容标注**：机器写入标 `generated:true` frontmatter，便于区分与回溯。
4. **同步一致性**：Bridge 保证 vault ↔ 后端双向一致；冲突时 vault 胜。
5. **禁止**：把 Obsidian 当数据库（用字段模拟 `[[链接]]`/`#标签`/图谱）——即 `notes.py` 当前反模式须修正。

---

## 7. 事件治理

- 写操作必须发对应 `MEMORY_*` 事件（CREATED/UPDATED/STORED/LINKED/ARCHIVED）。
- 下游（Context Engine / RuntimeViz / ProactiveEngine）**只读订阅**，不回写 Memory。
- ProactiveEngine 决策（IGNORE/SUGGEST/NOTIFY/CREATE_GOAL）不执行，所有执行经 `submit_goal` + Policy Guard。

---

## 8. 红线（本 Sprint + 长期）

### 8.1 本 Sprint 红线（不可违反）
- ❌ 不修改任何代码（Python/JS/CSS/HTML）。
- ❌ 不新增功能 / 不改 Runtime / Agent / Planner / Tool / UI / 数据库。
- ❌ 不触碰 Obsidian 存储实现（仅设计知识层）。
- ✅ 只做架构/文档/接口/数据流设计。

### 8.2 长期治理红线（UMA 落地后）
- ❌ 禁止第二 Memory / 第二 RAG / 第二用户态源。
- ❌ 禁止绕过 `MemoryEngine.write` 直接写表。
- ❌ 禁止把 Obsidian 当数据库。
- ❌ 禁止观察态静默冻结为长期记忆。
- ❌ 禁止 Context Engine 覆盖更高权威。

---

## 9. 治理检查清单（Verify 阶段用）

- [ ] 所有写经 `MemoryEngine.write`？
- [ ] 用户态是否单后端（无三源）？
- [ ] Obsidian 是否仅作知识层（后端无链接/标签/图谱逻辑）？
- [ ] 禁存域是否被严格遵守（Goal/WorldModel/中间态不落 Memory）？
- [ ] 所有写是否发 `MEMORY_*` 事件？
- [ ] 下游是否只读订阅？
- [ ] purge 是否经 `Governance.check` + `tool_audit`？
- [ ] 权威层级是否未被覆盖？

---
*本档为设计稿，未改动任何代码。STOP — 待 Review。*
