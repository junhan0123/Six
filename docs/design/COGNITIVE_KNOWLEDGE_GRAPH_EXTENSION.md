# Cognitive Knowledge Graph Extension — Xiao6 v1.4

> 认知知识图扩展 | Project Intelligence System v1.4 · Phase 10
> 任务等级：LONG RUNNING ARCHITECTURE GOVERNANCE TASK
> 纪律：仅设计关系模式；不实现图存储、不替代 v1.2 实例图 / v1.3 类型化关系图、不修改冻结基线。

---

## 1. 目的与定位

v1.3 `KNOWLEDGE_RELATION_GRAPH.md` 定义了 Knowledge **内部**的类型化关系（7 主轴 + 6 文档层）。但 Phase 1 §3.7 指出：**知识图未含 Memory/World/Context 边界关系**——无法表达「此 KU 来自 World Model 观察」「此 Knowledge 服务于 Context Engine 输入」等跨系统关系。

本 Phase **扩展**关系模式，新增三类跨系统关系：
- **Memory Boundary**（Knowledge ↔ Memory/User Model）
- **World State Boundary**（Knowledge ↔ World Model）
- **Context Flow**（Knowledge ↔ Context Engine 三源）

> ⚠️ **与既有图的关系（重要，继承 v1.3 Phase 5 §1）**
> - `PROJECT_KNOWLEDGE_GRAPH.md`（v1.2）= **实例化图**（示例节点），保留不动。
> - `KNOWLEDGE_RELATION_GRAPH.md`（v1.3）= **Knowledge 内部类型化模式**，保留不动。
> - 本文件 = **跨系统认知关系扩展**，三者**并存不替代**：实例图管示例、v1.3 模式管 Knowledge 内部、本文件管七系统间边界关系。

---

## 2. 新增跨系统关系类型

### 2.1 Memory Boundary 关系（Knowledge ↔ Memory/User Model）

| kind | 方向 | 含义 | 约束 |
|------|------|------|------|
| `references_user` | KU → Memory(User) | 知识泛化引用用户特征（不复制隐私） | 仅引用，不复制 User Fact 正文 |
| `excludes_memory` | KU → Memory | 知识明确不承载记忆内容（边界声明） | 如红线 KU 标此边，防误写入 Memory |
| `derived_from_experience` | KU → Memory(learnings) | KU 由 Memory 经验经治理升级而来 | 须走过治理六步（v1.3 Phase 10） |

### 2.2 World State Boundary 关系（Knowledge ↔ World Model）

| kind | 方向 | 含义 | 约束 |
|------|------|------|------|
| `excludes_world_state` | KU → World Model | 知识明确不承载实时态势（边界声明） | 如稳定事实 KU 标此边 |
| `promoted_from_observation` | KU → World Model | KU 由 World Model 观察经治理升级而来 | 须走 Phase 4 §4 升级纪律 |
| `describes_world_schema` | KU → World Model | 知识描述世界态势的**稳定结构**（如「热点标记用 RingGeometry」） | 非实时值，是结构规则（L90） |

### 2.3 Context Flow 关系（Knowledge ↔ Context Engine 三源）

| kind | 方向 | 含义 | 约束 |
|------|------|------|------|
| `feeds_context` | KU → Context Engine | KU 是 Context Engine 的知识输入源 | 三并列源之一（与 Memory/World） |
| `context_priority` | KU → KU | 上下文组装时优先级（L100 优先） | 复用 v1.3 Authority |
| `context_supersedes` | KU(high) → KU(low) | 上下文去冲突时高权威覆盖低 | 复用 v1.3 Phase 5 `supersedes` |

> Context Flow 不新建「Context Engine 节点类型」——Context Engine 在图中作为**汇点（sink）**概念存在，标记知识「流向」即可，不赋予其信息权威（呼应 Phase 6 §4.5）。

---

## 3. 跨系统关系不变量（未来实现期校验）

继承 v1.3 Phase 5 §5 精神，新增：

1. **边界声明必标**：稳定事实 KU（L90/L100）须有 `excludes_memory` + `excludes_world_state` 边，显式声明不承载记忆/态势。
2. **升级必走治理**：`promoted_from_observation` / `derived_from_experience` 源须有治理记录（Change Review），禁止静默升级。
3. **引用不复制**：`references_user` 不得导致 User Fact 正文进入 Knowledge（防隐私污染）。
4. **无环**：跨系统边不得成环（如 KU→World→KU 反向环）。
5. **Context 不赋权**：Context Engine 作为 sink，不产生 `supersedes` 反向边（不反向覆盖 Knowledge）。

---

## 4. 扩展后关系全景（七系统）

```
DECISION ──decides──> Architecture ──implements──> Module ──emits──> Event
                        │                              │
                   (v1.3 主轴，不变)              updates──> State ──persists──> Memory
                                                        │
                                                   (v1.3 主轴，不变)

[v1.4 跨系统扩展]
Knowledge(KU) ──excludes_memory──> Memory/User
Knowledge(KU) ──derived_from_experience──> Memory(learnings)
Knowledge(KU) ──excludes_world_state──> World Model
Knowledge(KU) ──promoted_from_observation──> World Model
Knowledge(KU) ──describes_world_schema──> World Model
Knowledge(KU) ──feeds_context──> Context Engine(sink)
Memory ──(User Model)── 独立子域，不进 Knowledge 权威
Goal System ──任务态── 完成后经验──> Memory learnings / 经治理 Knowledge
Event System ──通信脊柱── 各系统经 EventBus 流动，不承载持久认知
```

---

## 5. 与既有图的并存纪律

- ✅ 不替代 `PROJECT_KNOWLEDGE_GRAPH.md`（v1.2 实例图）。
- ✅ 不替代 `KNOWLEDGE_RELATION_GRAPH.md`（v1.3 Knowledge 内部模式）。
- ✅ 本文件仅**新增跨系统边界关系**，与二者角色分离。
- ✅ 不建图数据库；关系以 Markdown + 元数据承载（继承 v1.3 Phase 5 / Phase 7）。

---

## 6. 设计纪律确认

✅ 仅扩展跨系统关系模式，未建图存储、未改代码。
✅ 三类新关系（Memory Boundary / World State Boundary / Context Flow）固化。
✅ 与 v1.2 实例图、v1.3 类型化模式并存不替代。
✅ 不变量防隐私污染/静默升级/成环。
✅ 不触碰 GOLDEN_STATE 红线、不进入 Phase 9 实现。

> Phase 10 完成。下一步：Phase 11 全局一致性审计（任务 #217）。
