# -*- coding: utf-8 -*-
"""tests.r8_agent_benchmark.test_c_failure_recovery — C. Failure Recovery 测试

验证：
  1) ERROR_TAXONOMY：AgentRuntime._classify_error 的 18 类词汇（异常类型快路径 / 合成标记 / 关键词）。
  2) Recovery Router：_execute_task 对 run() 级异常的路由（network 退避重试 / file 换替代工具 /
     fatal 快速失败 / 重试耗尽）。
  3) Retry：network 类经短退避重试（≤ _MAX_RETRIES+1 次），成功/耗尽两种终态。
  4) Policy Deny：NEVER 工具 block、危险参数 block、confirm 无 Goal 拒绝——全部经真实
     policy_engine / run()，且确认工具函数未被调用（Policy 在 Tool 之前拦截）。
  5) 当前行为观察（不绕过）：真实工具抛异常时 execute_tool 吞为失败串 → _execute_task
     无条件 ok=True（failure masking）——以 WARN 记录为已知问题，供 R8-P1 评级。

测试边界说明：
  - Router 测试用「run() 级异常」模拟（patch ai_core.execution.run 抛异常），这是路由器
    的契约输入（运行核心自身崩溃/基础设施异常）；真实工具异常不冒泡（见第 5 项）。
  - 合成工具经 tools.TOOL_FUNCS 注册/还原，全部执行仍走真实 run()/policy 门，不绕过。
"""

import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))

from _fixture import check, warn, section, ToolRegistry, Probe  # noqa: E402

GOAL_ID = 999000 + int(time.time()) % 1000  # 测试用目标 id（隔离，不落 DB 真目标）


def _patch_run(fake_fn):
    """把 ai_core.execution.run 替换为 fake（_execute_task 局部导入取模块属性）。"""
    import ai_core.execution as _exec
    _orig = _exec.run
    _exec.run = fake_fn
    return _orig, _exec


def _restore_run(orig, _exec):
    _exec.run = orig


# ---------------------------------------------------------------- taxonomy ----

def test_taxonomy():
    from agent_runtime import AgentRuntime

    cases = [
        (ConnectionError("refused"), "network"),
        (TimeoutError("timed out"), "timeout"),
        (FileNotFoundError("no such file"), "file"),
        (PermissionError("denied"), "permission"),
        (RuntimeError("unknown tool: xyz"), "tool_missing"),
        (RuntimeError("skill broken"), "skill_error"),
        (RuntimeError("mcp server down"), "mcp_error"),
        (RuntimeError("computer_action failed"), "computer_error"),
        (RuntimeError("json syntax error"), "parse_error"),
        (RuntimeError("pickle serialization"), "serialization"),
        (RuntimeError("schema invalid required"), "validation"),
        (RuntimeError("no space left on device"), "resource"),
        (RuntimeError("budget_exhausted"), "budget_exhausted"),
        (RuntimeError("depth_exceeded"), "depth_exceeded"),
        (RuntimeError("injection_blocked"), "injection_blocked"),
        (RuntimeError("denied by policy"), "policy_blocked"),
        (RuntimeError("completely obscure failure"), "unknown"),
    ]
    ok = True
    for exc, expect in cases:
        got = AgentRuntime._classify_error(exc, "t")
        if got != expect:
            ok = False
            print(f"  [FAIL] classify {exc!r} -> {got!r} (expect {expect!r})")
    check(f"ERROR_TAXONOMY {len(cases)} 类分类正确", ok)
    return ok


# ---------------------------------------------------------------- router ------

def _mk_task(tid, tool):
    return {"id": tid, "title": f"task-{tid}",
            "note": f"来自目标 #X 拆解 | revision=1 round=1 | suggested_tool={tool} args={{}}"}


def test_router_network_retry_success():
    import ai_core.execution as _exec
    from agent_runtime import AgentRuntime
    from ai_core.execution import trace as _trace

    rt = AgentRuntime()
    probe = Probe()
    calls = []

    def fake_run(task, context=None, **kw):
        calls.append({"task": task, "context": context})
        if len(calls) < 3:
            raise ConnectionError("simulated network failure")
        return {"success": True, "result": "recovered ok"}

    orig, _mod = _patch_run(fake_run)
    try:
        with ToolRegistry() as reg:
            reg.register("__r8_net_flaky__", probe.make_fn("unused"), readonly=True)
            res = rt._execute_task(GOAL_ID, _mk_task(101, "__r8_net_flaky__"))
    finally:
        _restore_run(orig, _mod)

    ok = bool(res.get("ok")) and len(calls) == 3
    check("network 异常 → 短退避重试 → 3 次内恢复成功",
          ok, f"calls={len(calls)} res.ok={res.get('ok')}")
    recs = [r for r in _trace.recent(limit=30) if r.get("tool_name") == "__r8_net_flaky__"
            and r.get("recovery_action") == "retry_with_backoff"]
    check("trace 记录 retry_with_backoff", len(recs) >= 2, f"{len(recs)} 条")
    return ok and len(recs) >= 2


