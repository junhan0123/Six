---
id: know-phase-28-4-automation-workflow-capability
type: concept
---
# Phase 28.4 Automation & Workflow Capability 验收报告

> 能力编排层 —— 把既有能力（research / web / computer / vision / document / data）组合成真实工作流。
> 严格零执行权红线；唯一真实执行链 `Orchestrator → ExecutionSandbox`；复用 Phase 16 Workflow Engine，不重造第二引擎。

---

## 1. 验收概要

- **能力层**：Automation & Workflow Capability（能力编排层）
- **目标**：将 Phase 25–28.3 的 6 类既有能力编排成可审批、可恢复、可产物化的真实工作流
- **核心约束**：`Workflow ≠ Executor`；编排层自身 `hasExecutionAuthority() === false`；只生成纯数据执行请求，真实执行唯一经 `Orchestrator → ExecutionSandbox`
- **验收结论**：7 道 Gate 双次复现（轮 1 全 7 闸 / 轮 2 重跑 1·2·3·5·6·7）全绿；外部依赖保持 0（`PAIOS_MODEL=heuristic`）
- **本阶段严格止于 Phase 28.4**，未进入 28.5

## 2. 基线对比（Phase 28.3 → 28.4）

| 真源指标 | 前置基线 | 本阶段后 | Δ |
|---|---|---|---|
| `package.json` 版本 | 0.34.0 | **0.35.0** | +1 |
| EventBus 唯一事件常量 | 418 | **432** | +14（`Automation*` 事件） |
| `test:all` 套件段数 | 42 | **43** | +1（末端 `phase28_4_automation_test.js`） |
| 外部依赖 | 0 | **0** | 不变（`PAIOS_MODEL=heuristic`） |

## 3. 架构红线（6 条，全程未破）

1. **Workflow ≠ Executor**：编排层不 spawn / exec / fork / shell / child_process，不直接写文件、不直接出网、不直接键鼠、不直接调 Sandbox 内部
2. **编排层零执行权**：`AutomationWorkflow.hasExecutionAuthority() === false`；`acquireExecutionHandle` / `performExecution` 必须不存在或抛 `ForbiddenInjectionError`
3. **能力层只经 Contract / Registry 调用**：禁止 `new ComputerAgent()` 之类的能力 Agent 实例化；只持有契约元数据
4. **复用 Phase 16 Workflow Engine**：`AutomationWorkflow` 组合 `Workflow` 实例，委托其 DAG / 调度 / 恢复 / 审批；不另造第二引擎
5. **不改 Phase 25–28.3 既有能力内部实现**：本阶段只新增 `core/automation/`，不触碰 research/web/computer/vision/document/data 源码
6. **外部依赖保持 0**：无新增 npm 包，离线 Provider 仅按元数据确定性合成纯数据

## 4. 目录与文件清单（`core/automation/` 共 18 源文件）

```
core/automation/
├── index.js          # 权威零执行权声明 + 汇总导出 + verifyAutomationZeroAuthority
├── workflow.js       # AutomationWorkflow（中枢，组合 Phase 16 Workflow）
├── step.js           # AutomationStep（复用 WorkflowStep 生命周期 + 能力编排字段）
├── planner.js        # AutomationPlanner（目标 → WorkflowPlan，纯数据）
├── runner.js         # AutomationRunner（只生成请求，绝不执行）
├── registry.js       # CapabilityRegistry（契约索引，不实例化能力 Agent）
├── capability.js     # CapabilityContract + 内置 6 类能力契约
├── context.js        # AutomationContext（纯数据上下文）
├── state.js          # AutomationState（13 态状态机）
├── condition.js      # 条件求值（纯数据确定性）
├── graph.js          # DAG 分析（环检测 / 拓扑 / 就绪集 / 分支）
├── constants.js      # 状态 / 转移 / 禁注键 / 请求类型常量
├── result.js         # 自动化结果（纯数据，函数净化）
├── delivery.js       # ArtifactPipeline（产物描述符管线，仅引用不二进制）
├── approval.js       # AutomationApproval（审批闸）
├── recovery.js       # AutomationRecovery（只改状态不执行）
├── policy.js         # AutomationPolicy（策略）
└── error.js          # 编排层错误类（ForbiddenInjectionError / ApprovalRejectError 等）
```
`AUTOMATION_MODULE_COUNT = 18`（含 `constants.js`）。

