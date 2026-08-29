# Xiao6 Knowledge Engine — Storage Spec & Migration (Knowledge Foundation v1.0)

> **Sprint**: Knowledge Engine Sprint v1.0 — Knowledge Foundation
> **Mode**: Design Only（不实现、不写代码；迁移方案为后续实现 Sprint 的蓝图）
> **Companion**: 继承 `KNOWLEDGE_ENGINE_ARCHITECTURE.md` §2–§3 + `KNOWLEDGE_SCHEMA.md`
> **Status**: 设计稿（待 Review）

---

## 0. 本档定位

定义 Knowledge Vault 的**物理存储布局、命名约定、治理规则**，以及从现有 4 类知识源**迁移到统一知识层**的完整方案。目标：所有知识以文件为唯一事实来源、Local First、git 跟踪、可回滚。

---

## 1. 物理布局（权威）

```
G:\Xiao6\knowledge\            # 仓库内、git 跟踪、Local First
├── index.md                        # MOC 根导航
├── projects/                       # 项目上下文（Xiao6 专属）
├── people/                         # 人物/实体知识卡
├── concepts/                       # 概念/技术/方法论
├── decisions/                      # 运营级决策/知识层 ADR
├── rules/                          # 运行规则/约束/红线
├── experiences/                    # 验证经验/方法/可用 Prompt
├── failures/                       # Bug/复盘/勿为之举
├── daily/                          # 策展型工作日志（canonical Daily Capture）
├── inbox/                          # 快速捕获/agent 建议
└── archive/                        # 冷/弃用知识
```

> 注：`.obsidian/` 配置目录在实现阶段由 Obsidian 打开 `knowledge/` 时自动生成，本 Sprint 不创建。

---

## 2. 命名约定

### 2.1 文件命名
- 稳定 slug，无空格，用 `-` 连接：`rules/permission-guard.md`、`failures/electron-click-through.md`。
- 带日期（日志/事件类）：`daily/2026-08-06.md`、`failures/2026-08-01-crash-recovery.md`。
- 禁止：中文空格、特殊字符、`#`/`[`/`]`。
- 文件名 ≠ `id`；`id` 在 frontmatter（重命名文件不影响引用，见 SCHEMA §2.1）。

### 2.2 目录 ↔ type 映射（强制一致）
| 目录 | `type` | 说明 |
|------|--------|------|
| `projects/` | `project` | 项目上下文 |
| `people/` | `person` | 人物/实体 |
| `concepts/` | `concept` | 概念/技术 |
| `decisions/` | `decision` | 运营决策 |
| `rules/` | `rule` | 规则/红线 |
| `experiences/` | `experience` | 经验/方法 |
| `failures/` | `failure` | 失败/复盘 |
| `daily/` | （无 type，日志） | 工作日志 |
| `inbox/` | `captured` | 未整理 |
| `archive/` | （任意，status=archived/deprecated） | 归档 |

### 2.3 `index.md`（MOC）
- 根导航，列出各域入口 + 关键索引（复用现有 `00_System/Index.md` MOC 模式）。
- 例：
```markdown
# Xiao6 Knowledge Map
## Rules
- [[Permission Guard 是唯一次要写权限]]
## Failures
- [[Electron 桌宠点击穿透]]
```

---

## 3. 治理规则（Storage 层）

1. **单一真相源**：Vault `.md` 文件。Backend 索引（SQLite）仅派生。
2. **人类编辑优先**：agent 只写 `inbox/`（`source:agent`）；人类确认后 `transition` 到正式域。
3. **无静默删除**：仅 `archived`/`deprecated`；git 保留全历史。
4. **git 即审计**：每次知识变更提交；可 diff/blame。
5. **权限门控**：写经 PermissionGuard；`rules/`/`decisions/` 高影响域需人类确认。
6. **跨项目隔离**：个人/跨项目知识（NovaKit/麦香岁月）**不吸收**，仅 `related_docs`/externallink 引用。
7. **与 `docs/` 边界**：`docs/` = 设计/治理/审计冻结树；`knowledge/` = 活知识层。治理级 `DECISION_*` 留 `docs/decisions/`，运营级决策落 `knowledge/decisions/` 并链接回治理级（见 ARCHITECTURE §3.5）。

---

## 4. 迁移方案（从 4 类现有源 → 统一知识层）

