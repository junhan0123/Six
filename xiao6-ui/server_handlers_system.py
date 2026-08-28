# -*- coding: utf-8 -*-
"""server.py 拆分出的 system 域 Handler mixin（由拆分脚本生成，勿手改）。"""
import asyncio
import io
import json
import os
import queue
import re
import sys
import threading
import time
import urllib.request
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
from memory import compress_memory
from context import build_context_prompt
from notes import (create_note, extract_daily_note, extract_persons, extract_profile, get_all_tags, get_backlinks,
                   get_graph, get_note, get_notes, parse_md_links, parse_md_tags, search_notes)
from prefetch import start_prefetch_scheduler
from proactive import SUBSCRIBERS, SUBSCRIBERS_LOCK, flush_pending, make_daily_briefing, tick_loop
from self_check import run_self_check
from social import status as social_status
from sysmon import get_logs, get_sysmon
from tasks import recover_tasks
from ai_core.lifecycle import lifecycle
from ai_core.execution import run as _execution_run
from tools import TOOL_FUNCS, TOOLS, detect_intents, run_fc_loop, select_tools, get_pending_video, clear_pending_video, strip_think_tags
from wakeword import get_status as wakeword_status, start as wakeword_start, stop as wakeword_stop

from server_globals import *
from server_globals import _PROVIDER_PROBE_CACHE, _is_local_peer, _sse_put, _sse_use_eventbus, _proactive_dnd_state, _remote_allowed_tools, _hotspot_modal_payload, _resolve_cors_origins, _ACCESS_LOG_REDACT_RE, _REMOTE_FORBIDDEN, _CORS_ALLOWED_ORIGINS, BRIEFING_LOCK


