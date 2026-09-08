#!/usr/bin/env python3
"""PHASE 146 — GFE Forecast Engine Foundation

Global Foresight Engine (GFE) 预测引擎基础实现。
职责：
- 预测创建与管理
- 多证据融合
- 概率预测结果保存
- Confidence 计算
- 预测版本追踪

架构边界：
- 只读访问其他 GFE 模块数据
- 不修改已有模块
- 不调用 Runtime/Execution
- 仅做预测推演
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
TOPIC_FORECAST_CREATED = "gfe_forecast_created"
TOPIC_FORECAST_UPDATED = "gfe_forecast_updated"

# Forecast statuses
STATUS_DRAFT = "draft"
STATUS_REVIEWED = "reviewed"
STATUS_FINAL = "final"
STATUS_ARCHIVED = "archived"

ALL_STATUSES = [STATUS_DRAFT, STATUS_REVIEWED, STATUS_FINAL, STATUS_ARCHIVED]

# Evidence source types
SOURCE_WORLD_STATE = "world_state"
SOURCE_EVENTS = "events"
SOURCE_HISTORIES = "histories"
SOURCE_CAUSAL = "causal"
SOURCE_ANALYSTS = "analysts"
SOURCE_SCENARIOS = "scenarios"

ALL_SOURCES = [
    SOURCE_WORLD_STATE, SOURCE_EVENTS, SOURCE_HISTORIES,
    SOURCE_CAUSAL, SOURCE_ANALYSTS, SOURCE_SCENARIOS
]


# ============================================================
# Data Models
# ============================================================

@dataclass
class Forecast:
    """预测模型。"""
    forecast_id: str
    question: str
    target: str
    prediction: str
    probability: float
    confidence: float
    time_horizon: Optional[int]
    status: str
    created_at: float
    updated_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "forecast_id": self.forecast_id,
            "question": self.question,
            "target": self.target,
            "prediction": self.prediction,
            "probability": round(self.probability, 3),
            "confidence": round(self.confidence, 3),
            "time_horizon": self.time_horizon,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


@dataclass
class ForecastEvidence:
    """预测证据模型。"""
    evidence_id: str
    forecast_id: str
    source_type: str
    source_ref: Optional[str]
    weight: float
    impact: float
    confidence: float
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "forecast_id": self.forecast_id,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "weight": round(self.weight, 3),
            "impact": round(self.impact, 3),
            "confidence": round(self.confidence, 3),
            "created_at": self.created_at
        }


@dataclass
class ForecastVersion:
    """预测版本模型。"""
    version_id: str
    forecast_id: str
    previous_prediction: Optional[str]
    new_prediction: str
    change_reason: Optional[str]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "forecast_id": self.forecast_id,
            "previous_prediction": self.previous_prediction,
            "new_prediction": self.new_prediction,
            "change_reason": self.change_reason,
            "created_at": self.created_at
        }


# ============================================================
# Forecast Engine
# ============================================================

class ForecastEngine:
    """预测引擎。

    核心功能：
    - 创建和管理预测
    - 添加证据
    - 计算置信度
    - 版本追踪
    - 多证据融合
    """

    def __init__(self, db_conn_func=None):
        self._conn = db_conn_func or db_conn
        self._lock = threading.RLock()
        # 内存缓存
        self._forecasts: Dict[str, Forecast] = {}
        self._refresh_cache()

    def _refresh_cache(self):
        """刷新内存缓存。"""
        try:
            conn = self._conn()
            for row in conn.execute("SELECT * FROM gfe_forecasts").fetchall():
                forecast = self._row_to_forecast(row)
                self._forecasts[forecast.forecast_id] = forecast
        except Exception as e:
            print(f"[ForecastEngine] 刷新缓存失败: {e}")

    def create_forecast(
        self,
        question: str,
        target: str,
        prediction: str,
        probability: float = 0.5,
        confidence: float = 0.5,
        time_horizon: Optional[int] = None,
        status: str = STATUS_DRAFT
    ) -> Optional[Forecast]:
        """创建预测。"""
        try:
            with self._lock:
                conn = self._conn()
                forecast_id = f"forecast_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_forecasts
                       (forecast_id, question, target, prediction, probability, confidence,
                        time_horizon, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        forecast_id, question, target, prediction,
                        probability, confidence, time_horizon, status, now, now
                    )
                )
                conn.commit()

                forecast = Forecast(
                    forecast_id=forecast_id,
                    question=question,
                    target=target,
                    prediction=prediction,
                    probability=probability,
                    confidence=confidence,
                    time_horizon=time_horizon,
                    status=status,
                    created_at=now,
                    updated_at=now
                )
                self._forecasts[forecast_id] = forecast

                # 发布 EventBus 事件
                self._emit_event(TOPIC_FORECAST_CREATED, {
                    "forecast_id": forecast_id,
                    "question": question,
                    "target": target,
                    "timestamp": now
                })

                return forecast

        except Exception as e:
            print(f"[ForecastEngine] 创建预测失败: {e}")
            return None

    def add_evidence(
        self,
        forecast_id: str,
        source_type: str,
        source_ref: Optional[str] = None,
        weight: float = 0.5,
        impact: float = 0.5,
        confidence: float = 0.5
    ) -> Optional[ForecastEvidence]:
        """添加预测证据。"""
        try:
            with self._lock:
                conn = self._conn()

                # 验证预测存在
                if forecast_id not in self._forecasts:
                    row = conn.execute(
                        "SELECT * FROM gfe_forecasts WHERE forecast_id = ?",
                        (forecast_id,)
                    ).fetchone()
                    if not row:
                        return None
                    self._forecasts[forecast_id] = self._row_to_forecast(row)

                evidence_id = f"evidence_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_forecast_evidence
                       (evidence_id, forecast_id, source_type, source_ref, weight, impact, confidence, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (evidence_id, forecast_id, source_type, source_ref, weight, impact, confidence, now)
                )
                conn.commit()

                return ForecastEvidence(
                    evidence_id=evidence_id,
                    forecast_id=forecast_id,
                    source_type=source_type,
                    source_ref=source_ref,
                    weight=weight,
                    impact=impact,
                    confidence=confidence,
                    created_at=now
                )

        except Exception as e:
            print(f"[ForecastEngine] 添加证据失败: {e}")
            return None

    def update_forecast(
        self,
        forecast_id: str,
        prediction: Optional[str] = None,
        probability: Optional[float] = None,
        confidence: Optional[float] = None,
        status: Optional[str] = None,
        change_reason: Optional[str] = None
    ) -> Optional[Forecast]:
        """更新预测。"""
        try:
            with self._lock:
                conn = self._conn()

                # 获取现有预测
                if forecast_id not in self._forecasts:
                    row = conn.execute(
                        "SELECT * FROM gfe_forecasts WHERE forecast_id = ?",
                        (forecast_id,)
                    ).fetchone()
                    if not row:
                        return None
                    self._forecasts[forecast_id] = self._row_to_forecast(row)

                forecast = self._forecasts[forecast_id]
                old_prediction = forecast.prediction
                now = time.time()

                # 构建更新语句
                updates = []
                params = []
                if prediction is not None:
                    updates.append("prediction = ?")
                    params.append(prediction)
                if probability is not None:
                    updates.append("probability = ?")
                    params.append(probability)
                if confidence is not None:
                    updates.append("confidence = ?")
                    params.append(confidence)
                if status is not None:
                    updates.append("status = ?")
                    params.append(status)
                updates.append("updated_at = ?")
                params.append(now)
                params.append(forecast_id)

                conn.execute(
                    f"UPDATE gfe_forecasts SET {', '.join(updates)} WHERE forecast_id = ?",
                    params
                )
                conn.commit()

                # 记录版本
                if prediction is not None and prediction != old_prediction:
                    version_id = f"version_{int(time.time())}_{uuid.uuid4().hex[:6]}"
                    conn.execute(
                        """INSERT INTO gfe_forecast_versions
                           (version_id, forecast_id, previous_prediction, new_prediction, change_reason, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (version_id, forecast_id, old_prediction, prediction, change_reason, now)
                    )
                    conn.commit()

                # 刷新缓存
                updated_row = conn.execute(
                    "SELECT * FROM gfe_forecasts WHERE forecast_id = ?",
                    (forecast_id,)
                ).fetchone()
                if updated_row:
                    self._forecasts[forecast_id] = self._row_to_forecast(updated_row)
                    forecast = self._forecasts[forecast_id]

                # 发布 EventBus 事件
                self._emit_event(TOPIC_FORECAST_UPDATED, {
                    "forecast_id": forecast_id,
                    "question": forecast.question,
                    "timestamp": now
                })

                return forecast

        except Exception as e:
            print(f"[ForecastEngine] 更新预测失败: {e}")
            return None

    def calculate_confidence(self, forecast_id: str) -> Optional[float]:
        """计算预测置信度。

        基于证据的权重和置信度加权平均。
        """
        try:
            conn = self._conn()

            # 获取所有证据
            rows = conn.execute(
                "SELECT * FROM gfe_forecast_evidence WHERE forecast_id = ?",
                (forecast_id,)
            ).fetchall()

            if not rows:
                # 无证据时使用预测本身的置信度
                if forecast_id in self._forecasts:
                    return self._forecasts[forecast_id].confidence
                return 0.5

            total_weight = 0.0
            weighted_confidence = 0.0

            for row in rows:
                weight = float(row[5]) if row[5] else 0.5
                confidence = float(row[7]) if row[7] else 0.5
                total_weight += weight
                weighted_confidence += weight * confidence

            if total_weight > 0:
                result = weighted_confidence / total_weight
                return max(0.0, min(1.0, result))  # 限制在 [0, 1]
            return 0.5

        except Exception as e:
            print(f"[ForecastEngine] 计算置信度失败: {e}")
            return None

    def merge_evidence(self, forecast_id: str) -> Dict[str, Any]:
        """融合多证据。

        读取其他 GFE 模块的数据进行证据融合。
        """
        try:
            conn = self._conn()
            result = {
                "forecast_id": forecast_id,
                "sources": {},
                "total_evidence": 0,
                "fused_confidence": 0.0
            }

            # 读取各模块数据（只读）
            # 1. 世界状态
            world_state_evidence = self._collect_world_state_evidence(forecast_id)
            result["sources"][SOURCE_WORLD_STATE] = world_state_evidence

            # 2. 事件数据
            events_evidence = self._collect_events_evidence(forecast_id)
            result["sources"][SOURCE_EVENTS] = events_evidence

            # 3. 历史案例
            histories_evidence = self._collect_histories_evidence(forecast_id)
            result["sources"][SOURCE_HISTORIES] = histories_evidence

            # 4. 因果图
            causal_evidence = self._collect_causal_evidence(forecast_id)
            result["sources"][SOURCE_CAUSAL] = causal_evidence

            # 5. 分析师报告
            analysts_evidence = self._collect_analysts_evidence(forecast_id)
            result["sources"][SOURCE_ANALYSTS] = analysts_evidence

            # 6. 情景数据
            scenarios_evidence = self._collect_scenarios_evidence(forecast_id)
            result["sources"][SOURCE_SCENARIOS] = scenarios_evidence

            # 计算总证据数
            result["total_evidence"] = sum(len(v) for v in result["sources"].values())

            # 融合置信度
            result["fused_confidence"] = self._calculate_fused_confidence(result["sources"])

            return result

        except Exception as e:
            print(f"[ForecastEngine] 融合证据失败: {e}")
            return {}

    def get_forecast(self, forecast_id: str) -> Optional[Forecast]:
        """获取单个预测。"""
        if forecast_id in self._forecasts:
            return self._forecasts[forecast_id]

        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM gfe_forecasts WHERE forecast_id = ?",
            (forecast_id,)
        ).fetchone()

        if row:
            forecast = self._row_to_forecast(row)
            self._forecasts[forecast_id] = forecast
            return forecast

        return None

    def get_forecasts(
        self,
        question: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Forecast]:
        """查询预测列表。"""
        try:
            conn = self._conn()
            query = "SELECT * FROM gfe_forecasts WHERE 1=1"
            params = []

            if question:
                query += " AND question = ?"
                params.append(question)
            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_forecast(row) for row in rows if row]

        except Exception as e:
            print(f"[ForecastEngine] 查询预测失败: {e}")
            return []

    def get_evidence(self, forecast_id: str) -> List[ForecastEvidence]:
        """查询预测证据。"""
        try:
            conn = self._conn()
            rows = conn.execute(
                "SELECT * FROM gfe_forecast_evidence WHERE forecast_id = ? ORDER BY created_at",
                (forecast_id,)
            ).fetchall()
            return [self._row_to_evidence(row) for row in rows if row]

        except Exception as e:
            print(f"[ForecastEngine] 查询证据失败: {e}")
            return []

    def get_versions(self, forecast_id: str) -> List[ForecastVersion]:
        """查询预测版本历史。"""
        try:
            conn = self._conn()
            rows = conn.execute(
                "SELECT * FROM gfe_forecast_versions WHERE forecast_id = ? ORDER BY created_at DESC",
                (forecast_id,)
            ).fetchall()
            return [self._row_to_version(row) for row in rows if row]

        except Exception as e:
            print(f"[ForecastEngine] 查询版本失败: {e}")
            return []

    # ---- 证据收集方法（只读访问其他模块）----

    def _collect_world_state_evidence(self, forecast_id: str) -> List[Dict]:
        """收集世界状态证据。"""
        try:
            conn = self._conn()
            # 读取 gfe_world_states 表（只读）
            rows = conn.execute(
                "SELECT * FROM gfe_world_states ORDER BY snapshot_time DESC LIMIT 10"
            ).fetchall()
            return [{"type": SOURCE_WORLD_STATE, "count": len(rows)}]
        except Exception:
            return []

    def _collect_events_evidence(self, forecast_id: str) -> List[Dict]:
        """收集事件证据。"""
        try:
            conn = self._conn()
            # 读取 gfe_events 表（只读）
            rows = conn.execute(
                "SELECT * FROM gfe_events ORDER BY event_time DESC LIMIT 20"
            ).fetchall()
            return [{"type": SOURCE_EVENTS, "count": len(rows)}]
        except Exception:
            return []

    def _collect_histories_evidence(self, forecast_id: str) -> List[Dict]:
        """收集历史案例证据。"""
        try:
            conn = self._conn()
            # 读取 gfe_historical_cases 表（只读）
            rows = conn.execute(
                "SELECT * FROM gfe_historical_cases ORDER BY period_start DESC LIMIT 10"
            ).fetchall()
            return [{"type": SOURCE_HISTORIES, "count": len(rows)}]
        except Exception:
            return []

    def _collect_causal_evidence(self, forecast_id: str) -> List[Dict]:
        """收集因果图谱证据。"""
        try:
            conn = self._conn()
            # 读取 gfe_causal_edges 表（只读）
            rows = conn.execute(
                "SELECT * FROM gfe_causal_edges ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
            return [{"type": SOURCE_CAUSAL, "count": len(rows)}]
        except Exception:
            return []

    def _collect_analysts_evidence(self, forecast_id: str) -> List[Dict]:
        """收集分析师报告证据。"""
        try:
            conn = self._conn()
            # 读取 gfe_analysis_reports 表（只读）
            rows = conn.execute(
                "SELECT * FROM gfe_analysis_reports ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
            return [{"type": SOURCE_ANALYSTS, "count": len(rows)}]
        except Exception:
            return []

    def _collect_scenarios_evidence(self, forecast_id: str) -> List[Dict]:
        """收集情景数据证据。"""
        try:
            conn = self._conn()
            # 读取 gfe_scenarios 表（只读）
            rows = conn.execute(
                "SELECT * FROM gfe_scenarios ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
            return [{"type": SOURCE_SCENARIOS, "count": len(rows)}]
        except Exception:
            return []

    def _calculate_fused_confidence(self, sources: Dict[str, Any]) -> float:
        """计算融合置信度。"""
        total_evidence = 0
        for s in sources.values():
            if isinstance(s, list):
                total_evidence += sum(item.get("count", 0) for item in s)
            elif isinstance(s, dict):
                total_evidence += s.get("count", 0)

        if total_evidence == 0:
            return 0.5

        # 简单加权：证据数量越多，置信度越高（上限 0.9）
        base_confidence = min(0.9, total_evidence / 20.0)
        return base_confidence

    # ---- 内部方法 ----

    def _row_to_forecast(self, row) -> Forecast:
        """将 DB 行转换为 Forecast 对象。"""
        return Forecast(
            forecast_id=row[0],
            question=row[1],
            target=row[2],
            prediction=row[3],
            probability=float(row[4]) if row[4] else 0.5,
            confidence=float(row[5]) if row[5] else 0.5,
            time_horizon=int(row[6]) if row[6] else None,
            status=row[7] if row[7] else STATUS_DRAFT,
            created_at=float(row[8]) if row[8] else time.time(),
            updated_at=float(row[9]) if row[9] else None
        )

    def _row_to_evidence(self, row) -> ForecastEvidence:
        """将 DB 行转换为 ForecastEvidence 对象。"""
        return ForecastEvidence(
            evidence_id=row[0],
            forecast_id=row[1],
            source_type=row[2],
            source_ref=row[3],
            weight=float(row[4]) if row[4] else 0.5,
            impact=float(row[5]) if row[5] else 0.5,
            confidence=float(row[6]) if row[6] else 0.5,
            created_at=float(row[7]) if row[7] else time.time()
        )

    def _row_to_version(self, row) -> ForecastVersion:
        """将 DB 行转换为 ForecastVersion 对象。"""
        return ForecastVersion(
            version_id=row[0],
            forecast_id=row[1],
            previous_prediction=row[2],
            new_prediction=row[3],
            change_reason=row[4],
            created_at=float(row[5]) if row[5] else time.time()
        )

    def _emit_event(self, event_type: str, payload: Dict[str, Any]):
        """发布 EventBus 事件。"""
        try:
            publish_system(event_type, payload, source="gfe_forecast")
        except Exception as e:
            print(f"[ForecastEngine] EventBus 发布失败: {e}")


# ============================================================
# Seed Data
# ============================================================

def seed_forecasts():
    """初始化种子预测。"""
    engine = ForecastEngine()

    # 预测1：中国经济增长
    f1 = engine.create_forecast(
        question="中国未来12个月GDP增速？",
        target="CN_GDP_growth",
        prediction="5.0%-5.5%",
        probability=0.65,
        confidence=0.7,
        time_horizon=365,
        status=STATUS_REVIEWED
    )

    if f1:
        engine.add_evidence(f1.forecast_id, SOURCE_WORLD_STATE, "CN_world_state_latest", 0.8, 0.7)
        engine.add_evidence(f1.forecast_id, SOURCE_HISTORIES, "historical_pattern_2019_2023", 0.6, 0.6)
        engine.add_evidence(f1.forecast_id, SOURCE_EVENTS, "recent_policy_announcements", 0.7, 0.65)

    # 预测2：美联储利率路径
    f2 = engine.create_forecast(
        question="美联储未来6个月利率路径？",
        target="US_interest_rate",
        prediction="维持高位或小幅下调",
        probability=0.6,
        confidence=0.65,
        time_horizon=180,
        status=STATUS_DRAFT
    )

    if f2:
        engine.add_evidence(f2.forecast_id, SOURCE_WORLD_STATE, "US_world_state_latest", 0.85, 0.8)
        engine.add_evidence(f2.forecast_id, SOURCE_ANALYSTS, "consensus_forecast_q3_2024", 0.75, 0.7)

    # 预测3：全球能源价格
    f3 = engine.create_forecast(
        question="未来12个月国际油价走势？",
        target="global_oil_price",
        prediction="$80-95/桶区间震荡",
        probability=0.55,
        confidence=0.6,
        time_horizon=365,
        status=STATUS_DRAFT
    )

    if f3:
        engine.add_evidence(f3.forecast_id, SOURCE_CAUSAL, "supply_demand_causal_model", 0.7, 0.65)
        engine.add_evidence(f3.forecast_id, SOURCE_SCENARIOS, "geopolitical_risk_scenario", 0.6, 0.55)

    print(f"[ForecastEngine] Seeded 3 forecasts")
    return True


# ============================================================
# Singleton
# ============================================================

_instance: Optional[ForecastEngine] = None
_instance_lock = threading.Lock()


def get_forecast_engine() -> ForecastEngine:
    """获取单例 ForecastEngine。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = ForecastEngine()
        return _instance


def reset_forecast_engine():
    """重置单例（用于测试）。"""
    global _instance
    with _instance_lock:
        _instance = None
