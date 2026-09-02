---
id: know-phase-31-2-autonomous-task-execution-recovery-la
type: concept
---
# Phase 31.2 最终验收报告 — Autonomous Task Execution & Recovery Layer（自主任务执行与恢复层）

> 验收主体：PersonalAIOS Kernel / Capability Runtime —— Phase 31.2 新增「多步编排 / exactly-once 派发 / 陈旧结果防护 / 重规划 / checkpoint 恢复」自主任务运行时层。
> 验收结论：**PHASE_31_2_COMPLETE = true / STOP_AT_PHASE_31_2 = true**。
> 验收纪律：验收优先于实现 · 真实 API 优先于猜测 · Reuse > Duplicate · Zero Execution Authority · Deterministic · No External Dependency · No Test Framework · No Silent Scope Expansion。

---

## 1. Executive Summary

Phase 31.2 在 Phase 24.0 任务运行时地基（`core/autonomy/task/`）之上，补齐了「自主任务执行与恢复层」：控制器 `AutonomousTask` 接收目标 → 分解为计划（`TaskPlan`）→ 依赖调度（`TaskScheduler`）→ exactly-once 派发（`TaskDispatch`）→ 经注入的 `TaskManager`（唯一真实执行入口 Orchestrator → ExecutionSandbox）投递 → 陈旧防护验收（`TaskStaleGuard`）→ 结果评估（`TaskResultEvaluator`）→ 进度（`TaskProgress`）→ checkpoint 恢复 → 失败且阻塞时确定性重规划（`TaskReplan`）→ 目标满足度判定（`finalize`）。

控制器**自身零执行权**：`hasExecutionAuthority()` 恒 `false`；`acquireExecutionHandle()` / `performExecution()` 恒抛错；构造期硬闸拒收任何执行句柄（`orchestrator` / `sandbox` / `executionSandbox` 等）。全七道 Gate + Round 2 双次复现 + 最终一致性 + 全量回归 **全部 PASS**。无生产代码被破坏，无第二执行引擎，无外部依赖，无测试框架引入。

## 2. Phase Scope

- **新增能力**：Autonomous Task Execution & Recovery Layer（自主任务执行与恢复层）。
- **核心模块**（`core/autonomy/task/`）：8 个多步编排子层 API 全 1.0.0 —— `TaskPlan` / `TaskScheduler` / `TaskDispatch` / `TaskStaleGuard` / `TaskProgress` / `TaskResultEvaluator` / `TaskReplan` / `AutonomousTask`，叠加 Phase 24.0 任务运行时内核（共 25 个实现模块 + `index.js`）。
- **复用**：`TaskManager`（Phase 24.0）→ Orchestrator → ExecutionSandbox；认知对齐层不重造；能力选择 / 学习仅按引用接入。
- **不新增 EventBus 事件**：复用既有 `TaskRuntime*` 事件（EventBus 仍 490，无净新增）。

## 3. Baseline

| 项 | 真源值 |
|---|---|
| package.json.version / kernelVersion | 0.39.0 |
| EventBus 唯一事件常量 | 490 |
| test:all 套件段数 | 55 |
| 任务运行时状态机 | 14 态（3 终态） |
| 任务运行时禁注键数 | 387 |
| 任务运行时广播事件数 | 18 |
| 多步编排层 API 版本 | 1.0.0（8 个子层全一致） |
| Runtime Control Plane（同 Phase 31.2 兄弟子层） | 10 模块 / 7 控制请求态 / 46 禁注键 / API 1.0.0 |

## 4. Architecture

```
Goal
  ↓ planGoal()            → TaskPlan.createTaskPlan（分解 + 依赖 DAG）
  ↓ runGoal() 主循环
      nextStep()          → TaskScheduler（拓扑确定下一步）
      executeStep()       → TaskDispatch.prepareStep（exactly-once 幂等派发）
                            → manager.submit(childTaskId)
                                → ExecutionRequestManager（授权/审批/请求纯数据）
                                → Orchestrator.submitExecutionRequest（唯一执行入口）
                                → ExecutionSandbox（真实执行，adapter 边界）
                            → TaskStaleGuard.accept（陈旧结果防护）
                            → TaskResultEvaluator.evaluateStep（SUCCESS/CANCELLED/BLOCKED/RETRY）
      checkpoint()        → 纯数据快照（可 JSON 序列化）
      失败且阻塞          → TaskReplan.replan（移除失败步骤 + 全部下游依赖者，确定性回退）
  ↓ finalize()            → 目标满足度判定（纯数据）
```

