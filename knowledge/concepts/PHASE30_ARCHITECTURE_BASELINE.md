---
id: know-phase30-architecture-baseline
type: concept
---
# PHASE30_ARCHITECTURE_BASELINE

> **Phase 30 — Capability Operating System（能力操作系统架构转折）**
> 架构侦察基线（规格 §三 / §四 / §四十九「第一动作不是写代码」）。
> 本文件在完整读取真实真源后产出，明确：架构 / 已有能力 / 入口 / 结果模型 / 事件 / 执行边界 / 缺失闭环 / 计划新增模块 / 禁止修改模块 / 数据流 / 红线 / 版本策略，并明确回答侦察问题。
> 所有事实来自真源读取（package.json / core/events/EventBus.js / core/automation/{registry,capability,constants}.js / core/autonomous/{constraints,autonomous-capability-selector}.js / core/orchestration/{selector,planner,constraints}.js / core/plugin/{bridge,runtime}/** / core/execution/{authorization,approval,request,sandbox}/** / core/continuity/** / scripts/check-consistency.js / PHASE29_3_ARCHITECTURE_BASELINE.md / 各前序报告），未含任何推测。

---

## 0. 元信息

| 项 | 值 | 真源 |
|---|---|---|
| 项目 | PersonalAIOS | /Users/yaowei/WorkBuddy/PersonalAIOS |
| 当前版本 | `0.38.0` | package.json `version` / `kernelVersion` |
| 运行环境 | Node 22.x / macOS / `PAIOS_MODEL=heuristic` / 完全离线 | package.json scripts |
| 测试框架 | 自研零依赖 Harness（`core/test/Harness.js`）+ Node 原生 `node` | 无 Jest/Vitest/Mocha |
| EventBus 权威事件总数 | **485**（动态 `Object.keys(EVENTS).length`） | core/events/EventBus.js |
| test:all 套数 | **52**（链尾 `phase30_capability_os_conversation_e2e_test.js`） | package.json `test:all` |
| 依赖 | 仅 `electron` | package.json `dependencies` |
| 外部依赖 | **0** | 全仓 scanner 已验（red line 5） |
| Phase 29.4 状态 | COMPLETE（12 模块 / 14 态 / 52 迁移 / 14 Continuity* 事件） | PHASE29_4_LONG_HORIZON_CONTINUITY_REPORT.md |
| 执行权唯一持有者 | `core/execution/sandbox/ExecutionSandbox` | SandboxState + Orchestrator（`AUTHORIZED_CALLERS=["orchestrator"]`） |

---

## 1. 架构总览（Architecture）

Phase 30 的任务是把「一堆能力模块」**升级为统一的 Capability Operating System** —— 建立统一的 Intent → Goal → Capability Discovery → Selection → Proposal → Permission/Risk → Execution Mode → Observation → Verification → Result → Memory → Human Expression 边界。

**已存在的 10 个能力层（全部零执行权、已实现、已验收）**：

| 层 | 目录 | 模块规模 | 零执行权 |
|---|---|---|---|
| Research | `core/research/` | 14 模块（Phase 26.2） | 模块级+实例恒 `false` |
| Vision | `core/vision/` | 多模块（Phase 28.1） | 恒 `false` |
| Document | `core/document/` | 多模块（Phase 28.2） | 恒 `false` |
| Data | `core/data/` | 多模块（Phase 28.3） | 恒 `false` |
| Automation | `core/automation/` | registry+capability+planner+runner（Phase 28.4） | 恒 `false` |
| Orchestration | `core/orchestration/` | selector+planner+loop（Phase 28.5） | 恒 `false` |
| Autonomous | `core/autonomous/` | 25 模块（Phase 28.6） | 恒 `false`（`verifyAutonomousZeroAuthority` 10 项） |
| Reasoning | `core/reasoning/` | 19 模块（Phase 29.1） | 恒 `false` |
| Learning | `core/learning/` | 13 模块（Phase 29.2） | 恒 `false` |
| Continuity | `core/continuity/` | 12 模块（Phase 29.4） | 恒 `false`（`verifyContinuityZeroAuthority` 12 项） |

**已存在的「能力治理」基础设施（Phase 21–23 / 28.4）**：

| 组件 | 位置 | 说明 |
|---|---|---|
| `CapabilityRegistry` | `core/automation/registry.js` | **成熟**：`register/get/require/has/list/count/validateRequest`，种子 6 内置能力（research/web/computer/vision/document/data），零执行权。Phase 30 **扩展**对象（§8）。 |
| `CapabilityContract` | `core/automation/capability.js` | name/version/category/actions/risk/inputSchema/outputSchema/supportsDryRun/supportsApproval。纯数据。 |
| `OrchestrationSelector` | `core/orchestration/selector.js` | 关键词→能力匹配；近重复于 AutonomousCapabilitySelector。 |
| `AutonomousCapabilitySelector` | `core/autonomous/autonomous-capability-selector.js` | 同上，几乎一字不差复制。 |
| `PluginCapabilityBridge` | `core/plugin/bridge/PluginCapabilityBridge.js` | 完整能力桥：resolver/trustGate/permissionGate/approvalGate/cache/health/audit/router/metrics；零执行权（`requestCapability` 只产请求）。 |
| `PluginCapabilityRegistry` | `core/plugin/runtime/PluginCapabilityRegistry.js` | 插件域能力注册表（pluginId 维度）。 |
| `CapabilityResolution` / `CapabilityPermissionGate` / `CapabilityApprovalGate` / `CapabilityExecutionRouter` / `CapabilityHealth` / `CapabilityAudit` | `core/plugin/bridge/` | 插件桥子组件，纯数据闸。 |
| `ApprovalManager`（多份） | `core/execution/approval/` `core/human_control/` `core/cognition/alignment/` | 审批管理层。 |
| `RiskClassifier` / `AutonomyPolicy` | `core/cognition/alignment/` | 风险分类 / 自治策略。 |
| `AuthorizationManager` | `core/execution/authorization/` | 授权判定。 |
| `ExecutionRequest*` | `core/execution/request/` | Builder/Validator/Serializer/Manager/Registry。 |
| `Orchestrator` | `core/orchestrator/Orchestrator.js` | 唯一协调者；只经事件通信。 |
| `ExecutionSandbox` | `core/execution/sandbox/ExecutionSandbox.js` | 唯一执行权（`AUTHORIZED_CALLERS=["orchestrator"]`）。 |

**关键结论**：Phase 30 不重造上述任何引擎。它新增一个**薄而统一**的 `core/capability/` 编排层（Facade + 纯数据契约 + 扩展后的 Registry + 统一 Router + Adapters），把既有能力层与既有治理能力**粘合**成「能力操作系统」。所有「能力执行」仍唯一经 `Orchestrator → ExecutionSandbox`。

---

## 2. 已有能力清单（Existing Capabilities，含入口与零执行权）

| 层 | 入口（构造函数 / 工厂） | 关键方法 | hasExecutionAuthority |
|---|---|---|---|
| Research（26.2） | `new ResearchAgent(opts)` / `queryPlanner` / `synthesize` | `agent.research(goal, opts)` → ResearchReport | 恒 `false` |
| Vision（28.1） | `new VisionAgent(opts)` | `agent.analyze(req)` / `generate` / `edit` → 产物描述符 | 恒 `false` |
| Document（28.2） | `new DocumentAgent(opts)` | `agent.render(req)` / `review` → 产物描述符 | 恒 `false` |
| Data（28.3） | `new DataAgent(opts)` | `agent.analyze(req)` / `transform` / `chart` → 纯数据产物 | 恒 `false` |
| Automation（28.4） | `new AutomationWorkflow(opts)` / `CapabilityRegistry` | `wf.plan/run` → 生成 ExecutionRequest（不直执行） | 恒 `false` |
| Orchestration（28.5） | `new OrchestrationLoop(opts)` / `OrchestrationSelector` | `loop.run` / `selector.select(goal)` | 恒 `false` |
| Autonomous（28.6） | `new AutonomousLoop(opts)` / `AutonomousCapabilitySelector` | `loop.run` / `selector.select(goal)` | 恒 `false` |
| Reasoning（29.1） | `new ReasoningLoop(opts)` | `loop.run(goalInput)` → ReasoningResult | 恒 `false` |
| Learning（29.2） | `createAdaptiveReasoningLearning(opts)` | `learnFromOutcome` / `recommendForGoal` | 恒 `false` |
| Continuity（29.4） | `new ContinuityManager(opts)` | `mgr.executeLongGoal(goal, opts)` | 恒 `false` |
| Registry（28.4） | `new CapabilityRegistry(seed)` / `createBuiltinCapabilities()` | `register/get/require/has/list/count/validateRequest` | 恒 `false` |
| Execution Pipeline（23） | `verifyExecutionPipelineZeroAuthority()` | 授权/审批/请求三层零执行权；sandbox 白名单仅 `orchestrator` | 三层恒 `false` |
| EventBus | `new EventBus()` / `EVENTS`（冻结枚举） | `emit/on/bridge` | n/a（事件总线） |

---

## 3. 入口点汇总表（Entry Points）

| 用途 | 入口 | 返回形状 | 真源 |
|---|---|---|---|
| 注册能力契约 | `new CapabilityRegistry().register(CapabilityContract)` / `.get(name)` / `.validateRequest(req)` | 契约 / bool | core/automation/registry.js |
| 选择能力（编排） | `new OrchestrationSelector({registry, eventBus}).select(goal, opts)` → `{selection, steps}` | `{selection:{goalId,capabilities,count,selectedAt}, steps:[{id,capability,action,input,dependsOn,risk,approvalRequired}]}` | core/orchestration/selector.js L54 |
| 选择能力（自主） | `new AutonomousCapabilitySelector({registry, eventBus}).select(goal, opts)` → `{selection, steps}` | 同上结构 | core/autonomous/autonomous-capability-selector.js L54 |
| 插件能力桥 | `new PluginCapabilityBridge(opts).requestCapability(spec)` → CapabilityOutcome | `{kind, ok, stage, resolution, handle, request, route, executionAuthority:false}` | core/plugin/bridge/PluginCapabilityBridge.js L333 |
| 验证执行管线 | `verifyExecutionPipelineZeroAuthority()` | `{allZeroAuthority, sandboxAuthorizedCallers:["orchestrator"], singleAuthorizedSubmitter:true}` | core/execution/index.js |
| 跑自主闭环 | `new AutonomousLoop({...}).run(goalInput, opts)` | AutonomousWorkResult（纯数据） | core/autonomous/ |
| 跑长程连续 | `new ContinuityManager({eventBus}).executeLongGoal(goal, opts)` | `{sessionId, goal, cycleCount, checkpointCount, currentState, ..., executionAuthority:false}` | core/continuity/continuity-manager.js |

---

## 4. 结果模型（Result Models）

- **AutonomousWorkResult**（28.6+29.3）：`executionAuthority:false` / `authorityHolder:"execution-sandbox"` / 无 forbidden 键。
- **ReasoningResult**（29.1）：`{status, executionAuthority:false, authorityHolder:"execution-sandbox"}`，`isReasoningResult` 校验。
- **LearningReport**（29.2）：deepFrozen，`recommendation.isAdvisory===true`（纯建议，绝不 apply）。
- **VerificationResult**（29.3）：`{executionSuccess, outputValid, goalSatisfied, evidenceSufficient, qualitySufficient, deliveryReady, completed}`，`completed` 由 `goalSatisfied===true` 硬驱动。
- **CapabilityOutcome**（plugin bridge）：`{kind, ok, stage, ..., executionAuthority:false}`。
- **ExecutionResult**（sandbox）：唯一执行层结果（`ExecutionSandbox` 持有）。

---

## 5. 事件模型（Events）

- 权威总数 = **485**，动态取自 `Object.keys(EVENTS).length`（EventBus.js 冻结枚举，**禁止硬编码旧数量**）。
- 已存在高度相关的能力事件词汇（Phase 21/22/28.x）：`PluginCapabilityResolved` / `PluginCapabilityResolved` / `PluginCapabilityExecutionRouted` / `CapabilityRegistered` / `ToolRegistered` / `ToolCapabilityDiscovered` / `ComponentRegistered` / `GoalCreated` / `GoalAnalyzed` / `AutonomousGoalCreated` / `AutonomousCapabilitySelected` / `OrchestrationCapabilitiesSelected` / `OrchestrationUnderstandingCompleted` 等。
- **Phase 30 红线：0 新增事件**（规格 §28「尽可能保持 EventBus = 485」）。Capability OS 作为纯数据 Facade，**不 emit 任何新事件**；如需广播，复用既有 `ComponentRegistered` / `GoalCreated` / `AutonomousCapabilitySelected` 等同义词汇。新增任何 `Capability*` 事件名会使 `Object.keys(EVENTS).length` 从 485 变 486，直接击穿 Gate 2（`scan-capability-os-execution.js` 的 `EXPECTED_EVENT_BUS_TOTAL=485`）。
- 阶段新增的所有纯数据模块（intent/goal/descriptor/registry/router/proposal/composition/graph/permission/observation/verification/result/context/expression/adapter/facade）**不引用 `EVENTS`、不 emit 事件**（纯函数、零事件依赖），从根上保证 0 新增事件。

---

## 6. 执行边界（Execution Boundary — 零执行权）

- **唯一真实执行链**：`Orchestrator → ExecutionSandbox`（`verifyExecutionPipelineZeroAuthority()` 证明：授权/审批/请求三层 `allZeroAuthority===true`；sandbox 白名单 `AUTHORIZED_CALLERS` 仅 `["orchestrator"]`，`singleAuthorizedSubmitter===true`）。
- **所有能力层零执行权**：10 个能力层的模块级 + 实例 `hasExecutionAuthority()===false`。
- **Capability OS 自身零执行权**：新 `core/capability/` 层所有类/模块 `hasExecutionAuthority()===false`；`CapabilityOS` / `CapabilityRouter` / `CapabilityRegistry` / `CapabilityProposal` **不得拥有** `acquireExecutionHandle` / `performExecution` / `execute` / `run` / `invoke` 方法（构造期 `assertNoCapabilityInjected` 硬闸拒收执行句柄）。
- **HANDOFF 规则（严格零引用）**：Capability OS 源码（剥离注释与字符串后）不得出现 `submitExecutionRequest` / `orchestrator.` / `executionHandle` / `sandboxHandle` / `new XxxAgent` / `new Orchestrator` / `new ExecutionSandbox`（scan-capability-os-execution.js `HANDOFF_TOKENS`）。

---

## 7. 缺失闭环缺口（Missing Closure Gaps — Phase 30 的最小新增边界）

侦察确认 10 个能力层 + Registry + 两选择器 + 插件桥均已存在且零执行权，但**缺乏统一的「能力操作系统边界」**。具体缺口：

- **缺口 1 — 无统一 Intent / Action 边界**：用户自然语言直接进入各层 `select(goal)`，没有 `Intent`（type/source/entities/confidence/requestedAction/explicitExecutionIntent）与 `ActionBoundary`（observation/information/planning/proposal/execution 判定）。无法区分「帮我看看新闻」与「去查一下新闻」的执行意图差异。
- **缺口 2 — 无统一 Capability Descriptor**：既有 `CapabilityContract` 仅 name/actions/risk；没有规格 §10 要求的 id/version/category/description/inputSchema/outputSchema/riskLevel/permissionMode/executionModes/supportsPlanning/supportsExecution/supportsObservation/supportsVerification/provider/availability/health/uiPresentation/requiredContext/constraints/metadata。各能力层（research/vision/document/data/...）无统一描述对象。
- **缺口 3 — 两选择器重复**：`OrchestrationSelector` 与 `AutonomousCapabilitySelector` 几乎一字不差（同关键词表、同默认动作、同 emits 模式），违反「不重复造 Router」。Phase 30 须统一为单一 `CapabilityRouter`（可解释选择：score/reasons/alternatives/confidence）。
- **缺口 4 — 无 Capability Composition / Graph**：研究→文档、数据→文档等组合只能在各层硬编码，没有 `CapabilityPlan`（`[research, data, document]` 纯数据步骤 + 依赖 + 产物契约）与 `CapabilityGraph`（节点/边 requires/produces/dependsOn/compatibleWith，不执行）。
- **缺口 5 — 无统一 Permission Boundary 适配**：既有 `ApprovalManager`/`RiskClassifier`/`AutonomyPolicy`/`AuthorizationManager` 分散在 4+ 处，无统一 `CapabilityPermissionDecision`（mode/risk/requiresApproval/reason/capabilityId）接口。
- **缺口 6 — 无统一 Observation / Verification / Result / HumanExpression 契约**：各层各自产出 result，没有规格 §20–§24 的统一 Observation / VerificationResult（区分 executionSuccess vs goalSatisfied）/ CapabilityResult / HumanExpression 契约。
- **缺口 7 — 无统一 CapabilityContext / Facade**：没有把 intent/goal/availableCapabilities/permissions/riskPolicy/memoryContext 聚合为统一上下文，也没有 `CapabilityOS` Facade 暴露 `understand/resolveGoal/discoverCapabilities/selectCapability/createProposal/evaluatePermission/createExecutionRequest/verifyResult/createHumanExpression`（只 prepare/route/validate/describe，不 execute）。

> 这 7 类缺口全部通过「在 `core/capability/` 新增统一层」补齐，**不重造任何既有引擎、不修改既有能力层内部、不新建第二个 Registry（扩展既有）/ 不新建第二个 Router（统一既有两选择器）**。

---

## 8. 计划新增模块（Planned New Modules — core/capability/）

> 设计原则：**Reuse > Duplicate**。扩展既有 `CapabilityRegistry`，统一既有两选择器为 `CapabilityRouter`，复用 `CoreCapabilityBridge` 治理模式与 `continuity`/`autonomous` 的零执行权自检范式。

| 新文件 | 职责 | 复用（不重造） | 零执行权 |
|---|---|---|---|
| `core/capability/constraints.js` | 红线 / 纯数据拷贝 / 禁止注入键（自主层 44 键超集 + 能力层特有句柄） | `pureCopy` 复用 autonomous；`CAPABILITY_FORBIDDEN_INJECTION_KEYS` 为严格超集 | `hasExecutionAuthority()=>false`；`assertNoCapabilityInjected` |
| `core/capability/intent.js` | `Intent` 纯数据模型 + `createIntent` + `ActionBoundary`（`classifyIntent`：INFORM/PLAN/PROPOSE_ACTION/EXECUTE + explicit 判定） | 纯数据 | 恒 `false`；不携带 Agent/Tool/Handle |
| `core/capability/goal.js` | `Goal` 纯数据模型（与 Intent 解耦；executionRequired/approvalRequired） | `GoalPure` 风格 | 恒 `false` |
| `core/capability/descriptor.js` | `CapabilityDescriptor` 统一描述对象（规格 §10 全集字段） | 由既有 `CapabilityContract` 归一 | 恒 `false` |
| `core/capability/registry.js` | **扩展** `core/automation/registry.js` 的 `CapabilityRegistry`（`class CapabilityRegistry extends Existing`）：新增 `registerCapability/getCapability/hasCapability/listCapabilities/findCapabilities/resolveCapability/validateCapabilityInput/getCapabilityHealth` + 种子全部 10 能力层为 Descriptor | 复用既有 register/get/has/list/count/validateRequest + 嵌入式 forbidden 闸 | 恒 `false` |
| `core/capability/router.js` | **统一** `CapabilityRouter`（取代两选择器重复）：`route({intent, goal, context, capabilities})` → `{selectedCapability, score, reasons, alternatives, confidence}`（可解释） | 复用既有关键词映射 + scoring；调用统一 Registry | 恒 `false` |
| `core/capability/proposal.js` | `CapabilityProposal` 统一提议（状态机 proposed/approved/rejected/blocked/executing/completed/failed；自己不执行） | 纯数据 | 恒 `false` |
| `core/capability/composition.js` | `CapabilityComposition` / `CapabilityPlan`（步骤 + 依赖 + 产物契约，纯数据） | 复用既有步骤形状 | 恒 `false` |
| `core/capability/graph.js` | `CapabilityGraph`（节点=能力，边=requires/produces/dependsOn/compatibleWith，纯数据，不执行） | 纯数据 | 恒 `false` |
| `core/capability/permission.js` | `CapabilityPermissionDecision`（mode/risk/requiresApproval/reason/capabilityId）+ 适配既有 `ApprovalManager`/`RiskClassifier`/`AutonomyPolicy`/`AuthorizationManager` | 复用既有治理组件（不重造引擎） | 恒 `false` |
| `core/capability/execution-mode.js` | `ExecutionMode` 枚举（none/simulation/api/mcp/browser/computer/desktop/sandbox）+ 能力声明 supportsExecution 集合 | 纯数据 | 恒 `false` |
| `core/capability/observation.js` | `Observation` 统一契约（id/source/capabilityId/timestamp/status/data/evidence/metadata；禁携带 process/browserHandle/executionToken） | 纯数据 | 恒 `false` |
| `core/capability/verification.js` | `VerificationResult`（verified/confidence/criteria/evidence/failureReason/observedState/expectedState；区分 executionSuccess vs goalSatisfied） | 复用 29.3 Verification 语义 | 恒 `false` |
| `core/capability/result.js` | `CapabilityResult`（status/capabilityId/goalId/output/observation/verification/evidence/executionReference/summary；禁嵌入 binary/process/handle） | 纯数据 | 恒 `false` |
| `core/capability/human-expression.js` | `HumanExpression`（type/title/summary/details/actions/evidence/approvalRequired；UI 可消费） | 纯数据 | 恒 `false` |
| `core/capability/context.js` | `CapabilityContext` 统一上下文（intent/goal/userPreferences/availableCapabilities/permissions/riskPolicy/memoryContext/conversationContext/executionPolicy；禁注入 orchestrator/sandbox/agent instances） | 纯数据 | 恒 `false` |
| `core/capability/adapters.js` | `CapabilityAdapter` 把各既有能力层归一为 `CapabilityDescriptor`：Research/Vision/Document/Data/Automation/Orchestration/Autonomous/Reasoning/Learning/Continuity。Adapter 无执行权 | 只读既有层元数据；不 new Agent | 恒 `false` |
| `core/capability/capability-os.js` | `CapabilityOS` Facade：`understand/resolveGoal/discoverCapabilities/selectCapability/createProposal/evaluatePermission/createExecutionRequest/verifyResult/createHumanExpression`（只 prepare/route/validate/describe，不 execute） | 组合上述模块 | 恒 `false`（无 execute 方法） |
| `core/capability/index.js` | 聚合导出 + `CAPABILITY_OS_MODULE_COUNT` + `verifyCapabilityOSZeroAuthority()`（多不变量自检，仿 continuity） | 仿 continuity/index.js | 恒 `false` |

**扩展而非重复的证据**：
- Registry：新 `core/capability/registry.js` 的 `CapabilityRegistry` **继承** `core/automation/registry.js` 的 `CapabilityRegistry`（同一类名，扩展方法），满足 §11「优先扩展、不创建第二个 Registry」。
- Router：新 `CapabilityRouter` 为**唯一**统一选择器；既有 `OrchestrationSelector` / `AutonomousCapabilitySelector` **保留不删**（§44「不要破坏 Phase 28.5/28.6」），但新增代码统一经 `CapabilityRouter`；两旧选择器可在未来 deprecate，本阶段不破坏。
- Bridge：新 `CapabilityOS` **不重造** 插件桥（`PluginCapabilityBridge` 已成熟）；Phase 30 的 Permission Decision 仅**适配**既有 `ApprovalManager`/`RiskClassifier`/`AutonomyPolicy`/`AuthorizationManager`。

---

## 9. 禁止修改模块（Forbidden Modifications — 规格 §四十二）

| 模块 | 是否可改 | 原因 |
|---|---|---|
| `core/execution/*`（含 ExecutionSandbox） | **禁止** | 唯一执行入口；改则破坏红线 1 |
| `core/orchestrator/*` | **禁止** | 唯一授权提交者 |
| `core/sandbox/*` | **禁止** | 执行权持有者 |
| `core/research/*` `core/vision/*` `core/document/*` `core/data/*` `core/automation/*` `core/orchestration/*` `core/autonomous/*` `core/reasoning/*` `core/learning/*` `core/continuity/*` 内部实现 | **禁止改内部** | 规格 §42「本阶段只增加 adapter / descriptor / registry / router / boundary，不重写既有能力内部」 |
| `core/events/EventBus.js` | **禁止新增事件** | 红线：EventBus 保持 485（§28） |
| `core/plugin/bridge/*` `core/plugin/runtime/*` | **禁止改内部** | 复用，不重造 |

**可改**：`package.json`（version/kernelsion/description/test:all 链）、`main.js`（追加演示段）、新增 `core/capability/*` 全部、新增测试/扫描器脚本、`scripts/check-consistency.js`（仅当派生点规则需扩展时，通常无需改）。

---

## 10. 红线（Hard Red Lines — 贯穿全局）

1. 能力层（含新 Capability OS）自身**不得拥有执行权**；唯一真实执行权仍归 `ExecutionSandbox`。
2. 唯一真实执行链：`Orchestrator → ExecutionSandbox`。
3. 能力层只能产生：pure data / plans / proposals / execution requests / observations / verification results / references / advisory recommendations。
4. 禁止任何能力层 `new Agent()` / `new Orchestrator()` / `new ExecutionSandbox()` / 直接 shell / 直接 process / 直接 filesystem mutation / 直接 browser automation / 直接 GUI automation / 直接 MCP execution / 直接 network execution。
5. 外部依赖继续保持 **0**。
6. 不引入 Jest / Vitest / Mocha；继续用自研 Harness。
7. **Intent ≠ Action**：理解 ≠ 执行；inform ≠ execute；proposal ≠ execution。
8. **禁止伪造成功**：未执行不得打印 executed=true；Verification 未过不得 goalSatisfied=true；Capability 不存在不得模拟存在。

---

## 11. 版本策略（Version Strategy — §29）

- 当前真源：`package.json` `version` / `kernelVersion` = `0.38.0`。
- Phase 30 形成真实生产能力（统一能力操作系统边界），**升级至 `0.38.0`**。
- 同步范围（Gate 3 重点）：
  - `package.json` `version` + `kernelVersion` → `0.38.0`；`description` 追加「Capability OS 架构层（core/capability/：Intent/Goal/Action Boundary / Capability Descriptor / Registry 扩展 / Router 统一 / Proposal / Composition / Graph / Permission Boundary / Verification / Result / HumanExpression / Context / Facade），全部零执行权」，保留 `EventBus 共 485 个事件`（Gate 4 依赖）。
  - 全部断言 `0.37.0` (`/^v?0\.37\.0$/`) 或 `kernelVersion === "0.37.0"` 的测试文件 → `0.38.0`（`check-consistency --fix` 覆盖标准点；变量别名/字符串字面量须手工，MEMORY 已记陷阱）。
  - `test:all` 链尾套件 → `phase30_capability_os_conversation_e2e_test.js`；套数 **50 → 52**（+Gate1 `phase30_capability_os_test.js` + Gate6 `phase30_capability_os_conversation_e2e_test.js`；Gate5 `scripts/capability-os-smoke.js` 为脚本非套件）。
  - EventBus 保持 **485**（0 新增事件）。
- **严禁混杂残留**：全仓不得出现 `0.36.0` / `0.37.0`（升级后）/ `471` / `432` / `448` / `464` 与 `485` 并存；统一 `0.38.0` / `485`。

---

## 12. 侦察问题回答（Recon Q&A）

**Q1：现有 CapabilityRegistry 是否成熟？** 是（`core/automation/registry.js`，6 内置能力、validateRequest、零执行权）。Phase 30 **扩展**它，不新建第二个。
**Q2：是否已有 Router/Selector？** 有，且**重复两份**（OrchestrationSelector + AutonomousCapabilitySelector）。Phase 30 统一为 `CapabilityRouter`，旧两份保留不破坏。
**Q3：Permission/Approval/Authorization 是否已存在？** 是，分散在 `core/execution/{authorization,approval}`、`core/human_control`、`core/cognition/alignment`（RiskClassifier/AutonomyPolicy）。Phase 30 仅**适配**为统一 `CapabilityPermissionDecision`，不重造引擎。
**Q4：EventBus 是否要加事件？** 否，保持 485；Capability OS 纯数据、0 事件 emit。
**Q5：执行权是否唯一？** 是，`ExecutionSandbox.AUTHORIZED_CALLERS=["orchestrator"]`，全仓 scanner 已验零执行权。
**Q6：既有能力层内部要不要改？** 否，规格 §42 明令只加 adapter/descriptor/registry/router/boundary，不重写内部。
**Q7：Capability OS 是否执行？** 否，只 prepare/route/validate/describe；唯一执行链仍 Orchestrator→Sandbox。
**Q8：是否引入新依赖/框架？** 否，外部依赖 0，继续自研 Harness。

---

## 13. 下一步（STEP 5+）

基线确认后，按规格执行顺序进入实现：
STEP 5 Intent/Goal/ActionBoundary → STEP 6 CapabilityDescriptor → STEP 7 扩展 Registry → STEP 8 CapabilityRouter → STEP 9 CapabilityProposal → STEP 10 Composition → STEP 11 Graph → STEP 12 Permission boundary → STEP 13 Observation/Verification/Result → STEP 14 HumanExpression → STEP 15 CapabilityContext → STEP 16 CapabilityOS Facade → STEP 17 Adapters → STEP 18 zero-authority scanner → STEP 19–22 Gates 1/5/6/7 → STEP 23–26 Gates 3/4 → STEP 27–33 双次复现/报告/Memory/STOP。

> **STOP_AT_PHASE_30** 纪律：完成 7 Gate + 双次复现一致 + 报告 + Memory 后，严格停止，不自动进入 Phase 31。
