#!/usr/bin/env python3
"""PHASE 140 — GFE World State Engine Foundation

Global Foresight Engine (GFE) 世界状态引擎基础层。
职责：
- Country State Snapshot (快照)
- Indicator Time Series (指标时序)
- State Change Tracking (状态变更追踪)
- EventBus 集成

架构边界：
- 不实现 Forecast Engine
- 不实现 Historical Comparison
- 不实现 Causal Graph
- 不实现 Analyst Council
- 不调用 Runtime/Execution
- 仅记录状态，不做预测
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
TOPIC_WORLD_STATE_CREATED = "gfe_world_state_created"
TOPIC_WORLD_STATE_UPDATED = "gfe_world_state_updated"
TOPIC_INDICATOR_UPDATED = "gfe_indicator_updated"

# Category constants
CATEGORY_ECONOMY = "economy"
CATEGORY_DEMOGRAPHICS = "demographics"
CATEGORY_FINANCE = "finance"
CATEGORY_INDUSTRY = "industry"
CATEGORY_TECHNOLOGY = "technology"
CATEGORY_ENERGY = "energy"
CATEGORY_MILITARY = "military"
CATEGORY_DIPLOMACY = "diplomacy"
CATEGORY_TRADE = "trade"
CATEGORY_FISCAL = "fiscal"
CATEGORY_SOCIAL = "social"

ALL_CATEGORIES = [
    CATEGORY_ECONOMY, CATEGORY_DEMOGRAPHICS, CATEGORY_FINANCE,
    CATEGORY_INDUSTRY, CATEGORY_TECHNOLOGY, CATEGORY_ENERGY,
    CATEGORY_MILITARY, CATEGORY_DIPLOMACY, CATEGORY_TRADE,
    CATEGORY_FISCAL, CATEGORY_SOCIAL
]


# ============================================================
# Data Models
# ============================================================

@dataclass
class CountryState:
    """国家状态快照。"""
    state_id: str
    country_code: str
    snapshot_time: float
    confidence: float = 0.5
    provenance: Optional[str] = None
    demographics: Dict[str, Any] = field(default_factory=dict)
    economy: Dict[str, Any] = field(default_factory=dict)
    finance: Dict[str, Any] = field(default_factory=dict)
    industry: Dict[str, Any] = field(default_factory=dict)
    technology: Dict[str, Any] = field(default_factory=dict)
    energy: Dict[str, Any] = field(default_factory=dict)
    military: Dict[str, Any] = field(default_factory=dict)
    diplomacy: Dict[str, Any] = field(default_factory=dict)
    trade: Dict[str, Any] = field(default_factory=dict)
    fiscal: Dict[str, Any] = field(default_factory=dict)
    social: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        """序列化为前端格式。"""
        return {
            "state_id": self.state_id,
            "country_code": self.country_code,
            "snapshot_time": self.snapshot_time,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "demographics": self.demographics,
            "economy": self.economy,
            "finance": self.finance,
            "industry": self.industry,
            "technology": self.technology,
            "energy": self.energy,
            "military": self.military,
            "diplomacy": self.diplomacy,
            "trade": self.trade,
            "fiscal": self.fiscal,
            "social": self.social,
            "created_at": self.created_at
        }


@dataclass
class Indicator:
    """经济指标。"""
    indicator_id: str
    country_code: str
    name: str
    category: str
    value: Optional[float]
    unit: Optional[str]
    timestamp: float
    source_id: Optional[str]
    confidence: float = 0.5
    provenance: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "indicator_id": self.indicator_id,
            "country_code": self.country_code,
            "name": self.name,
            "category": self.category,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp,
            "source_id": self.source_id,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "created_at": self.created_at
        }


@dataclass
class StateChange:
    """状态变更记录。"""
    change_id: str
    country_code: str
    field_name: str
    old_value: Optional[str]
    new_value: Optional[str]
    change_reason: Optional[str]
    source_refs: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# World State Engine
# ============================================================

class WorldStateEngine:
    """世界状态引擎。

    负责维护国家状态快照、指标时序和状态变更追踪。
    仅记录状态，不做预测。
    """

    def __init__(self, db_conn_func=None):
        self._conn = db_conn_func or db_conn
        self._lock = threading.RLock()

    def create_snapshot(
        self,
        country_code: str,
        state_data: Dict[str, Any],
        confidence: float = 0.5,
        provenance: Optional[str] = None
    ) -> Optional[CountryState]:
        """创建国家状态快照。

        Args:
            country_code: ISO 3166-1 alpha-2 国家代码
            state_data: 状态数据字典，包含 demographics, economy, finance 等
            confidence: 置信度 0-1
            provenance: 数据来源追溯

        Returns:
            CountryState 或 None（失败时）
        """
        try:
            with self._lock:
                conn = self._conn()
                # Use UUID to avoid collisions when called rapidly
                import uuid
                state_id = f"{country_code}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                snapshot_time = time.time()

                # 提取各维度数据
                demographics = state_data.get("demographics", {})
                economy = state_data.get("economy", {})
                finance = state_data.get("finance", {})
                industry = state_data.get("industry", {})
                technology = state_data.get("technology", {})
                energy = state_data.get("energy", {})
                military = state_data.get("military", {})
                diplomacy = state_data.get("diplomacy", {})
                trade = state_data.get("trade", {})
                fiscal = state_data.get("fiscal", {})
                social = state_data.get("social", {})

                conn.execute(
                    """INSERT INTO gfe_world_states
                       (state_id, country_code, snapshot_time, confidence, provenance,
                        demographics, economy, finance, industry, technology,
                        energy, military, diplomacy, trade, fiscal, social, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        state_id, country_code, snapshot_time, confidence, provenance,
                        json.dumps(demographics, ensure_ascii=False),
                        json.dumps(economy, ensure_ascii=False),
                        json.dumps(finance, ensure_ascii=False),
                        json.dumps(industry, ensure_ascii=False),
                        json.dumps(technology, ensure_ascii=False),
                        json.dumps(energy, ensure_ascii=False),
                        json.dumps(military, ensure_ascii=False),
                        json.dumps(diplomacy, ensure_ascii=False),
                        json.dumps(trade, ensure_ascii=False),
                        json.dumps(fiscal, ensure_ascii=False),
                        json.dumps(social, ensure_ascii=False),
                        time.time()
                    )
                )
                conn.commit()

                state = CountryState(
                    state_id=state_id,
                    country_code=country_code,
                    snapshot_time=snapshot_time,
                    confidence=confidence,
                    provenance=provenance,
                    demographics=demographics,
                    economy=economy,
                    finance=finance,
                    industry=industry,
                    technology=technology,
                    energy=energy,
                    military=military,
                    diplomacy=diplomacy,
                    trade=trade,
                    fiscal=fiscal,
                    social=social,
                    created_at=time.time()
                )

                # 发布 EventBus 事件
                self._emit_event(TOPIC_WORLD_STATE_CREATED, {
                    "state_id": state_id,
                    "country_code": country_code,
                    "confidence": confidence,
                    "timestamp": snapshot_time
                })

                return state

        except Exception as e:
            print(f"[WorldStateEngine] 创建快照失败: {e}")
            return None

    def get_current_state(self, country_code: str) -> Optional[CountryState]:
        """获取国家最新状态快照。"""
        try:
            conn = self._conn()
            row = conn.execute(
                """SELECT * FROM gfe_world_states
                   WHERE country_code = ?
                   ORDER BY snapshot_time DESC
                   LIMIT 1""",
                (country_code,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_state(row)

        except Exception as e:
            print(f"[WorldStateEngine] 查询当前状态失败: {e}")
            return None

    def get_history(
        self,
        country_code: str,
        limit: int = 10
    ) -> List[CountryState]:
        """获取国家历史状态快照。"""
        try:
            conn = self._conn()
            rows = conn.execute(
                """SELECT * FROM gfe_world_states
                   WHERE country_code = ?
                   ORDER BY snapshot_time DESC
                   LIMIT ?""",
                (country_code, limit)
            ).fetchall()

            return [self._row_to_state(row) for row in rows if row]

        except Exception as e:
            print(f"[WorldStateEngine] 查询历史状态失败: {e}")
            return []

    def update_indicator(
        self,
        country_code: str,
        name: str,
        category: str,
        value: float,
        unit: Optional[str] = None,
        source_id: Optional[str] = None,
        confidence: float = 0.5,
        provenance: Optional[str] = None
    ) -> Optional[Indicator]:
        """更新或创建指标。

        采用时间序列模式：每次调用创建新记录。
        """
        try:
            with self._lock:
                conn = self._conn()
                indicator_id = f"{country_code}_{name}_{int(time.time())}"
                timestamp = time.time()

                conn.execute(
                    """INSERT INTO gfe_indicators
                       (indicator_id, country_code, name, category, value, unit,
                        timestamp, source_id, confidence, provenance, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        indicator_id, country_code, name, category, value, unit,
                        timestamp, source_id, confidence, provenance, time.time()
                    )
                )
                conn.commit()

                indicator = Indicator(
                    indicator_id=indicator_id,
                    country_code=country_code,
                    name=name,
                    category=category,
                    value=value,
                    unit=unit,
                    timestamp=timestamp,
                    source_id=source_id,
                    confidence=confidence,
                    provenance=provenance,
                    created_at=time.time()
                )

                # 发布 EventBus 事件
                self._emit_event(TOPIC_INDICATOR_UPDATED, {
                    "indicator_id": indicator_id,
                    "country_code": country_code,
                    "name": name,
                    "category": category,
                    "value": value,
                    "timestamp": timestamp
                })

                return indicator

        except Exception as e:
            print(f"[WorldStateEngine] 更新指标失败: {e}")
            return None

    def get_indicator_history(
        self,
        country_code: str,
        name: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Indicator]:
        """获取指标历史序列。"""
        try:
            conn = self._conn()
            if category:
                rows = conn.execute(
                    """SELECT * FROM gfe_indicators
                       WHERE country_code = ? AND name = ? AND category = ?
                       ORDER BY timestamp DESC
                       LIMIT ?""",
                    (country_code, name, category, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM gfe_indicators
                       WHERE country_code = ? AND name = ?
                       ORDER BY timestamp DESC
                       LIMIT ?""",
                    (country_code, name, limit)
                ).fetchall()

            return [self._row_to_indicator(row) for row in rows if row]

        except Exception as e:
            print(f"[WorldStateEngine] 查询指标历史失败: {e}")
            return []

    def calculate_state_change(
        self,
        country_code: str,
        old_state: CountryState,
        new_state: CountryState,
        reason: Optional[str] = None
    ) -> List[StateChange]:
        """计算状态变化记录。

        对比两个状态快照，生成变更记录列表。
        """
        changes = []

        # 对比各维度
        fields = [
            "demographics", "economy", "finance", "industry",
            "technology", "energy", "military", "diplomacy",
            "trade", "fiscal", "social"
        ]

        for field_name in fields:
            old_val = getattr(old_state, field_name, {})
            new_val = getattr(new_state, field_name, {})

            if old_val != new_val:
                change_id = f"{country_code}_{field_name}_{int(time.time())}"
                change = StateChange(
                    change_id=change_id,
                    country_code=country_code,
                    field_name=field_name,
                    old_value=json.dumps(old_val, ensure_ascii=False),
                    new_value=json.dumps(new_val, ensure_ascii=False),
                    change_reason=reason,
                    timestamp=time.time()
                )
                changes.append(change)

                # 持久化变更记录
                self._record_change(change)

        return changes

    def get_state_changes(
        self,
        country_code: str,
        field_name: Optional[str] = None,
        limit: int = 50
    ) -> List[StateChange]:
        """获取状态变更历史记录。"""
        try:
            conn = self._conn()
            if field_name:
                rows = conn.execute(
                    """SELECT * FROM gfe_state_changes
                       WHERE country_code = ? AND field_name = ?
                       ORDER BY timestamp DESC
                       LIMIT ?""",
                    (country_code, field_name, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM gfe_state_changes
                       WHERE country_code = ?
                       ORDER BY timestamp DESC
                       LIMIT ?""",
                    (country_code, limit)
                ).fetchall()

            return [self._row_to_change(row) for row in rows if row]

        except Exception as e:
            print(f"[WorldStateEngine] 查询状态变更失败: {e}")
            return []

    # ---- 内部方法 ----

    def _row_to_state(self, row) -> CountryState:
        """将 DB 行转换为 CountryState 对象。"""
        return CountryState(
            state_id=row[0],
            country_code=row[1],
            snapshot_time=float(row[2]) if row[2] else time.time(),
            confidence=float(row[3]) if row[3] else 0.5,
            provenance=row[4],
            demographics=json.loads(row[5] or "{}"),
            economy=json.loads(row[6] or "{}"),
            finance=json.loads(row[7] or "{}"),
            industry=json.loads(row[8] or "{}"),
            technology=json.loads(row[9] or "{}"),
            energy=json.loads(row[10] or "{}"),
            military=json.loads(row[11] or "{}"),
            diplomacy=json.loads(row[12] or "{}"),
            trade=json.loads(row[13] or "{}"),
            fiscal=json.loads(row[14] or "{}"),
            social=json.loads(row[15] or "{}"),
            created_at=float(row[16]) if row[16] else time.time()
        )

    def _row_to_indicator(self, row) -> Indicator:
        """将 DB 行转换为 Indicator 对象。"""
        return Indicator(
            indicator_id=row[0],
            country_code=row[1],
            name=row[2],
            category=row[3],
            value=float(row[4]) if row[4] else None,
            unit=row[5],
            timestamp=float(row[6]) if row[6] else time.time(),
            source_id=row[7],
            confidence=float(row[8]) if row[8] else 0.5,
            provenance=row[9],
            created_at=float(row[10]) if row[10] else time.time()
        )

    def _row_to_change(self, row) -> StateChange:
        """将 DB 行转换为 StateChange 对象。"""
        try:
            source_refs = json.loads(row[6] or "[]")
        except (json.JSONDecodeError, TypeError):
            source_refs = []

        return StateChange(
            change_id=row[0],
            country_code=row[1],
            field_name=row[2],
            old_value=row[3],
            new_value=row[4],
            change_reason=row[5],
            source_refs=source_refs,
            timestamp=float(row[7]) if row[7] else time.time()
        )

    def _record_change(self, change: StateChange):
        """持久化状态变更记录。"""
        try:
            conn = self._conn()
            conn.execute(
                """INSERT INTO gfe_state_changes
                   (change_id, country_code, field_name, old_value, new_value,
                    change_reason, source_refs, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    change.change_id, change.country_code, change.field_name,
                    change.old_value, change.new_value, change.change_reason,
                    json.dumps(change.source_refs, ensure_ascii=False),
                    change.timestamp
                )
            )
            conn.commit()
        except Exception as e:
            print(f"[WorldStateEngine] 记录变更失败: {e}")

    def _emit_event(self, event_type: str, payload: Dict[str, Any]):
        """发布 EventBus 事件。"""
        try:
            publish_system(event_type, payload, source="gfe_world_state")
        except Exception as e:
            print(f"[WorldStateEngine] EventBus 发布失败: {e}")


# ============================================================
# Singleton
# ============================================================

_instance: Optional[WorldStateEngine] = None
_instance_lock = threading.Lock()


def get_world_state_engine() -> WorldStateEngine:
    """获取单例 WorldStateEngine。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = WorldStateEngine()
        return _instance


def reset_world_state_engine():
    """重置单例（用于测试）。"""
    global _instance
    with _instance_lock:
        _instance = None