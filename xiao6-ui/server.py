#!/usr/bin/env python3
"""
小6 · 本地指挥核心 · server.py（薄入口）
- 纯标准库（仅 TTS 用 edge-tts，lazy import）
- 托管界面 (index.html / styles.css / app.js)
- POST /api/chat  ->  function calling 闭环：调 Agnes -> 本地执行工具 -> 回填 -> 流式输出
- POST /api/speak ->  用 edge-tts 合成中文语音并返回 mp3
- GET  /api/health
- API Key 仅存于服务端（环境变量或同目录 .env），绝不暴露给前端
"""

import asyncio
import http.server
import io
import json
import os
import queue
import re
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError
from urllib.parse import parse_qs

import capabilities
import config
import data_manager
from asr import status as asr_status, transcribe_bytes
from config import CONTENT, PORT
from db import db_conn, get_memory_graph, save_turn
from focus import capture_foci
from geo_weather import get_geo, get_weather, reverse_geocode
from hotspots import get_hotspots
from llm import _urlopen_with_proxy, agnes_completion, resolve_provider
import provider_registry
from media import status as media_status

# Phase 10-C · 本地 Provider 可用性探测缓存（仅白名单 127.0.0.1；spec §八）
# 进程内内存 dict，存最近一次探测结果；禁扫描、禁任意远程探测。
_PROVIDER_PROBE_CACHE = {}
from memory import compress_memory
from context import build_context_prompt
from notes import (
    create_note,
    extract_daily_note,
    extract_persons,
    extract_profile,
    get_all_tags,
    get_backlinks,
    get_graph,
    get_note,
    get_notes,
    parse_md_links,
    parse_md_tags,
    search_notes,
)
from prefetch import start_prefetch_scheduler
from proactive import SUBSCRIBERS, SUBSCRIBERS_LOCK, flush_pending, make_daily_briefing, tick_loop

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
from self_check import run_self_check
from social import status as social_status
from sysmon import get_logs, get_sysmon


def _proactive_dnd_state() -> bool:
    """读取后端 NotificationPolicy 的权威 DND 状态（经 db.meta，单一来源）。"""
    try:
        import proactive_config as _pc

        return _pc.policy.is_dnd_enabled()
    except Exception:
        return False
from tasks import recover_tasks
from ai_core.lifecycle import lifecycle
from ai_core.execution import run as _execution_run
from tools import TOOL_FUNCS, TOOLS, detect_intents, run_fc_loop, select_tools, get_pending_video, clear_pending_video, strip_think_tags

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
    cfg = (config.REMOTE_TOOL_WHITELIST or "").strip()
    if cfg:
        return {x.strip() for x in cfg.split(",") if x.strip()}
    return {t["function"]["name"] for t in TOOLS if t["function"]["name"] not in _REMOTE_FORBIDDEN}


def _is_local_peer(peer):
    return peer in ("127.0.0.1", "::1", "localhost", "0:0:0:0:0:0:0:1", "::ffff:127.0.0.1")


# 访问日志脱敏：请求行（self.requestline）会原样包含查询串，?token= 等敏感参数
# 若直接落盘/输出到 stderr 会造成凭证泄露。统一在 log_message 落盘前脱敏。
_ACCESS_LOG_REDACT_RE = re.compile(
    r"([?&](?:token|access[_-]?token|auth[_-]?token|secret|password|passwd|api[_-]?key|apikey)=)[^&\s\"']+",
    re.IGNORECASE,
)
from wakeword import get_status as wakeword_status, start as wakeword_start, stop as wakeword_stop


# ---------- HTTP Handler ----------
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
        port = 8010
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


from server_globals import *
from server_globals import _PROVIDER_PROBE_CACHE, _is_local_peer, _sse_put, _sse_use_eventbus, _proactive_dnd_state, _remote_allowed_tools, _hotspot_modal_payload, _resolve_cors_origins, _ACCESS_LOG_REDACT_RE, _REMOTE_FORBIDDEN, _CORS_ALLOWED_ORIGINS, BRIEFING_LOCK
import server_handlers
from server_handlers import SystemMixin, MemoryMixin, TasksMixin, ChatMixin, CapabilityMixin, SocialMixin, SessionTraceMixin



