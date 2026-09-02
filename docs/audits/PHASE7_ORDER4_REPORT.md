# Phase 7 Order 4 — Agent Computer Loop Integration 交付报告

> 模式：**Implementation Only**（严格落地，未进入 Order 5）
> 日期：2026-08-03
> 负责人：Senior Developer（高级开发工程师）

---

## 一、修改文件清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `xiao6-ui/agent_runtime.py` | **修改** | `_execute_task` 增加电脑能力路由分支；新增 `_execute_computer_task` 方法（委托 `PermissionGuard`） |
| `xiao6-ui/tests/phase7-order4.backend.test.py` | **新增** | 后端单测：Task→Action 转换 / PermissionGuard 调用 / Executor 链路 / Verification 成功失败 / Event Contract 对称性 |
| `xiao6-ui/tests/phase7-order4.frontend.test.js` | **新增** | 前端单测：ComputerAction 7 个 reducer / AppState 单写 / Overlay·Galaxy 红线 |
| `xiao6-ui/tests/phase7-order4.integration.test.py` | **新增** | 集成测试：场景 A（记事本闭环）/ 场景 B（VS Code 确认门） |

**未改动**（确认无回归）：`eventbus.py`、`zz-events.js`、`permission_guard.py`、`capability_registry.py`、`computer_executor.py`、`verification.py`、`computer_action.py`、`app-state.js`、`galaxy-state.js`、`goals.py`、`tasks.py`、`policy_engine.py`，以及全部 Phase 6 / Phase 7 Order 1–3 模块与测试。

---

## 二、Agent → Computer 生命周期图

```
                         ┌─────────────────────────────────────────────┐
                         │  Intent Gateway (Order 5，本 Order 不进入)   │
                         │  INTENT_RECEIVED → INTENT_ACCEPTED → …       │
                         └───────────────────────────┬─────────────────┘
                                                       │ create_goal
                                                       ▼
   submit_goal() ──────────────► AGENT_CREATED ──► GOAL_STARTED
                                                       │
                          ┌────────────────────────────┴───────────────────────────┐
                          │  AgentRuntime._run_goal (PLANNING → EXECUTING → REFLECTING)│
                          │                                                          │
                          │   plan_goal → TASK_CREATED → TASK_STARTED/RUNNING         │
                          │           │                                              │
                          │           ▼  _execute_task                                │
                          │  ┌──────────────────────────────────────────────┐       │
                          │  │ 解析 tool = suggested_tool                    │       │
                          │  │  if capability_registry.is_known(tool):       │       │
                          │  │       └─► _execute_computer_task(...)  ◀ 本Order │       │
                          │  └──────────────────────────────────────────────┘       │
                          │           │                                              │
                          │           ▼  (委托 PermissionGuard 单例)                  │
                          │  guard.plan(cap, target, params)                         │
                          │       └─► ComputerAction 构造 + COMPUTER_ACTION_PLANNED   │
                          │           │                                              │
                          │           ▼  guard.run()                                  │
                          │  decide → Policy Engine.evaluate                         │
                          │       auto  ──────────────────────┐                      │
                          │       confirm ─► request_approval │ (复用既有模态通道)    │
                          │                  (AGENT_WAITING)  │                      │
                          │       block/deny ─► COMPUTER_ACTION_DENIED                 │
                          │           │ approve                                    │
                          │           ▼                                            │
                          │  computer_executor.execute ─► COMPUTER_ACTION_CALLED/DONE│
                          │           │                                            │
                          │           ▼  VerificationLayer.verify                   │
                          │  COMPUTER_ACTION_VERIFIED / UNVERIFIED                  │
                          │           │                                            │
                          │           ▼  (ok) TASK_COMPLETED                        │
                          └───────────┼────────────────────────────────────────────┘
                                      ▼
                          REFLECTING → AGENT_COMPLETED → GOAL_COMPLETED
```

**红线遵守**：Agent / Runtime 不拥有 `ComputerAction` 构造权（`guard.plan` 内部构造），不直调 `executor`（`guard.run` 内部调用）；confirm 流程 100% 复用既有 `policy_engine.request_approval` 模态通道，无第二权限系统。

---

## 三、Task → Action → Execute → Verify 流转

