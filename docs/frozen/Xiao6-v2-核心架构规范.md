# 《Xiao6 v2 核心架构规范（Architecture Specification）》

> 版本：v2.0-Architecture-Spec
> 角色：Chief AI Architect（首席系统架构师）
> 适用范围：Xiao6 项目所有当前与未来子系统
> 效力：本文档为项目最高等级设计规范。所有后续代码、模块、工具、工作流、Skill 的实现与扩展，均不得违反本文档。

---

## 阅读约定

- 规范中 **“必须（MUST）”** 为强制要求，违反即视为架构违例。
- **“禁止（MUST NOT）”** 为红线，任何情况下不得突破。
- **“应当（SHOULD）”** 为推荐做法，允许在文档化理由与 CTO 评审后例外。
- **“可以（MAY）”** 为可选扩展点。
- 所有模块名称采用英文代码标识，正文解释用中文。

---

## 第一章 设计原则（Design Principles）

### 1.1 Single Responsibility（单一职责）

每个模块、类、函数只负责一个明确概念或一条明确业务线。例如：Planner 只负责目标拆解，Reasoning 只负责思考，Executor 只负责执行，Reflection 只负责复盘。

- **为什么**：职责混淆会导致变更半径不可控、单测难以编写、运行时行为难以预测。Xiao6 作为长期演进的 Personal AI OS，必须让每块积木可被独立替换。
- **例外**：允许极薄的适配层（Adapter/Facade）组合多个下层接口，但适配层本身不得包含业务规则。

### 1.2 Low Coupling / High Cohesion（低耦合、高内聚）

模块之间通过显式接口与事件总线通信，不直接持有对方实例。相关数据与行为必须集中在同一模块。

- **为什么**：降低局部改动引发的全局回归风险；便于单模块测试与并行开发。
- **例外**：允许基础设施工具（如日志、配置读取、DTO 基类）被多模块依赖，但这类工具必须是无状态、无业务逻辑的。

### 1.3 Local First（本地优先）

用户数据、记忆、画像、工作流状态默认落盘本地。云端 LLM 仅作为计算能力调用，不能成为状态所有者。

- **为什么**：隐私、离线可用、长期拥有权是 Personal AI OS 的根基。
- **例外**：经用户明确授权的第三方 API 调用（天气、搜索、LLM 推理）允许临时数据出境，但结果必须本地持久化或按策略遗忘。

### 1.4 Security First（安全优先）

任何工具、工作流、Skill 在执行前必须通过 Sandbox 审计；危险命令、文件越权、Prompt Injection 必须被拦截或降级。

- **为什么**：AI Agent 拥有调用工具与读写本地数据的能力，一旦失控损失巨大。
- **例外**：仅用户通过受信界面（Developer Dashboard）显式开启的调试模式可放宽部分审计，但所有操作仍须留痕。

### 1.5 Event Driven（事件驱动）

模块间唯一允许的通信方式是 EventBus。禁止跨模块直接函数调用、禁止直接修改其他模块的状态。

- **为什么**：事件驱动是解耦、异步、可观测、可回放的基础。
- **例外**：纯工具函数库、配置读取、DTO 共享不视为模块间通信；数据库连接池等基础设施可共享。

### 1.6 Backward Compatibility（向后兼容）

已有 API 路径、数据库表、工具 name/参数/返回、前端 `window.ZZ*` 桥、SSE 事件格式，在未经过渡期与 Migration 前不得破坏。

- **为什么**：Xiao6 已经承载 34 项用户功能，任何重构不能以牺牲现有功能为代价。
- **例外**：经评审确认无调用方、且已提供 Migration 与 Rollback 方案后可废弃旧接口。

### 1.7 Incremental Evolution（增量演进）

新能力以新增模块、新增事件、新增 Skill 的方式加入，不推翻已有运行时。

- **为什么**：长期项目无法承受大爆炸式重构；每一轮升级都必须可回滚。
- **例外**：无。所有升级必须增量。

### 1.8 Stateless API / Stateful Runtime（无状态 API，有状态运行时）

HTTP API 层不保存会话状态；Agent Runtime 内部可维护本轮对话的临时状态（Cognitive State、Plan、Working Memory），但必须在会话结束时落盘或清理。

- **为什么**：API 层无状态利于横向扩展与测试；Runtime 有状态是实现智能体所必需。
- **例外**：SSE 长连接天然持有连接状态，但连接状态不得混同于业务状态。

### 1.9 No God Module（禁止神模块）

任何单一文件不得同时承担路由、业务编排、工具执行、数据持久化、事件分发等多项职责。

- **为什么**：神模块是维护性灾难。v1 的 `server.py` 1220 行即为此教训。
- **例外**：启动入口文件 `server.py` 可以极薄地负责“启动服务器 + 委托路由”，但不得包含业务逻辑。

### 1.10 No Circular Dependency（禁止循环依赖）

模块依赖图必须是有向无环图（DAG）。若出现循环依赖，必须通过引入抽象接口或事件总线打破。

- **为什么**：循环依赖导致编译/导入顺序不确定、单元测试困难、模块边界模糊。
- **例外**：无。

### 1.11 Explicit Interface over Implicit Convention（显式接口优于隐式约定）

模块对外能力必须通过显式接口（函数签名、事件 Topic、DTO 定义）声明，禁止依赖文件名、全局变量、魔术字符串等隐式契约。

- **为什么**：减少“改一处崩三处”的隐蔽耦合。
- **例外**：纯前端组件的 CSS class 命名可保留约定，但组件间通信仍须走事件总线或 Props。

### 1.12 Observability by Design（可观测性内建）

每个模块必须暴露内部状态（Cognitive State、Queue、Latency、Error Count），通过 EventBus 或 Metrics 接口供 Developer Dashboard 消费。

- **为什么**：Personal AI OS 的调试不能靠 `print`，必须实时可视化。
- **例外**：无。

---

## 第二章 总体架构

### 2.1 系统分层

