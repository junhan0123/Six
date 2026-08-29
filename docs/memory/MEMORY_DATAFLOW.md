# Xiao6 AI OS — Memory Dataflow v1.0

> **Sprint**: AI OS Phase · Sprint 1 — Memory Architecture Design v1.0
> **配套**: `MEMORY_ENGINE_ARCHITECTURE.md`
> **Discipline**: 纯设计，无代码改动。
> **Status**: 设计稿（待 Review）

---

## 0. 范围

本文档定义 UMA 的数据流：**摄取（Ingest）→ 抽取（Extract）→ 蒸馏（Distill）→ 检索（Retrieve）→ 同步（Sync Bridge）→ 事件扇出（EventBus）**。所有流均只读分析现状，给出统一后的目标流。

---

## 1. 摄取流（Ingestion）

### 1.1 对话摄取（L1 → L5/L7）
```
用户消息
  → chat_log INSERT (L1)
  → 会话结束/阈值触发 compress_memory()
      → memory_summary (L5 摘要)
      → 二次压缩
  → _distill_learnings() → learnings (L7)
```
- 当前实现：`memory.py` `compress_memory` / `_distill_learnings`。
- 目标：写经 `MemoryEngine.write(L1, ...)`，压缩结果经 L9 状态机落 L5/L7，并发 `MEMORY_STORED`。

### 1.2 知识摄取（L4）
```
文档/对话归档
  → knowledge.ingest_document() / archive_conversation()
  → knowledge_docs + knowledge_chunks (L4 后端)
  → embed.py → mem_vectors(scope='knowledge') (L6)
  → _emit_memory() → MEMORY_STORED / MEMORY_LINKED
```
- 目标：归档先落 L3（项目），经治理六步可升 L4（知识）；L4 同时触发 Sync Bridge 写 vault。

### 1.3 笔记摄取（L4，Obsidian 知识层）
```
AI 创建/更新笔记 (tool_note_* / extract_daily_note)
  → Sync Bridge.sync_to_vault()
      → 写 vault .md (含 [[链接]] #标签)
      → 索引 SQLite 正文 + 向量
  → MEMORY_LINKED (图谱边建立)
```
- **修正点**：当前 `notes.py` 直接写 SQLite `notes` 表并自算链接/图谱；目标改为经 Bridge 写 vault，后端只存正文+向量+指针。

---

## 2. 抽取流（Extraction）

```
后台 LLM (cognitive/extractor.maybe_extract, 阈值 THRESHOLD=40)
  → 一次 pass 产出:
      ├─ user_model_delta → upsert_user_model() (L5)
      └─ episode → add_episode() (L7)
  → 显式避免双写 memory_summary / 竞争删除 chat_log
```
- 门控：`FEATURE_USER_MODEL` / `FEATURE_EPISODIC_MEMORY`。
- 目标：抽取结果统一经 `UserModelService.upsert`（L5 收敛）与 `MemoryEngine.write(L7, episode)`。

---

## 3. 蒸馏流（Distillation，L9）

```
memory_distiller.distill()
  → _heuristic() (正则离线优先)
  → _llm_extract() (多轮才试)
  → _dedup()
  → _persist() → memories 表 (L5, type∈{habit,preference,important_event,relationship})
  → important_event 带日期 → upsert important_dates
```
- 目标：蒸馏状态机化（RAW→DISTILLED），结果落 L5，发 `MEMORY_UPDATED`。

---

## 4. 检索流（Retrieval，L8）

```
请求方 (Context Engine / 下游)
  → MemoryEngine.retrieve(query, scope[], budget)
      → 各 Source 实现统一接口:
          MemorySource   → memory.build_memory_block
          KnowledgeSource→ knowledge.semantic_query
          EpisodeSource  → episodic.recall_episodes (0.6*cos + 0.25*imp + 0.15*recency)
          WeatherSource  → (占位, 待接入)
          ConversationSource → (占位, 待接入)
          SystemSource   → (占位, 待接入)
          VaultGraphSource → Sync Bridge.resolve_backlinks (L4 邻域展开)
      → ranker 统一排序
      → budget 截断 (保底顺序: Goal→Memory→WorldModel→Knowledge)
      → bundle → build → 注入 L2 Working Memory
```
- 当前：`context/sources.py` 仅 `MemorySource` 接入，其余占位；`SourceRegistry` 逐源 try/except 隔离。
- 目标：所有源实现统一 `Source` 接口，VaultGraphSource 接入 L4 图谱邻域。

---

## 5. 同步桥流（Sync Bridge，L4）★

### 5.1 机器→Vault
```
MemoryEngine.write(L4, knowledge)
  → Sync Bridge.sync_to_vault(record)
      → 渲染 .md (frontmatter: id, type, generated, tags; body: [[链接]])
      → 写 vault 文件
      → 索引 SQLite 正文 + 向量 (L6)
      → 重建图谱索引 (边)
  → MEMORY_LINKED
```

### 5.2 Vault→机器（人类编辑）
```
定时轮询 / mtime 短路
  → 检测 vault 文件变更 (hash/mtime)
  → Sync Bridge.sync_from_vault(changed_files)
      → 更新 SQLite 正文
      → 重算向量 (L6)
      → 重建图谱边
  → MEMORY_UPDATED (人类编辑优先)
```

### 5.3 冲突策略
- 人类编辑（vault）> 机器生成（标 `generated:true`）。
- 同 ID 冲突：保留 vault 版本，机器侧标 `stale`，不静默覆盖。

---

## 6. 事件扇出流（EventBus，L10）

```
任意写操作
  → MemoryEngine.write()
      → publish_domain(MEMORY_CREATED/UPDATED/STORED/LINKED/ARCHIVED, payload)
      → TOPIC_SSE="zz.sse" 扇出
          → Context Engine (重汇编 L2)
          → RuntimeViz (只读投影)
          → ProactiveEngine (决策, 不执行)
          → 前端 zz-events.js
```
- 事件名契约见 `eventbus.py` `DOMAIN_EVENT_NAMES`（已含 `MEMORY_*`）。
- 系统事件（`SYSTEM_EVENT_NAMES`）独立监听，不进 AppState（与领域事件互斥）。

---

## 7. 数据流总图（目标态）

```
[用户/外部]
   │ ingest
   ▼
L1 Session ─compress─► L5 Long-term ──┐
   │                                  │
   │ extract                           │ distill
   ▼                                  ▼
L7 Reflection ◄──────────────  L5 UserModelService(单后端)
   │                                  │
   │ archive                          │ retrieve
   ▼                                  ▼
L3 Project ─promote(治理六步)─► L4 Knowledge(Vault+Backend+Bridge)
                                      │ sync
                                      ▼
                              L6 Semantic(vectors) ◄──┐
                                      │                │
                              L8 Retrieval ────────────┘
                                      │ rank+budget
                                      ▼
                              L2 Working ──► Context Engine ──► LLM
                                      │
                              L10 Governance (全程边界/审计/事件)
```

---

## 8. 关键不变式（Invariants）

1. **所有写经 `MemoryEngine.write`** → 保证事件扇出与治理校验不被绕过。
2. **Obsidian 只作知识层** → 链接/标签/图谱存 vault，后端不重造。
3. **用户态单后端** → `profile`/`habits.json` 经适配退役，消除三源。
4. **检索统一 Source 接口** → 新增记忆源零改动管线。
5. **事件互斥** → 领域事件进 AppState，系统事件独立；未命名事件抛 ValueError。

---
*本档为设计稿，未改动任何代码。STOP — 待 Review。*
