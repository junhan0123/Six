# Knowledge Contract Alignment Report — Xiao6 v1.3.1

> 知识契约对齐报告 | Project Intelligence System v1.3.1
> 任务类型：Documentation Maintenance + Schema Consistency Fix
> 严格模式：Audit → Plan → Execute → Verify → Report
> 纪律：仅修正文档、不改代码/Runtime/Memory/Event Contract/Policy/Architecture；不引入 RAG/Embedding；不新增功能；完成后停止等待指令。

---

## 1. Audit Scope（审计范围）

- **对象**：v1.3 Knowledge Unit 字段契约在 Phase 2（`KNOWLEDGE_UNIT_SYSTEM.md`）与 Phase 3（`KNOWLEDGE_METADATA_SCHEMA.md`）之间的漂移。
- **源头**：v1.3 稳定性审计（`KNOWLEDGE_FOUNDATION_STABILITY_REPORT.md` §3.1 OBSERVATION）记录的「`title`/`content` 去留未定」问题。
- **修复目标**：明确 **Knowledge Unit = Identity + Governance（Metadata）**， **Knowledge Payload = Content Carrier**；统一字段定义、字段归属、字段生命周期。
- **允许修改**：两份主文档 + 因字段引用产生的必要文档；其余冻结基线/业务代码一律不动。

---

## 2. Phase2 / Phase3 字段差异（差异清单）

| 维度 | Phase 2（修复前） | Phase 3（修复前） | 差异性质 |
|------|-------------------|-------------------|----------|
| 章节标题 | 「KU 字段规范（10 字段）」 | 「完整字段表（11 字段）」 | 计数口径不一致 |
| `title` | 列为字段 #2（Identity） | **缺失** | Phase 3 误删 |
| `content` | 列为字段 #11（必填） | **缺失** | Phase 3 未纳入，但无声明其归属 |
| `domain` | 未列（仅靠 id 段隐含） | 新增为字段 #6 | Phase 3 新增 |
| `version` | 未列 | 新增为字段 #9 | Phase 3 新增 |
| 层数概念 | 隐含「10 元数据 + content 承载」 | 单表 11 字段，无 Payload 分层 | 无统一分层模型 |
| §1 叙述 | — | 「补充 domain+version 两字段于 10 字段之上」→ 逻辑应为 12 却写成 11 | 叙述与表格矛盾 |
| 下游引用 | — | `KNOWLEDGE_GOVERNANCE_RULES` 称「11 字段」；v1.3 FINAL_REPORT 称「10/11 字段」 | 计数沿链失真 |

**根因**：Phase 2 把 `content` 放进元数据表（#11），Phase 3 固化时既删了 `content` 又误删了 `title`，且未建立「Metadata / Payload」分层，导致相邻文档字段集未对齐。

---

## 3. 最小修复方案（Minimal Fix）

确立统一分层模型，使两份文档及周边引用完全一致：

> **Knowledge Unit = Metadata（Identity + Governance，12 字段）+ Payload（content，1 载体）**

- **Metadata 层（12 字段）**——可机检、可版本化、可检索的索引卡：
  - **Identity（4）**：`id` / `title` / `type` / `domain`
  - **Governance（8）**：`status` / `authority` / `source` / `tags` / `relations` / `version` / `created` / `updated`
- **Payload 层（1）**：`content`（知识正文）——**不计入元数据**，检索/排序/过滤只基于 Metadata。

**最小改动原则**：
1. Phase 2 §2：拆为「12 Metadata 字段 + 1 Payload」两层表，原 `#11 content` 移入 Payload 段。
2. Phase 3 §2：补回 `title`（Identity），保留 `domain`+`version`，明确 `content` 属 Payload；§1 叙述与 §8 计数同步修正。
3. 下游引用（`KNOWLEDGE_GOVERNANCE_RULES`、`PROJECT_INTELLIGENCE_v1.3_FINAL_REPORT`、`KNOWLEDGE_FOUNDATION_STABILITY_REPORT`）的字段计数一次性对齐为「12 Metadata + Payload」。
4. **不**改任何字段语义、枚举取值、状态词表、权威规则、关系类型——仅对齐归属与计数。

---

## 4. 执行修正（Edits Applied）

