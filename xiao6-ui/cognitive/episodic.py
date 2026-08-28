#!/usr/bin/env python3
"""庄周 · 认知层 · 情节记忆（Episodic Memory）

过去重要事件/决定/承诺/偏好的结构化条目，按与当前输入的**语义相关度**召回。
复用现有 embed.py 本地 ONNX 向量检索（零新依赖、本地优先），叠加
importance + recency 加权取 top-k。仅依赖 db / embed，不依赖 context。
"""

from __future__ import annotations

from datetime import datetime

from db import db_conn
from embed import add_vector, embed_doc, embed_query, model_ready, semantic_search

_TOP_K = 5


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_episode(title: str, summary: str, category: str = "fact", importance: float = 0.5,
                project: str = "", source: str = "system", event: str = "") -> int | None:
    """插入一条情节记忆并（best-effort）索引向量。返回新 id。

    - project：关联项目（如 ZhuangZhou）；空串表示不关联
    - source ：事件来源 system(阶段完成) / user(用户确认) / decision(关键决策)
    - event  ：事件类型标签
    仅记录可验证真实事件；禁止编造。
    """
    title = (title or "").strip() or (summary or "")[:40]
    summary = (summary or "").strip()
    if not summary:
        return None
    try:
        importance = max(0.0, min(1.0, float(importance)))
    except Exception:
        importance = 0.5
    # P5.2 · Canonical Memory Integration：写入不再由本模块直连 DB，统一经
    # cognitive.memory_adapter → memory.py Canonical Memory API（唯一写入权威），
    # episodes 表退化为 adapter 维护的兼容投影（召回读模型 + 向量索引引用键）。
    from cognitive.memory_adapter import record_episode

    eid = record_episode(
        title=title, summary=summary, category=category, importance=importance,
        project=project, source=source, event=event, created=_now(),
    ).get("projection_id")
    # 向量索引（best-effort，缺模型/出错均不影响主链路）
    try:
        if model_ready():
            add_vector("episode", eid, embed_doc(summary))
    except Exception as e:
        print(f"[episodic] 索引失败 eid={eid}: {e}")
    return eid


def recall_episodes(user_text: str, top_k: int = _TOP_K):
    """按语义相关度召回相关情节，返回 [(score, row), ...]。

    row = (id, title, summary, category, importance, created)
    总得分 = 0.6*余弦 + 0.25*importance + 0.15*recency_decay。
    """
    if not user_text or not model_ready():
        return []
    try:
        qv = embed_query(user_text)
    except Exception:
        return []
    conn = db_conn()
    try:
        cand = semantic_search("episode", qv, top_k=top_k * 3, min_score=0.18)
        if not cand:
            return []
        scored = []
        for ref_id, cos in cand:
            row = conn.execute(
                "SELECT id,title,summary,category,importance,created,project,source,event "
                "FROM episodes WHERE id=?",
                (ref_id,),
            ).fetchone()
            if not row:
                continue
            created = row[5] or ""
            try:
                dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
                age_days = (datetime.now() - dt).days
                recency = max(0.0, 1.0 - age_days / 180.0)
            except Exception:
                recency = 0.5
            imp = row[4] if row[4] is not None else 0.5
            final = 0.6 * cos + 0.25 * float(imp) + 0.15 * recency
            scored.append((final, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]
    finally:
        conn.close()
    # P5.2：访问统计更新（读路径副作用）亦交由 Memory 层投影模块执行，
    # 使 cognitive 内不再残留任何记忆表写入 SQL。
    from memory_projection import touch_episodes

    touch_episodes([row[0] for _, row in top], _now())
    return top


def render_episodes_block(items) -> str:
    """渲染【相关经历】列表（含项目/来源），硬上限约 600 token。"""
    if not items:
        return ""
    lines = []
    for score, row in items:
        eid, title, summary, category, importance, created = row[0], row[1], row[2], row[3], row[4], row[5]
        proj, src, evt = (row[6] or ""), (row[7] or ""), (row[8] or "")
        tag = f"[{category}] " if category else ""
        meta = " / ".join([m for m in (proj, src) if m])
        head = (f"{tag}{title}" + (f"（{meta}）" if meta else "")) + f"（相关度{score:.2f}）"
        snippet = (summary or "")[:160]
        lines.append(f"{head}\n  {snippet}")
    if not lines:
        return ""
    return "【相关经历】\n" + "\n\n".join(lines)


def list_episodes(limit: int = 20):
    """供 /api/episodes 调试/可观测：按最近访问 + 创建时间降序返回。"""
    try:
        limit = max(1, min(int(limit), 100))
    except Exception:
        limit = 20
    conn = db_conn()
    try:
        rows = conn.execute(
            "SELECT id,title,summary,category,importance,created,access_count,project,source,event "
            "FROM episodes ORDER BY COALESCE(last_accessed,'0000') DESC, created DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": r[0], "title": r[1], "summary": r[2], "category": r[3],
            "importance": r[4], "created": r[5], "access_count": r[6],
            "project": r[7], "source": r[8], "event": r[9],
        }
        for r in rows
    ]


# ── 真实事件记录入口（禁止编造；仅记录可验证事件）──

def record_phase_event(phase_name: str, project: str = "", importance: float = 0.95) -> int | None:
    """记录一个项目阶段完成事件（source='system'）。"""
    return add_episode(
        title="%s 完成" % phase_name,
        summary="阶段 %s 已交付并完成验收。" % phase_name,
        category="milestone",
        importance=importance,
        project=project,
        source="system",
        event="phase_complete",
    )


def record_user_confirmed(fact: str, project: str = "", importance: float = 0.9) -> int | None:
    """记录用户明确确认的事实（source='user'，L1 最高可信）。"""
    return add_episode(
        title="用户确认：%s" % fact[:40],
        summary=fact,
        category="confirmation",
        importance=importance,
        project=project,
        source="user",
        event="user_confirmed",
    )


def record_decision(decision: str, project: str = "", importance: float = 0.8) -> int | None:
    """记录一个关键决策事件（source='decision'）。"""
    return add_episode(
        title="决策：%s" % decision[:40],
        summary=decision,
        category="decision",
        importance=importance,
        project=project,
        source="decision",
        event="key_decision",
    )
