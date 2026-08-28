"""ai_core.execution — Execution Platform Package (S79.7 minimal compat)
Minimal compatibility layer to allow server startup.
"""

from __future__ import annotations

from .api import run, Execution
from .events import ExecutionEvent

# Stub classes for compatibility
class ExecutionContext:
    pass

class PermissionMode:
    PASSIVE = "passive"
    ACTIVE = "active"

class ExecutionSession:
    pass

class SessionState:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ExecutionQueue:
    pass

class ExecutionState:
    IDLE = "idle"
    BUSY = "busy"
    BLOCKED = "blocked"

class ExecutionPolicy:
    pass

class ExecutionMetrics:
    pass

class ExecutionRecovery:
    pass

class ExecutionReflection:
    pass

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
