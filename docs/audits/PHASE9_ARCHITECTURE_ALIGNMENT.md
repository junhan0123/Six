# Phase 9 — Cognitive Orchestration Layer

## Step 0 · Architecture Alignment Report（只读分析）

> 本报告仅基于真实重读 8 个冻结文件得出，未编写任何代码、未创建模块、未修改既有文件。
> 目标：确认 Phase 9 各模块与已冻结架构的集成点、事件契约边界、红线合规，为 Step 1（Design）提供对齐基线。

---

### 0. 重读确认（冻结代码基线）

| 文件 | 关键事实（重读确认） |
|---|---|
| `agent_runtime.py` | 唯一编排运行时。状态机 `IDLE→PLANNING→EXECUTING→REFLECTING`。`_run_goal` 在 REFLECTING 阶段发射 `REFLECTING` 并调用 `reflect(goal_id, executions)`（L185-186）。电脑能力经 `capability_registry.is_known` → `_execute_computer_task` → `permission_guard` 闭环（L212-216、252-308），Agent/Runtime 不构造 ComputerAction、不直调 executor。 |
| `memory.py` | 唯一记忆系统。`build_memory_block()`（L237）汇总画像+长期摘要+近期对话+学习经验；`build_context_prefix()`（L266）汇总时间/待办/焦点/任务/地理/热点/预取作为 system prompt 注入。`record_learning`/`get_learnings` 持久化学习经验。无第二记忆系统。 |
| `eventbus.py` | `DOMAIN_EVENT_NAMES` = **71**，`SYSTEM_EVENT_NAMES` = **8**。`publish_domain(name,payload)` 对 `name not in DOMAIN_EVENT_NAMES` 抛 `ValueError`（L234-235）；`publish_system` 同理校验（L269-270）。信封：`{"xiao6_event":name,"payload":payload,"ts":...}`。 |
| `app-state.js` | 唯一状态写入口 `applyEvent(name,payload)`（L701）：非合约事件静默忽略；有 reducer 则改状态，并 `emit(name)` + `emit('*')`。`state.workspace = {currentId:null}`（L24）已预留。`state.knowledge` 已存在（L21，由 `MEMORY_STORED`/`MEMORY_LINKED` 写入）。 |
| `computer-state.js` | 纯投影层（非视觉），订阅 `AppState('*')`，`getComputer()` 单向派生（L34-39），无写入口。 |
| `perception-state.js` | 纯投影层，订阅 `AppState('*')`，处理 5 个 `PERCEPTION_*` 事件（L30-84），无写入口、不写 AppState。 |
| `policy_engine.py` | 唯一权限来源。`evaluate/request_approval/resolve` 四级授权（auto/confirm/session/never）。`tool_permission` 复用 `tools.READONLY_TOOLS`（LOW→auto），其余默认 confirm。无第二权限系统。 |
| `capability_registry.py` | 唯一能力目录 `_CAPABILITIES`（声明式元数据，无 OS 调用）。`RISK_TIER` 把风险映射到 PolicyEngine 词汇（LOW→AUTO, MEDIUM→CONFIRM）。`risk_of`/`tier_of`/`is_known` 供 AgentRuntime 路由。 |

---

### 1. 当前架构地图（已冻结层）

```
                ┌─────────────────────────────────────────────┐
                │  EventBus（单一脊柱）                        │
                │  DOMAIN 71 + SYSTEM 8 · publish_domain/      │
                │  publish_system 双通道单一来源                │
                └──────────────┬──────────────────┬───────────┘
                               │ publish_domain    │ publish_system
                               ▼                   ▼
                  ┌────────────────────┐   ┌──────────────────────┐
                  │ AppState（唯一写入口）│   │ 独立 SSE 监听器        │
                  │ reducers → state    │   │ app.js/glance-card.js │
                  └─────────┬──────────┘   └──────────────────────┘
            subscribe('*')  │ 单向投影
        ┌──────────────────┼───────────────────────┐
        ▼                  ▼                       ▼
  ComputerState      PerceptionState        （未来 CognitiveState，纯投影）
  （纯投影）          （纯投影）

  后端生产者（均不持有 Goal 编排权）：
   - PerceptionRuntime  →  PERCEPTION_*（观察层，Vision 绝不控制）
   - Computer Operating Layer（PermissionGuard/Executor/Verification）→ COMPUTER_*

  唯一编排运行时：
   - AgentRuntime（IDLE→PLANNING→EXECUTING→REFLECTING）
        └ 消费 PolicyEngine（唯一权限）/ CapabilityRegistry（唯一目录）/ tools.TOOL_FUNCS（唯一工具执行器）
        └ 反思阶段：reflect() 已由 reflector 落 MEMORY_CREATED 等
```

---

### 2. Phase 9 模块 ↔ 冻结层集成点