```
┌─────────────────────────────────────────────────────────────┐
│  UI Layer（Electron / Browser）                              │
│  - HUD / Dashboard / Command Palette / Voice Orb / Developer │
├─────────────────────────────────────────────────────────────┤
│  API Layer（api/）                                            │
│  - chat · memory · settings · tools · system · notification │
│  - static · devices · workflow · skill                      │
├─────────────────────────────────────────────────────────────┤
│  Agent Runtime（agent/）                                      │
│  - Planner → Reasoning → Decision → Executor → Reflection    │
├─────────────────────────────────────────────────────────────┤
│  Cognitive Services                                           │
│  - Context Engine · World Model · Goal System · User Model   │
│  - Personality Engine · Knowledge Graph                      │
├─────────────────────────────────────────────────────────────┤
│  Capability & Execution                                       │
│  - Skill System · Workflow Engine · Tool System              │
├─────────────────────────────────────────────────────────────┤
│  Event Bus（唯一脊柱）                                        │
├─────────────────────────────────────────────────────────────┤
│  Resource Manager                                             │
│  - CPU / GPU / Memory / API Rate Limit / Tool Busy / LLM Busy│
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                   │
│  - xiao6.db · goals.db · user_profile.db · file system  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 每层职责

| 层 | 必须负责 | 禁止负责 |
|---|---|---|
| UI Layer | 用户交互渲染、状态展示、语音球动画、SSE 消费 | 业务规则、工具执行、数据持久化 |
| API Layer | HTTP 请求解析、参数校验、路由委托、响应格式化、SSE 连接管理 | Agent 运行逻辑、记忆压缩、目标推理 |
| Agent Runtime | 单轮/多轮对话的完整闭环：Plan / Reason / Decide / Execute / Reflect | HTTP 传输、数据库原始访问、前端 DOM |
| Cognitive Services | 为 Runtime 提供结构化上下文（Goal / World / User / Personality / Memory） | 直接调用工具、直接回复用户 |
| Capability & Execution | 工具注册与执行、Skill 生命周期、Workflow 解释与调度 | 业务编排、用户模型推理 |
| Event Bus | 可靠的事件路由、订阅管理、异步分发、死信处理 | 业务语义解释、状态持久化 |
| Resource Manager | 资源申请、排队、抢占、限流、取消 | 业务决策 |
| Data Layer | 数据持久化、事务、迁移、索引 | 业务规则、LLM 调用 |

### 2.3 数据流原则

1. 用户请求进入 API Layer。
2. API Layer 构造 `TurnRequest` DTO，交给 Agent Runtime。
3. Runtime 调用 Context Engine 装配上下文。
4. Context Engine 读取 Memory、Goal、World、User、Personality、Knowledge Graph，不直接读取原始数据库。
5. Planner 产出 Plan；Reasoning 产出思考与决策；Executor 调用 Tool / Workflow / Skill；Reflection 产出复盘结果。
6. 所有关键状态变更通过 EventBus 发布。
7. Reply Generator 产出回复，经 API Layer 以 SSE 推送给前端。

### 2.4 禁止事项

- API Layer 禁止直接调用 `tools.TOOL_FUNCS`。
- Planner 禁止直接查询数据库。
- Tool 禁止直接修改 Memory 或 Goal。
- Memory 模块禁止触发主动推送。
- UI 禁止直接调用 `agent.runtime.run()`。

---

## 第三章 Agent Runtime 生命周期

### 3.1 标准生命周期

```
Receive
    ↓
Context Loading  ──→ ContextEngine.assemble()
    ↓
Goal Loading     ──→ GoalManager.get_active_goals()
    ↓
World Update     ──→ WorldModel.snapshot()
    ↓
Planning         ──→ Planner.plan(turn, goals, world)
    ↓
Reasoning        ──→ Reasoning.think(plan, context)
    ↓
Decision         ──→ DecisionEngine.decide()
    ↓
Execution        ──→ Executor.execute(decision)
    ↓
Reflection       ──→ Reflection.reflect(result)
    ↓
Memory Update    ──→ Memory.write(episode, working→long-term)
    ↓
Goal Update      ──→ GoalManager.update(progress)
    ↓
Response         ──→ ReplyGenerator.generate()
    ↓
