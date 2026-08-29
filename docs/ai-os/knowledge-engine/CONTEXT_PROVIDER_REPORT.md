# CONTEXT_PROVIDER_REPORT

> Knowledge Platform Sprint v1.0 — Stage G
> 上下文注入层接入统一知识层（Context Provider Integration）
> 生成时间：2026-08-06 | 状态：✅ 完成 | 验证：PASSED

---

## 1. 目标

将「统一知识层（Knowledge Runtime）」作为**上下文来源（Context Source）**接入 Context Engine 的采集管线，使对话在相关时可注入本地知识块。

核心约束（L0 红线）：
- **唯一知识入口** = `knowledge.*`（Runtime facade）；任何来源不得直接读 markdown。
- **无 RAG / 无嵌入 / 无向量库 / 无数据库**（Local First）。
- 经 `knowledge.search` 关键词召回，而非语义召回。

---

## 2. 改动清单

| 文件 | 改动 | 性质 |
|------|------|------|
| `xiao6-ui/context/knowledge_source.py` | 重写为 `KnowledgeSource`：移除旧 `knowledge.semantic_query`（RAG），改用 `knowledge.search(query, limit=4)` 关键词召回；gating flag 改为 `FEATURE_KNOWLEDGE_PLATFORM` | 重写 |
| `xiao6-ui/config.py` | `FEATURE_KNOWLEDGE_RAG` → `FEATURE_KNOWLEDGE_PLATFORM`（声明 / reload 全局列表 / 赋值含旧 env 名向后兼容 / config 字典） | 重命名 + 兼容 |
| `xiao6-ui/context/builder.py` | L62：注册条件改用 `FEATURE_KNOWLEDGE_PLATFORM` | 重命名 |
| `xiao6-ui/self_check.py` | `_check_knowledge_index()` 移除旧 `from db import db_conn` + `SELECT ... mem_vectors`（违反红线），改为 `knowledge.reload()` 取 `validation_ok` | 红线修复 |
| `xiao6-ui/tools.py` | `_KNOWLEDGE_ENABLED` 改用 `FEATURE_KNOWLEDGE_PLATFORM` | 重命名 |
| `xiao6-ui/server.py` | 3 处 feature 字段名同步（`knowledge_platform` / `feature_knowledge_platform` / `FEATURE_KNOWLEDGE_PLATFORM`） | 重命名 |
| `xiao6-ui/settings.js` | 设置项 key 改为 `FEATURE_KNOWLEDGE_PLATFORM` | 重命名 |
| `xiao6-ui/command-palette.js` | flag 改为 `FEATURE_KNOWLEDGE_PLATFORM`（label「知识平台」） | 重命名 |

---

## 3. 架构

```
用户提问 (ctx.user_text)
        │
        ▼
Context Engine ── SourceRegistry.collect(ctx)
        │
        ├─ MemorySource         (既有 Memory Engine)
        ├─ UserModelSource      (FEATURE_USER_MODEL)
        ├─ EpisodicSource       (FEATURE_EPISODIC_MEMORY)
        ├─ PersonalitySource    (FEATURE_PERSONALITY)
        ├─ GoalSource           (FEATURE_GOAL_SYSTEM)
        └─ KnowledgeSource ★    (FEATURE_KNOWLEDGE_PLATFORM)  ← 本 Stage
                │
                ▼
        knowledge.search(query, limit=4)   ← 唯一入口，关键词召回
                │
                ▼
        Knowledge Runtime (engine/loader/resolver/links/validator)
                │
                ▼
        本地 knowledge/*.md（唯一事实源，Obsidian 可编辑）
```

- **注册时机**：`ContextBuilder.__init__` 在 `FEATURE_KNOWLEDGE_PLATFORM=True` 时 `registry.register(KnowledgeSource())`（默认 ON，关闭即不注入）。
- **隔离**：单源异常在 `SourceRegistry.collect` 内被 try/except 隔离，不影响其他来源与对话。
- **优先级**：`priority=0.6`（低于目标 0.7 / 用户模型 0.9，高于情节记忆 0.5）；`token_est=1200`；`recency=0.7`；`user_relevance=0.7`。
- **上限**：每次最多 4 块命中，硬上限约 1200 token，默认预算内不裁剪。

---

## 4. 召回语义（无 RAG）

`knowledge.search` 为 **关键词 / 全文扫描** 召回，实现于 Runtime（非向量）：
- 扫描 frontmatter（title / tags / alias / id）+ 正文，按词频/字段权重打分。
- **不分词嵌入、不做余弦相似度、不查 `mem_vectors`**。
- 同层仍可经 `knowledge.related` / `knowledge.resolve` 做关联扩展与标题解析，但本来源仅用 `search`。

---

## 5. 验证（冒烟，2026-08-06）

运行环境：Python 3.11.9（项目运行时，pyyaml 6.0.3）。

| 检查项 | 结果 |
|--------|------|
| `config.FEATURE_KNOWLEDGE_PLATFORM` 存在且 = True | ✅ |
| `knowledge.reload()` → nodes=46, relations=35, validation_ok=True | ✅ (0.039s) |
| `knowledge.search("本地优先")` → 4 hits（命中 concept / decision 等） | ✅ |
| `KnowledgeSource` 可导入，name="knowledge" | ✅ |
| `builder.py` 引用 `FEATURE_KNOWLEDGE_PLATFORM` | ✅ |
| `knowledge_source.py` 无 `semantic_query`/`mem_vectors`/`embed(`/`vector` 令牌 | ✅ |
| 全仓残留 `FEATURE_KNOWLEDGE_RAG`（代码层）= 仅 `config.py:221` 向后兼容旧 env 名 | ✅ 合规 |
| `self_check._check_knowledge_index` 不再 import `db` / 查 `mem_vectors` | ✅ 红线修复 |

**结论：SMOKE PASS。**

---

## 6. 红线合规

- ❌ 未引入 RAG / Embedding / 向量库 / SQLite / Neo4j / FAISS / Chroma。
- ❌ 未改动 memory / planner / workflow / agent / llm。
- ❌ 未联网、未云同步、未新增 AI 功能。
- ✅ 知识访问统一经 `knowledge.*`；Context 来源不直接读 markdown。
- ✅ `self_check` 旧 DB 查询（违反「无数据库」）已移除。

---

## 7. 已知边界

- `knowledge.py` 仍保留 `semantic_query` 作为**已废弃的关键词别名**（仅作兼容，本来源不使用）；未来「检索增强」阶段若启用向量检索，将另立独立 flag，不污染本层。
- 文档（`docs/ai-os/*`、`docs/memory/*`、`docs/PHASE9_PROACTIVE_AUDIT.md` 等）仍描述旧 RAG 方案，属历史设计记录；统一知识层的最终状态以 `KNOWLEDGE_PLATFORM_SUMMARY.md` 与各 `KNOWLEDGE_*_REPORT.md` 为准（Stage I 收口）。
- 召回为纯关键词，未做语义排序；如需更智能召回留待未来独立检索增强阶段（不在本 Sprint 范围）。
