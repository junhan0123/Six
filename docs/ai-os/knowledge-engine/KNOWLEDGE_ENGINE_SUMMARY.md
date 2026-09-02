# Xiao6 Knowledge Engine Sprint v1.0 — Knowledge Foundation · SUMMARY

> **Sprint**: Knowledge Engine Sprint v1.0 — Knowledge Foundation
> **Mode**: Audit → Architecture → Design → Report → **STOP**
> **Discipline**: 纯设计。未改动任何代码；未实现 RAG/Embedding/向量库/Obsidian 集成；未新增 AI 功能。
> **Status**: ✅ 设计完成 · 🛑 **STOP 等待 Review**

---

## 1. 完成摘要

本 Sprint 建立了 Xiao6 **统一知识层（Knowledge Layer）** 的设计地基，明确其**不是 RAG、不是向量数据库、不是第二 Memory**，而是**以 `.md` 文件为唯一事实来源的人类可读知识组织面**。设计继承并延展冻结架构基线 `docs/ai-os/03_KNOWLEDGE_ENGINE.md` 与 ADR-002（知识即文件），全程零代码改动、完全兼容 L0 冻结红线。

### 交付物（6 份，落盘 `docs/ai-os/knowledge-engine/`）
| # | 文档 | 内容 |
|---|------|------|
| 1 | `KNOWLEDGE_ENGINE_ARCHITECTURE.md` | 审计事实 + 整体架构 + 7 域文件结构 + 关系图 + Local-First 治理 |
| 2 | `KNOWLEDGE_SCHEMA.md` | 文档 Schema：frontmatter 元数据 / wikilink·tags / 生命周期状态机 / 溯源 |
| 3 | `KNOWLEDGE_STORAGE_SPEC.md` | 目录布局 / 命名约定 / 治理规则 / **10 步迁移方案** |
| 4 | `KNOWLEDGE_API_SPEC.md` | **文件级 API 契约**（read/query/reference/suggest/update/link/transition）+ 事件 + 权限 |
| 5 | `KNOWLEDGE_ROADMAP.md` | K0(设计)→K1(Vault+迁移)→K2(API)→K3(Context)→K4(Sync)→K5(检索增强,未来) |
| 6 | `KNOWLEDGE_ENGINE_SUMMARY.md` | 本文件 |

---

## 2. 审计关键发现

