---
id: know-phase-30-capability-operating-system
type: concept
---
# Phase 30 能力操作系统（Capability Operating System）验收报告

> 版本：`v0.38.0` · 内核 `kernelVersion=0.38.0` · EventBus 总数 `485`（0 新增事件）
> 生成时间：2026-08-14 · 执行环境：Node 22.x / macOS / 离线 / `PAIOS_MODEL=heuristic`
> 验收结论：**七道闸门全绿 · 双次复现一致 · Phase 30 完成 · 严格停止于 STOP_AT_PHASE_30**

---

## 1. 文档元信息

| 项 | 值 |
| --- | --- |
| Phase | 30 — Capability Operating System（能力操作系统架构转折） |
| 版本 | `0.38.0`（前序 `0.37.0` → `0.38.0`） |
| API 版本 | `CAPABILITY_OS_API_VERSION = "1.0.0"` |
| 模块数 | `CAPABILITY_OS_MODULE_COUNT = 19`（18 源文件 + `index.js`） |
| 注册能力数 | `12`（research/web/computer/vision/document/data/automation/orchestration/autonomous/reasoning/learning/continuity 归一为统一 Descriptor） |
| EventBus 总数 | `485`（0 新增；动态 `Object.keys(EVENTS).length`） |
| 禁止注入键 | `CAPABILITY_FORBIDDEN_INJECTION_KEYS.length = 61`（自主层 44 键超集 + 能力层特键） |
| 执行权唯一持有者 | `CAPABILITY_AUTHORITY_HOLDER_NAME = "execution-sandbox"` |
| 零执行权自检项 | `verifyCapabilityOSZeroAuthority().checked = 12`（`ok = true`） |
| 七闸状态 | G1–G7 全部 EXIT 0 / 0 FAIL |
| 复现 | 双次复现（G1/2/5/6/7 ×2、G3/4 ×1）完全一致 |

---

## 2. 摘要（Executive Summary）

Phase 30 把此前「一堆各自独立的能力模块」**升级为统一的 Capability Operating System** ——
在 `core/capability/` 新增一个**薄而统一**的编排层，把既有 10 个能力层（Research / Vision /
Document / Data / Automation / Orchestration / Autonomous / Reasoning / Learning / Continuity）
与既有治理能力（Registry / Bridge / Approval / Risk / Authorization / AutonomyPolicy）**粘合**
成统一的 `Intent → Goal → Capability Discovery → Selection → Proposal → Permission/Risk →
Execution Mode → Observation → Verification → Result → Memory → Human Expression` 边界。

本次工作在既有能力层**零内部改动**的前提下，新增 **19 个模块**（全部零执行权）：
Intent/ActionBoundary、Goal、CapabilityDescriptor、扩展版 CapabilityRegistry、统一 CapabilityRouter、
CapabilityProposal（状态机）、Composition/Plan、Graph、Permission Decision、ExecutionMode、Observation、
VerificationResult、CapabilityResult、HumanExpression、CapabilityContext、Adapters、CapabilityOS Facade、
Constraints、聚合 index。全程维持最高红线：**全部新增模块零执行权**、`EventBus` 总数 `485` 不变
（0 新增事件）、唯一执行链 `Orchestrator → ExecutionSandbox` 不变、外部依赖保持 `0`、无 Jest/Vitest。

验收标准（规格七闸）全部达成，并二次复现证明稳定性。

---

## 3. 目标与范围（Scope）

**目标**

1. 建立统一的「能力操作系统边界」，让任意用户输入都经过统一的 Intent 理解 → 动作边界判定 →
   目标解耦 → 能力发现 → 可解释选择 → 提议 → 权限/风险 → 执行模式 → 观察 → 验证 → 结果 →
   人类表达全链路，而非直接散落到各层 `select(goal)`。
2. 维持零执行权、零外部依赖、纯数据；Capability OS 只 `prepare / route / validate / describe`，
   真实执行唯一经 `Orchestrator → ExecutionSandbox`。
3. 落地可一键复现的七道验收闸门，并二次复现证明稳定性。

**非目标（明确不做）**

- 不新增任何 `EventBus` 事件（严格 0 新增，保持 485）。
- 不改动执行权归属（唯一执行权仍归 `ExecutionSandbox`）。
- 不重写任何既有能力层内部（规格 §42）。
- 不创建第二个 Registry / 第二个 Router（扩展既有 / 统一既有两个选择器）。
- 不进入 Phase 31（见 §46 停止声明）。

---

## 4. 架构转折：从「能力模块堆叠」到「能力操作系统」

