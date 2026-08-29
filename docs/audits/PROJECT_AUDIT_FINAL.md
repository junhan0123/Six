# PROJECT_AUDIT_FINAL — 小6 Phase 6 最终工程审计

> 范围：Phase 6 全 8 个 Order 收口后的运行时 + Design System 一致性审计。
> 日期：2026-08-03
> 纪律：Implementation Only / Architecture Frozen —— 本研究仅在既有架构上审计与收口，未重新设计。

---

## 1. 模块统计

| 类别 | 数量 | 说明 |
|------|------|------|
| 前端 JS（活跃，排除 tests/vendor） | ~52 | 含 8 个 Phase 6 运行时治理模块 + 预冻结功能模块 |
| 后端 Python（活跃，排除 .bak） | ~75 | server.py + agent_runtime/goals/tasks/memory/knowledge/intent_gateway/eventbus 等 + tests |
| CSS | 2 | `styles.css`（基础令牌 + 布局）、`premium.css`（增量精装层） |
| HTML | 6 | `index.html`（主入口）、`dashboard.html`、`mobile-app.html`、`selfcheck.html`、`weather-modal-preview.html`、`architecture-diagram.html` |
| **Phase 6 运行时治理栈** | **8** | `zz-events.js` / `app-state.js` / `galaxy-state.js` / `galaxy-runtime.js` / `overlay-runtime.js` / `event-bridge.js` / `intent-gateway.js` / `solar-system.js`（状态节点+焦点消费端） |
| 测试 | 15 | Order 1–8 前端(8) + 后端/集成(7) |

> 备份目录 `xiao6-ui.bak.*`（4 个）为实施过程快照，不计入活跃代码。

---

## 2. Runtime 架构图

```
                        后端领域事件 (publish_domain, name 须∈DOMAIN_EVENT_NAMES)
                                       │  SSE (/api/stream)
                                       ▼
                            event-bridge.js  ── 信封 → AppState.applyEvent
                                       │
                                       ▼
   ┌─────────────────────────── AppState（唯一状态核心 / 纯状态机）──────────────────────────┐
   │  reducers[name] 单一写入入口 · subscribe 观察者 · getGalaxyNodes() 投影源                  │
   │  state: goals / agents / tasks / memory / knowledge / intents / focus( FOCUS_CHANGED )   │
   └───────┬───────────────────────────────┬────────────────────────────────┬──────────────┘
           │ 订阅 '*'                        │ 订阅 '*'                         │ 订阅 '*'
           ▼                                 ▼                                  ▼
     galaxy-state.js                  overlay-runtime.js                solar-system.js
     (纯数据投影 · get*Nodes)         (AppState+GalaxyState →            (品牌银河 100% 保留；
           │                           Overlay Model · 6 类/5 态)         仅消费 Runtime 数据：
           │                                 │                              syncState / 焦点→FOCUS_CHANGED)
           ▼                                 ▼                                  │
     galaxy-runtime.js                  Overlay Model ── subscribe ──▶ (未来 Overlay Renderer)
     (GalaxyState → Renderer 模型 · 8 态)
           │
           ▼
     solar-system.js  syncState()  → 状态节点 mesh（占位，无视觉状态实现）
```

**纪律闭环**：任何状态变化必须 Event → AppState → Runtime → Renderer；无模块自行维护业务状态。

---

## 3. Event 全表（38，前端 `zz-events.js` 与后端 `eventbus.DOMAIN_EVENT_NAMES` 逐字对齐）

| 分组 | 事件 |
|------|------|
| Goal (7) | GOAL_CREATED, GOAL_UPDATED, GOAL_PLANNED, GOAL_STARTED, GOAL_RUNNING, GOAL_COMPLETED, GOAL_FAILED |
| Agent (7) | AGENT_CREATED, AGENT_STARTED, AGENT_THINKING, AGENT_WORKING, AGENT_WAITING, AGENT_COMPLETED, AGENT_FAILED |
| Task (5) | TASK_CREATED, TASK_STARTED, TASK_RUNNING, TASK_COMPLETED, TASK_FAILED |
| Tool (2) | TOOL_CALLED, TOOL_DONE |
| Memory (5) | MEMORY_UPDATED, MEMORY_CREATED, MEMORY_STORED, MEMORY_LINKED, MEMORY_ARCHIVED |
| Intent (6, Order 5) | INTENT_RECEIVED, INTENT_ANALYZING, INTENT_CLASSIFIED, INTENT_ACCEPTED, INTENT_REJECTED, INTENT_CONVERTED_TO_GOAL |
| 系统 (6) | NOTIFICATION_RAISED, REFLECTING, ERROR_OCCURRED, WORKSPACE_SWITCHED, FOCUS_CHANGED, STATE_SYNC |

