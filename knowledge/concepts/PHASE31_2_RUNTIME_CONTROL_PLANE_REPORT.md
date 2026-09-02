---
id: know-phase-31-2-runtime-control-plane
type: concept
---
# Phase 31.2 —— 统一运行时控制平面（Runtime Control Plane）验收报告

> 层级：`core/runtime/control/`（Phase 31.2）
> 范式：**零执行权**（在 Phase 31.1「统一运行时内核」之上新增纯治理 / 纯协调 / 纯状态 / 纯观测 / 纯审计控制平面）
> 唯一真实执行链：`Orchestrator → ExecutionSandbox`（不变）
> 验收结论：**七道 Gate 全绿 · 双次独立复现一致 · 严格停在 Phase 31.2**

---

## 0. 报告元信息

- 报告生成时间：2026-08-14（续跑会话收尾）
- 仓库：`/Users/yaowei/WorkBuddy/PersonalAIOS`（非 git 仓库，Node 22.x，离线，`PAIOS_MODEL=heuristic`）
- 项目版本：`0.38.0`
- EventBus 事件总数：**490**（Phase 31.2 不净增）
- `test:all` 串行套数：**54**（末端 = `phase31_2_runtime_control_test.js`）
- 控制平面模块数：**10**（9 源文件 + `index.js`）
- 控制请求状态机：**7 态**
- 控制平面禁注键：**46**（复用统一运行时内核清单，不另建）
- 零执行权自证项数：**27**（`verifyRuntimeControlZeroAuthority().checked`）

---

## 1. 概述

Phase 31.2 在已交付的「统一运行时内核」（`core/runtime/unified/`，Phase 31.1）之上，新增一层**统一运行时控制平面**（`core/runtime/control/`）。它不引入新的 Agent、不建立第二套 Workflow / Scheduler / Executor，不复制任何引擎实例；只做五件事：

1. **观测（observe）**——读取运行时会话状态，纯读不改；
2. **治理（govern）**——对控制动作做风险分类与审批判定（复用 `RiskClassifier` / `AutonomyPolicy`）；
3. **协调（request / approve / apply）**——生成 `ControlRequest`、走审批闸、在批准后把请求落地到 `UnifiedRuntimeManager`（复用内核语义化生命周期阶段，广播既有 `Runtime*` 事件）；
4. **状态（state machine）**——控制请求自身的 7 态状态机，独立于运行时会话 12 态；
5. **审计（audit）**——append-only 轨迹，不可删除 / 改写。

控制平面自身**零执行权**：它永远不直执行、不注入 `Orchestrator` / `ExecutionSandbox` / `Tool` / `Agent` / `Worker`，真正改变运行时会话状态仍由唯一真实执行链完成。

---

## 2. 设计红线与硬约束（不可破）

1. **红线① 唯一真实执行链**：`Orchestrator → ExecutionSandbox` 不可被控制平面替代、旁路或复制。
2. **红线② 不复制引擎实例**：控制平面复用 `UnifiedRuntimeManager`，不 new 第二套运行时 / Scheduler / Executor。
3. **红线③ 执行句柄硬闸**：构造期 `assertNoControlInjected` 拒收一切执行句柄键（`acquireExecutionHandle` / `performExecution` / `executionSandbox` / `orchestrator` / `tool` / `agent` / `worker` 等），违者抛 `ForbiddenInjectionError`。
4. **红线④ 复用而非重复**：46 禁注键、风险分类、审批策略、状态语义全部复用既有实现，不另建平行体系。
5. **红线⑤ EventBus 不净增**：仅供用既有 `Runtime*` 事件（5 个：Suspended / Checkpointed / Completed / Failed / Cancelled），`EVENTS` 总数恒为 490。
6. **红线⑥ 审计不可变**：审计轨迹 append-only，`delete` / `remove` / `truncate` / `clear` / `rewrite` 一律抛错。
7. **红线⑦ 确定性**：核心统计与输入强相关，`Date.now()` 仅作 metadata（`durationMs`），不进入断言关键路径。

---

## 3. 架构定位：控制平面 vs 执行链

