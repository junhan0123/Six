# Phase 7 Order 2 — Action Model + Permission Guard（完成报告）

> **模式**：Strict Implementation Only（实现层，仅落地设计，不进入 Order 3）
> **前置**：Phase 7 Order 1 已冻结（Computer World Model，事件合约 38→57）
> **本 Order 事件合约**：57 → **62**（+5 `COMPUTER_ACTION_*`）
> **状态**：✅ 实现完成，全部测试通过。**已停止，等待批准进入 Order 3。**

---

## 0. 本 Order 严守的边界（红线，全部遵守）

| 禁止项 | 本 Order 执行情况 |
|---|---|
| 不进入 Order 3 | ✅ 仅落地 Action Model + Permission Guard，未触碰执行编排 |
| 不实现完整 Agent Computer Loop | ✅ 仅提供 Guard 链，未接 Agent 主循环 |
| 不实现视觉点击 | ✅ 无任何鼠标/坐标/视觉识别代码 |
| 不实现 High/Critical 操作 | ✅ `modify_file/execute_command/kill_process` 及 `delete/system/network` 仅登记为占位，执行一律 DENIED |
| 不绕过 Policy Engine | ✅ Capability Registry 完全复用既有 Policy Engine（auto/confirm/never + default_deny + dangerous 拦截） |
| 不新增第二权限系统 | ✅ 零新权限表、零新风险体系；风险档位仅映射到既有 Policy Engine 决策 |

**执行安全**：本 Order 的 Executor **只允许 Mock Executor**（LOW/MEDIUM 返回安全/预览结果，HIGH/CRITICAL 抛 `NotImplementedError`），不调用任何真实 OS 危险操作。

---

## 1. 修改文件列表

### 1.1 新建后端（Python，`G:/xiao6/xiao6-ui/`）
| 文件 | 作用 |
|---|---|
| `capability_registry.py` | Capability Registry：声明 13 个能力（7 已实现 LOW/MEDIUM + 6 HIGH/CRITICAL 占位）；`_register_into_policy_engine()` 将 LOW 能力注入 `tools.READONLY_TOOLS`；复用 `policy_engine.AUTO/CONFIRM`；`RISK_TIER={LOW:AUTO, MEDIUM:CONFIRM}` |
| `computer_action.py` | `ComputerAction` 数据模型：`actionId / capability / target / parameters / risk / expectedEffect / permissionDecision / result`（+ `goalId/status/decisionReason/createdAt`）；`to_dict()/from_dict()` |
| `computer_executor.py` | `MockComputerExecutor`：本 Order 唯一合法 Executor；LOW/MEDIUM 返回安全预览结果，HIGH/CRITICAL 抛 `NotImplementedError`；支持 `fail_next` 用于失败路径测试 |
| `permission_guard.py` | `PermissionGuard`：`plan()` / `decide()` / `run()`；`run()` 强制完整链路 decide→(confirm?request_approval)→executor.execute→publish `COMPUTER_ACTION_CALLED/DONE/FAILED`；HIGH/CRITICAL 与未知能力 → DENIED；模块级单例 `guard` |

### 1.2 新建前端（JS，`G:/xiao6/xiao6-ui/`）
| 文件 | 作用 |
|---|---|
| `capability-registry.js` | `ZZCapabilities` 全局对象：镜像后端能力 + 风险档位 |
| `computer-action.js` | `ZZComputerAction` 构造器 + `fromDict/toDict`；未知能力抛错 |
| `permission-guard.js` | `ZZPermissionGuard`：`plan()/decide()/run()`；`defaultDecider` 映射 LOW→auto、MEDIUM→confirm、HIGH/CRITICAL→deny；`mockExecutor` 返回安全预览；经 `AppState.applyEvent` 发事件；`run` 仅在审批通过后才调 executor |

### 1.3 修改（事件合约 + 投影 + 回归计数）
| 文件 | 改动 |
|---|---|
| `eventbus.py` | `DOMAIN_EVENT_NAMES` 新增 5 个 `COMPUTER_ACTION_*`（57→**62**） |
| `zz-events.js` | `EVENTS` 新增 5 个 `COMPUTER_ACTION_*`（57→**62**）；新增 `BATCH_7_ACTION` 数组（5 事件）；API 导出 `BATCH_7_ACTION` |
| `app-state.js` | `state.computer` 新增 `actions: {}`；新增 5 个 reducer（`COMPUTER_ACTION_PLANNED/CALLED/DONE/FAILED/DENIED`）+ 辅助 `_actionRec(id)` 写入 `state.computer.actions[actionId]` |
| `tests/phase6-order1.backend.test.py` | 期望事件集合 +5（→62） |
| `tests/phase6-order3.frontend.test.js` | 断言计数 57→62 |
| `tests/phase6-order4.frontend.test.js` | 断言计数 57→62 |
| `tests/phase6-order5.frontend.test.js` | 断言计数 57→62 |
| `tests/phase6-order8.frontend.test.js` | 断言计数 57→62 |
| `tests/phase7-order1.frontend.test.js` | 断言计数 57→62 |

