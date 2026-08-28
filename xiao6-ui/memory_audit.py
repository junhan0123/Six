"""庄周 · 记忆审计（纯标准库实现）。

提供记忆存储的「查看」与「（显式）清理」：audit() 汇总统计与样本；
prune(store,...) 按天数清理过期条目（仅用户显式触发，绝不自动执行）；
build_audit_payload() 包装前端面板载荷。防御式编程，任意存储失败均静默降级，
通过各模块自身原语访问数据，不修改任何既有文件（对齐 worldcup.py / person_card.py）。
"""

from datetime import datetime, timedelta
# 这些模块不 import 本文件，顶层导入安全；仍逐层 try/except 以便缺失 API 时优雅降级。
try:
    import db as _db
except Exception:
    _db = None
try:
    import notes as _notes
except Exception:
    _notes = None
try:
    import person_card as _pc
except Exception:
    _pc = None
def _now_iso():
    """当前时间（与项目其余日志格式一致）。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def _cutoff(keep_days):
    """返回 keep_days 天前的时间阈值，用于判断条目是否过期。"""
    return (datetime.now() - timedelta(days=int(keep_days))).strftime("%Y-%m-%d %H:%M:%S")
def _snippet(text, n=60):
    """内容截断为摘要，超长加省略号。"""
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= n else text[:n] + "…"

# ---------- 各存储采样（读取路径，全部防御式） ----------
def _sample_chat():
    """从 db.chat_log 读取对话历史统计与最近 5 条样本。"""
    store = {"name": "chat", "count": 0, "samples": []}
    if _db is None or not hasattr(_db, "db_conn"):
        store["note"] = "不可用"
        return store
    try:
        conn = _db.db_conn()
        try:
            store["count"] = conn.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0]
            rows = conn.execute("SELECT ts, role, content FROM chat_log ORDER BY id DESC LIMIT 5").fetchall()
            store["samples"] = [{"role": r[1], "snippet": _snippet(r[2]), "ts": r[0]} for r in rows]
        finally:
            conn.close()
    except Exception as e:
        store["note"] = "读取失败：" + str(e)
    return store
def _sample_notes():
    """从 notes.get_notes 读取笔记统计与最近 5 条样本。"""
    store = {"name": "notes", "count": 0, "samples": []}
    if _notes is None or not hasattr(_notes, "get_notes"):
        store["note"] = "不可用"
        return store
    try:
        rows = _notes.get_notes(limit=5)
        store["count"] = len(rows)
        if _db is not None and hasattr(_db, "db_conn"):
            try:
                conn = _db.db_conn()
                store["count"] = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
                conn.close()
            except Exception:
                pass
        store["samples"] = [{"title": r.get("title", ""), "snippet": _snippet(r.get("markdown") or r.get("content")), "ts": r.get("ts", "")} for r in rows]
    except Exception as e:
        store["note"] = "读取失败：" + str(e)
    return store
def _sample_person_cards():
    """从 person_card.list_cards 读取人物卡统计与最近 5 个名字。"""
    store = {"name": "person_cards", "count": 0, "samples": []}
    if _pc is None or not hasattr(_pc, "list_cards"):
        store["note"] = "不可用"
        return store
    try:
        cards = _pc.list_cards()
        store["count"] = len(cards)
        store["samples"] = [{"name": c.get("name", "")} for c in cards[:5]]
    except Exception as e:
        store["note"] = "读取失败：" + str(e)
    return store

# ---------- 公开 API ----------
def audit():
    """汇总各记忆存储：统计 + 最近样本。

    返回 {"stores":[{name,count,samples,note?}], "totals":{..}, "generated_at":<iso>}。
    任一存储 API 缺失/异常时，对应项报告 count=0、samples=[]、note="不可用"。
    """
    stores = [_sample_chat(), _sample_notes(), _sample_person_cards()]
    totals = {s["name"]: s.get("count", 0) for s in stores}
    totals["all"] = sum(totals.values())
    return {"stores": stores, "totals": totals, "generated_at": _now_iso()}
def build_audit_payload():
    """返回供前端审计面板直接消费的载荷（在 audit() 之上补充展示元信息）。"""
    data = audit()
    data["ok"] = True
    data["title"] = "记忆审计"
    return data
def prune(store, keep_days=30):
    """按天数清理某个记忆存储中过期的条目。

    仅当用户显式触发时调用，本函数不会被任何定时/自动逻辑调用（绝不误删）。
    受支持存储：notes / chat / person_cards。无对应删除能力时返回
    {"ok":False,"note":"该存储暂不支持清理"}。
    """
    store = (store or "").strip().lower()
    if store not in ("notes", "chat", "person_cards"):
        return {"ok": False, "store": store, "note": "未知存储，支持：notes/chat/person_cards"}
    cutoff = _cutoff(keep_days)
    try:
        if store == "notes":
            return _prune_notes(cutoff)
        if store == "chat":
            return _prune_chat(cutoff)
        if store == "person_cards":
            return _prune_person_cards(cutoff)
    except Exception as e:
        return {"ok": False, "store": store, "note": "清理异常：" + str(e)}
    return {"ok": False, "store": store, "note": "该存储暂不支持清理"}

# ---------- 清理实现（均使用对应模块自身原语，防御式） ----------
def _prune_notes(cutoff):
    """删除早于 cutoff 的笔记（连同 FTS 索引一起清理）。"""
    if _db is None or not hasattr(_db, "db_conn"):
        return {"ok": False, "store": "notes", "note": "该存储暂不支持清理"}
    try:
        conn = _db.db_conn()
        try:
            old = conn.execute("SELECT id FROM notes WHERE ts < ?", (cutoff,)).fetchall()
            deleted = len(old)
            for (nid,) in old:
                conn.execute("DELETE FROM notes WHERE id=?", (nid,))
                if hasattr(_db, "fts_delete"):
                    try:
                        _db.fts_delete(conn, nid)
                    except Exception:
                        pass
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "deleted": deleted, "store": "notes"}
    except Exception as e:
        return {"ok": False, "store": "notes", "note": "清理失败：" + str(e)}
def _prune_chat(cutoff):
    """删除早于 cutoff 的对话记录，但『绝不清空全部』（保留至少一条，避免误抹历史）。"""
    if _db is None or not hasattr(_db, "db_conn"):
        return {"ok": False, "store": "chat", "note": "该存储暂不支持清理"}
    try:
        conn = _db.db_conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0]
            old = conn.execute("SELECT COUNT(*) FROM chat_log WHERE ts < ?", (cutoff,)).fetchone()[0]
            if old == 0:
                return {"ok": True, "deleted": 0, "store": "chat"}
            if old >= total:  # 安全护栏：清理会删光整表则中止，保留全部历史
                return {"ok": False, "store": "chat", "note": "清理会清空全部对话历史，已中止"}
            conn.execute("DELETE FROM chat_log WHERE ts < ?", (cutoff,))
            conn.commit()
            deleted = conn.execute("SELECT changes()").fetchone()[0]
        finally:
            conn.close()
        return {"ok": True, "deleted": deleted, "store": "chat"}
    except Exception as e:
        return {"ok": False, "store": "chat", "note": "清理失败：" + str(e)}
def _prune_person_cards(cutoff):
    """删除 updated 早于 cutoff 的人物卡（使用 person_card 自身的读写原语）。"""
    if _pc is None or not (hasattr(_pc, "_load") and hasattr(_pc, "_save")):
        return {"ok": False, "store": "person_cards", "note": "该存储暂不支持清理"}
    try:
        cards = _pc._load()
        kept = [c for c in cards if (c.get("updated") or "") >= cutoff]
        removed = len(cards) - len(kept)
        if removed == 0:
            return {"ok": True, "deleted": 0, "store": "person_cards"}
        _pc._save(kept)
        return {"ok": True, "deleted": removed, "store": "person_cards"}
    except Exception as e:
        return {"ok": False, "store": "person_cards", "note": "清理失败：" + str(e)}
