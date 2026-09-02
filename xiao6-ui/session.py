"""Phase 44 · Session & Checkpoint Foundation — Facade / Coordination layer.

设计纪律（红线自检）：
- 本模块是 FACADE，不是第二套系统。
- 它**不拥有**任何 canonical truth：
  * 对话 truth  → db.chat_log（server.py line ~2502 已用 session_id 作为线程键）
  * Goal truth  → goals.py / goals 表
  * Task truth  → tasks.py / tasks 表
  * Runtime     → agent_runtime.py（只读投影，不改执行逻辑）
  * Event       → eventbus.py（本阶段不新增任何事件；复用既有 DOMAIN 事件）
  * Memory      → memory / memory_v2（本阶段不涉及）
- 本模块仅持久化两种“协调元数据 / 引用指针”（位于既有 xiao6.db，非新 db 文件）：
  * session_registry   —— 会话生命周期协调索引（created_at/updated_at/status），无内容列。
  * session_checkpoints —— 可恢复边界的**引用**（goal_id/task_id/chat_log_id/runtime_ref），
                          不复制目标/任务/对话内容。
- 新增的 goals.session_id / tasks.session_id 软外键列（db._migrate_session）与既有
  tasks.goal_id 同构，仅用于“一次会话产生的目标/任务”聚合投影，不复制任何内容。

所有写出口均 best-effort / 异常静默，绝不阻断主链路（server.py 调用处亦 try/except 包裹）。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from db import db_conn

SESSION_ID_MAX_LEN = 64  # 与 server.py chat handler 的 session_id 截断上限一致（line ~2502）


# ---------------------------------------------------------------------------
# 数据容器
# ---------------------------------------------------------------------------
@dataclass
class Session:
    session_id: str
    created_at: str
    updated_at: Optional[str] = None
    status: str = "active"


@dataclass
class Checkpoint:
    checkpoint_id: str
    session_id: str
    created_at: str
    goal_id: Optional[int] = None
    task_id: Optional[int] = None
    chat_log_id: Optional[int] = None
    runtime_ref: Optional[str] = None
    label: Optional[str] = None
    status: str = "valid"


@dataclass
class SessionProjection:
    session_id: str
    conversation: List[dict] = field(default_factory=list)
    active_goals: List[dict] = field(default_factory=list)
    active_tasks: List[dict] = field(default_factory=list)
    runtime_state: dict = field(default_factory=dict)
    latest_checkpoint: Optional[Checkpoint] = None


@dataclass
class ResumeResult:
    status: str  # valid | stale | invalid | missing | requires_replan
    checkpoint: Optional[Checkpoint] = None
    goal_id: Optional[int] = None
    task_id: Optional[int] = None
    next_action: str = "none"  # continue | requires_replan | none
    reason: str = ""


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def normalize_session_id(raw) -> str:
    """规范化会话标识：沿用 server.py 的现有 session_id 语义，截断 64 字符，缺省 'default'。"""
    if not raw:
        return "default"
    return str(raw).strip()[:SESSION_ID_MAX_LEN] or "default"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Session 生命周期（协调索引，仅元数据）
# ---------------------------------------------------------------------------
def create_session(raw_id=None) -> Session:
    """注册 / 复用一个会话协调记录（幂等 upsert）。不创建任何 canonical 数据。"""
    sid = normalize_session_id(raw_id)
    now = _now()
    conn = db_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO session_registry(session_id, created_at, updated_at, status) "
            "VALUES(?,?,?, 'active')",
            (sid, now, now),
        )
        conn.execute(
            "UPDATE session_registry SET updated_at=?, status='active' WHERE session_id=?",
            (now, sid),
        )
        conn.commit()
        row = conn.execute(
            "SELECT session_id, created_at, updated_at, status FROM session_registry WHERE session_id=?",
            (sid,),
        ).fetchone()
    finally:
        conn.close()
    return Session(*row)


def get_session(raw_id) -> Optional[Session]:
    """读取会话协调记录；若不存在则返回 None（投影不依赖此函数）。"""
    sid = normalize_session_id(raw_id)
    conn = db_conn()
    try:
        row = conn.execute(
            "SELECT session_id, created_at, updated_at, status FROM session_registry WHERE session_id=?",
            (sid,),
        ).fetchone()
    finally:
        conn.close()
    return Session(*row) if row else None


def close_session(raw_id) -> bool:
    """将会话协调记录标记为 closed（仅元数据标签，不影响任何 canonical 数据）。返回是否存在该记录。"""
    sid = normalize_session_id(raw_id)
    now = _now()
    conn = db_conn()
    try:
        cur = conn.execute(
            "UPDATE session_registry SET status='closed', updated_at=? WHERE session_id=?",
            (now, sid),
        )
        conn.commit()
        existed = cur.rowcount > 0
    finally:
        conn.close()
    return existed


# ---------------------------------------------------------------------------
# 软外键标记（最小集成 seam：把会话产生的 goal/task 打上 session_id 标签）
# ---------------------------------------------------------------------------
def link_goal(raw_id, goal_id) -> bool:
    """将某 goal 标记为属于某会话（写既有 goals.session_id 列；goals.py 逻辑不被改动）。"""
    sid = normalize_session_id(raw_id)
    try:
        conn = db_conn()
        conn.execute("UPDATE goals SET session_id=? WHERE id=?", (sid, int(goal_id)))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def link_task(raw_id, task_id) -> bool:
    """将某 task 标记为属于某会话（写既有 tasks.session_id 列；tasks.py 逻辑不被改动）。"""
    sid = normalize_session_id(raw_id)
    try:
        conn = db_conn()
        conn.execute("UPDATE tasks SET session_id=? WHERE id=?", (sid, int(task_id)))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Projection（只读聚合既有 canonical source）
# ---------------------------------------------------------------------------
def get_projection(raw_id) -> SessionProjection:
    """从既有 canonical 系统聚合本次会话的投影视图。只读取，不写入 canonical 数据。"""
    sid = normalize_session_id(raw_id)
    proj = SessionProjection(session_id=sid)

    # 1) 对话（复用 db.chat_log，server.py save_turn 的落点）
    conn = db_conn()
    try:
        rows = conn.execute(
            "SELECT role, content, ts FROM chat_log WHERE session=? ORDER BY id DESC LIMIT 20",
            (sid,),
        ).fetchall()
        proj.conversation = [
            {"role": r[0], "content": r[1], "ts": r[2]} for r in reversed(rows)
        ]

        # 2) 会话范围内的活跃目标（goals.session_id 软外键）
        grows = conn.execute(
            "SELECT id, title, status FROM goals WHERE session_id=? "
            "AND status IN ('active','paused') ORDER BY id DESC",
            (sid,),
        ).fetchall()
        proj.active_goals = [
            {"id": g[0], "title": g[1], "status": g[2]} for g in grows
        ]

        # 3) 会话范围内的活跃任务（直接打标 或 经 goal 归属）
        trows = conn.execute(
            "SELECT id, title, status FROM tasks WHERE "
            "(session_id=? OR goal_id IN (SELECT id FROM goals WHERE session_id=?)) "
            "AND status IN ('open','running') ORDER BY id DESC",
            (sid, sid),
        ).fetchall()
        proj.active_tasks = [
            {"id": t[0], "title": t[1], "status": t[2]} for t in trows
        ]
    finally:
        conn.close()

    # 4) 运行时状态（只读投影 agent_runtime，异常静默；不改动任何执行逻辑）
    proj.runtime_state = _read_runtime_state()

    # 5) 最近检查点
    proj.latest_checkpoint = get_checkpoint(sid)
    return proj


def _read_runtime_state() -> dict:
    """只读读取 AgentRuntime 当前执行身份（goal_id / running / queue）。失败返回空。"""
    try:
        import agent_runtime

        rt = agent_runtime.runtime
        return {
            "running": bool(getattr(rt, "_running", False)),
            "current_goal": getattr(rt, "_current", None),
            "queue_len": len(getattr(rt, "_queue", []) or []),
        }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Checkpoint（reference-based 引用指针，不复制 truth）
# ---------------------------------------------------------------------------
def create_checkpoint(
    raw_id,
    *,
    goal_id=None,
    task_id=None,
    chat_log_id=None,
    runtime_ref=None,
    label=None,
) -> str:
    """创建一个可恢复边界检查点：仅存储对既有 canonical 实体的引用，不复制内容。"""
    sid = normalize_session_id(raw_id)
    create_session(sid)  # 确保协调记录存在（幂等）
    cp_id = uuid.uuid4().hex
    now = _now()
    conn = db_conn()
    try:
        conn.execute(
            "INSERT INTO session_checkpoints("
            "checkpoint_id, session_id, created_at, goal_id, task_id, chat_log_id, runtime_ref, label, status) "
            "VALUES(?,?,?,?,?,?,?,?, 'valid')",
            (
                cp_id,
                sid,
                now,
                int(goal_id) if goal_id is not None else None,
                int(task_id) if task_id is not None else None,
                int(chat_log_id) if chat_log_id is not None else None,
                runtime_ref,
                label,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return cp_id


def get_checkpoint(raw_id, checkpoint_id=None) -> Optional[Checkpoint]:
    """读取检查点；未指定 checkpoint_id 时返回该会话最近一个。"""
    sid = normalize_session_id(raw_id)
    conn = db_conn()
    try:
        if checkpoint_id:
            row = conn.execute(
                "SELECT checkpoint_id, session_id, created_at, goal_id, task_id, "
                "chat_log_id, runtime_ref, label, status FROM session_checkpoints "
                "WHERE checkpoint_id=? AND session_id=?",
                (checkpoint_id, sid),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT checkpoint_id, session_id, created_at, goal_id, task_id, "
                "chat_log_id, runtime_ref, label, status FROM session_checkpoints "
                "WHERE session_id=? ORDER BY created_at DESC, rowid DESC LIMIT 1",
                (sid,),
            ).fetchone()
    finally:
        conn.close()
    return Checkpoint(*row) if row else None


# ---------------------------------------------------------------------------
# Resume（协调，不重新执行；诚实返回 stale / invalid / missing）
# ---------------------------------------------------------------------------
def resume(raw_id, checkpoint_id=None) -> ResumeResult:
    """协调式 resume：校验检查点引用的 canonical 状态是否仍然有效，绝不盲目重执行。

    返回 ResumeResult：
      - status='valid'            引用齐备且目标未越过边界 → next_action='continue'
      - status='stale'            已有更新的检查点 / 目标已终态 → next_action='requires_replan'
      - status='invalid'          引用的 goal/task 已在 canonical 中消失 → next_action='requires_replan'
      - status='missing'          无检查点 → next_action='none'
    """
    sid = normalize_session_id(raw_id)
    cp = get_checkpoint(sid, checkpoint_id)
    if cp is None:
        return ResumeResult(status="missing", next_action="none", reason="no checkpoint for session")

    # 软外键：直接读取 goals / tasks 现状（复用既有 canonical 真相）
    conn = db_conn()
    try:
        if cp.goal_id is not None:
            grow = conn.execute(
                "SELECT id, status FROM goals WHERE id=?", (cp.goal_id,)
            ).fetchone()
            if grow is None:
                return ResumeResult(
                    status="invalid",
                    checkpoint=cp,
                    goal_id=cp.goal_id,
                    next_action="requires_replan",
                    reason="referenced goal %s no longer exists in canonical goals" % cp.goal_id,
                )
            goal_status = grow[1]
        else:
            goal_status = None

        if cp.task_id is not None:
            trow = conn.execute(
                "SELECT id FROM tasks WHERE id=?", (cp.task_id,)
            ).fetchone()
            if trow is None:
                return ResumeResult(
                    status="invalid",
                    checkpoint=cp,
                    task_id=cp.task_id,
                    next_action="requires_replan",
                    reason="referenced task %s no longer exists in canonical tasks" % cp.task_id,
                )
    finally:
        conn.close()

    # 边界已越过：目标已终态 → 需要重新规划而非续跑
    if goal_status in ("completed", "failed", "blocked_by_policy"):
        return ResumeResult(
            status="stale",
            checkpoint=cp,
            goal_id=cp.goal_id,
            next_action="requires_replan",
            reason="goal %s already terminal (status=%s)" % (cp.goal_id, goal_status),
        )

    # 已被更新的检查点取代
    newer = _has_newer_checkpoint(sid, cp.created_at)
    if newer:
        return ResumeResult(
            status="stale",
            checkpoint=cp,
            goal_id=cp.goal_id,
            task_id=cp.task_id,
            next_action="requires_replan",
            reason="a newer checkpoint supersedes this boundary",
        )

    return ResumeResult(
        status="valid",
        checkpoint=cp,
        goal_id=cp.goal_id,
        task_id=cp.task_id,
        next_action="continue",
        reason="checkpoint references intact canonical state",
    )


def _has_newer_checkpoint(sid: str, created_at: str) -> bool:
    conn = db_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM session_checkpoints "
            "WHERE session_id=? AND created_at > ?",
            (sid, created_at),
        ).fetchone()
        return bool(row and row[0] > 0)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 诊断辅助（供测试 / 运维；不改动 canonical）
# ---------------------------------------------------------------------------
def list_sessions(limit: int = 50) -> List[Session]:
    """列出已注册的会话协调记录（仅元数据）。"""
    conn = db_conn()
    try:
        rows = conn.execute(
            "SELECT session_id, created_at, updated_at, status FROM session_registry "
            "ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [Session(*r) for r in rows]


def list_checkpoints(raw_id, limit: int = 50) -> List[Checkpoint]:
    """列出某会话的全部检查点（引用指针）。"""
    sid = normalize_session_id(raw_id)
    conn = db_conn()
    try:
        rows = conn.execute(
            "SELECT checkpoint_id, session_id, created_at, goal_id, task_id, "
            "chat_log_id, runtime_ref, label, status FROM session_checkpoints "
            "WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
            (sid, limit),
        ).fetchall()
    finally:
        conn.close()
    return [Checkpoint(*r) for r in rows]
