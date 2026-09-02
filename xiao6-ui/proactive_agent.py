#!/usr/bin/env python3
"""proactive_agent 模块兼容层。

S95: 修复 server.py 中 import proactive_agent 找不到模块的问题。
实际实现位于 proactive.py，本模块提供兼容接口。
"""

# 从实际的 proactive 模块导入可用的接口
from proactive import (  # noqa: F401
    SUBSCRIBERS,
    SUBSCRIBERS_LOCK,
    flush_pending,
    make_daily_briefing,
    tick_loop,
    collect_today_suggestions,
    set_rate_limited,
    is_rate_limited,
    mark_user_activity,
)


def get_status():
    """返回 Proactive Agent 状态。"""
    return {
        "ok": True,
        "feature": True,
        "module": "proactive",
        "subscribers": len(SUBSCRIBERS),
    }


def bootstrap():
    """初始化 Proactive Agent。"""
    return {
        "scheduler": "tick_loop",
        "ok": True,
    }

__version__ = "1.0.0"
