---
id: know-phase-28-5-autonomous-orchestration-capability
type: concept
---
# Phase 28.5 —— 自主编排层（Autonomous Orchestration Capability）能力验收报告

> 报告生成时间：2026-08-13
> 项目：PersonalAIOS（Node.js / Electron AI 内核，version=0.35.0，kernelVersion=0.35.0）
> 定位：在 Phase 28.4（多能力组成 Workflow）之上，补齐「系统根据用户目标自主判断用哪些能力、如何组合、何时重规划、最终完成复杂任务」的能力 —— 即 **Autonomous Task Loop**。
> 验收结论：**Phase 28.5 七道 Gate 全部通过，且轮 1 / 轮 2 复现一致。严格停在 Phase 28.5，未自动进入 28.6。**

---

## 一、文档概述与执行摘要（Executive Summary）

Phase 28.5 解决的核心问题：Phase 28.4 已经能把既有能力（research/web/computer/vision/document/data）组合成工作流，但「由谁来决定用哪些能力、按什么顺序、何时重规划、何时交付、何时停机等人」仍由外部调用方硬编码。Phase 28.5 引入**自主编排层（Orchestration Layer）**，让系统对用户目标自主完成「理解 → 选择 → 规划 → 运行 → 观察 → 评估 → 重规划 → 交付」的闭环。

本层是 Phase 28.4 之上的「大脑」，但**始终不持有任何执行权**。唯一真实执行链仍是 `Orchestrator → ExecutionSandbox`；编排层只生成纯数据 `OrchestrationResult` / 纯数据 `ExecutionRequest`（仅描述）/ 纯数据 `Delivery`（仅引用）。

验收维度：枚举完整性、状态机正确性、零执行权硬自证、跨产品大规模交叉断言、集成冒烟、多轮对话 e2e、运行时端到端演示，共 7 道 Gate，全部 PASS。

---

## 二、Phase 28.5 定位与 Autonomous Task Loop 定义

自主编排闭环（Autonomous Task Loop）路径：

```
Goal → Understand → Select → Plan → Run → Observe → Evaluate
     →（needs_replan）→ Replan → Plan …
     →（success / partial_success）→ Deliver → Done
     →（failed / requires_human / cancelled）→ Blocked
```

- **Understand**：`understandGoal` 把自由文本解析为结构化 `OrchestrationGoal`（意图 / 优先级 / 约束 / 成功标准）。
- **Select**：`OrchestrationSelector` 依据关键词启发式 + `CapabilityRegistry` 选择能力序列（只引用既有能力，绝不 `new Agent()`）。
- **Plan**：`OrchestrationPlanner` 复用 Phase 28.4 的 `AutomationWorkflow` 物化为 planned 态工作流。
- **Run**：由注入的确定性 provider 在离线测试中模拟「外部执行链」回传结论（真实运行时不使用 provider，结论来自真实 Sandbox）。
- **Observe / Evaluate / Replan / Deliver**：纯数据观察、纯函数评估、失败能力兜底重规划、纯数据交付。

---

## 三、七条最高红线（不可逾越）

1. **唯一真实执行入口**：`Orchestrator → ExecutionSandbox`，禁止在编排层建立第二执行入口。
2. **编排层零执行权**：所有 Orchestration 类 `hasExecutionAuthority() === false`；`acquireExecutionHandle()` / `performExecution()` 必须抛错或不存在。
3. **禁止执行原语**：禁止 `child_process / exec / spawn / fork / shell / terminal / direct network / filesystem / browser / computer / sandbox` 等。
4. **禁止绕过能力注册**：禁止 `new ResearchAgent()` / `new ComputerAgent()` …，能力必须只经 `CapabilityRegistry → CapabilityContract → AutomationWorkflow`。
5. **禁止改动核心执行组件**：禁止修改 `ExecutionSandbox / Orchestrator / Authorization / ApprovalManager` 核心逻辑。
6. **禁止重造引擎**（红线 6 复用纪律）：禁止新建第二套 Planner / Workflow Engine / Task Manager / Memory Engine，必须先复用 `core/cognition/`、`core/autonomy/`、`core/autonomy/workflow/`、`core/automation/`、`core/memory/`。
7. **禁止引入外部测试框架**：禁止引入 Jest / Vitest / Playwright / Puppeteer / 第三方引擎 / 框架，继续用现有 `core/test/Harness.js`。

