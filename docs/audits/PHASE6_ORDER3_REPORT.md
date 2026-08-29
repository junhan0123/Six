# Phase 6 Order 3 — Frontend Runtime State Binding（前端运行时状态绑定）

> **状态**：Verified + Report（已完成，已停）。本 Order 的运行时状态绑定基础设施在前序 Order 1–3 已实现并通过全量测试；本次为**核对 + 文档化**，确认 `Backend Event → EventBus → AppState → UI Renderer` 全链路绑定 Goal / Task / Agent / Execution / Galaxy 五类状态，并补齐 Execution 可视化渲染器（见 `EXECUTION_VISUALIZATION_REPORT.md`）。
> **红线遵守**：无第二 State / 无 UI 直连后端 / 未改 Runtime 架构 / 未绕过 AppState 单一写入口 / 未新增 Runtime·Memory·EventBus·Permission。

---

## 1. 修改文件列表（本次核对相关）

| 文件 | 性质 | 说明 |
|---|---|---|
| `docs/audits/PHASE6_ORDER3_REPORT.md` | **新建** | 本绑定核对报告。 |
| `docs/audits/EXECUTION_VISUALIZATION_REPORT.md` | **新建** | Order 5 Execution Timeline 绑定报告（Execution 渲染器落盘）。 |
| `docs/audits/MEMORY_CONTEXT_VISUALIZATION_REPORT.md` | **新建** | Order 6 Memory Context 绑定报告（Memory 渲染器落盘）。 |
| `docs/audits/GALAXY_RUNTIME_BINDING_REPORT.md` | **新建** | Order 4 Galaxy Runtime 绑定报告（银河渲染器核对）。 |

> 说明：核心绑定代码（app-state.js / event-bridge.js / galaxy-state.js / galaxy-runtime.js / solar-system.js）在前序 Phase 6 Order 1–4 已落地，本次**未改动其绑定逻辑**，仅核对并文档化。唯一改动为运行期修正（`MEMORY_STORED` 复位 `exec.reflecting`，见 Order 5 报告 §4），属非架构的状态转换完整性修复。

---

## 2. 绑定链路（单一来源，全链路可验证）

```
Backend Domain Event
  └─> EventBus（eventbus.py:56 单例）· publish_domain()
        └─> SSE（/api/stream）
              └─> event-bridge.js         ← 前端唯一 SSE→AppState 桥接（仅接受 zz-events.js 合约事件名）
                    └─> AppState.applyEvent(state.app-state.js:701 唯一写入口)
                          └─> reducers（Goal/Task/Agent/Execution/Memory/Knowledge/Intent/Computer）
                                ├─> GalaxyState.pull() ← AppState.getGalaxyNodes()   (galaxy-state.js:38-39)
                                │     └─> GalaxyRuntime.getRenderModel()             (galaxy-runtime.js:80)
                                │           └─> solar-system.js syncState()          (solar-system.js:542)  ← Galaxy 渲染器（绑定）
                                └─> RuntimeViz.getExecutionTimeline() / getMemoryContext()  (runtime-visualization.js) ← Execution/Memory 渲染器（绑定，Order 5/6 新增）
```

- **单一写入口**：所有后端领域事件经 `applyEvent` 进入 `state`；`event-bridge.js` 是唯一的 SSE→状态桥接；`zz-events.js` `EVENTS` 为事件名唯一来源（前后端逐字对齐）。
- **无第二 State**：前端仅 `AppState` 一个状态核心；`GalaxyState` 是**纯投影层**（`pull()` 单向派生自 `AppState.getGalaxyNodes()`），`RuntimeViz` 为**只读消费者**，均无独立数据源。
- **无 UI 直连后端**：渲染器只订阅 `AppState`，不发起 `fetch` / `XHR` / `/api/` 调用（已单测断言）。

---

## 3. State 子树绑定（Goal / Task / Agent / Execution / Galaxy）

| 状态域 | AppState 子树 | 写入事件（举例） | 已绑定渲染器 |
|---|---|---|---|
| Goal | `state.goals` | `GOAL_CREATED` / `GOAL_RUNNING` / `GOAL_COMPLETED` | 银河轨道（goal→orbit）；Execution Timeline `user_goal` 阶段 |
| Task | `state.tasks` | `TASK_CREATED` / `TASK_RUNNING` / `TASK_COMPLETED` | 银河轨道子节点；Execution Timeline `tool` 阶段 |
| Agent | `state.agents` | `AGENT_CREATED` / `AGENT_STARTED` / `AGENT_THINKING` | 银河卫星；Execution Timeline `planner` / `reasoning` 阶段 |
| Execution | `state.execution` | `MEMORY_CREATED` / `MEMORY_STORED` / `GOAL_COMPLETED` | Execution Timeline `reflection` / `result` 阶段（本次绑定） |
| Galaxy | `state.galaxyNodes`（由 Goals/Tasks/Agents/Memory 经 `upsertNode` 生成） | 见上 | `solar-system.js`（已绑定，见 Galaxy 报告） |

> 绑定基础设施（reducers + 事件合约 + SSE 桥接）**完整且经既有测试验证**（phase6-order3.frontend.test.js 等 0 失败）。

---

## 4. 纪律遵守确认

- ✅ 无第二 Runtime / Memory / EventBus / Permission（仅 `AppState` + `GalaxyState` 投影层 + `RuntimeViz` 只读消费者）。
- ✅ 无 UI 直连后端（渲染层零 `fetch`/`XHR`/`/api/`）。
- ✅ 未绕过 `AppState` 单一写入口（`applyEvent` @ app-state.js:701 为唯一入口）。
- ✅ 未改 Runtime 架构 / 未新增执行引擎或记忆系统。
- ✅ 事件合约单一来源（后端 `DOMAIN_EVENT_NAMES` 与前端 `EVENTS` 逐字对齐）。

---

## 5. 已知缺口与后续建议（非本 Order 范围）

- **主聊天/目标/任务面板未订阅 AppState**：`app.js` / `tasks.js` / `dashboard.html` 当前仍用本地 DOM 直渲，未消费 `AppState`（前序 grep 确认 `AppState.`/`subscribe` 零命中）。银河渲染器与本次新增的 Execution/Memory 可视化已绑定，但**主交互面板**尚未接入统一状态核心。
  - **建议**：后续 Order 将 `app.js` 的 Goal/Task/Agent 卡片改为订阅 `AppState.subscribe('*', render)`，彻底消除双数据源风险。
- **`memory-panel.js` 直连后端**：该旧工具经 `/api/memory_audit` 渲染记忆审计，未走 AppState（属历史遗留）。本次新增的 `RuntimeViz.getMemoryContext()` 为合规的只读投影替代；旧面板建议后续 Order 迁移或下线。

---

**结论**：Phase 6 Order 3 的前端运行时状态绑定链路（`Backend Event → EventBus → SSE → event-bridge.js → AppState → reducers → UI Renderer`）已完整建立并验证，Goal/Task/Agent/Execution/Galaxy 五类状态全部进入统一状态核心，且银河渲染器与 Execution/Memory 渲染器均已绑定 AppState。**已停止，等待后续 Order 将主交互面板接入统一状态核心。**