## 5. 模块职责总览

| 模块 | 职责 | 零执行权 |
|---|---|---|
| AutomationWorkflow | 编排中枢，组合 Phase 16 Workflow，物化计划 / 审批 / 运行 / 回收 | 恒 false |
| AutomationStep | 单步，复用 WorkflowStep 生命周期 + capability/action/input/risk/approvalRequired | 恒 false |
| AutomationPlanner | 把步骤定义物化为 WorkflowPlan（纯数据） | 恒 false |
| AutomationRunner | 生成 CapabilityRequest / ExecutionRequest（只描述不执行） | 恒 false |
| CapabilityRegistry | 契约索引；`validateRequest` 纯数据校验；不实例化能力 Agent | 恒 false |
| AutomationState | 13 态状态机；`assertNoAutomationInjected` 注入硬闸 | 恒 false |
| Condition | 条件求值（field/op/value 纯数据确定性） | 纯函数 |
| Graph | 环检测 / 拓扑排序 / 就绪集 / 条件分支 / 失败分支 | 纯函数 |
| ArtifactPipeline | 产物描述符收集（仅 `artifact://` 引用，杜绝二进制泄漏） | 纯数据 |
| Approval/Recovery/Policy | 审批闸 / 恢复（只改状态）/ 策略 | 恒 false |

## 6. 零执行权铁律（设计层）

编排层在任何层级都不持有执行权：
- 模块级 `hasExecutionAuthority()` 全部返回 `false`（capability / registry / result / delivery / runner / planner 6 个子模块）
- 所有类实例 `hasExecutionAuthority() === false`
- `AutomationWorkflow.acquireExecutionHandle()` / `performExecution()` 抛 `ForbiddenInjectionError`
- 执行令牌 `executionToken` 恒为 0（即使经审批发放，也只在 Orchestrator → Sandbox 侧生效，编排层自身仍 0）

## 7. hasExecutionAuthority 全链路恒 false

`verifyAutomationZeroAuthority()` 校验：
- 6 个子模块模块级 `hasExecutionAuthority()` 全部 `=== false`
- 11 类实例（wf/step/ctx/policy/approval/recovery/runner/planner/registry/pipeline/state）全部 `=== false`
- 层级权威声明 `hasExecutionAuthority()`（来自 `index.js`）返回 `false`，遮蔽各子模块 star 同名导出

## 8. acquireExecutionHandle / performExecution 抛错

`AutomationWorkflow` 不提供执行入口：
```js
acquireExecutionHandle() { throw new ForbiddenInjectionError(["acquireExecutionHandle"]); }
performExecution()      { throw new ForbiddenInjectionError(["performExecution"]); }
```
自证：对两方法逐一调用，均抛错（`threw === 2`）；且 `wf.executionToken === 0`。

## 9. 执行令牌恒为 0

构造期 `this.executionToken = 0`。`requestApprovals()` 无审批点时虽发放 `token=1`，但仅表示「经审批后可在 Orchestrator → Sandbox 侧执行」，编排层自身 `hasExecutionAuthority()` 仍为 `false`。`dryRun()` 不创建 Token（`token=0`、不生成 ExecutionRequest）。

## 10. 唯一真实执行链

```
用户目标 → AutomationWorkflow.plan() → 契约校验 → 审批闸 → run() 生成纯数据 ExecutionRequest
         →（描述 target: "orchestrator.submitExecutionRequest"）→ 调用方外部交接
         → Orchestrator → ExecutionSandbox（唯一真实执行权在此落地）
         → recordStepResult() 回收外部执行结论
```
编排层只生成「请求」，从不触发执行；`Runner` 不持有 `orchestrator`、不调用 `submitExecutionRequest`。

