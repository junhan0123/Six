# 03 · Execution Session（执行会话）

> 模块：`ai_core/execution/session.py`
> Milestone：M3 · 设计纪律：Session 仅记录生命周期，不参与执行决策

---

## 1. 职责

`ExecutionSession` 是单次 Tool 执行的统一会话对象，记录**生命周期与结果**。它**不参与任何执行决策**（Behavior Never Change）——所有状态变更经 `transition()` 留痕，供 Reflection / State / Event 消费。

---

## 2. 生命周期（9 态）

```
Created → Pending → Running → Waiting → Paused
        → Retrying → Completed → Cancelled → Failed
```

`SessionState` 常量：
`CREATED / PENDING / RUNNING / WAITING / PAUSED / RETRYING / COMPLETED / CANCELLED / FAILED`
`SessionState.ALL`：上述元组（用于 `transition` 校验）。

---

## 3. 公开 API

```python
class ExecutionSession:
    def __init__(self, context: ExecutionContext): ...
    def transition(self, state: str) -> None:
        """状态变更留痕（history）；非法状态 raise ValueError。"""
    def begin(self) -> None:
        """标记一次执行尝试开始：首次=Running，重试=Retrying。"""
    def complete(self, result) -> None:
        """记录结果并置 COMPLETED。"""
    def fail(self, error) -> None:
        """记录错误并置 FAILED。"""
    def cancel(self) -> None:
        """置 CANCELLED。"""
    def as_dict(self) -> dict:
        """导出 execution_id/goal_id/tool/state/attempts/时间戳/error。"""
```

---

## 4. 关键语义

- `begin()`：首次调用置 `RUNNING`；重试调用（attempts>1）置 `RETRYING`。仅记录，不介入决策。
- `transition()` 写入 `history`（含状态 + 时间戳），便于事后复盘追踪。
- `as_dict()` 供 `ExecutionState.set` / `ExecutionEvent.publish` / `ExecutionReflection.record_*` 复用，保证三套可观测层看到一致快照。

---

## 5. 红线合规

- 不引入第二状态机（tasks 表 / goals 表 / scheduler 的状态机保持不变）。
- `ExecutionState` 把四套原子状态**归一**为本会话模型的枚举（见 `05_EXECUTION_STATE.md`）。

---

*版本：2026-08-06。*