| Phase 9 模块 | 类型 | 集成点（复用，不新建） | 纪律边界 |
|---|---|---|---|
| **Workspace Manager** | 新模块（状态管理） | 持 `Workspace{id,name,rootPath,projectType,relatedFiles,activeTasks,memoryLinks,computerContext}`；经 `publish_domain(WORKSPACE_CREATED/UPDATED)` 通知。可持久化到 DB（新表或 `meta`）。 | **只管理状态，绝不直接读/写文件系统**（不做文件索引器）。`state.workspace` 已有 `currentId`，新事件可扩展该子树。 |
| **Context Engine** | 新模块（汇编，不推理） | 输入 = `goals.get_goal` + `memory.build_memory_block` + `WorkspaceManager` + `ComputerState.getWorld()`/`COMPUTER_WORLD_SYNC` + `PerceptionRuntime.observe()`（Phase 8 已提供只读快照）。输出 `ContextPackage{identity,goal,environment,knowledge,memory,available_capabilities,constraints}`。 | **只汇编、不规划、不决策**（类比 Vision "observe only" → Context "assemble only"）。产物供 AgentRuntime 消费，不自行执行。 |
| **Capability Registry Upgrade** | 升级既有 `capability_registry.py` | 在 `_CAPABILITIES` 增加 `type`(computer/knowledge/memory/automation/analysis) + `provider` + `description` 字段；新非电脑能力（knowledge/memory/analysis/automation）声明为 `LOW` 风险 → 复用 `RISK_TIER`→AUTO。 | **不新建第二 Tool 系统**。`tools.TOOL_FUNCS` 仍是唯一执行器；capability 仅元数据。继续复用 PolicyEngine。 |
| **Knowledge Workspace** | 接口（Step 5 仅接口） | 复用既有 `state.knowledge`（`MEMORY_STORED`/`MEMORY_LINKED` 已建）/ `knowledge.py`。接口：`link(document↔project↔memory)`。 | **不实现完整 RAG**（第一阶段只接口）。**不新增 `KNOWLEDGE_LINKED` 事件**（已被 `MEMORY_LINKED` 覆盖）。 |
| **Context Reflection** | 接入 AgentRuntime（Step 6） | 在现有 REFLECTING 阶段（`reflect()` 之后）消费最新 `ContextPackage`，发射 `CONTEXT_UPDATED`。可顺带更新 `workspace.activeTasks`/`memoryLinks`。 | **不成第二 Runtime**；**不自动执行**（只发状态更新事件）。 |

**前端投影（可选，非 Step 0/1 必需）**：若 UI 需展示 Workspace/Context，新增 `cognitive-state.js` 作为纯投影层（与 `computer-state.js`/`perception-state.js` 同构，订阅 `AppState('*')`，无写入口）。ContextPackage 全量不进 AppState（性能），仅经 `CONTEXT_BUILT/UPDATED` 发轻量元数据（contextId/goalId/builtAt/capabilityCount/focus）。

---

### 3. 事件契约分析（含 KNOWLEDGE_LINKED 冲突）

**当前**：DOMAIN=71，SYSTEM=8。

**你提出的 6 个新事件逐项核对**：

| 提议事件 | 判定 | 说明 |
|---|---|---|
| `WORKSPACE_CREATED` | ✅ 新增 DOMAIN | 与已冻结的 `WORKSPACE_SWITCHED`（reserved，意为"切换活跃工作区"）**命名不同、语义不同、互不冲突**。 |
| `WORKSPACE_UPDATED` | ✅ 新增 DOMAIN | 同上，生命周期更新事件。 |
| `CONTEXT_BUILT` | ✅ 新增 DOMAIN | 上下文包构建完成信号（轻量元数据）。 |
| `CONTEXT_UPDATED` | ✅ 新增 DOMAIN | 反思后上下文更新信号。 |
| `CAPABILITY_DISCOVERED` | ✅ 新增 DOMAIN | 能力目录发现新能力信号；与 `capability_registry.py` 模块名不同，互不冲突。 |
| `KNOWLEDGE_LINKED` | ❌ **拒绝 / 合并** | **已存在等价的 `MEMORY_LINKED`**（zz-events.js:119 注释明确"MEMORY_LINKED 取代预留的 KNOWLEDGE_LINKED，单一来源，禁第二套事件"；app-state.js 有 `MEMORY_LINKED` reducer）。新增 `KNOWLEDGE_LINKED` 违反单一来源纪律。知识关联直接复用 `MEMORY_LINKED`。 |

**净新增**：**5 个 DOMAIN**（76 总数），SYSTEM 不变（8）。≤10 预算，**合规**。

