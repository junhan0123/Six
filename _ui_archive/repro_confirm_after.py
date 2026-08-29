# -*- coding: utf-8 -*-
"""
PHASE 5.9-P0-1 · STEP 6 AFTER 行为验证
验证 F2（ai_core/execution/api.py NONE 分支）+ F1（policy_engine force_modal）：
  - 场景1 REJECT：CONFIRM 工具（run_shell）→ 用户拒绝 → 绝不执行（execute_tool 不被调用）
  - 场景2 APPROVE：CONFIRM 工具 → 用户批准 → 才执行（execute_tool 被调用）
全程复用既有 approval 机制（request_approval → modal 事件 → resolve 唤醒），无第二套系统。
"""
import sys
import threading
import time

sys.path.insert(0, "G:/xiao6/xiao6-ui")

import tools as T

_called = []
_orig = T.execute_tool


def fake_execute(name, args, allowed=None):
    _called.append((name, args))
    return "XIAO6_CONFIRM_TEST_EXECUTED_AFTER_APPROVAL"


T.execute_tool = fake_execute

from eventbus import bus, TOPIC_SSE
from policy_engine import resolve
from ai_core.execution import run
from ai_core.execution.context import PermissionMode

captured = {}


def on_ev(ev):
    p = getattr(ev, "payload", None)
    if isinstance(p, dict) and p.get("xiao6_event") == "modal" and p.get("kind") == "agent_approval":
        captured["ticket"] = p.get("ticket")
        captured["tool"] = p.get("tool")


tok = bus.subscribe(TOPIC_SSE, on_ev)


def wait_captured(timeout=8.0):
    t0 = time.time()
    while "ticket" not in captured and time.time() - t0 < timeout:
        time.sleep(0.05)


# ===== 场景 1：用户拒绝（REJECT）=====
print("== 场景1 REJECT ==")
_called.clear()
captured.clear()
res1 = None


def _run1():
    global res1
    res1 = run("run_shell", {"command": "echo XIAO6_CONFIRM_TEST"}, permission=PermissionMode.NONE)


th1 = threading.Thread(target=_run1)
th1.start()
wait_captured()
if "ticket" in captured:
    print("  modal/agent_approval 事件已发布，ticket 捕获 =", captured["ticket"][:12], "...")
    print("  模拟用户点击「拒绝」→ resolve(ticket, reject)")
    resolve(captured["ticket"], "reject")
else:
    print("  !! 未捕获到 modal/agent_approval 事件（审批卡未弹出）")
th1.join(timeout=15)
ran1 = any(n == "run_shell" for n, _ in _called)
print("  run 返回 =", repr(res1))
print("  execute_tool 被调用(run_shell) =", ran1)
print("  场景1 通过(拒绝→不执行) =", not ran1 and ("未批准" in str(res1) or "未执行" in str(res1)))

# ===== 场景 2：用户批准（APPROVE）=====
print("== 场景2 APPROVE ==")
_called.clear()
captured.clear()
res2 = None


def _run2():
    global res2
    res2 = run("run_shell", {"command": "echo XIAO6_CONFIRM_TEST"}, permission=PermissionMode.NONE)


th2 = threading.Thread(target=_run2)
th2.start()
wait_captured()
if "ticket" in captured:
    print("  模拟用户点击「批准」→ resolve(ticket, approve)")
    resolve(captured["ticket"], "approve")
else:
    print("  !! 未捕获到 modal/agent_approval 事件")
th2.join(timeout=15)
ran2 = any(n == "run_shell" for n, _ in _called)
print("  run 返回 =", repr(res2))
print("  execute_tool 被调用(run_shell) =", ran2)
print("  场景2 通过(批准→执行) =", ran2)

bus.unsubscribe(tok)

import json

result = {
    "scenario1_reject": {"execute_called": ran1, "run_return": res1,
                         "passed": bool(not ran1 and ("未批准" in str(res1) or "未执行" in str(res1)))},
    "scenario2_approve": {"execute_called": ran2, "run_return": res2,
                          "passed": bool(ran2)},
}
with open("G:/xiao6/_ui_archive/step6_after_repro.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("证据已写入 step6_after_repro.json")
print("AFTER 验证结论:", "PASS" if (result["scenario1_reject"]["passed"] and result["scenario2_approve"]["passed"]) else "FAIL")
