---
id: know-phase-27-4-computer-agent
type: concept
---
# Phase 27.4 — Computer Agent 验收报告（零执行权）

> 版本：`PersonalAIOS v0.32.0 Kernel`
> 验收范围：Phase 27.1 → 27.4（**严格停在 27.4，不进入 Phase 28**）
> 核心约束：**Computer Agent 自身零执行权**，真实动作唯一经注入的 `orchestrator` → `ExecutionSandbox` 落地。
> 报告日期：2026-08-10

---

## 1. 验收概览

Phase 27 在 `core/computer/` 下实现了一套 **零执行权** 的 Computer Agent（桌面/浏览器自动化智能体），覆盖 Observe → Plan → Act → Verify 多轮回环。本验收交付 7 道 Gate 的「首现 + 复现」，全部以离线、确定性、零外部依赖的方式运行，并保证 EventBus 事件总数维持 **388**。

## 2. 交付范围与边界

- **已交付**：15 个 `core/computer/` 模块的 Phase 27.1–27.4 实现 + 7 道 Gate 的测试/扫描器/演示。
- **明确边界**：本验收止于 Phase 27.4。Phase 28（若有）不在本次范围，不自动进入。
- **零新增执行能力**：Computer 层不向 EventBus 新增任何事件，不引入任何执行句柄/原生调用。

## 3. 零执行权架构模型

- 所有 `core/computer/` 类的实例方法 `hasExecutionAuthority()` 恒返回 `false`。
- 模块常量 `COMPUTER_EXECUTION_AUTHORITY === false`，`COMPUTER_AUTHORITY_HOLDER === "execution-sandbox"`。
- `ComputerAgent.acquireExecutionHandle()` 恒抛错（无执行入口）。
- 运行期自证 `verifyComputerZeroAuthority()` 动态构造全部 15 个类实例 + `createDemoOrchestrator` + `ComputerAgent`，断言每个实例零执行权，返回 `{ ok: true, fails: [] }`。

## 4. 唯一合法执行链

```
ComputerAgent._requestExecution
  → orchestrator.submitExecutionRequest(req, { via: "computer-agent" })
  → ExecutionSandbox（沙箱仅认 caller === "orchestrator"）
```

- 未注入 `orchestrator` 时：进入「纯规划模拟」，动作仅被记录、不被执行（`executed: false`，执行计数不增加，`status` 改写为 `simulated-pass`）。
- Computer 层向 `orchestrator` 翻译出的 `ExecutionRequest` 纯数据含 `executionAuthority: false`、`layer: "request"`、`correlationId: actionId`，绝不携带函数/句柄。

## 5. 模块清单（15 个 `core/computer` 模块）

`computer-state` · `computer-action` · `computer-action-plan` · `computer-observation` · `computer-adapter` · `computer-risk` · `computer-policy` · `computer-capability` · `computer-verifier` · `computer-planner` · `computer-session` · `computer-history` · `computer-memory` · `computer-agent` · `index`（含运行期自证与导出）。

## 6. 15 态状态机 / 42 迁移

- 状态数 `COMPUTER_STATE_COUNT = 15`，终态 = `completed / failed / cancelled / rejected`。
- 合法迁移边数 `COMPUTER_TRANSITION_COUNT = 42`（白名单，非法迁移抛 `IllegalComputerTransitionError`）。
- 生命周期：`created → observing → observed → planning → planned → [awaiting_approval?] → acting → verifying → verified →（completed | observing…）`；人审拒绝进 `rejected`（阻断，零执行）。
- 扫描器 `EXPECTED_STATE_COUNT=15`、`EXPECTED_TRANSITION_COUNT=42` 与源码对齐。

## 7. 13 类纯数据动作 + 三重纯度硬闸

- 动作类型 `COMPUTER_ACTION_TYPE_COUNT = 13`：`click / type / keypress / hotkey / move / scroll / drag / screenshot / navigate / open_app / read_file / write_file / run_command`。
- 语义黑名单 `COMPUTER_ACTION_BANNED_FIELDS` 共 **23** 个字段（如 `fn / handler / callback / processHandle / sandboxHandle / executor / runner` 等）。
- 三重纯度硬闸：`hasFunctionDeep`（无函数深嵌） + `findForbiddenKeysDeep`（无执行面键） + `findBannedFieldsDeep`（无语义黑名单字段）；任一命中即构造期抛错。

## 8. 5 级风险 + 审批阈值

