#!/usr/bin/env python3
"""小6 · Phase 9 B1：薄决策层（ProactiveEngine，纯函数，无副作用）

输入：一个 signal dict（type + 上下文字段）。
输出：Decision(action, signal_type, importance, title, description, payload)

action ∈ {IGNORE, SUGGEST, NOTIFY, CREATE_GOAL}
- 不读 DB、不调 runtime、不 publish 事件、不调工具 —— 纯逻辑。
- CREATE_GOAL 的执行由 proactive.py 的 enacter 负责（经 runtime.submit_goal，带 intent_id 标记），
  不在此层落地，严格遵守「所有主动行为必须 Event→ProactiveDecision→Goal System→Agent Runtime→Policy Guard」。

信号类型（signal.type）：
  - goal_stalled    目标停滞（idle_days ≥ 阈值）→ SUGGEST（ask 模式）/ CREATE_GOAL（auto 模式）/ IGNORE（off 或未满阈值）
  - goal_deadline   目标临近/到期 → NOTIFY
  - error / agent_failed / goal_failed → NOTIFY（high）
  - long_running    任务长时间运行 → NOTIFY（high）
  - reminder / hotspot / weather / alert / review / rule → NOTIFY（沿用既有规则，引擎仅裁决重要度）

建议模式（proactive_config.suggestion_mode）：
  - auto → 可 CREATE_GOAL
  - ask  → 仅 SUGGEST（交用户确认）
  - off  → IGNORE（引擎不决策，交回既有规则通知）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from proactive_config import suggestion_mode, stall_days, importance_rank

ACTION_IGNORE = "IGNORE"
ACTION_SUGGEST = "SUGGEST"
ACTION_NOTIFY = "NOTIFY"
ACTION_CREATE_GOAL = "CREATE_GOAL"

# 引擎可产出 CREATE_GOAL 的信号类型（其余信号不自动建目标）
_GOAL_CAPABLE = {"goal_stalled"}


@dataclass
class Decision:
    action: str
    signal_type: str
    importance: str = "normal"
    title: Optional[str] = None
    description: Optional[str] = None
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "signal_type": self.signal_type,
            "importance": self.importance,
            "title": self.title,
            "description": self.description,
            "payload": self.payload,
        }


def _decide_goal_stalled(signal: dict) -> Decision:
    """目标停滞信号：依建议模式给出 SUGGEST / CREATE_GOAL / IGNORE。"""
    idle = int(signal.get("idle_days") or 0)
    threshold = int(signal.get("stall_threshold") or stall_days())
    title = signal.get("title") or "推进停滞目标"
    next_step = signal.get("next_step") or signal.get("description") or ""
    mode = suggestion_mode()

    if idle < threshold:
        return Decision(ACTION_IGNORE, "goal_stalled", title=title)
    if mode == "auto":
        return Decision(
            ACTION_CREATE_GOAL,
            "goal_stalled",
            importance="normal",
            title=f"推进：{title}",
            description=next_step,
            payload={"goal_id": signal.get("goal_id"), "idle_days": idle},
        )
    if mode == "ask":
        return Decision(
            ACTION_SUGGEST,
            "goal_stalled",
            importance="normal",
            title=f"建议推进：{title}",
            description=next_step,
            payload={"goal_id": signal.get("goal_id"), "idle_days": idle},
        )
    # off：不决策
    return Decision(ACTION_IGNORE, "goal_stalled", title=title)


def _decide_notify(signal: dict, importance: str) -> Decision:
    return Decision(
        ACTION_NOTIFY,
        signal.get("type", "notify"),
        importance=importance,
        title=signal.get("title"),
        description=signal.get("description") or signal.get("content") or signal.get("error"),
        payload=signal.get("payload") or {},
    )


def decide(signal: dict) -> Decision:
    """纯函数：将一条 signal 映射为决策。无任何副作用。"""
    if not signal or not isinstance(signal, dict):
        return Decision(ACTION_IGNORE, "unknown")
    stype = (signal.get("type") or "").lower()

    # 目标停滞：唯一可能自动建 Goal 的信号
    if stype == "goal_stalled":
        return _decide_goal_stalled(signal)

    # 到期/临近 → 通知
    if stype == "goal_deadline":
        return _decide_notify(signal, "normal")

    # 异常/失败 → 高重要度通知
    if stype in ("error", "agent_failed", "goal_failed"):
        return _decide_notify(signal, "high")

    # 长时间运行 → 高重要度通知
    if stype == "long_running":
        return _decide_notify(signal, "high")

    # 其余信号（reminder / hotspot / weather / alert / review / rule 等）
    # 引擎不做 IGNORE，沿用既有规则推送，仅裁决重要度（默认 low/normal，可被 signal 覆盖）
    imp = signal.get("importance") or "normal"
    return _decide_notify(signal, imp)


def is_goal_action(decision: "Decision") -> bool:
    """该决策是否会落地为 Goal 创建（CREATE_GOAL）。供 enacter 判定。"""
    return decision.action == ACTION_CREATE_GOAL


# ── 便捷工厂（供 proactive.py enacter 构建信号）──
def signal_goal_stalled(goal_id, title, idle_days, next_step=None, stall_threshold=None):
    return {
        "type": "goal_stalled",
        "goal_id": goal_id,
        "title": title,
        "idle_days": idle_days,
        "next_step": next_step,
        "stall_threshold": stall_threshold,
    }


def signal_error(title=None, error=None, payload=None):
    return {"type": "error", "title": title, "error": error, "payload": payload or {}}


def signal_long_running(title=None, detail=None, payload=None):
    return {"type": "long_running", "title": title, "detail": detail, "payload": payload or {}}


# 模块级便捷常量（供测试 / 调用方引用，避免硬编码字符串）
ENGINE_VERSION = "1.0.0"
