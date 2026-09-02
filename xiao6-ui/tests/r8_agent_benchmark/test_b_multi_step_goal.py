# -*- coding: utf-8 -*-
"""tests.r8_agent_benchmark.test_b_multi_step_goal — B. 多步骤 Goal 测试

验证完整链路（不绕过任何门）：
    submit_goal → plan_goal（LLM 拆解）→ ExecutionPolicy（Plan Gate + evaluate）
    → ai_core.execution.run()（Policy 门）→ Tool → 观察/评估（Verify）→ completed

断言：
  1) goal 收敛到 completed（四态终态之一，非超时/非失败）。
  2) 拆解产出 ≥1 个 task 且全部 done。
  3) 观察缓冲中确有成功工具执行（真实 run() 结果）。
  4) Execution Trace 记录了该 goal_id 的执行（含 task_id 串联）。
  5) 记录端到端耗时（submit → completed wall-clock），供报告评级。

无头验证环境：使用设计内 GDE 预批准通道 policy_engine.pre_approve_tools（per-goal 隔离），
与 GoalDecisionEngine 建 Goal 后的行为一致——非绕过 Policy。
"""

import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))

from _fixture import check, section  # noqa: E402

TIMEOUT_S = 180
MAX_ATTEMPTS = 2   # LLM 拆解有方差（偶尔不给 suggested_tool）→ 失败时换新目标重试一次


def _attempt(rt):
    """单次 Goal 尝试：提交→等待终态→校验。返回 (ok, detail)。"""
    from goals import get_goal
    from tasks import get_tasks
    from policy_engine import pre_approve_tools
    from ai_core.execution import trace as _trace

    t_submit = time.time()
    goal_id = rt.submit_goal(
        title="R8-P1 基准目标：查询当前时间并计算 21*2",
        description="请依次查询当前本地时间，并用计算器计算 21*2，确认执行链完整。",
    )
    if not goal_id:
        return False, {"error": "submit_goal 返回空"}

    # GDE 预批准通道（per-goal；与 GoalDecisionEngine 行为一致）
    pre_approve_tools(goal_id, [
        "get_time", "calculator", "note_save", "note_list", "add_knowledge",
        "memory_search", "list_skills", "use_skill", "set_goal", "update_goal",
        "list_goals", "complete_task", "file_read", "file_list",
    ])

    deadline = time.time() + TIMEOUT_S
    g = None
    while time.time() < deadline:
        g = get_goal(goal_id)
        if g and g.status in ("completed", "failed", "blocked_by_policy",
                              "max_steps_exceeded", "cancelled"):
            break
        time.sleep(2)
    wall_s = round(time.time() - t_submit, 1)

    detail = {"goal_id": goal_id, "status": g.status if g else None,
              "round_status": g.round_status if g else None, "wall_s": wall_s}
    if g is None or g.status != "completed":
        return False, detail

    rows = get_tasks(goal_id=goal_id, limit=100)
    done = [t for t in rows if t.get("status") == "done"]
    detail["tasks"] = f"{len(done)}/{len(rows)}"
    if not rows or len(done) != len(rows):
        return False, detail

    obs = getattr(rt, "_observations", {}).get(goal_id, [])
    ok_obs = [o for o in obs if o.get("ok")]
    detail["obs"] = "; ".join(f"{o.get('tool')}" for o in ok_obs) or "无"
    if not ok_obs:
        return False, detail

    recs = [r for r in _trace.recent(limit=200) if r.get("goal_id") == goal_id]
    ok_recs = [r for r in recs if r.get("status") == "ok"]
    detail["trace"] = f"{len(ok_recs)}/{len(recs)} ok"
    if not ok_recs or not all(r.get("task_id") is not None for r in ok_recs):
        return False, detail
    return True, detail


def run_b():
    section("B. 多步骤 Goal 测试（submit_goal → … → completed）")

    import agent_runtime

    rt = agent_runtime.runtime
    if not rt._running:
        rt.start()
        print("       Agent Runtime 线程已启动")

    for attempt_no in range(1, MAX_ATTEMPTS + 1):
        ok, detail = _attempt(rt)
        if ok:
            check("goal 收敛 completed（非超时/失败）", True,
                  f"goal #{detail['goal_id']} wall={detail['wall_s']}s (attempt {attempt_no})")
            check("plan_goal 拆解 ≥1 task", True, detail.get("tasks", ""))
            check("全部 task done（Verify 通过）", True, detail.get("tasks", ""))
            check("观察缓冲有成功工具执行", True, detail.get("obs", ""))
            check("trace 记录本 goal 的执行", True, detail.get("trace", ""))
            check("trace 有 ok 终态且带 task_id", True, detail.get("trace", ""))
            print(f"       goal #{detail['goal_id']}: completed wall={detail['wall_s']}s "
                  f"tasks={detail.get('tasks')}")
            return True
        print(f"       [attempt {attempt_no}] goal #{detail.get('goal_id')} 未完成: "
              f"status={detail.get('status')} round={detail.get('round_status')} "
              f"tasks={detail.get('tasks', '-')}（LLM 拆解方差/环境，重试）")

    check("goal 收敛 completed（非超时/失败）", False,
          f"{MAX_ATTEMPTS} 次尝试均未收敛（LLM 拆解方差或环境问题，详见日志）")
    return False


if __name__ == "__main__":
    sys.exit(0 if run_b() else 1)
