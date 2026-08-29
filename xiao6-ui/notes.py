#!/usr/bin/env python3
"""小6 · 笔记 / 画像 / 提醒 / 每日笔记（Obsidian 风格，SQLite + Markdown 混合）"""

import json
import re
import sqlite3

from db import db_conn, fts_upsert
from llm import agnes_completion


# ---------- Markdown 解析 ----------
def parse_md_links(text):
    """提取 [[双向链接]] 目标（去重保序）。"""
    found = re.findall(r"\[\[([^\]]+)\]\]", text or "")
    seen, out = set(), []
    for f in found:
        name = f.strip().split("|")[0].strip()
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def parse_md_tags(text):
    """提取 #标签（支持中文，去重）。"""
    found = re.findall(r"(?<![\w/])#([\u4e00-\u9fa5A-Za-z0-9_\-]+)", text or "")
    seen, out = set(), []
    for f in found:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


# ---------- 笔记 CRUD ----------
def create_note(title, markdown, tags="", folder="收件箱", aliases=""):
    from datetime import datetime

    title = (title or "").strip() or "未命名笔记"
    md = (markdown or "").strip()
    folder = (folder or "收件箱").strip() or "收件箱"
    tags = ",".join(parse_md_tags(tags + " " + md)) if tags else ",".join(parse_md_tags(md))
    links = ",".join(parse_md_links(md))
    conn = db_conn()
    cur = conn.execute(
        "INSERT INTO notes(ts,content,tag,title,markdown,tags,links,folder,aliases) VALUES(?,?,?,?,?,?,?,?,?)",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            md[:200],
            (tags or "笔记"),
            title,
            md,
            tags,
            links,
            folder,
            aliases,
        ),
    )
    nid = cur.lastrowid
    fts_upsert(conn, nid, title, md, tags, folder)
    conn.commit()
    conn.close()
    try:
        from embed import index_note

        index_note(nid, md)
    except Exception as e:
        print("[notes] 向量索引跳过:", e)
    return nid


def get_notes(folder=None, tag=None, limit=200):
    conn = db_conn()
    sql = "SELECT id,ts,title,markdown,tags,links,folder,aliases FROM notes"
    wheres, params = [], []
    if folder:
        wheres.append("folder=?")
        params.append(folder)
    if tag:
        wheres.append("(tags LIKE ? OR folder=?)")
        params.append("%" + tag + "%")
        params.append(tag)
    if wheres:
        sql += " WHERE " + " AND ".join(wheres)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [
        dict(
            id=r[0],
            ts=r[1],
            title=r[2],
            markdown=r[3],
            tags=r[4],
            links=(r[5].split(",") if r[5] else []),
            folder=r[6],
            aliases=r[7],
        )
        for r in rows
    ]


def get_note(nid):
    conn = db_conn()
    r = conn.execute("SELECT id,ts,title,markdown,tags,links,folder,aliases FROM notes WHERE id=?", (nid,)).fetchone()
    conn.close()
    if not r:
        return None
    return dict(
        id=r[0],
        ts=r[1],
        title=r[2],
        markdown=r[3],
        tags=r[4],
        links=(r[5].split(",") if r[5] else []),
        folder=r[6],
        aliases=r[7],
    )


def search_notes(q):
    """按关键词检索笔记。

    Phase 2.1：优先走 FTS5(trigram) 中文全文检索（需 ≥3 字符才能形成三元组，
    子串召回更准更快）；短查询（<3 字）或 FTS 不可用 / 索引未命中时，
    自动降级到 LIKE 子串检索，保证召回率不丢失。
    """
    q = (q or "").strip()
    if not q:
        return []
    conn = db_conn()
    # ≥3 字符才走 FTS5（trigram 要求至少 3 字才能构成有效三元组）
    if len(q) >= 3:
        try:
            safe = q.replace('"', '""')  # 转义内部双引号，避免破坏 FTS 字符串字面量
            rows = conn.execute(
                "SELECT id,title,markdown,tags,folder FROM notes "
                "WHERE id IN (SELECT rowid FROM notes_fts WHERE notes_fts MATCH ?) "
                "ORDER BY id DESC LIMIT 50",
                ('"' + safe + '"',),
            ).fetchall()
            results = [dict(id=r[0], title=r[1], markdown=r[2], tags=r[3], folder=r[4]) for r in rows]
            if results:
                conn.close()
                return results
            # 索引未命中 → 落到下方 LIKE 兜底（如索引被禁用或尚未回填）
        except sqlite3.OperationalError:
            # 无 FTS5 支持或索引缺失 → 降级
            pass
    # LIKE 兜底（短查询 / FTS 缺失 / 索引未命中）
    like = "%" + q + "%"
    rows = conn.execute(
        "SELECT id,title,markdown,tags,folder FROM notes "
        "WHERE title LIKE ? OR markdown LIKE ? OR tags LIKE ? OR folder LIKE ? "
        "ORDER BY id DESC LIMIT 50",
        (like, like, like, like),
    ).fetchall()
    conn.close()
    return [dict(id=r[0], title=r[1], markdown=r[2], tags=r[3], folder=r[4]) for r in rows]