## 11. 复用 Phase 16 Workflow Engine

- `AutomationWorkflow` 内部持 `this.wf = new Workflow({...})`，委托其 DAG 调度 / 恢复 / 审批 / 度量
- `AutomationStep extends WorkflowStep`，复用其 `CREATED/READY/RUNNING/BLOCKED/COMPLETED/FAILED/SKIPPED` 生命周期
- `AutomationPlanner` 复用 `WorkflowPlanner.decompose` 做依赖分析
- `AutomationRunner` 复用 `WorkflowScheduler`（DEPENDENCY 策略）+ `analyzeGraph`
- 不另造第二引擎，避免状态机漂移与执行权边界歧义

## 12. AutomationStep 设计

复用 `WorkflowStep` 生命周期，叠加编排专属字段（纯数据）：
- `capability / action / input / dependsOn / condition / risk / approvalRequired / retryPolicy`
- `conditionPasses(context)` 纯数据确定性求值
- `hasExecutionAuthority()` 恒 false
- `input` 经 `pureWorkflowCopy` 净化（函数 → null），杜绝可执行对象泄漏

## 13. AutomationWorkflow 设计

中枢编排器，关键方法：
- `addStep(def)`：先经 `registry.has(capability)` 契约校验，再物化到 Phase 16 引擎（`CapabilityNotFoundError` 拦截未注册能力）
- `addDependency({from,to})`：显式建图边（注意 `addStep({dependsOn})` 只在 step 上记录依赖、不建边，必须经 `addDependency` 或 `plan()` 物化）
- `plan(goal, {steps})`：经 `AutomationPlanner.plan()` 物化步骤 + 依赖，环检测后进入 `planned`
- `requestApprovals()`：有审批点 → `awaiting_approval`；无 → 自动 `token=1` + `running`
- `grantApproval(id)` / `rejectApproval(id)`：全批准 → `running`+`token=1`；驳回 → `failed`+`token=0`（抛 `ApprovalRejectError`）
- `run(context)`：生成纯数据请求；`awaiting_approval` 不生成执行请求；返回 `{requests, executionRequests, approvalsRequired}`
- `dryRun(context)`：预测不执行、不创建 Token、不生成 ExecutionRequest
- `recordStepResult(stepId, result)`：回收外部执行结论（complete/skip/fail），触发 `_checkCompletion`
- `recover(stepId, strategy, ctx)`：只改状态不执行

## 14. 规划器 AutomationPlanner

- 输入：用户目标（纯数据）+ `opts.steps`（含 capability/action/dependsOn/condition/risk/approvalRequired）
- 输出 `WorkflowPlan`：`{ goal, steps[], dependencies[], estimatedRisks[], approvalPoints[], artifacts[] }`
- 复用 `WorkflowPlanner.decompose` 做依赖分析；按 `dependsOn` 物化图边
- 契约校验：未注册能力抛 `CapabilityNotFoundError`
- 零执行权：自身 `hasExecutionAuthority()` 恒 false

## 15. 运行器 AutomationRunner

- `generateRequests(wf, context, {approvedStepIds, executionToken})`：
  - 经 `analyzeGraph` 求就绪集；仅对就绪且（无需审批或已批准）步骤生成请求
  - `CapabilityRequest`（纯数据描述）+ `ExecutionRequest`（`executionToken > 0` 才生成；`target: "orchestrator.submitExecutionRequest"` 仅描述、Runner 自身不调用）
- `dryRun(wf, context)`：预测步骤 / 依赖 / 风险 / 审批点 / 产物，`executionRequests: []`、`token: 0`
- 零执行权：不持有 orchestrator、不调用 submitExecutionRequest、不触发任何执行

## 16. 契约注册表 CapabilityRegistry

- 构造期 `createBuiltinCapabilities()` 注册内置 6 类能力契约：`research / web / computer / vision / document / data`
- `validateRequest(req)`：纯数据校验（能力存在 + action 受支持 + inputSchema）
- **不实例化任何能力 Agent**（禁止 `new ComputerAgent()` 等），仅持有契约元数据
- 构造期 `assertNoWorkflowInjected` 注入硬闸

