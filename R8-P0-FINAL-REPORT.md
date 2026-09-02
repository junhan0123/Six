# Xiao6 v1.0.0 R8-P0 Runtime Stabilization — FINAL REPORT

> 修复任务（非重构）。目标：恢复唯一执行链
> `Chat → Agent Runtime → ai_core.execution.run() → Policy → PermissionGuard → Tool → Verification`
>
> 状态：**全部完成，验证通过**。未执行：UI 恢复 / 版本修改 / Git 清理（按任务要求暂停，等待下一阶段）。

---

## 一、结论

| 验证项 | 结果 |
|---|---|
| python server.py 启动 | ✅ 正常启动，端口 8000 监听 |
| GET /api/ready | ✅ HTTP 200，ready=true，**无 TypeError** |
| Chat E2E | ✅ HTTP 200，SSE 流式回复正常 |
| 一次真实工具调用 | ✅ calculator 收到真实 args `{"expr": "12*34"}` → `12*34 = 408`；get_time 返回真实时间 |
| 一次 Goal 执行 | ✅ Goal #5 → `completed`，经 Agent Runtime → run() → Policy(auto) → get_time |
| 最小参数契约测试 | ✅ 15/15 PASS（`test_r8_tool_args_contract.py`） |

---

## 二、修改文件

**修改（10 个跟踪文件）：**

| 文件 | 变更 |
|---|---|
| `xiao6-ui/server_globals.py` | 恢复真实安全实现（Task 1） |
| `xiao6-ui/ai_core/execution/api.py` | FAIL-CLOSED 修复 + 失败判定修复 + 参数契约文档（Task 2 核心） |
| `xiao6-ui/agent_runtime.py` | run() 参数契约 + Skill 执行消除 execute_tool 绕过（Task 2/4） |
| `xiao6-ui/capability_runtime.py` | run() 参数契约 + 回退路径消除 execute_tool 绕过（Task 2/4） |
| `xiao6-ui/reflector.py` | run() 参数契约（Task 2） |
| `xiao6-ui/social_inbound.py` | run() 参数契约（Task 2） |
| `xiao6-ui/tools.py` | run() 参数契约（兜底路径）（Task 2） |
| `xiao6-ui/capability_os/__init__.py` | invoke_capability 消除 execute_tool 绕过（Task 4） |
| `xiao6-ui/ai_core/execution/__init__.py` | 重新导出真实 ExecutionPolicy（Task 3） |
| `xiao6-ui/context/budget.py` | 补齐 ContextBudget(max_calls/consume_call)（Goal E2E 阻塞修复） |

**新增（3 个文件）：**

| 文件 | 说明 |
|---|---|
| `xiao6-ui/ai_core/execution/policy.py` | 恢复 ExecutionPolicy 门面（Task 3） |
| `xiao6-ui/test_r8_tool_args_contract.py` | 最小测试：工具收到真实 args（Task 2） |
| `xiao6-ui/r8_goal_e2e.py` | Goal 执行 E2E 验证脚本 |

---

## 三、根因

### Task 1 — server_globals stub 覆盖 server.py 真实安全实现
S79.7 为绕过缺依赖问题把 `server_globals.py` 整体替换为宽松 stub；`server.py` 在 L187-188
`from server_globals import *` + 显式导入，**覆盖**了同一文件 L104-184 的真实实现：
- `_is_local_peer` 恒返回 True（远程访问门控失效）；
- `_ACCESS_LOG_REDACT_RE = None`（访问日志凭证泄露面）；
- `_CORS_ALLOWED_ORIGINS = {"*"}` / `_resolve_cors_origins = lambda: {"*"}`（CORS 全面回显）；
- `_REMOTE_FORBIDDEN = False`（远程高危工具禁用表失效）；
- 同时 `_sse_put=None` / `_sse_use_eventbus=False` / `_proactive_dnd_state={}` / `_hotspot_modal_payload={}` / `BRIEFING_LOCK=None` 被按函数调用 → TypeError。

### Task 2 — Execution Core 参数契约
`ai_core.execution.run(task, context)` 从 `context.get("args", {})` 取工具参数，但 5 处调用方
把原始 args 直接当 `context` 传（`run(tool, args)`）→ `context.get("args")` 恒为空 → **工具参数全部丢失**。
受影响：agent_runtime / capability_runtime / reflector / social_inbound / tools（兜底）。

### Task 3 — policy.py 缺失
`agent_runtime.py` 导入 `from ai_core.execution.policy import ExecutionPolicy`（S79.7 拆分时丢失）；
`ai_core/execution/__init__.py` 中只留了一个无 `get()`/`evaluate()` 的占位类 → 运行时 ImportError。

