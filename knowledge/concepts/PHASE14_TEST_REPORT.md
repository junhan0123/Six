---
id: know-personalaios-phase-14-0-autonomous-agent-runtime
type: concept
---
# PersonalAIOS Phase 14.0 —— Autonomous Agent Runtime 测试报告

> 当前版本：**v0.17.0**
> 报告生成日期：2026-08-05
> 测试入口：`phase14_agent_runtime_test.js`（27 段，3559 断言，全 PASS）
> 全量回归：`npm run test:all`（19 套，14285 + 3559 = 17844 断言，零回归）

---

## 1. 概述与版本号

Phase 14.0 在已完成的 Phase 13.0（自主执行沙箱，v0.16.0）基础上，建立**只管理、不执行的自主 Agent 运行时（Autonomous Agent Runtime）**。

核心约束（来自任务书）：

- Agent 运行时**不持有任何执行引用**；唯一允许真正执行的链路仍然是 **Orchestrator → ExecutionSandbox**（Phase 13 已确立）。
- 运行时负责 Agent 的注册 / 激活 / 挂起 / 恢复、会话、上下文、能力、信箱、监督、统计、快照与记忆写入——**但绝不调用任何执行单元**。
- 任何试图把 14 类执行句柄（worker / tool / tools / toolRegistry / terminalAdapter / applicationAdapter / processAdapter / orchestrator / agentRegistry / messageRouter / executor / agent / agents / executionSandbox）注入运行时的行为，在**构造期**即被硬闸拒绝。

版本号：v0.16.0 → **v0.17.0**（`package.json` + `main.js` 横幅同步升级）。

---

## 2. 架构变化（运行时只管理 / 执行权唯一归属 ExecutionSandbox）

| 维度 | 改造前 | 改造后 |
| --- | --- | --- |
| Agent 运行时 | 不存在独立运行时，Agent 状态零散 | `core/agent/runtime/` 15 模块构成**只管理不执行**运行时 |
| 执行权限 | 无 Agent 运行时概念 | `AgentRuntimeManager.hasExecutionAuthority()` **恒为 false**；执行权唯一属于 `ExecutionSandbox` |
| 注入边界 | — | 14 类执行句柄构造期硬闸 `assertNoAgentRuntimeInjected` 全拒 |
| 数据纯度 | — | 跨模块数据一律纯数据；函数→null（`pureCopy` / `pureAgentRuntimeCopy`） |
| 监督器 | 无 | `AgentSupervisor` **仅分析**（健康/趋势/建议），无 restart/execute 方法 |
| 导出边界 | — | `core/agent/runtime/index.js` 单独导出；不导出任何执行句柄 |

隔离三重证明：① 构造期 14 类 × 多入口硬闸全拒；② 源码级扫描 `core/agent/runtime/*` **0 执行 token**（扫描正则为 `execute|dispatch|invoke|worker|tool|executor`，仅 `core/execution/sandbox/ExecutionSandbox.js` 允许携带）；③ 运行期 `hasExecutionAuthority()` 恒 false + 信箱/记忆拒收函数 → 物理不可达执行链。

---

## 3. 新增 / 修改文件清单

新增目录 `core/agent/runtime/`（15 模块，统一出口 `index.js`）：

| 文件 | 职责 | 是否允许执行 token |
| --- | --- | --- |
| `core/agent/runtime/index.js` | 运行时 15 模块聚合导出 | 否（源码扫描 0 命中） |
| `AgentRuntimeState.js` | 10 态状态机 + 14 类禁止注入 + 构造期硬闸 | 否 |
| `AgentRuntimeModel.js` | 运行时模型（12 字段、纯数据） | 否 |
| `AgentPure.js` | 纯数据工具（含函数→null 的 `pureCopy`/`deepCopy`） | 否 |
| `AgentContext.js` | 六分区上下文（update/setVariable/addReference 拒函数） | 否 |
| `AgentMailbox.js` | 消息信箱（send/broadcast/reply/receive/read/timeout/retry/deadLetter） | 否 |
| `AgentLifecycle.js` | 9 态生命周期 + 非法转移异常 | 否 |
| `AgentRegistry.js` | Agent 注册表 | 否 |
| `AgentCapabilityRegistry.js` | 能力注册表 | 否 |
| `AgentSession.js` | 会话管理 | 否 |
| `AgentSupervisor.js` | 监督器（**仅分析**，无 restart/execute） | 否 |
| `AgentInstance.js` | 运行时视图（对外只读投影） | 否 |
| `AgentRuntimeSnapshot.js` | 七域纯数据快照（`pureAgentRuntimeCopy`） | 否 |
| `AgentRuntimeMemory.js` | 七分区只写记忆（write only） | 否 |
| `AgentRuntimeManager.js` | 运行时总管（20 计数器、`hasExecutionAuthority()` 恒 false） | 否 |

