# Phase 7 Order 3 — Computer Executor + Verification Foundation

> **状态**：Implementation Only（已完成，已停）。等待批准进入 Order 4。
> **前置**：Phase 7 Order 1 / Order 2 已冻结。
> **红线遵守**：未进入 Order 4 / 未实现完整 Vision / 未实现 High·Critical 操作 / 未开放任意 Shell / 未修改或删除无关文件 / 未绕过 Permission Guard / 未创建第二执行系统。

---

## 1. 修改文件列表

### 1.1 后端（Python，`xiao6-ui/`）

| 文件 | 改动性质 | 说明 |
|---|---|---|
| `computer_executor.py` | 重写（保留 Mock） | 保留 `MockComputerExecutor`；新增 `RealComputerExecutor`（安全真实执行）。 |
| `verification.py` | **新建** | `VerificationLayer` + `RealObserver`，执行后重新观察。 |
| `permission_guard.py` | 修改 | `PermissionGuard.__init__` 增加 `verifier` 注入；`run()` 在 DONE 后接 Verification 并发 VERIFIED/UNVERIFIED。 |
| `computer_action.py` | 修改 | `ComputerAction` 增加 `verified` / `verificationDetail` 字段及 `to_dict`/`from_dict`。 |
| `eventbus.py` | 修改 | `DOMAIN_EVENT_NAMES` 增加 `COMPUTER_ACTION_VERIFIED`、`COMPUTER_ACTION_UNVERIFIED`（总数 62 → 64）。 |

### 1.2 前端（JS，`xiao6-ui/`）

| 文件 | 改动性质 | 说明 |
|---|---|---|
| `zz-events.js` | 修改 | `EVENTS` 增加 2 个验证事件；`BATCH_7_ACTION` 由 5 → 7。 |
| `app-state.js` | 修改 | `_actionRec` 初始化 `verified/verificationDetail`；新增 2 个 reducer（VERIFIED / UNVERIFIED）。 |
| `permission-guard.js` | 修改 | `run()` 在 DONE 后接 `ctx.verifier`（可选注入，未注入则跳过，保持 Order 2 前端测试绿）。 |
| `computer-action.js` | 修改 | `ComputerAction` 增加 `verified / verificationDetail` 字段及 `toDict`/`fromDict`。 |

### 1.3 测试

| 文件 | 性质 | 说明 |
|---|---|---|
| `tests/phase7-order3.backend.test.py` | **新建** | 17 项检查（Executor 架构 / Mock 流程 / Low 真实安全 / Medium Confirm / Permission 拒绝 / Verification 成功失败 / 合约对称）。 |
| `tests/phase7-order3.frontend.test.js` | **新建** | 12 项检查（合约 64 / Cap 注册表 7 / Guard+Verification / AppState 投影）。 |
| `tests/phase6-order1.backend.test.py` | 计数 bump | 64 名契约对称。 |
| `tests/phase6-order1.frontend.test.js` | 计数 bump | 57 → 64（契约名单一来源）。 |
| `tests/phase6-order3/4/5.frontend.test.js` | 计数 bump | 64。 |
| `tests/phase6-order8.frontend.test.js` | 计数 bump | 62 → 64。 |
| `tests/phase7-order1.frontend.test.js` | 计数 bump | 62 → 64（含后端对称 64）。 |
| `tests/phase7-order2.backend.test.py` | 计数 bump | 64。 |
| `tests/phase7-order2.frontend.test.js` | 计数 bump | 合约 64；`BATCH_7_ACTION` 5 → 7。 |

> 部署备注：前端 JS 改动按项目惯例需在 `index.html` 的 `?.js?v=` 处 bump 缓存版本并重启 Electron + Ctrl+F5 生效。本次为代码+测试交付，未改动 `index.html`（属运行时生效步骤，留待部署时执行）。

---

## 2. Executor 架构

### 2.1 调用链（单一路径，Agent 不可直连 Executor）

