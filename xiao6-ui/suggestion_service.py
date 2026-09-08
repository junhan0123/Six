#!/usr/bin/env python3
"""PHASE 130 — Proactive Suggestion Layer

基于 Observation，生成用户可见的建议。
只读建议，不自动执行。

数据流：
Observation → SuggestionEngine → SuggestionQueue → User

设计原则：
1. 纯函数规则：Observation 字段 → Suggestion 字段
2. 幂等去重：同 observation_id 只允许一个 active suggestion
3. 持久化存储：SQLite 保存，重启不丢失
4. Human in the Loop：用户接受/拒绝后才标记状态
"""

from __future__ import annotations

import sqlite3
import time
import threading
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime

# ============================================================
# Constants
# ============================================================

SUGGESTION_TYPE_TASK_STALE = "TASK_STALE"
SUGGESTION_TYPE_TASK_FAILED = "TASK_FAILED"
SUGGESTION_TYPE_GOAL_STUCK = "GOAL_STUCK"
SUGGESTION_TYPE_GOAL_COMPLETED = "GOAL_COMPLETED"

PRIORITY_HIGH = 1
PRIORITY_MEDIUM = 5
PRIORITY_LOW = 10

STATUS_PENDING = "pending"
STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"
STATUS_EXPIRED = "expired"

# Import health status constants from observation_service
try:
    from observation_service import HEALTH_GOOD, HEALTH_WARNING, HEALTH_STALE, HEALTH_FAILED
except ImportError:
    HEALTH_GOOD = "GOOD"
    HEALTH_WARNING = "WARNING"
    HEALTH_STALE = "STALE"
    HEALTH_FAILED = "FAILED"


# ============================================================
# Suggestion Data Model
# ============================================================

@dataclass
class Suggestion:
    """建议记录。"""
    id: str
    observation_id: str
    type: str              # TASK_STALE / TASK_FAILED / GOAL_STUCK
    title: str
    description: str
    priority: int          # 1 (high) / 5 (medium) / 10 (low)
    status: str            # pending / accepted / rejected / expired
    created_at: float
    accepted_at: Optional[float] = None
    rejected_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_frontend(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "observation_id": self.observation_id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at,
            "accepted_at": self.accepted_at,
            "rejected_at": self.rejected_at
        }


# ============================================================
# Suggestion Generator Rules
# ============================================================

class SuggestionGenerator:
    """根据 Observation 生成建议（纯函数规则）。"""
    
    # 规则映射表
    RULES = [
        {
            "health": HEALTH_STALE,
            "type": SUGGESTION_TYPE_TASK_STALE,
            "title": "任务可能停滞",
            "description": "任务超过72小时无进度更新，建议检查执行状态。",
            "priority": PRIORITY_MEDIUM
        },
        {
            "health": HEALTH_WARNING,
            "type": SUGGESTION_TYPE_TASK_STALE,
            "title": "任务进度可能缓慢",
            "description": "任务24小时无进度更新，建议关注执行状态。",
            "priority": PRIORITY_LOW
        },
        {
            "health": HEALTH_FAILED,
            "type": SUGGESTION_TYPE_TASK_FAILED,
            "title": "任务执行失败",
            "description": "任务执行失败，建议检查失败原因并重新执行。",
            "priority": PRIORITY_HIGH
        },
        {
            "risk": "high",
            "type": SUGGESTION_TYPE_TASK_FAILED,
            "title": "高风险任务",
            "description": "检测到高风险信号，建议立即检查。",
            "priority": PRIORITY_HIGH
        },
        {
            "risk": "medium",
            "type": SUGGESTION_TYPE_TASK_STALE,
            "title": "任务需要关注",
            "description": "任务存在中等风险，建议定期检查进度。",
            "priority": PRIORITY_MEDIUM
        }
    ]
    
    @classmethod
    def generate(cls, observation: Dict[str, Any]) -> Optional[Suggestion]:
        """
        根据 Observation 生成建议。
        
        Returns:
            Suggestion 或 None（无匹配规则）
        """
        if not observation:
            return None
        
        health_status = observation.get("health", {}).get("status")
        risk_level = observation.get("risk", {}).get("level")
        
        # 查找匹配规则（按顺序匹配）
        for rule in cls.RULES:
            matched = True
            
            # 检查 health 条件
            if "health" in rule:
                if health_status != rule["health"]:
                    matched = False
            
            # 检查 risk 条件
            if "risk" in rule:
                if risk_level != rule["risk"]:
                    matched = False
            
            if matched:
                # 生成建议
                return Suggestion(
                    id=f"sug_{int(time.time() * 1000)}",
                    observation_id=observation.get("id", ""),
                    type=rule["type"],
                    title=rule["title"],
                    description=rule["description"],
                    priority=rule["priority"],
                    status=STATUS_PENDING,
                    created_at=time.time()
                )
        
        return None


