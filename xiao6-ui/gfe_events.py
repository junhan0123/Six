#!/usr/bin/env python3
"""PHASE 141 — GFE Event Intelligence Foundation

Global Foresight Engine (GFE) 事件智能层。
职责：
- 事件摄入与标准化
- 自动分类
- 影响分析
- 风险信号生成
- EventBus 集成

架构边界：
- 不实现 Forecast Engine
- 不实现 Historical Comparison
- 不调用 Runtime/Execution
- 仅做事件处理和影响分析
"""

from __future__ import annotations

import json
import time
import uuid
import threading
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from datetime import datetime

from db import db_conn
from eventbus import publish_system


# ============================================================
# Constants
# ============================================================

# EventBus Topics
TOPIC_EVENT_DETECTED = "gfe_event_detected"
TOPIC_EVENT_ANALYZED = "gfe_event_analyzed"
TOPIC_RISK_SIGNAL_CREATED = "gfe_risk_signal_created"

# Event categories
CATEGORY_POLICY = "policy"
CATEGORY_ECONOMY = "economy"
CATEGORY_FINANCE = "finance"
CATEGORY_TECHNOLOGY = "technology"
CATEGORY_ENERGY = "energy"
CATEGORY_MILITARY = "military"
CATEGORY_DIPLOMACY = "diplomacy"
CATEGORY_SOCIAL = "social"
CATEGORY_DISASTER = "disaster"

ALL_CATEGORIES = [
    CATEGORY_POLICY, CATEGORY_ECONOMY, CATEGORY_FINANCE,
    CATEGORY_TECHNOLOGY, CATEGORY_ENERGY, CATEGORY_MILITARY,
    CATEGORY_DIPLOMACY, CATEGORY_SOCIAL, CATEGORY_DISASTER
]

# Event status
STATUS_DETECTED = "detected"
STATUS_ANALYZED = "analyzed"
STATUS_INTEGRATED = "integrated"
STATUS_ARCHIVED = "archived"

# Impact direction
DIRECTION_POSITIVE = "positive"
DIRECTION_NEGATIVE = "negative"
DIRECTION_NEUTRAL = "neutral"

# Risk signal types
SIGNAL_TYPE_ANOMALY = "anomaly"
SIGNAL_TYPE_TREND = "trend"
SIGNAL_TYPE_SHOCK = "shock"
SIGNAL_TYPE_CORRELATION = "correlation"
SIGNAL_TYPE_ESCALATION = "escalation"


# ============================================================
# Data Models
# ============================================================

@dataclass
class GFEEvent:
    """GFE 事件模型。"""
    event_id: str
    source_id: Optional[str]
    title: str
    summary: Optional[str]
    category: str
    country_code: Optional[str]
    region: Optional[str]
    severity: float = 0.5
    confidence: float = 0.5
    impact: Optional[str] = None
    status: str = STATUS_DETECTED
    provenance: Optional[str] = None
    event_time: Optional[float] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source_id": self.source_id,
            "title": self.title,
            "summary": self.summary,
            "category": self.category,
            "country_code": self.country_code,
            "region": self.region,
            "severity": self.severity,
            "confidence": self.confidence,
            "impact": self.impact,
            "status": self.status,
            "provenance": self.provenance,
            "event_time": self.event_time,
            "created_at": self.created_at
        }


@dataclass
class EventImpact:
    """事件影响模型。"""
    impact_id: str
    event_id: str
    target_dimension: str
    impact_direction: str
    impact_strength: float
    time_horizon: Optional[int]
    reason: Optional[str]
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskSignal:
    """风险信号模型。"""
    signal_id: str
    country_code: str
    signal_type: str
    description: str
    severity: float
    probability: float
    confidence: float
    source_event_ids: List[str] = field(default_factory=list)
    status: str = "active"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "country_code": self.country_code,
            "signal_type": self.signal_type,
            "description": self.description,
            "severity": self.severity,
            "probability": self.probability,
            "confidence": self.confidence,
            "source_event_ids": self.source_event_ids,
            "status": self.status,
            "created_at": self.created_at
        }


# ============================================================
# Event Intelligence Engine
# ============================================================

