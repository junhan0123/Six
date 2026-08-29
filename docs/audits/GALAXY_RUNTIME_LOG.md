# GALAXY_RUNTIME_LOG · Phase 6 · Order 6 — Galaxy Runtime Binding

> 本文件记录 Order 6 将银河从「静态展示层」升级为「真实系统状态可视化运行层」的实施与真实运行证据。
> 纪律：Implementation Only / Architecture Frozen。本 Order 不做视觉优化 / Shader / 美术 / 动画 / CSS / Design Token / Three.js 重构——只做**状态绑定**。

---

## 1. 架构：从展示层到运行层

```
真实状态（AppState）
   ↓  applyEvent（唯一写入入口，来自 Event Bridge / 本地合成）
GalaxyState（纯数据投影，{id,type,state,relation,metadata}）
   ↓  getGoalNodes() / getAgentNodes() / getTaskNodes() / getMemoryNodes() / getKnowledgeLinks()
GalaxyRuntime（纯数据转换：状态投影 → Renderer 可消费模型，无 Three.js / 无后端 / 无 API）
   ↓  getRenderModel()
Renderer（solar-system.js，消费模型渲染动态状态节点）
```

**关键纪律落实**：GalaxyRuntime 只读 `GalaxyState`（派生自 `AppState`），绝不读后端、绝不调 API、绝不做业务判断。链路严格单向：AppState → GalaxyState → GalaxyRuntime → Renderer。

---

## 2. GalaxyRuntime 职责（纯转换层）

`galaxy-runtime.js`（新增，112 行，UMD，Node 可单测）：
- `RUNTIME_STATES`：仅暴露 8 个规范生命周期态枚举（**不写颜色/Glow/Shader/动画参数**，属 Order 8）。
- `mapState(domainRuntime)`：把 GalaxyState 运行态收敛到 8 词表（`Error→Failed`、`Dormant→Archived`、`Working→Running`、`Stored/Linked→Completed` 等），**绝不出界**。
- `getRenderModel()`：把 GalaxyState 投影为渲染模型，结构：
  ```js
  {
    core:     { id:'sun', type:'core', state:'Active', label:'小6核心' }, // 品牌静态身份
    planets:  [ Goal   → Planet ],
    satellites:[ Agent  → Satellite（parentId = goal:<goalId>） ],
    orbits:   [ Task   → Orbit Node（parentId = goal:<goalId>） ],
    archives: [ Memory → Archive Node（parentId = goal:<goalId>） ],
    links:    [ Knowledge → Link Node（parentId = memory:<memoryId>） ]
  }
  ```

### 2.1 生命周期态接口（Scope ④）
| 状态 | 含义 | 来源映射 |
|------|------|----------|
| Dormant | 休眠/挂起 | Sleeping / 默认 |
| Created | 已创建 | Created |
| Running | 运行中 | Started / Running / Working |
| Thinking | 思考中 | Thinking |
| Waiting | 等待中 | Waiting / Paused |
| Completed | 已完成 | Completed / Stored / Linked |
| Failed | 失败 | Failed / Error |
| Archived | 已归档 | Archived / Dormant |

> 仅提供状态枚举与映射；**不实现视觉**。状态→颜色/Glow/动画映射由 Order 8 统一设计。

---

## 3. 节点绑定（Scope ③，使用既有接口，禁止重造数据）

| 领域对象 | 银河节点 | 父级 | 数据来源（既有接口） |
|----------|----------|------|----------------------|
| Goal | Planet | 太阳（核心） | `GalaxyState.getGoalNodes()` |
| Agent | Satellite | 所属 Goal（`goal:<goalId>`） | `GalaxyState.getAgentNodes()` |
| Task | Orbit Node | 所属 Goal（`goal:<goalId>`） | `GalaxyState.getTaskNodes()` |
| Memory | Archive Node | 所属 Goal（`goal:<goalId>`） | `GalaxyState.getMemoryNodes()` |
| Knowledge | Link Node | 所属 Memory（`memory:<memoryId>`） | `GalaxyState.getKnowledgeLinks()` |

全部经由 Order 1–5 已建立的 `GalaxyState` 投影接口，无第二套数据、无重造。

---

## 4. 审计结论（Scope ①，实读非凭记忆）

- `solar-system.js`（24059→约 25000 字节）：**完全自包含**——硬编码 `SUN` + `PLANETS`（8 行星天文数据）+ 月球 + 土星环 + 星空 + 星云 + 流星 + 点击聚焦；渲染网格全部来自自身常量，**零连接** `AppState`/`GalaxyState`。它不 mock Goal，但「自己生成业务对象」正是 Scope ⑤ 的收敛目标。
- `galaxy-state.js`：干净的纯数据投影层，已含全部 `get*Nodes()` 接口——正是 Scope ③ 要求的既有接口。
- `app-state.js`：`getGalaxyNodes()` 为节点真源；`applyEvent` 为唯一写入入口。
- `event-bridge.js`：信封→`AppState.applyEvent` 桥接，白名单纪律完好。
- **结论**：品牌银河（太阳/八行星/星空/点击聚焦）是**银河本体**，依宪法红线须保留 100%；故收敛方案 = 保留品牌框架，**新增**对 `GalaxyRuntime` 动态状态节点的消费，而非改写品牌引擎。