### Task 4 — execute_tool 绕过
3 处直连 `tools.execute_tool`，绕开 Policy 门：
`agent_runtime._execute_skill_task`、`capability_runtime.execute` 回退分支、`capability_os.invoke_capability`（tool/builtin/computer_action 分支）。

### 附加发现（Goal E2E 阻塞根因，faulthandler 栈定位）
1. **`ai_core.execution.api.run()` 的 `default_deny=(permission_mode == "GOAL")`**：默认 NONE 模式下
   default_deny=False → ① 关闭 LOW_RISK 自动分支，低危工具误入 confirm；② 无 Goal 上下文时
   `request_approval` 不快速拒绝而挂起 300s（`ev.wait`，Reflector 回灌 add_knowledge 被挂死）；
   ③ 有 goal_id 时 confirm 工具反而自动放行（Policy 漏洞）。
2. **`context/budget.py`（S79.7 stub）缺 `max_calls`/`consume_call()`**：`agent_runtime._run_goal`
   `ContextBudget(max_calls=...)` → TypeError，Goal 无法进入执行轮。

---

## 四、修复方式

### Task 1（server_globals.py）
将 stub 整体替换为与 `server.py` 内真实实现逐字一致的安全实现：
- `_is_local_peer(peer)`：仅回环地址集合 `("127.0.0.1", "::1", "localhost", "0:0:0:0:0:0:0:1", "::ffff:127.0.0.1")`；
- `_ACCESS_LOG_REDACT_RE`：真实 `re.compile(...)` token/secret 脱敏正则；
- `_CORS_ALLOWED_ORIGINS = set()` + 真实 `_resolve_cors_origins(bind_host, port)`（回环+显式绑定主机，绝不 `"*"`）；
- `_REMOTE_FORBIDDEN`：真实高危工具禁用集合；
- 同恢复 `_remote_allowed_tools()` / `_hotspot_modal_payload()` / `_sse_put()` / `_sse_use_eventbus()` /
  `_proactive_dnd_state()` / `BRIEFING_LOCK`（`config`/`TOOLS` 函数内延迟导入，避免循环依赖）；
- 显式 `__all__`，防止 `from server_globals import *` 泄漏模块级依赖。
`server.py` 无需改动：其导入行为不变，导入到的实现已恢复为真实代码（与 L104-184 语义一致）。

### Task 2（run(task, context={"args": args})）
核心接口 `run(task, context)` 不动；5 处调用方统一改为：

```python
run(task, context={"args": args})
```

- `agent_runtime.py`：`_execution_run(tool, {"args": args})`
- `capability_runtime.py`：`_execution_run(name, {"args": args or {}}, allowed=allowed)`
- `reflector.py`：`_execution_run("add_knowledge", {"args": {...}})`
- `social_inbound.py`：`_execution_run(n, {"args": a})`
- `tools.py`：`_execution_run(p["name"], {"args": p["args"]}, allowed=allowed)`
- 最小测试 `test_r8_tool_args_contract.py`：以 calculator（READONLY/AUTO，真实走 Policy 门）证明工具收到真实 args。

### Task 3（ai_core/execution/policy.py）
新建 `ExecutionPolicy` 门面（单例 `get()`），`evaluate()` / `request_approval()` / `pre_approve_tools()`
100% 委托既有 `policy_engine`（权限真相单一来源，不重新设计 Policy）；`__init__.py` 重新导出该类并移除占位类。

### Task 4（消除 execute_tool 绕过）
3 处直连 `execute_tool` 全部改为经 `ai_core.execution.run()`（Policy 门先裁决，再委派 execute_tool）：
- `agent_runtime._execute_skill_task`：`_execution_run(skill_handle, {"args": args or {}, "goal_id": goal_id})`，FAIL CLOSED 处理 block/拒绝；
- `capability_runtime.execute` 回退分支（FEATURE_CAPABILITY_RUNTIME=False 仅影响能力选择，不再绕过 Policy）；
- `capability_os.invoke_capability`（tool/builtin/computer_action 分支）。
`ai_core.execution.run` 内部对 `execute_tool` 的调用是唯一合法调用点（单一 policy 门）。

### 附加修复
- `api.py`：Policy 门恒 `default_deny=True`（FAIL CLOSED，关闭上述 3 个漏洞/挂起）；失败判定补齐
  execute_tool 全部失败标记（`未知技能`/`被安全策略阻止`/`在远程会话中不可用`/…），执行异常如实报 `success=False`。
