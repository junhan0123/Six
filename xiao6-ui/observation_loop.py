#!/usr/bin/env python3
"""Observation Loop — 主动智能观察层。

职责：
- 从多个来源收集观察数据
- 只读操作
- 生成结构化观察记录

约束：
- 不修改 AgentRuntime
- 不创建第二执行入口
- 不自动调用工具
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import List, Dict, Any, Optional


def collect_observations() -> List[Dict[str, Any]]:
    """
    收集系统观察数据。
    
    来源：
    - Memory Intelligence
    - Knowledge Intelligence
    - World Model
    - Goals
    - Tasks
    
    返回：
    [
        {
            "type": str,
            "source": str,
            "importance": float,
            "timestamp": float,
            "detail": str
        },
        ...
    ]
    """
    observations = []
    now = time.time()
    
    # 1. Memory Intelligence
    try:
        import memory_intelligence as mi
        status = mi.get_status()
        total = status.get("total", 0)
        avg_imp = status.get("average_importance", 0)
        categories = status.get("categories", {})
        
        if total > 0:
            observations.append({
                "type": "memory_activity",
                "source": "memory_intelligence",
                "importance": min(1.0, avg_imp / 10.0),
                "timestamp": now,
                "detail": f"Memory: {total} records, avg importance {avg_imp:.2f}"
            })
            
            # 检查是否有高重要性记忆
            for cat, count in categories.items():
                if count > 5:
                    observations.append({
                        "type": "memory_concentration",
                        "source": "memory_intelligence",
                        "importance": 0.6,
                        "timestamp": now,
                        "detail": f"High concentration in {cat}: {count} records"
                    })
    except Exception:
        pass
    
    # 2. Knowledge Intelligence
    try:
        import knowledge_intelligence as ki
        status = ki.get_status()
        total_docs = status.get("total_documents", 0)
        quality = status.get("quality_score", 0)
        
        if total_docs > 0:
            observations.append({
                "type": "knowledge_activity",
                "source": "knowledge_intelligence",
                "importance": min(1.0, quality / 10.0),
                "timestamp": now,
                "detail": f"Knowledge: {total_docs} docs, quality score {quality:.2f}"
            })
    except Exception:
        pass
    
    # 3. World Model
    try:
        import gfe_intelligence as gi
        status = gi.status()
        total_events = status.get("total_events", 0)
        risk_level = status.get("risk_level", "unknown")
        overall_severity = status.get("overall_severity", 0)
        
        if total_events > 0:
            obs_importance = overall_severity
            observations.append({
                "type": "world_event",
                "source": "world_model",
                "importance": obs_importance,
                "timestamp": now,
                "detail": f"World: {total_events} events, risk level {risk_level}, severity {overall_severity:.2f}"
            })
    except Exception:
        pass
    
    # 4. Goals
    try:
        from db import db_conn
        conn = db_conn()
        total_goals = conn.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
        active_goals = conn.execute(
            "SELECT COUNT(*) FROM goals WHERE status='active'"
        ).fetchone()[0]
        stalled = conn.execute(
            "SELECT COUNT(*) FROM goals WHERE status='active' AND progress < 10"
        ).fetchone()[0]
        conn.close()
        
        if total_goals > 0:
            observations.append({
                "type": "goal_activity",
                "source": "goals",
                "importance": 0.7 if stalled > 0 else 0.5,
                "timestamp": now,
                "detail": f"Goals: {active_goals}/{total_goals} active, {stalled} potentially stalled"
            })
    except Exception:
        pass
    
    # 5. Tasks
    try:
        from db import db_conn
        conn = db_conn()
        total_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        open_tasks = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='open'"
        ).fetchone()[0]
        conn.close()
        
        if total_tasks > 0:
            observations.append({
                "type": "task_activity",
                "source": "tasks",
                "importance": 0.6 if open_tasks > 5 else 0.4,
                "timestamp": now,
                "detail": f"Tasks: {open_tasks}/{total_tasks} open"
            })
    except Exception:
        pass
    
    return observations


def get_observation_count() -> int:
    """返回当前观察数量。"""
    return len(collect_observations())