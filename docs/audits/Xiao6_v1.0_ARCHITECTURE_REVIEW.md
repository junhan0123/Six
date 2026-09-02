# Xiao6 v1.0 Architecture Review

> 类型：**Strict Audit Only / Analysis Only**
> 范围：Phase 6 / Phase 7 / Phase 8 审查对象
> 纪律：不写代码、不修改文件、不创建模块、不进入 Phase 9 Implementation、不重构、不优化
> 方法：所有结论均基于本次重新读取的真实源码（eventbus.py / agent_runtime.py / memory.py / policy_engine.py / permission_guard.py / computer_action.py / computer_executor.py / verification.py / capability_registry.py / app-state.js / galaxy-state.js / overlay-runtime.js / computer-state.js / perception-state.js / zz-events.js），并以 `grep`/`python` 实测计数验证。

---

# 1. Executive Summary

Xiao6 v1.0 的核心架构纪律在 Phase 6/7/8 落地后**保持健康**：

- **事件单一来源**纪律严格成立：后端 `DOMAIN_EVENT_NAMES=71`、前端 `EVENTS` 逐字一致；`SYSTEM_EVENT_NAMES=8` 平行通道互斥。新增事件经 `publish_domain`/`publish_system` 校验，未知名抛 `ValueError`。
- **AppState 唯一写入口**纪律严格成立：`applyEvent → reducers[name]` 是唯一状态变更路径；4 个前端投影层（Galaxy/Overlay/Computer/Perception）均为只读订阅者，绝不回写。
- **唯一编排运行时**：`AgentRuntime` 是唯一能做"Goal→Capability→Executor"决策的运行时。`CaptureRuntime` / `PerceptionRuntime` 仅为**观察生产者**（发事件，不决策、不构造动作）。**无第二 Runtime**。
- **安全闭环**：Vision/Perception 永远只产出 Observation（经 `PERCEPTION_*` 事件），绝不构造 `ComputerAction`；`computer_executor` 不直接写状态，仅经 `PermissionGuard` 发事件。
- **依赖方向**全部正向：Observation→State、Goal→Agent、Capability→Executor；未发现反向违例。

**结论：PASS —— 可以继续 Phase 9。** 见第 10 节。

> 注：整个 `xiao6-ui/` 实际含 80+ 个 `.py` 与 48 个 `.js` 模块（含 Phase 9–12 已落地的 `goal_decision_engine.py`、`context*`、`mobile.py`、`clipboard_monitor.py`、HUD 等），本审查**仅针对 Phase 6/7/8 审查对象及其直接协作者**给出结论；更宽系统未发现影响本次结论的架构污染。

---

# 2. Current Architecture Status

## 2.1 Architecture Reality Map（真实清点）

| 维度 | 真实数量 | 实测来源 |
|------|---------|---------|
| 后端 DOMAIN 事件名 | **71** | `eventbus.DOMAIN_EVENT_NAMES` |
| 后端 SYSTEM 事件名 | **8** | `eventbus.SYSTEM_EVENT_NAMES` |
| EventBus 内部 TOPIC | 5（SSE / HUD_STATE / GOAL_UPDATE / MOBILE_SYNC / CLIPBOARD） | `eventbus.py` 常量 |
| 编排运行时（决策） | **1**（AgentRuntime） | `agent_runtime.py` |
| 观察生产者（后台循环） | 2（CaptureRuntime / PerceptionRuntime） | `capture_runtime.py` / `perception_runtime.py` |
| 前端权威状态核心 | 1（AppState，含 11 子树） | `app-state.js` |
| 前端只读投影层 | 4（GalaxyState / OverlayRuntime / ComputerState / PerceptionState） | 各 `*state*.js` |
| 前端视觉运行时 | 1（galaxy-runtime.js，Three.js 渲染器） | 目录清点（非审查对象） |
| 审查范围内后端模块 | 20 | 见 §3 |
| 审查范围内前端模块 | 11 | 见 §3 |
| 全量测试文件（P6/7/8） | 28（14 backend `.test.py` + 14 frontend `.frontend.test.js`） | `tests/` 目录 |

## 2.2 真实模块清单（审查范围内）