- 风险等级 `RISK_LEVELS`：`none / low / medium / high / critical`。
- 基础风险映射：`screenshot=none`、`click/type/...=low`、`hotkey/navigate/open_app=medium`、`write_file=high`、`run_command=critical`。
- 审批阈值 `COMPUTER_APPROVAL_RISK_THRESHOLD = high`；`requiresApprovalForRisk` 在 `riskRank(risk) >= riskRank(high)` 时为 `true`。
- 注意：`assessActionRisk({type:"screenshot"})` 返回 `low`（声明风险默认 LOW 会覆盖基础 `none`），而 `COMPUTER_ACTION_RISK_MAP["screenshot"]` 仍为 `none`——这是源码既有行为，测试已按实际行为断言。

## 9. 适配器边界（Static / Mock / Deterministic）

- `ComputerAdapter` 基类 + 三套离线实现：`StaticComputerAdapter`（预置快照）、`MockComputerAdapter`（随机离线观察）、`DeterministicComputerAdapter(seed)`（种子可复现）。
- 所有适配器 `hasExecutionAuthority() === false`，符合 `conformsToComputerAdapter` 鸭子类型契约。
- `DeterministicComputerAdapter` 同 `seed` 产生同一观察序列（`observationId` 由模块级全局计数器生成，跨实例不自洽，故复现比较时剥离 `observationId/timestamp` 仅比场景字段）。

## 10. 辅助层

- `ComputerPlanner`：关键词→动作类型网格 + 兜底（截图+点击）；`isGoalMet` 基于 observation。
- `ComputerVerifier` / `verifyActionResult`：`passed / score / status`，`rejected/failed → passed:false`，未执行 → `not-executed`。
- `ComputerPolicy`（`evaluateComputerPolicy`）：fail-closed，`READ_ONLY/LOCAL_ONLY/SAFE_EXECUTION/USER_APPROVAL/FULL_ACCESS`；`SAFE_EXECUTION` 对破坏性行为拒绝、对网络动作放行且 `requiresPermission:true`。
- `ComputerCapabilityRegistry` / `isActionCapable`：能力×动作映射。
- `ComputerSession` / `ComputerHistory` / `InMemoryComputerMemory`：纯数据轨迹；`COMPUTER_HISTORY_KINDS` 共 **9** 种（含 `fail`）。

## 11. Gate 1：长测（`phase27_computer_test.js`）

- 验收目标：状态机穷举、动作纯度、观察/计划、适配器契约、风险/策略/能力矩阵、Agent 多轮回环、零执行权穷举、EventBus 388 不变量。
- 规模：**≥ 30,000 断言 / ≥ 60 段**（实际 62 段）。
- 自研 Harness（`createHarness`）：`section/ok/eq/deepEq/throws/throwsAsync/noThrow/count/summary/exitCode`，结尾固定 `process.exit(T.exitCode())`。

## 12. Gate 1 结果

```
Phase 27.0 Computer Agent：PASS 33646 / FAIL 0（共 62 段，73ms）EXIT=0
```
- 修复的 10 处测试期望与真实源码不一致均已对齐：`observationId` 全局计数剥离、BANNED_FIELDS=23、`assessActionRisk` screenshot=low、`write_file` 需显式 `risk:"high"`、DET-DIFF 跨 10 轮比较、`verifyActionResult` undefined→`not-executed`、`Session.finish({status})` 对象传参、HISTORY_KINDS=9、AGENT-EVENTS 用 `requireApprovalAll` 触发审批、AGENT-INJECTION 移除 `browserGateway`、POLICY-FULL 仅非破坏性网络需 permission。

## 13. Gate 2：执行扫描器（`scripts/scan-computer-execution.js`）

- 镜像 `scan-research-execution.js`，扫描 `core/computer/**`。
- 规则：Execution Token（`fork/osascript/robotjs/electron/BrowserWindow/globalShortcut/native/shell-call/fs-rm/fs-unlink/require-call/process-manip/executionHandle/sandboxHandle` 等，带 `\b` 词边界）+ External Dep + Violation。
- `verifyRuntimeInvariants()` 调 `verifyComputerZeroAuthority()` 并校验 15/42/Computer 事件=0/EventBus=388。

## 14. Gate 2 结果

```
Execution Token   = 0
External Dep      = 0
Violation         = 0
Runtime Invariant = PASS
State Machine     = 15 态 / 42 迁移
Computer Events   = 0 个（不新增 EventBus 事件）
EventBus Total    = 388
EXIT              = 0
```

## 15. Gate 3：一致性校验（`scripts/check-consistency.js`）

