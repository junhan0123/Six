# Overlay Runtime Log — Phase 6 Order 7

> 本文件为 Order 7 Overlay Runtime Binding 的运行时架构与验证记录。配套变更日志见 `CHANGELOG_PHASE6_ORDER7.md`。
> 纪律：Implementation Only / Architecture Frozen。Overlay Runtime 是**纯数据转换层**，非视觉、非 UI、非样式。

---

## 1. 修改文件列表

- **新增** `xiao6-ui/overlay-runtime.js`（Overlay Runtime Layer，约 240 行，UMD）
- **新增** `xiao6-ui/tests/phase6-order7.frontend.test.js`（26 项）
- **新增** `xiao6-ui/tests/phase6-order7.integration.test.py`（10 项）
- **新增** `xiao6-ui/tests/_o7_overlay_harness.js`（IT 前端回放校验）
- **修改** `xiao6-ui/app-state.js`：`FOCUS_CHANGED` reducer + `getFocus()`；`ERROR_OCCURRED` 状态规范化 `'error'`→`'Error'`
- **修改** `xiao6-ui/solar-system.js`：focus → `FOCUS_CHANGED` 发布；状态节点可点击（消费 `GalaxyRuntime` 节点）
- **修改** `xiao6-ui/index.html`：注册 `overlay-runtime.js`，版本号 bump 至 `?v=20260803o7`

---

## 2. Git Diff Summary

- 合约事件总数保持 **38**（单一来源 `zz-events.js` ↔ `eventbus.DOMAIN_EVENT_NAMES` 逐字一致）；`FOCUS_CHANGED` 仅落地 reducer，未新增事件。
- `overlay-runtime.js` 不依赖 DOM / CSS / Three.js / 网络 / 后端 / API；数据单向派生自 `AppState` + `GalaxyState`。
- `solar-system.js` 品牌渲染引擎零改动；仅两处交互接线（发布 focus、节点可点击）。
- 跨运行时一致性修复：`ERROR_OCCURRED` 状态规范化，使 `galaxy-runtime.mapState` 与 `overlay-runtime.steadyLifecycle` 词表统一。

---

## 3. Overlay 数据流图

```
AppState ──┐
           ├─→ OverlayRuntime（纯数据转换）──→ Overlay Model ──→ Existing Overlay Renderer
GalaxyState ┘        ↑ subscribe('*') / onNodeChange
                     └── 只读，绝不反向写状态、绝不读后端
```

- `OverlayRuntime.getModel()` 返回 `{ focus: <overlay|null>, items: [<overlay>, ...] }`
- 每个 overlay：`{ id, sourceId, sourceType, type, lifecycle, title, body, meta }`
- `CLOSED` 状态（Dormant/Archived）的节点被信息层过滤，不进入 `items`

---

## 4. 六类 Overlay 映射表

| 领域节点 type | Overlay 类型 | 首现态 | 稳态收敛 |
|---|---|---|---|
| `goal` | Detail | OPEN（Created）/ COMPLETED（终态） | COMPLETED |
| `agent` | Execution | OPEN / ACTIVE | COMPLETED |
| `task` | Execution | OPEN / ACTIVE | COMPLETED |
| `memory` | Memory | OPEN / COMPLETED | COMPLETED |
| `error` | Warning | COMPLETED（单次错误即终态） | COMPLETED |
| `intent` | Info / Action(needsConfirm) | OPEN | OPEN |
| `knowledge` | —（不生成） | — | — |

映射函数：`mapType(sourceType, node)`；生命周期：`steadyLifecycle(state)` + 首现终态直接收敛规则。

---

## 5. Focus → Overlay 生命周期图

```
点击银河状态节点(Three.js, userData.nodeId)
   → solar-system.focusOn → publish FOCUS_CHANGED(nodeId)
   → AppState.applyEvent(FOCUS_CHANGED) → state.focus = {capability, id}
   → OverlayRuntime（subscribe AppState）收到通知 → _recomputePrev()
   → getModel(): 读 AppState.focus + GalaxyState 节点 → Overlay Model.focus (Detail Overlay)
   → Overlay Renderer 打开 Detail 面板
```

- **闭合验证**：Overlay 全程经 `AppState.focus` 驱动，**不直接监听 Three.js**（scope ⑤ 红线）。
- 五态：`OPEN / UPDATING / ACTIVE / COMPLETED / CLOSED`，状态一律来自 AppState / GalaxyState。

---

## 6. 真实运行日志

真实后端 `run_intent_gateway("分析当前项目状态")` → `_run_goal(gid)` 捕获 SSE 事件，经 Node 子进程加载真实前端运行时增量回放：

- 捕获序列（节选）：`GOAL_CREATED → AGENT_CREATED → AGENT_WORKING → TASK_CREATED×2 → TASK_RUNNING → MEMORY_CREATED → MEMORY_STORED → MEMORY_LINKED → AGENT_COMPLETED → GOAL_COMPLETED`
- Overlay 校验（OVERLAY HARNESS 6/6）：
  - Goal→Detail = COMPLETED（末端）
  - Agent（AGENT_WORKING 点）→ Execution = ACTIVE
  - Task（TASK_RUNNING 点）→ Execution = ACTIVE
  - Memory→Memory = COMPLETED
  - items ≥ 4
  - `FOCUS_CHANGED(goal:gid)` → `Overlay Model.focus` = Detail overlay

捕获文件：`D:\Cache\Temp\zz_order7_itest_capture.json`

---

## 7. 风险分析

1. **UPDATING 闪光消费窗口**：由首帧 `getModel` 消费；内部 `_notify` 已向订阅者推送带 UPDATING 的模型，符合推送语义。FE 测试经 `subscribe` 捕获验证。
2. **合约单一来源**：`FOCUS_CHANGED` 为既有事件，仅落地 reducer，未新增事件名，38 事件不变。
3. **状态词表一致性**：`ERROR_OCCURRED` `'error'`→`'Error'` 规范化，已确认无回归，且修复 `galaxy-runtime` 潜在风险。
4. **银河本体红线**：品牌渲染引擎零改动；`overlay-runtime.js` 与 `galaxy-runtime.js` 同构，未引入第二套状态系统。
5. **无视觉溢出**：`overlay-runtime.js` 全文件无 DOM / CSS / 颜色 / Glow / Shader / 动画 / 布局代码。

---

## 8. 全量测试结果

| Order | Frontend | Backend/Integration | 状态 |
|---|---|---|---|
| 1 | 7 | 3 | ✅ |
| 2 | 22 | 9 | ✅ |
| 3 | 39 | 16 | ✅ |
| 4 | 19 | 16 | ✅ |
| 5 | 19 | 17 | ✅ |
| 6 | 17 | 16 | ✅ |
| **7** | **26** | **10** | ✅ |
| **合计** | **149** | **87** | **236/236 ✅** |

---

**合规声明**：Overlay Runtime 仅为真实状态→信息层模型的纯数据绑定，未触碰冻结设计文档、未重新设计 Overlay 视觉、未新增 UI 框架/Design Token、未绕过 AppState / Galaxy State / Event Contract / publish_domain() / Event Bridge。银河本体（太阳+8 行星+星空+流星+点击聚焦）100% 保留。

**Order 7 停。等待批准。未经批准不进入 Order 8。**
