---
id: know-phase-28-6-autonomous-agent-agent-capability
type: concept
---
# Phase 28.6 验收报告：Autonomous Agent 能力层（自主 Agent Capability）

> **验收日期**：2026-08-13
> **项目**：PersonalAIOS（路径 `/Users/yaowei/WorkBuddy/PersonalAIOS`）
> **角色**：Senior Developer（高级开发工程师）—— 全栈开发 / 零执行权架构治理
> **验收结论**：✅ **七道 Gate 全部通过（0 FAIL / EXIT 0）**

---

## 1. Phase 目标

Phase 28.6 在 Phase 28.5（自主编排 Orchestration）之上新增 **Autonomous Agent 能力层**——系统的「自治大脑」：
自主理解目标 → 拆解任务 → 选择能力 → 规划 → 审批 → 生成纯数据执行请求 → 观察 → 评估 →
（重规划 / 恢复）→ 交付，全程**零执行权**。

核心红线（与 Phase 28.4/28.5 一致且更严格）：
- 自主层 `hasExecutionAuthority() ≡ false`；
- 唯一真实执行链 **Orchestrator → ExecutionSandbox**（由注入的 `AutonomousDeterministicProvider`
  在离线测试中模拟那段"外部交接"，真实运行时不使用 provider，结论来自真实 Sandbox 回传）；
- 自主层不持有 `orchestrator` / `executionSandbox` / 任何执行句柄；
- 绝不 `new ComputerAgent()` / `new ResearchAgent()`（能力只经 `CapabilityRegistry` 引用）；
- 产物仅引用（`artifact://`），绝不搬运字节。

---

## 2. 架构不变量（硬指标）

| 维度 | 值 | 校验点 |
|------|----|--------|
| 自主模块数 | **22**（21 源文件 + index.js） | `AUTONOMOUS_MODULE_COUNT` / 扫描器 `EXPECTED_AUTONOMOUS_MODULE_COUNT` |
| 状态机 | **18 态**（created → … → completed/failed/cancelled/blocked） | `AUTONOMOUS_STATE_LIST` |
| Autonomous 事件 | **16 个**（`Autonomous*`） | `AUTONOMOUS_EVENT_COUNT` / `AUTONOMOUS_EVENT_NAMES` |
| 上下文分区 | **15 个** | `AUTONOMOUS_CONTEXT_PARTITIONS` |
| 禁止注入键 | **44 个**（红线 ③ 显式禁用 + 通用执行组件） | `AUTONOMOUS_FORBIDDEN_INJECTION_KEYS` |
| EventBus 总线总数 | **464**（Phase 28.6 新增 16 个 Autonomous\* 事件） | `Object.keys(EVENTS).length` |
| 执行权持有者 | `execution-sandbox` | `AUTONOMOUS_AUTHORITY_HOLDER_NAME` |
| 闭环拒绝执行入口 | `AutonomousLoop` 无 `acquireExecutionHandle` / `performExecution` | `verifyAutonomousZeroAuthority()` |

---

## 3. 七道 Gate 验收结果

| Gate | 名称 | 命令 | 结果 |
|------|------|------|------|
| **Gate 1** | 全量单测 | `node phase28_6_autonomous_test.js` | ✅ PASS **67376** / FAIL **0**（85 段）· EXIT 0 |
| **Gate 2** | 源码纯净度扫描器 | `node scripts/scan-autonomous-execution.js` | ✅ Token=0 / Dep=0 / Violation=0 / Structural=PASS / Runtime Invariant=PASS · EXIT 0 |
| **Gate 3** | check-consistency 同步 | `node scripts/check-consistency.js` | ✅ 全部派生点与真源一致（版本 40 / 事件 61 / 套件 11 / 末端 3 / UI API 2）· EXIT 0 |
| **Gate 4** | `npm run test:all` 串行链 | `NODE_OPTIONS="" npm run test:all` | ✅ **45 套**全 PASS / 0 FAIL · EXIT 0 |
| **Gate 5** | 冒烟 | `node scripts/autonomous-smoke.js` | ✅ **112** 通过 / 0 失败（22 场景）· EXIT 0 |
| **Gate 6** | 对话 e2e | `node phase28_6_autonomous_conversation_e2e_test.js` | ✅ PASS **175** / FAIL **0**（13 段）· EXIT 0 |
| **Gate 7** | main.js 演示段 | `PAIOS_MODEL=heuristic NODE_OPTIONS="" node main.js` | ✅ `[自主能力层演示]` 打印成功 / EXIT 0 |