---

## 四、七道验收 Gate 总览

| Gate | 验收物 | 通过标准 | 轮1 | 轮2 |
|------|--------|----------|-----|-----|
| Gate 1 | `phase28_5_orchestration_test.js` | ≥35000 断言 / ≥70 段 / 0 FAIL | PASS 48983 / FAIL 0（82 段） | PASS 48983 / FAIL 0 |
| Gate 2 | `scripts/scan-orchestration-execution.js` | Token/Dep/Violation=0 | 全 0 / EXIT 0 | 全 0 / EXIT 0 |
| Gate 3 | `check-consistency --fix` + `check` | 派生点与真源一致 / EXIT 0 | 一致 / EXIT 0 | 一致 / EXIT 0 |
| Gate 4 | `test:all`（接入编排套件） | 44 套 / EXIT 0 / 无退化 | EXIT 0 | EXIT 0 |
| Gate 5 | `scripts/orchestration-smoke.js` | ≥20 场景全 PASS | 22 场景 / 107 检查 / 0 FAIL | 一致 |
| Gate 6 | `phase28_5_orchestration_conversation_e2e_test.js` | ≥12 多轮 / ≥150 断言 / 0 FAIL | 13 段 / 159 断言 / 0 FAIL | 一致 |
| Gate 7 | `main.js` 演示 + `PAIOS_MODEL=heuristic node main.js` | [自主编排层演示] + EXIT 0 | 打印 / EXIT 0 | EXIT 0 |

---

## 五、架构总览：自主编排层在系统中的位置

```
用户目标
   │
   ▼
OrchestrationAgent（门面，只编排不执行）
   │
   ├─ OrchestrationLoop（自主闭环：11 态状态机）
   │     ├─ understandGoal          → OrchestrationGoal（复用 core/autonomy/GoalModel）
   │     ├─ OrchestrationSelector   → 只经 CapabilityRegistry
   │     ├─ OrchestrationPlanner    → 复用 AutomationWorkflow（Phase 28.4 / Phase 16 引擎）
   │     ├─ OrchestrationObserver   → 收集执行回报（纯数据）
   │     ├─ OrchestrationEvaluator  → 6 outcome 纯函数判定
   │     ├─ OrchestrationReplanner → 失败能力兜底（computer→web）
   │     ├─ OrchestrationRecovery   → 复用 AutomationRecovery（5 策略）
   │     ├─ OrchestrationBudget     → 资源预算记账
   │     └─ OrchestrationDecision   → 复用 DecisionEngine（core/cognition）
   │
   ▼ 生成纯数据 ExecutionRequest（仅描述）
Orchestrator → ExecutionSandbox（唯一真实执行链，由 provider 离线模拟）
   │
   ▼ 回传纯数据结论
OrchestrationLoop 回收 → createOrchestrationResult（纯数据）→ createDelivery（纯数据引用）
```

---

## 六、核心闭环：OrchestrationLoop 状态机（11 态 / 11 迁移）

- 11 态：`INIT / UNDERSTAND / SELECT / PLAN / RUN / OBSERVE / EVALUATE / REPLAN / DELIVER / DONE / BLOCKED`。
- 合法迁移表 `ORCHESTRATION_LOOP_TRANSITIONS`：`INIT→UNDERSTAND`、`UNDERSTAND→SELECT`、`SELECT→PLAN`、`PLAN→RUN`、`RUN→OBSERVE`、`OBSERVE→EVALUATE`、`EVALUATE→{DELIVER,REPLAN,BLOCKED}`、`REPLAN→PLAN`、`DELIVER→DONE`；`DONE`/`BLOCKED` 为终态（无出边）。
- 合法迁移总数 = **11**；迁移表被 `Object.freeze` 冻结（对象浅冻结，内层数组不可变语义由 `assertOrchestrationTransition` 强制）。
- `OrchestrationLoop` 无 `acquireExecutionHandle` / `performExecution` 方法（红线 1/2 双重保证）。

