# Memory Boundary Specification — Xiao6 v1.4

> Memory 边界规范 | Project Intelligence System v1.4 · Phase 3
> 任务等级：LONG RUNNING ARCHITECTURE GOVERNANCE TASK
> 纪律：仅设计/规范；不实现、不修改 memory.py 实现、不引入第二 Memory、不触碰 DECISION_003。

---

## 1. 目的与定位

DECISION_003 已确立 **`memory.py` 为唯一记忆系统**（profile / memory_summary / learnings / reminders 等），禁止第二 Memory（含第二 RAG 存储）。v1.3 进一步声明「Knowledge ≠ Memory，内容域不重叠」。

但 DECISION_003 与 v1.3 未**显式划定 Memory 的内部边界**——尤其未析出 **User Model（用户模型）** 这一关键子域，亦未列明 Memory **禁止承载**的信息类别。本 Phase 固化 Memory 的：

1. **负责什么**（含 User Model 子域析出）。
2. **不负责什么**（禁存架构知识 / 临时任务态 / 外部实时事实）。
3. **与 Knowledge / World Model / Goal System 的硬边界**。

> Memory 边界是**认知层纪律**，不改变 memory.py 实现；User Model 仍存于 memory.py `profile`，仅为概念析出。

---

## 2. Memory 负责域（Allowed）

| 子域 | 内容 | 载体（memory.py） | 分类模型归属 |
|------|------|-------------------|--------------|
| **User Model** | 用户事实 + 用户偏好（§2.1） | `profile` | User Fact / User Preference |
| **对话摘要** | 历史对话的压缩摘要 | `memory_summary` | —（上下文复用） |
| **历史经验** | 任务完成后的经验教训 | `learnings` | Historical Experience |
| **提醒** | 用户设定的待办/提醒 | `reminders` | —（用户态） |

### 2.1 User Model 子域（从 Memory 析出）
- **User Fact**：用户客观事实（身份、所在地、设备、健康等）。
- **User Preference**：用户主观偏好（语言、风格、禁忌、习惯）。
- **边界**：User Model 与 **Knowledge（项目知识）** 内容域**完全不重叠**；与 **World Model（实时态势）** 不重叠（用户当前所在城市是 User Fact 持久态，用户「此刻屏幕亮度」是 World State 观察态，二者区分清晰）。
- **权威**：用户态数据，单一来源由 DECISION_003 保护；**不进入 Knowledge L100–L30 权威体系**。

---

## 3. Memory 禁存域（Forbidden）— 硬约束

以下信息**禁止写入 Memory**（含 User Model 子域）：

| # | 禁存类别 | 理由 | 正确归属 |
|---|----------|------|----------|
| 1 | **项目架构知识**（红线/事件数/模块职责/决策） | 属 Knowledge 层，写入 Memory 会**分裂权威源**、污染用户态 | Knowledge（KU，L100–L30） |
| 2 | **架构决策记录** | 决策是项目知识，须走 DECISION_* + KU `type=decision`（L80） | Knowledge |
| 3 | **实时世界/外部态势**（屏幕/热点/天气/设备瞬时状态） | 属 World Model 观察态，非用户长期记忆 | World Model |
| 4 | **当前 Goal / 任务进度** | 属 Goal System 任务态，非长期记忆 | Goal System（goals.py） |
| 5 | **单次会话中间上下文** | 易失，持久化会膨胀 Memory | Temporary Context（运行态） |
| 6 | **未治理的「洞察/规则」冒充知识** | 低权威内容不得进 Knowledge；但也不应塞进 Memory 伪装——若确为系统经验，归 `learnings`（§2 历史经验） | Historical Experience 或经治理 Knowledge |

> 红线 #1/#2 是**最高频误用**：AI 易把「项目知识」顺手写进 memory.py。本规范明确：memory.py 只存「用户/系统长期记忆」，项目知识**只读** Knowledge 层，绝不回写 Memory（呼应 v1.3 Phase 9 §3.1）。

---

## 4. 与相邻系统的硬边界

### 4.1 Memory vs Knowledge（核心边界）
- **Memory 承载**：用户/系统长期记忆（User Model / 对话摘要 / 经验 / 提醒）。
- **Knowledge 承载**：关于项目本身的知识（架构/红线/决策/阶段）。
- **边界**：内容域不重叠；**知识进上下文不写 Memory，记忆不被知识覆盖**（v1.3 Phase 9 §3.1）。
- **引用而非复制**：Memory 中若需提及某条项目知识，存其 KU id / source 引用，不复制知识正文。

### 4.2 Memory vs World Model
- **Memory**：稳定用户态（「用户住上海」）。
- **World Model**：实时态势（「此刻上海天气暴雨」）。
- **边界**：World Model 观察态**不持久化为 Memory**；若某观察需长期记录（如「用户所在城市气候」），先归 User Fact（Memory）并去掉实时性。

### 4.3 Memory vs Goal System
- **Memory**：已完成任务沉淀的经验（`learnings`）。
- **Goal System**：进行中 Goal 的任务态。
- **边界**：Goal 生命周期内信息归 Goal System；**完成后**经验才沉淀 Memory（经 reflector，仅写被允许存储）。

### 4.4 Memory vs Context Engine
- **Memory** 是 Context Engine 的**三并列输入源之一**（与 Knowledge / World Model）；Context Engine 读 Memory 投影（state.memory），不写 Memory。
- Memory 写入走 memory.py + 治理，不经由 Context Engine。

---

## 5. 单一来源纪律（DECISION_003 重申）

- 所有持久化记忆经 `memory.py`；禁止 `memory2.py` 或平行记忆存储。
- 禁止在感知/上下文层缓存**可写**记忆副本（DECISION_003 未来限制）。
- Knowledge Workspace（Phase 9 接口）只建索引，指向同一 memory.py 底座，**不新建第二 Memory**。

---

## 6. 与 v1.3 / GOLDEN_STATE 的兼容性

- ✅ 不修改 memory.py 实现、不引入第二 Memory。
- ✅ 与 v1.3 Phase 9 §3.1（Knowledge ≠ Memory）、Phase 11 §4.1 完全一致。
- ✅ 与 DECISION_003 单一来源、GOLDEN_STATE「禁止第二 Memory」红线零冲突。
- ✅ User Model 析出为概念子域，不新建存储。

---

## 7. 设计纪律确认

✅ 仅固化 Memory 边界规范，未改代码/Runtime/Memory 实现。
✅ 析出 User Model 子域（概念层），不新建存储。
✅ 明确 6 类禁存信息，防知识/态势/任务态污染 Memory。
✅ 与 Knowledge / World Model / Goal System / Context Engine 硬边界固化。
✅ 不触碰 GOLDEN_STATE 红线、DECISION_003。

> Phase 3 完成。下一步：Phase 4 定义 World Model Boundary Specification（任务 #208）。
