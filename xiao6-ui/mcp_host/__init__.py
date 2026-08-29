#!/usr/bin/env python3
"""Xiao6 · MCP Host / External Tool Bridge（Phase 41）

小6第一次真正进入「外部世界可执行 AI OS」的桥：
  MCP Host（服务器管理 / stdio 传输 / 工具发现 / 调用 / 审计）
  + Browser Automation（第一个真实外部能力，经 Playwright MCP）。

纪律（严格，见 PHASE-41 spec）：
- 不新建第二套 Capability / Permission / Execution / EventBus / Memory / Context
  / AgentRuntime / Planner / Goal 系统。全部复用 Phase 40 Capability Foundation。
- MCP 服务器是「外部能力提供方」，不是 Capability Registry。
- 启动命令固定为受信任二进制（命令允许列表），LLM 不能决定。
- 仅 stdio transport；asyncio.create_subprocess_exec，绝不 shell=True。

对外 API：
  get_host()             —— MCPServerManager 单例（配置 + 运行时状态）
  ensure_loaded()        —— 加载受信任内置配置（不启动服务器）
  get_runtime()          —— 持久异步事件循环（见 runtime.py）
  execute_mcp_capability_sync(...) —— 同步执行入口
  bootstrap_mcp(audit_path)       —— 初始化（加载配置 + 审计路径）
"""
from __future__ import annotations

from .config import (
    ServerConfig, ServerState,
    COMMAND_ALLOWLIST, ALLOWED_BROWSERS,
    resolve_env, build_playwright_config,
)
from .transport import StdioTransport, TransportError
from .host import (
    MCPServer, MCPServerManager, ToolSpec, AuditEntry,
    get_host, ensure_loaded, bootstrap_mcp,
)
from .executor import (
    execute_mcp_capability, execute_mcp_capability_sync,
)
from .browser import BrowserSession, browser_scope
from .runtime import MCPRuntime, get_runtime

__all__ = [
    "ServerConfig", "ServerState",
    "COMMAND_ALLOWLIST", "ALLOWED_BROWSERS",
    "resolve_env", "build_playwright_config",
    "StdioTransport", "TransportError",
    "MCPServer", "MCPServerManager", "ToolSpec", "AuditEntry",
    "execute_mcp_capability", "execute_mcp_capability_sync",
    "BrowserSession", "browser_scope",
    "MCPRuntime", "get_runtime",
    "get_host", "ensure_loaded", "bootstrap_mcp",
]
