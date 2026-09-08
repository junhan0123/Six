#!/usr/bin/env python3
"""PHASE 139 — GFE Data Source Foundation

Global Foresight Engine (GFE) 数据源基础层。
职责：
- DataSource 模型定义
- SourceManager 注册/查询/可靠性管理
- EventBus 集成（事件发布）
- 可信度评分算法

架构边界：
- 不实现 World State Engine
- 不实现 Forecast Engine
- 不实现 Causal Graph
- 不实现 Analyst Council
- 不调用 Runtime/Execution
"""

from __future__ import annotations

import json
import time
import threading
import sqlite3
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from datetime import datetime

from db import db_conn


# ============================================================
# Constants
# ============================================================

# 数据源类型
TYPE_OFFICIAL = "official"
TYPE_INTERNATIONAL = "international"
TYPE_FINANCIAL = "financial"
TYPE_NEWS = "news"
TYPE_ACADEMIC = "academic"
TYPE_HISTORICAL = "historical"
TYPE_OPEN_DATA = "open_data"

ALL_TYPES = [
    TYPE_OFFICIAL, TYPE_INTERNATIONAL, TYPE_FINANCIAL,
    TYPE_NEWS, TYPE_ACADEMIC, TYPE_HISTORICAL, TYPE_OPEN_DATA
]

# 可信度范围
MIN_RELIABILITY = 0.0
MAX_RELIABILITY = 1.0

# Authority 权重
AUTHORITY_WEIGHTS = {
    TYPE_OFFICIAL: 0.95,
    TYPE_INTERNATIONAL: 0.90,
    TYPE_FINANCIAL: 0.85,
    TYPE_ACADEMIC: 0.75,
    TYPE_NEWS: 0.70,
    TYPE_HISTORICAL: 0.65,
    TYPE_OPEN_DATA: 0.60,
}

# EventBus Topics
TOPIC_SOURCE_REGISTERED = "gfe_source_registered"
TOPIC_SOURCE_UPDATED = "gfe_source_updated"
TOPIC_SOURCE_RELIABILITY_CHANGED = "gfe_source_reliability_changed"


# ============================================================
# Data Models
# ============================================================

@dataclass
class DataSource:
    """数据源模型。"""
    source_id: str
    name: str
    type: str
    authority: Optional[str]
    country: Optional[str]
    reliability: float = 0.5
    historical_accuracy: float = 0.0
    update_frequency: Optional[str] = None
    license: Optional[str] = None
    provenance: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "name": self.name,
            "type": self.type,
            "authority": self.authority,
            "country": self.country,
            "reliability": round(self.reliability, 3),
            "last_updated": self.last_updated,
        }


# ============================================================
# Reliability Calculator
# ============================================================

class ReliabilityCalculator:
    """可信度评分计算器。"""

    # 权重配置
    WEIGHT_BASE = 0.4
    WEIGHT_HISTORICAL = 0.3
    WEIGHT_AUTHORITY = 0.2
    WEIGHT_FRESHNESS = 0.1

    @classmethod
    def calculate(
        cls,
        base_reliability: float,
        historical_accuracy: float,
        source_type: str,
        last_updated: Optional[float] = None,
    ) -> float:
        """计算综合可信度。

        公式：
        overall = base * 0.4 + historical * 0.3 + authority * 0.2 + freshness * 0.1

        限制：0 <= score <= 1
        """
        # 规范化输入
        base = max(MIN_RELIABILITY, min(MAX_RELIABILITY, base_reliability))
        historical = max(MIN_RELIABILITY, min(MAX_RELIABILITY, historical_accuracy))
        authority = cls._get_authority_score(source_type)
        freshness = cls._get_freshness_score(last_updated)

        # 加权计算
        score = (
            base * cls.WEIGHT_BASE
            + historical * cls.WEIGHT_HISTORICAL
            + authority * cls.WEIGHT_AUTHORITY
            + freshness * cls.WEIGHT_FRESHNESS
        )

        # 限制范围
        return max(MIN_RELIABILITY, min(MAX_RELIABILITY, score))

    @classmethod
    def _get_authority_score(cls, source_type: str) -> float:
        """获取 Authority 权重分数。"""
        return AUTHORITY_WEIGHTS.get(source_type, 0.5)

    @classmethod
    def _get_freshness_score(cls, last_updated: Optional[float]) -> float:
        """根据更新时间计算新鲜度分数。

        - 今天内更新：1.0
        - 7 天内：0.8
        - 30 天内：0.6
        - 超过 30 天：0.4
        """
        if last_updated is None:
            return 0.3

        age_seconds = time.time() - last_updated
        age_days = age_seconds / 86400

        if age_days <= 1:
            return 1.0
        elif age_days <= 7:
            return 0.8
        elif age_days <= 30:
            return 0.6
        else:
            return 0.4


