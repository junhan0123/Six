# Context Assembly Governance — Xiao6 v1.4

> 上下文组装治理 | Project Intelligence System v1.4 · Phase 6
> 任务等级：LONG RUNNING ARCHITECTURE GOVERNANCE TASK
> 纪律：仅设计/规范；不实现 Context Engine、不新增 Runtime、不进入项目实现 Phase 9。

---

## 1. 目的与定位

v1.3 Phase 9/11 已定义 Knowledge Layer 作为 Context Engine 的**三并列输入源之一**（与 Memory / World Model）。但「三源如何组装、谁提供什么、谁不能覆盖谁」的**可机读治理规则**尚未固化。

本 Phase 定义**上下文组装治理**——一条端到端的概念流程，明确：

1. 从用户请求到 LLM 上下文的**收集顺序**。
2. 每个系统**提供什么、不提供什么**。
3. **不可覆盖关系**（哪些源优先级高于哪些、谁不能覆盖谁）。

> Context Engine 本身（项目实现 Phase 9）仍待设计审批、未实现；本文仅治理其**组装关系**，不实现。

---

## 2. 组装流程（概念管道）

```
[1] User Request
        ↓
[2] Goal System         → 提供当前 Goal / 任务上下文（任务态）
        ↓
[3] Memory (User Model) → 提供用户事实/偏好 + 对话摘要 + 历史经验
        ↓
[4] World Model         → 提供当前世界/设备/外部态势（观察态）
        ↓
[5] Knowledge Layer     → 提供项目稳定知识（经 v1.3 检索管道：检索→过滤→排序→去冲突）
        ↓
[6] Context Engine      → 三源合并 + 预算截断 + 不可覆盖裁决 → ContextPackage
        ↓
[7] LLM                 → 带上下文推理/回复
```

> 顺序说明：Goal（任务驱动）→ Memory（用户态）→ World Model（环境态）→ Knowledge（项目态）是**并列收集**，非串行依赖；[6] 是汇编点。

---

## 3. 各系统「提供什么 / 不提供什么」

| 系统 | 提供（输入 Context Engine） | 不提供 |
|------|------------------------------|--------|
| **Goal System** | 当前 Goal 描述、Task 进度、任务约束 | 项目知识、用户偏好、世界态势 |
| **Memory / User Model** | 用户事实/偏好、对话摘要、历史经验 | 项目架构知识、实时态势、Goal |
| **World Model** | 屏幕/设备/外部实时态势 | 稳定事实、用户长期态、Goal |
| **Knowledge Layer** | 已检索+过滤+排序+去冲突的项目知识块（带 source） | 用户隐私、实时态势、Goal |
| **Context Engine** | **汇编结果**（ContextPackage） | 不拥有任何信息、不新增权威 |

---

## 4. 不可覆盖关系（权威矩阵预览，详见 Phase 7）

Context Engine 合并三源时，遵循以下**不可覆盖纪律**：

### 4.1 知识权威不可被覆盖
- Knowledge 层带 v1.3 L100–L30 权威；**L100（GOLDEN_STATE 红线/事实）永远最高优先**，Memory/World Model/Goal 内容**不得覆盖** Knowledge L100 事实。
- 例：World Model 报告「屏幕显示某事件数=72」与 Knowledge「事件=71（L100）」冲突 → **以 Knowledge L100 为准**，World Model 观察标记为「待核实/脏数据」。

### 4.2 用户态优先于通用默认
- 当用户明确偏好（Memory User Model）与通用知识默认冲突时，**用户态优先**（如「用户要求回复不带 emoji」覆盖通用知识「可带 emoji 提升亲和力」）。
- 此优先**仅限用户自身交互风格**，不覆盖项目红线（L100）。

### 4.3 实时态势不推翻稳定知识
- World Model 观察态**不得**推翻 Knowledge 稳定事实（§4.1）；观察态仅作「当前环境补充」，非权威来源。

### 4.4 Goal 不覆盖知识/记忆
- Goal 是任务态，其约束**不覆盖** Knowledge 红线（L100）与 Memory 用户态优先；Goal 仅限定「本次任务范围」。

### 4.5 Context Engine 不创造权威
- Context Engine **只汇编、不赋权**；它服从各源系统的既有权威（Knowledge L100–L30、Memory DECISION_003、World Model 观察态）。
- 禁止 Context Engine 因「拼接后看似合理」而合成新权威事实（防幻觉/Prompt Injection，呼应 v1.3 Phase 9 §3.5）。

---

## 5. 预算截断纪律

- 上下文超 token 预算时，**截断顺序**（保底，呼应 v1.3 Phase 8 §4）：
  1. **FROZEN 基线 KU（L100/L90 红线/事实）永远保留**。
  2. **用户态（Memory User Model 偏好/事实）保留**（交互相关性最高）。
  3. 其余按 v1.3 Ranking（Authority/Relevance/Freshness/Usage/Dependency）截取 Top-K。
  4. World Model 观察态超预算可优先裁剪（易失、可再取）。
- 截断**不得**丢弃 L100 红线——否则违反 GOLDEN_STATE。

---

## 6. 与 v1.3 / ARCHITECTURE_MAP 的兼容性

- ✅ 三源并列模型继承 v1.3 Phase 9 §2 / Phase 11 §3，未改。
- ✅ Context Engine 不新增决策 Runtime（DECISION_002）、不写状态（GOLDEN_STATE AppState 纪律）。
- ✅ 不可覆盖关系与 v1.3 Phase 4（高覆盖低）、Phase 7（权威先验）、GOLDEN_STATE L100 完全一致。
- ✅ 不进入项目实现 Phase 9、不实现检索/排序。

---

## 7. 设计纪律确认

✅ 仅治理上下文组装关系，未实现 Context Engine。
✅ 明确收集顺序、各系统提供/不提供、不可覆盖纪律、截断保底。
✅ 与 v1.3 三源模型、Authority 体系、GOLDEN_STATE 零冲突。
✅ 不新增 Runtime/Memory/EventBus、不进入 Phase 9 实现。

> Phase 6 完成。下一步：Phase 7 定义 Cognitive Authority Matrix（任务 #210）。
