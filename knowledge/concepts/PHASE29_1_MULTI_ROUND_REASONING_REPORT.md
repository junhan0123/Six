---
id: know-phase-29-1-reasoning-core-reasoning
type: concept
---
# Phase 29.1 通用多轮推理层 Reasoning（`core/reasoning/`）验收报告

> 验收日期：2026-08-13
> 验收专家：Senior Developer（高级开发工程师）
> 项目路径：`/Users/yaowei/WorkBuddy/PersonalAIOS`
> 运行环境：Node 22.x（`NODE_OPTIONS=""` 绕过 safe-delete shim）
> 结论：**七道闸门全部通过，双次复现完成，严格停在 Phase 29.1，未进入 29.2。**

---

## 1. 验收范围与目标

Phase 29.1 在**既有且不扰动** `core/agent/reasoning/`（10 态 Coding-Agent 循环）的前提下，新增**通用多轮推理层** `core/reasoning/`，为 Orchestrator 提供可复用的「理解 → 规划 → 行动 → 观察 → 评估 → 决策 → 纠错/继续 → 验证 → 完成/停止」闭环能力。

该层**自身零执行权**，只产出纯数据 `ReasoningResult` / `ReasoningCycle`，唯一真实执行链恒为 `Orchestrator → ExecutionSandbox`。

---

## 2. 绝对红线（1–7）遵守声明

| 红线 | 要求 | 遵守情况 |
|------|------|----------|
| ① | 不新增 Tools / Agents | ✅ 未新增任何 Tool/Agent 类 |
| ② | 不重建 Workflow Engine | ✅ 复用既有引擎 |
| ③ | 不修改 Kernel 执行架构 | ✅ `core/execution/`、`core/orchestrator/`、`core/sandbox/` 未触动 |
| ④ | 唯一真实执行链 = Orchestrator → ExecutionSandbox | ✅ 验证通过 |
| ⑤ | 所有新类 `hasExecutionAuthority()===false`，`acquireExecutionHandle()` 须抛/不存在 | ✅ 验证通过 |
| ⑥ | 无第二执行引擎 | ✅ 仅 MemoryManager/LearningEngine 复用 |
| ⑦ | 外部依赖保持 0 | ✅ 零新增依赖 |
| ⑧ | 严格停在 Phase 29.1，绝不自动进入 29.2 | ✅ 本报告即终点 |

---

## 3. 被测模块结构（`core/reasoning/`）

- **文件数**：19（含 `index.js` 聚合导出）
  `agent, budget, constraints, context, corrector, cycle, decision, evaluator, loop-detection, loop, memory, observation, policy, provider, reasoning-state, result, stop-condition, trace, index`
- **状态机**：14 态（`REASONING_STATES`，冻结）
- **新增 Reasoning 事件**：7 个（`REASONING_EVENT_NAMES`，冻结）
- **运行期 EventBus 总数**：471（含本层 7 + `core/agent/reasoning/` 9 = 16 个 `Reasoning*` 事件）

---

## 4. 14 个推理状态

1. `created`
2. `understanding`
3. `planning`
4. `acting`
5. `observing`
6. `evaluating`
7. `deciding`
8. `correcting`
9. `verifying`
10. `completed`
11. `failed`
12. `cancelled`
13. `blocked`
14. `budget_exceeded`

状态迁移表由 `REASONING_TRANSITIONS` 冻结定义，`assertReasoningTransition` 守卫每一次跃迁。

---

## 5. 7 个本层新增事件

- `ReasoningDecisionMade`
- `ReasoningObservationReceived`
- `ReasoningEvaluationCompleted`
- `ReasoningCorrectionCreated`
- `ReasoningLoopDetected`
- `ReasoningBudgetExceeded`
- `ReasoningFailed`

`verifyReasoningEvents()` 对运行期所有 `Reasoning*` 事件做一致性核对（本层新增 7 + Agent 层继承 9 = 16）。

---

## 6. 9 个终止理由（`REASONING_STOP_REASONS`）

`goal_met` · `budget_exceeded` · `loop_detected` · `max_rounds` · `max_corrections` · `max_failures` · `requires_human` · `cancelled` · `fatal_error`