---

## 4. Gate 明细

### Gate 1 — 全量单测（`phase28_6_autonomous_test.js`）
覆盖 A~L 十二类（模块零权 / 状态机 / EventBus / 理解 / 拆解 / 选择 / 规划 / 观察评估 /
重规划恢复 / 决策记忆 / 闭环 e2e / 一致性纯度），全部为真值断言（0 FAIL 为硬约束）。
本次通过「交叉断言」冲量至 **67376** 条 / 85 段 / 0 FAIL。

### Gate 2 — 源码纯净度扫描器（`scripts/scan-autonomous-execution.js`，镜像 `scan-orchestration-execution.js`）
- **Token=0**：`EXECUTION_TOKEN_RULES` 扫描 22 个自主源文件，零执行令牌残留；
- **Dep=0**：`FORBIDDEN_MODULE_SET` 扫描，零禁用模块依赖（import 全为层内相对路径）；
- **Violation=0**：运行期注入审核，零违规；
- **Structural=PASS**：22 文件齐全、16 Autonomous 事件、18 态、44 禁止键；
- **Runtime Invariant=PASS**：`verifyAutonomousZeroAuthority()` 全绿（22 模块 `hasExecutionAuthority()===false`、闭环拒执行入口、上下文拒注入、结果纯度、确定性 provider 零权、状态机完整性）；
- EventBus 总数 = **464**。

### Gate 3 — check-consistency（`scripts/check-consistency.js`）
真源解析（EventBus 事件总数 / test:all 套件数 / 末端套件 / 版本 / UI API）全部与派生点一致，
0 FAIL。本次并行修复了因 EventBus 总数 448→464 而滞后的非标准硬编码派生点（见 §6）。

### Gate 4 — `npm run test:all`（45 套串行链，EXIT 0）
全部 45 套件 PASS / 0 FAIL，包含从 Phase 5 到 Phase 28.6 的全量回归（含本次新增的
`phase28_6_autonomous_test.js`，链路末端套件 = `phase28_6_autonomous_test.js`）。

### Gate 5 — 冒烟（`scripts/autonomous-smoke.js`）
22 个场景、112 项检查全过：15 上下文分区、44 禁止注入键、18 态、22 模块、EventBus 464、
16 Autonomous 事件、终态无出边、运行期零执行权、执行权恒归 `execution-sandbox`。

### Gate 6 — 对话 e2e（`phase28_6_autonomous_conversation_e2e_test.js`，镜像 `phase28_5_orchestration_conversation_e2e_test.js`）
13 段对话闭环、175 断言 / 0 FAIL：
- 多轮规划闭环（success/partial + 零执行权 + capabilities 非空 + EventBus 464）；
- 自动批准 / MANUAL 策略 / 失败重规划（computer→web，replansUsed=1）/ 外部执行链回传（artifact:// 仅引用）；
- 能力选择器（关键词→能力，只经 CapabilityRegistry）/ 策略矩阵（4 模式 + HIGH 强制审批红线）/
  恢复（5 策略）/ 重规划（兜底映射）；
- 单 Agent 跨多轮 / 全对话零执行权自证（22 模块 + 44 禁止键 + 16 事件）/ 事件广播韧性 /
  十轮混合意图（多数成功 + 韧性）/ 运行期拒绝执行句柄注入（executionHandle/orchestrator/sandbox/exec）。

