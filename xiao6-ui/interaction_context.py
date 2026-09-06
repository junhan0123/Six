#!/usr/bin/env python3
"""Interaction Context — 交互上下文管理。

职责：
- 管理用户交互会话状态
- 提供上下文追踪
- 不持久化到数据库

约束：
- 内存存储
- 不创建数据库表
- 线程安全
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class InteractionSession:
    """单次交互会话。"""
    session_id: str
    user_input: str = ""
    command: Optional[Dict[str, Any]] = None
    intent: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_input": self.user_input,
            "command": self.command,
            "intent": self.intent,
            "response": self.response,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration": (self.ended_at or time.time()) - self.started_at,
            "metadata": self.metadata
        }


class InteractionContext:
    """交互上下文管理器。"""

    def __init__(self):
        self._sessions: Dict[str, InteractionSession] = {}
        self._lock = threading.Lock()
        self._max_sessions = 100  # 最大保留会话数

    def create_session(self, user_input: str = "") -> InteractionSession:
        """创建新会话。"""
        session_id = f"sess_{int(time.time() * 1000)}_{threading.current_thread().ident}"
        session = InteractionSession(session_id=session_id, user_input=user_input)
        
        with self._lock:
            self._sessions[session_id] = session
            self._cleanup_old_sessions()
        
        return session

    def get_session(self, session_id: str) -> Optional[InteractionSession]:
        """获取会话。"""
        with self._lock:
            return self._sessions.get(session_id)

    def update_session(self, session_id: str, **kwargs) -> bool:
        """更新会话。"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                for key, value in kwargs.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                return True
        return False

    def end_session(self, session_id: str) -> bool:
        """结束会话。"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.ended_at = time.time()
                return True
        return False

    def get_recent_sessions(self, limit: int = 10) -> List[InteractionSession]:
        """获取最近会话。"""
        with self._lock:
            sorted_sessions = sorted(
                self._sessions.values(),
                key=lambda s: s.started_at,
                reverse=True
            )
            return sorted_sessions[:limit]

    def _cleanup_old_sessions(self):
        """清理旧会话。"""
        if len(self._sessions) > self._max_sessions:
            sorted_ids = sorted(
                self._sessions.keys(),
                key=lambda k: self._sessions[k].started_at
            )
            for sid in sorted_ids[:len(self._sessions) - self._max_sessions]:
                del self._sessions[sid]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息。"""
        with self._lock:
            active = sum(1 for s in self._sessions.values() if s.ended_at is None)
            completed = sum(1 for s in self._sessions.values() if s.ended_at is not None)
            
            return {
                "total_sessions": len(self._sessions),
                "active_sessions": active,
                "completed_sessions": completed,
                "max_sessions": self._max_sessions
            }


# 全局上下文管理器
_ctx = InteractionContext()


def get_context() -> InteractionContext:
    """获取全局上下文管理器。"""
    return _ctx