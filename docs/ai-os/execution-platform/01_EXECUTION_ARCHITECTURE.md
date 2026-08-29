# 01 · Execution Platform 架构（Execution Architecture）

> 配套：`CURRENT_EXECUTION_ARCHITECTURE.md`（审计基线）、`EXECUTION_DECISIONS.md`（决策）
> 本文为 **实施后** 架构定稿。`ai_core/execution/` 已落地，5 处执行入口已统一收口。

---

## 1. 设计目标

把审计发现的「两条并行链路 + 一个无闸门工具函数 + 三套事件通道 + 四套状态源」收口为**单一 Execution Platform**：

- **Single Execution Entry**：`Execution.run()` 是全项目唯一执行入口。
- **Single Executor**：`execute_tool` 仍是真正实现者（Router 不重写）。
- **Single EventBus / Permission / State / Queue / Context / Metrics / Recovery / Reflection**：全部单例或单一门面，无第二套。

---

## 2. 分层结构

```
调用方（Chat / Goal / Workflow / Reflection / Social）
        │  （唯一入口）
        ▼
┌─────────────────────────────────────────────┐
│  ai_core.execution.api.run()  ← 统一收口 Router │
│  包裹：Context / Session / Queue / State /     │
│        Event / Policy / Metrics / Recovery /   │
│        Reflection（全部为簿记/可观测，不改返回值）│
└─────────────────────────────────────────────┘
        │  （仅调，不重写）
        ▼
┌─────────────────────────────────────────────┐
│  tools.execute_tool(name, args, allowed)       │
│  — 真正实现者（查表→调用→吞异常返字符串）       │
└─────────────────────────────────────────────┘
        │
        ▼
   TOOL_FUNCS[name](args)  /  tool_factory 自定义工具
```

### 组件清单（11 文件）

| 文件 | 类/函数 | 职责 | 单一性 |
|---|---|---|---|
| `api.py` | `run` / `Execution` | 唯一执行入口 + 统一门面 | 单入口 |
| `context.py` | `ExecutionContext` / `PermissionMode` | 统一执行上下文 | 单上下文 |
| `session.py` | `ExecutionSession` / `SessionState` | 生命周期（9 态） | 单会话模型 |
| `queue.py` | `ExecutionQueue` | FIFO/Priority/Retry/Resume/Delay/Cancel 登记 | 单队列 |
| `state.py` | `ExecutionState` | 四套状态源归一 | 单状态视图 |
| `events.py` | `ExecutionEvent` | 8 执行事件经 EventBus SYSTEM 通道 | 单事件出口 |
| `policy.py` | `ExecutionPolicy` | 委托 PolicyEngine + PermissionGuard | 单权限门面 |
| `metrics.py` | `ExecutionMetrics` | 计数/耗时/重试/Token 聚合 | 单指标 |
| `recovery.py` | `ExecutionRecovery` | 委托 `tasks.recover_tasks()` | 单恢复 |
| `reflection.py` | `ExecutionReflection` | 本地 JSONL 复盘（非 Memory/Knowledge） | 单复盘 |
| `__init__.py` | 导出 | 统一公开 API | — |

---

## 3. 调用链（实施后）

### 3.1 Chat → Tool（经统一入口，权限默认 NONE）
```
_handle_chat → run_fc_loop → run_one(tools.py:3286)
            → _execution_run(name, args, allowed)
            → Execution.run → execute_tool（NONE：不裁决，与现状等价）
（兜底）server.py:2008 → _execution_run(name, args, allowed=remote_allowed)
```

### 3.2 Goal → Tool（经统一入口，agent_runtime 显式裁决）
```
submit_goal → agent_runtime._execute_task(agent_runtime.py:234)
   ├─ policy.evaluate / policy.request_approval（同一 PolicyEngine，语义不变）
   └─ _execution_run(tool, args)  → Execution.run（NONE：不二次裁决）→ execute_tool
```

### 3.3 Reflection / Social（经统一入口，NONE）
```
reflector.py:89  → _execution_run("add_knowledge", {...})
social_inbound.py:125 → _execution_run(n, a)
```

---

## 4. 红线合规（实施后复核）

| 冻结红线 | 状态 |
|---|---|
| 单 Runtime | ✅ agent_runtime 单例未动 |
| 单 EventBus | ✅ 8 执行事件复用 `SYSTEM_EVENT_NAMES`，无第二 EventBus |
| 单 Permission | ✅ `ExecutionPolicy` 100% 委托 PolicyEngine/PermissionGuard |
| 事件契约不扩张（DOMAIN/zz-events.js） | ✅ 仅扩 SYSTEM 通道，前端忽略未知 system 事件 |
| 禁改 Planner/Workflow/Goal/Agent/Tool 行为 | ✅ 仅路由收口，`execute_tool` 未改 |
| 禁云/联网/新 AI 功能 | ✅ 纯本地薄收口层 |

---

## 5. 与审计基线的偏差说明（已决策）

- **偏差 1（事件命名）：** spec 8 事件原拟走 DOMAIN，因 `zz-events.js` 红线改为 SYSTEM 通道（见 `EXECUTION_DECISIONS.md` D2）。
- **偏差 2（异常语义）：** 内核初版吞异常返字符串，回归测试 `test_execute_task_retry` 失败；改为 re-raise 透明路由后恢复（见 D4）。
- **偏差 3（单例遮蔽 Bug）：** `ExecutionQueue.get`/`ExecutionState.get` 类方法被同名实例方法遮蔽，已重命名实例方法为 `get_session`/`get_status`（见 `13_EXECUTION_REGRESSION.md`）。

---

*架构定稿版本：2026-08-06。*