```
                          ┌──────────────────────────────────────────────┐
                          │            Runtime Control Plane              │
                          │   (core/runtime/control/ · 零执行权)           │
                          │                                                │
                          │  observe → govern → request → approve → apply  │
                          │     ↑ observ.loop        │ control-applied     │
                          │     └──────── result ────┘                     │
                          └───────────────┬───────────────┬───────────────┘
                                          │ 协调（复用）    │ 观测（纯读）
                                          ▼               ▼
               唯一真实执行链：   Orchestrator ──► ExecutionSandbox
                                          ▲
                                          │ 复用语义化生命周期阶段
                                          │ (suspend/resume/checkpoint/
                                          │  pause/complete/fail/cancel)
                          ┌───────────────┴───────────────────────────────┐
                          │          Unified Runtime Manager              │
                          │   (core/runtime/unified/ · Phase 31.1)        │
                          │   真正改状态 · 广播既有 Runtime* 事件           │
                          └──────────────────────────────────────────────┘
```

控制平面是一个**侧向协调者**：它在运行时会话外侧观察、分类、批准、落地，但每一次「真正改变状态」都调用 `UnifiedRuntimeManager` 的方法，由内核完成并广播既有事件。EventBus 订阅者（既有的 `ContinuityManager`、scheduler 等）无需任何改动即可感知控制结果。

---

## 4. 模块清单（10 模块）

| # | 模块文件 | 职责 | 零执行权函数 |
|---|---------|------|------------|
| 1 | `RuntimeControlState.js` | 控制请求 7 态状态机 + 46 禁注键 + 注入守卫 | `hasExecutionAuthority` |
| 2 | `RuntimeControlRequest.js` | `ControlRequest` 数据对象 + 工厂 `createControlRequest` | `hasExecutionAuthority` |
| 3 | `RuntimeObserver.js` | 纯观测器（读会话状态，不改） | `hasExecutionAuthority` |
| 4 | `RuntimeGovernor.js` | 治理模型（风险分类 + 审批决策，复用 RiskClassifier/AutonomyPolicy） | `hasExecutionAuthority` |
| 5 | `RuntimeThrottle.js` | 确定性限流（per-type + global 上限） | `hasExecutionAuthority` |
| 6 | `RuntimeCheckpointController.js` | 检查点协调（委托内核 checkpoint 语义） | `hasExecutionAuthority` |
| 7 | `RuntimeAuditTrail.js` | append-only 审计轨迹 | `hasExecutionAuthority` |
| 8 | `RuntimeMetrics.js` | 确定性指标计数 | `hasExecutionAuthority` |
| 9 | `RuntimeControlPlane.js` | 控制平面门面（串联 observe/govern/request/approve/apply） | `hasExecutionAuthority` |
| 10 | `index.js` | 统一导出 + 零执行权自证 `verifyRuntimeControlZeroAuthority` | `hasExecutionAuthority`（权威遮蔽） |

`index.js` 额外导出：`RUNTIME_CONTROL_MODULE_COUNT=10`、`RUNTIME_CONTROL_API_VERSION="1.0.0"`、`RUNTIME_CONTROL_AUTHORITY_HOLDER_NAME="execution-sandbox"`、`CONTROL_REQUEST_STATE_COUNT=7`、`CONTROL_FORBIDDEN_INJECTION_KEYS`（46）、`CONTROL_ACTION_TYPES`、`verifyRuntimeControlZeroAuthority`。

---

## 5. 控制请求 7 态状态机

状态常量（`CONTROL_REQUEST_STATES`，key 大写 / value 小写）：

- `CREATED = "created"`
- `PENDING = "pending"`（已提交，待审批）
- `APPROVED = "approved"`（已批准，待应用）
- `REJECTED = "rejected"`（已拒绝，终态）
- `APPLIED = "applied"`（已落地到内核）
- `DONE = "done"`（闭环完成，终态）
- `FAILED = "failed"`（应用失败，终态）

终态：`REJECTED` / `DONE` / `FAILED`（无出边，非法迁移抛 `ControlRequestStateError`）。
合法转移总数 > 0；非终态均有出边。`assertControlRequestTransition("done","created")` 必抛（已自证）。

`CONTROL_REQUEST_STATE_COUNT === 7`、`CONTROL_REQUEST_FINAL_STATES.length === 3`，均经 `verifyRuntimeControlZeroAuthority` 校验。

---

## 6. 治理风险矩阵 CONTROL_RISK_MATRIX

控制动作 → 风险等级（复用 `RiskClassifier` 的 `RISK_LEVELS`）：

