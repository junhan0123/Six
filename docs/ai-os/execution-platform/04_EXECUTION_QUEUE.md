# 04 · Execution Queue（执行队列）

> 模块：`ai_core/execution/queue.py`
> Milestone：M4 · 设计纪律：默认同步执行，不替换任务持久层

---

## 1. 职责

`ExecutionQueue` 是进程内**统一执行队列**（单例），支持 FIFO / Priority / Retry / Resume / Delay / Cancel。Goal / Workflow 统一经此登记，不再各自维护队列。

---

## 2. 公开 API

```python
class ExecutionQueue:
    @classmethod
    def get(cls) -> "ExecutionQueue": ...        # 单例
    def enqueue(self, session, priority=0, delay=0.0) -> None: ...
    def dequeue(self) -> Optional[ExecutionSession]: ...   # FIFO/Priority，Delay 未到点重入队
    def cancel(self, execution_id) -> bool: ...
    def pause(self, execution_id) -> bool: ...
    def resume(self, execution_id) -> bool: ...
    def mark_retry(self, session) -> None: ...
    def get_session(self, execution_id) -> Optional[ExecutionSession]: ...  # 注意：实例方法
    def snapshot(self) -> List[dict]: ...
```

> ⚠️ **命名注意（实施中发现并修复）：** 单例访问器为类方法 `ExecutionQueue.get()`；实例级查找方法已重命名为 `get_session(execution_id)`，避免与类方法 `get` 同名遮蔽（详见 `13_EXECUTION_REGRESSION.md`）。

---

## 3. 行为纪律

- **默认同步执行**（与现状一致）。Queue 是「统一登记与调度抽象」，不替换任务持久层（tasks 表 / scheduler）。
- **线程安全**：所有方法持 `threading.Lock`，符合单 Runtime / 单 EventBus 纪律下的共享登记器语义。
- `dequeue()` 支持 `Delay`：未到 `ready_at` 的条目重新入堆并短暂让出，不阻塞。
- `cancel/pause/resume` 仅变更会话状态，真正中断执行仍由调用方（如 `cancel_token`）负责。

---

## 4. 与审计基线的关系

审计 §13 指出「tasks 表 vs scheduler.TaskStatus 两套任务生命周期」。`ExecutionQueue` 不消除这两套持久层，而是提供**运行时单一视图**与统一登记入口，使未来调度可经此收口而不新建第二队列。

---

*版本：2026-08-06。*
