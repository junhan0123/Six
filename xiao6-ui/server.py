#!/usr/bin/env python3
"""
小6 · 本地指挥核心 · server.py（薄入口）
- 纯标准库（仅 TTS 用 GPT-SoVITS / Qwen3-TTS，lazy import）
- 托管界面 (index.html / styles.css / app.js)
- POST /api/chat  ->  function calling 闭环：调 Agnes -> 本地执行工具 -> 回填 -> 流式输出
- POST /api/speak ->  用 GPT-SoVITS 合成中文语音并返回 mp3
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

# ─────────────────────────────────────────────────────────────
# UI CONSOLIDATION (v1.0.0) · 唯一正式 UI 根目录
#   G:\xiao6\ui  ← 由本机 :8000 同源托管（无第二端口 / 无代理 / 无跳转）
# 可用环境变量 XIAO6_UI_DIR 覆盖；缺省为 <项目根>/ui（即 xiao6-ui 的同级 ui/）
# ─────────────────────────────────────────────────────────────
def _ui_root():
    env = os.environ.get("XIAO6_UI_DIR")
    if env:
        return os.path.realpath(env)
    here = os.path.dirname(os.path.abspath(__file__))          # .../xiao6/xiao6-ui
    return os.path.realpath(os.path.join(here, os.pardir, "ui"))  # .../xiao6/ui

# 静态资源后缀：命中则不走 SPA fallback，未命中（如 /work /tasks）才回落到 index.html
_UI_STATIC_EXT = {
    ".html", ".htm", ".js", ".mjs", ".css", ".json", ".map",
    ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".txt", ".md", ".webmanifest", ".xml",
}

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
from tools import TOOL_FUNCS, TOOLS, detect_intents, select_tools, get_pending_video, clear_pending_video, strip_think_tags

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
        return "http://127.0.0.1:%d" % int(getattr(config, "PORT", 8000))

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
            # UI CONSOLIDATION：优先托管唯一正式 UI（G:\xiao6\ui\index.html）
            ui_fp = self._resolve_ui("/index.html")
            if ui_fp:
                return self._serve_abs(ui_fp)
            return self._serve_file("index.html")   # 兜底：UI 目录缺失时保持原行为
        if path == "/api/health":
            # liveness：仅表进程存活；ok 取最近一次自检缓存，不触发外部探测（P0.2 修复 RC-4）
            # refresh=1 时强制重新运行自检
            force_refresh = qs.get("refresh", ["0"])[0] in ("1", "true", "True")
            cached = lifecycle.self_check_result
            if force_refresh:
                from self_check import run_self_check
                cached = run_self_check(force=True)
                lifecycle.self_check_result = cached
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
                        {
                            "ok": False,
                            "ready": ready,
                            "status": "initializing",
                            "runtime": "ready",
                            "database": "ready",
                            "tools": len(getattr(tools, 'TOOL_FUNCS', [])),
                            "capabilities": None,
                            "optional_services": {},
                            "key_present": key_ok,
                            "self_check": None,
                        },
                        ensure_ascii=False,
                    ),
                )
            ok = bool(key_ok and cached.get("ok"))
            degraded_checks = [c for c in cached.get("checks", []) if not c.get("ok")]
            optional_services = {}
            for check in degraded_checks:
                name = check.get("name", "")
                if "TTS" in name or "语音" in name:
                    optional_services["tts"] = "blocked"
                elif "热点" in name:
                    optional_services["hotspots"] = "degraded"
                else:
                    optional_services[name.lower().replace(" ", "_")] = "failed"

            # Get tool count
            try:
                import tools as _tools_module
                tool_count = len(getattr(_tools_module, 'TOOL_FUNCS', []))
            except Exception:
                tool_count = 0

            caps = None
            try:
                import capability_os
                if hasattr(capability_os, 'verification') and hasattr(capability_os.verification, 'verify_all'):
                    v = capability_os.verification.verify_all()
                    if v:
                        caps = {
                            "total": v.get('total', 0),
                            "ready": v.get('ready', 0),
                            "partial": v.get('partial', 0),
                            "blocked": v.get('blocked', 0),
                            "not_implemented": v.get('not_implemented', 0),
                        }
            except Exception:
                pass

            status = "ready"
            if degraded_checks:
                status = "degraded"

            return self._send(
                200,
                json.dumps(
                    {
                        "ok": ok,
                        "ready": ready,
                        "status": status,
                        "runtime": "ready",
                        "database": "ready",
                        "tools": tool_count,
                        "capabilities": caps,
                        "optional_services": optional_services,
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
        if path == "/api/interaction/status":
            try:
                import interaction_system as ins
                data = ins.get_status()
                return self._send(200, json.dumps(data, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/interaction/activity":
            try:
                import interaction_activity as ia
                manager = ia.get_activity_manager()
                activities = manager.get_activities(limit=20)
                stats = manager.get_stats()
                return self._send(200, json.dumps({
                    "ok": True,
                    "activities": [a.to_dict() for a in activities],
                    "stats": stats
                }, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/intelligence/feed":
            try:
                import intelligence_feed as ifeed
                limit = 20
                feed_types = None
                data = ifeed.get_feed(limit=limit, feed_types=feed_types)
                return self._send(200, json.dumps(data, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/intelligence/feedback":
            try:
                import intelligence_memory_loop as iml
                raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                payload = json.loads(raw.decode("utf-8", "replace") or "{}")
                item_id = payload.get("id", "")
                feedback = payload.get("feedback", "")
                insight = payload.get("insight", "")
                result = iml.handle_feedback(item_id, feedback, insight)
                return self._send(200, json.dumps(result, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/intelligence/foresight":
            try:
                import foresight_engine as fe
                engine = fe.get_foresight_engine()
                # 刷新数据
                engine.refresh_from_intelligence(
                    {"total": 35, "recent_logs": []},
                    {"total": 330},
                    {"risk_level": "medium", "events": []},
                    {"observation_sources": 4, "high_importance_observations": 1}
                )
                signals = engine.get_signals(20)
                warnings = engine.get_warnings(10)
                return self._send(200, json.dumps({
                    "ok": True,
                    "signals": signals.get("signals", []),
                    "warnings": warnings.get("warnings", []),
                    "total": len(signals.get("signals", []))
                }, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/intelligence/foresight/status":
            try:
                import foresight_engine as fe
                engine = fe.get_foresight_engine()
                return self._send(200, json.dumps(engine.get_status(), ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/intelligence/context":
            try:
                import intelligence_context as ic
                engine = ic.get_context_engine()
                # 刷新数据
                engine.refresh_from_intelligence(
                    {"total": 35},
                    {"total": 330},
                    {"events": [], "risk_level": "medium"},
                    {"signals": [], "warnings": []}
                )
                contexts = engine.get_contexts(20)
                return self._send(200, json.dumps({
                    "ok": True,
                    "contexts": contexts.get("contexts", []),
                    "total": len(contexts.get("contexts", []))
                }, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/intelligence/context/status":
            try:
                import intelligence_context as ic
                engine = ic.get_context_engine()
                return self._send(200, json.dumps(engine.get_status(), ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/intelligence/reasoning":
            try:
                import intelligence_reasoning as ir
                engine = ir.get_reasoning_engine()
                # 刷新数据
                engine.refresh_from_intelligence(
                    {"total": 35},
                    {"total": 330},
                    {"events": [], "risk_level": "medium"},
                    {"signals": [], "warnings": []},
                    {"contexts": []}
                )
                reasonings = engine.get_reasonings(20)
                return self._send(200, json.dumps({
                    "ok": True,
                    "reasonings": reasonings.get("reasonings", []),
                    "total": len(reasonings.get("reasonings", []))
                }, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/intelligence/reasoning/status":
            try:
                import intelligence_reasoning as ir
                engine = ir.get_reasoning_engine()
                return self._send(200, json.dumps(engine.get_status(), ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
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
        if path == "/api/memory/intelligence/status":
            try:
                import memory_intelligence as mi
                data = mi.get_intelligence_status()
                return self._send(200, json.dumps(data, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
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
        if path == "/api/observations":
            try:
                import observation_service
                svc = observation_service.get_observation_service()
                limit = int(qs.get("limit", ["20"])[0]) if "limit" in qs else 20
                return self._send(200, json.dumps({
                    "observations": svc.get_observations(limit),
                    "stats": svc.get_stats()
                }, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/suggestions":
            try:
                import suggestion_service
                svc = suggestion_service.get_suggestion_service()
                pending = svc.get_pending(limit=20)
                pending.sort(key=lambda x: x.get("priority", 5))
                return self._send(200, json.dumps({
                    "suggestions": pending,
                    "count": len(pending)
                }, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        # /api/proposals/*
        if path.startswith("/api/proposals"):
            try:
                import proposal_service
                svc = proposal_service.get_proposal_service()
                parts = path.split("/")
                # GET /api/proposals → list pending
                if len(parts) == 4:
                    pending = svc.get_pending(limit=20)
                    return self._send(200, json.dumps({
                        "proposals": pending,
                        "count": len(pending)
                    }, ensure_ascii=False))
                # POST /api/proposals/{id}/approve
                if len(parts) == 5 and parts[4] == "approve":
                    ok = svc.approve(parts[3])
                    return self._send(200, json.dumps({"ok": ok}, ensure_ascii=False))
                # POST /api/proposals/{id}/reject
                if len(parts) == 5 and parts[4] == "reject":
                    ok = svc.reject(parts[3])
                    return self._send(200, json.dumps({"ok": ok}, ensure_ascii=False))
                return self._send(404, json.dumps({"error": "not found"}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path.startswith("/api/proposals"):
            try:
                import proposal_service
                parts = path.split("/")
                # GET /api/proposals - 获取待处理提案
                if len(parts) == 3:
                    svc = proposal_service.get_proposal_service()
                    proposals = svc.get_pending_proposals(limit=20)
                    proposals.sort(key=lambda x: x.get("estimated_cost", 5))
                    return self._send(200, json.dumps({
                        "proposals": proposals,
                        "count": len(proposals)
                    }, ensure_ascii=False))
                # POST /api/proposals/{id}/approve
                if len(parts) == 4 and parts[3] == "approve":
                    proposal_id = parts[2]
                    svc = proposal_service.get_proposal_service()
                    success = svc.approve_proposal(proposal_id)
                    if success:
                        return self._send(200, json.dumps({"ok": True}, ensure_ascii=False))
                    return self._send(400, json.dumps({"error": "approve failed"}, ensure_ascii=False))
                # POST /api/proposals/{id}/reject
                if len(parts) == 4 and parts[3] == "reject":
                    proposal_id = parts[2]
                    svc = proposal_service.get_proposal_service()
                    success = svc.reject_proposal(proposal_id)
                    if success:
                        return self._send(200, json.dumps({"ok": True}, ensure_ascii=False))
                    return self._send(400, json.dumps({"error": "reject failed"}, ensure_ascii=False))
                # POST /api/proposals/{id}/create-task
                if len(parts) == 4 and parts[3] == "create-task":
                    proposal_id = parts[2]
                    try:
                        import proposal_task_adapter
                        svc = proposal_task_adapter.ProposalTaskAdapter()
                        # 获取提案
                        from proposal_service import get_proposal_service
                        all_proposals = get_proposal_service().get_all_proposals()
                        proposal = next((p for p in all_proposals if p.get("id") == proposal_id), None)
                        if not proposal:
                            return self._send(404, json.dumps({"error": "proposal not found"}, ensure_ascii=False))
                        if proposal.get("status") != "approved":
                            return self._send(400, json.dumps({"error": "proposal not approved"}, ensure_ascii=False))
                        # 创建任务
                        task = svc.create_task(proposal)
                        if task:
                            return self._send(200, json.dumps({"ok": True, "task_id": task["id"]}, ensure_ascii=False))
                        return self._send(400, json.dumps({"error": "create task failed"}, ensure_ascii=False))
                    except Exception as e:
                        return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
                return self._send(404, json.dumps({"error": "not found"}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))

        # PHASE 139: /api/gfe/sources/*
        if path.startswith("/api/gfe/sources"):
            try:
                from gfe_sources import get_source_manager
                manager = get_source_manager()
                parts = path.split("/")
                # GET /api/gfe/sources → list all or filtered
                if len(parts) == 4 and path.endswith("/sources"):
                    type_filter = qs.get("type", [None])[0] if qs.get("type") else None
                    sources = manager.list_sources(type_filter=type_filter)
                    return self._send(200, json.dumps({
                        "sources": [s.to_frontend() for s in sources],
                        "count": len(sources)
                    }, ensure_ascii=False))
                # POST /api/gfe/sources → register new source
                if len(parts) == 4 and path.endswith("/sources"):
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    ds = manager.register_source(
                        source_id=body.get("source_id"),
                        name=body.get("name"),
                        type=body.get("type"),
                        authority=body.get("authority"),
                        country=body.get("country"),
                        provenance=body.get("provenance"),
                        metadata=body.get("metadata"),
                    )
                    if ds:
                        return self._send(200, json.dumps({"ok": True, "source": ds.to_frontend()}, ensure_ascii=False))
                    return self._send(400, json.dumps({"error": "registration failed"}, ensure_ascii=False))
                # GET /api/gfe/sources/{source_id} → single source
                if len(parts) == 5:
                    ds = manager.get_source(parts[4])
                    if ds:
                        return self._send(200, json.dumps({"source": ds.to_frontend()}, ensure_ascii=False))
                    return self._send(404, json.dumps({"error": "not found"}, ensure_ascii=False))
                return self._send(404, json.dumps({"error": "not found"}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))

            return self._handle_notes()
        # PHASE 141: /api/gfe/events/*
        if path.startswith("/api/gfe/events"):
            try:
                from gfe_events import get_event_intelligence_engine
                engine = get_event_intelligence_engine()
                parts = path.split("/")
                # GET /api/gfe/events → list events
                if len(parts) == 4 and path.endswith("/events"):
                    events = engine.get_events(limit=50)
                    return self._send(200, json.dumps({
                        "events": [e.to_frontend() for e in events],
                        "count": len(events)
                    }, ensure_ascii=False))
                # POST /api/gfe/events → create event
                if len(parts) == 4 and path.endswith("/events"):
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    event = engine.ingest_event(
                        title=body.get("title"),
                        summary=body.get("summary", ""),
                        category=body.get("category", "economy"),
                        country_code=body.get("country_code", "CN"),
                        provenance=body.get("provenance", "manual"),
                        source_id=body.get("source_id"),
                    )
                    if event:
                        return self._send(200, json.dumps({
                            "ok": True,
                            "event": event.to_frontend()
                        }, ensure_ascii=False))
                    return self._send(400, json.dumps({"error": "failed to create event"}, ensure_ascii=False))
                # GET /api/gfe/events/{id} → single event
                if len(parts) == 5:
                    event = engine.get_event(parts[4])
                    if event:
                        return self._send(200, json.dumps({"event": event.to_frontend()}, ensure_ascii=False))
                    return self._send(404, json.dumps({"error": "not found"}, ensure_ascii=False))
                # GET /api/gfe/risk-signals
                if len(parts) == 4 and path.endswith("/risk-signals"):
                    signals = engine.get_risk_signals(limit=50)
                    return self._send(200, json.dumps({
                        "signals": [s.to_frontend() for s in signals],
                        "count": len(signals)
                    }, ensure_ascii=False))
                return self._send(404, json.dumps({"error": "not found"}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        # PHASE 142: /api/gfe/history/*
        if path.startswith("/api/gfe/history"):
            try:
                from gfe_history import get_historical_comparison_engine
                engine = get_historical_comparison_engine()
                parts = path.split("/")
                # GET /api/gfe/history/cases → list cases
                if len(parts) == 5 and path.endswith("/cases"):
                    cases = engine.get_cases(limit=50)
                    return self._send(200, json.dumps({
                        "cases": [c.to_frontend() for c in cases],
                        "count": len(cases)
                    }, ensure_ascii=False))
                # POST /api/gfe/history/case → create case
                if len(parts) == 5 and path.endswith("/case"):
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    case = engine.add_case(
                        case_id=body.get("case_id"),
                        title=body.get("title"),
                        period_start=body.get("period_start"),
                        period_end=body.get("period_end"),
                        country_code=body.get("country_code"),
                        category=body.get("category"),
                        description=body.get("description", ""),
                        state_snapshot=body.get("state_snapshot", "{}"),
                        provenance=body.get("provenance", "historical_database"),
                    )
                    if case:
                        return self._send(200, json.dumps({"ok": True, "case": case.to_frontend()}, ensure_ascii=False))
                    return self._send(400, json.dumps({"error": "failed to create case"}, ensure_ascii=False))
                # GET /api/gfe/history/compare/{country} → compare with history
                if len(parts) == 6 and path.endswith("/compare"):
                    country_code = parts[5]
                    current_state = engine.world_state_engine.get_current_state(country_code) if engine.world_state_engine else None
                    if not current_state:
                        return self._send(404, json.dumps({"error": "country state not found"}, ensure_ascii=False))
                    matches = engine.compare_state(country_code, current_state)
                    return self._send(200, json.dumps({
                        "country": country_code,
                        "matches": matches
                    }, ensure_ascii=False))
                return self._send(404, json.dumps({"error": "not found"}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        # PHASE 143: /api/gfe/causal/*
        if path.startswith("/api/gfe/causal"):
            try:
                from gfe_causal import get_causal_graph_engine
                engine = get_causal_graph_engine()
                parts = path.split("/")
                # GET /api/gfe/causal/nodes → list nodes
                if len(parts) == 5 and path.endswith("/nodes"):
                    category = qs.get("category", [None])[0]
                    nodes = engine.get_nodes(category=category, limit=100)
                    return self._send(200, json.dumps({
                        "nodes": [n.to_frontend() for n in nodes],
                        "count": len(nodes)
                    }, ensure_ascii=False))
                # POST /api/gfe/causal/node → create node
                if len(parts) == 5 and path.endswith("/node"):
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    node = engine.add_node(
                        name=body.get("name"),
                        category=body.get("category"),
                        description=body.get("description"),
                        entity_type=body.get("entity_type"),
                        provenance=body.get("provenance")
                    )
                    if node:
                        return self._send(200, json.dumps({"ok": True, "node": node.to_frontend()}, ensure_ascii=False))
                    return self._send(400, json.dumps({"error": "failed to create node"}, ensure_ascii=False))
                # POST /api/gfe/causal/edge → create edge
                if len(parts) == 5 and path.endswith("/edge"):
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    edge = engine.add_edge(
                        source_node=body.get("source_node"),
                        target_node=body.get("target_node"),
                        relationship_type=body.get("relationship_type"),
                        strength=body.get("strength", 0.5),
                        confidence=body.get("confidence", 0.5),
                        time_delay=body.get("time_delay"),
                        evidence_refs=body.get("evidence_refs"),
                        provenance=body.get("provenance")
                    )
                    if edge:
                        return self._send(200, json.dumps({"ok": True, "edge": edge.to_frontend()}, ensure_ascii=False))
                    return self._send(400, json.dumps({"error": "failed to create edge"}, ensure_ascii=False))
                # GET /api/gfe/causal/path/{node} → find impact path
                if len(parts) == 6 and path.endswith("/path"):
                    node_name = parts[4]
                    path_result = engine.calculate_impact_path(node_name)
                    if path_result:
                        return self._send(200, json.dumps({
                            "node": node_name,
                            "path": path_result.to_frontend()
                        }, ensure_ascii=False))
                    return self._send(404, json.dumps({"error": "path not found"}, ensure_ascii=False))
                return self._send(400, json.dumps({"error": "invalid causal path"}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        # S143.3: /api/gfe/intelligence/*
        if path.startswith("/api/gfe/intelligence"):
            try:
                import gfe_intelligence as gi
                parts = path.split("/")
                # GET /api/gfe/intelligence/status
                if len(parts) == 5 and path.endswith("/status"):
                    data = gi.status()
                    return self._send(200, json.dumps(data, ensure_ascii=False))
                # POST /api/gfe/intelligence/analyze
                if len(parts) == 5 and path.endswith("/analyze"):
                    body = self._read_json()
                    dry_run = True
                    if "_error" not in body:
                        dry_run = body.get("dry_run", True)
                    data = gi.analyze(dry_run=dry_run)
                    return self._send(200, json.dumps(data, ensure_ascii=False))
                return self._send(404, json.dumps({"error": "not found"}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        # PHASE 147: /api/gfe/ledger/*
        if path.startswith("/api/gfe/ledger"):
            try:
                from gfe_forecast_ledger import get_forecast_ledger
                ledger = get_forecast_ledger()
                parts = path.split("/")
                # GET /api/gfe/ledger/records → list records
                if len(parts) == 5 and path.endswith("/records"):
                    forecast_id = qs.get("forecast_id", [None])[0]
                    limit = int(qs.get("limit", ["50"])[0])
                    records = ledger.get_ledgers(forecast_id=forecast_id, limit=limit)
                    return self._send(200, json.dumps({
                        "records": [r.to_frontend() for r in records],
                        "count": len(records)
                    }, ensure_ascii=False))
                # POST /api/gfe/ledger/record → record prediction
                if len(parts) == 5 and path.endswith("/record"):
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    record = ledger.record_prediction(
                        forecast_id=body.get("forecast_id"),
                        prediction=body.get("prediction"),
                        probability=body.get("probability", 0.5)
                    )
                    if record:
                        return self._send(200, json.dumps({
                            "ok": True,
                            "record": record.to_frontend()
                        }, ensure_ascii=False))
                    return self._send(400, json.dumps({"error": "failed to record prediction"}, ensure_ascii=False))
                # POST /api/gfe/ledger/evaluate → evaluate prediction
                if len(parts) == 5 and path.endswith("/evaluate"):
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    evaluated = ledger.evaluate_prediction(
                        ledger_id=body.get("ledger_id"),
                        actual_result=body.get("actual_result"),
                        predicted_probability=body.get("predicted_probability", 0.5)
                    )
                    if evaluated:
                        return self._send(200, json.dumps({
                            "ok": True,
                            "record": evaluated.to_frontend()
                        }, ensure_ascii=False))
                    return self._send(400, json.dumps({"error": "failed to evaluate prediction"}, ensure_ascii=False))
                # GET /api/gfe/ledger/metrics → get metrics
                if len(parts) == 5 and path.endswith("/metrics"):
                    forecast_type = qs.get("forecast_type", [None])[0]
                    metrics = ledger.get_metrics(forecast_type=forecast_type)
                    return self._send(200, json.dumps({
                        "metrics": [m.to_frontend() for m in metrics],
                        "count": len(metrics)
                    }, ensure_ascii=False))
                # GET /api/gfe/ledger/analyst/{id} → get analyst accuracy
                if len(parts) == 6 and path.endswith("/accuracy"):
                    analyst_id = parts[4]
                    accuracy = ledger.get_analyst_accuracy(analyst_id)
                    return self._send(200, json.dumps(accuracy, ensure_ascii=False))
                return self._send(400, json.dumps({"error": "invalid ledger path"}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/audit":
            return self._handle_audit()
        # PHASE 148: /api/gfe/warnings/*
        if path.startswith("/api/gfe/warnings"):
            try:
                from gfe_warning import get_early_warning_engine
                engine = get_early_warning_engine()
                parts = path.split("/")
                # GET /api/gfe/warnings → list alerts
                if len(parts) == 5 and "/warnings" in path:
                    country_code = qs.get("country_code", [None])[0]
                    status = qs.get("status", [None])[0]
                    alerts = engine.get_alerts(country_code=country_code, status=status)
                    return self._send(200, json.dumps({
                        "alerts": [a.to_frontend() for a in alerts],
                        "count": len(alerts)
                    }, ensure_ascii=False))
                # GET /api/gfe/warnings/rules → list rules
                if len(parts) == 6 and "/warnings/rules" in path:
                    category = qs.get("category", [None])[0]
                    rules = engine.get_rules(category=category)
                    return self._send(200, json.dumps({
                        "rules": [r.to_frontend() for r in rules],
                        "count": len(rules)
                    }, ensure_ascii=False))
                # POST /api/gfe/warnings/evaluate/{country} → evaluate risk
                if len(parts) == 7 and "/warnings/evaluate/" in path:
                    country_code = parts[5]
                    result = engine.evaluate_risk(country_code)
                    return self._send(200, json.dumps(result, ensure_ascii=False))
                return self._send(400, json.dumps({"error": "invalid warnings path"}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/tasks":
            return self._handle_tasks()
        # PHASE 149: /api/gfe/calibration/*
        if path.startswith("/api/gfe/calibration"):
            try:
                from gfe_calibration import get_calibration_engine
                engine = get_calibration_engine()
                parts = path.split("/")
                # GET /api/gfe/calibration/report → calibration report
                if len(parts) == 5 and path.endswith("/report"):
                    report = engine.get_calibration_report()
                    return self._send(200, json.dumps(report, ensure_ascii=False))
                # POST /api/gfe/calibration/evaluate → record evaluation
                if len(parts) == 5 and path.endswith("/evaluate"):
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    record = engine.record_evaluation(
                        forecast_id=body.get("forecast_id"),
                        analyst_id=body.get("analyst_id"),
                        domain=body.get("domain"),
                        predicted_probability=body.get("predicted_probability", 0.5),
                        actual_result=body.get("actual_result", 0.5),
                        confidence=body.get("confidence", 0.5)
                    )
                    if record:
                        return self._send(200, json.dumps({
                            "ok": True,
                            "record": record.to_frontend()
                        }, ensure_ascii=False))
                    return self._send(400, json.dumps({"error": "failed to record evaluation"}))
                # GET /api/gfe/calibration/analyst/{id} → analyst metrics
                if len(parts) == 6 and path.endswith("/metrics"):
                    analyst_id = parts[5]
                    domain = qs.get("domain", [None])[0]
                    metrics = engine.get_analyst_metrics(analyst_id=analyst_id, domain=domain)
                    return self._send(200, json.dumps({
                        "metrics": [m.to_frontend() for m in metrics],
                        "count": len(metrics)
                    }, ensure_ascii=False))
                return self._send(400, json.dumps({"error": "invalid calibration path"}))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}))
        # PHASE 150: /api/gfe/dashboard — 聚合接口
        if path == "/api/gfe/dashboard":
            try:
                from gfe_events import get_event_intelligence_engine
                from gfe_forecast import get_forecast_engine
                from gfe_warning import get_early_warning_engine
                from gfe_calibration import get_calibration_engine
                import time

                ev_engine = get_event_intelligence_engine()
                fc_engine = get_forecast_engine()
                ew_engine = get_early_warning_engine()
                cal_engine = get_calibration_engine()

                events = ev_engine.get_events(limit=20)
                forecasts = fc_engine.get_forecasts(limit=10)
                warnings = ew_engine.get_alerts(status="active")
                cal_report = cal_engine.get_calibration_report()

                # 计算风险概览
                active_count = len([e for e in events if e.severity >= 0.5])
                high_sev_count = len([e for e in events if e.severity >= 0.7])

                total_risk = 0
                if events:
                    total_risk = sum(e.severity * (e.confidence or 0.5) for e in events) / len(events)

                risk_summary = {
                    "total_risk_index": round(total_risk, 4),
                    "active_events_count": active_count,
                    "high_severity_count": high_sev_count,
                    "updated_at": time.time()
                }

                # 格式化数据
                events_fmt = [e.to_frontend() for e in events[:10]]
                forecasts_fmt = [f.to_frontend() for f in forecasts[:10]]
                warnings_fmt = [w.to_frontend() for w in warnings[:10]]

                result = {
                    "risk_summary": risk_summary,
                    "events": events_fmt,
                    "forecasts": forecasts_fmt,
                    "warnings": warnings_fmt,
                    "calibration": cal_report,
                    "timestamp": time.time()
                }

                return self._send(200, json.dumps(result, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}))
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
        if path == "/api/session/resume":
            return self._handle_session_resume()
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
        # —— Phase 47.5：工具清单（GET，只读）——
        if path == "/api/tools/list":
            try:
                tool_list = [
                    {
                        "name": t["function"]["name"],
                        "description": t["function"].get("description", ""),
                        "parameters": t["function"].get("parameters", {}),
                    }
                    for t in TOOLS
                ]
                return self._send(200, json.dumps({"ok": True, "count": len(tool_list), "tools": tool_list}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
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
        # S95 · Capability 真实验证（GET，只读；调用 verification.verify_all）
        if path == "/api/capability_os/verify":
            try:
                import capability_os
                return self._send(200, json.dumps(capability_os.verify_capabilities(), ensure_ascii=False))
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
        if path == "/api/knowledge/intelligence/status":
            try:
                import knowledge_intelligence as ki
                data = ki.get_status()
                return self._send(200, json.dumps(data, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/intelligence/status":
            try:
                import intelligence_registry as ir
                data = ir.get_status()
                return self._send(200, json.dumps(data, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
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
        # ── UI CONSOLIDATION (v1.0.0) · 唯一正式 UI：G:\xiao6\ui ──
        # /api/* 在上方已全部 return；此处双保险再次排除，API 绝不 fallback 到 index.html
        if not path.startswith("/api/"):
            ui_fp = self._resolve_ui(path)
            if ui_fp:
                return self._serve_abs(ui_fp)
            # 前端路由（/work /tasks /memory /settings …）刷新 → 回落 index.html
            if self._is_spa_route(path):
                idx = self._resolve_ui("/index.html")
                if idx:
                    return self._serve_abs(idx)
        # ── 以下为历史静态逻辑，保留以向下兼容（不删除既有能力）──
        if path.startswith("/static/"):
            return self._serve_file(path[len("/static/") :])
        if path.startswith("/xiao6-space"):
            return self._serve_file("xiao6-space" + path[len("/xiao6-space"):])
        if self._resolve_static(path):
            return self._serve_file(path.lstrip("/"))
        self._send(404, json.dumps({
            "ok": False,
            "error": "invalid_api_path",
            "message": "API路径不存在",
            "suggestion": self._suggest_path(path),
        }))

    def _suggest_path(self, path: str) -> str:
        """Suggest correct API path for common mistakes."""
        if not path or not path.startswith("/api/"):
            return ""
        known_paths = [
            "/api/memory", "/api/goals", "/api/tasks",
            "/api/perception/screen", "/api/perception/window",
        ]
        # Handle common /list suffix mistake
        if path.endswith("/list"):
            base = path[:-5]
            if base in known_paths:
                return base
        # Handle other common patterns
        for kp in known_paths:
            if kp in path:
                return kp
        return ""

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

    # ── UI CONSOLIDATION · 唯一正式 UI（G:\xiao6\ui）静态解析 ──
    def _resolve_ui(self, path):
        """解析 UI 根目录下的静态文件。

        安全强度与 _resolve_static 对齐：
        - 禁止 ".." 路径分量 / NUL（防路径穿越）
        - 禁止 .env / .git（凭证与仓库元数据）
        - realpath 归一 + commonpath 边界校验（symlink 越界同样被拒）
        空路径视为 index.html。返回绝对路径；非法或不存在返回 None。
        """
        name = (path or "").split("?", 1)[0].split("#", 1)[0]
        name = name.replace("\\", "/").lstrip("/")
        if not name:
            name = "index.html"
        if name.startswith("/") or "\x00" in name:
            return None
        if ".." in name.split("/"):
            return None
        root = _ui_root()
        fp = os.path.realpath(os.path.join(root, name))
        try:
            if os.path.commonpath([root, fp]) != root:
                return None
        except ValueError:
            return None
        bn = os.path.basename(fp)
        if bn == ".env" or ".env" in bn or ".git" in bn:
            return None
        if not os.path.isfile(fp):
            return None
        return fp

    def _is_spa_route(self, path):
        """是否应回落到 UI index.html（前端路由刷新）。
        /api/* 永不 fallback；带静态资源后缀的也不 fallback。"""
        name = (path or "").split("?", 1)[0].split("#", 1)[0]
        if name.startswith("/api/"):
            return False
        ext = os.path.splitext(name)[1].lower()
        return ext not in _UI_STATIC_EXT

    def _serve_abs(self, fp):
        """按绝对路径发送文件（复用 CONTENT 的 Content-Type 映射）。"""
        ext = os.path.splitext(fp)[1].lower()
        try:
            with open(fp, "rb") as f:
                data = f.read()
        except Exception:
            return self._send(404, json.dumps({"error": "read failed"}, ensure_ascii=False))
        return self._send(200, data, CONTENT.get(ext, "application/octet-stream"))

    def _serve_abs_head(self, fp):
        ext = os.path.splitext(fp)[1].lower()
        try:
            clen = os.path.getsize(fp)
        except Exception:
            return self._send_head(404)
        return self._send_head(200, CONTENT.get(ext, "application/octet-stream"), clen)

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
            # UI CONSOLIDATION：优先托管唯一正式 UI（G:\xiao6\ui\index.html）
            ui_fp = self._resolve_ui("/index.html")
            if ui_fp:
                return self._serve_abs_head(ui_fp)
            return self._serve_file_head("index.html")   # 兜底：保持原行为
        if path.startswith("/api/"):
            return self._send_head(200)
        # ── UI CONSOLIDATION · 唯一正式 UI：G:\xiao6\ui（HEAD 探测）──
        if not path.startswith("/api/"):
            ui_fp = self._resolve_ui(path)
            if ui_fp:
                return self._serve_abs_head(ui_fp)
            if self._is_spa_route(path):
                idx = self._resolve_ui("/index.html")
                if idx:
                    return self._serve_abs_head(idx)
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
        if ppath == "/api/interaction/parse":
            try:
                import interaction_system as ins
                payload = self._read_json()
                text = payload.get("text", "") if "_error" not in payload else ""
                data = ins.parse_interaction(text)
                return self._send(200, json.dumps(data, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if ppath == "/api/interaction/activity":
            try:
                import interaction_activity as ia
                manager = ia.get_activity_manager()
                activities = manager.get_activities(limit=20)
                stats = manager.get_stats()
                return self._send(200, json.dumps({
                    "ok": True,
                    "activities": [a.to_dict() for a in activities],
                    "stats": stats
                }, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
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
        if ppath == "/api/session/resume":
            return self._handle_session_resume()
        if ppath == "/api/trace":
            return self._handle_trace_get()
        if ppath == "/api/activity":
            return self._handle_activity_get()
        if ppath == "/api/knowledge":
            return self._handle_knowledge()
        if ppath == "/api/knowledge/intelligence/analyze":
            try:
                import knowledge_intelligence as ki
                dry_run = True
                payload = self._read_json()
                if "_error" not in payload:
                    dry_run = payload.get("dry_run", True)
                data = ki.analyze(dry_run=dry_run)
                return self._send(200, json.dumps(data, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
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
        if ppath == "/api/memory/intelligence/analyze":
            try:
                import memory_intelligence as mi
                dry_run = True
                payload = self._read_json()
                if "_error" not in payload:
                    dry_run = payload.get("dry_run", True)
                data = mi.analyze_intelligence(dry_run=dry_run)
                return self._send(200, json.dumps(data, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if ppath == "/api/gfe/intelligence/analyze":
            try:
                import gfe_intelligence as gi
                payload = self._read_json()
                dry_run = True
                if "_error" not in payload:
                    dry_run = payload.get("dry_run", True)
                data = gi.analyze(dry_run=dry_run)
                return self._send(200, json.dumps(data, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if ppath == "/api/proactive/analyze":
            try:
                import proactive_intelligence as pi
                payload = self._read_json()
                dry_run = True
                if "_error" not in payload:
                    dry_run = payload.get("dry_run", True)
                data = pi.analyze(dry_run=dry_run)
                return self._send(200, json.dumps(data, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
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
    # PHASE 130：观察服务（只读，不修改 Runtime）
    try:
        import observation_service
        observation_service.init_observation_service()
        print("[Observation Service] 观察层已初始化（监听 EventBus）。")
    except Exception as e:
        print(f"[Observation Service] 初始化失败（已跳过）: {e}")
    # PHASE 131：提案服务（用户审批后才创建任务）
    try:
        import proposal_service
        proposal_service.init_proposal_service()
        print("[Proposal Service] 提案层已初始化。")
    except Exception as e:
        print(f"[Proposal Service] 初始化失败（已跳过）: {e}")
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

