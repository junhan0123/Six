"""ai_core.execution — Execution Platform Package

Unified execution entry point with policy gate.
All execution flows through ai_core.execution.run().
"""

from __future__ import annotations

from .api import run, Execution
from .events import ExecutionEvent

# Context and session models
from context.models import BuildContext, ContextItem, ContextBundle


class ExecutionContext:
    """Execution context holder."""
    
    def __init__(self, session_id: str = "default", goal_id: int = None, **kwargs):
        self.session_id = session_id
        self.goal_id = goal_id
        self.metadata = kwargs
    
    def as_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "goal_id": self.goal_id,
            **self.metadata
        }


class ExecutionSession:
    """Execution session state machine."""
    
    def __init__(self, execution_id: str, task: str, context: BuildContext, goal_id: int = None):
        self.execution_id = execution_id
        self.task = task
        self.context = context
        self.goal_id = goal_id
        self.state = "pending"
        self.created_at = None
        self.completed_at = None
        self.result = None
        self.error = None
    
    def set_state(self, state: str):
        """Update execution state."""
        self.state = state
        if state in ("completed", "failed"):
            import time
            self.completed_at = time.time()
    
    def as_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "task": self.task,
            "session_id": self.context.session_id,
            "goal_id": self.goal_id,
            "state": self.state,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class PermissionMode:
    """Permission mode constants."""
    NONE = "NONE"
    GOAL = "GOAL"


class SessionState:
    """Session state constants."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionQueue:
    """Execution queue (stub for future use)."""
    
    def __init__(self):
        self._queue = []
    
    def enqueue(self, task: str, args: dict = None) -> str:
        """Add task to queue."""
        exec_id = f"exec-{len(self._queue)+1:04d}"
        self._queue.append({"id": exec_id, "task": task, "args": args})
        return exec_id
    
    def dequeue(self) -> dict:
        """Get next task from queue."""
        if self._queue:
            return self._queue.pop(0)
        return None


class ExecutionState:
    """Execution state constants."""
    IDLE = "idle"
    BUSY = "busy"
    BLOCKED = "blocked"


class ExecutionPolicy:
    """Execution policy holder."""
    
    def __init__(self, default_deny: bool = True):
        self.default_deny = default_deny


class ExecutionMetrics:
    """Execution metrics collector."""
    
    def __init__(self):
        self.count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_time = 0.0
    
    def record(self, success: bool, duration: float):
        self.count += 1
        self.total_time += duration
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1


class ExecutionRecovery:
    """Execution recovery handler."""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.checkpoints = {}
    
    def save_checkpoint(self, execution_id: str, state: dict):
        self.checkpoints[execution_id] = {
            "state": state,
            "timestamp": time.time()
        }
    
    def restore_checkpoint(self, execution_id: str) -> dict:
        return self.checkpoints.get(execution_id)
    
    def clear_checkpoint(self, execution_id: str):
        self.checkpoints.pop(execution_id, None)


class ExecutionReflection:
    """Execution reflection and learning."""
    
    def __init__(self):
        self.history = []
    
    def record(self, execution_id: str, result: dict):
        self.history.append({
            "execution_id": execution_id,
            "result": result,
            "timestamp": time.time()
        })
    
    def get_insights(self) -> list:
        """Return execution insights for learning."""
        return self.history[-10:]  # Last 10 executions


import time

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
