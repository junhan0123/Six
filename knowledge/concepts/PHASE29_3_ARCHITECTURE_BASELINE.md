---
id: know-phase29-3-architecture-baseline
type: concept
---
# PHASE29_3_ARCHITECTURE_BASELINE

> **Phase 29.3 — Unified Autonomous Work Loop（统一自主工作闭环）**
> 架构侦察基线（规格 §五「第一动作不是写代码」）。
> 本文件在完整读取真实真源后产出，明确：架构 / 已有能力 / 入口 / 结果模型 / 事件 / 执行边界 / 缺失闭环 / 计划新增模块 / 禁止修改模块 / 数据流 / 生命周期 / 红线，并明确回答 15 个侦察问题。
> 所有事实来自真源读取（package.json / core/events/EventBus.js / core/autonomous/*（22 文件）/ core/reasoning/* / core/learning/reasoning-learning/* / core/automation/registry.js / core/execution/index.js / scripts/scan-autonomous-execution.js），未含任何推测。

---

## 0. 元信息

| 项 | 值 | 真源 |
|---|---|---|
| 项目 | PersonalAIOS | /Users/yaowei/WorkBuddy/PersonalAIOS |
| 当前版本 | `0.35.0` | package.json `version` / `kernelVersion` |
| 运行环境 | Node 22.x / macOS / `PAIOS_MODEL=heuristic` / 完全离线 | package.json scripts |
| 测试框架 | 自研零依赖 Harness（`core/test/Harness.js`）+ Node 原生 `node` | 无 Jest/Vitest/Mocha |
| EventBus 权威事件总数 | **471**（动态 `Object.keys(EVENTS).length`） | core/events/EventBus.js |
| test:all 套数 | 46（链尾 `phase29_2_learning_test.js`） | package.json `test:all` |
| 依赖 | 仅 `electron` | package.json `dependencies` |
| core/autonomous 文件数 | **22**（Phase 28.6） | `ls core/autonomous/` + scan-autonomous-execution.js |
| core/autonomous 状态机 | **18 态** | autonomous-state.js `AUTONOMOUS_STATE_LIST` |
| Autonomous* 事件 | **16** | autonomous-state.js `AUTONOMOUS_EVENT_COUNT` |
| core/autonomous-work 是否存在 | **不存在**（故本阶段扩展 `core/autonomous/`，不新建重复目录） | `ls -d core/autonomous-work` → NOT PRESENT |

---

## 1. 架构总览（Architecture）

Phase 29.3 的任务是把**已有能力层**「连接」成统一自主工作闭环，**不重实现任何已有引擎、不新增大量孤立能力**。

已有能力层（全部零执行权、已实现、已验收）：
- **Reasoning（Phase 29.1）** `core/reasoning/` — 通用多轮推理闭环（19 模块 / 14 态 / 7 Reasoning* 事件）。
- **Learning（Phase 29.2）** `core/learning/reasoning-learning/` — 自适应推理学习层（13 模块 / 0 新增事件 / advisory-only）。
- **Automation（Phase 28.4）** `core/automation/` — CapabilityRegistry（research/web/computer/vision/document/data）。
- **Autonomous（Phase 28.6）** `core/autonomous/` — 自主 Agent 闭环骨架（22 文件 / 18 态 / 16 Autonomous* 事件）。
- **Orchestration（Phase 28.5）** / **Execution（Phase 23）** / **Sandbox（Phase 13）** / **Research/Vision/Document/Data/Computer/Web Agent** — 下游执行与能力体。
- **EventBus** `core/events/EventBus.js` — 471 冻结事件。

**关键结论**：Phase 28.6 `core/autonomous/` 已近乎完整覆盖 Phase 29.3 的闭环骨架（AutonomousLoop / 18 态 / 16 事件 / CapabilityRegistry 集成 / Replanner / Recovery / Budget / Observer / Evaluator）。Phase 29.3 的最小新增边界 = 在 `core/autonomous/` 内补齐 **三段集成缺口**（Verification + Reasoning + Learning），**不新建 `core/autonomous-work/` 重复目录**，EventBus 保持 471（16 Autonomous* 事件复用，0 新增）。

---

## 2. 已有能力清单（Existing Capabilities，含入口与零执行权）

| 层 | 模块数 | 入口（构造函数 / 工厂 / 纯函数） | 关键方法 | hasExecutionAuthority |
|---|---|---|---|---|
| Autonomous（28.6） | 22 | `new AutonomousLoop(opts)` / `new AutonomousCapabilitySelector(...)` / `createAutonomousResult(opts)` | `loop.run(goalInput, opts)` / `selector.select(goal, opts)` / `evaluator.evaluate(obs, opts)` | 模块级 + 实例恒 `false`（`verifyAutonomousZeroAuthority` 10 项 invariants） |
| Reasoning（29.1） | 19 | `new ReasoningLoop(opts)` / `understandGoal(goalInput)` / `planFromGoal(goal)` / `createReasoningResult(opts)` | `loop.run(goalInput, opts)` → ReasoningResult | 模块级 + 实例恒 `false`（`verifyReasoningZeroAuthority`） |
| Learning（29.2） | 13（12 源 + index） | `createAdaptiveReasoningLearning(opts)` → `AdaptiveReasoningLearning` | `learnFromOutcome(result, {nowIso, goalContext})` / `recommendForGoal(ctx)` / `injectContext(ctx)` | 模块级 + 实例 + 门面恒 `false`（`verifyReasoningLearningZeroAuthority` 8 项 invariants） |
| Automation/Registry（28.4） | — | `new CapabilityRegistry(seed)` / `createBuiltinCapabilities()` | `register/get/require/has/list/count/validateRequest` | 恒 `false` |
| Execution Pipeline（23） | — | `verifyExecutionPipelineZeroAuthority()` | 授权/审批/请求三层零执行权；sandbox 白名单仅 `orchestrator` | 三层恒 `false` |
| EventBus | — | `new EventBus()` / `EVENTS`（冻结枚举） | `emit/on/bridge` | n/a（事件总线） |

---

## 3. 入口点汇总表（Entry Points）

| 用途 | 入口 | 返回形状 | 真源 |
|---|---|---|---|
| 跑自主闭环 | `new AutonomousLoop({eventBus, registry, policy, budget, selector, planner, observer, evaluator, replanner, recovery, decision, context, memory}).run(goalInput, opts)` | `AutonomousResult`（纯数据） | autonomous-loop.js L46/L98 |
| 理解目标 | `understandGoal(goalInput, {eventBus, source})` → `{goal, understanding}` | `{AutonomousGoal.toJSON(), understanding}` | autonomous-goal.js（循环内 L109） |
| 拆解任务 | `decomposeGoal(goal, {eventBus})` → `{tasks}` | task 数组 | autonomous-task.js（循环内 L118） |
| 选择能力 | `new AutonomousCapabilitySelector({registry, eventBus}).select(goal, {approvalRequired})` → `{selection, steps}` | `{selection:{goalId,capabilities,count,selectedAt}, steps:[{id,capability,action,input,dependsOn,risk,approvalRequired}]}` | autonomous-capability-selector.js L54 |
| 评估一轮 | `new AutonomousEvaluator({eventBus}).evaluate(observations, {goal, budget, replansUsed, awaitingApproval})` | `{outcome, reason, counts, total, canReplan}` | autonomous-evaluator.js L47 |
| 跑推理环 | `new ReasoningLoop({eventBus, registry, policy, budget, provider}).run(goalInput, opts)` → `ReasoningResult` | ReasoningResult（纯数据） | core/reasoning/loop.js L136 |
| 造推理结果 | `createReasoningResult({goalId, objective, intent, status, cycles, finalDecision, intermediateResults, capabilitiesUsed, summary, replansUsed, correctionsUsed})` | ReasoningResult（`isReasoningResult` 校验） | core/reasoning/result.js L32 |
| 学习一次 | `createAdaptiveReasoningLearning({memoryManager, learningEngine, policy}).learnFromOutcome(result, {nowIso, goalContext})` | `LearningReport`（deepFrozen，advisory） | core/learning/reasoning-learning/engine.js L108 |
| 注册能力 | `new CapabilityRegistry().register(CapabilityContract)` / `.get(name)` / `.validateRequest(req)` | 契约 / bool | core/automation/registry.js L34/L43/L67 |
| 验证执行管线 | `verifyExecutionPipelineZeroAuthority()` | `{allZeroAuthority, sandboxAuthorizedCallers:["orchestrator"], singleAuthorizedSubmitter:true}` | core/execution/index.js L135 |

---

## 4. 结果模型（Result Models）

### 4.1 AutonomousResult（Phase 28.6，现有）
`createAutonomousResult({goalId, objective, intent, status, capabilities, steps, artifacts, summary, replansUsed})` →
纯数据：`executionAuthority:false` / `authorityHolder:"execution-sandbox"` / 无任何 `AUTONOMOUS_FORBIDDEN_INJECTION_KEYS` 字段。
`status` 来自 `evaluator.outcome`（success/partial_success/failed/blocked/needs_replan/requires_human）。

### 4.2 ReasoningResult（Phase 29.1，现有）
`createReasoningResult(...)` →
`{id, goalId, objective, intent, status, stopReason, rounds, cycles, finalDecision, intermediateResults, capabilitiesUsed, summary, replansUsed, correctionsUsed, executionAuthority:false, authorityHolder:"execution-sandbox"}`。
`isReasoningResult(v)` 校验（status∈7 态、executionAuthority、authorityHolder、无 banned 字段）。
**Learning 层 `learnFromOutcome` 强制要求合法 `ReasoningResult`**（engine.js L109 `isReasoningResult` 守卫）。

### 4.3 LearningReport（Phase 29.2，现有）
`learnFromOutcome` 返回 deepFrozen：
`{learned, layer, version, goalId, objective, status, features, reasoningPatterns, genericPatterns, strategyScores, confidence:{level, consistency, sampleCount}, contradiction, recommendation, context, memory, historySize, executionAuthority:false, authorityHolder:"execution-sandbox"}`。
`recommendation.isAdvisory===true` / `context.isAdvisory===true`（纯建议，绝不 apply）。

### 4.4 VerificationResult（Phase 29.3，**新增**）
Phase 29.3 新增 `autonomous-verification.js` 产出：
`{executionSuccess, outputValid, goalSatisfied, evidenceSufficient, qualitySufficient, deliveryReady, completed}`。
`completed` 由 `goalSatisfied===true` **硬驱动**（规格 §12），不能只由 `executionSuccess` 驱动。

### 4.5 AutonomousWorkResult（Phase 29.3，**扩展 AutonomousResult**）
在 `autonomous-result.js` 内新增 `createAutonomousWorkResult(...)`（复用 `createAutonomousResult` 并追加工作闭环字段）：
`{...AutonomousResult, goalSatisfied, verification:VerificationResult, learningOutcome:LearningReport|null, session, cycles, delivery}`。
所有追加字段均为纯数据、零执行权、无 forbidden 注入键。

---

## 5. 事件模型（Events）

- 权威总数 = **471**，动态取自 `Object.keys(EVENTS).length`（EventBus.js 冻结枚举，**禁止硬编码旧数量**）。
- Autonomous* 事件 = **16**（已在 EventBus 注册）：`AutonomousGoalCreated / AutonomousGoalUnderstood / AutonomousTaskCreated / AutonomousPlanCreated / AutonomousCapabilitySelected / AutonomousPlanApproved / AutonomousExecutionRequested / AutonomousObservationReceived / AutonomousEvaluationCompleted / AutonomousReplanStarted / AutonomousPlanPatched / AutonomousRecoveryStarted / AutonomousRecoveryCompleted / AutonomousCompleted / AutonomousFailed / AutonomousCancelled`。
- Reasoning* 事件 = **7**（Phase 29.1 新增）。
- **Phase 29.3 红线：0 新增事件**（规格建议优先复用 16 个 Autonomous* 事件）。新增任何 `Autonomous*` 事件名会使 `autoEvents.length` 从 16 变 17，直接击穿 Gate 2（`scan-autonomous-execution.js` / 新 `scan-autonomous-work-execution.js` 的 `EXPECTED_AUTONOMOUS_EVENT_COUNT=16` 与 `EXPECTED_EVENT_BUS_TOTAL=471`）。
- 阶段三新增桥接模块（Verification / ReasoningBridge / LearningBridge）**不引用 `EVENTS`、不 emit 任何事件**（纯函数、零事件依赖），从根上保证 0 新增事件。

---

## 6. 执行边界（Execution Boundary — 零执行权）

- **唯一真实执行链**：`Orchestrator → ExecutionSandbox`（`verifyExecutionPipelineZeroAuthority()` 证明：授权/审批/请求三层 `allZeroAuthority===true`；sandbox 白名单 `AUTHORIZED_CALLERS` 仅 `["orchestrator"]`，`singleAuthorizedSubmitter===true`）。
- **所有能力层零执行权**：Autonomous / Reasoning / Learning / Automation-Registry 的模块级 + 实例 `hasExecutionAuthority()===false`。
- **AutonomousLoop 自身零执行权**：无 `acquireExecutionHandle` / `performExecution`；离线测试经注入 `provider.execute(batch)` 模拟「外部交接」，真实运行时不使用 provider，结论来自真实 Sandbox 回传（autonomous-loop.js L174）。
- **HANDOFF 规则（严格零引用）**：自主层源码（剥离注释与字符串后）不得出现 `submitExecutionRequest` / `orchestrator.` / `executionHandle` / `sandboxHandle` / `new XxxAgent`（scan-autonomous-execution.js `HANDOFF_TOKENS`）。

---

## 7. 缺失闭环缺口（Missing Closure Gaps — Phase 29.3 的最小新增边界）

侦察确认 Phase 28.6 `AutonomousLoop` 已覆盖「理解→拆解→选择→规划→审批→执行请求生成→观察→评估→重规划→恢复→完成」，但有三处缺口，恰是 Phase 29.3 要补的：

- **缺口 1 — Reasoning 未集成**：`AutonomousLoop.run` 直接使用自身 `planner/observer/evaluator/provider`，**未调用 Phase 29.1 `ReasoningLoop`**（autonomous-loop.js 无 `new ReasoningLoop`）。复杂目标缺多轮推理/自主纠错。
- **缺口 2 — Learning 未集成**：`AutonomousLoop` 无 `learnFromOutcome` 调用（无 `createAdaptiveReasoningLearning`）。闭环不从历史推理结果学习，无法把 advisory 反馈喂给下一轮 planning/strategy。
- **缺口 3 — Verification 无 `goal_satisfied` 闸**：`AutonomousEvaluator.evaluate` 仅按 `completed+skipped===total && failed===0` 计数判 `success`（autonomous-evaluator.js L67）。`completed` 由「执行成功计数」驱动，而非由「目标达成（`goal_satisfied`）」驱动，**违反规格 §12**。需要独立 Verification 层区分 `execution_success` vs `goal_satisfied`。

> 这三类缺口均通过「扩展 `core/autonomous/`，新增 3 个桥接模块 + 扩展 `autonomous-result.js`」补齐，**不重造任何引擎、不新建 `core/autonomous-work/`**。

---

## 8. 计划新增模块（Planned New Modules — 扩展而非重复）

在 `core/autonomous/` 内新增 **3 个文件**（22 → 25 模块）：

| 新文件 | 职责 | 复用（不重造） | 零执行权 |
|---|---|---|---|
| `autonomous-verification.js` | Verification 层：`verify(observations, {goal, evalResult, budget})` → VerificationResult（含 `goalSatisfied` 硬闸，驱动 `completed`） | 复用 `goal.intent`/`constraints` 与 `evaluator` 计数；纯数据判定 | `hasExecutionAuthority()=>false`；不引用 EVENTS |
| `autonomous-reasoning-bridge.js` | Reasoning 集成桥：`reason(goal, opts)` → 调 `new ReasoningLoop(...).run(goal, opts)` → ReasoningResult；把推理结果回填自主上下文 | 复用 `core/reasoning` `ReasoningLoop`/`createReasoningResult` | `hasExecutionAuthority()=>false`；不引用 EVENTS |
| `autonomous-learning-bridge.js` | Learning 集成桥：`learn(autonomousCycleOrOutcome)` → 归一为合法 ReasoningResult（`createReasoningResult`）→ `adaptiveLearning.learnFromOutcome(result, {goalContext})` → LearningReport（advisory）；`getAdvisory(goalContext)` 回喂下一轮 planning | 复用 `core/learning/reasoning-learning` `AdaptiveReasoningLearning` + `core/reasoning` `createReasoningResult` | `hasExecutionAuthority()=>false`；不引用 EVENTS；advisory-only |

并**扩展现有模块**（非新建）：
- `autonomous-result.js`：新增 `createAutonomousWorkResult(...)`（复用 `createAutonomousResult` + 追加 `goalSatisfied/verification/learningOutcome/session/cycles/delivery`），作为统一 `AutonomousWorkResult`。
- `autonomous-loop.js`：注入 `verification / reasoningBridge / learningBridge` 协作者（默认构造），在 `_complete` 前跑 Verification（`goalSatisfied===true` 才 completed），在每轮评估后（或终态）调用 `learningBridge.learn`，把 advisory 上下文喂入下一轮 replan/select；`AutonomousWorkLoop` 作为 `AutonomousLoop` 的别名在 `index.js` 导出（不新增文件）。
- `index.js`：导出 3 新模块 + 新 `xxxHasExec` + 维护 `AUTONOMOUS_MODULE_COUNT=25`。

**为什么不再建 `core/autonomous-work/`**：规格 §20 明确「先检查现有命名避免重复；可承载则扩展已有模块」。22 文件已含 loop/session/plan/step/observation/result/budget/recovery/replanner/capability-selector/state，仅缺 verification + 两桥。新建 `core/autonomous-work/` 会与 `core/autonomous/` 形成同义重复，违反 §4「不重构已验收模块 / 不新建重复能力」。

---

## 9. 禁止修改模块（Forbidden Modifications — 规格 §四）

| 模块 | 是否可改 | 原因 |
|---|---|---|
| `core/execution/*`（含 ExecutionSandbox） | **禁止** | 唯一执行入口；改则破坏红线 1 |
| `core/orchestrator/*` | **禁止** | 唯一授权提交者 |
| `core/sandbox/*` | **禁止** | 执行权持有者 |
| `core/agent/reasoning/*`（Coding Agent 级推理环） | **禁止** | 已验收；Phase 29.3 仅复用，不重造 |
| `core/reasoning/*`（Phase 29.1） | **禁止改核心行为** | 仅作为桥接被调用；可新增导出别名 |
| `core/learning/*`（含 reasoning-learning，Phase 29.2） | **禁止改核心行为** | 仅作为 `learnFromOutcome` 被调用；advisory-only |
| `core/automation/*`（CapabilityRegistry） | **禁止改契约** | 仅 `get/has/validateRequest` 查询 |
| `core/orchestration/*`（Phase 28.5） | **禁止** | 已验收 |
| `core/events/EventBus.js` | **禁止新增事件** | 总数须恒 471 |
| 旧测试（phase5~phase29_2） | **禁止删 / 禁止降断言** | 不降验收门槛 |
| 其他第三方依赖 / Jest / Vitest / Mocha | **禁止引入** | 零依赖铁律 |

---

## 10. 数据流（Data Flow）

```
用户目标 goalInput
  │
  ▼
[AutonomousLoop.run]
  ├─ understandGoal        → goal + understanding
  ├─ decomposeGoal         → tasks
  ├─ selector.select(goal) → {selection, steps}        (复用 CapabilityRegistry)
  ├─ planner.plan(goal, steps)
  ├─ workflow.run → ExecutionRequest[]  ──(纯数据描述, target="orchestrator.submitExecutionRequest")──▶ 调用方在外部交接给 Orchestrator→ExecutionSandbox（真实执行唯一发生在此）
  │      ▲ provider.execute(batch) 仅离线模拟；真实结论来自 Sandbox 回传
  ├─ observer.observe(workflow) → observations
  ├─ decision.decideAll(observations) → 建议
  ├─ evaluator.evaluate(observations) → {outcome, counts}            （执行成功计数）
  ├─ [NEW] verification.verify(observations, {goal, evalResult}) → VerificationResult{goalSatisfied,...}
  │       completed 仅当 goalSatisfied===true
  ├─ [NEW] learningBridge.learn(cycleOutcome) → 归一 ReasoningResult → adaptiveLearning.learnFromOutcome → LearningReport(advisory)
  │       → advisory 上下文喂入下一轮 select/planner/replan
  ├─ 分支：SUCCESS+goalSatisfied → _complete(goal, observations, VerificationResult)
  │        NEEDS_REPLAN/FAILED+可重规划 → recovery.recommend → replanner.replan → 下一轮（携带 advisory）
  │        REQUIRES_HUMAN/超预算/不可重规划 → BLOCKED/FAILED/CANCELLED
  ▼
createAutonomousWorkResult({...AutonomousResult, goalSatisfied, verification, learningOutcome, delivery})
```

---

## 11. 生命周期（Lifecycle）

复用 Phase 28.6 18 态状态机（`AUTONOMOUS_STATES` / `AUTONOMOUS_TRANSITIONS` 白名单），**不新建冲突状态机**：
`created → understanding → understood → decomposing → planning → planned → selecting → awaiting_approval → executing → observing → evaluating →（replanning/recovering）→ completing → completed`（或 `failed`/`cancelled`/`blocked`）。
- 每轮评估后新增 Verification 闸：仅 `goalSatisfied===true` 允许 `evaluating → completing`；否则按 `evaluator.outcome` 走 replan/recover/block。
- 每轮（或终态）调用 LearningBridge：advisory 反馈写入 `AutonomousContext`，供下一轮 `select`/`planner`/`replanner` 读取（只读建议，不自动改执行/审批/sandbox/authorization）。
- 循环保护（规格 §15）：`AutonomousBudget`（maxReplans/maxReplan/budget）+ `AutonomousLoop.cancel()` 外部取消闸 + `reasoningBridge` 内 `ReasoningLoopDetector`（loop fingerprint / state repetition）。循环必有终点。

---

## 12. 红线（Red Lines）

1. **唯一执行链 Orchestrator→ExecutionSandbox**：自主层只生成纯数据 ExecutionRequest 描述，绝不直执行（无 child_process/fs/fetch/真实 API）。
2. **零执行权**：所有新增模块 `hasExecutionAuthority()===false`；无 `acquireExecutionHandle/performExecution/apply/rollback/submitExecutionRequest`。
3. **禁止注入执行句柄**：`AUTONOMOUS_FORBIDDEN_INJECTION_KEYS`（含 `acquireExecutionHandle/executionHandle/sandboxHandle/orchestrator/submitExecutionRequest/...`）构造期硬闸。
4. **Learning 仅 advisory**：`learnFromOutcome` 反馈只影响下一轮 planning/strategy，**绝不自动修改执行/审批/sandbox/authorization policy**（recommendation/context `isAdvisory===true`）。
5. **Verification 硬闸**：`completed` 由 `goal_satisfied===true` 驱动，不能只由 `execution_success` 驱动。
6. **0 新增事件**：EventBus 恒 471；不新建 `Autonomous*` 事件。
7. **不重造引擎**：Reasoning/Learning/Automation/Orchestration/Recovery 全部复用，不新建第二执行引擎 / Kernel Manager。
8. **零依赖**：不引入第三方测试框架/库；仅 `node:` 内置 + 层内相对引用。
9. **不自动进入 Phase 29.4**：完成即严格停止。
10. **不回问「是否继续」**：完成即 `STOP_AT_PHASE_29_3`。

---

## 13. 15 个侦察问题（明确回答）

**Q1. Phase 29.1 Reasoning Engine 的入口是什么？**
`core/reasoning/index.js` 导出 `ReasoningLoop` / `understandGoal` / `planFromGoal` / `createReasoningResult` / `isReasoningResult` / `verifyReasoningZeroAuthority`。入口类 `new ReasoningLoop(opts).run(goalInput, opts)` → 纯数据 `ReasoningResult`（`core/reasoning/loop.js` L136）。`understandGoal(goalInput)` / `planFromGoal(goal)` 为纯函数（`loop.js` L43/L63）。模块级 `hasExecutionAuthority()=>false`。

**Q2. Phase 29.1 ReasoningResult 的形状是什么？**
`createReasoningResult(opts)` 产出（`core/reasoning/result.js` L32）：`{id, goalId, objective, intent, status, stopReason, rounds, cycles, finalDecision, intermediateResults, capabilitiesUsed, summary, replansUsed, correctionsUsed, executionAuthority:false, authorityHolder:"execution-sandbox"}`。`isReasoningResult(v)` 校验（status∈`success/partial_success/failed/blocked/cancelled/budget_exceeded/loop_detected`，零执行权，无 banned 字段）。**Learning 层强制要求合法 ReasoningResult**。

**Q3. Phase 29.2 Learning 的入口是什么？**
`core/learning/reasoning-learning/index.js` 导出 `createAdaptiveReasoningLearning(opts)` → `AdaptiveReasoningLearning`。主入口 `learnFromOutcome(result, {nowIso, goalContext})`（`engine.js` L108），要求 `isReasoningResult(result)` 为真，返回 deepFrozen `LearningReport`。另有 `recommendForGoal(ctx)` / `injectContext(ctx)`（纯 advisory）。`verifyReasoningLearningZeroAuthority()`（8 项 invariants）。

**Q4. Phase 29.2 Learning 能否修改执行/审批/sandbox/authorization？**
**不能**。本层是「学习/自适应层」而非执行层：`recommendation.isAdvisory===true` / `context.isAdvisory===true`（index.js L148-152 自证）；门面无 `apply/rollback/submitExecutionRequest`（engine.js `verifyZeroAuthority` L257）；原始历史永不删除（衰减只降权）。反馈只影响下一轮 planning/strategy。

**Q5. Phase 28.6 AutonomousLoop 的入口是什么？**
`new AutonomousLoop({eventBus, registry, policy, budget, selector, planner, observer, evaluator, replanner, recovery, decision, context, memory}).run(goalInput, opts)`（`autonomous-loop.js` L46/L98）→ `AutonomousResult`。`hasExecutionAuthority()=>false`；`provider.execute(batch)` 仅离线模拟外部执行；`cancel()` 置 `this.cancelled`（外部取消闸）。

**Q6. Phase 28.6 状态机是什么？**
`AUTONOMOUS_STATES`（18 态：`created/understanding/understood/decomposing/planning/planned/selecting/awaiting_approval/executing/observing/evaluating/replanning/recovering/completing/completed/failed/cancelled/blocked`）；`AUTONOMOUS_TRANSITIONS` 合法迁移白名单（终态无出边）；`AUTONOMOUS_EVENT_NAMES`（16 个 Autonomous* 事件）；`AUTONOMOUS_EVENT_COUNT=16`（`autonomous-state.js`）。

**Q7. CapabilityRegistry 入口与内置能力？**
`new CapabilityRegistry(seed)`（`seed!==false` 时种子 `createBuiltinCapabilities()`）。方法 `register/get/require/has/list/count/validateRequest`（`core/automation/registry.js` L34+）。内置 6 能力：`research/web/computer/vision/document/data`。`hasExecutionAuthority()=>false`。自主层只经 `registry.get/has/validateRequest` 引用契约，**绝不 `new XxxAgent`**。

**Q8. ExecutionSandbox 的执行入口与唯一链？**
`verifyExecutionPipelineZeroAuthority()`（`core/execution/index.js` L135）证明：授权/审批/请求三层 `allZeroAuthority===true`；sandbox 白名单 `AUTHORIZED_CALLERS`（取自 `ExecutionSandbox.js`）= `["orchestrator"]`，`singleAuthorizedSubmitter === (length===1 && [0]==="orchestrator")` 为 `true`。唯一合法链路 `…→Orchestrator→ExecutionSandbox→ExecutionResult`。

**Q9. EventBus 权威事件总数？**
**471**，动态 `Object.keys(EVENTS).length`（EventBus.js 冻结枚举）。Phase 28.6 新增 16 个 Autonomous* 事件；Phase 29.1 新增 7 个 Reasoning* 事件。Phase 29.3 **必须保持 471**（0 新增事件），否则 Gate 2/3/4 全灭。

**Q10. AutonomousLoop 是否集成 Phase 29.1 Reasoning？**
**否（缺口 1）**。`autonomous-loop.js` 全文无 `new ReasoningLoop` / `core/reasoning` 引用；其 `planner/observer/evaluator/provider` 均为自主层自有组件。Phase 29.3 经 `autonomous-reasoning-bridge.js` 注入 `ReasoningLoop`（复杂目标多轮推理）。

**Q11. AutonomousLoop 是否集成 Phase 29.2 Learning？**
**否（缺口 2）**。`autonomous-loop.js` 无 `createAdaptiveReasoningLearning` / `learnFromOutcome`。Phase 29.3 经 `autonomous-learning-bridge.js` 在每轮（或终态）调用 `learnFromOutcome`（advisory），回喂下一轮 planning。

**Q12. Verification 现状？**
`AutonomousEvaluator.evaluate` 是**代理闸**：仅按 `completed+skipped===total && failed===0` 计数判 `success`（`autonomous-evaluator.js` L67），无显式 `goal_satisfied` 判定。→ **缺口 3**：`completed` 由「执行成功计数」驱动，而非「目标达成」。**Phase 29.3 新增 `autonomous-verification.js`，以 `goalSatisfied===true` 为 `completed` 硬闸**（规格 §12）。

**Q13. Replanning 现状？**
`AutonomousReplanner.replan(previousSteps, observations, {replanIndex})` 已存在（`autonomous-replanner.js`）；`AutonomousLoop` 在 `evalResult.outcome∈{NEEDS_REPLAN, FAILED}` 且 `budget.canReplan(replansUsed)` 时调用，`replansUsed++`，**真实 plan revision**（非 `planVersion++`）（`autonomous-loop.js` L216-L242）。Phase 29.3 让其携带 LearningBridge 的 advisory 上下文。

**Q14. 各能力层执行权？**
全部 `false`：Autonomous（模块级+实例，`verifyAutonomousZeroAuthority` 10 invariants）/ Reasoning（`verifyReasoningZeroAuthority`）/ Learning（`verifyReasoningLearningZeroAuthority` 8 invariants）/ Automation-Registry / Execution Pipeline 三层。唯一持有者为 ExecutionSandbox（白名单 `orchestrator`）。

**Q15. 当前最小闭环缺口到底是什么？**
**Verification（缺 `goal_satisfied` 硬闸）+ Reasoning（29.1 未接入）+ Learning（29.2 未接入）三段集成**。解决方式 = 在 `core/autonomous/` 内新增 3 个桥接模块（verification / reasoning-bridge / learning-bridge）+ 扩展 `autonomous-result.js`/`autonomous-loop.js`，**不新建 `core/autonomous-work/`，EventBus 保持 471，0 新增事件，所有新增模块零执行权**。

---

## 14. 七道闸门计划（Gate Plan — 规格 §四十二）

| Gate | 产物 | 通过条件 | 双次复现 |
|---|---|---|---|
| G1 | `phase29_3_autonomous_work_loop_test.js`（新建） | ≥70 段 / ≥60000 断言 / 0 FAIL | ×2 |
| G2 | `scripts/scan-autonomous-work-execution.js`（新建，同源于 scan-autonomous-execution.js） | Token=0 / Dep=0 / Violation=0 / EXIT 0（含 0 新增事件、模块数=25、EventBus=471） | ×2 |
| G3 | `node scripts/check-consistency.js --fix` | EXIT 0 | 复跑 |
| G4 | `npm run test:all`（链尾加本阶段 2 测试文件） | 链尾 + 该文件 / 0 FAIL | 至少首轮通过 |
| G5 | `scripts/autonomous-work-smoke.js`（新建） | ≥20 场景 / 0 FAIL | ×2 |
| G6 | `phase29_3_autonomous_work_conversation_e2e_test.js`（新建） | ≥15 多轮 / ≥250 断言 / 0 FAIL | ×2 |
| G7 | `main.js` 新增 `[统一自主工作闭环演示]`（真实运行） | EXIT 0 | ×2 |

> **同步点（必须同步，否则旧 Gate 灭）**：
> - `scripts/scan-autonomous-execution.js`：`EXPECTED_AUTONOMOUS_FILES` 增 3 文件、`EXPECTED_AUTONOMOUS_MODULE_COUNT` 22→25（保持 Phase 28.6 Gate 仍绿）。
> - `core/autonomous/index.js`：`AUTONOMOUS_MODULE_COUNT` 22→25，导出 3 新模块 + `xxxHasExec`。
> - `package.json`：`version`/`kernelVersion` 升级；`test:all` 链尾追加 2 文件；新增 `test:phase29_3` / `check:autonomous-work:execution` / `smoke:autonomous-work` / `gate6:autonomous-work:e2e` 脚本。
> - `scripts/check-consistency.js`：派生计数点同步（实施时核查）。

---

## 15. 版本与完成判定（Version & Completion）

- **版本升级**：`package.json` `version`/`kernelVersion` 由 `0.35.0` 按规则升级（拟 `0.36.0`，最终值以 `check-consistency` 真源校验为准），同步 description 前缀追加 Phase 29.3 说明、test:all 链、scanner 常量、reports、memory。
- **完成判定**：G1–G7 全过（双次复现达成）→ 产出 `PHASE29_3_UNIFIED_AUTONOMOUS_WORK_LOOP_REPORT.md`（≥35 节）→ 更新 memory（`.workbuddy/memory/2026-08-13.md` + 同步 `MEMORY.md`）→ 明确 `PHASE_29_3_COMPLETE` / `STOP_AT_PHASE_29_3`。
- **严格停止**：不进入 Phase 29.4、不回问「是否继续」。

---

*基线已确认最小新增边界 = `core/autonomous/` 内 3 桥接模块（verification / reasoning-bridge / learning-bridge）+ 扩展 `autonomous-result.js`/`autonomous-loop.js`，EventBus 471 不变，所有新增模块零执行权，0 新增事件。下一步按规格 §四十六 小步实施 Step 2（Core Data Model）。*
