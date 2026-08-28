# -*- coding: utf-8 -*-
"""ai_core.execution.policy — ExecutionPolicy 统一门面（R8-P0 恢复）

唯一职责：把 agent_runtime 的 ExecutionPolicy 调用委托给既有 Policy Engine
（policy_engine.evaluate / request_approval），**不新建第二套权限系统**、
**不重新设计 Policy**。与既有 agent_runtime 的用法保持兼容：

    policy = ExecutionPolicy.get()
    dec = policy.evaluate(tool, args, goal_id=..., default_deny=True)
    d   = policy.request_approval(tool, args, summary=..., goal_id=..., default_deny=True)
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class ExecutionPolicy:
    """统一 Policy 门面（单例）。

    所有 evaluate / request_approval 均转发 policy_engine（权限真相单一来源）。
    """

    _instance: Optional["ExecutionPolicy"] = None

    def __init__(self, default_deny: bool = True):
        self.default_deny = default_deny

    @classmethod
    def get(cls) -> "ExecutionPolicy":
        """返回进程级单例（与既有 permission_guard.guard 同风格）。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def evaluate(self, tool: str, args: Optional[dict] = None, *,
                 goal_id: Optional[int] = None, default_deny: bool = True,
                 **kwargs) -> dict:
        """统一裁决：返回 {"decision": auto|confirm|block, "reason", "permission"}。"""
        from policy_engine import evaluate
        return evaluate(tool, args or {}, goal_id=goal_id, default_deny=default_deny)

    def request_approval(self, tool: str, args: Optional[dict] = None, *,
                         summary: str = "", goal_id: Optional[int] = None,
                         default_deny: bool = True, **kwargs) -> str:
        """确认级审批：返回 approve|reject|timeout（委托 policy_engine）。"""
        from policy_engine import request_approval
        return request_approval(
            tool, args or {}, summary=summary, goal_id=goal_id, default_deny=default_deny,
        )

    def pre_approve_tools(self, goal_id: int, tools: list) -> None:
        """Goal 级预批准（委托 policy_engine.pre_approve_tools）。"""
        from policy_engine import pre_approve_tools
        pre_approve_tools(goal_id, tools)