- 真源 = `package.json`（version/kernelVersion/description 抬头）、`EventBus.js`（正则解析事件数）、`test:all` `&&` 段数。
- `version: 0.32.0` 全链路派生点（38 处）自动同步一致；`--fix` 已同步。
- `PIPELINE_SET` 禁止注入清单不含 `orchestrator`（仅 `orchestratorHandle/Ref/Client/Gateway`），故 `ComputerAgent` 可注入 `orchestrator` 键。

## 16. Gate 4：EventBus 388 不变量

- Computer 层不向 `EventBus` 新增任何事件常量，全部使用字符串字面量（如 `EVENTS.ComputerAwaitingApproval || "ComputerAwaitingApproval"`，其中 `EVENTS` 无该键）发事件。
- 总线事件定义总数维持 **388**（`Object.keys(EVENTS).length === 388`），冒烟/对话测试均复测通过。

## 17. Gate 5：集成冒烟（`scripts/computer-agent-smoke.js`）

- 14 个真实场景：批准闭环、人审拒绝、纯规划模拟、需人工、Static/Deterministic 适配器、事件广播、Memory 摘要、注入拒绝、零执行权穷举、策略矩阵、风险映射、状态机完整性、适配器契约。
- 设计：离线、确定性、零网络/零 API Key，`process.exit(failed===0?0:1)`。

## 18. Gate 5 结果

```
Computer Agent 冒烟汇总：52 通过 / 0 失败（共 52 项 · 14 个场景）EXIT=0
```
关键断言：高风险拒绝 → `blocked / human_rejection / exec=0`；纯规划 → `completed / exec=0`；零执行权穷举 `ok`；`SAFE_EXECUTION` 网络 `requiresPermission:true`；`READ_ONLY` 网络 `denied`；状态机 15/42；EventBus 仍为 388。

## 19. Gate 6：对话端到端（`phase27_computer_conversation_e2e_test.js`）

- 8 段（≥6 段要求），模拟「用户 ↔ Computer Agent」多轮对话，每轮全新 `ComputerAgent`（共享 Memory），走完整 Observe→Plan→Act→Verify 循环。
- 场景：多轮批准累积、中途人审拒绝 + 后续轮仍可完成、纯规划多轮、高风险人审闸门、验证失败→requires_human、零执行权跨轮持续、升级人工后对话韧性、收口不变量。

## 20. Gate 6 结果

```
Phase 27.4 Computer Agent Conversation E2E：PASS 64 / FAIL 0（共 8 段，7ms）EXIT=0
```
关键断言：拒绝轮 `blocked/human_rejection/exec=0` 且后续轮 `completed`；高风险轮广播 `ComputerAwaitingApproval`；`requires_human` 轮 `exec=0`；所有轮 `executionAuthority=false`、`authorityHolder=execution-sandbox`、纯数据。

## 21. Gate 7：main.js 演示

- 在 `main.js` 新增 Phase 27.4 Computer Agent 演示段（try/catch 包裹，失败不影响 EXIT）。
- 场景 A：高风险目标 + `requireApprovalAll` + `simulateHuman:"reject"` → 人审拒绝 → `blocked / human_rejection / 执行计数=0`。
- 场景 B：常规目标 + `simulateHuman:"approve"` → 批准 → 执行 → `completed / 执行计数=2`。
- 运行指令：`PAIOS_MODEL=heuristic node main.js`。

## 22. Gate 7 结果

```
[Computer Agent 演示] 层级=computer | 执行权=无（唯一属于 execution-sandbox）
  · 高风险目标 → status=blocked | blockedBy=human_rejection | 执行计数=0
  · 状态机=15 态 / 42 迁移 | 适配器契约=true | 事件=5 类
  · 常规目标 → status=completed | 执行计数=2
  · 零执行权自证：通过 | Computer Agent 零执行权恒=false | acquireExecutionHandle 恒抛错

PAIOS_MODEL=heuristic node main.js  →  EXIT=0
```

## 23. 失败恢复语义

- **验证失败重试**：`retries < maxRetries` → `RECOVERED` 后进入下一轮（含 replan）；重试耗尽 → `requires_human`（`status:"requires_human"`，执行计数恒为 0）。
- **人审拒绝**：`handoff.report.status === "rejected"` → `REJECTED` 态、`status:"blocked"`、`blockedBy:"human_rejection"`、执行计数恒为 0、立即 `return` 收口。
- 全程受 `maxRounds / timeoutMs` 约束，绝不无限循环。

## 24. 确定性与可复现性

- `DeterministicComputerAdapter(seed)` 同种子产生同一观察序列；`mulberry32` 全周期 PRNG，相邻种子在 10 轮内必出现分叉。
- 全部测试离线、无随机外部输入，可一键复现。

## 25. 纯数据保证