def test_router_retry_exhaustion():
    import ai_core.execution as _exec
    from agent_runtime import AgentRuntime

    rt = AgentRuntime()
    calls = []

    def fake_run(task, context=None, **kw):
        calls.append(task)
        raise ConnectionError("always down")

    orig, _mod = _patch_run(fake_run)
    try:
        with ToolRegistry() as reg:
            reg.register("__r8_net_down__", lambda a: "x", readonly=True)
            res = rt._execute_task(GOAL_ID, _mk_task(102, "__r8_net_down__"))
    finally:
        _restore_run(orig, _mod)

    max_attempts = rt._MAX_RETRIES + 1
    ok = (not res.get("ok")) and res.get("category") == "network" \
        and res.get("attempts") == max_attempts and len(calls) == max_attempts
    check(f"重试耗尽（{max_attempts} 次后 FAIL CLOSED）", ok,
          f"category={res.get('category')} attempts={res.get('attempts')} calls={len(calls)}")
    return ok


def test_router_timeout_fail_closed():
    import ai_core.execution as _exec
    from agent_runtime import AgentRuntime

    rt = AgentRuntime()
    calls = []

    def fake_run(task, context=None, **kw):
        calls.append(task)
        raise TimeoutError("simulated timeout")

    orig, _mod = _patch_run(fake_run)
    try:
        with ToolRegistry() as reg:
            reg.register("__r8_timeout__", lambda a: "x", readonly=True)
            res = rt._execute_task(GOAL_ID, _mk_task(103, "__r8_timeout__"))
    finally:
        _restore_run(orig, _mod)

    ok = (not res.get("ok")) and res.get("category") == "timeout" and res.get("attempts") == 1
    check("timeout → 分类 timeout、不重试、快速失败（当前路由器行为）", ok,
          f"category={res.get('category')} attempts={res.get('attempts')}")
    # 设计意图（_FATAL 注释）视 timeout 为可重试，但路由器未重试 —— 已知问题记录
    warn("已知问题：timeout 被分类但当前路由器不重试（设计注释与实现不一致）",
         "报告 §已知问题")
    return ok


def test_router_file_alternative():
    import ai_core.execution as _exec
    from agent_runtime import AgentRuntime

    rt = AgentRuntime()
    calls = []

    def fake_run(task, context=None, **kw):
        calls.append(task)
        if len(calls) == 1:
            raise FileNotFoundError("no such file")
        return {"success": True, "result": "alt ok"}

    orig, _mod = _patch_run(fake_run)
    try:
        with ToolRegistry() as reg:
            reg.register("__r8_file_x__", lambda a: "x", readonly=True)
            reg.register("__r8_file_y__", lambda a: "y", readonly=True)
            # 手工挂替代映射：排除 __r8_file_x__ 后路由器取 TOOL_FUNCS 第一个键
            res = rt._execute_task(GOAL_ID, _mk_task(104, "__r8_file_x__"))
    finally:
        _restore_run(orig, _mod)

    alt_used = len(calls) == 2 and calls[1] != calls[0]
    ok = bool(res.get("ok")) and alt_used
    check("file 异常 → 换替代工具重试成功", ok,
          f"calls={[c for c in calls]}")
    return ok


def test_router_policy_deny_before_exec():
    """NEVER 工具在路由器内被 Policy 拦截：blocked=True，run 未被调用。

    （kill_process 是已注册 HIGH 风险 computer capability，会先路由到
    PermissionGuard deny——本项用合成工具 + policy_engine.set_never 直测
    ExecutionPolicy block 路径。）
    """
    import ai_core.execution as _exec
    from agent_runtime import AgentRuntime
    from policy_engine import set_never

    set_never("__r8_never__", permanent=False)  # 仅内存，不落盘
    rt = AgentRuntime()
    calls = []

    def fake_run(task, context=None, **kw):
        calls.append(task)
        return {"success": True, "result": "SHOULD NOT RUN"}

    orig, _mod = _patch_run(fake_run)
    try:
        with ToolRegistry() as reg:
            reg.register("__r8_never__", lambda a: "x", readonly=True)
            res = rt._execute_task(GOAL_ID, _mk_task(105, "__r8_never__"))
    finally:
        _restore_run(orig, _mod)

    ok = bool(res.get("blocked")) and not calls
    check("policy deny（NEVER 工具）在执行前拦截", ok,
          f"blocked={res.get('blocked')} run_calls={len(calls)}")
    return ok