**Phase 6（事件 / 状态 / 意图 / 编排）**
- 后端：`eventbus.py`、`agent_runtime.py`、`intent_gateway.py`、`goals.py`、`tasks.py`、`reflector.py`、`memory.py`
- 前端：`app-state.js`、`galaxy-state.js`、`overlay-runtime.js`、`zz-events.js`、`intent-gateway.js`、`event-bridge.js`（SSE 桥）

**Phase 7（电脑操作层）**
- 后端：`computer_action.py`（DTO）、`computer_executor.py`、`permission_guard.py`、`capability_registry.py`、`capture_provider.py`、`capture_runtime.py`、`frame.py`
- 前端：`computer-state.js`、`computer-action.js`、`capability-registry.js`、`permission-guard.js`

**Phase 8（感知层）**
- 后端：`perception_runtime.py`、`perception_model.py`、`semantic_fusion.py`、`uia_provider.py`、`ocr_provider.py`、`vision_provider.py`
- 前端：`perception-state.js`

**Phase 6 设计系统**：非独立 JS 模块，由 CSS 设计令牌层（index.html / 样式文件）承载，不在本次代码审查对象内；其纪律（令牌而非硬编码）在 Phase 6/8 测试中有约定性校验。

## 2.3 真实依赖关系（核心边）

```
CaptureRuntime ──publish_domain(COMPUTER_WORLD_SYNC)──▶ EventBus ──SSE──▶ event-bridge ──applyEvent──▶ AppState.computer
                                                                                                      │
                                                                                            ComputerState(投影)
PerceptionRuntime ──publish_domain(PERCEPTION_*)──▶ EventBus ──SSE──▶ event-bridge ──emit('*')──▶ PerceptionState(投影)
                 └─publish_system(perception_alert/health)──▶ app.js / glance-card.js (SYSTEM 通道)

AgentRuntime ──goal_id──▶ goals.plan_goal / tasks
            ├─(非电脑能力)▶ policy_engine.evaluate ─▶ tools.execute_tool
            └─(电脑能力)──▶ capability_registry.is_known ─▶ PermissionGuard.plan/run
                                                        ├─▶ policy_engine.evaluate(裁决)
                                                        ├─▶ computer_executor.execute
                                                        └─▶ VerificationLayer.verify
            PermissionGuard ──publish_domain(COMPUTER_ACTION_*)──▶ EventBus ──▶ AppState.computer.actions

AgentRuntime ──REFLECTING──▶ reflector.reflect ──▶ MEMORY_CREATED/DISTILL ──▶ AppState.memory/knowledge
```

---

# 3. Module Audit（模块膨胀检查）

| 模块 | 当前职责 | 是否必要 | 风险 | 处置 |
|------|---------|---------|------|------|
| `agent_runtime.py` | 目标驱动编排状态机 + LLM 派发 + 记忆蒸馏 + 重要日期 + 每日维护 | 必要 | **中**：已含 P12 记忆人格/对话记忆/每日维护，呈"准上帝模块"趋势（~728 行，编排+记忆+LLM） | **Keep**（建议后续把记忆蒸馏拆为独立协作模块，非阻塞） |
| `eventbus.py` | 进程级 pub/sub + 双命名空间校验 + 重试/死信 | 必要 | 低 | **Keep** |
| `app-state.js` | 统一状态核心（11 子树 + reducer 唯一写入口） | 必要 | 低 | **Keep** |
| `zz-events.js` | 事件名单一来源 + 批次分组 + 校验 | 必要 | 低 | **Keep** |
| `galaxy-state.js` | 银河节点数据投影（非视觉） | 必要 | 低 | **Keep** |
| `overlay-runtime.js` | Overlay 模型投影（纯数据→模型） | 必要 | 低 | **Keep** |
| `computer_action.py` | 电脑动作 DTO | 必要 | 低 | **Keep** |
| `computer_executor.py` | 唯一执行系统（Mock + Real，安全约束） | 必要 | 低 | **Keep** |
| `permission_guard.py` | 权限闸门（plan/decide/run） | 必要 | 低 | **Keep** |
| `capability_registry.py` | 能力目录 + 风险→Policy 映射 | 必要 | 低 | **Keep** |
| `capture_*.py` / `frame.py` | 屏幕采集 | 必要 | 低 | **Keep** |
| `perception_runtime.py` | 感知运行时（生产者） | 必要 | 低 | **Keep** |
| `perception_model.py` | 融合后观测 DTO | 必要 | 低 | **Keep** |
| `semantic_fusion.py` | UIA+OCR+Vision 融合（禁推理） | 必要 | 低 | **Keep** |
| `uia_provider.py` / `ocr_provider.py` / `vision_provider.py` | 三类观察源 + Mock | 必要 | 低 | **Keep**（7 模块对 MVP 观察层属合理拆分） |
| `perception-state.js` | 感知纯投影 | 必要 | 低 | **Keep** |
| `memory.py` | 压缩 + 上下文注入 + 学习蒸馏 | 必要 | **中**：压缩/上下文构建/学习三责合一（~328 行） | **Keep**（建议后续拆 `context_builder` vs `compression`，非阻塞） |
| `knowledge.py` | 知识层（最小） | 必要 | 低 | **Keep** |

