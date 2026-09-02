# Cognitive Context Blueprint — Xiao6 v1.3

> 认知上下文蓝图（未来架构输入） | Project Intelligence System v1.3 · Phase 11
> 任务等级：LONG RUNNING KNOWLEDGE INTELLIGENCE FOUNDATION TASK
> 纪律：仅定义**关系蓝图**与未来输入；**不提供实现方案**、不写代码、不引入新系统。

---

## 1. 目的

为未来「认知上下文（Cognitive Context）」能力预留**架构关系蓝图**：厘清 Knowledge / Memory / World Model / Context Engine / Reflection 五者的角色与信息流，使后续实现 Phase（含项目 Phase 9+）有清晰的概念地基。

> ❗ **最高纪律**：本文件是**蓝图/输入**，不是实现方案。不定义类、不写伪代码、不引数据库、不启动任何实现。仅描述「未来若做认知上下文，这五者应如何协作」。

---

## 2. 五要素定义

| 要素 | 角色 | 当前状态（v1.3） |
|------|------|------------------|
| **Knowledge** | 关于项目本身的知识（架构/红线/决策/阶段） | 本 v1.3 全部产物（KU+检索+排序+治理） |
| **Memory** | 用户/系统的长期记忆 | `memory.py` 单一来源（FROZEN，GOLDEN_STATE 红线） |
| **World Model** | 当前世界态势（热点/环境/外部数据） | 观察性，PerceptionState 投影 |
| **Context Engine** | 组装最终 LLM 上下文的引擎 | 项目 Phase 9 待设计审批（未实现） |
| **Reflection** | 对上下文/行为的反思与自我修正 | 规划中（目标决策/自我修正模块，未实现） |

---

## 3. 关系蓝图（信息流）

```
                 ┌──────────── Reflection ────────────┐
                 │  (反思/自我修正，未来)              │
                 │      ↑ 反馈 ┊ 触发再检索            │
                 └──────┼────────┼─────────────────────┘
                        │        │
   Knowledge ───┐       │        │       ┌─── Memory
   (v1.3 KU)    │       ↓        ↓       │  (memory.py)
                └──→ Context Engine ←─────┘
                        ↑
   World Model ─────────┘  (态势投影)

   Context Engine → LLM → 行为/回复 → Reflection 评估 → 可能回写 Memory / 触发 Knowledge 再检索
```

- **Knowledge** 与 **Memory** 与 **World Model** 是 Context Engine 的**三个并列输入源**（见 Phase 9 §2）。
- **Reflection** 是闭环顶端：消费上下文产出，反馈给 Context Engine（再检索）或 Memory（沉淀），但不直接改 Knowledge（Knowledge 改写走 Phase 10 治理）。

---

## 4. 关键关系约束（继承自前序纪律）

1. **Knowledge ≠ Memory**：内容域不重叠（项目知识 vs 用户记忆）；知识不写 Memory，记忆不覆盖知识（Phase 9 §3.1）。
2. **Knowledge 只读消费**：Context Engine 读 Knowledge Layer 产出，写入走 Phase 10 治理（Create→…→Freeze）。
3. **Reflection 不越权**：Reflection 可触发再检索、可写 Memory，但**不得**直接修改 FROZEN 知识或系统红线（GOLDEN_STATE）。
4. **无新基础设施**：五者协作是逻辑层，不新增 Runtime/Memory/EventBus（GOLDEN_STATE 红线）。
5. **权威贯穿**：Knowledge 输入 Context Engine 时带 Phase 4 权威，Reflection 评估不得因「新反思」推翻 L100 基线（禁止时间优先）。

---

## 5. 对未来实现的输入清单

本蓝图为未来实现 Phase 提供以下**设计输入**（非实现）：

- Context Engine 应支持 ≥3 个上下文源并行收集（Knowledge/Memory/World Model）。
- 知识源接口 = Phase 6 管道输出（检索→过滤→排序→去冲突块）。
- Reflection 回路需定义触发条件与反馈通道（不在此展开）。
- 所有源的输出须带 `source` 溯源，供 LLM 引用与 Reflection 评估。

---

## 6. 明确不做什么

❌ 不提供 Context Engine 实现方案。
❌ 不定义 Reflection 算法/触发逻辑。
❌ 不引入向量库/图库/新存储。
❌ 不修改 GOLDEN_STATE / Event Contract / Runtime / Memory / Policy / State。
❌ 不进入项目实现 Phase 9。

---

## 7. 设计纪律确认

✅ 仅定义五要素关系蓝图，未提供实现。
✅ 继承 Phase 9 不替代 Memory/World Model 约束。
✅ Reflection 不越权改 FROZEN 知识/红线。
✅ 与 GOLDEN_STATE 红线零冲突。

> Phase 11 完成。下一步：Phase 12 最终审计（任务 #193）。
