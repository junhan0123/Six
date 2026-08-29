# Knowledge Unit System — Xiao6 v1.3

> 知识单元系统 | Project Intelligence System v1.3 · Phase 2
> 任务等级：LONG RUNNING KNOWLEDGE INTELLIGENCE FOUNDATION TASK
> 纪律：仅设计/规范；不实现检索、不引入数据库、不修改业务代码与冻结基线。

---

## 1. 为什么需要 Knowledge Unit（KU）

来自 Phase 1 审计 §3.7：**当前知识粒度在文档级**，无法定位「某条红线」「某事件数」「某决策理由」为独立可检索单元。Context Engine（Phase 9）组装上下文时若只能整篇塞入，会浪费 token、引入噪声。

**KU = 知识的最小自治单元**：一条可被独立标识、独立赋权、独立关联、独立检索的事实/规则/决策/结构描述。

> KU 是**逻辑单元**，不是文件。一个 `.md` 文档可包含多个 KU；一个 KU 也可跨文档引用。v1.3 仅规范 KU 的结构与字段，**不要求把现有 84 文档拆成 KU 文件**（那是未来实现期的事，不在本任务范围）。

---

## 2. KU 字段规范（Metadata: Identity + Governance，12 字段 + Payload）

KU 由两层构成：**Metadata（Identity + Governance）** 提供可机检、可版本化、可检索的索引层；**Payload（Content Carrier）** 承载知识正文。

### 2.1 Metadata 字段（12 个，Identity + Governance）

| # | 字段 | 层 | 类型 | 必填 | 含义 |
|---|------|----|------|------|------|
| 1 | `id` | Identity | string | ✅ | KU 全局唯一 ID，格式 `KU-<domain>-<seq>`（见 §3） |
| 2 | `title` | Identity | string | ✅ | 人类可读标题（≤ 60 字） |
| 3 | `type` | Identity | enum | ✅ | KU 类型（见 §4） |
| 4 | `domain` | Identity | enum | ✅ | 知识域，与 `id` 的 `<domain>` 段一致（枚举见 Phase 3 §5） |
| 5 | `status` | Governance | enum | ✅ | 生命周期状态，继承 6 值（见 Phase 3 §4） |
| 6 | `authority` | Governance | enum | ✅ | 权威等级 L100/L90/L80/L70/L50/L30（见 Phase 4） |
| 7 | `source` | Governance | string | ✅ | 权威来源文档路径（如 `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`） |
| 8 | `tags` | Governance | string[] | ✅ | 领域/主题标签，便于检索（如 `runtime`, `redline`, `event`） |
| 9 | `relations` | Governance | object[] | ⬜ | 指向其它 KU / 决策的关联（见 Phase 5 关系类型） |
| 10 | `version` | Governance | string | ✅ | 语义版本 `MAJOR.MINOR`，初始 `1.0`（见 Phase 3 §6） |
| 11 | `created` | Governance | date | ✅ | KU 创建日期（ISO 8601） |
| 12 | `updated` | Governance | date | ✅ | KU 最近更新日期（ISO 8601） |

> **Identity 层**（id / title / type / domain）：定义 KU「是谁」。创建后 `id` 与 `domain` 不可改（防漂移）；`title` / `type` 仅 MAJOR 变更时调整。
> **Governance 层**（status / authority / source / tags / relations / version / created / updated）：定义 KU「如何被治理与演进」，随评审/变更而更新。

### 2.2 Payload 字段（Content Carrier，1 个）

| 字段 | 类型 | 必填 | 含义 |
|------|------|------|------|
| `content` | text | ✅ | KU 承载的知识正文（事实/规则/理由）。**属 Payload 层，不计入 Metadata 字段**；检索/排序/过滤只基于 Metadata（见 Phase 3 §1 / Phase 6 / Phase 8）。 |

> 完整 KU = **12 个 Metadata 字段（Identity + Governance）+ 1 个 Payload（content）**。v1.3.1 明确此分层，消弭 Phase 2 / Phase 3 间 `title` / `content` 归属漂移（详见 `docs/audits/KNOWLEDGE_CONTRACT_ALIGNMENT_REPORT.md`）。

---

## 3. KU ID 方案

```
KU-<domain>-<seq>
```

- `<domain>`：知识域缩写，取自 `tags` 主域，如 `runtime` / `event` / `memory` / `policy` / `state` / `galaxy` / `decision` / `phase` / `governance` / `ui` / `deploy`。
- `<seq>`：该域内自增序号（4 位，从 0001 起）。