class SystemMixin:
    def _handle_hotspots(self):
        qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        force = qs.get("refresh", [""])[0] in ("1", "true", "yes")
        viewed = qs.get("viewed", [""])[0] in ("1", "true", "yes")
        try:
            data = get_hotspots(force=force, viewed=viewed)
            self._send(200, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            self._send(
                502,
                json.dumps({"ok": False, "error": str(e), "refreshMinutes": 30, "platforms": {}}, ensure_ascii=False),
            )


    def _handle_weather(self):
        qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        city = qs.get("city", [""])[0].strip() or None
        mode = qs.get("mode", [""])[0].strip() or None
        force = qs.get("refresh", [""])[0] in ("1", "true", "yes")
        lat = qs.get("lat", [""])[0].strip() or None
        lon = qs.get("lon", [""])[0].strip() or None
        # 若前端已拿到浏览器经纬度，优先用它作为 wttr.in 查询坐标
        if lat and lon:
            city = "%s,%s" % (lat, lon)
        try:
            data = get_weather(city=city, mode=mode, force=force)
            self._send(200, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            self._send(
                502,
                json.dumps(
                    {"ok": False, "error": str(e), "refreshMinutes": 30, "card": None, "forecast": []},
                    ensure_ascii=False,
                ),
            )


    def _handle_briefing(self):
        """GET /api/briefing — 聚合今日天气 + 热点 + 待办，供「每日简报」面板使用。"""
        try:
            from datetime import datetime, date
            today = date.today().strftime("%Y-%m-%d")
            # 天气（compact 模式，含今日对齐后的 condition/high/low）
            weather = {"city": "", "condition": "", "temp": "", "high": "", "low": ""}
            try:
                w = get_weather(mode="compact")
                card = w.get("card") or {}
                weather = {
                    "city": w.get("city") or card.get("city") or "",
                    "condition": card.get("condition") or "",
                    "temp": card.get("temp") or "",
                    "high": card.get("high") or "",
                    "low": card.get("low") or "",
                }
            except Exception as e:
                weather["error"] = str(e)
            # 热点：合并各平台，按 rank 取前 6
            hotspots = []
            try:
                hs = get_hotspots()
                platforms = hs.get("platforms") or {}
                merged = []
                for _plat, items in platforms.items():
                    for it in (items or []):
                        merged.append(it)
                merged.sort(key=lambda x: (x.get("rank") or 99))
                hotspots = [
                    {
                        "platform": i.get("platform"),
                        "rank": i.get("rank"),
                        "text": i.get("text"),
                        "heat": i.get("heat"),
                        "url": i.get("url"),
                    }
                    for i in merged[:6]
                ]
            except Exception as e:
                hotspots = [{"error": str(e)}]
            # 待办（仅未完成的）
            tasks = []
            try:
                tasks = get_tasks(only_open=True, limit=10) or []
            except Exception:
                tasks = []
            data = {
                "date": today,
                "generatedAt": datetime.now().strftime("%H:%M"),
                "weather": weather,
                "hotspots": hotspots,
                "tasks": tasks,
                "suggestions": [],
            }
            # Phase 4-C V2：今日建议段（停滞 / 临近目标）注入简报面板
            try:
                if getattr(config, "FEATURE_PROACTIVE_V2", False):
                    from proactive import collect_today_suggestions

                    data["suggestions"] = collect_today_suggestions()
            except Exception:
                pass
            self._send(200, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


    def _handle_audit(self):
        """GET /api/audit[?limit=50] 只读列出工具审计日志（Phase 3.2）。"""
        qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        limit = max(1, min(200, int(qs.get("limit", ["50"])[0] or 50)))
        try:
            conn = db_conn()
            rows = conn.execute(
                "SELECT ts,tool,summary,status,risk,source,duration_ms FROM tool_audit ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
            data = [
                {
                    "ts": r[0],
                    "tool": r[1],
                    "summary": r[2],
                    "status": r[3],
                    "risk": r[4],
                    "source": r[5],
                    "duration_ms": r[6],
                }
                for r in rows
            ]
            self._send(200, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))


    def _handle_wakeword(self):
        """GET /api/wakeword[?action=start|stop] — 常驻语音唤醒词状态/控制（P8 脚手架）。"""
        qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        action = qs.get("action", ["status"])[0]
        try:
            if action == "start":
                data = wakeword_start()
            elif action == "stop":
                data = wakeword_stop()
            else:
                data = wakeword_status()
            self._send(200, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))


    def _handle_external(self):
        """GET /api/external — Phase 4 外部 provider 配置状态。

        仅暴露布尔/provider 名，绝不泄露任何密钥本身。
        """
        try:
            data = {
                "media": media_status(),
                "social": social_status(),
                "asr": asr_status(),
                "desktop": {
                    "built": True,
                    "note": "Electron 桌面壳已构建（electron/ 目录：拉起后端+托盘+单实例+原生桥，前端零改动）",
                },
            }
            self._send(200, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))


    def _handle_alert_config_get(self):
        """GET /api/alert-config — 返回舆情告警配置（关键词 / 渠道 / 可用渠道）。"""
        try:
            import json as _json
            conn = db_conn()
            kw_row = conn.execute("SELECT value FROM meta WHERE key='alert_keywords'").fetchone()
            ch_row = conn.execute("SELECT value FROM meta WHERE key='alert_channels'").fetchone()
            conn.close()
            keywords = _json.loads(kw_row[0]) if kw_row and kw_row[0] else []
            channels = _json.loads(ch_row[0]) if ch_row and ch_row[0] else ["ui"]
            return self._send(200, _json.dumps({
                "keywords": keywords,
                "channels": channels,
                "available_channels": [
                    {"id": "ui", "label": "浏览器推送", "ready": True},
                    {"id": "qq", "label": "QQ 消息", "ready": False},
                    {"id": "email", "label": "邮件", "ready": False},
                ],
            }, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}))


    def _handle_alert_config_post(self):
        """POST /api/alert-config — 保存舆情告警配置（关键词列表 / 渠道列表）。"""
        try:
            import json as _json
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = _json.loads(raw.decode("utf-8", "replace") or "{}")
            except Exception:
                body = _json.loads(raw.decode("latin-1", "replace") or "{}")
            keywords = body.get("keywords")
            channels = body.get("channels")
            if isinstance(keywords, (list, tuple)):
                kw = _json.dumps(list(keywords), ensure_ascii=False)
            elif isinstance(keywords, str):
                items = [k.strip() for k in keywords.replace("\n", ",").split(",") if k.strip()]
                kw = _json.dumps(items, ensure_ascii=False)
            else:
                kw = "[]"
            if isinstance(channels, (list, tuple)):
                ch = _json.dumps(list(channels), ensure_ascii=False)
            else:
                ch = "[]"
            conn = db_conn()
            conn.execute(
                "INSERT INTO meta(key,value) VALUES('alert_keywords',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (kw,))
            conn.execute(
                "INSERT INTO meta(key,value) VALUES('alert_channels',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (ch,))
            conn.commit()
            conn.close()
            return self._send(200, _json.dumps({
                "ok": True,
                "keywords": _json.loads(kw),
                "channels": _json.loads(ch),
            }, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}))


    def _handle_always_on_status(self):
        """GET /api/always-on/status — 常驻伴随状态（CPU/降级/运行）。"""
        try:
            from always_on import get_controller

            ctrl = get_controller(cpu_limit=getattr(config, "ALWAYS_ON_CPU_LIMIT", 5))
            snap = ctrl.sample_and_maybe_degrade() if ctrl.is_running() else ctrl.status()
            return self._send(
                200,
                json.dumps(
                    {
                        "ok": True,
                        "enabled": True,
                        "running": snap.get("running", False),
                        "degraded": snap.get("degraded", False),
                        "cpu_percent": snap.get("cpu_percent", 0.0),
                        "cpu_limit": snap.get("cpu_limit", getattr(config, "ALWAYS_ON_CPU_LIMIT", 5)),
                    },
                    ensure_ascii=False,
                ),
            )
        except Exception as e:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_always_on_control(self):
        """POST /api/always-on/control — {action:"start"|"stop"}。"""
        try:
            payload = self._read_json()
            if "_error" in payload:
                return self._send(400, json.dumps({"error": payload["_error"]}, ensure_ascii=False))
            action = (payload.get("action") or "").strip().lower()
            if action not in ("start", "stop"):
                return self._send(400, json.dumps({"ok": False, "error": "action 须为 start|stop"}, ensure_ascii=False))
            from always_on import get_controller

            ctrl = get_controller(cpu_limit=getattr(config, "ALWAYS_ON_CPU_LIMIT", 5))
            ok = ctrl.start() if action == "start" else ctrl.stop()
            return self._send(
                200,
                json.dumps({"ok": bool(ok), "action": action, "running": ctrl.is_running()}, ensure_ascii=False),
            )
        except Exception as e:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_cross_device_status(self):
        """GET /api/cross-device/status — 跨端接力注册表状态。"""
        try:
            from cross_device import get_relay

            st = get_relay().status()
            return self._send(200, json.dumps({"ok": True, "enabled": True, **st}, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_cross_device_relay(self):
        """POST /api/cross-device/relay — {action:"create"|"claim", ...}。"""
        try:
            payload = self._read_json()
            if "_error" in payload:
                return self._send(400, json.dumps({"error": payload["_error"]}, ensure_ascii=False))
            action = (payload.get("action") or "").strip().lower()
            from cross_device import get_relay

            relay = get_relay()
            if action == "create":
                state = payload.get("state") or {}
                if not isinstance(state, dict):
                    return self._send(400, json.dumps({"ok": False, "error": "state 必须为对象"}))
                pkg = relay.create(state, str(payload.get("from_device") or "unknown"), to_device=payload.get("to_device"))
                return self._send(200, json.dumps({"ok": True, **pkg}, ensure_ascii=False))
            if action == "claim":
                hid = (payload.get("handoff_id") or "").strip()
                if not hid:
                    return self._send(400, json.dumps({"ok": False, "error": "handoff_id 必填"}))
                ok, err, rec = relay.claim(hid, str(payload.get("to_device") or "unknown"))
                if not ok:
                    return self._send(409, json.dumps({"ok": False, "error": err, "handoff": rec}, ensure_ascii=False))
                return self._send(200, json.dumps({"ok": True, "handoff": rec}, ensure_ascii=False))
            return self._send(400, json.dumps({"ok": False, "error": "action 须为 create|claim"}))
        except Exception as e:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_mobile_briefing(self):
        """GET /api/mobile/briefing — 移动端轻量简报（紧凑、适合小屏）。"""
        try:
            from mobile import build_briefing

            conn = db_conn()
            rem_rows = conn.execute("SELECT due_ts,content,done FROM reminders ORDER BY due_ts ASC").fetchall()
            conn.close()
            reminders = [{"due": d, "content": c, "done": bool(done)} for d, c, done in rem_rows]
            geo = get_geo() or {}
            weather = geo.get("weather") or {}
            briefing = build_briefing(
                greeting=f"{config.AI_DISPLAY_NAME} 已为你备好",
                reminders=reminders,
                weather=weather,
            )
            return self._send(200, json.dumps({"ok": True, "enabled": True, "briefing": briefing}, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_mobile_reminder(self):
        """POST /api/mobile/reminder — 向移动伴随端推送一条提醒（经 EventBus 同步）。"""
        try:
            payload = self._read_json()
            if "_error" in payload:
                return self._send(400, json.dumps({"error": payload["_error"]}, ensure_ascii=False))
            content = (payload.get("content") or "").strip()
            if not content:
                return self._send(400, json.dumps({"ok": False, "error": "content 必填"}))
            from mobile import sync_event

            ok = sync_event("mobile", {"type": "reminder", "content": content, "due": payload.get("due")})
            return self._send(200, json.dumps({"ok": True, "synced": bool(ok), "content": content}, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_mobile_chat(self):
        """POST /api/mobile/chat — 移动端发起对话，经 EventBus 同步到桌面接力（不改 /api/chat）。"""
        try:
            payload = self._read_json()
            if "_error" in payload:
                return self._send(400, json.dumps({"error": payload["_error"]}, ensure_ascii=False))
            message = (payload.get("message") or "").strip()
            if not message:
                return self._send(400, json.dumps({"ok": False, "error": "message 必填"}))
            from mobile import sync_event

            ok = sync_event("mobile", {"type": "chat", "message": message})
            return self._send(200, json.dumps({"ok": True, "synced": bool(ok), "relayed": True}, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_calendar_events(self):
        """GET /api/calendar/events — 系统日历事件列表（Windows 专属，默认关闭）。"""
        try:
            from calendar_reader import read_calendar

            events = read_calendar(limit=20)
            return self._send(200, json.dumps({"ok": True, "enabled": True, "events": events}, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_calendar_next(self):
        """GET /api/calendar/next — 最近的未来日历事件。"""
        try:
            from calendar_reader import next_event, read_calendar

            events = read_calendar(limit=20)
            nxt = next_event(events)
            return self._send(200, json.dumps({"ok": True, "enabled": True, "next": nxt}, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_focus_app(self):
        """GET /api/focus/app — 当前前台应用焦点摘要。"""
        try:
            from app_focus import get_foreground_app, summarize_app

            info = get_foreground_app()
            return self._send(200, json.dumps({"ok": True, "enabled": True, "focus": summarize_app(info)}, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_focus_window(self):
        """POST /api/focus/window — 归一化给定窗口描述（纯函数 summarize_app 经 HTTP 暴露）。"""
        try:
            payload = self._read_json()
            if "_error" in payload:
                return self._send(400, json.dumps({"error": payload["_error"]}, ensure_ascii=False))
            from app_focus import summarize_app

            info = payload.get("window") or {}
            return self._send(200, json.dumps({"ok": True, "enabled": True, "summary": summarize_app(info)}, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_clipboard_history(self):
        """GET /api/clipboard/history — 剪贴板内存历史。"""
        try:
            from clipboard_monitor import get_history

            hist = get_history().recent(limit=20)
            return self._send(200, json.dumps({"ok": True, "enabled": True, "history": hist}, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_clipboard_clear(self):
        """POST /api/clipboard/clear — 清空剪贴板历史。"""
        try:
            from clipboard_monitor import get_history

            n = get_history().clear()
            return self._send(200, json.dumps({"ok": True, "cleared": n}, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_knowledge(self):
        """P4-B 知识库写入/删除端点。

        POST {action:"upload", title, text, source?}            → 入库一篇文档
        POST {action:"archive", session, title?}                 → 归档一段对话
        DELETE ?id=<doc_id>                                      → 删除一篇文档
        """
        try:
            import knowledge

            if self.command == "DELETE":
                qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
                did = int((qs.get("id", ["0"])[0] or "0"))
                if not did:
                    return self._send(400, json.dumps({"error": "id required"}))
                ok = knowledge.delete_doc(did)
                return self._send(200, json.dumps({"ok": ok}, ensure_ascii=False))
            payload = self._read_json()
            if "_error" in payload:
                return self._send(400, json.dumps({"error": payload["_error"]}))
            action = (payload.get("action") or "upload").strip()
            if action == "archive":
                session = (payload.get("session") or "").strip()
                if not session:
                    return self._send(400, json.dumps({"error": "session required"}))
                doc_id = knowledge.archive_conversation(session, payload.get("title") or "")
                return self._send(
                    200,
                    json.dumps({"ok": bool(doc_id), "doc_id": doc_id}, ensure_ascii=False),
                )
            # 默认：upload 一篇文档（text 必填）
            title = (payload.get("title") or "未命名文档").strip()[:120]
            text = (payload.get("text") or "").strip()
            if not text:
                return self._send(400, json.dumps({"error": "text required"}))
            doc_id = knowledge.ingest_document(title, text, payload.get("source") or "upload")
            return self._send(
                200,
                json.dumps({"ok": bool(doc_id), "doc_id": doc_id}, ensure_ascii=False),
            )
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))

    # ---------- Phase 8：Agent Runtime 端点 ----------

    def _handle_agent_state(self):
        """GET /api/agent/state — 遥测用：返回 runtime 当前状态。"""
        if not getattr(config, "FEATURE_AGENT_RUNTIME", False):
            return self._send(200, json.dumps({"enabled": False, "state": "disabled"}, ensure_ascii=False))
        try:
            import agent_runtime
            return self._send(200, json.dumps({"enabled": True, **agent_runtime.runtime.get_state()}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))

    # ---------- R8-P3 · Agent API Surface（恢复悬空端点 /api/agent/*）----------
    # API → Agent Runtime 完整控制链，全部复用既有系统（禁止直连工具）：
    #   goal     → GoalSystem（agent_runtime.submit_goal → goals.create_goal）
    #   intent   → IntentGateway（intent_gateway.run_intent_gateway → GDE → submit_goal）
    #   approval → Approval 流程（policy_engine.resolve 唤醒挂起审批单）

    def _handle_agent_goal(self):
        """POST /api/agent/goal — 提交目标到 Agent Runtime（GoalSystem 单一路径）。

        载荷：{"title": str, "description": str(可选), "intentId": str(可选)}
        响应：200 {"ok": True, "goalId": int, "title": str}
        错误：400 参数缺失/非法 JSON；404 feature 关闭；500 内部异常
        """
        if not getattr(config, "FEATURE_AGENT_RUNTIME", False):
            return self._send(404, json.dumps(
                {"ok": False, "disabled": True, "error": "Agent Runtime 未启用"}, ensure_ascii=False))
        payload = self._read_json()
        if "_error" in payload:
            return self._send(400, json.dumps({"ok": False, "error": payload["_error"]}, ensure_ascii=False))
        title = (payload.get("title") or "").strip()
        if not title:
            return self._send(400, json.dumps({"ok": False, "error": "缺少 goal title"}, ensure_ascii=False))
        description = (payload.get("description") or "").strip()
        intent_id = payload.get("intentId")
        try:
            import agent_runtime
            rt = agent_runtime.runtime
            if not rt._running:
                rt.start()  # 幂等：保证提交后目标能被编排执行
            goal_id = rt.submit_goal(title=title, description=description, intent_id=intent_id)
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": f"目标创建失败：{e}"}, ensure_ascii=False))
        if not goal_id:
            return self._send(500, json.dumps({"ok": False, "error": "目标创建失败（返回空）"}, ensure_ascii=False))
        return self._send(200, json.dumps({"ok": True, "goalId": goal_id, "title": title}, ensure_ascii=False))

    def _handle_agent_intent(self):
        """POST /api/agent/intent — 用户意图经 IntentGateway（GDE 识别/决策 → 建目标）。

        载荷：{"text": str, "source": str(可选)}
        响应：200 {"ok": True, "intentId", "action", "classification", "confidence",
                   "title", "goalId", "reason"}（action ∈ create|propose|resume|skip）
        错误：400 参数缺失/非法 JSON；404 feature 关闭；500 内部异常
        """
        if not getattr(config, "FEATURE_AGENT_RUNTIME", False):
            return self._send(404, json.dumps(
                {"ok": False, "disabled": True, "error": "Agent Runtime 未启用"}, ensure_ascii=False))
        payload = self._read_json()
        if "_error" in payload:
            return self._send(400, json.dumps({"ok": False, "error": payload["_error"]}, ensure_ascii=False))
        text = (payload.get("text") or "").strip()
        if not text:
            return self._send(400, json.dumps({"ok": False, "error": "缺少 intent text"}, ensure_ascii=False))
        source = (payload.get("source") or "api").strip()
        try:
            import agent_runtime
            if not agent_runtime.runtime._running:
                agent_runtime.runtime.start()  # 幂等：保证 create 决策的目标可被编排执行
            from intent_gateway import run_intent_gateway
            result = run_intent_gateway(text, source=source)
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": f"意图处理失败：{e}"}, ensure_ascii=False))
        return self._send(200, json.dumps({"ok": True, **result}, ensure_ascii=False))

    def _handle_agent_approval(self):
        """POST /api/agent/approval — Approval 流程：唤醒挂起的审批单。

        UI 契约（冻结快照 zz-workspace.js）：
            POST /api/agent/approval?ticket=<ticket>&decision=<approve|reject>
        响应：200 {"ok": True, "ticket", "decision"} / 400 非法参数 / 404 未知或过期 ticket / 500 内部异常
        """
        qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        ticket = (qs.get("ticket") or [""])[0].strip()
        decision = (qs.get("decision") or [""])[0].strip().lower()
        if not ticket or decision not in ("approve", "reject"):
            return self._send(400, json.dumps(
                {"ok": False, "error": "ticket/decision 缺失或非法（decision ∈ approve|reject）"},
                ensure_ascii=False))
        try:
            from policy_engine import resolve
            if not resolve(ticket, decision):
                return self._send(404, json.dumps(
                    {"ok": False, "error": "未知或已过期的审批单"}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": f"审批处理失败：{e}"}, ensure_ascii=False))
        return self._send(200, json.dumps({"ok": True, "ticket": ticket, "decision": decision}, ensure_ascii=False))

    # ---------- Phase 11 全息 HUD 端点 ----------

    def _handle_hud_config(self):
        """GET /api/hud/config — 返回 HUD 相关特性开关与性能门控阈值（前端据此决定 init 哪些层）。"""
        try:
            cfg = {
                "hud_ring": bool(getattr(config, "FEATURE_HUD_RING", False)),
                "glance_card": bool(getattr(config, "FEATURE_GLANCE_CARD", False)),
                "avatar_scene": bool(getattr(config, "FEATURE_AVATAR_SCENE", False)),
                "perf_threshold": int(getattr(config, "HUD_RING_PERF_THRESHOLD", 5)),
            }
            return self._send(200, json.dumps(cfg, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_hud_state(self):
        """GET /api/hud/state — 返回当前 HUD 推导态（agent 编排态映射），供前端首屏校正光环。

        Phase 34 Task 3：扩展为 richer 映射，使桌面数字人能点亮 EXECUTING 态：
        - agent_runtime 状态机 IDLE/PLANNING/EXECUTING/REFLECTING（只读 get_state，不改核心逻辑）。
        - EXECUTING → "executing"（桌宠执行中）；PLANNING/REFLECTING → "thinking"（思考/规划中）；
          IDLE → "idle"。SPEAKING 由前端 TTS 播放态驱动（主 UI setOrb），桌面宠物的 SPEAKING
          待后端接入 TTS 信号后自动点亮；当前状态词表 + 控制器 + CSS 降级均已就绪。
        """
        try:
            state = "idle"
            goal_id = None
            progress = None
            if getattr(config, "FEATURE_AGENT_RUNTIME", False):
                try:
                    import agent_runtime
                    rt = agent_runtime.runtime.get_state()
                    rt_state = (rt.get("state") or "IDLE").upper()
                    if rt_state == "EXECUTING":
                        state = "executing"
                    elif rt_state in ("PLANNING", "REFLECTING"):
                        state = "thinking"
                    else:
                        state = "idle"
                    cur = rt.get("current_goal")
                    if cur:
                        goal_id = cur.get("id")
                        progress = cur.get("progress")
                except Exception:
                    pass
            return self._send(200, json.dumps(
                {"state": state, "goal_id": goal_id, "progress": progress}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_devices_get(self):
        """GET /api/devices — 列出已注册设备（模块4 跨设备协同脚手架）。"""
        try:
            from devices import list_devices

            return self._send(200, json.dumps({"ok": True, "devices": list_devices()}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}))


    def _handle_devices_post(self):
        """POST /api/devices — 注册/心跳一个设备。body: {device_id,name,meta} 或 {device_id,heartbeat:true}"""
        try:
            payload = self._read_json()
            if "_error" in payload:
                return self._send(400, json.dumps({"error": payload["_error"]}))
            from devices import register, heartbeat

            did = (payload.get("device_id") or "").strip()
            if not did:
                return self._send(400, json.dumps({"error": "device_id required"}))
            if payload.get("heartbeat"):
                heartbeat(did)
                return self._send(200, json.dumps({"ok": True, "heartbeat": True}))
            dev = register(did, payload.get("name"), payload.get("meta"))
            return self._send(200, json.dumps({"ok": True, "device": dev}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}))


    def _handle_config_get(self):
        """返回前端设置面板所需的非敏感配置与状态。"""
        import media

        return self._send(
            200,
            json.dumps(
                {
                    "ai_name": config.AI_DISPLAY_NAME,
                    "theme": config.THEME,
                    # Phase I · 发布通道（development | release）：前端据此收起开发者入口。
                    # 非敏感、只读；沿用既有 /api/config，不新增端点。
                    "build_channel": getattr(config, "BUILD_CHANNEL", "development"),
                    "memory_graph": config.MEMORY_GRAPH_ENABLED,
                    "llm": {
                        "provider": config.AGNES_PROVIDER,
                        "active": config.ACTIVE_LLM,
                        "base_url": config.AGNES_BASE,
                        "model": config.AGNES_MODEL,
                        "key_present": bool(config.AGNES_KEY),
                        "reasoning": config.AGNES_REASONING,
                        "llm2": {
                            "base_url": config.LLM2_BASE_URL,
                            "model": config.LLM2_MODEL,
                            "key_present": bool(config.LLM2_API_KEY),
                        },
                    },
                    # ── Phase 10-C：Provider 框架状态（不含任何 API Key；spec §七）──
                    "providers": [
                        {
                            "id": s["id"],
                            "label": s["label"],
                            "kind": s["kind"],
                            "privacy_class": s["privacy_class"],
                            "auth_required": s["auth_required"],
                            "openai_compatible": s["openai_compatible"],
                            "user_selectable": s["user_selectable"],
                            "default_base_url": s["default_base_url"],
                            "hosts": s["hosts"],
                            "probe_path": s["probe_path"],
                            "capabilities": s["capabilities"],
                            "configured": b["configured"],
                            # ── G-11：供设置面板回填已保存的连接参数（非敏感）──
                            # ⚠ 仅 base_url / model；api_key 永不下发（spec §七）
                            "resolved_base_url": b["base_url"],
                            "resolved_model": b["model"],
                        }
                        for s, b in (
                            (sp, resolve_provider(sp["id"])) for sp in provider_registry.list_specs()
                        )
                    ],
                    "active_provider": config.ACTIVE_LLM,
                    "fallback_enabled": False,
                    "provider_probe": dict(_PROVIDER_PROBE_CACHE),
                    "tts": {
                        "backend": config.TTS_BACKEND,
                        "voice": config.TTS_VOICE,
                        "rate": config.TTS_RATE,
                        "sovits_url": config.GPT_SOVITS_URL,
                        "sovits_ref": config.GPT_SOVITS_REF_AUDIO,
                        "sovits_prompt": config.GPT_SOVITS_PROMPT_TEXT,
                    },
                    "media": {
                        **media.status(),
                        "group_present": bool(config.MINIMAX_GROUP_ID),
                    },
                    "web_search": {
                        "engine": config.WEB_SEARCH_ENGINE,
                        "key_present": bool(config.WEB_SEARCH_KEY),
                        "serper_present": bool(config.WEB_SEARCH_SERPER_KEY),
                        "jina_present": bool(config.WEB_SEARCH_JINA_KEY),
                        "brave_present": bool(config.WEB_SEARCH_BRAVE_KEY),
                        "searxng_url": config.WEB_SEARCH_SEARXNG_URL,
                    },
                    "social": {
                        **social_status(),
                        "inbound_enabled": bool(config.SOCIAL_INBOUND_TOKEN),
                        "feishu_ws_enabled": config.FEISHU_WS_ENABLED in ("1", "true", "yes"),
                    },
                    "tool_factory": {
                        "enabled": config.TOOL_FACTORY_ENABLED in ("1", "true", "yes"),
                        "command_enabled": config.TOOL_FACTORY_COMMAND_ENABLED in ("1", "true", "yes"),
                        "domain_allowlist": config.TOOL_FACTORY_DOMAIN_ALLOWLIST,
                    },
                    "agent_delegate": {
                        "enabled": config.AGENT_DELEGATE_ENABLED in ("1", "true", "yes"),
                        "auto": config.AGENT_DELEGATE_AUTO in ("1", "true", "yes"),
                        "timeout": config.AGENT_DELEGATE_TIMEOUT,
                        "cli_present": bool(config.AGENT_DELEGATE_CLI),
                    },
                    "remote": {
                        "token_set": bool(config.REMOTE_ACCESS_TOKEN),
                        "tool_whitelist": config.REMOTE_TOOL_WHITELIST,
                    },
                    "security": config.security_policy(),
                    "proxy": {
                        "url": config.ZHUANGZHOU_PROXY_URL,
                    },
                    "asr": {
                        "provider": config.ASR_PROVIDER,
                        "local_supported": True,
                        "aliyun_present": bool(config.ALIYUN_ASR_KEY and config.ALIYUN_ASR_TOKEN),
                        "xfyun_present": bool(
                            config.XFYUN_ASR_APPID and config.XFYUN_ASR_APIKEY and config.XFYUN_ASR_APISECRET
                        ),
                        "volcengine_present": bool(config.VOLCENGINE_ASR_KEY and config.VOLCENGINE_ASR_SECRET),
                    },
                    "version": {
                        "current": config.APP_VERSION,
                        "app_name": config.AI_DISPLAY_NAME,
                    },
                    "feature_premium_ui": getattr(config, "FEATURE_PREMIUM_UI", True),
                    "feature_knowledge_platform": getattr(config, "FEATURE_KNOWLEDGE_PLATFORM", True),
                    "feature_proactive_v2": getattr(config, "FEATURE_PROACTIVE_V2", True),
                    "feature_multi_device": getattr(config, "FEATURE_MULTI_DEVICE", True),
                    "feature_always_on": getattr(config, "FEATURE_ALWAYS_ON", False),
                    "feature_cross_device": getattr(config, "FEATURE_CROSS_DEVICE", False),
                    "feature_mobile_companion": getattr(config, "FEATURE_MOBILE_COMPANION", False),
                    "feature_calendar_sense": getattr(config, "FEATURE_CALENDAR_SENSE", False),
                    "feature_app_focus": getattr(config, "FEATURE_APP_FOCUS", False),
                    "feature_clipboard_sense": getattr(config, "FEATURE_CLIPBOARD_SENSE", False),
                    "feature_persona": getattr(config, "FEATURE_PERSONA", True),
                    "feature_memory_distill": getattr(config, "FEATURE_MEMORY_DISTILL", False),
                    "kws_enabled": getattr(config, "ZHUANGZHOU_KWS_ENABLED", "true").lower() in ("1", "true", "yes"),
                    # ── Phase 9 B1/B2：主动智能引擎 ──
                    "feature_proactive_engine": getattr(config, "FEATURE_PROACTIVE_ENGINE", True),
                    "proactive_suggestion_mode": os.environ.get("PROACTIVE_SUGGESTION_MODE", "ask"),
                    "proactive_window": [
                        int(os.environ.get("PROACTIVE_WINDOW_START", "8")),
                        int(os.environ.get("PROACTIVE_WINDOW_END", "22")),
                    ],
                    "proactive_quiet": [
                        int(os.environ.get("PROACTIVE_QUIET_START", "23")),
                        int(os.environ.get("PROACTIVE_QUIET_END", "7")),
                    ],
                    "proactive_dnd": _proactive_dnd_state(),
                },
                ensure_ascii=False,
            ),
        )


    def _handle_config_post(self):
        """安全更新 .env 中的配置。API Key 仅在传入非空值时覆盖。"""
        payload = self._read_json()
        if "_error" in payload:
            return self._send(400, json.dumps({"error": payload["_error"]}, ensure_ascii=False))

        # 前端可用键 -> .env 键名
        allowed = {
            "AGNES_PROVIDER",
            "AGNES_BASE_URL",
            "AGNES_MODEL",
            "AGNES_API_KEY",
            "AGNES_REASONING",
            "AI_DISPLAY_NAME",
            "ZHUANGZHOU_THEME",
            "ZHUANGZHOU_MEMORY_GRAPH",
            "ZhuangZhou_TTS_VOICE",
            "ZhuangZhou_TTS_RATE",
            "ZHUANGZHOU_TTS_BACKEND",
            "ZHUANGZHOU_GPT_SOVITS_URL",
            "ZHUANGZHOU_GPT_SOVITS_REF",
            "ZHUANGZHOU_GPT_SOVITS_PROMPT",
            "ZHUANGZHOU_PROXY_URL",
            "ZHUANGZHOU_WEB_SEARCH_KEY",
            "ZHUANGZHOU_WEB_SEARCH_ENGINE",
            "ZHUANGZHOU_MEDIA_PROVIDER",
            "MINIMAX_API_KEY",
            "MINIMAX_GROUP_ID",
            "ZHUANGZHOU_ASR_PROVIDER",
            "ALIYUN_ASR_KEY",
            "ALIYUN_ASR_TOKEN",
            "XFYUN_ASR_APPID",
            "XFYUN_ASR_APIKEY",
            "XFYUN_ASR_APISECRET",
            "VOLCENGINE_ASR_KEY",
            "VOLCENGINE_ASR_SECRET",
            "HOTDATA_KEY",
            "DISCORD_BOT_TOKEN",
            "FEISHU_APP_ID",
            "FEISHU_APP_SECRET",
            "ZHUANGZHOU_DEFAULT_CITY",
            "ZHUANGZHOU_LOCATION",
            "ZHUANGZHOU_SANDBOX_FILE",
            "ZHUANGZHOU_SANDBOX_EXEC",
            "ZHUANGZHOU_BLOCKED_TOOLS",
            "ZHUANGZHOU_WEB_SEARCH_SERPER_KEY",
            "ZHUANGZHOU_WEB_SEARCH_JINA_KEY",
            "ZHUANGZHOU_WEB_SEARCH_BRAVE_KEY",
            "ZHUANGZHOU_WEB_SEARCH_SEARXNG_URL",
            "LLM2_BASE_URL",
            "LLM2_API_KEY",
            "LLM2_MODEL",
            "LLM2_PROVIDER",
            "ACTIVE_LLM",
            # ── Phase 10-C / G-11：本地 Provider 连接参数（无 API Key；仅 127.0.0.1 白名单端点）──
            "OLLAMA_BASE_URL",
            "OLLAMA_MODEL",
            "LMSTUDIO_BASE_URL",
            "LMSTUDIO_MODEL",
            "MLX_BASE_URL",
            "MLX_MODEL",
            "ZHUANGZHOU_KWS_ENABLED",
            "ZHUANGZHOU_WAKE_PHRASE",
            "ZHUANGZHOU_KWS_SENSITIVITY",
            "ZHUANGZHOU_VOSK_KWS_ENABLED",
            "ZHUANGZHOU_DOC_DIR",
            "ZHUANGZHOU_AUTO_REVIEW",
            "SOCIAL_INBOUND_TOKEN",
            "FEISHU_WS_ENABLED",
            "TOOL_FACTORY_ENABLED",
            "TOOL_FACTORY_COMMAND_ENABLED",
            "TOOL_FACTORY_DOMAIN_ALLOWLIST",
            "AGENT_DELEGATE_ENABLED",
            "AGENT_DELEGATE_AUTO",
            "AGENT_DELEGATE_TIMEOUT",
            "AGENT_DELEGATE_CLI",
            "REMOTE_ACCESS_TOKEN",
            "REMOTE_TOOL_WHITELIST",
            "FEATURE_USER_MODEL",
            "FEATURE_EPISODIC_MEMORY",
            "FEATURE_PREMIUM_UI",
            "FEATURE_KNOWLEDGE_PLATFORM",
            "FEATURE_PROACTIVE_V2",
            "FEATURE_MULTI_DEVICE",
            "FEATURE_HUD_RING",
            "FEATURE_GLANCE_CARD",
            "FEATURE_AVATAR_SCENE",
            "HUD_RING_PERF_THRESHOLD",
            "FEATURE_ALWAYS_ON",
            "ALWAYS_ON_CPU_LIMIT",
            "FEATURE_CROSS_DEVICE",
            "FEATURE_MOBILE_COMPANION",
            "FEATURE_CALENDAR_SENSE",
            "FEATURE_APP_FOCUS",
            "FEATURE_CLIPBOARD_SENSE",
            "FEATURE_PERSONA",
            "FEATURE_MEMORY_DISTILL",
            # ── Phase 9 B1/B2：主动智能引擎配置 ──
            "FEATURE_PROACTIVE_ENGINE",
            "PROACTIVE_SUGGESTION_MODE",
            "PROACTIVE_WINDOW_START",
            "PROACTIVE_WINDOW_END",
            "PROACTIVE_QUIET_START",
            "PROACTIVE_QUIET_END",
            "PROACTIVE_ALLOWED_TYPES",
            "PROACTIVE_STALL_DAYS",
            "PROACTIVE_LONG_RUNNING_MIN",
        }
        updates = {}
        for k, v in payload.items():
            if k not in allowed:
                continue
            # API Key 类字段：空字符串/null 表示"不修改"
            if "KEY" in k or "SECRET" in k or "TOKEN" in k or k in ("ALIYUN_ASR_KEY", "VOLCENGINE_ASR_KEY"):
                if v is None or (isinstance(v, str) and not v.strip()):
                    continue
            # 布尔值统一转小写字符串
            if isinstance(v, bool):
                v = "true" if v else "false"
            updates[k] = str(v).strip()

        try:
            config.update_env_file(updates)
        except Exception as e:
            return self._send(500, json.dumps({"error": f"保存失败：{e}"}, ensure_ascii=False))

        return self._send(200, json.dumps({"ok": True, "saved": list(updates.keys())}, ensure_ascii=False))

    # ── Phase 10-C：本地 Provider 可用性探测（仅白名单 127.0.0.1；spec §八）──

    def _handle_providers_probe_get(self):
        """返回最近一次本地探测缓存（不重新探测）。"""
        return self._send(
            200,
            json.dumps({"ok": True, "cached": True, "probe": dict(_PROVIDER_PROBE_CACHE)}, ensure_ascii=False),
        )


    def _handle_providers_probe_post(self):
        """触发本地 Provider 可用性探测（仅白名单 127.0.0.1，超时 ≤2s，不重试不扫描）。"""
        results = self._probe_local_providers()
        _PROVIDER_PROBE_CACHE.clear()
        _PROVIDER_PROBE_CACHE.update(results)
        return self._send(
            200,
            json.dumps({"ok": True, "cached": False, "probe": results}, ensure_ascii=False),
        )


    def _probe_local_providers(self):
        """探测本地 Provider（白名单内）。

        - 仅遍历 provider_registry.local_probe_targets() 的 127.0.0.1 白名单；
        - 仅当解析出的 base_url 主机在 spec.hosts 白名单内才探测（禁扫描、禁任意远程）；
        - 复用 llm._urlopen_with_proxy（强制绕过环境变量代理，确保真·直连 localhost）；
        - 超时 2s、不重试；结果写入进程内 _PROVIDER_PROBE_CACHE。
        """
        from urllib.parse import urlparse

        results = {}
        for pid, host in provider_registry.local_probe_targets():
            spec = provider_registry.get_spec(pid)
            binding = resolve_provider(pid)
            base = binding["base_url"]
            hp = urlparse(base).netloc  # e.g. 127.0.0.1:11434
            if hp not in spec["hosts"]:
                results[pid] = {
                    "reachable": False,
                    "probed": False,
                    "reason": "host-not-in-whitelist",
                    "url": base,
                    "error": None,
                }
                continue
            url = base + (spec["probe_path"] or "")
            try:
                req = urllib.request.Request(url, headers={"Accept": "application/json"})
                resp = _urlopen_with_proxy(req, timeout=2)
                code = resp.getcode()
                results[pid] = {
                    "reachable": 200 <= code < 400,
                    "probed": True,
                    "http_code": code,
                    "url": base,
                    "error": None,
                }
            except Exception as e:
                results[pid] = {
                    "reachable": False,
                    "probed": True,
                    "http_code": None,
                    "url": base,
                    "error": str(e)[:200],
                }
        return results

    # ── Phase 9 B2：主动智能状态 / DND 同步 ──

    def _handle_proactive_status(self):
        """返回 Proactive Engine 配置与 DND 状态，供设置面板与 Companion 显示。"""
        import proactive_config as _pc

        ws, we = _pc.proactive_window()
        qs, qe = _pc.proactive_quiet()
        return self._send(
            200,
            json.dumps(
                {
                    "ok": True,
                    "feature_proactive_engine": _pc.feature_proactive_engine(),
                    "suggestion_mode": _pc.suggestion_mode(),
                    "window": [ws, we],
                    "quiet": [qs, qe],
                    "allowed_types": sorted(_pc.allowed_types()),
                    "stall_days": _pc.stall_days(),
                    "long_running_minutes": _pc.long_running_minutes(),
                    "dnd": _pc.policy.is_dnd_enabled(),
                },
                ensure_ascii=False,
            ),
        )


    def _handle_proactive_dnd(self):
        """Companion 切换 DND 时同步到后端（NotificationPolicy 的权威 DND 来源）。"""
        import proactive_config as _pc

        payload = self._read_json()
        if "_error" in payload:
            return self._send(400, json.dumps({"error": payload["_error"]}, ensure_ascii=False))
        enabled = bool(payload.get("enabled", False))
        try:
            _pc.policy.set_dnd(enabled)
        except Exception as e:
            return self._send(500, json.dumps({"error": f"设置失败：{e}"}, ensure_ascii=False))
        return self._send(200, json.dumps({"ok": True, "dnd": enabled}, ensure_ascii=False))


    def _handle_models(self):
        """从 OpenAI 兼容端点拉取模型列表，供前端 LLM 设置面板选择。"""
        payload = self._read_json()
        if "_error" in payload:
            return self._send(400, json.dumps({"error": payload["_error"]}, ensure_ascii=False))
        base_url = (payload.get("base_url") or "").strip().rstrip("/") or config.AGNES_BASE
        api_key = (payload.get("api_key") or "").strip() or config.AGNES_KEY
        if not base_url:
            return self._send(400, json.dumps({"error": "端点不能为空"}, ensure_ascii=False))
        try:
            req = urllib.request.Request(
                base_url + "/models",
                headers={"Authorization": "Bearer " + api_key},
                method="GET",
            )
            resp = _urlopen_with_proxy(req, timeout=15)
            data = json.loads(resp.read().decode("utf-8"))
            models = [
                {"id": m.get("id"), "owned_by": m.get("owned_by", "")}
                for m in data.get("data", [])
                if m.get("id")
            ]
            models.sort(key=lambda x: x["id"])
            return self._send(200, json.dumps({"ok": True, "models": models}, ensure_ascii=False))
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")[:300]
            return self._send(502, json.dumps({"error": f"端点返回 {e.code}: {body}"}, ensure_ascii=False))
        except Exception as e:
            return self._send(502, json.dumps({"error": f"获取模型失败：{e}"}, ensure_ascii=False))


    def _handle_test_llm(self):
        """用最小对话请求测试端点连通性，返回延迟。"""
        payload = self._read_json()
        if "_error" in payload:
            return self._send(400, json.dumps({"error": payload["_error"]}, ensure_ascii=False))
        base_url = (payload.get("base_url") or "").strip().rstrip("/") or config.AGNES_BASE
        api_key = (payload.get("api_key") or "").strip() or config.AGNES_KEY
        model = (payload.get("model") or "").strip() or config.AGNES_MODEL
        if not model:
            return self._send(400, json.dumps({"error": "模型不能为空"}, ensure_ascii=False))
        body = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
            "temperature": 0,
            "stream": False,
        }
        start = time.time()
        try:
            req = urllib.request.Request(
                base_url + "/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + api_key,
                },
                method="POST",
            )
            resp = _urlopen_with_proxy(req, timeout=30)
            latency = int((time.time() - start) * 1000)
            result = json.loads(resp.read().decode("utf-8"))
            if not result.get("choices"):
                raise RuntimeError("响应中没有 choices")
            return self._send(
                200,
                json.dumps({"ok": True, "latency_ms": latency, "model": model}, ensure_ascii=False),
            )
        except HTTPError as e:
            latency = int((time.time() - start) * 1000)
            body = e.read().decode("utf-8", errors="ignore")[:300]
            return self._send(
                502,
                json.dumps({"error": f"测试失败 HTTP {e.code}（{latency}ms）：{body}"}, ensure_ascii=False),
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return self._send(
                502,
                json.dumps({"error": f"测试失败（{latency}ms）：{e}"}, ensure_ascii=False),
            )


