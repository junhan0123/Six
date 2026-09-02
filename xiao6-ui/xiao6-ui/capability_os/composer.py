#!/usr/bin/env python3
"""Xiao6 · 能力操作系统 · 多能力组合器（Composer）—— Phase 23.1

职责：把「一个任务」拆成「多能力有序执行计划（DAG）」。

示例：
  任务「帮我整理桌面上的项目」
    → Perception（看桌面）→ Computer Action（整理/打开）→ Memory（记录）

纪律：
- composer 只「编排」，不执行。产出的 plan 交给 Agent / Permission Guard 消费，
  绝不自己调用任何能力。
- 组合顺序强制遵循 router 的 观察→理解→执行 原则。
- 任一被 block 的能力，plan 直接标记 unsafe，不会被放进可执行步骤。
"""

from __future__ import annotations

from typing import Dict, List

from .registry import get_registry, Permission
from .matcher import match_ids
from .router import route


def compose(task: str, top_k: int = 6) -> Dict:
    """组合多能力完成一个任务。

    返回：
    {
      "task": str,
      "matched": [cap_id...],
      "route": {ordered, needs_confirm, blocked, safe_to_execute},
      "steps": [ {order, id, name, phase, action, permission, note} ... ],
      "safe": bool,
      "summary": str,
    }
    """
    task = (task or "").strip()
    matched_ids = match_ids(task, top_k=top_k)
    r = route(matched_ids)

    steps: List[Dict] = []
    order = 0
    for s in r["ordered"]:
        order += 1
        cap = get_registry().get(s["id"])
        action = _describe_action(cap, task) if cap else s["id"]
        steps.append({
            "order": order,
            "id": s["id"],
            "name": cap.name if cap else s["id"],
            "icon": cap.icon if cap else "•",
            "phase": s["phase"],
            "permission": s["permission"],
            "blocked": s["blocked"],
            "action": action,
        })

    safe = r["safe_to_execute"] and len(matched_ids) > 0
    summary = _summarize(steps, safe)

    return {
        "task": task,
        "matched": matched_ids,
        "route": r,
        "steps": steps,
        "safe": safe and not r["blocked"],
        "summary": summary,
    }


def _describe_action(cap, task: str) -> str:
    """为某能力生成一句「将要做什么」的可读描述。"""
    g = cap.group
    if g == "Perception":
        return f"观察当前屏幕/窗口：{task}"
    if g == "Self Diagnosis":
        return f"体检并定位问题：{task}"
    if g == "Memory":
        return f"检索记忆以理解上下文：{task}"
    if g == "Knowledge":
        return f"查本地知识库：{task}"
    if g == "User Model":
        return f"读取用户画像/偏好：{task}"
    if g == "World Pulse":
        return f"获取热点/时事上下文：{task}"
    if g == "Computer Action":
        return f"经 Guard 执行电脑动作（需确认）：{task}"
    if g == "Tools":
        return f"调用工具：{task}"
    if g == "Goals":
        return f"建立/推进目标：{task}"
    if g == "Voice":
        return f"语音输入输出：{task}"
    return task


def _summarize(steps: List[Dict], safe: bool) -> str:
    if not steps:
        return "未匹配到可执行能力（走通用 LLM 处理）。"
    icons = " → ".join(f"{s['icon']}{s['name']}" for s in steps)
    verdict = "✅ 计划安全可执行" if safe else "⛔ 含被拒绝/未实现能力，不可自动执行"
    return f"{icons}\n{verdict}"
