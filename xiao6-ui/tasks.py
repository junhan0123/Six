#!/usr/bin/env python3
"""庄周 · 多步任务管理（Phase 3.1）：创建 / 续跑 / 完成，重启可恢复。

纯本地零密钥。任务持久化在 SQLite `tasks` 表，进程重启后仍在；
启动时 `recover_tasks()` 把上次在进行中(running)被中断的任务翻回 open，
配合 ACI 注入的「未完成任务」上下文，庄周可在下一轮对话中接着干。
"""

import json

from db import db_conn


def _now():
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- 基础读写（带迁移兼容） ----------


def create_task(title, steps=None, total_steps=None, note=None, goal_id=None):
    """创建一条多步任务，返回 task id（int）；标题为空返回 None。供内部 / 目标拆解使用。"""
    title = (title or "").strip()
    if not title:
        return None
    if isinstance(steps, list):
        steps_json = json.dumps(steps, ensure_ascii=False)
        total = total_steps if isinstance(total_steps, int) and total_steps > 0 else len(steps)
    else:
        steps_json = None
        total = total_steps if isinstance(total_steps, int) and total_steps > 0 else 0
    now = _now()
    conn = db_conn()
    cur = conn.execute(
        "INSERT INTO tasks(title,steps,current_step,total_steps,status,step,note,goal_id,created,updated) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (title, steps_json, 0, total, "open", "", note or "", goal_id if goal_id else None, now, now),
    )
    tid = cur.lastrowid
    conn.commit()
    conn.close()
    return tid


def set_task(title, steps=None, total_steps=None, note=None, goal_id=None):
    """创建一条多步任务，返回 human 文本（含 task id）。"""
    title = (title or "").strip()
    if not title:
        return "错误：任务标题不能为空"
    if isinstance(steps, list):
        total = total_steps if isinstance(total_steps, int) and total_steps > 0 else len(steps)
    else:
        total = total_steps if isinstance(total_steps, int) and total_steps > 0 else 0
    tid = create_task(title, steps=steps, total_steps=total, note=note, goal_id=goal_id)
    return f"已创建任务 #{tid}：{title}" + (f"（共 {total} 步）" if total else "")


def update_task_step(task_id, step=None, current_step=None, note=None, status=None):
    """更新任务进度：可改当前步序号 / 当前步标签 / 备注 / 状态。"""
    try:
        tid = int(task_id)
    except (TypeError, ValueError):
        return "错误：task_id 必须是数字"
    conn = db_conn()
    row = conn.execute("SELECT id,title FROM tasks WHERE id=?", (tid,)).fetchone()
    if not row:
        conn.close()
        return f"错误：找不到任务 #{tid}"
    sets, params = [], []
    if step is not None:
        sets.append("step=?")
        params.append(str(step))
    if isinstance(current_step, int):
        sets.append("current_step=?")
        params.append(current_step)
    if note is not None:
        sets.append("note=?")
        params.append(str(note))
    if status is not None:
        sets.append("status=?")
        params.append(str(status))
    if not sets:
        conn.close()
        return f"任务 #{tid}（{row[1]}）无需更新。"
    sets.append("updated=?")
    params.append(_now())
    params.append(tid)
    conn.execute("UPDATE tasks SET " + ",".join(sets) + " WHERE id=?", params)
    conn.commit()
    conn.close()
    return f"已更新任务 #{tid}（{row[1]}）。"


def complete_task(task_id, success=True, note=None):
    """完成任务（success=False 标记为失败），返回 human 文本。"""
    try:
        tid = int(task_id)
    except (TypeError, ValueError):
        return "错误：task_id 必须是数字"
    conn = db_conn()
    row = conn.execute("SELECT id,title FROM tasks WHERE id=?", (tid,)).fetchone()
    if not row:
        conn.close()
        return f"错误：找不到任务 #{tid}"
    status = "done" if success else "failed"
    note_txt = str(note) if note is not None else ""
    conn.execute(
        "UPDATE tasks SET status=?,note=?,current_step=total_steps,updated=? WHERE id=?",
        (status, note_txt, _now(), tid),
    )
    conn.commit()
    conn.close()
    return f"任务 #{tid}（{row[1]}）已{'完成' if success else '标记失败'}。"