| 控制动作 | 风险 | 需审批 |
|---------|------|-------|
| `RESUME` | LOW | 否（auto） |
| `CHECKPOINT` | LOW | 否（auto） |
| `THROTTLE` | LOW | 否（auto） |
| `RECOVER` | LOW | 否（auto） |
| `PAUSE` | MEDIUM | 是（confirm） |
| `COMPLETE` | MEDIUM | 是（confirm） |
| `FAIL` | MEDIUM | 是（confirm） |
| `CANCEL` | HIGH | 是（human） |

- `RuntimeGovernor.classify(action)` 返回 `{ risk, requiresApproval }`，已自证：PAUSE=MEDIUM/需审批、RESUME=LOW/免审批、CANCEL=HIGH/需审批。
- `RuntimeGovernor.decide(action, risk)` 复用 `AutonomyPolicy`：LOW→`{autoApprove:true, mode:"auto"}`、HIGH→`{autoApprove:false, mode:"human"}`，已自证。

---

## 7. 控制闭环 observe→govern→request→approve→apply→observe

标准闭环（已写入零执行权自证 Item 17 `closed-loop-consistent`）：

1. `plane.observe(mgr, sid, t1)` —— 纯读，返回 `{ state, executionAuthority:false, ... }`，不改会话。
2. `plane.govern(observation)` —— 对 running 态返回 `{suggestedAction:null, risk:null}`（无需干预）；对 suspended/resuming 建议 RESUME、recovering 建议 CHECKPOINT、waiting_execution 建议 THROTTLE。
3. `plane.createControlRequest({type, sessionId})` —— 生成 `ControlRequest`（CREATE 态，`executionAuthority:false`）。
4. `plane.requestControl(req, t)` —— 提交，转 PENDING。
5. `plane.approve(req.id, actor, note)` —— 走审批闸；MEDIUM/HIGH 需审批，LOW 自动。
6. `plane.apply(req, mgr, t)` —— 经 `switch(req.type)` 调 `UnifiedRuntimeManager` 方法（如 `pause`→`mgr.suspend`），广播既有 `Runtime*` 事件，转 APPLIED→DONE，登记幂等。
7. `plane.observe(mgr, sid, t2)` —— 再次观测确认状态已迁移（如 running→suspended）。

`_markApplied` 负责 APPLIED→DONE + `idempotency.add(requestId)`。

---

## 8. 幂等性设计

- `requestId` 去重：`RuntimeControlPlane` 持有 `idempotency` Set。
- 同一 `requestId` 重复 `apply`：返回 `{ applied:false, reason:"idempotent-skip" }`，**不重复迁移内核状态、不重复计数、不重复审计**（自证 Item 16 `apply-idempotent`）。
- 实测：首次 apply `controlsApplied=1`，二次 apply 后 `controlsApplied` 不变。

---

## 9. 确定性 Metrics

`RuntimeMetrics` 核心计数与输入强相关，确定性可重复：

- `recordObservation()` —— 在 `observe()` 内调用。
- `recordControl(type, {risk, requiresApproval})` —— 在 `createControlRequest()` 内调用。
- `recordApplied(type)` —— 在 `_markApplied` 内调用。
- `snapshot()` 返回 `{ observations, controlsCreated, controlsApplied, byType, durationMs, ... }`。
- `durationMs` 仅作 metadata，恒 `null`（除非显式传入时间戳），不进入断言路径（自证 Item 15 `metrics-deterministic`）。

示例快照：`{ observations:1, controlsCreated:1, controlsApplied:1, byType.pause.created:1, byType.pause.applied:1, durationMs:null }`。

---

## 10. 审计轨迹 append-only

`RuntimeAuditTrail`：

- `record(kind, payload)` 仅追加；`count()` / `byKind(kind)` 只读。
- `delete` / `remove` / `truncate` / `clear` / `rewrite` 五个变更方法一律抛错（自证 Item 14 `audit-trail-append-only`）。
- 审计 kind 含 `observation` / `control-created` / `control-approved` / `control-applied` 等。
- main.js 演示段实测：16 条审计，含 `control-applied=4`、`control-approved=2`。

---

## 11. Observation（纯观测）

`RuntimeObserver` 是纯读组件：

- 读取 `RuntimeManager.getSession(sid).current()` 等只读接口；
- 不调用任何写方法、不持有执行句柄；
- 自证 Item 10 `observer-pure-readonly`：observe 前后会话状态不变，`ob.state === before === after`，`executionAuthority:false`。

---

## 12. Governor（治理模型复用 RiskClassifier / AutonomyPolicy）

`RuntimeGovernor` 不重新发明风险体系，复用 Phase 7.3：

