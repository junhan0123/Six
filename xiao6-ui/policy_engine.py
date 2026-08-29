#!/usr/bin/env python3
"""小6 · 授权内核（Policy Engine）—— Agent 级 human-in-the-loop 闸门。

取代「执行侧护栏」之外的空缺：执行侧（sandbox / tool_factory）已负责
「能不能安全运行」（危险命令 / 内网 / 云元数据硬阻断），本模块负责
「该不该自动做」（auto / confirm / session / never 四级授权）。

设计要点：
- 复用 tools.READONLY_TOOLS 作为 auto 种子（零重复）。
- 复用 sandbox.is_dangerous_command 判定 never/dangerous（零重复）。
- confirm 级：生成 ticket，经 EventBus(TOPIC_SSE) 弹前端审批卡，
  后端用 threading.Event 挂起，POST /api/agent/approval 唤醒（Round 2 接线）。
- never 黑名单持久化到 data/policy_store.json（零密钥、纯本地）。
- session 缓存：当前进程内存 set，本次会话内已批准则等同 auto。

纯标准库，无新依赖。
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from typing import Optional

# ---------- 四级权限常量 ----------
AUTO = "auto"
CONFIRM = "confirm"
SESSION = "session"
NEVER = "never"

# 显式 never（危险 / 不可逆）静态种子；run_shell 视参数由 is_dangerous 再判
_NEVER_TOOLS = {"kill_process", "file_delete"}

POLICY_STORE_PATH = os.path.join("data", "policy_store.json")

_lock = threading.RLock()
_session_approved: dict = {}        # per-goal 已批准工具集合（发现 A 修复：隔离状态泄漏）
_never_store: set = set()           # 持久化永久禁止
_pending: dict = {}                 # ticket -> {event, decision, tool, args}


def _load_store() -> None:
    global _never_store
    try:
        if os.path.exists(POLICY_STORE_PATH):
            with open(POLICY_STORE_PATH, "r", encoding="utf-8") as f:
                d = json.load(f) or {}
            _never_store = set(d.get("never", []))
    except Exception:
        _never_store = set()


def _save_store() -> None:
    try:
        os.makedirs(os.path.dirname(POLICY_STORE_PATH), exist_ok=True)
        with open(POLICY_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump({"never": sorted(_never_store)}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


_load_store()


def tool_permission(tool: str) -> str:
    """返回某工具的声明权限等级（不查参数）。"""
    if tool in _never_store:
        return NEVER
    if tool in _NEVER_TOOLS:
        return NEVER
    try:
        from tools import READONLY_TOOLS
        if tool in READONLY_TOOLS:
            return AUTO
    except Exception:
        pass
    # 默认：写操作 / 外部副作用 / 未显式映射的工具 -> confirm
    # （P10-4：低危自动执行改由 evaluate() 的 LOW_RISK_TOOLS 白名单精确控制，
    #   不再用全局 AGENT_POLICY_DEFAULT=auto  blanket 放行，避免 run_shell 等高危工具被自动执行）
    return CONFIRM


def is_never_by_args(tool: str, args: dict) -> bool:
    """参数级危险判定（复用 sandbox.is_dangerous_command）。"""
    if tool == "run_shell":
        cmd = (args or {}).get("command") or ""
        try:
            from sandbox import is_dangerous_command
            return bool(is_dangerous_command(cmd))
        except Exception:
            return False
    return False


# ───────────────────────── 47.3 MCP 安全边界（M-01/M-02/M-03）─────────────────────────
# 仅对 external.mcp.* 做工具/参数级显式分类；最终裁决仍由 evaluate 统一出口，
# 不改变四级语义（auto/confirm/block），不新建第二套权限系统（Policy Truth = 本模块）。
import re as _re

# 云元数据 / 内网危险目标（M-01）：云厂商实例元数据服务(IMDS)、链路本地、RFC1918 私有段。
# 注：回环/localhost(127.0.0.1) 不在 BLOCK 之列，降为 CONFIRM（合法本地开发导航；
#   Phase 41 真实浏览器回归依赖本地夹具页；且浏览器在用户本机，SSRF 风险远低于 IMDS/RFC1918）。
#   IMDS(169.254.169.254) 与 RFC1918 仍硬阻断（凭据窃取 / 内网横向）。
_CLOUD_METADATA_HOSTS = {"169.254.169.254", "169.254.169.123",
                         "metadata.google.internal", "metadata.goog"}
_LINKLOCAL_RE = _re.compile(r"^169\.254\.\d{1,3}\.\d{1,3}$")
_PRIVATE_RE_LIST = [
    _re.compile(r"^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),
    _re.compile(r"^192\.168\.\d{1,3}\.\d{1,3}$"),
    _re.compile(r"^172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}$"),
]


def _kw(tool: str, kws) -> bool:
    return any(k in tool for k in kws)


def _is_dangerous_url(url) -> bool:
    """M-01：仅允许 http/https；阻断云元数据(IMDS) / 链路本地 / RFC1918 私有网段 / 非法 scheme。
    回环/localhost 不在此阻断之列（降为 CONFIRM，合法本地开发导航）。"""
    if not url:
        return False
    u = str(url).strip().lower()
    if not (u.startswith("http://") or u.startswith("https://")):
        return True  # file:// / data: / javascript: / ftp: 等非法 scheme 一律阻断
    try:
        from urllib.parse import urlparse
        host = urlparse(u).hostname or ""
    except Exception:
        host = ""
    if not host:
        return True
    if host in _CLOUD_METADATA_HOSTS:
        return True
    if _LINKLOCAL_RE.match(host):
        return True
    for rx in _PRIVATE_RE_LIST:
        if rx.match(host):
            return True
    return False


def _classify_external_mcp(cap_id: str, args: dict):
    """external.mcp.* 显式分级。返回 {decision, reason, permission} 或 None（格式异常）。

    AUTO   : 只读观察类（snapshot / screenshot / extract / tabs / list_pages / get_text …）
    BLOCK  : 导航至内网/云元数据/非法 scheme；外部文件删除
    CONFIRM: 导航（安全 URL）/ JS 执行 / 文件读写 / 交互 —— 需人工确认或 GDE 预批准
    """
    if not cap_id.startswith("external.mcp."):
        return None
    parts = cap_id.split(".")
    if len(parts) < 4:
        return None
    tool = ".".join(parts[3:]).lower()

    # 只读观察类（M-03 收敛：仅显式只读集 AUTO，其余默认 CONFIRM）
    if _kw(tool, ("snapshot", "screenshot", "extract", "tabs", "list_pages",
                  "get_text", "get_content", "console", "accessibility", "observe", "read")):
        return {"decision": "auto", "reason": "只读观察类外部能力，自动执行", "permission": AUTO}

    # M-01：导航类 — 先做 URL 安全分类
    if _kw(tool, ("navigate", "go_back", "go_forward", "scroll",
                  "tab_new", "tab_close", "tab_select", "new_page", "close_page")):
        url = str(args.get("url") or args.get("href") or args.get("link")
                  or args.get("page") or args.get("target") or "")
        if _is_dangerous_url(url):
            return {"decision": "block",
                    "reason": "导航目标被拦截（内网/云元数据/非法 scheme）: %s" % url,
                    "permission": NEVER}
        return {"decision": "confirm",
                "reason": "导航至外部地址，需人工确认或 GDE 预批准", "permission": CONFIRM}

    # M-02：JS 执行（page.evaluate）— 高危，需人工确认
    if "evaluate" in tool:
        return {"decision": "confirm",
                "reason": "JS 执行（page.evaluate）属高危操作，需人工确认", "permission": CONFIRM}

    # M-03：文件操作 — 删除类直接阻断，其余需确认
    if _kw(tool, ("file", "upload", "download", "save_as", "save-file")):
        if _kw(tool, ("delete", "remove")):
            return {"decision": "block", "reason": "外部文件删除被阻断", "permission": NEVER}
        return {"decision": "confirm", "reason": "外部文件读写，需人工确认", "permission": CONFIRM}

    # 交互类 — 需人工确认
    if _kw(tool, ("click", "type", "fill", "press", "select", "drag", "hover", "input")):
        return {"decision": "confirm", "reason": "外部交互操作，需人工确认", "permission": CONFIRM}

    # 未显式分类 — 默认 CONFIRM（不自动放行）
    return {"decision": "confirm",
            "reason": "未显式分类的外部 MCP 能力，默认需人工确认", "permission": CONFIRM}


def evaluate(tool: str, args: Optional[dict] = None, context: Optional[dict] = None,
             goal_id: Optional[int] = None, default_deny: bool = True) -> dict:
    """统一裁决：返回 {decision: auto|confirm|block, reason, permission}。"""
    args = args or {}
    # 47.3 M-01/M-02/M-03：external.mcp.* 显式分级。
    # 唯一权限真相源仍是本模块；此处仅做工具/参数级显式分类，不改变四级语义，
    # 不新建第二套权限系统。只读观察类 AUTO；IMDS/RFC1918 危险 URL 与外部文件删除 BLOCK；
    # 其余（导航含回环 / JS 执行 / 文件读写 / 交互）CONFIRM，保留 GDE session 预批准。
    if tool.startswith("external.mcp."):
        cls = _classify_external_mcp(tool, args)
        if cls is not None:
            d0 = cls["decision"]
            if d0 == "block":
                return {"decision": "block", "reason": cls["reason"], "permission": cls["permission"]}
            if d0 == "auto":
                return {"decision": "auto", "reason": cls["reason"], "permission": AUTO}
            # confirm：保留 GDE session 预批准；无预批准则按 default-deny 走确认
            with _lock:
                if goal_id and tool in _session_approved.get(goal_id, set()):
                    return {"decision": "auto", "reason": f"Goal #{goal_id} 已预批准", "permission": SESSION}
            if default_deny or not goal_id:
                return {"decision": "confirm", "reason": cls["reason"], "permission": CONFIRM}
            return {"decision": "auto", "reason": cls["reason"], "permission": AUTO}

    # P10-4：低危工具白名单 — 无 Goal 上下文也自动执行（低危集人工维护，不含高危/危险命令）
    # 受 AGENT_POLICY_DEFAULT 总开关约束：仅当全局默认=auto 时放行（confirm 则全部走确认）
    from tools import LOW_RISK_TOOLS
    import config
    if default_deny and tool in LOW_RISK_TOOLS and not goal_id and config.AGENT_POLICY_DEFAULT == "auto":
        return {"decision": "auto", "reason": f"低危工具 {tool}，自动执行", "permission": AUTO}
    perm = tool_permission(tool)
    if is_never_by_args(tool, args):
        return {"decision": "block", "reason": "危险命令被拦截（sandbox.is_dangerous_command）", "permission": NEVER}
    if perm == NEVER:
        return {"decision": "block", "reason": "工具已被列入永久禁止名单", "permission": NEVER}
    if perm == AUTO:
        return {"decision": "auto", "reason": "只读 / 低危工具，自动执行", "permission": AUTO}
    # CONFIRM（含 run_shell 静态标记）：检查该 Goal 的 session 批准缓存（per-goal 隔离）
    with _lock:
        if goal_id and tool in _session_approved.get(goal_id, set()):
            return {"decision": "auto", "reason": f"Goal #{goal_id} 已预批准", "permission": SESSION}
    # 发现 B 修复：无 goal_id 时强制 confirm（default-deny），不给 LLM 非确定派发绕过审批
    if default_deny or not goal_id:
        return {"decision": "confirm", "reason": "无 Goal 上下文，需人工确认", "permission": CONFIRM}
    return {"decision": "auto", "reason": "仅读 / 低危工具，自动执行", "permission": AUTO}


def pre_approve_tools(goal_id: int, tools: list) -> None:
    """GDE 建 Goal 后调用：把高置信度工具预批准到该 Goal 级别（per-goal 隔离）。"""
    with _lock:
        _session_approved.setdefault(goal_id, set()).update(tools)


def approve_in_goal(goal_id: Optional[int], tool: str) -> None:
    """request_approval 通过后，把 tool 记到该 goal 的批准集合（发现 A 修复）。"""
    with _lock:
        _session_approved.setdefault(goal_id, set()).add(tool)


# ---------- confirm 审批闭环 ----------

def request_approval(tool: str, args: dict, summary: str = "", timeout: float = 300.0,
                     goal_id: Optional[int] = None, default_deny: bool = True) -> str:
    """生成 ticket，发 modal 审批卡，挂起等待。返回 approve|reject|timeout。"""
    if default_deny and not goal_id:
        return "reject"  # 无 Goal 上下文时直接拒绝，不弹审批
    ticket = uuid.uuid4().hex
    ev = threading.Event()
    with _lock:
        _pending[ticket] = {"event": ev, "decision": None, "tool": tool, "args": args}
    try:
        from eventbus import publish_system
        publish_system("modal", {
            "kind": "agent_approval",
            "ticket": ticket,
            "tool": tool,
            "args_preview": _preview(tool, args),
            "summary": summary or f"小6请求执行工具 {tool}",
        }, source="policy_engine")
    except Exception as e:
        print(f"[policy] 审批弹窗发布失败（按拒绝处理）: {e}")
        with _lock:
            _pending.pop(ticket, None)
        return "reject"
    if not ev.wait(timeout):
        with _lock:
            _pending.pop(ticket, None)
        return "timeout"
    with _lock:
        rec = _pending.pop(ticket, {})
    decision = rec.get("decision") or "reject"
    if decision == "approve":
        approve_in_goal(goal_id, tool)
    return decision


def resolve(ticket: str, decision: str) -> bool:
    """POST /api/agent/approval 调用：唤醒挂起的执行。"""
    with _lock:
        rec = _pending.get(ticket)
        if not rec:
            return False
        rec["decision"] = decision
        rec["event"].set()
    return True


def set_never(tool: str, permanent: bool = True) -> None:
    with _lock:
        _never_store.add(tool)
        for _s in _session_approved.values():
            _s.discard(tool)
    if permanent:
        _save_store()


def _preview(tool: str, args: dict) -> dict:
    """脱敏后的参数预览（不依赖外部模块）。"""
    a = args or {}
    if tool == "run_shell":
        return {"command": str(a.get("command") or "")[:200]}
    if tool in ("file_read", "file_list", "file_write", "file_delete"):
        return {"path": a.get("path") or a.get("filename") or a.get("file_path") or ""}
    if tool in ("web_fetch", "browser_read"):
        return {"url": a.get("url") or a.get("link") or a.get("href") or ""}
    if tool == "web_search":
        return {"query": a.get("query") or a.get("q") or ""}
    return {"tool": tool}
