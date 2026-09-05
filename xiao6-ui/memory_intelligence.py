#!/usr/bin/env python3
"""Memory Intelligence — 只读聚合层。

职责：
- 读取已有 memory 数据
- 计算重要性评分
- 返回分析结果

约束：
- 禁止写入数据库
- 禁止修改现有 memory.py
- 只读操作
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from db import db_conn
from memory_scoring import get_statistics, analyze_memories


def get_intelligence_status() -> dict:
    """获取 Intelligence 状态摘要。

    返回：
    {
      "total": int,
      "categories": dict,
      "average_importance": float,
      "decay_statistics": dict
    }
    """
    try:
        conn = db_conn()
        rows = conn.execute(
            "SELECT id, event_type, content, title, detail, mem_id, "
            "entities, concepts, tags, links, salience, source_ref, "
            "timestamp, visibility, content_hash, confidence, source, status "
            "FROM memories WHERE visibility=1 ORDER BY id DESC LIMIT 500"
        ).fetchall()
        conn.close()

        memories = []
        for r in rows:
            memories.append({
                "id": r[0],
                "event_type": r[1],
                "content": r[2],
                "title": r[3],
                "detail": r[4],
                "mem_id": r[5],
                "entities": r[6],
                "concepts": r[7],
                "tags": r[8],
                "links": r[9],
                "salience": r[10],
                "source_ref": r[11],
                "timestamp": r[12],
                "visibility": r[13],
                "content_hash": r[14],
                "confidence": r[15],
                "source": r[16],
                "status": r[17],
            })

        stats = get_statistics(memories)

        # 衰减统计
        decay_stats = {
            "model": "exponential",
            "formula": "I(t) = I(0) × e^(-λt)",
            "rates": {
                "CORE": 0.001,
                "ACTIVE": 0.1,
                "CONTEXT": 0.05,
                "TRANSIENT": 1.0,
                "ARCHIVE": 0.0001,
            },
            "decaying_count": stats.get("decaying_count", 0),
        }

        return {
            "total": stats["total"],
            "categories": stats["categories"],
            "average_importance": stats["average_importance"],
            "decay_statistics": decay_stats,
            "scoring_model": stats["scoring_model"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    except Exception as e:
        return {
            "error": str(e),
            "total": 0,
            "categories": {},
            "average_importance": 0,
            "decay_statistics": {},
        }


def analyze_intelligence(dry_run: bool = True) -> dict:
    """执行分析（dry-run 模式，禁止修改数据库）。

    返回：
    {
      "mode": "dry_run",
      "total_analyzed": int,
      "candidates": list,  # 需要关注的记忆
      "suggestions": list  # 建议操作
    }
    """
    try:
        conn = db_conn()
        rows = conn.execute(
            "SELECT id, event_type, content, title, detail, mem_id, "
            "entities, concepts, tags, links, salience, source_ref, "
            "timestamp, visibility, content_hash, confidence, source, status "
            "FROM memories WHERE visibility=1 ORDER BY id ASC"
        ).fetchall()
        conn.close()

        memories = []
        for r in rows:
            memories.append({
                "id": r[0],
                "event_type": r[1],
                "content": r[2],
                "title": r[3],
                "detail": r[4],
                "mem_id": r[5],
                "entities": r[6],
                "concepts": r[7],
                "tags": r[8],
                "links": r[9],
                "salience": r[10],
                "source_ref": r[11],
                "timestamp": r[12],
                "visibility": r[13],
                "content_hash": r[14],
                "confidence": r[15],
                "source": r[16],
                "status": r[17],
            })

        analysis = analyze_memories(memories)

        # 提取需要关注的候选
        candidates = []
        suggestions = []

        for r in analysis["results"]:
            # 高重要性 → 推荐保留
            if r.get("importance", 0) >= 7:
                candidates.append({
                    "id": r["memory_id"],
                    "type": "high_importance",
                    "reason": f"重要性 {r['importance']:.2f}，建议保留为 CORE",
                    "category": r.get("category"),
                })
            # 衰减中 → 建议检查
            if r.get("status") == "decaying":
                candidates.append({
                    "id": r["memory_id"],
                    "type": "decaying",
                    "reason": f"重要性衰减至 {r.get('current_importance', 0):.2f}",
                    "category": r.get("category"),
                })
            # 可考虑归档
            if r.get("category") == "TRANSIENT" and r.get("age_days", 0) > 30:
                suggestions.append({
                    "action": "archive",
                    "id": r["memory_id"],
                    "reason": f"临时记忆，已 {r['age_days']:.0f} 天，可归档",
                })

        return {
            "mode": "dry_run" if dry_run else "live",
            "total_analyzed": len(analysis["results"]),
            "categories": analysis["categories"],
            "average_importance": analysis["average_importance"],
            "candidates": candidates[:20],  # 最多20条
            "suggestions": suggestions[:10],  # 最多10条
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    except Exception as e:
        return {
            "error": str(e),
            "mode": "dry_run",
            "total_analyzed": 0,
            "candidates": [],
            "suggestions": [],
        }