## 17. 状态机 AutomationState（13 态）

`AUTOMATION_STATE_LIST.length === 13`：
`created → planning → planned → ready → running → awaiting_approval → completed / failed / cancelled / blocked / paused / skipped`
- `completed → cancelled` 合法（含 allowed 转移），故 `completed` 非终态（`isFinal()` 对 completed 返回 false）
- `running → awaiting_approval` **非法**（仅 `planned/ready → awaiting_approval`）

## 18. 状态转移语义

- 合法进入 `awaiting_approval` 仅来自 `planned` / `ready`
- `grantApproval` 全批准 + 无驳回 → `running` + `token=1`
- `rejectApproval` → `failed` + `token=0`（抛 `ApprovalRejectError`）
- `_checkCompletion`：所有步骤终态 → `completed`（无失败）/ `failed`（有失败）；产物描述符仅引用不二进制

## 19. 审批闸 AutomationApproval

- `requestStepApproval(step, {type:"USER"})` 生成审批记录
- `grant(id)` / `reject(id)` 记录状态；`pending()` 返回待审批集
- 与 `AutomationWorkflow` 协作：`reject` 直接停机（`throw ApprovalRejectError`），绝不自我放行

## 20. 恢复 AutomationRecovery

- `recover(wf, stepId, strategy, ctx)`：只改状态不执行
- 策略受 `AutomationPolicy` 约束；恢复动作在 Phase 16 引擎侧完成，编排层不亲自执行

## 21. 产物管线 ArtifactPipeline

- `collect(steps)`：仅收集 `artifact://${capability}/${id}` 引用描述符
- 杜绝二进制 / 原始字节泄漏（与 Phase 28.2 Document 产物管线同源范式）

## 22. 条件分支 Condition

- `buildCondition` / `evaluateCondition(cond, context)`：纯数据确定性（field/op/value）
- 驱动 `graph.js` 的条件依赖（`DEPENDENCY_TYPES.CONDITIONAL`）；命中与否由上下文字段决定

## 23. DAG 图分析 Graph

- `analyzeGraph(wf, context)`：环检测（`hasCycle`）、拓扑排序、就绪集（`computeReady`）、条件分支（`evaluateConditionalBranches`）、失败分支（`computeFailureBranch`）
- `detectCycle` / `topologicalSort` 纯函数；环检测失败 `plan()` 直接抛错
- 错误用法纠正（测试阶段）：`addStep({dependsOn})` 不建边，必须显式 `addDependency`

## 24. 结果纯度 Result

- `createAutomationResult({output})`：函数型 output 经 `pureWorkflowCopy` 净化为 `null`（与 Workflow.js:40 同源），绝不保留可调用对象
- `isAutomationResult` / `resultIsSuccess` 纯数据判定
- `createFailedResult` 表达零交付失败结论

## 25. 事件体系（14 个 Automation* 事件）

EventBus 新增 14 个 `Automation*` 事件（418 → 432）：
`AutomationCreated / Planning / Planned / StepReady / StepRunning / StepCompleted / StepSkipped / StepFailed / ApprovalRequested / ApprovalGranted / ApprovalRejected / RecoveryStarted / Recovered / Completed`
- `AUTOMATION_EVENT_COUNT === 14`，与 `Object.keys(EVENTS).filter(k=>k.startsWith("Automation")).length === 14` 一致

## 26. EventBus 总览（432）

- EventBus 真源 `core/events/EventBus.js` 静态解析 `export const EVENTS = {...}` 唯一事件数 = **432**
- 其中 `Automation*` = 14；其余为既有 Phase 1–28.3 事件
- `AutomationWorkflow` 构造即广播 `AutomationCreated`；`_emit` best-effort（观察面失败不影响主链路）

## 27. Gate 1 —— 单元测试（PASS 64033 / FAIL 0）