唯一真实执行链：**Orchestrator → ExecutionSandbox**。控制器只编排/派发/重规划/收敛，自身零执行权、绝不直执行。

## 5. Module Inventory

`core/autonomy/task/` 共 26 个 `.js`（25 实现模块 + `index.js`）。新增编排子层（8 个，API 均 `1.0.0`）：

- `TaskPlan.js`（计划分解 / 依赖图 / 拓扑 / add/remove/dependents）
- `TaskScheduler.js`（nextStep / scheduleAll / isComplete / hasBlockingFailure）
- `TaskDispatch.js`（exactly-once 派发 / dispatchedCount / childId 格式）
- `TaskStaleGuard.js`（陈旧防护三态：ok / duplicate / stale-or-unknown / missing-request-id）
- `TaskProgress.js`（进度百分比 / 快照字段 / Math.floor 确定性）
- `TaskResultEvaluator.js`（结果评估映射 / STEP_OUTCOMES）
- `TaskReplan.js`（确定性回退：移除失败 + 下游；可复用 Reasoning 层 proposePlan）
- `AutonomousTask.js`（多步编排总控，extends PipelineComponent）

Phase 24.0 内核（复用，不重造）：TaskState / TaskFailure / TaskContext / TaskResult / TaskModel / TaskRegistry / TaskHistory / TaskMetrics / TaskSnapshot / TaskSerializer / TaskRetryPolicy / TaskTimeout / TaskRecovery / TaskCompensation / TaskMonitor / TaskLifecycle / TaskManager。

## 6. PipelineComponent（零执行权基类事实）

`AutonomousTask extends PipelineComponent`（`core/execution/shared/pipeline-base.js`）。**关键 API 事实（已攻击式验证）**：

- `hasExecutionAuthority()` → `false`（实例方法，非 static）。
- `acquireExecutionHandle()` → 恒抛 `PipelineExecutionAuthorityDenied`。
- `performExecution()` → 恒抛 `PipelineExecutionAuthorityDenied`。
- `describe()` → `{ component, layer, apiVersion, executionAuthority: false, authorityHolder: "execution-sandbox", forbiddenInjectionCount }`。
- **`instance.executionAuthority` 与 `instance.authorityHolder` 均为 `undefined`** —— 基类构造器只设置 `componentName` / `layer` / `clock` / `emit`，**不把这两个字段设为 instance prop**。因此禁止断言 `component.executionAuthority === false`；正确方式是用 `hasExecutionAuthority()` 与 `describe()` 自证。

## 7. AutonomousTask（多步编排总控）

- 构造：`super(guardedTaskOptions(...))` 先跑本层禁注硬闸；随后显式拒绝 `orchestrator` / `executionSandbox` / `sandbox`（抛 `TaskRuntimeInjectionError`，fail-closed）；要求注入 `manager`（唯一执行入口）。
- `planGoal(input)` → 创建计划 + 在 manager 中创建代表整体目标的父任务（供审计/checkpoint）。
- `executeStep(stepId)` → exactly-once 派发 → manager.submit（唯一真实执行链）→ 陈旧防护验收 → 评估结果 → 更新进度。
- `runGoal(input, opts)` → 主循环：checkpoint → nextStep → executeStep →（失败且阻塞→replan）→ finalize。返回纯数据收敛结果。
- `checkpoint()` / `restore(snapshot)` → 纯数据快照确定性重放。
- `describe()` / `hasExecutionAuthority()` → 零执行权自证。

## 8. Pipeline（计划 / 调度）

`TaskPlan.createTaskPlan` 分解目标为带依赖的 DAG；`TaskScheduler.nextStep` 在拓扑序上返回下一个就绪步骤（确定性）；`scheduleAll` / `isComplete` / `hasBlockingFailure` 提供全局判定。`validatePlanDag` 校验 DAG 合法性（无环 / 依赖存在）。

