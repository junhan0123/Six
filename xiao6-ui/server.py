#!/usr/bin/env python3
"""
搴勫懆 路 鏈?湴鎸囨尌鏍稿績 路 server.py锛堣杽鍏ュ彛锛?
- 绾?爣鍑嗗簱锛堜粎 TTS 鐢?edge-tts锛宭azy import锛?
- 鎵樼?鐣岄潰 (index.html / styles.css / app.js)
- POST /api/chat  ->  function calling 闂?幆锛氳皟 Agnes -> 鏈?湴鎵ц?宸ュ叿 -> 鍥炲? -> 娴佸紡杈撳嚭
- POST /api/speak ->  鐢?edge-tts 鍚堟垚涓?枃璇?煶骞惰繑鍥?mp3
- GET  /api/health
- API Key 浠呭瓨浜庢湇鍔??锛堢幆澧冨彉閲忔垨鍚岀洰褰?.env锛夛紝缁濅笉鏆撮湶缁欏墠绔?
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

# Phase 10-C 路 鏈?湴 Provider 鍙?敤鎬ф帰娴嬬紦瀛橈紙浠呯櫧鍚嶅崟 127.0.0.1锛泂pec 搂鍏?級
# 杩涚▼鍐呭唴瀛?dict锛屽瓨鏈€杩戜竴娆℃帰娴嬬粨鏋滐紱绂佹壂鎻忋€佺?浠绘剰杩滅▼鎺㈡祴銆?
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
import sessions as sessions_mgr
import projects as proj_mgr
import skills as local_skills
import server_handlers_skills as skill_handlers
from prefetch import start_prefetch_scheduler
from proactive import SUBSCRIBERS, SUBSCRIBERS_LOCK, flush_pending, make_daily_briefing, tick_loop

# 姣忔棩绠€鎶ャ€屼粎鎺ㄤ竴娆°€嶅幓閲嶉攣锛氬? SSE 杩炴帴锛堟垨杩滅▼ Web 瀹㈡埛绔??寮€锛夊苟鍙戝缓绔嬫椂锛?
# 涓茶?鍖栧? last_briefing_date 鐨勮?鍐欙紝閬垮厤绠€鎶ヨ?鍙屾帹銆?
BRIEFING_LOCK = threading.Lock()


def _sse_use_eventbus():
    """SSE 鎵囧嚭鏄?惁璧?EventBus锛堥粯璁?ON锛宖alse 鍥為€€ SUBSCRIBERS 鏃ц矾寰勶級銆"""
    try:
        from eventbus import enabled

        return enabled()
    except Exception:
        return False


def _sse_put(q, payload):
    """EventBus 璁㈤槄鍥炶皟锛氭妸浜嬩欢杞借嵎鎶曞叆鏈?繛鎺ョ殑闃熷垪銆"""
    try:
        q.put(payload)
    except Exception:
        pass
from self_check import run_self_check
from social import status as social_status
from sysmon import get_logs, get_sysmon


def _proactive_dnd_state() -> bool:
    """璇诲彇鍚庣? NotificationPolicy 鐨勬潈濞?DND 鐘舵€侊紙缁?db.meta锛屽崟涓€鏉ユ簮锛夈€"""
    try:
        import proactive_config as _pc

        return _pc.policy.is_dnd_enabled()
    except Exception:
        return False
from tasks import recover_tasks
from ai_core.lifecycle import lifecycle
from ai_core.execution import run as _execution_run
from tools import TOOL_FUNCS, TOOLS, detect_intents, run_fc_loop, select_tools, get_pending_video, clear_pending_video, strip_think_tags

# ---------- Phase C锛氳繙绋嬭?闂?畨鍏?----------
# 杩滅▼浼氳瘽榛樿?绂佹?鐨勯珮鍗卞伐鍏凤紙run_shell/file_write/install/濮旀墭/宸ュ巶绠?悊绛夛級銆?
# 鏈?樉寮忛厤缃?REMOTE_TOOL_WHITELIST 鏃讹紝杩滅▼浠呭紑鏀俱€屽畨鍏ㄩ粯璁ゃ€嶇櫧鍚嶅崟锛堝叏閮ㄥ噺鍘讳笅琛?級銆?
_REMOTE_FORBIDDEN = {
    "run_shell", "session_state", "reset_session",
    "file_write", "file_make_dir", "file_delete", "file_rename",
    "install_software", "delegate_agent",
    "create_custom_tool", "delete_custom_tool",
}


def _remote_allowed_tools():
    """杩斿洖杩滅▼浼氳瘽鍏佽?浣跨敤鐨勫伐鍏峰悕闆嗗悎銆"""
    cfg = (config.REMOTE_TOOL_WHITELIST or "").strip()
    if cfg:
        return {x.strip() for x in cfg.split(",") if x.strip()}
    return {t["function"]["name"] for t in TOOLS if t["function"]["name"] not in _REMOTE_FORBIDDEN}


def _is_local_peer(peer):
    return peer in ("127.0.0.1", "::1", "localhost", "0:0:0:0:0:0:0:1", "::ffff:127.0.0.1")


# 璁块棶鏃ュ織鑴辨晱锛氳?姹傝?锛坰elf.requestline锛変細鍘熸牱鍖呭惈鏌ヨ?涓诧紝?token= 绛夋晱鎰熷弬鏁?
# 鑻ョ洿鎺ヨ惤鐩?杈撳嚭鍒?stderr 浼氶€犳垚鍑?瘉娉勯湶銆傜粺涓€鍦?log_message 钀界洏鍓嶈劚鏁忋€?
_ACCESS_LOG_REDACT_RE = re.compile(
    r"([?&](?:token|access[_-]?token|auth[_-]?token|secret|password|passwd|api[_-]?key|apikey)=)[^&\s\"']+",
    re.IGNORECASE,
)
from wakeword import get_status as wakeword_status, start as wakeword_start, stop as wakeword_stop


# ---------- HTTP Handler ----------
def _hotspot_modal_payload(hs):
    """鎶婄粨鏋勫寲鐑?偣鏁版嵁鍘嬬缉涓哄墠绔?脊绐楁墍闇€鐨勬渶灏忓瓧娈点€"""
    platforms = hs.get("platforms", {}) or {}
    PLATFORM_LABELS = {"douyin": "Douyin", "xiaohongshu": "Xiaohongshu", "wechat": "WeChat", "weibo": "Weibo"}
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


# ---------- Phase 47.1锛欳ORS 鐧藉悕鍗曪紙鍙栦唬 "*"锛?---------
# 浠呭洖鏄句笌缁戝畾绔?彛涓€鑷寸殑 loopback / 鏄惧紡缁戝畾涓绘満 Origin锛?
# 浠绘剰澶栭儴 Origin 涓€寰嬩笉鍥炴樉锛堟潨缁?CSRF / 璺ㄥ煙鏁版嵁娉勯湶闈?級銆?
_CORS_ALLOWED_ORIGINS = set()


def _resolve_cors_origins(bind_host, port):
    """鏍规嵁缁戝畾缃戝彛璁?畻鍏佽?鐨?CORS Origin 闆嗗悎銆"""
    origins = set()
    try:
        port = int(port)
    except Exception:
        port = 8010
    origins.add("http://127.0.0.1:%d" % port)
    origins.add("http://localhost:%d" % port)
    if bind_host in ("0.0.0.0", "", None):
        # 寮€鏀?LAN 鏃舵妸鏈?満闈炲洖鐜?IP 涔熺撼鍏ワ紙浠呭綋宸查厤 REMOTE_ACCESS_TOKEN 鎵嶄細璧板埌姝ゅ垎鏀?級
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
from server_handlers import SystemMixin, MemoryMixin, TasksMixin, ChatMixin, CapabilityMixin, SocialMixin
from task_reliability import task_manager, TaskState



class Handler(BaseHTTPRequestHandler, SystemMixin, MemoryMixin, TasksMixin, ChatMixin, CapabilityMixin, SocialMixin):
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
        """杩斿洖褰撳墠璇锋眰搴斿洖鏄剧殑 CORS Origin锛堜弗鏍肩櫧鍚嶅崟锛夈€"""
        origin = (self.headers.get("Origin") or "").strip()
        if origin and origin in _CORS_ALLOWED_ORIGINS:
            return origin
        # 瀹夊叏榛樿?锛氫富鍥炵幆 Origin锛堢粷涓嶅洖鏄句换鎰忓?閮?Origin锛?
        return "http://127.0.0.1:%d" % int(getattr(config, "PORT", 8010))

    def _remote_gate(self):
        """杩滅▼璁块棶闂ㄦ帶锛氶潪鏈?満璇锋眰椤荤粡 Bearer Token 鏍?獙锛圧EMOTE_ACCESS_TOKEN锛夈€"
        杩斿洖 True 鏀捐?锛涜繑鍥?False 琛ㄧず宸插彂閫佹嫆缁濆搷搴斻€"""
        peer = (self.client_address or ("",))[0]
        if _is_local_peer(peer):
            return True
        token = config.REMOTE_ACCESS_TOKEN
        if not token:
            # 鏈?厤缃?繙绋?token锛氬交搴曠?姝?换浣曢潪鏈?満璁块棶
            self._send(403, json.dumps(
                {"error": "浠呭厑璁告湰鏈鸿?闂?紱濡傞渶杩滅▼璁块棶璇峰湪璁剧疆涓?厤缃?REMOTE_ACCESS_TOKEN"}, ensure_ascii=False))
            return False
        # 鏍?獙 Bearer Token锛堟敮鎸?Authorization 澶存垨 ?token= 鏌ヨ?鍙傛暟锛?
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
        self._send(401, json.dumps({"error": "杩滅▼璁块棶闇€瑕佹湁鏁堢殑 Bearer Token"}, ensure_ascii=False))
        return False

    # 鈥斺€?Phase 62 路 Custom Model 鎸佷箙鍖栫?鐞嗭紙鏈€灏忓疄鐜帮紝澶嶇敤 model_manager锛夆€斺€?
    def _handle_model_get(self):
        """GET /api/model 鈥?杩斿洖褰撳墠婵€娲绘ā鍨?+ 鍏ㄩ儴鍙?€夋ā鍨嬪垪琛ㄣ€"""
        try:
            import model_manager

            models = model_manager.list_models()
            active = model_manager.get_active()
            return self._send(200, json.dumps({
                "ok": True,
                "active_id": active.get("id") if active else None,
                "active": active,
                "models": models,
            }, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def _handle_model_post(self):
        """POST /api/model 鈥?action: list|add|set|delete銆"

        - add:   {action:"add", name, provider_type, model, base_url, api_key, context_length, temperature, max_tokens}
        - set:   {action:"set", id}
        - delete:{action:"delete", id}
        """
        try:
            import model_manager

            p = self._read_json()
            if "_error" in p:
                return self._send(400, json.dumps({"ok": False, "error": p["_error"]}, ensure_ascii=False))
            action = (p.get("action") or "list").strip().lower()
            if action == "add":
                models = model_manager.add_model(p)
                return self._send(200, json.dumps({"ok": True, "models": models}, ensure_ascii=False))
            if action == "set":
                mid = (p.get("id") or "").strip()
                if not mid:
                    return self._send(400, json.dumps({"ok": False, "error": "id required"}, ensure_ascii=False))
                active = model_manager.set_active(mid)
                return self._send(200, json.dumps({"ok": True, "active": active}, ensure_ascii=False))
            if action == "delete":
                mid = (p.get("id") or "").strip()
                if not mid:
                    return self._send(400, json.dumps({"ok": False, "error": "id required"}, ensure_ascii=False))
                ok = model_manager.delete_model(mid)
                return self._send(200, json.dumps({"ok": True, "deleted": ok}, ensure_ascii=False))
            # 榛樿? list
            models = model_manager.list_models()
            active = model_manager.get_active()
            return self._send(200, json.dumps({"ok": True, "active_id": active.get("id") if active else None, "active": active, "models": models}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    # 鈥斺€?浼氳瘽绠?悊锛堝乏渚ф爮瀵硅瘽鍘嗗彶 / 缃?《 / 褰掓。 / 閲嶅懡鍚?/ 鍒犻櫎锛夆€斺€?
    def _handle_sessions_get(self):
        try:
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            archived = qs.get("archived", [""])[0].lower()
            project_q = (qs.get("project") or [""])[0].strip()
            project_id = int(project_q) if project_q.isdigit() else None
            if archived in ("1", "true", "yes"):
                items = sessions_mgr.list_sessions(archived=True, project_id=project_id)
            elif archived in ("0", "false", "no"):
                items = sessions_mgr.list_sessions(archived=False, project_id=project_id)
            else:
                items = sessions_mgr.list_sessions(archived=None, project_id=project_id)
            return self._send(200, json.dumps({"ok": True, "sessions": items}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def _handle_sessions_cleanup(self):
        """POST /api/sessions/cleanup — 清理空会话"""
        try:
            deleted = sessions_mgr.delete_empty_sessions()
            return self._send(200, json.dumps({"ok": True, "deleted": deleted}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def _handle_sessions_post(self):
        try:
            p = self._read_json()
            if "_error" in p:
                return self._send(400, json.dumps({"ok": False, "error": p["_error"]}, ensure_ascii=False))
            title = (p.get("title") or "新对话").strip()
            pid = p.get("project_id")
            sid = sessions_mgr.create_session(title, project_id=pid)
            return self._send(200, json.dumps({"ok": True, "id": sid, "session": sessions_mgr.get_session(sid)}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def _handle_sessions_patch(self):
        try:
            ppath = self.path.split("?", 1)[0]
            sid = ppath[len("/api/sessions/"):].strip("/")
            sid = int(sid)
            p = self._read_json()
            if "_error" in p:
                return self._send(400, json.dumps({"ok": False, "error": p["_error"]}, ensure_ascii=False))
            ok = False
            if "title" in p:
                ok = sessions_mgr.rename_session(sid, p["title"])
            if "pinned" in p:
                ok = sessions_mgr.pin_session(sid, bool(p["pinned"])) or ok
            if "archived" in p:
                ok = sessions_mgr.archive_session(sid, bool(p["archived"])) or ok
            if "project_id" in p:
                pid = p["project_id"]
                pid = int(pid) if pid else None
                ok = sessions_mgr.set_session_project(sid, pid) or ok
            return self._send(200, json.dumps({"ok": ok, "session": sessions_mgr.get_session(sid)}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def _handle_sessions_delete(self, sid):
        try:
            sid = int(sid)
            ok = sessions_mgr.delete_session(sid)
            return self._send(200, json.dumps({"ok": ok, "id": sid}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    # —————————————— 项目管理（侧边栏「项目」分组对话）——————————————
    def _handle_projects_get(self):
        try:
            items = proj_mgr.list_projects()
            for it in items:
                it["session_count"] = proj_mgr.count_sessions(it["id"])
            return self._send(200, json.dumps({"ok": True, "projects": items}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def _handle_projects_get_one(self, pid):
        try:
            pid = int(pid)
            p = proj_mgr.get_project(pid)
            if not p:
                return self._send(404, json.dumps({"ok": False, "error": "not found"}, ensure_ascii=False))
            p["session_count"] = proj_mgr.count_sessions(pid)
            return self._send(200, json.dumps({"ok": True, "project": p}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def _handle_projects_post(self):
        try:
            p = self._read_json()
            if "_error" in p:
                return self._send(400, json.dumps({"ok": False, "error": p["_error"]}, ensure_ascii=False))
            name = (p.get("name") or "").strip()
            if not name:
                return self._send(400, json.dumps({"ok": False, "error": "name required"}, ensure_ascii=False))
            pid = proj_mgr.create_project(name, p.get("path", "") or "", p.get("emoji") or "📁")
            return self._send(200, json.dumps({"ok": True, "id": pid, "project": proj_mgr.get_project(pid)}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def _handle_projects_delete(self, pid):
        try:
            pid = int(pid)
            proj_mgr.delete_project(pid)
            return self._send(200, json.dumps({"ok": True, "id": pid}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def _handle_sessions_context_usage(self, sid):
        try:
            sid = int(sid)
            usage = sessions_mgr.get_context_usage(sid)
            return self._send(200, json.dumps({"ok": True, **usage}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def _handle_skills_get(self):
        try:
            items = local_skills.list_skills()
            return self._send(200, json.dumps({"ok": True, "skills": items}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    # ---- Skill 搜索 / 安装 ----
    def _handle_skills_search(self):
        try:
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            query = qs.get("q", [""])[0].strip()
            if not query:
                return self._send(200, json.dumps({"ok": True, "items": []}, ensure_ascii=False))
            items = skill_handlers.search_github_skills(query)
            return self._send(200, json.dumps({"ok": True, "items": items}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def _handle_skills_install(self):
        try:
            p = self._read_json()
            if "_error" in p:
                return self._send(400, json.dumps({"ok": False, "error": p["_error"]}, ensure_ascii=False))
            source = (p.get("source") or "").strip()
            if not source:
                return self._send(400, json.dumps({"ok": False, "error": "source required"}, ensure_ascii=False))
            result = skill_handlers.install_skill_from_github(source)
            return self._send(200, json.dumps(result, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def do_GET(self):
        if not self._remote_gate():
            return
        path = self.path.split("?", 1)[0]
        qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        if path in ("/", "/index.html"):
            return self._serve_file("index.html")
        if path == "/api/health":
            # liveness锛氫粎琛ㄨ繘绋嬪瓨娲伙紱ok 鍙栨渶杩戜竴娆¤嚜妫€缂撳瓨锛屼笉瑙?彂澶栭儴鎺㈡祴锛圥0.2 淇?? RC-4锛?
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
                        "theme": config.XIAO6_THEME,
                        "xiao6_theme": config.XIAO6_THEME,
                        "memory_graph": config.MEMORY_GRAPH_ENABLED,
                        "key_present": key_ok,
                        "agent_policy_default": config.AGENT_POLICY_DEFAULT,
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
            # Phase 22锛氬惎鍔ㄨ嚜妫€鎶ュ憡锛堝悗鍙板凡璺戯紝缁撴灉缂撳瓨锛沠orce=1 閲嶇畻锛?
            try:
                import self_diagnosis
                force = qs.get("force", ["0"])[0] in ("1", "true")
                rep = self_diagnosis.get_report(force=force)
                return self._send(200, json.dumps(rep.to_dict(), ensure_ascii=False))
            except Exception as e:
                return self._send(200, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/ready":
            # readiness锛氭湇鍔℃槸鍚?畬鎴愬垵濮嬪寲銆佸姛鑳芥槸鍚?氨缁?紙P0.2 鏂板?锛?
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
        if path == "/api/model":
            return self._handle_model_get()
        if path.startswith("/api/sessions/") and path.endswith("/context_usage"):
            sid = path[len("/api/sessions/"):].rsplit("/", 1)[0]
            return self._handle_sessions_context_usage(sid)
        if path == "/api/sessions":
            return self._handle_sessions_get()
        if path == "/api/projects" or path == "/api/projects/":
            return self._handle_projects_get()
        if path.startswith("/api/projects/"):
            pid = path[len("/api/projects/"):].strip("/")
            return self._handle_projects_get_one(pid)
        if path == "/api/skills":
            return self._handle_skills_get()
        if path == "/api/skills/search":
            return self._handle_skills_search()
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
                        "check_url": "https://github.com/AGI-ZhuangZhou/ZhuangZhou/releases/latest",
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
                # S76: Minimal API adapters for Trace and Memory Write
        if path == "/api/traces":
            try:
                from agent.unified_trace import get_trace_context
                ctx = get_trace_context()
                stats = ctx.get_stats()
                return self._send(200, json.dumps({"ok": True, "traces": stats}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}))
        if path == "/api/memory/write":
            try:
                from notes import create_note
                payload = self._read_json()
                content_text = (payload.get("content") or "").strip()
                title = (payload.get("title") or "记忆").strip() or "记忆"
                tags = payload.get("tags", "")
                if not content_text:
                    return self._send(400, json.dumps({"error": "content required"}))
                note_id = create_note(title, content_text, tags=tags)
                return self._send(200, json.dumps({"ok": True, "note_id": note_id}))
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}))
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
            # Phase 34 Task 4锛氱粺涓€鍚?姩灏辩华鐘舵€侊紙STARTING鈫払ACKEND_READY鈫扐I_READY鈫扐VATAR_READY鈫扲EADY锛?
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
        if path == "/api/terminal/state":
            try:
                import shell_session
                state = shell_session.session_state()
                return self._send(200, json.dumps({"ok": True, "state": state}, ensure_ascii=False))
            except Exception as e:
                return self._send(200, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path.startswith("/api/terminal/"):
            action = path[len("/api/terminal/"):]
            try:
                import shell_session
                if action == "reset":
                    shell_session.reset_session()
                    return self._send(200, json.dumps({"ok": True}, ensure_ascii=False))
                elif action == "output":
                    state = shell_session.session_state()
                    return self._send(200, json.dumps({"ok": True, "stdout": state.get("stdout", ""), "stderr": state.get("stderr", ""), "cwd": state.get("cwd", "")}, ensure_ascii=False))
                else:
                    return self._send(404, json.dumps({"error": "unknown action"}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/workspace/files":
            try:
                sandbox_dir = os.path.join(os.path.dirname(__file__), "sandbox")
                files = []
                if os.path.exists(sandbox_dir):
                    for root, dirs, filenames in os.walk(sandbox_dir):
                        for f in filenames:
                            full = os.path.join(root, f)
                            rel = os.path.relpath(full, sandbox_dir)
                            size = os.path.getsize(full)
                            files.append({"path": rel, "name": f, "size": size})
                return self._send(200, json.dumps({"ok": True, "files": files}, ensure_ascii=False))
            except Exception as e:
                return self._send(200, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path.startswith("/api/workspace/file/"):
            try:
                sandbox_dir = os.path.join(os.path.dirname(__file__), "sandbox")
                rel = path[len("/api/workspace/file/"):]
                full = os.path.normpath(os.path.join(sandbox_dir, rel))
                if not full.startswith(sandbox_dir):
                    return self._send(403, json.dumps({"error": "access denied"}, ensure_ascii=False))
                if not os.path.exists(full):
                    return self._send(404, json.dumps({"error": "not found"}, ensure_ascii=False))
                with open(full, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                return self._send(200, json.dumps({"ok": True, "content": content, "size": len(content)}, ensure_ascii=False))
            except Exception as e:
                return self._send(200, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path.startswith("/api/notes"):
            return self._handle_notes()
        if path == "/api/tasks":
            return self._handle_tasks()
        if path.startswith("/api/goals"):
            # P0-B 路 鍙??鐩?爣蹇?収銆傚?鐢?goals.py锛屼笉澶嶅埗鏁版嵁搴撻€昏緫銆?
            # 浠?GET锛涘啓鎿嶄綔涓€寰嬬粡 Intent Gateway 鈫?Runtime锛屾?澶勪笉鏆撮湶浠讳綍鍐?鐘舵€佹満銆?
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
                # /api/goals/<id> 鍗曟潯
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
        # 鈥斺€?Phase 23 路 Capability OS 缁熶竴鑳藉姏鐩?綍锛圙ET锛屽彧璇伙級鈥斺€?
        if path == "/api/capability_os/catalog":
            try:
                import capability_os
                return self._send(200, json.dumps(capability_os.catalog_view(), ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        # 鈥斺€?Phase 40 路 Capability Foundation 缁熶竴瑙嗗浘锛圙ET锛屽彧璇伙紱鐪熺浉婧愬嚭鍙?級鈥斺€?
        if path == "/api/capability_foundation":
            try:
                import capability_os
                return self._send(200, json.dumps(capability_os.foundation_view(), ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        # 鈥斺€?Phase 24 路 Proactive Agent锛圙ET锛屽彧璇荤姸鎬侊紱鍙?缓璁?笉鎵ц?锛夆€斺€?
        if path == "/api/proactive_agent/status":
            try:
                import proactive_agent
                return self._send(200, json.dumps(proactive_agent.get_status(), ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        # 鈥斺€?Phase 30 路 Self Awareness Loop锛圙ET锛屽彧璇荤姸鎬侊紱鍙??鐭ヤ笉鎵ц?锛夆€斺€?
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
            # Phase 18 路 Personal Context Engine锛堝彧璇昏仛鍚堣?鍥撅紝鐜扮畻鐜板彇涓嶈惤鐩橈級
            if not getattr(config, "FEATURE_PERSONAL_CONTEXT", True):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "Personal Context 鏈?惎鐢"}))
            return self._handle_os_bridge("personal_context")
        if path == "/api/personal_ai":
            # Phase 37.2 路 Personal AI 缁熶竴鐢诲儚锛堢‘璁?绾犳?/钂搁?/鍙屾簮瀵归綈锛涜?鑱氬悎瑙嗗浘锛?
            if not getattr(config, "FEATURE_PERSONAL_AI", True):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "Personal AI 鏈?惎鐢"}))
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
            # 鎸夐渶瑙?彂鏈?湴妯″瀷鍔犺浇锛堥?娆′細涓嬭浇 ~700MB 妯″瀷锛夛紝浠呭綋鐢ㄦ埛涓诲姩鎺㈡祴鏃惰皟鐢?
            return self._send(200, json.dumps(asr_status(), ensure_ascii=False))
        # 鈥斺€?Phase 15/16/17 路 OS Bridge锛堣杽濮旀墭锛岄€昏緫鍏ㄥ湪 os_bridge 涓庢棦鏈夊唴鏍搁噷锛夆€斺€?
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
                        {"docs": knowledge.list_docs(), "stats": knowledge.stats()},
                        ensure_ascii=False,
                    ),
                )
            except Exception as e:
                return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        if path == "/api/devices":
            if not getattr(config, "FEATURE_MULTI_DEVICE", True):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "澶氱?鍚屾?鏈?惎鐢"}))
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
        # 鈥斺€?Phase 20 路 Computer Perception锛堝彧璇?GET锛屽彧寤?Eyes 涓嶅缓 Hands锛夆€斺€?
        if path == "/api/perception":
            if not getattr(config, "FEATURE_PERCEPTION", True):
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled", "error": "Computer Perception 鏈?惎鐢"}, ensure_ascii=False))
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
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled", "error": "Computer Perception 鏈?惎鐢"}, ensure_ascii=False))
            try:
                import perception

                return self._send(200, json.dumps({"ok": True, "screen": perception.screen_observer.screen_info()}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/perception/window":
            if not getattr(config, "FEATURE_PERCEPTION", True):
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled", "error": "Computer Perception 鏈?惎鐢"}, ensure_ascii=False))
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
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled", "error": "Computer Perception 鏈?惎鐢"}, ensure_ascii=False))
            if not getattr(config, "FEATURE_PERCEPTION_OCR", True):
                return self._send(200, json.dumps({"ok": False, "reason_code": "ocr_disabled", "error": "OCR 瀛愬紑鍏虫湭鍚?敤"}, ensure_ascii=False))
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
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled", "error": "Computer Perception 鏈?惎鐢"}, ensure_ascii=False))
            try:
                import perception

                return self._send(200, json.dumps({"ok": True, "text": perception.describe(scope="window")}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if path == "/api/perception/status":
            if not getattr(config, "FEATURE_PERCEPTION", True):
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled", "error": "Computer Perception 鏈?惎鐢"}, ensure_ascii=False))
            try:
                import perception

                return self._send(200, json.dumps({"ok": True, "status": perception.backend_status()}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        # 鈥斺€?Phase 20.5 路 Memory Truth Layer锛堝彧璇?GET锛夆€斺€?
        if path == "/api/memory/truth":
            if not getattr(config, "FEATURE_MEMORY_TRUTH", True):
                return self._send(200, json.dumps({"ok": False, "reason_code": "feature_disabled",
                                                   "error": "Memory Truth Layer 鏈?惎鐢"}, ensure_ascii=False))
            try:
                from memory_intelligence import verify_and_tag
                # db_conn is already imported at module level (line 32)
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
        fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), path.lstrip("/"))
        if os.path.isfile(fp):
            return self._serve_file(path.lstrip("/"))
        self._send(404, json.dumps({"error": "not found"}))

    def _send_head(self, code, ctype="application/json; charset=utf-8", clen=0):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        if clen:
            self.send_header("Content-Length", str(clen))
        self.end_headers()

    def _serve_file_head(self, name):
        fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
        if not os.path.isfile(fp):
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
        fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), path.lstrip("/"))
        if os.path.isfile(fp):
            return self._serve_file_head(path.lstrip("/"))
        self._send_head(404)

    def do_DELETE(self):
        if not self._remote_gate():
            return
        ppath = self.path.split("?", 1)[0]
        if ppath.startswith("/api/tasks/"):
            tid = ppath[len("/api/tasks/"):].strip("/")
            return self._handle_tasks_delete(tid)
        if ppath.startswith("/api/sessions/"):
            sid = ppath[len("/api/sessions/"):].strip("/")
            return self._handle_sessions_delete(sid)
        if ppath.startswith("/api/projects/"):
            pid = ppath[len("/api/projects/"):].strip("/")
            return self._handle_projects_delete(pid)
        return self._send(404, json.dumps({"error": "unknown"}))

    def do_PATCH(self):
        if not self._remote_gate():
            return
        ppath = self.path.split("?", 1)[0]
        if ppath.startswith("/api/tasks/"):
            return self._handle_tasks_patch()
        if ppath.startswith("/api/sessions/"):
            return self._handle_sessions_patch()
        if ppath == "/api/runtime/state":
            return self._handle_runtime_state_patch()
        return self._send(404, json.dumps({"error": "unknown"}))

    def _serve_file(self, name):
        fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
        if not os.path.isfile(fp):
            return self._send(404, json.dumps({"error": "missing " + name}))
        ext = os.path.splitext(name)[1].lower()
        with open(fp, "rb") as f:
            data = f.read()
        self._send(200, data, CONTENT.get(ext, "application/octet-stream"))

    def do_POST(self):
        if not self._remote_gate():
            return
        ppath = self.path.split("?", 1)[0]  # 鍘绘帀鏌ヨ?涓插悗鍐嶈矾鐢憋紙涓?do_GET 涓€鑷达級
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
        if ppath == "/api/tasks":
            return self._handle_tasks_post()
        if ppath == "/api/models":
            return self._handle_models()
        if ppath == "/api/model":
            return self._handle_model_post()
        if ppath == "/api/sessions":
            return self._handle_sessions_post()
        if ppath == "/api/projects":
            return self._handle_projects_post()
        if ppath == "/api/sessions/cleanup":
            return self._handle_sessions_cleanup()
        if ppath == "/api/skills/install":
            return self._handle_skills_install()
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
        if ppath == "/api/knowledge":
            return self._handle_knowledge()
        if ppath == "/api/dev/e2e/approval":
            return self._handle_dev_e2e_approval()
        if ppath == "/api/dev/e2e/scene":
            return self._handle_dev_e2e_scene()
        if ppath == "/api/dev/e2e/timeline":
            return self._handle_dev_e2e_timeline()
        if ppath == "/api/dev/e2e/task":
            return self._handle_dev_e2e_task()
        if ppath == "/api/workbench/active":
            return self._handle_workbench_active()
        if ppath == "/api/workbench/tasks":
            return self._handle_workbench_tasks()
        if ppath.startswith("/api/workbench/task/"):
            task_id = ppath[len("/api/workbench/task/"):].strip("/")
            if "/" in task_id:
                action = task_id.split("/", 1)[1]
                task_id = task_id.split("/", 1)[0]
                return self._handle_workbench_task_control(task_id, action)
            return self._handle_workbench_task_detail()
        if ppath == "/api/workbench/clear":
            return self._handle_workbench_clear()
        if ppath.startswith("/api/terminal/"):
            action = ppath[len("/api/terminal/"):]
            try:
                import shell_session
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)))) if self.headers.get("Content-Length") else {}
                command = body.get("command", "").strip()
                if action == "exec":
                    if not command:
                        return self._send(400, json.dumps({"error": "command required"}, ensure_ascii=False))
                    timeout = body.get("timeout", 30)
                    result = shell_session.run_in_session(command, timeout=timeout)
                    return self._send(200, json.dumps({"ok": True, "result": result}, ensure_ascii=False))
                elif action == "state":
                    state = shell_session.session_state()
                    return self._send(200, json.dumps({"ok": True, "state": state}, ensure_ascii=False))
                elif action == "reset":
                    shell_session.reset_session()
                    return self._send(200, json.dumps({"ok": True}, ensure_ascii=False))
                else:
                    return self._send(404, json.dumps({"error": "unknown action"}, ensure_ascii=False))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if ppath == "/api/devices":
            if not getattr(config, "FEATURE_MULTI_DEVICE", True):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "澶氱?鍚屾?鏈?惎鐢"}))
            return self._handle_devices_post()
        if ppath == "/api/always-on/control":
            if not getattr(config, "FEATURE_ALWAYS_ON", False):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "甯搁┗浼撮殢鏈?惎鐢"}))
            return self._handle_always_on_control()
        if ppath == "/api/boot/avatar-ready":
            # Phase 34 Task 4锛氭?闈㈡暟瀛椾汉绐楀彛灏辩华涓婃姤 鈫?鎺ㄨ繘缁熶竴灏辩华鐘舵€佸埌 AVATAR_READY/READY
            try:
                import beta_boot
                beta_boot.mark_avatar_ready()
                return self._send(200, json.dumps({"ok": True, "state": beta_boot.status()["state"]}, ensure_ascii=False))
            except Exception as e:
                return self._send(200, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        if ppath == "/api/cross-device/relay":
            if not getattr(config, "FEATURE_CROSS_DEVICE", False):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "璺ㄧ?鎺ュ姏鏈?惎鐢"}))
            return self._handle_cross_device_relay()
        if ppath == "/api/mobile/reminder":
            if not getattr(config, "FEATURE_MOBILE_COMPANION", False):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "绉诲姩浼撮殢绔?湭鍚?敤"}))
            return self._handle_mobile_reminder()
        if ppath == "/api/mobile/chat":
            if not getattr(config, "FEATURE_MOBILE_COMPANION", False):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "绉诲姩浼撮殢绔?湭鍚?敤"}))
            return self._handle_mobile_chat()
        if ppath == "/api/focus/window":
            if not getattr(config, "FEATURE_APP_FOCUS", False):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "搴旂敤鐒?偣鏈?惎鐢"}))
            return self._handle_focus_window()
        if ppath == "/api/clipboard/clear":
            if not getattr(config, "FEATURE_CLIPBOARD_SENSE", False):
                return self._send(404, json.dumps({"ok": False, "disabled": True, "error": "鍓?创鏉跨洃鍚?湭鍚?敤"}))
            return self._handle_clipboard_clear()
        if ppath == "/api/memory/backfill":
            return self._handle_memory_backfill()
        if ppath.startswith("/api/notes"):
            return self._handle_notes_post()
        if ppath.startswith("/api/memories"):
            return self._handle_memories_post()
        if ppath == "/api/memory/important-dates":
            return self._handle_important_dates_post()
        if ppath == "/api/memory/query":
            return self._handle_memory_query()
        if ppath == "/api/memory/confirm":
            return self._handle_memory_confirm()
        if ppath == "/api/memory/write":
            return self._handle_memory_write()

        if ppath == "/api/data/import":
            return self._handle_data_import()
        if ppath == "/api/agent/goal":
            return self._handle_agent_goal()
        if ppath == "/api/agent/intent":
            return self._handle_agent_intent()
        if ppath == "/api/agent/approval":
            return self._handle_agent_approval()
        # 鈥斺€?Phase 16/17 路 OS Bridge 鈥斺€?
        if ppath == "/api/vision/capture":
            return self._handle_vision_capture()
        if ppath == "/api/action/plan":
            return self._handle_action_plan()
        if ppath == "/api/action/execute":
            return self._handle_action_execute()
        # 鈥斺€?Phase 23 路 Capability OS锛堝彧璇?鍜ㄨ?灞傦紝缁濅笉鎵ц?浠讳綍鑳藉姏锛夆€斺€?
        if ppath == "/api/capability_os/match":
            return self._handle_capability_match()
        if ppath == "/api/capability_os/plan":
            return self._handle_capability_plan()
        # 鈥斺€?Phase 24 路 Proactive Agent锛氭墜鍔ㄨЕ鍙戜竴杞??娴嬶紙鍙?缓璁?紝涓嶆墽琛岋級鈥斺€?
        if ppath == "/api/proactive_agent/run":
            return self._handle_proactive_run()
        # 鈥斺€?Phase 30 路 Self Awareness Loop锛氭墜鍔ㄨЕ鍙戜竴杞??鐭ワ紙鍙?缓璁?紝涓嶆墽琛岋級鈥斺€?
        if ppath == "/api/self_awareness/run":
            return self._handle_self_awareness_run()
        # 鈥斺€?Phase 30 路 Self Awareness Loop锛氫汉宸ュ?鎵癸紙鍙?敼鐘舵€侊紝涓嶆墽琛岋級鈥斺€?
        if ppath == "/api/self_awareness/decide":
            return self._handle_self_awareness_decide()
        return self._send(404, json.dumps({"error": "unknown"}))

    # 鈥斺€?Phase 23 路 Capability OS 钖勫?鐞嗗櫒锛堝彧璇?鍜ㄨ?锛屼笉鎵ц?锛夆€斺€?
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
    # 鈹€鈹€ 鏃ュ織缁熶竴 + 杞?浆锛坙ogs/小6.log锛?MB脳3锛沴ogging 妯″潡杈撳嚭缁熶竴鍏ユ枃浠讹級鈹€鈹€
    try:
        import logging
        from logging.handlers import RotatingFileHandler

        os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs"), exist_ok=True)
        _lf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "小6.log")
        _rh = RotatingFileHandler(_lf, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        _rh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        logging.basicConfig(level=logging.INFO, handlers=[_rh], force=True)
    except Exception as _le:
        print(f"[鏃ュ織] 閰嶇疆澶辫触锛堜笉褰卞搷鍚?姩锛? {_le}")
    # 鈹€鈹€ Phase 47.1锛氱綉缁滆竟鐣屽姞鍥猴紙榛樿?浠呮湰鏈猴紱0.0.0.0 椤婚厤 REMOTE_ACCESS_TOKEN锛夆攢鈹€
    bind_host = (getattr(config, "BIND_HOST", "127.0.0.1") or "127.0.0.1").strip()
    if bind_host == "0.0.0.0" and not config.REMOTE_ACCESS_TOKEN:
        print("[SECURITY] BIND_HOST=0.0.0.0 浣嗘湭閰嶇疆 REMOTE_ACCESS_TOKEN锛屽洖閫€涓?127.0.0.1锛堜粎鏈?満鍙??闂?級銆")
        bind_host = "127.0.0.1"
    _CORS_ALLOWED_ORIGINS.clear()
    _CORS_ALLOWED_ORIGINS.update(_resolve_cors_origins(bind_host, port))
    if bind_host == "0.0.0.0":
        print(f"[缃戠粶] 鐩戝惉鎵€鏈夌綉鍙?http://0.0.0.0:{port}锛堣繙绋嬭?闂?凡瑕佹眰 REMOTE_ACCESS_TOKEN锛")
    else:
        print(f"[缃戠粶] 浠呯洃鍚?湰鏈?http://{bind_host}:{port}")
    if not config.AGNES_KEY:
        print("[WARN] 鏈??娴嬪埌 AGNES_API_KEY锛岃?鍦?.env 鎴栬?缃?潰鏉夸腑閰嶇疆鍚庨噸鍚?€")
    db_conn().close()
    n = recover_tasks()  # Phase 3.1锛氭妸涓婃? running 琚?腑鏂?殑浠诲姟缈诲洖 open锛屼娇鍏跺彲缁?窇
    if n:
        print(f"[鎭㈠?] {n} 涓??涓?柇鐨勫?姝ヤ换鍔″凡鏍囪?涓哄彲缁?€")
    # 鍑虹珯浠?悊鏀?寔锛氳嫢閰嶇疆浜嗕唬鐞嗗湴鍧€锛屽叏灞€瀹夎? opener锛屼娇鎵€鏈?urllib 璋冪敤
    # 锛圓gnes 妯″瀷/鍚?姩鑷??锛夎嚜鍔ㄨ蛋浠?悊銆傛湰鏈鸿?闂?apihub.agnes-ai.com 闇€缁忔湰鍦?Clash銆?
    _proxy = os.environ.get("ZHUANGZHOU_PROXY_URL") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
    if _proxy:
        import urllib.request as _urllib

        _urllib.install_opener(_urllib.build_opener(_urllib.ProxyHandler({"http": _proxy, "https": _proxy})))
        print(f"[浠?悊] 宸插惎鐢ㄥ叏灞€浠?悊 -> {_proxy}")
    print(f"搴勫懆 鎸囨尌鏍稿績鍚?姩涓?->  http://localhost:{port}")
    print(f"妯″瀷: {config.AGNES_MODEL}  |  鎻愪緵鍟? {config.AGNES_PROVIDER}  |  宸ュ叿: {', '.join(TOOL_FUNCS.keys())}")
    # S79: 启动配置冲突检测（诊断环境变量与 .env 一致性）
    try:
        config.check_env_conflict()
    except Exception as _ce:
        print(f"[WARN] 配置冲突检测失败: {_ce}")
    # 鐭ヨ瘑搴擄細鍚?姩鍗虫壂鎻?+ 寤虹储寮?+ 鍚?敤鏂囦欢 watcher锛堜慨澶嶏細姝ゅ墠浠呭湪璇锋眰鏃舵噿鍔犺浇锛寃atcher 浠庢湭婵€娲伙級
    try:
        import knowledge

        knowledge.load()
        print(f"[鐭ヨ瘑] 宸插姞杞?{knowledge.stats().get('docs', 0)} 绡囨枃妗?紝watcher 宸插惎鐢ㄣ€")
    except Exception as e:
        print(f"[鐭ヨ瘑] 鍔犺浇澶辫触锛堜笉褰卞搷鏍稿績鍚?姩锛? {e}")

    # 鈹€鈹€ P0.1锛氬惎鍔ㄨ嚜妫€鏀逛负鍚庡彴寮傛?锛岄伩鍏嶉樆濉炵?鍙?粦瀹氾紙淇?? RC-2锛夆攢鈹€
    # 绔?彛鍦ㄤ笅鏂?serve_forever() 绔嬪嵆鐩戝惉锛涜嚜妫€鍦ㄥ悗鍙扮嚎绋嬭窇锛屽畬鎴愬悗缃?綅 lifecycle 灏辩华鏍囧織銆?
    # 锛堝師 _async_self_check 宸叉娊绂昏嚦 ai_core.lifecycle.Lifecycle.run_boot_self_check锛?
    lifecycle.run_boot_self_check()
    threading.Thread(target=tick_loop, daemon=True).start()
    print("涓诲姩鏅鸿兘锛圖 鏈燂級蹇冭烦宸插惎鍔?細鍒版湡鎻愰啋 + 姣忔棩绠€鎶ャ€")
    threading.Thread(target=get_geo, daemon=True).start()  # 棰勭儹瀹氫綅/澶╂皵缂撳瓨
    print("瀹氫綅 & 澶╂皵閲囬泦宸插悗鍙伴?鐑?€")
    threading.Thread(target=_warmup_embed, daemon=True).start()  # 鍚戦噺璇?箟 RAG 妯″瀷棰勭儹 + 鍏ㄩ噺鍥炲?
    start_prefetch_scheduler()  # Phase 2锛欰CI 棰勭儹缂撳瓨锛堝ぉ姘?鏂伴椈瀹氭椂棰勫彇锛屾ā鍨嬮啋鏉ュ嵆鐢?級
    print("ACI 棰勭儹缂撳瓨璋冨害宸插惎鍔?紙澶╂皵/鏂伴椈瀹氭椂棰勫彇锛夈€")
    # Phase 8锛氳?闊冲敜閱掕瘝甯搁┗鐩戝惉锛圞WS 榛樿?寮€鍚?椂锛屽悗绔?惎鍔ㄥ嵆鐩戝惉楹?厠椋庯級
    if config.ZHUANGZHOU_KWS_ENABLED.lower() in ("1", "true", "yes"):
        try:
            def _on_wake(transcript):
                """鍞ら啋璇嶅懡涓?悗锛岃嚜鍔ㄥ紑鍚??闊冲?璇濇ā寮忋€"""
                print(f"[KWS] 鍞ら啋璇嶅懡涓? {transcript}")
                from eventbus import publish_system
                publish_system("wakeword_detected", {
                    "transcript": transcript,
                }, source="wakeword")
            wakeword_start(detect_callback=_on_wake)
            print("[KWS] 甯搁┗鐩戝惉宸插惎鍔")
        except Exception as e:
            print(f"[KWS] 鍚?姩澶辫触锛堥潪鑷村懡锛? {e}")
    # 涓?枃鍞ら啋璇嶆?娴嬶紙kws.py锛夛細鍓嶇?璇?煶寰?幆涓?瘡娈垫柇鍙ュ悗 POST /api/kws 鍒ゅ畾锛?
    # openwakeword锛坵akeword.py锛変綔涓鸿嫳鏂?"hey jarvis" fallback 浠嶇敱涓婃柟甯搁┗鐩戝惉鎵胯浇銆?
    if config.ZHUANGZHOU_KWS_ENABLED.lower() in ("1", "true", "yes"):
        try:
            import kws as _kws  # noqa: F401锛堢‘璁ゆā鍧楀彲鍔犺浇锛?api/kws 宸插氨缁?級

            def _kws_loop():
                """鍚庡彴绾跨▼锛氭寔缁??娴?KWS锛堥?鐣欐墿灞曚綅锛屽綋鍓嶇敱鍓嶇? /api/kws 椹卞姩锛夈€"""
                from asr import transcribe_bytes  # noqa: F401锛堝?鐢ㄧ幇鏈?ASR锛?
                # 澶嶇敤鐜版湁楹?厠椋庤緭鍏ワ紙濡傛灉鏈夛級锛涘惁鍒欒烦杩囷紝绛夊緟鍓嶇?璋冪敤 /api/kws
                pass

            # 鍚?姩 KWS 鍚庡彴妫€娴嬶紙濡傛灉楹?厠椋庡彲鐢?級
            # 娉ㄦ剰锛氬?鏋滃墠绔?凡鐢?_voiceLoop锛岃繖閲屽彧闇€鎻愪緵 API 绔?偣
            print("[KWS] 涓?枃鍞ら啋璇嶆?娴嬪凡灏辩华锛堥渶鍓嶇?閰嶅悎璋冪敤 /api/kws锛")
        except Exception as e:
            print(f"[KWS] 鍚?姩澶辫触锛堥潪鑷村懡锛? {e}")
    # 绀句氦鎺ユ敹绔?細椋炰功闀胯繛鎺ワ紙鍙?€夛紝渚濊禆缂哄け/鏈?紑鍚?垯闈欓粯璺宠繃锛屼笉褰卞搷涓婚摼璺?級
    try:
        import social_feishu_ws

        social_feishu_ws.start_feishu_ws()
    except Exception as e:
        print(f"[绀句氦鎺ユ敹] 椋炰功闀胯繛鎺ュ惎鍔ㄨ烦杩囷細{e}")
    # Phase 8锛欰gent Runtime锛堢紪鎺掔姸鎬佹満锛夆€?FEATURE_AGENT_RUNTIME 闂ㄦ帶锛岄粯璁ゅ叧闂?
    if getattr(config, "FEATURE_AGENT_RUNTIME", False):
        try:
            import agent_runtime
            agent_runtime.runtime.start()
            print("[Agent Runtime] 宸插惎鍔?紙缂栨帓鐘舵€佹満 + Policy Engine + Reflector锛夈€")
        except Exception as e:
            print(f"[Agent Runtime] 鍚?姩澶辫触锛堝凡璺宠繃锛? {e}")
    # Phase 21锛欳omputer Action锛堟墜锛夆€?鍚?姩鏈熸妸妯″潡绾у崟渚?PermissionGuard 鍘熷湴鏇挎崲涓?
    # 鐧藉悕鍗曞彈闄愮殑鐪熷疄鎵ц?鍣?楠岃瘉鍣?紝浣?Agent 闂?幆璺?緞涓庣敓浜?REST 璺?緞寮曠敤鍚屼竴 Guard锛堜慨澶?G8/R1锛夈€?
    if getattr(config, "FEATURE_COMPUTER_ACTION", True):
        try:
            import os_bridge
            os_bridge._get_guard()
            print("[Computer Action] 鐧藉悕鍗?Guard 宸插湪鍚?姩鏃舵寕杞斤紙Hand ready锛夈€")
        except Exception as e:
            print(f"[Computer Action] Guard 鎸傝浇澶辫触锛堝凡璺宠繃锛屽姩浣滃皢璧?Mock锛? {e}")
    # Phase 22锛氬惎鍔ㄨ嚜妫€锛堝彧璇伙紝鍚庡彴绾跨▼璺戯紝涓嶉樆濉炵?鍙?粦瀹氾紱缁撴灉瀛?self_diagnosis._latest锛?
    try:
        import self_diagnosis
        self_diagnosis.startup_check()
        print("[Self Diagnosis] 鍚?姩鑷??宸插湪鍚庡彴瑙?彂锛圫tart Diagnosis ready锛夈€")
    except Exception as e:
        print(f"[Self Diagnosis] 鍚?姩鑷??鍒濆?鍖栧け璐ワ紙宸茶烦杩囷級: {e}")
    # Phase 23锛氳兘鍔涙搷浣滅郴缁燂紙鍙??鑱氬悎鏃㈡湁鑳藉姏鐪熺浉婧愶紝鏋勫缓缁熶竴 Capability 娉ㄥ唽琛?紱涓嶆墽琛屼换浣曡兘鍔涳級
    try:
        import capability_os
        capability_os.bootstrap()
        reg = capability_os.get_registry()
        print(f"[Capability OS] 缁熶竴鑳藉姏娉ㄥ唽琛ㄥ凡鏋勫缓锛堝叡 {len(reg)} 椤硅兘鍔涳紝"
              f"鍙?敤 {len(capability_os.available_capabilities())} 椤癸級銆")
    except Exception as e:
        print(f"[Capability OS] 娉ㄥ唽琛ㄦ瀯寤哄け璐ワ紙宸茶烦杩囷級: {e}")
    # Phase 24锛氫富鍔ㄦ櫤鑳藉眰锛堣?瀵?9 婧?鈫?Attention Score 鈫?寤鸿?锛涘彧璇伙紝缁濅笉鎵ц?/鍐欏叆锛?
    try:
        import proactive_agent
        info = proactive_agent.bootstrap()
        print(f"[Proactive Agent] 瑙傚療灞傚凡鍒濆?鍖栵紙scheduler={info.get('scheduler')}锛夈€")
    except Exception as e:
        print(f"[Proactive Agent] 鍒濆?鍖栧け璐ワ紙宸茶烦杩囷級: {e}")
    # Phase 34 Task 4锛氱粺涓€鍚?姩灏辩华鐘舵€佹満鎺ㄨ繘锛堜粎鐘舵€佹爣璁帮紝鏃犲壇浣滅敤锛?
    try:
        import beta_boot
        beta_boot.mark_backend_ready()
        beta_boot.mark_ai_ready()
        print("[Beta Boot] 灏辩华鐘舵€侊細BACKEND_READY / AI_READY锛堢瓑寰呮?闈?Avatar 涓婃姤 AVATAR_READY锛夈€")
    except Exception as e:
        print(f"[Beta Boot] 鐘舵€佹帹杩涘け璐ワ紙宸插拷鐣ワ級: {e}")
    httpd = http.server.ThreadingHTTPServer((bind_host, port), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n宸插叧闂?€")


def _warmup_embed():
    """鍚戦噺璇?箟 RAG锛氶?鐑?ā鍨?+ 鍚戦噺搴撲负绌烘椂鍏ㄩ噺鍥炲?鍘嗗彶绗旇?/璁板繂銆"""
    try:
        import embed

        if not embed.model_ready():
            print("[embed] 妯″瀷缂哄け锛岃烦杩囬?鐑")
            return
        print("[embed] 棰勭儹鍚戦噺妯″瀷鈥")
        embed.embed_doc("棰勭儹")
        try:
            n = embed.backfill_all()
            print("[embed] backfill completed: %s items" % n)
        except Exception as e:
            print("[embed] 鍥炲?寮傚父锛堝彲蹇界暐锛?", e)
    except Exception as e:
        print("[embed] 棰勭儹澶辫触锛堝彲蹇界暐锛?", e)


if __name__ == "__main__":
    main()


