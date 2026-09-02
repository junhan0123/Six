# -*- coding: utf-8 -*-
"""tests.r8_agent_benchmark.run_benchmark — R8-P1 全量基准入口

运行：在 xiao6-ui 目录下
    python tests/r8_agent_benchmark/run_benchmark.py

依次执行 A（单工具）/ B（多步骤 Goal）/ C（Failure Recovery），
输出汇总（含各套件耗时），退出码 0=全部通过。
"""

import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))

from ai_core.execution import trace as _trace  # noqa: E402

from test_a_single_tool import run_a  # noqa: E402
from test_b_multi_step_goal import run_b  # noqa: E402
from test_c_failure_recovery import run_c  # noqa: E402
from failure_truthfulness_test import run_truthfulness  # noqa: E402
from test_r8p4_planner import run_r8p4  # noqa: E402


def main():
    print("=" * 70)
    print("R8-P1/P2/P4 Agent Reliability Benchmark Suite")
    print("=" * 70)

    # 每次全量运行从干净 trace 开始（避免跨运行污染断言）
    _trace.clear()

    results = []
    t_start = time.time()

    t0 = time.time()
    ok_a = run_a()
    dur_a = round(time.time() - t0, 1)
    results.append(("A 单工具", ok_a, dur_a))

    t0 = time.time()
    ok_b = run_b()
    dur_b = round(time.time() - t0, 1)
    results.append(("B 多步骤 Goal", ok_b, dur_b))

    t0 = time.time()
    ok_c = run_c()
    dur_c = round(time.time() - t0, 1)
    results.append(("C Failure Recovery", ok_c, dur_c))

    t0 = time.time()
    ok_d = run_truthfulness()
    dur_d = round(time.time() - t0, 1)
    results.append(("R8-P2 Truthfulness", ok_d, dur_d))

    t0 = time.time()
    ok_e = run_r8p4()
    dur_e = round(time.time() - t0, 1)
    results.append(("R8-P4 Planner", ok_e, dur_e))

    total = round(time.time() - t_start, 1)

    print("\n" + "=" * 70)
    print("R8-P1 BENCHMARK SUMMARY")
    print("=" * 70)
    for name, ok, dur in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:24s} {dur}s")
    print(f"  Total: {total}s")
    n_traces = len(_trace.recent(limit=500))
    print(f"  Execution Trace 记录数（本运行）: {n_traces}")
    all_ok = all(r[1] for r in results)
    print("\n  Overall: " + ("ALL PASS ✅" if all_ok else "SOME FAIL ❌"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