---

## 七、目标理解：understandGoal + OrchestrationGoal

- `understandGoal(text)` 返回 `{ goal, understanding }`；`OrchestrationGoal` 复用 `core/autonomy/GoalModel.createGoal`。
- 意图启发式（`GOAL_INTENTS`）：`CREATE / ANALYZE / OPTIMIZE / MAINTAIN / LEARN`，值为**大写**（如 `GOAL_INTENTS.CREATE === "CREATE"`）。
- 优先级（`GOAL_PRIORITIES`）：`CRITICAL / HIGH / MEDIUM / LOW`，默认 `MEDIUM`。
- 约束检测：`plan-only / requires-approval / high-risk-caution / offline`。

---

## 八、能力选择：OrchestrationSelector（只经 CapabilityRegistry）

- `CAPABILITY_KEYWORDS`：research / web / computer / vision / document / data 六类关键词（连续子串匹配，如「操作界面」「简报」）。
- `select(goal)` 返回 `{ selection, steps }`，`selection.capabilities` 为有序能力列表，仅引用 `CapabilityRegistry` 既有契约。
- 无关键词命中时兜底选 `research`。
- 绝不 `new ComputerAgent()` / `new ResearchAgent()`（红线 4）。

---

## 九、规划：OrchestrationPlanner（复用 AutomationWorkflow）

- 复用 Phase 28.4 的 `AutomationWorkflow` + `AutomationPlanner`（其底层复用 Phase 16 Workflow Engine），不重造规划器（红线 6）。
- `plan(goal, steps)` 产出 `{ workflow, plan }`，`workflow.state.value === "planned"`。
- 产出纯数据 `WorkflowPlan`（`hasFunctionDeep === false`）。

---

## 十、观察：OrchestrationObserver

- `observe(wf)` 把 `AutomationWorkflow` 步骤状态收拢为结构化观察数组（stepId / capability / action / status / risk / output / observedAt）。
- 复用既有工作流快照，不重造观察引擎（红线 6）。

---

## 十一、评估：OrchestrationEvaluator（6 outcome 纯函数）

- `ORCHESTRATION_OUTCOMES`：`SUCCESS / PARTIAL_SUCCESS / FAILED / BLOCKED / NEEDS_REPLAN / REQUIRES_HUMAN`。
- `evaluate(observations, { goal, budget, replansUsed, awaitingApproval })` 为纯函数判定：全完成→success；部分失败且有预算→needs_replan；全失败无预算→failed/partial；无观察→blocked；等待审批→requires_human。
- 不重造评估引擎。

---

## 十二、重规划：OrchestrationReplanner（computer→web 兜底）

- `FALLBACK_CAPABILITY`：`computer→web→research→data→vision→document→research`。
- `replan(previousSteps, observations)` 保留成功步骤，对失败步骤施加兜底能力；新步携带 `replannedFrom`。
- `DEFAULT_MAX_REPLANS = 3`。

---

## 十三、恢复：OrchestrationRecovery（复用 AutomationRecovery 5 策略）

- 复用 Phase 28.4 `AutomationRecovery`（底层映射到 Phase 16 WorkflowRecovery 5 策略），不重造（红线 6）。
- `recommend(step, error)`：timeout→RETRY、not found/404→FALLBACK、permission→ABORT、HIGH risk→REPLAN、默认→RETRY。
- `recover(workflow, stepId, strategy, ctx)` 只改状态不执行。

---

## 十四、预算：OrchestrationBudget