- `context/budget.py`：补齐 `max_calls` + `consume_call()`（耗尽返回 False，FAIL CLOSED），保留既有 API。

---

## 五、测试结果

### 5.1 最小参数契约测试（test_r8_tool_args_contract.py）→ 15/15 PASS

```
[PASS] run() success with real args            -> {"success": true, "result": "21 * 2 = 42", "decision": "auto"}
[PASS] calculator received real args (21*2=42) -> 21 * 2 = 42
[PASS] broken raw-args contract loses tool args -> "错误：表达式为空"（参数确实丢失，契约证明）
[PASS] capability_runtime.execute success      -> 6 * 7 = 42
[PASS] capability_runtime args reached tool
[PASS] ExecutionPolicy.get() singleton
[PASS] ExecutionPolicy.evaluate delegates to policy_engine -> {"decision": "auto", ...}
[PASS] ExecutionPolicy has request_approval
[PASS] _is_local_peer is callable
[PASS] _is_local_peer('127.0.0.1') is local
[PASS] _is_local_peer('192.168.1.5') is NOT local
[PASS] _ACCESS_LOG_REDACT_RE is a compiled regex
[PASS] _CORS_ALLOWED_ORIGINS is a set and not {'*'}
[PASS] _REMOTE_FORBIDDEN is a set containing run_shell
[PASS] _resolve_cors_origins is callable and returns loopback origins
===== R8-P0 参数契约最小测试 汇总 =====
15/15 PASS
```

### 5.2 python server.py 启动
- 启动成功（workbuddy python 3.13.14），监听 `http://127.0.0.1:8000`；
- 62 个工具挂载；Agent Runtime / Capability OS / Computer Action Guard 均按启动流程挂载。

### 5.3 GET /api/ready
```
HTTP 200 {"ok": false, "ready": true, "key_present": true, "degraded": true, "self_check": {...}}
```
**无 TypeError**。`ok=false/degraded` 仅来自环境类自检项（edge_tts 未安装 / Open-Meteo SSL 超时 /
knowledge_runtime.cache DocCache 导入缺失——均为 S79.x 遗留环境问题，与本任务无关、非 TypeError）。

### 5.4 Chat E2E
```
POST /api/chat {"messages":[{"role":"user","content":"你好，请用一句话介绍你自己。"}]}
→ HTTP 200，SSE: {"choices":[{"delta":{"content":"我是 Agnes，由 Sapiens AI 开发的语言模型。"}}]} [DONE]
```

### 5.5 一次真实工具调用（参数不丢失的直接证据）
```
POST /api/chat "帮我算一下 12 乘以 34 等于多少"
data: {"zhuangzhou_event":"tool_start","tool":"calculator","args":{"expr":"12*34"}}
data: {"zhuangzhou_event":"tool_end","tool":"calculator",
       "result":"{'success': True, 'execution_id': '7c740bbd', 'result': '12*34 = 408', 'tool': 'calculator', 'decision': 'auto'}"}
data: {"choices":[{"delta":{"content":"12 乘以 34 等于 **408**。"}}]}
```
LLM 传参 `{"expr":"12*34"}` → run() → Policy(auto) → execute_tool → 工具真实算出 `408`。
（另验证 get_time 工具调用：返回真实本地时间。）

### 5.6 一次 Goal 执行（r8_goal_e2e.py）
```
[runtime] 已启动 Agent Runtime 线程
[goal] 已提交目标 #5
[goal] 已按 GDE 通道预批准低危工具集（per-goal）
[goal] 状态: active (round=1)
[goal] 状态: completed (round=1)
[goal] 终态: completed
[goal] 观察记录: 1 条，成功 1 条
       - tool=get_time ok=True blocked=False result={'success': True, ... 'result': '本地 时间：2026年08月28日 19:29:xx 星期五', ...}
===== R8-P0 Goal 执行 E2E 汇总 =====
目标完成      : PASS (completed)
真实工具调用  : PASS (get_time)
总体: ALL PASS ✅
```
链路：submit_goal → plan_goal（LLM 拆解）→ Plan Gate（policy_engine）→ _execute_task →
ExecutionPolicy.get().evaluate → ai_core.execution.run → Policy → execute_tool → get_time →
Reflector 回灌 add_knowledge（LOW_RISK 自动放行，不再挂起）。
（无头验证环境使用设计内 GDE 预批准通道 `policy_engine.pre_approve_tools`（per-goal），非绕过 Policy。）