```
Task
  └─> ComputerAction (数据模型：capability / target / args / status / verified ...)
        └─> PermissionGuard.decide()   → Policy Engine 复用（LOW=auto / MEDIUM=confirm / HIGH·CRITICAL=deny）
              └─> PermissionGuard.run()
                    ├─ confirm 路径 → 弹 modal 等用户批准
                    └─ 批准后 → Executor.execute(action)   ← Agent 永远不直接调用
                          └─> VerificationLayer.verify(action, result)
                                └─> publish COMPUTER_ACTION_VERIFIED / UNVERIFIED
```

> `tools.execute_tool`（Agent 工具通道）是**独立**的 Agent-tool 路径，不属于 Computer 执行系统，未创建第二执行系统。

### 2.2 `RealComputerExecutor`（可取消 / 可超时 / 可审计 / 结构化返回）

```python
class RealComputerExecutor:
    def __init__(self, timeout=30.0, max_read_bytes=1_000_000, audit_path=None):
        ...
    def execute(self, action, cancel: threading.Event = None) -> dict:
        # 1) 拒绝 HIGH/CRITICAL（capability_registry.is_implemented / risk_of）
        # 2) 以 ThreadPoolExecutor(timeout=timeout) 包裹 _dispatch，cancel 经 threading.Event 触发
        # 3) 任何路径（成功/失败/拒绝/超时）均记 audit 并返回结构化 result
        # 返回: {ok, data, error, capability, target, duration, cancelled, timed_out}
```

- **结构化 result**：所有分支统一返回 `{ok, data, error, ...}`，上层（Guard/Verification）按 `ok` + `data` 判定。
- **可取消**：`cancel: threading.Event`；`_op_*` 长操作轮询 cancel，收到即抛 `CancelledError` → `cancelled=True`。
- **可超时**：`ThreadPoolExecutor.submit(...).result(timeout=timeout)`；超时 → `timed_out=True`，并 `cancel.set()` 让线程尽快退出。
- **可审计**：`_audit(action, res, duration)` 写入内存 `audit_log`，若传 `audit_path` 追加 JSONL（一行一记录）。

### 2.3 `_dispatch` 路由（仅 LOW + MEDIUM，无 HIGH/CRITICAL）

| capability | 风险 | `_op_*` 实现 | 安全约束 |
|---|---|---|---|
| `read_file` | LOW | `_op_read_file` | 只读 `open(..., 'r')`，返回 `content[:4000]` 预览，不写、不改。 |
| `list_process` | LOW | `_op_list_process` | `tasklist /fo csv`（无 shell），解析进程名。 |
| `capture_screen` | LOW | `_op_capture_screen`/`_capture_memory` | `mss` 或 `PIL.ImageGrab` 截到**内存**（`BytesIO`），**永不落盘**。 |
| `get_window_info` | LOW | `_op_get_window_info`/`_win_enum` | `ctypes.windll.user32` 枚举窗口，只读。 |
| `open_application` | MEDIUM | `_op_open_application` | `os.startfile` / `subprocess.Popen([list])`（**无 shell**）。 |
| `focus_window` | MEDIUM | `_op_focus_window`/`_win_focus` | `SetForegroundWindow`（仅聚焦，不改内容）。 |
| `browser_navigate` | MEDIUM | `_op_browser_navigate` | `webbrowser.open(url)`（仅导航）。 |

> **无任意 Shell**：所有子进程均 `Popen([list])` 形式，绝不使用 `shell=True`；无 `execute_command`/`delete`/`kill_process`/`modify_file`/`network`/`system`（HIGH·CRITICAL 仅声明未实现，在 Guard 与 Executor 双层拒绝）。

---

## 3. Verification 流程

### 3.1 `VerificationLayer`（执行后重新观察）

```python
class VerificationLayer:
    def __init__(self, observer=None):   # observer=None → 仅结构校验，不发 OS 调用
        ...
    def verify(self, action, result) -> (verified: bool, detail: str):
        # 路由到 _verify_<capability>
```

