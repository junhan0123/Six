#!/usr/bin/env python3
"""GFE Intelligence — GFE 智能聚合层。

职责：
- 读取已有 GFE 数据
- 分析世界状态
- 返回分析结果

约束：
- 不修改现有 gfe 模块
- 不创建新数据库
- 只读操作
- 不实现预测
- 不实现自动决策
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List


def status() -> Dict[str, Any]:
    """获取 GFE Intelligence 状态摘要。

    返回：
    {
        total_events: int,
        risk_level: str,
        overall_severity: float,
        entity_counts: dict,
        generated_at: str
    }
    """
    try:
        from world_model import analyze_world_state, get_entities

        world_state = analyze_world_state()
        entities = get_entities()

        return {
            "total_events": entities["counts"]["events"],
            "total_nations": entities["counts"]["nations"],
            "risk_level": world_state.get("risk_level", "unknown"),
            "overall_severity": world_state.get("overall_severity", 0.5),
            "entity_counts": entities["counts"],
            "trending_categories": world_state.get("trending_categories", []),
            "analysis_summary": world_state.get("analysis", {}),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    except Exception as e:
        return {
            "error": str(e),
            "total_events": 0,
            "total_nations": 0,
            "risk_level": "error",
            "overall_severity": 0.0,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


def analyze(dry_run: bool = True) -> Dict[str, Any]:
    """执行 GFE 分析（dry-run 模式，禁止修改数据库）。

    返回：
    {
        mode: "dry_run",
        events_analyzed: int,
        world_state: dict,
        entity_analysis: dict,
        suggestions: list
    }
    """
    try:
        from world_model import get_entities, get_events, analyze_world_state
        from gfe_events import get_event_intelligence_engine

        engine = get_event_intelligence_engine()
        gfe_events = engine.get_events(limit=100)

        # 分析世界状态
        world_state = analyze_world_state()

        # 获取实体
        entities = get_entities()

        # 获取事件关系
        events_data = get_events()

        # 生成建议（仅基于规则，无 ML）
        suggestions = []

        # 高风险事件建议
        for evt in gfe_events:
            evt_dict = evt.to_frontend() if hasattr(evt, 'to_frontend') else evt
            if evt_dict.get("severity", 0.5) >= 0.8:
                suggestions.append({
                    "type": "high_severity_event",
                    "event_id": evt_dict.get("event_id"),
                    "title": evt_dict.get("title", ""),
                    "severity": evt_dict.get("severity"),
                    "action": "review",
                    "reason": f"高严重程度事件 ({evt_dict.get('severity'):.2f})",
                })

        # 国家集中度建议
        countries = {}
        for evt in gfe_events:
            evt_dict = evt.to_frontend() if hasattr(evt, 'to_frontend') else evt
            cc = evt_dict.get("country_code")
            if cc:
                countries[cc] = countries.get(cc, 0) + 1

        for cc, count in sorted(countries.items(), key=lambda x: x[1], reverse=True)[:3]:
            if count >= 5:
                suggestions.append({
                    "type": "country_concentration",
                    "country_code": cc,
                    "event_count": count,
                    "action": "monitor",
                    "reason": f"该国事件密集 ({count} 条)",
                })

        return {
            "mode": "dry_run" if dry_run else "live",
            "events_analyzed": len(gfe_events),
            "world_state": {
                "risk_level": world_state.get("risk_level"),
                "overall_severity": world_state.get("overall_severity"),
                "trending_categories": world_state.get("trending_categories"),
            },
            "entity_analysis": {
                "total_entities": entities["counts"]["total"],
                "by_type": {k: v for k, v in entities["counts"].items() if k != "total"},
            },
            "event_relations": {
                "total_relations": events_data.get("statistics", {}).get("total_relations", 0),
                "by_type": _count_relation_types(events_data.get("relations", [])),
            },
            "suggestions": suggestions[:10],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    except Exception as e:
        return {
            "error": str(e),
            "mode": "dry_run",
            "events_analyzed": 0,
            "suggestions": [],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


def _count_relation_types(relations: List[Dict]) -> Dict[str, int]:
    """统计关系类型分布。"""
    counts = {}
    for r in relations:
        rtype = r.get("relation_type", "unknown")
        counts[rtype] = counts.get(rtype, 0) + 1
    return counts