### 1.4 新建测试
| 文件 | 作用 |
|---|---|
| `tests/phase7-order2.backend.test.py` | 后端链验证（21 项） |
| `tests/phase7-order2.frontend.test.js` | 前端链验证（20 项） |

---

## 2. 架构影响

- **新增 Computer Action 执行安全层（介于 Agent 与 OS 之间）**：
  `Task → Capability → Policy Engine → Decision → Execute/Confirm/Deny`
- **Capability Registry 是「能力声明」层，不是「授权」层**：它只描述有哪些能力、风险档位如何，授权决策 100% 委托给既有 Policy Engine。零新权限/风险系统。
- **Permission Guard 是「唯一执行入口」**：Agent **禁止直接调用 Executor**；Executor 只能从 `Guard.run()` 内部被调用。这从源头切断「Agent 绕过审批直接执行危险操作」的路径。
- **ComputerAction 成为可审计的执行单元**：每次动作都带 `actionId / capability / risk / permissionDecision / result`，并落盘为事件，前端 `state.computer.actions` 为纯投影（只读），与 Phase 7 Order 1 的 World Model 投影纪律一致。
- **HIGH/CRITICAL 在本 Order 是「设计即拒绝」**：能力已登记（便于 Order 3+ 扩展），但决定一律 DENIED，Executor 不实现，不接触真实 OS。
- **事件合约继续「双端单一来源」**：后端 `DOMAIN_EVENT_NAMES` 与前端 `EVENTS` 逐字相等（已脚本校验 62==62），无散落硬编码。

---

## 3. 权限模型变化

**结论：权限模型没有新增任何概念，完全复用既有 Policy Engine。**

- **复用点**：
  - `policy_engine.AUTO / CONFIRM / NEVER` 三档决策原样复用。
  - `tools.READONLY_TOOLS` 原样复用：Capability Registry 将 LOW 能力（`read_file/capture_screen/get_window_info/list_process`）注入 `READONLY_TOOLS`，从而自动获得 `AUTO`（免确认）决策——与既有只读工具同待遇。
  - `policy_engine.evaluate()` 的 default_deny、dangerous 命令拦截、never 工具拦截全部原样生效，未做任何削弱。
- **风险档位 → Policy 决策的映射（仅声明，非新系统）**：
  - `LOW` → `AUTO`（免确认，等同只读工具）
  - `MEDIUM` → `CONFIRM`（需 modal 审批，等同既有 confirm 工具）
  - `HIGH / CRITICAL` → 本 Order 设计为 `DENIED`（能力登记但未实现，未来 Order 再决定映射）
- **Agent 调用纪律（新增约束）**：Agent 不再直接 `execute_tool()`，而是通过 `PermissionGuard` 走「能力→策略→决策→执行」四段式；审批 UI 复用既有 `app.js` 的 `agent_approval` modal + `POST /api/agent/approval`。

---

## 4. Event Contract 变化

- **新增 5 个领域事件（仅追加，不改既有）**：
  | 事件 | 触发时机 | 载体 |
  |---|---|---|
  | `COMPUTER_ACTION_PLANNED` | Guard.plan() 生成 ComputerAction | domain |
  | `COMPUTER_ACTION_CALLED` | Guard.run() 实际调用 Executor 前 | domain |
  | `COMPUTER_ACTION_DONE` | Executor 执行成功 | domain |
  | `COMPUTER_ACTION_FAILED` | Executor 执行异常 | domain |
  | `COMPUTER_ACTION_DENIED` | 决策为 deny / 未知能力 / HIGH·CRITICAL | domain |
- **总数**：`DOMAIN_EVENT_NAMES` 38（冻结）→ 57（Order1）→ **62（Order2）**；前端 `EVENTS` 同步 **62**。
- **双端一致性**：已用脚本分别统计后端 set 与前端的 `names()`，均为 62，逐字相等。
- **前端投影**：`app-state.js` 新增 `state.computer.actions` 与 5 个 reducer，写入 `state.computer.actions[actionId]`，供 UI 只读展示动作轨迹（与 World Model 投影同一模式）。
- **回归测试同步**：6 个既有测试中的事件计数断言全部从 57 提升到 62，确保任何一端漏改会被立即捕获。

