---
id: know-personalaios-handoff-doc
type: concept
---
# PersonalAIOS — 项目状态与未来开发路线（Handoff Doc）

> 生成时间：2026-08-15 ｜ 当前版本 **v0.39.0** ｜ 状态：**Phase 31.2 已收口（`STOP_AT_PHASE_31_2`）**
> 本文件为交接/续开发用。详细验收见根目录 `PHASE31_2_*.md` 与各 `PHASE*_REPORT.md`。

---

## 0. 一句话定位

PersonalAIOS 是一个**零外部运行时依赖、零测试框架、全链路零执行权**的个性化 AI 操作系统内核（Node.js / ESM）。它把 Capability OS / Autonomous Work / Reasoning / Learning / Continuity / Unified Runtime 统一编排；**真实执行唯一经由 `Orchestrator → ExecutionSandbox`**。

---

## 1. 当前状态速览

| 项 | 值 |
|---|---|
| `version` / `kernelVersion` | **0.39.0** |
| EventBus 事件总数 | **490**（Phase 31.2 未新增任何事件） |
| `test:all` 套数 | **55**（字面 `&&` 串行链，Exit 0 / **0 FAIL**） |
| 内核运行时依赖 | **0**（仅 `electron` 用于 UI；内核与测试用 `node` 即可跑） |
| 测试框架 | 自研 `core/test/Harness.js`（**禁 jest/vitest/mocha/chai**） |
| 最近阶段 | **Phase 31.2**（Runtime Control Plane + Autonomous Task Execution & Recovery Layer） |
| 执行权红线 | 全层 `hasExecutionAuthority() === false`；唯一执行链 `Orchestrator → ExecutionSandbox` |
| 双次复现 | 七 Gate 轮 1 == 轮 2，数字完全对齐 |

---

## 2. 架构分层（自上而下）

- `core/capability/` — 能力 OS / 统一能力路由（`CapabilityRegistry` / `CapabilityRouter` / `CapabilityRequest`）
- `core/autonomous/` — 统一自主工作闭环（`AutonomousLoop` + 3 桥接 Verification·Reasoning·Learning）；其中 `core/autonomous/task/` 为 Phase 31.2 第二子层（多步编排 / 恢复 / 检查点）
- `core/reasoning/` — 多轮推理与自主调试（`ReasoningLoop`，**提议者非执行器**）
- `core/learning/` — 自适应学习（纯数据 `Pattern`/`Recommendation`，`isAdvisory === true`）
- `core/continuity/` — 长程连续工作（`Session`/`Cycle`/`Checkpoint`/`Recovery`，包裹而非替代 `AutonomousAgent`）
- `core/runtime/` — 统一运行时内核（Phase 31.1）+ `core/runtime/control/`（Phase 31.2 第一子层：纯治理/协调/观测/审计控制平面）
- `core/orchestrator/` — 编排器（**唯一驱动执行**）
- `core/execution/` + `core/sandbox/` — `ExecutionSandbox`（**唯一真实执行边界**）
- `core/workflow/` · `core/blueprint/` · `core/conversation/` · `core/web/` · `core/research/` · `core/vision/` · `core/document/` · `core/data/` · `core/automation/` · `core/computer/` — 各能力/层

---

## 3. 零执行权安全边界（最高红线，未来改动也必须遵守）

- **唯一真实执行链**：`Orchestrator → ExecutionSandbox`。任何 Runtime / Recovery / Coordination / Autonomous 层**不得** `acquireExecutionHandle` / `performExecution` / `spawn` / `exec` / 直调 terminal·app·browser·file executor / 绕过 Orchestrator 或 ExecutionSandbox。
- 所有 Phase 31.2 组件 `hasExecutionAuthority() === false`；`describe()` 给出 `{ executionAuthority: false, authorityHolder: "execution-sandbox" }`。
- ⚠️ **验证零执行权只能经 `hasExecutionAuthority()` 与 `describe()`**。`PipelineComponent` / `AutonomousTask` **不**把 `executionAuthority` / `authorityHolder` 设为实例属性（二者 = `undefined`）；**不可**断言 `instance.executionAuthority === false`（语义错）。
- 构造期硬闸拒收执行句柄注入：`assertNo*Injected` → `ForbiddenInjectionError` / `TaskRuntimeInjectionError`（注入即拒）。

---

## 4. 如何运行 / 测试

```bash
node main.js "创建一个简单React Todo应用"     # 内核 CLI 演示（不需要 node_modules）
PAIOS_MODEL=heuristic node main.js           # 离线 heuristic 模式
npm run test:all                             # 55 套全量回归（Exit 0 / 0 FAIL）
npm run check-consistency                    # 一致性扫描（version / EventBus / suites / description）
node phase31_2_task_runtime_test.js          # 单套运行
npm start                                    # Electron UI（需先 npm install 装 electron）
```

- 内核与 `test:all` **不需要** `node_modules`（零运行时依赖）。只有 `npm start`（Electron UI）需要 `electron`。
- 新机器上若要用 UI：`npm ci`（凭 `package-lock.json` 精确复现）或 `npm install`。

---

## 5. Phase 31.2 收口要点（最新阶段）

