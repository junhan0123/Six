"""ai_core.execution.api — Unified Execution Entry Point

Single policy gate for all capability execution.
All execution flows through this function:
  1. Policy evaluation (policy_engine.evaluate)
  2. Approval check (policy_engine.request_approval for confirm-level)
  3. Tool execution (tools.execute_tool)
  4. Event publication (ExecutionEvent)
"""

from __future__ import annotations
import uuid
import time
from typing import Any, Dict, Optional

from ai_core.execution.events import ExecutionEvent, ExecutionSession


def run(task: str, context: dict = None, **kwargs) -> dict:
    """Unified execution entry point with policy gate.
    
    Args:
        task: Capability/tool name (e.g., "get_time", "file_list")
        context: Execution context with session_id, goal_id, etc.
        **kwargs: Additional params (allowed, retry, permission)
    
    Returns:
        dict with success, result, execution_id
    """
    context = context or {}
    execution_id = kwargs.get("execution_id") or uuid.uuid4().hex[:8]
    tool_name = task
    tool_args = context.get("args", {})
    session_id = context.get("session_id", "default")
    goal_id = context.get("goal_id")
    allowed = kwargs.get("allowed")
    permission_mode = kwargs.get("permission", "NONE")  # NONE or GOAL
    
    # Initialize execution session
    from context.models import BuildContext
    build_ctx = BuildContext(
        session_id=session_id,
        goals=[f"goal-{goal_id}"] if goal_id else [],
    )
    # Create execution session with proper context
    exec_session = ExecutionSession(
        execution_id=execution_id,
        task=tool_name,
        context=build_ctx
    )
    # Set goal_id on session directly
    exec_session.goal_id = goal_id
    
    # Publish started event
    ExecutionEvent.get().execution_started(exec_session)
    
    try:
        # Step 1: Policy evaluation
        from policy_engine import evaluate, request_approval
        policy_result = evaluate(
            tool_name,
            tool_args,
            goal_id=goal_id,
            default_deny=(permission_mode == "GOAL")
        )
        
        decision = policy_result.get("decision", "block")
        
        # Step 2: Handle confirmation required
        if decision == "block":
            exec_session.set_state("failed")
            ExecutionEvent.get().execution_cancelled(exec_session)
            return {
                "success": False,
                "execution_id": execution_id,
                "error": f"Policy blocked: {policy_result.get('reason', '')}",
                "decision": "block",
                "result": None
            }
        
        if decision == "confirm":
            # Request approval for confirm-level tools
            approval_result = request_approval(
                tool_name,
                tool_args,
                goal_id=goal_id,
                default_deny=(permission_mode == "GOAL")
            )
            if approval_result != "approve":
                exec_session.set_state("failed")
                ExecutionEvent.get().execution_cancelled(exec_session)
                return {
                    "success": False,
                    "execution_id": execution_id,
                    "error": f"Approval rejected: {approval_result}",
                    "decision": "confirm_rejected",
                    "result": None
                }
        
        # Step 3: Execute tool
        from tools import execute_tool
        ExecutionEvent.get().tool_started(exec_session)
        
        try:
            result = execute_tool(tool_name, tool_args, allowed=allowed)
            result_str = str(result) if result is not None else ""
        except Exception as e:
            result_str = f"Execution error: {e}"
        
        # Step 4: Publish completion
        ok = not result_str.startswith("工具执行失败") and not result_str.startswith("未知工具")
        exec_session.set_state("completed" if ok else "failed")
        ExecutionEvent.get().tool_finished(exec_session, ok=ok)
        ExecutionEvent.get().execution_completed(exec_session)
        
        return {
            "success": ok,
            "execution_id": execution_id,
            "result": result_str,
            "tool": tool_name,
            "decision": decision
        }
        
    except Exception as e:
        exec_session.set_state("failed")
        ExecutionEvent.get().execution_cancelled(exec_session)
        return {
            "success": False,
            "execution_id": execution_id,
            "error": str(e),
            "result": None
        }


class Execution:
    """Async wrapper for execution (compatibility layer)."""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
    
    async def run(self, task: str, context: dict = None, **kwargs) -> dict:
        """Async run delegates to sync run()."""
        return run(task, context, **kwargs)
