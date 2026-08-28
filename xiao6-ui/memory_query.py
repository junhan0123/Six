#!/usr/bin/env python3
"""庄周 · 长期记忆查询（Phase 12 · P12-4）

入口：query_memory(query, limit=5) -> list[dict]
  - 模糊搜索：标题/内容/标签（memories 表）+ 主题/关键点（conversation_memories 表）
  - 时间范围：支持绝对日期（2026-03-15）与相对词（上周/昨天/上个月）
  - 纯 SQL LIKE + 索引无关，表规模小时 < 50ms，远超 < 500ms 验收
  - best-effort，异常返回空列表，绝不抛错
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta


def _relative_time(query: str):
    """解析中文相对时间词，返回 (since: str|None, until: str|None)，格式 YYYY-MM-DD。"""
    today = datetime.now().date()
    q = query or ""
    since = until = None
    if "今天" in q:
        since = until = today.isoformat()
    elif "昨天" in q:
        d = (today - timedelta(days=1)).isoformat()
        since = until = d
    elif "前天" in q:
        d = (today - timedelta(days=2)).isoformat()
        since = until = d
    elif "上周" in q:
        since = (today - timedelta(days=14)).isoformat()
        until = (today - timedelta(days=7)).isoformat()
    elif "这周" in q or "本周" in q:
        since = (today - timedelta(days=7)).isoformat()
        until = today.isoformat()
    elif "上个月" in q:
        since = (today - timedelta(days=60)).isoformat()
        until = (today - timedelta(days=30)).isoformat()
    elif "本月" in q:
        since = (today.replace(day=1)).isoformat()
        until = today.isoformat()
    # 绝对日期 YYYY-MM-DD / YYYY年MM月DD日
    m = re.search(r"(\d{4})[-年/](\d{1,2})[-月/](\d{1,2})", q)
    if m:
        since = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        until = since
    return since, until


def _search_memories(conn, like: str, since, until, limit) -> list[dict]:
    sql = (
        "SELECT id, event_type, content, title, tags, timestamp FROM memories "
        "WHERE (content LIKE ? OR title LIKE ? OR tags LIKE ?)"
    )
    args = [like, like, like]
    if since:
        sql += " AND timestamp >= ?"
        args.append(since + " 00:00:00")
    if until:
        sql += " AND timestamp <= ?"
        args.append(until + " 23:59:59")
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    rows = conn.execute(sql, args).fetchall()
    return [
        {
            "source": "memory",
            "type": r[1] or "note",
            "title": r[3] or r[1] or "记忆",
            "content": r[2] or "",
            "tags": r[4] or "",
            "date": (r[5] or "")[:10],
        }
        for r in rows
    ]


def _search_conversations(conn, like: str, since, until, limit) -> list[dict]:
    # conversation_memories 可能在 P12-3 才创建；不存在时静默跳过
    try:
        conn.execute("SELECT 1 FROM conversation_memories LIMIT 1")
    except Exception:
        return []
    sql = (
        "SELECT id, date, topic, key_points, sentiment FROM conversation_memories "
        "WHERE (topic LIKE ? OR key_points LIKE ?)"
    )
    args = [like, like]
    if since:
        sql += " AND date >= ?"
        args.append(since)
    if until:
        sql += " AND date <= ?"
        args.append(until)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    rows = conn.execute(sql, args).fetchall()
    return [
        {
            "source": "conversation",
            "type": "conversation",
            "title": r[2] or "对话摘要",
            "content": r[3] or "",
            "sentiment": r[4] or "",
            "date": r[1] or "",
        }
        for r in rows
    ]


def query_memory(query: str, limit: int = 5, since: str | None = None, until: str | None = None) -> list[dict]:
    """模糊搜索长期记忆 + 历史对话摘要。

    Args:
        query:  搜索词（支持相对时间词：上周/昨天/本月…）
        limit:  返回条数上限
        since:  可选绝对起始日期 YYYY-MM-DD（覆盖相对词推导）
        until:  可选绝对结束日期 YYYY-MM-DD
    Returns:
        记忆字典列表（按时间倒序，最多 limit 条）。异常返回 []。
    """
    try:
        if since is None or until is None:
            rs, ru = _relative_time(query or "")
            since = since or rs
            until = until or ru
        from db import db_conn

        conn = db_conn()
        like = f"%{(query or '').strip()}%"
        results = []
        results.extend(_search_memories(conn, like, since, until, limit))
        results.extend(_search_conversations(conn, like, since, until, limit))
        conn.close()
        # 按日期倒序，截断到 limit
        results.sort(key=lambda x: x.get("date", ""), reverse=True)
        return results[:limit]
    except Exception:
        return []