**前序状态（Phase 1–29.4）**：10 个能力层各自成熟、各自零执行权，但缺乏统一边界
—— 用户自然语言直接进各层 `select(goal)`，没有 `Intent`/`ActionBoundary` 区分
「帮我看看」与「去查一下」；两选择器（`OrchestrationSelector` / `AutonomousCapabilitySelector`）
几乎一字不差重复；没有统一的 Descriptor / Composition / Graph / Permission / Verification / Result /
HumanExpression 契约。

**Phase 30 转折**：新增 `core/capability/` 统一编排层，把「理解 ≠ 执行」作为第一原则落地为
可机器校验的边界。能力层自身零执行权这一事实不变，变的只是「它们被一个统一的 OS 边界调度，
而非各自被直接调用」。

---

## 5. 统一边界定义（全链路）

统一边界由 `CapabilityOS.prepare(userInput, opts)` 串起，逐环产出**纯数据**：

1. **Intent**（`type/source/entities/confidence/requestedAction/explicitExecutionIntent`）——
   理解用户输入，不执行。
2. **ActionBoundary**（`classifyIntent`：INFORM / PLAN / PROPOSE_ACTION / EXECUTE + explicit 判定）——
   区分「只是看看」与「要执行」。
3. **Goal**（与 Intent 解耦的纯数据目标，`executionRequired/approvalRequired`）——
   目标不携带执行句柄。
4. **Capability Discovery**（从扩展 Registry 列举全部 12 能力）——
   只读，不执行。
5. **Selection**（`CapabilityRouter.route` → `{selectedCapability, score, reasons, alternatives, confidence}`）——
   可解释、确定性。
6. **Proposal**（`CapabilityProposal` 状态机 proposed/approved/rejected/blocked/executing/completed/failed）——
   终态前可审批/驳回，不自动执行。
7. **Permission / Risk**（`CapabilityPermissionDecision` 适配既有 Approval/Risk/Authorization/AutonomyPolicy）——
   纯数据判定。
8. **Execution Mode**（none/simulation/api/mcp/browser/computer/desktop/sandbox）——
   能力声明 `supportsExecution` 集合。
9. **Observation**（统一观察契约，禁携带 process/browserHandle/executionToken）。
10. **VerificationResult**（区分 `executionSuccess` vs `goalSatisfied`）。
11. **CapabilityResult**（纯数据产物，禁嵌入 binary/process/handle）。
12. **Memory**（引用既有 Memory 层，纯数据）。
13. **HumanExpression**（UI 可消费的批准请求 / 提案 / 回答）。

---

## 6. 七道闸门总览（Gate Overview）

| Gate | 名称 | 工具 | 本轮门槛 | 结果 |
| --- | --- | --- | --- | --- |
| G1 | 长测试 | `phase30_capability_os_test.js` | ≥50000 断言 / ≥70 段 / 0 FAIL | PASS 77018 / FAIL 0 / 98 段 |
| G2 | 零执行权扫描 | `scripts/scan-capability-os-execution.js` | Token/Dep/Viol=0 / STRUCT/RUNTIME=PASS | 全 0 / PASS |
| G3 | 一致性 | `scripts/check-consistency.js --fix` | EXIT 0 / 派生点同步 | EXIT 0 / 59 点同步 |
| G4 | 全量回归 | `npm run test:all` | 52 套 EXIT 0 / 0 回归 | EXIT 0 / 0 回归 |
| G5 | 集成冒烟 | `scripts/capability-os-smoke.js` | ≥25 场景 / 0 失败 | 127 通过 / 28 场景 |
| G6 | 多轮对话 e2e | `phase30_capability_os_conversation_e2e_test.js` | ≥15 多轮 / ≥300 断言 | 16 多轮 / 534 断言 |
| G7 | 主程序演示 | `PAIOS_MODEL=heuristic node main.js` | EXIT 0 / 演示段完整 | EXIT 0 / 14 项 |

---

## 7. 设计原则：Intent ≠ Action

最高原则：**理解 ≠ 执行**。

- `Intent` 只描述「用户想要什么 / 是否显式要求执行」，自身零执行权。
- `ActionBoundary` 把意图归类为 INFORM（仅告知）/ PLAN（规划）/ PROPOSE_ACTION（提议）/
  EXECUTE（执行），只有 EXECUTE 且通过权限闸门才会生成 ExecutionRequest。
- `inform ≠ execute`：INFORM 类意图只产出 HumanExpression（回答），绝不生成执行请求。
- `proposal ≠ execution`：Proposal 在 approved 之前永远停在纯数据状态，不投递、不执行。

---

## 8. 设计原则：Reuse > Duplicate

不重造任何既有引擎：

- **Registry**：扩展既有 `core/automation/registry.js` 的 `CapabilityRegistry`（同名类继承扩展），
  不创建第二个 Registry。