class EventIntelligenceEngine:
    """事件智能引擎。

    负责事件摄入、分类、影响分析和风险信号生成。
    """

    def __init__(self, db_conn_func=None):
        self._conn = db_conn_func or db_conn
        self._lock = threading.RLock()

    def ingest_event(
        self,
        title: str,
        category: str,
        summary: Optional[str] = None,
        country_code: Optional[str] = None,
        region: Optional[str] = None,
        source_id: Optional[str] = None,
        provenance: Optional[str] = None,
        event_time: Optional[float] = None
    ) -> Optional[GFEEvent]:
        """摄入新事件。

        Args:
            title: 事件标题
            category: 事件类别
            summary: 事件摘要
            country_code: 关联国家代码
            region: 区域
            source_id: 来源 ID
            provenance: 来源追溯
            event_time: 事件发生时间

        Returns:
            GFEEvent 或 None（失败时）
        """
        try:
            with self._lock:
                conn = self._conn()
                event_id = f"evt_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_events
                       (event_id, source_id, title, summary, category, country_code,
                        region, severity, confidence, impact, status, provenance,
                        event_time, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event_id, source_id, title, summary, category, country_code,
                        region, 0.5, 0.7, None, STATUS_DETECTED, provenance,
                        event_time, now
                    )
                )
                conn.commit()

                event = GFEEvent(
                    event_id=event_id,
                    source_id=source_id,
                    title=title,
                    summary=summary,
                    category=category,
                    country_code=country_code,
                    region=region,
                    severity=0.5,
                    confidence=0.7,
                    status=STATUS_DETECTED,
                    provenance=provenance,
                    event_time=event_time,
                    created_at=now
                )

                # 发布 EventBus 事件
                self._emit_event(TOPIC_EVENT_DETECTED, {
                    "event_id": event_id,
                    "category": category,
                    "country_code": country_code,
                    "severity": 0.5,
                    "confidence": 0.7,
                    "timestamp": now
                })

                return event

        except Exception as e:
            print(f"[EventIntelligence] 摄入事件失败: {e}")
            return None

    def classify_event(self, event: GFEEvent) -> GFEEvent:
        """事件分类（根据关键词和规则）。"""
        try:
            title_lower = (event.title or "").lower()
            summary_lower = (event.summary or "").lower()
            text = f"{title_lower} {summary_lower}"

            # 基于关键词的分类规则
            policy_keywords = ["policy", "regulation", "law", "legislation", "tariff", "sanction"]
            economy_keywords = ["gdp", "growth", "inflation", "recession", "trade", "export", "import"]
            finance_keywords = ["interest", "rate", "fed", "central bank", "monetary", "bond", "yield"]
            technology_keywords = ["ai", "semiconductor", "technology", "innovation", "chip", "quantum"]
            energy_keywords = ["oil", "gas", "energy", "renewable", "electricity", "power"]
            military_keywords = ["military", "defense", "war", "conflict", "tension", "nuclear"]
            diplomacy_keywords = ["diplomatic", "summit", "meeting", "negotiation", "bilateral"]
            social_keywords = ["unemployment", "demographic", "migration", "protest", "election"]
            disaster_keywords = ["earthquake", "flood", "typhoon", "pandemic", "disaster"]

            # 匹配得分
            scores = {
                CATEGORY_POLICY: sum(1 for kw in policy_keywords if kw in text),
                CATEGORY_ECONOMY: sum(1 for kw in economy_keywords if kw in text),
                CATEGORY_FINANCE: sum(1 for kw in finance_keywords if kw in text),
                CATEGORY_TECHNOLOGY: sum(1 for kw in technology_keywords if kw in text),
                CATEGORY_ENERGY: sum(1 for kw in energy_keywords if kw in text),
                CATEGORY_MILITARY: sum(1 for kw in military_keywords if kw in text),
                CATEGORY_DIPLOMACY: sum(1 for kw in diplomacy_keywords if kw in text),
                CATEGORY_SOCIAL: sum(1 for kw in social_keywords if kw in text),
                CATEGORY_DISASTER: sum(1 for kw in disaster_keywords if kw in text),
            }

            # 选择得分最高的分类
            if scores:
                best_category = max(scores, key=scores.get)
                if scores[best_category] > 0:
                    event.category = best_category

            return event

        except Exception as e:
            print(f"[EventIntelligence] 分类失败: {e}")
            return event

    def analyze_impact(
        self,
        event: GFEEvent,
        country_code: Optional[str] = None
    ) -> List[EventImpact]:
        """分析事件影响。

        根据事件类别和严重程度，推断对 World State 各维度的影响。
        """
        impacts = []

        try:
            with self._lock:
                conn = self._conn()

                # 根据类别定义默认影响模式
                impact_patterns = {
                    CATEGORY_ECONOMY: [
                        ("economy", DIRECTION_NEGATIVE, 0.6, "GDP growth impact"),
                        ("trade", DIRECTION_NEGATIVE, 0.4, "Trade volume impact"),
                    ],
                    CATEGORY_FINANCE: [
                        ("finance", DIRECTION_NEGATIVE, 0.7, "Financial stability impact"),
                        ("economy", DIRECTION_NEGATIVE, 0.5, "Investment impact"),
                    ],
                    CATEGORY_TECHNOLOGY: [
                        ("technology", DIRECTION_POSITIVE, 0.6, "Technology advancement"),
                        ("industry", DIRECTION_POSITIVE, 0.4, "Industrial productivity"),
                    ],
                    CATEGORY_ENERGY: [
                        ("energy", DIRECTION_NEGATIVE, 0.8, "Energy supply disruption"),
                        ("economy", DIRECTION_NEGATIVE, 0.5, "Energy cost impact"),
                    ],
                    CATEGORY_MILITARY: [
                        ("military", DIRECTION_NEGATIVE, 0.7, "Security concern"),
                        ("diplomacy", DIRECTION_NEGATIVE, 0.5, "Diplomatic tension"),
                    ],
                    CATEGORY_DIPLOMACY: [
                        ("diplomacy", DIRECTION_POSITIVE, 0.6, "Diplomatic progress"),
                        ("trade", DIRECTION_POSITIVE, 0.4, "Trade relationship"),
                    ],
                }

                pattern = impact_patterns.get(event.category, [])

                for dimension, direction, strength, reason in pattern:
                    impact_id = f"imp_{int(time.time())}_{uuid.uuid4().hex[:6]}"
                    impact = EventImpact(
                        impact_id=impact_id,
                        event_id=event.event_id,
                        target_dimension=dimension,
                        impact_direction=direction,
                        impact_strength=strength * event.severity,
                        time_horizon=180,  # 默认6个月影响周期
                        reason=reason,
                        confidence=event.confidence
                    )
                    impacts.append(impact)

                    # 持久化影响记录
                    conn.execute(
                        """INSERT INTO gfe_event_impacts
                           (impact_id, event_id, target_dimension, impact_direction,
                            impact_strength, time_horizon, reason, confidence, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            impact.impact_id, impact.event_id, impact.target_dimension,
                            impact.impact_direction, impact.impact_strength,
                            impact.time_horizon, impact.reason, impact.confidence,
                            time.time()
                        )
                    )

                conn.commit()

                # 更新事件状态
                event.status = STATUS_ANALYZED
                self._update_event_status(event.event_id, STATUS_ANALYZED)

                # 发布 EventBus 事件
                self._emit_event(TOPIC_EVENT_ANALYZED, {
                    "event_id": event.event_id,
                    "category": event.category,
                    "country_code": country_code or event.country_code,
                    "impact_count": len(impacts),
                    "timestamp": time.time()
                })

        except Exception as e:
            print(f"[EventIntelligence] 影响分析失败: {e}")

        return impacts

    def create_risk_signal(
        self,
        country_code: str,
        signal_type: str,
        description: str,
        severity: float,
        probability: float,
        confidence: float,
        source_event_ids: Optional[List[str]] = None
    ) -> Optional[RiskSignal]:
        """创建风险信号。"""
        try:
            with self._lock:
                conn = self._conn()
                signal_id = f"sig_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_risk_signals
                       (signal_id, country_code, signal_type, description,
                        severity, probability, confidence, source_event_ids, status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        signal_id, country_code, signal_type, description,
                        severity, probability, confidence,
                        json.dumps(source_event_ids or []),
                        STATUS_DETECTED, now
                    )
                )
                conn.commit()

                signal = RiskSignal(
                    signal_id=signal_id,
                    country_code=country_code,
                    signal_type=signal_type,
                    description=description,
                    severity=severity,
                    probability=probability,
                    confidence=confidence,
                    source_event_ids=source_event_ids or [],
                    created_at=now
                )

                # 发布 EventBus 事件
                self._emit_event(TOPIC_RISK_SIGNAL_CREATED, {
                    "signal_id": signal_id,
                    "country_code": country_code,
                    "signal_type": signal_type,
                    "severity": severity,
                    "probability": probability,
                    "timestamp": now
                })

                return signal

        except Exception as e:
            print(f"[EventIntelligence] 创建风险信号失败: {e}")
            return None

    def get_events(
        self,
        country_code: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[GFEEvent]:
        """查询事件历史。"""
        try:
            conn = self._conn()
            query = "SELECT * FROM gfe_events WHERE 1=1"
            params = []

            if country_code:
                query += " AND country_code = ?"
                params.append(country_code)
            if category:
                query += " AND category = ?"
                params.append(category)
            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY event_time DESC, created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_event(row) for row in rows if row]

        except Exception as e:
            print(f"[EventIntelligence] 查询事件失败: {e}")
            return []

    def get_risk_signals(
        self,
        country_code: Optional[str] = None,
        signal_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[RiskSignal]:
        """查询风险信号。"""
        try:
            conn = self._conn()
            query = "SELECT * FROM gfe_risk_signals WHERE 1=1"
            params = []

            if country_code:
                query += " AND country_code = ?"
                params.append(country_code)
            if signal_type:
                query += " AND signal_type = ?"
                params.append(signal_type)
            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_signal(row) for row in rows if row]

        except Exception as e:
            print(f"[EventIntelligence] 查询风险信号失败: {e}")
            return []

    def scan_external_events(self):
        """扫描外部事件源。

        暂不接真实新闻 API。
        未来可接入：
        - Reuters
        - Bloomberg
        - IMF
        - World Bank
        - 官方数据
        """
        # 空实现，保留接口
        pass

    # ---- 内部方法 ----

    def _row_to_event(self, row) -> GFEEvent:
        """将 DB 行转换为 GFEEvent 对象。"""
        return GFEEvent(
            event_id=row[0],
            source_id=row[1],
            title=row[2],
            summary=row[3],
            category=row[4],
            country_code=row[5],
            region=row[6],
            severity=float(row[7]) if row[7] else 0.5,
            confidence=float(row[8]) if row[8] else 0.5,
            impact=row[9],
            status=row[10],
            provenance=row[11],
            event_time=float(row[12]) if row[12] else None,
            created_at=float(row[13]) if row[13] else time.time()
        )

    def _row_to_signal(self, row) -> RiskSignal:
        """将 DB 行转换为 RiskSignal 对象。"""
        try:
            source_event_ids = json.loads(row[8] or "[]")
        except (json.JSONDecodeError, TypeError):
            source_event_ids = []

        return RiskSignal(
            signal_id=row[0],
            country_code=row[1],
            signal_type=row[2],
            description=row[3],
            severity=float(row[4]) if row[4] else 0.5,
            probability=float(row[5]) if row[5] else 0.5,
            confidence=float(row[6]) if row[6] else 0.5,
            source_event_ids=source_event_ids,
            status=row[7],
            created_at=float(row[9]) if row[9] else time.time()
        )

    def _update_event_status(self, event_id: str, status: str):
        """更新事件状态。"""
        try:
            conn = self._conn()
            conn.execute(
                "UPDATE gfe_events SET status = ? WHERE event_id = ?",
                (status, event_id)
            )
            conn.commit()
        except Exception as e:
            print(f"[EventIntelligence] 更新事件状态失败: {e}")

    def _emit_event(self, event_type: str, payload: Dict[str, Any]):
        """发布 EventBus 事件。"""
        try:
            publish_system(event_type, payload, source="gfe_event")
        except Exception as e:
            print(f"[EventIntelligence] EventBus 发布失败: {e}")


# ============================================================
# Singleton
# ============================================================

_instance: Optional[EventIntelligenceEngine] = None
_instance_lock = threading.Lock()


def get_event_intelligence_engine() -> EventIntelligenceEngine:
    """获取单例 EventIntelligenceEngine。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = EventIntelligenceEngine()
        return _instance


def reset_event_intelligence_engine():
    """重置单例（用于测试）。"""
    global _instance
    with _instance_lock:
        _instance = None