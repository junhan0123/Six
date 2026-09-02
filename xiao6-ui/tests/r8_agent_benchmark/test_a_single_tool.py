# -*- coding: utf-8 -*-
"""tests.r8_agent_benchmark.test_a_single_tool — A. 单工具测试（calculator / get_time）

验证：
  1) calculator 经 ai_core.execution.run 收到真实 args 并正确计算（真实 Policy 门，AUTO 放行）。
  2) get_time 经 run 返回真实本地时间。
  3) Execution Trace 为每次执行落盘记录（tool_name / status=ok / duration_ms / args_summary）。
  4) 基准：连续 N 次调用的延迟分布（min/avg/max），供 R8-P1 报告评级。
"""

import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))

from _fixture import check, section  # noqa: E402


def _bench(fn, n=10):
    """连续 n 次执行，返回 (results, latencies_ms)。"""
    lats = []
    results = []
    for _ in range(n):
        t0 = time.perf_counter()
        results.append(fn())
        lats.append((time.perf_counter() - t0) * 1000.0)
    return results, lats


def _dist(lats):
    return {"n": len(lats), "min_ms": round(min(lats), 2),
            "avg_ms": round(sum(lats) / len(lats), 2), "max_ms": round(max(lats), 2)}


def run_a():
    from ai_core.execution import run
    from ai_core.execution import trace as _trace

    section("A. 单工具测试（calculator / get_time）")

    # ---- 1) calculator：真实 args 经统一执行入口 ----
    res = run("calculator", {"args": {"expression": "21 * 2"}})
    ok_calc = bool(res.get("success")) and "42" in str(res.get("result"))
    check("calculator success (21*2=42)", ok_calc, str(res.get("result")))

    # ---- 2) get_time：返回真实时间 ----
    res = run("get_time", {"args": {}})
    rt = str(res.get("result") or "")
    ok_time = bool(res.get("success")) and ("时间" in rt or ":" in rt)
    check("get_time success (真实时间)", ok_time, rt[:80])

    # ---- 3) Execution Trace 已落盘（status=ok + 关键字段）----
    recs = _trace.recent(limit=50)
    calc_recs = [r for r in recs if r.get("tool_name") == "calculator"]
    time_recs = [r for r in recs if r.get("tool_name") == "get_time"]
    check("trace 已记录 calculator", bool(calc_recs),
          f"{len(calc_recs)} 条" + (f" status={calc_recs[-1]['status']}" if calc_recs else ""))
    check("trace 已记录 get_time", bool(time_recs),
          f"{len(time_recs)} 条" + (f" status={time_recs[-1]['status']}" if time_recs else ""))
    fields_ok = True
    for r in (calc_recs[:1] + time_recs[:1]):
        for f in ("tool_name", "args_summary", "duration_ms", "status", "recovery_action",
                  "start_time", "end_time", "execution_id"):
            if f not in r:
                fields_ok = False
    check("trace 字段完整（task1 要求字段）", fields_ok)

    # ---- 4) 基准：N 次调用延迟分布 ----
    _res_c, lats_c = _bench(lambda: run("calculator", {"args": {"expression": "21 * 2"}}), n=10)
    _res_t, lats_t = _bench(lambda: run("get_time", {"args": {}}), n=10)
    d_c, d_t = _dist(lats_c), _dist(lats_t)
    ok_c = all(bool(r.get("success")) for r in _res_c)
    ok_t = all(bool(r.get("success")) for r in _res_t)
    check("calculator 基准 10/10 成功", ok_c, str(d_c))
    check("get_time 基准 10/10 成功", ok_t, str(d_t))
    print(f"       calculator latency: {d_c}")
    print(f"       get_time    latency: {d_t}")

    return all([ok_calc, ok_time, bool(calc_recs), bool(time_recs), fields_ok, ok_c, ok_t])


if __name__ == "__main__":
    sys.exit(0 if run_a() else 1)
