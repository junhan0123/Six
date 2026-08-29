# Xiao6 Knowledge Engine — Architecture (Knowledge Foundation v1.0)

> **Sprint**: AI OS · Knowledge Engine Sprint v1.0 — Knowledge Foundation
> **Mode**: Audit → Architecture → Design → Report → STOP
> **Discipline**: 纯架构/文档/接口/数据流设计。**本 Sprint 不修改任何代码、不实现 RAG/Embedding/向量数据库/Obsidian 集成、不新增 AI 功能。**
> **Baseline**: 继承并延展 `docs/ai-os/03_KNOWLEDGE_ENGINE.md`（冻结架构基线）+ ADR-002（知识即文件）。
> **Status**: 设计稿（待 Review）

---

## 0. 本档定位

本文档是 Xiao6 **统一知识层（Knowledge Layer）** 的权威架构定义，回答四件事：

1. 现有知识组织方式的审计事实（§1）。
2. 统一知识层的整体架构与 7 大知识域文件结构（§2–§3）。
3. Knowledge 与 Memory / Workflow / Goal / Context Engine 的关系图（§4）。
4. Local-First 知识治理总览与红线（§5）。

配套文档（同目录）：
- `KNOWLEDGE_SCHEMA.md` — 知识文档 Schema（元数据/引用/标签/生命周期）。
- `KNOWLEDGE_STORAGE_SPEC.md` — 目录布局、命名约定、治理规则、迁移方案。
- `KNOWLEDGE_API_SPEC.md` — 仅设计的文件级 API 契约。
- `KNOWLEDGE_ROADMAP.md` — 分阶段实施路线图。
- `KNOWLEDGE_ENGINE_SUMMARY.md` — 总览 + STOP + 下一阶段可执行 Prompt。

---

## 1. 审计事实（现有知识组织方式）

Sprint 以只读方式审计了 4 类现有知识源，确认当前知识**碎片化、无统一 schema、不在项目 git 内、跨项目与个人知识混杂**。

### 1.1 Obsidian Vault — `C:\Users\Administrator\Documents\Obsidian Vault`
- **规模**：29 个 `.md` 文件，早期稀疏状态。
- **结构**：`00_System/`(19 个规则/Agent 文件)、`01_Projects/`(AI_Workspace/NovaKit/麦香岁月/Project_Index)、`02_Bug/`、`03_Prompt/`、`04_AI/`、`05_Library/`(空)、`Daily/`(仅 1 篇)、`Inbox/`(空)。
- **未初始化**：未发现 `.obsidian` 配置目录（尚未在 Obsidian 应用中作为 vault 打开，或配置在别处）。
- **格式 convention**：
  - 自由 markdown；`Project_Index.md` 用标准 `[Name](path)` 链接；`00_System/Index.md` 是一份 MOC（Map of Content）导航页——**良好模式，复用**。
  - `Knowledge_Rules.md` 定义目录职责 + 判断规则（"是否产生长期价值？"）——**良好模式，复用为治理判断**。
  - `Agent_Constitution.md` 定义身份与规则，含"不修改 MEMORY.md、USER.md""不迁移已有文件内容"——注意：这是**个人 vault 的规则**，对本项目级知识层仅作精神参考（见 §3.5）。
  - `Daily/2026-08-01.md` 采用 `## <任务> 完成 / ## 下一步方向` + commit 哈希——**良好溯源 convention，复用**。
- **问题**：
  - ❌ **在 Xiao6 git 仓库之外**（非 Local First，未随项目版本控制）。
  - ❌ **混杂个人/跨项目知识**（NovaKit、麦香岁月游戏）与通用 AI 工作区。
  - ❌ **无统一 frontmatter / 生命周期状态**（文件无 YAML 元数据）。
  - ❌ **无 Decisions/Rules/Experiences/Failures 一等公民域**（Rules 散在 `00_System`，Failures 在 `02_Bug`，Experiences 散在 `05_Library`/`04_AI`）。
  - ❌ `05_Library`/`Inbox` 空置，使用不一致。