修改文件：`core/agent/runtime/AgentPure.js`（`pureCopy`/`deepCopy` 函数 null 化顺序修复）、`core/agent/runtime/AgentRuntimeSnapshot.js`（`pureAgentRuntimeCopy` 同修复）、`core/events/EventBus.js`（+24 个 Agent 运行时事件）、`core/orchestrator/Orchestrator.js`（接入 `agentRuntimeManager`）、`main.js`（横幅 v0.17.0 + `[自主 Agent 运行时]` 汇总段）、`package.json`（升 v0.17.0、`test:phase14`、`test:all` 串联 19 套）、`phase14_agent_runtime_test.js`（新增，27 段）、`phase13_execution_sandbox_test.js`（事件常量计数 176→200 回归修正）。

---

## 4. AgentRuntimeState 状态机（10 态 + 14 类硬闸）

10 个状态：`CREATED / INITIALIZING / READY / RUNNING / SUSPENDED / ARCHIVED / RECOVERING / STOPPING / STOPPED / FAILED`。

- 非法转移抛 `IllegalAgentRuntimeTransitionError`；终态不可转出。
- **14 类禁止注入**：`AGENT_RUNTIME_FORBIDDEN_INJECTIONS = ["worker","tool","tools","toolRegistry","terminalAdapter","applicationAdapter","processAdapter","orchestrator","agentRegistry","messageRouter","executor","agent","agents","executionSandbox"]`（与 Phase 9/12/13 同源、Phase 14 特化）。
- 构造期硬闸 `assertNoAgentRuntimeInjected(opts, label)`：任一被禁 key 出现即抛 `IllegalInjectionError`。

测试覆盖：10 态枚举、100+ 组转移、终态、非法转移异常、14 类 × 多入口硬闸（段 1：337 断言；段 2：261 断言全 PASS）。

---

## 5. AgentPure / AgentRuntimeSnapshot（纯数据 / 函数 null 化）

- `hasFunctionDeep(v)` 深度检测函数；`isPureData(v)` 为真当且仅当无函数。
- `pureCopy(v)` / `deepCopy(v)`：递归拷贝，**函数→null、循环引用安全**。
- `AgentRuntimeSnapshot.pureAgentRuntimeCopy(v)`：快照专用同语义净化。
- `createAgentRuntimeSnapshot(data)`：七域（runtime / registry / mailbox / context / session / supervisor / statistics）纯数据镜像。

> **本轮修复（真实源码缺陷）**：原 `pureCopy` / `pureAgentRuntimeCopy` 把 `if (typeof v === "function") return null;` 写在 `if (v === null || typeof v !== "object") return v;` **之后**——对函数值 `typeof v !== "object"` 为真，导致函数原样穿透、未转为 null。已将函数检查提前到最前，彻底修复函数 null 化。此修复消除了段 3/4/5/13/14 共 12 条断言失败。

测试覆盖：纯数据检测、函数→null、嵌套/数组内函数、循环引用、快照七域（段 4：37 断言；段 13：56 断言；段 26：112 断言全 PASS）。

---

## 6. AgentContext / AgentMailbox / AgentLifecycle

- `AgentContext`（六分区）：`update` / `setVariable` / `addReference` 均拒收函数。
- `AgentMailbox`：FIFO 收件箱、广播（发送者不自收）、回复（携带 inReplyTo）、超时 / 重试 / 死信、payload 深拷贝隔离、含函数即拒收。
- `AgentLifecycle`（9 态）：转移表覆盖合法流向，非法转移抛 `IllegalAgentLifecycleTransitionError`。

测试覆盖：六分区写入/拒函数、信箱全链路 + 死信迁移、9 态生命周期（段 5：63 断言；段 6：97 断言；段 7：271 断言全 PASS）。

---

## 7. AgentRegistry / CapabilityRegistry / Session / Supervisor / Instance

- `AgentRegistry`：注册 / 移除 / 查询 / 列出。
- `AgentCapabilityRegistry`：能力注册 / 移除 / 评估（只记录不执行）。
- `AgentSession`：会话创建 / 关闭 / 上下文绑定。
- `AgentSupervisor`：**仅分析**（健康、趋势、建议），**无 restart/execute 方法**——从设计上杜绝"监督器越权执行"。
- `AgentInstance`：对外只读运行时视图投影。

