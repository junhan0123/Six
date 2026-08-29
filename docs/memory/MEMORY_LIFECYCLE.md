# Xiao6 AI OS — Memory Lifecycle v1.0

> **Sprint**: AI OS Phase · Sprint 1 — Memory Architecture Design v1.0
> **配套**: `MEMORY_ENGINE_ARCHITECTURE.md` (L9)
> **Discipline**: 纯设计，无代码改动。
> **Status**: 设计稿（待 Review）

---

## 0. 范围

本文档定义记忆的**生命周期状态机**与各层衰减/蒸馏/归档策略。当前各模块（compress/distill/archive/extract）各自为政，目标态由统一的 L9 Lifecycle 状态机驱动。

---

## 1. 统一状态机

### 1.1 状态定义
| 状态 | 含义 | 典型层 |
|---|---|---|
| `RAW` | 刚产生，未处理（如 chat_log 原始对话） | L1/L3 |
| `ACTIVE` | 活跃可用（已索引、可被检索） | L2/L4/L5/L7 |
| `DISTILLED` | 已蒸馏为稳定事实/经验 | L5/L7 |
| `ARCHIVED` | 归档冷存（低频检索） | L3/L4 |
| `PROMOTED` | 升级到更高层（观察态→知识，项目→跨项目） | L3→L4, WM→L4 |
| `DECAYED` | 衰减/降权（久未访问、置信下降） | L5/L7 |
| `PURGED` | 彻底删除（仅限明确策略或用户请求） | 任意 |

### 1.2 状态转移图
```
        ingest
   ┌─────────────┐
   │    RAW      │──────────┐
   └─────────────┘          │ index
        │ compress/distill  ▼
        ▼            ┌─────────────┐
   ┌─────────────┐   │   ACTIVE    │◄───────────┐
   │  DISTILLED   │◄──┤             │            │ promote
   └─────────────┘   └─────┬───────┘            │
        │                  │ decay              │
        │                  ▼                     │
        │           ┌─────────────┐             │
        │           │   DECAYED   │             │
        │           └─────┬───────┘             │
        │                 │ purge               │
        │                 ▼                     │
        │          ┌─────────────┐              │
        └─────────►│  ARCHIVED   │──────────────┘
                   └─────────────┘
```

### 1.3 转移规则
- `RAW → ACTIVE`：索引完成（写入向量 L6 + 注册检索源）。
- `RAW → DISTILLED`：经 `memory_distiller` 蒸馏为稳定事实。
- `ACTIVE → DECAYED`：超过 `DECAY_TTL` 未访问或 confidence < 阈值。
- `DECAYED → PURGED`：仅当用户显式删除或达硬留存上限（默认不自动 purge 用户态）。
- `ARCHIVED → ACTIVE`：被检索命中或升级路径触发。
- `PROMOTED`：跨层升级，须走治理（见 GOVERNANCE 六步）。

---

## 2. 各层生命周期策略

### L1 Session
- **TTL**：会话级。会话结束触发收敛。
- **收敛**：compress_memory → L5 摘要；会话中间态不落长期。
- **不归档**：会话非持久资产，结束即释放（仅 `conversation_memories` 保留摘要）。

### L2 Working
- **TTL**：单次请求级。请求结束即丢弃（纯内存）。
- **不持久化**：Working Memory 不产生权威。

### L3 Project
- **归档**：`knowledge.archive_conversation` 落 `knowledge_docs`/`chunks`。
- **升级**：经治理六步 → L4（知识复用）。
- **衰减**：项目归档超 `PROJECT_TTL`（建议 180d）降权，不自动删。

### L4 Knowledge（Obsidian 层）
- **ACTIVE**：vault `.md` 存在且被索引。
- **图谱维护**：链接变更经 Bridge 重建边（`MEMORY_LINKED`）。
- **衰减**：vault 文件 mtime 超 `KNOWLEDGE_TTL` 且零反向链接 → 降权。
- **删除**：仅用户从 vault 删除（人类优先），Bridge 同步删后端。

### L5 Long-term（含 UserModelService 收敛）
- **写入**：`upsert` 累加 confidence（沿用 0→0.95 逻辑）。
- **衰减**：confidence < `L5_DECAY_CONF`（建议 0.3）且久未确认 → `DECAYED`。
- **蒸馏**：`memories` 表稳定事实（`habit/preference/important_event/relationship`）。
- **留存**：用户态默认**不自动 purge**（隐私与连续性优先）。

### L6 Semantic
- **随上游**：向量随 L3/L4/L5/L7 记录的 ACTIVE/ARCHIVED 同步。
- **重建**：vault 变更触发重算（Bridge）。

### L7 Reflection
- **蒸馏**：`learnings` / `episodes` / `memories`。
- **重要度**：`episodes` 用 importance 权重；`recall` 得分 = 0.6*cos + 0.25*imp + 0.15*recency。
- **升 L5**：反思经验经治理可升为用户/世界稳定事实。

### L8 Retrieval
- **无状态**：管线本身无生命周期，仅消费各层 ACTIVE 态。

### L9 Lifecycle
- **驱动者**：状态机自身，监听 `MEMORY_*` 事件触发转移。

### L10 Governance
- **审计留存**：`tool_audit` 表记录写操作；治理不衰减。

---

## 3. 衰减与蒸馏参数（建议值，待标定）

| 参数 | 当前值（沿用） | 建议 | 用途 |
|---|---|---|---|
| `MEM_KEEP` | 24 | 24 | 保留对话条数 |
| `MEM_THRESHOLD` | 40 | 40 | 压缩阈值 |
| `MEM_SUMMARY_MAXLINES` | 12 | 12 | 摘要上限 |
| `LEARN_DISTILL_MIN_INTERVAL` | 21600s | 21600s | 蒸馏最小间隔 |
| `EXTRACT_THRESHOLD` | 40 | 40 | 抽取阈值 |
| `EXTRACT_STEP` | 20 | 20 | 抽取步长 |
| `EPISODE_TOP_K` | 5 | 5 | 情节召回 |
| `L5_DECAY_CONF` | — | 0.3 | 用户态衰减 |
| `PROJECT_TTL` | — | 180d | 项目归档降权 |
| `KNOWLEDGE_TTL` | — | 365d | 知识降权 |

---

## 4. 升级纪律（观察态 → 稳定知识）

遵循 `WORLD_MODEL_BOUNDARY_SPECIFICATION`：
1. World Model 观察态**禁存** Memory（硬边界）。
2. 若观察态需升级为知识 → 走治理六步：
   - 提取候选 → 去重 → 人工/AI 校验 → 标 confidence → 落 L4（经 Bridge 写 vault）→ 发 `MEMORY_PROMOTED`。
3. **禁止静默冻结**：观察态不得无治理直接写入长期记忆。

---

## 5. 删除与合规

- **用户请求删除**：经 `Governance.check` 校验 → 标 `PURGED` → 同步删 vault + 向量 + 索引。
- **自动 purge**：仅限非用户态、超硬留存的临时态（如 `prefetch_cache`）。
- **审计**：所有 purge 入 `tool_audit`。

---
*本档为设计稿，未改动任何代码。STOP — 待 Review。*