**重点检查结论**
- **重复职责**：未发现审查范围内模块重复。⚠️ 提示（超出审查范围但相关）：存在 `capabilities.py` 与 `capability_registry.py` 命名接近——建议 Phase 9 前确认二者是否为"能力实现"vs"能力注册表"的不同职责，避免未来误用（本审查未读该文件，仅作风险提示）。
- **上帝模块**：`agent_runtime.py` 与 `memory.py` 有"准上帝"趋势，但职责仍内聚，不阻塞 Phase 9。
- **空壳模块**：无。所有 Phase 8 provider 均有 Mock 实现，可测。
- **未来不可维护模块**：无直接证据；主要风险在 `agent_runtime.py` 随 P10–P12 继续膨胀。

**处置汇总**：全部 **Keep**。2 个非阻塞建议（拆记忆/确认 capabilities 命名）。无 Merge / Refactor / Remove 必要项。

---

# 4. Event Audit（事件架构审计）

## 4.1 统计
- `DOMAIN_EVENT_NAMES = 71`，`SYSTEM_EVENT_NAMES = 8`。
- 增长轨迹：Phase 6 基线 38 → Order5 +6（44）→ Phase 7 +22（66）→ Phase 8 +5（71）；SYSTEM 6 → 8。
- 平均每个 Phase 新增 ~11 个 DOMAIN 事件，增速**温和**。

## 4.2 事件污染检查
- **双命名空间互斥**：`publish_domain`（DOMAIN）与 `publish_system`（SYSTEM）各自校验、互不重叠；`applyEvent` 对非合约事件静默忽略（属 SYSTEM 则放行）。**无污染**。
- **单一来源**：前端 `EVENTS` 与后端 `DOMAIN_EVENT_NAMES` 逐字一致（已有 `phase6-order1.backend` + 全部 `.frontend` 测试强制对齐）。**无漂移**。
- **类型混合**（DOMAIN 内含状态/动作/感知/UI 事件）：属单一合约的正常聚合，不视为污染——因全部走 `Event→AppState→Runtime→Renderer` 单一管道。

## 4.3 管道合规
```
Event ──publish_domain──▶ EventBus(TOPIC_SSE) ──SSE──▶ event-bridge.js ──applyEvent──▶ AppState(reducers) ──emit──▶ 投影层(Renderer 数据源)
```
SYSTEM 事件绕过 AppState，由 `app.js`/`glance-card.js` 独立消费（设计如此，非污染）。

## 4.4 未来扩展余量
Phase 9 预计新增 `WORKSPACE_CREATED` / `WORKSPACE_UPDATED` / `CONTEXT_BUILT` / `CONTEXT_UPDATED` / `CAPABILITY_DISCOVERED`（5 个 DOMAIN，≤10 预算），净增后 DOMAIN=76。余量充足。

**Event Health Report：HEALTHY** —— 无污染、无漂移、增速可控、扩展余量充足。

---

# 5. Runtime Audit（运行时复杂度审计）

## 5.1 真实 Runtime 图