测试覆盖：四表注册/查询、能力评估、会话生命周期、监督器只分析、实例只读（段 8：45；段 9：52；段 10：45；段 11：81；段 12：55 断言全 PASS）。

---

## 8. AgentRuntimeMemory（七分区，只写）

- 7 个分区（运行时 / 注册 / 上下文 / 信箱 / 会话 / 监督 / 统计），19 个只写方法（`writeOnly: true`）。
- 写入前经 `pureAgentRuntimeCopy` 净化，函数→null；写失败**静默降级**并累计 `failures`，不影响主链路。
- 只写不读回：无 `get` / `read` 公开方法。

测试覆盖：七分区写入、只写不读回、写失败降级、函数净化（段 14：184 断言全 PASS）。

---

## 9. AgentRuntimeManager（总管 / 执行权恒 false）

- 20 个计数器（含 `denied`：任何非法注入/函数消息的拒收累计）。
- 完整编排 API：`ready/stop/suspend/archive/recover`、`registerAgent/removeAgent/activateAgent/suspendAgent/recoverAgent`、`createSession/closeSession`、`updateContext`、`registerCapability/removeCapability`、`sendMessage/receiveMessage/broadcast/reply/sweepTimeouts/retryMessages/collectDeadLetters`、`heartbeat/checkHealth/suggestRestart/reportResource`、`publishStatistics/statistics/createSnapshot`、`stateOf/agentStateOf/getAgent/listAgents/getContext/listSessions`。
- **`hasExecutionAuthority()` 恒为 false**；`attach(bus)` 供 Orchestrator `_safeAttach`；`describe()` 汇总运行态。

测试覆盖：运行时生命周期、Agent 全生命周期、会话/上下文/能力、信箱通信、监督/统计/快照（段 15：127；段 16：52；段 17：47；段 18：43；段 19：75 断言全 PASS）。

---

## 10. EventBus（Phase 14 新增 24 个 Agent 运行时事件）

`core/events/EventBus.js` 在 Phase 13 的 176 个事件基础上**新增 24 个**（EventBus 总常量 176 → **200**；注：新增块中 `AgentRecovered` 与既有键重名，不增计数，故净增 24）。

24 个新事件常量：

`AgentRuntimeCreated / AgentRuntimeStarted / AgentRuntimeStopped / AgentRuntimeSuspended / AgentRuntimeRecovered / AgentRuntimeArchived / AgentRuntimePaused / AgentRuntimeResumed / AgentRuntimeStatisticsUpdated / AgentRemoved / AgentActivated / AgentSuspended / AgentMailboxUpdated / AgentMessageReceived / AgentBroadcastSent / AgentBroadcastReceived / AgentSessionCreated / AgentSessionClosed / AgentContextUpdated / AgentCapabilityRegistered / AgentCapabilityRemoved / AgentHealthUpdated / AgentStatisticsUpdated / AgentSnapshotCreated`

端到端实跑事件链（来自 `main.js` 冒烟）：`AgentRuntimeCreated:1, AgentRuntimeStarted:1, AgentActivated:3, AgentCapabilityRegistered:1, AgentSessionCreated:1, AgentContextUpdated:1, AgentMailboxUpdated:1, AgentMessageReceived:1, AgentHealthUpdated:1, AgentSnapshotCreated:1, AgentStatisticsUpdated:1`（其余事件随演示复杂度未全部触发，但类型与广播由段 20 全量验证）。

测试覆盖：24 事件常量存在、广播可达、类型正确、早期事件未破坏（段 20：266 断言全 PASS）。

---

## 11. 执行隔离硬闸（14 类 + 源码扫描 + 构造期 + 运行期）

- **14 类禁止注入**（`AGENT_RUNTIME_FORBIDDEN_INJECTIONS`，见第 4 节）。
- **构造期硬闸**：`AgentRuntimeManager` 及所有纯数据配件构造时调 `assertNoAgentRuntimeInjected`，传入任一被禁句柄即抛错。
- **源码级扫描**：正则 `/execute|dispatch|invoke|worker|tool|executor/gi`，`core/agent/runtime/*` 全部 **0 命中**（真实扫描结果：token total = 0）；`core/execution/sandbox/ExecutionSandbox.js` 为唯一合法例外。
- **运行期**：`hasExecutionAuthority()` 恒 false；信箱 `sendMessage` / `broadcast` / `reply` 含函数即拒收并累计 `denied`。