```
Task(note="suggested_tool=open_application args={target:notepad.exe}")
   │  _resolve_dispatch → _parse_suggested
   ▼
tool = "open_application", args = {target:"notepad.exe"}
   │  capability_registry.is_known(tool) == True  →  进入电脑能力分支
   ▼
_execute_computer_task(goal_id, task, capability, parameters)
   │  risk_of(capability)=="MEDIUM" → emit AGENT_WAITING
   │  guard.plan(capability, target, parameters, goal_id)   ← 构造 ComputerAction
   ▼
action (ComputerAction, status="planned")  + COMPUTER_ACTION_PLANNED
   │  guard.run(action, goal_id, default_deny=True)
   ▼
PermissionGuard.run:
   1) decide  → Policy Engine.evaluate(capability, params) → {decision:"confirm"}
   2) confirm → policy_engine.request_approval(...) → "approve"
   3) execute → computer_executor.execute(action)  → COMPUTER_ACTION_CALLED / DONE
   4) verify  → VerificationLayer.verify(action, result) → COMPUTER_ACTION_VERIFIED
   ▼
action (status="done"/"verified", verified=True)
   ▼
_execute_computer_task 返回 {ok:True, action_id, status, verified}
   ▼
_run_goal 循环 → TASK_COMPLETED → … → GOAL_COMPLETED
```

- **Task 类型（§4）**：以 `capability_registry.is_known(tool)` 检测实现 `computer_operation` 等效类型（§4「或等效」），不新增 DB 列、不破坏既有 Task 类型、不新建 Runtime。
- **复用既有 Agent Executor（§5）**：闭环为「已有 Agent Runtime ↓ Capability Registry ↓ Computer Executor」；未创建 `computer_agent.py` / `desktop_agent.py` / `computer_runtime.py`。

---

## 四、真实运行日志（场景 A：打开记事本，去重连续重复）

```
GOAL_CREATED
AGENT_CREATED
GOAL_STARTED
GOAL_UPDATED
AGENT_STARTED
AGENT_THINKING
TASK_CREATED
GOAL_RUNNING
AGENT_WORKING
TASK_STARTED
TASK_RUNNING
AGENT_WAITING                 ← MEDIUM 确认门（等待批准语义）
COMPUTER_ACTION_PLANNED      ← guard.plan 构造 ComputerAction
COMPUTER_ACTION_CALLED       ← guard.run → executor.execute 前
COMPUTER_ACTION_DONE         ← executor 返回 ok
COMPUTER_ACTION_VERIFIED      ← VerificationLayer 复核通过（真实 observer 确认）
TASK_COMPLETED
AGENT_THINKING
REFLECTING
AGENT_COMPLETED
GOAL_COMPLETED
```
`EXEC_CALLS = [{'capability':'open_application','target':'notepad.exe', ...}]`
→ 证明 **真实执行** 发生（非伪造事件），且 `COMPUTER_ACTION_VERIFIED` 由 `guard.run` 的 Verification 层真实产生。

（场景 B：打开 VS Code 同链路，额外验证 `AGENT_WAITING` + `request_approval` 被触发，批准后才执行。）

---

## 五、Event Contract 变更

- **结论：零新增事件**。Order 4 未引入任何新事件名。
- `COMPUTER_ACTION_PLANNED / CALLED / DONE / FAILED / DENIED / VERIFIED / UNVERIFIED`（7 个）已在 Order 2 / Order 3 落地，本 Order 仅消费。
- 后端 `eventbus.DOMAIN_EVENT_NAMES` = **64**，前端 `zz-events.js EVENTS` = **64**，二者集合逐字一致（单测 `Event Contract：前后端事件名集合完全一致` PASS）。
- 纪律遵守：`PermissionGuard` 全部经 `publish_domain` 发出；无字符串硬编码事件、无私自 SSE、无绕过 `publish_domain()`。

---

## 六、测试结果

| 套件 | 运行命令 | 结果 |
|------|----------|------|
| 后端单测 | `python tests/phase7-order4.backend.test.py` | **PASS 15/15** |
| 前端单测 | `node tests/phase7-order4.frontend.test.js` | **PASS 19/19** |
| 集成测试 | `python tests/phase7-order4.integration.test.py` | **PASS 13/13** |