| 文件 | 位置 | 修正 |
|------|------|------|
| `docs/design/KNOWLEDGE_UNIT_SYSTEM.md` | §2 | 重写为「Metadata 12 字段（Identity+Governance）+ Payload」双层表；`content` 移入 §2.2 |
| 同上 | §8 | 「将 §2 的 10 字段…」→「12 Metadata 字段（含 domain+version，content 归 Payload）」 |
| `docs/design/KNOWLEDGE_METADATA_SCHEMA.md` | §1 | 叙述改为「content 属 Payload，补充 domain+version，Metadata 共 12 字段」 |
| 同上 | §2 | 表补回 `title`（Identity），加「层」列，注明 content 不在此表 |
| 同上 | §6 | `MINOR` 版本说明标注「Payload content」 |
| 同上 | §8 | 「填全 11 字段」→「12 Metadata + Payload(content)」 |
| `docs/frozen/KNOWLEDGE_GOVERNANCE_RULES.md` | §2 [1] / §6 | 「11 字段」→「12 Metadata + Payload」计数（仅计数，未改治理策略） |
| `docs/audits/PROJECT_INTELLIGENCE_v1.3_FINAL_REPORT.md` | §2 行 29–30 | 「10/11 字段」→「12 Metadata + Payload」 |
| `docs/audits/KNOWLEDGE_FOUNDATION_STABILITY_REPORT.md` | §10 | 新增「v1.3.1 Resolution Note」闭环 OBSERVATION（保留原审计结论） |

---

## 5. 字段契约最终版（Final Contract）

```
Knowledge Unit (KU)
├── Metadata 层（Identity + Governance，12 字段，可机检/可版本化/可检索）
│   ├── Identity（创建后 id/domain 不可改；title/type 仅 MAJOR 变更）
│   │   1. id        string  ✅  KU-<domain>-<seq>，全局唯一不可复用
│   │   2. title     string  ✅  人类可读标题（≤60字）
│   │   3. type      enum    ✅  redline/decision/fact/rule/structure/spec/glossary/boundary
│   │   4. domain    enum    ✅  知识域，与 id 段一致（枚举见 METADATA §5）
│   └── Governance（随评审/变更演进；status 继承 source）
│       5. status    enum    ✅  6 值生命周期（ACTIVE/FROZEN/AUDIT/DESIGN/ARCHIVE/DEPRECATED）
│       6. authority enum    ✅  L100/L90/L80/L70/L50/L30（由 source 推导）
│       7. source    string  ✅  已登记权威来源路径（Single Source）
│       8. tags      string[]✅  含主域+子主题
│       9. relations object[]⬜  类型化关联（Phase 5）
│      10. version   string  ✅  语义版本 MAJOR.MINOR，初始 1.0
│      11. created   date    ✅  创建日期
│      12. updated   date    ✅  更新日期 ≥ created
└── Payload 层（Content Carrier，1 字段，不计入 Metadata）
     content  text  ✅  知识正文（事实/规则/理由）；检索/排序/过滤不解析 content
```

**生命周期归属**：
- **Identity**：`id`/`domain` 创建后不可改（防漂移）；`title`/`type` 仅在 MAJOR 变更（事实/权威/source 变）时调整。
- **Governance**：`version` 随变更演进（`MINOR`=content 措辞/补充；`MAJOR`=事实/权威/source 变，须 Change Review）；`status` 默认继承 `source` 文档状态。
- **Payload**：`content` 的修订驱动 `version` MINOR  bumps；其本身不进入元数据校验与检索打分键。

---

## 6. 自动审计结果（Auto-Audit）

- **命令**：`docs/reference/PROJECT_DOCUMENT_AUDIT.py`
- **结果**：
  - **PROBLEMS: 0** ✅（满足「必须保持 PROBLEMS = 0」要求）
  - **WARNS: 1** ⚠️
    - 警告内容：`可能孤儿文档(未列入 inventory): docs/audits/KNOWLEDGE_FOUNDATION_STABILITY_REPORT.md`
    - **成因**：该文件是上一轮稳定性审计（v1.3 Stability Audit）的交付物；该任务在严格只读纪律下**刻意未登记**入 `DOCUMENT_INVENTORY.md`。
    - **与本任务关系**：**非本次修改引入**；`DOCUMENT_INVENTORY.md` 不在本任务允许修改清单内，按「禁止自行修复」规则不予处理。