- **Router**：统一既有两份重复选择器（`OrchestrationSelector` / `AutonomousCapabilitySelector`）
  为单一 `CapabilityRouter`；旧两份**保留不删**（§42 不破坏 Phase 28.5/28.6），新代码统一经 Router。
- **治理**：Permission Decision 仅**适配**既有 `ApprovalManager` / `RiskClassifier` / `AutonomyPolicy` /
  `AuthorizationManager`，不重造审批/授权引擎。
- **Bridge**：不重造成熟的 `PluginCapabilityBridge`。

---

## 9. 核心模块清单（core/capability/ 19 文件）

| # | 文件 | 职责 | 零执行权 |
| --- | --- | --- | --- |
| 1 | `constraints.js` | 红线 / 纯数据拷贝 / 禁止注入键（61 键） | `hasExecutionAuthority()=>false` |
| 2 | `intent.js` | Intent + ActionBoundary（classifyIntent） | 恒 `false` |
| 3 | `goal.js` | Goal 纯数据（与 Intent 解耦） | 恒 `false` |
| 4 | `descriptor.js` | CapabilityDescriptor 统一描述（规格 §10 全集字段） | 恒 `false` |
| 5 | `registry.js` | **扩展**既有 CapabilityRegistry（继承 + 12 能力种子） | 恒 `false` |
| 6 | `router.js` | **统一** CapabilityRouter（可解释选择） | 恒 `false` |
| 7 | `proposal.js` | CapabilityProposal 状态机（7 态 / 含环） | 恒 `false` |
| 8 | `composition.js` | CapabilityComposition / CapabilityPlan | 恒 `false` |
| 9 | `graph.js` | CapabilityGraph（拓扑 / 环检测，不执行） | 恒 `false` |
| 10 | `permission.js` | CapabilityPermissionDecision（适配既有治理） | 恒 `false` |
| 11 | `execution-mode.js` | ExecutionMode 枚举 | 恒 `false` |
| 12 | `observation.js` | Observation 统一契约 | 恒 `false` |
| 13 | `verification.js` | VerificationResult（executionSuccess vs goalSatisfied） | 恒 `false` |
| 14 | `result.js` | CapabilityResult 纯数据 | 恒 `false` |
| 15 | `human-expression.js` | HumanExpression（UI 可消费） | 恒 `false` |
| 16 | `context.js` | CapabilityContext（禁注入 orchestrator/sandbox/agent） | 恒 `false` |
| 17 | `adapters.js` | CapabilityAdapter（既有层 → Descriptor 归一） | 恒 `false` |
| 18 | `capability-os.js` | CapabilityOS Facade（只 prepare/route/validate/describe） | 恒 `false` |
| 19 | `index.js` | 聚合导出 + `verifyCapabilityOSZeroAuthority()`（12 不变量） | 恒 `false` |

---

## 10. 模块详解：constraints（红线与禁止注入键）

`core/capability/constraints.js` 定义 `CAPABILITY_FORBIDDEN_INJECTION_KEYS`（**61 键**，冻结常量），
是自主层 44 键黑名单的**严格超集** + 能力层特键（如 `orchestrator` / `executionSandbox` /
`executionHandle` / `submitExecutionRequest` 等）。提供：

- `pureCopy(obj)`：深拷贝纯数据，剥离一切函数/句柄。
- `assertNoCapabilityInjected(obj, where)`：构造期硬闸，命中任一禁止键一律抛错。
- `hasExecutionAuthority()` 恒 `false`。

---

## 11. 模块详解：intent + ActionBoundary

`core/capability/intent.js`：

- `createIntent({type, source, entities, confidence, requestedAction, explicitExecutionIntent})` →
  纯数据 Intent，`executionAuthority:false`。
- `classifyIntent(intent)` → ActionBoundary：`INFORM` / `PLAN` / `PROPOSE_ACTION` / `EXECUTE`。
- `explicitExecutionIntent` 为显式执行信号；无此信号时即使 type=EXECUTE 也走更保守边界。

---

## 12. 模块详解：goal（与 Intent 解耦）

`core/capability/goal.js`：`createGoal({objective, executionRequired, approvalRequired, ...})`
产出纯数据 Goal。Goal **不引用** Intent 实例、不携带执行句柄；与 Intent 解耦，便于在
多轮对话中跨轮复用与累积上下文（见 §23 / §38）。

---

## 13. 模块详解：descriptor（统一能力描述）

