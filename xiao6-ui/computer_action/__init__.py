#!/usr/bin/env python3
"""庄周 · Computer Action Layer v1.0（独立能力层）—— Phase 21

门面：observe / plan / execute / get_capabilities / run_loop。
设计纪律（守红线）：
- 所有真实裁决/执行委托 permission_guard + safety + os_bridge，不新建第二执行系统。
- Agent Runtime / Planner / Executor 核心、EventBus、Memory 核心一律不触碰。
- 仅开放白名单动作（safety.WHITELIST）：open_application / open_folder /
  open_file / search / copy_text。删除/改系统/自动发消息/无确认危险操作均被拒。
- 兼容既有 `from computer_action import ComputerAction`（数据模型来源 computer_action_model）。
"""
from __future__ import annotations

# 兼容既有数据模型导入（不重复定义）
from computer_action_model import ComputerAction

__all__ = ["ComputerAction", "observe", "plan", "execute", "get_capabilities", "run_loop"]


def observe(scope="window"):
    """观察环节：包装 perception，返回动作闭环可用的环境快照。"""
    from .observer import observe as _observe
    return _observe(scope)


def plan(capability, target="", parameters=None, *, goal_id=None):
    """规划环节：白名单前置校验 + 委托 os_bridge.action_plan 裁决（绝不执行）。"""
    from .planner import plan as _plan
    return _plan(capability, target=target, parameters=parameters, goal_id=goal_id)


def execute(action_id, confirmed=False, goal_id=None):
    """执行环节：委托 os_bridge.action_execute（用户确认 → 真实执行 → 验证）。"""
    from .planner import execute as _execute
    return _execute(action_id, confirmed=confirmed, goal_id=goal_id)


def get_capabilities():
    """当前 Hand 能力清单（白名单内）。"""
    from .safety import WHITELIST
    try:
        from capability_os.registry import get_capability
        out = []
        for c in sorted(WHITELIST):
            cap = get_capability(c)
            if cap is None:
                out.append({"id": c})
            else:
                out.append({"id": c, "label": cap.name,
                            "risk": cap.risk, "expectedEffect": cap.description})
        return out
    except Exception:
        return [{"id": c} for c in sorted(WHITELIST)]


def run_loop(capability, target="", parameters=None, *, goal_id=None, scope="window"):
    """高层编排（可选）：观察 → 规划 → 执行 → 验证，并广播四态相位事件。

    注意：需要用户确认的动作（MEDIUM）在 run_loop 自动路径下会被拒绝（confirmed=False），
    真实确认仍发生在 UI（action_plan → action_execute(confirmed=True)）。
    """
    from eventbus import publish_domain
    from .observer import observe as _observe

    publish_domain("COMPUTER_ACTION_PHASE", {"phase": "observe", "capability": capability, "goalId": goal_id})
    obs = _observe(scope)

    preview = plan(capability, target=target, parameters=parameters, goal_id=goal_id)
    publish_domain("COMPUTER_ACTION_PHASE", {"phase": "plan", "capability": capability, "goalId": goal_id})
    if not preview.get("ok") or preview.get("blocked"):
        return {"ok": False, "observation": obs, "plan": preview}

    action_id = preview.get("actionId")
    need = preview.get("needConfirm", False)
    publish_domain("COMPUTER_ACTION_PHASE", {"phase": "execute", "capability": capability, "goalId": goal_id})
    res = execute(action_id, confirmed=not need, goal_id=goal_id)
    publish_domain("COMPUTER_ACTION_PHASE", {"phase": "verify", "capability": capability, "goalId": goal_id})
    return {"ok": True, "observation": obs, "plan": preview, "result": res}