# ============================================================
# Source Manager
# ============================================================

class SourceManager:
    """数据源管理器。"""

    def __init__(self, db_conn_func=None):
        self._conn = db_conn_func or db_conn
        self._lock = threading.RLock()

    def register_source(
        self,
        source_id: str,
        name: str,
        type: str,
        authority: Optional[str] = None,
        country: Optional[str] = None,
        provenance: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[DataSource]:
        """注册新数据源。"""
        try:
            with self._lock:
                conn = self._conn()

                # 检查是否已存在
                existing = conn.execute(
                    "SELECT source_id FROM gfe_sources WHERE source_id = ?",
                    (source_id,)
                ).fetchone()

                if existing:
                    # 更新现有源
                    conn.execute(
                        """UPDATE gfe_sources
                           SET name=?, type=?, authority=?, country=?, provenance=?,
                               metadata=?, last_updated=?
                           WHERE source_id=?""",
                        (
                            name, type, authority, country, provenance,
                            json.dumps(metadata or {}),
                            datetime.now().isoformat(),
                            source_id,
                        )
                    )
                else:
                    # 插入新源
                    conn.execute(
                        """INSERT INTO gfe_sources
                           (source_id, name, type, authority, country, provenance,
                            metadata, created_at, last_updated)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            source_id, name, type, authority, country, provenance,
                            json.dumps(metadata or {}),
                            datetime.now().isoformat(),
                            datetime.now().isoformat(),
                        )
                    )

                conn.commit()

            # 构建 DataSource 对象
            ds = self.get_source(source_id)
            if ds:
                # 发布 EventBus 事件
                self._emit_event(TOPIC_SOURCE_REGISTERED, ds.to_dict())
                return ds

            return None

        except Exception as e:
            print(f"[SourceManager] 注册失败: {e}")
            return None

    def get_source(self, source_id: str) -> Optional[DataSource]:
        """获取单个数据源。"""
        try:
            conn = self._conn()
            row = conn.execute(
                "SELECT * FROM gfe_sources WHERE source_id = ?",
                (source_id,)
            ).fetchone()

            if not row:
                return None

            return self._row_to_ds(row)

        except Exception as e:
            print(f"[SourceManager] 查询失败: {e}")
            return None

    def list_sources(self, type_filter: Optional[str] = None) -> List[DataSource]:
        """列出所有数据源。"""
        try:
            conn = self._conn()

            if type_filter:
                rows = conn.execute(
                    "SELECT * FROM gfe_sources WHERE type = ? ORDER BY created_at DESC",
                    (type_filter,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM gfe_sources ORDER BY created_at DESC"
                ).fetchall()

            return [self._row_to_ds(row) for row in rows]

        except Exception as e:
            print(f"[SourceManager] 查询失败: {e}")
            return []

    def update_reliability(
        self,
        source_id: str,
        new_reliability: float,
        historical_accuracy: Optional[float] = None,
    ) -> bool:
        """更新数据源可信度。"""
        try:
            with self._lock:
                conn = self._conn()

                # 获取旧值
                old = conn.execute(
                    "SELECT reliability, historical_accuracy, type, last_updated FROM gfe_sources WHERE source_id = ?",
                    (source_id,)
                ).fetchone()

                if not old:
                    return False

                old_reliability = float(old[0]) if old[0] else 0.5
                
                # Parse last_updated from string to timestamp
                old_last_updated = None
                if old[3]:
                    try:
                        old_last_updated = datetime.fromisoformat(old[3]).timestamp()
                    except (ValueError, TypeError):
                        pass

                # 计算新的综合可信度
                row = conn.execute(
                    "SELECT type, last_updated FROM gfe_sources WHERE source_id = ?",
                    (source_id,)
                ).fetchone()

                if not row:
                    return False

                new_historical = historical_accuracy or (float(old[1]) if old[1] else 0.0)
                calculated = ReliabilityCalculator.calculate(
                    base_reliability=new_reliability,
                    historical_accuracy=new_historical,
                    source_type=row[0],
                    last_updated=old_last_updated,
                )

                conn.execute(
                    """UPDATE gfe_sources
                       SET reliability=?, historical_accuracy=?, last_updated=?
                       WHERE source_id=?""",
                    (
                        calculated,
                        new_historical,
                        datetime.now().isoformat(),
                        source_id,
                    )
                )
                conn.commit()

            # 发布 EventBus 事件（如果可信度变化）
            if abs(calculated - old_reliability) > 0.01:
                ds = self.get_source(source_id)
                if ds:
                    self._emit_event(TOPIC_SOURCE_RELIABILITY_CHANGED, {
                        "source_id": source_id,
                        "old_reliability": old_reliability,
                        "new_reliability": calculated,
                    })

            return True

        except Exception as e:
            print(f"[SourceManager] 更新失败: {e}")
            return False

    def calculate_score(self, source_id: str) -> Optional[float]:
        """计算数据源综合得分。"""
        try:
            ds = self.get_source(source_id)
            if not ds:
                return None

            return ReliabilityCalculator.calculate(
                base_reliability=ds.reliability,
                historical_accuracy=ds.historical_accuracy,
                source_type=ds.type,
                last_updated=ds.last_updated,
            )

        except Exception as e:
            print(f"[SourceManager] 计算失败: {e}")
            return None

    def remove_source(self, source_id: str) -> bool:
        """删除数据源。"""
        try:
            conn = self._conn()
            conn.execute(
                "DELETE FROM gfe_sources WHERE source_id = ?",
                (source_id,)
            )
            conn.commit()
            return True

        except Exception as e:
            print(f"[SourceManager] 删除失败: {e}")
            return False

    def seed_initial_sources(self):
        """初始化示例数据源。"""
        seeds = [
            {
                "source_id": "imf_wdi",
                "name": "IMF World Economic Outlook",
                "type": TYPE_INTERNATIONAL,
                "authority": "International Monetary Fund",
                "country": None,
                "provenance": "https://www.imf.org/en/Data",
                "metadata": {"update_frequency": "semi-annual", "coverage": "global"},
            },
            {
                "source_id": "uscensus",
                "name": "U.S. Census Bureau",
                "type": TYPE_OFFICIAL,
                "authority": "U.S. Government",
                "country": "US",
                "provenance": "https://www.census.gov/",
                "metadata": {"update_frequency": "monthly", "coverage": "US"},
            },
            {
                "source_id": "bls_indicators",
                "name": "BLS Economic Indicators",
                "type": TYPE_FINANCIAL,
                "authority": "Bureau of Labor Statistics",
                "country": "US",
                "provenance": "https://www.bls.gov/data/",
                "metadata": {"update_frequency": "monthly", "coverage": "employment"},
            },
            {
                "source_id": "worldbank_open_data",
                "name": "World Bank Open Data",
                "type": TYPE_OPEN_DATA,
                "authority": "World Bank Group",
                "country": None,
                "provenance": "https://data.worldbank.org/",
                "metadata": {"update_frequency": "annual", "coverage": "global"},
            },
            {
                "source_id": "nber_macro",
                "name": "NBER Macroeconomic Database",
                "type": TYPE_ACADEMIC,
                "authority": "National Bureau of Economic Research",
                "country": "US",
                "provenance": "https://www.nber.org/data/",
                "metadata": {"update_frequency": "quarterly", "coverage": "macro"},
            },
        ]

        for seed in seeds:
            self.register_source(**seed)

    def _row_to_ds(self, row) -> DataSource:
        """将 DB 行转换为 DataSource 对象。"""
        # row[11] and row[12] are TEXT (ISO format), need to parse to float
        created_at = None
        last_updated = None
        if row[11]:
            try:
                created_at = datetime.fromisoformat(row[11]).timestamp()
            except (ValueError, TypeError):
                created_at = time.time()
        if row[12]:
            try:
                last_updated = datetime.fromisoformat(row[12]).timestamp()
            except (ValueError, TypeError):
                last_updated = time.time()
        
        return DataSource(
            source_id=row[0],
            name=row[1],
            type=row[2],
            authority=row[3],
            country=row[4],
            reliability=float(row[5]) if row[5] else 0.5,
            historical_accuracy=float(row[6]) if row[6] else 0.0,
            update_frequency=row[7],
            license=row[8],
            provenance=row[9],
            metadata=json.loads(row[10]) if row[10] else {},
            created_at=created_at or time.time(),
            last_updated=last_updated or time.time(),
        )

    def _emit_event(self, event_type: str, payload: Dict[str, Any]):
        """发布 EventBus 事件。"""
        try:
            from eventbus import publish_system
            publish_system(event_type, payload)
        except Exception as e:
            print(f"[SourceManager] EventBus 发布失败: {e}")


# ============================================================
# Singleton Instance
# ============================================================

_instance: Optional[SourceManager] = None
_instance_lock = threading.Lock()


def get_source_manager() -> SourceManager:
    """获取单例 SourceManager。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = SourceManager()
        return _instance


def reset_source_manager():
    """重置单例（仅用于测试）。"""
    global _instance
    with _instance_lock:
        _instance = None