### 1.2 用户级 MEMORY.md — `~/.WorkBuddy/MEMORY.md`（13KB）
- 扁平自由格式**跨项目个人记忆**（Agnes/Claude Code/Hermes/TTS/Godot/桌面路径/游戏项目）。
- ❌ **非 Xiao6 专属**；❌ 未按知识域结构化；无 frontmatter/标签/链接。
- **结论**：保持为跨项目个人记忆，**不吸收进 Xiao6 知识层**（关注点分离：个人 vs 项目）。

### 1.3 Daily Log（三处分散）
- (a) Obsidian `Daily/2026-08-01.md` — 任务完成日志（含 commit 哈希）。
- (b) WorkBuddy 会话内存 `.workbuddy/memory/YYYY-MM-DD.md` — **本会话活动日志**（working_memory 来源），会话级、非 Xiao6 产物。
- (c) Xiao6 项目自身 `.workbuddy/memory/` — **空**，尚无项目级每日日志。
- **问题**：每日日志三处分散、无权威归属。知识层须定义**唯一 canonical Daily Capture 位置**。

### 1.4 项目文档 — `G:\Xiao6\docs/`
- 巨大文档树：`architecture/ archive/ audits/ decisions/ design/ frozen/ memory/ reference/ releases/ ui-foundation/ ui-ux-polish/ ai-os/` + ~90 份根级报告。
- `docs/decisions/` — 已存在 8 份 `DECISION_*.md` + `CR-*.md`（**Decisions 域已作为项目文档存在**）。
- `docs/ai-os/03_KNOWLEDGE_ENGINE.md` — **冻结的知识引擎架构基线**（本 Sprint 必须继承延展，不得矛盾）。
- `docs/memory/` — Memory Engine Sprint 交付物（架构文档，**非知识内容**）。
- **问题**：`docs/` 是**设计/治理/文档树**，不是知识库。知识隐含于这些文档但未结构化为可查询知识层；决策记录未接入知识图谱；各文档无统一 schema。

### 1.5 与冻结基线的关系（关键）
- `03_KNOWLEDGE_ENGINE.md` 已定义：Vault=真相源、SQLite/向量=派生、Sync Bridge、结构 `daily/project/inbox/archive/people/concepts`、生命周期 `captured→reviewed→linked→consolidated→archived`、红线。
- `02_MEMORY_ENGINE.md`：L4 = 指向 Knowledge 的索引+摘要（Memory 引用 Knowledge，**不复制正文**）。
- `13_ARCHITECTURE_DECISIONS.md` ADR-002：**知识即文件**（冻结）。
- `AI_BOOTSTRAP.md`：明确"随后：Knowledge OS Sprint"——确认本 Sprint 是规划中的下一步。
- **本 Sprint 的 7 域模型 = 对 `03` 结构的精化与扩展**（新增 Decisions/Rules/Experiences/Failures），核心原则（文件即真相、人类编辑优先、非数据库）**完全继承**。

---

## 2. 整体架构

### 2.1 核心断言（重申，强化）
> **知识层不是数据库，不是 RAG，不是向量索引。**
> 知识层是**以 `.md` 文件为唯一事实来源的人类可读、可导航、可链接、可拥有的知识组织面**。
> 任何索引（标签表、反向链接表、未来可选的向量嵌入）都是**派生的、可丢弃的、非权威的**。

这与 ADR-002、冻结 `03` 完全一致。本 Sprint 明确**将 RAG/Embedding/向量检索推迟为未来的"检索增强"阶段（明确超出本 Sprint 范围）**，以避免把知识层重新做成数据库。