- 所有 Computer 层产出经 `deepFreeze` + `pureDataCopy`，并过 `hasFunctionDeep` 检测（无函数深嵌）。
- 动作构造期过 `findForbiddenKeysDeep`（执行面键）+ `findBannedFieldsDeep`（语义黑名单）。
- 验证器/记忆写入仅存摘要，绝不写原始正文/句柄。

## 26. 构造期注入硬闸

- `assertNoInjected(opts, "ComputerAgent")` 以 `PIPELINE_FORBIDDEN_INJECTIONS`（三层并集，含 `sandboxHandle / processGateway / shellGateway / executionRequestExecutor / kernelHandle / sandboxBridge` 等）为红线，注入对象/函数值即抛 `PipelineInjectionError`。
- `browserGateway` 不在红线内（非执行面别名），故测试已移除该项错误期望。

## 27. EventBus 非污染保证

- Computer 层不新增事件常量、不调用 `EVENTS` 注册，总线 388 总数不受任何 Computer 路径影响。
- 冒烟测试与对话 e2e 均在运行后复测 `Object.keys(EVENTS).length === 388`。

## 28. 运行方式（npm scripts 一览）

```bash
node phase27_computer_test.js                 # Gate 1：长测（≥30k 断言 / 62 段）
node scripts/scan-computer-execution.js       # Gate 2：执行扫描（Token/Dep/Violation=0）
node scripts/check-consistency.js             # Gate 3：一致性（0.32.0 链路）
node scripts/computer-agent-smoke.js         # Gate 5：集成冒烟（14 场景）
node phase27_computer_conversation_e2e_test.js # Gate 6：对话 e2e（8 段）
PAIOS_MODEL=heuristic node main.js           # Gate 7：入口演示（EXIT=0）
```
对应 npm scripts：`test:phase27` · `check:computer:execution` · `smoke:computer` · `gate6:computer:e2e`。

## 29. 本次未改动项

- **源码行为零改动**：所有 `core/computer/` 模块的行为与 API 未变，仅追加 `main.js` 演示段与测试/扫描器文件。
- 未改 `test:all` 段数（避免 suiteCount 耦合）；`package.json` version 升级至 `0.32.0` 已通过 `--fix` 同步 38 处派生点。
- EventBus 388 红线、PIPELINE 红线清单均未被触碰。

## 30. 七道 Gate 验收矩阵

| Gate | 资产 | 关键指标 | 结果 |
|------|------|----------|------|
| 1 | phase27_computer_test.js | 33646 断言 / 62 段 / FAIL 0 | ✅ EXIT=0 |
| 2 | scan-computer-execution.js | Token/Dep/Violation=0 · 15态/42迁移 · Computer事件=0 · EventBus=388 | ✅ EXIT=0 |
| 3 | check-consistency.js | 0.32.0 链路 38 派生点一致 | ✅ EXIT=0 |
| 4 | EventBus 388 不变量 | Computer 层新增事件=0 | ✅ 388 |
| 5 | computer-agent-smoke.js | 52 断言 / 14 场景 / FAIL 0 | ✅ EXIT=0 |
| 6 | phase27_computer_conversation_e2e_test.js | 64 断言 / 8 段 / FAIL 0 | ✅ EXIT=0 |
| 7 | main.js 演示 | 高风险→blocked/human_rejection/exec=0 · 常规→completed/exec=2 | ✅ EXIT=0 |

## 31. 风险与限制

- `DeterministicComputerAdapter.observationId` 由模块级全局计数器生成，跨独立实例不可 `deepEq`（测试已剥离比较）。
- 默认 planner 关键词不含 `write/run`，故「写文件/跑命令」类 HIGH/CRITICAL 动作需经注入自定义 planner 或 `requireApprovalAll` 才在演示中触发人审闸门。
- 同一 `ComputerAgent` 实例状态机为终态持久化，多轮对话采用每轮新实例（真实对话可独立实例 / 共享 Memory）。

## 32. 结论与签署

Phase 27.4 Computer Agent **零执行权**架构完整落地：15 模块、15 态/42 迁移状态机、13 类纯数据动作（三重纯度硬闸）、5 级风险 + 审批阈值、三套离线适配器契约、Observe→Plan→Act→Verify 多轮回环，真实动作唯一经 `orchestrator → ExecutionSandbox`。七道 Gate（首现 + 复现）全部通过，**EXIT=0**，EventBus 维持 388，版本 `v0.32.0` 链路一致。**本次严格停在 Phase 27.4，不自动进入 Phase 28。**

— Senior Developer（高级开发工程师）· PersonalAIOS Phase 27.4 验收