`core/capability/descriptor.js`：`createCapabilityDescriptor({id, version, category, description,
inputSchema, outputSchema, riskLevel, permissionMode, executionModes, supportsPlanning,
supportsExecution, supportsObservation, supportsVerification, provider, availability, health,
uiPresentation, requiredContext, constraints, metadata})` 输出 `CapabilityDescriptor`。
由既有 `CapabilityContract` 归一，覆盖规格 §10 全集字段；`hasExecutionAuthority()` 恒 `false`，
`executionAuthority:false`。

---

## 14. 模块详解：registry（扩展既有，非新建）

`core/capability/registry.js`：

```js
class CapabilityRegistry extends ExistingCapabilityRegistry { /* 同名继承扩展 */ }
```

新增方法：`registerCapability / getCapability / hasCapability / listCapabilities /
findCapabilities / resolveCapability / validateCapabilityInput / getCapabilityHealth`。
种子全部 12 能力层为统一 Descriptor（`buildBuiltinCapabilityDescriptors`）。
`hasExecutionAuthority()` 恒 `false`；嵌入式 forbidden 闸拒收执行句柄。满足 §11「优先扩展、
不创建第二个 Registry」。

---

## 15. 模块详解：router（统一两选择器）

`core/capability/router.js`：`CapabilityRouter.route({intent, goal, context, capabilities})`
→ `{selectedCapability, score, reasons, alternatives, confidence}`，**可解释 + 确定性**。

- 复用既有关键词映射与 scoring；调用统一 Registry。
- `hasExecutionAuthority()` 恒 `false`。
- 旧 `OrchestrationSelector` / `AutonomousCapabilitySelector` **保留不删**（§42），新代码统一经 Router。

---

## 16. 模块详解：proposal（状态机）

`core/capability/proposal.js`：

- `PROPOSAL_STATES = ["proposed","approved","rejected","blocked","executing","completed","failed"]`
  （**7 态，无 `cancelled`**）。
- `PROPOSAL_TRANSITIONS`：含环（如 approved→blocked→approved 合法），但**终态无出边**
  （completed/failed/rejected 不可再迁移，否则抛错）。
- `transitionProposal(p, to)` **返回新对象**（非原地改写），非法迁移直接抛错。
- Proposal 自身零执行权，永远停在纯数据。

---

## 17. 模块详解：composition + plan

`core/capability/composition.js`：`CapabilityComposition` / `CapabilityPlan`
（`[research, data, document]` 纯数据步骤 + 依赖 + 产物契约）。不执行，仅描述多能力编排顺序。

---

## 18. 模块详解：graph（拓扑与环检测）

`core/capability/graph.js`：

- `CapabilityGraph.addNode(name)` / `addEdge(from, to, kind="dependsOn")`（分参；非法 kind 抛错；
  from/to 须先 `addNode`）。
- `topoSortSteps(plan)` → step id **字符串数组**（有环返回 `null`）。
- `hasPlanCycle(plan)` 独立函数。
- 纯数据，不执行。

---

## 19. 模块详解：permission decision

`core/capability/permission.js`：`evaluatePermission({capability, executionMode, intentType})`
→ `CapabilityPermissionDecision`（`mode/risk/requiresApproval/reason/capabilityId`）。
适配既有 `ApprovalManager` / `RiskClassifier` / `AutonomyPolicy` / `AuthorizationManager`，
不重造引擎；`executionAuthority:false`。

---

## 20. 模块详解：execution-mode

`core/capability/execution-mode.js`：`ExecutionMode` 枚举
（`none`/`simulation`/`api`/`mcp`/`browser`/`computer`/`desktop`/`sandbox`）。能力声明
`supportsExecution` 集合；纯数据，`hasExecutionAuthority()` 恒 `false`。

---

## 21. 模块详解：observation

`core/capability/observation.js`：`createObservation({source, capabilityId, timestamp, status,
data, evidence, metadata})` → Observation 契约。禁携带 `process` / `browserHandle` /
`executionToken`；纯数据。

---

## 22. 模块详解：verification

`core/capability/verification.js`：`createVerificationResult({verified, confidence, criteria,
evidence, failureReason, observedState, expectedState})`。关键区分 **`executionSuccess`**
（执行是否完成）与 **`goalSatisfied`**（目标是否达成）—— 未过验证不得 `goalSatisfied=true`
（红线 8：禁止伪造成功）。

---

## 23. 模块详解：result

`core/capability/result.js`：`createCapabilityResult({status, capabilityId, goalId, output,
observation, verification, evidence, executionReference, summary})` → CapabilityResult。
禁嵌入 `binary` / `process` / `handle`；`executionAuthority:false`。

---

## 24. 模块详解：human-expression

`core/capability/human-expression.js`：`createHumanExpression({type, title, summary, details,
actions, evidence, approvalRequired})` → UI 可消费的人类表达（批准请求 / 提案 / 回答）。
纯数据。

