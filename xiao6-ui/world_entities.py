#!/usr/bin/env python3
"""World Entities — 世界实体模型定义。

定义 GFE World Model 的基础实体类型：
- Nation (国家)
- Enterprise (企业)
- Technology (技术)
- Market (市场)
- Policy (政策)
- Event (事件)

约束：
- 仅定义模型，不修改现有 gfe 模块
- 不创建新数据库
- 只读聚合现有数据
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


# 实体类型常量
ENTITY_NATION = "nation"
ENTITY_ENTERPRISE = "enterprise"
ENTITY_TECHNOLOGY = "technology"
ENTITY_MARKET = "market"
ENTITY_POLICY = "policy"
ENTITY_EVENT = "event"

ALL_ENTITY_TYPES = [
    ENTITY_NATION, ENTITY_ENTERPRISE, ENTITY_TECHNOLOGY,
    ENTITY_MARKET, ENTITY_POLICY, ENTITY_EVENT
]


@dataclass
class WorldEntity:
    """世界实体基类。"""
    id: str
    type: str
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)
    confidence: float = 0.5
    related_entities: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=datetime.now().timestamp)
    updated_at: float = field(default_factory=datetime.now().timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "attributes": self.attributes,
            "sources": self.sources,
            "confidence": self.confidence,
            "related_entities": self.related_entities,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_frontend(self) -> Dict[str, Any]:
        return self.to_dict()


@dataclass
class Nation(WorldEntity):
    """国家实体。"""
    type: str = ENTITY_NATION
    country_code: str = ""
    region: str = ""
    indicators: Dict[str, Any] = field(default_factory=dict)
    name: str = ""

    def to_frontend(self) -> Dict[str, Any]:
        data = super().to_frontend()
        data["country_code"] = self.country_code
        data["region"] = self.region
        data["indicators"] = self.indicators
        return data


@dataclass
class Enterprise(WorldEntity):
    """企业实体。"""
    type: str = ENTITY_ENTERPRISE
    ticker: str = ""
    industry: str = ""
    market_cap: Optional[float] = None
    name: str = ""

    def to_frontend(self) -> Dict[str, Any]:
        data = super().to_frontend()
        data["ticker"] = self.ticker
        data["industry"] = self.industry
        data["market_cap"] = self.market_cap
        return data


@dataclass
class Technology(WorldEntity):
    """技术实体。"""
    type: str = ENTITY_TECHNOLOGY
    domain: str = ""
    maturity: str = ""  # emerging, growing, mature, declining
    impact_score: float = 0.0
    name: str = ""

    def to_frontend(self) -> Dict[str, Any]:
        data = super().to_frontend()
        data["domain"] = self.domain
        data["maturity"] = self.maturity
        data["impact_score"] = self.impact_score
        return data


@dataclass
class Market(WorldEntity):
    """市场实体。"""
    type: str = ENTITY_MARKET
    market_type: str = ""  # stock, bond, commodity, forex, crypto
    region: str = ""
    size: Optional[float] = None
    name: str = ""

    def to_frontend(self) -> Dict[str, Any]:
        data = super().to_frontend()
        data["market_type"] = self.market_type
        data["region"] = self.region
        data["size"] = self.size
        return data


@dataclass
class Policy(WorldEntity):
    """政策实体。"""
    type: str = ENTITY_POLICY
    jurisdiction: str = ""
    category: str = ""  # fiscal, monetary, trade, tech, environmental
    status: str = "proposed"  # proposed, active, repealed
    name: str = ""

    def to_frontend(self) -> Dict[str, Any]:
        data = super().to_frontend()
        data["jurisdiction"] = self.jurisdiction
        data["category"] = self.category
        data["status"] = self.status
        return data


@dataclass
class WorldEvent(WorldEntity):
    """事件实体（用于 World Model 统一表示）。"""
    type: str = ENTITY_EVENT
    event_category: str = ""  # economy, politics, society, technology, environment
    severity: float = 0.5
    impact_scope: List[str] = field(default_factory=list)
    name: str = ""

    def to_frontend(self) -> Dict[str, Any]:
        data = super().to_frontend()
        data["event_category"] = self.event_category
        data["severity"] = self.severity
        data["impact_scope"] = self.impact_scope
        return data


# 实体类型映射
ENTITY_TYPE_MAP = {
    ENTITY_NATION: Nation,
    ENTITY_ENTERPRISE: Enterprise,
    ENTITY_TECHNOLOGY: Technology,
    ENTITY_MARKET: Market,
    ENTITY_POLICY: Policy,
    ENTITY_EVENT: WorldEvent,
}


def create_entity(entity_type: str, **kwargs) -> Optional[WorldEntity]:
    """创建世界实体。"""
    cls = ENTITY_TYPE_MAP.get(entity_type)
    if cls is None:
        return None
    return cls(**kwargs)


def get_entity_types() -> List[str]:
    """获取所有实体类型。"""
    return ALL_ENTITY_TYPES
