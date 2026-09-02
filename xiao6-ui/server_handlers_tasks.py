# -*- coding: utf-8 -*-
"""server_handlers_tasks — Tasks/Notes Handler Mixin（R8-UI 恢复）

从拆分前备份恢复 TasksMixin（GET /api/tasks、GET/POST /api/notes*）。
仅 API 表面恢复，不触碰 Runtime / Execution Core。
"""

import json
from urllib.parse import parse_qs

from db import db_conn
from notes import (
    create_note,
    get_all_tags,
    get_backlinks,
    get_graph,
    get_note,
    get_notes,
    parse_md_links,
    parse_md_tags,
    search_notes,
)


class TasksMixin:
    def _handle_notes(self):
        """GET /api/notes[?folder=&tag=] 列表
        GET /api/notes/<id> 单条
        GET /api/notes/graph 图谱
        GET /api/notes/tags 标签云
        GET /api/notes/search?q= 搜索
        GET /api/notes/backlinks?title= 或 ?id= 反向链接"""
        path = self.path.split("?", 1)[0]
        qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        sub = path[len("/api/notes"):].strip("/")
        try:
            if sub == "graph":
                return self._send(200, json.dumps(get_graph(), ensure_ascii=False))
            if sub == "tags":
                return self._send(200, json.dumps(get_all_tags(), ensure_ascii=False))
            if sub == "search":
                return self._send(200, json.dumps(search_notes(qs.get("q", [""])[0]), ensure_ascii=False))
            if sub == "backlinks":
                key = qs.get("title", [""])[0] or qs.get("id", [""])[0]
                if key.isdigit():
                    n = get_note(int(key))
                    key = n["title"] if n else ""
                return self._send(200, json.dumps(get_backlinks(key), ensure_ascii=False))
            if sub.isdigit():
                n = get_note(int(sub))
                if not n:
                    return self._send(404, json.dumps({"error": "not found"}, ensure_ascii=False))
                return self._send(200, json.dumps(n, ensure_ascii=False))
            folder = qs.get("folder", [""])[0] or None
            tag = qs.get("tag", [""])[0] or None
            return self._send(200, json.dumps(get_notes(folder, tag), ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))

    def _handle_tasks(self):
        """GET /api/tasks[?only_open=1] 只读列出任务。"""
        qs = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        only_open = qs.get("only_open", [""])[0] in ("1", "true", "yes")
        try:
            from tasks import get_tasks

            data = get_tasks(only_open=only_open, limit=50)
            self._send(200, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))

    def _handle_notes_post(self):
        """POST /api/notes 创建 | /api/notes/update 更新 | /api/notes/delete 删除"""
        path = self.path.split("?", 1)[0]
        sub = path[len("/api/notes"):].strip("/")
        payload = self._read_json()
        if "_error" in payload:
            return self._send(400, json.dumps({"error": payload["_error"]}, ensure_ascii=False))
        try:
            if sub == "":
                nid = create_note(
                    payload.get("title", ""),
                    payload.get("markdown", ""),
                    payload.get("tags", ""),
                    payload.get("folder", "收件箱"),
                    payload.get("aliases", ""),
                )
                return self._send(200, json.dumps({"ok": True, "id": nid}, ensure_ascii=False))
            if sub == "update":
                nid = int(payload.get("id") or 0)
                if not nid:
                    return self._send(400, json.dumps({"error": "id required"}, ensure_ascii=False))
                md = (payload.get("markdown") or "").strip()
                conn = db_conn()
                conn.execute(
                    "UPDATE notes SET title=?, markdown=?, tags=?, links=?, folder=?, aliases=? WHERE id=?",
                    (
                        payload.get("title", ""),
                        md,
                        payload.get("tags", "") or ",".join(parse_md_tags(md)),
                        ",".join(parse_md_links(md)),
                        payload.get("folder", "收件箱"),
                        payload.get("aliases", ""),
                        nid,
                    ),
                )
                conn.commit()
                conn.close()
                return self._send(200, json.dumps({"ok": True, "id": nid}, ensure_ascii=False))
            if sub == "delete":
                nid = int(payload.get("id") or 0)
                if not nid:
                    return self._send(400, json.dumps({"error": "id required"}, ensure_ascii=False))
                conn = db_conn()
                conn.execute("DELETE FROM notes WHERE id=?", (nid,))
                conn.commit()
                conn.close()
                return self._send(200, json.dumps({"ok": True}, ensure_ascii=False))
        except Exception as e:
            return self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))
        return self._send(404, json.dumps({"error": "unknown action"}, ensure_ascii=False))