## 9. Task State Machine

14 态（`TASK_STATE_COUNT=14`，3 终态：`succeeded` / `abandoned` / `cancelled`）。状态迁移由 `TaskLifecycle.applyTransition` + `canTransitionTask` 守卫，非法迁移抛 `TaskRuntimeStateError`。`verifyTaskStateGraph()` 静态证明状态图自洽。

## 10. Step State Machine

每步经派发 → 子任务 created → submitted → running → succeeded/failed；失败进入 recovering → retrying/compensating/abandoned。步骤级结果由 `TaskResultEvaluator.evaluateStep` 映射为 `STEP_OUTCOMES`（SUCCESS / CANCELLED / BLOCKED / RETRY）。

## 11. Retry

两层重试，分工明确：① 沙箱内层重试（`retryLimit`）；② 任务级重试 —— 内层预算耗尽、沙箱交回「失败」后，`TaskManager._onFailure` 经 `analyzeRecovery` 判为可恢复 → `_retry`（另开新 ExecutionRequest 再来一轮）。`TaskRetryPolicy` + `shouldRetry` 决定上限与策略。

## 12. Failure

`TaskFailure.classifyFailure` 分类失败（瞬时 / 永久 / 授权 / 审批 / 超时等）。永久失败（或授权/审批失败）不重试，进入 recovery 终态判定 → 终止（abandon）或触发重规划（若阻塞下游且允许）。

## 13. Replan

`TaskReplan.replan(plan, { stepId }, {})`：若注入 `reasoner`（复用 Reasoning 层）则委托其 `proposePlan`；否则走确定性回退——`collectDependents` 收集失败步骤的全部下游依赖者，`removeStep` 逐一移除。重规划只产出纯数据新计划，不执行任何动作、不持有执行句柄。**本验收的真实默认行为为「移除失败步骤 + 全部下游」**，剩余目标仍满足即收敛（Gate 7 实测：s3 永久失败 → 移除 s3 及下游 s4 → 余 s1/s2/s5 完成）。

## 14. Convergence

`finalize()` 依据 `progressState` 计算 `goalSatisfied` = `total>0 && completed===total && blocked===0 && failed===0 && cancelled===0`。收敛后返回纯数据 `{ goalId, goalSatisfied, status, totalSteps, completedSteps, ..., executionAuthority: false, authorityHolder: "execution-sandbox", checkpoints, replans, events }`。

## 15. ExecutionRequest

`ExecutionRequestManager.create(contextToRequestInput(ctx))` 生成纯数据请求（who/what/why/capability/resource/scope/arguments/risk/approval/requestId）。**不含执行器语义、不含函数**。`scan-task-runtime-execution.js` 静态验证请求层纯数据红线。

## 16. Result Model

`TaskResult.createTaskResult` / `PipelineResult`（若适用）均为纯数据；`assertTaskResultPure` / `assertTaskRuntimePure` 在落库前硬闸纯度。`createTaskResult` 输出只读 `status` / `summary` / `requestId`，绝不携带 buffer/stream/handle/instance。

## 17. Delivery

执行结论经 Orchestrator 回填为纯字符串（`resultReason` / `resultError`），任务运行时只读纯数据判定失败类型与可否重试，不触碰任何执行句柄。Delivery 即「纯数据结果 + 事件广播」。

## 18. Zero Authority

- `AutonomousTask.hasExecutionAuthority()` = `false`（攻击式验证：ADV-2）。
- `acquireExecutionHandle()` / `performExecution()` 均抛错（ADV-3/4）。
- `verifyAutonomousTaskOrchestration().ok` = `true`（checked=8，覆盖 4 组件执行权 + exactly-once + 陈旧防护 + 重规划 + 红线注入拒绝）。
- `verifyAutonomousTaskRuntime().selfProofOk` = `true`，`allZeroAuthority` = `true`。
- `authorityHolder` 唯一为 `execution-sandbox`（来自 `describe()`，非 instance prop）。

## 19. Forbidden Injection

