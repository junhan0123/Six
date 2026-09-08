#!/usr/bin/env python3
"""PHASE 149 — GFE Forecast Calibration Foundation

Global Foresight Engine (GFE) 预测校准引擎基础实现。
职责：
- 预测评估记录
- Brier Score 计算
- 校准度评估
- 分析师权重调整
- 校准报告生成

架构边界：
- 只读访问已有 GFE 模块数据
- 不修改已有表结构
- 不调用 Runtime/Execution
- 仅做统计计算和报告
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
TOPIC_FORECAST_CALIBRATED = "gfe_forecast_calibrated"
TOPIC_ANALYST_WEIGHT_UPDATED = "gfe_analyst_weight_updated"

# Weight adjustment bounds
WEIGHT_MIN = 0.1
WEIGHT_MAX = 1.0


# ============================================================
# Data Models
# ============================================================

@dataclass
class CalibrationRecord:
    """校准记录模型。"""
    record_id: str
    forecast_id: Optional[str]
    analyst_id: Optional[str]
    domain: Optional[str]
    predicted_probability: float
    actual_result: float
    brier_score: float
    confidence_error: float
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "forecast_id": self.forecast_id,
            "analyst_id": self.analyst_id,
            "domain": self.domain,
            "predicted_probability": round(self.predicted_probability, 3),
            "actual_result": round(self.actual_result, 3),
            "brier_score": round(self.brier_score, 3),
            "confidence_error": round(self.confidence_error, 3),
            "created_at": self.created_at
        }


@dataclass
class AnalystMetrics:
    """分析师指标模型。"""
    metric_id: str
    analyst_id: str
    domain: Optional[str]
    sample_count: int
    average_brier_score: float
    accuracy_rate: float
    calibration_score: float
    weight_adjustment: float
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_frontend(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "analyst_id": self.analyst_id,
            "domain": self.domain,
            "sample_count": self.sample_count,
            "average_brier_score": round(self.average_brier_score, 3),
            "accuracy_rate": round(self.accuracy_rate, 3),
            "calibration_score": round(self.calibration_score, 3),
            "weight_adjustment": round(self.weight_adjustment, 3),
            "updated_at": self.updated_at
        }


# ============================================================
# ForecastCalibrationEngine
# ============================================================

class ForecastCalibrationEngine:
    """预测校准引擎。

    核心功能：
    - 记录预测评估
    - 计算 Brier Score
    - 计算校准度
    - 调整分析师权重
    - 生成校准报告
    """

    def __init__(self):
        self._lock = threading.Lock()

    @staticmethod
    def _calculate_brier_score(predicted: float, actual: float) -> float:
        """计算 Brier Score。

        Brier = (predicted - actual)^2
        """
        return (predicted - actual) ** 2

    @staticmethod
    def _calculate_confidence_error(predicted: float, actual: float, confidence: float) -> float:
        """计算置信度误差。

        confidence_error = |predicted - actual| / confidence
        """
        if confidence > 0:
            return abs(predicted - actual) / confidence
        return abs(predicted - actual)

    def record_evaluation(
        self,
        forecast_id: Optional[str],
        analyst_id: Optional[str],
        domain: Optional[str],
        predicted_probability: float,
        actual_result: float,
        confidence: float = 0.5
    ) -> Optional[CalibrationRecord]:
        """记录预测评估。"""
        try:
            conn = db_conn()
            record_id = "cal_" + uuid.uuid4().hex[:8]
            brier_score = self._calculate_brier_score(predicted_probability, actual_result)
            confidence_error = self._calculate_confidence_error(predicted_probability, actual_result, confidence)
            created_at = time.time()

            conn.execute(
                """INSERT INTO gfe_calibration_records
                   (record_id, forecast_id, analyst_id, domain,
                    predicted_probability, actual_result, brier_score, confidence_error, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (record_id, forecast_id, analyst_id, domain,
                 predicted_probability, actual_result, brier_score, confidence_error, created_at)
            )
            conn.commit()

            record = CalibrationRecord(
                record_id=record_id,
                forecast_id=forecast_id,
                analyst_id=analyst_id,
                domain=domain,
                predicted_probability=predicted_probability,
                actual_result=actual_result,
                brier_score=brier_score,
                confidence_error=confidence_error,
                created_at=created_at
            )

            publish_system(TOPIC_FORECAST_CALIBRATED, {
                "record_id": record_id,
                "analyst_id": analyst_id,
                "domain": domain,
                "brier_score": brier_score
            })

            return record
        except Exception as e:
            print(f"[Calibration] 记录评估失败: {e}")
            return None

    def calculate_calibration(self, analyst_id: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """计算分析师校准度。

        calibration = 1 - average_brier_score
        """
        try:
            conn = db_conn()
            query = "SELECT predicted_probability, actual_result, brier_score FROM gfe_calibration_records WHERE analyst_id = ?"
            params = [analyst_id]

            if domain:
                query += " AND domain = ?"
                params.append(domain)

            rows = conn.execute(query, params).fetchall()
            if not rows:
                return {
                    "analyst_id": analyst_id,
                    "domain": domain,
                    "sample_count": 0,
                    "average_brier_score": None,
                    "calibration_score": None
                }

            avg_brier = sum(r[2] for r in rows) / len(rows)
            calibration = 1.0 - avg_brier

            return {
                "analyst_id": analyst_id,
                "domain": domain,
                "sample_count": len(rows),
                "average_brier_score": round(avg_brier, 4),
                "calibration_score": round(calibration, 4)
            }
        except Exception as e:
            print(f"[Calibration] 计算校准度失败: {e}")
            return {}

    def get_analyst_metrics(self, analyst_id: Optional[str] = None, domain: Optional[str] = None) -> List[AnalystMetrics]:
        """获取分析师指标。"""
        try:
            conn = db_conn()
            query = """
                SELECT analyst_id, domain,
                       COUNT(*) as sample_count,
                       AVG(brier_score) as avg_brier,
                       AVG(CASE WHEN ABS(predicted_probability - actual_result) < 0.2 THEN 1.0 ELSE 0.0 END) as accuracy
                FROM gfe_calibration_records
                WHERE 1=1
            """
            params = []
            if analyst_id:
                query += " AND analyst_id = ?"
                params.append(analyst_id)
            if domain:
                query += " AND domain = ?"
                params.append(domain)
            query += " GROUP BY analyst_id, domain"

            rows = conn.execute(query, params).fetchall()
            results = []
            for r in rows:
                metric_id = f"metric_{r[0]}_{r[1] or 'all'}"
                avg_brier = r[3] or 0.5
                calibration_score = 1.0 - avg_brier
                weight_adj = calibration_score - 0.5  # deviation from baseline

                results.append(AnalystMetrics(
                    metric_id=metric_id,
                    analyst_id=r[0],
                    domain=r[1],
                    sample_count=r[2],
                    average_brier_score=avg_brier,
                    accuracy_rate=r[4] or 0.5,
                    calibration_score=calibration_score,
                    weight_adjustment=weight_adj
                ))
            return results
        except Exception as e:
            print(f"[Calibration] 获取分析师指标失败: {e}")
            return []

    def update_analyst_weight(
        self,
        analyst_id: str,
        domain: Optional[str] = None,
        reason: str = ""
    ) -> Optional[Dict[str, Any]]:
        """调整分析师权重。

        new_weight = old_weight * calibration_score
        限制范围: 0.1 - 1.0
        """
        try:
            conn = db_conn()

            # 获取当前权重（gfe_analyst_agents 使用 agent_id 作为主键）
            query = """
                SELECT agent_id, weight
                FROM gfe_analyst_agents
                WHERE agent_id = ?
            """
            params = [analyst_id]

            row = conn.execute(query, params).fetchone()
            if not row:
                return None

            old_weight = float(row[1]) if row[1] else 0.5

            # 计算校准度
            cal_result = self.calculate_calibration(analyst_id, domain)
            cal_score = cal_result.get("calibration_score") or 0.5

            # 计算新权重
            new_weight = old_weight * cal_score
            new_weight = max(WEIGHT_MIN, min(WEIGHT_MAX, new_weight))

            # 更新权重
            conn.execute(
                """UPDATE gfe_analyst_agents SET weight = ? WHERE agent_id = ?""",
                (new_weight, analyst_id)
            )

            # 记录历史
            history_id = "cal_hist_" + uuid.uuid4().hex[:8]
            conn.execute(
                """INSERT INTO gfe_calibration_history
                   (history_id, analyst_id, old_weight, new_weight, reason, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (history_id, analyst_id, old_weight, new_weight, reason, time.time())
            )
            conn.commit()

            publish_system(TOPIC_ANALYST_WEIGHT_UPDATED, {
                "analyst_id": analyst_id,
                "domain": domain,
                "old_weight": round(old_weight, 3),
                "new_weight": round(new_weight, 3),
                "reason": reason
            })

            return {
                "analyst_id": analyst_id,
                "domain": domain,
                "old_weight": round(old_weight, 3),
                "new_weight": round(new_weight, 3),
                "calibration_score": round(cal_score, 3),
                "reason": reason
            }
        except Exception as e:
            print(f"[Calibration] 调整权重失败: {e}")
            return None

    def get_calibration_report(self) -> Dict[str, Any]:
        """生成校准报告。"""
        try:
            conn = db_conn()

            # 总体统计
            total_records = conn.execute("SELECT COUNT(*) FROM gfe_calibration_records").fetchone()[0]
            avg_brier = conn.execute("SELECT AVG(brier_score) FROM gfe_calibration_records").fetchone()[0] or 0.5
            overall_calibration = 1.0 - avg_brier

            # 按分析师统计
            analyst_stats = []
            rows = conn.execute("""
                SELECT analyst_id, domain, COUNT(*) as n, AVG(brier_score) as avg_brier
                FROM gfe_calibration_records
                GROUP BY analyst_id, domain
                ORDER BY n DESC
            """).fetchall()
            for r in rows:
                analyst_stats.append({
                    "analyst_id": r[0],
                    "domain": r[1],
                    "sample_count": r[2],
                    "average_brier_score": round(r[3], 4),
                    "calibration_score": round(1.0 - r[3], 4)
                })

            # 按领域统计
            domain_stats = []
            rows = conn.execute("""
                SELECT domain, COUNT(*) as n, AVG(brier_score) as avg_brier
                FROM gfe_calibration_records
                GROUP BY domain
                ORDER BY n DESC
            """).fetchall()
            for r in rows:
                domain_stats.append({
                    "domain": r[0],
                    "sample_count": r[1],
                    "average_brier_score": round(r[2], 4),
                    "calibration_score": round(1.0 - r[2], 4)
                })

            return {
                "total_records": total_records,
                "overall_brier_score": round(avg_brier, 4),
                "overall_calibration_score": round(overall_calibration, 4),
                "by_analyst": analyst_stats,
                "by_domain": domain_stats,
                "generated_at": time.time()
            }
        except Exception as e:
            print(f"[Calibration] 生成报告失败: {e}")
            return {}

    def seed_data(self):
        """种子数据。"""
        try:
            conn = db_conn()
            count = conn.execute("SELECT COUNT(*) FROM gfe_calibration_records").fetchone()[0]
            if count > 0:
                return

            # 模拟一些校准数据
            import random
            domains = ["economy", "finance", "technology"]
            analysts = ["analyst_macro", "analyst_finance", "analyst_tech"]

            for i in range(20):
                analyst_id = random.choice(analysts)
                domain = random.choice(domains)
                predicted = random.uniform(0.3, 0.9)
                actual = random.uniform(0.2, 1.0)
                brier = (predicted - actual) ** 2

                record_id = "cal_" + uuid.uuid4().hex[:8]
                conn.execute(
                    """INSERT INTO gfe_calibration_records
                       (record_id, analyst_id, domain, predicted_probability, actual_result, brier_score, confidence_error, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (record_id, analyst_id, domain, predicted, actual, brier, abs(predicted - actual), time.time())
                )

            conn.commit()
            print("[Calibration] Seeded calibration records")
        except Exception as e:
            print(f"[Calibration] 种子数据失败: {e}")


# ============================================================
# Singleton
# ============================================================

_instance: Optional[ForecastCalibrationEngine] = None
_instance_lock = threading.Lock()


def get_calibration_engine() -> ForecastCalibrationEngine:
    """获取校准引擎单例。"""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = ForecastCalibrationEngine()
                _instance.seed_data()
    return _instance


# ============================================================
# Frontend format helpers
# ============================================================

def record_to_frontend(record: CalibrationRecord) -> Dict[str, Any]:
    """校准记录前端格式。"""
    return record.to_frontend()


def metrics_to_frontend(metrics: AnalystMetrics) -> Dict[str, Any]:
    """分析师指标前端格式。"""
    return metrics.to_frontend()