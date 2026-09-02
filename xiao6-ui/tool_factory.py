#!/usr/bin/env python3
"""小6 · 工具工厂 / 动态 API 槽（运行时自扩展工具）

安全模型（参考实现「工具工厂/市场」的受控实现）：
- 每个自定义工具由一份**声明式 spec** 描述，绝不接受/执行用户提供的 Python/JS 代码。
- 执行策略（strategy.type）仅允许两种受控类型：
    * "http"    → 调用白名单域名内的 HTTP 接口（动态 API 槽）。支持 GET/POST、参数模板化、超时。
    * "command" → 在文件沙箱内以超时执行一条命令模板（默认禁用，需显式开启）。
- http 策略强制域名白名单，并硬阻断指向本机/内网/链路本地/云元数据（SSRF 防护）。
- spec 持久化于 SQLite custom_tools 表，重启不丢。

设计要点（对齐参考实现「动态 API 能力槽」）：动态 API 槽本质上就是「strategy.type=http」的自定义工具；
工具工厂则额外支持 command 策略（默认关）。两者共用本模块的声明/持久化/分发能力。
"""

import ipaddress
import json
import re
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

import config
from db import db_conn


# ---------------------------------------------------------------------------
# 安全：SSRF / 内网防护
# ---------------------------------------------------------------------------
_BLOCKED_HOST_KEYWORDS = ("metadata", "169.254")
_BLOCKED_HOST_REGEX = (
    r"^(localhost|localhost\.localdomain|.*\.local|.*\.internal|.*\.lan|.*\.home|.*\.corp|ip6-localhost)$",
    r"^0\.0\.0\.0$",
    r"^\[?::1\]?$",
)


def _host_of(url):
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _is_private_host(host):
    """硬阻断：本机 / 私有网段 / 链路本地 / 云元数据。True = 危险。"""
    h = (host or "").lower()
    if not h:
        return True
    if h in ("localhost", "localhost.localdomain", "0.0.0.0", "::1", "ip6-localhost"):
        return True
    if any(re.search(p, h) for p in _BLOCKED_HOST_REGEX):
        return True
    if any(k in h for k in _BLOCKED_HOST_KEYWORDS):
        return True
    # 防御 DNS rebinding：解析后若落到私有/链路本地/保留地址则阻断（解析失败不阻断，allowlist 已先行把关）
    try:
        for addr in socket.getaddrinfo(h, None):
            ip = addr[4][0].split("%")[0]
            try:
                ipo = ipaddress.ip_address(ip)
            except ValueError:
                continue
            if ipo.is_loopback or ipo.is_private or ipo.is_link_local or ipo.is_reserved or ipo.is_multicast:
                return True
    except (socket.gaierror, UnicodeError, ValueError, OSError):
        pass
    return False


def _domain_allowed(host, allowlist):
    """host 是否在允许域名集合内（后缀匹配，支持 example.com 与 *.example.com）。"""
    h = (host or "").lower()
    if not h:
        return False
    for rule in allowlist:
        rule = (rule or "").strip().lower()
        if not rule:
            continue
        if rule.startswith("*."):
            base = rule[2:]
            if h == base or h.endswith("." + base):
                return True
        elif h == rule or h.endswith("." + rule):
            return True
    return False


def _global_allowlist():
    return [x for x in (config.TOOL_FACTORY_DOMAIN_ALLOWLIST or "").split(",") if x.strip()]


# ---------------------------------------------------------------------------
# 参数模板化：将 {{key}} 替换为 args 中的值
# ---------------------------------------------------------------------------
def _substitute(template, args):
    def repl(m):
        return str((args or {}).get(m.group(1).strip(), ""))

    return re.sub(r"\{\{\s*([\w]+)\s*\}\}", repl, template or "")


# ---------------------------------------------------------------------------
# spec 校验（声明式，禁止任意代码执行）
# ---------------------------------------------------------------------------
_ALLOWED_STRATEGIES = ("http", "command")
_BANNED_FIELDS = ("code", "eval", "exec", "python", "javascript", "script", "cmd_raw", "py")


def _validate_spec(spec):
    if not isinstance(spec, dict):
        raise ValueError("spec 必须是 JSON 对象")
    name = spec.get("name")
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]{1,40}$", str(name or "")):
        raise ValueError("name 必须为 2-40 位字母/数字/下划线，且以字母或下划线开头")
    if not str(spec.get("description") or "").strip():
        raise ValueError("description 不能为空")
    params = spec.get("parameters")
    if params is None:
        params = {"type": "object", "properties": {}, "required": []}
    if not isinstance(params, dict) or params.get("type") != "object":
        raise ValueError("parameters 必须是 type=object 的 JSON Schema")
    strategy = spec.get("strategy")
    if not isinstance(strategy, dict):
        raise ValueError("strategy 必须是对象")
    stype = strategy.get("type")
    if stype not in _ALLOWED_STRATEGIES:
        raise ValueError(f"strategy.type 仅允许：{', '.join(_ALLOWED_STRATEGIES)}")
    # 严禁任何代码执行字段
    for banned in _BANNED_FIELDS:
        if banned in spec or banned in strategy:
            raise ValueError(f"禁止在 spec 中包含 {banned!r} 字段（安全策略）")
    if stype == "http":
        url = strategy.get("url")
        if not str(url or "").strip():
            raise ValueError("http 策略需要 url")
        host = _host_of(url)
        if _is_private_host(host):
            raise ValueError(f"禁止指向本机/内网/元数据地址：{host}")
        dl = strategy.get("domain_allowlist") or []
        if isinstance(dl, str):
            dl = [x for x in dl.split(",") if x.strip()]
        if not _domain_allowed(host, list(dl) + _global_allowlist()):
            raise ValueError(
                f"域名 {host} 不在白名单；需在 strategy.domain_allowlist 或全局 TOOL_FACTORY_DOMAIN_ALLOWLIST 中声明"
            )
    return True