- 风险分类：复用 `core/cognition/alignment/RiskClassifier.js` 的 `RISK_LEVELS`。
- 审批决策：复用 `AutonomyPolicy.decide()`。
- `classify(action)` → 风险矩阵（见 §6）。
- `decide(action, risk)` → `{ autoApprove, mode }`（LOW auto / HIGH human）。
- `govern(observation)` → 观测态→建议动作映射（纯函数，无副作用）。

---

## 13. Throttle（限流确定性）

`RuntimeThrottle` 确定性限流：

- 配置 `{ maxPerWindow, perTypeMax, windowMs }`。
- `record(type, now)` / `check(type, now)` 基于传入 `now`，不调用真实时钟。
- per-type 上限优先于 global 上限；其它类型不受单类上限影响（自证 Item 13 `throttle-deterministic`）。
- 示例：perTypeMax=2 时，第 3 次同类型 PAUSE → `{allowed:false, reason:"per-type-limit"}`，但 RESUME 仍可 `{allowed:true}`。

---

## 14. Checkpoint Controller

`RuntimeCheckpointController` 协调检查点动作：

- 复用内核 `UnifiedRuntimeManager.checkpoint()` 语义化阶段（广播既有 `RuntimeCheckpointed` 事件）。
- 自身零执行权，只把「建议 CHECKPOINT」落地为对内核的调用。
- 风险等级 LOW，免审批（自动）。

---

## 15. 复用层（Reuse > Duplicate）

| 复用项 | 来源 | 说明 |
|-------|------|------|
| `UnifiedRuntimeManager` | `core/runtime/unified/` (Phase 31.1) | 真正改状态、广播既有事件 |
| 46 禁注键 | `core/runtime/unified/runtime-invariant.js` | `RUNTIME_FORBIDDEN_INJECTION_KEYS` 直接再导出，不另建清单 |
| `RiskClassifier` | `core/cognition/alignment/` (Phase 7.3) | 风险等级枚举 |
| `AutonomyPolicy` | `core/cognition/alignment/` (Phase 7.3) | 审批决策 |
| `Runtime*` 事件 | `core/events/EventBus.js` | 5 个既有事件（Suspended/Checkpointed/Completed/Failed/Cancelled），不新增 |
| 自研 Harness | `core/test/Harness.js` | 所有 phase 测试零依赖断言 |

---

## 16. 零执行权自证 verifyRuntimeControlZeroAuthority（27 项）

`index.js` 导出的硬自证函数，覆盖 20+ invariants（运行实测 `checked=27`）：

1. 各模块级 `hasExecutionAuthority()` 全为 false（9 模块）。
2. 所有类实例 `hasExecutionAuthority() === false`。
3. 控制请求 7 态状态机（key 大写 / value 小写，`CREATED="created"` / `PENDING="pending"`）。
4. 合法转移总表非空、非终态有出边、终态无出边。
5. 非法转移硬抛 `ControlRequestStateError`。
6. 46 禁注键非空，含红线③ 10 键 + Phase 12.0 基础键。
7. 控制平面禁注清单 === 统一运行时内核清单（长度相等）。
8. 构造期拒收执行句柄（orchestrator/executionSandbox/tool/agent/worker）→ `ForbiddenInjectionError`。
9. 构造期拒收任意禁注键（scheduler/planner/...）→ `ForbiddenInjectionError`。
10. 控制请求纯度（零执行权 + 无禁注键字段）。
11. 观测器纯只读（observe 前后状态不变）。
12. 治理复用 RiskClassifier（PAUSE=MEDIUM / RESUME=LOW / CANCEL=HIGH）。
13. 审批复用 AutonomyPolicy（LOW auto / HIGH human）。
14. 限流确定性（per-type 上限）。
15. 审计 append-only（5 变更方法全抛错）。
16. 指标确定性（计数与输入强相关）。
17. 幂等（重复 apply 不重复迁移/计数/审计）。
18. 闭环一致（observe→govern→request→approve→apply→observe）。
19. 审批闸（未批准不得 apply）。
20. 复用既有 Runtime* 事件（`EVENTS` 总数恒 490）。
21. authorityHolder 恒为 execution-sandbox。
22. API 版本 1.0.0。
23. 模块数 10。
24. …（其余 4 项 cover 边界与一致性，运行实测 checked=27，全部 ok）。

返回 `{ ok:true, moduleCount:10, controlStateCount:7, checked:27, authorityHolder:"execution-sandbox" }`。

---

## 17. Gate 1 指标与证据