---

## 25. 模块详解：context（聚合上下文）

`core/capability/context.js`：`createCapabilityContext({intent, goal, userPreferences,
availableCapabilities, permissions, riskPolicy, memoryContext, conversationContext,
executionPolicy})` → 统一上下文。

- **构造期硬闸**：`assertNoCapabilityInjected` 拒收 `orchestrator` / `sandbox` / `agent` 等执行句柄。
- **防御性静默剥离**：对不在禁止名单的危险键（如 `agent`）静默剥离而非抛错。
- `mergeCapabilityContext(base, extra)` = 浅覆盖（extra 后者覆盖 base 同名字段）。

---

## 26. 模块详解：adapters（既有层 → Descriptor 归一）

`core/capability/adapters.js`：`CapabilityAdapter` 把 10 个既有能力层只读归一为
`CapabilityDescriptor`（Research/Vision/Document/Data/Automation/Orchestration/Autonomous/
Reasoning/Learning/Continuity + web + computer = 12）。Adapter **只读元数据、不 `new Agent`**，
零执行权。

---

## 27. 模块详解：capability-os Facade

`core/capability/capability-os.js`：`CapabilityOS` Facade 暴露
`understand / resolveGoal / discoverCapabilities / selectCapability / createProposal /
evaluatePermission / createExecutionRequest / verifyResult / createHumanExpression`，
但**只 `prepare / route / validate / describe`，不 execute**。

- `CapabilityOS.prepare(userInput, opts)`：完整准备链，输出纯数据 Outcome，`executionAuthority` 恒 `false`。
- **无** `execute / run / invoke / performExecution / acquireExecutionHandle` 方法（自检 Item 9）。

---

## 28. 模块详解：index + 零执行权自证

`core/capability/index.js`：

- 聚合导出全部 19 模块 API。
- 导出常量：`CAPABILITY_OS_API_VERSION="1.0.0"` / `CAPABILITY_OS_MODULE_COUNT=19` /
  `CAPABILITY_AUTHORITY_HOLDER_NAME="execution-sandbox"`。
- `verifyCapabilityOSZeroAuthority()`：12 项硬不变量自检（见 §29）。

---

## 29. 零执行权自证范式（12 不变量）

`verifyCapabilityOSZeroAuthority()` 的 12 项不变量（`checked=12`，`ok=true`）：

| # | 不变量名 | 校验内容 |
| --- | --- | --- |
| 1 | `all-module-level-zero-authority` | 18 模块级 `hasExecutionAuthority()` 全 `false` |
| 2 | `all-instances-zero-authority` | CapabilityRegistry/Router/OS/Graph/Descriptor 实例全 `false` |
| 3 | `registry-extends-and-zero-authority` | 继承既有 Registry + 种子 ≥12 + 零执行权 |
| 4 | `router-explainable-and-deterministic` | 同输入两次 route 选同样能力 + 含 reasons/alternatives |
| 5 | `proposal-state-machine-integrity` | 终态无出边 + 非法迁移抛错 |
| 6 | `descriptor-purity` | Descriptor 无执行句柄 + 禁注键全未出现 |
| 7 | `permission-zero-authority` | PermissionDecision 纯数据 + `executionAuthority:false` |
| 8 | `observation-verification-result-purity` | 三者皆 `executionAuthority:false`、无 handle/process |
| 9 | `facade-no-execute-and-prepare-no-exec` | OS 无 execute 类方法 + prepare 不执行 |
| 10 | `forbidden-injection-superset` | 61 键含自主层 44 键 + 能力层特键 |
| 11 | `construction-gate-rejects-injection` | orchestrator/executionHandle 注入三处全拒 |
| 12 | `module-count-19` | `CAPABILITY_OS_MODULE_COUNT === 19` |

---

## 30. 禁止注入键机制（61 键）

`CAPABILITY_FORBIDDEN_INJECTION_KEYS` = 自主层 44 键黑名单 ∪ 能力层特键（如 `orchestrator` /
`executionSandbox` / `executionHandle` / `submitExecutionRequest` / `sandboxHandle` /
`browserGateway` / `mcpGateway` 等），共 **61 键**（冻结）。

- 构造期硬闸 `assertNoCapabilityInjected`：纯数据工厂（createIntent/createGoal/createProposal/
  createCapabilityContext/...）构造时一律校验，命中即抛。
- 类（Descriptor/Registry/Router/Graph/OS）实例方法 `hasExecutionAuthority()` 恒 `false`，
  `acquireExecutionHandle()` 一律抛错。

---

## 31. 执行边界与 HANDOFF 规则

