#!/usr/bin/env python3
"""MCP Host · 服务器管理器（§七/§八/§九）

职责（不新建第二套 Capability/Permission/Execution 系统）：
- Server Configuration：name/command/args/env/enabled/permission_profile（不硬编码 Playwright）。
- Server Manager：load/validate/start/stop/restart/health/reconnect。
  - 状态机 DISABLED/STARTING/READY/DEGRADED/ERROR/STOPPED。
  - 启动握手超时 + 退避 + 连续失败上限（达到上限直接 STOPPED，no infinite restart）。
- Transport：stdio（见 transport.py）。
- Tool Discovery：initialize → notifications/initialized → tools/list。
- Tool Registry Adapter / Invocation / Timeout / Cancellation / Audit。

MCP 服务器是「外部能力提供方」，不是 Capability Registry。
Xiao6侧：discover → map → authorize → invoke → verify。
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .config import ServerConfig, ServerState, resolve_env, build_playwright_config
from .transport import StdioTransport, TransportError
from .runtime import get_runtime

logger = logging.getLogger("mcp_host.host")

PROTOCOL_VERSION = "2024-11-05"
CLIENT_INFO = {"name": "xiao6", "version": "1.0.0"}


@dataclass
class ToolSpec:
    server: str
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)

    def capability_id_of(self) -> str:
        return f"external.mcp.{self.server}.{self.name}"


@dataclass
class AuditEntry:
    ts: float
    server: str
    tool: str
    capability_id: str
    ok: bool
    latency: float
    error: str = ""


class MCPServer:
    def __init__(self, config: ServerConfig):
        self.config = config
        self.state = ServerState.DISABLED if not config.enabled else ServerState.STOPPED
        self.transport: Optional[StdioTransport] = None
        self.tools: List[ToolSpec] = []
        self.failure_count = 0
        self.last_error: str = ""
        self.last_activity: float = 0.0
        self.started_at: float = 0.0
        self.backoff_until: float = 0.0
        self.lock = None  # 延迟到运行时 loop 创建 asyncio.Lock（避免跨 loop 绑定问题）

    async def _ensure_lock(self):
        if self.lock is None:
            self.lock = asyncio.Lock()
        return self.lock

    async def start(self) -> bool:
        lock = await self._ensure_lock()
        async with lock:
            if self.state in (ServerState.STARTING, ServerState.READY, ServerState.DEGRADED):
                return self.state in (ServerState.READY, ServerState.DEGRADED)
            if not self.config.enabled:
                self.state = ServerState.DISABLED
                return False
            if self.backoff_until and time.time() < self.backoff_until:
                self.state = ServerState.ERROR  # 退避中，不无限重启
                return False
            self.state = ServerState.STARTING
            self.last_error = ""
            try:
                env = resolve_env(self.config)
                self.transport = StdioTransport(
                    self.config.command, self.config.args, env,
                    stderr_handler=lambda s: logger.debug("[%s] %s", self.config.name, s[:300]),
                )
                await self.transport.start()
                await self.transport.request("initialize", {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": CLIENT_INFO,
                }, timeout=self.config.timeout)
                await self.transport.notify("notifications/initialized", {})
                tools_res = await self.transport.request(
                    "tools/list", {}, timeout=self.config.timeout)
                raw_tools = (tools_res or {}).get("tools", []) or []
                self.tools = [self._to_spec(t) for t in raw_tools]
                self.started_at = time.time()
                self.last_activity = time.time()
                self.failure_count = 0
                self.state = ServerState.DEGRADED if not self.tools else ServerState.READY
                # 发现后立即把工具发布到 Capability Foundation（不新建注册表）
                if self.tools:
                    self._publish_capabilities()
                return True
            except Exception as e:  # 真实失败，绝不伪造 READY
                self.failure_count += 1
                self.last_error = f"{type(e).__name__}: {e}"
                if self.failure_count >= self.config.max_failures:
                    self.state = ServerState.STOPPED  # 达到上限，停手，不无限重启
                else:
                    self.state = ServerState.ERROR
                    self.backoff_until = time.time() + self.config.backoff_base * self.failure_count
                await self._safe_close()
                return False

    def _to_spec(self, t: Dict[str, Any]) -> ToolSpec:
        return ToolSpec(
            server=self.config.name,
            name=t.get("name", "?"),
            description=t.get("description", ""),
            input_schema=t.get("inputSchema", {}) or {},
        )

    async def stop(self) -> None:
        lock = await self._ensure_lock()
        async with lock:
            await self._safe_close()
            self.state = ServerState.STOPPED if self.config.enabled else ServerState.DISABLED

    async def _safe_close(self) -> None:
        if self.transport is not None:
            try:
                await self.transport.close()
            except Exception:
                pass
        self.transport = None

    async def call_tool(self, tool: str, args: Dict[str, Any], timeout: Optional[float] = None) -> Dict[str, Any]:
        if self.state not in (ServerState.READY, ServerState.DEGRADED):
            raise TransportError(f"服务器 {self.config.name} 状态 {self.state}，不可调用")
        if self.transport is None:
            raise TransportError("transport 未就绪")
        timeout = timeout or self.config.call_timeout
        res = await self.transport.request(
            "tools/call", {"name": tool, "arguments": args or {}}, timeout=timeout)
        self.last_activity = time.time()
        return res or {}

    def is_tool_available(self, tool: str) -> bool:
        return any(t.name == tool for t in self.tools)

    def _publish_capabilities(self) -> None:
        """把已发现的工具发布到 Capability Foundation（discover → map）。

        纪律：这是既有统一注册表的【受控扩展点】，不是第二套注册表。
        幂等（按 id 覆盖）。
        """
        try:
            from capability_os.registry import (
                Capability, Risk, Permission, register_capability)
            from capability_os.execution_mapping import register_mcp_executor
            for t in self.tools:
                cap_id = t.capability_id_of()
                register_capability(Capability(
                    id=cap_id,
                    name=f"{self.config.name}·{t.name}",
                    description=(t.description or f"MCP 工具 {t.name}（服务器 {self.config.name}）"),
                    group="External · MCP",
                    icon="🔌",
                    risk=Risk.MEDIUM,
                    permission=Permission.CONFIRM,
                    available=True,
                    implemented=True,
                    entry=f"mcp://{self.config.name}/{t.name}",
                    data_source=f"MCP:{self.config.name}",
                    keywords=[t.name, self.config.name, "mcp", "browser", "external"],
                ))
                register_mcp_executor(cap_id, self.config.name, t.name)
        except Exception as e:
            logger.warning("发布 MCP 能力失败: %s", e)

    def view(self) -> Dict[str, Any]:
        return {
            "name": self.config.name,
            "state": self.state,
            "enabled": self.config.enabled,
            "permission_profile": self.config.permission_profile,
            "transport": self.config.transport,
            "tool_count": len(self.tools),
            "tools": [{"name": t.name, "description": t.description,
                       "capability_id": t.capability_id_of()} for t in self.tools],
            "failure_count": self.failure_count,
            "last_error": self.last_error,
            "last_activity": self.last_activity,
            "started_at": self.started_at,
            "browser": self.config.browser,
            "headless": self.config.headless,
        }


class MCPServerManager:
    def __init__(self):
        self._servers: Dict[str, MCPServer] = {}
        self._audit: List[AuditEntry] = []
        self._audit_path: Optional[str] = None
        self._lock = threading.Lock()  # 保护 _servers 字典的短临界区

    # —— 配置 ——
    def add_config(self, config: ServerConfig) -> List[str]:
        errs = config.validate()
        if not errs:
            with self._lock:
                self._servers[config.name] = MCPServer(config)
        return errs

    def load_defaults(self) -> List[str]:
        # 仅加载受信任的内置配置（Playwright）。LLM 不决定配置内容。
        return self.add_config(build_playwright_config())

    def get(self, name: str) -> Optional[MCPServer]:
        with self._lock:
            return self._servers.get(name)

    def list_servers(self) -> List[MCPServer]:
        with self._lock:
            return list(self._servers.values())

    # —— 生命周期（异步，运行于持久 runtime loop）——
    async def start(self, name: str) -> bool:
        srv = self.get(name)
        if srv is None:
            return False
        return await srv.start()

    async def stop(self, name: str) -> None:
        srv = self.get(name)
        if srv:
            await srv.stop()

    async def restart(self, name: str) -> bool:
        srv = self.get(name)
        if srv is None:
            return False
        await srv.stop()
        return await srv.start()

    async def ensure_started(self, name: str) -> bool:
        srv = self.get(name)
        if srv is None:
            return False
        if srv.state in (ServerState.READY, ServerState.DEGRADED):
            return True
        return await srv.start()

    # —— 同步便捷封装（经持久 runtime loop 派发）——
    def start_server(self, name: str, timeout: float = 180.0) -> bool:
        return get_runtime().run(self.start(name), timeout=timeout)

    def stop_server(self, name: str) -> None:
        get_runtime().run(self.stop(name))

    def restart_server(self, name: str, timeout: float = 180.0) -> bool:
        return get_runtime().run(self.restart(name), timeout=timeout)

    # —— 发现 / 注册表适配器（只读视图，不修改系统状态）——
    def external_capabilities(self) -> List[Dict[str, Any]]:
        out = []
        for srv in self.list_servers():
            for t in srv.tools:
                out.append({
                    "id": t.capability_id_of(),
                    "server": srv.config.name,
                    "tool": t.name,
                    "name": f"{srv.config.name}·{t.name}",
                    "description": t.description,
                    "group": "External · MCP",
                    "icon": "🔌",
                    "risk": "MEDIUM",
                    "permission": "confirm",
                    "available": srv.state == ServerState.READY,
                    "implemented": True,
                    "source": f"mcp://{srv.config.name}/{t.name}",
                    "input_schema": t.input_schema,
                })
        return out

    def is_tool_available(self, server: str, tool: str) -> bool:
        srv = self.get(server)
        return srv.is_tool_available(tool) if srv else False

    def capability_available(self, capability_id: str) -> bool:
        # external.mcp.<server>.<tool>
        if not capability_id.startswith("external.mcp."):
            return False
        parts = capability_id.split(".", 3)
        if len(parts) < 4:
            return False
        return self.is_tool_available(parts[2], parts[3])

    # —— 调用（异步）——
    async def call(self, server: str, tool: str, args: Dict[str, Any],
                   timeout: Optional[float] = None) -> Dict[str, Any]:
        srv = self.get(server)
        if srv is None:
            raise TransportError(f"未知 MCP 服务器: {server}")
        # 能力已在 start() 发现时发布到 Capability Foundation（discover → map）
        t0 = time.time()
        cap_id = f"external.mcp.{server}.{tool}"
        ok = False
        err = ""
        result: Dict[str, Any] = {}
        try:
            result = await srv.call_tool(tool, args, timeout)
            ok = True
        except Exception as e:
            ok = False
            err = f"{type(e).__name__}: {e}"
            result = {"error": err}
        dt = time.time() - t0
        self._audit.append(AuditEntry(t0, server, tool, cap_id, ok, dt, err))
        if self._audit_path:
            try:
                with open(self._audit_path, "a", encoding="utf-8") as f:
                    f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(t0))} "
                            f"{cap_id} ok={ok} {dt:.2f}s {err}\n")
            except Exception:
                pass
        return result

    def call_server(self, server: str, tool: str, args: Dict[str, Any],
                    timeout: Optional[float] = None) -> Dict[str, Any]:
        return get_runtime().run(self.call(server, tool, args, timeout), timeout=(timeout or 120) + 15)

    # —— 视图 ——
    def servers_view(self) -> Dict[str, Any]:
        servers = self.list_servers()
        return {
            "servers": [s.view() for s in servers],
            "total": len(servers),
            "ready": sum(1 for s in servers if s.state == ServerState.READY),
            "external_capabilities": self.external_capabilities(),
        }

    def set_audit_path(self, path: str) -> None:
        self._audit_path = path

    def recent_audit(self, n: int = 20) -> List[Dict[str, Any]]:
        tail = self._audit[-n:]
        return [{"ts": a.ts, "server": a.server, "tool": a.tool,
                 "capability_id": a.capability_id, "ok": a.ok,
                 "latency": round(a.latency, 3), "error": a.error} for a in tail]

    async def shutdown_all(self) -> None:
        for srv in self.list_servers():
            try:
                await srv.stop()
            except Exception:
                pass


# —— 包级单例（避免循环导入：get_host 定义在本模块，由 __init__ 再导出）——
_HOST = None
_LOADED = False


def get_host() -> "MCPServerManager":
    global _HOST
    if _HOST is None:
        _HOST = MCPServerManager()
    return _HOST


def ensure_loaded() -> "MCPServerManager":
    """加载受信任内置配置（Playwright）。不启动服务器、不修改系统状态。幂等。"""
    global _LOADED
    host = get_host()
    if not _LOADED and not host.list_servers():
        host.load_defaults()
        _LOADED = True
    return host


def bootstrap_mcp(audit_path: str = None) -> "MCPServerManager":
    """初始化 MCP Host：加载配置 + 设置审计路径。"""
    host = ensure_loaded()
    if audit_path:
        host.set_audit_path(audit_path)
    return host