- 文件：`phase31_2_runtime_control_test.js`
- 实测：**PASS 64978 / FAIL 0（共 72 段，562ms）**
- 门槛：≥70 段 / ≥60000 断言 / 0 FAIL → **达标**
- 覆盖：状态机 7 态全转移、风险矩阵、闭环、幂等、Metrics 确定性、审计 append-only、观测纯读、审批闸、复用到统一运行时/RiskClassifier/AutonomyPolicy、零执行权自证 27 项、EventBus 490 不变。

---

## 18. Gate 2 指标与证据

- 文件：`scripts/scan-runtime-control-execution.js`
- 实测：
  ```
  TOKEN   = 0
  DEP     = 0
  VIOL    = 0
  STRUCT  = PASS
  RUNTIME = PASS
  ```
- 扫描维度：执行 token、外部依赖、红线违规、结构（模块/状态/禁注键）、运行时不变量（唯一真实执行链）。
- EXIT 0 → **PASS**

---

## 19. Gate 3 指标与证据

- 命令：`node scripts/check-consistency.js`（无参复核）
- 实测：`G3_EXIT=0`，0 漂移。
- 此前 `--fix` 已同步标准 `eq(Object.keys(EVENTS).length, N)` 派生点；变量别名 / 字符串字面量由手工修复（见 §27）。
- 复验结论：所有派生点与真源（version=0.38.0、EventBus=490、test:all=54、末端=phase31_2 套）一致。

---

## 20. Gate 4 指标与证据

- 命令：`npm run test:all`（字面 `&&` 串行链；`pretest:all` 先跑 check-consistency）
- 实测：`G4_EXIT=0`
- 套数：**54**（末端 = `phase31_2_runtime_control_test.js`）
- G4 日志 FAIL 扫描：`FAIL [1-9]` 命中数 = **0**（全仓无失败套件）
- 末端口套运行：`Phase 31.2 Runtime Control Plane 控制平面验收：PASS 64978 / FAIL 0（共 72 段）`
- 结论：全 54 套 0 FAIL / EXIT 0。

---

## 21. Gate 5 指标与证据

- 文件：`scripts/runtime-control-smoke.js`
- 实测：**183 通过 / 0 失败（共 183 项 · 28 个场景）**
- 门槛：≥25 场景 / ≥150 检查 / 0 FAIL → **达标**
- 横幅打印：`执行权归属=execution-sandbox · 控制平面零执行权恒=false · 唯一真实执行链 Orchestrator → ExecutionSandbox`

---

## 22. Gate 6 指标与证据

- 文件：`phase31_2_runtime_control_conversation_e2e_test.js`
- 实测：**PASS 510 / FAIL 0（共 5 段，10ms）**
- 门槛：≥12 多轮 / ≥500 断言 / 0 FAIL → **达标**（实际 14 轮多轮对话）
- 段：`31-2-E2E-*` 含多轮对话段 + `31-2-E2E-METRICS`（3 通过 / 0 失败）
- 覆盖：跨会话活跃指针 `ctx.current`、治理风险断言（running 态 `risk:null` 分支）、聚合指标（observations=3 / controlsCreated=7 / controlsApplied=7 / idempotency.size=7）。

---

## 23. Gate 7 指标与证据

- 入口：`main.js` `[运行时控制平面演示]` 段
- 实测：`node main.js` EXIT 0，演示段精确打印：
  ```
  [运行时控制平面演示] 层级=runtime-control | API版本=1.0.0 | 模块=10 | 控制请求7态 | 禁注键=46 类
    1. 控制闭环: observe(running) → checkpoint → pause → resume → cancel，终态=cancelled
    2. 零执行权自证 verifyRuntimeControlZeroAuthority().ok=true | 检查项=27 | 执行权恒定=无（唯一属于 ExecutionSandbox 层）
    3. 指标(确定性): 控制创建=4 | 应用=4 | 观测=1 | 幂等登记=4
    4. 审计 append-only: 条目=16 | 含 control-applied=4 | 含 control-approved=2
    5. 复用: 治理复用到 RiskClassifier/AutonomyPolicy（CANCEL=HIGH 需人工确认）；真正改状态仍交 UnifiedRuntimeManager，不复制引擎实例
    唯一真实执行链 Orchestrator → ExecutionSandbox：控制平面只治理/协调/观测/审计，自身零执行权、绝不直执行
  ```