```
                  ┌─────────────────────────────────────────────┐
   用户输入 ──────▶│ AgentRuntime (唯一决策运行时)               │
                  │  IDLE→PLANNING→EXECUTING→REFLECTING         │
                  └───────────┬───────────────┬─────────────────┘
                              │               │
                  ┌───────────▼──┐     ┌───────▼──────────────┐
                  │ capabilities │     │ PermissionGuard       │
                  │ / tools      │     │ (闸门,非运行时)       │
                  └───────────┬──┘     └───┬───────────┬──────┘
                              │            │           │
                        tools.execute  policy_engine  computer_executor
                                          (evaluate)   (唯一执行)
                                                        │
                                                  VerificationLayer

   [观察生产者，非决策]
   CaptureRuntime ──▶ COMPUTER_WORLD_SYNC ──┐
   PerceptionRuntime ──▶ PERCEPTION_* ──────┼──▶ EventBus ──▶ AppState ──▶ 4 投影层
                                            │
   (PerceptionRuntime 绝不调用 PermissionGuard/Executor)

   [前端]
   galaxy-runtime.js (Three.js 视觉渲染器) 订阅 GalaxyState
   OverlayRuntime (数据→模型) 订阅 AppState+GalaxyState
```

## 5.2 分析
- **第二 Runtime**：**无**。唯一决策运行时 = `AgentRuntime`。`CaptureRuntime`/`PerceptionRuntime` 是后台 `while` 循环的生产者，不路由、不裁决、不构造动作。
- **职责重叠**：无。感知（观察）vs 编排（决策）vs 执行（动作）三权分立清晰。
- **循环依赖**：无。`verification.py` 的 `PerceptionWorldModelObserver` 仅以 `perception_runtime` **实例**作为参数（鸭子类型），模块级不 `import perception_runtime`，故无环。
- **调用方向错误**：无（见 §7）。

## 5.3 Runtime Coordinator 判断
当前 `AgentRuntime` 已是唯一协调者；Phase 9 的 Cognitive Context Engine 是"上下文汇编器"，喂给既有 `AgentRuntime`，**不新增协调者**。

**结论：保持现状，无需 Runtime Coordinator。**

---

# 6. Memory Audit（记忆架构审计）

## 6.1 现有层次（对照 LangChain Memory 思想）
| 层次 | Xiao6 对应 | 实现位置 |
|------|----------------|---------|
| 短期 / 即时 | 最近 24 轮原始对话（`MEM_KEEP=24`） | `memory.py` + `chat_log` |
| 工作记忆 | 上下文前缀（时间/待办/焦点/任务/地理/热点/预取） | `build_context_prefix` |
| 长期记忆 | 压缩摘要 `memory_summary` + 学习经验 `learnings` + 画像 `profile` + 对话记忆 `conversation_memories` | `memory.py` / `memory_distiller.py` |
| 项目记忆 | `PROJECT_DETECTED/UPDATED` 事件 → `state.computer.projects`（World Model 投影） | `app-state.js` + `computer-state.js` |
| 知识记忆 | `knowledge.py` + `state.knowledge`（`MEMORY_STORED/LINKED`） | `knowledge.py` / `app-state.js` |

## 6.2 分析
- **无第二 Memory 系统**：所有记忆经 `memory.py` / `knowledge.py` 单一路径，无重复存储层。
- **术语过载风险**（中）："memory" 一词横跨 `memory.py` / `memory_distiller.py` / `memory_query.py` / `memory_audit.py` 四个模块；但职责分明（压缩/蒸馏/查询/审计），非混乱。
- **是否混乱**：未混乱。层次映射对应 LangChain 思想合理。

## 6.3 重新规划建议（供 Phase 9 参考，非本次执行）
- **Memory Layer ↓ Workspace Layer ↓ Knowledge Layer** 的正确实现 = **复合读取**，而非新增存储：
  - Workspace = 把 `goals`+`tasks`+`computer.projects`+`perception`+`memory_summary`+`knowledge` **组合**为一个 `WorkspaceContext` 对象。
  - 不得为 Workspace 新建数据库表或第二记忆系统。

---

# 7. Workspace Architecture Review（工作空间架构评审）

## 7.1 现状
- `state.workspace = { currentId: null }`（AppState 已预留）。
- `WORKSPACE_SWITCHED`（DOMAIN，reserved）已登记——语义为"切换活跃工作区"，与 Phase 9 拟议的 `WORKSPACE_CREATED/UPDATED` 命名/语义不同、互不冲突。