### 2.2 三件套（继承 `03`，明确边界）
```
┌──────────────────────────────────────────────────┐
│  Knowledge Vault（知识真相源 · 文件）               │
│  projects/ people/ concepts/ decisions/ rules/      │
│  experiences/ failures/ daily/ inbox/ archive/      │
│  index.md（MOC）                                     │
│  [[wikilinks]]  #tags  graph  frontmatter           │
│  人类可读、可手写、可用 Obsidian 浏览                │
└───────────────────┬──────────────────────────────┘
                    │  Sync Bridge（人类编辑优先；仅索引镜像）
┌───────────────────▼──────────────────────────────┐
│  Backend（派生索引 · 可选、可丢弃）                  │
│  SQLite（frontmatter 索引/关系指针） + 未来可选向量  │
│  不重造链接/标签/图谱逻辑；正文只在 Vault           │
└───────────────────┬──────────────────────────────┘
                    │  文件级查询接口
┌───────────────────▼──────────────────────────────┐
│  Knowledge Engine API（文件级：read/query/          │
│  reference/suggest/update/transition）· 设计态      │
└──────────────────────────────────────────────────┘
```
- **Vault = 知识层**：语义关系（链接/标签/图谱）是一等公民，存于 `.md`。
- **Backend = 派生索引**：仅存 frontmatter 索引、关系指针；**绝不存正文真相**。
- **Bridge = 一致性**：Vault 文件变更 → 重建索引；索引变更（如合并）→ 仅更新索引，不改写正文。
- **API = 文件级接口**：对 `.md` 的读取/引用/更新/生命周期迁移；**不是向量查询 API**。

### 2.3 物理位置决策（Review 决策点 D1）
- **推荐**：知识层 Vault 落于 **`G:\Xiao6\knowledge/`**（仓库内、git 跟踪、Local First、属于单一事实源）。
- **理由**：Local First 要求单一 git 仓库；现有外部 vault 在仓库外，违背该原则。
- **迁移**：将现有外部 vault 中 **Xiao6 相关知识**迁入 `knowledge/`；个人/跨项目知识（NovaKit/麦香岁月）**不吸收**，仅以 wikilink/externallink 引用。
- **Obsidian 集成**：实现阶段用 Obsidian 打开 `knowledge/` 文件夹即完成"融入小6"，无需自建 Obsidian 同步逻辑（文件即真相，Obsidian 只是编辑 UI）。

---

## 3. 统一知识层文件结构（7 域 + 横切）

在冻结 `03` 的 `daily/project/inbox/archive/people/concepts` 基础上，精化为 **7 个一等公民知识域 + 3 个横切容器 + 1 个 MOC**。

```
knowledge/
├── index.md                  # MOC（Map of Content）根导航
├── projects/                 # 项目上下文（Xiao6 专属；外部项目仅链接）
├── people/                   # 人物/实体知识卡（用户、协作者、Agent 身份）
├── concepts/                 # 概念/技术主题/方法论/领域知识
├── decisions/                # 运营级决策/ADR（知识层；治理级 DECISION_* 见 §3.5）
├── rules/                    # 运行规则/约束/策略/红线（迁移自 00_System）
├── experiences/              # 验证过的经验/方法/可用 Prompt（迁移自 05_Library/03_Prompt/04_AI）
├── failures/                 # Bug 记录/复盘/勿为之举（迁移自 02_Bug + BUG_WALL.md）
├── daily/                    # 策展型工作日志（canonical Daily Capture）
├── inbox/                    # 快速捕获、未整理（agent 建议落此处）
└── archive/                  # 冷/弃用知识（不删除，仅归档/标记 deprecated）
```

