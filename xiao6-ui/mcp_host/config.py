"""mcp_host.config — MCP Host Configuration

Configuration types for MCP server management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ServerState(str, Enum):
    """MCP Server state machine."""
    DISABLED = "disabled"
    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    ERROR = "error"


@dataclass
class ServerConfig:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    enabled: bool = True
    permission_profile: str = "default"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "enabled": self.enabled,
            "permission_profile": self.permission_profile,
        }


# Command allowlist for trusted binaries
COMMAND_ALLOWLIST = [
    "node",
    "npx",
    "python3",
    "python",
]

# Allowed browser binaries
ALLOWED_BROWSERS = [
    "chromium",
    "chrome",
    "chrome.exe",
    "msedge",
    "firefox",
]


def resolve_env(config: ServerConfig) -> Dict[str, str]:
    """Resolve environment variables for an MCP server config."""
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin"}
    if config.env:
        env.update(config.env)
    return env


def build_playwright_config() -> List[ServerConfig]:
    """Build default Playwright MCP server configurations."""
    configs = []
    
    # Chromium
    configs.append(ServerConfig(
        name="playwright-chromium",
        command="node",
        args=["-e", "const {spawn} = require('child_process'); spawn('npx', ['@playwright/mcp'], {stdio: 'inherit'});"],
        enabled=False,
        permission_profile="browsing",
    ))
    
    return configs
