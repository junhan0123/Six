#!/usr/bin/env python3
"""PHASE 142 — GFE Historical Comparison Foundation

Global Foresight Engine (GFE) 历史比较层基础实现。
职责：
- 历史案例存储与查询
- 基于权重的相似度计算
- 历史参照与当前状态比对
- 事件总线集成

架构边界：
- 不使用机器学习模型
- 不调用 Runtime/Execution
- 仅做历史类比分析
- 保持数据追溯性（provenance）
"""

from __future__ import annotations

import json
import time
import uuid
import threading
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any

from db import db_conn
from eventbus import publish_system


# ============================================================
# Constants
# ============================================================

# EventBus Topics
TOPIC_HISTORICAL_CASE_ADDED = "gfe_historical_case_added"
TOPIC_HISTORICAL_COMPARISON_COMPLETED = "gfe_historical_comparison_completed"
TOPIC_SIMILARITY_CALCULATED = "gfe_similarity_calculated"

# Category constants
CATEGORY_FINANCE = "finance"
CATEGORY_ENERGY = "energy"
CATEGORY_TECHNOLOGY = "technology"
CATEGORY_ECONOMY = "economy"
CATEGORY_DIPLOMACY = "diplomacy"
CATEGORY_MILITARY = "military"
CATEGORY_SOCIAL = "social"

ALL_CATEGORIES = [
    CATEGORY_FINANCE, CATEGORY_ENERGY, CATEGORY_TECHNOLOGY,
    CATEGORY_ECONOMY, CATEGORY_DIPLOMACY, CATEGORY_MILITARY,
    CATEGORY_SOCIAL
]

# 相似度维度权重
DIMENSION_WEIGHTS = {
    "economy": 0.25,
    "finance": 0.20,
    "technology": 0.15,
    "energy": 0.10,
    "trade": 0.10,
    "industry": 0.10,
    "social": 0.10,
}

# 默认权重（如果维度不在字典中）
DEFAULT_WEIGHT = 0.10


# ============================================================
# Data Models
# ============================================================

@dataclass
class HistoricalCase:
    """历史案例模型。"""
    case_id: str
    title: str
    period_start: Optional[float]
    period_end: Optional[float]
    country_code: Optional[str]
    category: str
    description: Optional[str]
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    event_refs: List[str] = field(default_factory=list)
    outcome: Optional[str] = None
    lessons: Optional[str] = None
    provenance: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "country_code": self.country_code,
            "category": self.category,
            "description": self.description,
            "state_snapshot": self.state_snapshot,
            "event_refs": self.event_refs,
            "outcome": self.outcome,
            "lessons": self.lessons,
            "provenance": self.provenance,
            "created_at": self.created_at
        }


@dataclass
class HistoricalMatch:
    """历史比对结果模型。"""
    match_id: str
    current_reference: str
    case_id: str
    similarity_score: float
    matching_dimensions: List[str]
    explanation: Optional[str]
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "current_reference": self.current_reference,
            "case_id": self.case_id,
            "similarity_score": self.similarity_score,
            "matching_dimensions": self.matching_dimensions,
            "explanation": self.explanation,
            "confidence": self.confidence,
            "created_at": self.created_at
        }


# ============================================================
# Historical Comparison Engine
# ============================================================