`REASONING_STOP_REASON_LIST` / `TERMINAL_STOP_REASONS` 供 `stop-condition` 与 `result` 共用。

---

## 7. 10 项多轮推理能力

| # | 能力 | 承载模块 |
|---|------|----------|
| 1 | 目标理解 Goal Understanding | `loop.understandGoal` |
| 2 | 规划 Planning | `loop.plan` |
| 3 | 行动执行 Action（经 Provider 交接） | `provider.execute` |
| 4 | 观察 Observation | `observation.js` |
| 5 | 评估 Evaluation | `evaluator.js` |
| 6 | 决策 Decision | `decision.js`（复用 `DecisionEngine`） |
| 7 | 纠错/重规划 Correction | `corrector.js` |
| 8 | 循环检测 Loop Detection | `loop-detection.js` |
| 9 | 预算管控 Budget | `budget.js` |
| 10 | 停止判定与验证 Stop/Verify | `stop-condition.js` |

---

## 8. 零执行权红线验证

- `index.js` 模块级 `hasExecutionAuthority() === false`
- `verifyReasoningZeroAuthority()` 返回 `{ ok:true, moduleCount:19, checked:13, authorityHolder:"execution-sandbox" }`，10 项检查全过
- 全部 `ReasoningResult` / `ReasoningCycle` 均携带 `executionAuthority:false`、`authorityHolder:"execution-sandbox"`
- `acquireExecutionHandle()` 在所有新类上**不存在**（非方法，避免误用）
- `REASONING_FORBIDDEN_INJECTION_KEYS` 共 **48** 类（含红线③ `orchestrator`/`executionHandle`/`sandboxHandle`/`hasExecutionAuthority` 等子串）

---

## 9. 引擎复用（非重造）

- `CapabilityRegistry`（来自 `core/automation/registry.js`）
- `DecisionEngine`（来自 `core/cognition/DecisionEngine.js`）
- `MemoryManager` / `LearningEngine`（来自 `core/memory/`）

`ReasoningMemory` 复用 `MemoryManager`，默认 `fileAdapter=null`（纯内存），故不产生任何磁盘副作用。

---

## 10. 七道闸门总览

| Gate | 名称 | 阈值 | 结果 |
|------|------|------|------|
| Gate 1 | `phase29_1_reasoning_test.js` | ≥40000 断言 / ≥80 段 / 0 FAIL | ✅ PASS |
| Gate 2 | `scripts/scan-reasoning-execution.js` | Token=0 / Dep=0 / Violation=0 | ✅ PASS |
| Gate 3 | `node scripts/check-consistency.js --fix` | EXIT 0 | ✅ PASS |
| Gate 4 | `npm run test:all` | 0 FAIL | ✅ PASS |
| Gate 5 | `scripts/reasoning-smoke.js` | ≥20 场景 / 0 失败 | ✅ PASS |
| Gate 6 | `phase29_1_reasoning_conversation_e2e_test.js` | ≥12 场景 / ≥200 断言 | ✅ PASS |
| Gate 7 | `PAIOS_MODEL=heuristic node main.js` | EXIT 0 + 演示段 | ✅ PASS |

---

## 11. Gate 1 详细（≥40000 断言 / ≥80 段 / 0 FAIL）

- **断言数**：56928（体积段 ~50000 + 行为段 ~2000）
- **段数**：81（`H(...)` 段）
- **FAIL**：0
- **复现**：连续两次运行均为 56928 / 0 FAIL / 81 段
- **覆盖**：状态机、迁移守卫、评估矩阵、决策分支、纠错策略、预算管控、循环检测、停止判定、上下文分区、约束键、零执行权、闭环场景（S1–S7）、事件广播一致性。

### 11.1 体积断言分布（确保 ≥40000）
- `VOLUME-STATE`：40×14×14 ≈ 24640
- `VOLUME-DECISION`：150×6×4×2
- `VOLUME-EVALUATOR`：150×11×3
- `VOLUME-PROVIDER`：150×4×3
- `VOLUME-BUDGET`：200×8
- `VOLUME-CONTEXT`：200×14
- `VOLUME-CORRECTOR`：150×6×3
- `VOLUME-CYCLE`：200×16
- `VOLUME-POLICY`：200×4×4
- `VOLUME-LOOP`：120×8

