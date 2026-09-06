#!/usr/bin/env python3
"""Proactive Policy — 防骚扰策略。

职责：
- 同主题 24 小时限制
- 忽略后 7 天冷却
- 每日建议数量限制

约束：
- 只读 meta 表
- 不修改其他模块
"""

from __future__ import annotations

import time
from typing import Dict, Any, Optional


# 配置常量
SAME_TOPIC_WINDOW_HOURS = 24
IGNORED_COOLDOWN_DAYS = 7
MAX_SUGGESTIONS_PER_DAY = 10


def _meta_get(key: str, default: str = "0") -> str:
    """读取 meta 表键值（best-effort）。"""
    try:
        from db import db_conn
        conn = db_conn()
        row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        conn.close()
        return row[0] if row else default
    except Exception:
        return default


def _meta_set(key: str, value: str) -> None:
    """写入 meta 表键值（best-effort）。"""
    try:
        from db import db_conn
        conn = db_conn()
        conn.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def is_topic_throttled(topic: str) -> bool:
    """
    检查同主题是否在 24 小时窗口内已发送过建议。
    
    返回：
    True = 应限制
    False = 可发送
    """
    last_ts_str = _meta_get(f"proactive_last_{topic}", "0")
    try:
        last_ts = float(last_ts_str)
    except ValueError:
        last_ts = 0
    
    now = time.time()
    window_seconds = SAME_TOPIC_WINDOW_HOURS * 3600
    
    if now - last_ts < window_seconds:
        return True
    
    return False


def mark_topic_sent(topic: str) -> None:
    """标记主题已发送建议。"""
    _meta_set(f"proactive_last_{topic}", str(time.time()))


def is_ignored(topic: str) -> bool:
    """
    检查主题是否被用户忽略（7 天冷却期）。
    
    返回：
    True = 已忽略，冷却中
    False = 可重新发送
    """
    ignored_ts_str = _meta_get(f"proactive_ignored_{topic}", "0")
    try:
        ignored_ts = float(ignored_ts_str)
    except ValueError:
        ignored_ts = 0
    
    now = time.time()
    cooldown_seconds = IGNORED_COOLDOWN_DAYS * 24 * 3600
    
    if now - ignored_ts < cooldown_seconds:
        return True
    
    return False


def mark_ignored(topic: str) -> None:
    """标记主题为已忽略。"""
    _meta_set(f"proactive_ignored_{topic}", str(time.time()))


def get_daily_suggestion_count() -> int:
    """获取今日已发送建议数量。"""
    today = time.strftime("%Y-%m-%d")
    count_str = _meta_get(f"proactive_count_{today}", "0")
    try:
        return int(count_str)
    except ValueError:
        return 0


def increment_daily_count() -> None:
    """增加今日建议计数。"""
    today = time.strftime("%Y-%m-%d")
    current = get_daily_suggestion_count()
    _meta_set(f"proactive_count_{today}", str(current + 1))


def should_send(topic: str, suggestions_count: int) -> bool:
    """
    综合判断是否应发送建议。
    
    规则：
    1. 同主题 24 小时限制
    2. 忽略后 7 天冷却
    3. 每日建议数量限制
    
    返回：
    True = 可以发送
    False = 应限制
    """
    if is_topic_throttled(topic):
        return False
    
    if is_ignored(topic):
        return False
    
    if suggestions_count >= MAX_SUGGESTIONS_PER_DAY:
        return False
    
    return True


def get_policy_status() -> Dict[str, Any]:
    """返回当前策略状态。"""
    return {
        "same_topic_window_hours": SAME_TOPIC_WINDOW_HOURS,
        "ignored_cooldown_days": IGNORED_COOLDOWN_DAYS,
        "max_suggestions_per_day": MAX_SUGGESTIONS_PER_DAY,
        "daily_count": get_daily_suggestion_count()
    }