# ------------------------------------------------------- 真实路径（不 patch）----

def test_real_tool_exception_behavior():
    """真实路径：合成工具抛异常 → R8-P2 修复后 _execute_task 如实 ok=False
    （Failure Truthfulness；R8-P1 时代的 failure masking 已修复）。"""
    from agent_runtime import AgentRuntime

    rt = AgentRuntime()
    probe = Probe()
    with ToolRegistry() as reg:
        reg.register("__r8_boom__", probe.make_fn("x", raises=RuntimeError("boom real")),
                     readonly=True)
        res = rt._execute_task(GOAL_ID, _mk_task(106, "__r8_boom__"))

    truthful = bool(not res.get("ok")) and "工具执行失败" in str(res.get("error") or "")
    check("真实工具异常 → ok=False（R8-P2 Failure Truthfulness）", truthful,
          f"ok={res.get('ok')} error={(res.get('error') or '')[:60]}")
    check("（观测）工具函数确实被调用且异常被 execute_tool 捕获", probe.call_count == 1,
          f"probe_calls={probe.call_count}")
    return truthful


def test_policy_confirm_reject_no_goal():
    """confirm 级工具 + 无 Goal 上下文 → request_approval 快速拒绝，工具未执行。"""
    from ai_core.execution import run
    from ai_core.execution import trace as _trace

    probe = Probe()
    with ToolRegistry() as reg:
        reg.register("__r8_confirm__", probe.make_fn("should not run"))  # 非 readonly/lowlrisk
        res = run("__r8_confirm__", {"args": {"k": 1}})

    ok = (not res.get("success")) and res.get("decision") == "confirm_rejected" \
        and probe.call_count == 0
    check("confirm 无 Goal → 快速拒绝且工具未执行", ok,
          f"decision={res.get('decision')} probe_calls={probe.call_count}")
    recs = [r for r in _trace.recent(limit=20) if r.get("tool_name") == "__r8_confirm__"]
    check("trace 记录 rejected", bool(recs) and recs[-1].get("status") == "rejected",
          f"{len(recs)} 条")
    return ok


def test_policy_dangerous_args_block():
    """run_shell 危险参数（rm -rf /）→ is_never_by_args 硬阻断，命令未执行。"""
    from ai_core.execution import run
    from ai_core.execution import trace as _trace

    res = run("run_shell", {"args": {"command": "rm -rf /"}})
    ok = (not res.get("success")) and res.get("decision") == "block"
    check("run_shell 危险参数 → Policy 硬阻断（决策 block）", ok,
          f"decision={res.get('decision')} error={(res.get('error') or '')[:50]}")
    recs = [r for r in _trace.recent(limit=20) if r.get("tool_name") == "run_shell"]
    check("trace 记录 blocked/policy_blocked",
          bool(recs) and recs[-1].get("status") == "blocked"
          and recs[-1].get("recovery_action") == "policy_blocked", f"{len(recs)} 条")
    return ok


def test_policy_never_tool_block():
    """NEVER 名单工具（kill_process）经 run() → block。"""
    from ai_core.execution import run
    res = run("kill_process", {"args": {"pid": 1}})
    ok = (not res.get("success")) and res.get("decision") == "block"
    check("kill_process（NEVER 名单）→ block", ok, f"decision={res.get('decision')}")
    return ok


# ------------------------------------------------------------------- main ------

def run_c():
    section("C. Failure Recovery 测试（exception / timeout / policy deny）")

    results = []
    # 1) ERROR_TAXONOMY
    results.append(test_taxonomy())
    # 2) Recovery Router + Retry（run() 级异常模拟）
    results.append(test_router_network_retry_success())
    results.append(test_router_retry_exhaustion())
    results.append(test_router_timeout_fail_closed())
    results.append(test_router_file_alternative())
    # 3) Policy Deny（真实 policy，无 patch）
    results.append(test_router_policy_deny_before_exec())
    results.append(test_policy_confirm_reject_no_goal())
    results.append(test_policy_dangerous_args_block())
    results.append(test_policy_never_tool_block())
    # 4) 真实路径行为（R8-P2 Failure Truthfulness 已修复：ok=False）
    results.append(test_real_tool_exception_behavior())

    passed = sum(1 for r in results if r)
    print(f"\n  C 套件：{passed}/{len(results)} 项通过")
    return all(results)


if __name__ == "__main__":
    sys.exit(0 if run_c() else 1)