**一致性**：后端 `publish_domain` 强制 `name in DOMAIN_EVENT_NAMES`，越界即 `ValueError`；前端经 `ZZ.EVENTS` 常量引用，无裸字符串（Order 8 收口后 0 处硬编码）。

---

## 4. State 全表

| 层 | 词表 | 规模 | 来源 |
|----|------|------|------|
| AppState 域节点态 | Created, Running, Completed, Failed, Thinking, Waiting, Archived, Dormant, Error | 9 | `app-state.js` reducer |
| GalaxyState 投影态 | 23 个输入→投影映射（含 Started/Working/Paused/Stored/Linked/Sleeping + Intent 态） | 23 | `galaxy-state.js` RUNTIME_MAP |
| GalaxyRuntime 规范态 | Dormant, Created, Running, Thinking, Waiting, Completed, Failed, Archived | 8 | `galaxy-runtime.js` RUNTIME_STATES |
| OverlayRuntime 类型 | Info, Detail, Action, Execution, Memory, Warning | 6 | `overlay-runtime.js` OVERLAY_TYPES |
| OverlayRuntime 生命周期 | OPEN, UPDATING, ACTIVE, COMPLETED, CLOSED | 5 | `overlay-runtime.js` OVERLAY_LIFECYCLE |

**收敛保证**：`galaxy-runtime.mapState()` 覆盖 galaxy-state 全部投影态，输出恒在 8 词表内（O8 测试 C 锁证）。

---

## 5. Token 使用统计

| 文件 | 层 | 令牌 | 重复 |
|------|----|------|------|
| `styles.css` `:root` | 基础单一来源 | `--void --void2 --panel --panel-solid --glass --line --line-strong --cyan --teal --amber --red --txt --dim --dim2 --glow`（15） | 0 |
| `premium.css` `:root` | 增量层（引用基础层） | `--ease-premium --ease-out-soft --motion-fast --motion-base --motion-slow --elev-1/2/3 --r-sm/md/lg/xl`（12） | 0 |
| 跨文件 | — | 基础层与增量层**零命名冲突** | 0 |

主题变体（`body[data-theme="light"/dark-cyan/…]`）与逐元素覆盖（`.hs-open-btn{--bc:…}`）为合法令牌重定义，非重复定义。

---

## 6. CSS 审计

- **死变量**：无。`:root` 令牌全部被引用（`--qc-c`/`--bc` 等别名均用于 quick-chip / hud-right 按钮）。
- **死样式**：未做穷举删除（避免触碰冻结视觉）；活动规则均服务于现有 DOM。
- **重复变量**：无（见 §5）。
- **历史兼容变量**：无遗留 `@deprecated`/`-old-` 前缀变量。
- **无引用规则**：未发现与现存 DOM 完全脱节的全局类（热点/地图等模块类与各自 HTML 对应）。
- **结论**：Design System 单一来源成立，无需删改。

---

## 7. JS 审计（运行时治理栈）

| 文件 | 职责 | 审计结论 |
|------|------|----------|
| `zz-events.js` | 事件名单一来源 | 38 常量，无裸字符串风险 |
| `app-state.js` | 纯状态机 | 单一写入入口；`console.warn` 为合约守卫（保留） |
| `galaxy-state.js` | 纯数据投影 | 无 Three.js/DOM；`getIntentNodes` 为合法投影 API（被 O5 测试消费） |
| `galaxy-runtime.js` | Galaxy→Renderer 模型 | 纯转换；`mapState` 收敛完整 |
| `overlay-runtime.js` | AppState+GalaxyState→Overlay 模型 | 纯转换；6 类/5 态；无 DOM/CSS |
| `event-bridge.js` | SSE 信封→AppState | 仅桥接，不新建连接 |
| `intent-gateway.js` | 意图投递薄层 | 仅 `POST /api/agent/intent`，不写 AppState |
| `solar-system.js` | 品牌银河 + Runtime 消费端 | 品牌引擎零改动；仅加 `syncState`/`_nodePosition`/焦点→`FOCUS_CHANGED`（Order 8 收口为常量） |

**违反项**：仅 1 处硬编码事件（`solar-system.js:612`），已修复为 `ZZ.EVENTS.FOCUS_CHANGED`。
**死代码**：运行时栈内无。
**Mock 数据**：`hotspot.js MOCK_FEED` 为装饰性示例事件流（刻意、冻结前），非运行时 mock，保留。

---

## 8. Python 审计（后端）

