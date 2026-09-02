# 小6 AI OS 2.0 — Phase A 任务六：Health Check（HEALTH_SYSTEM_REPORT）

> Sprint: AI OS Phase A — Core Intelligence Sprint v1.0
> 任务: 任务六（Health Check）→ 输出本报告
> 上游: 任务二（Lifecycle 就绪门控）、`CORE_AUDIT.md`（F1 事件契约）
> 日期: 2026-08-05
> 状态: ✅ 设计完成；本任务 STOP，待逐任务 Review

---

## 1. 目的与范围

**目标**：建立 AI Core **七子系统健康探针 + 就绪门控**，让内核"是否健康/能否接活"可观测、可诊断。

**范围**：仅观测，不修复、不改业务。探针失败只报告状态，不自动重启（重启属任务八 Recovery）。

**七个被测子系统**（对应 L0 主干 + L5 内核）：
1. **EventBus** — 通信主干（红线 #3）
2. **Permission** — 权限引擎（红线 #4）
3. **Memory** — 记忆单源（红线，L7 接口）
4. **Context** — 上下文管线（任务三）
5. **LLM** — 推理计算（云端调用，Local First 仅计算）
6. **Executor** — 执行通道（P11 单一执行通道）
7. **Boot** — 启动就绪信号（`_boot_ready_event`，server.py:2596）

---

## 2. 健康模型

```python
@unique
class HealthStatus(Enum):
    HEALTHY = "healthy"     # 正常
    DEGRADED = "degraded"   # 可用但异常（如 LLM 延迟高/重试中）
    DOWN = "down"           # 不可用（探针失败）

@dataclass
class SubsystemHealth:
    name: str
    status: HealthStatus
    detail: str = ""
    ts: float = field(default_factory=time.time)

@dataclass
class HealthReport:
    overall: HealthStatus           # = worst(subsystems)
    subsystems: dict[str, SubsystemHealth]
    ts: float
```

- `overall` = 所有子系统中最差一档（DOWN 优先于 DEGRADED 优先于 HEALTHY）。
- **关键子系统**（EventBus/Permission/Boot）DOWN → `overall=DOWN` 且**阻塞** lifecycle BOOT→READY。
- **非关键**（LLM DEGRADED）允许 READY 但标记 degraded（LLM 偶发超时不应阻断内核就绪）。

---

## 3. 探针接口与实现

```python
class HealthProbe(Protocol):
    name: str
    critical: bool
    def check(self) -> SubsystemHealth: ...

# 实现（均为只读探测，best-effort，异常即 DOWN）
class EventBusProbe:     # bus 单例存在 + 可 publish/subscribe 一轮
class PermissionProbe:   # policy_engine 可 import + evaluate 一次 sanity
class MemoryProbe:       # db.db_conn() 可连 + memory 模块可 import
class ContextProbe:      # ContextBuilder() 可构造 + ≥1 Source 注册
class LLMProbe:          # agnes_completion 轻量 ping（不耗大量 token）
class ExecutorProbe:     # tools.execute_tool / guard 可 import（noop 工具探测）
class BootProbe:         # _boot_ready_event.is_set() == True
```

- 所有探针 **try/except 包裹**：异常 → `DOWN`，detail=异常摘要；绝不因探针自身崩溃影响内核。
- LLM 探针为**非关键**：超时/限流记 DEGRADED，不阻断就绪（Local First 下 LLM 是外部依赖，不应让内核"死"在启动）。

---

## 4. 聚合与就绪门控（对接任务二 Lifecycle）

- `HealthCheck.run() -> HealthReport`：并行跑七探针（线程池，超时 2s/探针），汇总。
- **Lifecycle 集成**：`AICoreLifecycle.boot()`（任务二 §4）在置 READY 前调用 `HealthCheck.run()`；任一 **critical=DOWN** 则停留 BOOT 并广播错误，不进 READY。
- 与既有 `_boot_ready_event`（`server.py:2596`）对齐：BootProbe 即读该 Event；自检线程置位后，Lifecycle 才允许 READY。

---

## 5. 暴露方式（规避 F1 事件漂移）

- **内部 API**：`HealthCheck.run()` 供 Lifecycle / 调试调用。
- **HTTP 就绪端点**：`server.py` 新增 `GET /healthz`（liveness）与 `GET /readyz`（readiness，基于 overall + critical 门控）；返回 JSON `HealthReport`——**不新增 SSE 事件名**。
- **可观测广播**：如需前端感知，复用任务二既定的 `agent_state` 信封新增 `health` 字段（向后兼容，旧消费者忽略），**不新增 `SYSTEM_EVENT_NAMES` 条目**，从而不扩大 F1 漂移。若未来确需专属事件，先按 F1 补 Migration 文档。

---

## 6. 红线合规

| 红线 | 合规性 | 说明 |
|------|--------|------|
| 单 Runtime | ✅ | 探针同进程，无新进程 |
| 单 EventBus | ✅ | 仅读 bus 状态，不新发事件（除非复用 agent_state） |
| 单 Permission | ✅ | PermissionProbe 只 sanity 调用，不新建权限 |
| Local First | ✅ | LLM 探针为外部能力探测，不持有状态 |
| 事件契约(F1) | ✅→规避 | 健康检查不经新系统事件名；复用 agent_state 信封 |
| No God Module | ✅ | `health.py` 只探测聚合，不含执行/路由 |

---

## 7. 实现清单

1. 新增 `ai_core/health.py`：`HealthStatus`/`SubsystemHealth`/`HealthReport` + `HealthProbe` 协议 + 七实现 + `HealthCheck.run()`。
2. `AICoreLifecycle.boot()` 接入 `HealthCheck.run()` 作就绪门控（任务二 §4）。
3. `server.py` 新增 `/healthz` + `/readyz`。
4. （可选）`agent_state` 信封增 `health` 字段。
5. 单测：各探针 mock 正常/异常、overall 取最差、critical 门控、超时。

**本任务为设计交付；代码落地待 Phase A 实现阶段（经 Review 批准）。**

**STOP**：任务六设计完成。待 Review 批准后进入任务七（Metrics）。未经批不得修改代码、不得扩大范围。