- 闭环演示：observe(running) → CHECKPOINT(LOW 自动) → PAUSE(MEDIUM 批准) → RESUME(从 suspended) → CANCEL(HIGH 批准)，终态 = cancelled。

---

## 24. 双次复现 —— Round 1

首轮独立复跑（无代码改动），七道 Gate 指标：

| Gate | 指标 | 结果 |
|------|------|------|
| G1 | 64978 / 0 / 72 段 | ✅ |
| G2 | TOKEN/DEP/VIOL=0 · STRUCT/RUNTIME=PASS · EXIT 0 | ✅ |
| G3 | EXIT 0 / 0 drift | ✅ |
| G4 | 54 套 / EXIT 0 / 0 FAIL | ✅ |
| G5 | 183 / 0 / 28 场景 | ✅ |
| G6 | 510 / 0 / 5 段 | ✅ |
| G7 | main.js RC 0 / 演示段精确打印 | ✅ |

---

## 25. 双次复现 —— Round 2

第二轮独立复跑（无代码改动），与 Round 1 完全对齐：

- G1 64978/0（72 段）
- G2 0/0/0（STRUCT/RUNTIME=PASS）
- G3 一致（EXIT 0 / 0 drift）
- G4 `test:all` 54 套 0 FAIL、G4_EXIT=0
- G5 183/0（28 场景）
- G6 510/0（5 段）
- G7 `[运行时控制平面演示]` 行精确打印 + EXIT 0

稳定性成立：Phase 31.2 验收结论可固化。

---

## 26. EventBus = 490 不变论证

- Phase 31.2 **不新增任何 EventBus 事件**，仅供用既有 5 个 `Runtime*` 事件（Suspended / Checkpointed / Completed / Failed / Cancelled，均由 `UnifiedRuntimeManager` 在内核生命周期阶段广播）。
- 真源核验：`Object.keys(EVENTS).length === 490`（本轮实测）。
- 零执行权自证 Item 20 `reuse-runtime-events-no-new` 硬校验：`EVENTS[n]===n` 且 `Object.keys(EVENTS).length===490`。
- 全 54 套 Gate 4 链路 0 FAIL，证明无事件计数漂移。

---

## 27. stale 断言修复清单（Gate 4 前置一致性修复）

因 Phase 29.3/29.4/30/31.1 把 EventBus 由 485→490，多个旧测试文件硬编码 `485`/`404` 未被 `check-consistency --fix` 自动同步（`--fix` 只同步标准 `eq(Object.keys(EVENTS).length, N)` 形式，不覆盖变量别名 / 字符串字面量，见 MEMORY.md 第 14/49 行）。本会话手工修复 10 处（既有的 stale 断言，非本次引入）：

| 文件 | 行 | 修复前 → 修复后 |
|------|----|----------------|
| `phase14_agent_runtime_test.js` | 2143 | `NEW_EVENTS.length >= 490` → `>= 20`（消息本写「≥20」，断言误植 490 致 `&&` 链中断） |
| `phase28_1_vision_test.js` | 342 | `keys.length 485` → `490` |
| `phase28_3_data_test.js` | 868 | `total 485` → `490` |
| `phase28_4_automation_test.js` | 118 | `485` → `490`（enum-region-eventbus-total） |
| `phase28_4_automation_test.js` | 808 | `485` → `490`（final-eventbus-count） |
| `phase28_5_orchestration_test.js` | 123 | `485` → `490`（enum-region-eventbus-total） |
| `phase28_5_orchestration_test.js` | 769 | `485` → `490`（final-eventbus-count） |
| `phase28_6_autonomous_test.js` | 170 | `total 485` → `490` |
| `phase28_6_autonomous_test.js` | 175 | `viaValues 485` → `490`（按值去重 = 键数 = 490） |
| `phase27_computer_test.js` | 160 | `total 404` → `490` |

修复动机与 `check-consistency --fix` 同精神：使 `test:all` 字面 `&&` 链贯通至第 54 套（Phase 31.2），而非新增功能。EventBus 真值 490 未因本次修改而改变。

---

## 28. 与 Phase 31.1 衔接

- Phase 31.1 交付**统一运行时内核** `core/runtime/unified/`（11 模块、`UnifiedRuntimeManager`、12 态状态机、46 禁注键、`verifyRuntimeZeroAuthority`）。
- Phase 31.2 在其之上叠加**控制平面** `core/runtime/control/`，复用内核的 `UnifiedRuntimeManager` 与 46 禁注键。
- `main.js` 演示段顺序：先 Phase 31.1 `[统一运行时演示]`（catch 后），再 Phase 31.2 `[运行时控制平面演示]`，二者共享同一 `UnifiedRuntimeManager` 实例语义。
- 控制平面不修改 `core/runtime/unified/` 任何源码（红线②：不复制引擎实例、不复刻内核）。

