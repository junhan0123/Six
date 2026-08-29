# -*- coding: utf-8 -*-
"""
PHASE 5.9-P0-1 · STEP 2 安全复现（BEFORE 状态证据）
复现对象：聊天路径（PermissionMode.NONE）下 CONFIRM 级工具（run_shell）是否被
          未经用户确认即执行。
方法：monkeypatch tools.execute_tool 以记录「是否被调用」，对 run_shell 仅返回
      模拟结果（不真正执行命令，安全）。
结论判定：若 execute_tool 被调用 -> CONFIRM WITHOUT APPROVAL = EXECUTION（BUG）。
"""
import sys
sys.path.insert(0, "G:/xiao6/xiao6-ui")

import tools as T
_called = []
_orig = T.execute_tool

def fake_execute(name, args, allowed=None):
    _called.append((name, args))
    if name == "run_shell":
        # 仅记录调用并模拟安全结果，不真正执行 shell 命令
        return "XIAO6_CONFIRM_TEST_WOULD_EXECUTE"
    return _orig(name, args, allowed) if _orig is not None else "ok"

T.execute_tool = fake_execute

from ai_core.execution import run
from ai_core.execution.context import PermissionMode
import policy_engine as pe

print("== PHASE 5.9-P0-1 STEP2 BEFORE 复现 ==")
dec = pe.evaluate("run_shell", {"command": "echo XIAO6_CONFIRM_TEST"}, default_deny=True)
print("policy_engine.evaluate(run_shell, no_goal) -> decision =", dec.get("decision"))

# 聊天路径：默认 permission=NONE（小6聊天/run_fc_loop 即此上下文）
res = run("run_shell", {"command": "echo XIAO6_CONFIRM_TEST"}, permission=PermissionMode.NONE)

called = any(n == "run_shell" for n, _ in _called)
print("run() 返回值 =", repr(res))
print("execute_tool 被调用(run_shell) =", called)
print(">>> BEFORE 结论: CONFIRM 工具在 NONE 路径下未经审批即执行 =", "YES (安全缺陷)" if called else "NO")

import json
with open("G:/xiao6/_ui_archive/step2_before_repro.json", "w", encoding="utf-8") as f:
    json.dump({
        "evaluate_decision": dec.get("decision"),
        "run_return": res,
        "execute_tool_called_for_run_shell": called,
        "bug_confirmed": called,
    }, f, ensure_ascii=False, indent=2)
print("证据已写入 step2_before_repro.json")