def get_all_tags():
    conn = db_conn()
    rows = conn.execute("SELECT tags FROM notes WHERE tags IS NOT NULL AND tags<>''").fetchall()
    conn.close()
    counter = {}
    for (t,) in rows:
        for tag in t.split(","):
            tag = tag.strip()
            if tag:
                counter[tag] = counter.get(tag, 0) + 1
    return [{"tag": k, "count": v} for k, v in sorted(counter.items(), key=lambda x: -x[1])]


def get_graph():
    """返回 Obsidian 式图谱：节点=笔记，边=[[双向链接]]。"""
    conn = db_conn()
    rows = conn.execute("SELECT id,title,markdown,content,links,folder FROM notes").fetchall()
    conn.close()
    nodes, edges = [], []
    title_to_id = {}
    for r in rows:
        nid, title, markdown, content, links, folder = r
        md = (markdown or "") or (content or "")
        if not md.strip():
            continue
        title = (title or "").strip() or md.strip()[:18]
        title_to_id[title] = nid
        nodes.append({"id": nid, "title": title, "folder": folder, "val": 1 + (len(links.split(",")) if links else 0)})
    for r in rows:
        nid, title, markdown, content, links, folder = r
        if not links:
            continue
        for lk in links.split(","):
            lk = lk.strip()
            if lk in title_to_id and title_to_id[lk] != nid:
                edges.append({"source": nid, "target": title_to_id[lk]})
    return {"nodes": nodes, "edges": edges}


def get_backlinks(title):
    """返回指向某标题的笔记（反向链接）。"""
    conn = db_conn()
    like = "%[[" + title + "%"
    rows = conn.execute("SELECT id,title,folder FROM notes WHERE markdown LIKE ?", (like,)).fetchall()
    conn.close()
    return [dict(id=r[0], title=r[1], folder=r[2]) for r in rows]


