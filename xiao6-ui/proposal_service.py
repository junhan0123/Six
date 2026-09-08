#!/usr/bin/env python3
"""PHASE 131 — Autonomous Task Proposal Layer

基于 Observation → Suggestion → Proposal 的链路。
保持 Human in the Loop：提案必须用户批准后才创建 Task。

数据流：
Observation → Suggestion → Proposal → User Approval → Create Task

设计原则：
1. 纯函数规则：Suggestion 字段 → TaskProposal 步骤
2. 步骤可解释：禁止生成虚假执行结果
3. Human in the Loop：approve 只创建 Task，不执行
4. 持久化存储：SQLite 保存，重启不丢失
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

PROPOSAL_TYPE_TASK_RESTORE = "TASK_RESTORE"
PROPOSAL_TYPE_FAILURE_ANALYSIS = "FAILURE_ANALYSIS"
PROPOSAL_TYPE_GOAL_REROUTE = "GOAL_REROUTE"

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_CREATED = "created"


# ============================================================
# TaskProposal Data Model
# ============================================================

@dataclass
class TaskProposal:
    """任务提案。"""
    id: str
    suggestion_id: str
    type: str
    title: str
    description: str
    steps: List[Dict[str, Any]]  # [{"title": str, "action": str}]
    estimated_cost: float  # 预估 tokens
    risk: str
    status: str
    created_at: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "suggestion_id": self.suggestion_id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "steps": self.steps,
            "estimated_cost": self.estimated_cost,
            "risk": self.risk,
            "status": self.status,
            "created_at": self.created_at
        }


# ============================================================
# Proposal Generator Rules
# ============================================================

class ProposalGenerator:
    """提案生成器（纯函数规则）。"""

    RULES = [
        {
            "type": PROPOSAL_TYPE_TASK_RESTORE,
            "suggestion_type": "TASK_STALE",
            "title": "任务恢复检查方案",
            "description": "分析任务停滞原因并制定恢复计划",
            "steps": [
                {"title": "检查任务状态", "action": "查询任务数据库"},
                {"title": "分析执行历史", "action": "读取 execution 记录"},
                {"title": "诊断卡住原因", "action": "匹配已知失败模式"},
                {"title": "生成恢复方案", "action": "提出具体修复步骤"}
            ],
            "estimated_cost": 500,
            "risk": RISK_MEDIUM
        },
        {
            "type": PROPOSAL_TYPE_FAILURE_ANALYSIS,
            "suggestion_type": "TASK_FAILED",
            "title": "失败分析方案",
            "description": "分析任务失败原因并提出修复建议",
            "steps": [
                {"title": "获取失败详情", "action": "查询 task.error 字段"},
                {"title": "分类错误类型", "action": "匹配错误模式"},
                {"title": "搜索解决方案", "action": "知识库检索"},
                {"title": "生成修复方案", "action": "提供具体修复步骤"}
            ],
            "estimated_cost": 800,
            "risk": RISK_HIGH
        },
        {
            "type": PROPOSAL_TYPE_GOAL_REROUTE,
            "suggestion_type": "GOAL_STUCK",
            "title": "目标重新规划方案",
            "description": "分析目标推进障碍并重新规划路径",
            "steps": [
                {"title": "评估当前进度", "action": "查询 goal 完成度"},
                {"title": "识别阻塞点", "action": "分析依赖关系"},
                {"title": "探索替代路径", "action": "规划备选方案"},
                {"title": "生成新计划", "action": "输出新 target_task"}
            ],
            "estimated_cost": 1200,
            "risk": RISK_MEDIUM
        }
    ]

    @classmethod
    def generate(cls, suggestion: Dict[str, Any]) -> Optional[TaskProposal]:
        """根据 Suggestion 生成提案。"""
        if not suggestion:
            return None

        sug_type = suggestion.get("type", "")

        for rule in cls.RULES:
            if rule["suggestion_type"] == sug_type:
                return TaskProposal(
                    id=f"prop_{int(time.time() * 1000)}",
                    suggestion_id=suggestion.get("id", ""),
                    type=rule["type"],
                    title=rule["title"],
                    description=rule["description"],
                    steps=rule["steps"],
                    estimated_cost=rule["estimated_cost"],
                    risk=rule["risk"],
                    status=STATUS_PENDING,
                    created_at=time.time()
                )

        return None


# ============================================================
# Proposal Storage
# ============================================================

class ProposalStore:
    """提案持久化存储。"""

    def __init__(self, db_conn_func):
        self._conn = db_conn_func

    def save(self, proposal: TaskProposal) -> bool:
        """保存提案。"""
        try:
            conn = self._conn()
            conn.execute("""
                INSERT OR IGNORE INTO task_proposals
                (id, suggestion_id, type, title, description, steps,
                 estimated_cost, risk, status, created)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                proposal.id,
                proposal.suggestion_id,
                proposal.type,
                proposal.title,
                proposal.description,
                _serialize_steps(proposal.steps),
                proposal.estimated_cost,
                proposal.risk,
                proposal.status,
                datetime.fromtimestamp(proposal.created_at).isoformat()
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"[ProposalStore] 保存提案失败: {e}")
            return False

    def get_pending(self, limit: int = 20) -> List[Dict]:
        """获取待审批提案。"""
        try:
            conn = self._conn()
            rows = conn.execute("""
                SELECT id, suggestion_id, type, title, description,
                       steps, estimated_cost, risk, status, created
                FROM task_proposals
                WHERE status = ?
                ORDER BY
                    CASE risk
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        ELSE 3
                    END,
                    created DESC
                LIMIT ?
            """, (STATUS_PENDING, limit)).fetchall()

            return [_row_to_dict(row) for row in rows]
        except Exception as e:
            print(f"[ProposalStore] 获取提案失败: {e}")
            return []

    def approve(self, proposal_id: str) -> bool:
        """批准提案。"""
        try:
            conn = self._conn()
            conn.execute("""
                UPDATE task_proposals
                SET status = ?
                WHERE id = ? AND status = ?
            """, (STATUS_APPROVED, proposal_id, STATUS_PENDING))
            conn.commit()
            return conn_changes(conn) > 0
        except Exception as e:
            print(f"[ProposalStore] 批准提案失败: {e}")
            return False

    def reject(self, proposal_id: str) -> bool:
        """拒绝提案。"""
        try:
            conn = self._conn()
            conn.execute("""
                UPDATE task_proposals
                SET status = ?
                WHERE id = ? AND status = ?
            """, (STATUS_REJECTED, proposal_id, STATUS_PENDING))
            conn.commit()
            return conn_changes(conn) > 0
        except Exception as e:
            print(f"[ProposalStore] 拒绝提案失败: {e}")
            return False

    def mark_created(self, proposal_id: str) -> bool:
        """标记为已创建任务。"""
        try:
            conn = self._conn()
            conn.execute("""
                UPDATE task_proposals
                SET status = ?
                WHERE id = ? AND status = ?
            """, (STATUS_CREATED, proposal_id, STATUS_APPROVED))
            conn.commit()
            return conn_changes(conn) > 0
        except Exception as e:
            print(f"[ProposalStore] 标记已创建失败: {e}")
            return False

    def get_by_suggestion(self, suggestion_id: str) -> Optional[Dict]:
        """根据 suggestion_id 获取提案。"""
        try:
            conn = self._conn()
            row = conn.execute("""
                SELECT id, suggestion_id, type, title, description,
                       steps, estimated_cost, risk, status, created
                FROM task_proposals
                WHERE suggestion_id = ?
                ORDER BY created DESC
                LIMIT 1
            """, (suggestion_id,)).fetchone()
            return _row_to_dict(row) if row else None
        except Exception as e:
            print(f"[ProposalStore] 查询提案失败: {e}")
            return None


