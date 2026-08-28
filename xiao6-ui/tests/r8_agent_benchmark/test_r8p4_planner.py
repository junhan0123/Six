# -*- coding: utf-8 -*-
"""tests.r8_agent_benchmark.test_r8p4_planner — R8-P4 Context/Planner 衔接修复测试

验证已知问题修复：context.facade 缺失导致无 suggested_tool 任务派发失败（
「No module named 'context.facade'」→ legacy prompt → 仅 system 消息 → 400）。

断言：
  1) context.facade.build_cognitive_context 可用且返回非空上下文（与 Chat 同一组装源）。
  2) 无 suggested_tool 的任务经 _llm_dispatch 真实 LLM 派发成功
     （返回非空 tool + dict args，不再 400）。
  3) 既有契约不回归：facade 异常安全（mode/tier 兼容参数不炸）。

约束：不修改 ai_core.execution.run() / Policy / PermissionGuard；只修 Context/Planner 衔接。
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))

from _fixture import check, section  # noqa: E402


def run_r8p4():
    section("R8-P4 Context/Planner 衔接（context.facade + LLM 派发）")

    # 1) facade 可用且非空
    try:
        from context.facade import build_cognitive_context
        ctx = build_cognitive_context(
            goal_id=1, task={"id": 9, "title": "查询当前时间", "steps": ["调用 get_time"]}, mode="plan")
        ok_facade = callable(build_cognitive_context) and isinstance(ctx, str) and len(ctx) > 0
        check("build_cognitive_context 可用且非空", ok_facade, f"len={len(ctx) if isinstance(ctx, str) else '?'}")
        # 契约兼容：mode/tier 占位参数不炸
        ctx2 = build_cognitive_context(goal_id=None, task=None, mode="act", tier=None)
        check("mode/tier 契约参数兼容", isinstance(ctx2, str), f"len={len(ctx2)}")
    except Exception as e:
        check("build_cognitive_context 可用且非空", False, f"异常 {e}")
        return False

    # 2) 无 suggested_tool 任务经真实 LLM 派发成功（R8-P2 失败场景回归）
    from agent_runtime import AgentRuntime

    rt = AgentRuntime()
    task = {"id": 998, "title": "查询当前时间", "steps": ["调用 get_time 获取当前时间"]}
    tool, args = rt._llm_dispatch(task, goal_id=None)
    ok_dispatch = isinstance(tool, str) and bool(tool) and isinstance(args, dict)
    check("无 suggested_tool 任务 LLM 派发成功（不再 400）", ok_dispatch,
          f"tool={tool} args={args}")
    return ok_facade and ok_dispatch


if __name__ == "__main__":
    sys.exit(0 if run_r8p4() else 1)
