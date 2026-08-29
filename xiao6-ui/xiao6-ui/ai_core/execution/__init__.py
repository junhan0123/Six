"""ai_core.execution — Xiao6 AI OS 统一执行平台（Execution Platform）。

全项目唯一执行内核。所有 Chat / Goal / Workflow / Tool 执行统一经 Execution.run()。

纪律（来自 Phase 3 红线）：
- Single Execution Path / Entry / Context / Queue / State / EventBus /
  Permission / Metrics / Recovery / Reflection。
- Move Never Rewrite / Extract Never Redesign / Behavior Never Change。
- 不新增 AI 功能 / Plugin / MCP / Workflow / Agent / Prompt / Tool / UI / DB /
  EventBus / Permission / Runtime / Memory / Knowledge / 网络通信 / 云能力。
"""

from .api import run, Execution
from .context import ExecutionContext, PermissionMode
from .session import ExecutionSession, SessionState
from .queue import ExecutionQueue
from .state import ExecutionState
from .events import ExecutionEvent
from .policy import ExecutionPolicy
from .metrics import ExecutionMetrics
from .recovery import ExecutionRecovery
from .reflection import ExecutionReflection

__all__ = [
    "run", "Execution",
    "ExecutionContext", "PermissionMode",
    "ExecutionSession", "SessionState",
    "ExecutionQueue",
    "ExecutionState",
    "ExecutionEvent",
    "ExecutionPolicy",
    "ExecutionMetrics",
    "ExecutionRecovery",
    "ExecutionReflection",
]
