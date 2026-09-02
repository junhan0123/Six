# Phase 7 Order 1 — Computer World Model Foundation · 实施报告

> 作者：Senior Developer（高级开发工程师 / 吴八哥）
> 类型：**Implementation Only**（严格"完成即停"，未进入 Order 2）
> 前置冻结：Phase 6（245/245 PASS，双通道事件纪律，AppState 唯一写入，Galaxy/Overlay 纯投影，Policy Engine 四级权限，银河品牌 100% 保留）
> 本 Order 约束（已遵守）：不修改冻结架构 / 不重设计 Phase 7 / 不实现 OS 操作能力 / 不实现鼠标键盘控制 / 不实现视觉识别
> 纪律基线：Architecture Constitution（20 铁律）+ Phase 6 工程纪律（事件双端锁、AppState 唯一写入、Runtime 纯投影）

---

## 1. 修改文件列表

| 文件 | 变更 | 说明 |
|------|------|------|
| `xiao6-ui/zz-events.js` | 修改 | `EVENTS` 新增 19 个 Computer World Model 观测事件；新增 `BATCH_7` |
| `xiao6-ui/eventbus.py` | 修改 | `DOMAIN_EVENT_NAMES` 同步新增同 19 个名（单一来源纪律，与前端逐字相等） |
| `xiao6-ui/app-state.js` | 修改 | `state` 新增 `computer` 子树（8 集合）；`API` 新增 `getComputer()`；新增 19 个 reducer |
| `xiao6-ui/computer-state.js` | **新建** | 纯投影层，镜像 `galaxy-state.js` 模式（订阅 AppState、派生 computer、零 UI/Three.js/Overlay） |
| `xiao6-ui/tests/phase7-order1.frontend.test.js` | **新建** | Order1 验证 + `MockComputerProvider`（经 `AppState.applyEvent` 注入合法观测事件） |
| `tests/phase6-order1.frontend.test.js` | 修改 | 合约计数 38→57 |
| `tests/phase6-order3.frontend.test.js` | 修改 | 合约计数 38→57 |
| `tests/phase6-order4.frontend.test.js` | 修改 | 合约计数 38→57 |
| `tests/phase6-order5.frontend.test.js` | 修改 | 合约计数 38→57 |
| `tests/phase6-order8.frontend.test.js` | 修改 | 合约计数断言 38→57 + 文档注释 |
| `tests/phase6-order1.backend.test.py` | 修改 | `DOMAIN_EVENT_NAMES` 期望集合 +19 名 + 打印文案 38→57 |

**未触碰**（确认守住边界）：`policy_engine.py`、`galaxy-state.js`、`galaxy-runtime.js`、`overlay-runtime.js`、`solar-system.js`、`index.html`、`styles.css`、`premium.css`、鼠标/键盘/视觉/动作相关任何代码。

---

## 2. 架构影响分析

- **严格复用 Phase 6 纪律，未改冻结架构**：事件契约双端锁、AppState 唯一写入入口、Runtime 纯投影、银河品牌 100% 保留，全部不变。
- **ComputerState 角色 = GalaxyState 的兄弟投影**：订阅 `AppState.subscribe('*')`，单向派生 `state.computer`，不持有真相、不 emit 任何事件、无任何写入口（测试 D 已锁死）。
- **数据流（与 Phase 6 完全一致）**：
  ```
  OS 观察者(未来) → publish_domain → SSE → event-bridge.ingest
       → AppState.applyEvent（唯一写入）
       → reducer 写 state.computer
       → ComputerState 投影（只读派生）
  ```
  本 Order 仅建数据层 + `MockComputerProvider`（精确模拟上述通路的 `applyEvent` 段），**未接真实 Windows API**。
- **银河品牌零污染**：ComputerState 不向 `galaxyNodes` 写任何节点；world 状态未来经 Environment/Info Overlay 呈现，**不进入银河隐喻**。
- **Policy Engine 未改**：电脑能力注册（capability→risk 映射）按设计规范留 Order 2，本 Order 不涉及动作授权。
- **index.html 未改**：ComputerState 仍为纯数据模块，浏览器挂载延至构建 Environment Overlay 的后续 Order（保持"不依赖 UI"边界，且"完成即停"）。

---

## 3. Event Contract 变化