- `AutonomousTask` 构造注入 `orchestrator`/`sandbox`/`executionSandbox`/`terminal`/`tool`/`worker`/`agent`/`registry` → **拒收**（抛 `TaskRuntimeInjectionError`，ADV-1）。
- 基类 `PipelineComponent` 构造器在 super 实参位先跑 `assertNoInjected`（管线禁注清单，含安全别名）。
- 任务运行时禁注清单 = **387** 类（超集于管线清单）；Runtime Control Plane = 46 类。

## 20. Purity

- `hasFunctionDeep(output)` 恒 `false`：ExecutionRequest / TaskResult / PipelineResult / Checkpoint / RetryResult / ReplanResult 均不含函数 / 执行面键 / 实例。
- `findForbiddenKeysDeep`（若 scanner 提供）用于深度禁注键探测；注入键抛错、纯度键可被白名单剥离（按真实 API 语义断言，不要求所有非法字段都抛异常）。

## 21. Determinism

- 逻辑时钟（`normalizeClock`）驱动全部超时/重试/进度，绝不依赖真实时间。
- 相同 `goal`/`steps`/`provider`/`options` 产生稳定结构：状态数、步骤数、retry 次数、replan 次数、convergence、executionAuthority、authorityHolder 一致（sessionId/timestamp 等允许变化字段除外）。
- `probe-312.js` 与端到端 e2e 双验证确定性重放。

## 22. EventBus

- EventBus 真源 = **490**（Phase 31.2 复用既有 `TaskRuntime*` 事件，无净新增；一致性扫描器真源 `truthEventCount` 核对一致）。
- `TASK_RUNTIME_EMIT_COUNT` = 18（均为纯广播，不携带任何执行句柄）。

## 23. Memory

- 本层不直连 Memory；若经 `learner` / `capabilitySelector` 复用既有层，仅按引用接入，不复制引擎实例。
- 纯数据结果可安全写 Memory（无 buffer / 无 execution handle / 无 agent/sandbox 实例），符合既有 Memory 契约，不创建第二套 Memory。

## 24. Gate 1 — 核心测试

| 子层 | 命令 | 段数 | 断言 | FAIL | EXIT |
|---|---|---|---|---|---|
| task-runtime | `node phase31_2_task_runtime_test.js` | 80 | 231,834 | 0 | 0 |
| runtime-control | `node phase31_2_runtime_control_test.js` | 72 | 64,978 | 0 | 0 |

覆盖：版本/事件/套数/描述不变量、8 大模块 API 完整、零执行权自证、禁注清单、计划分解/拓扑/依赖、调度确定性、派发 exactly-once、陈旧防护三态、进度确定性、结果评估映射、重规划确定性回退、checkpoint/restore、端到端 A–F 真实链路。门槛（≥80 段 / ≥120000 断言 / 0 FAIL）**达标**。

## 25. Gate 2 — Execution Scanner

| 子层 | 命令 | TOKEN | DEP | VIOL | STRUCT | RUNTIME | EXIT |
|---|---|---|---|---|---|---|---|
| task-runtime | `node scripts/scan-task-runtime-execution.js` | 0 | 0 | 0 | PASS | PASS | 0 |
| runtime-control | `node scripts/scan-runtime-control-execution.js` | 0 | 0 | 0 | PASS | PASS | 0 |

要求 Token=0 / Dependency=0 / Violation=0 全部满足；Structural（index 导出 hasExecutionAuthority + verify*）与 Runtime Invariant（verify*.ok）全 PASS。

## 26. Gate 3 — Consistency

`node scripts/check-consistency.js --fix` → EXIT 0；`node scripts/check-consistency.js` → EXIT 0；**全部派生点与真源一致**。

- 真源 package.json.version = 0.39.0；EventBus = 490；test:all 套件段数 = 55；末端套件 = phase31_2_task_runtime_test.js。
- 已校验派生点：版本号 48 处 · 事件总数 108 处 · 套件数 12 处 · 末端套件 3 处 · UI API 方法数 2 处。
- 全仓搜索确认无旧 EventBus / 旧 version / 旧 test suite count / 旧阶段描述漂移（除一处刻意保留的否定断言 `phase17_goal_test.js:2173 0.19.0`，非 drift）。
- `--fix` 不覆盖所有非标准派生点，故已做全仓字符串搜索核对（见 §32）。

