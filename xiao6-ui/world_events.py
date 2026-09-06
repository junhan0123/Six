#!/usr/bin/env python3
"""World Events — 事件模型与关系定义。

定义事件间关系：
- CAUSES (因果)
- AFFECTS (影响)
- CORRELATES (相关)
- PRECEDES (先后)

约束：
- 仅定义模型和关系分析
- 不修改现有 gfe_events.py
- 只读聚合现有数据
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


# 关系类型常量
RELATION_CAUSES = "CAUSES"
RELATION_AFFECTS = "AFFECTS"
RELATION_CORRELATES = "CORRELATES"
RELATION_PRECEDES = "PRECEDES"

ALL_RELATION_TYPES = [
    RELATION_CAUSES, RELATION_AFFECTS,
    RELATION_CORRELATES, RELATION_PRECEDES
]


@dataclass
class EventRelation:
    """事件关系模型。"""
    relation_id: str
    source_event_id: str
    target_event_id: str
    relation_type: str  # CAUSES, AFFECTS, CORRELATES, PRECEDES
    strength: float = 0.5  # 0.0-1.0
    confidence: float = 0.5
    evidence: Optional[str] = None
    created_at: float = field(default_factory=datetime.now().timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relation_id": self.relation_id,
            "source_event_id": self.source_event_id,
            "target_event_id": self.target_event_id,
            "relation_type": self.relation_type,
            "strength": self.strength,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "created_at": self.created_at,
        }

    def to_frontend(self) -> Dict[str, Any]:
        return self.to_dict()


@dataclass
class WorldEventNode:
    """世界事件节点（扩展自 GFEEvent）。"""
    event_id: str
    title: str
    category: str
    severity: float = 0.5
    confidence: float = 0.5
    country_code: Optional[str] = None
    region: Optional[str] = None
    related_relations: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=datetime.now().timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "category": self.category,
            "severity": self.severity,
            "confidence": self.confidence,
            "country_code": self.country_code,
            "region": self.region,
            "related_relations": self.related_relations,
            "created_at": self.created_at,
        }


def analyze_event_relations(events: List[Dict[str, Any]]) -> List[EventRelation]:
    """分析事件间关系（启发式）。

    规则：
    - 同国家 + 同类别 + 时间接近 → CORRELATES
    - 不同类别 + 同国家 + 时间接近 → AFFECTS
    - 政策事件 + 经济事件 → CAUSES
    - 时间先后 + 相关领域 → PRECEDES
    """
    relations = []

    for i, e1 in enumerate(events):
        for e2 in events[i+1:]:
            # 时间差
            t1 = e1.get("created_at") or e1.get("event_time") or 0
            t2 = e2.get("created_at") or e2.get("event_time") or 0
            time_diff = abs(t1 - t2)

            # 同国家
            same_country = (e1.get("country_code") and
                          e1.get("country_code") == e2.get("country_code"))

            # 同类别
            same_category = e1.get("category") == e2.get("category")

            # 生成关系
            if same_country and same_category and time_diff < 86400 * 7:
                # 7天内同国家同类别 → CORRELATES
                relations.append(EventRelation(
                    relation_id=f"rel_{e1.get('event_id', '')}_{e2.get('event_id', '')}",
                    source_event_id=e1.get("event_id", ""),
                    target_event_id=e2.get("event_id", ""),
                    relation_type=RELATION_CORRELATES,
                    strength=0.6,
                    confidence=0.5,
                    evidence=f"同国家({e1.get('country_code')})同类别{e1.get('category')}时间相近"
                ))
            elif same_country and not same_category and time_diff < 86400 * 30:
                # 30天内同国家不同类别 → AFFECTS
                relations.append(EventRelation(
                    relation_id=f"rel_{e1.get('event_id', '')}_{e2.get('event_id', '')}",
                    source_event_id=e1.get("event_id", ""),
                    target_event_id=e2.get("event_id", ""),
                    relation_type=RELATION_AFFECTS,
                    strength=0.4,
                    confidence=0.4,
                    evidence=f"同国家({e1.get('country_code')})不同类别时间相近"
                ))
            elif e1.get("category") == "policy" and e2.get("category") in ("economy", "finance"):
                # 政策 → 经济/金融 → CAUSES
                relations.append(EventRelation(
                    relation_id=f"rel_{e1.get('event_id', '')}_{e2.get('event_id', '')}",
                    source_event_id=e1.get("event_id", ""),
                    target_event_id=e2.get("event_id", ""),
                    relation_type=RELATION_CAUSES,
                    strength=0.7,
                    confidence=0.6,
                    evidence="政策→经济/金融因果关系"
                ))
            elif t1 < t2:
                # 时间先后 → PRECEDES
                relations.append(EventRelation(
                    relation_id=f"rel_{e1.get('event_id', '')}_{e2.get('event_id', '')}",
                    source_event_id=e1.get("event_id", ""),
                    target_event_id=e2.get("event_id", ""),
                    relation_type=RELATION_PRECEDES,
                    strength=0.3,
                    confidence=0.3,
                    evidence=f"时间先后关系 (diff={time_diff/86400:.1f} days)"
                ))

    return relations


def get_relation_types() -> List[str]:
    """获取所有关系类型。"""
    return ALL_RELATION_TYPES
