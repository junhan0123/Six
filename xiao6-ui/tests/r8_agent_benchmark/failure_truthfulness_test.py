# -*- coding: utf-8 -*-
"""tests.r8_agent_benchmark.failure_truthfulness_test — R8-P2 Failure Truthfulness

验证修复目标（任何失败最终 success=False 且进入正确 Recovery/失败状态）：

  A. 工具异常   → run() success=False；_execute_task ok=False（ERROR_TAXONOMY 分类）
  B. 未知工具   → run() success=False；_execute_task ok=False、category=tool_missing
  C. 权限拒绝   → 工具函数调用次数 = 0（Policy 在 Tool 之前拦截）
  D. 成功工具   → success=True / ok=True（不误伤）

另验证 R8-P2 新增能力：
  - 真实工具异常（ConnectionError）现在可被 Recovery Router 退避重试并恢复
    （失败串携带异常类名 → ERROR_TAXONOMY 恢复类型语义），无需 patch run。
所有执行均走真实 ai_core.execution.run() + policy 门，不绕过、不直连 execute_tool。
"""

import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))

from _fixture import check, section, ToolRegistry, Probe  # noqa: E402

GOAL_ID = 998000 + int(time.time()) % 1000


def _mk_task(tid, tool):
    return {"id": tid, "title": f"task-{tid}",
            "note": f"来自目标 #X 拆解 | revision=1 round=1 | suggested_tool={tool} args={{}}"}


# ---------------------------------------------------------------- A ---------

def test_a_tool_exception():
    from ai_core.execution import run
    from agent_runtime import AgentRuntime

    probe = Probe()
    with ToolRegistry() as reg:
        reg.register("__r8_boom__", probe.make_fn("x", raises=RuntimeError("unexpected tool failure")),
                     readonly=True)
        # A1: run() 层
        res = run("__r8_boom__", {"args": {"k": 1}})
        ok_run = bool(not res.get("success")) and "工具执行失败" in str(res.get("result"))
        check("A1 工具异常 → run() success=False", ok_run,
              f"success={res.get('success')} result={(res.get('result') or '')[:60]}")
        # A2: _execute_task 层
        rt = AgentRuntime()
        res2 = rt._execute_task(GOAL_ID, _mk_task(301, "__r8_boom__"))
        cat_ok = res2.get("category") in AgentRuntime.ERROR_TAXONOMY
        ok_task = bool(not res2.get("ok")) and cat_ok
        check("A2 工具异常 → _execute_task ok=False + 分类入词汇表", ok_task,
              f"ok={res2.get('ok')} category={res2.get('category')}")
    return ok_run and ok_task


def test_a_timeout():
    from ai_core.execution import run
    from agent_runtime import AgentRuntime

    probe = Probe()
    with ToolRegistry() as reg:
        reg.register("__r8_slow__", probe.make_fn("x", raises=TimeoutError("timed out")),
                     readonly=True)
        res = run("__r8_slow__", {"args": {}})
        ok_run = bool(not res.get("success"))
        rt = AgentRuntime()
        res2 = rt._execute_task(GOAL_ID, _mk_task(302, "__r8_slow__"))
        ok_task = bool(not res2.get("ok")) and res2.get("category") == "timeout"
        check("timeout → success=False / category=timeout（失败状态）", ok_run and ok_task,
              f"run.success={res.get('success')} task.category={res2.get('category')}")
    return ok_run and ok_task


def test_a_network_recovers_via_router():
    """真实工具 ConnectionError（无 patch run）→ Recovery Router 退避重试并恢复。"""
    from agent_runtime import AgentRuntime

    probe = Probe()
    state = {"n": 0}

    def flaky(args):
        state["n"] += 1
        probe.calls.append({"args": dict(args or {})})
        if state["n"] < 3:
            raise ConnectionError("connection refused")
        return "recovered ok"

    with ToolRegistry() as reg:
        reg.register("__r8_net_real__", flaky, readonly=True)
        rt = AgentRuntime()
        res = rt._execute_task(GOAL_ID, _mk_task(303, "__r8_net_real__"))

    ok = bool(res.get("ok")) and state["n"] == 3 and probe.call_count == 3
    check("真实网络异常 → 路由器重试 3 次恢复（ok=True）", ok,
          f"calls={state['n']} ok={res.get('ok')}")
    return ok