- **事件契约**：`eventbus.publish_domain` 强制校验 `name ∈ DOMAIN_EVENT_NAMES`，否则 `ValueError`；所有业务事件经此单一来源。
- **绕过 Runtime**：无。前端经 SSE → `event-bridge` → `AppState` 消费；后端不直推内部状态给前端。
- **死代码/孤儿模块**：未做全量删除（避免改动冻结后端）；`reflector.py` 等按合约发射 `MEMORY_*` 事件，正常。
- **一致性**：事件名与前端逐字对齐（O1 BE 测试锁证 38）。

---

## 9. Dead Code

- **运行时栈**：无死代码、无未引用模块、无重复 Helper（`_goalIdOf` 单一定义于 `galaxy-runtime.js`）。
- **预冻结功能模块**：含历史遗留实现（avatar/hotspot/command-palette/doc 等），为冻结前活跃功能，非死代码，**不在 Phase 6 重构范围**，保留。
- **调试代码**：运行时栈无 `debugger`/遗留 `console.log`；`app-state.js:430` 的 `console.warn` 为有意守卫。
- **Mock 数据**：`hotspot.js MOCK_FEED` 为装饰性示例，保留（见 §7）。

---

## 10. Technical Debt

| 项 | 性质 | 是否本 Order 处理 | 建议 |
|----|------|------------------|------|
| 预冻结功能模块直连 `/api`（app.js `/api/memory`、`/api/agent/state`；memory-panel 等） | 业务数据直读，未走 AppState 投影 | 否（超出 Phase 6 运行时范围，改动=redesign） | 未来若有"记忆/智能体状态"可视化需求，应经 `publish_domain`→AppState 回流，再投影到 Galaxy/Overlay |
| 品牌银河 Magic Color（`0x5599bb`/`0x88aaff`） | 宪法红线保护的品牌资产 | 否 | 维持品牌资产，不纳入 Design Token |
| 状态节点 3D 布局 Magic Number | 场景几何常量 | 否 | 若未来抽出为配置，应在 Runtime 之外独立维护，不污染 Design Token |
| 多主题并存（`light`/5 个 dark 变体） | 产品功能（非债务） | 否 | 维持 |

---

## 11. Remaining Risks

1. **品牌银河与运行时解耦的边界**：`solar-system.js` 消费 `GalaxyRuntime` 仅渲染占位 sphere（无视觉状态实现），符合 Order 6/7"不实现视觉"纪律；未来若要做状态着色，须由 Design System（Order 后期）提供令牌，不得硬编码。
2. **预冻结模块直连 API**：若这些模块未来需反映真实业务状态，需补 Event Bridge 回流（见 Technical Debt）。当前不影响 Phase 6 运行时正确性。
3. **未提交（uncommitted）状态**：Phase 6 全程实现均未 commit（纪律要求停止待 Code Review）。Code Review 通过后建议一次性 commit，并保留 `.bak` 快照至评审结束。
4. **测试覆盖**：运行时栈 240/240 绿；预冻结功能模块（avatar/hotspot 等）有独立 `tests/test_*.py`，未纳入 Phase 6 回归（范围外）。

---

## 12. Phase 6 最终完成报告

| Order | 主题 | 关键交付 | 测试 |
|-------|------|----------|------|
| 1 | Event Contract | `zz-events.js` 单一来源 + 后端 `eventbus` 对齐（38） | FE 7 / BE 3 |
| 2 | Goal 生命周期 | Goal→Galaxy Node 投影 | FE 22 / IT 9 |
| 3 | Agent/Task 生命周期 | Agent→Satellite / Task→Orbit | FE 39 / IT 16 |
| 4 | Memory 生命周期 | Memory→Archive / Knowledge→Link | FE 19 / IT 16 |
| 5 | Intent Gateway | 意图→目标决策闭环 + 6 生命周期事件 | FE 19 / IT 17 |
| 6 | Galaxy Runtime Binding | `galaxy-runtime.js` 纯转换层 | FE 17 / IT 16 |
| 7 | Overlay Runtime Binding | `overlay-runtime.js` 6 类/5 态 + Focus 闭环 | FE 26 / IT 10 |
| 8 | Design System Runtime Consolidation | 收口硬编码事件 + 全栈一致性审计 + 收敛回归锁 | FE 4 / — |
| **合计** | | | **FE 153 + BE/IT 87 = 240/240 全绿** |

**结论**：Phase 6 Implementation 全部 8 个 Order 已落地，运行时栈（Event → AppState → Runtime → Renderer）统一、一致、单一来源；Design System 令牌层无重复/无死变量；全量测试 240/240 通过。银河本体 100% 保留。

**下一步**：停止实现，等待最终 Code Review。
