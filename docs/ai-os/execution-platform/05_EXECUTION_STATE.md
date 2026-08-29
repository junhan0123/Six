# 05 · Execution State（执行状态）

> 模块：`ai_core/execution/state.py`
> Milestone：M5 · 设计纪律：收口四套状态源，不改底层持久层

---

## 1. 职责

`ExecutionState` 是统一执行状态视图（单例），把审计发现的**四套状态来源**归一为单一 `SessionState` 枚举：

1. `tasks.py` 任务表
2. `goals.py` 目标表
3. `agent_runtime.py` 内存态（`{IDLE,PLANNING,EXECUTING,REFLECTING}`）
4. `scheduler.TaskStatus`（`{scheduled,triggered,completed,...}`）

---

## 2. 状态映射（`_SOURCE_MAP`）

| 来源 | 原子状态 | 归一为 |
|---|---|---|
| tasks | open / running / done / failed / cancelled | PENDING / RUNNING / COMPLETED / FAILED / CANCELLED |
| agent_runtime | IDLE / PLANNING / EXECUTING / REFLECTING | CREATED / PENDING / RUNNING / WAITING |
| scheduler | scheduled / triggered / completed | PENDING / RUNNING / COMPLETED |

`normalize(raw)` 把任意来源原始状态归一为统一枚举；未知值原样返回（不丢信息）。

---

## 3. 公开 API

```python
class ExecutionState:
    @classmethod
    def get(cls) -> "ExecutionState": ...          # 单例
    def set(self, execution_id, status, **extra) -> None: ...
    def get_status(self, execution_id) -> Optional[dict]: ...   # 实例方法（注意命名）
    def normalize(self, raw: str) -> str: ...
    def register_source(self, entity_id, source, raw_status) -> None: ...
    def snapshot(self) -> Dict[str, dict]: ...
```

> ⚠️ 单例访问器为类方法 `ExecutionState.get()`；实例级读取已重命名为 `get_status(execution_id)`（避免与类方法同名遮蔽，见 `13_EXECUTION_REGRESSION.md`）。

---

## 4. 行为纪律

- **不改动底层持久层**（tasks / goals / scheduler）；仅提供统一映射与运行时登记。
- 作为**唯一状态写源**的运行时视图：各调用方经 `Execution.run` 写入统一状态，其余三套底层为投影/只读镜像。
- 线程安全（`threading.Lock`）。

---

*版本：2026-08-06。*