Idle             ──→ CognitiveState.set(IDLE)
```

### 3.2 每一步规范

| 阶段 | 输入 | 输出 | 失败恢复 | 超时/重试 |
|---|---|---|---|---|
| Receive | HTTP Request / SSE 连接 / TICK 事件 | `TurnRequest` DTO | 400 返回，记录审计 | 无 |
| Context Loading | 用户消息、本轮 ID、预算档位 | `ContextSnapshot` | 降级到最小上下文 | 2s 超时，单次 |
| Goal Loading | 用户 ID、时间、World State | 活跃 Goal 列表 | 空列表继续 | 1s 超时，单次 |
| World Update | 当前时间、缓存标记 | `WorldSnapshot` | 使用缓存快照 | 各采集器独立超时 |
| Planning | TurnRequest + ContextSnapshot + Goals + World | `Plan`（Step 列表） | 生成单步 Fallback Plan | 5s 超时，重试 1 次 |
| Reasoning | Plan + Context + Tool Registry | `ReasoningResult`（思考+下一步） | 标记为 uncertain，降低置信度 | 10s 超时，重试 1 次 |
| Decision | ReasoningResult + Safety Policy | `Decision`（动作类型+目标） | 拒绝或追问用户 | 1s 内本地决策 |
| Execution | Decision + Tool/Workflow/Skill | `ExecutionResult`（成功/失败/部分成功） | Tool 级重试 + Workflow 级补偿 | Tool 超时 30s，Workflow 超时按节点 |
| Reflection | ExecutionResult + Plan + Reply | `ReflectionResult` | 记录失败原因到审计 | 3s 超时，失败不阻塞回复 |
| Memory Update | Episode、ReflectionResult | 写入状态 | 异步重试 3 次 | 后台执行 |
| Goal Update | ReflectionResult 中的 progress | Goal 状态更新 | 记录待处理 | 后台执行 |
| Response | 最终内容 + SSE 事件 | 流式或完整回复 | 返回友好错误 | 受 LLM 推理超时约束 |
| Idle | 无 | 释放本轮 Working Memory | 无 | 无 |

### 3.3 失败恢复原则

- 任何阶段失败都必须产出 `StageResult`（成功/失败/降级/超时）。
- Runtime 不得因非致命阶段失败而直接 500；必须进入 Recovery Path。
- Recovery Path 的默认行为：降级上下文 → 调用 LLM 生成解释 → 返回用户 → 记录审计。
- 致命失败（如 LLM 完全不可用）才允许返回 503，并触发 Developer Dashboard 告警。

### 3.4 超时原则

- 用户感知路径总超时默认 60s；后台路径（Memory Update / Goal Update）总超时 30s。
- 每个外部 HTTP 调用必须单独设置超时（默认 10s）。
- 所有超时必须被捕获并进入 Reflection。

---

## 第四章 Context Engine 规范

### 4.1 Context 来源与优先级

Context 来源按以下顺序参与拼装，最终由 Context Engine 统一排序与裁剪：

1. **System Prompt Base**：系统级人格与安全基线。
2. **Personality**：动态人格参数（专业度、主动度、解释长度、严肃度、技术深度）。
3. **World State**：时间、位置、天气、系统负载、Git、当前项目、网络、作息。
4. **Goal**：长期/短期/循环目标，按相关度与优先级排序。
5. **User Model**：用户画像、习惯、偏好、项目、联系人。
6. **Long-Term Memory**：高度相关记忆节点（按向量/关键词相似度）。
7. **Episode Memory**：近期对话轮次（最近 N 轮，可配置）。
8. **Working Memory**：本轮已产生的中间结果、Tool 返回值、Plan 状态。
9. **Knowledge Graph**：与当前话题相关的实体与关系。
10. **Tool State**：当前可用工具列表、Tool 繁忙状态、Rate Limit。

### 4.2 Context Ranking 算法

Ranking 必须综合以下维度，输出 0–1 的分数：

- **Relevance Score**：与当前用户输入的语义/关键词相似度。
- **Recency Score**：时间越近越高，但非线性（24h 内权重高，超过 7 天骤降）。
- **Importance Score**：由模块维护（如 Goal 优先级、User Model confidence、Memory 标注的重要性）。
- **Source Reliability**：World State 高于推测性记忆；用户确认过的高于自动抽取。

Ranking 公式（规范）：

```
final_score = w1*relevance + w2*recency + w3*importance + w4*reliability
```

权重默认：`relevance=0.35, recency=0.25, importance=0.25, reliability=0.15`。权重可在 Personality 或配置中微调，但必须在 `ContextEngineConfig` 中显式声明。

### 4.3 Context Budget 算法

- 支持的 Token 预算档位：16K、32K、64K、96K。
- 预算分配顺序（必须保留 System Base 与最近 N 轮）：
  1. 保留 System Base（含 Personality + World 摘要）。
  2. 保留最近 6 轮 Episode Memory（可配置）。
  3. 按 Ranking 从高到低填充 Goal、User Model、Long-Term Memory、Knowledge Graph、Working Memory、Tool State。
  4. 每类 Context 设置内部上限（例如 Long-Term Memory 最多占预算 30%）。
- 当总 token 超过预算时，按 Ranking 从低到高裁剪，不得删除 System Base 与最近 2 轮对话。
- 必须记录本次裁剪摘要（删除了哪些来源、各来源占比），写入审计日志。

### 4.4 禁止事项

- **禁止**把全部 Memory 直接塞进 Prompt。
- **禁止**由调用方手写拼接 System Prompt（必须通过 Context Engine）。
- **禁止**在 Context Engine 内部调用 LLM 做排序（排序应当是确定性的本地算法，LLM 仅可在可选的 Rerank 步骤中调用）。

---

## 第五章 Memory Architecture

### 5.1 记忆分层

| 类型 | 定义 | 生命周期 | 写入触发 | 删除/压缩 |
|---|---|---|---|---|
| Working Memory | 单轮 Runtime 内的临时上下文 | 本轮有效，Idle 时清理 | Runtime 各阶段写入 | 自动清理 |
| Conversation Memory | 近期多轮对话原始记录 | 保留最近 N 轮（默认 50） | 每轮结束 | 超阈值后归档到 Episode Memory |
| Episode Memory | 按事件/会话组织的压缩记忆 | 长期保留 | 对话结束或手动触发 | 低重要性 + 过期可压缩/遗忘 |
| Long-Term Memory | 经提取的事实、画像、项目、人物 | 永久保留 | Reflection 确认或显式确认 | 自动遗忘策略 |
| Semantic Memory | 向量化的语义片段 | 与 Long-Term 同步 | LLM 抽取或 Embedding | 按相似度合并 |
| Goal Memory | 目标相关的进展、失败、复盘 | 与 Goal 生命周期一致 | Goal Update 阶段 | Goal 废弃时归档 |
| Knowledge Memory | 从外部文档/网页/代码提取的结构化知识 | 长期 | Workflow 或 Skill 触发 | 按引用频率遗忘 |

### 5.2 写入规则

- **Working Memory**：任何 Runtime 中间产物均可写入，但不得落盘。
- **Conversation Memory**：每轮用户与 Agent 的完整交互必须落盘。
- **Episode Memory**：当 Conversation Memory 超过阈值，或 Reflection 判定某次对话为重要事件时，生成 Episode。
- **Long-Term Memory**：仅当 Reflection 判定“该事实值得长期保留”或用户显式确认后才写入。
- **Semantic Memory**：Long-Term Memory 写入后异步生成 Embedding。

### 5.3 压缩与遗忘

- **压缩**：当 Conversation Memory 超过阈值，触发后台压缩线程，将旧对话提炼为 Episode Memory。
- **遗忘**：Long-Term Memory 采用置信度 × 时间衰减模型。低 confidence + 长期未被检索的记录进入“待遗忘”状态，经 Reflection 二次确认后删除或归档。
- **禁止**：任何模块不得直接删除 Long-Term Memory，必须通过 `MemoryManager.archive_or_forget()` 接口。

---

## 第六章 World Model

### 6.1 World State 定义

`WorldModel` 维护一个统一、只读（外部）、按需刷新的世界快照 `WorldSnapshot`。内容包括：

| 域 | 说明 | 来源 |
|---|---|---|
| time | 本地时间、日期、星期、时区 | 系统时钟 |
| location | 当前位置（城市、经纬度、所在地类型） | geo_weather / IP / 用户配置 |
| weather | 当前天气、温度、AQI、预警 | geo_weather + 缓存 |
| device | 当前设备 ID、类型、电量、网络类型 | 系统 API / Electron 桥 |
| cpu / gpu / memory | 使用率、温度、可用容量 | sysmon |
| running_software | 当前活跃软件/进程（受隐私策略限制） | sysmon（可选） |
| git_status | 当前项目分支、未提交变更、最近提交 | 本地 shell / Git 库扫描 |
| current_project | 当前工作目录对应的项目名 | Git 根目录 / 用户标记 |
| network | 网络可达性、延迟、代理状态、外部服务健康 | self_check / http_client |
| devices | 已注册协同设备列表 | devices.py |
| work_hours / rest_hours | 工作时间、休息时间、勿扰模式 | User Model + 配置 |
| events_today | 今日日程/任务/Deadline | Goal + Task + 外部日历（可选） |

### 6.2 刷新策略

- **time**：每次 snapshot 实时读取。
- **weather / location**：TTL 默认 10 分钟，可配置。
- **cpu/gpu/memory**：TTL 默认 30 秒。
- **git_status / current_project**：TTL 默认 5 分钟；进入新项目时主动刷新。
- **network**：TTL 默认 1 分钟；外部服务健康检查可异步。

### 6.3 状态变化事件

任何 World State 域发生重大变化（如位置变化、天气预警、网络中断、项目切换），必须发布 `WorldStateChanged` 事件到 EventBus，供 Proactive、Context Engine、Developer Dashboard 订阅。

---

## 第七章 Cognitive State

### 7.1 Agent 自身状态机

Agent Runtime 必须维护并对外广播以下 Cognitive State：

| 状态 | 含义 | 允许转换 |
|---|---|---|
| IDLE | 空闲，等待输入 | → THINKING / SLEEPING |
| THINKING | 加载上下文、Planning、Reasoning | → PLANNING / SEARCHING / EXECUTING / ERROR / WAITING |
| PLANNING | 正在拆解目标 | → REASONING / ERROR |
| SEARCHING | 正在检索记忆/知识/网络 | → REASONING / EXECUTING / ERROR |
| LEARNING | 正在从结果中学习/更新模型 | → REFLECTING / IDLE |
| EXECUTING | 正在执行工具/工作流/技能 | → REFLECTING / ERROR / WAITING |
| REFLECTING | 正在复盘本轮 | → IDLE / ERROR / LEARNING |
| SLEEPING | 低功耗待机，仅 Proactive 可唤醒 | → IDLE |
| BUSY | 资源满载，新请求排队 | → THINKING（资源释放后） |
| WAITING | 等待用户确认/外部回调 | → THINKING / IDLE |
| ERROR | 发生不可恢复错误 | → IDLE（人工/自动恢复后） |

### 7.2 HUD 实时展示

Developer Dashboard 与主界面 HUD 必须订阅 `CognitiveStateChanged` 事件，实时显示当前状态、状态持续时间、当前 Plan 摘要、正在执行的工具名。

---

## 第八章 Decision Engine

### 8.1 决策分层

Decision Engine 是 Reasoning 与 Executor 之间的显式闸门。它回答一组布尔/分类问题：

| 决策 | 问题 | 输入 | 输出 |
|---|---|---|---|
| Should Search | 是否需要搜索记忆/知识/网络？ | 用户输入 + 当前 Context 缺口 | yes/no + search_target |
| Should Ask User | 信息是否不足需要追问？ | Context 完整度 + Goal 必填项 | yes/no + question |
| Should Use Tool | 是否必须调用工具？ | 用户意图 + 可用工具 | yes/no + tool_candidates |
| Should Save Memory | 是否保存本轮为长期记忆？ | Reflection 结果 + 重要性 | yes/no + memory_type |
| Should Update Goal | 是否更新目标进度？ | Reflection 中的 progress | yes/no + goal_id |
| Should Execute Workflow | 是否触发工作流？ | 用户输入匹配 Workflow 触发器 | yes/no + workflow_id |
| Should Wait | 是否等待外部事件/用户确认？ | 工具返回需确认 / 资源不足 | yes/no + reason |
| Should Reject | 是否拒绝危险/越权请求？ | Sandbox 审计 + 安全策略 | yes/no + reason |

### 8.2 决策树原则

- 安全决策（Should Reject）具有最高优先级，必须先执行。
- 资源决策（Should Wait / Should Use Tool）次之。
- 学习决策（Should Save Memory / Should Update Goal）在 Reflection 后执行。
- 所有决策必须记录到审计日志，并附决策理由（rationale）。

---

## 第九章 Planner

### 9.1 Planner 职责

- 接收用户请求、Goal、World State，产出可执行的 `Plan`。
- Plan 由有序的 `Step` 组成，每个 Step 包含：step_id、type（tool/llm/workflow/skill/memory/wait）、target、input、dependencies、expected_output、retry_policy。
- 支持子 Plan：Step 可以嵌套子 Plan，形成层级任务树。

### 9.2 Goal 拆解

- Planner 必须读取活跃 Goal，判断用户请求是否与 Goal 相关。
- 若相关，Planner 应将请求拆解为朝向 Goal 的子任务；若不相关，产出独立 Plan。
- 拆解结果必须标注每个 Step 对 Goal 的贡献度（0–1）。

### 9.3 依赖分析

- Step 的 `dependencies` 必须显式声明，Executor 据此决定串行/并行。
- 无依赖的写操作 Step 必须串行；无依赖的读操作 Step 可以并行。
- 循环依赖必须在 Planning 阶段报错，不得进入 Execution。

### 9.4 失败恢复

- 若 Planner 无法产出有效 Plan（如目标模糊），必须生成 Fallback Plan（单步：向用户澄清）。
- Planner 本身超时或失败，不得阻塞 Runtime，必须进入 Recovery Path。

---

## 第十章 Reasoning

### 10.1 Reasoning 职责

- 对 Planner 产出的 Plan 进行“思考”：评估每一步合理性、预判工具结果、识别信息缺口、选择下一步动作。
- 产出 `ReasoningResult`：包含 reasoning_text（思维链）、next_action、confidence、assumptions、risks。

### 10.2 思考过程

标准思考框架：

1. **理解意图**：用户到底想要什么？
2. **评估上下文**：已有信息是否足够？
3. **识别缺口**：缺少哪些事实？需要搜索/询问/假设？
4. **选择工具**：哪些工具最可能填补缺口？
5. **验证假设**：哪些假设需要在执行后验证？
6. **风险分析**：调用失败、结果不可靠、隐私/安全风险的应对方案。

### 10.3 工具选择

- Reasoning 只选择工具候选集，不直接调用工具。
- 工具选择必须基于 Tool Registry 的元数据（description、参数、副作用、 Busy 状态）。
- 对高副作用工具（写文件、发消息、删除数据），必须降低选择阈值并触发额外 Decision 审核。

### 10.4 假设验证

- Reasoning 必须显式列出 `assumptions`。
- Executor 执行后，Reflection 必须验证这些假设是否成立；不成立的假设进入 Learning 流程。

---

## 第十一章 Reflection

### 11.1 Reflection 职责

每轮 Runtime 结束时，Reflection 模块必须执行以下分析：

1. **任务成功度**：Plan 是否完成？用户请求是否满足？
2. **工具失败分析**：哪些 Tool 失败？失败原因？是否可重试？
3. **Prompt 充分性**：上下文是否足够？是否因裁剪丢失关键信息？
4. **知识更新**：是否需要写入 Long-Term Memory / Knowledge Graph？
5. **Goal 更新**：是否需要更新 Goal 进度、状态、优先级？
6. **用户模型更新**：是否发现新的用户习惯/偏好/项目？
7. **人格适配**：本轮回复是否匹配 Personality 参数？

### 11.2 ReflectionResult 输出

`ReflectionResult` 必须包含：

- success_score（0–1）
- completed_steps / failed_steps
- tool_failures 列表（tool / reason / recoverable）
- memory_insights（待写入记忆列表）
- goal_updates（待更新目标列表）
- user_model_updates（待更新画像列表）
- learned_lessons（可复用经验）
- next_round_suggestions（对下一轮的建议）

### 11.3 对下一轮的影响

- ReflectionResult 中的 `next_round_suggestions` 必须被写入 Working Memory，供下一轮 Context Engine 读取。
- 若 Reflection 发现高频失败模式，必须发布 `PatternDetected` 事件，触发 Skill 或 Workflow 优化建议。

---

## 第十二章 Goal System

### 12.1 Goal 分类

| 类型 | 定义 | 示例 |
|---|---|---|
| 长期目标（Long-term） | 持续数周以上的方向性目标 | “提升 Python 水平”“完成项目 X” |
| 短期目标（Short-term） | 数小时到数天内完成 | “今天修复 bug #123” |
| 一次性目标（One-shot） | 单次请求即完成 | “查一下明天的天气” |
| 循环目标（Recurring） | 按周期重复 | “每天早上 9 点生成日报” |

### 12.2 Goal 属性

每个 Goal 必须包含：goal_id、title、description、type、priority（1–5）、deadline、status（active/paused/completed/abandoned）、progress（0–100）、parent_goal_id（可选）、associated_task_ids、created_at、updated_at、source（用户/Agent/Workflow）。

### 12.3 自动生成与废弃

- Agent 可以根据对话内容自动提议 Goal，但**禁止**自动创建高优先级长期 Goal；必须经用户确认。
- 过期且未完成的 Goal 进入 `stale` 状态，由 Reflection 提议废弃或延期。
- 已完成的 Goal 保留为 Goal Memory，供未来复盘。

### 12.4 Goal 与任务关联

- Goal 可以关联 Task（来自 `tasks.py` 或 Workflow）。
- 当 Task 完成时，必须发布 `TaskCompleted` 事件，GoalManager 自动重新计算相关 Goal 的 progress。

---

## 第十三章 User Model

### 13.1 User Profile 组成

`UserModel` 统一维护以下画像维度：

- 工作习惯：工作时段、专注模式、常用工具链、项目偏好。
- 开发习惯：常用语言、框架、编码风格、调试偏好。
- 常用软件：IDE、浏览器、通讯工具、设计工具等。
- 偏好：回复长度、解释深度、主动程度、严肃/幽默倾向。
- 项目：用户参与的项目列表、角色、技术栈、当前优先级。
- 联系人：人物名称、关系、联系方式、上下文。
- 兴趣：技术方向、爱好、学习目标。
- 学习方向：正在学习的内容、进度、资源。

### 13.2 每条记录元数据

每个画像条目必须附带：

- confidence（0–1）：置信度。
- last_update：最后更新时间。
- source：来源（用户显式/对话抽取/Workflow/Skill）。
- importance：重要性权重。
- evidence：支撑该条目的原始证据引用。

### 13.3 自动遗忘与更新

- 低 confidence + 长期未被使用 + 与新证据矛盾的条目进入待遗忘队列。
- 新证据与旧条目冲突时，按 confidence 与 source 可信度决定更新或保留旧值并标记冲突。
- 所有更新必须经 Reflection 确认或用户显式确认（高 importance 条目）。

---

## 第十四章 Knowledge Graph

### 14.1 节点类型

知识图谱节点类型必须包含：

- Project（项目）
- Task（任务）
- Person（人物）
- Document（文档/笔记/代码文件）
- Goal（目标）
- Issue（问题/Bug）
- Memory（记忆节点）
- Tool（工具）
- Workflow（工作流）
- Skill（技能）

### 14.2 关系类型

必须支持的关系：

- belongs_to / part_of
- depends_on / blocks
- related_to
- created_by / owned_by
- mentions
- solved_by / caused_by
- uses（Tool/Skill/Workflow 被某项目/任务使用）

### 14.3 查询与更新

- 查询接口必须支持：按节点 ID、按关系跳数、按类型过滤、按时间范围过滤。
- 更新必须通过 EventBus 发布 `KnowledgeGraphUpdated` 事件，禁止直接写入图数据库后不发事件。
- 图更新必须是幂等的：同一证据多次抽取不得产生重复节点（通过唯一键去重）。

---

## 第十五章 Event Bus

### 15.1 地位

EventBus 是系统唯一的模块间通信脊柱。除基础设施共享（日志、配置读取、数据库连接池）外，所有模块间交互必须通过 EventBus。

### 15.2 事件模型

每个事件必须包含：

- event_id（UUID）
- topic（事件类型，如 `ConversationStarted`）
- timestamp
- source（发布模块名）
- payload（DTO，强类型）
- priority（0–9，默认 5）
- correlation_id（用于追踪同一轮对话/同一工作流）

### 15.3 核心事件列表

必须支持的事件（但不限于）：

- ConversationStarted / ConversationFinished
- GoalUpdated / TaskCreated / TaskCompleted
- MemoryUpdated / MemoryCompressed
- WeatherUpdated / WorldStateChanged
- ToolFinished / ToolFailed
- WorkflowStarted / WorkflowFinished / WorkflowFailed
- SkillInstalled / SkillUninstalled
- PersonalityChanged / UserModelUpdated
- CognitiveStateChanged / ResourcePressure
- PatternDetected / ReflectionCompleted

### 15.4 Pub/Sub 语义

- **Publish**：异步、非阻塞；发布者不关心订阅者数量。
- **Subscribe**：支持同步（立即执行）与异步（线程池）订阅者。
- **Priority**：高优先级事件优先派发。
- **Retry**：订阅者失败时，根据事件重要性重试 0–3 次。
- **Dead Letter**：重试耗尽的事件进入 Dead Letter 队列，供 Developer Dashboard 展示。

### 15.5 禁止事项

- 禁止模块 A `import B; B.do_something()` 式直接调用。
- 禁止在 EventBus 中携带不可序列化的对象（如文件句柄、数据库连接、HTTP Response）。
- 禁止订阅者阻塞发布线程超过 100ms（同步订阅者必须极轻量）。

---

## 第十六章 Workflow Engine

### 16.1 Workflow 规范

Workflow 使用 YAML 描述，包含：

- metadata：id、name、version、description、author、triggers
- variables：输入变量与默认值
- steps：步骤列表
- on_error：错误处理策略

### 16.2 节点类型

必须支持的节点：

- start / end
- llm：调用 LLM
- tool：调用 Tool
- memory：读写 Memory
- condition：分支
- loop：循环（for/while）
- wait：等待事件或时间
- retry：重试包装器
- parallel：并行执行多个分支
- skill：调用 Skill

### 16.3 控制流

- Condition 支持表达式，表达式只能访问 variables 与 step outputs。
- Loop 必须设置最大迭代次数，防止死循环。
- Retry 必须配置 max_attempts、backoff、retryable_errors。
- Timeout 可在任意节点上设置，超时后走 on_error。

### 16.4 安全与隔离

- Workflow 加载时必须经过 Schema 校验与 Sandbox 审计。
- Workflow 中调用写操作节点必须二次确认（除非用户显式授权）。
- Workflow 执行上下文与 Runtime 隔离，错误不得拖垮主进程。

---

## 第十七章 Skill System

### 17.1 Skill 组成

一个 Skill 是一个自包含包，必须包含：

- skill.yaml：元数据、版本、依赖、触发器、权限声明
- prompt/：专属 Prompt 模板
- workflow/：专属 Workflow
- memory/：初始化记忆模板
- goals/：默认目标模板
- tools/：专属 Tool 注册（可选）
- assets/：静态资源、图标、文档

### 17.2 Skill 生命周期

- Discover：扫描 skills/ 目录与市场。
- Install：校验、加载、注册到 Skill Registry，发布 `SkillInstalled`。
- Enable/Disable：运行时切换，不删除文件。
- Uninstall：注销、清理事件订阅、发布 `SkillUninstalled`。
- Update：版本升级需经过兼容性校验与 Rollback 方案。

### 17.3 依赖与权限

- Skill 必须声明所需权限（文件读写、网络、外部命令、敏感数据）。
- Skill 依赖的其他 Skill 必须在 skill.yaml 中显式列出。
- Skill 不得覆盖核心系统事件 Topic，只能订阅与发布自定义事件（除非注册为系统扩展）。

---

## 第十八章 Tool System

### 18.1 Tool 生命周期

1. **Register**：Tool 向 Tool Registry 注册 name、description、parameters、returns、side_effects、timeout、permissions。
2. **Discover**：Reasoning / Planner 查询 Tool Registry 元数据。
3. **Schedule**：Executor 通过 Resource Manager 申请资源后调度执行。
4. **Execute**：Tool 实际运行，必须返回结构化结果（success / error / partial）。
5. **Audit**：Sandbox 记录调用参数与结果（脱敏）。
6. **Reflect**：Reflection 分析 Tool 结果是否满足预期。

### 18.2 权限

- 每个 Tool 必须声明权限级别：read、write、network、shell、privacy_sensitive。
- 高权限 Tool 默认需要用户授权或 Decision Engine 放行。
- Tool 不得访问声明范围之外的资源。

### 18.3 超时与取消

- Tool 必须声明默认超时；Executor 可覆盖。
- Tool 必须支持取消信号（cooperative cancellation）。
- 超时或取消必须返回明确错误码，不得静默失败。

### 18.4 日志、重试、缓存

- 所有 Tool 调用必须记录到审计日志。
- 可重试的 Tool 失败必须由 Executor 重试，重试策略在 Plan Step 中声明。
- 读操作 Tool 可声明缓存策略；缓存必须带 TTL，写操作禁止缓存。

---

## 第十九章 Personality Engine

### 19.1 人格维度

Personality 由五个可配置维度构成：

- 专业程度（professionalism）：0–1，越高越正式、术语越多。
- 主动程度（proactivity）：0–1，越高越主动提议、提醒、追问。
- 技术深度（technical_depth）：0–1，越高越深入底层原理。
- 解释长度（verbosity）：0–1，越高回复越详细。
- 严肃程度（seriousness）：0–1，越低越轻松幽默。

### 19.2 动态生成

- Personality Engine 根据 User Model、当前 Goal、World State、历史对话，每轮生成一组 Personality Parameters。
- 这些参数被注入 Context Engine，影响 System Prompt 的措辞与长度。
- Personality 不是固定 Prompt；禁止把人格写死在 `config.SYSTEM_PROMPT` 中。

### 19.3 用户控制

- 用户可通过设置面板显式调整人格维度。
- 用户可保存多个人格 Profile（如“工作模式”“学习模式”“休闲模式”）。
- Agent 不得在未告知用户的情况下，将 Personality 调整为极端值。

---

## 第二十章 Resource Manager

### 20.1 资源类型

Resource Manager 统一调度：

- CPU / GPU / Memory（本地计算资源）
- API Rate Limit（LLM、搜索、天气等外部 API）
- Tool Busy（有并发限制的工具）
- Workflow Busy（运行中工作流槽位）
- LLM Busy（并发推理槽位）

### 20.2 资源申请

- Executor 在执行 Tool / Workflow / Skill 前必须向 Resource Manager 申请资源令牌。
- 资源不足时进入队列；队列支持优先级与超时。
- 高优先级任务（用户主动请求）可抢占低优先级后台任务（预热、Workflow）。

### 20.3 排队与抢占

- 排队必须公开给 Developer Dashboard（队列长度、预计等待时间）。
- 抢占必须触发 `ResourcePreempted` 事件，被抢占任务进入保存点（savepoint）以便恢复。
- 禁止无限排队，必须设置最大等待时间，超时返回 `ResourceUnavailable`。

---

## 第二十一章 Developer Dashboard

### 21.1 定位

Developer Dashboard 是 Electron 桌面端（或浏览器开发者模式）的独立面板，用于实时观测与调试 Agent。

### 21.2 必须显示的信息

- Current Prompt（当前注入 LLM 的完整 Prompt）
- Current Context（各来源占比、Token 使用情况）
- Current Goal（活跃 Goal 列表）
- Current Workflow（运行中工作流）
- Current Cognitive State（状态机可视化）
- Current Planner Plan（当前 Plan 与 Step 状态）
- Current Reflection（最近 ReflectionResult）
- Tool Queue（等待/执行中的工具）
- Memory Queue（待压缩/待嵌入的记忆）
- Event Bus（最近 50 条事件流）
- Latency（各阶段耗时）
- Token（本轮消耗）
- Cost（估算 API 费用）

### 21.3 交互能力

- 允许手动触发 Workflow。
- 允许查看/编辑 Context Budget 参数。
- 允许模拟用户输入进行沙盒测试。
- 允许导出当前 Prompt 与事件日志。

---

## 第二十二章 模块职责边界

### 22.1 核心模块边界表

| 模块 | 必须负责 | 绝不能负责 | 唯一允许通信方式 |
|---|---|---|---|
| api/chat.py | HTTP 聊天路由、SSE 流管理 | Agent 运行逻辑 | 调用 AgentRuntime.run() |
| agent/runtime.py | 编排 Planner/Reasoning/Executor/Reflection | 数据库访问、HTTP | EventBus + 返回 DTO |
| agent/planner.py | 拆解 Plan | 执行工具 | 返回 Plan DTO |
| agent/reasoning.py | 思考与工具候选选择 | 直接调用工具 | 返回 ReasoningResult |
| agent/executor.py | 执行 Plan Step | 业务编排、HTTP | 调用 Tool Registry / Resource Manager |
| agent/reflection.py | 复盘与学习 | 修改外部状态 | 发布事件 + 返回 ReflectionResult |
| context_engine.py | 动态拼装 Prompt | 直接调用 LLM | 返回 ContextSnapshot |
| world_state.py | 维护世界快照 | 业务决策 | 发布 WorldStateChanged |
| goals/manager.py | 目标 CRUD、进度计算 | 直接调用工具 | 发布 GoalUpdated |
| user_model.py | 用户画像维护 | 直接回复用户 | 发布 UserModelUpdated |
| personality.py | 人格参数生成 | 固定 Prompt | 返回 PersonalityParams |
| eventbus.py | 事件路由 | 业务语义 | Pub/Sub |
| memory.py | 记忆读写压缩 | 主动推送 | 发布 MemoryUpdated |
| tools.py / tool registry | 工具注册与执行 | 业务编排 | 被 Executor 调用 |
| workflow/engine.py | 工作流解释执行 | 业务决策 | 被 Executor / EventBus 触发 |
| skills/registry.py | Skill 生命周期 | 直接执行业务 | 被 Executor / Workflow 调用 |
| resource_manager.py | 资源调度 | 业务决策 | 被 Executor 申请 |

### 22.2 通用边界原则

- 任何模块不得直接读写其他模块的数据库文件。
- 任何模块不得直接修改其他模块的内部状态对象。
- 任何模块发生状态变更，必须通过 EventBus 发布事件。

---

## 第二十三章 数据库规范

### 23.1 数据库划分

| 数据库 | 用途 | 是否允许修改 |
|---|---|---|
| xiao6.db | 已有记忆、笔记、任务、审计、prefetch_cache | 现有表结构不得破坏；新增扩展表需 Migration |
| goals.db | Goal System 专属 | 新增，独立 |
| user_profile.db | User Model 专属 | 新增，独立 |
| knowledge_graph.db | Knowledge Graph 专属 | 新增，独立 |
| workflow_state.db | Workflow 运行状态（持久化） | 新增，独立 |

### 23.2 Migration 规范

- 所有 Schema 变更必须通过版本化 Migration 脚本执行。
- Migration 必须可回滚（Rollback），并经过本地测试。
- 禁止手动修改生产数据库。
- Migration 脚本必须记录到 `db/migrations/` 目录，命名格式：`YYYYMMDD_HHMMSS_description.sql`。

### 23.3 数据访问

- 业务代码不直接执行 SQL，必须通过 Repository 层。
- Repository 层不得跨数据库直接 JOIN。
- 所有写操作必须记录到审计日志。

---

## 第二十四章 目录规范

### 24.1 目标目录结构

```
xiao6-ui/
├── server.py                  # 极薄启动入口
├── api/                       # HTTP 路由层
│   ├── __init__.py
│   ├── chat.py
│   ├── memory.py
│   ├── settings.py
│   ├── tools.py
│   ├── system.py
│   ├── notification.py
│   ├── static.py
│   ├── devices.py
│   ├── workflow.py
│   └── skill.py
├── agent/                     # Agent Runtime
│   ├── __init__.py
│   ├── runtime.py
│   ├── planner.py
│   ├── reasoning.py
│   ├── executor.py
│   ├── reflection.py
│   └── types.py
├── cognitive/                 # 认知服务层
│   ├── context_engine.py
│   ├── world_state.py
│   ├── user_model.py
│   ├── personality.py
│   └── knowledge_graph.py
├── goals/                     # Goal System
│   ├── manager.py
│   ├── models.py
│   └── db.py
├── eventbus.py                # 事件总线
├── workflow/                  # Workflow Engine
│   ├── engine.py
│   ├── loader.py
│   ├── steps.py
│   └── workflows/
├── skills/                    # Skill System
│   ├── registry.py
│   ├── loader.py
│   └── builtin/
├── tools/                     # Tool System（原 tools.py 拆分）
│   ├── registry.py
│   ├── executor.py
│   ├── builtin/               # 23 工具按领域分组
│   └── permissions.py
├── memory/                    # Memory System（原 memory.py 升级）
│   ├── manager.py
│   ├── repository.py
│   ├── compressor.py
│   └── embeddings.py
├── resource/                  # Resource Manager
│   └── manager.py
├── db/                        # Migration + 连接管理
│   ├── connection.py
│   └── migrations/
├── config/                    # 配置服务
│   └── service.py
├── sandbox.py                 # 安全审计
├── llm.py                     # LLM 调用层
├── self_check.py              # 系统自检
├── sysmon.py                  # 系统监控
├── geo_weather.py             # 天气/定位
├── hotspots.py                # 热点舆情
├── notes.py                   # 笔记 Vault
├── tasks.py                   # 任务管理
├── asr.py                     # 语音转写
├── media.py                   # 媒体生成
├── social.py                  # 社交渠道
├── message_processor.py       # 消息处理面板数据
├── http_client.py             # 统一 HTTP 客户端
├── data/                      # 数据库文件目录
│   ├── xiao6.db
│   ├── goals.db
│   ├── user_profile.db
│   ├── knowledge_graph.db
│   └── workflow_state.db
├── tests/                     # 测试目录（与源码对应）
├── app.js                     # 前端主应用
├── index.html
├── styles.css
└── vendor/
```

### 24.2 目录职责说明

- `api/`：只放 HTTP 路由与参数校验，不放业务逻辑。
- `agent/`：只放 Agent Runtime 生命周期，不放数据库访问。
- `cognitive/`：只放为 Runtime 提供上下文的认知服务。
- `tools/`：工具注册、执行、权限、内置工具包；原 `tools.py` 必须拆分。
- `memory/`：记忆读写、压缩、Embedding；原 `memory.py` 必须拆分。
- `workflow/`：工作流引擎与 YAML 工作流。
- `skills/`：Skill 注册表与内置技能包。

### 24.3 禁止事项

- 禁止任何目录下出现超过 500 行的业务文件（God File）。
- 禁止跨目录直接 import 业务模块（必须通过接口或 EventBus）。
- 禁止循环依赖；出现循环依赖时必须引入抽象接口或事件。

---

## 第二十五章 编码规范

### 25.1 日志

- 使用结构化 JSON 日志，必须包含 `request_id` 或 `correlation_id`。
- 日志级别：error（需立即处理）、warn（异常但已处理）、info（关键审计）、debug（开发调试）。
- 禁止 `print`，禁止在生产代码中使用 `console.log`。
- 禁止在日志中输出密码、Token、PII、文件内容。

### 25.2 异常

- 使用类型化异常体系，所有业务异常继承 `Xiao6Error`。
- 异常必须携带 `code`、`message`、`status_code`（HTTP 相关）、`is_operational`。
- 控制器层必须有全局异常处理器，不得把堆栈返回给客户端。
- 禁止静默捕获异常。

### 25.3 类型

- Python 代码必须使用类型注解（type hints）。
- 所有 DTO 必须使用 dataclass / Pydantic / TypedDict 定义，禁止用裸字典传递业务数据。
- mypy 类型检查必须通过。

### 25.4 注释

- 公共接口必须写 docstring，说明输入、输出、异常、副作用。
- 复杂算法必须解释“为什么”。
- 禁止无意义的注释。

### 25.5 接口与 DTO

- 模块间接口必须显式定义，禁止依赖隐式约定。
- DTO 命名规范：`<Action><Entity>Request` / `<Action><Entity>Response`。
- DTO 字段使用英文，注释用中文。

### 25.6 命名

- 模块/文件：小写 + 下划线。
- 类：PascalCase。
- 函数/变量：snake_case。
- 常量：UPPER_SNAKE_CASE。
- 事件 Topic：PascalCase，动词 + 名词。
- 私有方法/变量：前缀 `_`。

---

## 第二十六章 性能规范

### 26.1 响应时间

| 路径 | 最大响应时间 |
|---|---|
| API 健康检查 | < 200ms |
| 聊天首字（Time to First Token） | < 1.5s |
| 聊天完整回复（简单问题） | < 10s |
| 工具调用（本地） | < 5s |
| 工具调用（外部网络） | < 30s |
| Workflow 启动 | < 500ms |
| Context Engine 装配 | < 2s |

### 26.2 Prompt 与上下文

- System Prompt + Context 总长度默认不超过 16K Token；可配置到 32K/64K/96K。
- Long-Term Memory 注入条数默认不超过 20 条。
- Goal 注入默认不超过 5 个活跃目标。
- 必须记录每轮 Token 消耗与占比。

### 26.3 Memory 数量

- Conversation Memory 保留最近 50 轮。
- Episode Memory 保留最近 200 条。
- Long-Term Memory 无硬性上限，但低重要性条目必须遗忘。

### 26.4 缓存策略

- World State 按域 TTL 缓存。
- 读操作 Tool 可带 TTL 缓存。
- LLM 响应不缓存（除明确可缓存的摘要类调用）。
- 所有缓存必须带 TTL，禁止无 TTL 缓存。

---

## 第二十七章 安全规范

### 27.1 权限

- 每个 Tool、Skill、Workflow 必须声明权限清单。
- 高权限操作必须二次确认或用户预授权。
- Agent 不得自行授权自己提升权限。

### 27.2 危险命令

- 所有 shell/系统命令必须通过 `sandbox.py` 审计。
- 危险命令（rm、format、disk、registry、kill 等）默认拒绝。
- 允许白名单机制：用户可在配置中显式声明可信命令前缀。

### 27.3 Prompt Injection

- 用户输入、工具返回、网页内容在注入 Prompt 前必须经过清洗与边界标注。
- 禁止把不可信内容直接拼接到 System Prompt。
- 对高敏感操作（删除、发送、修改配置），必须要求显式确认。

### 27.4 Tool 隔离

- 每个 Tool 运行在独立执行上下文中，错误不得影响主进程。
- Tool 返回必须结构化，禁止返回原始异常堆栈。
- 高副作用 Tool 必须支持取消与回滚。

### 27.5 API 保护

- 所有 API 必须校验输入参数。
- 静态文件服务必须限制访问范围，禁止任意文件读取。
- 配置接口必须防止写入敏感字段（如 API Key 之外的黑名单字段）。

### 27.6 数据安全

- 用户数据默认本地存储，不得明文传输到未授权第三方。
- 日志中不得记录明文 Token、密码、私钥。
- 数据库文件必须可被用户备份、导出、删除。

---

## 第二十八章 扩展规范

### 28.1 新增 Tool

1. 在 `tools/builtin/` 下新建模块。
2. 实现执行函数，返回结构化 DTO。
3. 在 `tools/registry.py` 注册 name、description、parameters、returns、permissions、timeout。
4. 编写单元测试与集成测试。
5. 更新能力清单面板元数据。

### 28.2 新增 Skill

1. 在 `skills/builtin/` 下新建目录。
2. 编写 `skill.yaml`，声明元数据、权限、依赖、触发器。
3. 放置 prompt/workflow/memory/goals/tools 子目录。
4. 通过 Skill Registry 加载。
5. 编写测试与文档。

### 28.3 新增 Workflow

1. 在 `workflow/workflows/` 下新建 YAML。
2. 使用 Workflow Engine 支持的节点。
3. 通过触发器或 Developer Dashboard 注册。
4. 必须经过 Schema 校验与 Sandbox 审计。

### 28.4 新增 Memory 类型

1. 在 `memory/repository.py` 中新增表/集合。
2. 在 Memory Manager 中新增读写方法。
3. 在 Context Engine 中新增来源与 Ranking 权重。
4. 提供 Migration 与 Rollback 脚本。

### 28.5 新增 API

1. 在 `api/` 下新建路由模块或扩展现有模块。
2. 参数校验、DTO、错误处理必须完整。
3. 不得直接调用数据库，必须调用对应领域服务。
4. 更新测试与文档。

### 28.6 新增 LLM Provider

1. 在 `llm.py` 中实现 Provider Adapter，统一接口为 `completion(messages, tools, ...)`。
2. 配置中声明 provider、base_url、model、key。
3. 不得破坏现有 Agnes 调用路径。

---

## 第二十九章 未来演进路线

### 29.1 版本边界

| 版本 | 主题 | 允许变化 |
|---|---|---|
| v2 | Agent OS 骨架 | EventBus、Agent Runtime、Context Engine、World/Goal/User/Personality、Server 模块化 |
| v3 | 自主智能增强 | Proactive 升级、多 Agent 协作、长期记忆自组织、知识图谱自动扩展 |
| v4 | 多模态与具身 | 视觉、语音、设备控制、跨端协同、本地模型推理（LLM on device） |

### 29.2 允许变化

- 具体 LLM Provider 可替换。
- 具体 Tool 实现可替换。
- 前端框架/组件库可逐步升级。
- 数据库引擎可在保持接口抽象的前提下替换（如 SQLite → PostgreSQL）。
- Workflow 节点类型与 Skill 包可无限扩展。

### 29.3 永远不能变化

- Local First 原则。
- EventBus 作为唯一模块通信方式。
- Agent Runtime 的分层（Planner / Reasoning / Decision / Executor / Reflection）。
- Context 必须由 Context Engine 生成。
- 向后兼容原则。
- 安全审计必须存在。

---

## 第三十章 Architecture Constitution（架构宪法）

以下铁律为 Xiao6 系统的最高约束，任何后续设计、代码、Skill、Workflow 均不得违反。

1. **不允许 God Module**。任何业务文件不得超过 500 行；超过必须拆分。
2. **不允许跨模块直接调用**。模块间通信必须通过 EventBus。
3. **Context 必须由 Context Engine 生成**。禁止任何模块手写 System Prompt。
4. **Planner 不得直接调用 Tool**。Planner 只产出 Plan，执行由 Executor 负责。
5. **Tool 不得操作数据库业务逻辑**。Tool 只能执行声明的原子操作，状态变更通过事件。
6. **Goal 不能直接修改 Memory**。Goal 更新必须通过 EventBus 触发 Memory / User Model 更新。
7. **Reflection 必须发生在每轮结束**。任何 Runtime 闭环都必须包含 Reflection。
8. **所有新模块必须可独立测试**。不得依赖其他模块的真实实例才能跑单测。
9. **所有升级必须向后兼容**。已有 API、数据库表、工具契约、前端桥在未迁移前不得破坏。
10. **所有状态变更必须发布事件**。无事件则视为违规耦合。
11. **禁止无 TTL 缓存**。任何缓存必须带过期时间。
12. **禁止静默捕获异常**。所有异常必须记录、分类、处理。
13. **禁止在日志中输出密钥与 PII**。
14. **禁止 Tool/Workflow/Skill 自行提升权限**。
15. **禁止把用户数据作为训练数据上传云端**。
16. **Personality 不得写死为固定 Prompt**。
17. **Memory 不得全部塞进 Prompt**。
18. **所有外部调用必须设超时**。
19. **所有高副作用操作必须可审计、可回滚、可取消**。
20. **本地数据所有权永远属于用户**。

---

## 附录 A：规范与 v1/v2 设计文档的关系

- 《Xiao6 v2 架构升级设计文档》是**实施计划**（What / When / How / Risk / Rollback）。
- 本文档是**最高规范**（Must / Must Not / Always / Never）。
- 实施计划中的具体步骤不得违反本规范；若冲突，以本规范为准。

---

## 附录 B：术语表

| 术语 | 定义 |
|---|---|
| Turn | 一次用户请求到 Agent 回复的完整回合 |
| Plan | Planner 产出的有序 Step 集合 |
| Step | Plan 中的最小执行单元 |
| Episode | 压缩后的会话/事件记忆 |
| Skill | Prompt + Workflow + Memory + Goal + Tools 的组合包 |
| Context Budget | Prompt 允许的最大 Token 预算 |
| ReflectionResult | Reflection 模块输出的复盘结果 DTO |
| DTO | Data Transfer Object，模块间传递数据的强类型对象 |

---

> 本规范自发布之日起生效。所有后续代码评审、架构讨论、Skill 审核均以本规范为准。