- 上限：maxSteps=24、maxReplans=3、maxRetries=6、maxSources=20、maxWorkflowDepth=8、maxExecutionRequests=48。
- `canReplan(replansUsed)` 决定闭环能否继续重规划；`consumeStep / consumeReplan / consumeExecutionRequest` 纯记账。

---

## 十五、决策：OrchestrationDecision（复用 DecisionEngine）

- 复用 Phase 7.1 `DecisionEngine`（`core/cognition/DecisionEngine.js`），不重造决策引擎（红线 6）。
- `decide(observation)` 返回纯数据建议数组后闭嘴；编排层只消费建议，绝不自行执行。

---

## 十六、结果：OrchestrationResult（纯数据，零执行权）

- `createOrchestrationResult` 产出 `{ goalId, objective, intent, status, capabilities, steps, artifacts, summary, replansUsed, executionAuthority:false }`。
- `assertResultPurity` 硬闸拒绝任何执行句柄字段；`isOrchestrationResult` 判定 `executionAuthority===false` 且 capabilities/steps 为数组。
- `OrchestrationResult` 类实例 `hasExecutionAuthority() === false`。

---

## 十七、交付：createDelivery（纯数据引用）

- `ORCHESTRATION_DELIVERY_CHANNELS`：`IN_MEMORY / EVENT_BUS / ARTIFACT_REF`（值分别为 `in_memory / event_bus / artifact_ref`）。
- `createDelivery({ channel })` 将 `o.channel` 当作**键**查表（如 `"EVENT_BUS"` → `"event_bus"`），仅描述渠道，不实际发送/写入。
- `isDelivery` 判定 `executionAuthority===false` 且 `channel` 为字符串。

---

## 十八、确定性 Provider：DeterministicOrchestrationProvider

- 离线确定性「外部执行链」模拟器，站在 Orchestrator→Sandbox 交接位置，回传纯数据结论。
- `{ failCapabilities: Set }` 让指定能力确定性失败（用于触发重规划验证）。
- `execute(requests)` 纯合成 `output`，自身 `hasExecutionAuthority() === false`。
- 真实运行时不使用本类；结论来自真实 Sandbox 回传。

---

## 十九、编排门面：OrchestrationAgent（executeGoal）

- `executeGoal(goalInput, opts)` 默认 `new DeterministicOrchestrationProvider` 驱动 `OrchestrationLoop.run`，返回纯数据 `OrchestrationResult`。
- `toJSON()` 暴露 `{ policy, budget, loop, executionAuthority:false }`。
- 构造期 `assertNoOrchestrationInjected` 拒绝一切执行组件（红线 3）。

---

## 二十、18 个模块清单与职责

`core/orchestration/` 共 **18** 个源文件（按字母序）：

`agent.js` · `budget.js` · `constraints.js` · `context.js` · `decision.js` · `delivery.js` · `evaluator.js` · `goal.js` · `index.js` · `loop.js` · `observer.js` · `planner.js` · `policy.js` · `provider.js` · `recovery.js` · `replanner.js` · `result.js` · `selector.js`

- `index.js`：统一导出 + `verifyOrchestrationZeroAuthority()` 硬自证 + 权威零执行权声明（`ORCHESTRATION_MODULE_COUNT=18`、`ORCHESTRATION_AUTHORITY_HOLDER_NAME="execution-sandbox"`）。
- 每个模块均导出 `*HasExec` 模块级零执行权函数，供逐模块断言。

---

## 二十一、零执行权硬自证：verifyOrchestrationZeroAuthority

`verifyOrchestrationZeroAuthority()` 校验项（`checked=10`）：
1. 所有模块级 `hasExecutionAuthority()` 为 false；
2. 所有类实例 `hasExecutionAuthority() === false`；
3. Orchestration* 事件数 = 16；
4. 循环状态机态数 > 0；
5. 合法迁移总数 > 0；
6. 禁止注入键非空；
7. 循环拒绝执行入口（无 acquire/perform 方法）；
8. 上下文拒绝执行句柄注入；
9. 结果纯度（executionAuthority=false 且无执行句柄字段）；
10. 确定性 provider 零执行权 + 纯数据模拟。