**示例**：
- `KU-runtime-0001`：「AgentRuntime 是唯一决策运行时」
- `KU-event-0007`：「DOMAIN_EVENT_NAMES = 71」
- `KU-redline-0003`：「禁止第二 Runtime / Memory / EventBus / Permission」

> ID 一旦分配**不可复用**、**不可改域**。删除的 KU 其 ID 进入「作废区」，新 KU 用新 seq。此规则防 ID 漂移（与 GOLDEN_STATE 的 Drift 精神一致）。

---

## 4. KU 类型（type 枚举）

| type | 含义 | 示例 |
|------|------|------|
| `redline` | 不可逾越红线 | 禁止第二 Runtime |
| `decision` | 架构决策（对齐 DECISION_001–006） | EventBus 单一来源 |
| `fact` | 量化/状态事实 | 领域事件 = 71 |
| `rule` | 操作规则/流程 | 新模块须挂 Decision |
| `structure` | 系统结构描述 | AppState 11 子树 |
| `spec` | 规范条款 | Phase8 感知规范某条 |
| `glossary` | 术语定义 | KU / Authority Level 定义 |
| `boundary` | 边界声明 | v2 文档不替代 v1.0 基线 |

> type 与 `source` 联合确定权威：同一条 `redline` 若 source 指向 GOLDEN_STATE，则 authority=L100；若 source 仅指向某 design 稿，则 authority≤L50。

---

## 5. KU 与现有文档的映射（非拆分，仅标注）

v1.3 不强拆 84 文档，但要求**关键知识**在治理时显式标注其 KU 化潜力。示例映射：

| 现有文档 | 可提取 KU 类型 | 数量级 |
|----------|---------------|--------|
| `XIAO6_GOLDEN_STATE_v1.0.md` | redline / fact / structure | ~15–20 |
| `DECISION_001`–`006` | decision / rule | 6+ |
| `ARCHITECTURE_DRIFT_CHECK.md` | redline / rule | ~10 |
| `PROJECT_KNOWLEDGE_GRAPH.md` | decision / rule | 6 |
| v2 设计稿 | boundary / spec（低权威） | 多 |

> 此映射为**将来实现期**的拆件清单，本任务只规范 KU 结构，不做拆件。

---

## 6. KU 状态（status）继承约定

`status` 直接复用 Phase 3 定义的 6 值生命周期（ACTIVE / FROZEN / AUDIT / DESIGN / ARCHIVE / DEPRECATED），与文档状态词表统一，避免 v1.2 §7 发现的 `REFERENCE` 不在图例问题。

- KU 的 status **继承其 source 文档的状态**（source FROZEN → KU FROZEN）。
- 若 source 为 DEPRECATED/ARCHIVE，该 KU 不得进入核心上下文（见 Phase 10 治理规则）。

---

## 7. KU 关联（relations）占位

`relations` 字段结构在 Phase 5（KNOWLEDGE_RELATION_GRAPH）正式定义类型。此处先占位格式：

```yaml
relations:
  - { kind: "derives_from", target: "KU-decision-0001" }
  - { kind: "contradicts", target: "KU-design-0042", note: "v2 前瞻 vs v1.0 冻结" }
```

> 关系类型化是 Phase 5 的交付；此处仅约定 relations 为对象数组，避免 Phase 1 §3.8「关系未形式化」问题在 KU 层重演。

---

## 8. KU 与 Authority / Metadata / Retrieval 的衔接

| 后续 Phase | 对 KU 的增强 |
|-----------|--------------|
| Phase 3 Metadata Schema | 将 §2 的 12 Metadata 字段（Identity + Governance）固化为正式元数据 Schema（补充 `domain` + `version`；`content` 归为 Payload 载体） |
| Phase 4 Authority System | 为 `authority` 字段填充 L100–L30 语义与覆盖规则 |
| Phase 5 Relation Graph | 为 `relations` 填充类型化关系 |
| Phase 6 Retrieval Strategy | 定义 KU 如何被检索与组装 |
| Phase 8 Ranking Model | 定义 KU 的多维排序分（Authority/Relevance/...） |

---

## 9. 设计纪律确认

✅ 仅规范 KU 结构与字段，未拆文档、未建数据库。
✅ 不修改 GOLDEN_STATE / Event Contract / Runtime / Memory / Policy / State。
✅ KU 为逻辑单元，不要求物理文件化（那是未来实现期）。
✅ 与 v1.2 `PROJECT_KNOWLEDGE_GRAPH` 并存，不替代。

> Phase 2 完成。下一步：Phase 3 定义 KU Metadata Schema（任务 #192）。
