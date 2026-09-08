#!/usr/bin/env python3
"""PHASE 147 — GFE Forecast Ledger Foundation

Global Foresight Engine (GFE) 预测账本基础实现。
职责：
- 保存历史预测记录
- 记录实际结果
- 计算 Brier Score
- 预测准确率统计
- 校准度评估

架构边界：
- 只读访问其他 GFE 模块数据
- 不修改已有模块
- 不调用 Runtime/Execution
- 仅做预测评估和统计
"""

from __future__ import annotations

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

TOPIC_FORECAST_EVALUATED = "gfe_forecast_evaluated"
TOPIC_ACCURACY_UPDATED = "gfe_accuracy_updated"

TYPE_BINARY = "binary"
TYPE_PROBABILITY = "probability"
TYPE_RANGE = "range"
TYPE_DIRECTIONAL = "directional"
ALL_TYPES = [TYPE_BINARY, TYPE_PROBABILITY, TYPE_RANGE, TYPE_DIRECTIONAL]


# ============================================================
# Data Models
# ============================================================

@dataclass
class LedgerRecord:
    """预测账本记录模型。"""
    ledger_id: str
    forecast_id: str
    prediction: str
    actual_result: Optional[str]
    brier_score: Optional[float]
    accuracy_score: Optional[float]
    evaluated_at: Optional[float]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "forecast_id": self.forecast_id,
            "prediction": self.prediction,
            "actual_result": self.actual_result,
            "brier_score": round(self.brier_score, 3) if self.brier_score else None,
            "accuracy_score": round(self.accuracy_score, 3) if self.accuracy_score else None,
            "evaluated_at": self.evaluated_at,
            "created_at": self.created_at
        }


@dataclass
class ForecastMetrics:
    """预测指标模型。"""
    metric_id: str
    forecast_type: str
    sample_count: int
    average_brier_score: float
    accuracy_rate: float
    calibration_score: float
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "forecast_type": self.forecast_type,
            "sample_count": self.sample_count,
            "average_brier_score": round(self.average_brier_score, 3),
            "accuracy_rate": round(self.accuracy_rate, 3),
            "calibration_score": round(self.calibration_score, 3),
            "updated_at": self.updated_at
        }


# ============================================================
# Forecast Ledger Engine
# ============================================================

