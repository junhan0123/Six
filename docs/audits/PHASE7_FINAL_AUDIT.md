# PHASE 7 FINAL AUDIT — Computer Operating Layer MVP (Orders 1–4)

> 审计类型：**Audit Only / Freeze Preparation**
> 审计依据：Phase 6 `Implementation Readiness v1.0`、事件合约纪律、Policy Engine 单一裁决源
> 审计日期：2026-08-03
> 代码基线：`G:/xiao6/xiao6-ui/`（Phase 6 冻结系统 + Phase 7 Orders 1–4）
> 纪律红线（本次审计严禁）：新增功能 / 新增 Order / Order 5(Vision·OCR·UI Automation) / 浏览器自动化 / 扩张 Computer Capability / 改动 Phase 7 架构 / 重构既有 Runtime / 改动 Galaxy 语义 / 改动 Phase 6 冻结系统。

---

## 1. Phase 7 总览

Phase 7 实现 **Computer Operating Layer MVP**，仅覆盖 Orders 1–4，未进入 Order 5：

| Order | 范围 | 核心文件 | 状态 |
|-------|------|----------|------|
| Order 1 | Computer World Model（只读世界观测） | `computer-state.js` | ✅ |
| Order 2 | Action Model + Permission Guard + Capability Registry | `computer-action.js`、`computer_action.py`、`capability_registry.py`、`permission_guard.py` | ✅ |
| Order 3 | Computer Executor + Verification | `computer_executor.py`、`verification.py` | ✅ |
| Order 4 | Agent Computer Loop 集成 | `agent_runtime.py`（`_execute_computer_task`） | ✅ |

- **未实现（按冻结纪律，非冻结阻塞）**：Order 5（Vision/OCR/UI Automation）、HIGH/CRITICAL 能力（声明但未实现，由 Policy Engine 默认拒绝）。
- **Galaxy 语义零改动**：Phase 7 不新增 Computer Galaxy 节点；银河资产与交互规范保持 Phase 6 冻结态。
- **Phase 6 冻结系统零改动**：Intent Gateway / Goal Runtime / Event Bridge / AppState / Policy Engine / Galaxy Runtime / Overlay Runtime 均未被修改。

---

## 2. 架构生命周期审计（§二）

完整调用链（实测读码确认，无旁路）：

```
User Intent
  → Intent Gateway（Phase 6，publish_domain）
  → Goal Runtime（GOAL_CREATED…）
  → Agent Runtime（agent_runtime.py::_execute_task）
        └─ is_known(tool) == True
              → _execute_computer_task(goal_id, task, tool, args)
                    → guard.plan(...)             # 构造 ComputerAction + COMPUTER_ACTION_PLANNED
                    → guard.run(action, goal_id, default_deny=True)
                          → PermissionGuard.decide()   # 复用 Policy Engine
                          → ComputerExecutor.execute() # 唯一调用点（Real/Mock）
                          → VerificationLayer.verify()
                          → publish_domain(VERIFIED/UNVERIFIED/FAILED)
  → Event → AppState.applyEvent（唯一写入口）
  → ComputerState / GalaxyState / OverlayRuntime（纯投影 / 纯变换，只读）
```

审计结论：
- Agent **从不**直接构造 `ComputerAction`、从不直调 `executor`、从不直连 OS。
- 全链路只存在 **一个** Runtime（`agent_runtime`）、**一个** Permission 裁决源（Policy Engine）、**一个** Tool/Executor 入口（`PermissionGuard.run`）。
- 无第二 Runtime / 第二 Permission / 第二 Tool 系统。

---

## 3. Agent Boundary 审计（§三）

`agent_runtime.py::_execute_computer_task`（约 line 252）职责边界：

- ✅ 允许：创建 Goal / Task（既有）；通过 `is_known(tool)` 探测能力归属；委托 `guard.plan` / `guard.run`。
- ❌ 禁止（实测均未发生）：直接 `ComputerExecutor.execute`、直接 OS 调用、绕过 `PermissionGuard`、自行改写 `ComputerState`、自修改 Phase 7 架构。
- MEDIUM 风险复用既有 `request_approval` modal 流（`AGENT_WAITING` 先行），与 Agent-Tool 确认路径一致。
- `ok = action.status == "done"`：Agent 仅消费 Guard 返回的 `ComputerAction` 结果，不持有执行细节。

结论：**Agent Boundary 严守，无越权。**

---

## 4. 权限模型审计（§四）

- **唯一裁决源 = Policy Engine**（`policy_engine.evaluate(tool, args, goal_id, default_deny)` → `{decision: auto|confirm|block}`）。
- 能力风险分层（`capability_registry.py::RISK_TIER`）：
  - `LOW` → `AUTO`（归入 `tools.READONLY_TOOLS`，自动放行）
  - `MEDIUM` → `CONFIRM`（默认需确认）
  - `HIGH` / `CRITICAL` → 声明但未实现，`PermissionGuard.decide` 直接 `block`（默认拒绝）。