class HistoricalComparisonEngine:
    """历史比较引擎。

    核心功能：
    - 添加历史案例
    - 查询历史案例
    - 计算当前状态与历史案例的相似度
    - 生成比对报告
    """

    def __init__(self, db_conn_func=None):
        self._conn = db_conn_func or db_conn
        self._lock = threading.RLock()

    def add_case(
        self,
        title: str,
        category: str,
        description: Optional[str] = None,
        period_start: Optional[float] = None,
        period_end: Optional[float] = None,
        country_code: Optional[str] = None,
        state_snapshot: Optional[Dict[str, Any]] = None,
        event_refs: Optional[List[str]] = None,
        outcome: Optional[str] = None,
        lessons: Optional[str] = None,
        provenance: Optional[str] = None
    ) -> Optional[HistoricalCase]:
        """添加历史案例。

        Args:
            title: 案例标题
            category: 案例类别
            description: 描述
            period_start: 时期开始时间戳
            period_end: 时期结束时间戳
            country_code: 关联国家代码
            state_snapshot: 状态快照 JSON
            event_refs: 关联事件 ID 列表
            outcome: 结果描述
            lessons: 经验教训
            provenance: 来源追溯

        Returns:
            HistoricalCase 或 None（失败时）
        """
        try:
            with self._lock:
                conn = self._conn()
                case_id = f"case_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_historical_cases
                       (case_id, title, period_start, period_end, country_code,
                        category, description, state_snapshot, event_refs,
                        outcome, lessons, provenance, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        case_id, title, period_start, period_end, country_code,
                        category, description,
                        json.dumps(state_snapshot or {}),
                        json.dumps(event_refs or []),
                        outcome, lessons, provenance, now
                    )
                )
                conn.commit()

                case = HistoricalCase(
                    case_id=case_id,
                    title=title,
                    period_start=period_start,
                    period_end=period_end,
                    country_code=country_code,
                    category=category,
                    description=description,
                    state_snapshot=state_snapshot or {},
                    event_refs=event_refs or [],
                    outcome=outcome,
                    lessons=lessons,
                    provenance=provenance,
                    created_at=now
                )

                # 发布 EventBus 事件
                self._emit_event(TOPIC_HISTORICAL_CASE_ADDED, {
                    "case_id": case_id,
                    "title": title,
                    "category": category,
                    "country_code": country_code,
                    "timestamp": now
                })

                return case

        except Exception as e:
            print(f"[HistoricalComparison] 添加案例失败: {e}")
            return None

    def get_cases(
        self,
        category: Optional[str] = None,
        country_code: Optional[str] = None,
        limit: int = 50
    ) -> List[HistoricalCase]:
        """查询历史案例。"""
        try:
            conn = self._conn()
            query = "SELECT * FROM gfe_historical_cases WHERE 1=1"
            params = []

            if category:
                query += " AND category = ?"
                params.append(category)
            if country_code:
                query += " AND country_code = ?"
                params.append(country_code)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_case(row) for row in rows if row]

        except Exception as e:
            print(f"[HistoricalComparison] 查询案例失败: {e}")
            return []

    def compare_state(
        self,
        country_code: str,
        current_state: Dict[str, Any],
        top_k: int = 10
    ) -> List[HistoricalMatch]:
        """比对当前状态与历史案例。

        Args:
            country_code: 当前国家代码
            current_state: 当前状态数据
            top_k: 返回最多结果数

        Returns:
            相似度排名列表，按 similarity_score 降序
        """
        try:
            with self._lock:
                conn = self._conn()

                # 获取所有历史案例
                rows = conn.execute(
                    "SELECT * FROM gfe_historical_cases ORDER BY created_at DESC"
                ).fetchall()

                matches = []
                now = time.time()

                for row in rows:
                    case = self._row_to_case(row)

                    # 计算相似度
                    score, dimensions, explanation = self.calculate_similarity(
                        current_state,
                        case.state_snapshot
                    )

                    # 只保留有匹配的结果
                    if score > 0.1:  # 最低相似度阈值
                        match_id = f"match_{int(now)}_{uuid.uuid4().hex[:6]}"
                        match = HistoricalMatch(
                            match_id=match_id,
                            current_reference=country_code,
                            case_id=case.case_id,
                            similarity_score=round(score, 3),
                            matching_dimensions=dimensions,
                            explanation=explanation,
                            confidence=0.7
                        )
                        matches.append(match)

                        # 持久化匹配结果
                        self._save_match(match)

                # 按相似度排序
                matches.sort(key=lambda x: x.similarity_score, reverse=True)

                # 只返回 top_k
                matches = matches[:top_k]

                # 发布 EventBus 事件
                self._emit_event(TOPIC_HISTORICAL_COMPARISON_COMPLETED, {
                    "country_code": country_code,
                    "match_count": len(matches),
                    "top_score": matches[0].similarity_score if matches else 0,
                    "timestamp": now
                })

                return matches

        except Exception as e:
            print(f"[HistoricalComparison] 状态比对失败: {e}")
            return []

    def calculate_similarity(
        self,
        current_state: Dict[str, Any],
        historical_state: Dict[str, Any]
    ) -> tuple:
        """计算两个状态之间的加权相似度。

        算法：
        - 遍历所有维度
        - 对数值型字段计算绝对差异并归一化
        - 按预定义权重累加
        - 最终分数 = 1 - 加权平均差异

        Returns:
            (score, matching_dimensions, explanation)
        """
        try:
            total_weight = 0.0
            weighted_diff = 0.0
            matching_dims = []
            explanations = []

            # 遍历所有维度
            for dim in DIMENSION_WEIGHTS:
                weight = DIMENSION_WEIGHTS[dim]
                current_val = current_state.get(dim, {})
                historical_val = historical_state.get(dim, {})

                if not current_val or not historical_val:
                    continue

                # 提取关键指标
                current_metrics = self._extract_metrics(current_val)
                historical_metrics = self._extract_metrics(historical_val)

                # 计算该维度的相似度
                dim_score, dim_diff = self._calculate_dimension_similarity(
                    current_metrics,
                    historical_metrics
                )

                weighted_diff += dim_diff * weight
                total_weight += weight

                # 记录匹配维度
                if dim_score > 0.6:
                    matching_dims.append(dim)
                    explanations.append(f"{dim}: {dim_score:.2f}")

            # 计算最终相似度
            if total_weight > 0:
                final_score = max(0.0, 1.0 - (weighted_diff / total_weight))
            else:
                final_score = 0.0

            explanation = "; ".join(explanations[:3]) if explanations else "No direct dimension matches"

            return round(final_score, 3), matching_dims, explanation

        except Exception as e:
            print(f"[HistoricalComparison] 相似度计算失败: {e}")
            return 0.0, [], str(e)

    def get_matches(
        self,
        current_reference: Optional[str] = None,
        case_id: Optional[str] = None,
        min_score: float = 0.0,
        limit: int = 50
    ) -> List[HistoricalMatch]:
        """查询历史比对结果。"""
        try:
            conn = self._conn()
            query = "SELECT * FROM gfe_historical_matches WHERE 1=1"
            params = []

            if current_reference:
                query += " AND current_reference = ?"
                params.append(current_reference)
            if case_id:
                query += " AND case_id = ?"
                params.append(case_id)
            if min_score > 0:
                query += " AND similarity_score >= ?"
                params.append(min_score)

            query += " ORDER BY similarity_score DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_match(row) for row in rows if row]

        except Exception as e:
            print(f"[HistoricalComparison] 查询匹配结果失败: {e}")
            return []

    # ---- 内部方法 ----

    def _extract_metrics(self, state_data: Dict[str, Any]) -> Dict[str, float]:
        """从状态数据中提取数值型指标。"""
        metrics = {}
        for key, value in state_data.items():
            if isinstance(value, (int, float)):
                metrics[key] = float(value)
            elif isinstance(value, str):
                # 尝试解析数字字符串
                try:
                    metrics[key] = float(value)
                except (ValueError, TypeError):
                    pass
        return metrics

    def _calculate_dimension_similarity(
        self,
        current: Dict[str, float],
        historical: Dict[str, float]
    ) -> tuple:
        """计算单个维度的相似度。

        Returns:
            (dimension_score, dimension_diff)
        """
        if not current or not historical:
            return 0.0, 1.0

        # 找共同指标
        common_keys = set(current.keys()) & set(historical.keys())
        if not common_keys:
            return 0.0, 1.0

        total_diff = 0.0
        count = 0

        for key in common_keys:
            curr_val = current[key]
            hist_val = historical[key]

            # 避免除零
            if hist_val == 0:
                if curr_val == 0:
                    diff = 0.0
                else:
                    diff = 1.0
            else:
                diff = abs(curr_val - hist_val) / abs(hist_val)
                diff = min(diff, 2.0)  # 限制最大差异为 200%

            total_diff += diff
            count += 1

        avg_diff = total_diff / count if count > 0 else 1.0
        dimension_score = max(0.0, 1.0 - avg_diff)

        return dimension_score, avg_diff

    def _save_match(self, match: HistoricalMatch):
        """持久化匹配结果。"""
        try:
            conn = self._conn()
            conn.execute(
                """INSERT INTO gfe_historical_matches
                   (match_id, current_reference, case_id, similarity_score,
                    matching_dimensions, explanation, confidence, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    match.match_id, match.current_reference, match.case_id,
                    match.similarity_score,
                    json.dumps(match.matching_dimensions),
                    match.explanation,
                    match.confidence,
                    match.created_at
                )
            )
            conn.commit()
        except Exception as e:
            print(f"[HistoricalComparison] 保存匹配失败: {e}")

    def _row_to_case(self, row) -> HistoricalCase:
        """将 DB 行转换为 HistoricalCase 对象。"""
        try:
            state_snapshot = json.loads(row[7] or "{}")
        except (json.JSONDecodeError, TypeError):
            state_snapshot = {}

        try:
            event_refs = json.loads(row[8] or "[]")
        except (json.JSONDecodeError, TypeError):
            event_refs = []

        return HistoricalCase(
            case_id=row[0],
            title=row[1],
            period_start=float(row[2]) if row[2] else None,
            period_end=float(row[3]) if row[3] else None,
            country_code=row[4],
            category=row[5],
            description=row[6],
            state_snapshot=state_snapshot,
            event_refs=event_refs,
            outcome=row[9],
            lessons=row[10],
            provenance=row[11],
            created_at=float(row[12]) if row[12] else time.time()
        )

    def _row_to_match(self, row) -> HistoricalMatch:
        """将 DB 行转换为 HistoricalMatch 对象。"""
        try:
            matching_dimensions = json.loads(row[4] or "[]")
        except (json.JSONDecodeError, TypeError):
            matching_dimensions = []

        return HistoricalMatch(
            match_id=row[0],
            current_reference=row[1],
            case_id=row[2],
            similarity_score=float(row[3]) if row[3] else 0.0,
            matching_dimensions=matching_dimensions,
            explanation=row[5],
            confidence=float(row[6]) if row[6] else 0.5,
            created_at=float(row[7]) if row[7] else time.time()
        )

    def _emit_event(self, event_type: str, payload: Dict[str, Any]):
        """发布 EventBus 事件。"""
        try:
            publish_system(event_type, payload, source="gfe_historical")
        except Exception as e:
            print(f"[HistoricalComparison] EventBus 发布失败: {e}")


# ============================================================
# Seed Data
# ============================================================

def seed_historical_cases():
    """初始化种子历史案例。"""
    engine = HistoricalComparisonEngine()

    # 2008 Global Financial Crisis
    engine.add_case(
        title="2008 Global Financial Crisis",
        category=CATEGORY_FINANCE,
        description="Subprime mortgage crisis triggered global financial meltdown",
        period_start=1200000000,  # 2008
        period_end=1230000000,    # 2009
        country_code="US",
        state_snapshot={
            "finance": {"credit_crunch": 0.9, "bank_failures": 15, "stock_drop": -0.5},
            "economy": {"gdp_growth": -3.5, "unemployment": 0.1},
            "trade": {"exports_drop": -0.2, "imports_drop": -0.25}
        },
        outcome="Massive government bailouts, quantitative easing, Dodd-Frank Act",
        lessons="Systemic risk contagion, regulatory gaps in derivatives",
        provenance="Federal Reserve, IMF, World Bank reports"
    )

    # 1997 Asian Financial Crisis
    engine.add_case(
        title="1997 Asian Financial Crisis",
        category=CATEGORY_FINANCE,
        description="Currency crisis spreads from Thailand to multiple Asian economies",
        period_start=860000000,   # 1997
        period_end=890000000,    # 1998
        country_code="TH",
        state_snapshot={
            "finance": {"currency_devalue": 0.5, "reserve_drop": -0.4},
            "economy": {"gdp_growth": -10.0, "capital_flight": 0.8},
            "trade": {"export_decline": -0.3}
        },
        outcome="IMF bailout packages, structural reforms, currency pegs abandoned",
        lessons="Fixed exchange rates vulnerable to speculative attacks",
        provenance="IMF Articles of Agreement, ASEAN documents"
    )

    # 1970s Oil Crisis
    engine.add_case(
        title="1970s Oil Crisis",
        category=CATEGORY_ENERGY,
        description="OPEC oil embargo causes energy price shock and stagflation",
        period_start=150000000,   # 1973
        period_end=210000000,    # 1974
        country_code="US",
        state_snapshot={
            "energy": {"oil_price_shock": 4.0, "supply_disruption": 0.9},
            "economy": {"inflation": 0.12, "gdp_stagnation": -0.03},
            "trade": {"oil_imports_increase": 0.6}
        },
        outcome="Strategic Petroleum Reserve created, fuel economy standards (CAFE)",
        lessons="Energy dependency creates macroeconomic vulnerability",
        provenance="US Energy Information Administration, OPEC records"
    )

    # 2000 Dot-com Bubble
    engine.add_case(
        title="2000 Dot-com Bubble",
        category=CATEGORY_TECHNOLOGY,
        description="Technology stock speculation bubble bursts",
        period_start=946684800,   # 2000
        period_end=978307200,    # 2001
        country_code="US",
        state_snapshot={
            "technology": {"tech_stock_drop": -0.78, "ipo_crash": 0.9},
            "economy": {"gdp_growth": -0.01, "employment_tech": -0.15},
            "finance": {"market_cap_loss": -5000}
        },
        outcome="NASDAQ drops 78%, many tech companies bankruptcy",
        lessons="Speculative bubbles in technology sectors",
        provenance="SEC filings, NASDAQ historical data"
    )

    # 1980 Volcker Inflation Cycle
    engine.add_case(
        title="1980 Volcker Inflation Cycle",
        category=CATEGORY_ECONOMY,
        description="Federal Reserve raises interest rates to combat inflation",
        period_start=252460800,   # 1980
        period_end=315571200,    # 1981
        country_code="US",
        state_snapshot={
            "economy": {"inflation_rate": 0.135, "interest_rate": 0.20},
            "finance": {"bond_yield_surge": 0.5, "recession_risk": 0.9},
            "social": {"unemployment": 0.075}
        },
        outcome="Inflation tamed but recession occurs, unemployment peaks at 10.8%",
        lessons="Monetary tightening can break inflation expectations but causes pain",
        provenance="Federal Reserve records, Bureau of Labor Statistics"
    )

    # Additional cases for richer comparison
    engine.add_case(
        title="European Sovereign Debt Crisis",
        category=CATEGORY_FINANCE,
        description="Greece and other Eurozone countries face debt sustainability crisis",
        period_start=1293840000,  # 2011
        period_end=1356998400,   # 2012
        country_code="GR",
        state_snapshot={
            "finance": {"bond_yield_surge": 0.8, "bailout_amount": 240},
            "economy": {"gdp_contract": -0.25, "austerity_measure": 0.9},
            "social": {"unemployment": 0.27, "protest_intensity": 0.8}
        },
        outcome="EU/IMF bailout packages, severe austerity, political upheaval",
        lessons="Currency union without fiscal union creates fragility",
        provenance="European Central Bank, IMF Country Reports"
    )

    print(f"[HistoricalComparison] Seeded 6 historical cases")
    return True


# ============================================================
# Singleton
# ============================================================

_instance: Optional[HistoricalComparisonEngine] = None
_instance_lock = threading.Lock()


def get_historical_comparison_engine() -> HistoricalComparisonEngine:
    """获取单例 HistoricalComparisonEngine。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = HistoricalComparisonEngine()
        return _instance


def reset_historical_comparison_engine():
    """重置单例（用于测试）。"""
    global _instance
    with _instance_lock:
        _instance = None