- **结论文件**：`docs/audits/PROJECT_DOCUMENT_AUDIT_RESULT.md`（结论 PASS，无阻断问题）

---

## 7. 修改文件列表（Modified Files）

| # | 文件 | 目录 | 改动性质 | 是否冻结 |
|---|------|------|----------|----------|
| 1 | `KNOWLEDGE_UNIT_SYSTEM.md` | docs/design | 字段分层重构 | 否 |
| 2 | `KNOWLEDGE_METADATA_SCHEMA.md` | docs/design | 字段表补 title + Payload 分层 | 否 |
| 3 | `KNOWLEDGE_GOVERNANCE_RULES.md` | docs/frozen | 仅字段计数对齐（2 处） | **是（仅计数，未改策略）** |
| 4 | `PROJECT_INTELLIGENCE_v1.3_FINAL_REPORT.md` | docs/audits | 摘要计数对齐（2 处） | 否 |
| 5 | `KNOWLEDGE_FOUNDATION_STABILITY_REPORT.md` | docs/audits | 追加 §10 闭环说明 | 否 |

> 注：本次**未新增**独立设计文档（除本报告）；本报告本身为新增交付物，按纪律未登记入 inventory（属维护动作，留待后续批准）。

---

## 8. 风险说明（Risk Notes）

| 风险 | 等级 | 说明 / 缓解 |
|------|------|-------------|
| 冻结治理规则被改动 | 低 | `KNOWLEDGE_GOVERNANCE_RULES.md` 属 `docs/frozen/`，本次**仅**修正其两处字段计数措辞，未改任何准入红线/生命周期策略。建议后续走一次 Freeze Rule + Change Review 正式重冻，使计数修订纳入变更记录。 |
| 孤儿文档警告 | 低（既有） | WARN 指向稳定性报告，源于上一轮只读纪律刻意不登记；不影响正确性，非回归。 |
| 下游 v2 文档独立 schema | 低（既有） | `Xiao6-v2-*` 自带字段定义，与 KU 契约无关；依 Single Source 原则其权威≤L30，已降权，不冲突。 |
| 字段语义误读 | 极低 | 已通过「层」列与 Payload 段显式区分 Metadata/Payload，杜绝 `content` 再被误列为元数据。 |
| 系统红线 / 架构 / Runtime / Memory / Event / Policy | **无** | 全程零触碰；未引入 RAG/Vector DB/Embedding；未进入 Phase 9 实现。 |

---

## 9. 下一步建议（Recommendations）

1. **（建议）登记库存**：批准一次维护动作，将 `KNOWLEDGE_FOUNDATION_STABILITY_REPORT.md` 与本报告登记入 `DOCUMENT_INVENTORY.md`，并复跑自动审计以清除 WARN（维持 PROBLEMS:0）。
2. **（建议）正式重冻治理规则**：对 `KNOWLEDGE_GOVERNANCE_RULES.md` 的计数修订走 Change Review + Freeze Rule，更新 `CHANGELOG_AI`。
3. **（未来实现期）落地校验**：在 Phase 12 审计钩子中加入「Metadata 12 字段齐全 + Payload 单独承载」校验（复用 Phase 3 §7 清单）。
4. **（可选）v2 文档边界声明**：延续 v1.3 建议，为 `Xiao6-v2-*` 头部加「不替代 v1.0 冻结基线」声明，进一步防混淆。

---

## 10. 完成纪律确认

✅ 仅修正文档字段契约，未改代码/Runtime/Memory/Event Contract/Policy/Architecture。
✅ 未引入 RAG / Vector DB / Embedding；未新增功能；未进入 Phase 9 实现。
✅ 未删除任何历史文档；冻结基线（GOLDEN_STATE）零触碰。
✅ 自动审计 **PROBLEMS: 0**；唯一 WARN 为既有孤儿报告，已说明且未自行修复。
✅ `title`/`content` 归属漂移已闭环，Phase 2/3 字段集现在完全一致。

> v1.3.1 Knowledge Contract Alignment **完成**。按纪律**停止，等待下一条指令**。