| capability | 验证判定 |
|---|---|
| `read_file` | `result.data.content` 非空 → verified |
| `list_process` | `result.data.processes` 非空 → verified |
| `capture_screen` | `result.data.bytes` 存在 → verified |
| `get_window_info` | `result.data.window` 存在 → verified |
| `open_application` | 经 `observer` 重查进程/应用列表，目标名在列 → verified |
| `focus_window` | `observer` 当前前台窗口 == target → verified |
| `browser_navigate` | 导航为尽力而为，结构成功即 `verified=True`（detail 标注 best-effort） |

- **成功** → `publish_domain("COMPUTER_ACTION_VERIFIED", payload)`；`action.verified=True`
- **失败** → `publish_domain("COMPUTER_ACTION_UNVERIFIED", payload)`；`action.verified=False`，`verificationDetail` 记录原因（如“目标应用未在运行进程列表中出现”）。

### 3.2 `RealObserver`（真实重观察）

```python
class RealObserver:
    def list_processes(self):           # 复用 RealComputerExecutor._op_list_process
        ...
    def foreground_window(self):        # ctypes 取当前前台窗口标题
        ...
```

### 3.3 接线点

- **后端**：`PermissionGuard.run()` 在 `status='done'` 后调用 `self.verifier.verify(action, result)`，并据结果发 VERIFIED/UNVERIFIED。
- **前端**：`permission-guard.js` 的 `run()` 在 DONE 后，若 `ctx.verifier` 存在则调用并 `emit` 对应事件；**未注入 verifier 时跳过**（保证 Order 2 前端测试不受影响）。
- **AppState**：`COMPUTER_ACTION_VERIFIED`/`UNVERIFIED` reducer 写入 `state.computer.actions[id].verified` 与 `verificationDetail`，并据当前 status 同步标记 `verified`/`unverified`。

---

## 4. Event Contract 变化

- **新增 2 个领域事件**（前后端单一来源，逐字对齐）：
  - `COMPUTER_ACTION_VERIFIED`
  - `COMPUTER_ACTION_UNVERIFIED`
- **总数**：`DOMAIN_EVENT_NAMES`（eventbus.py）= `EVENTS`（zz-events.js）= **64**（38 冻结 + Order1 19 + Order2 5 + Order3 2）。
- **`BATCH_7_ACTION`**：5 → **7**（纳入 2 个验证事件）。
- **对称性**：测试 `phase7-order3.{backend,frontend}` 与 `phase6-order1.backend` 均校验前后端 `sorted(DOMAIN_EVENT_NAMES) == sorted(EVENTS)`，**无差集**。
- 命名空间纪律：`publish_domain` 仅发射 `DOMAIN_EVENT_NAMES` 内事件；`COMPUTER_ACTION_*` 系列均为领域事件（进入 AppState 统一状态核心），与系统事件（`publish_system`）互斥。

---

## 5. 测试结果

### 5.1 Order 3 新增测试

| 套件 | 结果 |
|---|---|
| `tests/phase7-order3.backend.test.py` | **17 / 17 PASS** |
| `tests/phase7-order3.frontend.test.js` | **12 / 12 PASS** |

覆盖要求项：**Mock Executor 流程** / **Low Risk 真实安全测试**（tempfile 读、list_process，零污染）/ **Medium Confirm 流程** / **Permission 拒绝**（HIGH、未知 plan、不可绕过）/ **Verification 成功·失败**。

### 5.2 全量回归（Phase 6 Order 1–8 + Phase 7 Order 1/2/3）

| 层 | 文件 | 结果 |
|---|---|---|
| FE | phase6-order1/2/3/4/5/6/7/8 | 全部 0 失败 |
| FE | phase7-order1 | 15/15 |
| FE | phase7-order2 | 20/20 |
| FE | phase7-order3 | 12/12 |
| BE | phase6-order1.backend | 3/3 |
| BE | phase6-order2~7.integration | 9+16+16+17+16+10 = 全部 PASS |
| BE | phase7-order2.backend | 21/21 |
| BE | phase7-order3.backend | 17/17 |