# ---------------------------------------------------------------- B ---------

def test_b_unknown_tool():
    from ai_core.execution import run
    from agent_runtime import AgentRuntime

    with ToolRegistry() as reg:
        # 只加 READONLY（policy AUTO）不注册 TOOL_FUNCS —— 模拟「计划了不存在的工具」
        reg.register_readonly_only("__r8_ghost__")
        res = run("__r8_ghost__", {"args": {}})
        ok_run = bool(not res.get("success")) and "未知工具" in str(res.get("result"))
        check("B1 未知工具 → run() success=False", ok_run,
              f"success={res.get('success')} result={(res.get('result') or '')[:40]}")

        rt = AgentRuntime()
        res2 = rt._execute_task(GOAL_ID, _mk_task(304, "__r8_ghost__"))
        ok_task = bool(not res2.get("ok")) and res2.get("category") == "tool_missing"
        check("B2 未知工具 → _execute_task ok=False / tool_missing", ok_task,
              f"ok={res2.get('ok')} category={res2.get('category')}")
    return ok_run and ok_task


# ---------------------------------------------------------------- C ---------

def test_c_permission_denied_zero_calls():
    from ai_core.execution import run
    from policy_engine import set_never

    probe = Probe()
    set_never("__r8_deny__", permanent=False)  # 仅内存
    with ToolRegistry() as reg:
        reg.register("__r8_deny__", probe.make_fn("should never run"), readonly=True)
        res = run("__r8_deny__", {"args": {}})
        ok_never = bool(not res.get("success")) and res.get("decision") == "block" \
            and probe.call_count == 0
        check("C1 NEVER 拒绝 → success=False 且工具调用 0 次", ok_never,
              f"decision={res.get('decision')} calls={probe.call_count}")

    probe2 = Probe()
    with ToolRegistry() as reg:
        reg.register("__r8_confirm__", probe2.make_fn("should never run"))  # 非 readonly → confirm
        res2 = run("__r8_confirm__", {"args": {}})
        ok_confirm = bool(not res2.get("success")) and res2.get("decision") == "confirm_rejected" \
            and probe2.call_count == 0
        check("C2 confirm 无 Goal → 快速拒绝且工具调用 0 次", ok_confirm,
              f"decision={res2.get('decision')} calls={probe2.call_count}")

    return ok_never and ok_confirm


# ---------------------------------------------------------------- D ---------

def test_d_success_tool():
    from ai_core.execution import run
    from agent_runtime import AgentRuntime

    res = run("calculator", {"args": {"expression": "21 * 2"}})
    ok_run = bool(res.get("success")) and "42" in str(res.get("result"))
    check("D1 成功工具 → run() success=True", ok_run, str(res.get("result")))

    rt = AgentRuntime()
    res2 = rt._execute_task(GOAL_ID, _mk_task(305, "get_time"))
    ok_task = bool(res2.get("ok"))
    check("D2 成功工具 → _execute_task ok=True", ok_task, str(res2.get("result"))[:60])

    return ok_run and ok_task


# ------------------------------------------------------------------- main -----

def run_truthfulness():
    section("R8-P2 Failure Truthfulness 测试（A 异常 / B 未知 / C 拒绝 / D 成功）")
    results = [
        test_a_tool_exception(),
        test_a_timeout(),
        test_a_network_recovers_via_router(),
        test_b_unknown_tool(),
        test_c_permission_denied_zero_calls(),
        test_d_success_tool(),
    ]
    passed = sum(1 for r in results if r)
    print(f"\n  R8-P2 套件：{passed}/{len(results)} 项通过")
    return all(results)


if __name__ == "__main__":
    sys.exit(0 if run_truthfulness() else 1)
