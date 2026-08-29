# Xiao6 Knowledge Engine — API Spec (Knowledge Foundation v1.0)

> **Sprint**: Knowledge Engine Sprint v1.0 — Knowledge Foundation
> **Mode**: **Design Only（仅设计契约，不实现、不写代码）**
> **Companion**: 继承 `KNOWLEDGE_ENGINE_ARCHITECTURE.md` §2.2/§4 + `KNOWLEDGE_SCHEMA.md`
> **Status**: 设计稿（待 Review）

---

## 0. 本档定位与红线

定义 Knowledge Engine 的**文件级 API 契约**——AI 如何读取 / 引用 / 更新知识。

**本 Sprint 红线（重申，关键）**：
- ❌ 本 API **不是向量查询 API**；❌ 不含 `semantic_query` / `embed` / `vector_search`。
- ❌ 不实现 RAG / Embedding / 向量数据库（推迟为未来"检索增强"阶段）。
- ✅ API 仅对 `.md` 文件做：读取、按链接/标签/域检索、引用、建议写入、生命周期迁移。
- ✅ 所有写经 PermissionGuard + EventBus，运行于单 Runtime 内（L0 红线一致）。

---

## 1. 运行边界（与 L0 红线一致）

```
Knowledge Engine (文件级 API)
   │ 运行于单 Runtime 内（无第二 Runtime）
   ▼
PermissionGuard（单权限）── 所有写必须经此
   ▼
EventBus（单通信）── publish knowledge:* 领域事件
   ▼
Knowledge Vault (knowledge/*.md)  ←── Human 手写优先
```

- **不直连** SQLite/向量；Backend 索引是 Vault 的派生镜像，API 以 Vault 文件为权威。
- **不做** Memory/Goal/Workflow 内部状态操作；仅按 `id` 引用。
- **Context Engine** 是首要消费者：只读调用 `read`/`query` 装配上下文（L8 检索 Source 之一）。

---

## 2. 接口契约（逻辑签名，非实现）

### 2.1 读取
```
KnowledgeEngine.read(path: str) -> KnowledgeDoc
  解析 .md → {frontmatter, body, wikilinks, tags}
  失败（frontmatter 非法）→ 返回错误并建议落 inbox/ 修复，不崩溃

KnowledgeEngine.read_by_id(id: str) -> KnowledgeDoc
  经 frontmatter id 索引定位文件
```

### 2.2 检索（文件级，非向量）
```
KnowledgeEngine.query(
    domain:   Optional[type-enum],       # projects/people/.../None=全域
    tags:     Optional[list[str]],       # #area/subtag 交集/并集
    status:   Optional[list[status]],    # 状态过滤
    text:     Optional[str],             # 正文/标题关键字（grep，非语义）
    links_to: Optional[str],             # 反查：谁链接了我（反向链接）
) -> list[KnowledgeDoc轻量引用]
```
- 检索基于：frontmatter 字段 + wikilink 图 + 标签 + 关键字。**无 embedding**。
- 排序：status 权重（`consolidated` > `linked` > `reviewed`）→ updated 近因 → title。
- 未来"检索增强"阶段可在 L8 管线叠加向量近似，但**不改变本文件级 API**（仅新增可选 Source）。

### 2.3 引用（溯源）
```
KnowledgeEngine.reference(path: str) -> Citation
  返回 {id, title, path, source, updated}
  供 Context Engine / 回复中附带来源，可一键在 Obsidian 打开
```

### 2.4 写入（建议模式，agent）
```
KnowledgeEngine.suggest(doc: KnowledgeDocDraft) -> PendingRef
  仅能创建 status=captured，强制 source:agent + confidence + provenance
  落 inbox/，不写入正式域、不覆盖人类正文
  触发 review_due；人类确认后由 transition 迁入正式域
```

### 2.5 更新（人类 / 经许可的 agent）
```
KnowledgeEngine.update(path: str, delta: dict) -> KnowledgeDoc
  经 PermissionGuard 校验 → 改写 frontmatter/正文 → 更新 updated
  发布 knowledge:written {path, op}
  人类正文优先：agent 更新 = 追加/建议，不静默覆盖（冲突以人类胜出）
```