# ============================================================
# Suggestion Storage
# ============================================================

class SuggestionStore:
    """建议持久化存储（SQLite）。"""
    
    def __init__(self, db_conn_func):
        self._conn = db_conn_func
    
    def save(self, suggestion: Suggestion) -> bool:
        """保存建议，去重。"""
        try:
            conn = self._conn()
            conn.execute("""
                INSERT OR IGNORE INTO suggestions
                (observation_id, type, title, description, priority, status, created)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                suggestion.observation_id,
                suggestion.type,
                suggestion.title,
                suggestion.description,
                suggestion.priority,
                suggestion.status,
                datetime.fromtimestamp(suggestion.created_at).isoformat()
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"[SuggestionStore] 保存建议失败: {e}")
            return False
    
    def get_pending(self, limit: int = 20) -> List[Dict]:
        """获取待处理的建议。"""
        try:
            conn = self._conn()
            rows = conn.execute("""
                SELECT id, observation_id, type, title, description,
                       priority, status, created, accepted_at, rejected_at
                FROM suggestions
                WHERE status = ?
                ORDER BY priority ASC, created DESC
                LIMIT ?
            """, (STATUS_PENDING, limit)).fetchall()

            return [self._row_to_dict(row) for row in rows]
        except Exception as e:
            print(f"[SuggestionStore] 获取建议失败: {e}")
            return []
    
    def accept(self, suggestion_id: str) -> bool:
        """用户接受建议。"""
        try:
            conn = self._conn()
            conn.execute("""
                UPDATE suggestions 
                SET status = ?, accepted_at = ?
                WHERE id = ? AND status = ?
            """, (
                STATUS_ACCEPTED,
                datetime.now().isoformat(),
                suggestion_id,
                STATUS_PENDING
            ))
            conn.commit()
            return conn_changes(conn) > 0
        except Exception as e:
            print(f"[SuggestionStore] 接受建议失败: {e}")
            return False
    
    def reject(self, suggestion_id: str) -> bool:
        """用户拒绝建议。"""
        try:
            conn = self._conn()
            conn.execute("""
                UPDATE suggestions 
                SET status = ?, rejected_at = ?
                WHERE id = ? AND status = ?
            """, (
                STATUS_REJECTED,
                datetime.now().isoformat(),
                suggestion_id,
                STATUS_PENDING
            ))
            conn.commit()
            return conn_changes(conn) > 0
        except Exception as e:
            print(f"[SuggestionStore] 拒绝建议失败: {e}")
            return False
    
    def _row_to_dict(self, row) -> Dict:
        """数据库行转字典。"""
        return {
            "id": row[0],
            "observation_id": row[1],
            "type": row[2],
            "title": row[3],
            "description": row[4],
            "priority": row[5],
            "status": row[6],
            "created_at": self._parse_ts(row[7]),
            "accepted_at": self._parse_ts(row[8]),
            "rejected_at": self._parse_ts(row[9])
        }
    
    @staticmethod
    def _parse_ts(ts_str: Optional[str]) -> Optional[float]:
        """解析时间戳。"""
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str).timestamp()
        except (ValueError, TypeError):
            return None


def conn_changes(conn) -> int:
    """获取最近修改的行数。"""
    try:
        return conn.total_changes
    except AttributeError:
        return 0


# ============================================================
# Suggestion Service
# ============================================================

class SuggestionService:
    """建议服务：监听 Observation，生成并存储建议。"""
    
    def __init__(self, db_conn_func, observation_service=None):
        self._db = SuggestionStore(db_conn_func)
        self._obs_svc = observation_service
        self._lock = threading.Lock()
        self._stats = {
            "generated": 0,
            "duplicates_skipped": 0,
            "errors": 0
        }
    
    def process_observation(self, observation: Dict) -> Optional[Suggestion]:
        """
        处理单条 Observation，生成建议。
        
        Returns:
            新生成的 Suggestion，或 None（已存在或无匹配）
        """
        if not observation:
            return None
        
        # 生成建议
        suggestion = SuggestionGenerator.generate(observation)
        if not suggestion:
            return None
        
        # 检查是否已存在（幂等去重）
        existing = self._db.get_pending()
        for existing_sug in existing:
            if existing_sug["observation_id"] == observation.get("id"):
                self._stats["duplicates_skipped"] += 1
                return None
        
        # 保存
        if self._db.save(suggestion):
            self._stats["generated"] += 1
            return suggestion
        else:
            self._stats["errors"] += 1
            return None
    
    def get_pending(self, limit: int = 20) -> List[Dict]:
        """获取待处理建议。"""
        return self._db.get_pending(limit)
    
    def accept(self, suggestion_id: str) -> bool:
        """用户接受建议。"""
        return self._db.accept(suggestion_id)
    
    def reject(self, suggestion_id: str) -> bool:
        """用户拒绝建议。"""
        return self._db.reject(suggestion_id)
    
    def get_stats(self) -> Dict:
        """获取服务统计。"""
        return {
            **self._stats,
            "pending_count": len(self._db.get_pending())
        }


# ============================================================
# 全局单例
# ============================================================

_instance: Optional[SuggestionService] = None
_instance_lock = threading.Lock()


def get_suggestion_service(db_conn_func=None):
    """获取全局 Suggestion Service 单例。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            from db import db_conn as default_conn
            _instance = SuggestionService(db_conn_func or default_conn)
        return _instance


def init_suggestion_service():
    """初始化并返回 Suggestion Service。"""
    return get_suggestion_service()


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    print("=== PHASE 130 Suggestion Layer Tests ===\n")
    
    # Test 1: STALE task → Suggestion
    print("Test 1: STALE task generates suggestion")
    stale_obs = {
        "id": "obs_stale_001",
        "health": {"status": "STALE", "reason": "任务超过72小时没有进度更新"},
        "risk": {"level": "medium", "signal": "任务长时间无更新"}
    }
    sug = SuggestionGenerator.generate(stale_obs)
    assert sug is not None
    assert sug.type == SUGGESTION_TYPE_TASK_STALE
    assert sug.priority == PRIORITY_MEDIUM
    print(f"  PASS: type={sug.type}, priority={sug.priority}")
    
    # Test 2: FAILED task → Suggestion
    print("\nTest 2: FAILED task generates suggestion")
    failed_obs = {
        "id": "obs_failed_001",
        "health": {"status": "FAILED", "reason": "任务失败需要处理"},
        "risk": {"level": "high", "signal": "任务失败：Connection timeout"}
    }
    sug = SuggestionGenerator.generate(failed_obs)
    assert sug is not None
    assert sug.type == SUGGESTION_TYPE_TASK_FAILED
    assert sug.priority == PRIORITY_HIGH
    print(f"  PASS: type={sug.type}, priority={sug.priority}")
    
    # Test 3: GOOD task → No suggestion
    print("\nTest 3: GOOD task no suggestion")
    good_obs = {
        "id": "obs_good_001",
        "health": {"status": "GOOD", "reason": "任务正常完成"},
        "risk": {"level": "none", "signal": ""}
    }
    sug = SuggestionGenerator.generate(good_obs)
    assert sug is None
    print("  PASS: no suggestion generated")
    
    # Test 4: Duplicate detection
    print("\nTest 4: Duplicate detection")
    from db import db_conn
    store = SuggestionStore(db_conn)
    
    # Save the stale suggestion
    if sug:
        store.save(sug)
    
    # Try to generate and save same observation again
    sug2 = SuggestionGenerator.generate(stale_obs)
    store.save(sug2)  # Should be ignored due to INSERT OR IGNORE
    
    # Check pending suggestions
    existing = store.get_pending()
    stale_count = sum(1 for s in existing if s["observation_id"] == stale_obs["id"])
    assert stale_count == 1, f"Expected 1, got {stale_count}"
    print(f"  PASS: duplicate correctly detected (count={stale_count})")
    
    # Test 5: Service integration
    print("\nTest 5: Service integration")
    svc = SuggestionService(db_conn)
    obs = svc.get_pending()
    assert isinstance(obs, list)
    print(f"  PASS: service works, pending count={len(obs)}")
    
    print("\n=== All Tests Complete ===")