**全量回归（Phase 6 O1–O8 + Phase 7 O1–O4）**：
- Python 后端/集成：12/12 PASS（含 `phase6-hotfix`、`phase6-order{1,2,3,4,5,6,7}`、`phase7-order{2,3,4}`）
- 前端：12/12 PASS（`phase6-order{1..8}`、`phase7-order{1,2,3,4}`）
- **总计：0 失败**

---

## 七、风险分析

| 风险点 | 评估 | 缓解 |
|--------|------|------|
| `open_application` 需观察者才能 VERIFIED | 默认 `guard` 的 `VerificationLayer(observer=None)` 会使 `open_application` 落到 `UNVERIFIED` | 生产须注入 `RealObserver`（已在 `verification.RealObserver` 提供）；测试已注入 `MockObserver` 验证 VERIFIED 路径。执行成功（`status=done`）仍判任务完成，验证仅复核，不阻断闭环 |
| MockExecutor 返回扁平结构（无 `data` 包裹） | 部分能力（read_file/list_process）在无 `data` 包裹时验证读到空 → `UNVERIFIED` | 仅 `browser_navigate` 可无观察者自检通过；真实 `RealComputerExecutor` 返回 `{data:...}` 形状，验证对齐。属 Order 1–3 既有约定，本 Order 未改动 |
| MEDIUM→confirm 在无人环境会阻塞 | `request_approval` 模态在无真实用户时超时/拒绝 | 生产由真实模态通道处理；测试以 `request_approval→"approve"` 模拟用户批准，验证「批准后才执行」语义 |
| `AGENT_WAITING` 对 MEDIUM 的先验假设 | `risk_of==MEDIUM ⟺ confirm` 对当前已注册实现能力确定成立 | 仅作 Agent 编排态展示；即便极端 block 场景，Guard 仍正确发 `DENIED`，不影响正确性 |
| 既有 Tool 路径回归 | 电脑分支为 `is_known` 前置拦截，未知工具完全走原 `execute_tool` 路径 | 回归测试全绿；路由分流单测 PASS |

---

## 八、架构合规检查（对照 §禁止事项 + §红线）

| 检查项 | 结果 |
|--------|------|
| 不修改冻结架构文档 | ✅ 未触碰任何 `.md` 规范文档 |
| 不重新设计 Agent Runtime | ✅ 仅新增路由分支 + 委托方法，运行时架构不变 |
| 不创建第二套 Agent | ✅ Computer Layer 作为能力，经既有 Agent Runtime 路由 |
| 不创建第二套 Tool 系统 | ✅ 非能力工具走原 `tools.execute_tool`；能力走 `PermissionGuard` |
| 不创建第二套 Permission 系统 | ✅ 100% 委托 `policy_engine`（`evaluate`/`request_approval`），无第二权限 |
| 不进入 Order 5 | ✅ 本 Order 止于闭环落地，停止等待批准 |
| 不实现 Vision/UI Automation/OCR/鼠标键盘 | ✅ 仅 `open_application`（`os.startfile`）等既有能力，无视觉/自动化 |
| 不扩大 Computer Layer 范围 | ✅ 仅把 Order 1–3 既有模块接入 Agent Runtime |
| Task→ComputerAction 接入顺序 | ✅ Agent↓Task↓ComputerAction↓PermissionGuard↓Executor（Agent 不构 ComputerAction） |
| Event Contract 纪律 | ✅ 全经 `publish_domain`，前后端 64 事件逐字一致 |
| AppState 纪律 | ✅ 状态仅经 Event→AppState.applyEvent→reducer；Executor/Agent 不直写 UI |
| Galaxy/Overlay 红线 | ✅ Galaxy 仅 Task 轨道态；Overlay 取 `computer.actions`；无新 Computer Galaxy 节点（前端单测 `getNode('action:a1')===null` PASS） |

---

## 结论

Phase 7 Order 4 已完成：既有 Agent Runtime 正式接入 Computer Capability，形成首个完整闭环
`User Intent → … → Goal → Agent Runtime → Task → ComputerAction → PermissionGuard → Executor → Verification → Event → AppState → ComputerState → Reflection`，
真实事件、零伪造，全量回归 0 失败。**按纪律已停止，未进入 Order 5，等待批准。**
