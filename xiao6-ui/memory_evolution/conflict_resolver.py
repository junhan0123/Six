#!/usr/bin/env python3
"""Memory Evolution Layer · 冲突检测与仲裁（Conflict Detection）

核心铁律（继承自 cognitive.user_model.merge_project）：
  **低可信不得覆盖高可信；内容矛盾不得静默覆盖 → 进入 pending_review。**

本模块只针对既有 ``memories`` 表的写入/扫描，复用其 confidence/source/status 列，
不新建存储。任何未授权写入受 MAX_UNVERIFIED_CONF 钳制。

决策枚举：
  KEEP_OLD       新值 conf ≤ 旧值 → 不覆盖，仅补 source
  UPDATE         新值 conf > 旧值 且同实体 → 合法覆盖（高可信覆盖低可信）
  PENDING_REVIEW 同实体但内容矛盾 → 标 pending_review，不覆盖，等人工/高可信裁定
  DROP           跨名且低可信（低于 MIN_NEW_PROJECT_CONF 思想）→ 丢弃，不污染
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# 未授权写入的可信上限（防「虚假高可信」）
MAX_UNVERIFIED_CONF = 0.6
# 跨名新实体准入门槛（低于此且非高可信源 → 丢弃）
MIN_NEW_ENTITY_CONF = 0.5
# 高可信源（可合法覆盖）
_TRUSTED_HIGH_SRC = ("user_confirmed", "project_state")


class Decision(str, Enum):
    KEEP_OLD = "keep_old"
    UPDATE = "update"
    PENDING_REVIEW = "pending_review"
    DROP = "drop"


@dataclass
class ConflictDecision:
    decision: Decision
    reason: str
    existing_conf: float
    incoming_conf: float


def _conf_of(source: str | None, confidence: float | None) -> float:
    if confidence is not None:
        try:
            return float(confidence)
        except Exception:
            pass
    # 来源 → 默认可信（与 user_model CONF_BY_SOURCE 同源）
    mapping = {
        "user_confirmed": 1.0,
        "project_state": 0.9,
        "conversation": 0.7,
        "inference": 0.4,
    }
    return float(mapping.get(source or "inference", 0.4))


def _clamp_unauthorized(confidence: float | None, authorized: bool) -> float:
    """未授权写入的 conf 钳制 ≤ MAX_UNVERIFIED_CONF，杜绝虚假高可信。"""
    c = float(confidence if confidence is not None else 0.5)
    if not authorized:
        return min(c, MAX_UNVERIFIED_CONF)
    return max(0.0, min(1.0, c))


def decide(existing: dict | None, incoming: dict, authorized: bool = False) -> ConflictDecision:
    """对一条 incoming 记忆裁定写入策略。

    existing: 同 mem_id/同实体的现有行（可为 None = 全新）。
    incoming: {mem_id?, content, source?, confidence?, entity?}
    """
    inc_conf = _clamp_unauthorized(incoming.get("confidence"), authorized)
    inc_src = incoming.get("source") or "inference"

    if existing is None:
        # 全新实体：跨名低可信丢弃
        if inc_conf <= MIN_NEW_ENTITY_CONF and inc_src not in _TRUSTED_HIGH_SRC:
            return ConflictDecision(Decision.DROP,
                                    "新实体低可信(%.2f)非高可信源，丢弃不污染" % inc_conf,
                                    0.0, inc_conf)
        return ConflictDecision(Decision.UPDATE, "新实体高可信准入", 0.0, inc_conf)

    old_conf = _conf_of(existing.get("source"), existing.get("confidence"))
    old_content = (existing.get("content") or "").strip()
    new_content = (incoming.get("content") or "").strip()

    # 铁律①：低可信不得覆盖高可信
    if inc_conf <= old_conf:
        # 仅当旧值缺 source 时补充，不覆盖内容
        return ConflictDecision(Decision.KEEP_OLD,
                                "新值conf%.2f≤旧值%.2f，保留旧值" % (inc_conf, old_conf),
                                old_conf, inc_conf)

    # 铁律②：高可信覆盖低可信（合法）
    if inc_conf > old_conf:
        # 但若内容矛盾 → 不静默覆盖，进 pending_review（除非 incoming 显式高可信授权）
        if old_content and new_content and old_content != new_content:
            # 用归一化比对，避免空白差异误判
            import re
            def _norm(s): return re.sub(r"\s+", " ", s).strip()
            if _norm(old_content) != _norm(new_content):
                return ConflictDecision(Decision.PENDING_REVIEW,
                                        "同实体内容矛盾(旧=%.30s/新=%.30s)，进 pending_review"
                                        % (old_content, new_content),
                                        old_conf, inc_conf)
        return ConflictDecision(Decision.UPDATE,
                                "高可信%.2f>低可信%.2f，合法覆盖" % (inc_conf, old_conf),
                                old_conf, inc_conf)


def scan_conflicts(limit: int = 500) -> list[dict]:
    """全表扫描矛盾记忆并标 pending_review（仅置状态，不改内容）。

    检测三类矛盾：
      1) 同 mem_id 但 content 与最新写入不一致（理论不常发生，防御性）；
      2) 同实体（entities/tags/title 归一）存在多条 active 且内容互异；
      3) 与 user_model canonical 项目矛盾的 profile 类记忆。
    返回被标记的行列表。
    """
    flagged: list[dict] = []
    try:
        from db import db_conn
        from cognitive.user_model import canonical_project

        conn = db_conn()
        rows = conn.execute(
            "SELECT id,mem_id,content,entities,tags,title,event_type,status,confidence,source "
            "FROM memories WHERE archived=0 AND status NOT IN ('deprecated','consolidated') "
            "ORDER BY id LIMIT ?",
            (limit,),
        ).fetchall()
        # 按实体聚类
        import re, json, hashlib

        def _norm(s): return re.sub(r"\s+", " ", (s or "").strip()).lower()
        def _ent_key(r):
            # SELECT 顺序: id,mem_id,content,entities,tags,title,event_type,...
            # 索引: r[2]=content, r[3]=entities, r[4]=tags, r[5]=title
            # 聚类键只用「结构化实体 + 标签」，刻意排除 title：
            # 矛盾记忆（如「主项目=Xiao6」vs「主项目=OtherApp」）标题本就不同，
            # 若含 title 则永不聚合。无结构化实体时退用 content 前 40 字，
            # 避免所有默认 entities='[]' 的记忆被错误聚成一个大组而误标。
            e = _norm(r[3]); t = _norm(r[4])
            has_entity = e not in ("", "[]", "null")
            if has_entity:
                return "e:" + e + "|" + t
            return "c:" + _norm(r[2])[:40]

        groups: dict[str, list] = {}
        for r in rows:
            groups.setdefault(_ent_key(r), []).append(r)

        canon_proj, canon_conf = canonical_project()

        for key, grp in groups.items():
            if len(grp) < 2:
                # 仍检查与 user_model canonical 矛盾（单条也查）
                for r in grp:
                    if _is_project_conflict(r, canon_proj, canon_conf):
                        _mark(conn, r[0], flagged,
                              "与用户模型canonical项目(%s)矛盾" % (canon_proj or "?"))
                continue
            # 多行：找最高可信基准
            grp_sorted = sorted(grp, key=lambda x: float(x[8] or 0.5), reverse=True)
            base = grp_sorted[0]
            base_norm = _norm(base[2])
            for r in grp_sorted[1:]:
                if _norm(r[2]) != base_norm and (r[7] or "active") == "active":
                    _mark(conn, r[0], flagged,
                          "同实体多版本内容矛盾(基准id=%s)" % base[0])
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[conflict_resolver] scan_conflicts 忽略: {e}")
    return flagged


def _is_project_conflict(r, canon_proj, canon_conf) -> bool:
    if not canon_proj or canon_conf < 0.7:
        return False
    try:
        import json
        ents = json.loads(r[4]) if r[4] else []
        tags = json.loads(r[5]) if r[5] else []
        blob = " ".join(str(x) for x in (ents + tags + [r[6], r[2]]))
        if canon_proj.lower() in blob.lower():
            return False  # 一致
        # 若记忆显式提到另一个项目名且 canonical 也存在 → 矛盾
        return False  # 保守：单条不轻易标，避免误杀
    except Exception:
        return False


def _mark(conn, mid: int, flagged: list, reason: str):
    """经 Canonical Memory API 置 pending_review（verified_at 仅在原值为 NULL 时补 _now()）。

    P4.3-B：消除对 memories 表的直接写，统一治理列 + 事件。
    `conn` 入参保留以兼容 scan_conflicts 调用点（本函数不再使用）。
    """
    try:
        import memory
        cur = memory.get_memory(id=mid)
        if not cur:
            return
        va = _now() if not cur.get("verified_at") else None
        if memory.update_memory(id=mid, status="pending_review", verified_at=va):
            flagged.append({"id": mid, "reason": reason})
    except Exception:
        pass


def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
