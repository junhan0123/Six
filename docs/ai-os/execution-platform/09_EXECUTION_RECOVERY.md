# 09 · Execution Recovery（执行恢复）

> 模块：`ai_core/execution/recovery.py`
> Milestone：M9 · 设计纪律：复用 `tasks.recover_tasks()`，不重写恢复机制

---

## 1. 职责

`ExecutionRecovery` 是统一执行恢复器（单例），建立 Checkpoint / Resume / Restart / Recover 收口。

---

## 2. 公开 API

```python
class ExecutionRecovery:
    @classmethod
    def get(cls) -> "ExecutionRecovery": ...
    def recover(self) -> int:
        """启动时恢复被中断任务：委托 tasks.recover_tasks()，返回恢复计数。"""
    def checkpoint(self, session) -> dict:
        """为一次执行建内存检查点（持久化仍由 tasks/goals 表负责）。"""
    def resume(self, execution_id) -> bool:
        """恢复已暂停/取消的登记（仅簿记，真实续跑由调用方负责）。"""
    def restart(self, execution_id) -> bool:
        """重启：登记状态置回 pending（仅簿记，不触发真实执行）。"""
```

---

## 3. 行为纪律（红线）

- `recover()` 直接委托 `tasks.recover_tasks()`——既是现状、也是唯一恢复入口（Move Never Rewrite）。
- `checkpoint` / `resume` / `restart` 为统一登记与簿记，**不替换底层持久层**（tasks 表 / goals 表的恢复语义完全保留）。
- 进程启动时 `recover()` 由 `main` 调用，与现状一致。

---

*版本：2026-08-06。*
