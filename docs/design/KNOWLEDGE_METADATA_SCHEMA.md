# Knowledge Metadata Schema — Xiao6 v1.3

> 知识元数据模式 | Project Intelligence System v1.3 · Phase 3
> 任务等级：LONG RUNNING KNOWLEDGE INTELLIGENCE FOUNDATION TASK
> 纪律：仅设计/规范；不实现、不引入数据库、不修改冻结基线。

---

## 1. 目的

Phase 2 定义 KU 的字段结构，将 `content` 标为承载项、其余为元数据。本 Phase 将其固化为**正式元数据模式（Metadata Schema）**：明确 **`content` 属于 Payload 层（非元数据）**，并补充 `domain` 与 `version` 两个元数据字段，使 **Metadata 层共 12 字段（Identity: id / title / type / domain；Governance: status / authority / source / tags / relations / version / created / updated）**，每个字段具备类型、约束、取值范围与继承规则，使 KU 具备**机器可读、可校验、可版本化**的元数据层。

> 元数据 ≠ 内容。**Metadata = Identity + Governance（12 字段）**，是 KU 的「索引卡」；`content` 是 **Payload（Content Carrier）**，是「正文」。检索/排序/过滤只基于 Metadata，不解析 content（参见 Phase 2 §2.2 / Phase 6 / Phase 8）。

---

## 2. 完整字段表（Metadata: 12 字段，Identity + Governance）

> 此表为 **Metadata 层**。Payload 层 `content` 不在此列（见 §1 / Phase 2 §2.2）。

| # | 字段 | 层 | 类型 | 必填 | 取值 / 约束 |
|---|------|----|------|------|-------------|
| 1 | `id` | Identity | string | ✅ | `KU-<domain>-<seq>`，全局唯一，不可复用（见 Phase 2 §3） |
| 2 | `title` | Identity | string | ✅ | 人类可读标题（≤ 60 字）（见 Phase 2 §2.1） |
| 3 | `type` | Identity | enum | ✅ | `redline` / `decision` / `fact` / `rule` / `structure` / `spec` / `glossary` / `boundary`（见 Phase 2 §4） |
| 4 | `domain` | Identity | enum | ✅ | 知识域（见 §5），与 `id` 的 `<domain>` 段一致 |
| 5 | `status` | Governance | enum | ✅ | 生命周期 6 值（见 §4） |
| 6 | `authority` | Governance | enum | ✅ | L100 / L90 / L80 / L70 / L50 / L30（见 Phase 4） |
| 7 | `source` | Governance | string | ✅ | 权威来源文档相对路径（如 `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`） |
| 8 | `tags` | Governance | string[] | ✅ | 主题标签，含主域 + 子主题（如 `["runtime","agent"]`） |
| 9 | `relations` | Governance | object[] | ⬜ | 类型化关联（见 Phase 5），默认 `[]` |
| 10 | `version` | Governance | string | ✅ | 语义版本 `MAJOR.MINOR`（见 §6），初始 `1.0` |
| 11 | `created` | Governance | date | ✅ | 创建日期 `YYYY-MM-DD` |
| 12 | `updated` | Governance | date | ✅ | 更新日期 `YYYY-MM-DD`，≥ created |

**Payload（单独承载，不计入 Metadata）**：`content`（text，必填）— KU 知识正文，见 Phase 2 §2.2。

---

## 3. 字段约束细则

### 3.1 `id`
- 正则：`^KU-[a-z0-9]+-\d{4}$`
- 域段 `<domain>` 须是 §5 枚举之一（或未来扩展登记值）。
- 一经分配不可改域、不可复用（防 ID 漂移）。

### 3.2 `type`
- 严格枚举，不得自由文本。
- `boundary` 专用于「v2 前瞻不替代 v1.0 冻结」类声明，便于检索时降权（见 Phase 4/8）。

### 3.3 `source`
- 必须是 `DOCUMENT_INVENTORY.md` 中已登记的相对路径。
- 指向不存在文件（如 §3.3 孤儿规范）的 KU **不得创建**（Single Source + 防 dangling）。

### 3.4 `tags`
- 至少含 1 个主域标签（= `domain`）。
- 建议 ≤ 5 个子主题，避免标签膨胀。

---