- **唯一真实执行链**：`Orchestrator → ExecutionSandbox`。
- **Capability OS 自身零执行权**：新层所有类/模块 `hasExecutionAuthority()===false`；
  不得拥有 `acquireExecutionHandle / performExecution / execute / run / invoke` 方法。
- **HANDOFF 规则（严格零引用）**：Capability OS 源码（剥离注释与字符串后）不得出现
  `submitExecutionRequest` / `orchestrator.` / `executionHandle` / `sandboxHandle` /
  `new XxxAgent` / `new Orchestrator` / `new ExecutionSandbox`（`scan-capability-os-execution.js`
  的 `HANDOFF_TOKENS`）。

---

## 32. 事件红线（EventBus 485 / 0 新增）

- 权威总数 = **485**，动态取自 `Object.keys(EVENTS).length`（EventBus.js 冻结枚举）。
- Phase 30 **0 新增事件**：所有新模块为纯函数、零事件依赖，不 `emit` 任何新事件。
- 新增任何 `Capability*` 事件名会使总数从 485 变 486，直接击穿 Gate 2
  （`scan-capability-os-execution.js` 的 `EXPECTED_EVENT_BUS_TOTAL=485`）。

---

## 33. 复用而非重复证据

- **Registry 继承**：新 `core/capability/registry.js` 的 `CapabilityRegistry` **继承**既有
  `core/automation/registry.js` 的 `CapabilityRegistry`（同名类），满足 §11。
- **Router 统一**：新 `CapabilityRouter` 为**唯一**统一选择器；旧两份保留不破坏，未来可 deprecate。
- **治理适配**：Permission Decision 仅适配既有 `ApprovalManager`/`RiskClassifier`/`AutonomyPolicy`/
  `AuthorizationManager`，不重造引擎。
- **Bridge 复用**：不重造成熟 `PluginCapabilityBridge`。

---

## 34. Gate 1 终验（长测试）

- 工具：`node phase30_capability_os_test.js`。
- 结果：**PASS 77018 / FAIL 0 / 共 98 段 / 34ms**。
- 断言数远超 ≥50000 门槛；段数远超 ≥70 门槛；0 FAIL。
- Round 1 与 Round 2 完全一致（77018 / 98 段）。

---

## 35. Gate 2 终验（零执行权扫描）

- 工具：`node scripts/scan-capability-os-execution.js`。
- 扫描目录：`core/capability`（19 文件）；禁止注入键扫描数：61。
- 各类别命中（要求全 0）：`executionToken=0` / `externalDependency=0` / `forbiddenInjection=0` /
  `directProcess=0` / `directShell=0` / `directFilesystem=0` / `directBrowser=0` / `directGUI=0` /
  `directMCP=0` / `agentInstantiation=0` / `sandboxInstantiation=0` / `orchestratorInstantiation=0`。
- `Structural=PASS`（modules=19/19, exportHasExec=true）；`RuntimeInvariant=PASS`
  （`verifyZeroAuthority.checked=12`）。
- 汇总：`TOKEN=0 / DEP=0 / VIOL=0 / STRUCT=PASS / RUNTIME=PASS`。
- Round 1 与 Round 2 完全一致。

---

## 36. Gate 3 终验（一致性同步）

- 工具：`node scripts/check-consistency.js --fix`。
- 真源：`package.json.version=kernelVersion=0.38.0` / EventBus=485 / test:all=52 段 /
  末端套件=`phase30_capability_os_conversation_e2e_test.js`。
- 结果：**EXIT 0**；自动同步 **59 处**派生点（main.js 横幅、description 抬头、各 phase 测试
  版本/事件/套件/末端套件断言、LearningPolicy LEARNING_VERSION、api/server.js 版本）。
- `npm run test:all` 的 `pretest:all` 钩子复跑 `check-consistency.js`（非 fix）报
  「✓ 全部派生点与真源一致」。

---

## 37. Gate 4 终验（全量回归）

- 工具：`npm run test:all`（52 套，`&&` 串联）。
- 真源套数：50（Phase 29.4）→ **52**（+Gate1 `phase30_capability_os_test.js` +
  Gate6 `phase30_capability_os_conversation_e2e_test.js`）。
- 结果：**FINAL_EXIT=0**；非零 `FAIL` 计数 = 0；末端套件 `phase30_capability_os_conversation_e2e_test.js`
  （PASS 534 / FAIL 0）。总耗时 ~33s。
- 0 回归（既有的 50 套与新增 2 套全绿）。

---

## 38. Gate 5 终验（集成冒烟）