**合计：0 失败。** 所有测试退出码 0，无 `✗`、无 `AssertionError`、无 `Traceback`。

---

## 6. 风险分析

### 6.1 已消除 / 已约束的风险

| 风险点 | 处置 |
|---|---|
| Agent 直连 Executor 绕过 Guard | 调用链强制 `Task → ComputerAction → PermissionGuard → Executor`；Agent 仅产出 Task，不直接调用 Executor。 |
| High·Critical 真实操作 | 能力注册表仅实现 LOW(4)+MEDIUM(3)；HIGH/CRITICAL 在 Guard 与 Executor **双层拒绝**。 |
| 任意 Shell / 命令执行 | 无 `shell=True`；仅 `Popen([list])`、`tasklist /fo csv`、`webbrowser.open`、`os.startfile`。 |
| 用户文件 / 项目源码污染 | `read_file` 只读预览（返回 `content[:4000]`）；测试全部用 `tempfile.mkstemp`（系统 TEMP），验证内容未变后 `os.remove`。 |
| 截图落盘 | `capture_screen` 仅截到内存 `BytesIO`，**永不写磁盘**。 |
| 执行失控（卡死） | `ThreadPoolExecutor(timeout=30s)` + `threading.Event` cancel；超时/取消均结构化返回并记录 audit。 |
| 无审计追溯 | `audit_log`（内存）+ 可选 `audit_path`（JSONL）。 |
| 默认生产误触发真实 OS 调用 | `PermissionGuard()` 默认 = Mock（不触碰真实系统）；生产须显式 `PermissionGuard(RealComputerExecutor(), VerificationLayer(RealObserver()))` 才启用真实路径。 |
| 前端 Verification 影响旧测试 | 前端 `verifier` 为**可选注入**，未注入则跳过；Order 2 前端测试保持绿。 |
| 事件契约漂移 | 单一来源：后端 `DOMAIN_EVENT_NAMES` 与前端 `EVENTS` 逐字对齐，测试强制对称校验。 |

### 6.2 残余风险（已知、可接受、受控）

1. **MEDIUM 操作会真实启动应用/导航**：`open_application`/`browser_navigate`/`focus_window` 属 MEDIUM → Policy Engine 默认 `confirm` 层，**每次需用户批准**；Verification 为尽力而为（窗口焦点判定可能因系统焦点竞争存在毫秒级竞态，detail 已显式标注）。
2. **Verification 为“尽力验证”而非“强一致”**：`browser_navigate` 结构成功即判定 verified（浏览器是否真正渲染目标页不在本层保证范围）。
3. **真实 OS API 依赖 Windows**：`ctypes.windll.user32`、`tasklist`、`mss`/`PIL` 为 Windows 桌面环境实现；跨平台（Mac/Linux/Web）需后续 Order 扩展 Observer/Executor 适配层——本 Order 严格限定 Windows 桌面真实安全执行，不进入 Vision 完整实现。
4. **无 WCAG 影响**：本层为执行/验证内核，无 UI 渲染，不涉及对比度/键盘导航；UI 层（银河/HUD）的 WCAG 由 Phase 6 Hotfix 已修令牌覆盖。

### 6.3 纪律遵守确认

- ✅ 未进入 Order 4（未实现 Vision 完整层）
- ✅ 未实现 High·Critical 操作
- ✅ 未开放任意 Shell
- ✅ 未修改 / 删除无关文件（仅 Order 3 指定代码 + 测试，及回归计数同步）
- ✅ 未绕过 Permission Guard（所有执行经 Guard）
- ✅ 未创建第二执行系统（`tools.execute_tool` 为独立 Agent-tool 通道，非 Computer 执行系统）

---

**结论**：Phase 7 Order 3 已完成真实但安全的 Computer Executor + Verification 基础闭环，Observation → Action → Verification 通跑通过，全量测试 0 失败。**已停止，等待批准进入 Order 4。**
