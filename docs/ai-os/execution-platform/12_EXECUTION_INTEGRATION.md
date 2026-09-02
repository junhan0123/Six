# 12 · Integration（集成收口）

> Milestone：M11 · 设计纪律：全部接入 Execution Platform，不得保留第二执行入口

---

## 1. 五处执行入口统一收口（已完成）

| # | 文件 | 原代码 | 新代码 | 行为变化 |
|---|---|---|---|---|
| 1 | `tools.py:3286` (`run_one`) | `execute_tool(p["name"], p["args"], allowed)` | `_execution_run(p["name"], p["args"], allowed)` | 无 |
| 2 | `server.py:2008` (chat 兜底) | `execute_tool(name, args, remote_allowed)` | `_execution_run(name, args, allowed=remote_allowed)` | 无（修正 keyword 传参） |
| 3 | `agent_runtime.py:234` (`_execute_task`) | `execute_tool(tool, args)`（前已 `evaluate`/`request_approval`） | `_execution_run(tool, args)` | 无（权限检查仍由 agent_runtime 显式完成，内核不二次裁决） |
| 4 | `reflector.py:89` (`add_knowledge`) | `execute_tool("add_knowledge", {...})` | `_execution_run("add_knowledge", {...})` | 无 |
| 5 | `social_inbound.py:125` (意图兜底) | `execute_tool(n, a)` | `_execution_run(n, a)` | 无 |

> 同步改动：上述文件顶部 import 由 `from tools import execute_tool` 改为 `from ai_core.execution import run as _execution_run`（`server.py` 顺手移除已无用的 `execute_tool` import）。

---

## 2. 第二入口残留核查（grep 证明）

全仓 `grep execute_tool\(` 结果：

- `tools.py:3957` → `def execute_tool(...)`（**定义**，唯一真正实现者）
- `ai_core/execution/api.py:105` → `result = execute_tool(name, args, allowed)`（**内部 Router 调用**，唯一收口点）
- `docs/...` / `tests/...` → 文档与测试字符串，非代码调用

**结论：无第二执行入口残留。** 所有外部调用统一经 `_execution_run` → `Execution.run`。

---

## 3. agent_runtime 权限路径确认（语义等价）

`agent_runtime._execute_task` 改动前后对比：

| 步骤 | 原 | 新 |
|---|---|---|
| 导入 | `from policy_engine import evaluate, request_approval` + `from tools import execute_tool` | `from ai_core.execution.policy import ExecutionPolicy` + `from ai_core.execution import run as _execution_run` |
| 裁决 | `dec = evaluate(tool, args, goal_id=..., default_deny=True)` | `dec = policy.evaluate(tool, args, goal_id=..., default_deny=True)`（委托同一 PolicyEngine） |
| 审批 | `d = request_approval(tool, args, summary=..., goal_id=..., default_deny=True)` | `d = policy.request_approval(...)`（委托同一 PolicyEngine） |
| 执行 | `result = execute_tool(tool, args)` | `result = _execution_run(tool, args)`（NONE，不二次裁决） |

权限检查**恰好一次**（agent_runtime 显式完成），内核不重复裁决；返回值 `str(result)[:2000]` 不变。

---

## 4. EventBus 集成

- `eventbus.py:272-279` 新增 8 个执行事件到 `SYSTEM_EVENT_NAMES`。
- `ExecutionEvent.publish` 经 `publish_system` 扇出；前端忽略未知 system 事件，零 UI 改动。
- Chat SSE（`tool_start`/`tool_end` via `emit`）保持兼容，未触碰。

---

*版本：2026-08-06。*
