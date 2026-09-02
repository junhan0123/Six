# -*- coding: utf-8 -*-
"""Session & Trace Handler Mixin — API endpoints for session/trace management."""

import json
import uuid
from urllib.parse import parse_qs

import session
import config
from db import db_conn


class SessionTraceMixin:
    """Mixin providing /api/sessions, /api/session, /api/trace endpoints."""

    def _handle_sessions_get(self):
        """GET /api/sessions — 列出所有会话协调记录。"""
        try:
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            limit = int(qs.get("limit", ["50"])[0] or "50")
            sessions = session.list_sessions(limit)
            data = [
                {
                    "session_id": s.session_id,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                    "status": s.status,
                }
                for s in sessions
            ]
            self._send(200, json.dumps({"ok": True, "sessions": data}, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))

    def _handle_session_get(self):
        """GET /api/session?session_id=xxx — 获取单个会话详情。"""
        try:
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            session_id = (qs.get("session_id", ["default"])[0] or "default").strip()
            
            proj = session.get_projection(session_id)
            data = {
                "session_id": proj.session_id,
                "conversation": proj.conversation,
                "active_goals": proj.active_goals,
                "active_tasks": proj.active_tasks,
                "runtime_state": proj.runtime_state,
                "latest_checkpoint": {
                    "checkpoint_id": proj.latest_checkpoint.checkpoint_id,
                    "created_at": proj.latest_checkpoint.created_at,
                    "goal_id": proj.latest_checkpoint.goal_id,
                    "task_id": proj.latest_checkpoint.task_id,
                    "label": proj.latest_checkpoint.label,
                    "status": proj.latest_checkpoint.status,
                } if proj.latest_checkpoint else None,
            }
            self._send(200, json.dumps({"ok": True, "session": data}, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))

    def _handle_session_post(self):
        """POST /api/session — 创建/注册新会话。"""
        try:
            payload = self._read_json()
            if "_error" in payload:
                return self._send(400, json.dumps({"error": payload["_error"]}))

            session_id = (payload.get("session_id") or uuid.uuid4().hex[:16]).strip()
            s = session.create_session(session_id)
            data = {
                "session_id": s.session_id,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "status": s.status,
            }
            self._send(200, json.dumps({"ok": True, "session": data}, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))

    def _handle_session_resume(self):
        """POST /api/session/resume — 恢复会话到检查点。"""
        try:
            payload = self._read_json()
            if "_error" in payload:
                return self._send(400, json.dumps({"error": payload["_error"]}))

            session_id = (payload.get("session_id") or "default").strip()
            checkpoint_id = payload.get("checkpoint_id")

            # 调用 session.resume() 获取恢复结果
            result = session.resume(session_id, checkpoint_id=checkpoint_id)

            # 如果有效，返回投影数据
            if result.status == "valid":
                proj = session.get_projection(session_id)
                data = {
                    "status": "valid",
                    "session_id": proj.session_id,
                    "conversation": proj.conversation,
                    "active_goals": proj.active_goals,
                    "active_tasks": proj.active_tasks,
                    "runtime_state": proj.runtime_state,
                    "next_action": result.next_action,
                    "reason": result.reason,
                }
                self._send(200, json.dumps({"ok": True, "resume": data}, ensure_ascii=False))
            else:
                # 无效或过时，返回状态
                data = {
                    "status": result.status,
                    "session_id": session_id,
                    "next_action": result.next_action,
                    "reason": result.reason,
                }
                self._send(200, json.dumps({"ok": False, "resume": data}, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))

    def _handle_session_delete(self):
        """DELETE /api/session?session_id=xxx — 关闭会话（软删除）。"""
        try:
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            session_id = (qs.get("session_id", ["default"])[0] or "default").strip()
            
            existed = session.close_session(session_id)
            self._send(200, json.dumps({"ok": True, "existed": existed}, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))

    def _handle_trace_get(self):
        """GET /api/trace?session_id=xxx&limit=N — 获取会话追踪事件。"""
        try:
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            session_id = (qs.get("session_id", ["default"])[0] or "default").strip()
            limit = int(qs.get("limit", ["100"])[0] or "100")
            
            # 从 eventbus 死信队列和 SSE 历史中获取追踪（best-effort）
            # 实际实现中，可集成 eventbus 的历史缓存
            conn = db_conn()
            try:
                # 从 chat_log 获取对话追踪
                rows = conn.execute(
                    "SELECT id, ts, session, role, content FROM chat_log "
                    "WHERE session=? ORDER BY id DESC LIMIT ?",
                    (session_id, limit),
                ).fetchall()
                
                trace = [
                    {
                        "id": r[0],
                        "timestamp": r[1],
                        "session": r[2],
                        "role": r[3],
                        "content": r[4][:200] if r[4] else "",
                    }
                    for r in reversed(rows)
                ]
            finally:
                conn.close()
            
            data = {
                "session_id": session_id,
                "trace": trace,
                "count": len(trace),
            }
            self._send(200, json.dumps({"ok": True, "trace": data}, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))

    def _handle_activity_get(self):
        """GET /api/activity?session_id=xxx — 获取会话活动摘要。"""
        try:
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            session_id = (qs.get("session_id", ["default"])[0] or "default").strip()
            
            proj = session.get_projection(session_id)
            
            data = {
                "session_id": session_id,
                "conversation_turns": len(proj.conversation),
                "active_goals": len(proj.active_goals),
                "active_tasks": len(proj.active_tasks),
                "has_checkpoint": proj.latest_checkpoint is not None,
                "runtime_running": proj.runtime_state.get("running", False),
                "current_goal": proj.runtime_state.get("current_goal"),
                "queue_len": proj.runtime_state.get("queue_len", 0),
            }
            self._send(200, json.dumps({"ok": True, "activity": data}, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))