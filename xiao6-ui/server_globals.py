# -*- coding: utf-8 -*-
"""server_globals — Server Global State（R8-P0 恢复真实实现）

共享模块级基础设施（拆分自 server.py 的全局状态单一来源）。
server.py 与 server_handlers_* 均经本模块取用全局；**禁止**回退为宽松 stub：
  - _is_local_peer        —— 真实本机判定（回环地址集合），绝不恒为 True
  - _ACCESS_LOG_REDACT_RE —— 真实访问日志脱敏正则，绝不置 None
  - _CORS_ALLOWED_ORIGINS —— 真实 CORS 白名单（启动时由 _resolve_cors_origins 填充），绝不为 {"*"}
  - _REMOTE_FORBIDDEN     —— 真实远程会话禁用高危工具集合，绝不为 False
"""

import re
import threading

# Provider probe cache（仅白名单 127.0.0.1；spec §八）
_PROVIDER_PROBE_CACHE = {}

# 每日简报「仅推一次」去重锁：多 SSE 连接（或远程 Web 客户端多开）并发建立时，
# 串行化对 last_briefing_date 的读写，避免简报被双推。
BRIEFING_LOCK = threading.Lock()


def _sse_use_eventbus():
    """SSE 扇出是否走 EventBus（默认 ON，false 回退 SUBSCRIBERS 旧路径）。"""
    try:
        from eventbus import enabled

        return enabled()
    except Exception:
        return False


def _sse_put(q, payload):
    """EventBus 订阅回调：把事件载荷投入本连接的队列。"""
    try:
        q.put(payload)
    except Exception:
        pass


def _proactive_dnd_state() -> bool:
    """读取后端 NotificationPolicy 的权威 DND 状态（经 db.meta，单一来源）。"""
    try:
        import proactive_config as _pc

        return _pc.policy.is_dnd_enabled()
    except Exception:
        return False


# ---------- Phase C：远程访问安全 ----------
# 远程会话默认禁止的高危工具（run_shell/file_write/install/委托/工厂管理等）。
# 未显式配置 REMOTE_TOOL_WHITELIST 时，远程仅开放「安全默认」白名单（全部减去下表）。
_REMOTE_FORBIDDEN = {
    "run_shell", "session_state", "reset_session",
    "file_write", "file_make_dir", "file_delete", "file_rename",
    "install_software", "delegate_agent",
    "create_custom_tool", "delete_custom_tool",
}


def _remote_allowed_tools():
    """返回远程会话允许使用的工具名集合。"""
    import config
    from tools import TOOLS

    cfg = (config.REMOTE_TOOL_WHITELIST or "").strip()
    if cfg:
        return {x.strip() for x in cfg.split(",") if x.strip()}
    return {t["function"]["name"] for t in TOOLS if t["function"]["name"] not in _REMOTE_FORBIDDEN}


def _is_local_peer(peer):
    """本机判定：仅回环地址视为本地，其余一律按远程处理。"""
    return peer in ("127.0.0.1", "::1", "localhost", "0:0:0:0:0:0:0:1", "::ffff:127.0.0.1")


# 访问日志脱敏：请求行（self.requestline）会原样包含查询串，?token= 等敏感参数
# 若直接落盘/输出到 stderr 会造成凭证泄露。统一在 log_message 落盘前脱敏。
_ACCESS_LOG_REDACT_RE = re.compile(
    r"([?&](?:token|access[_-]?token|auth[_-]?token|secret|password|passwd|api[_-]?key|apikey)=)[^&\s\"']+",
    re.IGNORECASE,
)


def _hotspot_modal_payload(hs):
    """把结构化热点数据压缩为前端弹窗所需的最小字段。"""
    platforms = hs.get("platforms", {}) or {}
    PLATFORM_LABELS = {"douyin": "抖音", "xiaohongshu": "小红书", "wechat": "微信", "weibo": "微博"}
    out = {}
    for key, label in PLATFORM_LABELS.items():
        items = platforms.get(key, [])[:6]
        out[key] = {
            "label": label,
            "items": [
                {
                    "rank": it.get("rank"),
                    "text": it.get("text"),
                    "heat": it.get("heat"),
                    "url": it.get("url") or "",
                    "source": it.get("source") or "",
                }
                for it in items
            ],
        }
    return {"fetchedAt": hs.get("fetchedAt"), "stale": hs.get("stale"), "platforms": out}


# ---------- Phase 47.1：CORS 白名单（取代 "*"）----------
# 仅回显与绑定端口一致的 loopback / 显式绑定主机 Origin；
# 任意外部 Origin 一律不回显（杜绝 CSRF / 跨域数据泄露面）。
_CORS_ALLOWED_ORIGINS = set()


def _resolve_cors_origins(bind_host, port):
    """根据绑定网口计算允许的 CORS Origin 集合。"""
    origins = set()
    try:
        port = int(port)
    except Exception:
        port = 8000
    origins.add("http://127.0.0.1:%d" % port)
    origins.add("http://localhost:%d" % port)
    if bind_host in ("0.0.0.0", "", None):
        # 开放 LAN 时把本机非回环 IP 也纳入（仅当已配 REMOTE_ACCESS_TOKEN 才会走到此分支）
        try:
            import socket

            for info in socket.getaddrinfo(socket.gethostname(), None):
                ip = info[4][0]
                if ip not in ("127.0.0.1", "::1") and ":" not in ip:
                    origins.add("http://%s:%d" % (ip, port))
        except Exception:
            pass
    elif bind_host not in ("127.0.0.1", "localhost", "::1"):
        origins.add("http://%s:%d" % (bind_host, port))
    return origins


# 显式 __all__：`from server_globals import *` 只导入全局状态本身，
# 不泄漏模块级依赖（re / threading / config / TOOLS）。
__all__ = [
    "_PROVIDER_PROBE_CACHE",
    "_is_local_peer",
    "_sse_put",
    "_sse_use_eventbus",
    "_proactive_dnd_state",
    "_remote_allowed_tools",
    "_hotspot_modal_payload",
    "_resolve_cors_origins",
    "_ACCESS_LOG_REDACT_RE",
    "_REMOTE_FORBIDDEN",
    "_CORS_ALLOWED_ORIGINS",
    "BRIEFING_LOCK",
]