# ---------------------------------------------------------------------------
# 持久化（SQLite custom_tools）
# ---------------------------------------------------------------------------
def list_custom_tools():
    try:
        conn = db_conn()
        rows = conn.execute("SELECT name, spec_json, created FROM custom_tools ORDER BY id").fetchall()
        conn.close()
        out = []
        for name, sj, created in rows:
            try:
                spec = json.loads(sj)
            except Exception:
                continue
            out.append({
                "name": name,
                "description": spec.get("description", ""),
                "strategy": (spec.get("strategy") or {}).get("type", ""),
                "created": created,
            })
        return out
    except Exception:
        return []


def get_custom_tool(name):
    try:
        conn = db_conn()
        row = conn.execute("SELECT spec_json FROM custom_tools WHERE name=?", (name,)).fetchone()
        conn.close()
        return json.loads(row[0]) if row else None
    except Exception:
        return None


def save_custom_tool(spec):
    _validate_spec(spec)
    name = spec["name"]
    sj = json.dumps(spec, ensure_ascii=False)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = db_conn()
    conn.execute(
        "INSERT INTO custom_tools(name, spec_json, created) VALUES(?,?,?) "
        "ON CONFLICT(name) DO UPDATE SET spec_json=excluded.spec_json, created=excluded.created",
        (name, sj, now),
    )
    conn.commit()
    conn.close()
    return name


def delete_custom_tool(name):
    conn = db_conn()
    conn.execute("DELETE FROM custom_tools WHERE name=?", (name,))
    conn.commit()
    conn.close()
    return True


# ---------------------------------------------------------------------------
# 运行时注入（供 tools.py 使用）
# ---------------------------------------------------------------------------
def enabled():
    return config.TOOL_FACTORY_ENABLED in ("1", "true", "yes")


def dynamic_tool_schemas():
    """返回 TOOLS 形状的 schema 列表，注入给 LLM。"""
    if not enabled():
        return []
    try:
        conn = db_conn()
        rows = conn.execute("SELECT spec_json FROM custom_tools").fetchall()
        conn.close()
    except Exception:
        return []
    out = []
    for (sj,) in rows:
        try:
            spec = json.loads(sj)
        except Exception:
            continue
        params = spec.get("parameters") or {"type": "object", "properties": {}, "required": []}
        out.append({
            "type": "function",
            "function": {
                "name": spec["name"],
                "description": spec.get("description", ""),
                "parameters": params,
            },
        })
    return out


def execute_custom_tool(name, args):
    if not enabled():
        return "工具工厂未启用（设置 TOOL_FACTORY_ENABLED=true）"
    spec = get_custom_tool(name)
    if not spec:
        return f"未知自定义工具：{name}"
    strategy = (spec.get("strategy") or {})
    stype = strategy.get("type")
    if stype == "http":
        return _exec_http(strategy, args or {})
    if stype == "command":
        return _exec_command(strategy, args or {})
    return f"不支持的策略：{stype}"


def _exec_http(strategy, args):
    url = _substitute(strategy.get("url", ""), args)
    method = (strategy.get("method") or "GET").upper()
    host = _host_of(url)
    if _is_private_host(host):
        return f"安全拦截：禁止访问本机/内网地址 {host}"
    dl = strategy.get("domain_allowlist") or []
    if isinstance(dl, str):
        dl = [x for x in dl.split(",") if x.strip()]
    if not _domain_allowed(host, list(dl) + _global_allowlist()):
        return f"安全拦截：域名 {host} 不在白名单"
    timeout = min(int(strategy.get("timeout", 15) or 15), 60)
    headers = {k: _substitute(v, args) for k, v in (strategy.get("headers") or {}).items()}
    data = None
    if method == "POST":
        body = strategy.get("body")
        if isinstance(body, dict):
            body = json.dumps({k: _substitute(str(v), args) for k, v in body.items()}, ensure_ascii=False)
        elif isinstance(body, str):
            body = _substitute(body, args)
        if body:
            data = body.encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        text = raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return f"HTTP 错误 {e.code}：{e.reason}"
    except Exception as e:
        return f"请求失败：{e}"
    MAX = 8000
    if len(text) > MAX:
        text = text[:MAX] + f"\n…（截断，原长 {len(text)} 字符）"
    return text


def _exec_command(strategy, args):
    if config.TOOL_FACTORY_COMMAND_ENABLED not in ("1", "true", "yes"):
        return "command 策略已禁用（需开启 TOOL_FACTORY_COMMAND_ENABLED）"
    cmd = _substitute(strategy.get("command", ""), args)
    if not cmd:
        return "命令为空"
    timeout = min(int(strategy.get("timeout", 10) or 10), 60)
    try:
        from sandbox import resolve_in_sandbox
        cwd = resolve_in_sandbox(".")
        proc = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        out = (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return f"命令执行超时（>{timeout}s）"
    except Exception as e:
        return f"命令执行失败：{e}"
    MAX = 4000
    if len(out) > MAX:
        out = out[:MAX] + f"\n…（截断，原长 {len(out)}）"
    return out
