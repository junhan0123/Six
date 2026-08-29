# Phase 6 Order 5 — Execution Visualization（执行可视化）

> **状态**：Implemented + Verified + Report（已完成，已停）。新增 `runtime-visualization.js` 的 **Execution Timeline** 渲染器，将 `User Goal → Planner → Reasoning → Tool → Reflection → Result` 六阶段从 `AppState` 运行时状态派生并可视化。
> **红线遵守**：只读 `AppState` / 无第二 State / 无 UI 直连后端 / 未改 Runtime·Memory 架构 / 未新增执行引擎。

---

## 1. 模块与职责

| 文件 | 性质 | 说明 |
|---|---|---|
| `xiao6-ui/runtime-visualization.js` | **新建** | 纯数据模型 `getExecutionTimeline()` / `getMemoryContext()` + 防御性 DOM 渲染器（仅浏览器 `document` 存在时 `mount`，Node 中跳过单测）。 |
| `xiao6-ui/runtime-viz.css` | **新建** | `#runtime-viz` 固定右下角 340px 玻璃面板（青色高亮 #34d8ff，Orbitron/Rajdhani），含时间线 + 记忆上下文样式，移动端响应式。 |
| `xiao6-ui/index.html` | 修改 | `<head>` 引入 `runtime-viz.css?v=20260804p1`；`galaxy-runtime.js` 后注入 `runtime-visualization.js?v=20260804p1`（缓存版本 bump，重启 Electron + Ctrl+F5 生效）。 |
| `tests/phase6-runtime-viz.frontend.test.js` | **新建** | 14 项检查：6 阶段顺序/状态、Memory Context、World Model 投影、单一来源纪律（无 `fetch`/`XHR`/`/api/`）。 |

---

## 2. Execution Timeline 六阶段（数据来源 = AppState）

| 阶段 | 标签 | 状态推导 | 数据来源（AppState 子树） |
|---|---|---|---|
| `user_goal` | 用户目标 | `goal ? Active : Idle` | `state.goals[currentGoalId]` |
| `planner` | 规划 | `= 首个 Agent 的 status`（如 Thinking） | `state.agents`（按 goalId 过滤） |
| `reasoning` | 推理 | `agent.status===Thinking ? Active : (goal ? Done : Idle)` | `state.agents` |
| `tool` | 工具 | `task 有 Running→Active / Failed→Error / 全 Completed→Done / 否则 Idle` | `state.tasks`（按 goalId 过滤） |
| `reflection` | 反思 | `exec.reflecting ? Active : (已沉淀记忆 ? Done : Idle)` | `state.execution.reflecting` + `state.memory` |
| `result` | 结果 | `goal.status===Completed ? Done : (Failed ? Error : Idle)` | `state.goals[currentGoalId]` |

- **数据链**：对应后端 `execution_guard.py`（执行守卫 / 反思触发）与 `conversation_loop.py`（规划→推理→工具→反思→结果）产出的领域事件，经 `EventBus → SSE → event-bridge.js → AppState.applyEvent` 流入，本模块**只读投影**。
- **单向性**：`getExecutionTimeline(state)` 纯函数，无副作用、不修改 `AppState`、不触发网络。

---

## 3. 后端对应（事件通道纪律）

```
execution_guard.py / conversation_loop.py
  └─> publish_domain(GOAL_CREATED / AGENT_CREATED / AGENT_THINKING / TASK_CREATED / TASK_RUNNING / MEMORY_CREATED / MEMORY_STORED / GOAL_COMPLETED ...)
        └─> EventBus → SSE → event-bridge.js → AppState.applyEvent（唯一写入口）
              └─> RuntimeViz.getExecutionTimeline(state)   ← 本模块只读消费
```

- 全部为 `DOMAIN_EVENT_NAMES` 领域事件，进入统一状态核心；与系统事件（`publish_system`）互斥。

---

## 4. 运行时修正（非架构，本次伴随修复）

**问题**：`AppState.execution.reflecting` 在 `MEMORY_CREATED` 时被置 `true`，但此前**全运行时无任何 reducer 将其复位为 `false`**——导致反思阶段状态卡在 `Active`，Execution Timeline 的 `reflection=Done` 分支永远不可达（潜在运行时缺陷）。

**修复**：在 `app-state.js` 的 `MEMORY_STORED` reducer 中增加 `state.execution.reflecting = false;`（记忆持久化即反思完成）。属**既有 reducer 内的状态转换完整性修复，非架构变更、非新增模块**。

**验证影响**：仅 `phase6-order4.frontend.test.js:39` 断言 `MEMORY_CREATED` 后 `reflecting===true`（在 `MEMORY_STORED` 之前）——不受影响；全前端 15 套回归 0 失败。`index.html` 中 `app-state.js` 版本 bump 至 `?v=20260804p2`。

---

## 5. 测试结果

| 套件 | 结果 |
|---|---|
| `tests/phase6-runtime-viz.frontend.test.js` | **14 / 14 PASS** |
| 全前端回归（phase6-order1..8 + phase7-order1..4 + phase8 + runtime-viz） | **15 套 0 失败** |

单一来源纪律断言通过：模块源码不含 `fetch(` / `XMLHttpRequest` / `/api/`。

---

**结论**：Phase 6 Order 5 Execution Visualization 已落地——Execution Timeline 六阶段从 `AppState` 运行时状态实时派生并可视化，数据单向来自后端执行链路，模块严格只读、零后端直连。伴随修复了 `reflecting` 标志卡死的运行时缺陷。**已停止。**
