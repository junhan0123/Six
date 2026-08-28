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
        context: Execution context. 工具参数必须放 context["args"]；
                 可选附加键：session_id / goal_id。
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
    task_id = context.get("task_id")
    step_id = context.get("step_id")
    allowed = kwargs.get("allowed")
    permission_mode = kwargs.get("permission", "NONE")  # NONE or GOAL

    # R8-P1：Execution Trace 观测点（入口）——纯观测，不改变任何执行逻辑
    _trace_t0 = time.time()
    from ai_core.execution import trace as _trace
    
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
        # R8-P0：统一执行入口 FAIL CLOSED —— default_deny 恒为 True。
        # 修复：原先 default_deny=(permission_mode == "GOAL") 在默认 NONE 模式下为 False，
        #   1) 关闭 LOW_RISK 自动分支，低危工具误入 confirm；
        #   2) 无 Goal 上下文时 request_approval 不快速拒绝而是挂起 300s（ev.wait）；
        #   3) 有 goal_id 且 default_deny=False 时 confirm 工具反而自动放行（policy 漏洞）。
        # 现与 agent_runtime / capability_runtime 的契约一致：无 Goal 上下文直接拒绝，有 Goal 走审批。
        policy_result = evaluate(
            tool_name,
            tool_args,
            goal_id=goal_id,
            default_deny=True
        )
        
        decision = policy_result.get("decision", "block")
        
        # Step 2: Handle confirmation required
        if decision == "block":
            exec_session.set_state("failed")
            ExecutionEvent.get().execution_cancelled(exec_session)
            _trace.record(goal_id=goal_id, task_id=task_id, step_id=step_id,
                           tool_name=tool_name, args=tool_args, start_time=_trace_t0,
                           end_time=time.time(), status=_trace.STATUS_BLOCKED,
                           error=f"Policy blocked: {policy_result.get('reason', '')}",
                           recovery_action=_trace.RECOVERY_POLICY_BLOCKED,
                           execution_id=execution_id)
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
                default_deny=True
            )
            if approval_result != "approve":
                exec_session.set_state("failed")
                ExecutionEvent.get().execution_cancelled(exec_session)
                _trace.record(goal_id=goal_id, task_id=task_id, step_id=step_id,
                               tool_name=tool_name, args=tool_args, start_time=_trace_t0,
                               end_time=time.time(), status=_trace.STATUS_REJECTED,
                               error=f"Approval rejected: {approval_result}",
                               recovery_action=_trace.RECOVERY_FAIL_CLOSED,
                               execution_id=execution_id)
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
        
        exec_error = False
        try:
            result = execute_tool(tool_name, tool_args, allowed=allowed)
            result_str = str(result) if result is not None else ""
        except Exception as e:
            result_str = f"Execution error: {e}"
            exec_error = True
        
        # Step 4: Publish completion
        # R8-P0：失败判定复用 execute_tool 的失败前缀/中部标记（与 CapabilityResult 同词汇），
        # 确保 Policy 拒绝 / 工具失败 / 未知工具或技能如实上报 success=False，不被误判为成功。
        ok = not exec_error and not any(m in result_str for m in (
            "工具执行失败", "未知工具", "未知技能", "外部 MCP 能力执行失败",
            "无执行体映射", "在远程会话中不可用", "被权限策略阻止",
            "被安全策略阻止", "用户拒绝执行", "为永久拒绝占位",
        ))
        exec_session.set_state("completed" if ok else "failed")
        ExecutionEvent.get().tool_finished(exec_session, ok=ok)
        ExecutionEvent.get().execution_completed(exec_session)
        
        # R8-P1：Execution Trace 观测点（正常终态）
        _trace.record(goal_id=goal_id, task_id=task_id, step_id=step_id,
                       tool_name=tool_name, args=tool_args, start_time=_trace_t0,
                       end_time=time.time(),
                       status=_trace.STATUS_OK if ok else _trace.STATUS_FAILED,
                       error=None if ok else result_str,
                       recovery_action=_trace.RECOVERY_NONE,
                       execution_id=execution_id, extra={"decision": decision})
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
        # R8-P1：Execution Trace 观测点（异常终态）
        _trace.record(goal_id=goal_id, task_id=task_id, step_id=step_id,
                       tool_name=tool_name, args=tool_args, start_time=_trace_t0,
                       end_time=time.time(), status=_trace.STATUS_FAILED,
                       error=str(e), recovery_action=_trace.RECOVERY_FAIL_CLOSED,
                       execution_id=execution_id)
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
