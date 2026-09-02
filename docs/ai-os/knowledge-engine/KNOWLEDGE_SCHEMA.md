# Xiao6 Knowledge Engine — Document Schema (Knowledge Foundation v1.0)

> **Sprint**: Knowledge Engine Sprint v1.0 — Knowledge Foundation
> **Mode**: Design Only（不实现、不写代码）
> **Companion**: 继承 `KNOWLEDGE_ENGINE_ARCHITECTURE.md` §3；本档定义每条知识文档的**元数据/引用/标签/生命周期**规范。
> **Status**: 设计稿（待 Review）

---

## 0. 本档定位

定义 Knowledge Vault 中**每一条知识文档**的统一结构，使知识：
- 机器可解析（frontmatter）、人类可读（正文）；
- 可链接（wikilink）、可标签（tags）、可追溯（provenance）；
- 有生命周期状态与版本溯源。

所有 Vault 文档**必须**遵循本 Schema。既有文档迁移时补齐 frontmatter（见 STORAGE_SPEC 迁移方案）。

---

## 1. 文档物理结构

每条知识 = 一个 `.md` 文件，由两部分组成：

```markdown
---
<YAML frontmatter：机器可解析元数据>
---

<正文：人类可读知识内容，可用 [[wikilinks]] 与 #tags>
```

- 正文鼓励使用 `[[笔记名]]` 双向链接与 `#区域/子标签` 标签。
- 一个文件 = 一个知识单元（原子性：一篇讲清一件事）。

---

## 2. Frontmatter 字段规范

### 2.1 必填字段
| 字段 | 类型 | 取值/格式 | 说明 |
|------|------|----------|------|
| `id` | string | `know-<domain>-<slug>` | **稳定唯一 ID**，不依赖文件名（重命名文件不影响引用）。例：`know-rule-permission-guard` |
| `type` | enum | `project\|person\|concept\|decision\|rule\|experience\|failure` | 知识域，对应目录 |
| `title` | string | 人类可读标题 | 与 `index.md`/Obsidian 标题一致 |
| `status` | enum | `captured\|reviewed\|linked\|consolidated\|archived\|deprecated` | 生命周期状态（§4） |
| `created` | date | `YYYY-MM-DD` | 创建日期 |
| `updated` | date | `YYYY-MM-DD` | 末次更新日期 |
| `source` | enum | `human\|agent` | 作者：人类手写 / Agent 生成 |

### 2.2 可选字段
| 字段 | 类型 | 说明 |
|------|------|------|
| `tags` | string[] | `#区域/子标签`，如 `["agent/runtime","redline"]` |
| `links` | string[] | 显式关联 `id` 列表（正文 `[[wikilink]]` 亦计入，二者互补） |
| `confidence` | enum | `high\|medium\|low`——仅 `source:agent` 时填，人类知识默认不填 |
| `related_goals` | string[] | 关联 Goal Engine 的 `goal_id`（id 引用，无共享状态） |
| `related_docs` | string[] | 关联冻结设计/治理文档路径，如 `["docs/decisions/DECISION_003_MEMORY_SINGLE_SOURCE.md"]` |
| `related_knowledge` | string[] | 关联其他知识 `id`（冗余于 wikilink，便于机器索引） |
| `provenance` | string | 溯源：commit 哈希 / 会话 id / 来源 URL（agent 生成必填） |
| `owner` | string | 责任归属（人/Agent/团队） |
| `review_due` | date | 待人类复核截止日（`source:agent` 落 `inbox/` 时填） |

### 2.3 示例
```yaml
---
id: know-rule-permission-guard
type: rule
title: Permission Guard 是唯一次要写权限
status: consolidated
created: 2026-08-06
updated: 2026-08-06
source: human
tags: [agent/runtime, redline, permission]
links: [know-decision-single-runtime, know-concept-execution-channel]
related_docs: [docs/decisions/DECISION_005_PERMISSION_POLICY.md]
confidence: high
owner: 老板
---
```

---

## 3. 引用与链接规范

### 3.1 Wikilink（正文）
- 格式：`[[目标笔记标题]]` 或 `[[目标笔记标题|显示文本]]`。
- Obsidian 原生双向链接 + 反向链接 + Graph，是知识图谱的一等公民。
- 机器索引时解析 wikilink → 对应文件 `id`（通过文件名或 frontmatter `title` 解析）。

