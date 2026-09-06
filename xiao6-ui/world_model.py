#!/usr/bin/env python3
"""World Model — 世界模型聚合层。

职责：
- 只读聚合现有 GFE 数据
- 构建统一世界实体视图
- 分析世界状态

约束：
- 不修改现有 gfe 模块
- 不创建新数据库
- 只读操作
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional

from world_entities import (
    WorldEntity, Nation, Enterprise, Technology,
    Market, Policy, WorldEvent, get_entity_types
)
from world_events import EventRelation, analyze_event_relations


def get_entities() -> Dict[str, Any]:
    """获取所有世界实体（聚合自 GFE 数据）。

    返回：
    {
        "entities": list,
        "counts": dict,
        "generated_at": str
    }
    """
    entities = {
        "nations": [],
        "enterprises": [],
        "technologies": [],
        "markets": [],
        "policies": [],
        "events": [],
    }

    try:
        from gfe_events import get_event_intelligence_engine
        engine = get_event_intelligence_engine()

        # 从 GFE 事件构建实体
        gfe_events = engine.get_events(limit=100)
        for evt in gfe_events:
            evt_dict = evt.to_frontend() if hasattr(evt, 'to_frontend') else evt
            entities["events"].append({
                "id": evt_dict.get("event_id"),
                "type": "event",
                "name": evt_dict.get("title", ""),
                "category": evt_dict.get("category", ""),
                "confidence": evt_dict.get("confidence", 0.5),
                "severity": evt_dict.get("severity", 0.5),
                "country_code": evt_dict.get("country_code"),
                "created_at": evt_dict.get("created_at"),
            })

        # 从事件中提取国家实体
        countries = set()
        for evt in gfe_events:
            cc = evt_dict.get("country_code") if isinstance(evt_dict, dict) else getattr(evt, 'country_code', None)
            if cc:
                countries.add(cc)

        for cc in countries:
            country_events = [e for e in gfe_events
                            if (isinstance(e, dict) and e.get("country_code") == cc)
                            or (hasattr(e, 'country_code') and e.country_code == cc)]
            entities["nations"].append({
                "id": f"nation_{cc}",
                "type": "nation",
                "name": cc,
                "country_code": cc,
                "event_count": len(country_events),
                "avg_severity": sum(e.get("severity", 0.5) for e in country_events) / len(country_events) if country_events else 0.5,
                "confidence": 0.7,
            })

    except Exception as e:
        entities["error"] = str(e)

    return {
        "entities": entities,
        "counts": {
            "nations": len(entities["nations"]),
            "enterprises": len(entities["enterprises"]),
            "technologies": len(entities["technologies"]),
            "markets": len(entities["markets"]),
            "policies": len(entities["policies"]),
            "events": len(entities["events"]),
            "total": sum(len(v) for v in entities.values() if isinstance(v, list)),
        },
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_events() -> Dict[str, Any]:
    """获取事件图谱（含关系）。

    返回：
    {
        "events": list,
        "relations": list,
        "statistics": dict,
        "generated_at": str
    }
    """
    try:
        from gfe_events import get_event_intelligence_engine
        engine = get_event_intelligence_engine()
        gfe_events = engine.get_events(limit=100)

        # 转换为统一格式
        events = []
        for evt in gfe_events:
            evt_dict = evt.to_frontend() if hasattr(evt, 'to_frontend') else evt
            events.append({
                "id": evt_dict.get("event_id"),
                "title": evt_dict.get("title", ""),
                "category": evt_dict.get("category", ""),
                "severity": evt_dict.get("severity", 0.5),
                "confidence": evt_dict.get("confidence", 0.5),
                "country_code": evt_dict.get("country_code"),
                "status": evt_dict.get("status", "detected"),
                "created_at": evt_dict.get("created_at"),
            })

        # 分析关系
        relations = analyze_event_relations(events)

        # 统计
        categories = {}
        for e in events:
            cat = e.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "events": events[:50],  # 最多50条
            "relations": [r.to_frontend() for r in relations[:30]],  # 最多30条
            "statistics": {
                "total_events": len(events),
                "total_relations": len(relations),
                "by_category": categories,
                "avg_severity": sum(e.get("severity", 0.5) for e in events) / len(events) if events else 0,
                "avg_confidence": sum(e.get("confidence", 0.5) for e in events) / len(events) if events else 0,
            },
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    except Exception as e:
        return {
            "error": str(e),
            "events": [],
            "relations": [],
            "statistics": {},
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


def analyze_world_state() -> Dict[str, Any]:
    """分析世界状态（只读聚合）。

    返回：
    {
        "overall_severity": float,
        "risk_level": str,
        "key_entities": list,
        "trending_categories": list,
        "analysis": dict,
        "generated_at": str
    }
    """
    try:
        from gfe_events import get_event_intelligence_engine
        engine = get_event_intelligence_engine()
        gfe_events = engine.get_events(limit=100)

        # 计算整体严重程度
        severities = []
        categories = {}
        countries = {}

        for evt in gfe_events:
            evt_dict = evt.to_frontend() if hasattr(evt, 'to_frontend') else evt
            sev = evt_dict.get("severity", 0.5)
            severities.append(sev)

            cat = evt_dict.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

            cc = evt_dict.get("country_code")
            if cc:
                countries[cc] = countries.get(cc, 0) + 1

        avg_severity = sum(severities) / len(severities) if severities else 0.5

        # 风险等级
        if avg_severity >= 0.8:
            risk_level = "critical"
        elif avg_severity >= 0.6:
            risk_level = "high"
        elif avg_severity >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"

        # 关键实体（高严重程度事件）
        key_entities = []
        for evt in gfe_events:
            evt_dict = evt.to_frontend() if hasattr(evt, 'to_frontend') else evt
            if evt_dict.get("severity", 0.5) >= 0.7:
                key_entities.append({
                    "id": evt_dict.get("event_id"),
                    "title": evt_dict.get("title", ""),
                    "severity": evt_dict.get("severity"),
                    "category": evt_dict.get("category"),
                    "country_code": evt_dict.get("country_code"),
                })

        # 趋势类别（按事件数量排序）
        trending_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "overall_severity": round(avg_severity, 2),
            "risk_level": risk_level,
            "key_entities": key_entities[:10],
            "trending_categories": [{"category": c, "count": n} for c, n in trending_categories],
            "entity_counts": {
                "total_events": len(gfe_events),
                "by_category": categories,
                "by_country": dict(list(countries.items())[:10]),
            },
            "analysis": {
                "description": f"当前世界风险等级: {risk_level}, 平均严重程度: {avg_severity:.2f}",
                "top_category": trending_categories[0][0] if trending_categories else "unknown",
                "top_country": list(countries.keys())[0] if countries else "unknown",
            },
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    except Exception as e:
        return {
            "error": str(e),
            "overall_severity": 0.5,
            "risk_level": "unknown",
            "key_entities": [],
            "trending_categories": [],
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
