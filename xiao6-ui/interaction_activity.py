#!/usr/bin/env python3
"""Interaction Activity — 交互活动记录。

职责：
- 记录交互活动
- 提供活动查询
- 内存存储（不写数据库）

约束：
- 不创建新数据库
- 不修改现有数据表
- 线程安全
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class Activity:
    """活动记录。"""
    activity_id: str
    type: str  # "parse", "intent", "analysis", "command"
    title: str
    status: str = "idle"  # idle, running, completed, error
    description: str = ""
    intent_type: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "activity_id": self.activity_id,
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "description": self.description,
            "intent_type": self.intent_type,
            "timestamp": self.timestamp,
            "relative_time": _rel_time(self.timestamp)
        }


def _rel_time(ts: float) -> str:
    """计算相对时间。"""
    diff = time.time() - ts
    if diff < 60:
        return "刚刚"
    elif diff < 3600:
        return f"{int(diff / 60)} 分钟前"
    elif diff < 86400:
        return f"{int(diff / 3600)} 小时前"
    else:
        return f"{int(diff / 86400)} 天前"


class ActivityManager:
    """活动管理器。"""

    def __init__(self):
        self._activities: List[Activity] = []
        self._lock = threading.Lock()
        self._max_activities = 50

    def add_activity(self, activity_type: str, title: str, status: str = "running",
                     description: str = "", intent_type: str = "", metadata: Dict[str, Any] = None) -> Activity:
        """添加活动记录。"""
        activity_id = f"act_{int(time.time() * 1000)}_{threading.current_thread().ident}"
        activity = Activity(
            activity_id=activity_id,
            type=activity_type,
            title=title,
            status=status,
            description=description,
            intent_type=intent_type,
            metadata=metadata or {}
        )
        with self._lock:
            self._activities.append(activity)
            self._cleanup()
        return activity

    def get_activities(self, limit: int = 10, status_filter: Optional[str] = None) -> List[Activity]:
        """获取活动列表。"""
        with self._lock:
            activities = self._activities[::-1]  # 最新在前
            if status_filter:
                activities = [a for a in activities if a.status == status_filter]
            return activities[:limit]

    def update_activity_status(self, activity_id: str, status: str) -> bool:
        """更新活动状态。"""
        with self._lock:
            for activity in self._activities:
                if activity.activity_id == activity_id:
                    activity.status = status
                    return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取活动统计。"""
        with self._lock:
            total = len(self._activities)
            active = sum(1 for a in self._activities if a.status == "running")
            completed = sum(1 for a in self._activities if a.status == "completed")
            
            return {
                "total": total,
                "active": active,
                "completed": completed,
                "max_activities": self._max_activities
            }

    def _cleanup(self):
        """清理旧活动。"""
        if len(self._activities) > self._max_activities:
            self._activities = self._activities[-self._max_activities:]


# 全局活动管理器
_activity_manager = ActivityManager()


def get_activity_manager() -> ActivityManager:
    """获取全局活动管理器。"""
    return _activity_manager


def add_interaction_activity(intent_type: str, title: str, description: str = "") -> Activity:
    """便捷函数：添加交互活动。"""
    return _activity_manager.add_activity(
        activity_type="interaction",
        title=title,
        status="running",
        description=description,
        intent_type=intent_type
    )


def complete_activity(activity_id: str) -> bool:
    """便捷函数：完成活动。"""
    return _activity_manager.update_activity_status(activity_id, "completed")