返回 `{ ok:true, moduleCount:18, checked:10, failures:[], authorityHolder:"execution-sandbox" }`。

---

## 二十二、执行权归属与唯一真实执行链

- `ORCHESTRATION_AUTHORITY_HOLDER = "execution-sandbox"`（唯一可持执行权的组件）。
- 编排层所有 `hasExecutionAuthority()` 恒返回 `false`；`toJSON()` / `createOrchestrationResult` 均显式暴露 `executionAuthority:false`。
- 唯一真实执行链：`Orchestrator → ExecutionSandbox`；编排层只生成纯数据请求，由外部回传结论。

---

## 二十三、禁止注入键（37 类）与构造期硬闸

- `ORCHESTRATION_FORBIDDEN_INJECTION_KEYS` 共 **37** 个（比 automation 层更严格），含：`exec / executionHandle / executionToken / terminal / process / childProcess / browser / computer / sandbox / orchestrator / submitExecutionRequest / spawn / fork / dispatch / browserExecutor / computerExecutor / sandboxClient / executionClient` 等。
- `assertNoOrchestrationInjected(obj, label)` 在**构造期与写入期**扫描顶层键，命中即抛错。
- 确认项：`new OrchestrationContext({executionHandle})` / `new OrchestrationGoal({exec})` / `new OrchestrationLoop({orchestrator})` / `new OrchestrationAgent({sandbox})` 均被拦截。

---

## 二十四、事件体系：16 个 Orchestration* 事件 + EventBus 总数 448

- 编排层新增 **16** 个 `Orchestration*` 事件（`ORCHESTRATION_EVENT_NAMES`）：`OrchestrationGoalCreated / UnderstandingCompleted / CapabilitiesSelected / PlanningStarted / PlanningCompleted / Started / StepObserved / EvaluationCompleted / ReplanRequested / Replanned / ApprovalRequested / Completed / PartialSuccess / Failed / RequiresHuman / Cancelled`。
- `EventBus` 真源总数 = **448**（编排层 16 + Web 12 + 其它既有 420，累计无退化）。
- `ORCHESTRATION_EVENT_COUNT = 16`。

---

## 二十五、复用既有基础设施（红线 6 合规）

- 工作流/规划/恢复：复用 `core/automation/`（AutomationWorkflow / AutomationPlanner / AutomationRecovery / CapabilityRegistry）。
- 认知决策：复用 `core/cognition/DecisionEngine.js`。
- 目标模型：复用 `core/autonomy/GoalModel.js`。
- 状态机基座与禁止键：`core/orchestration/constraints.js` 集中定义，不重造第二套。
- 测试：复用 `core/test/Harness.js`，未引入任何第三方测试框架（红线 7）。

---

## 二十六、Gate 1：phase28_5_orchestration_test.js

- 结果：**PASS 48983 / FAIL 0（共 82 段，~311ms）**，满足 ≥35000 断言 / ≥70 段 / 0 FAIL。
- 覆盖：枚举区（23+ section）、循环状态机矩阵、各子组件语义、零执行权自证、大规模交叉断言（如 `cross-product-instances` 39000×13、`cross-product-forbidden-keys` 200×37、`cross-product-policy-modes` 400×3、eventbus 300 等）。
- 复跑一致性：轮 1 / 轮 2 均为 48983 / 0。

---

## 二十七、Gate 2：scan-orchestration-execution.js

- 结果：**Execution Token = 0 / External Dep = 0 / Violation = 0 / Structural = PASS / Runtime Invariant = PASS / Module Count = 18 / Orchestration Events = 16 / EventBus Total = 448 / EXIT = 0**。
- 扫描目录 `core/orchestration`；`EXPECTED_ORCHESTRATION_FILES` 18 名；`verifyRuntimeInvariants()` 调 `verifyOrchestrationZeroAuthority()` + 17 个 `*HasExec` + 结果纯度 + 循环拒绝执行入口 + 上下文拒绝注入 + 16 事件 + 448 总数。
- HANDOFF_TOKENS 严格零引用：`submitExecutionRequest / orchestrator. / executionHandle / sandboxHandle / new XxxAgent`。