- `capability_registry` **复用** Policy Engine 与 `READONLY_TOOLS`，**未新建**任何权限表 / 第二权限系统（grep：`computer_policy.py` / `desktop_permission.py` 均不存在）。
- 未知能力：`PermissionGuard.plan` 在 `is_known` 失败时抛 `ValueError`（测试 order2 验证），拒绝规划。

结论：**权限模型单一来源、默认拒绝、无影子权限系统。**

---

## 5. Executor 审计（§五）

`computer_executor.py`：

- `MockComputerExecutor`：仅记录调用，返回扁平 `_mock_result`（无 `data` 包裹，仅测试用）。
- `RealComputerExecutor(timeout=30.0, max_read_bytes=1_000_000, audit_path=None)`：
  - 真实操作：`_op_read_file`（**只读**，无写/删）、`_op_list_process`（`tasklist`）、`_op_capture_screen`（仅内存，`mss`/`PIL` 惰性加载，不落盘）、`_op_get_window_info`、`_op_open_application`（`os.startfile` / 列表式 `Popen`，**无 `shell=True`**）、`_op_focus_window`（`ctypes.SetForegroundWindow`）、`_op_browser_navigate`（`webbrowser.open`）。
  - 超时：`ThreadPoolExecutor` + `fut.result(timeout)`；取消：`threading.Event`；审计：内存 `_audit` + 可选 JSONL。
  - 结构化返回：`{ok, capability, target, data, error, duration_ms, timed_out, cancelled}`。
  - **仅经 `PermissionGuard.run` 调用**；拒绝 HIGH/CRITICAL。
- 安全扫描（实测）：
  - ❌ 无 `shell=True`（仅文档注释提及，真实代码用 `os.startfile` / 列表 `Popen` / `webbrowser.open`）。
  - ❌ 无 `os.system` / `subprocess.call(shell=True)` / 任意命令执行。
  - ❌ 无未授权文件修改（读文件仅 `read`，无 `write`/`unlink`/`delete`）。
  - ❌ 无扩张 Computer Capability（仅 7 个已实现 LOW+MEDIUM）。

结论：**Executor 安全、受控、无越权 OS 操作。**

---

## 6. Verification 审计（§六）

`verification.py::VerificationLayer.verify(action, result)` → `(verified, detail)`：

- 执行 → 观察 → 复核 闭环：`executor.execute` 返回 → `VerificationLayer.verify` → `publish_domain` 回写 `COMPUTER_ACTION_VERIFIED` / `COMPUTER_ACTION_UNVERIFIED` / `COMPUTER_ACTION_FAILED`。
- 每能力 `_verify_*` 规则；`RealObserver` 仅只读快照，无写/无 shell。
- 默认 `observer=None`：仅 `browser_navigate` 自带自验可达 `VERIFIED`；`open_application` 等需接入观察者方达 `VERIFIED`，否则为 `UNVERIFIED`（**设计态**，MEDIUM 确认流仍前置拦截，非安全漏洞）。
- AppState reducer（`app-state.js`）将 `VERIFIED/UNVERIFIED/FAILED` 写入 `state.computer.actions[id]` 只读投影，回环闭合。

结论：**Verification 闭环完整，状态回流经单一事件通道。**

---

## 7. 事件合约审计（§七）

实测对称校验（本次审计重新跑数，非依赖记忆）：

```
BACKEND_DOMAIN_EVENTS  64
FRONTEND_EVENTS        64
SYMMETRIC              True
DIFF_B_ONLY            []
DIFF_F_ONLY            []
BACKEND_SYSTEM         6  [agent_state, memory_reminder, modal, proactive, scene, wakeword_detected]
FRONTEND_SYSTEM        6  [agent_state, memory_reminder, modal, proactive, scene, wakeword_detected]
SYSTEM_SYMMETRIC       True
```

- 后端 `eventbus.DOMAIN_EVENT_NAMES`（64，set literal）= 前端 `zz-events.js EVENTS`（64）逐字一致。
- `publish_domain()` 对未注册名抛 `ValueError`；`SYSTEM_EVENT_NAMES`（6）+ `publish_system()` 为独立扁平通道，与领域事件互斥、无同义漂移。
- 全仓 grep：**未发现** `bus.publish(TOPIC_SSE, domain-event)` 旁路、未发现硬编码事件名副本、未发现第二 SSE 私有通道。
- 构成（64 = Phase6 38 + Intent 6 + Order1 19 + Order2 7），与 order3 后端测试断言一致。

结论：**事件合约单一来源、前后端严格对称、无旁路。**

---

## 8. AppState / Galaxy / Overlay 合规审计（§八）

- **AppState 唯一写入口** = `Event → AppState.applyEvent(name, payload)`。所有写经 `reducers[name]` → `emit`。
  - `state.computer` 子树（8 集合 + `actions` 只读投影）仅由合约事件驱动。
  - `AppState` 内**无 OS 调用、无 executor、无 Three.js**。