### 3.1 域职责映射（对接现有散布知识）
| 新域 | 承接现有 | 内容 |
|------|---------|------|
| `projects/` | `01_Projects/`(Xiao6 相关) | 项目上下文、结构、状态 |
| `people/` | 实体笔记 | 用户画像、协作者、Agent 身份卡 |
| `concepts/` | `05_Library` 概念部分 | 技术概念、方法论、领域知识 |
| `decisions/` | 运营决策 | 功能级"为何选 X"、知识层 ADR |
| `rules/` | `00_System/*`(Agent_Constitution/Knowledge_Rules/Execution_Rules/Tool_Policy…) | 运行规则、约束、红线 |
| `experiences/` | `05_Library`/`03_Prompt`/`04_AI` | 验证方法、可用 Prompt、踩坑对策 |
| `failures/` | `02_Bug/` + `BUG_WALL.md` | Bug 根因、复盘、勿为之举 |

### 3.2 横切容器
- `daily/`：策展型工作日志（人类/agent 复核后的），带 commit 哈希溯源（复用现有 Daily convention）。会话级草稿仍留 WorkBuddy 内存，不入 Vault。
- `inbox/`：Quick Capture。Agent 生成的知识建议**只落此处**，标 `source:agent`，待人类确认后迁入正式域。
- `archive/`：冷知识 / `deprecated` 知识。机器不自动删除。

### 3.3 `index.md`（MOC）
根导航页，列出各域入口与关键索引（复用 `00_System/Index.md` 的 MOC 模式）。Obsidian Graph 视图亦以 `index.md` 为中枢。

### 3.4 命名约定（详见 STORAGE_SPEC）
- 文件名：`domain/YYYYMMDD-<slug>.md` 或 `domain/<slug>.md`（稳定、可读、无空格）。
- 每个文件含 YAML `frontmatter`（见 SCHEMA）：`id`(稳定唯一)、`type`、`status`、`tags`、`source`、`created`/`updated`。

### 3.5 与 `docs/decisions/` 的边界（Review 决策点 D2）
- **治理级决策**（`DECISION_*.md` / `CR-*.md`）留在 `docs/decisions/`——冻结、审计日志风格，是项目宪法性记录。
- **运营级决策/知识层 ADR** 落 `knowledge/decisions/`——解释"某功能为何这样实现"，通过 `related_docs` 链接回治理级决策。
- 二者不重复；知识层决策引用治理级决策，保持单一权威。

---

## 4. 关系图（Knowledge ↔ Memory / Workflow / Goal / Context Engine）

```
                         ┌─────────────────────────────┐
                         │   Human (编辑 Vault .md)     │
                         └──────────────┬──────────────┘
                                        │ 手写/修订（优先）
                                        ▼
┌──────────────────────────────────────────────────────────────────┐
│  Knowledge Vault (knowledge/*.md)  — 唯一事实来源                    │
│  projects/people/concepts/decisions/rules/experiences/failures/...  │
└──────┬───────────────────────────────────────────┬───────────────┘
       │ Sync Bridge（索引镜像）                     │ KnowledgeEngine API
       ▼                                             │ （read/query/reference/
┌──────────────────────┐                            │  suggest/update/transition）
│ Backend 派生索引       │                            ▼
│ (SQLite frontmatter)  │                  ┌────────────────────────────┐
└──────────┬───────────┘                  │  Knowledge Engine (文件级)   │
           │ L4 索引指针                    │  运行于单 Runtime 内         │
           ▼                               └─────────┬──────────────────┘
┌──────────────────────┐                            │ publish knowledge:*
│ Memory Engine L4      │◄─── 引用(不复制) ──────────┘ (EventBus 领域事件)
│ (指向 Knowledge 的     │                │
│  索引+摘要)            │                ▼
└──────────┬───────────┘        ┌──────────────────────┐
           │                    │  PermissionGuard      │◄── 所有写经此
           ▼                    │  (单权限)              │
┌──────────────────────┐        └──────────────────────┘
│ Goal Engine           │◄─── related_goals / related_knowledge（id 引用）
│ Workflow Engine       │◄─── 步骤引用知识作参考材料（id 引用）
│ Context Engine        │◄─── 只读订阅 knowledge:*；作为 L8 检索 Source 装配上下文
└──────────────────────┘
```