class ForecastLedger:
    """预测账本引擎。"""

    def __init__(self, db_conn_func=None):
        self._conn = db_conn_func or db_conn
        self._lock = threading.RLock()
        self._metrics: Dict[str, ForecastMetrics] = {}
        self._refresh_metrics()

    def _refresh_metrics(self):
        try:
            conn = self._conn()
            for row in conn.execute("SELECT * FROM gfe_forecast_metrics").fetchall():
                metrics = self._row_to_metrics(row)
                self._metrics[metrics.metric_id] = metrics
        except Exception as e:
            print(f"[ForecastLedger] 刷新指标缓存失败: {e}")

    def record_prediction(
        self,
        forecast_id: str,
        prediction: str,
        probability: float,
        forecast_type: str = TYPE_PROBABILITY
    ) -> Optional[LedgerRecord]:
        """记录预测。"""
        try:
            with self._lock:
                conn = self._conn()
                ledger_id = f"ledger_{int(time.time())}_{uuid.uuid4().hex[:8]}"
                now = time.time()

                conn.execute(
                    """INSERT INTO gfe_forecast_ledger
                       (ledger_id, forecast_id, prediction, actual_result, brier_score,
                        accuracy_score, evaluated_at, created_at)
                       VALUES (?, ?, ?, NULL, NULL, NULL, NULL, ?)""",
                    (ledger_id, forecast_id, prediction, now)
                )
                conn.commit()

                return LedgerRecord(
                    ledger_id=ledger_id,
                    forecast_id=forecast_id,
                    prediction=prediction,
                    actual_result=None,
                    brier_score=None,
                    accuracy_score=None,
                    evaluated_at=None,
                    created_at=now
                )
        except Exception as e:
            print(f"[ForecastLedger] 记录预测失败: {e}")
            return None

    def evaluate_prediction(
        self,
        ledger_id: str,
        actual_result: str,
        predicted_probability: float
    ) -> Optional[LedgerRecord]:
        """评估预测并计算 Brier Score。"""
        try:
            with self._lock:
                conn = self._conn()

                row = conn.execute(
                    "SELECT * FROM gfe_forecast_ledger WHERE ledger_id = ?",
                    (ledger_id,)
                ).fetchone()
                if not row:
                    return None

                now = time.time()
                brier_score = self._calculate_brier_score(predicted_probability, actual_result)
                accuracy_score = self._calculate_accuracy(brier_score)

                conn.execute(
                    """UPDATE gfe_forecast_ledger
                       SET actual_result = ?, brier_score = ?, accuracy_score = ?, evaluated_at = ?
                       WHERE ledger_id = ?""",
                    (actual_result, brier_score, accuracy_score, now, ledger_id)
                )
                conn.commit()

                led = LedgerRecord(
                    ledger_id=ledger_id,
                    forecast_id=row[1],
                    prediction=row[2],
                    actual_result=actual_result,
                    brier_score=brier_score,
                    accuracy_score=accuracy_score,
                    evaluated_at=now,
                    created_at=float(row[7]) if row[7] else now
                )

                self._update_metrics(led.forecast_id, brier_score, accuracy_score)

                self._emit_event(TOPIC_FORECAST_EVALUATED, {
                    "ledger_id": ledger_id,
                    "forecast_id": led.forecast_id,
                    "brier_score": brier_score,
                    "timestamp": now
                })

                return led
        except Exception as e:
            print(f"[ForecastLedger] 评估预测失败: {e}")
            return None

    def get_ledger(self, ledger_id: str) -> Optional[LedgerRecord]:
        """获取单个账本记录。"""
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM gfe_forecast_ledger WHERE ledger_id = ?",
            (ledger_id,)
        ).fetchone()

        if row:
            return self._row_to_ledger(row)
        return None

    def get_ledgers(
        self,
        forecast_id: Optional[str] = None,
        limit: int = 50
    ) -> List[LedgerRecord]:
        """查询账本记录列表。"""
        try:
            conn = self._conn()
            query = "SELECT * FROM gfe_forecast_ledger WHERE 1=1"
            params = []

            if forecast_id:
                query += " AND forecast_id = ?"
                params.append(forecast_id)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_ledger(row) for row in rows if row]
        except Exception as e:
            print(f"[ForecastLedger] 查询账本失败: {e}")
            return []

    def get_metrics(self, forecast_type: Optional[str] = None) -> List[ForecastMetrics]:
        """查询预测指标。"""
        try:
            conn = self._conn()
            query = "SELECT * FROM gfe_forecast_metrics WHERE 1=1"
            params = []

            if forecast_type:
                query += " AND forecast_type = ?"
                params.append(forecast_type)

            query += " ORDER BY updated_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_metrics(row) for row in rows if row]
        except Exception as e:
            print(f"[ForecastLedger] 查询指标失败: {e}")
            return []

    def get_analyst_accuracy(self, analyst_id: str) -> Dict[str, Any]:
        """获取分析师预测准确率。"""
        try:
            conn = self._conn()
            rows = conn.execute(
                """SELECT r.analysis, r.confidence, l.brier_score
                   FROM gfe_analysis_reports r
                   JOIN gfe_forecast_ledger l ON r.analyst_id = ?
                   WHERE l.brier_score IS NOT NULL""",
                (analyst_id,)
            ).fetchall()

            if not rows:
                return {"analyst_id": analyst_id, "sample_size": 0, "avg_brier": None}

            brier_scores = [float(r[2]) for r in rows if r[2] is not None]
            avg_brier = sum(brier_scores) / len(brier_scores) if brier_scores else 0.5

            return {
                "analyst_id": analyst_id,
                "sample_size": len(rows),
                "avg_brier_score": round(avg_brier, 3),
                "accuracy_estimate": round(1.0 - avg_brier, 3)
            }
        except Exception as e:
            print(f"[ForecastLedger] 查询分析师准确率失败: {e}")
            return {"analyst_id": analyst_id, "error": str(e)}

    # ---- 统计方法 ----

    def _calculate_brier_score(self, predicted_probability: float, actual_result: str) -> float:
        """计算 Brier Score = (predicted - actual)^2。"""
        if isinstance(actual_result, (int, float)):
            actual = float(actual_result)
        elif isinstance(actual_result, str):
            actual = 1.0 if actual_result.lower() in ("true", "yes", "1", "发生") else 0.0
        else:
            actual = 0.5

        predicted = max(0.0, min(1.0, predicted_probability))
        brier = (predicted - actual) ** 2
        return round(brier, 6)

    def _calculate_accuracy(self, brier_score: float) -> float:
        """从 Brier Score 计算准确度 = 1 - Brier Score。"""
        return round(max(0.0, min(1.0, 1.0 - brier_score)), 3)

    def _update_metrics(self, forecast_id: str, brier_score: float, accuracy: float):
        """更新预测指标。"""
        try:
            conn = self._conn()

            rows = conn.execute(
                """SELECT brier_score, accuracy_score
                   FROM gfe_forecast_ledger
                   WHERE forecast_id = ? AND brier_score IS NOT NULL""",
                (forecast_id,)
            ).fetchall()

            if not rows:
                return

            sample_count = len(rows)
            avg_brier = sum(float(r[0]) for r in rows) / sample_count
            avg_accuracy = sum(float(r[1]) for r in rows) / sample_count
            calibration = self._calculate_calibration(rows)

            metric_id = f"metric_{forecast_id}"
            now = time.time()

            conn.execute(
                """INSERT INTO gfe_forecast_metrics
                   (metric_id, forecast_type, sample_count, average_brier_score,
                    accuracy_rate, calibration_score, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(metric_id) DO UPDATE SET
                   sample_count = excluded.sample_count,
                   average_brier_score = excluded.average_brier_score,
                   accuracy_rate = excluded.accuracy_rate,
                   calibration_score = excluded.calibration_score,
                   updated_at = excluded.updated_at""",
                (metric_id, "unknown", sample_count, avg_brier, avg_accuracy, calibration, now)
            )
            conn.commit()

            metrics = ForecastMetrics(
                metric_id=metric_id,
                forecast_type="unknown",
                sample_count=sample_count,
                average_brier_score=avg_brier,
                accuracy_rate=avg_accuracy,
                calibration_score=calibration,
                updated_at=now
            )
            self._metrics[metric_id] = metrics

            self._emit_event(TOPIC_ACCURACY_UPDATED, {
                "forecast_id": forecast_id,
                "sample_count": sample_count,
                "avg_accuracy": avg_accuracy,
                "timestamp": now
            })
        except Exception as e:
            print(f"[ForecastLedger] 更新指标失败: {e}")

    def _calculate_calibration(self, rows: List[tuple]) -> float:
        """计算校准度（简化版）。"""
        try:
            avg_brier = sum(float(r[0]) for r in rows) / len(rows)
            return max(0.0, min(1.0, 1.0 - avg_brier))
        except Exception:
            return 0.5

    # ---- 内部方法 ----

    def _row_to_ledger(self, row) -> LedgerRecord:
        return LedgerRecord(
            ledger_id=row[0],
            forecast_id=row[1],
            prediction=row[2],
            actual_result=row[3],
            brier_score=float(row[4]) if row[4] else None,
            accuracy_score=float(row[5]) if row[5] else None,
            evaluated_at=float(row[6]) if row[6] else None,
            created_at=float(row[7]) if row[7] else time.time()
        )

    def _row_to_metrics(self, row) -> ForecastMetrics:
        return ForecastMetrics(
            metric_id=row[0],
            forecast_type=row[1],
            sample_count=int(row[2]) if row[2] else 0,
            average_brier_score=float(row[3]) if row[3] else 0.5,
            accuracy_rate=float(row[4]) if row[4] else 0.5,
            calibration_score=float(row[5]) if row[5] else 0.5,
            updated_at=float(row[6]) if row[6] else time.time()
        )

    def _emit_event(self, event_type: str, payload: Dict[str, Any]):
        try:
            publish_system(event_type, payload, source="gfe_ledger")
        except Exception as e:
            print(f"[ForecastLedger] EventBus 发布失败: {e}")


