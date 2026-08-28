#!/usr/bin/env python3
"""庄周 · 记忆压缩与上下文注入（ACI 预判注入）"""

from db import db_conn
from focus import recent_foci
from geo_weather import build_geo_block
from llm import agnes_completion
from tasks import get_open_tasks
import hashlib
import time

# 当 chat_log 超过阈值，把最早的若干轮对话压缩成「长期记忆摘要」，
# 避免 system prompt 随对话增长无限膨胀（省 token + 保留长期价值）。
MEM_KEEP = 24  # 始终保留的最近原始轮次（即时上下文）
MEM_THRESHOLD = 40  # 总轮次超过此值才触发压缩
MEM_SUMMARY_MAXLINES = 12  # 长期摘要超过此行数触发「二次压缩」，防无限膨胀
# 自我学习：LLM 蒸馏经验的最小间隔（秒），避免高频对话时反复消耗 LLM 调用
LEARN_DISTILL_MIN_INTERVAL = 21600  # 6 小时
LEARN_WEIGHT_DEFAULT = 1.0


def _meta_get(key, default="0"):
    """读取 meta 表键值（best-effort）。"""
    try:
        conn = db_conn()
        row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        conn.close()
        return row[0] if row else default
    except Exception:
        return default


def _meta_set(key, value):
    """写入 meta 表键值（best-effort）。"""
    try:
        conn = db_conn()
        conn.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def compress_memory():
    """把最旧的对话轮次压缩进 memory_summary，并删除已压缩的原始行。

    增强（自我学习系统）：
      - 摘要再压缩：合并后行数超 MEM_SUMMARY_MAXLINES 时，二次 LLM 压缩成 ≤8 条，防无限膨胀；
      - 经验蒸馏：按 LEARN_DISTILL_MIN_INTERVAL 间隔，LLM 从近期对话抽取可持久学习经验写入 learnings 表。
    任何 LLM 失败均静默跳过，绝不阻塞对话主链路。
    """
    try:
        from datetime import datetime

        conn = db_conn()
        total = conn.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0]
        if total <= MEM_KEEP:
            conn.close()
            return
        prune = total - MEM_KEEP
        old = conn.execute("SELECT role,content FROM chat_log ORDER BY id ASC LIMIT ?", (prune,)).fetchall()
        convo = "\n".join((("用户" if r == "user" else "six") + "：" + c) for r, c in old)
        row = conn.execute("SELECT summary FROM memory_summary WHERE id=1").fetchone()
        prev = (row[0] if row and row[0] else "").strip()
        prompt = (
            "以下是与用户的若干历史对话片段，请压缩为简洁的中文要点"
            "（不超过 8 条，每条一行，只保留对长期服务用户有价值的事实、偏好、决定、待办、项目进展）。\n"
            "已有摘要：\n" + (prev or "（无）") + "\n\n新对话片段：\n" + convo
        )
        try:
            with agnes_completion([{"role": "user", "content": prompt}], tools=[], stream=False, timeout=60) as resp:
                import json

                d = json.loads(resp.read().decode("utf-8"))
            new_summary = d["choices"][0]["message"]["content"].strip()
        except Exception:
            conn.close()
            return  # 压缩失败不阻塞，下一轮再试
        merged = (prev + "\n" + new_summary).strip() if prev else new_summary

        # 摘要再压缩：行数超阈值时二次压缩，保持长期摘要精炼不膨胀
        merged_lines = [l for l in merged.split("\n") if l.strip()]
        if len(merged_lines) > MEM_SUMMARY_MAXLINES:
            try:
                re_prompt = (
                    "以下是一份长期记忆摘要，内容已偏多。请在不丢失关键事实/偏好/决定的前提下，"
                    "压缩为不超过 8 条的中文要点，每条一行：\n" + merged
                )
                with agnes_completion([{"role": "user", "content": re_prompt}], tools=[], stream=False, timeout=60) as resp:
                    import json as _json

                    d2 = _json.loads(resp.read().decode("utf-8"))
                re_sum = d2["choices"][0]["message"]["content"].strip()
                if re_sum:
                    merged = re_sum
            except Exception:
                pass

        conn.execute(
            "INSERT INTO memory_summary(id,summary,updated) VALUES(1,?,?) "
            "ON CONFLICT(id) DO UPDATE SET summary=excluded.summary, updated=excluded.updated",
            (merged, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.execute("DELETE FROM chat_log WHERE id IN (SELECT id FROM chat_log ORDER BY id ASC LIMIT ?)", (prune,))
        conn.commit()
        conn.close()

        # 经验蒸馏（门控 FEATURE_SELF_LEARNING）：按最小间隔触发，避免高频对话时反复消耗 LLM
        try:
            import config

            if getattr(config, "FEATURE_SELF_LEARNING", False):
                last = int(_meta_get("last_distill_ts", "0"))
                now_ts = int(time.time())
                if now_ts - last >= LEARN_DISTILL_MIN_INTERVAL:
                    _meta_set("last_distill_ts", now_ts)
                    _distill_learnings()
        except Exception:
            pass
    except Exception:
        pass


def _distill_learnings():
    """LLM 从近期对话蒸馏出可持久化的学习经验（偏好/纠错/方法），写入 learnings 表。"""
    try:
        conn = db_conn()
        rows = conn.execute("SELECT role,content FROM chat_log ORDER BY id DESC LIMIT 40").fetchall()
        conn.close()
        convo = "\n".join((("用户" if r == "user" else "six") + "：" + c) for r, c in reversed(rows))
        if not convo.strip():
            return
        prompt = (
            "分析以下最近与用户的对话，抽取可长期用于改进服务的「学习经验」。\n"
            "只输出真正有价值、可复用的一条或几条（最多 4 条），每条一行，格式严格为：\n"
            "类型|内容\n"
            "类型取值：preference(用户偏好/习惯)、correction(用户纠错/不要做什么)、method(有效做法/流程)。\n"
            "示例：preference|用户偏好用简体中文、简洁、带要点的回答\n"
            "只输出这些行，不要解释、不要编号。若没有值得长期记住的经验，输出空。\n\n对话：\n" + convo
        )
        with agnes_completion([{"role": "user", "content": prompt}], tools=[], stream=False, timeout=60) as resp:
            import json

            d = json.loads(resp.read().decode("utf-8"))
        text = d["choices"][0]["message"]["content"].strip()
        if not text:
            return
        tmap = {"preference": "feedback", "correction": "correction", "method": "distill"}
        for line in text.split("\n"):
            line = line.strip()
            if not line or "|" not in line:
                continue
            ltype, content = line.split("|", 1)
            ltype = ltype.strip().lower()
            content = content.strip()
            if not content:
                continue
            record_learning(content, tmap.get(ltype, "distill"))
    except Exception:
        pass


def record_learning(text, ltype="feedback"):
    """持久化一条学习经验（用户显式反馈或 LLM 蒸馏）。

    - content_hash UNIQUE 保证同一内容只增权重不重复写入（自然去重）；
    - best-effort，绝不抛错。
    """
    if not text or not isinstance(text, str):
        return
    text = text.strip()
    if len(text) > 500:
        text = text[:500]
    try:
        h = hashlib.md5(text.encode("utf-8")).hexdigest()
        from datetime import datetime

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = db_conn()
        conn.execute(
            "INSERT INTO learnings(type,content,content_hash,weight,created,last_used) "
            "VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(content_hash) DO UPDATE SET weight=weight+1, last_used=excluded.last_used",
            (ltype, text, h, LEARN_WEIGHT_DEFAULT, now, now),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_learnings(limit=20, ltype=None):
    """返回学习经验列表（按权重降序，权重高=被多次确认/触发）。"""
    try:
        conn = db_conn()
        if ltype:
            rows = conn.execute(
                "SELECT id,type,content,weight,created,last_used FROM learnings "
                "WHERE type=? ORDER BY weight DESC, id DESC LIMIT ?",
                (ltype, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id,type,content,weight,created,last_used FROM learnings "
                "ORDER BY weight DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        return [
            {"id": r[0], "type": r[1], "content": r[2], "weight": r[3], "created": r[4], "last_used": r[5]}
            for r in rows
        ]
    except Exception:
        return []


def build_learnings_block():
    """汇总自我学习经验，注入 system prompt 供模型「学以致用」。无数据返回空串。"""
    try:
        items = get_learnings(limit=12)
        if not items:
            return ""
        lines = []
        for it in items:
            tag = {"feedback": "用户偏好", "correction": "纠错", "distill": "经验"}.get(it["type"], it["type"])
            lines.append(f"  - [{tag}] {it['content']}")
        if not lines:
            return ""
        return "【自我学习经验】\n" + "\n".join(lines) + "\n"
    except Exception:
        return ""


def build_memory_block(recent=12):
    """汇总用户画像 + 长期记忆摘要 + 近期对话，作为 system prompt 的上下文注入。"""
    conn = db_conn()
    prof = conn.execute("SELECT key,value FROM profile ORDER BY key").fetchall()
    row = conn.execute("SELECT summary FROM memory_summary WHERE id=1").fetchone()
    summary = (row[0] if row and row[0] else "").strip()
    rows = conn.execute("SELECT role,content FROM chat_log ORDER BY id DESC LIMIT ?", (recent,)).fetchall()
    conn.close()
    parts = []
    if prof:
        # Phase 20.5 · Truth Layer：profile.项目 若与 User Model 高可信真相冲突，
        # 保留原行（不删除），但注入时标注「已失效，以用户模型为准」，避免失真污染。
        # P5.2 §12 · 反向依赖移除：原 `from cognitive.user_model import canonical_project`
        # 形成 memory → cognitive 反向依赖；现读 Memory 层中性 helper
        # （memory_projection 直读 user_model 投影 + 同一份纯选择逻辑），
        # 依赖方向恢复为 cognitive → memory 单向。
        canonical = ""
        try:
            from memory_projection import canonical_project
            canonical, _ = canonical_project()
        except Exception:
            canonical = ""
        lines = []
        for k, v in prof:
            if k == "项目" and canonical and (v or "").strip() and (v or "").strip() != canonical:
                lines.append("- 项目（已失效，以用户模型为准）：%s" % canonical)
            else:
                lines.append("- %s：%s" % (k, v))
        parts.append("【用户画像】\n" + "\n".join(lines))
    if summary:
        parts.append("【长期记忆摘要】\n" + summary)
    # Phase 38J · 打断「AI 历史回复 → 回灌 system prompt → 复述坏回复」回声闭环。
    # 仅保留用户侧内容作为记忆锚点；AI 自身历史回复（role=zhuangzhou/assistant）
    # 不再作为示范台词回灌 system prompt，避免坏回复被模型复述放大形成回声。
    if rows:
        turns = []
        for role, content in reversed(rows):
            if role != "user":
                continue
            turns.append(f"用户：{content}")
        if turns:
            parts.append("【近期对话记忆】\n" + "\n".join(turns))
    # 自我学习经验注入：让模型在回复时「学以致用」
    learn = build_learnings_block()
    if learn:
        parts.append(learn)
    if not parts:
        return ""
    return "\n\n" + "\n\n".join(parts) + "\n"


_hotspot_cache = {"txt": None, "at": 0.0, "ttl": 60.0}


def _cached_hotspot(message):
    """热点上下文：短超时(2s) + 60s 缓存 + 失败降级为空。

    Phase 19 性能修复——原 ``build_hotspot_context`` 直连外部热点 API，
    失败/超时（实测 502/timeout）会阻塞整条上下文构建 3–27s；本封装把它
    隔离为可降级的非阻塞部件，对话主链路不再被外部网络拖垮。
    """
    global _hotspot_cache
    now = time.time()
    if _hotspot_cache["txt"] is not None and (now - _hotspot_cache["at"]) < _hotspot_cache["ttl"]:
        return _hotspot_cache["txt"]
    txt = ""
    try:
        from hotspots import build_hotspot_context
        import threading
        import queue as _q

        _rq = _q.Queue()

        def _run():
            try:
                _rq.put(build_hotspot_context(message))
            except Exception:
                _rq.put("")

        _th = threading.Thread(target=_run, daemon=True)
        _th.start()
        _th.join(2.0)  # 最多等 2s，超时即放弃（降级为空）
        if not _th.is_alive():
            try:
                txt = _rq.get_nowait() or ""
            except Exception:
                txt = ""
    except Exception:
        txt = ""
    _hotspot_cache["txt"] = txt
    _hotspot_cache["at"] = now
    return txt


def build_context_prefix(message=""):
    """【ACI 预判注入】每次对话前预取当前时间 + 待办提醒 + 定位，模型「睁眼」即拿到。"""
    from datetime import datetime

    now = datetime.now()
    date = now.strftime("%Y年%m月%d日 %H:%M:%S 星期") + "一二三四五六日"[now.weekday()]
    conn = db_conn()
    rem = conn.execute("SELECT due_ts,content FROM reminders WHERE done=0 ORDER BY due_ts ASC LIMIT 10").fetchall()
    conn.close()
    rem_txt = ""
    if rem:
        lines = "\n".join(f"  - [{(d or '时间未定')}] {c}" for d, c in rem)
        rem_txt = "\n【待办提醒】\n" + lines
    geo_txt = build_geo_block()
    foci = recent_foci(6)
    focus_txt = ""
    if foci:
        lines = "\n".join(f"  - [{f['kind']}] {f['text']}" for f in foci)
        focus_txt = "\n【当前开放话题/焦点】\n" + lines
    open_tasks = get_open_tasks(5)
    task_txt = ""
    if open_tasks:
        lines = []
        for t in open_tasks:
            # Phase 38J · 进度脱敏：未完成任务标题仍注入以供续跑，
            # 但「第 X/Y 步」进度分数不再主动念给用户（避免进度泛滥与回声）。
            lines.append(f"  - #{t['id']} {t['title']}")
        task_txt = "\n【未完成任务（可续跑）】\n" + "\n".join(lines)
    try:
        hotspot_txt = _cached_hotspot(message)
    except Exception:
        hotspot_txt = ""
    if hotspot_txt:
        hotspot_txt = "\n" + hotspot_txt
    try:
        import prefetch

        pfx = prefetch.format_prefetched_items(prefetch.get_valid_prefetch())
        prefetch_txt = ("\n\n[预取背景] 系统已提前获取以下背景（天气/新闻），可直接引用：\n" + pfx) if pfx else ""
    except Exception:
        prefetch_txt = ""

    return f"\n\n[当前上下文] 现在时间：{date}{rem_txt}{focus_txt}{task_txt}{geo_txt}{hotspot_txt}{prefetch_txt}\n"


def build_system_prompt(message=""):
    import config

    name = config.AI_DISPLAY_NAME or "小6"
    base = config.SYSTEM_PROMPT.format(name=name)
    # Phase 12 · P12-2 人格一致性：人格块作为系统提示「第一段、最高优先级」注入，
    # 保证跨会话语气/风格/边界稳定。门控 FEATURE_PERSONA（纯 prompt 附加，零风险）。
    persona_block = ""
    try:
        if getattr(config, "FEATURE_PERSONA", False):
            from persona_engine import get_persona_prompt

            persona_block = get_persona_prompt()
    except Exception:
        pass
    return persona_block + base + build_context_prefix(message) + build_memory_block()


# ═══════════════════════════════════════════════════════════════════════════
# P4.2 · Canonical Memory API
# ---------------------------------------------------------------------------
# 单一写入/读取入口（依据 P4-MEMORY-CONTRACT.md）。
# 所有产品写入路径（memory_distiller / db.import_memories /
# db.upsert_memory_by_mem_id / db.upsert_person / hotspots / notes）必须经此 API，
# 禁止直接 `conn.execute("INSERT/UPDATE/DELETE FROM memories")` 绕过
# （Legacy Bypass 纪律，违反即阻断 P4.2 GATE）。
# memory_evolution.* 为显式治理层（状态/置信迁移），属 canonical 治理，不在绕过之列。
# ═══════════════════════════════════════════════════════════════════════════

import json as _mjson
from datetime import datetime as _mdt

_ALLOWED_STATUS = {"active", "deprecated", "conflict", "pending_review", "decayed", "consolidated"}


def _mnow():
    return _mdt.now().strftime("%Y-%m-%d %H:%M:%S")


def _mjson_or_none(v):
    """list/dict → JSON；str 原样；None → None（与 db._json_or_empty 区别：None 保持 NULL）。"""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    try:
        return _mjson.dumps(v, ensure_ascii=False)
    except Exception:
        return None


def _m_clamp_confidence(c):
    try:
        c = float(c)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, c))


def _m_norm_status(s):
    return s if s in _ALLOWED_STATUS else "active"


def _publish_memory_event(name, payload):
    """持久化成功后发布领域事件（绝不先于写入；发布失败静默，绝不影响持久化）。"""
    try:
        from eventbus import publish_domain

        publish_domain(name, payload, source="memory")
    except Exception:
        pass


def publish_memory_event(name, payload):
    """公开封装：持久化成功后发布 Memory 领域事件（best-effort，绝不阻塞主流程）。

    供 memory_evolution.* 治理层（consolidation / lifecycle）在成功变更后发布
    MEMORY_CONSOLIDATED / MEMORY_DECAYED 等语义事件，统一经 EventBus 单一来源。
    """
    _publish_memory_event(name, payload)


def _m_hash_exists_elsewhere(ch, self_id):
    from db import db_conn

    conn = db_conn()
    try:
        r = conn.execute(
            "SELECT 1 FROM memories WHERE content_hash=? AND id<>?", (ch, self_id)
        ).fetchone()
    finally:
        conn.close()
    return r is not None


def _m_set_archived(mid, val):
    from db import db_conn

    conn = db_conn()
    try:
        conn.execute("UPDATE memories SET archived=? WHERE id=?", (val, mid))
        conn.commit()
        conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


def create_memory(
    content,
    event_type="note",
    *,
    title=None,
    detail=None,
    mem_id=None,
    entities=None,
    concepts=None,
    tags=None,
    links=None,
    salience=0,
    source_ref=None,
    visibility=1,
    confidence=None,
    source=None,
    status="active",
    verified_at=None,
    timestamp=None,
):
    """Canonical Memory 创建（content_hash 幂等）。

    流程：validation → content_hash 去重 → persistence → domain event。
    - content_hash = db.memory_content_hash(content)，作为唯一幂等键；
    - ON CONFLICT(content_hash) DO NOTHING：同内容重复调用不产生重复行；
    - confidence / source / status 写入真实列（distiller 旧实现错塞进 tags，P4.2 修正）；
    - 仅当真实插入（rowcount==1）后发布 MEMORY_CREATED。
    返回新行 id；冲突未插入返回 None。
    """
    from db import db_conn, memory_content_hash

    content = (content or "").strip()
    if not content:
        return None
    ch = memory_content_hash(content)
    if ch is None:
        return None
    now = timestamp or _mnow()
    conn = db_conn()
    try:
        cur = conn.execute(
            "INSERT INTO memories("
            "event_type,content,title,detail,mem_id,entities,concepts,tags,links,"
            "salience,source_ref,timestamp,visibility,content_hash,confidence,source,status,verified_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(content_hash) DO NOTHING",
            (
                event_type or "note",
                content,
                (title or content[:60]),
                detail or "",
                mem_id,
                _mjson_or_none(entities),
                _mjson_or_none(concepts),
                _mjson_or_none(tags),
                _mjson_or_none(links),
                int(salience or 0),
                source_ref,
                now,
                int(visibility if visibility is not None else 1),
                ch,
                _m_clamp_confidence(confidence),
                source or "inference",
                _m_norm_status(status),
                verified_at,
            ),
        )
        inserted = cur.rowcount == 1
        new_id = cur.lastrowid if inserted else None
        conn.commit()
        conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        raise
    if inserted:
        _publish_memory_event(
            "MEMORY_CREATED",
            {
                "id": new_id,
                "event_type": event_type or "note",
                "content_hash": ch,
                "source": source or "inference",
            },
        )
    return new_id


def get_memory(*, id=None, mem_id=None, content_hash=None):
    """按 id / mem_id / content_hash 读取一条 canonical memory（含治理列）。"""
    from db import db_conn

    if id is None and mem_id is None and content_hash is None:
        return None
    if id is not None:
        where, arg = "id=?", id
    elif mem_id is not None:
        where, arg = "mem_id=?", mem_id
    else:
        where, arg = "content_hash=?", content_hash
    conn = db_conn()
    try:
        r = conn.execute(
            "SELECT id,event_type,content,detail,title,mem_id,entities,concepts,tags,links,"
            "salience,source_ref,timestamp,visibility,content_hash,archived,confidence,source,status,verified_at "
            "FROM memories WHERE " + where + " LIMIT 1",
            (arg,),
        ).fetchone()
    finally:
        conn.close()
    if not r:
        return None
    return {
        "id": r[0],
        "event_type": r[1],
        "content": r[2],
        "detail": r[3],
        "title": r[4],
        "mem_id": r[5],
        "entities": r[6],
        "concepts": r[7],
        "tags": r[8],
        "links": r[9],
        "salience": r[10],
        "source_ref": r[11],
        "timestamp": r[12],
        "visibility": r[13],
        "content_hash": r[14],
        "archived": r[15],
        "confidence": r[16],
        "source": r[17],
        "status": r[18],
        "verified_at": r[19],
    }


def update_memory(*, id=None, mem_id=None, content_hash=None, **fields):
    """更新指定字段（不触碰主键；改 content 会重算 content_hash 并按冲突去重）。
    返回是否发生更新（True/False）。None 值字段视为「不提供」被跳过（保留原值）。
    """
    from db import db_conn, memory_content_hash

    cur = get_memory(id=id, mem_id=mem_id, content_hash=content_hash)
    if not cur:
        return False
    allowed = {
        "event_type", "title", "detail", "entities", "concepts", "tags", "links",
        "salience", "source_ref", "visibility", "confidence", "source", "status",
        "verified_at", "archived", "content",
    }
    new_content = fields.get("content")
    if "content" in fields:
        new_content = (new_content or "").strip()
        if not new_content:
            fields = {k: v for k, v in fields.items() if k != "content"}
        else:
            nh = memory_content_hash(new_content)
            # 若其它行已占该 hash，放弃 content 变更（避免 UNIQUE 冲突），保留其余字段更新
            if nh != cur["content_hash"] and _m_hash_exists_elsewhere(nh, cur["id"]):
                fields = {k: v for k, v in fields.items() if k != "content"}
    sets, args = [], []
    for k, v in fields.items():
        if k not in allowed or v is None:
            continue
        if k == "confidence":
            v = _m_clamp_confidence(v)
        elif k == "status":
            v = _m_norm_status(v)
        elif k in ("entities", "concepts", "tags", "links"):
            v = _mjson_or_none(v)
        elif k == "content":
            v = new_content
            args.append(memory_content_hash(new_content))
            sets.append("content_hash=?")
        args.append(v)
        sets.append(f"{k}=?")
    if not sets:
        return False
    args.append(cur["id"])
    conn = db_conn()
    try:
        conn.execute(
            "UPDATE memories SET " + ", ".join(sets) + " WHERE id=?", tuple(args)
        )
        conn.commit()
        conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        raise
    _publish_memory_event(
        "MEMORY_UPDATED", {"id": cur["id"], "fields": list(fields.keys())}
    )
    return True


def archive_memory(*, id=None, mem_id=None, content_hash=None):
    """软归档（archived=1）。返回是否生效。"""
    cur = get_memory(id=id, mem_id=mem_id, content_hash=content_hash)
    if not cur or cur["archived"]:
        return False
    _m_set_archived(cur["id"], 1)
    _publish_memory_event(
        "MEMORY_ARCHIVED", {"id": cur["id"], "mem_id": cur.get("mem_id")}
    )
    return True


def restore_memory(*, id=None, mem_id=None, content_hash=None):
    """从归档恢复（archived=0）。返回是否生效。"""
    cur = get_memory(id=id, mem_id=mem_id, content_hash=content_hash)
    if not cur or not cur["archived"]:
        return False
    _m_set_archived(cur["id"], 0)
    _publish_memory_event(
        "MEMORY_UPDATED", {"id": cur["id"], "restored": True}
    )
    return True


def delete_memory(*, id=None, mem_id=None, content_hash=None, tombstone=True):
    """逻辑/合规擦除（tombstone）。默认 tombstone=True：置 status='deprecated' + archived=1，
    保留 id/timestamp 作为 tombstone，永不物理 DROP。tombstone=False 等同 archive。
    返回是否生效。
    """
    cur = get_memory(id=id, mem_id=mem_id, content_hash=content_hash)
    if not cur:
        return False
    from db import db_conn

    conn = db_conn()
    try:
        if tombstone:
            conn.execute(
                "UPDATE memories SET status='deprecated', archived=1 WHERE id=?",
                (cur["id"],),
            )
        else:
            conn.execute("UPDATE memories SET archived=1 WHERE id=?", (cur["id"],))
        conn.commit()
        conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        raise
    _publish_memory_event(
        "MEMORY_ARCHIVED", {"id": cur["id"], "tombstone": tombstone}
    )
    return True


def delete_by_source_ref(source_ref_prefix, tombstone=True):
    """Canonical 清理：删除某 source 写入的全部记忆（幂等重导前置）。

    - 匹配 source_ref LIKE 'prefix:%'（与 create_memory 写入的 ``f"{source}:{mem_id}"``
      同源），不影响其它来源记忆；
    - tombstone=True（默认）：status='deprecated' + archived=1（保留数据可恢复，绝不物理 DROP）；
    - tombstone=False：仅 archived=1；
    - 走 Canonical Memory Layer 内部批量更新（非逐行 API），仅发一次 MEMORY_ARCHIVED。
    返回受影响行数。
    """
    from db import db_conn

    like = (source_ref_prefix or "") + ":%"
    conn = db_conn()
    try:
        if tombstone:
            cur = conn.execute(
                "UPDATE memories SET status='deprecated', archived=1 WHERE source_ref LIKE ?",
                (like,),
            )
        else:
            cur = conn.execute(
                "UPDATE memories SET archived=1 WHERE source_ref LIKE ?", (like,)
            )
        n = cur.rowcount
        conn.commit()
        conn.close()
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        raise
    _publish_memory_event(
        "MEMORY_ARCHIVED",
        {"source_ref": source_ref_prefix, "rows": n, "tombstone": tombstone},
    )
    return n


def upsert_memory(mem):
    """按 mem_id PATCH/INSERT（canonical 等价物 of db.upsert_memory_by_mem_id）。

    mem_id 提供：已存在则 PATCH 传入字段（None 跳过），否则 INSERT。
    mem_id 缺失：按 content 走 create_memory。
    返回 mem_id（提供时）或新行 id。
    """
    if not isinstance(mem, dict):
        return None
    mem_id = mem.get("mem_id")
    content = (mem.get("content") or "").strip()
    if not mem_id:
        return create_memory(
            content,
            mem.get("event_type"),
            title=mem.get("title"),
            detail=mem.get("detail"),
            entities=mem.get("entities"),
            concepts=mem.get("concepts"),
            tags=mem.get("tags"),
            links=mem.get("links"),
            salience=mem.get("salience"),
            source_ref=mem.get("source_ref"),
            visibility=mem.get("visibility"),
            confidence=mem.get("confidence"),
            source=mem.get("source"),
            status=mem.get("status"),
        )
    existing = get_memory(mem_id=mem_id)
    if existing:
        update_memory(
            id=existing["id"],
            event_type=mem.get("event_type"),
            title=mem.get("title"),
            detail=mem.get("detail"),
            content=mem.get("content"),
            entities=mem.get("entities"),
            concepts=mem.get("concepts"),
            tags=mem.get("tags"),
            links=mem.get("links"),
            salience=mem.get("salience"),
            source_ref=mem.get("source_ref"),
            visibility=mem.get("visibility"),
        )
        return mem_id
    create_memory(
        content,
        mem.get("event_type"),
        title=mem.get("title"),
        detail=mem.get("detail"),
        mem_id=mem_id,
        entities=mem.get("entities"),
        concepts=mem.get("concepts"),
        tags=mem.get("tags"),
        links=mem.get("links"),
        salience=mem.get("salience"),
        source_ref=mem.get("source_ref"),
        visibility=mem.get("visibility"),
        confidence=mem.get("confidence"),
        source=mem.get("source"),
        status=mem.get("status"),
    )
    return mem_id


def search_memories(query, limit=20, since=None, until=None):
    """模糊/结构化搜索（canonical adapter → memory_query.query_memory）。"""
    try:
        from memory_query import query_memory

        return query_memory(query, limit=limit, since=since, until=until)
    except Exception:
        return []


def retrieve_memories(query, top_k=8):
    """经统一检索策略召回（canonical adapter → memory_evolution.DefaultEvolutionPolicy）。

    成功召回后（best-effort）发布 MEMORY_RETRIEVED（每调用一次，便于观测检索活动，不阻塞主流程）。
    """
    try:
        from memory_evolution import default as _me

        res = _me.retrieve(query, top_k=top_k)
    except Exception:
        res = []
    try:
        _publish_memory_event(
            "MEMORY_RETRIEVED", {"query": query or "", "count": len(res or [])}
        )
    except Exception:
        pass
    return res


def consolidate_memories(rows=None, authorized=False):
    """合并去重（canonical adapter → memory_evolution.consolidate）。"""
    try:
        from memory_evolution import default as _me

        return _me.consolidate(rows, authorized=authorized)
    except Exception:
        return None