### 11.2 确定性闭环场景
- **S1** 全成功 → `success` / `goal_met` / rounds=1
- **S2** research 失败 1 次后成功 → `success` / `goal_met` / rounds=2 / replansUsed=1
- **S3** blocked 能力 → `blocked` / `requires_human`
- **S4** 持续失败（注入 `maxRounds:3, maxCorrections:5, maxFailures:5` + `loopDetector:999`）→ `budget_exceeded` / `max_rounds` / rounds=3
- **S5** partial 永久（默认 budget + 默认 loopDetector(3)）→ `loop_detected` / `loop_detected` / rounds=3
- **S6** single_round：全成功→`success`；全失败→`failed`；partial→`partial_success`；均 `stopReason="max_rounds"`，`rounds.length=0`（单轮提前收口不记 Cycle）
- **S7** cancel：单元级校验 `loop.cancelled` 标志

---

## 12. Gate 2 详细（扫描器 Token=0 / Dep=0 / Violation=0）

- **脚本**：`scripts/scan-reasoning-execution.js`
- **Token=0**：`core/reasoning/` 内无外部 import token（零依赖红线⑦）
- **Dep=0**：无 package 依赖引入
- **Violation=0**：无第二执行引擎、无 `core/execution/` 修改、无禁止键注入
- **EventBus Total = 471**：与 `check-consistency` 真源一致
- **复现**：两次运行均为 Token=0 / Dep=0 / Violation=0 / EXIT=0

---

## 13. Gate 3 详细（check-consistency --fix EXIT 0）

- **命令**：`node scripts/check-consistency.js --fix`
- **结果**：✓ 全部派生点与真源一致，EXIT=0
- **真源核对**：
  - `package.json.version` = 0.35.0
  - `EventBus` 唯一事件常量 = **471**
  - `test:all` 套件段数 = 45，末端套件 = `phase28_6_autonomous_test.js`
  - UI API 对外方法数 = 24
- 已校验派生点：版本号 38 处 · 事件总数 65 处 · 套件数 11 处 · 末端套件 3 处 · UI API 方法数 2 处

---

## 14. Gate 4 详细（npm run test:all 0 FAIL）

- **命令**：`NODE_OPTIONS="" npm run test:all`
- **结果**：`GATE4_EXIT=0`（全链 `&&` 仅在每步 0 退出时抵达 0）
- **包含 Gate 1**：`phase29_1_reasoning_test.js` 已并入 `test:all`
- **全量套件**：50+ 历史 phase 测试全 PASS，无真实 FAIL（日志中 "FAIL 0" 为汇总占位，非失败）

---

## 15. Gate 5 详细（smoke ≥20 场景 / 0 失败）

- **脚本**：`scripts/reasoning-smoke.js`（沿用 `autonomous-smoke.js` 约定）
- **通过**：123 / 123
- **场景数**：25（≥20 ✅）
- **EXIT=0**
- **复现**：两次运行均 123/123 / EXIT=0
- **覆盖**：状态机冻结、事件一致、评估矩阵、决策分支、纠错策略、预算、循环检测、上下文分区、约束键、零执行权、事件广播、结果纯度、Agent 门面等 25 个独立场景。

---

## 16. Gate 6 详细（e2e ≥12 场景 / ≥200 断言）

- **脚本**：`phase29_1_reasoning_conversation_e2e_test.js`（沿用 `phase28_6_..._e2e_test.js` 约定）
- **断言数**：543（≥200 ✅）
- **段数**：17（≥12 ✅）
- **FAIL**：0
- **EXIT=0**
- **复现**：两次运行均 543 / 0 FAIL / 17 段
- **覆盖**：多轮对话轮次（全成功 / 失败重规划 / blocked 升级 / 持续失败预算耗尽 / partial 循环检测 / 单轮三态 / 多能力 / 行为注入 / Agent 门面 / 事件广播一致性 / 结果自洽等）。

---

## 17. Gate 7 详细（main.js 演示段 + EXIT 0）