## 27. Gate 4 — test:all

`NODE_OPTIONS="" npm run test:all` → **EXIT 0**。

- 链式 `node X && node Y && ...` 共 **55** 个套件，**全部执行**（无早期停止，无缺失）。
- 全链 **0 FAIL**（已 grep `FAIL [1-9]` / `失败 [1-9]` / `failed [1-9]` / `npm ERR` / `not ok` 均为空）。
- 末套件 `phase31_2_task_runtime_test.js` 完整跑完（231,834 断言 / 0 FAIL），佐证整链贯通。

## 28. Gate 5 — Smoke

| 子层 | 命令 | 检查 | 场景 | FAIL | EXIT |
|---|---|---|---|---|---|
| task-runtime | `node scripts/task-runtime-smoke.js` | 279 | 35 | 0 | 0 |
| runtime-control | `node scripts/runtime-control-smoke.js` | 183 | 28 | 0 | 0 |

覆盖：module exports / constructor / zero authority / forbidden injection / pipeline creation / task creation / step creation / dependency / state transition / execution request purity / retry / transient failure / permanent failure / replan / convergence / failure recovery / deterministic / serialization / EventBus / authority holder / no execution token / forbidden keys / external dependency = 0 / main integration。

## 29. Gate 6 — 对话 E2E

| 子层 | 文件 | 断言 | FAIL | 段 | EXIT |
|---|---|---|---|---|---|
| task-runtime | `phase31_2_task_runtime_conversation_e2e_test.js` | 797 | 0 | 4（≥16 多轮 / ≥700 断言） | 0 |
| runtime-control | `phase31_2_runtime_control_conversation_e2e_test.js` | 510 | 0 | 5（≥12 多轮 / ≥500 断言） | 0 |

task-runtime e2e 真实执行跨 17 turns 的完整闭环：plan → step-by-step execution → transient retry → permanent failure → replan → convergence。逐轮验证：状态正确、上下文无非法污染、execution authority 恒 false、纯数据结果、authorityHolder 正确、禁注键不存在、EventBus 正确、跨轮状态正确。**未破坏既有 PipelineComponent 断言（正确使用 `hasExecutionAuthority()` / `describe()`，未断言不存在的 instance prop）**。

## 30. Gate 7 — main.js 真实演示

`PAIOS_MODEL=heuristic node main.js "完成一个需要多步骤执行、失败恢复和重新规划的自主任务"` → **EXIT 0**。

新增 `[自主任务流水线演示]` 段（紧邻既有 Phase 31.2 Runtime Control Plane 演示，最小插入，未改动其他 demo / 错误处理 / 事件监听），真实跑通：

```
[自主任务流水线演示] 层级=task-runtime | API版本=1.0.0 | 目标=goal_b825b5f7 | 初始步骤数=5 | 重规划后步骤数=3
  1. Transient Failure: s2 首调抛错 → Retry: 任务级重试后成功（适配器 s2 实际调用=2 次）
  2. Permanent Failure: s3 永久失败（适配器 s3 实际调用=3 次）→ Replan: 移除失败步骤 s3 及其下游 s4（重规划次数=1）
  3. Convergence: 状态=satisfied | 完成=3/3 | goalSatisfied=true | 检查点=5 | 执行事件=5
  4. 任务完成=是（移除永久失败及其下游后，剩余目标仍满足） | 结果冻结=true
  5. 零执行权自证: hasExecutionAuthority()=false | verifyAutonomousTaskOrchestration().ok=true（检查项=8）| verifyAutonomousTaskRuntime().selfProofOk=true
  6. 执行权=false | authorityHolder=execution-sandbox | executionToken=0 | 唯一链路:Orchestrator → ExecutionSandbox
```

