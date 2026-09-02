# -*- coding: utf-8 -*-
"""R8-P0 · 最小测试：Execution Core 参数契约 run(task, context={"args": args})

验证：
  1) ai_core.execution.run(task, context={"args": args}) 会把真实 args 透传给工具
     （calculator 收到 expression，结果可证明参数未丢失）。
  2) 旧错误写法 run(task, raw_args) 会导致参数丢失（工具收到空参数）——证明契约必须统一。
  3) capability_runtime.execute 统一收敛点同样保证 args 到达工具。
  4) ExecutionPolicy.get() 门面可用（evaluate 委托 policy_engine）。
  5) server_globals 安全全局为真实实现（_is_local_peer / 脱敏正则 / CORS 白名单 / _REMOTE_FORBIDDEN）。

运行：在 xiao6-ui 目录下 `python test_r8_tool_args_contract.py`（或 pytest 收集）。
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    PASS.append(bool(cond))
    print(f"[{status}] {name}" + (f"  -> {detail}" if detail else ""))


def test_run_args_contract():
    """核心：run(task, context={"args": args}) 工具必须收到真实 args。"""
    from ai_core.execution import run

    # 正确契约：args 放在 context["args"]（calculator 为 READONLY/AUTO，可无审批直过 Policy）
    res = run("calculator", {"args": {"expression": "21 * 2"}})
    check("run() success with real args", bool(res.get("success")), json.dumps(res, ensure_ascii=False))
    check("calculator received real args (21*2=42)",
          "42" in str(res.get("result")), str(res.get("result")))

    # 旧错误写法（raw args 当 context 传）：args 丢失 → 工具收到空参数
    # （工具正常返回「表达式为空」而非计算结果；run() 对工具自身错误串仍报 success，
    #   故此处只断言参数确实丢失，不断言 success 标志。）
    res2 = run("calculator", {"expression": "21 * 2"})
    check("broken raw-args contract loses tool args",
          "表达式为空" in str(res2.get("result")), json.dumps(res2, ensure_ascii=False))


def test_capability_runtime_contract():
    """capability_runtime.execute（默认 Chat 收敛点）同样保证 args 到达工具。"""
    from capability_runtime import execute

    r = execute("calculator", {"expression": "6 * 7"})
    check("capability_runtime.execute success", bool(r.success), r.message)
    check("capability_runtime args reached tool", "42" in str(r.data), str(r.data))


def test_execution_policy_facade():
    """ExecutionPolicy.get() 门面可用且委托 policy_engine。"""
    from ai_core.execution.policy import ExecutionPolicy

    policy = ExecutionPolicy.get()
    check("ExecutionPolicy.get() singleton", policy is ExecutionPolicy.get())
    dec = policy.evaluate("calculator", {"expression": "1"}, goal_id=None, default_deny=True)
    check("ExecutionPolicy.evaluate delegates to policy_engine",
          dec.get("decision") == "auto", str(dec))
    check("ExecutionPolicy has request_approval", callable(getattr(policy, "request_approval", None)))


def test_server_globals_restored():
    """server_globals 安全全局必须是真实实现（禁止 stub 回退）。"""
    import server_globals as sg

    check("_is_local_peer is callable", callable(sg._is_local_peer))
    check("_is_local_peer('127.0.0.1') is local", sg._is_local_peer("127.0.0.1") is True)
    check("_is_local_peer('192.168.1.5') is NOT local", sg._is_local_peer("192.168.1.5") is False)
    check("_ACCESS_LOG_REDACT_RE is a compiled regex",
          sg._ACCESS_LOG_REDACT_RE is not None and hasattr(sg._ACCESS_LOG_REDACT_RE, "sub"))
    check("_CORS_ALLOWED_ORIGINS is a set and not {'*'}",
          isinstance(sg._CORS_ALLOWED_ORIGINS, set) and sg._CORS_ALLOWED_ORIGINS != {"*"})
    check("_REMOTE_FORBIDDEN is a set containing run_shell",
          isinstance(sg._REMOTE_FORBIDDEN, set) and "run_shell" in sg._REMOTE_FORBIDDEN)
    check("_resolve_cors_origins is callable and returns loopback origins",
          callable(sg._resolve_cors_origins) and
          "http://127.0.0.1:8000" in sg._resolve_cors_origins("127.0.0.1", 8000))


if __name__ == "__main__":
    test_run_args_contract()
    test_capability_runtime_contract()
    test_execution_policy_facade()
    test_server_globals_restored()
    total, ok = len(PASS), sum(PASS)
    print("\n===== R8-P0 参数契约最小测试 汇总 =====")
    print(f"{ok}/{total} PASS")
    sys.exit(0 if ok == total else 1)
