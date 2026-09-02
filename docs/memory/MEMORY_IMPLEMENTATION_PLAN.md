# Xiao6 AI OS — Memory Implementation Plan v1.0

> **Sprint**: AI OS Phase · Sprint 1 — Memory Architecture Design v1.0
> **配套**: `MEMORY_ENGINE_ARCHITECTURE.md` / `MEMORY_DATAFLOW.md` / `MEMORY_LIFECYCLE.md` / `MEMORY_GOVERNANCE.md`
> **Discipline**: 本档为**设计/规划**文档。本 Sprint 自身**不执行**任何编码；下列阶段为后续 Sprint 的落地路线。
> **Status**: 设计稿（待 Review）

---

## 0. 目标

把当前 13+ 表 + `habits.json` 的记忆分叉，收敛为 UMA 十层架构：
- 统一记忆抽象层 `MemoryEngine`（L1–L10）。
- `UserModelService` 单后端消除三源（L5）。
- **Obsidian vault 作为知识层 + Sync Bridge**（L4），修正 `notes.py` 反模式。
- 统一检索 `Source` 接口（L8）+ 生命周期状态机（L9）+ 治理（L10）。

---

## 1. 分阶段路线（后续 Sprint 执行，本 Sprint 不做）

### Phase A — 抽象层骨架（零视觉/行为变化）
- **A1** 定义 `MemoryEngine` 逻辑接口（`write` / `retrieve` / `transition`），包装现有 `memory.py` 调用（不改底层）。
- **A2** 统一 `MEMORY_*` 事件发射点：确认所有写经 `MemoryEngine.write` 扇出（复用 `eventbus`）。
- **A3** 建立 `Source` 接口契约；`MemorySource` 先行接入 L8。
- **验收**：现有行为不变，仅增加统一入口与事件。

### Phase B — 用户态收敛（L5）
- **B1** 实现 `UserModelService`（`load`/`upsert`/`render`），后端选 `user_model` 表。
- **B2** 读适配：`profile` 与 `habits.json` 改建为 `UserModelService` 适配器（读重定向，写重定向至 `user_model`）。
- **B3** 双跑过渡期（读适配并行），验证行为一致后退役 `profile`/`habits.json` 写路径。
- **验收**：三源→单后端，无双写；用户态渲染一致。

### Phase C — Obsidian 知识层（L4）★ 重点
- **C1** 建立 Obsidian vault 目录结构（`.md` + frontmatter 规范：`id/type/generated/tags`）。
- **C2** 实现 `Sync Bridge`：`sync_to_vault`（机器→vault）与 `sync_from_vault`（vault→机器，mtime/哈希检测）。
- **C3** 重构 `notes.py`：后端只存正文+向量+指针+metadata；链接/标签/图谱逻辑迁出，改由 vault 承载。
- **C4** 接入 `VaultGraphSource` 到 L8 检索（图谱邻域展开）。
- **验收**：人类可在 Obsidian 浏览/编辑知识；后端无链接/标签/图谱重造；双向同步一致。

### Phase D — 检索管线统一（L8）
- **D1** `KnowledgeSource` / `EpisodeSource` 接 `Source` 接口。
- **D2** `WeatherSource` / `ConversationSource` / `SystemSource` 占位补全（按 Context Engine 规划）。
- **D3** `ranker` 统一排序 + 预算截断保底顺序（Goal→Memory→WorldModel→Knowledge）。
- **验收**：新增记忆源零改动管线。

### Phase E — 生命周期状态机（L9）
- **E1** 实现 `Lifecycle.transition` 状态机（RAW→ACTIVE→DISTILLED→ARCHIVED→PROMOTED/DECAYED/PURGED）。
- **E2** 蒸馏/压缩/归档接入状态机；衰减参数（`L5_DECAY_CONF`/`PROJECT_TTL`/`KNOWLEDGE_TTL`）标定。
- **验收**：记忆状态可观测、可追踪。

### Phase F — 治理收口（L10）
- **F1** 治理检查清单自动化（CI/脚本校验禁存域、单来源、事件扇出）。
- **F2** `tool_audit` 补全覆盖（所有层写/删）。
- **验收**：治理红线可被自动验证。

---

## 2. 迁移依赖图

```
A (抽象层) ──► B (用户态) ──┐
A ──► C (Obsidian层) ───────┼──► D (检索) ──► E (生命周期) ──► F (治理)
A ──► D (检索骨架) ──────────┘
```
- A 是地基，须最先。
- B 与 C 可并行（独立层）。
- D 依赖 A + B/C 的 Source 实现。
- E 依赖 D（检索消费状态）。
- F 贯穿，最后收口自动化。

---

## 3. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 用户态双跑期不一致 | 中 | B3 双跑 + 行为对比测试 |
| Obsidian 同步冲突 | 中 | 人类优先 + `stale` 标记，不静默覆盖 |
| 向量重算成本 | 低 | mtime/哈希短路，增量重算 |
| 检索预算截断误伤 | 中 | 保底顺序 + 回归测试 |
| 迁移期回滚 | 低 | 适配器可逆，保留旧表至验收通过 |

---

## 4. 验收标准（Definition of Done）

1. 所有记忆写经 `MemoryEngine.write` 且发 `MEMORY_*` 事件。
2. 用户态单后端（无 `profile`/`habits.json` 双写）。
3. Obsidian 仅作知识层：后端无 `[[链接]]`/`#标签`/图谱重造；vault 可人类编辑。
4. 检索统一 `Source` 接口；新增源零改动管线。
5. 生命周期状态机覆盖 L1–L7。
6. 治理检查清单自动化通过（禁存域/单来源/事件扇出）。

---

## 5. 本 Sprint 交付边界（重申）

- ✅ 本 Sprint 已交付：4 份架构/数据流/生命周期/治理设计 + 本计划 + Sprint 总结（共 6 份）。
- ❌ 本 Sprint **不执行** Phase A–F 任何编码。
- ⏸ 后续 Sprint 按本计划执行，每阶段 STOP 等 Review。

---
*本档为设计/规划稿，未改动任何代码。STOP — 待 Review。*
