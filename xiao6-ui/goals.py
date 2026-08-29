#!/usr/bin/env python3
"""小6 · 目标系统核心服务（Phase 3）

Goal = 用户意图 / 项目 / 长期方向；可拆解为多个 Task（经 tasks.goal_id 软外键归属）。
目标进度优先由子 Task 完成比例自动聚合，也允许手动覆盖。
所有状态变更经 eventbus 发布到 "zz.goal" 主题（供 proactive / scene / SSE 桥消费）。

依赖方向（无环）：
- goals.py → db.py（持久化）
- goals.py → eventbus.py（发布事件）
- goals.py → tasks.py（plan_goal 拆解时创建子任务，延迟导入避免环）
- tools.py → goals.py（调用本模块 API）
- proactive.py → goals.py（TICK 扫描到期目标）
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from db import db_conn


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 内部 Goal 事件名 → Phase 6 规范领域事件名（zz-events.js 单一来源，readiness §5）。
# 仅映射、不新增同义事件；未列出的内部事件不发规范信封。
_GOAL_EVENT_TO_DOMAIN = {
    "GoalCreated": "GOAL_CREATED",
    "GoalUpdated": "GOAL_UPDATED",
    "GoalDeleted": "GOAL_UPDATED",          # 删除=置 archived，归并到更新流
    "GoalProgressChanged": "GOAL_UPDATED",  # 进度变更=字段级更新
    "GoalCompleted": "GOAL_COMPLETED",
}


def _emit(event_type: str, goal: "Goal", extra: Optional[dict] = None):
    """经事件总线发布一条 Goal 事件（异常静默，绝不阻断主链路）。

    Order 2：在保留原 zz.goal 内部主题的同时，额外把内部事件映射为规范领域事件，
    经 publish_domain() 发到 TOPIC_SSE（前端 AppState 合约入口，readiness §2.2 R1）。
    职责不变：本函数仍是 Goal 模块唯一事件出口；映射表集中于此，禁止散落硬编码。
    """
    try:
        from eventbus import bus

        bus.publish(
            "zz.goal",
            {
                "event": event_type,
                "goal_id": goal.id,
                "title": goal.title,
                "status": goal.status,
                "progress": goal.progress,
                "priority": goal.priority,
                "horizon": goal.horizon,
                "due_date": goal.due_date,
                **(extra or {}),
            },
            source="goals",
        )
    except Exception as e:
        print(f"[goals] 事件发布失败（已忽略）: {e}")

    # —— Phase 6 Order 2：规范领域事件信封（单一来源纪律，缺失名由 publish_domain 拒绝）——
    domain = _GOAL_EVENT_TO_DOMAIN.get(event_type)
    if not domain:
        return
    try:
        from eventbus import publish_domain

        payload = {
            "goalId": goal.id,
            "title": goal.title,
            "status": goal.status,
            "progress": goal.progress,
            "priority": goal.priority,
            "horizon": goal.horizon,
            "dueDate": goal.due_date,
        }
        # 进度变更携带字段级信息，便于前端 reducer 精确合并（不覆盖生命周期状态）
        if event_type == "GoalProgressChanged":
            payload["field"] = "progress"
            payload["value"] = goal.progress
        payload.update(extra or {})
        publish_domain(domain, payload, source="goals")
    except Exception as e:
        print(f"[goals] 领域事件发布失败（已忽略）: {e}")


# ---------- 值对象 ----------


@dataclass
class Goal:
    id: int
    title: str
    description: str = ""
    status: str = "active"            # active / paused / completed / archived
    priority: str = "medium"          # low / medium / high / critical
    horizon: str = "short"            # short / medium / long
    progress: int = 0                 # 0-100
    parent_id: Optional[int] = None
    due_date: Optional[str] = None
    completed_at: Optional[str] = None
    created: str = ""
    updated: str = ""
    # Phase 46 · 多轮 / 动态重规划 canonical 状态（由 agent_runtime 写入，plan_goal 仅读）
    revision: int = 1            # 重规划版本号；仅由 bump_revision() 递增
    round_index: int = 1         # 当前执行轮次序号（1-based）
    round_status: str = "none"   # 本轮 FSM 状态，永不取 'completed'

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "horizon": self.horizon,
            "progress": self.progress,
            "parent_id": self.parent_id,
            "due_date": self.due_date,
            "completed_at": self.completed_at,
            "created": self.created,
            "updated": self.updated,
            "revision": self.revision,
            "round_index": self.round_index,
            "round_status": self.round_status,
        }


# ---------- CRUD ----------


def _row_to_goal(r) -> Goal:
    """位置式解析；兼容老库/部分 SELECT（列数不足时按缺省兜底）。
    列序：id,title,description,status,priority,horizon,progress,parent_id,due_date,
    completed_at,created,updated[,revision,round_index,round_status]
    """
    base = list(r[:12])
    while len(base) < 12:
        base.append(None)
    (id_, title, description, status, priority, horizon, progress,
     parent_id, due_date, completed_at, created, updated) = base
    revision = r[12] if len(r) > 12 and r[12] is not None else 1
    round_index = r[13] if len(r) > 13 and r[13] is not None else 1
    round_status = r[14] if len(r) > 14 and r[14] is not None else "none"
    return Goal(
        id=id_, title=title, description=description, status=status, priority=priority,
        horizon=horizon, progress=progress or 0, parent_id=parent_id, due_date=due_date,
        completed_at=completed_at, created=created, updated=updated,
        revision=revision, round_index=round_index, round_status=round_status,
    )


def get_revision(goal_id) -> int:
    """返回目标当前 revision（缺省 1）。"""
    g = get_goal(goal_id)
    return g.revision if g else 1


def get_round(goal_id) -> int:
    """返回目标当前 round_index（缺省 1）。"""
    g = get_goal(goal_id)
    return g.round_index if g else 1


def set_round(goal_id, index: int, status: str) -> bool:
    """写 Goal 级 FSM：round_index / round_status。revision 由 bump_revision 独占，此处不动。
    非法 round_status 值不写入（保留原值），避免污染 FSM。
    """
    g = get_goal(goal_id)
    if not g:
        return False
    _valid_round = (
        "none", "planned", "running", "observing", "evaluating",
        "COMPLETE", "CONTINUE", "REPLAN", "BLOCK", "FAIL",
    )
    new_status = status if status in _valid_round else g.round_status
    conn = db_conn()
    conn.execute(
        "UPDATE goals SET round_index=?,round_status=?,updated=? WHERE id=?",
        (index, new_status, _now(), g.id),
    )
    conn.commit()
    conn.close()
    return True


def bump_revision(goal_id) -> int:
    """Phase 46 · 唯一合法递增 revision 的入口（仅 agent_runtime._do_replan 调用）。
    返回递增后的 revision；目标不存在时返回 1。
    """
    g = get_goal(goal_id)
    if not g:
        return 1
    new_rev = (g.revision or 1) + 1
    conn = db_conn()
    conn.execute(
        "UPDATE goals SET revision=?,updated=? WHERE id=?",
        (new_rev, _now(), g.id),
    )
    conn.commit()
    conn.close()
    return new_rev


def task_revision_of(note) -> Optional[int]:
    """从 task.note 解析 plan_goal 写入的 revision 标记；无标记=legacy（归 revision 1）。"""
    if not note:
        return None
    import re
    m = re.search(r"revision=(\d+)", note or "")
    return int(m.group(1)) if m else None


# Goal 规范状态集合（含诚实四态终态；session.py 亦据此判定，需保持同步）
_VALID_GOAL_STATUS = {
    "active", "paused", "completed", "archived",
    "failed", "max_steps_exceeded", "blocked_by_policy",
}


def _valid_status(s):
    return s if s in _VALID_GOAL_STATUS else "active"


def create_goal(title, description="", priority="medium", horizon="short",
                due_date=None, status="active", intent_id=None) -> Goal:
    """创建目标，返回 Goal 对象。intent_id 为 Order 5 Intent Gateway 关联字段（可选）。"""
    title = (title or "").strip()
    if not title:
        raise ValueError("目标标题不能为空")
    if priority not in ("low", "medium", "high", "critical"):
        priority = "medium"
    if horizon not in ("short", "medium", "long"):
        horizon = "short"
    now = _now()
    conn = db_conn()
    cur = conn.execute(
        "INSERT INTO goals(title,description,status,priority,horizon,progress,parent_id,due_date,completed_at,created,updated) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (title, description or "", _valid_status(status), priority, horizon, 0,
         None, due_date or None, None, now, now),
    )
    gid = cur.lastrowid
    conn.commit()
    conn.close()
    g = get_goal(gid)
    if g:
        # Order 5：若由 Intent Gateway 触发，GOAL_CREATED 携带 intentId 供前端关联 targetGoal
        _emit("GoalCreated", g, extra={"intentId": intent_id} if intent_id else None)
    return g


def get_goal(goal_id) -> Optional[Goal]:
    try:
        gid = int(goal_id)
    except (TypeError, ValueError):
        return None
    conn = db_conn()
    row = conn.execute(
        "SELECT id,title,description,status,priority,horizon,progress,parent_id,due_date,completed_at,created,updated,revision,round_index,round_status "
        "FROM goals WHERE id=?",
        (gid,),
    ).fetchone()
    conn.close()
    return _row_to_goal(row) if row else None


def update_goal(goal_id, **fields) -> Optional[Goal]:
    """更新目标字段；支持 status/progress/priority/horizon/title/description/due_date。
    返回更新后的 Goal，或 None（目标不存在）。"""
    g = get_goal(goal_id)
    if not g:
        return None
    sets, params = [], []
    allowed = {
        "title": str, "description": str, "status": str,
        "priority": str, "horizon": str, "progress": int, "due_date": str,
    }
    for k, v in fields.items():
        if k not in allowed or v is None:
            continue
        if k == "status":
            v = _valid_status(v)
        elif k == "priority" and v not in ("low", "medium", "high", "critical"):
            continue
        elif k == "horizon" and v not in ("short", "medium", "long"):
            continue
        elif k == "progress":
            try:
                v = max(0, min(100, int(v)))
            except (TypeError, ValueError):
                continue
        sets.append(f"{k}=?")
        params.append(v)
    # 完成态联动：状态切到 completed 时补 completed_at；切回非完成时清空
    if "status" in fields:
        new_status = _valid_status(fields["status"])
        if new_status == "completed" and not g.completed_at:
            sets.append("completed_at=?")
            params.append(_now())
        elif new_status != "completed":
            sets.append("completed_at=?")
            params.append(None)
    if not sets:
        return g
    sets.append("updated=?")
    params.append(_now())
    params.append(g.id)
    conn = db_conn()
    conn.execute("UPDATE goals SET " + ",".join(sets) + " WHERE id=?", params)
    conn.commit()
    conn.close()
    g2 = get_goal(g.id)
    if g2:
        _emit("GoalUpdated", g2)
    return g2


def delete_goal(goal_id) -> bool:
    """删除目标（软删：置 status='archived'，保留数据可追溯）。
    返回是否成功（目标存在）。"""
    g = get_goal(goal_id)
    if not g:
        return False
    conn = db_conn()
    conn.execute("UPDATE goals SET status='archived',updated=? WHERE id=?", (_now(), g.id))
    conn.commit()
    conn.close()
    g_archived = get_goal(g.id)
    if g_archived:
        _emit("GoalDeleted", g_archived)
    return True


def list_goals(status=None, horizon=None, limit=50) -> list[Goal]:
    """列出目标（按 due_date 升序，无日期排后；其次 id 降序）。"""
    sql = (
        "SELECT id,title,description,status,priority,horizon,progress,parent_id,due_date,completed_at,created,updated,revision,round_index,round_status "
        "FROM goals WHERE 1=1"
    )
    params = []
    if status:
        sql += " AND status=?"
        params.append(status)
    if horizon:
        sql += " AND horizon=?"
        params.append(horizon)
    sql += " ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC, id DESC LIMIT ?"
    params.append(limit)
    conn = db_conn()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_row_to_goal(r) for r in rows]


def list_active_goals(limit=5) -> list[Goal]:
    """列出活跃（active）目标，供上下文注入与简报使用。"""
    return list_goals(status="active", limit=limit)


# ---------- 进度聚合 ----------


def _goal_tasks(goal_id) -> list[dict]:
    """返回某目标下的子任务（id/title/status），用于快照展示。"""
    conn = db_conn()
    rows = conn.execute(
        "SELECT id,title,status FROM tasks WHERE goal_id=? ORDER BY id ASC",
        (goal_id,),
    ).fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "status": r[2]} for r in rows]


def recalc_progress(goal_id) -> int:
    """根据子 Task 完成比例重新计算目标进度，返回 0-100。
    - 有子任务：progress = 完成数 / 总数 * 100；若全部完成且当前 active → 置为 completed。
    - 无子任务：保留原手动进度，不自动变更。
    进度变化发布 GoalProgressChanged；完成态转换发布 GoalCompleted。
    """
    g = get_goal(goal_id)
    if not g:
        return 0
    conn = db_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM tasks WHERE goal_id=?", (g.id,)).fetchone()[0]
        done = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE goal_id=? AND status='done'", (g.id,)
        ).fetchone()[0]
    finally:
        conn.close()

    if total > 0:
        new_progress = round(done * 100 / total)
    else:
        new_progress = g.progress  # 无子任务：保留手动进度

    new_status = g.status
    just_completed = False
    if total > 0 and done >= total and g.status == "active":
        new_status = "completed"
        just_completed = True

    if new_progress == g.progress and new_status == g.status:
        return new_progress  # 无变化，不刷库、不发文

    now = _now()
    conn = db_conn()
    try:
        conn.execute(
            "UPDATE goals SET progress=?,status=?,completed_at=?,updated=? WHERE id=?",
            (
                new_progress,
                new_status,
                now if just_completed else (g.completed_at if new_status == "completed" else None),
                now,
                g.id,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    g2 = get_goal(g.id)
    if g2:
        _emit("GoalProgressChanged", g2, extra={"from_progress": g.progress})
        if just_completed:
            _emit("GoalCompleted", g2)
    return new_progress


# ---------- 上下文快照 ----------


def _horizon_label(h):
    return {"short": "本周", "medium": "本月", "long": "长期"}.get(h, h or "")


def active_goals_snapshot(limit=3) -> str:
    """生成注入上下文的目标快照文本（活跃目标，最多 limit 个）。无人活跃目标返回空串。

    Phase 39-B（修复 38J-R 进度泄漏）：仅输出目标标题，剥离「进度 xx% / 第 X/Y 步」
    等自然语言状态——内部 Goal.progress 与子任务结构化数据保持不变，需时由工具精确返回
    （与 #581 对 personal_context_source 的「进度脱敏」处理保持一致）。
    这样小6在「好了吗？」类问询中不会把进度百分比原样念出，
    而用户明确问「做到多少了？」时仍可由能力精确返回真实进度。
    """
    goals = list_active_goals(limit=limit)
    if not goals:
        return ""
    # 仅保留标题：不暴露进度 % / 步骤 / 优先级等内部状态，避免被 TTS 念出造成泄漏
    lines = [f"- [#{g.id}] {g.title}" for g in goals]
    return "\n".join(lines)


# ---------- 一次性 LLM 拆解 ----------


def plan_goal(goal_id, replan=False) -> list[int]:
    """调用 LLM 把目标拆解为若干 Task，写入 tasks 表并关联 goal_id，返回 task_id 列表。
    异常（网络/解析失败）时返回空列表，绝不影响主链路。

    Phase 46 · replan=True 表示「动态重规划」路径：本函数**绝不删除任何既有 Task**
    （DONE/FAILED/OPEN 全部保留），也**绝不递增 revision**（revision 仅由
    goals.bump_revision / agent_runtime._do_replan 递增）。新执行路径以「新建 Task 行
    （新身份）」表达，note 中写入当前 revision 标记，供 _run_goal 按 revision 过滤
    （旧 revision 的 Task 惰性保留、不再执行）。replan=False 为首次/常规规划，行为同构。
    """
    g = get_goal(goal_id)
    if not g:
        return []
    # 规划总是对应「某个 revision 的全新执行路径」→ 其 Task 统一归属当前 revision、round=1
    _revision = g.revision or 1
    import json
    try:
        from tools import TOOL_FUNCS
        _tool_names = ", ".join(sorted(TOOL_FUNCS.keys()))
    except Exception:
        _tool_names = ""
    # Phase 42 · 把已发现的 external.mcp.* 能力纳入 Planner 可见清单（§五–§八）
    # 只读聚合，不新建第二套元数据；MCP 工具经 capability_os.discovery 暴露。
    try:
        from capability_os.discovery import external_capability_ids
        _ext_ids = external_capability_ids()
        if _ext_ids:
            _tool_names = (_tool_names + ", " + ", ".join(_ext_ids)) if _tool_names else ", ".join(_ext_ids)
    except Exception:
        _ext_ids = []
    # Phase 45 · 把本地技能包纳入 Planner 可见清单（镜像 external MCP 块，只读聚合）。
    # 技能是「能力组合描述包」，经 use_skill 加载为正文上下文；此处仅让 Planner 知晓其存在，
    # 不把技能名当作可直接调用的工具。
    _skill_names = []
    try:
        from skills import list_skills as _ls

        _skill_names = [s.get("name") for s in _ls() if s.get("name")]
    except Exception:
        _skill_names = []
    _skill_block = ""
    if _skill_names:
        _skill_block = (
            "\n可用技能包（通过 use_skill 加载，作为步骤上下文与能力组合，"
            "不要当作可直接调用的工具）：" + ", ".join(_skill_names)
        )
    _system_text = (
        "你是一个执行计划助手。把用户的目标拆解为 3-8 个具体、可执行、互斥的步骤。"
        "每个步骤应有明确产出，并尽量指定由哪个已有工具执行（tool）及其参数（args）。"
        "只输出 JSON，不要任何解释。格式："
        '{"tasks":[{"title":"步骤标题","steps":["子步骤1"],"tool":"工具名(可选)","args":{}(可选)}]}'
        + (f"\n可用工具：{_tool_names}" if _tool_names else "")
        + _skill_block
    )
    messages = [
        {
            "role": "system",
            "content": _system_text,
        },
        {
            "role": "user",
            "content": f"目标：{g.title}\n描述：{g.description or '无'}\n请输出拆解计划 JSON。",
        },
    ]
    try:
        import llm

        with llm.agnes_completion(messages, stream=False, temperature=0.5, reasoning=None) as resp:
            data = __import__("json").loads(resp.read().decode("utf-8"))
        msg = (data.get("choices") or [{}])[0].get("message", {})
        text = msg.get("content") or ""
    except Exception as e:
        print(f"[goals] plan_goal LLM 调用失败（返回空）: {e}")
        return []

    specs = _extract_tasks_json(text)
    if not specs:
        return []

    ids = []
    try:
        import tasks  # 延迟导入，避免与 tasks.py 形成环
    except Exception:
        tasks = None
    for spec in specs:
        title = (spec.get("title") if isinstance(spec, dict) else str(spec)).strip()
        if not title:
            continue
        steps = spec.get("steps") if isinstance(spec, dict) else None
        note = f"来自目标 #{goal_id} 拆解 | revision={_revision} round=1"
        # Round 2：把 Plan 推荐的工具写入 task 备注，供 Agent Runtime 直接派发（无需每次 LLM）
        sug_tool = (spec.get("tool") if isinstance(spec, dict) else None)
        if isinstance(sug_tool, str) and sug_tool.strip():
            sug_tool = sug_tool.strip()
            known = set()
            try:
                from tools import TOOL_FUNCS
                known = set(TOOL_FUNCS.keys())
            except Exception:
                pass
            # Phase 42 · 允许 suggested_tool 绑定到已发现的 external.mcp.* 能力
            try:
                from capability_os.discovery import external_capability_ids as _eci
                known.update(_eci())
            except Exception:
                pass
            if sug_tool in known:
                try:
                    _args_json = json.dumps(spec.get("args") or {}, ensure_ascii=False)
                except Exception:
                    _args_json = "{}"
                note += f" | suggested_tool={sug_tool} args={_args_json}"
        tid = None
        if tasks is not None and hasattr(tasks, "create_task"):
            tid = tasks.create_task(
                title=title, steps=steps, note=note, goal_id=goal_id
            )
        if tid:
            ids.append(tid)
    # 拆解后刷新一次目标进度（即便无子任务完成，也保证状态一致）
    recalc_progress(goal_id)
    return ids


def _extract_tasks_json(text):
    """从 LLM 文本中尽量稳健地提取 tasks 列表（容错：去 markdown 围栏、截取首个 JSON 对象）。"""
    if not text:
        return []
    import json
    import re

    raw = text.strip()
    # 去 ```json ... ``` 围栏
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S)
    if m:
        raw = m.group(1).strip()
    # 尝试直接解析
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and isinstance(obj.get("tasks"), list):
            return obj["tasks"]
        if isinstance(obj, list):
            return obj
    except Exception:
        pass
    # 退路：截取首个 { 到末个 } 之间的内容
    s = raw.find("{")
    e = raw.rfind("}")
    if s >= 0 and e > s:
        try:
            obj = json.loads(raw[s : e + 1])
            if isinstance(obj, dict) and isinstance(obj.get("tasks"), list):
                return obj["tasks"]
        except Exception:
            pass
    return []