### 3.2 显式 links（frontmatter）
- `links` / `related_knowledge` 用 `id` 而非标题，避免重命名断裂。
- 二者互补：wikilink 供人类浏览图谱；`id` 供机器精确索引。

### 3.3 跨域引用
- **引用 Goal/Workflow/Memory**：仅用 `related_goals` / `related_docs` 的 id 或路径，**不复制其状态**。
- **引用外部项目/个人知识**（NovaKit/麦香岁月）：用 Obsidian `externallink` 或 `related_docs` 外链，**不吸收进 Vault**（见 ARCHITECTURE §3.5）。

### 3.4 标签规范
- 层级标签：`#域/子域`，如 `#agent/runtime`、`#ui/token`、`#bug/crash`。
- 语义标签：`#redline`（红线）、`#decision`（决策）、`#lesson`（经验）。
- 禁止在 SQLite/向量内重造标签逻辑（ADR-002 / 冻结 `03` 红线）。

---

## 4. 生命周期状态机

继承冻结 `03` 的 `captured→reviewed→linked→consolidated→archived`，并增加 `deprecated`：

```
  captured(inbox/agent建议)
      │
      ▼
  reviewed(人类复核)
      │
      ▼
  linked(接入 concepts/people/projects 关系网)
      │
      ▼
  consolidated(已 distill、可检索、高可信)
      │
      ├──────────────► archived(冷但有效，不删除)
      │
      └──────────────► deprecated(被取代/过时，保留溯源，不删除)
```

| 状态 | 含义 | 可检索 | 机器可写 |
|------|------|--------|---------|
| `captured` | 刚捕获/agent 建议，未分类 | 限 inbox | 仅 agent→inbox |
| `reviewed` | 人类复核过，待链接 | 是 | 人类 |
| `linked` | 已接入关系网 | 是 | 人类 |
| `consolidated` | 已蒸馏、稳定可信 | 是（优先） | 人类 |
| `archived` | 低频冷知识 | 是（降权） | 人类 |
| `deprecated` | 被取代/过时 | 否（仅溯源） | 人类 |

- **状态迁移**：经 `KnowledgeEngine.transition(path, state)`（设计态，见 API_SPEC），每次迁移 publish `knowledge:state_changed`。
- **无静默删除**：机器不自动删除知识；归档/弃用由人类或经确认的生命周期策略执行。
- **agent 权限**：agent 只能创建 `captured`（落 `inbox/`）或建议状态迁移，且 `source:agent`+`confidence` 标注；`consolidated`/`deprecated` 须人类确认。

---

## 5. 版本与溯源

- **版本真相 = git**：每个知识文件的提交历史即版本链，可 diff/blame，无需文件内版本号。
- **溯源字段**：`provenance`（commit/会话/URL）记录知识来源；agent 生成必填。
- **不覆盖**：agent 更新知识 = 新增/建议 + 追加 provenance，不静默改写人类正文。
- **冲突策略**：人类正文永远胜出；索引冲突以 Vault 为准重建（继承冻结 `03` Sync Bridge 契约）。

---

## 6. 与 Memory L4 的边界（Schema 视角）

- Knowledge 文档 frontmatter 含 `id`；Memory L4 存 **`{knowledge_id, summary, path}` 索引**，不存正文。
- 同步：Vault 文件变更 → Sync Bridge 更新 Memory L4 索引；Memory 不反向写正文。
- Schema 中 `related_*` 字段是**引用**，不是知识副本。

---

## 7. 校验规则（实现阶段用，本 Sprint 仅定义）

- 每个 Vault `.md` 必须含合法 YAML frontmatter 且 `id`/`type`/`status`/`source` 齐全。
- `id` 全局唯一（跨域不重）。
- `status` ∈ 枚举；`source:agent` 必须含 `confidence`+`provenance`。
- `type` 与所在目录一致（`type:rule` ↔ `rules/`）。
- `links`/`related_*` 指向的 `id` 须存在（或标 `pending`）。
- 校验失败 → 落 `inbox/` 待人工修复，不阻塞读取。

---

*本档为设计稿，未改动任何代码。STOP — 待 Review。*