# ============================================================
# Seed Data
# ============================================================

def seed_ledger_data():
    """初始化种子数据（模拟历史评估记录）。"""
    ledger = ForecastLedger()

    test_records = [
        {"forecast_id": "forecast_test_1", "prediction": "GDP增长5.0%-5.5%", "actual_result": "5.2%", "probability": 0.65},
        {"forecast_id": "forecast_test_2", "prediction": "通胀率低于3%", "actual_result": "true", "probability": 0.7},
        {"forecast_id": "forecast_test_3", "prediction": "利率维持高位", "actual_result": "true", "probability": 0.6}
    ]

    for record in test_records:
        led = ledger.record_prediction(
            forecast_id=record["forecast_id"],
            prediction=record["prediction"],
            probability=record["probability"]
        )
        if led:
            ledger.evaluate_prediction(
                ledger_id=led.ledger_id,
                actual_result=record["actual_result"],
                predicted_probability=record["probability"]
            )

    print(f"[ForecastLedger] Seeded test data")
    return True


# ============================================================
# Singleton
# ============================================================

_instance: Optional[ForecastLedger] = None
_instance_lock = threading.Lock()


def get_forecast_ledger() -> ForecastLedger:
    """获取单例 ForecastLedger。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = ForecastLedger()
        return _instance


def reset_forecast_ledger():
    """重置单例（用于测试）。"""
    global _instance
    with _instance_lock:
        _instance = None