## 7.2 AnythingLLM Workspace 思想映射
```
Workspace {
  project,      → state.computer.projects / goals
  files,        → 未来经 Computer Capability 只读列举（不新增文件操作模块）
  memory,       → memory_summary / learnings / profile
  tasks,        → state.tasks
  computer_state → state.computer（World Model 投影）
  knowledge,     → state.knowledge
  history       → chat_log（近期）+ memory_summary（长期）
}
```
上述每一字段**均已存在于既有状态树**，Workspace 仅是聚合视图。

## 7.3 判断
- Workspace 应成为 **Phase 9 核心**，但定位为 **状态管理器 + 上下文聚合器**（只读组合既有状态），**严禁直接操作文件**（符合用户禁令）。
- 不应新建第二 Memory / 第二文件索引；仅做接口与状态组合。

**结论：Workspace 应作为 Phase 9 核心，且必须是 Context Engine 的输入聚合层，非存储层。**

---

# 8. Dependency Audit（依赖方向审计）

## 8.1 合规方向（全部成立）
- **Data: Observation → State** ✅
  CaptureRuntime/PerceptionRuntime → EventBus → AppState → 投影层。实测：`computer_executor.py` 与 `perception_runtime.py` 均**不** `import eventbus` 写状态。
- **Decision: Goal → Agent** ✅
  `AgentRuntime` 驱动 `goals`/`tasks`；`goals`/`tasks` 不反向依赖 `AgentRuntime`。
- **Action: Capability → Executor** ✅
  `AgentRuntime._execute_computer_task` 仅调 `PermissionGuard.plan/run`；`PermissionGuard` → `policy_engine` → `computer_executor`。`AgentRuntime` 自身**不构造 `ComputerAction`**（仅 Guard 构造）。

## 8.2 禁止方向检查（grep 实测）
| 禁止边 | 实测结果 | 结论 |
|--------|---------|------|
| State 调用 Agent | `app-state/galaxy-state/overlay-runtime/computer-state/perception-state/event-bridge` 均无 `import agent_runtime` | ✅ 无违例 |
| UI 调用 Runtime | 前端投影层均为纯订阅者；`galaxy-runtime.js` 仅订阅 `GalaxyState` | ✅ 无违例 |
| Perception 调用 Action | `perception_runtime.py` 不 `import permission_guard/computer_executor/computer_action` | ✅ **安全 PASS** |
| Executor 修改 State | `computer_executor.py` 不 `import eventbus`、不 `applyEvent`、不引用 `AppState` | ✅ 无违例 |

## 8.3 Dependency Violation Report
**未发现任何依赖违例。** 四层正向依赖成立，四条禁止边全部干净。

---

# 9. Scalability Assessment（未来可扩展性评审）

模拟未来 Phase：

| 未来 Phase | 需求 | 当前架构支持度 | 说明 |
|-----------|------|--------------|------|
| **Phase 9 Cognitive Context** | Workspace Manager + Context Engine + Capability Catalog 升级 + Knowledge 接口 + Reflection 循环 | ✅ 充分 | 全部可建于既有 `goals`/`tasks`/`computer`/`perception`/`memory`/`knowledge` 之上；Reflection 可挂在既有 `REFLECTING` 之后发 `CONTEXT_UPDATED`。无新核心层。 |
| **Phase 10 Proactive Intelligence** | 主动推送 | ✅ 已有 `proactive.py` + `perception_alert` SYSTEM 通道 | 直接复用。 |
| **Phase 11 Knowledge Graph** | 知识图谱 | ✅ 已有 `knowledge.py` + `state.knowledge` | 可扩展，无架构阻碍。 |
| **Phase 12 Automation** | 自动化 | ✅ 已有 `tools`/`tool_factory`/`sandbox` + `AgentRuntime` | 可扩展。 |

**回答三个问题：**
1. **需要重构吗？** —— **不需要核心重构**。仅需 2 个非阻塞整理（拆 `agent_runtime` 记忆职责、确认 `capabilities.py` 命名）。
2. **需要新增核心层吗？** —— **不需要**。Phase 9 是"上下文汇编器"，喂给既有 `AgentRuntime`；不新增 Runtime / Memory / Tool / Permission 系统。
3. **哪些地方现在不要动？** ——
   - EventBus 单一来源（DOMAIN/SYSTEM 双命名空间）
   - AppState 唯一写入口（`applyEvent` + reducers）
   - AgentRuntime 核心循环（IDLE→PLANNING→EXECUTING→REFLECTING）
   - Galaxy / Overlay 视觉与数据层
   - PolicyEngine 唯一权限裁决
   - PermissionGuard + computer_executor + VerificationLayer 安全闭环