> 原则：增量、可回滚、git 跟踪、不破坏现有源直至确认切换。每步可独立提交。

### Step 1 — Vault 骨架
- 创建 `knowledge/` 全部目录 + 初始 `index.md`。
- 不动现有外部 vault / `docs/`。

### Step 2 — 迁移 `rules/`（高价值、低风险）
- 源：`C:\Users\Administrator\Documents\Obsidian Vault\00_System\*.md`
  （Agent_Constitution / Knowledge_Rules / Execution_Rules / Tool_Policy / Tool_Registry / Memory_System / Workflow / 等）。
- 动作：复制到 `knowledge/rules/`，**剔除纯个人 Agent 条款**（如"不修改 MEMORY.md"属个人 vault 规则），保留 Xiao6 相关运行规则；补 frontmatter（`type:rule`, `status:consolidated`, `source:human`）。

### Step 3 — 迁移 `failures/`
- 源：`02_Bug/*.md` + 根级 `BUG_WALL.md`。
- 动作：迁入 `knowledge/failures/`，补 frontmatter（`type:failure`）；`BUG_WALL.md` 拆为多条 failure 笔记（按 bug 原子化）。

### Step 4 — 迁移 `experiences/`
- 源：`05_Library/` + `03_Prompt/` + `04_AI/`。
- 动作：迁入 `knowledge/experiences/`；验证过的 Prompt 标 `tags:[prompt]`；技术方法标 `tags:[method]`；补 frontmatter。

### Step 5 — 迁移 `concepts/` + `people/`
- 源：`05_Library` 概念部分 + 实体笔记。
- 动作：概念 → `concepts/`；人物/实体（用户、协作者、Agent 身份）→ `people/`；补 frontmatter。

### Step 6 — 迁移 `projects/`
- 源：`01_Projects/`（Xiao6 相关）。
- 动作：Xiao6 项目上下文 → `projects/`；外部项目（NovaKit/麦香岁月）**不迁移**，在 `projects/` 建一个索引笔记以 `related_docs`/externallink 引用。

### Step 7 — 迁移 `decisions/`
- 源：`docs/decisions/DECISION_*.md` + `CR-*.md`。
- 动作：**治理级留 `docs/decisions/`**（冻结）。在 `knowledge/decisions/` 建"知识层 ADR"笔记解释运营决策，通过 `related_docs` 链接治理级决策（不复制）。

### Step 8 — 建立 `daily/`（canonical Daily Capture）
- 迁移 Obsidian `Daily/2026-08-01.md` → `knowledge/daily/2026-08-01.md`，补 frontmatter。
- 约定：此后 Xiao6 策展工作日志落 `knowledge/daily/`；会话草稿仍留 WorkBuddy 内存（不进 Vault）。

### Step 9 — 构建 `index.md` MOC
- 链接全部域入口与关键笔记；验证 Obsidian Graph 连通。

### Step 10 — 收尾（实现阶段，需 Review 批准）
- 更新 `AI_BOOTSTRAP.md` 反映 Knowledge Sprint 状态；在 AI 入口协议加 Knowledge 段。
- 旧外部 vault 保留为个人第二大脑，不删除（回滚安全）。

### 回滚
- 每步独立 git 提交；任一迁移出问题 `git revert` 该步即可。
- 不删除任何源文件直至 Step 10 确认；确认后外部 vault 可保留作个人用途。

---

## 5. Backend 派生索引（可选、可丢弃）

- 实现阶段可建 SQLite 存 frontmatter 索引 + 关系指针（`id`↔路径↔`links`）。
- **绝不存正文**；重建索引不得丢失原文。
- 向量嵌入（若未来检索增强阶段启用）= 独立 scope，结果本地缓存，非真相源。
- 本 Sprint 不实现；仅定边界。

---

## 6. 开放问题（待 Review）
- Q1：`knowledge/decisions/` 是否需镜像全部 `docs/decisions/` 摘要？→ 建议仅运营级 + 链接。
- Q2：外部项目引用方式（externallink vs `related_docs`）统一标准？
- Q3：Daily Capture 与 WorkBuddy 会话内存的自动桥接是否必要？（本 Sprint 建议手动策展，避免自动噪声）

---

*本档为设计稿，未改动任何代码。迁移方案为后续实现 Sprint 蓝图。STOP — 待 Review。*
