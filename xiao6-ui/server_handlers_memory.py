# -*- coding: utf-8 -*-
"""server.py 拆分出的 memory 域 Handler mixin（由拆分脚本生成，勿手改）。"""
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


class MemoryMixin:
    def _handle_memories(self):
        """GET /api/memories 列表 | /api/memories/graph 图谱(nodes+edges)。

        支持 ?archived=1 返回归档冷存储记忆；?type=person 按类型过滤（同样受 archived 约束）。
        """
        path = self.path.split("?", 1)[0]
        sub = path[len("/api/memories") :].strip("/")
        try:
            if sub == "graph":
                data = get_memory_graph()
            else:
                from db import get_memories, get_memories_by_type

                qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
                t = qs.get("type", [""])[0].strip()
                archived = 1 if qs.get("archived", [""])[0] in ("1", "true", "yes") else 0
                if t:
                    data = get_memories_by_type(t, limit=300, archived=archived)
                else:
                    data = get_memories(limit=500, archived=archived)
            self._send(200, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))


    def _handle_memories_post(self):
        """POST /api/memories/archive — 归档 / 恢复一条记忆（Hermes 冷存储生命周期）。

        请求体（JSON）：{ "mem_id": "person_xxx", "archived": 1 }  —— archived=1 归档，0 恢复。
        仅切换 mem_id 对应行的 archived 状态，不删除数据，可随时恢复。
        """
        payload = self._read_json()
        if "_error" in payload:
            return self._send(400, json.dumps({"error": payload["_error"]}))
        mem_id = payload.get("mem_id")
        if not mem_id:
            return self._send(400, json.dumps({"error": "mem_id required"}))
        archived = 1 if payload.get("archived", 1) in (1, "1", True, "true", "yes") else 0
        try:
            from db import archive_memory

            n = archive_memory(mem_id, archived)
            if n == 0:
                return self._send(404, json.dumps({"error": "mem_id not found", "mem_id": mem_id}))
            return self._send(200, json.dumps({"ok": True, "mem_id": mem_id, "archived": archived, "rows": n}))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}))

    # ---- Phase 12 记忆人格深度：重要日期 + 对话记忆 + 记忆查询 ----


    def _handle_important_dates_get(self):
        """GET /api/memory/important-dates — 列出所有重要日期。"""
        try:
            from db import db_conn

            conn = db_conn()
            rows = conn.execute(
                "SELECT id, date, type, description, reminder_days, created FROM important_dates "
                "ORDER BY date ASC"
            ).fetchall()
            conn.close()
            data = [
                {"id": r[0], "date": r[1], "type": r[2], "description": r[3],
                 "reminder_days": r[4], "created": r[5]}
                for r in rows
            ]
            return self._send(200, json.dumps({"ok": True, "dates": data}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}))


    def _handle_important_dates_post(self):
        """POST /api/memory/important-dates — CRUD（action: create|update|delete）。"""
        payload = self._read_json()
        if "_error" in payload:
            return self._send(400, json.dumps({"error": payload["_error"]}))
        action = (payload.get("action") or "create").strip().lower()
        try:
            from db import db_conn
            from datetime import datetime

            conn = db_conn()
            if action == "delete":
                did = int(payload.get("id") or 0)
                if not did:
                    return self._send(400, json.dumps({"error": "id required"}))
                n = conn.execute("DELETE FROM important_dates WHERE id=?", (did,)).rowcount
                conn.commit()
                conn.close()
                return self._send(200, json.dumps({"ok": True, "deleted": n}))
            if action == "update":
                did = int(payload.get("id") or 0)
                if not did:
                    return self._send(400, json.dumps({"error": "id required"}))
                fields, vals = [], []
                for col in ("date", "type", "description", "reminder_days"):
                    if col in payload and payload[col] not in (None, ""):
                        fields.append(f"{col}=?")
                        vals.append(payload[col])
                if not fields:
                    return self._send(400, json.dumps({"error": "nothing to update"}))
                vals.append(did)
                conn.execute(f"UPDATE important_dates SET {','.join(fields)} WHERE id=?", vals)
                conn.commit()
                conn.close()
                return self._send(200, json.dumps({"ok": True, "updated": did}))
            # 默认 create
            date_s = (payload.get("date") or "").strip()
            desc = (payload.get("description") or "").strip()
            if not date_s:
                return self._send(400, json.dumps({"error": "date required"}))
            dtype = (payload.get("type") or "event").strip() or "event"
            rdays = int(payload.get("reminder_days", 3) or 3)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur = conn.execute(
                "SELECT id FROM important_dates WHERE date=? AND type=?", (date_s, dtype)
            ).fetchone()
            if cur:
                conn.close()
                return self._send(200, json.dumps({"ok": True, "id": cur[0], "dup": True}))
            cur = conn.execute(
                "INSERT INTO important_dates(date, type, description, reminder_days, created, updated) "
                "VALUES(?,?,?,?,?,?)",
                (date_s, dtype, desc, rdays, now, now),
            )
            new_id = cur.lastrowid
            conn.commit()
            conn.close()
            return self._send(200, json.dumps({"ok": True, "id": new_id}))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}))


    def _handle_conversations_get(self):
        """GET /api/memory/conversations — 查询历史对话沉淀摘要。"""
        try:
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            limit = int(qs.get("limit", ["50"])[0] or "50")
            from db import db_conn

            conn = db_conn()
            rows = conn.execute(
                "SELECT id, date, topic, key_points, sentiment, created FROM conversation_memories "
                "ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            conn.close()
            data = [
                {"id": r[0], "date": r[1], "topic": r[2], "key_points": r[3],
                 "sentiment": r[4], "created": r[5]}
                for r in rows
            ]
            return self._send(200, json.dumps({"ok": True, "conversations": data}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}))


    def _handle_memory_confirm(self):
        # Phase 37.2 · 记忆确认/纠正/忽略（append-only 账本，绝不写 memories.status）
        try:
            p = self._read_json() or {}
        except Exception:
            p = {}
        memory_id = p.get("memory_id")
        action = (p.get("action") or "confirm").strip().lower()
        note = (p.get("note") or p.get("text") or "").strip()
        correction = (p.get("correction") or note).strip()
        if action not in ("confirm", "correct", "ignore"):
            action = "confirm"
        if not memory_id:
            return self._send(400, json.dumps({"ok": False, "error": "memory_id 必填"}, ensure_ascii=False))
        try:
            import personal_ai
            if action == "confirm":
                rid = personal_ai.confirm_memory(memory_id, note)
            elif action == "correct":
                rid = personal_ai.correct_memory(memory_id, correction, note)
            else:
                rid = personal_ai.ignore_memory(memory_id, note)
            return self._send(200, json.dumps({"ok": True, "id": rid, "action": action}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def _handle_memory_write(self):
        """POST /api/memory/write — 最小记忆写入适配器。

        写入经 Canonical Memory API（memory.create_memory）落到 memories 表，
        与 /api/memory/query（memory_query.query_memory）同源，
        保证 write → persist → query → read back 真实闭环。
        """
        try:
            import memory

            payload = self._read_json()
            if "_error" in payload:
                return self._send(400, json.dumps({"error": payload["_error"]}))
            content_text = (payload.get("content") or "").strip()
            if not content_text:
                return self._send(400, json.dumps({"error": "content required"}))
            title = (payload.get("title") or "").strip() or None
            raw_tags = payload.get("tags") or ""
            if isinstance(raw_tags, (list, tuple)):
                tags = [str(t).strip() for t in raw_tags if str(t).strip()] or None
            else:
                tags = [t.strip() for t in str(raw_tags).split(",") if t.strip()] or None
            mem_id = memory.create_memory(
                content_text,
                event_type=(payload.get("event_type") or "note").strip() or "note",
                title=title,
                tags=tags,
                source=(payload.get("source") or "user").strip() or "user",
            )
            # note_id 保留以兼容既有前端契约
            return self._send(
                200,
                json.dumps({"ok": True, "memory_id": mem_id, "note_id": mem_id}, ensure_ascii=False),
            )
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}))



    def _handle_memory_query(self):
        """POST /api/memory/query — 模糊搜索长期记忆 + 历史对话摘要。"""
        payload = self._read_json()
        if "_error" in payload:
            return self._send(400, json.dumps({"error": payload["_error"]}))
        query = (payload.get("query") or "").strip()
        limit = int(payload.get("limit", 5) or 5)
        try:
            from memory_query import query_memory

            results = query_memory(query, limit=limit)
            return self._send(200, json.dumps({"ok": True, "query": query, "results": results}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}))


    def _handle_memory_backfill(self):
        """POST/GET /api/memory/backfill — Phase 19 回填 memories.salience（幂等，安全）。"""
        try:
            import memory_intelligence

            n = memory_intelligence.backfill_salience()
            return self._send(200, json.dumps({"ok": True, "updated": n}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))


    def _handle_memory_audit(self):
        """GET /api/memory_audit?action=audit|prune&store=&keep_days= — 记忆审计。"""
        from urllib.parse import parse_qs
        qs = parse_qs(self.path.split("?", 1)[-1])
        action = (qs.get("action", ["audit"])[0] or "audit").lower()
        try:
            import memory_audit as _ma
            if action == "prune":
                store = qs.get("store", [""])[0] or ""
                keep = int(qs.get("keep_days", ["30"])[0] or "30")
                res = _ma.prune(store, keep)
                return self._send(200, json.dumps(res, ensure_ascii=False))
            res = _ma.audit()
            return self._send(200, json.dumps(res, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


    def _handle_learnings(self):
        """GET /api/learnings?action=list|delete&id=&type=&limit= — 自我学习经验读写。"""
        from urllib.parse import parse_qs

        qs = parse_qs(self.path.split("?", 1)[-1])
        action = (qs.get("action", ["list"])[0] or "list").lower()
        try:
            from memory import get_learnings

            if action == "delete":
                lid = int(qs.get("id", ["0"])[0] or "0")
                deleted = 0
                if lid:
                    conn = db_conn()
                    cur = conn.execute("DELETE FROM learnings WHERE id=?", (lid,))
                    deleted = cur.rowcount
                    conn.commit()
                    conn.close()
                return self._send(200, json.dumps({"ok": True, "deleted": deleted}, ensure_ascii=False))
            ltype = (qs.get("type", [""])[0] or "") or None
            limit = int(qs.get("limit", ["50"])[0] or "50")
            items = get_learnings(limit=limit, ltype=ltype)
            return self._send(
                200,
                json.dumps({"ok": True, "learnings": items, "count": len(items)}, ensure_ascii=False),
            )
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))