- **Obsidian Vault**（外部 `C:\Users\Administrator\Documents\Obsidian Vault`）：29 文件、仓库外、混杂个人/跨项目、无 frontmatter/生命周期；其 `00_System`(rules)、`02_Bug`(failures)、`05_Library`/`04_AI`(experiences) 直接映射 3 个知识域。
- **用户级 MEMORY.md**：跨项目个人记忆，**不吸收**进项目知识层（关注点分离）。
- **Daily Log**：三处分散（Obsidian Daily / WorkBuddy 内存 / 空项目 .workbuddy）——需 canonical 归属。
- **项目 docs/**：`docs/decisions/` 已存 Decisions；`docs/ai-os/03_KNOWLEDGE_ENGINE.md` 是冻结基线，本 Sprint 延展而非矛盾。

---

## 3. 核心设计决策

1. **知识层 = 文件**：`.md` 唯一真相；索引（SQLite/未来向量）派生可弃。
2. **7 域 + 横切**：`projects/people/concepts/decisions/rules/experiences/failures` + `daily/inbox/archive` + `index.md`(MOC)。精化冻结 `03` 结构。
3. **物理位置**：推荐落 `G:\Xiao6\knowledge/`（仓库内、git、Local First）；迁移外部 vault 中 Xiao6 相关知识，个人/跨项目仅引用。
4. **API = 文件级**：非向量查询；所有写经 PermissionGuard + EventBus（`knowledge:*` 提案）。
5. **RAG/Embedding 推迟**：明确为未来 K5"检索增强"，绝不取代文件真相源。
6. **关系图**：Knowledge 与 Memory(L4 索引)/Goal/Workflow 仅 id 引用；Context Engine 是首要只读消费者（L8 Source）。

---

## 4. 纪律红线检查（全程合规）

- ✅ 零代码改动（仅新增 6 份 `.md` 设计文档）。
- ✅ 未实现 RAG/Embedding/向量库/Obsidian 集成。
- ✅ 未新增 AI 功能。
- ✅ 继承冻结 `03` + ADR-002，无矛盾。
- ✅ 兼容 L0 红线：单 Runtime / 单权限 / 单 EventBus / Local First / 无 God Module / 增量演进。
- ✅ 事件契约 DOMAIN=71/SYSTEM=8 未改动（仅提案 `knowledge:*` 待中央合约追加）。

---

## 5. 待 Review 决策点
- **D1**：Vault 落 `G:\Xiao6\knowledge/`（推荐）vs 保留外部 vault 链接。
- **D2**：`knowledge/decisions/`(运营级) 与 `docs/decisions/`(治理级) 边界。
- **D3**：Daily Capture 权威归属（Vault `daily/` = 策展日志）。
- **D4**：Sync Bridge 触发时机（监听 vs 轮询+mtime，实现阶段定）。

---

## 6. 当前项目状态
- 本 Sprint 处于 **STOP（设计完成，待 Review）**。
- 现有运行时/代码未受任何影响；知识层为新增文件树，不影响 `server.py`/前端/事件合约。
- 冻结 `03` 与 ADR-002 仍为权威架构基线，本 Sprint 文档是其 Foundation 实现蓝图。

---

## 7. 下一阶段建议
Review 批准后进入 **K1（Vault 脚手架 + 高价值迁移）**：创建 `knowledge/` 骨架、迁移 `rules/failures/experiences`、补 frontmatter、建 MOC。此阶段仍低风险、可回滚、git 跟踪。

---

## 8. 下一阶段完整可执行 Prompt（供 Review 后直接启用）

```
进入 Xiao6 Knowledge Engine Sprint v1.0 — K1（Vault 脚手架 + 高价值迁移）。

背景：
- 设计已冻结于 docs/ai-os/knowledge-engine/（ARCHITECTURE/SCHEMA/STORAGE_SPEC/API_SPEC/ROADMAP/SUMMARY 六份）。
- 继承冻结基线 docs/ai-os/03_KNOWLEDGE_ENGINE.md + ADR-002（知识即文件）。
- L0 红线全程有效（单 Runtime/单权限/单 EventBus/Local First/无 God Module/增量演进）。

目标（K1）：
1. 创建 G:\Xiao6\knowledge\ 全目录（projects/people/concepts/decisions/rules/experiences/failures/daily/inbox/archive）+ index.md MOC。
2. 按 KNOWLEDGE_STORAGE_SPEC.md 迁移方案 Step 2–9，先迁高价值低风险域：
   - rules/ ← 外部 vault 00_System/*.md（剔除纯个人 Agent 条款，补 frontmatter type:rule）
   - failures/ ← 外部 vault 02_Bug/*.md + 根 BUG_WALL.md（原子化拆分，type:failure）
   - experiences/ ← 外部 vault 05_Library/ + 03_Prompt/ + 04_AI/（type:experience，标 prompt/method 标签）
3. 每条补合规 frontmatter（SCHEMA §2：id/type/status/source/created/updated/tags…）。
4. 建立 index.md MOC，链接各域入口。

纪律：
- 纯文件迁移 + 补 frontmatter 脚本（脚本本身属 K1 交付）；不写 Runtime 业务逻辑。
- 个人/跨项目知识（NovaKit/麦香岁月）不吸收，仅 related_docs/externallink 引用。
- 每步独立 git 提交，可回滚。
- 不动 server.py/前端/事件合约；不在 K1 实现 KnowledgeEngine API（那是 K2）。

验收：
- Obsidian 打开 knowledge/ 可浏览图谱；frontmatter 静态校验通过；git 可回滚。
- 交付 K1 报告 + 更新 memory。随后 STOP 等 Review 再进 K2。
```

---

*🛑 STOP — 设计完成，等待人工 Review 批准。未经批准不得进入 K1 实现、不得修改任何代码。*
