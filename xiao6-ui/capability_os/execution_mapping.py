"""capability_os.execution_mapping — Execution Mapping (S79.7 compat)
Minimal compatibility layer for capability execution mapping.
"""

from typing import Callable, Dict, Any, Optional


# Executor registry
_EXECUTORS: Dict[str, Callable] = {}


def register_executor(name: str, executor: Callable) -> None:
    """Register an executor function."""
    _EXECUTORS[name] = executor


def get_executor(name: str) -> Optional[Callable]:
    """Get a registered executor by name."""
    return _EXECUTORS.get(name)


def executor_callable(name: str, **kwargs) -> Optional[Callable]:
    """Get an executor callable by name. Returns None if not found."""
    return get_executor(name)


def tool_to_capability(tool_name: str) -> Optional[str]:
    """Map a tool name to a capability ID."""
    return None


def map_tool_to_capability(tool_name: str) -> Optional[str]:
    """Map a tool name to a capability ID (alias)."""
    return tool_to_capability(tool_name)


def list_executors() -> list:
    """List all registered executor names."""
    return list(_EXECUTORS.keys())
