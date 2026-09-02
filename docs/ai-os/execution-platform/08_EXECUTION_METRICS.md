# 08 · Execution Metrics（执行指标）

> 模块：`ai_core/execution/metrics.py`
> Milestone：M8 · 设计纪律：仅聚合计数/耗时，不拦截工具、不改返回值

---

## 1. 职责

`ExecutionMetrics` 是统一执行指标聚合器（单例），统计 Tool Count / Duration / Retry / Success / Failure / Token / CPU / Memory 采样。纯可观测层。

---

## 2. 公开 API

```python
class ExecutionMetrics:
    @classmethod
    def get(cls) -> "ExecutionMetrics": ...
    def record(self, name, duration, ok) -> None: ...
    def record_retry(self) -> None: ...
    def record_token(self, n) -> None: ...
    def record_resource(self, cpu=None, mem=None) -> None: ...
    def snapshot(self) -> dict:
        """tool_count/success/failure/retry/duration_sum/avg/max/per_tool/token_total/..."""
```

- `per_tool`：按工具名聚合 count/success/failure/dur_avg。
- `record_resource`：CPU/Memory 为可选采集，采不到记录为 0/None，**不影响执行**。

---

## 3. 行为纪律

- 仅聚合计数与耗时；不拦截工具实现、不改变返回值。
- 线程安全（`threading.Lock`）。
- 与 `Execution.run` 的 Success/Failure 判定一致（`record(..., ok)` 由 `api.run` 在 execute_tool 返回/异常时调用）。

---

*版本：2026-08-06。*