---

## 5. solar-system.js 收敛（Scope ⑤，品牌本体 100% 不变）

最小侵入式改动（净增 ~60 行，品牌渲染引擎零重构）：
1. 构造器新增 `this.stateNodes = new Map()`（动态节点 mesh 登记表）。
2. `init()` 末尾订阅 `GalaxyState.onNodeChange(() => this.syncState())` 并首次 `syncState()`（事件驱动，**无新动画循环**）。
3. 新增 `syncState()`：读取 `GalaxyRuntime.getRenderModel()`，按 `planets/satellites/orbits/archives/links` 增删 mesh（确定性布局，父节点优先；状态节点置于太阳外围 115+ 避免与品牌天体重叠）；`MeshBasicMaterial` 单一占位中性色（状态→视觉映射留 Order 8）。
4. 新增 `_nodePosition()`：确定性坐标（父节点附近偏移 / 无父则外围环），**无动画参数**。
5. `node --check` 通过；品牌银河的自转/公转/星空/流星/点击聚焦逻辑一行未动。

---

## 6. 真实运行证据（Scope ⑥，真实创建 Goal）

### 6.1 后端集成真实运行（phase6-order6.integration.test.py，系统 py3.11，16/16 PASS）
真实驱动 `run_intent_gateway("分析当前项目状态") → runtime._run_goal`，捕获经 `publish_domain()` 发到 SSE 的规范事件序列：
```
INTENT_RECEIVED → INTENT_ANALYZING → INTENT_CLASSIFIED → INTENT_ACCEPTED
→ INTENT_CONVERTED_TO_GOAL → GOAL_CREATED → AGENT_CREATED → GOAL_STARTED
→ AGENT_STARTED → AGENT_THINKING → TASK_CREATED → TASK_CREATED → GOAL_RUNNING
→ AGENT_WORKING → TASK_STARTED → TASK_RUNNING → TASK_COMPLETED → TASK_STARTED
→ TASK_RUNNING → TASK_COMPLETED → AGENT_THINKING → REFLECTING → MEMORY_CREATED
→ MEMORY_STORED → MEMORY_LINKED → AGENT_COMPLETED → GOAL_COMPLETED
```
断言全部通过：
- 节点驱动事件 GOAL_CREATED / AGENT_CREATED / TASK_CREATED×2 / MEMORY_CREATED / MEMORY_STORED / MEMORY_LINKED / GOAL_COMPLETED 均由**真实后端**产生；
- **parentId 接线正确**：GOAL_CREATED 带 `goalId`+`intentId`；AGENT_CREATED/TASK_CREATED/MEMORY_CREATED 均带 `goalId`（→ 挂到 `goal:g1`）；MEMORY_LINKED 带 `knowledgeId`+`memoryId`（→ 挂到 `memory:<id>`）；
- 事件顺序 `GOAL_CREATED < AGENT_CREATED < TASK_CREATED < MEMORY_CREATED < MEMORY_LINKED < GOAL_COMPLETED`；
- 真实 DB：Goal=completed，knowledge_docs 已落库。

### 6.2 前端状态绑定真实回放（phase6-order6.frontend.test.js，node，17/17 PASS）
将 6.1 的真实事件序列（同 payload）经 `AppState.applyEvent` 回放 → `GalaxyState` 自动同步 → `GalaxyRuntime.getRenderModel()` 断言：
- GOAL_CREATED 后 → `planets` 出现 `goal:g1`，state=Created；
- AGENT_CREATED 后 → `satellites` 出现 `agent:a1`，**parentId=goal:g1**；
- TASK_CREATED×2 后 → `orbits` 出现 `task:t1/t2`，**parentId=goal:g1**；
- GOAL_RUNNING/AGENT_WORKING 后 → Goal/Agent 状态同步为 **Running**；
- MEMORY_CREATED 后 → `archives` 出现 `memory:mem1`，parentId=goal:g1，state=Created；
- MEMORY_LINKED 后 → `links` 出现 `knowledge:k1`，**parentId=memory:mem1**，state=Completed；
- GOAL_COMPLETED 后 → Goal state=Completed（终态同步）；
- 失败/归档路径：AGENT_FAILED→state=Failed（Error→Failed 收敛）；MEMORY_ARCHIVED→state=Archived（Dormant→Archived 收敛）；
- 最终计数正确：1 Planet / 1 Satellite / 2 Orbit / 1 Archive / 1 Link。

**结论**：真实 Goal 创建后，GalaxyRuntime 模型实时出现 Goal Planet → Agent Satellite → Task Orbit → Memory Archive → Knowledge Link，且状态随事件流同步变化。银河从静态展示层变为真实系统状态可视化运行层，验证通过。

---

## 7. 合规声明
- ✅ Implementation Only / Architecture Frozen（未改任何冻结设计文档）。
- ✅ 未重新设计 Galaxy Interaction；未新增第二套状态系统。
- ✅ 未绕过 GalaxyState / AppState / Event Contract / Event Bridge / `publish_domain()`。
- ✅ 未做新 UI / 新 CSS / Shader / 光效 / 星空优化 / 动画调参 / Design Token / Three.js 重构。
- ✅ 银河本体（品牌太阳系）100% 保留。

**Order 6 已完成并验证。停止，不进入 Order 7，等待批准。**
