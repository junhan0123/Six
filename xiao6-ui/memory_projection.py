#!/usr/bin/env python3
"""庄周 · Memory 层 · Legacy 投影写入器（P5.2 · Canonical Memory Integration）

**定位（务必读清，避免误判为「第二套记忆系统」）：**

本模块是 P5.2 §13 PROJECTION RULE 的落地点：把原先散落在
`cognitive/user_model.py`、`cognitive/episodic.py`、`agent_runtime.py` 里的
**既有** legacy 记忆表写入 SQL（user_model / episodes / conversation_memories）
原样搬迁到 Memory 层的单一归属地。

它**不是**：
  - 第二套 Memory 系统 —— 无检索、无排序、无合并、无生命周期、无冲突消解；
  - 第二套持久层 —— 沿用既有 `db.db_conn()` 与既有表 schema，未新建库/表；
  - 第二个写入权威 —— 写入权威由 Canonical Memory（`memory.py`）持有，
    本模块产出的 legacy 行仅是**兼容投影 / 读模型**（P5.2 §13）。

它**是**：
  - legacy 投影写入的唯一归属地（禁止再散落进 cognitive 业务模块）；
  - 唯一合法调用方：Memory 层自身 与 `cognitive.memory_adapter`（由 adapter 独占编排）。

另含 P5.2 §12（反向依赖移除）所需的中性纯变换 `select_canonical_project()` /
`canonical_project()`：`memory.py` 原先 `from cognitive.user_model import canonical_project`
形成 memory → cognitive 反向依赖，现改读本模块，依赖方向恢复为 cognitive → memory 单向。
`cognitive.user_model.canonical_project()` 亦委托本模块的纯变换，零逻辑重复。

依赖：仅 `db` + 标准库。不 import memory / cognitive / policy / executor。
"""

from __future__ import annotations

import json as _json
from datetime import datetime

from db import db_conn

# ── user_model 投影：legacy 置信度演化常量（数值沿用迁移前实现，未做任何调整）──
# 迁移前来源：cognitive/user_model.py::upsert_user_model
#   bump=True  → new_conf = min(0.95, (旧值 or 0.0) + 0.05)
#   bump=False → new_conf = 旧值 or 0.5
_UM_CONF_CAP = 0.95
_UM_CONF_STEP = 0.05
_UM_CONF_FALLBACK = 0.5


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════════════════
# user_model 投影（单行 id=1；O(1) 读取的兼容读模型）
# ═══════════════════════════════════════════════════════════════════════════

def user_model_row():
    """读取 user_model 投影行 → (data_json, confidence, updated)；空返回 None。"""
    conn = db_conn()
    try:
        return conn.execute(
            "SELECT data, confidence, updated FROM user_model WHERE id=1"
        ).fetchone()
    finally:
        conn.close()


def write_user_model(data_json: str, *, bump_confidence: bool = True,
                     updated: str | None = None) -> float:
    """写入 user_model 投影行（legacy 语义等价：INSERT ... ON CONFLICT(id) DO UPDATE）。

    置信度读-改-写在同一连接内完成（较迁移前更紧凑，数值语义完全一致）。
    返回写入后的 confidence。
    """
    conn = db_conn()
    try:
        row = conn.execute("SELECT confidence FROM user_model WHERE id=1").fetchone()
        if bump_confidence:
            new_conf = min(_UM_CONF_CAP, (row[0] if row else 0.0) + _UM_CONF_STEP)
        else:
            new_conf = row[0] if row else _UM_CONF_FALLBACK
        conn.execute(
            "INSERT INTO user_model(id,data,confidence,updated) VALUES(1,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET data=excluded.data, "
            "confidence=excluded.confidence, updated=excluded.updated",
            (data_json, new_conf, updated or _now()),
        )
        conn.commit()
        return new_conf
    finally:
        conn.close()


def select_canonical_project(model) -> tuple[str | None, float]:
    """纯变换：从用户模型字典里取「最可信项目」→ (name, confidence)。

    P5.2 §12：这是原 `cognitive.user_model.canonical_project` 的**纯选择逻辑**，
    下沉到 Memory 层作为中性 helper，供 memory.py 与 cognitive 双方复用（零重复实现）。
    """
    best, best_c = None, 0.0
    if not isinstance(model, dict):
        return (None, 0.0)
    for p in (model.get("projects") or []):
        if not isinstance(p, dict):
            continue
        try:
            c = float(p.get("confidence", 0) or 0)
        except (TypeError, ValueError):
            continue
        if c > best_c:
            best_c = c
            best = p.get("name")
    return (best, best_c)


def canonical_project() -> tuple[str | None, float]:
    """读 user_model 投影 → 最可信项目 (name, confidence)。失败/空返回 (None, 0.0)。

    供 `memory.py` 交叉校验 profile.项目（替代原 memory → cognitive 反向导入）。
    与 cognitive 版差异：本函数为**纯读**，不触发 user_model 引导播种（bootstrap）。
    """
    try:
        row = user_model_row()
        if not row or not row[0]:
            return (None, 0.0)
        return select_canonical_project(_json.loads(row[0]))
    except Exception:
        return (None, 0.0)


# ═══════════════════════════════════════════════════════════════════════════
# episodes 投影（情节记忆读模型；向量索引 scope='episode' 依赖其自增 id）
# ═══════════════════════════════════════════════════════════════════════════

def insert_episode(*, title: str, summary: str, category: str = "fact",
                   importance: float = 0.5, created: str | None = None,
                   project: str = "", source: str = "system",
                   event: str = "") -> int | None:
    """插入 episodes 投影行（列与截断长度沿用迁移前实现）。返回新 id。"""
    conn = db_conn()
    try:
        cur = conn.execute(
            "INSERT INTO episodes(title,summary,category,importance,created,project,source,event) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (title, summary, category, importance, created or _now(),
             (project or "")[:120], (source or "system")[:32], (event or "")[:64]),
        )
        eid = cur.lastrowid
        conn.commit()
        return eid
    finally:
        conn.close()


def touch_episodes(ids, now: str | None = None) -> None:
    """召回后的访问统计更新（last_accessed / access_count）—— 读路径副作用，非记忆写入。"""
    ids = [i for i in (ids or []) if i is not None]
    if not ids:
        return
    stamp = now or _now()
    conn = db_conn()
    try:
        for eid in ids:
            conn.execute(
                "UPDATE episodes SET last_accessed=?, access_count=access_count+1 WHERE id=?",
                (stamp, eid),
            )
        conn.commit()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# conversation_memories 投影（P12-3 对话沉淀读模型）
# ═══════════════════════════════════════════════════════════════════════════

def insert_conversation_memory(*, date: str, topic: str, key_points,
                               sentiment: str = "neutral",
                               created: str | None = None) -> int | None:
    """插入 conversation_memories 投影行（key_points 落 JSON，语义沿用迁移前实现）。"""
    if isinstance(key_points, str):
        kp = key_points
    else:
        kp = _json.dumps(list(key_points or []), ensure_ascii=False)
    conn = db_conn()
    try:
        cur = conn.execute(
            "INSERT INTO conversation_memories(date, topic, key_points, sentiment, created) "
            "VALUES(?,?,?,?,?)",
            (date, topic, kp, sentiment, created or _now()),
        )
        rid = cur.lastrowid
        conn.commit()
        return rid
    finally:
        conn.close()
