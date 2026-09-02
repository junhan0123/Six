# Phase 6 Order 6 — Memory Context Visualization（记忆上下文可视化）

> **状态**：Implemented + Verified + Report（已完成，已停）。新增 `runtime-visualization.js` 的 **Memory Context** 投影，展示已加载记忆 / 知识 / 世界模型 / 上下文窗口代理 / 压缩状态，全部派生自 `AppState`。
> **红线遵守**：只读 `AppState` / 无第二 State / 无 UI 直连后端 / 未改 Memory 架构 / 未新增记忆 / 未改 Runtime 架构。

---

## 1. 模块与职责

| 文件 | 性质 | 说明 |
|---|---|---|
| `xiao6-ui/runtime-visualization.js` | **新建**（含 `getMemoryContext`） | `getMemoryContext(state)`：`memories` / `knowledge` / `worldModel` / `context` / `compression`。 |
| `xiao6-ui/runtime-viz.css` | **新建** | `#runtime-viz` 面板内「记忆上下文 / 世界模型」区块样式。 |
| `xiao6-ui/index.html` | 修改 | 引入 `runtime-viz.css` + `runtime-visualization.js`（缓存版本 `?v=20260804p1`）。 |
| `tests/phase6-runtime-viz.frontend.test.js` | **新建** | 含 Memory Context / World Model 投影断言。 |

---

## 2. 投影内容（数据来源 = AppState）

| 投影字段 | 来源子树 | 说明 |
|---|---|---|
| `memories[]` | `state.memory` | 已加载记忆列表（id / title / scope / status / createdAt）。 |
| `knowledge[]` | `state.knowledge` | 知识条目（id / title / source / status），由 `MEMORY_STORED` / `MEMORY_LINKED` 写入。 |
| `worldModel{}` | `state.computer`（Phase 7 Order 1 八集合） | `windows` / `applications` / `processes` / `files` / `projects` / `browsers` / `terminals` / `devices` 实时计数。 |
| `context.loadedItems` | `memories.length + knowledge.length` | 上下文窗口代理指标（已加载记忆 + 知识条数）。 |
| `compression{}` | —（后端 `memory_distiller` 维护） | 压缩/蒸馏状态只读标注，本视图不计算、不新增。 |

- **世界模型投影**：`state.computer` 由 Phase 7 Order 1 的 `COMPUTER_WORLD_SYNC` / `WINDOW_*` / `PROCESS_*` 等 19 个观测事件经 `applyEvent` 写入；本视图**只读投影**其八集合计数，无第二数据源。
- **单向性**：`getMemoryContext(state)` 纯函数，不改 `AppState`、不发网络。

---

## 3. 与 Memory 架构的关系（纪律）

- **不新增记忆**：本视图只展示 `AppState.memory` / `AppState.knowledge` 已有内容，不调用任何记忆写入 API。
- **不改 Memory 架构**：`AppState.memory` / `knowledge` 由 `MEMORY_CREATED` / `MEMORY_STORED` / `MEMORY_LINKED` / `MEMORY_ARCHIVED` reducer 维护（前序 Phase 6 Order 4 已落地），本模块不触碰 reducer。
- **压缩状态后端属主**：精确 token 计数与蒸馏/压缩状态由后端 `memory_distiller.py` 维护，经 `MEMORY_STORED` / `LINKED` 事件投影；本视图仅做只读标注（`compression.status = 'tracked-by-backend'`）。

---

## 4. 测试结果

| 套件 | 结果 |
|---|---|
| `tests/phase6-runtime-viz.frontend.test.js` | **14 / 14 PASS**（含 `memories 含 m1` / `knowledge 含 k1（source=reflection）` / `worldModel 初始 0` / `worldModel 随 WINDOW_OPENED/PROCESS_SPAWNED 更新` / `context.loadedItems=2`） |
| 全前端回归 | **15 套 0 失败** |

单一来源纪律断言通过：模块源码不含 `fetch(` / `XMLHttpRequest` / `/api/`。

---

**结论**：Phase 6 Order 6 Memory Context Visualization 已落地——已加载记忆 / 知识 / 世界模型 / 上下文窗口代理 / 压缩状态全部从 `AppState` 运行时状态只读投影并可视化，未新增/未改动 Memory 架构，零后端直连。**已停止。**
