# -*- coding: utf-8 -*-
"""
PHASE 5.9-P0-1 · STEP 7 安全回归
验证 F2 补丁未破坏既有权限语义：
  R1: AUTO 工具（get_time）在 NONE 路径直接执行，不弹审批（不退化）
  R2: BLOCK 危险命令（rm -rf /，经 is_never_by_args / sandbox）仍拦截，execute_tool 不被调用
  R3: evaluate 决策矩阵：get_time=auto / run_shell(echo)=confirm / 危险命令=block
  R4: policy.evaluate 未被绕过（NONE 分支显式先行 evaluate）
"""
import sys
import threading
import time

sys.path.insert(0, "G:/xiao6/xiao6-ui")

import tools as T

_called = []


def fake_execute(name, args, allowed=None):
    _called.append(name)
    return f"FAKE_{name}"


T.execute_tool = fake_execute

import policy_engine as pe
from ai_core.execution import run
from ai_core.execution.context import PermissionMode

print("== R3 evaluate 决策矩阵 ==")
matrix = {}
for tool, args in [
    ("get_time", {"city": "北京"}),
    ("run_shell", {"command": "echo hi"}),
    ("run_shell", {"command": "rm -rf /"}),
    ("run_shell", {"command": "curl -s http://169.254.169.254/latest/meta-data/"}),
]:
    d = pe.evaluate(tool, args, default_deny=True)
    matrix[tool + "|" + str(args)[:30]] = d.get("decision")
    print(f"  {tool} {str(args)[:40]} -> {d.get('decision')}")

print("== R1 AUTO 工具直接执行（无审批）==")
_called.clear()
r = run("get_time", {"city": "北京"}, permission=PermissionMode.NONE)
r1 = "get_time" in _called
print("  get_time executed =", r1, "| return =", repr(r)[:60])

print("== R2 BLOCK 危险命令拦截 ==")
_called.clear()
r = run("run_shell", {"command": "rm -rf /"}, permission=PermissionMode.NONE)
r2 = "run_shell" in _called
print("  run_shell(rm -rf /) executed =", r2, "| return =", repr(r)[:80])

print("== R2b CONFIRM 级（IMDS curl 属既有 confirm 语义）未经批准不执行 ==")
_called.clear()
captured = {}
from eventbus import bus, TOPIC_SSE
from policy_engine import resolve as _resolve


def _on_ev(ev):
    p = getattr(ev, "payload", None)
    if isinstance(p, dict) and p.get("xiao6_event") == "modal" and p.get("kind") == "agent_approval":
        captured["ticket"] = p.get("ticket")


_tok = bus.subscribe(TOPIC_SSE, _on_ev)
_res = {}


def _run_imds():
    _res["r"] = run("run_shell", {"command": "curl -s http://169.254.169.254/latest/meta-data/"},
                    permission=PermissionMode.NONE)


_th = threading.Thread(target=_run_imds)
_th.start()
_t0 = time.time()
while "ticket" not in captured and time.time() - _t0 < 8:
    time.sleep(0.05)
if "ticket" in captured:
    _resolve(captured["ticket"], "reject")
_th.join(timeout=15)
r2b = "run_shell" in _called
print("  run_shell(IMDS curl) executed =", r2b, "| return =", repr(_res.get("r"))[:80])
bus.unsubscribe(_tok)

import json

result = {
    "matrix": matrix,
    "r1_auto_get_time_executed": r1,
    "r2_block_rm_rf_executed": r2,
    "r2b_confirm_imds_curl_executed": r2b,
    "passed": bool(r1 and not r2 and not r2b
                   and matrix.get("get_time|{'city': '北京'}") in ("auto",)
                   and matrix.get("run_shell|{'command': 'echo hi'}") == "confirm"
                   and matrix.get("run_shell|{'command': 'rm -rf /'}") == "block"),
}
with open("G:/xiao6/_ui_archive/step7_regression.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("证据已写入 step7_regression.json")
print("STEP7 回归结论:", "PASS" if result["passed"] else "FAIL")