### 4.1 边界原则（冻结红线一致）
- **Knowledge ↔ Memory**：Memory L4 = 指向 Knowledge 的**索引+摘要**（按 `id`/路径）；Knowledge = 正文真相。二者经 Sync Bridge 一致。**Memory 绝不复制知识正文**。
- **Knowledge ↔ Goal**：Goal 可引用知识（`related_knowledge`）；知识可引用 Goal（`related_goals`）。**仅 id 引用，无共享状态**。
- **Knowledge ↔ Workflow**：Workflow DAG 步骤可把知识作参考材料引用；`experiences/` 常即一个方法/工作流。**按 id 链接**。
- **Knowledge ↔ Context Engine**：Context Engine **只读**通过 `KnowledgeEngine.read/query` 取知识装配系统提示上下文——这是知识的**首要消费路径**；知识是 L8 检索管线中的一个 Source。
- **Knowledge ↔ EventBus**：`knowledge:written` / `knowledge:linked` / `knowledge:state_changed` 领域事件；消费者：Context Engine（重索引）、Memory L4（更新索引）、Surface/Proactive（感知）。
- **Knowledge ↔ Obsidian**：Obsidian 应用 = 人类编辑 Vault 文件的 UI。Vault 文件即知识，无需自建"集成"逻辑（超出本 Sprint 的"Obsidian 集成实现"红线；本 Sprint 仅设计文件结构，Obsidian 打开文件夹即完成融入）。

---

## 5. Local-First 知识治理总览

### 5.1 五大支柱（对齐 `09_LOCAL_FIRST.md`）
1. **驻留**：知识文件在本地 `G:\Xiao6\knowledge/`，git 跟踪。
2. **离线**：无网可读写、可浏览、可链接。
3. **无硬云依赖**：云同步（若启用）可选、非权威、不破坏本地真相。
4. **隐私**：知识纯本地，不外传。
5. **可读拥有**：任意文本编辑器/Obsidian 可读写，无专有二进制格式。

### 5.2 治理规则（要点，细则见 STORAGE_SPEC/GOVERNANCE）
- **单一真相源** = Vault 内 `.md` 文件。
- **人类编辑优先**：Agent `suggest` → `inbox/` → 人类确认 → 迁入正式域；Agent 绝不覆盖人类手写正文。
- **版本即审计**：git 是历史/审计日志，每个知识文件可 diff。
- **权限门控**：知识写经 PermissionGuard；高影响域（`rules/`/`decisions/`）需人类确认。
- **生命周期**：无静默删除；仅 `archived`/`deprecated`。

### 5.3 红线（延展冻结 `03` + 本 Sprint 新增）
1. 禁止把知识塞进 SQLite/向量库作为真相源（ADR-002）。
2. 禁止机器覆盖人类手写 Vault 正文。
3. **禁止将 RAG/Embedding/向量检索作为本 Sprint 实现范围**（推迟为未来检索增强阶段）。
4. 禁止第二知识源（第二 vault / 第二 knowledge store）。
5. 禁止知识写入绕过 PermissionGuard / EventBus。
6. 禁止知识层直接持有 Memory/Goal/Workflow 状态（仅按 id 引用）。

---

## 6. 开放决策点（待 Review）
- **D1**：Vault 落 `G:\Xiao6\knowledge/`（推荐）vs 保留外部 vault 并链接。
- **D2**：`knowledge/decisions/` 与 `docs/decisions/` 的边界（本档方案：治理级留 `docs/`，运营级落 `knowledge/`）。
- **D3**：Daily Capture 权威归属（本档方案：Vault `daily/` = 策展日志；会话草稿留 WorkBuddy 内存）。
- **D4**：Sync Bridge 触发时机（文件监听 vs 轮询+mtime）——实现阶段决策，本 Sprint 仅定契约。

---

*本档为设计稿，未改动任何代码。继承冻结 `03` + ADR-002。STOP — 待 Review。*