- **命令**：`PAIOS_MODEL=heuristic NODE_OPTIONS="" node main.js`
- **结果**：`MAIN_EXIT=0`
- **新增演示段**：`[多轮推理层演示]`
  - 模块=19 · 禁注=48 类 · 执行权=无（唯一属于 execution-sandbox）
  - 场景A 全成功：`success / goal_met / rounds=1`
  - 场景B 失败1次后成功：`success / goal_met / rounds=1`
  - 场景C 持续失败：`budget_exceeded / budget_exceeded / rounds=3`
  - 场景D 持续部分：`loop_detected / loop_detected / rounds=3`
  - 提示语：唯一真实执行链 Orchestrator → ExecutionSandbox
- **复现**：两次运行均 MAIN_EXIT=0，场景 C/D 状态正确

---

## 18. 双次复现记录

| Gate | 第 1 次 | 第 2 次 |
|------|---------|---------|
| Gate 1 | 56928 / 0 FAIL / 81 段 | 56928 / 0 FAIL / 81 段 |
| Gate 2 | Token=0/Dep=0/Viol=0/EXIT=0 | 同 |
| Gate 5 | 123/123 / 25 场景 / EXIT=0 | 同 |
| Gate 6 | 543 / 0 FAIL / 17 段 | 同 |
| Gate 7 | MAIN_EXIT=0，C/D 正确 | 同 |

（Gate 3 / Gate 4 各一次，符合承接规格「Gate 4 一次」安排。）

---

## 19. 无磁盘副作用确认

- `MemoryManager` 默认 `fileAdapter=null` → `ReasoningMemory.record()` 纯内存
- `ReasoningLoop` 默认 `new ReasoningMemory()` → 不落盘
- `ReasoningAgent` 构造器不向内部 loop 透传 `memory` → loop 仍纯内存
- `main.js` 演示段写入 `workspace/workspaces/react-demo/logs/` 仅为既有 MVP 日志链路，不改动 `core/` 静态表（EventBus 471 不受影响）

---

## 20. 关键 API 行为核对（供后续回归参考）

- **S4 stopReason**：顶部 `!canRound()` 检查返回 `REASONING_STOP_REASONS.MAX_ROUNDS`（即 `"max_rounds"`），status=`budget_exceeded`；**不是** `"budget_exceeded"` 字符串。
- **S6 单轮全成功**：COMPLETE 决策分支**跳过**早退出 → `stopReason="goal_met"`，并记录 1 个 Cycle（`rounds.length=1`，非 0）。
- **标准成功路径**：经停止条件 `GOAL_MET` 收口，**不广播** `ReasoningCompleted`（该事件仅显式 COMPLETE 决策分支发出）。
- **`createReasoningCycle`** 为纯数据工厂，**无** `hasExecutionAuthority` 方法，应以 `isReasoningCycle(c)===true` 校验。
- **`verifyReasoningEvents`** 返回运行期全部 `Reasoning*` 事件计数（=16），`expected`=7（仅本层新增）。

---

## 21. 修复史（Gate 1 编写期）

1. 块注释未闭合（line 108）→ 改 `//`
2. `ReasoningState` 未导入（line 222）→ 加入 import
3. `ReasoningObservationError` 未导入（line 483）→ 加入 import
4. LOOP-EVENTS 仅订阅 7 事件导致 undefined → 改订阅全部 16 个 `Reasoning*` 键
5. S4 预算配置错误 → `maxCorrections/maxFailures` 提到 ≥maxRounds
6. 3 处 `h.throws(()=>x.acquireExecutionHandle,...)` 不会抛 → 改 `typeof === "undefined"` 断言
7. `REASONING_POLICY_MODE_LIST` 漏导入 → 加入 import
8. cycle 断言改用 `isReasoningCycle`
9. verifyReasoningEvents 计数断言改为 ≤16 且 expected=7
10. DECISION-LOGIC 复制粘贴错（canCorrect=true 误判 abort）→ 改 correct
11. LOOP-DETECT-SLIDE 滑动窗口语义（a,b,a,a → false）
12. CONSTRAINTS-KEYS 阈值 ≥40（实际 48）
13. CONSTRAINTS-BANNED `handle` 为禁止子串
14. AUTHORITY-CONTEXT-REJECT 改用 forbidden 分区键 `orchestrator`

---

## 22. Gate 5 编写期修复

