# 11 · Execution API（统一执行入口）

> 模块：`ai_core/execution/api.py`
> Milestone：M1（纯 Router）+ M2–M10（簿记编排）
> 设计纪律：纯 Router + 簿记，**绝不改变 execute_tool 返回值与异常风格**

---

## 1. `Execution.run()` —— 全项目唯一执行入口

```python
def run(name: str, args: Any, *, allowed: Optional[Any] = None,
        context: Optional[ExecutionContext] = None,
        goal_id: Optional[int] = None,
        permission: str = PermissionMode.NONE,
        timeout: Optional[float] = None,
        retry: int = 0,
        cancel_token: Any = None,
        logger: Any = None,
        metadata: Optional[Dict[str, Any]] = None) -> Any:
    """行为等价于直接调用 execute_tool(name, args, allowed)。"""
```

### 执行流程（簿记顺序）

1. **Context**：未传则按入参构造 `ExecutionContext`。
2. **Session / Queue / State 登记**：`enqueue` → `state.set(created)` → `events.execution_started` → `state.set(running)`。
3. **Policy（仅 GOAL）**：`permission==GOAL` 才走 `policy.evaluate` + `policy.request_approval`；block/拒绝返回说明字符串。chat 默认 NONE → 跳过（保持现状绕过）。
4. **执行（纯 Router）**：`result = execute_tool(name, args, allowed)`（lazy import，单实现者）。
5. **成功**：`metrics.record(ok)` → `events.tool_finished(ok=True)` → `session.complete` → `state.set(completed)` → `events.execution_completed` → `reflection.record_success` → `return result`。
6. **异常（透明路由）**：记录失败指标/复盘后 **re-raise**，异常原样上抛给调用方（如 `agent_runtime._execute_task` 重试回路）。`retry>0` 且 `should_retry` 时进入内核重试循环。
7. **权限 block/拒绝**：返回说明字符串（不抛异常），并记失败复盘。

> ⚠️ **异常语义（关键）**：`run()` 是 `execute_tool` 的**透明路由**。生产态下 `execute_tool` 吞异常返字符串、`run()` 返回该字符串，与直接调用逐字等价；仅在工具真抛出时 re-raise（记录后），与直接调用异常传播一致。

---

## 2. `Execution` 门面（静态入口）

```python
from ai_core.execution import Execution

Execution.run("read_file", {"path": "..."})          # 等价 run()
Execution.context_cls                                 # ExecutionContext
Execution.session_cls                                 # ExecutionSession
Execution.queue()                                     # ExecutionQueue.get()
Execution.state()                                     # ExecutionState.get()
Execution.events()                                    # ExecutionEvent.get()
Execution.policy()                                    # ExecutionPolicy.get()
Execution.metrics()                                   # ExecutionMetrics.get()
Execution.recovery()                                  # ExecutionRecovery.get()
Execution.reflection()                                # ExecutionReflection.get()
```

---

## 3. 调用方迁移示例

| 原代码 | 新代码 |
|---|---|
| `tools.run_one`: `return p, str(execute_tool(p["name"], p["args"], allowed))` | `return p, str(_execution_run(p["name"], p["args"], allowed))` |
| `server.py:2008`: `execute_tool(name, args, remote_allowed)` | `_execution_run(name, args, allowed=remote_allowed)` |
| `agent_runtime`: `execute_tool(tool, args)`（前已 `policy.evaluate/request_approval`） | `_execution_run(tool, args)` |
| `reflector`: `execute_tool("add_knowledge", {...})` | `_execution_run("add_knowledge", {...})` |
| `social_inbound`: `execute_tool(n, a)` | `_execution_run(n, a)` |

---

*版本：2026-08-06。*
