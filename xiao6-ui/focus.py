#!/usr/bin/env python3
"""小6 · 线索/焦点栈（Phase 2.3，本地优先、零密钥）

记录对话中近期被提及的实体（URL、[[双向链接]]、话题），用于：
1. 指代消解 —— 把「那个网页」「它」「进度怎样」映射到最近焦点；
2. ACI 上下文注入 —— 让模型「睁眼」即知当前开放话题，缓解话题漂移。

设计：纯本地 SQLite，无外部密钥；焦点有上限（LRU 淘汰），避免无限增长。
"""

import re

from db import db_conn

FOCUS_LIMIT = 20  # 焦点栈最大容量（超出淘汰最久未命中）
_URL_RE = re.compile(r"https?://[^\s，。、；;]+")
_REF_RE = re.compile(r"(那个|这个|它|他|她|刚才说的|上面的|之前提到的|前面说的|上次说的)")


def _now():
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def push_focus(kind, text):
    """记录/提升一个焦点。已存在则 hits+1 并刷新 ts；超出上限淘汰最旧。"""
    text = (text or "").strip()
    if not text:
        return
    conn = db_conn()
    row = conn.execute("SELECT id,hits FROM focus WHERE kind=? AND text=?", (kind, text)).fetchone()
    if row:
        conn.execute("UPDATE focus SET hits=hits+1, ts=? WHERE id=?", (_now(), row[0]))
    else:
        conn.execute("INSERT INTO focus(kind,text,ts,hits) VALUES(?,?,?,1)", (kind, text, _now()))
        cnt = conn.execute("SELECT count(*) FROM focus").fetchone()[0]
        if cnt > FOCUS_LIMIT:
            conn.execute(
                "DELETE FROM focus WHERE id IN (SELECT id FROM focus ORDER BY ts ASC LIMIT ?)",
                (cnt - FOCUS_LIMIT,),
            )
    conn.commit()
    conn.close()


def recent_foci(limit=6):
    """返回最近焦点（按时间倒序）。"""
    conn = db_conn()
    rows = conn.execute("SELECT kind,text FROM focus ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [{"kind": k, "text": t} for k, t in rows]


def resolve_reference(text, foci):
    """纯函数：把指代代词替换为焦点栈顶最相关实体，便于单测。

    规则：若文本含指代词且焦点栈非空，则用最近焦点（foci[0]）替换首个指代词；
    否则原样返回。返回 (resolved_text, used_focus_or_None)。
    """
    t = (text or "").strip()
    if not foci or not _REF_RE.search(t):
        return t, None
    top = foci[0]["text"]
    resolved = _REF_RE.sub(top, t, count=1)
    return resolved, top


def capture_foci(text):
    """从一段文本中捕获 URL 与 [[双向链接]] 实体并压入焦点栈（零密钥启发式）。"""
    for u in _URL_RE.findall(text or ""):
        push_focus("url", u.rstrip("，。、；;）)】].,"))
    for lk in re.findall(r"\[\[([^\]]+)\]\]", text or ""):
        name = lk.strip().split("|")[0].strip()
        if name:
            push_focus("entity", name)
