# TRAE Runtime 架构审计报告

> 审计日期：2026-08-28 · 性质：独立只读审计 · 对象：G:\xiao6（工作区现状，非历史报告推测）

---

## 一、Agent 执行链完整性

目标链路：

```
Chat/UI → server.py → Agent Runtime → Planner → Execution Core
       → Policy Engine → Permission Guard → Tool → Verification
```

### 实际链路状态：**BROKEN（断裂）**

| 环节 | 状态 | 证据 |
|---|---|---|
| Chat/UI → server.py | ✅ 存在 | `server_handlers_chat.py` 接收聊天请求 |
| server.py → Agent Runtime | ✅ 存在 | `agent_runtime.py` 被 `server_handlers_chat.py:223` 引用 |
| Agent Runtime → Planner | ✅ 存在 | `agent_runtime.py` Goal 四态循环（completed/failed/max_steps_exceeded/blocked_by_policy） |
| Runtime → Execution Core | ❌ **P0 断裂** | 见下文 §二 |
| Policy Engine | ⚠️ 存在但被弱化 | `policy_engine.py` 完整，但统一入口默认 `default_deny=False` |
| Permission Guard | ✅ 存在 | `permission_guard.py` 闭环完整（plan→decide→approve→execute→verify） |
| Tool | ⚠️ 可被绕过 | `tools.execute_tool` 自身无 Policy 校验 |
| Verification | ✅ 存在 | `VerificationLayer.verify`（permission_guard.py 内） |

---

## 二、P0-1：统一执行入口 `ai_core.execution.run()` 参数契约断裂

### 声明的契约