非兜底验证（grep 确认）：EXIT 0 ✓ · Gate 7 banner 存在 ✓ · 关键结果字段存在 ✓ · 无 `fallback skip` ✓ · 无 catch 伪造成功 ✓ · 无 `demo unavailable` ✓ · 无 `not implemented` ✓ · 无隐藏异常 ✓ · 未执行真实系统命令 ✓ · 未产生 execution token ✓ · 唯一 authorityHolder 仍 `execution-sandbox` ✓。

注：演示中 worker adapter 的真实执行请求载荷 `resource` 位于 `req.payload.resourceId`（纯字符串），非 `req.payload.resource.id` —— 已据此修正适配器键读取，确保瞬时失败/永久失败/重规划路径**真实触发**（非假成功）。

## 31. Round 1

| Gate | 结果 |
|---|---|
| G1 | task 80 段 / 231,834 断言 / 0 FAIL；rc 72 段 / 64,978 断言 / 0 FAIL |
| G2 | task + rc：TOKEN=0 DEP=0 VIOL=0 STRUCT=PASS RUNTIME=PASS |
| G3 | FIX_EXIT=0 / CHECK_EXIT=0 / 全部派生点一致 |
| G4 | EXIT 0 / 55/55 套件 / 0 FAIL |
| G5 | task 279/0（35 场景）；rc 183/0（28 场景） |
| G6 | task 797/0；rc 510/0 |
| G7 | EXIT 0 / 真实 runGoal 链 / 0 FAIL |

## 32. Round 2（双次复现）

复现 G1/G2/G5/G6/G7 + 最终 G3/G4，对比 Round 1：

| 指标 | R1 | R2 | 一致 |
|---|---|---|---|
| G1 task 段/断言 | 80 / 231,834 | 80 / 231,834 | ✅ |
| G1 rc 段/断言 | 72 / 64,978 | 72 / 64,978 | ✅ |
| G2 TOKEN/DEP/VIOL | 0/0/0 | 0/0/0 | ✅ |
| G5 task / rc 检查 | 279 / 183 | 279 / 183 | ✅ |
| G6 task / rc 断言 | 797 / 510 | 797 / 510 | ✅ |
| G7 EXIT / 真实链 | 0 / 真实 | 0 / 真实 | ✅ |
| EventBus | 490 | 490 | ✅ |
| version | 0.39.0 | 0.39.0 | ✅ |
| 套数 | 55 | 55 | ✅ |
| executionToken | 0 | 0 | ✅ |

**Round 1 == Round 2，无漂移。**

## 33. Regression

- 全量 `test:all` 55 套件全部执行、0 FAIL、EXIT 0（G4 + Final 两次独立运行一致）。
- 未修改 `core/execution` / `core/orchestrator` / `core/sandbox` 任何核心。
- 未创建第二套执行引擎；未注入 worker/tool/toolRegistry/orchestrator/agentRegistry/messageRouter。
- 无第三方测试框架引入；无新外部依赖。

## 34. Known Pitfalls

1. **`PipelineComponent` 不设 `executionAuthority` / `authorityHolder` instance prop**（均为 `undefined`）。零执行权必须用 `hasExecutionAuthority()` 与 `describe()` 证明；禁止断言 `instance.executionAuthority === false`。Gate 6 已采用此正确方式，未回退到错误断言。
2. **真实执行请求载荷的 `resource` 在 `req.payload.resourceId`**（纯字符串），不是 `req.payload.resource.id`。适配器若读错键，会静默错过瞬态/永久失败路径（演示曾一度显示「适配器调用=0 次」，修正键读取后真实触发重试/重规划）。
3. **默认 `TaskReplan.replan` 是「移除失败 + 全部下游」的确定性回退**，而非凭空新增步骤；只有注入 `reasoner` 才走 proposePlan 新增。演示输出如实反映移除语义，未伪造「新增步骤成功」。

## 35. API Facts（关键事实记录）