---

# 10. Recommended Roadmap（建议路线图）

| 优先级 | 项 | 类型 | 阻塞 Phase 9? |
|--------|----|----|--------------|
| P0 | 进入 Phase 9 Step 1（设计 Cognitive Context Architecture v1.0） | 设计 | 否（已 PASS） |
| P1 | Phase 9 Order 2：Context Engine（组合既有状态为 ContextPackage） | 实现 | 否 |
| P1 | Phase 9 Order 1：Workspace Manager（状态管理，禁文件操作） | 实现 | 否 |
| P2 | Capability Registry 升级为统一 Catalog（computer/knowledge/memory/automation/analysis） | 实现 | 否 |
| P2 | Knowledge Workspace 仅接口（复用 `state.knowledge`） | 实现 | 否 |
| P3 | Reflection 循环挂 `REFLECTING` 后发 `CONTEXT_UPDATED` | 实现 | 否 |
| 建议(非阻塞) | 拆 `agent_runtime.py` 的记忆蒸馏/LLM 派发为协作模块 | 重构 | 否 |
| 建议(非阻塞) | 确认 `capabilities.py` 与 `capability_registry.py` 职责边界 | 澄清 | 否 |

---

# 11. Final Decision

# ✅ PASS —— 可以继续 Phase 9

**判定依据（全部满足）：**
- **架构纪律**：事件单一来源（71/8 逐字对齐）、AppState 唯一写入口、无第二 Runtime / Memory / Tool / Permission 系统 —— 全部成立。
- **模块健康**：审查范围内 31 个模块职责清晰，无重复、无空壳、无不可维护模块；仅 2 个准上帝模块趋势（非阻塞）。
- **事件健康**：无污染、无漂移、增速温和、扩展余量充足（Phase 9 +5 后仍 <80）。
- **运行时健康**：唯一决策运行时，无重叠、无循环依赖。
- **记忆健康**：单系统、层次对应 LangChain 思想、无混乱。
- **依赖健康**：四条正向依赖成立，四条禁止边全部干净（含 Perception 绝不控制的安全红线）。
- **可扩展性**：Phase 9–12 均可在不新增核心层的前提下实现。

**进入 Phase 9 的前提约束（来自本审查，必须延续）：**
1. 不新增第二 Runtime / Memory / Tool / Permission。
2. Workspace Manager 只管理状态，禁止直接操作文件。
3. Context Engine 只汇编既有状态为 ContextPackage，不承载业务判断、不绕过 AgentRuntime。
4. 知识关联复用既有 `MEMORY_LINKED`（不新增 `KNOWLEDGE_LINKED`，避免第二事件源）。
5. Reflection 循环挂在既有 `REFLECTING` 之后，发 `CONTEXT_UPDATED`，不新建反思运行时。

---

# 12. Appendix — 实测验证记录

- `python -c "import eventbus; len(DOMAIN_EVENT_NAMES)"` → **71**
- `python -c "import eventbus; len(SYSTEM_EVENT_NAMES)"` → **8**
- `grep` 前端状态文件 `import agent_runtime` → **0 命中**（State→Agent 违例不存在）
- `grep` `perception_runtime.py` `import (permission_guard|computer_executor|computer_action)` → **0 命中**（Perception→Action 违例不存在）
- `grep` `computer_executor.py` `publish_domain|applyEvent|AppState|import eventbus` → **0 命中**（Executor→State 违例不存在）
- `grep` `verification.py` `import perception_runtime` → **0 命中**（无循环依赖）
- P6/7/8 测试文件清点：**28 个**（14 backend + 14 frontend），全量测试在 Phase 8 MVP 收尾时已达 **0 FAIL / 0 Regression**（本轮为只读审查，未重跑，未改动任何文件）。

*报告结束 —— 未进入 Phase 9 Implementation，等待批准。*