def get_tasks(only_open=False, limit=20, goal_id=None):
    """返回任务列表（dict）。only_open 只取未完成任务；goal_id 按目标过滤。"""
    conn = db_conn()
    sql = (
        "SELECT id,title,steps,current_step,total_steps,status,step,note,created,updated "
        "FROM tasks WHERE 1=1"
    )
    params = []
    if only_open:
        sql += " AND status IN ('open','running','paused')"
    if goal_id is not None:
        sql += " AND goal_id=?"
        params.append(goal_id)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    out = []
    for r in rows:
        steps = None
        if r[2]:
            try:
                steps = json.loads(r[2])
            except Exception:
                steps = None
        out.append(
            {
                "id": r[0],
                "title": r[1],
                "steps": steps,
                "current_step": r[3],
                "total_steps": r[4],
                "status": r[5],
                "step": r[6],
                "note": r[7],
                "created": r[8],
                "updated": r[9],
            }
        )
    return out


def get_open_tasks(limit=5, goal_id=None):
    """供 ACI 注入：取最近若干未完成任务；goal_id 按目标过滤。"""
    return get_tasks(only_open=True, limit=limit, goal_id=goal_id)


def recover_tasks():
    """启动时把『进行中(running)被中断』的任务翻回 open，使其可被续跑。
    返回恢复的任务数（0 表示无需恢复）。"""
    try:
        conn = db_conn()
        n = conn.execute("SELECT count(*) FROM tasks WHERE status='running'").fetchone()[0]
        if n:
            conn.execute("UPDATE tasks SET status='open',updated=? WHERE status='running'", (_now(),))
            conn.commit()
        conn.close()
        return n
    except Exception:
        return 0


# ---------- 工具包装（供 LLM function calling 调用） ----------


def _refresh_goal_progress(task_id):
    """任务变更后，若其归属某目标则刷新目标进度（异常静默，绝不阻断主链路）。"""
    try:
        import goals

        tid = int(task_id)
        conn = db_conn()
        row = conn.execute("SELECT goal_id FROM tasks WHERE id=?", (tid,)).fetchone()
        conn.close()
        if row and row[0]:
            goals.recalc_progress(row[0])
    except Exception:
        pass


def tool_set_task(args):
    return set_task(
        args.get("title", ""),
        steps=args.get("steps"),
        total_steps=args.get("total_steps"),
        note=args.get("note"),
        goal_id=args.get("goal_id"),
    )


def tool_update_task_step(args):
    res = update_task_step(
        args.get("task_id"),
        step=args.get("step"),
        current_step=args.get("current_step"),
        note=args.get("note"),
        status=args.get("status"),
    )
    # 状态变更为完成时，刷新所属目标进度
    if (args.get("status") or "").lower() in ("done", "failed"):
        _refresh_goal_progress(args.get("task_id"))
    return res


def tool_complete_task(args):
    res = complete_task(args.get("task_id"), success=args.get("success", True), note=args.get("note"))
    _refresh_goal_progress(args.get("task_id"))
    return res


def tool_task_list(args):
    only_open = bool(args.get("only_open", False))
    rows = get_tasks(only_open=only_open, limit=20)
    if not rows:
        return "当前没有任务。" if not only_open else "当前没有未完成的任务。"
    lines = []
    for r in rows:
        prog = f" 第{r['current_step']}/{r['total_steps']}步" if r["total_steps"] else ""
        lines.append(f"  - #{r['id']} [{r['status']}] {r['title']}{prog}")
    return "任务列表：\n" + "\n".join(lines)
