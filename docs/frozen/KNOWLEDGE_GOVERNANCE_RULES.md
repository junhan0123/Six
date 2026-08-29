# Knowledge Governance Rules — Xiao6 v1.3

> 知识治理规则（FROZEN） | Project Intelligence System v1.3 · Phase 10
> 任务等级：LONG RUNNING KNOWLEDGE INTELLIGENCE FOUNDATION TASK
> 纪律：本文件为冻结治理规则，定义 KU 生命周期与准入红线；不修改业务代码、不替代交接协议。

---

## 1. 定位与边界

- 本文件是 **v1.3 知识治理规则**，规范 Knowledge Unit（KU）从生到冻的全生命周期。
- **补充** `AI_HANDOFF_PROTOCOL.md`，**不替代**它：交接协议管「AI 如何接手与维护项目」，本文件管「项目知识如何被创建、赋权、关联、冻结」。
- 落入 `docs/frozen/` → 与 GOLDEN_STATE 同级保管，未来修改须走 Freeze Rule + Change Review。

> 与 GOLDEN_STATE 关系：本文件是知识层的治理纪律，GOLDEN_STATE 是系统层的正确态基线。二者互不冲突，本文件不触碰 GOLDEN_STATE 的 6 条红线。

---

## 2. KU 生命周期（6 步强制）

任何新知识进入核心上下文，**必须**走完以下 6 步，缺一步不得入：

```
[1] Create      创建 KU（填全 12 Metadata 字段 Identity+Governance + Payload(content)；字段契约见 KNOWLEDGE_METADATA_SCHEMA §2 / KNOWLEDGE_UNIT_SYSTEM §2）
        ↓
[2] Review      评审（复用 AI_CHANGE_REVIEW_TEMPLATE：Reason/Impact/Rollback/Approval）
        ↓
[3] Classify    分类（定 type / domain / tags）
        ↓
[4] Assign Authority  赋权威（按 source 推导 L100–L30，Phase 4 §3.3）
        ↓
[5] Link Relations    关联（填 relations，按 Phase 5 类型化边）
        ↓
[6] Freeze      冻结（status→ACTIVE/FROZEN；归档则 ARCHIVE/DEPRECATED）
```

- 任一步失败 → KU 不得进入核心上下文（见 §3 红线）。
- `version` 初始 `1.0`，演进按 Phase 3 §6。

---

## 3. 准入红线（硬约束）

1. **禁止无来源知识**：KU 的 `source` 必须指向 `DOCUMENT_INVENTORY` 已登记文档（Phase 3 §3.3）。无 source = 不得创建 = 不得入核心上下文。
2. **禁止 dangling 引用**：`source` 指向不存在文件（如 Phase 1 §3.3 孤儿规范）的 KU 一律拒绝。
3. **禁止无权威知识**：`authority` 必须按 source 推导赋值（Phase 4 §3.3），不得留空或乱填。
4. **禁止无关联孤儿**（除非 Decision 根）：非 Decision KU 至少 1 条 `derived_from`（Phase 5 §5 不变量 1）。
5. **禁止低权威冒充**：L30（前瞻设计）默认不进核心上下文，除非无更高候选（Phase 4/6/7）。
6. **禁止时间优先提权**：新 KU 不因新而获高权威（Phase 4 §3.2）。

---

## 4. 修改与演进纪律

- KU `MAJOR` 版本变更（事实/权威/source 变）→ 必须走 Change Review + 更新 `CHANGELOG_AI`。
- 提升权威（如 v2 提案升 L80）→ 必须新建/关联 DECISION + Change Review，**不得**静默提权（呼应 AI_HANDOFF 的 Silent Change 禁止）。
- 冻结后修改：等同修改 frozen 文档，走 Freeze Rule 重审（GOLDEN_STATE 对比方法）。

---

## 5. 与现有治理的衔接

| 现有机制 | 本规则的衔接点 |
|----------|----------------|
| `AI_HANDOFF_PROTOCOL` | 本规则是其「知识维度」补充；维护闭环/Freeze Rule 共用 |
| `AI_CHANGE_REVIEW_TEMPLATE` | Step [2] Review 直接复用 |
| `DOCUMENT_INVENTORY` | Step [1] source 必须登记于此 |
| `ARCHITECTURE_DRIFT_CHECK` | 知识漂移（重复/冲突/越权）命中即回滚，与系统漂移同源 |
| `XIAO6_GOLDEN_STATE` | 不变量零触碰；本规则不修改基线 |

---

## 6. 审计钩子（供 Phase 12 / 未来实现）

- 每个 KU 可机检：12 Metadata 字段齐全（+Payload content 单独承载）？source 登记？authority 匹配？relations 合法？status 与 source 一致？
- 违规即记 `GOVERNANCE_CONSISTENCY_REPORT` 同类问题，回滚或重审。

---

## 7. 冻结声明

> 本文件属 `docs/frozen/`，为知识治理最高规则。任何 KU 创建/修改与此冲突时，以本规则优先；本规则自身修改须走 Freeze Rule + Change Review，并更新 `CHANGELOG_AI`。

---

## 8. 设计纪律确认

✅ 定义 KU 生命周期与准入红线，未改代码。
✅ 明确补充 `AI_HANDOFF_PROTOCOL`，不替代。
✅ 落入 frozen，与 GOLDEN_STATE 同级保管。
✅ 不触碰系统红线（Runtime/Memory/Event/Policy/State/Galaxy）。

> Phase 10 完成。下一步：Phase 11 定义 Cognitive Context Blueprint（任务 #187）。