- 文件：`phase28_4_automation_test.js`
- 结果：**PASS 64033 / FAIL 0**（共 **86 段**，~432–478ms）
- 覆盖：runner / workflow / delivery / result / verify-zero-authority / zero-authority-all-instances / injection-guard / cross-product-invariant（47500）/ cross-product-conditions（1500）/ cross-product-forbidden-keys（9600）/ cross-product-eventbus（300）/ cross-product-recovery（500）/ final-eventbus-count 等

## 28. Gate 2 —— 执行权扫描（Token/Dep/Violation = 0）

- 文件：`scripts/scan-automation-execution.js`
- 结果：**EXIT 0**；Module Count = 18、State Machine = 13 态、Automation Events = 14、EventBus Total = 432
- 零执行权扫描：注入令牌 / 依赖 / 违规 = 0

## 29. Gate 3 —— 一致性校验（check-consistency）

- `node scripts/check-consistency.js --fix` → EXIT 0
- `node scripts/check-consistency.js` → EXIT 0
- 派生点同步：版本号 / 事件总数 / 套件数 / 末端套件 / UI API 方法数 全部一致
- 版本锁定 **0.35.0**、套件数 **43**

## 30. Gate 4 —— test:all 接入（EXIT 0 / 43 套）

- `npm run test:all` → **EXIT 0** / 0 FAIL / 无退化
- 真源：version = 0.35.0、EventBus = 432、test:all 套件 = 43、末端套件 = `phase28_4_automation_test.js`
- 因 `&&` 链，末端套件运行即证明前 42 套全过；Phase 1–28.3 零回归

## 31. Gate 5 —— 冒烟测试（105 通过 / 0 失败）

- 文件：`scripts/automation-smoke.js`（镜像 `data-agent-smoke.js` 结构）
- 结果：**105 通过 / 0 失败**（共 **105 项 · 19 个场景**，EXIT 0）
- 场景覆盖：Plan / ContractGuard / StateMachine / Condition / Graph / Cycle / AutoApprove / ManualApprove / Reject / RunnerGenerate / DryRun / ArtifactPipeline / Result / Recovery / E2E / ZeroAuthority / InjectionReject / Events / ConditionalFailure
- 执行权归属 = `execution-sandbox`；AutomationWorkflow 零执行权恒 false

## 32. Gate 6 —— 多轮对话 E2E（PASS 181 / FAIL 0）

- 文件：`phase28_4_automation_conversation_e2e_test.js`（镜像 `phase28_3_data_conversation_e2e_test.js`）
- 结果：**PASS 181 / FAIL 0**（共 **12 段**，≥8 多轮 / ≥100 断言）
- 段落：MULTI-PLAN（6 轮规划）/ AUTO-APPROVE / MANUAL-APPROVE / REJECT-MIDWAY / EXTERNAL-EXEC / CONDITION-BRANCH / RECOVERY / STATEFUL（单 wf 4 轮推进）/ ZERO-AUTHORITY / EVENTS-RESILIENT / TEN-TURN（10 轮混合）/ INJECTION-GUARD
- 错误用法纠正：MANUAL-APPROVE 段手动 `grantApproval` 不重调 `requestApprovals`（避免 `running→awaiting_approval` 非法）；MULTI-PLAN 段直接 `wf.plan()` 不走 `run()`

## 33. Gate 7 —— main.js 演示（EXIT 0）

- 在 `main.js` 数据层演示之后、Phase 29.1 之前新增 `[自动化层演示]` 段
- 新增 import：`AutomationWorkflow / verifyAutomationZeroAuthority / hasExecutionAuthority(as automationHasExec) / AUTOMATION_AUTHORITY_HOLDER_NAME / AUTOMATION_STATE_LIST / AUTOMATION_EVENT_COUNT / AUTOMATION_FORBIDDEN_INJECTIONS`
- `PAIOS_MODEL=heuristic node main.js` → **EXIT 0**，输出：
  - `层级=automation | 规划=planned | 步骤=2 | 依赖=1 | 执行权=无（唯一属于 execution-sandbox）`
  - `审批闸 → status=running | 审批点=0 | executionToken=1 | 自动放行=是`
  - `运行（只生成请求）→ 请求总数=2 | 执行请求=1 | 目标能力=research | 自身执行权=false`（s2 document 经 DAG 门控于 s1 之后）
  - `结果回收 → 工作流终态=completed | 完成步骤=2/2 | 令牌仍=1`
  - `零执行权自证：通过 | 层执行权恒=false | 状态机=13 态 | Automation 事件=14 个 | 禁注键=51 类 | 广播事件=8 类`

