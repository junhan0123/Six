# -*- coding: utf-8 -*-
"""R8-P0 · Goal 执行 E2E：Agent Runtime → plan_goal → _execute_task → ai_core.execution.run → Policy → Tool

与服务器同进程语义：直接驱动 agent_runtime（FEATURE_AGENT_RUNTIME 门控的真实编排状态机），
提交一个目标，等待其经 PLANNING → EXECUTING → REFLECTING 收敛到终态。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from goals import get_goal  # noqa: E402


def main():
    import agent_runtime

    rt = agent_runtime.runtime
    if not rt._running:
        rt.start()
        print("[runtime] 已启动 Agent Runtime 线程")
    else:
        print("[runtime] Agent Runtime 已在运行")

    # 提交一个只依赖低危/只读工具的目标（get_time 为 READONLY → Goal 内 AUTO）
    goal_id = rt.submit_goal(
        title="R8-P0 验证目标：查询当前时间",
        description="请查询当前本地时间，并确认执行链（Policy → Tool）完整工作。",
    )
    print(f"[goal] 已提交目标 #{goal_id}")
    if not goal_id:
        print("[FAIL] submit_goal 返回空")
        return 1

    # 无头验证环境：按设计走 GDE 预批准通道（policy_engine.pre_approve_tools，per-goal 隔离）
    # —— 这正是 GoalDecisionEngine 建 Goal 后对高置信度工具做的同一件事，非绕过 Policy。
    # 预批准一组低危/只读工具，避免 Plan Gate / 执行阶段对 CONFIRM 工具弹审批卡挂起。
    try:
        from policy_engine import pre_approve_tools
        pre_approve_tools(goal_id, [
            "get_time", "calculator", "note_save", "note_list", "add_knowledge",
            "memory_search", "list_skills", "use_skill", "set_goal", "update_goal",
            "list_goals", "complete_task", "file_read", "file_list",
        ])
        print("[goal] 已按 GDE 通道预批准低危工具集（per-goal）")
    except Exception as e:
        print(f"[goal] 预批准失败（继续）: {e}")
    deadline = time.time() + 180
    last = None
    while time.time() < deadline:
        g = get_goal(goal_id)
        if g is None:
            print("[FAIL] 目标不存在")
            return 1
        if g.status != last:
            print(f"[goal] 状态: {g.status} (round={g.round_index})")
            last = g.status
        if g.status in ("completed", "failed", "blocked_by_policy", "max_steps_exceeded", "cancelled"):
            break
        time.sleep(2)
    else:
        print("[FAIL] 目标执行超时（180s）")
        return 1

    print(f"[goal] 终态: {g.status}")
    # 验证执行链产出：本轮观察到的执行应包含 get_time 且成功
    observations = getattr(rt, "_observations", {}).get(goal_id, [])
    tools_ok = [o for o in observations if o.get("ok")]
    print(f"[goal] 观察记录: {len(observations)} 条，成功 {len(tools_ok)} 条")
    for o in observations:
        print(f"       - tool={o.get('tool')} ok={o.get('ok')} blocked={o.get('blocked')} "
              f"result={str(o.get('result_snippet'))[:80]}")
    got_time = any(o.get("tool") == "get_time" and o.get("ok") for o in observations)
    completed = g.status == "completed"
    ok = completed and got_time
    print("\n===== R8-P0 Goal 执行 E2E 汇总 =====")
    print(f"目标完成      : {'PASS' if completed else 'FAIL'} ({g.status})")
    print(f"真实工具调用  : {'PASS' if got_time else 'FAIL'} (get_time)")
    print("总体:", "ALL PASS ✅" if ok else "SOME FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