## 4. 状态继承（6 值生命周期）

`status` 取值与文档状态词表**完全统一**（修复 v1.2 §7 `REFERENCE` 不在图例问题）：

| status | 含义 | KU 是否可入核心上下文 |
|--------|------|----------------------|
| `ACTIVE` | 生效中 | ✅ |
| `FROZEN` | 冻结，最高稳定 | ✅（最高优先） |
| `AUDIT` | 审计/验证态 | ⬜（仅审计用，不直接消费） |
| `DESIGN` | 前瞻/提案 | ⬜（低权威，见 Phase 4 降权） |
| `ARCHIVE` | 已归档失效 | ❌ |
| `DEPRECATED` | 已废弃 | ❌ |

**继承规则**：KU 的 `status` **默认继承其 `source` 文档的状态**。source 为 ARCHIVE/DEPRECATED → KU 自动不可入核心上下文（与 Phase 10 治理规则联动）。

---

## 5. 知识域（domain）枚举

| domain | 覆盖范围 |
|--------|----------|
| `runtime` | AgentRuntime / Capture / Perception 运行时 |
| `event` | DOMAIN/SYSTEM 事件契约 |
| `memory` | memory.py 单一来源 |
| `policy` | PermissionGuard / PolicyEngine |
| `state` | AppState / 投影层 |
| `galaxy` | 银河本体视觉资产 |
| `decision` | DECISION_001–006 及未来决策 |
| `phase` | Phase 6/7/8/9+ 阶段定义 |
| `governance` | 文档治理 / 审计 / 交接 |
| `ui` | 前端界面（热点/聊天/命令面板） |
| `deploy` | 打包 / 部署 / 离线能力 |
| `knowledge` | 知识架构本身（v1.3 产物） |

> 与 KU `id` 的 `<domain>` 段严格对应；新增域须登记到本表并在 `DOCUMENT_INVENTORY` 注明。

---

## 6. 版本语义（version）

- 格式 `MAJOR.MINOR`，初始 `1.0`。
- `MINOR`：Payload `content` 措辞/补充，不改动事实与权威 → `updated` 更新，`version` +0.1。
- `MAJOR`：事实变更 / 权威变更 / source 变更 → `version` +1.0，且须在 `CHANGELOG_AI` 留 Reason/Impact（复用 `AI_CHANGE_REVIEW_TEMPLATE`）。
- `version` 变更**不触发** `id` 变更（id 永久稳定，version 表达演进）。

> 版本化使 KU 可审计「何时为何改」，与 GOLDEN_STATE 的「对比方法」同源。

---

## 7. 元数据校验清单（未来实现期用）

以下规则供 Phase 12 最终审计与未来实现校验：

1. `id` 匹配正则且域内 seq 唯一。
2. `type` / `status` / `authority` / `domain` 在枚举内。
3. `source` 存在于 `DOCUMENT_INVENTORY`。
4. `tags` 含 `domain`。
5. `updated` ≥ `created`。
6. `status=ARCHIVE/DEPRECATED` → 不在核心上下文（Phase 10）。
7. `authority` 与 `source` 一致（FROZEN 基线来源 → ≥L90）。

---

## 8. 与后续 Phase 衔接

| Phase | 消费本 Schema 的字段 |
|-------|----------------------|
| Phase 4 Authority | `authority` 填充 L100–L30 + 覆盖规则 |
| Phase 5 Relation | `relations` 类型化 |
| Phase 6 Retrieval | 以 `domain`/`tags`/`type` 检索，`status`/`authority` 过滤 |
| Phase 8 Ranking | 以 `authority`/`updated`(freshness)/`version` 算分 |
| Phase 10 Governance | 创建 KU 时强制填全 12 Metadata 字段（Identity + Governance）+ Payload(content) 并校验 §7 |

---

## 9. 设计纪律确认

✅ 仅固化元数据模式，未建存储、未改代码。
✅ 状态 6 值与文档词表统一，修复 v1.2 图例缺陷。
✅ `source` 必须登记，杜绝 dangling reference（呼应 Phase 1 §3.3）。
✅ `version` 表达演进，不破坏 id 稳定性。

> Phase 3 完成。下一步：Phase 4 定义 Authority System（任务 #183）。