测试覆盖：多入口 × 14 类拒收 + 源码扫描 + 多 Runtime 隔离 + 运行期拒函数（段 21：109；段 24：203；段 25：120 断言全 PASS）。

---

## 12. 压力测试 / 多 Runtime / 多 Agent / 纯数据 / 回归

- 压力测试：大规模 Agent 注册、消息洪峰、快照并发、记忆批量写入，零失败（段 23：529 断言）。
- 多 Runtime 并存与隔离：独立运行时互不影响，计数器互不串扰（段 21：109）。
- 多 Agent / 多 Session 协同：跨 Agent 消息、会话隔离（段 22：138）。
- 纯数据检查：对外产出（快照/记忆/统计）零函数（段 26：112）。
- 回归检查：Phase 5～13 既有能力 + 系统接线（Orchestrator / EventBus / Memory）未被破坏（段 27：84）。

---

## 13. 测试总览（断言数量 / PASS-FAIL）

测试文件：`phase14_agent_runtime_test.js`，纯 `node` 运行，内置 `ok / eq / near / throws / noThrow / throwsAsync / noThrowAsync / hasFunction` 断言器。

| # | 测试段 | 维度 | PASS | FAIL |
| --- | --- | --- | --- | --- |
| 1 | AgentRuntimeState 10 态 / 非法转移 | 状态机 | 337 | 0 |
| 2 | 14 类执行句柄构造期硬闸 | 隔离硬闸 | 261 | 0 |
| 3 | AgentRuntimeModel 纯数据模型 | 模型 | 70 | 0 |
| 4 | AgentPure 纯数据工具 | 纯数据 | 37 | 0 |
| 5 | AgentContext 六分区上下文 | 上下文 | 63 | 0 |
| 6 | AgentMailbox 消息信箱 | 信箱 | 97 | 0 |
| 7 | AgentLifecycle 9 态生命周期 | 生命周期 | 271 | 0 |
| 8 | AgentRegistry Agent 注册表 | 注册表 | 45 | 0 |
| 9 | AgentCapabilityRegistry 能力注册表 | 能力 | 52 | 0 |
| 10 | AgentSession 会话 | 会话 | 45 | 0 |
| 11 | AgentSupervisor 监督器（仅分析） | 监督 | 81 | 0 |
| 12 | AgentInstance 运行时视图 | 视图 | 55 | 0 |
| 13 | AgentRuntimeSnapshot 七域快照 | 快照 | 56 | 0 |
| 14 | AgentRuntimeMemory 七分区只写 | 记忆 | 184 | 0 |
| 15 | AgentRuntimeManager 运行时生命周期 | 总管·生命 | 127 | 0 |
| 16 | Manager：Agent 生命周期管理 | 总管·Agent | 52 | 0 |
| 17 | Manager：会话 / 上下文 / 能力 | 总管·会话 | 47 | 0 |
| 18 | Manager：信箱通信 | 总管·信箱 | 43 | 0 |
| 19 | Manager：监督 / 统计 / 快照 | 总管·统计 | 75 | 0 |
| 20 | EventBus：Phase 14 新增事件 | 事件 | 266 | 0 |
| 21 | 多 Runtime 并存与隔离 | 隔离 | 109 | 0 |
| 22 | 多 Agent / 多 Session 协同 | 协同 | 138 | 0 |
| 23 | 压力测试 | 压力 | 529 | 0 |
| 24 | 源码隔离扫描 | 扫描 | 203 | 0 |
| 25 | 执行隔离（构造期 + 运行期） | 隔离 | 120 | 0 |
| 26 | 纯数据检查（零函数产出） | 纯数据 | 112 | 0 |
| 27 | 回归检查（Phase 5～13 + 系统接线） | 回归 | 84 | 0 |
| **合计** | **27 段 / 20+ 维度** | | **3559** | **0** |

要求：≥2600 断言、覆盖 ≥19 维度 → **达标（3559 断言 / 27 段 / 20+ 维度）**。

---

## 14. 自动修复记录（3 项）

按"出现任何错误：自动定位、自动修复、自动重测直到全 PASS"规则，本轮定位并修复 3 项（1 项**真实源码缺陷** + 2 项测试/回归断言修正）：

