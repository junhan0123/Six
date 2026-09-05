#!/usr/bin/env python3
"""Memory Consolidation Engine — 只支持 dry_run，禁止自动迁移。

职责：
- 分析可 Consolidation 的记忆候选
- 生成建议摘要
- 输出迁移建议

约束：
- 禁止自动迁移
- 禁止修改数据库
- 只输出分析结果
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from db import db_conn
from memory_scoring import classify_memory, calculate_importance


class ConsolidationEngine:
    """记忆巩固引擎（只读分析）。"""

    def __init__(self):
        self.thresholds = {
            "consolidate_age_days": 7,      # 超过7天的活跃记忆可考虑巩固
            "min_importance_for_consolidate": 3.0,
            "max_group_size": 10,           # 每组最多10条
        }

    def dry_run(self) -> dict:
        """执行 dry-run 分析。

        返回：
        {
          "mode": "dry_run",
          "candidate_count": int,
          "candidates": list,
          "suggested_summaries": list,
          "migration_suggestions": list,
          "statistics": dict
        }
        """
        try:
            conn = db_conn()
            rows = conn.execute(
                "SELECT id, event_type, content, title, detail, mem_id, "
                "entities, concepts, tags, links, salience, source_ref, "
                "timestamp, visibility, content_hash, confidence, source, status "
                "FROM memories WHERE visibility=1 AND status='active' "
                "ORDER BY timestamp ASC"
            ).fetchall()
            conn.close()

            now = datetime.now()
            candidates = []
            groups = {}

            for r in rows:
                mem = {
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
                }

                # 计算重要性和分类
                imp_result = calculate_importance(mem)
                importance = imp_result["importance"]
                category = imp_result["category"]
                age_days = imp_result["age_days"]

                # 过滤：只考虑活跃且超过7天的记忆
                if age_days < self.thresholds["consolidate_age_days"]:
                    continue
                if importance < self.thresholds["min_importance_for_consolidate"]:
                    continue
                if category in ("CORE", "ARCHIVE"):
                    continue

                # 按主题分组（简化：使用 event_type）
                group_key = mem.get("event_type") or "note"
                if group_key not in groups:
                    groups[group_key] = []
                if len(groups[group_key]) < self.thresholds["max_group_size"]:
                    groups[group_key].append({
                        "id": mem["id"],
                        "title": mem.get("title") or mem.get("content", "")[:50],
                        "importance": importance,
                        "age_days": age_days,
                        "content_preview": (mem.get("content") or "")[:100],
                    })

                candidates.append({
                    "id": mem["id"],
                    "importance": importance,
                    "age_days": age_days,
                    "category": category,
                    "event_type": group_key,
                })

            # 生成建议摘要
            suggested_summaries = []
            for group_key, items in groups.items():
                if len(items) >= 2:
                    suggested_summaries.append({
                        "group_key": group_key,
                        "count": len(items),
                        "items": items[:5],  # 最多5条预览
                        "suggestion": f"建议将 {group_key} 类 {len(items)} 条记忆整合为摘要",
                    })

            # 迁移建议
            migration_suggestions = []
            for group_key, items in groups.items():
                total_importance = sum(i["importance"] for i in items)
                avg_importance = total_importance / len(items) if items else 0
                migration_suggestions.append({
                    "from_group": group_key,
                    "item_count": len(items),
                    "avg_importance": round(avg_importance, 2),
                    "action": "consolidate_to_knowledge",
                    "reason": f"该组记忆重要性均匀（平均 {avg_importance:.2f}），建议整合",
                })

            # 统计
            statistics = {
                "total_active": len(rows),
                "consolidation_candidates": len(candidates),
                "groups_identified": len(groups),
                "avg_age_days": round(sum(c["age_days"] for c in candidates) / len(candidates), 1) if candidates else 0,
                "avg_importance": round(sum(c["importance"] for c in candidates) / len(candidates), 2) if candidates else 0,
            }

            return {
                "mode": "dry_run",
                "candidate_count": len(candidates),
                "candidates": candidates[:30],
                "suggested_summaries": suggested_summaries,
                "migration_suggestions": migration_suggestions,
                "statistics": statistics,
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "warning": "此操作为只读分析，不会修改任何数据",
            }

        except Exception as e:
            return {
                "error": str(e),
                "mode": "dry_run",
                "candidate_count": 0,
                "candidates": [],
                "suggested_summaries": [],
                "migration_suggestions": [],
                "statistics": {},
            }


# 单例实例
_consolidation_engine = None


def get_consolidation_engine() -> ConsolidationEngine:
    global _consolidation_engine
    if _consolidation_engine is None:
        _consolidation_engine = ConsolidationEngine()
    return _consolidation_engine
