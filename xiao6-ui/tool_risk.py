#!/usr/bin/env python3
"""Xiao6 · Tool Risk Registry（Agent Trust Layer）—— SAFE / CONFIRM / BLOCK 三级风险分级。

Phase 7 目标：执行链增加「工具风险分级 + 执行意图透明化」，提升 Agent 执行可信度。

纪律（极瘦红线，违反即失败）：
- 本模块只做「风险标注」视图，**不新建第二套权限系统**。
- 权限裁决真相源仍是 policy_engine（evaluate / tool_permission），四级 auto/confirm/session/never
  经 _PERM_TO_RISK 映射为三级 SAFE/CONFIRM/BLOCK。
- 执行入口仍是 ai_core.execution.run（policy 门 + approval），本模块不绕过、不替代。
"""
from __future__ import annotations

SAFE = "SAFE"
CONFIRM = "CONFIRM"
BLOCK = "BLOCK"

_RISK_ORDER = {SAFE: 0, CONFIRM: 1, BLOCK: 2}

# policy_engine 四级（auto/confirm/session/never）→ 三级风险标注
_PERM_TO_RISK = {
    "auto": SAFE,
    "session": SAFE,     # Goal 级预批准 = 用户已确认过，视为安全
    "confirm": CONFIRM,
    "never": BLOCK,
}

# 显式风险注册表（补充语义；policy_engine 仍是裁决真相源，此表仅作标注兜底/参考）
TOOL_RISK_REGISTRY = {
    # SAFE：只读 / 查询 / 获取状态（无需确认）
    "web_search": SAFE, "get_weather": SAFE, "get_time": SAFE,
    "get_hotspots": SAFE, "calculator": SAFE, "file_list": SAFE,
    "file_read": SAFE, "memory_search": SAFE, "note_list": SAFE,
    "task_list": SAFE, "profile_get": SAFE, "reminder_list": SAFE,
    "list_skills": SAFE, "list_processes": SAFE,
    # CONFIRM：修改 / 移动 / 删除 / 发送 / 改系统设置（需确认）
    "file_write": CONFIRM, "file_move": CONFIRM, "file_delete": CONFIRM,
    "file_make_dir": CONFIRM, "file_rename": CONFIRM, "note_save": CONFIRM,
    "profile_set": CONFIRM, "reminder_set": CONFIRM, "set_task": CONFIRM,
    "complete_task": CONFIRM, "update_task_step": CONFIRM,
    "run_shell": CONFIRM, "install_software": CONFIRM,
    # BLOCK：危险系统操作 / 未授权权限提升（禁止）
    "kill_process": BLOCK,
}


def risk_level(tool: str) -> str:
    """返回工具的三级风险等级（SAFE/CONFIRM/BLOCK）。

    优先以 policy_engine.tool_permission 为真相源（四级→三级映射），
    显式注册表 TOOL_RISK_REGISTRY 作为兜底覆盖。
    """
    try:
        from policy_engine import tool_permission
        perm = tool_permission(tool)
        return _PERM_TO_RISK.get(perm, CONFIRM)
    except Exception:
        pass
    return TOOL_RISK_REGISTRY.get(tool, CONFIRM)


def max_risk(tools: list) -> str:
    """返回一组工具的最高风险等级（用于 Execution Intent Report）。"""
    top = SAFE
    for t in tools or []:
        r = risk_level(t)
        if _RISK_ORDER.get(r, 1) > _RISK_ORDER.get(top, 0):
            top = r
    return top


def need_confirmation(tools: list) -> bool:
    """任意工具风险 >= CONFIRM 则需要用户确认（进入 Approval）。"""
    return any(risk_level(t) in (CONFIRM, BLOCK) for t in (tools or []))
