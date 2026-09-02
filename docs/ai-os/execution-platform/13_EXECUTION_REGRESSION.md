# 13 · Regression（回归）

> Milestone：M12 · 回归结果记录
> 运行环境：Python 3.11.9（系统），`G:/xiao6/xiao6-ui` 工作树

---

## 1. 静态检查

| 检查 | 命令 | 结果 |
|---|---|---|
| py_compile 全改动文件 | `python -m py_compile ai_core/execution/*.py eventbus.py tools.py server.py agent_runtime.py reflector.py social_inbound.py` | ✅ COMPILE_OK |
| Import 冒烟 | `import ai_core.execution` + `eventbus.SYSTEM_EVENT_NAMES` 含 8 执行事件 | ✅ IMPORT_OK / exec_events_registered=True |

---

## 2. 行为回归（自测脚本）

| 场景 | 预期 | 结果 |
|---|---|---|
| `run()` 成功返回 execute_tool 原值 | 返回值逐字一致 | ✅ |
| `run()` 异常透传（re-raise） | 异常原样上抛 | ✅ |
| State/Metrics/Reflection 簿记 | singleton `get()` 可用、计数/复盘写入 | ✅ |
| Queue `get_session` 查找 | 入队后可查回会话 | ✅ |
| Event 发布（SYSTEM 通道） | 不抛异常 | ✅ |

---

## 3. 现有测试套件（Goal Decision Engine）

`tests/test_goal_decision_engine.py` 共 37 个测试函数：

| 结果 | 数量 | 说明 |
|---|---|---|
| PASS | 35 | 含 `test_execute_task_retry`（Phase 3 相关重试用例） |
| FAIL（预存，非本次引入） | 2 | 见 §5 |

**`test_execute_task_retry` 修复说明：** 初版 `Execution.run` 内部 `try/except` 吞掉 `execute_tool` 异常并返字符串，导致 `agent_runtime._execute_task` 的重试回路收不到异常、重试失效（该测试 FAIL）。改为**透明路由 re-raise**（记录后上抛）后恢复 PASS，且生产行为零变化（生产态 `execute_tool` 吞异常返字符串、`run()` 返回该字符串，与直接调用逐字等价）。

---

## 4. 实施中发现并修复的 2 个 Bug

### Bug-1：单例类方法被同名实例方法遮蔽（致命）
- **现象：** `ExecutionQueue.get()` / `ExecutionState.get()` 实际解析到实例方法 `get(self, execution_id)`，调用即 `TypeError: missing 2 required positional arguments`。
- **根因：** `queue.py` / `state.py` 中单例访问器类方法 `get(cls)` 与实例查找方法 `get(self, execution_id)` **同名**，后者在类体中后定义，遮蔽前者。
- **修复：** 实例方法重命名为 `get_session` / `get_status`；单例访问器 `get()` 恢复为类方法。更新 `recovery.py` 内部 `q.get(execution_id)` → `q.get_session(execution_id)`。
- **验证：** 行为回归脚本通过（singleton 可用 + 查找可用）。

### Bug-2：`server.py` fallback 位置传参错误（致命）
- **现象：** `run()` 签名 `allowed` 为 keyword-only（`def run(name, args, *, allowed=None, ...)`），但 `server.py:2008` 写 `_execution_run(name, args, remote_allowed)` 位置传参，运行必 `TypeError`。
- **根因：** 初版集成时未注意 keyword-only 约束。
- **修复：** 改为 `_execution_run(name, args, allowed=remote_allowed)`；顺手移除 `server.py:93` 已无用的 `execute_tool` import。

---

## 5. 2 个预存失败（与 Phase 3 无关，已确认）

| 测试 | 失败原因 | 与 Execution Platform 关系 |
|---|---|---|
| `test_no_direct_tool_execution` | `submit_goal` 现被调用时传入 `intent_id` kwarg，但测试的 mock lambda 仅接受 `(title, description="")` | 无关——Phase 3 未触碰 `submit_goal` / GDE 提交签名（属既有演化债务） |
| `test_notify_goal_done_emits_event` | 期望发出 `goal_completed` 事件，未发出 | 无关——Phase 3 仅新增 `execution_*` SYSTEM 事件，未触碰 `goal_completed` 领域事件逻辑 |

**结论：** 2 个失败为预存债务（早于 Phase 3，源于 GDE/agent_runtime 既有演化），不在本次收口范围内；Phase 3 相关用例 `test_execute_task_retry` 已 PASS。

---

*版本：2026-08-06。*