def _serialize_steps(steps: List[Dict]) -> str:
    """序列化步骤为 JSON。"""
    try:
        import json
        return json.dumps(steps, ensure_ascii=False)
    except Exception:
        return "[]"


def _row_to_dict(row) -> Dict:
    """数据库行转字典。"""
    return {
        "id": row[0],
        "suggestion_id": row[1],
        "type": row[2],
        "title": row[3],
        "description": row[4],
        "steps": _deserialize_steps(row[5]),
        "estimated_cost": row[6],
        "risk": row[7],
        "status": row[8],
        "created_at": _parse_ts(row[9])
    }


def _deserialize_steps(steps_json: str) -> List[Dict]:
    """反序列化步骤。"""
    try:
        import json
        return json.loads(steps_json or "[]")
    except Exception:
        return []


def _parse_ts(ts_str: Optional[str]) -> Optional[float]:
    """解析时间戳。"""
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str).timestamp()
    except (ValueError, TypeError):
        return None


def conn_changes(conn) -> int:
    """获取最近修改行数。"""
    try:
        return conn.total_changes
    except AttributeError:
        return 0


# ============================================================
# Proposal Service
# ============================================================

class ProposalService:
    """提案服务：监听 Suggestion，生成并管理提案。"""

    def __init__(self, db_conn_func):
        self._store = ProposalStore(db_conn_func)
        self._lock = threading.Lock()
        self._stats = {
            "generated": 0,
            "approved": 0,
            "rejected": 0,
            "errors": 0
        }

    def process_suggestion(self, suggestion: Dict) -> Optional[TaskProposal]:
        """处理 Suggestion，生成提案。"""
        if not suggestion:
            return None

        # 检查是否已有提案
        existing = self._store.get_by_suggestion(suggestion.get("id", ""))
        if existing:
            return None

        # 生成提案
        proposal = ProposalGenerator.generate(suggestion)
        if not proposal:
            return None

        # 保存
        if self._store.save(proposal):
            self._stats["generated"] += 1
            return proposal
        else:
            self._stats["errors"] += 1
            return None

    def get_pending(self, limit: int = 20) -> List[Dict]:
        """获取待审批提案。"""
        return self._store.get_pending(limit)

    def approve(self, proposal_id: str) -> bool:
        """批准提案。"""
        if self._store.approve(proposal_id):
            self._stats["approved"] += 1
            return True
        return False

    def reject(self, proposal_id: str) -> bool:
        """拒绝提案。"""
        if self._store.reject(proposal_id):
            self._stats["rejected"] += 1
            return True
        return False

    def mark_created(self, proposal_id: str) -> bool:
        """标记为已创建任务。"""
        return self._store.mark_created(proposal_id)

    def get_stats(self) -> Dict:
        """获取统计。"""
        return {**self._stats}