---

## 5. 测试结果

### 5.1 本 Order 新增测试
| 测试 | 结果 | 覆盖 |
|---|---|---|
| `tests/phase7-order2.backend.test.py` | **21/21 PASS** | A 能力注册表 / B 前后端事件对称（Node 子进程读前端 names）/ C Policy Engine 复用 / D Guard 全链路（LOW→DONE、MEDIUM+approve→DONE、MEDIUM 无 goal→DENIED、HIGH→DENIED、未知能力→plan 报错、Agent 不可绕过 executor、失败路径） |
| `tests/phase7-order2.frontend.test.js` | **20/20 PASS** | A 合约 62 / B 注册表 / C ComputerAction 模型 / D Guard 全链路 / E AppState `actions` 投影 |

### 5.2 回归（全部绿）
| 测试 | 结果 |
|---|---|
| `phase6-order1.backend` | 3/3 |
| `phase6-order3.frontend` | 39/39 |
| `phase6-order4.frontend` | 19/19 |
| `phase6-order5.frontend` | 19/19 |
| `phase6-order8.frontend` | 4/4 |
| `phase7-order1.frontend` | 15/15 |

**合计**：本 Order 41 项 + 回归 99 项，**0 失败**。

### 5.3 关键链路断言（节选）
- LOW 能力（`read_file`）经 Guard → Policy Engine(AUTO) → Executor(mock) → `DONE`，且前端 `state.computer.actions[id].status==="done"`。
- MEDIUM 能力（`open_application`）+ 审批通过 → `CALLED`→`DONE`；无 goal/未审批 → `DENIED`。
- HIGH 能力（`modify_file`）→ `decide()` 置 `permissionDecision="deny"` 且 `status="denied"`，发出 `COMPUTER_ACTION_DENIED`，Executor 不被调用。
- 未知能力 `plan()` 直接抛错（不生成 action），杜绝幽灵动作。
- Agent 直连 Executor 的旁路路径在测试中无法触发（executor 仅暴露于 Guard 内部）。

---

## 6. 风险分析

### 6.1 本 Order 已消除的风险
| 风险 | 缓解 |
|---|---|
| Agent 绕过审批直接执行危险操作 | Executor 仅能从 `Guard.run()` 内部调用；Agent 无直接执行入口 |
| 新增第二套权限系统导致权限语义分裂 | 零新权限/风险表，全部映射回既有 Policy Engine |
| HIGH/CRITICAL 能力被误执行 | 设计即 `DENIED`，Executor 不实现，抛 `NotImplementedError` |
| 真实 OS 被破坏 | 本 Order Executor 仅为 Mock，不触碰任何真实文件/进程/网络 |
| 事件合约前后端漂移 | 双端 set 脚本校验 62==62；6 个回归断言锁定计数 |

### 6.2 遗留到 Order 3+ 的风险（本 Order 刻意不解决）
- **HIGH/CRITICAL 真实执行**：`modify_file/execute_command/kill_process/delete/system/network` 仅登记占位，Order 3+ 需设计真实 Executor、真实 Policy 映射与更细粒度确认（如二次确认、影响范围预览）。
- **Agent Computer Loop 编排**：本 Order 未接入 Agent 主循环；Order 3 需定义「Agent 如何基于 World Model 规划 Action → 提交 Guard」的闭环。
- **真实审批 UX**：本 Order 复用既有 modal，但 Computer Action 的「影响范围/回滚预览」等更丰富的确认信息尚未设计。

### 6.3 总体风险评级
**本 Order 风险：低。** 所有改动均为「声明 + 安全层 + Mock 执行」，不触碰真实 OS、不削弱既有 Policy Engine、不新增权限概念。银河品牌资产（太阳/轨道/星球/星空）与本 Order 零交集，未改动。

---

## 7. 结论与下一步

✅ Phase 7 Order 2 全部实现完成，测试全绿（62 事件双端对称，41+99 项断言通过）。
⛔ **按指令：完成即停止，未进入 Order 3。**
👉 **等待批准进入 Order 3**（Action Model + Permission Guard + Execution：Low/Medium 真实执行、Agent Computer Loop 部分闭环）。

— 报告生成于 Phase 7 Order 2 完成节点
