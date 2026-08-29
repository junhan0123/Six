# Knowledge System Boundary Specification — Xiao6 v1.4

> Knowledge 边界规范 | Project Intelligence System v1.4 · Phase 5
> 任务等级：LONG RUNNING ARCHITECTURE GOVERNANCE TASK
> 纪律：仅设计/规范；复用 v1.3 体系，不重写 KU/Metadata/Authority；不触碰 GOLDEN_STATE。

---

## 1. 目的与定位

v1.3 已建立完整的 Knowledge 子系统（KU / 12 Metadata / L100–L30 Authority / 类型化关系 / 检索 / 排序 / 治理）。本 Phase **不重写 v1.3**，而是在 v1.4「七认知系统」框架下，**固化 Knowledge 的边界**：

1. **负责什么**（稳定项目知识）。
2. **不负责什么**（禁存用户隐私 / 实时态势 / Goal / 对话历史）。
3. **与 Memory / World Model / Goal / User Model / Context Engine / Event 的硬边界**（七系统层统一视图）。

> 本文是 v1.3 知识体系的「边界封装」——把散落在 v1.3 Phase 9/11 的边界声明，提升为与 Memory/World Model/Goal/User Model 并列的统一边界规范。

---

## 2. Knowledge 负责域（Allowed）

| 类别 | 内容 | KU type | 权威来源 |
|------|------|---------|----------|
| **Project Knowledge** | 架构、模块职责、事件契约、阶段定义 | `fact` / `structure` / `spec` | GOLDEN_STATE(L100) / frozen(L90) |
| **Redline** | 不可逾越红线 | `redline` | GOLDEN_STATE(L100) |
| **Decision Record** | 架构/工程决策及理由 | `decision` | DECISION_001–006(L80) |
| **Rule** | 操作规则/流程 | `rule` | 决策/规范(L80/L50) |
| **Glossary** | 术语定义（KU/Authority/事件等） | `glossary` | 规范(L50+) |
| **Boundary** | 边界声明（如 v2 不替代 v1.0） | `boundary` | 基线(L100) |

> 共同特征：**稳定、可复用、跨会话有意义、关于项目本身**。由 `source` 推导 L100–L30 权威（v1.3 Phase 4）。

---

## 3. Knowledge 禁存域（Forbidden）— 硬约束

| # | 禁存类别 | 理由 | 正确归属 |
|---|----------|------|----------|
| 1 | **用户事实/偏好**（姓名/习惯/语言风格） | 属 User Model（Memory），写入 Knowledge 污染项目权威层 | Memory（profile） |
| 2 | **实时世界/外部态势**（屏幕/天气/地震瞬时） | 属 World Model 观察态，非稳定知识 | World Model |
| 3 | **当前 Goal / 任务进度** | 属 Goal System 任务态 | Goal System |
| 4 | **对话历史/摘要** | 属 Memory（memory_summary） | Memory |
| 5 | **单次会话中间上下文** | 易失，非稳定知识 | Temporary Context |
| 6 | **未治理的「经验/洞察」** | 低权威内容不得进 Knowledge；须先归 Memory learnings 或经治理升级 | Memory / 经治理 Knowledge |

> 红线 #1 是最关键：User Model 与 Knowledge 内容域**完全不重叠**，绝不允许把用户隐私提升为「项目知识 KU」（呼应 Phase 1 §3.2、Phase 3 §3）。

---

## 4. 与相邻系统的硬边界（七系统统一视图）

### 4.1 Knowledge vs Memory / User Model
- **Knowledge**：关于**项目**的稳定知识。
- **Memory / User Model**：关于**用户**的长期记忆。
- **边界**：内容域不重叠；**知识进上下文不写 Memory，记忆不覆盖知识**（v1.3 Phase 9 §3.1 / Phase 11 §4.1）。
- **引用而非复制**：Knowledge 中若需提及用户特征，存引用或泛化为规则，不复制用户隐私。

### 4.2 Knowledge vs World Model
- **Knowledge**：稳定事实（事件=71）。
- **World Model**：实时态势（此刻地震）。
- **边界**：知识不消费实时感知（v1.3 Phase 9 §3.2）；World Model 观察态升级为 Knowledge 须走治理（Phase 4 §4）。

### 4.3 Knowledge vs Goal System
- **Knowledge**：项目稳定知识。
- **Goal System**：进行中 Goal 任务态。
- **边界**：Goal 不进 Knowledge 权威体系；Goal 完成后经验沉淀经治理可升级（Phase 2 §3.9）。

### 4.4 Knowledge vs Context Engine
- **Knowledge** 是 Context Engine 的**三并列输入源之一**（与 Memory / World Model）。
- Knowledge Layer 产出「已检索+过滤+排序+去冲突块」，**只读消费**；写入走 Phase 10 治理（Create→…→Freeze）。
- Context Engine 不拥有 Knowledge，只消费其产出。

### 4.5 Knowledge vs Event System
- Knowledge 检索/治理**纯只读**，**不发射**领域事件（v1.3 Phase 6 §4）。
- 知识变更（Create/Freeze）属治理动作，经文档/CHANGELOG 留痕，不走 EventBus 领域事件。

---

## 5. Knowledge 层内部边界（继承 v1.3，不重写）

以下 v1.3 纪律在七系统框架下**继续有效**，本文仅引用不重复定义：

- **KU 结构**：12 Metadata（Identity+Governance）+ Payload(content)（v1.3.1 契约）。
- **Authority**：L100–L30，高覆盖低，禁止时间优先（v1.3 Phase 4）。
- **Relation**：7 主轴 + 6 文档层类型化边（v1.3 Phase 5）。
- **Retrieval**：7 阶段管道，不实现（v1.3 Phase 6）。
- **Governance**：6 步生命周期 + 准入红线（v1.3 Phase 10，FROZEN）。

---

## 6. 与 GOLDEN_STATE / v1.3 的兼容性

- ✅ 本文是 v1.3 知识体系的边界封装，未改 KU/Metadata/Authority/Relation 任何语义。
- ✅ 与 GOLDEN_STATE L100 优先条款、6 条红线零冲突。
- ✅ 与 v1.3 Phase 9/11 边界声明完全一致，仅提升为七系统统一视图。
- ✅ 不触碰 Runtime/Memory/Event/Policy/State/Galaxy 红线。

---

## 7. 设计纪律确认

✅ 仅固化 Knowledge 边界规范，复用 v1.3 体系，未重写。
✅ 明确 6 类负责 + 6 类禁存。
✅ 七系统硬边界统一视图（Memory/World Model/Goal/User Model/Context Engine/Event）。
✅ 与 GOLDEN_STATE / v1.3 零冲突、不触碰红线。

> Phase 5 完成。下一步：Phase 6 定义 Context Assembly Governance（任务 #212）。
