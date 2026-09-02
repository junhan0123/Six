# 02 · Execution Context（执行上下文）

> 模块：`ai_core/execution/context.py`
> Milestone：M2 · 设计纪律：Move Never Rewrite / Behavior Never Change

---

## 1. 职责

`ExecutionContext` 是单次工具执行统一携带的**数据载体**。它不改变任何执行语义——只把原本散落在各调用方的 `goal_id` / `permission` / `timeout` / `retry` / `cancel_token` 等字段收口为一个对象。

`PermissionMode` 与现有 PolicyEngine 四级语义对齐（**不新增第二套权限**）：
- `NONE`：不经 PolicyEngine 裁决（chat / reflector / social_inbound 现状）。
- `GOAL`：经 `policy_engine.evaluate` + `request_approval`（goal 路径）。
- `COMPUTER`：经 `PermissionGuard`（电脑能力路径，由 agent_runtime 直接走）。

---

## 2. 公开 API

```python
class ExecutionContext:
    __slots__ = ("execution_id", "goal_id", "workflow_id", "permission",
                 "timeout", "retry", "cancel_token", "logger", "metrics", "metadata")
    def __init__(self, execution_id=None, *, goal_id=None, workflow_id=None,
                 permission=PermissionMode.NONE, timeout=None, retry=0,
                 cancel_token=None, logger=None, metadata=None):
        ...
    def derive(self, **overrides) -> "ExecutionContext":
        """返回带覆盖字段的新上下文（避免跨调用共享可变状态）。"""
    def as_dict(self) -> dict:
        """导出为字典。"""

class PermissionMode:
    NONE = "none"
    GOAL = "goal"
    COMPUTER = "computer"
```

- `execution_id`：自动生成（`exec-` + 12 hex），可作为幂等/追踪键。
- `metadata`：调用方附加信息（如 `tool` 名），供 State/Event/Reflection 消费。
- `derive()`：不可变风格派生，避免 `context` 在重试/并发中被意外共享。

---

## 3. 行为纪律

- **纯数据载体**：无任何执行副作用、不调用 `execute_tool`、不裁决权限。
- `permission` 默认 `NONE`，与 chat 路径绕过 PolicyEngine 的现状**逐字等价**。
- 仅依赖标准库（`uuid` / `time`），无新依赖。

---

## 4. 使用位置

- `api.run()`：未传 context 时按入参构造；传了则复用（支持 `derive`）。
- `agent_runtime._execute_task`：显式 `permission=GOAL` 场景由调用方在 `run()` 外完成裁决，传入 NONE（不二次裁决）。
- `ExecutionPolicy.should_retry` / `is_cancelled`：读取 `ctx.retry` / `ctx.cancel_token`。

---

*版本：2026-08-06。*