class Handler(BaseHTTPRequestHandler, SystemMixin, MemoryMixin, TasksMixin, ChatMixin, CapabilityMixin, SocialMixin, SessionTraceMixin):
    protocol_version = "HTTP/1.1"

    def _send(self, code, body, ctype="application/json; charset=utf-8", headers=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", self._cors_origin())
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _cors_origin(self):
        """返回当前请求应回显的 CORS Origin（严格白名单）。"""
        origin = (self.headers.get("Origin") or "").strip()
        if origin and origin in _CORS_ALLOWED_ORIGINS:
            return origin
        # 安全默认：主回环 Origin（绝不回显任意外部 Origin）
        return "http://127.0.0.1:%d" % int(getattr(config, "PORT", 8010))

    def _remote_gate(self):
        """远程访问门控：非本机请求须经 Bearer Token 校验（REMOTE_ACCESS_TOKEN）。
        返回 True 放行；返回 False 表示已发送拒绝响应。"""
        peer = (self.client_address or ("",))[0]
        if _is_local_peer(peer):
            return True
        token = config.REMOTE_ACCESS_TOKEN
        if not token:
            # 未配置远程 token：彻底禁止任何非本机访问
            self._send(403, json.dumps(
                {"error": "仅允许本机访问；如需远程访问请在设置中配置 REMOTE_ACCESS_TOKEN"}, ensure_ascii=False))
            return False
        # 校验 Bearer Token（支持 Authorization 头或 ?token= 查询参数）
        auth = self.headers.get("Authorization", "") or ""
        if auth.startswith("Bearer "):
            provided = auth[7:].strip()
        else:
            provided = ""
        if not provided:
            try:
                from urllib.parse import parse_qs
                q = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
                provided = (q.get("token") or [""])[0]
            except Exception:
                provided = ""
        if provided and provided == token:
            return True
        self._send(401, json.dumps({"error": "远程访问需要有效的 Bearer Token"}, ensure_ascii=False))
        return False

    def do_GET(self):
        if not self._remote_gate():
            return
        path = self.path.split("?", 1)[0]
        qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        if path in ("/", "/index.html"):
            return self._serve_file("index.html")
        if path == "/api/health":
            # liveness：仅表进程存活；ok 取最近一次自检缓存，不触发外部探测（P0.2 修复 RC-4）
            cached = lifecycle.self_check_result
            key_ok = bool(config.AGNES_KEY)
            return self._send(
                200,
                json.dumps(
                    {
                        "status": "alive",
                        "ok": bool(key_ok and cached and cached.get("ok")),
                        "model": config.AGNES_MODEL,
                        "provider": config.AGNES_PROVIDER,
                        "tts_backend": config.TTS_BACKEND,
                        "ai_name": config.AI_DISPLAY_NAME,
                        "theme": config.THEME,
                        "memory_graph": config.MEMORY_GRAPH_ENABLED,
                        "key_present": key_ok,
                        "tools": [t["function"]["name"] for t in TOOLS],
                        "features": {
                            "premium_ui": config.FEATURE_PREMIUM_UI,
                            "knowledge_platform": config.FEATURE_KNOWLEDGE_PLATFORM,
                            "proactive_v2": config.FEATURE_PROACTIVE_V2,
                            "multi_device": config.FEATURE_MULTI_DEVICE,
                            "always_on": config.FEATURE_ALWAYS_ON,
                            "cross_device": config.FEATURE_CROSS_DEVICE,
                            "mobile_companion": config.FEATURE_MOBILE_COMPANION,
                            "calendar_sense": config.FEATURE_CALENDAR_SENSE,
                            "app_focus": config.FEATURE_APP_FOCUS,
                            "clipboard_sense": config.FEATURE_CLIPBOARD_SENSE,
                        },
                        "self_check": cached,
                    },
                    ensure_ascii=False,
                ),
            )
        if path == "/api/startup_diagnosis":
            # Phase 22：启动自检报告（后台已跑，结果缓存；force=1 重算）
            try:
                import self_diagnosis
                force = qs.get("force", ["0"])[0] in ("1", "true")
                rep = self_diagnosis.get_report(force=force)
                return self._send(200, json.dumps(rep.to_dict(), ensure_ascii=False))
            except Exception as e:
                return self._send(200, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/ready":
            # readiness：服务是否完成初始化、功能是否就绪（P0.2 新增）
            key_ok = bool(config.AGNES_KEY)
            cached = lifecycle.self_check_result
            ready = lifecycle.is_ready
            if cached is None:
                return self._send(
                    200,
                    json.dumps(
                        {"ok": False, "ready": ready, "key_present": key_ok, "degraded": False, "self_check": None},
                        ensure_ascii=False,
                    ),
                )
            ok = bool(key_ok and cached.get("ok"))
            return self._send(
                200,
                json.dumps(
                    {
                        "ok": ok,
                        "ready": ready,
                        "key_present": key_ok,
                        "degraded": not ok,
                        "self_check": cached,
                    },
                    ensure_ascii=False,
                ),
            )
        if path == "/api/config":
            return self._handle_config_get()
        if path == "/api/providers/probe":
            return self._handle_providers_probe_get()
        if path == "/api/proactive/status":
            return self._handle_proactive_status()
        if path == "/api/version":
            return self._send(
                200,
                json.dumps(
                    {
                        "ok": True,
                        "app_name": config.AI_DISPLAY_NAME,
                        "version": config.APP_VERSION,
                        "check_url": "https://github.com/AGI-Xiao6/Xiao6/releases/latest",
                    },
                    ensure_ascii=False,
                ),
            )
        if path == "/api/alert-config":
            return self._handle_alert_config_get()
        if path == "/api/memory":
            conn = db_conn()
            prof = conn.execute("SELECT key,value,updated FROM profile ORDER BY key").fetchall()
            note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            log_count = conn.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0]
            srow = conn.execute("SELECT summary FROM memory_summary WHERE id=1").fetchone()
            summary = (srow[0] if srow and srow[0] else "").strip()
            rem_rows = conn.execute("SELECT due_ts,content,done FROM reminders ORDER BY due_ts ASC").fetchall()
            reminders = [{"due": d, "content": c, "done": bool(done)} for d, c, done in rem_rows]
            conn.close()
            return self._send(
                200,
                json.dumps(
                    {
                        "profile": [{"key": k, "value": v, "updated": u} for k, v, u in prof],
                        "note_count": note_count,
                        "log_count": log_count,
                        "summary": summary,
                        "reminders": reminders,
                    },
                    ensure_ascii=False,
                ),
            )
        if path == "/api/memory/important-dates":
            return self._handle_important_dates_get()
        if path == "/api/memory/backfill":
            return self._handle_memory_backfill()
        if path == "/api/memory/conversations":
            return self._handle_conversations_get()
        if path == "/api/chat/history":
            return self._handle_chat_history()
        if path == "/api/stream":
            return self._handle_stream()
        if path == "/api/data/export":
            return self._handle_data_export()
        if path == "/api/geo":
            return self._send(200, json.dumps(get_geo() or {"location": None, "weather": None}, ensure_ascii=False))
        if path == "/api/geo/reverse":
            try:
                lat = qs.get("lat", [""])[0].strip()
                lon = qs.get("lon", [""])[0].strip()
                rev = reverse_geocode(lat, lon)
                if rev:
                    return self._send(200, json.dumps(rev, ensure_ascii=False))
                return self._send(200, json.dumps({"display": None, "lat": lat, "lon": lon}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/agent/state":
            return self._handle_agent_state()
        if path == "/api/hud/state":
            return self._handle_hud_state()
        if path == "/api/boot/state":
            # Phase 34 Task 4：统一启动就绪状态（STARTING→BACKEND_READY→AI_READY→AVATAR_READY→READY）
            try:
                import beta_boot
                return self._send(200, json.dumps(beta_boot.status(), ensure_ascii=False))
            except Exception as e:
                return self._send(200, json.dumps({"state": "STARTING", "error": str(e)}, ensure_ascii=False))
        if path == "/api/hud/config":
            return self._handle_hud_config()
        if path == "/api/hotspots":
            return self._handle_hotspots()
        if path == "/api/weather":
            return self._handle_weather()
        if path == "/api/briefing":
            return self._handle_briefing()
        if path == "/api/sysmon":
            return self._send(200, json.dumps(get_sysmon(), ensure_ascii=False))
        if path == "/api/logs":
            return self._send(200, json.dumps(get_logs(), ensure_ascii=False))
        if path.startswith("/api/notes"):
            return self._handle_notes()
        if path == "/api/tasks":
            return self._handle_tasks()
        if path.startswith("/api/goals"):
            # P0-B · 只读目标快照。复用 goals.py，不复制数据库逻辑。
            # 仅 GET；写操作一律经 Intent Gateway → Runtime，此处不暴露任何写/状态机。
            try:
                import goals as _goals

                if path == "/api/goals" or path == "/api/goals/":
                    _status = qs.get("status", [""])[0].strip() or None
                    _horizon = qs.get("horizon", [""])[0].strip() or None
                    try:
                        _limit = int(qs.get("limit", ["50"])[0])
                    except (TypeError, ValueError):
                        _limit = 50
                    items = _goals.list_goals(status=_status, horizon=_horizon, limit=_limit)
                    return self._send(
                        200,
                        json.dumps([g.to_dict() for g in items], ensure_ascii=False),
                    )
                # /api/goals/<id> 单条
                _sub = path[len("/api/goals/"):].strip("/")
                if _sub.isdigit():
                    g = _goals.get_goal(int(_sub))
                    if g:
                        return self._send(200, json.dumps(g.to_dict(), ensure_ascii=False))
                    return self._send(404, json.dumps({"error": "goal not found"}, ensure_ascii=False))
                return self._send(400, json.dumps({"error": "bad goals path"}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/audit":
            return self._handle_audit()
        if path == "/api/wakeword":
            return self._handle_wakeword()
        if path.startswith("/api/memories"):
            return self._handle_memories()
        if path == "/api/external":
            return self._handle_external()
        if path == "/api/doc":
            return self._handle_doc()
        if path == "/api/memory_audit":
            return self._handle_memory_audit()
        if path == "/api/learnings":
            return self._handle_learnings()
        if path == "/api/sessions":
            return self._handle_sessions_get()
        if path == "/api/session":
            if self.command == "GET":
                return self._handle_session_get()
            elif self.command == "POST":
                return self._handle_session_post()
            elif self.command == "DELETE":
                return self._handle_session_delete()
            return self._send(405, json.dumps({"error": "method not allowed"}))
        if path == "/api/trace":
            return self._handle_trace_get()
        if path == "/api/activity":
            return self._handle_activity_get()
        if path == "/api/social/inbound":
            return self._handle_social_inbound_get()
        if path == "/api/system-prompt":
            try:
                return self._send(200, json.dumps({"system_prompt": build_context_prompt()}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/capabilities":
            try:
                items = capabilities.capability_details()
                return self._send(
                    200,
                    json.dumps(
                        {"ok": True, "count": len(items), "items": items},
                        ensure_ascii=False,
                    ),
                )
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        # —— Phase 23 · Capability OS 统一能力目录（GET，只读）——
        if path == "/api/capability_os/catalog":
            try:
                import capability_os
                return self._send(200, json.dumps(capability_os.catalog_view(), ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        # —— Phase 40 · Capability Foundation 统一视图（GET，只读；真相源出口）——
        if path == "/api/capability_foundation":
            try:
                import capability_os
                return self._send(200, json.dumps(capability_os.foundation_view(), ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        # —— Phase 24 · Proactive Agent（GET，只读状态；只建议不执行）——
        if path == "/api/proactive_agent/status":
            try:
                import proactive_agent
                return self._send(200, json.dumps(proactive_agent.get_status(), ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        # —— Phase 30 · Self Awareness Loop（GET，只读状态；只认知不执行）——
        if path == "/api/self_awareness/status":
            try:
                import self_awareness
                return self._send(200, json.dumps(self_awareness.get_status(), ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/user_model":
            try:
                from cognitive.user_model import load_user_model, canonical_project, is_empty

                data = load_user_model()
                cproj, cconf = canonical_project()
                return self._send(200, json.dumps({
                    "ok": True,
                    "empty": is_empty(data),
                    "model": data,
                    "canonical_project": cproj,
                    "canonical_confidence": cconf,
                }, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/personal_context":
            # Phase 18 · Personal Context Engine（只读聚合视图，现算现取不落盘）
            if not getattr(config, "FEATURE_PERSONAL_CONTEXT", True):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "Personal Context 未启用"}))
            return self._handle_os_bridge("personal_context")
        if path == "/api/personal_ai":
            # Phase 37.2 · Personal AI 统一画像（确认/纠正/蒸馏/双源对齐；读聚合视图）
            if not getattr(config, "FEATURE_PERSONAL_AI", True):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "Personal AI 未启用"}))
            try:
                import personal_ai
                return self._send(200, json.dumps(personal_ai.get_personal_ai_view(), ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/episodes":
            try:
                from cognitive.episodic import list_episodes

                limit = int(qs.get("limit", ["20"])[0] or "20")
                return self._send(200, json.dumps({
                    "ok": True,
                    "episodes": list_episodes(limit),
                }, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/asr/status":
            # 按需触发本地模型加载（首次会下载 ~700MB 模型），仅当用户主动探测时调用
            return self._send(200, json.dumps(asr_status(), ensure_ascii=False))
        # —— Phase 15/16/17 · OS Bridge（薄委托，逻辑全在 os_bridge 与既有内核里）——
        if path == "/api/selfcheck":
            return self._handle_os_bridge("selfcheck")
        if path == "/api/vision/displays":
            return self._handle_os_bridge("vision_displays")
        if path == "/api/action/capabilities":
            return self._handle_os_bridge("action_capabilities")
        if path == "/api/action/observe":
            return self._handle_os_bridge("action_observe")
        if path == "/api/knowledge":
            try:
                import knowledge

                return self._send(
                    200,
                    json.dumps(
                        {"docs": knowledge.list_docs() or [], "stats": knowledge.stats() or {}},
                        ensure_ascii=False,
                    ),
                )
            except Exception as e:
                # R8-UI：知识后端未就绪（S79.7 stub 缺口）时优雅返回空列表，不 500
                #（UI fetchSnapshot 契约：{docs: [...]}）
                return self._send(
                    200,
                    json.dumps({"docs": [], "stats": {}, "error": str(e)}, ensure_ascii=False),
                )
        if path == "/api/devices":
            if not getattr(config, "FEATURE_MULTI_DEVICE", True):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "多端同步未启用"}))
            return self._handle_devices_get()
        if path == "/api/always-on/status":
            if not getattr(config, "FEATURE_ALWAYS_ON", False):
                return self._send(200, json.dumps({"ok": True, "enabled": False, "running": False}, ensure_ascii=False))
            return self._handle_always_on_status()
        if path == "/api/cross-device/status":
            if not getattr(config, "FEATURE_CROSS_DEVICE", False):
                return self._send(200, json.dumps({"ok": True, "enabled": False, "total": 0, "pending": 0, "claimed": 0}, ensure_ascii=False))
            return self._handle_cross_device_status()
        if path == "/api/mobile/briefing":
            if not getattr(config, "FEATURE_MOBILE_COMPANION", False):
                return self._send(200, json.dumps({"ok": True, "enabled": False, "briefing": None}, ensure_ascii=False))
            return self._handle_mobile_briefing()
        if path == "/api/calendar/events":
            if not getattr(config, "FEATURE_CALENDAR_SENSE", False):
                return self._send(200, json.dumps({"ok": True, "enabled": False, "events": []}, ensure_ascii=False))
            return self._handle_calendar_events()
        if path == "/api/calendar/next":
            if not getattr(config, "FEATURE_CALENDAR_SENSE", False):
                return self._send(200, json.dumps({"ok": True, "enabled": False, "next": None}, ensure_ascii=False))
            return self._handle_calendar_next()
        if path == "/api/focus/app":
            if not getattr(config, "FEATURE_APP_FOCUS", False):
                return self._send(200, json.dumps({"ok": True, "enabled": False, "focus": None}, ensure_ascii=False))
            return self._handle_focus_app()
        if path == "/api/clipboard/history":
            if not getattr(config, "FEATURE_CLIPBOARD_SENSE", False):
                return self._send(200, json.dumps({"ok": True, "enabled": False, "history": []}, ensure_ascii=False))
            return self._handle_clipboard_history()
        # —— Phase 20 · Computer Perception（只读 GET，只建 Eyes 不建 Hands）——
        if path == "/api/perception":
            if not getattr(config, "FEATURE_PERCEPTION", True):
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled", "error": "Computer Perception 未启用"}, ensure_ascii=False))
            try:
                _scope = (qs.get("scope", ["window"])[0] or "window").strip()
                if _scope not in ("window", "full"):
                    _scope = "window"
                _ocr = qs.get("ocr", ["1"])[0].lower() not in ("0", "false", "no")
                import perception

                return self._send(200, json.dumps(perception.observe(scope=_scope, with_ocr=_ocr), ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/perception/screen":
            if not getattr(config, "FEATURE_PERCEPTION", True):
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled", "error": "Computer Perception 未启用"}, ensure_ascii=False))
            try:
                import perception

                return self._send(200, json.dumps({"ok": True, "screen": perception.screen_observer.screen_info()}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/perception/window":
            if not getattr(config, "FEATURE_PERCEPTION", True):
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled", "error": "Computer Perception 未启用"}, ensure_ascii=False))
            try:
                import perception

                return self._send(200, json.dumps({
                    "ok": True,
                    "active_window": perception.window_detector.active_window(),
                    "windows": perception.window_detector.list_windows(limit=40),
                }, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/perception/ocr":
            if not getattr(config, "FEATURE_PERCEPTION", True):
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled", "error": "Computer Perception 未启用"}, ensure_ascii=False))
            if not getattr(config, "FEATURE_PERCEPTION_OCR", True):
                return self._send(200, json.dumps({"ok": False, "reason_code": "ocr_disabled", "error": "OCR 子开关未启用"}, ensure_ascii=False))
            try:
                _scope = (qs.get("scope", ["window"])[0] or "window").strip()
                if _scope not in ("window", "full"):
                    _scope = "window"
                import perception

                return self._send(200, json.dumps(perception.ocr_engine.read_screen(scope=_scope, with_cache=True), ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/perception/describe":
            if not getattr(config, "FEATURE_PERCEPTION", True):
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled", "error": "Computer Perception 未启用"}, ensure_ascii=False))
            try:
                import perception

                return self._send(200, json.dumps({"ok": True, "text": perception.describe(scope="window")}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/perception/status":
            if not getattr(config, "FEATURE_PERCEPTION", True):
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled", "error": "Computer Perception 未启用"}, ensure_ascii=False))
            try:
                import perception

                return self._send(200, json.dumps({"ok": True, "status": perception.backend_status()}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        # —— Phase 20.5 · Memory Truth Layer（只读 GET）——
        if path == "/api/memory/truth":
            if not getattr(config, "FEATURE_MEMORY_TRUTH", True):
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled",
                                                   "error": "Memory Truth Layer 未启用"}, ensure_ascii=False))
            try:
                from memory_intelligence import verify_and_tag
                # R8-UI：移除局部 `from db import db_conn`（会遮蔽 do_GET 全函数的 db_conn，
                # 导致 GET /api/memory 分支 UnboundLocalError）；模块级已导入 db_conn。
                stats = verify_and_tag(dry_run=True)
                conn = db_conn()
                by_status = {}
                by_source = {}
                try:
                    for st, n in conn.execute("SELECT status, COUNT(*) FROM memories GROUP BY status"):
                        by_status[st or "active"] = n
                    for sr, n in conn.execute("SELECT source, COUNT(*) FROM memories GROUP BY source"):
                        by_source[sr or "inference"] = n
                finally:
                    conn.close()
                return self._send(200, json.dumps({
                    "ok": True,
                    "stats": stats,
                    "by_status": by_status,
                    "by_source": by_source,
                    "feature_memory_truth": True,
                }, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path.startswith("/static/"):
            return self._serve_file(path[len("/static/") :])
        if path.startswith("/xiao6-space"):
            return self._serve_file("xiao6-space" + path[len("/xiao6-space"):])
        if self._resolve_static(path):
            return self._serve_file(path.lstrip("/"))
        self._send(404, json.dumps({"error": "not found"}))

    def _resolve_static(self, name):
        """R8 Release Closure · 静态文件安全解析（canonical path 校验）：
        - 禁止任何 ".." 路径分量 / 绝对路径 / NUL（防路径穿越）
        - 禁止 .env / .git（凭证与仓库元数据）
        - 禁止服务目录外文件（realpath 归一符号链接/大小写）
        - RC2：改用 os.path.commonpath 做 canonical 边界校验（等价更严格），
          symlink 经 realpath 归一后越界同样被拒。
        返回绝对路径；非法返回 None（调用方回 404）。"""
        name = (name or "").replace("\\", "/").lstrip("/")
        if not name or name.startswith("/") or "\x00" in name:
            return None
        if ".." in name.split("/"):
            return None
        base = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))
        fp = os.path.realpath(os.path.join(base, name))
        try:
            if os.path.commonpath([base, fp]) != base:
                return None
        except ValueError:
            return None
        bn = os.path.basename(fp)
        if bn == ".env" or ".env" in bn or ".git" in bn:
            return None
        if not os.path.isfile(fp):
            return None
        return fp

    def _send_head(self, code, ctype="application/json; charset=utf-8", clen=0):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        if clen:
            self.send_header("Content-Length", str(clen))
        self.end_headers()

    def _serve_file_head(self, name):
        fp = self._resolve_static(name)
        if not fp:
            return self._send_head(404)
        ext = os.path.splitext(name)[1].lower()
        clen = os.path.getsize(fp)
        self._send_head(200, CONTENT.get(ext, "application/octet-stream"), clen)

    def do_HEAD(self):
        if not self._remote_gate():
            return
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            return self._serve_file_head("index.html")
        if path.startswith("/api/"):
            return self._send_head(200)
        if path.startswith("/static/"):
            return self._serve_file_head(path[len("/static/") :])
        if path.startswith("/xiao6-space"):
            return self._serve_file_head("xiao6-space" + path[len("/xiao6-space"):])
        if self._resolve_static(path):
            return self._serve_file_head(path.lstrip("/"))
        self._send_head(404)

    def _serve_file(self, name):
        fp = self._resolve_static(name)
        if not fp:
            return self._send(404, json.dumps({"error": "missing " + name}))
        ext = os.path.splitext(name)[1].lower()
        with open(fp, "rb") as f:
            data = f.read()
        self._send(200, data, CONTENT.get(ext, "application/octet-stream"))

    def do_POST(self):
        if not self._remote_gate():
            return
        ppath = self.path.split("?", 1)[0]  # 去掉查询串后再路由（与 do_GET 一致）
        # R8 Release Closure · API 基础安全收口：
        # 这三个端点必须带 application/json Content-Type，且 Origin 必须命中 CORS 白名单
        # （浏览器跨站表单只能发 text/plain / form-urlencoded / multipart，无法伪造 JSON 头）
        if ppath in self._JSON_POST_ENDPOINTS:
            _denied = self._require_json_post()
            if _denied is not None:
                return _denied
        if ppath == "/api/chat":
            return self._handle_chat()
        if ppath == "/api/speak":
            return self._handle_speak()
        if ppath == "/api/config":
            return self._handle_config_post()
        if ppath == "/api/providers/probe":
            return self._handle_providers_probe_post()
        if ppath == "/api/proactive/dnd":
            return self._handle_proactive_dnd()
        if ppath == "/api/alert-config":
            return self._handle_alert_config_post()
        if ppath == "/api/models":
            return self._handle_models()
        if ppath == "/api/test-llm":
            return self._handle_test_llm()
        if ppath == "/api/asr":
            return self._handle_asr_post()
        if ppath == "/api/transcribe":
            return self._handle_transcribe_post()
        if ppath == "/api/kws":
            return self._handle_kws()
        if ppath == "/api/social/inbound":
            return self._handle_social_inbound_post()
        if ppath == "/api/sessions":
            return self._handle_sessions_get()
        if ppath == "/api/session":
            return self._handle_session_post()
        if ppath == "/api/trace":
            return self._handle_trace_get()
        if ppath == "/api/activity":
            return self._handle_activity_get()
        if ppath == "/api/knowledge":
            return self._handle_knowledge()
        if ppath == "/api/devices":
            if not getattr(config, "FEATURE_MULTI_DEVICE", True):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "多端同步未启用"}))
            return self._handle_devices_post()
        if ppath == "/api/always-on/control":
            if not getattr(config, "FEATURE_ALWAYS_ON", False):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "常驻伴随未启用"}))
            return self._handle_always_on_control()
        if ppath == "/api/boot/avatar-ready":
            # Phase 34 Task 4：桌面数字人窗口就绪上报 → 推进统一就绪状态到 AVATAR_READY/READY
            try:
                import beta_boot
                beta_boot.mark_avatar_ready()
                return self._send(200, json.dumps({"ok": True, "state": beta_boot.status()["state"]}, ensure_ascii=False))
            except Exception as e:
                return self._send(200, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if ppath == "/api/cross-device/relay":
            if not getattr(config, "FEATURE_CROSS_DEVICE", False):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "跨端接力未启用"}))
            return self._handle_cross_device_relay()
        if ppath == "/api/mobile/reminder":
            if not getattr(config, "FEATURE_MOBILE_COMPANION", False):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "移动伴随端未启用"}))
            return self._handle_mobile_reminder()
        if ppath == "/api/mobile/chat":
            if not getattr(config, "FEATURE_MOBILE_COMPANION", False):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "移动伴随端未启用"}))
            return self._handle_mobile_chat()
        if ppath == "/api/focus/window":
            if not getattr(config, "FEATURE_APP_FOCUS", False):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "应用焦点未启用"}))
            return self._handle_focus_window()
        if ppath == "/api/clipboard/clear":
            if not getattr(config, "FEATURE_CLIPBOARD_SENSE", False):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "剪贴板监听未启用"}))
            return self._handle_clipboard_clear()
        if ppath == "/api/memory/backfill":
            return self._handle_memory_backfill()
        if ppath.startswith("/api/notes"):
            return self._handle_notes_post()
        if ppath.startswith("/api/memories"):
            return self._handle_memories_post()
        if ppath == "/api/memory/important-dates":
            return self._handle_important_dates_post()
        if ppath == "/api/memory/write":
            return self._handle_memory_write()
        if ppath == "/api/memory/query":
            return self._handle_memory_query()
        if ppath == "/api/memory/confirm":
            return self._handle_memory_confirm()
        if ppath == "/api/data/import":
            return self._handle_data_import()
        if ppath == "/api/agent/goal":
            return self._handle_agent_goal()
        if ppath == "/api/agent/intent":
            return self._handle_agent_intent()
        if ppath == "/api/agent/approval":
            return self._handle_agent_approval()
        # —— Phase 16/17 · OS Bridge ——
        if ppath == "/api/vision/capture":
            return self._handle_vision_capture()
        if ppath == "/api/action/plan":
            return self._handle_action_plan()
        if ppath == "/api/action/execute":
            return self._handle_action_execute()
        # —— Phase 23 · Capability OS（只读/咨询层，绝不执行任何能力）——
        if ppath == "/api/capability_os/match":
            return self._handle_capability_match()
        if ppath == "/api/capability_os/plan":
            return self._handle_capability_plan()
        # —— Phase 24 · Proactive Agent：手动触发一轮观测（只建议，不执行）——
        if ppath == "/api/proactive_agent/run":
            return self._handle_proactive_run()
        # —— Phase 30 · Self Awareness Loop：手动触发一轮认知（只建议，不执行）——
        if ppath == "/api/self_awareness/run":
            return self._handle_self_awareness_run()
        # —— Phase 30 · Self Awareness Loop：人工审批（只改状态，不执行）——
        if ppath == "/api/self_awareness/decide":
            return self._handle_self_awareness_decide()
        return self._send(404, json.dumps({"error": "unknown"}))

    # —— Phase 23 · Capability OS 薄处理器（只读/咨询，不执行）——
    _JSON_POST_ENDPOINTS = {"/api/agent/goal", "/api/agent/intent", "/api/chat"}

    def _require_json_post(self):
        """R8 Release Closure · 防跨站/畸形 POST（返回 None=放行，否则为已发送的响应）。"""
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return self._send(
                415,
                json.dumps({"error": "Content-Type 必须为 application/json"}, ensure_ascii=False),
            )
        origin = (self.headers.get("Origin") or "").strip()
        if origin and origin not in _CORS_ALLOWED_ORIGINS:
            return self._send(
                403, json.dumps({"error": "跨站请求被拒绝"}, ensure_ascii=False),
            )
        return None

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw = b""
            while len(raw) < length:
                chunk = self.rfile.read(length - len(raw))
                if not chunk:
                    break
                raw += chunk
            if not raw:
                raw = self.rfile.read(1 << 20)
            return json.loads(raw.decode("utf-8", "replace") or "{}")
        except Exception as e:
            return {"_error": str(e)}

def main():
    port = PORT
    # ── 日志统一 + 轮转（logs/xiao6.log，5MB×3；logging 模块输出统一入文件）──
    try:
        import logging
        from logging.handlers import RotatingFileHandler

        os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"), exist_ok=True)
        _lf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "xiao6.log")
        _rh = RotatingFileHandler(_lf, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        _rh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logging.basicConfig(level=logging.INFO, handlers=[_rh], force=True)
    except Exception as _le:
        print(f"[日志] 配置失败（不影响启动）: {_le}")
    # ── Phase 47.1：网络边界加固（默认仅本机；0.0.0.0 须配 REMOTE_ACCESS_TOKEN）──
    bind_host = (getattr(config, "BIND_HOST", "127.0.0.1") or "127.0.0.1").strip()
    if bind_host == "0.0.0.0" and not config.REMOTE_ACCESS_TOKEN:
        print("[SECURITY] BIND_HOST=0.0.0.0 但未配置 REMOTE_ACCESS_TOKEN，回退为 127.0.0.1（仅本机可访问）。")
        bind_host = "127.0.0.1"
    _CORS_ALLOWED_ORIGINS.clear()
    _CORS_ALLOWED_ORIGINS.update(_resolve_cors_origins(bind_host, port))
    if bind_host == "0.0.0.0":
        print(f"[网络] 监听所有网口 http://0.0.0.0:{port}（远程访问已要求 REMOTE_ACCESS_TOKEN）")
    else:
        print(f"[网络] 仅监听本机 http://{bind_host}:{port}")
    if not config.AGNES_KEY:
        print("[WARN] 未检测到 AGNES_API_KEY，请在 .env 或设置面板中配置后重启。")
    else:
        # Production: just confirm presence, no details
        print("[AGNES_CONFIG] source=.env present=true status=OK")
    db_conn().close()
    n = recover_tasks()  # Phase 3.1：把上次 running 被中断的任务翻回 open，使其可续跑
    if n:
        print(f"[恢复] {n} 个被中断的多步任务已标记为可续。")
    # 出站代理支持：若配置了代理地址，全局安装 opener，使所有 urllib 调用
    # （Agnes 模型/启动自检）自动走代理。本机访问 apihub.agnes-ai.com 需经本地 Clash。
    _proxy = os.environ.get("XIAO6_PROXY_URL") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
    if _proxy:
        import urllib.request as _urllib

        _urllib.install_opener(_urllib.build_opener(_urllib.ProxyHandler({"http": _proxy, "https": _proxy})))
        print(f"[代理] 已启用全局代理 -> {_proxy}")
    print(f"小6 指挥核心启动中 ->  http://localhost:{port}")
    print(f"模型: {config.AGNES_MODEL}  |  提供商: {config.AGNES_PROVIDER}  |  工具: {', '.join(TOOL_FUNCS.keys())}")
    # 知识库：启动即扫描 + 建索引 + 启用文件 watcher（修复：此前仅在请求时懒加载，watcher 从未激活）
    try:
        import knowledge

        knowledge.load()
        print(f"[知识] 已加载 {knowledge.stats().get('docs', 0)} 篇文档，watcher 已启用。")
    except Exception as e:
        print(f"[知识] 加载失败（不影响核心启动）: {e}")

    # ── P0.1：启动自检改为后台异步，避免阻塞端口绑定（修复 RC-2）──
    # 端口在下方 serve_forever() 立即监听；自检在后台线程跑，完成后置位 lifecycle 就绪标志。
    # （原 _async_self_check 已抽离至 ai_core.lifecycle.Lifecycle.run_boot_self_check）
    lifecycle.run_boot_self_check()
    threading.Thread(target=tick_loop, daemon=True).start()
    print("主动智能（D 期）心跳已启动：到期提醒 + 每日简报。")
    threading.Thread(target=get_geo, daemon=True).start()  # 预热定位/天气缓存
    print("定位 & 天气采集已后台预热。")
    threading.Thread(target=_warmup_embed, daemon=True).start()  # 向量语义 RAG 模型预热 + 全量回填
    start_prefetch_scheduler()  # Phase 2：ACI 预热缓存（天气/新闻定时预取，模型醒来即用）
    print("ACI 预热缓存调度已启动（天气/新闻定时预取）。")
    # Phase 8：语音唤醒词常驻监听（KWS 默认开启时，后端启动即监听麦克风）
    if config.XIAO6_KWS_ENABLED.lower() in ("1", "true", "yes"):
        try:
            def _on_wake(transcript):
                """唤醒词命中后，自动开启语音对话模式。"""
                print(f"[KWS] 唤醒词命中: {transcript}")
                from eventbus import publish_system
                publish_system("wakeword_detected", {
                    "transcript": transcript,
                }, source="wakeword")
            wakeword_start(detect_callback=_on_wake)
            print("[KWS] 常驻监听已启动")
        except Exception as e:
            print(f"[KWS] 启动失败（非致命）: {e}")
    # 中文唤醒词检测（kws.py）：前端语音循环中每段断句后 POST /api/kws 判定；
    # openwakeword（wakeword.py）作为英文 "hey jarvis" fallback 仍由上方常驻监听承载。
    if config.XIAO6_KWS_ENABLED.lower() in ("1", "true", "yes"):
        try:
            import kws as _kws  # noqa: F401（确认模块可加载，/api/kws 已就绪）

            def _kws_loop():
                """后台线程：持续检测 KWS（预留扩展位，当前由前端 /api/kws 驱动）。"""
                from asr import transcribe_bytes  # noqa: F401（复用现有 ASR）
                # 复用现有麦克风输入（如果有）；否则跳过，等待前端调用 /api/kws
                pass

            # 启动 KWS 后台检测（如果麦克风可用）
            # 注意：如果前端已用 _voiceLoop，这里只需提供 API 端点
            print("[KWS] 中文唤醒词检测已就绪（需前端配合调用 /api/kws）")
        except Exception as e:
            print(f"[KWS] 启动失败（非致命）: {e}")
    # 社交接收端：飞书长连接（可选，依赖缺失/未开启则静默跳过，不影响主链路）
    try:
        import social_feishu_ws

        social_feishu_ws.start_feishu_ws()
    except Exception as e:
        print(f"[社交接收] 飞书长连接启动跳过：{e}")
    # Phase 8：Agent Runtime（编排状态机）— FEATURE_AGENT_RUNTIME 门控，默认关闭
    if getattr(config, "FEATURE_AGENT_RUNTIME", False):
        try:
            import agent_runtime
            agent_runtime.runtime.start()
            print("[Agent Runtime] 已启动（编排状态机 + Policy Engine + Reflector）。")
        except Exception as e:
            print(f"[Agent Runtime] 启动失败（已跳过）: {e}")
    # Phase 21：Computer Action（手）— 启动期把模块级单例 PermissionGuard 原地替换为
    # 白名单受限的真实执行器/验证器，使 Agent 闭环路径与生产 REST 路径引用同一 Guard（修复 G8/R1）。
    if getattr(config, "FEATURE_COMPUTER_ACTION", True):
        try:
            import os_bridge
            os_bridge._get_guard()
            print("[Computer Action] 白名单 Guard 已在启动时挂载（Hand ready）。")
        except Exception as e:
            print(f"[Computer Action] Guard 挂载失败（已跳过，动作将走 Mock）: {e}")
    # Phase 22：启动自检（只读，后台线程跑，不阻塞端口绑定；结果存 self_diagnosis._latest）
    try:
        import self_diagnosis
        self_diagnosis.startup_check()
        print("[Self Diagnosis] 启动自检已在后台触发（Start Diagnosis ready）。")
    except Exception as e:
        print(f"[Self Diagnosis] 启动自检初始化失败（已跳过）: {e}")
    # Phase 23：能力操作系统（只读聚合既有能力真相源，构建统一 Capability 注册表；不执行任何能力）
    try:
        import capability_os
        capability_os.bootstrap()
        reg = capability_os.get_registry()
        print(f"[Capability OS] 统一能力注册表已构建（共 {len(reg)} 项能力，"
              f"可用 {len(capability_os.available_capabilities())} 项）。")
    except Exception as e:
        print(f"[Capability OS] 注册表构建失败（已跳过）: {e}")
    # Phase 24：主动智能层（观察 9 源 → Attention Score → 建议；只读，绝不执行/写入）
    try:
        import proactive_agent
        info = proactive_agent.bootstrap()
        print(f"[Proactive Agent] 观察层已初始化（scheduler={info.get('scheduler')}）。")
    except Exception as e:
        print(f"[Proactive Agent] 初始化失败（已跳过）: {e}")
    # Phase 34 Task 4：统一启动就绪状态机推进（仅状态标记，无副作用）
    try:
        import beta_boot
        beta_boot.mark_backend_ready()
        beta_boot.mark_ai_ready()
        print("[Beta Boot] 就绪状态：BACKEND_READY / AI_READY（等待桌面 Avatar 上报 AVATAR_READY）。")
    except Exception as e:
        print(f"[Beta Boot] 状态推进失败（已忽略）: {e}")
    httpd = http.server.ThreadingHTTPServer((bind_host, port), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已关闭。")


def _warmup_embed():
    """向量语义 RAG：预热模型 + 向量库为空时全量回填历史笔记/记忆。"""
    try:
        import embed

        if not embed.model_ready():
            print("[embed] 模型缺失，跳过预热")
            return
        print("[embed] 预热向量模型…")
        embed.embed_doc("预热")
        try:
            n = embed.backfill_all()
            print("[embed] 历史向量回填完成：%s 条" % n)
        except Exception as e:
            print("[embed] 回填异常（可忽略）:", e)
    except Exception as e:
        print("[embed] 预热失败（可忽略）:", e)


if __name__ == "__main__":
    main()