[api.py](file:///G:/xiao6/xiao6-ui/ai_core/execution/api.py) L19-33：

```python
def run(task: str, context: dict = None, **kwargs) -> dict:
    ...
    tool_args = context.get("args", {})   # 要求调用方传 context={"args": {...}}
```

### 全部 5 个实际调用点 —— 无一按契约传参

| 调用点 | 代码 | 后果 |
|---|---|---|
| agent_runtime.py:566 | `_execution_run(tool, args)` | args 被当作 context，`tool_args = args.get("args", {})` = **{}** |
| capability_runtime.py:181 | `_execution_run(name, args or {}, allowed=allowed)` | 同上，**工具参数全丢** |
| reflector.py:89 | `_execution_run("add_knowledge", {...})` | 参数丢失 |
| social_inbound.py:125 | `_execution_run(n, a)` | 参数丢失 |
| tools.py:3319 | `_execution_run(p["name"], p["args"], allowed=allowed)` | 参数丢失 |

**结论：所有经统一入口的工具调用，真实参数全部被丢弃，工具以空参数 `{}` 执行。** 这与"行为等价于 execute_tool"的注释（agent_runtime.py:565、capability_runtime.py:152）直接矛盾。

---

## 三、P0-2：`ai_core/execution/policy.py` 模块不存在

- agent_runtime.py:551：`from ai_core.execution.policy import ExecutionPolicy`
- 实际目录 `ai_core/execution/` 仅含：`__init__.py`、`api.py`、`events.py`
- `__init__.py` 内联的 `ExecutionPolicy` 类（L106-110）**没有 `get()` 类方法**，而 agent_runtime.py:553 调用 `ExecutionPolicy.get()`
- 对比：`release/ai_core/execution/__init__.py` 从 `.context/.session/.queue/.state/.events/.policy/.metrics/.recovery/.reflection` 导入完整模块集 —— 说明顶层 `ai_core/execution` 是**未完成的不兼容精简替换**

**结论：Agent Goal 任务每次执行工具时触发 `ModuleNotFoundError`（或即使被外层捕获，工具也永远无法经此路径执行）。Goal 执行链在当前工作区实际不可用。**

---

## 四、P0-3：server_globals stub 覆盖真实实现（导入顺序缺陷）

[server.py](file:///G:/xiao6/xiao6-ui/server.py) 导入顺序：

```
L120: def _is_local_peer(peer): ...真实实现（判断 127.0.0.1/::1/localhost）
L126: _ACCESS_LOG_REDACT_RE = re.compile(...)   真实脱敏正则
L188: from server_globals import _is_local_peer, ..., _ACCESS_LOG_REDACT_RE, ...
      ↑ Python 顺序执行 → stub 覆盖上面两个真实实现
```

[server_globals.py](file:///G:/xiao6/xiao6-ui/server_globals.py)（标注 "S79.8 minimal compat"）提供的是：

| 符号 | stub 值 | 影响 |
|---|---|---|
| `_is_local_peer` | 恒返回 `True` 的函数 | **远端来源判定永久失效** → 远程访问限制（_REMOTE_FORBIDDEN / allowed 白名单前置）形同虚设 |
| `_ACCESS_LOG_REDACT_RE` | `None` | 访问日志脱敏关闭 → URL 查询串中的 token/apikey 可能明文落盘 |
| `_CORS_ALLOWED_ORIGINS` | `{"*"}` | CORS 全开放 |
| `_REMOTE_FORBIDDEN` | `False` | 远程禁用工具清单为空 |
| `_sse_put` | `None` | 依赖该函数的 SSE 路径若被触发将 TypeError |
| `_sse_use_eventbus` | `False` | 强制回退 SUBSCRIBERS 旧路径（覆盖 config 的 EventBus 门控） |

补充：**HEAD 提交中的 server_globals.py `_is_local_peer = True`（布尔值）**，此时 server.py:223 `_is_local_peer(peer)` 每次调用抛 `TypeError: 'bool' object is not callable`——即**已提交版本服务端每个请求必崩**；工作区未提交的"热修"仅把崩溃降级为安全语义回退。两种状态都不合格。

---

## 五、第二执行入口核查（是否绕过 ai_core.execution.run / Policy）

发现 **3 个绕过 Policy 的 execute_tool 直调点**：

| 位置 | 代码 | 性质 |
|---|---|---|
| agent_runtime.py:729 | `execute_tool(skill_handle, args or {})` | 原生 Skill 句柄直调，**无 Policy 评估** |
| capability_runtime.py:158 | `execute_tool(name, args or {}, allowed=allowed)` | feature flag 关闭时的回退路径，无 Policy |
| capability_os/__init__.py:259 | `execute_tool(tool_name, args or {}, allowed=None)` | 直调路径，无 Policy |

注：[tools.py:3990](file:///G:/xiao6/xiao6-ui/tools.py) `execute_tool` 自身**只做远程会话白名单，不做 Policy 裁决**，因此上述直调 = 完全绕过 Policy Engine。

结构性问题：`release/` 与 `xiao6-ui/xiao6-ui/` 两棵**完整重复代码树**内各有一份 capability_os / computer_action / config.py 等，形成潜在第三、第四执行入口（重复树问题在 Git 报告中单列）。

---

## 六、EventBus 唯一性

- [eventbus.py](file:///G:/xiao6/xiao6-ui/eventbus.py)：单例 `bus = EventBus()`（L156），域事件名注册校验、payload 序列化校验完整
- `ai_core/execution/events.py` 明确"复用唯一 EventBus（bus/publish_system）。禁止第二 EventBus" → Execution 事件经 SYSTEM 通道扇出，✅ 无第二 EventBus
- ⚠️ 但 server 侧 SSE 门控被 server_globals stub 强制为 `_sse_use_eventbus=False`（§四），实际运行走 SUBSCRIBERS 旧路径 —— EventBus 仍是唯一总线，但"EventBus 扇出"特性当前实际未生效

---

## 七、结论

| 检查项 | 结论 |
|---|---|
| 存在第二执行入口 | **是**（3 处 execute_tool 直调绕过 Policy） |
| 绕过 ai_core.execution.run | **是**（且该入口本身契约断裂、不可用） |
| 绕过 Policy | **是**（Skill 路径无 Policy；统一入口 default_deny=False 弱化） |
| EventBus 唯一 | **是**（但扇出特性被 stub 强制关闭） |
| 链路整体可用性 | **不可用（P0×3）** |

**Runtime 评级：❌ 未达稳定基线。** 当前提交（HEAD）状态服务端每请求必崩；工作区状态则参数丢失 + 安全控制被 stub 清空。