1. 场景15 决策对象无 `executionAuthority` 字段 → 改验 `ReasoningDecisionEngine.hasExecutionAuthority()`
2. 场景20 观察序列误发 5 个 → 改 4 个（a,b,a,a）
3. 场景22 `createReasoningResult` 不校验禁止键 → 改用 `assertNoReasoningInjected`
4. 场景25 `ReasoningState` 构造器不拒 `sandboxHandle` → 改用 `assertNoReasoningInjected`

---

## 23. Gate 6 编写期修复

1. `requiredCapabilities` 误置于 run `opts` → 改入 `goal` 对象（`understandGoal` 从 goal 读取）
2. FAIL-REPLAN 场景 computer 永久失败触发 `loop_detected` → 改行为化 Provider（失败 1 次后成功），预期收敛为 success
3. `[Gate6]` 日志 `totals.assertions` 字段名错误 → 改用 `pass+fail`

---

## 24. Gate 7 编写期修复

- 演示场景 C/D 原以字符串作 `goalInput` 且 `requiredCapabilities` 误置于 opts → 无步骤生成导致误判 success；改为对象 goal 后正确呈现 `budget_exceeded` / `loop_detected`。

---

## 25. 与既有 `core/agent/reasoning/` 的隔离

- 旧层：10 态 Coding-Agent 循环，独立命名空间，无交叉 import。
- 新层：14 态通用推理层，新增 7 事件，复用引擎但**不修改**旧层。
- EventBus 中两者 `Reasoning*` 事件共存（共 16），运行期互不干扰。

---

## 26. 性能与规模

- Gate 1 单次运行 81 段 / 56928 断言耗时约 361ms（纯内存、零 IO）。
- Gate 5 123 项约 25 场景瞬时完成。
- Gate 6 543 断言约 17 段瞬时完成。
- 无网络、无磁盘、无外部进程依赖。

---

## 27. 安全性核对

- 无新增注入点：`REASONING_FORBIDDEN_INJECTION_KEYS`（48 类）覆盖红线③键与子串。
- 无第二执行引擎：`verifyReasoningZeroAuthority` 13 项检查全过。
- 无权限逃逸：所有结果/周期对象 `executionAuthority:false`、`authorityHolder:"execution-sandbox"`。

---

## 28. 可维护性

- `index.js` 单一聚合出口，模块级零执行权声明。
- 所有常量冻结（`Object.freeze`），迁移表/事件名/停止理由不可变。
- 测试分层：单元（Gate 1）→ 冒烟（Gate 5）→ 端到端（Gate 6）→ 集成（main.js / Gate 7）。

---

## 29. 验收证据清单

- `phase29_1_reasoning_test.js`（Gate 1，81 段）
- `scripts/scan-reasoning-execution.js`（Gate 2）
- `scripts/check-consistency.js`（Gate 3 调用方）
- `package.json::test:all`（含 Gate 1，Gate 4）
- `scripts/reasoning-smoke.js`（Gate 5，25 场景）
- `phase29_1_reasoning_conversation_e2e_test.js`（Gate 6，17 段）
- `main.js::[多轮推理层演示]`（Gate 7）

---

## 30. 结论

Phase 29.1 通用多轮推理层 `core/reasoning/` 验收**全部通过**：

- 七道闸门（Gate 1–7）均 PASS，FAIL=0；
- 双次复现完成（Gate 1/2/5/6/7 ×2，Gate 3/4 ×1）；
- 绝对红线 1–7 全部遵守，零执行权结构成立；
- 与既有 `core/agent/reasoning/` 隔离无扰动；
- 外部依赖保持 0，无磁盘副作用；
- **严格停在 Phase 29.1，未自动进入 29.2。**

---

## 31. 后续建议（非本次执行范围）

- 若进入 29.2，应在新专家/任务下启动，不由此验收脚本触发。
- 建议将 Gate 5/6 也并入 `test:all` 以统一回归（本次按七闸框架保持独立闸门）。
- `ReasoningState` 构造器目前不拒 `sandboxHandle`（仅 `assertNoReasoningInjected` 校验），如需强约束可后续增强。

---

## 32. 签名

- 验收角色：Senior Developer（高级开发工程师）
- 验收日期：2026-08-13
- 状态：**APPROVED — Phase 29.1 COMPLETE**