# ---------- 每日笔记（AI 自动抽取） ----------
def extract_daily_note():
    """【AI 自动抽取】每轮对话后调用：今天首次触发时，调 Agnes 把当天对话要点抽成『每日笔记』。
    节流：meta.last_daily_note_date==今天则跳过，避免重复消耗额度。"""
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    try:
        conn = db_conn()
        row = conn.execute("SELECT value FROM meta WHERE key='last_daily_note_date'").fetchone()
        if row and row[0] == today:
            conn.close()
            return
        rows = conn.execute(
            "SELECT role,content FROM chat_log WHERE ts LIKE ? ORDER BY id ASC", (today + "%",)
        ).fetchall()
        conn.close()
        if len(rows) < 4:
            return  # 对话太少，不值得抽
        convo = "\n".join((("用户" if r == "user" else "小6") + "：" + c) for r, c in rows[-24:])
        prompt = (
            "你是小6的记忆整理模块。下面是一段今天的对话，请整理成一份结构化「每日笔记」"
            "（Markdown 格式），用于长期记忆。要求：\n"
            "1. 用 # 一级标题 作为当天主题概括（简短，不超过 12 字）\n"
            "2. 用 ## 小节 组织：要点 / 决定 / 待办 / 项目进展 / 人物\n"
            "3. 用 - 列表列出具体项；对重要的人或概念，用 [[名称]] 双向链接标注\n"
            "4. 在文末加一行标签：#每日笔记 #日期-" + today + "\n"
            "5. 只输出 Markdown 正文，不要解释、不要代码块包裹。\n\n对话：\n" + convo
        )
        try:
            with agnes_completion([{"role": "user", "content": prompt}], tools=[], stream=False, timeout=90) as resp:
                d = json.loads(resp.read().decode("utf-8"))
            md = d["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("[daily-note] 抽取失败:", e)
            return
        if not md:
            return
        create_note(title=today, markdown=md, tags="每日笔记", folder="每日笔记")
        conn = db_conn()
        conn.execute(
            "INSERT INTO meta(key,value) VALUES('last_daily_note_date',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (today,),
        )
        conn.commit()
        conn.close()
        print("[daily-note] 已生成每日笔记:", today)
    except Exception as e:
        print("[daily-note] 异常:", e)


def tool_note_daily(args):
    """手动强制生成/刷新今日每日笔记。"""
    extract_daily_note()
    return "已尝试整理今日笔记。"


# ---------- 工具实现：笔记 ----------
def tool_note_save(args):
    content = (args.get("content") or "").strip()
    if not content:
        return "错误：内容为空"
    title = (args.get("title") or content[:24]).strip()
    tag = (args.get("tag") or "笔记").strip()
    md = (args.get("markdown") or content).strip()
    folder = (args.get("folder") or "收件箱").strip()
    tags = (args.get("tags") or tag).strip()
    from datetime import datetime

    conn = db_conn()
    links = ",".join(parse_md_links(md))
    cur = conn.execute(
        "INSERT INTO notes(ts,content,tag,title,markdown,tags,links,folder) VALUES(?,?,?,?,?,?,?,?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), content, tag, title, md, tags, links, folder),
    )
    fts_upsert(conn, cur.lastrowid, title, md, tags, folder)
    conn.commit()
    conn.close()
    try:
        from embed import index_note

        index_note(cur.lastrowid, md)
    except Exception as e:
        print("[notes] 向量索引跳过:", e)
    return f"已保存笔记：{title}" + (f"（{tag}）" if tag else "")


def tool_note_list(args):
    limit = int(args.get("limit") or 10)
    conn = db_conn()
    rows = conn.execute("SELECT ts,content,tag FROM notes ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    if not rows:
        return "暂无笔记。"
    out = []
    for ts, content, tag in rows:
        out.append(f"[{ts}] {('[' + tag + '] ') if tag else ''}{content}")
    return "最近笔记：\n" + "\n".join(out)


# ---------- 工具实现：用户画像 ----------
def tool_profile_set(args):
    key = (args.get("key") or "").strip()
    value = (args.get("value") or "").strip()
    if not key or not value:
        return "错误：key 与 value 均不能为空"
    from datetime import datetime

    conn = db_conn()
    conn.execute(
        "INSERT INTO profile(key,value,updated) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated=excluded.updated",
        (key, value, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()
    return f"已记住：{key} = {value}"


def tool_profile_get(args):
    key = (args.get("key") or "").strip()
    conn = db_conn()
    if key:
        row = conn.execute("SELECT value FROM profile WHERE key=?", (key,)).fetchone()
        conn.close()
        return f"{key} = {row[0]}" if row else f"暂无「{key}」的记忆。"
    rows = conn.execute("SELECT key,value FROM profile ORDER BY key").fetchall()
    conn.close()
    if not rows:
        return "暂无长期记忆。"
    return "已记住的信息：\n" + "\n".join(f"- {k}：{v}" for k, v in rows)


# ---------- 工具实现：提醒 ----------
def parse_reminder_time(text):
    """尽力解析中文时间表达，返回 datetime 或 None。
    支持：立刻/马上/现在、N秒、N分钟、N小时、今天/明天 HH:MM、N点。"""
    from datetime import datetime, timedelta

    now = datetime.now()
    t = (text or "").strip()
    if re.search(r"立刻|马上|现在|立即", t):
        return now
    m = re.search(r"(\d+)\s*秒", t)
    if m:
        return now + timedelta(seconds=int(m.group(1)))
    m = re.search(r"(\d+)\s*分钟", t)
    if m:
        return now + timedelta(minutes=int(m.group(1)))
    m = re.search(r"(\d+)\s*小时", t)
    if m:
        return now + timedelta(hours=int(m.group(1)))
    m = re.search(r"(明天|后天)\s*(\d{1,2})[:：](\d{2})", t)
    if m:
        days = 1 if m.group(1) == "明天" else 2
        return (now + timedelta(days=days)).replace(
            hour=int(m.group(2)), minute=int(m.group(3)), second=0, microsecond=0
        )
    m = re.search(r"(今天)?\s*(\d{1,2})[:：](\d{2})", t)
    if m:
        return now.replace(hour=int(m.group(2)), minute=int(m.group(3)), second=0, microsecond=0)
    m = re.search(r"(\d{1,2})\s*点", t)
    if m:
        return now.replace(hour=int(m.group(1)), minute=0, second=0, microsecond=0)
    return None


def clean_reminder_text(text):
    """去掉提醒内容里的时间词，只保留事项本身（如「立刻 去倒杯水」→「去倒杯水」）。"""
    t = (text or "").strip()
    t = re.sub(r"(今天|明天|后天|大后天|立刻|马上|现在|立即|及时)", "", t)
    t = re.sub(r"\d+\s*(秒|分钟|小时|天|日)", "", t)
    t = re.sub(r"(早上|上午|中午|下午|晚上|傍晚|凌晨)?\s*\d{1,2}\s*[:：]?\s*\d{0,2}\s*点?", "", t)
    t = re.sub(r"\d{1,2}[:：]\d{2}", "", t)
    return t.strip(" 。，,、；;")


def tool_reminder_set(args):
    content = (args.get("content") or "").strip()
    if not content:
        return "错误：提醒内容为空"
    from datetime import datetime

    due = parse_reminder_time(content)
    clean = clean_reminder_text(content)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = db_conn()
    if due is None:
        conn.execute("INSERT INTO reminders(due_ts,content,done,created) VALUES(?,?,0,?)", (None, clean, now_str))
        conn.commit()
        conn.close()
        return f"已记录提醒（未识别到具体时间，会在每日简报中提示）：{clean}"
    conn.execute(
        "INSERT INTO reminders(due_ts,content,done,created) VALUES(?,?,0,?)",
        (due.strftime("%Y-%m-%d %H:%M:%S"), clean, now_str),
    )
    conn.commit()
    conn.close()
    return f"已设置提醒（{due.strftime('%Y-%m-%d %H:%M')}）：{clean}"


def tool_reminder_list(args):
    conn = db_conn()
    rows = conn.execute("SELECT due_ts,content FROM reminders WHERE done=0 ORDER BY due_ts ASC LIMIT 20").fetchall()
    conn.close()
    if not rows:
        return "当前没有待办提醒。"
    out = ["待办提醒："]
    for due, content in rows:
        out.append(f"- [{(due or '时间未定')}] {content}")
    return "\n".join(out)


# ---------- Phase 2.2：被动画像抽取 ----------
def parse_facts_text(text):
    """从 LLM 返回的画像抽取文本中解析 (key, value) 列表（纯函数，便于单测）。

    支持格式（每行一条）：
      - 称呼：老板
      - 偏好: 喜欢简洁回复
      - 领域：健康管理
    也容忍 '- 称呼：老板' / 'key: value'。空结果或含「（无）」时返回 []。
    返回去重后的 [(key, value), ...]。
    """
    facts = []
    seen = set()
    for line in (text or "").splitlines():
        line = line.strip().lstrip("-*•").strip()
        if not line or "（无）" in line or "(无)" in line:
            continue
        m = re.match(r"^([\u4e00-\u9fa5A-Za-z0-9_]{1,12})\s*[:：]\s*(.+)$", line)
        if not m:
            continue
        key = m.group(1).strip()
        val = m.group(2).strip().strip(" 。，,、；;")
        if not key or not val:
            continue
        if (key, val) in seen:
            continue
        seen.add((key, val))
        facts.append((key, val))
    return facts


def extract_profile():
    """【被动画像抽取】节流（每天最多一次，与每日笔记同策略）：用近期用户发言让
    Agnes 抽取可长期记住的事实（称呼/偏好/习惯/领域/项目），写入 profile 表。

    语义：被动抽取只「填空」，绝不覆盖用户显式设定的记忆（profile 以 key 为主键，
    profile_set 显式记忆优先）。今日已抽过则跳过，避免重复消耗额度。抽取失败不影响主链路。
    """
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    try:
        conn = db_conn()
        row = conn.execute("SELECT value FROM meta WHERE key='last_profile_extract'").fetchone()
        if row and row[0] == today:
            conn.close()
            return
        rows = conn.execute("SELECT content FROM chat_log WHERE role='user' ORDER BY id DESC LIMIT 40").fetchall()
        existing = {k for (k,) in conn.execute("SELECT key FROM profile").fetchall()}
        conn.close()
        if not rows:
            return
        recent = "\n".join(r[0] for r in rows)
        prompt = (
            "你是小6的画像抽取模块。下面是一段用户近期的发言。请从中提炼出"
            "值得长期记住的用户事实（如称呼、偏好、习惯、专业领域、正在做的项目）。\n"
            "规则：\n1. 只输出明确能从文本推断的事实，不要编造；\n"
            "2. 每条用「类别：内容」一行，类别限 称呼/偏好/习惯/领域/项目；\n"
            "3. 若无明确事实，只输出（无）。\n"
            "4. 只输出正文，不要解释、不要代码块。\n\n用户发言：\n" + recent
        )
        try:
            with agnes_completion([{"role": "user", "content": prompt}], tools=[], stream=False, timeout=60) as resp:
                d = json.loads(resp.read().decode("utf-8"))
            text = d["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("[profile-extract] 失败:", e)
            return
        facts = parse_facts_text(text)
        added = 0
        for key, val in facts:
            if key in existing:  # 被动抽取不覆盖显式记忆
                continue
            tool_profile_set({"key": key, "value": val})
            added += 1
        # 无论有无新事实都标记今日已抽，避免每天反复空抽
        conn = db_conn()
        conn.execute(
            "INSERT INTO meta(key,value) VALUES('last_profile_extract',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (today,),
        )
        conn.commit()
        conn.close()
        print(f"[profile-extract] 已抽取 {added} 条新画像（候选 {len(facts)}）")
    except Exception as e:
        print("[profile-extract] 异常:", e)


def extract_persons():
    """【人物卡片自动抽取】节流每天一次：从近期用户发言让 Agnes 抽取人物画像
    （姓名/关系/偏好/事件），写入 memories(event_type='person')。抽取失败不影响主链路。"""
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")
    try:
        from db import upsert_person

        conn = db_conn()
        row = conn.execute("SELECT value FROM meta WHERE key='last_person_extract'").fetchone()
        if row and row[0] == today:
            conn.close()
            return
        rows = conn.execute("SELECT content FROM chat_log WHERE role='user' ORDER BY id DESC LIMIT 60").fetchall()
        conn.close()
        if not rows:
            return
        recent = "\n".join(r[0] for r in rows)
        prompt = (
            "你是小6的人物抽取模块。下面是一段用户近期发言。请从中识别被提及的真实人物"
            "（如家人、同事、朋友、客户），并提炼每个人值得长期记住的画像。\n"
            "规则：\n1. 只输出能从文本明确推断的人物，不要编造；\n"
            "2. 每个人一行，格式：「姓名：关系/身份 · 偏好 · 相关事件」，如「小李：同事 · 负责后端 · 在做支付重构」；\n"
            "3. 若无明确人物，只输出（无）。\n"
            "4. 只输出正文，不要解释、不要代码块。\n\n用户发言：\n" + recent
        )
        try:
            with agnes_completion([{"role": "user", "content": prompt}], tools=[], stream=False, timeout=60) as resp:
                d = json.loads(resp.read().decode("utf-8"))
            text = d["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("[person-extract] 失败:", e)
            return
        added = 0
        for line in text.splitlines():
            line = line.strip()
            if not line or line == "（无）":
                continue
            if "：" in line:
                name, profile = line.split("：", 1)
            elif ":" in line:
                name, profile = line.split(":", 1)
            else:
                continue
            name = name.strip().strip("【").strip("】").strip("·").strip()
            profile = profile.strip()
            if not name or not profile:
                continue
            upsert_person(name, profile)
            added += 1
        conn = db_conn()
        conn.execute(
            "INSERT INTO meta(key,value) VALUES('last_person_extract',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (today,),
        )
        conn.commit()
        conn.close()
        print(f"[person-extract] 已抽取 {added} 个人物")
    except Exception as e:
        print("[person-extract] 异常:", e)