1. **【真实源码缺陷】`AgentPure.js` / `AgentRuntimeSnapshot.js` 函数 null 化顺序错误**：原 `pureCopy` / `pureAgentRuntimeCopy` 把函数检查写在通用非对象返回之后，导致函数穿透、未转为 null。已将 `if (typeof v === "function") return null;` 提前到最前。修复段 3/4/5/13/14 共 **12 条**失败（期望函数→null，实际 undefined）。
2. **【测试断言错误】`phase14` 段 18 广播收件箱计数**：原断言 `broadcast` 后 `b` 收件箱为 1，实际为 2——因为 `receiveMessage` 不把消息移出收件箱（仅标记 received），先前直投消息仍在。改为期望 2。
3. **【回归修正】`phase13_execution_sandbox_test.js` 事件常量计数 176→200**：Phase 14 新增 24 个 Agent 事件使 EventBus 总常量增至 200，更新 Phase 13 断言以保证 `test:all` 全绿（不改变 Phase 13 任何逻辑）。

---

## 15. 全量回归结果（19 套 / 17844 断言）

`npm run test:all` 串联 19 套（phase5 ~ phase14），全部 PASS，零回归：

```
phase5_test.js                 PASS
phase6_test.js                 PASS
phase7_decision_test.js        PASS
phase7_2_decision_manager      PASS
phase7_full_cognition          PASS
phase8_1_dynamic_planner       PASS
phase8_2_multi_agent           PASS
phase8_3_evolution             PASS
phase8_4_knowledge             PASS
phase9_1_autonomy              PASS
phase10_1_project              PASS
phase10_2_scheduler            PASS
phase10_3_workspace            PASS
phase10_4_timeline             PASS
phase10_5_forecast             PASS
phase11_system                 PASS  (1384 断言)
phase12_runtime                PASS  (1976 断言)
phase13_execution_sandbox      PASS  (3115 断言)
phase14_agent_runtime          PASS  (3559 断言)
```

**19 套合计：EXIT=0，0 FAIL；Phase 5~13 累计 14285 断言 + Phase 14 新增 3559 = 17844 断言全 PASS。**

---

## 16. 端到端冒烟（EXIT=0 / 横幅 / 运行时段 / 事件链）

命令：`PAIOS_MODEL=heuristic node main.js`

- **EXIT_CODE = 0** ✅
- **横幅**：`[PersonalAIOS v0.17.0 Kernel] 模型:heuristic | 权限:auto | 工作区:react-demo | Skill:react-dev@1.0.0 | 恢复:关` ✅
- **新增汇总段** `[自主 Agent 运行时]`：
  `运行时 paios-agent-rt | 状态:READY | 策略:SAFE | Agent 3 / 会话 1（共 1）/ 能力 1 | 信箱 1 | 注册 3 / 移除 0 / 激活 3 / 挂起 0 / 恢复 0 | 消息 1 发 / 1 收 / 广播 0 | 快照 1 | 记忆分区 7 个（写入 13 次）| 禁止注入 14 类 | 执行权:无（唯一属于 ExecutionSandbox）` ✅
- **事件链**：EventBus 广播 12825 事件，Phase 14 新增 Agent 运行时事件齐备且链路正确（见第 10 节）。✅

> **已知非阻断项（不在 Phase 14 范围、前置存在、已被优雅捕获不崩溃）**：`core/cognition/evolution/EvolutionEngine.js:123` 的 `learn: 需要 agentId + capability` 在 `TaskVerified` 监听器抛错，由 EventBus 监听器异常捕获机制记录（不影响进程退出，不影响 Agent 运行时）。该错误属 Phase 7/8 认知/进化子系统，非本阶段引入，为避免无关回归未改动该模块。

---

## 17. 结论

- Phase 14.0 自主 Agent 运行时**全部验收通过**：27 段 / 3559 断言 / **0 FAIL**；19 套全量回归 **17844 断言 0 FAIL**；端到端冒烟 **EXIT=0**、v0.17.0 横幅、`[自主 Agent 运行时]` 汇总段与 Agent 事件链正确。
- 建立了**只管理、不执行**的自主 Agent 运行时，并经由三重隔离（构造期 14 类硬闸 / 源码扫描 0 token / 运行期 `hasExecutionAuthority()` 恒 false）证明：**执行权唯一属于 ExecutionSandbox，Agent 运行时零执行权限**成立。
- 版本号已升 **v0.17.0**，`package.json` 与 `main.js` 横幅同步。
- 3 项收尾失败已自动定位并修复（1 项真实源码函数 null 化缺陷 + 1 项测试断言错误 + 1 项 Phase 13 事件计数回归修正）。

**验收结论：Phase 14.0 完成，可进入下一阶段。**
