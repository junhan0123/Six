# 10 · Execution Reflection（执行复盘）

> 模块：`ai_core/execution/reflection.py`
> Milestone：M10 · 设计纪律：本地 JSONL，非 Memory/Knowledge/DB/云

---

## 1. 职责

`ExecutionReflection` 是统一执行复盘记录器（单例），记录 Success / Failure / Lessons / Suggestion。**不是 Memory、不是 Knowledge**——只是一次执行的本地总结。

---

## 2. 公开 API

```python
class ExecutionReflection:
    @classmethod
    def get(cls) -> "ExecutionReflection": ...
    def record_success(self, ctx, result, lessons=None, suggestion=None) -> None: ...
    def record_failure(self, ctx, error, lessons=None, suggestion=None) -> None: ...
    def recent(self, n=20) -> List[dict]: ...
```

- 落盘：`data/execution_reflections.jsonl`（追加写，每行一条 JSON）。
- 内存环形缓冲：最近 200 条（`_MAX_MEMORY`），防无限增长。

---

## 3. 行为纪律（红线）

- 仅追加写本地日志，**不影响执行结果或返回值**。
- 不进 `memory.py`（非 Memory）、不进 `knowledge/`（非 Knowledge）。
- 本地 JSONL，非 Database、非云、非网络。
- 落盘异常被 `try/except` 吞掉（磁盘满等不影响主链路）。

---

*版本：2026-08-06。*