**落地纪律（沿用 Phase 6/7/8）**：
- `eventbus.py` `DOMAIN_EVENT_NAMES` 末尾加 5 名（71→76）。
- `zz-events.js` `EVENTS` 加同 5 名（71→76）+ 新增 `BATCH_9` 聚合 + 加入 `API`。
- `tests/` 中硬编码 `71` 断言维护为 `76`（沿用 Phase 8 的 `_fix_counts` 模式）；`phase6-order1.backend.expected` 集合补 5 名。
- `CONTEXT_BUILT/UPDATED` 若需前端 `reducer` 则加（写轻量 `state.context` 子树）；否则按 `perception` 模式纯投影。

---

### 4. 红线 / 边界校验（对照你的禁止清单）

| 红线 | 校验结论 |
|---|---|
| 不引入 LangChain / AnythingLLM 代码 | ✅ Phase 9 仅借鉴"Tool Registry / Chain 思想 / Workspace 概念"，全部用既有模块表达，不 import 任何外部框架。 |
| 不修改 Agent Runtime 核心流程 | ✅ Context Engine / Reflection 均为**生产者/消费者**，不改动 `AgentRuntime` 状态机；Reflection 仅挂在既有 REFLECTING 阶段之后。 |
| 不修改 Galaxy 视觉系统 / Overlay | ✅ 纯后端认知层 + 可选纯投影前端；不触碰 Three.js/Overlay。 |
| 不新增第二 Memory 系统 | ✅ 复用 `memory.py`（profile/memory_summary/learnings/reminders）。 |
| 不新增第二 Tool 系统 | ✅ 升级既有 `capability_registry.py`，`tools.TOOL_FUNCS` 仍是唯一执行器。 |
| 自动执行未知任务 | ✅ Context Engine "assemble only"；Reflection "emit only"，均无执行权。 |
| 自主学习 | ✅ 不开启 `FEATURE_SELF_LEARNING` 任一新路径；仅复用既有 `memory.py` 蒸馏（被门控）。 |
| Policy Engine 唯一权限来源 | ✅ 新能力风险映射复用 `RISK_TIER`→PolicyEngine；无新权限判定。 |
| AppState 唯一写入口 | ✅ 新事件经 `publish_domain`→`applyEvent`；投影层纯订阅。 |

**Runtime 数据流（验收目标对齐）**：
```
User Intent → Goal → Context Engine(汇编) → AgentRuntime → Capability → Execution → Reflection(发 CONTEXT_UPDATED)
```
全部经 EventBus 单一脊柱，无旁路。

---

### 5. 风险与建议

1. **【高】`KNOWLEDGE_LINKED` 命名冲突**——必须删除该提议，知识关联复用 `MEMORY_LINKED`。否则破坏单一来源纪律与既有 reducer。
2. **【中】`CONTEXT_BUILT/UPDATED` 载荷体积**——ContextPackage 含 memory/perception 全量，禁止整包进 SSE/AppState。只发轻量元数据；全量留后端供 AgentRuntime 同步调用。
3. **【中】Workspace Manager 范围蔓延**——"只管理状态"意味着它持有 `rootPath`/`relatedFiles` 等**引用**，绝不做文件系统扫描/索引。否则越界成"第二文件系统"。
4. **【低】事件计数维护**——与 Phase 8 一致，新增 5 名需同步 `tests/` 的 `71→76` 硬断言与 `phase6-order1.backend` 的 `expected` 集合，避免回归。
5. **【低】Context Engine 不得退化成 Planner**——明确其职责边界：聚合输入 → 产出 ContextPackage，**不推理/不规划/不派发工具**。决策仍由 AgentRuntime + PolicyEngine 负责。

---

### 6. Step 1 就绪结论

- ✅ 8 个冻结文件已真实重读，状态与你的冻结描述一致（Phase 6/7/8 链路完整，事件 71+8）。
- ✅ Phase 9 五大模块均能在**不破坏任何红线**的前提下接入：Workspace Manager / Context Engine / Capability Upgrade / Knowledge Interface / Reflection Loop 全部复用既有 EventBus、AppState、PolicyEngine、CapabilityRegistry、Memory、AgentRuntime。
- ✅ 事件增量收敛为 **5 个 DOMAIN（76 总数）**，SYSTEM 不变；`KNOWLEDGE_LINKED` 已识别为冲突并建议合并入 `MEMORY_LINKED`。
- ✅ 无第二 Runtime / Memory / Tool / Permission 系统；Agent Runtime 核心流程不被修改。

**建议 Step 1（Design）交付物**：`Cognitive Context Architecture v1.0`，含：模块关系图、数据流（Intent→Goal→Context→Agent→Capability→Execution→Reflection）、事件模型（5 新增事件信封 schema）、边界清单、风险登记。

> 本报告为只读分析产出，未修改任何既有文件、未创建代码模块。等待 Step 1 批准。