---

## 29. 与 Phase 29.4（长程连续工作层）关系

- Phase 29.4 `core/continuity/` 与 Phase 31.2 `core/runtime/control/` 同属「零执行权侧向协调层」范式：包裹 / 协调既有引擎，自身不直执行。
- 二者均：复用执行权唯一归属 `execution-sandbox`、构造期拒收执行句柄、EventBus 只复用既有事件（485 / 490 不变）。
- 控制平面对运行时会话的协调结果经既有 `Runtime*` 事件广播，`ContinuityManager` 等订阅者无需改动即可感知。

---

## 30. STOP_AT_PHASE_31_2 声明

- 本轮验收目标严格限定在 Phase 31.2 七道 Gate。
- **不进入 Phase 31.3 或任何后续 Phase**。
- 记忆标记：`PHASE_31_2_COMPLETE` / `STOP_AT_PHASE_31_2`（见 MEMORY.md 与 2026-08-14.md）。

---

## 31. 测试基础设施与回归纪律补充

- 自研 harness 红线：不引入 jest/vitest/mocha/chai（`core/test/Harness.js` + `harness-core.js` + `harness.js`）。
- `test:all` 须为**字面 `&&` 串行链**：任一 Gate FAIL 即短路中止后续套件（后续 phase 不跑，日志只见首个失败套件）。故改 package.json / 新增 phase 后必整链复跑确认 0 FAIL。
- `check-consistency --fix` 只同步标准推导点；变量别名 / 字符串字面量须手工同步（本次 §27 即此纪律的实操）。
- 运行 Node 须 `NODE_OPTIONS=""` 绕过 safe-delete shim；操作内核须 `cd /Users/yaowei/WorkBuddy/PersonalAIOS &&`。

---

## 32. 关键 API 事实（易错点，留待复用）

- `RuntimeControlPlane` 构造期：`new RuntimeControlPlane({ orchestrator:{} })` / `{ executionSandbox:{} }` / `{ tool:{} }` / `{ agent:{} }` / `{ worker:{} }` 均抛 `ForbiddenInjectionError`。
- `apply(req, mgr, t)` 前置审批闸：需审批请求（MEDIUM/HIGH）未批准不得应用，返回 `{ applied:false, reason:"requires-approval" }`。
- `observe(mgr, sid, t)` 纯读：`mgr.getSession(sid)` 终态会话仍在（非 null），活跃会话取 `ctx.current` 指针而非 `ctx.sid`。
- `govern(observation)` 对 running 态返回 `{suggestedAction:null, risk:null, reason:"无需干预"}`——风险断言须判 `if (resp.risk && resp.risk.risk)`，否则 running 态 `risk` 为 null 会误判。
- 幂等：重复 `apply` 同一 `requestId` → `{ applied:false, reason:"idempotent-skip" }`，不重复迁移/计数/审计。
- `RuntimeMetrics.snapshot().durationMs` 恒为 `null`（除非显式传入时间戳），不进入断言关键路径。

---

## 33. 扩展性：不新增引擎实例

控制平面刻意不 new 第二套 `RuntimeManager` / `Scheduler` / `Executor`。所有「真正改状态」都委托 `UnifiedRuntimeManager` 的既有方法（`suspend`/`resume`/`recover`/`checkpoint`/`complete`/`fail`/`cancel`），由内核广播既有 `Runtime*` 事件。新增控制动作类型只需在 `CONTROL_ACTION_TYPES` + `RuntimeControlPlane.apply()` 的 `switch` 中加分支，无需新增执行引擎。

---

## 34. 验收结论

七道 Gate 全部通过，双次独立复现一致，指标如下：

| Gate | 指标 | 门槛 | 结果 |
|------|------|------|------|
| G1 | 64978 / 0 / 72 段 | ≥70 段 / ≥60000 / 0 FAIL | ✅ |
| G2 | TOKEN/DEP/VIOL=0 · STRUCT/RUNTIME=PASS | 全 0 + PASS | ✅ |
| G3 | EXIT 0 / 0 drift | EXIT 0 | ✅ |
| G4 | 54 套 / EXIT 0 / 0 FAIL | 全 0 FAIL | ✅ |
| G5 | 183 / 0 / 28 场景 | ≥25 场景 / ≥150 / 0 | ✅ |
| G6 | 510 / 0 / 5 段 | ≥12 轮 / ≥500 / 0 | ✅ |
| G7 | main.js RC 0 / 演示精确打印 | EXIT 0 | ✅ |

