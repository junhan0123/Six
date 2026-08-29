#!/usr/bin/env python3
"""庄周 · 能力操作系统 · 能力匹配器（Matcher）—— Phase 23.1

职责：用户目标（自然语言）→ 候选能力列表（按相关度打分）。

设计纪律：
- 确定性优先：用关键词命中打分，结果可复现、可验证、无「假成功」。
- 不越权：matcher 只「建议」，不执行。CRITICAL 占位能力命中后标记为 blocked，
  由 router 在语义层拦截，永远不会进入执行路径。
- 不依赖 LLM 做主匹配（避免误报/幻觉）。保留可选 llm_assist 钩子，默认关闭。
"""

from __future__ import annotations

from typing import List, Dict, Tuple

from .registry import Capability, get_registry, Risk, Permission


def _score(cap: Capability, goal: str) -> int:
    """关键词命中打分；命中越多分越高。"""
    goal_l = goal.lower()
    score = 0
    for kw in cap.keywords:
        if kw and kw.lower() in goal_l:
            # 长关键词权重更高（更具体）
            score += 1 + min(len(kw), 6) // 3
    return score


def match(goal: str, top_k: int = 5, include_blocked: bool = True) -> List[Dict]:
    """匹配用户目标到能力。

    返回：[{capability, score, blocked}]，按 score 降序。
    blocked=True 表示命中了 CRITICAL 占位能力（应被 router 拒绝）。
    """
    goal = (goal or "").strip()
    if not goal:
        return []

    scored: List[Tuple[Capability, int]] = []
    for cap in get_registry().values():
        s = _score(cap, goal)
        if s > 0:
            scored.append((cap, s))

    scored.sort(key=lambda x: x[1], reverse=True)

    out: List[Dict] = []
    for cap, s in scored[:top_k]:
        blocked = (cap.permission == Permission.BLOCK) or (not cap.available)
        out.append({
            "capability": cap.to_dict(),
            "score": s,
            "blocked": blocked,
        })
    return out


def match_ids(goal: str, top_k: int = 5) -> List[str]:
    """仅返回命中的能力 id（按相关度）。供 router/composer 消费。"""
    return [m["capability"]["id"] for m in match(goal, top_k=top_k)]


def best_match(goal: str) -> Dict | None:
    """返回最高分命中（无则 None）。"""
    res = match(goal, top_k=1)
    return res[0] if res else None


def explain(goal: str, top_k: int = 5) -> str:
    """人类可读的匹配说明（可解释性要求）。"""
    res = match(goal, top_k=top_k)
    if not res:
        return "未匹配到任何已知能力（将走通用 LLM 处理）。"
    lines = [f"目标「{goal}」匹配到 {len(res)} 项能力："]
    for m in res:
        c = m["capability"]
        tag = " ⛔已拒绝" if m["blocked"] else ""
        lines.append(f"  · {c['icon']} {c['name']}（{c['group']}）"
                     f" 相关度={m['score']} 风险={c['risk']}{tag}")
    return "\n".join(lines)
