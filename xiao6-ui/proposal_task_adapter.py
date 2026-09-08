#!/usr/bin/env python3
"""PHASE 132 — Proposal Task Adapter

将 Approved Proposal 转换为 Task（只创建，不执行）。

流程：
Proposal (approved)
    ↓
Validate
    ↓
Create Task (pending)
    ↓
Return Task ID
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

from db import db_conn as get_db_conn
from proposal_validator import ProposalValidator


# ============================================================
# Task 数据结构
# ============================================================

@dataclass
class TaskSpec:
    """任务规格。"""
    id: str
    title: str
    description: str
    status: str = "pending"
    steps: List[Dict] = None
    estimated_cost: float = 0.0
    risk: str = "low"
    source: str = "proposal"
    proposal_id: str = ""
    created_at: float = 0.0


# ============================================================
# Task Creation Adapter
# ============================================================

class ProposalTaskAdapter:
    """提案 → 任务适配器。"""

    def __init__(self, db_conn_func=None, validator=None):
        self._conn = db_conn_func or get_db_conn
        self._validator = validator or ProposalValidator()

    def create_task(self, proposal: Dict[str, Any]) -> Optional[Dict]:
        """
        创建任务。
        
        Args:
            proposal: 已批准的提案
            
        Returns:
            创建的任务字典或 None
        """
        # 1. 验证提案
        result = self._validator.validate(proposal)
        if not result.valid:
            print(f"[TaskAdapter] 验证失败: {result.errors}")
            return None
        
        # 2. 构建任务规格
        task_spec = self._build_task_spec(proposal, result)
        
        # 3. 存入数据库
        task_id = self._save_task(task_spec)
        if not task_id:
            return None
        
        # 4. 更新提案状态
        self._update_proposal_status(proposal.get("id"), "created", task_id)
        
        return {
            "id": task_id,
            "title": task_spec.title,
            "status": task_spec.status,
            "proposal_id": proposal.get("id"),
            "created_at": task_spec.created_at
        }

    def _build_task_spec(self, proposal: Dict, validation: Any) -> TaskSpec:
        """从提案构建任务规格。"""
        return TaskSpec(
            id=str(uuid.uuid4()),
            title=proposal.get("title", "未命名任务"),
            description="",  # tasks表无此列
            status="pending",
            steps=proposal.get("steps", []),
            estimated_cost=proposal.get("estimated_cost", 0.0),
            risk=validation.risk_level,
            source="proposal",
            proposal_id=proposal.get("id", ""),
            created_at=datetime.now().timestamp()
        )

    def _save_task(self, spec: TaskSpec) -> Optional[str]:
        """保存任务到数据库。"""
        try:
            conn = self._conn()
            now = datetime.fromtimestamp(spec.created_at).isoformat()
            cur = conn.execute("""
                INSERT INTO tasks (title, steps, current_step, total_steps, status, step, note, goal_id, created, updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                spec.title,
                "",  # steps (TEXT，暂不存储)
                0,  # current_step
                0,  # total_steps
                spec.status,
                "",  # step
                spec.description,
                None,  # goal_id
                now,
                now
            ))
            task_id = str(cur.lastrowid)
            conn.commit()
            return task_id
        except Exception as e:
            print(f"[TaskAdapter] 保存任务失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _update_proposal_status(
        self, 
        proposal_id: str, 
        new_status: str, 
        task_id: Optional[str] = None
    ) -> bool:
        """更新提案状态。"""
        try:
            conn = self._conn()
            if task_id:
                conn.execute("""
                    UPDATE task_proposals
                    SET status = ?, task_id = ?, approved_at = ?
                    WHERE id = ?
                """, (new_status, task_id, datetime.now().isoformat(), proposal_id))
            else:
                conn.execute("""
                    UPDATE task_proposals
                    SET status = ?, approved_at = ?
                    WHERE id = ?
                """, (new_status, datetime.now().isoformat(), proposal_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"[TaskAdapter] 更新提案状态失败: {e}")
            return False


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=== PHASE 132 Proposal Task Adapter Tests ===\n")
    
    adapter = ProposalTaskAdapter()
    
    # Test 1: 创建正常任务
    print("Test 1: Create task from valid proposal")
    valid_proposal = {
        "id": "prop-test-1",
        "title": "恢复停滞任务",
        "description": "检查任务状态并重新执行",
        "steps": [
            {"title": "检查状态", "action": "GET /api/tasks"},
            {"title": "修复问题", "action": "POST /api/tasks/{id}/fix"}
        ],
        "risk": "medium",
        "estimated_cost": 100
    }
    result = adapter.create_task(valid_proposal)
    assert result is not None
    assert result["status"] == "pending"
    assert result["proposal_id"] == "prop-test-1"
    print(f"  PASS: task_id={result['id']}, status={result['status']}")
    
    # Test 2: 无效提案
    print("\nTest 2: Reject invalid proposal")
    invalid_proposal = {
        "id": "prop-test-2",
        "title": ""
    }
    result = adapter.create_task(invalid_proposal)
    assert result is None
    print(f"  PASS: rejected invalid proposal")
    
    # Test 3: 验证任务创建成功
    print("\nTest 3: Verify task creation")
    from db import db_conn
    conn = db_conn()
    # 查询最近创建的任务
    row = conn.execute(
        "SELECT id, title, status FROM tasks WHERE title='恢复停滞任务' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert row is not None
    print(f"  PASS: task created id={row[0]}, status={row[2]}")
    
    print("\n=== All Tests Complete ===")
