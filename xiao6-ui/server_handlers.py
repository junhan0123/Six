"""server_handlers — Server Handlers Module (S79.8)
Re-exports all handler mixins for backward compatibility.
"""

import json
from urllib.parse import parse_qs

from server_handlers_chat import ChatMixin
from server_handlers_memory import MemoryMixin
from server_handlers_system import SystemMixin
from server_handlers_session_trace import SessionTraceMixin
from server_handlers_tasks import TasksMixin

# Check what else is available
try:
    from server_handlers_system import SocialMixin
except ImportError:
    class SocialMixin:
        pass

# CapabilityMixin - Capability OS handlers
class CapabilityMixin:
    """Capability OS handlers for server."""

    def _handle_capability_match(self):
        """POST /api/capability_os/match — 意图→能力匹配。"""
        try:
            qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            # Try reading from POST body first
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            goal = ""
            top_k = 5
            if ctype == "application/json":
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = b""
                while len(raw) < length:
                    chunk = self.rfile.read(length - len(raw))
                    if not chunk:
                        break
                    raw += chunk
                try:
                    payload = json.loads(raw.decode("utf-8")) if raw else {}
                    goal = (payload.get("goal") or payload.get("query") or "").strip()
                    top_k = int(payload.get("top_k") or qs.get("top_k", ["5"])[0] or "5")
                except Exception:
                    goal = (qs.get("goal", [None])[0] or qs.get("query", [""])[0] or "").strip()
            else:
                goal = (qs.get("goal", [None])[0] or qs.get("query", [""])[0] or "").strip()
                top_k = int(qs.get("top_k", ["5"])[0] or "5")
            if not goal:
                return self._send(400, json.dumps({"error": "goal 参数不能为空"}, ensure_ascii=False))
            import capability_os
            results = capability_os.match(goal, top_k=top_k)
            return self._send(200, json.dumps({"ok": True, "results": results, "query": goal}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

    def _handle_capability_plan(self):
        """GET /api/capability_os/plan — 返回注册表统计与分组视图。"""
        try:
            import capability_os
            view = capability_os.foundation_view()
            return self._send(200, json.dumps(view, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))

__all__ = [
    'SystemMixin',
    'MemoryMixin',
    'TasksMixin',
    'ChatMixin',
    'CapabilityMixin',
    'SocialMixin',
    'SessionTraceMixin',
]
