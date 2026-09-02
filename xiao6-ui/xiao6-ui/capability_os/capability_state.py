#!/usr/bin/env python3
"""Xiao6 · 能力操作系统 · 能力运行时状态（Capability State）—— Phase 23.1

职责：
1. 跟踪「当前正在使用的能力」（active set），由外部事件（tool_started /
   COMPUTER_ACTION_CALLED）驱动，不自己产生执行。
2. 提供能力「当下是否可用」的快照（复用 self_diagnosis / capability_registry 的
   只读探测，不新增健康探测逻辑）。

纪律：只读 + 状态聚合。不执行、不修改 Memory、不发布新事件协议。
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .registry import get_registry, Capability


class CapabilityState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        # capability_id -> {since, source}  ：当前活跃能力
        self._active: Dict[str, dict] = {}
        # 最近一次 compose 出来的计划（供 UI 展示「将要用什么」）
        self._last_plan: Optional[dict] = None

    # —— 活跃能力（运行时，由事件驱动）——
    def activate(self, cap_id: str, source: str = "event") -> None:
        with self._lock:
            self._active[cap_id] = {"since": _now(), "source": source}

    def deactivate(self, cap_id: str) -> None:
        with self._lock:
            self._active.pop(cap_id, None)

    def active_ids(self) -> List[str]:
        with self._lock:
            return list(self._active.keys())

    def active_view(self) -> List[dict]:
        """返回 [{id, name, icon, group, since, source}] 供 UI 展示。"""
        reg = get_registry()
        with self._lock:
            out = []
            for cid, meta in self._active.items():
                c = reg.get(cid)
                if c:
                    out.append({
                        "id": c.id, "name": c.name, "icon": c.icon,
                        "group": c.group, "since": meta.get("since"),
                        "source": meta.get("source"),
                    })
            return out

    # —— 计划（由 composer 写入）——
    def set_plan(self, plan: dict) -> None:
        with self._lock:
            self._last_plan = plan

    def last_plan(self) -> Optional[dict]:
        with self._lock:
            return self._last_plan

    # —— 可用性快照（只读，复用既有探测入口）——
    def availability_snapshot(self) -> List[dict]:
        """返回每个能力的当前可用性（available 字段 + 是否被禁用）。"""
        out = []
        for c in get_registry().values():
            out.append({
                "id": c.id, "name": c.name, "group": c.group,
                "available": c.available, "risk": c.risk,
                "permission": c.permission,
            })
        return out


_STATE = CapabilityState()


def get_state() -> CapabilityState:
    return _STATE


def _now() -> float:
    import time
    return time.time()