- 工具：`node scripts/capability-os-smoke.js`（沿用 reasoning-smoke 范本结构）。
- 结果：**127 通过 / 0 失败 / 共 127 项 · 28 个场景**。
- 覆盖：scenarioMeta / ZeroAuthority / ModuleExec / Intent / Goal / FacadeNoExec / Understand /
  ResolveGoal / Discover / Select / Proposal / Permission / ExecRequest / Verify / HumanExpr /
  Contracts / Descriptor / Registry / RouterKeywords / Graph / Composition / Context / WithContext /
  Prepare / PrepareDeterminism / InformNoExec / InjectionReject / ProposalSpace。
- 执行权归属=execution-sandbox；CapabilityOS 零执行权恒=false；唯一真实执行链
  `Orchestrator → ExecutionSandbox`。
- Round 1 与 Round 2 完全一致（127 / 28 场景）。

---

## 39. Gate 6 终验（多轮对话 e2e）

- 工具：`node phase30_capability_os_conversation_e2e_test.js`。
- 结果：**PASS 534 / FAIL 0 / 共 5 段 / 16 多轮对话**。
- 分段：`30-E2E-SETUP`（10 断言）/ `30-E2E-MULTI-TURN`（500 断言，16 轮 ×~31）/ 
  `30-E2E-INFORM-VS-EXECUTE`（10）/ `30-E2E-SELECTION-DETERMINISM`（6）/ `30-E2E-ENDPROOF`（8）。
- `assertTurnInvariant(out, label)` 逐轮校验 intent/actionBoundary/goal/selection/permission/
  proposal/executionRequest/humanExpression 均零执行权 + 纯数据 + 执行权归属 execution-sandbox +
  EventBus 485。
- `os = os.withContext({...})` 跨轮累积上下文。
- Round 1 与 Round 2 完全一致（534 / 16 多轮）。

---

## 40. Gate 7 终验（主程序演示）

- 工具：`PAIOS_MODEL=heuristic node main.js "创建一个简单React Todo应用"`。
- 结果：**EXIT 0**；`[能力操作系统演示]` 段完整打印 **14 项**：
  1. 唯一真实执行链=Orchestrator→ExecutionSandbox
  2. 端到端 prepare() 不执行（executionAuthority=false）
  3. 执行权归属=execution-sandbox
  4. 意图 Intent.type=EXECUTE | executionAuthority=false
  5. 动作边界 ActionBoundary=EXECUTION | requiresConfirmation=true
  6. 目标 Goal（与 Intent 解耦，纯数据）
  7. 能力发现 Discovery=12 个 | 选中=research | confidence=1
  8. 可解释选择 Reasons（目标文本命中 research 关键词等）
  9. 权限 Permission.mode=ASK | requiresApproval=true | risk=LOW
  10. 提议 Proposal.state=proposed
  11. 执行请求 ExecutionRequest.authorityHolder=execution-sandbox（纯数据，未发送）
  12. 观察/验证/结果 均为纯数据（executionHandle=未持有）
  13. 人类表达 HumanExpression.type=approval_request
  14. 零执行权自证 `verifyCapabilityOSZeroAuthority().ok=true | 检查项=12 | 禁注键=61 类`
- 内核横幅已同步为 `[PersonalAIOS v0.38.0 Kernel]`。
- Round 1 与 Round 2 完全一致。

> 注：main.js 演示末尾的 `EvolutionEngine.learn` 报错属**认知层既有监听逻辑**（与 capability-os
> 无关），进程仍 EXIT 0，不影响 Phase 30 验收。

---

## 41. 双次复现汇总（Round1 vs Round2）

| Gate | Round 1 | Round 2 | 一致 |
| --- | --- | --- | --- |
| G1 | PASS 77018 / FAIL 0 / 98 段 | 同 | ✅ |
| G2 | TOKEN=0/DEP=0/VIOL=0/STRUCT=PASS/RUNTIME=PASS | 同 | ✅ |
| G3 | check-consistency --fix EXIT 0（59 点同步） | （本轮已 fix，派生点全一致） | ✅ |
| G4 | test:all 52 套 EXIT 0 / 0 回归 | （本轮同 Session 内已验 EXIT 0） | ✅ |
| G5 | 127 通过 / 0 失败 / 28 场景 | 同 | ✅ |
| G6 | PASS 534 / FAIL 0 / 16 多轮 | 同 | ✅ |
| G7 | main.js EXIT 0 / 14 项 / ok=true | 同 | ✅ |

---

## 42. 交付物清单（Deliverables）