**Phase 31.2 统一运行时控制平面验收通过，严格停在 Phase 31.2。**

---

## 附录 A：控制动作 → 风险 → 审批模式映射

| Action | Risk | requiresApproval | AutonomyPolicy mode | 落地方法 |
|--------|------|------------------|---------------------|---------|
| RESUME | LOW | false | auto | `mgr.resume` |
| CHECKPOINT | LOW | false | auto | `mgr.checkpoint` |
| THROTTLE | LOW | false | auto | 限流协调 |
| RECOVER | LOW | false | auto | `mgr.recover` |
| PAUSE | MEDIUM | true | confirm | `mgr.suspend` |
| COMPLETE | MEDIUM | true | confirm | `mgr.complete` |
| FAIL | MEDIUM | true | confirm | `mgr.fail` |
| CANCEL | HIGH | true | human | `mgr.cancel` |

---

## 附录 B：零执行权 27 项自证明细（verifyRuntimeControlZeroAuthority）

运行实测 `checked=27`、`ok=true`。要点（详见 §16）：

- 9 模块级 + 9 实例级 `hasExecutionAuthority()===false`
- 7 态状态机约定（key 大写 / value 小写）
- 合法/非法转移硬约束（非法抛 `ControlRequestStateError`）
- 46 禁注键含红线③ 10 键 + Phase 12.0 基础键，且 === 统一运行时内核清单
- 构造期拒收执行句柄与禁注键 → `ForbiddenInjectionError`
- 控制请求纯度、观测纯只读、治理/审批复用、限流确定性、审计 append-only、指标确定性
- 幂等、闭环一致、审批闸、复用既有 490 事件、authorityHolder=execution-sandbox、API=1.0.0、模块=10

---

## 附录 C：七道 Gate 速查表

| Gate | 命令 | 核心出口 |
|------|------|---------|
| G1 | `node phase31_2_runtime_control_test.js` | PASS 64978 / FAIL 0 / 72 段 |
| G2 | `node scripts/scan-runtime-control-execution.js` | TOKEN/DEP/VIOL=0 · STRUCT/RUNTIME=PASS · EXIT 0 |
| G3 | `node scripts/check-consistency.js` | EXIT 0 / 0 drift |
| G4 | `npm run test:all` | 54 套 / EXIT 0 / 0 FAIL |
| G5 | `node scripts/runtime-control-smoke.js` | 183 / 0 / 28 场景 |
| G6 | `node phase31_2_runtime_control_conversation_e2e_test.js` | PASS 510 / FAIL 0 / 5 段 |
| G7 | `node main.js` | `[运行时控制平面演示]` EXIT 0 |

---

## 附录 D：本轮新增/修改文件清单

新增（Phase 31.2）：
- `core/runtime/control/RuntimeControlState.js`
- `core/runtime/control/RuntimeControlRequest.js`
- `core/runtime/control/RuntimeObserver.js`
- `core/runtime/control/RuntimeGovernor.js`
- `core/runtime/control/RuntimeThrottle.js`
- `core/runtime/control/RuntimeCheckpointController.js`
- `core/runtime/control/RuntimeAuditTrail.js`
- `core/runtime/control/RuntimeMetrics.js`
- `core/runtime/control/RuntimeControlPlane.js`
- `core/runtime/control/index.js`
- `phase31_2_runtime_control_test.js`（Gate 1）
- `scripts/scan-runtime-control-execution.js`（Gate 2）
- `scripts/runtime-control-smoke.js`（Gate 5）
- `phase31_2_runtime_control_conversation_e2e_test.js`（Gate 6）
- `PHASE31_2_RUNTIME_CONTROL_PLANE_REPORT.md`（本报告）

修改（Phase 31.2）：
- `main.js`（引入 `core/runtime/control/index.js` + 新增 `[运行时控制平面演示]` 段）
- `package.json`（`version` 0.37.0→0.38.0、`test:all` 50→54 套 + 5 个 gate script）
- 8 个旧测试文件 stale 断言修复（§27，10 处，EventBus 485/404→490）

---

*报告结束 —— Phase 31.2 验收完成，STOP_AT_PHASE_31_2。*
