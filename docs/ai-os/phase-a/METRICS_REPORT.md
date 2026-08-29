# 小6 AI OS 2.0 — Phase A 任务七：Metrics（METRICS_REPORT）

> Sprint: AI OS Phase A — Core Intelligence Sprint v1.0
> 任务: 任务七（Metrics）→ 输出本报告
> 上游: 任务三（Context Size）/ 任务四（Latency, Tool Count）/ 任务八（Recovery Count）
> 日期: 2026-08-05
> 状态: ✅ 设计完成；本任务 STOP，待逐任务 Review

---

## 1. 目的与范围

**目标**：为 AI Core 建立**轻量、本地优先**的指标埋点，使性能与健壮性可量化、可回归。

**范围**：仅采集与聚合；不诊断、不告警、不外传（Local First 红线）。告警/看板属后续。

**五类指标（来自 Phase A 范围定义）**：
1. **Latency** — LLM 推理延迟、工具执行延迟
2. **Memory Usage** — 进程内存占用
3. **Tool Count** — 已注册工具/能力数 + 调用次数
4. **Context Size** — 单次请求上下文 Token 量
5. **Recovery Count** — 崩溃恢复发生次数

---

## 2. 指标目录（定义）

| 指标 | 名称 | 单位 | 类型 | 采集点 |
|------|------|------|------|--------|
| LLM 推理延迟 | `llm.latency` | ms | histogram(p50/p95) | 任务四 REASONING 相位计时 |
| 工具执行延迟 | `tool.latency` | ms | histogram(p50/p95) | 任务四 TOOL 相位计时 |
| 进程内存 | `proc.memory_rss` | MB | gauge | 定时采样（60s） |
| 注册能力数 | `capability.registered` | count | gauge | 启动时 + 注册变更（任务五 catalog） |
| 工具调用次数 | `tool.invocations` | count | counter | 每次 TOOL 执行 +1 |
| 上下文 Token | `context.tokens` | tokens | histogram | 任务三 `ContextBundle.total_tokens` |
| 恢复次数 | `recovery.count` | count | counter | 任务八 RECOVERING 进入 +1 |

---

## 3. 指标模型与采集器

```python
@dataclass
class MetricSample:
    name: str
    value: float
    unit: str
    tags: dict[str, str] = field(default_factory=dict)   # e.g. {"tool":"read_file"}
    ts: float = field(default_factory=time.time)

class MetricsCollector:     # 进程级单例 ai_core/metrics.py
    def record(self, name, value, unit, tags=None): ...   # 写入环形缓冲
    def histogram(self, name, value, unit, tags=None): ... # 追加到 p50/p95 窗口
    def gauge(self, name, value, unit, tags=None): ...
    def counter_inc(self, name, tags=None, by=1): ...
    def snapshot(self) -> dict: ...                        # 聚合输出
```

- **存储**：进程内环形缓冲（每指标保留最近 N=1000 样本 / 或滑动窗口），**不落盘数据库**（避免与业务状态写路径耦合，红线 #2 后端写入口纪律）；可选定时快照落本地日志（任务九）。
- **Local First**：指标仅在本地聚合与暴露；绝不发往云端 LLM 或外部。

---

## 4. 采集点接线

- **任务四 Execution Pipeline**：在 REASONING/TOOL 相位前后 `time.perf_counter()` 计时 → `histogram("llm.latency"/"tool.latency")`；TOOL 执行成功/失败 `counter_inc("tool.invocations", tags={tool})`。
- **任务三 Context Pipeline**：`ContextBuilder.build()` 返回 `total_tokens` → `histogram("context.tokens")`。
- **任务五 Capability Registry**：catalog 注册/注销 → `gauge("capability.registered")`。
- **任务八 Recovery**：进入 RECOVERING → `counter_inc("recovery.count")`。
- **定时采样**：`MetricsCollector` 启后台线程每 60s 采 `proc.memory_rss`（用 `psutil` 或 `tracemalloc`；缺失则跳过，best-effort）。

---

## 5. 暴露方式（规避 F1）

- **HTTP**：`server.py` 新增 `GET /metrics`，返回 `MetricsCollector.snapshot()` JSON（Prometheus 文本格式可选）。**不新增 SSE 事件名**。
- **可观测广播**：如需前端概览，复用任务二/六既定的 `agent_state` 信封新增 `metrics` 摘要字段（向后兼容），**不扩大 `SYSTEM_EVENT_NAMES`**（F1）。
- 指标采集本身**不发射领域/系统事件**，纯内部计数。

---

## 6. 红线合规

| 红线 | 合规性 | 说明 |
|------|--------|------|
| 单 Runtime | ✅ | 采集器同进程单例 |
| Local First | ✅ | 指标本地聚合，无外传 |
| 单 EventBus | ✅ | 指标不经事件通道（除非复用 agent_state 信封） |
| No God Module | ✅ | `metrics.py` 只采集聚合，不含业务 |
| 增量演进 | ✅ | 采集点以埋点形式接入既有管线，不改其逻辑 |
| 事件契约(F1) | ✅→规避 | 不经新系统事件名 |

---

## 7. 实现清单

1. 新增 `ai_core/metrics.py`：`MetricSample`/`MetricsCollector` + 环形缓冲 + `snapshot()`。
2. 任务四/三/五/八 各采集点加埋点（埋点失败静默，不阻断主流程）。
3. `server.py` 新增 `GET /metrics`。
4. （可选）`agent_state` 信封增 `metrics` 字段。
5. 单测：histogram p50/p95 计算、counter、snapshot、采集点 best-effort 静默。

**本任务为设计交付；代码落地待 Phase A 实现阶段（经 Review 批准）。**

**STOP**：任务七设计完成。待 Review 批准后进入任务八（Recovery）。未经批不得修改代码、不得扩大范围。
