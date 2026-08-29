# Xiao6 Knowledge Engine — Implementation Roadmap (Knowledge Foundation v1.0)

> **Sprint**: Knowledge Engine Sprint v1.0 — Knowledge Foundation（本档为其产出之一）
> **Mode**: Design Only（本档为路线图蓝图；K0 已完成设计，K1+ 需 Review 批准后方可实现）
> **Companion**: 继承 `KNOWLEDGE_ENGINE_ARCHITECTURE.md` + `KNOWLEDGE_STORAGE_SPEC.md`(迁移方案)
> **Status**: 设计稿（待 Review）

---

## 0. 本档定位

给出 Knowledge Engine 从**设计冻结 → 落地 → 增强**的分阶段路线图。本 Sprint（K0）只完成设计与 STOP；后续阶段需人工 Review 批准后进入，且**严禁在本 Sprint 写任何代码**。

---

## 1. 阶段总览

| 阶段 | 目标 | 关键交付 | 代码？ | Gate |
|------|------|---------|--------|------|
| **K0** | 设计冻结 | 6 份设计文档 + 本路线图 | ❌ 纯设计 | Review 批准 |
| **K1** | Vault 脚手架 + 高价值迁移 | `knowledge/` 骨架 + rules/failures/experiences 迁移 + MOC | ✅ | 静态校验 |
| **K2** | KnowledgeEngine 文件 API | read/query/reference/suggest/update/transition + 事件 + 权限 | ✅ | 单测 + GUI 协议 |
| **K3** | Context Engine 集成 | Knowledge 作为 L8 检索 Source | ✅ | 上下文装配验证 |
| **K4** | Sync Bridge（与 Memory L4 一致） | Vault↔Memory 索引镜像 | ✅ | 一致性测试 |
| **K5** | 检索增强（未来，超出本 Sprint） | 可选本地 Embedding/向量近似 | ✅（未来） | 独立 Gate |

> **K5 明确超出本 Sprint 范围**：用户要求"不是 RAG、不是向量数据库"。K5 仅在 K0–K4 稳定后、经独立 Review 才考虑，且向量仅作可选派生增强，绝不取代文件真相源。

---

## 2. K0 — Design Freeze（本 Sprint，已完成设计）
- 交付：`KNOWLEDGE_ENGINE_ARCHITECTURE.md` / `KNOWLEDGE_SCHEMA.md` / `KNOWLEDGE_STORAGE_SPEC.md` / `KNOWLEDGE_API_SPEC.md` / `KNOWLEDGE_ROADMAP.md` / `KNOWLEDGE_ENGINE_SUMMARY.md`。
- 继承冻结 `03` + ADR-002，无代码改动。
- **STOP**：待 Review。

## 3. K1 — Vault 脚手架 + 高价值迁移
- 创建 `G:\Xiao6\knowledge/` 全目录 + `index.md` MOC。
- 按 STORAGE_SPEC 迁移方案 Step 2–9：先迁 `rules/`(来自 00_System)、`failures/`(02_Bug+BUG_WALL)、`experiences/`(05_Library/03_Prompt/04_AI)——高价值、低风险。
- 补全 frontmatter（SCHEMA 合规）。
- **验收**：Vault 在 Obsidian 打开可浏览图谱；frontmatter 静态校验通过；git 可回滚。
- **不写 Runtime 代码**；纯文件迁移 + 脚本补 frontmatter（脚本本身属 K1 交付）。

## 4. K2 — KnowledgeEngine 文件 API（实现）
- 实现 API_SPEC §2 全部接口（read/read_by_id/query/reference/suggest/update/link/transition）。
- 接入 PermissionGuard（写门控）+ EventBus（`knowledge:*` 事件，须先由中央合约追加）。
- 运行于单 Runtime 内；Backend 派生索引（SQLite frontmatter，不含正文）。
- **验收**：单测覆盖 7 项（API_SPEC §7）；GUI 协议（人工 Obsidian 验证 suggest→inbox→确认→迁移）。

## 5. K3 — Context Engine 集成
- 将 Knowledge 注册为 L8 检索管线的一个 `Source`（API_SPEC §5）。
- Context Engine 只读调用 `query`/`reference` 装配上下文，附溯源。
- **验收**：真实对话中知识被检索并带来源引用；不引入向量。

## 6. K4 — Sync Bridge（与 Memory L4 一致）
- 实现 Vault↔Memory L4 索引镜像：Vault 变更 → 更新 Memory L4 `{id,summary,path}`；Memory 不反向写正文。
- 冲突策略：人类正文胜出（继承冻结 `03`）。
- **验收**：Memory L4 索引与 Vault 一致；无正文复制；冲突重建正确。

## 7. K5 — 检索增强（未来，超出本 Sprint，独立 Gate）
- 仅在 K0–K4 稳定且独立 Review 批准后。
- 可选本地 Embedding（ONNX）+ 向量近似，作为 L8 管线的**附加 Source**，结果本地缓存。
- 向量**绝不**作为真相源；文件 `.md` 仍为唯一事实来源。
- 触发条件：K3/K4 后实测关键字/图谱检索不足、且用户授权本地向量。

---

## 8. 关键路径与依赖
```
K0(设计) ──Review──► K1(Vault+迁移) ──► K2(API) ──► K3(Context集成)
                                              │
                                              ▼
                                          K4(Sync Bridge)
                                              │
                                              ▼
                                       K5(检索增强, 未来)
```
- K2 依赖中央事件合约追加 `knowledge:*` 事件（K0 已提案）。
- K4 依赖 K2（Vault 索引）+ Memory L4 接口（已存在）。
- 每阶段间有 Gate；任一层未通过不进下一层。

---

## 9. 风险与缓解
| 风险 | 缓解 |
|------|------|
| 迁移污染（吸收个人/跨项目知识） | ARCHITECTURE §3.5 边界；外部项目仅引用不吸收 |
| frontmatter 不一致 | SCHEMA 校验规则 + K1 静态校验脚本 |
| agent 覆盖人类正文 | suggest 仅落 inbox；update 冲突人类胜出 |
| 知识层变数据库（红线漂移） | 本 Sprint 红线 + K5 独立 Gate 约束 |
| 事件契约计数漂移 | `knowledge:*` 由中央合约统一追加，不在模块内硬编 |

---

## 10. Never-Do（本 Sprint 及后续均适用）
- 禁止把知识塞进数据库作为真相源。
- 禁止 RAG/Embedding/向量作为本 Foundation Sprint 实现。
- 禁止第二知识源 / 第二 vault。
- 禁止知识写入绕过 PermissionGuard / EventBus。
- 禁止知识层持有 Memory/Goal/Workflow 状态（仅 id 引用）。

---

*本档为设计稿路线图，未改动任何代码。K0 已完成设计，STOP 待 Review；K1+ 需批准后实现。*