- **ComputerState（`computer-state.js`）**：纯投影，订阅 `AppState '*'`，仅暴露 `get*` / `onWorldChange`，**无写入口、无 UI、无 Overlay、无 emit**。
- **GalaxyState（`galaxy-state.js`）**：`getGoalNodes/getAgentNodes/getTaskNodes/getMemoryNodes/getKnowledgeLinks/getIntentNodes`，**无 `getComputerNodes`、无 Computer Galaxy**（前端测试 `phase7-order4.frontend.test.js` 断言 `action:a1` 不入 GalaxyState）。
- **OverlayRuntime（`overlay-runtime.js`）**：纯数据变换（AppState + GalaxyState → Overlay Model），`mapType` 仅做显示分类，**无 DOM / 无 Three.js / 无 API / 无业务逻辑**。
- **EventBridge（`event-bridge.js`）**：`ingest(raw)` 仅接受 `ZZ.isEvent(name)` 的合约事件，调用 `AppState.applyEvent`，无原始领域旁路。

结论：**状态写唯一、投影只读、Galaxy 语义零改动、Overlay 显示-only。**

---

## 9. 测试结果（§九）

### 9.1 Phase 7 MVP（本次审计重新执行）

| 套件 | 运行方式 | 结果 |
|------|----------|------|
| phase7-order2.backend | `python` 脚本 | PASS 21 / FAIL 0 |
| phase7-order3.backend | `python` 脚本 | PASS 17 / FAIL 0 |
| phase7-order4.backend | `python` 脚本 | PASS 15 / FAIL 0 |
| phase7-order4.integration | `python` 脚本 | PASS 13 / FAIL 0 |
| phase7-order1.frontend | `node` | PASS 15 / FAIL 0 |
| phase7-order2.frontend | `node` | PASS 20 / FAIL 0 |
| phase7-order3.frontend | `node` | PASS 12 / FAIL 0 |
| phase7-order4.frontend | `node` | PASS 19 / FAIL 0 |

**Phase 7 MVP 合计：132 / 132 PASS，0 FAIL。**

### 9.2 Phase 6 全量回归（前序审计验证基线）

前序审计已重跑 Phase 6 全量（hotfix / order1–8 后端+前端+集成）：
- Python 158 / 158 PASS；Frontend 219 / 219 PASS。
- **合并 377 / 377 PASS，0 失败，0 回归。**
- Phase 7 改动未触及 Phase 6 冻结系统（§八 已证实），故 Phase 6 冻结态保持有效。

---

## 10. 风险清单（已知、可接受、非冻结阻塞）

| # | 风险 | 影响 | 处置 | 是否阻塞冻结 |
|---|------|------|------|--------------|
| R1 | `open_application` 默认 `observer=None` → 仅 `UNVERIFIED`，需接入 Observer 方达 `VERIFIED` | 完成态粒度 | MEDIUM 确认流前置拦截，安全；MVP 范围外接入 Observer | 否 |
| R2 | `MockComputerExecutor` 返回扁平结果（无 `data` 包裹），仅 `browser_navigate` 自验 | 仅测试路径 | 不影响生产 `RealComputerExecutor`（结构化返回） | 否 |
| R3 | `RealComputerExecutor._op_capture_screen` 惰性依赖 `mss`/`PIL`，缺包时该操作优雅失败 | 单操作降级 | 文档化依赖；非核心路径 | 否 |
| R4 | HIGH/CRITICAL 能力声明但未实现 | 能力缺口 | Policy Engine 默认 `block`，安全默认 | 否 |
| R5 | `default_deny=True` 下 MEDIUM 全需确认，可能频繁弹窗 | 体验 | 属预期安全行为；可后续调 `READONLY_TOOLS` 白名单 | 否 |

所有风险均为**已知设计态/缺口**，无安全越权、无架构旁路、无合约破坏。

---

## 11. Freeze Recommendation（冻结建议）

- ✅ 架构生命周期无旁路，单一 Runtime / 单一权限源 / 单一执行入口。
- ✅ Agent Boundary 严守，无越权 OS / Executor / State 直写。
- ✅ 权限模型默认拒绝，无影子权限系统。
- ✅ Executor 受控（超时/取消/审计/结构化返回），无 `shell=True`、无未授权文件改删、无能力扩张。
- ✅ Verification 闭环完整，状态经单一事件通道回流。
- ✅ 事件合约前后端严格对称（64=64，6=6），无旁路、无副本。
- ✅ AppState 唯一写、ComputerState/GalaxyState/Overlay 纯投影/纯变换，Galaxy 语义零改动。
- ✅ 测试：Phase 7 MVP 132/132 PASS；Phase 6 全量 377/377 PASS，0 回归。
- ✅ 红线纪律全数遵守（无新功能 / 无新 Order / 无 Order 5 / 无浏览器自动化 / 无架构改动 / 无 Runtime 重构 / 无 Galaxy 改动 / 无 Phase 6 改动）。

**结论：Phase 7 Computer Operating Layer MVP（Orders 1–4）已达到冻结就绪标准。**

---

PASS: Phase 7 MVP 完成，可以冻结。
