# Knowledge Relation Graph — Xiao6 v1.3

> 知识关系图（类型化关系模式） | Project Intelligence System v1.3 · Phase 5
> 任务等级：LONG RUNNING KNOWLEDGE INTELLIGENCE FOUNDATION TASK
> 纪律：仅设计/规范；不建图数据库、不修改冻结基线。

---

## 1. 目的与定位

Phase 1 §3.8 指出：v1.2 的 `PROJECT_KNOWLEDGE_GRAPH.md` 是**实例化示例图**（6 个 DECISION 节点 + 叙述性关联），关系不可机读、不可遍历、不可校验。

本 Phase 定义**类型化关系模式（Typed Relation Schema）**：一套可枚举的 `kind` + 方向 + 约束，使 KU 的 `relations` 字段（Phase 2/3）成为**可查询、可校验**的图，而非散文。

> ⚠️ **与 v1.2 实例化图的关系（重要）**
> - `docs/reference/PROJECT_KNOWLEDGE_GRAPH.md` = **实例化图**（具体节点示例，保留不动）。
> - 本文件 `KNOWLEDGE_RELATION_GRAPH.md` = **关系模式/规范**（定义关系类型，不存具体节点）。
> - 二者并存：模式管「关系怎么连」，实例图管「连了哪些例子」。本文件**不替代** v1.2 实例图。

---

## 2. 主轴关系（主轴类型）

沿 v1.2 主轴 `Decision → Architecture → Module → Event → State → Memory → Test → Documentation`，定义 7 条有向边类型：

| kind | 方向 | 含义 | 约束 |
|------|------|------|------|
| `decides` | Decision → Architecture | 决策决定架构 | 每 Architecture 须有 ≥1 上游 Decision |
| `implements` | Architecture → Module | 架构落地为模块 | Module 必挂 Architecture |
| `emits` | Module → Event | 模块发出事件 | Event 须有 emitting Module |
| `updates` | Event → State | 事件更新状态 | 对应 AppState reducer |
| `persists` | State → Memory | 状态持久化到 Memory | 单一来源 memory.py |
| `verifies` | Test → Module/Event | 测试验证模块/事件 | 契约测试双向 |
| `documents` | Documentation → * | 文档记录上述任一 | 文档须指向被记对象 |

> 主轴保证「任何新模块都能挂到某 Decision 之下」（v1.2 知识关联规则 1），且可机读校验。

---

## 3. 文档层关系（Document 层类型）

| kind | 方向 | 含义 | 约束 |
|------|------|------|------|
| `derived_from` | KU → Decision/Source | KU 源自某决策/来源 | 必填（呼应 Phase 3 `source`） |
| `supersedes` | KU(high) → KU(low) | 高权威覆盖低权威 | 仅当 authority 高时合法（Phase 4 §3.1） |
| `contradicts` | KU → KU | 显式冲突标注 | 须带 `note`（Phase 4 §3.4） |
| `related_to` | KU → KU | 弱关联（同域/同主题） | 不限方向 |
| `precedes` | Phase → Phase | 阶段先后 | 仅 phase 域 |
| `boundary_of` | boundary-KU → baseline-KU | 边界声明指向基线 | 如 v2 不替代 v1.0 |

---

## 4. 关系对象格式（relations 字段）

```yaml
relations:
  - { kind: "derived_from",  target: "KU-decision-0001" }
  - { kind: "contradicts",   target: "KU-design-0042", note: "v2 前瞻 vs v1.0 冻结核心" }
  - { kind: "boundary_of",   target: "KU-redline-0003", note: "v2 文档不替代本红线" }
```

- `target`：KU id 或决策 id（DECISION_xxx）或文档路径。
- `note`：`contradicts` / `boundary_of` 必填，其余可选。
- 方向性：`derived_from` 由 KU 指向来源；反向边不存（避免冗余）。

---

## 5. 可校验不变量（未来实现期用）

1. **Decision 根**：每个非 Decision KU 至少 1 条 `derived_from` 指向 Decision 或 FROZEN 基线。
2. **无孤儿**：`related_to` 之外，每个 KU 须有 ≥1 主轴或文档层入边/出边。
3. **覆盖合法**：`supersedes` 的源 authority 必须 > 目标 authority。
4. **无环**：`precedes` / `decides` 主轴不得成环。
5. **冲突显式**：两 KU 同事实冲突时，低方须有 `contradicts` 边。

> 这些不变量供 Phase 12 最终审计与未来图校验使用。

---

## 6. 与实例图的对照示例

以 DECISION_001_EVENTBUS 为例：
- **v1.2 实例图**：叙述「Architecture: 事件单一通信机制 → Module: eventbus.py → Event: DOMAIN 71/SYSTEM 8 → Test: phase6-order1 → Documentation: GOLDEN_STATE/DRIFT_CHECK」。
- **本模式**：将上述文本转为可机读边——`decides(D001, Arch-EventBus)`、`implements(Arch-EventBus, eventbus.py)`、`emits(eventbus.py, DOMAIN_EVENT)`、`verifies(phase6-order1, eventbus.py)`、`documents(GOLDEN_STATE, D001)`。

> 实例图是「人读示例」，本模式是「机读规范」。实现期可用本模式把实例图升级为可遍历图。

---

## 7. 设计纪律确认

✅ 仅定义关系类型与约束，未建图存储。
✅ 明确与 v1.2 `PROJECT_KNOWLEDGE_GRAPH` 并存，不替代。
✅ 关系类型化解决 Phase 1 §3.8「关系未形式化」。
✅ 不变量呼应 GOLDEN_STATE Drift 精神（可校验 = 可防漂移）。

> Phase 5 完成。下一步：Phase 6 定义 Retrieval Strategy（任务 #184）。