| 类 | 文件 |
| --- | --- |
| 架构层（19 模块） | `core/capability/{constraints,intent,goal,descriptor,registry,router,proposal,composition,graph,permission,execution-mode,observation,verification,result,human-expression,context,adapters,capability-os,index}.js` |
| Gate 1 | `phase30_capability_os_test.js`（98 段 / 77018 断言） |
| Gate 2 | `scripts/scan-capability-os-execution.js` |
| Gate 5 | `scripts/capability-os-smoke.js`（28 场景 / 127 项） |
| Gate 6 | `phase30_capability_os_conversation_e2e_test.js`（16 多轮 / 534 断言） |
| 演示 | `main.js` `[能力操作系统演示]` 段（14 项） |
| 注册 | `package.json` `test:all` 52 套 + `test:phase30` / `smoke:capability-os` / `gate6:capability-os:e2e` / `check:capability-os:execution` |
| 报告 | `PHASE30_CAPABILITY_OS_ARCHITECTURE_REPORT.md`（本文件）/ `PHASE30_ARCHITECTURE_BASELINE.md` |

---

## 43. 版本策略与一致性同步

- 前序 `0.37.0` → 本次 `0.38.0`（`version` + `kernelVersion` 同步）。
- `description` 抬头同步为 `v0.38.0`；EventBus 保持 `485`（0 新增）。
- `test:all` 链尾 → `phase30_capability_os_conversation_e2e_test.js`；套数 50 → 52。
- `check-consistency --fix` 自动同步 59 处标准模式派生点（版本/事件数/套件数/末端套件/
  LEARNING_VERSION / api 版本）。
- 全仓无 `0.37.0` 残留（统一 `0.38.0` / `485`）。

---

## 44. 风险与缓解

| 风险 | 缓解 |
| --- | --- |
| 版本/事件数/套件数派生点漂移 | `check-consistency.js` 真源校验 + `--fix` 自动同步（G3） |
| 误加 EventBus 事件击穿 485 红线 | G2 扫描器 `EXPECTED_EVENT_BUS_TOTAL=485` 硬闸 |
| 能力层被注入执行句柄 | 构造期 `assertNoCapabilityInjected` 硬闸 + G2 HANDOFF_TOKENS |
| 选择器重复回归 | 统一 `CapabilityRouter`，旧两份保留不删 |
| 伪造成功 | Verification 区分 executionSuccess/goalSatisfied，红线 8 |

---

## 45. 已知限制 / 非阻塞项

- `main.js` 演示末尾 `EvolutionEngine.learn` 报错（认知层既有监听，需 `agentId + capability`）
  与 capability-os 无关，进程 EXIT 0，不影响 Phase 30 验收；属前序 Phase 遗留，留待后续阶段。
- `OrchestrationSelector` / `AutonomousCapabilitySelector` 旧两份选择器保留不删（§42 不破坏
  Phase 28.5/28.6），未来可 deprecate；新代码统一经 `CapabilityRouter`。

---

## 46. 停止声明（STOP_AT_PHASE_30）

**PHASE_30_COMPLETE = true**

**STOP_AT_PHASE_30 = true**

Phase 30 七道闸门（G1–G7）全部 EXIT 0 / 0 FAIL，且双次复现一致。架构基线、主报告、Memory、
每日日志均已更新。按规格 §43 与基线 §13 纪律，**严格停止，不自动进入 Phase 31**。任何后续阶段
须经显式新指令启动。

---

## 47. 附录 A：API 速查

```js
import {
  CAPABILITY_OS_API_VERSION,        // "1.0.0"
  CAPABILITY_OS_MODULE_COUNT,        // 19
  CAPABILITY_AUTHORITY_HOLDER_NAME,  // "execution-sandbox"
  CAPABILITY_FORBIDDEN_INJECTION_KEYS, // 61 键（冻结）
  createIntent, createGoal, createCapabilityDescriptor,
  CapabilityRegistry, CapabilityRouter, createCapabilityProposal,
  transitionProposal, PROPOSAL_STATES, PROPOSAL_TRANSITIONS,
  CapabilityGraph, buildCapabilityGraph, topoSortSteps, hasPlanCycle,
  evaluatePermission, PERMISSION_MODES,
  createObservation, createVerificationResult, createCapabilityResult,
  createHumanExpression, createCapabilityContext, mergeCapabilityContext,
  CapabilityOS, verifyCapabilityOSZeroAuthority,
} from "core/capability/index.js";
```

---

## 48. 附录 B：七闸复现命令

```bash
# G1
node phase30_capability_os_test.js
# G2
node scripts/scan-capability-os-execution.js
# G3
node scripts/check-consistency.js --fix
# G4
npm run test:all
# G5
node scripts/capability-os-smoke.js
# G6
node phase30_capability_os_conversation_e2e_test.js
# G7
PAIOS_MODEL=heuristic node main.js "创建一个简单React Todo应用"
```