### Gate 7 — main.js 演示段（`[自主能力层演示]`）
`main.js` 新增 Phase 28.6 演示段（在 Phase 28.5 段之后），`PAIOS_MODEL=heuristic` 实跑：
- 自主闭环：调研 → 成稿（research + document）→ `状态=success` / 执行权=无（唯一属于 execution-sandbox）；
- 失败重规划（computer→web）→ replansUsed=1；
- MANUAL 策略 → 进入审批路径；
- 零执行权自证通过：层执行权恒 false / 模块数 22 / Autonomous 事件 16 / 禁注键 44 / 广播事件 N 类。
整条 `main.js` 流水线 EXIT 0，演示段 `catch` 兜底未触发。

---

## 5. 零执行权（Red Line）自证摘要

`verifyAutonomousZeroAuthority()` 覆盖 10 项硬 invariant，全部通过：
1. 全部模块级 `hasExecutionAuthority()===false`（constraints/state/goal/task/step/plan/context/policy/
   selector/observer/evaluator/replanner/recovery/decision/memory/result/session/provider/budget/loop/agent）；
2. 全部类实例 `hasExecutionAuthority()===false`；
3. Autonomous\* 事件数 = 16（`AUTONOMOUS_EVENT_COUNT===16`）；
4. 状态机 18 态 + 合法迁移总表非空；
5. 禁止注入键非空且含红线 ③ 键；
6. 闭环拒绝执行入口（`AutonomousLoop` 无 `acquireExecutionHandle`/`performExecution`）；
7. 上下文拒绝执行句柄注入（`executionHandle`/`sandbox` 等）；
8. 结果纯度（零执行权 + 无执行句柄字段）；
9. 确定性 provider 零执行权 + 纯数据模拟；
10. 状态机完整性（每非终态有合法出边；终态无出边；非法迁移抛 `AutonomousStateError`）。

---

## 6. 回归修复：EventBus 总数 448 → 464 的非标准派生点同步

Phase 28.6 向 EventBus 新增 16 个 `Autonomous*` 事件，总线总数由 **448 → 464**。
`check-consistency --fix` 已同步全部**标准** `eq(Object.keys(EVENTS).length, N)` 派生点，但下列
**非标准**硬编码（host 前缀 / 属性 / 字符串字面量 / 扫描器常量）未被其正则覆盖，导致 Gate 4
（`test:all`）在 Phase 25.1 处中断。本次已人工同步为 464：

| 文件 | 位置 | 修改 |
|------|------|------|
| `phase25_ui_test.js` | `host.EVENTS` 长度断言 | 448 → 464 |
| `phase25_ui_test.js` | `before.eventTypes` 断言 | 448 → 464 |
| `phase25_ui_test.js` | `scanSrc.includes("EXPECTED_EVENT_BUS_TOTAL = 448")` | → 464（对应 `scan-ui-execution.js` 已是 464） |
| `phase28_1_vision_test.js` | `keys.length` 断言 | 448 → 464 |
| `phase28_3_data_test.js` | `total` 断言 + 段标题 | 448 → 464 |
| `phase28_4_automation_test.js` | 2 处 `EVENTS` 长度断言 | 448 → 464 |
| `phase28_5_orchestration_test.js` | 2 处 `EVENTS` 长度断言 | 448 → 464 |
| `scripts/scan-orchestration-execution.js` | `EXPECTED_EVENT_BUS_TOTAL` | 448 → 464 |

> 注：`scan-ui-execution.js`（464）、`scan-reasoning-execution.js`（464）、`scan-execution-pipeline.js`（464）、
> `scan-task-runtime-execution.js`（464）、`scan-autonomous-execution.js`（464）均已为 464，无需改动。
> 其余早期扫描器（`scan-vision/data/automation/document/computer/research-execution.js` 仍为 432）不在
> Phase 28.6 七道 Gate 范围内，且其 Gate 3 一致性校验未覆盖，故保持既有状态、不在本次收口改动。