### 2.6 链接
```
KnowledgeEngine.link(a_id: str, b_id: str) -> void
  在 a 的 frontmatter links / 正文加 [[b 标题]]；双向索引更新
```

### 2.7 生命周期
```
KnowledgeEngine.transition(path: str, state: status) -> KnowledgeDoc
  校验状态机合法迁移（见 SCHEMA §4）
  发布 knowledge:state_changed {path, from, to}
  consolidated/deprecated 须人类确认（PermissionGuard）
```

---

## 3. 事件契约（领域事件，扩展现有 EventBus）

> 现有事件契约：DOMAIN=71 / SYSTEM=8（冻结，本 Sprint 不修改计数）。
> 以下 `knowledge:*` 为**新增领域事件提案**，须由中央事件合约管理者在 Review 批准后统一追加（不在本 Sprint 实现）。

| 事件 | payload | 发布者 | 消费者 |
|------|---------|--------|--------|
| `knowledge:written` | `{path, op, id}` | update() | Context Engine(重索引)、Memory L4(更新索引)、Surface |
| `knowledge:linked` | `{a_id, b_id}` | link() | Memory L4、Graph |
| `knowledge:state_changed` | `{path, from, to}` | transition() | Context Engine、Proactive(感知) |
| `knowledge:suggested` | `{inbox_path, id}` | suggest() | Surface(提示人类复核)、Proactive |

- 与 Memory 的 `memory:written` 平行；Knowledge 事件**不触发 LLM 主动推送**，由 Context Engine 显式查询（只读聚合，对齐 Memory 纪律）。

---

## 4. 权限边界（PermissionGuard）

- 读：`Context Engine` / `Proactive`（评估）/ 人类 —— 默认允许（只读）。
- 写（`suggest`/`update`/`transition`）：经 PermissionGuard。
  - `suggest`（agent→inbox）：允许，但标 `source:agent` + `review_due`。
  - `update`/`transition` 到 `consolidated`/`deprecated`（尤其 `rules/`/`decisions/`）：**需人类确认**（高影响）。
- 禁止：agent 直接写正式域 `status:consolidated`、覆盖人类正文、绕过 PermissionGuard。

---

## 5. 与 Context Engine 的集成（首要消费路径）

```
Context Engine (L8 检索管线)
   │ add Source: KnowledgeSource
   ▼
KnowledgeSource.retrieve(query, budget) -> ranked_blocks
   │ 调用 KnowledgeEngine.query(domain=knowledge, ...)
   │ 每个命中 → KnowledgeEngine.reference(path) 附溯源
   ▼
拼装进工作上下文（带 source 引用，可回跳 Vault 文件）
```
- Knowledge 是 L8 的一个 Source（与 Memory/Weather/Conversation 并列），统一 `Source` 接口。
- 图谱邻域展开（反向链接）作为排序增强项（未来可选）。

---

## 6. 不在本 API 范围（明确推迟）

| 能力 | 状态 | 归属 |
|------|------|------|
| `semantic_query` / `embed` / 向量检索 | ❌ 本 Sprint 不做 | 未来"检索增强"阶段 |
| RAG 问答链路 | ❌ 本 Sprint 不做 | 同上 |
| Obsidian 同步逻辑实现 | ❌ 本 Sprint 不做（仅设计文件结构） | 实现阶段用 Obsidian 打开文件夹 |
| 知识自动蒸馏/反思 | ❌ 本 Sprint 不做 | Memory L7 / 未来 |

---

## 7. 验收标准（实现阶段用，本 Sprint 仅定义）

1. `read`/`read_by_id` 能解析任意合规 Vault 文档（含 wikilink/tags）。
2. `query` 支持 domain/tags/status/text/links_to 组合，结果带溯源。
3. `suggest` 只能落 `inbox/` 且标 `source:agent`+`confidence`+`provenance`。
4. `update`/`transition` 经 PermissionGuard，发布对应 `knowledge:*` 事件。
5. 所有写不覆盖人类正文；冲突以人类胜出。
6. 无向量/embedding 调用；Backend 索引不含正文。
7. 与 L0 红线一致：单 Runtime、单权限、单 EventBus、Local First。

---

*本档为设计稿，未改动任何代码。API 为文件级，非向量查询。STOP — 待 Review。*
