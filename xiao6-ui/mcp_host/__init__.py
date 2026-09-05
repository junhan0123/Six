#!/usr/bin/env python3
"""Xiao6 · MCP Host — External Tool Bridge (Phase 41, incomplete in v1.0.0)

NOTE: This module is intentionally incomplete in v1.0.0.
Transport, runtime, executor, and browser submodules are not yet implemented.
Product code does not depend on this module being fully functional.

对外 API (stub):
  ensure_loaded()        — no-op stub
  bootstrap_mcp()        — no-op stub
"""
from __future__ import annotations


class ServerConfig:
    """Stub for ServerConfig."""
    def __init__(self, name: str, command: str, args=None, env=None, enabled=True, permission_profile="default"):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env
        self.enabled = enabled
        self.permission_profile = permission_profile


class ServerState:
    """Stub enum for state machine."""
    DISABLED = "disabled"
    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    DEGRADED = "degraded"
    ERROR = "error"


def resolve_env(config):
    return {}


def build_playwright_config():
    return []


def ensure_loaded():
    """No-op stub."""
    pass


def bootstrap_mcp(audit_path=None):
    """No-op stub."""
    pass


def get_host():
    """No-op stub."""
    return None


def get_runtime():
    """No-op stub."""
    return None


def execute_mcp_capability_sync(*args, **kwargs):
    """No-op stub."""
    return None