Phase 31.2 含两个子层：

1. **Runtime Control Plane**（`core/runtime/control/`，10 模块）：纯治理 / 协调 / 观测 / 审计；控制请求 **7 态**状态机；**46 禁注键**复用统一运行时内核清单；EventBus 恒 490。
2. **Autonomous Task Execution & Recovery Layer**（`core/autonomy/task/`，25 模块）：多步编排 / 依赖调度 / exactly-once 派发 / 陈旧结果防护 / 重规划 / checkpoint 恢复 / 进度评估；**14 态**任务状态机；**18 类**事件；**387 禁注键**；`AutonomousTask extends PipelineComponent`，`runGoal()` 经 `TaskManager.submit() → Orchestrator.submitExecutionRequest() → ExecutionSandbox` 返回冻结纯数据。

- 七 Gate 全绿 + 双次独立复现一致；报告：`PHASE31_2_AUTONOMOUS_TASK_REPORT.md`（49 节）/ `PHASE31_2_RUNTIME_CONTROL_PLANE_REPORT.md`。
- **`PHASE_31_2_COMPLETE = true` / `STOP_AT_PHASE_31_2 = true`**。

---

## 6. 已知约束与坑（接班必读）

- **EventBus 490 纪律**：不得因新层随意加事件；若确实必须加，须真源 + 所有标准/非标准派生点 + 扫描器 + 测试 + package description + `check-consistency` + `test:all` 全同步，并记录原因。
- **`check-consistency --fix` 只同步标准 `eq(...)` 形式**；变量别名（`Object.keys(host.EVENTS)` / `before.eventTypes` / `const total = T.eq(total, N)`）、字符串字面量（`EXPECTED_EVENT_BUS_TOTAL = N`）不会被同步，须手工核对（历史多次踩坑）。
- **`test:all` 是字面 `&&` 链**：任一 Gate FAIL 即中止后续所有套件；改 `package.json` / 新增 phase 后须整链复跑确认 0 FAIL。
- **`package.json` `description` 被多 phase 测试正则断言引用**；重写易丢 `EventBus 490` / `Phase 22` / `Phase 24.0` 等短语，导致较早 phase 在 `&&` 链中断。
- **Forbidden-injection 硬闸**：构造期注入 `orchestrator` / `executionSandbox` / `sandbox` 等即抛错。
- **Determinism**：重规划 `TaskReplan.replan` 移除失败步骤 + 其全部下游依赖，不臆造新步骤（除非注入 `reasoner`）。
- **禁测试框架**：不得引入 jest/vitest；沿用自研 harness。

---

## 7. 未来开发方向（路线提案，均未启动，需明确授权）

> 以下为接班者的候选方向，**当前均停在 Phase 31.2，未自动进入**。任何一项启动前须：先读对应 `core/` 真源 → 确认可复用既有层（**Reuse > Duplicate**）→ 守住零执行权红线 → 走 7 Gate + 双次复现。

- **Phase 31.3+：运行时深化** — 如真实执行结果回填/重放、跨会话 Run 持久化、Recovery 策略可配置化（仍纯协调，不获取执行权）。
- **UI / Electron 完善** — `ui/electron/` 与 `output/App.tsx`（当前 React Todo 演示仅为 smoke）；可补齐 Workbench / 可观测面板（只读投影，不赋予 UI 执行权）。
- **Capability 扩展** — 新增能力须走 `CapabilityRegistry` / `CapabilityRouter` 统一边界，生成 `CapabilityRequest → ExecutionRequest`，**不得**自建 Agent 执行器。
- **Plugin 生态** — `core/plugin/` 既有契约；新插件须零执行权、经统一边界。
- **外部 / 云端集成** — 当前 External Dependency = 0、离线优先；若引入真实外部 API，须保持 `ExecutionSandbox` 唯一边界，且 enrich 前中和不可信输入（参考 `core/web/` 的 Prompt Injection 防护）。
- **测试扩展** — 新 phase 加 `phaseXX_test.js` 并追加到 `test:all` 末端，同步 Phase 13/14/21 的套数计数与 EventBus 派生点。

---

## 8. 交接与恢复（本归档包）

- **归档文件**：`PersonalAIOS_2026-08-15.zip`（项目根源码归档）。
- **恢复步骤**：解压 → （如需 UI）`npm ci` → `node main.js` 或 `npm run test:all` 即可。
- **归档已排除**：`node_modules/`（可 `npm ci` 复现）、`.workbuddy/`（AI agent 工作记忆，非项目源码）、`_debug_*.mjs`（调试草稿）、`workspace/` / `phase5-test-ws/` / `phase6-test-ws/`（运行工作区，见 `.gitignore`）。
- **归档包含**：全部 `core/` 源码、各 phase 测试与报告、`package.json` + `package-lock.json`、`output/`、`main.js`、`harness.js`、本文件。
- **项目长期记忆（AI agent 侧，不随包转移）**：`/Users/yaowei/WorkBuddy/Claw/.workbuddy/memory/MEMORY.md` 与按日 `2026-08-XX.md`。

---

*本文件由 Senior Developer（高级开发工程师）在 Phase 31.2 收口后整理，供跨机续开发交接。*