---

## 六、Git diff

```
$ git diff --stat -- xiao6-ui
 xiao6-ui/agent_runtime.py              |  15 ++-
 xiao6-ui/ai_core/execution/__init__.py |   8 +-
 xiao6-ui/ai_core/execution/api.py      |  22 +++-
 xiao6-ui/capability_os/__init__.py     |   9 +-
 xiao6-ui/capability_runtime.py         |   9 +-
 xiao6-ui/context/budget.py             |  38 ++++++--
 xiao6-ui/reflector.py                  |   5 +-
 xiao6-ui/server_globals.py             | 166 ++++++++++++++++++++++++++++-----
 xiao6-ui/social_inbound.py             |   3 +-
 xiao6-ui/tools.py                      |   3 +-
 10 files changed, 226 insertions(+), 52 deletions(-)
（另新增：ai_core/execution/policy.py、test_r8_tool_args_contract.py、r8_goal_e2e.py）
```

关键 diff 摘录：

```diff
--- a/xiao6-ui/ai_core/execution/api.py
+++ b/xiao6-ui/ai_core/execution/api.py
         policy_result = evaluate(
             tool_name,
             tool_args,
             goal_id=goal_id,
-            default_deny=(permission_mode == "GOAL")
+            default_deny=True      # R8-P0：统一执行入口 FAIL CLOSED
         )
         ...
         if decision == "confirm":
             approval_result = request_approval(
                 tool_name,
                 tool_args,
                 goal_id=goal_id,
-                default_deny=(permission_mode == "GOAL")
+                default_deny=True
             )
-        ok = not result_str.startswith("工具执行失败") and not result_str.startswith("未知工具")
+        ok = not exec_error and not any(m in result_str for m in (
+            "工具执行失败", "未知工具", "未知技能", "外部 MCP 能力执行失败",
+            "无执行体映射", "在远程会话中不可用", "被权限策略阻止",
+            "被安全策略阻止", "用户拒绝执行", "为永久拒绝占位",
+        ))
```

```diff
--- a/xiao6-ui/agent_runtime.py
+++ b/xiao6-ui/agent_runtime.py
-                result = _execution_run(tool, args)
+                result = _execution_run(tool, {"args": args})
...
-        from tools import execute_tool
-        result = execute_tool(skill_handle, args or {})
+        from ai_core.execution import run as _execution_run
+        res = _execution_run(skill_handle, {"args": args or {}, "goal_id": goal_id})
+        if not isinstance(res, dict) or not res.get("success"):
+            return {"task_id": task_id, "ok": False, "blocked": True, ...}
+        result = res.get("result") or ""
```

```diff
--- a/xiao6-ui/server_globals.py
+++ b/xiao6-ui/server_globals.py
-# Local peer flag
-_is_local_peer = True
+def _is_local_peer(peer):
+    """本机判定：仅回环地址视为本地，其余一律按远程处理。"""
+    return peer in ("127.0.0.1", "::1", "localhost", "0:0:0:0:0:0:0:1", "::ffff:127.0.0.1")
+
+_ACCESS_LOG_REDACT_RE = re.compile(
+    r"([?&](?:token|access[_-]?token|auth[_-]?token|secret|password|passwd|api[_-]?key|apikey)=)[^&\s\"']+",
+    re.IGNORECASE,
+)
...
+_REMOTE_FORBIDDEN = {
+    "run_shell", "session_state", "reset_session",
+    "file_write", "file_make_dir", "file_delete", "file_rename",
+    "install_software", "delegate_agent",
+    "create_custom_tool", "delete_custom_tool",
+}
...
+_CORS_ALLOWED_ORIGINS = set()
+def _resolve_cors_origins(bind_host, port): ...   # 回环 + 显式绑定主机，绝不 "*"
```

完整 diff：`git -C G:\xiao6 diff -- xiao6-ui`。

---

## 七、按任务要求未执行（等待下一阶段）

- ❌ UI 恢复
- ❌ 版本修改
- ❌ Git 清理

## 八、遗留提示（非本任务范围）

- `/api/ready` self_check 的环境类降级项：`edge_tts` 未安装、Open-Meteo SSL 超时、
  `knowledge_runtime.cache` 缺 `DocCache` 导入、wakeword 线程缺 numpy —— 均为 S79.x 遗留，未在本任务处理。
- `POST /api/agent/goal|intent|approval` 处理器在拆分后为悬空引用（`server_handlers_*.py` 未实现），
  与本任务 4 项无关，Goal E2E 已验证运行时直驱链路。