- **新增 19 个领域事件**（全部 `COMPUTER_*` 前缀，只读观测语义，无动作）：
  ```
  COMPUTER_WORLD_SYNC, WINDOW_OPENED, WINDOW_CLOSED, WINDOW_FOCUSED,
  APP_LAUNCHED, APP_EXITED, PROCESS_SPAWNED, PROCESS_TERMINATED,
  FILE_CREATED, FILE_MODIFIED, FILE_DELETED, PROJECT_DETECTED, PROJECT_UPDATED,
  BROWSER_NAVIGATED, BROWSER_TAB_OPENED, BROWSER_TAB_CLOSED,
  TERMINAL_SPAWNED, TERMINAL_EXITED, DEVICE_STATE_CHANGED
  ```
- **合约总数 38 → 57**。前端 `EVENTS` 与后端 `DOMAIN_EVENT_NAMES` **逐字相等**（Phase6 O1 后端对称测试 + 新测试 A2 子进程校验双重确认，无差集）。
- **动作类事件（`COMPUTER_ACTION_*`）按 Phase 7 设计规范留 Order 2**——本 Order 不引入，避免越界到动作能力（符合"不实现 OS 操作能力"约束）。
- **单一来源纪律保持**：所有新 reducer 统一用 `ZZ.EVENTS.X` 常量；无裸字面量（Phase6 O8 静态扫描仍 PASS，且新测试 §D 用变量传名规避误伤）。

---

## 4. 测试结果

**Phase 7 Order 1 前端（新增）：15/15 PASS**
- A 合约=57、19 事件均 `isEvent`、`BATCH_7`=19、前后端对称无差集
- B `Event→AppState→ComputerState` 投影一致（含 8 集合全量）
- C 生命周期增量（open/focus/close/exit/delete/tab）
- D `ComputerState` 只读（无写入口）、非合约事件被拒、无 UI/Three.js 引用
- E 经 `event-bridge` 信封路径流入 `AppState.computer`
- F 向后兼容（Goal/Agent/Task 既有事件不受影响）

**Phase 6 全量回归（重跑，无失败）**
- 前端：O1(7)/O2(22)/O3(39)/O4(19)/O5(19)/O6(17)/O7(26)/O8(4) = **172/172 PASS**
- 后端/集成：O1(3)/O2(9)/O3(16)/O4(16)/O5(17)/O6(16)/O7(10)/hotfix(5) = **92/92 PASS**

**本会话合计重跑：260/260 PASS，0 失败。**

---

## 5. 风险分析

| # | 风险 | 等级 | 状态 / 缓解 |
|---|------|------|------------|
| R1 | 投影陈旧（观测 TTL）：World Model 是带 TTL 的观测缓存，OS 真相变化若未及时经事件回流会陈旧 | 中（未来项） | 设计规范 §2/§6 已标注 TTL 纪律；本 Order 未实现观察者，仅数据层。风险为未来项，已记录。 |
| R2 | 状态越权写入：模块直改 ComputerState / AppState.computer | 高 | **已闭环**：测试 D 锁死（ComputerState 无写入口；唯一入口 `applyEvent`；非合约事件被拒并告警）。 |
| R3 | 事件命名漂移：新增 19 名前后端不一致 | 高 | **已闭环**：O1 后端对称测试 + O8 计数 + 新测试 A2 子进程校验三重锁死，无差集。 |
| R4 | 范围蔓延：误引入 OS 操作 / 鼠标键盘 / 视觉 / UI | 高 | **已控制**：确认零 OS 调用、零动作能力、零 UI 依赖、Policy Engine 未改、index.html 未改。 |
| R5 | 契约计数回归：扩展导致旧 38 计数断言失败 | 中 | **已处理**：同步更新 6 个测试断言（O1/O3/O4/O5/O8 前端 + O1 后端），全绿。 |
| — | Windows API 风险 / 误操作 / Agent 失控 | — | 属 Order 2+ 动作层，本 Order 不涉及（严格只读）。 |

---

## 结论

Phase 7 Order 1 **完成**：Computer World Model 基础层（`ComputerState` 纯投影 + `AppState.computer` 子树 + 19 个观测事件合约 + `MockComputerProvider`）已落地，工程纪律与 Phase 6 完全一致，**260/260 测试通过**。

按指令**完成后立即停止，等待批准进入 Order 2**（Action Model + Permission Guard + Execution，仅 Low/Medium 风险）。
