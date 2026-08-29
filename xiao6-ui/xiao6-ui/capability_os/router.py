#!/usr/bin/env python3
"""庄周 · 能力操作系统 · 调用路由器（Router）—— Phase 23.1

职责：给定一组候选能力，决定「调用顺序」并标出需要确认 / 被拒绝的项。

原则（来自规格）：
  先观察（observe）→ 再理解（understand）→ 再执行（execute）。
  禁止直接执行危险动作：任何 CRITICAL/BLOCK 能力一律拦截，绝不放行进执行相位。

纪律：
- router 只「排序 + 标注」，不执行任何能力。
- 不复制权限逻辑：permission 标注只是对既有 Guard 词汇的镜像；真实拦截由
  permission_guard 在执行期做。这里做的是「语义层提前预警」，避免把危险意图
  传递给执行路径。
"""

from __future__ import annotations

from typing import List, Dict

from .registry import Capability, get_registry, OBSERVE_GROUPS, UNDERSTAND_GROUPS, \
    EXECUTE_GROUPS, Permission, Risk

# 相位顺序：观察 → 理解 → 执行
_PHASE_ORDER = ["observe", "understand", "execute"]


def _phase_of(cap: Capability) -> str:
    if cap.group in OBSERVE_GROUPS:
        return "observe"
    if cap.group in UNDERSTAND_GROUPS:
        return "understand"
    return "execute"


def route(cap_ids: List[str]) -> Dict:
    """对一组能力 id 排序并标注权限。

    返回：
    {
      "ordered": [ {id, name, phase, permission, blocked, reason} ... ],  # 观察→理解→执行
      "needs_confirm": [id...],
      "blocked": [id...],
      "safe_to_execute": bool,   # 无 blocked 且执行相位无越权
    }
    """
    caps: List[Capability] = []
    for cid in cap_ids:
        c = get_registry().get(cid)
        if c:
            caps.append(c)

    # 标注
    annotated = []
    needs_confirm = []
    blocked = []
    for c in caps:
        phase = _phase_of(c)
        is_blocked = (c.permission == Permission.BLOCK) or (not c.available)
        reason = ""
        if is_blocked:
            blocked.append(c.id)
            reason = "CRITICAL/未实现能力，已被能力层永久拒绝（须走 Permission Guard）"
        elif c.permission == Permission.CONFIRM:
            needs_confirm.append(c.id)
            reason = "MEDIUM 风险，执行前需用户确认"
        annotated.append({
            "id": c.id, "name": c.name, "phase": phase,
            "permission": c.permission, "blocked": is_blocked, "reason": reason,
        })

    # 按相位排序（同相位保持原序）
    annotated.sort(key=lambda a: _PHASE_ORDER.index(a["phase"]))

    return {
        "ordered": annotated,
        "needs_confirm": needs_confirm,
        "blocked": blocked,
        "safe_to_execute": len(blocked) == 0,
    }


def explain_route(route_result: Dict) -> str:
    """人类可读的路由说明。"""
    lines = ["调用顺序（观察 → 理解 → 执行）："]
    for step in route_result["ordered"]:
        mark = "⛔" if step["blocked"] else ("⚠️" if step["permission"] == Permission.CONFIRM else "✅")
        lines.append(f"  {mark} [{step['phase']}] {step['name']}（{step['permission']}）"
                     + (f" — {step['reason']}" if step["reason"] else ""))
    if route_result["needs_confirm"]:
        lines.append(f"需确认：{', '.join(route_result['needs_confirm'])}")
    if route_result["blocked"]:
        lines.append(f"已拒绝：{', '.join(route_result['blocked'])}")
    lines.append("安全可执行：" + ("是" if route_result["safe_to_execute"] else "否"))
    return "\n".join(lines)
