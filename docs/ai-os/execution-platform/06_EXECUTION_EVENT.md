# 06 · Execution Event（执行事件）

> 模块：`ai_core/execution/events.py`
> Milestone：M6 · 设计纪律：复用单 EventBus（SYSTEM 通道），禁第二 EventBus

---

## 1. 职责

`ExecutionEvent` 发布 8 个执行事件，**复用唯一 EventBus**（`eventbus.publish_system`）。不新建第二 EventBus、不扩张 DOMAIN 契约。

---

## 2. 8 个执行事件（已登记于 `eventbus.py:272-279`）

| 常量 | 事件名 | spec PascalCase |
|---|---|---|
| `EVENT_EXECUTION_STARTED` | `execution_started` | ExecutionStarted |
| `EVENT_EXECUTION_UPDATED` | `execution_updated` | ExecutionUpdated |
| `EVENT_EXECUTION_COMPLETED` | `execution_completed` | ExecutionCompleted |
| `EVENT_EXECUTION_CANCELLED` | `execution_cancelled` | ExecutionCancelled |
| `EVENT_TOOL_STARTED` | `tool_started` | ToolStarted |
| `EVENT_TOOL_FINISHED` | `tool_finished` | ToolFinished |
| `EVENT_RETRY_STARTED` | `retry_started` | RetryStarted |
| `EVENT_RETRY_FINISHED` | `retry_finished` | RetryFinished |

`ALL_EXECUTION_EVENTS`：上述元组（发布前白名单校验）。
`SPEC_TO_IMPL`：PascalCase → snake_case 映射表（文档/调试追溯）。

---

## 3. 公开 API

```python
class ExecutionEvent:
    @classmethod
    def get(cls) -> "ExecutionEvent": ...
    def publish(self, name, fields) -> None: ...   # 非执行事件名直接忽略；异常绝不冒泡
    def execution_started(self, session) -> None
    def execution_updated(self, session, **extra) -> None
    def execution_completed(self, session) -> None
    def execution_cancelled(self, session) -> None
    def tool_started(self, session) -> None
    def tool_finished(self, session, ok=True) -> None
    def retry_started(self, session) -> None
    def retry_finished(self, session, ok=True) -> None
```

---

## 4. 关键决策（为何走 SYSTEM 而非 DOMAIN）

- `eventbus.publish_domain` 拒绝未知事件名（`:234-235`）；`DOMAIN_EVENT_NAMES` 须与前端 `zz-events.js` 逐字一致，且「禁止新增同义事件名」。新增 DOMAIN 名 = 改前端 = 违反「禁新增 UI」红线。
- SYSTEM 通道本就承载 telemetry / 工具进度，前端对未知 system 事件**忽略**。故经 SYSTEM 通道扇出，复用单 EventBus、零 UI 改动、零 DOMAIN 契约变更。
- Chat SSE 保持兼容：`tool_start`/`tool_end` 仍经 `server.py` 的 `emit` 闭包直推（前端已用协议），Execution 事件走 EventBus SYSTEM，两者互不干扰。

---

## 5. 健壮性

- `publish()` 对非执行事件名直接 `return`（不发布）。
- 发布异常被 `try/except` 吞掉，**绝不冒泡**到执行主链路（Behavior Never Change）。

---

*版本：2026-08-06。*