- `AutonomousTask extends PipelineComponent`；构造拒收 `orchestrator`/`executionSandbox`/`sandbox`（抛 `TaskRuntimeInjectionError`）。
- `hasExecutionAuthority()` → `false`（实例方法）。
- `acquireExecutionHandle()` / `performExecution()` → 恒抛 `PipelineExecutionAuthorityDenied`。
- `describe()` → `{ executionAuthority: false, authorityHolder: "execution-sandbox", ... }`。
- `runGoal({ goal, steps }, { allowReplan, maxReplans })` → 纯数据收敛结果（`executionAuthority: false` / `authorityHolder: "execution-sandbox"`）。
- `verifyAutonomousTaskOrchestration({ clock })` → `{ ok, checked, components, problems }`（checked=8）。
- `verifyAutonomousTaskRuntime({ clock })` → `{ selfProofOk, allZeroAuthority, forbiddenInjectionCount, taskIsFrozen, requestHasNoFunction, requestHasNoExecutor }`。
- `instance.executionAuthority` / `instance.authorityHolder` = `undefined`（非 instance prop）。

## 36. Reproduction Commands

```bash
# Gate 1
node phase31_2_task_runtime_test.js
node phase31_2_runtime_control_test.js
# Gate 2
node scripts/scan-task-runtime-execution.js
node scripts/scan-runtime-control-execution.js
# Gate 3
node scripts/check-consistency.js --fix && node scripts/check-consistency.js
# Gate 4
NODE_OPTIONS="" npm run test:all
# Gate 5
node scripts/task-runtime-smoke.js
node scripts/runtime-control-smoke.js
# Gate 6
node phase31_2_task_runtime_conversation_e2e_test.js
node phase31_2_runtime_control_conversation_e2e_test.js
# Gate 7
PAIOS_MODEL=heuristic node main.js "完成一个需要多步骤执行、失败恢复和重新规划的自主任务"
# 攻击式自证
node scripts/probe-312.js
```

## 37. Deliverables

- **核心模块**：`core/autonomy/task/`（25 实现模块 + index.js；8 编排子层 API 1.0.0）。
- **测试**：`phase31_2_task_runtime_test.js`（80 段 / 231,834 断言）、`phase31_2_runtime_control_test.js`（72 段 / 64,978 断言）。
- **Scanner**：`scripts/scan-task-runtime-execution.js`、`scripts/scan-runtime-control-execution.js`。
- **Smoke**：`scripts/task-runtime-smoke.js`（279/0）、`scripts/runtime-control-smoke.js`（183/0）。
- **对话 E2E**：`phase31_2_task_runtime_conversation_e2e_test.js`（797/0/17 turns）、`phase31_2_runtime_control_conversation_e2e_test.js`（510/0）。
- **main.js Gate 7 演示**：`[自主任务流水线演示]`（紧邻 Phase 31.2 Runtime Control Plane 演示，最小插入）。
- **探针**：`scripts/probe-312.js`（开发期真实链路验证）。
- **报告**：`PHASE31_2_AUTONOMOUS_TASK_REPORT.md`（本文件）。
- **Memory**：`/Users/yaowei/WorkBuddy/Claw/.workbuddy/memory/MEMORY.md` + `2026-08-15.md`。

## 38. Boundary（架构红线守约）

- Capability 层不直接执行系统命令 / 终端 / 浏览器 / 产生真实 execution handle。
- 不绕过 Orchestrator / ExecutionSandbox；不新建第二执行引擎。
- 不 `new Agent()` 作为能力调用；不注入 worker/tool/toolRegistry/orchestrator/agentRegistry/messageRouter。
- 未修改 `core/execution` / `core/orchestrator` / `core/sandbox` 核心。
- 唯一真实执行权 = Orchestrator → ExecutionSandbox；本层（Pipeline / AutonomousTask / Task Runtime / Component）只计划/描述/编排/生成纯数据/接收结果/retry/replan/判定收敛。

## 39. Final Verdict

七道 Gate 全绿 + Round 2 复现全绿 + test:all EXIT 0 + 0 FAIL + Execution Token=0 + External Dependency=0 + Violation=0 + Structural PASS + Runtime PASS + Zero Authority PASS + main.js EXIT 0 + 报告完成 + MEMORY 完成。

**Phase 31.2 自主任务执行与恢复层验收通过。**

## 40. STOP Declaration

```
PHASE_31_2_COMPLETE = true
STOP_AT_PHASE_31_2 = true
```

严格停止：不进入 Phase 31.3，不提前设计 31.3，不创建 31.3 文件/测试/架构。