## 34. 双次复现结果

| Gate | 轮 1 | 轮 2 |
|---|---|---|
| 1 单测 | PASS 64033 / 0（86 段）EXIT0 | PASS 64033 / 0（86 段）EXIT0 |
| 2 扫描 | Token/Dep/Viol=0 EXIT0 | Token/Dep/Viol=0 EXIT0 |
| 3 一致性 | --fix + check 均 EXIT0 | --fix + check 均 EXIT0 |
| 4 test:all | EXIT0 / 43 套 0 FAIL | （轮 2 依规范不重跑，轮 1 已证） |
| 5 冒烟 | 105/0（19 场景）EXIT0 | 105/0（19 场景）EXIT0 |
| 6 E2E | PASS 181 / 0（12 段）EXIT0 | PASS 181 / 0（12 段）EXIT0 |
| 7 main | EXIT0 + `[自动化层演示]` | EXIT0 + `[自动化层演示]` |

## 35. 性能与规模指标

- 单元测试 86 段 ~432–478ms；冒烟 105 项即时；E2E 12 段 ~9ms
- 跨产品不变量（cross-product-*）合计 63400 项确定性校验全过
- 零执行权自证项 7 类 invariants 全绿；禁注键 **51 类**

## 36. 与 Phase 25–28.3 能力层集成

- 编排层通过 `CapabilityRegistry` 引用既有 6 类能力**契约元数据**，不改动其源码
- 既有 `EventBus` 扩展 14 个 `Automation*` 事件，与 research/web/computer/vision/document/data 事件同总线广播
- `main.js` 演示段与数据层 / 视觉层 / 调研层 / computer 层演示同构（统一 `层级=… | 执行权=无（唯一属于 execution-sandbox）` 范式）

## 37. 外部依赖保持 0

- 无新增 npm 依赖；`PAIOS_MODEL=heuristic` 下全链路离线确定性
- `AutomationRunner` / `Planner` 不引入任何网络 / 沙箱 / 进程调用

## 38. 已知限制 / 边界

- `addStep({dependsOn})` 不建图边，必须显式 `addDependency` 或经 `plan()` 物化（已在测试与文档中明确）
- `completed` 非终态（因 `completed → cancelled` 合法），断言须用 `state.value === "completed"` 而非 `isFinal()`
- `running → awaiting_approval` 非法转移，手动审批须复用同一 wf 的 `grantApproval` 而非重调 `requestApprovals`
- DAG 门控下 `run()` 首批仅派发就绪步骤（如 s1 research），依赖步骤（s2 document）须待前驱回收后再派发

## 39. 验收结论

Phase 28.4 Automation & Workflow Capability 全部 7 道 Gate 双次复现（轮 1 全 7 闸 / 轮 2 重跑 1·2·3·5·6·7）**全绿**，零执行权红线 6 条全程未破，复用 Phase 16 Workflow Engine 未重造第二引擎，外部依赖保持 0。能力编排层可安全组合既有 6 类能力为真实、可审批、可恢复、可产物化的工作流，真实执行唯一经 `Orchestrator → ExecutionSandbox`。

## 40. 后续边界（严格止于 Phase 28.4）

本阶段**严格停在 Phase 28.4**，未自动进入 28.5。后续如需进入 28.5，应在新指令下基于本验收基线（version 0.35.0 / EventBus 432 / test:all 43 套）推进，并同样满足 6 条零执行权红线与双次复现纪律。