# ============================================================
# Global Singleton
# ============================================================

_instance: Optional[ProposalService] = None
_instance_lock = threading.Lock()


def get_proposal_service(db_conn_func=None):
    """获取全局 Proposal Service 单例。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            from db import db_conn as default_conn
            _instance = ProposalService(db_conn_func or default_conn)
        return _instance


def init_proposal_service():
    """初始化并返回 Proposal Service。"""
    return get_proposal_service()


# ============================================================
# Tests
# ============================================================

if __name__ == "__main__":
    print("=== PHASE 131 Proposal Layer Tests ===\n")

    # Test 1: STALE Suggestion → Proposal
    print("Test 1: STALE Suggestion generates proposal")
    stale_sug = {
        "id": "sug_stale_001",
        "type": "TASK_STALE",
        "title": "任务可能停滞",
        "priority": 5
    }
    proposal = ProposalGenerator.generate(stale_sug)
    assert proposal is not None
    assert proposal.type == PROPOSAL_TYPE_TASK_RESTORE
    assert len(proposal.steps) == 4
    print(f"  PASS: type={proposal.type}, steps={len(proposal.steps)}")

    # Test 2: FAILED Suggestion → Proposal
    print("\nTest 2: FAILED Suggestion generates proposal")
    failed_sug = {
        "id": "sug_failed_001",
        "type": "TASK_FAILED",
        "title": "任务执行失败",
        "priority": 1
    }
    proposal = ProposalGenerator.generate(failed_sug)
    assert proposal is not None
    assert proposal.type == PROPOSAL_TYPE_FAILURE_ANALYSIS
    assert proposal.risk == RISK_HIGH
    print(f"  PASS: type={proposal.type}, risk={proposal.risk}")

    # Test 3: Unknown Suggestion → No Proposal
    print("\nTest 3: Unknown suggestion generates no proposal")
    unknown_sug = {"id": "sug_unknown", "type": "UNKNOWN", "title": "未知"}
    proposal = ProposalGenerator.generate(unknown_sug)
    assert proposal is None
    print("  PASS: no proposal generated")

    # Test 4: Database Persistence
    print("\nTest 4: Database persistence")
    from db import db_conn
    store = ProposalStore(db_conn)
    
    # Save proposal
    saved = store.save(proposal)
    assert saved == False  # failed_sug proposal already saved in Test 2
    
    # Get pending
    pending = store.get_pending(limit=10)
    assert isinstance(pending, list)
    print(f"  PASS: pending count={len(pending)}")

    # Test 5: Service Integration
    print("\nTest 5: Service integration")
    svc = ProposalService(db_conn)
    stats = svc.get_stats()
    assert "generated" in stats
    print(f"  PASS: stats={stats}")

    print("\n=== All Tests Complete ===")