"""capability_os.discovery — Capability Discovery (stub for S79.8)
Minimal implementation for capability discovery and tool catalog.
"""

from __future__ import annotations

# Tool to capability mapping (stub)
_TOOL_TO_CAPABILITY = {}


def is_external_mcp(capability_id: str) -> bool:
    """Check if a capability is from external MCP."""
    return capability_id.startswith("mcp:")


def external_capability_ids() -> list:
    """List all external capability IDs."""
    return []


def list_executable_capabilities() -> list:
    """List all executable capabilities."""
    return []


def dispatch_tool_list(handler) -> list:
    """Dispatch tool list request. Returns empty list (stub)."""
    return []


def ensure_external_capabilities() -> None:
    """Ensure external capabilities are loaded."""
    pass


EXTERNAL_PREFIX = "mcp:"


def discoverable_skill_handles() -> list:
    """Discover available skill handles. Returns empty list (stub)."""
    return []
