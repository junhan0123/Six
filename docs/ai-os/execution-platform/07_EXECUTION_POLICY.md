# 07 · Execution Policy（执行策略）

> 模块：`ai_core/execution/policy.py`
> Milestone：M7 · 设计纪律：100% 委托既有 PolicyEngine/PermissionGuard，无第二套权限

---

## 1. 职责

`ExecutionPolicy` 是统一执行策略**门面**（单例），收口 Permission / Retry / Timeout / Interrupt / Cancel / Max Runtime。全部委托既有 `policy_engine` / `permission_guard`，**不新增任何裁决逻辑**。

---

## 2. 公开 API

```python
class ExecutionPolicy:
    @classmethod
    def get(cls) -> "ExecutionPolicy": ...

    # —— Permission（委托 PolicyEngine）——
    def evaluate(self, tool, args=None, *, goal_id=None, default_deny=True) -> dict:
        """委托 policy_engine.evaluate（参数/返回值逐字透传）。"""
    def request_approval(self, tool, args, summary="", *, goal_id=None,
                         default_deny=True, timeout=300.0) -> str:
        """委托 policy_engine.request_approval（逐字透传）。"""

    # —— Computer Capability（委托 PermissionGuard，单一执行闭环）——
    def plan_computer_action(self, capability, *, target=None, parameters=None, goal_id=None):
        """委托 permission_guard.guard.plan。"""
    def run_computer_action(self, action, *, goal_id=None, default_deny=True):
        """委托 permission_guard.guard.run。"""

    # —— Retry / Cancel 判定（读取 ExecutionContext）——
    def should_retry(self, ctx, attempt, error) -> bool:
        """仅当 ctx.retry>0 且 attempt<ctx.retry 时允许重试。"""
    def is_cancelled(self, ctx) -> bool:
        """ctx.cancel_token 为 threading.Event 时读其状态。"""
```

---

## 3. 权限路径语义（收口而非新建）

| 调用方 | 行为 |
|---|---|
| chat / reflector / social_inbound | `_execution_run` 默认 `permission=NONE` → 内核**不裁决**，与现状绕过 PolicyEngine **逐字等价**（不改变哪些工具被允许/拦截）。 |
| goal | `agent_runtime._execute_task` 显式 `policy.evaluate` + `policy.request_approval`（同一 PolicyEngine），随后 `_execution_run(tool, args)`（NONE，不二次裁决）。权限检查**恰好一次**。 |

---

## 4. 行为纪律（红线）

- `evaluate` / `request_approval` 调用参数与返回值**逐字透传**，不改变任何裁决语义。
- 电脑能力仍由 `agent_runtime` 经 `PermissionGuard` 闭环（单一执行权限系统）。
- `should_retry`：默认 `ctx.retry=0` → 返回 False → 不重试（与现状 chat 路径一致；goal 路径重试由 `agent_runtime` 自身回路驱动）。
- 无第二权限系统、无第二 PolicyEngine。

---

*版本：2026-08-06。*