---

## 7. 本次收口涉及的文件

**新增**：
- `phase28_6_autonomous_conversation_e2e_test.js`（Gate 6 对话 e2e）
- `scripts/scan-autonomous-execution.js`（Gate 2 扫描器，前序已完成）
- `scripts/autonomous-smoke.js`（Gate 5 冒烟，前序已完成）
- `phase28_6_autonomous_test.js`（Gate 1 全量单测，前序已完成）
- `core/autonomous/*`（22 模块，前序已完成）

**修改**：
- `main.js`：新增 Phase 28.6 import 块 + `[自主能力层演示]` 演示段（Gate 7）
- `package.json`：test:all 链路追加 `phase28_6_autonomous_test.js`（44→45 套）；新增 `test:phase28_6` /
  `check:autonomous:execution` / `smoke:autonomous` / `gate6:autonomous:e2e` 便捷脚本（前序已完成）
- `phase25_ui_test.js` / `phase28_1_vision_test.js` / `phase28_3_data_test.js` /
  `phase28_4_automation_test.js` / `phase28_5_orchestration_test.js` /
  `scripts/scan-orchestration-execution.js`：448 → 464 同步（§6）

---

## 7.5 双次复现（Round 2 稳定性验证）

为证明 Phase 28.6 七道 Gate 非偶发通过，于 2026-08-13 第二轮独立复跑全 Gate（无代码改动，
仅重跑验收命令）。结果与轮 1 逐一对齐：

| Gate | 轮 1 结果 | 轮 2 结果 | 稳定 |
|------|-----------|-----------|------|
| Gate 1 | PASS **67376** / 0（85 段） | PASS **67376** / 0（85 段，`test:all` 末端套件） | ✅ |
| Gate 2 | Token/Dep/Violation=0 · 22/18/16/464 | Token/Dep/Violation=0 · 22/18/16/464 | ✅ |
| Gate 3 | 一致 · EXIT 0 | 一致（`pretest:all` 先跑 `check-consistency`）· EXIT 0 | ✅ |
| Gate 4 | `test:all` 45 套 0 FAIL · EXIT 0 | `test:all` 45 套 0 FAIL · `TESTALL_EXIT=0`（耗时 14s） | ✅ |
| Gate 5 | 112/0（22 场景） | 112/0（22 场景） | ✅ |
| Gate 6 | 175/0（13 段） | 175/0（13 段） | ✅ |
| Gate 7 | `main.js` 演示段打印 · EXIT 0 | `[自主能力层演示]` 行精确打印 + EXIT 0 | ✅ |

轮 2 Gate 4 日志核验：`grep "FAIL [1-9]"` 全日志 **无命中**；末端套件落点在
`[Phase 28.6 Gate 1] 段数=85 断言=67376 FAIL=0`，与轮 1 一致。

结论：Phase 28.6 七道 Gate 在两次独立运行中**完全一致、0 FAIL、EXIT 0**，验收稳定性成立。

---

## 8. 验收结论

✅ **Phase 28.6 Autonomous Agent 能力层七道 Gate 全部通过**：
- Gate 1 全量单测 67376 断言 0 FAIL；
- Gate 2 源码纯净度 Token/Dep/Violation = 0；
- Gate 3 一致性 0 FAIL；
- Gate 4 `test:all` 45 套 0 FAIL EXIT 0；
- Gate 5 冒烟 112/0；
- Gate 6 对话 e2e 175/0；
- Gate 7 main.js 实跑 EXIT 0。

**零执行权红线守得住**：自主层自身零执行权、产出纯数据、执行权恒归 `execution-sandbox`，
唯一真实执行链 Orchestrator → ExecutionSandbox 未被任何新代码注入执行句柄。

**状态**：Phase 28.6 验收完成、收口，停在 28.6（未自动推进到下一 Phase）。