---

## 二十八、Gate 3：check-consistency（真源同步 + 派生点一致）

- `--fix` 自动同步前会话遗留的 14 处版本派生点（含 phase 测试内 `eq(Object.keys(EVENTS).length, N)` / `eq(suites, N)` / 末端套件断言等），EXIT 0。
- 后续 `check-consistency`（无参）校验全部派生点与真源一致：EventBus=448、test:all=44、末端套件=phase28_5_orchestration_test.js、UI API=24。输出「✓ 全部派生点与真源一致」，EXIT 0。
- 轮 1 / 轮 2 一致。

---

## 二十九、Gate 4：test:all（44 套接入，无退化）

- `test:all` 已将 `phase28_5_orchestration_test.js` 接入，由 43 → **44** 套。
- 运行结果：**EXIT 0，全部 44 套 0 FAIL，无退化**。
- `pretest:all` 先跑 `check-consistency`（Gate 3 无参）亦 EXIT 0。

---

## 三十、Gate 5：orchestration-smoke.js（≥20 场景）

- 结果：**22 个场景 / 107 项检查 / 0 失败 / EXIT 0**（满足 ≥20 场景全 PASS）。
- 覆盖：目标理解、上下文分区、策略矩阵、选择器、规划器、观察者、评估器、重规划器、恢复器、预算、决策、结果、交付、确定性 provider、循环状态机、三路径闭环（success / fail+replan / manual）、Agent 纯数据结果、零执行权自证、构造期注入拦截、循环拒绝执行入口、事件广播、状态机全矩阵。
- `check(name, ok, detail)` + `process.exit(failed===0?0:1)` 模式。

---

## 三十一、Gate 6：conversation e2e（≥12 多轮 / ≥150 断言）

- 结果：**13 个多轮对话段 / 159 断言 / 0 FAIL / EXIT 0**（满足 ≥12 多轮 / ≥150 断言 / 0 FAIL）。
- 段：`28-ORCH-E2E-MULTI-PLAN`、`AUTO-APPROVE`、`MANUAL-APPROVE`、`FAIL-REPLAN`、`EXTERNAL-EXEC`、`CAPABILITY-SELECT`、`POLICY-MATRIX`、`RECOVERY`、`STATEFUL`、`ZERO-AUTHORITY`、`EVENTS-RESILIENT`、`TEN-TURN`、`INJECTION-GUARD`。
- 每轮校验不变量：结果 `executionAuthority===false`、capabilities 非空数组、EventBus 总数 448、执行权恒归 execution-sandbox、产物仅 `artifact://` 引用。

---

## 三十二、Gate 7：main.js [自主编排层演示] + PAIOS_MODEL=heuristic

- 在 `main.js` 的 Phase 28.4 自动化演示段之后新增「[自主编排层演示]」段，沿用 `verifyAutomationZeroAuthority` 同款风格，含 ≥10 要素：`OrchestrationAgent` 实例化 → `executeGoal("调研 AI 监管并产出简报")` → 选用能力 research+document / 状态 success / 执行权无 → 失败重规划（computer→web，replansUsed=1）→ MANUAL 策略 → `verifyOrchestrationZeroAuthority()`（模块数 18 / 16 事件 / 37 禁注键 / 广播事件 17 类），全程打印 `executionAuthority=false`。
- 运行 `PAIOS_MODEL=heuristic NODE_OPTIONS="" node main.js`：**EXIT 0**，演示段正确打印且未破坏既有 600 行演示流水线。
- 轮 1 / 轮 2 一致。

---

## 三十三、双轮复现一致性

- 轮 1（全 7 Gate）与轮 2（重跑 1·2·3·5·6·7）结果完全一致：
  - Gate 1：48983 / 0（82 段）两轮回测一致；
  - Gate 2：Token/Dep/Violation 全 0、EXIT 0；
  - Gate 3：`check-consistency` 派生点一致、EXIT 0；
  - Gate 5：107/0、22 场景；
  - Gate 6：159/0、13 段；
  - Gate 7：演示打印 + EXIT 0。
- Gate 4（test:all 44 套）在轮 1 已一次性验证 EXIT 0、无退化。

---

## 三十四、与 Phase 28.4 能力编排层的关系

- Phase 28.4 = 「能力编排」：把既有能力组合成真实工作流（规划 → 契约校验 → 条件分支 → 审批闸 → 生成纯数据执行请求 → 产物管线），`AutomationWorkflow` 零执行权。
- Phase 28.5 = 「自主编排」：在 Phase 28.4 之上加「大脑」，自主判断**用哪些能力 / 如何组合 / 何时重规划 / 何时交付**。
- 依赖方向单向：Orchestration → Automation（`OrchestrationPlanner` 复用 `AutomationWorkflow`、`OrchestrationRecovery` 复用 `AutomationRecovery`），绝不发生反向依赖或第二执行入口。

---

## 三十五、结论与边界声明：严格停在 Phase 28.5

- **Phase 28.5 自主编排层能力已完整验收，七道 Gate 全部通过且双轮复现一致。**
- **严格停在 Phase 28.5 —— 未自动进入 28.6。** 本会话未新增 28.6 相关规划、代码或测试；所有产物（18 模块、3 个新测试/扫描文件、main.js 演示段、package.json 接线）均服务于 28.5 验收收口。
- 零执行权纪律在 7 条红线约束下全程保持：编排层 `hasExecutionAuthority()` 恒为 false，唯一真实执行链 `Orchestrator → ExecutionSandbox` 未被改动、未被绕过。

---

## 附录 A：本次新增/修改产物清单

- **新增** `scripts/orchestration-smoke.js`（Gate 5，22 场景 / 107 检查）。
- **新增** `phase28_5_orchestration_conversation_e2e_test.js`（Gate 6，13 段 / 159 断言）。
- **修改** `main.js`：引入 `core/orchestration/index.js` 导出 + 新增「[自主编排层演示]」段（Gate 7）。
- （前会话已建，本会话沿用并验证）`core/orchestration/` 18 模块、`phase28_5_orchestration_test.js`（Gate 1）、`scripts/scan-orchestration-execution.js`（Gate 2）、`package.json` 4 个 gate script + `test:all` 44 套接线。

## 附录 B：关键客观指标速查

| 指标 | 值 |
|------|----|
| 编排层模块数 | 18 |
| Orchestration* 事件 | 16 |
| EventBus 总数 | 448 |
| 循环态 / 合法迁移 | 11 / 11 |
| 禁止注入键 | 37 |
| 上下文分区 | 13 |
| Gate 1 / 2 / 4 / 5 / 6 结果 | 48983/0 · Token0/Dep0/Viol0 · 44 套 EXIT0 · 107/0 · 159/0 |

## 附录 C：复现命令

```bash
cd /Users/yaowei/WorkBuddy/PersonalAIOS
NODE_OPTIONS="" node phase28_5_orchestration_test.js                 # Gate 1
NODE_OPTIONS="" node scripts/scan-orchestration-execution.js        # Gate 2
NODE_OPTIONS="" node scripts/check-consistency.js --fix             # Gate 3 (sync)
NODE_OPTIONS="" node scripts/check-consistency.js                  # Gate 3 (verify)
NODE_OPTIONS="" npm run test:all                                   # Gate 4
NODE_OPTIONS="" node scripts/orchestration-smoke.js                # Gate 5
NODE_OPTIONS="" node phase28_5_orchestration_conversation_e2e_test.js # Gate 6
NODE_OPTIONS="" PAIOS_MODEL=heuristic node main.js                 # Gate 7
```
