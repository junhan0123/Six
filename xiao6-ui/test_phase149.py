#!/usr/bin/env python3
"""PHASE 149 — GFE Forecast Calibration Foundation Tests

测试预测校准引擎基础功能：
- 数据库表创建
- 预测评估记录
- Brier Score计算
- Calibration计算
- 权重调整
- 报告生成
- 数据持久化
- EventBus集成
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from gfe_calibration import (
    ForecastCalibrationEngine,
    CalibrationRecord,
    AnalystMetrics,
    get_calibration_engine,
    WEIGHT_MIN,
    WEIGHT_MAX,
)
from db import db_conn


class TestPhase149Database(unittest.TestCase):
    """测试数据库结构。"""

    def setUp(self):
        db_conn().close()

    def test_tables_exist(self):
        """测试表存在。"""
        conn = db_conn()
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'gfe_calibration%'"
        ).fetchall()]
        self.assertIn("gfe_calibration_records", tables)
        self.assertIn("gfe_calibration_history", tables)

    def test_records_schema(self):
        """测试记录表结构。"""
        conn = db_conn()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_calibration_records)").fetchall()}
        expected = {"record_id", "forecast_id", "analyst_id", "domain",
                    "predicted_probability", "actual_result", "brier_score", "confidence_error", "created_at"}
        self.assertEqual(cols, expected)

    def test_metrics_schema(self):
        """测试指标表结构。"""
        conn = db_conn()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_analyst_metrics)").fetchall()}
        expected = {"metric_id", "analyst_id", "domain", "sample_count",
                    "average_brier_score", "accuracy_rate", "calibration_score", "weight_adjustment", "updated_at"}
        self.assertEqual(cols, expected)

    def test_history_schema(self):
        """测试历史表结构。"""
        conn = db_conn()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_calibration_history)").fetchall()}
        expected = {"history_id", "analyst_id", "old_weight", "new_weight", "reason", "created_at"}
        self.assertEqual(cols, expected)


class TestPhase149Engine(unittest.TestCase):
    """测试校准引擎功能。"""

    def setUp(self):
        db_conn().close()
        self.engine = get_calibration_engine()
        conn = db_conn()
        conn.execute("DELETE FROM gfe_calibration_history")
        conn.execute("DELETE FROM gfe_calibration_records")
        conn.commit()

    def tearDown(self):
        conn = db_conn()
        conn.execute("DELETE FROM gfe_calibration_history")
        conn.execute("DELETE FROM gfe_calibration_records")
        conn.commit()

    def test_brier_score_calculation(self):
        """测试Brier Score计算。"""
        # 完美预测
        brier = self.engine._calculate_brier_score(0.8, 1.0)
        self.assertAlmostEqual(brier, 0.04, places=4)

        # 错误预测
        brier = self.engine._calculate_brier_score(0.3, 0.9)
        self.assertAlmostEqual(brier, 0.36, places=4)

        # 完全错误
        brier = self.engine._calculate_brier_score(0.1, 1.0)
        self.assertAlmostEqual(brier, 0.81, places=4)

    def test_confidence_error(self):
        """测试置信度误差计算。"""
        error = self.engine._calculate_confidence_error(0.7, 0.9, 0.8)
        self.assertAlmostEqual(error, 0.25, places=4)  # 0.2 / 0.8

    def test_record_evaluation(self):
        """测试记录评估。"""
        record = self.engine.record_evaluation(
            forecast_id="f1",
            analyst_id="a1",
            domain="economy",
            predicted_probability=0.7,
            actual_result=0.8,
            confidence=0.8
        )
        self.assertIsNotNone(record)
        self.assertEqual(record.forecast_id, "f1")
        self.assertEqual(record.analyst_id, "a1")
        self.assertEqual(record.domain, "economy")
        self.assertAlmostEqual(record.brier_score, 0.01, places=4)

    def test_calculate_calibration(self):
        """测试校准度计算。"""
        # 记录一些评估
        self.engine.record_evaluation(None, "a1", "economy", 0.7, 0.8, 0.8)
        self.engine.record_evaluation(None, "a1", "economy", 0.6, 0.5, 0.7)

        result = self.engine.calculate_calibration("a1", "economy")
        self.assertEqual(result["analyst_id"], "a1")
        self.assertEqual(result["domain"], "economy")
        self.assertEqual(result["sample_count"], 2)
        self.assertIsNotNone(result["average_brier_score"])
        self.assertIsNotNone(result["calibration_score"])

    def test_get_analyst_metrics(self):
        """测试获取分析师指标。"""
        self.engine.record_evaluation(None, "a1", "economy", 0.7, 0.8, 0.8)
        self.engine.record_evaluation(None, "a2", "finance", 0.6, 0.5, 0.7)

        metrics = self.engine.get_analyst_metrics()
        self.assertEqual(len(metrics), 2)

        a1_metrics = [m for m in metrics if m.analyst_id == "a1"][0]
        self.assertEqual(a1_metrics.sample_count, 1)
        self.assertGreater(a1_metrics.calibration_score, 0)

    def test_update_analyst_weight(self):
        """测试权重调整。"""
        # 先记录一些评估
        self.engine.record_evaluation(None, "a1", "economy", 0.7, 0.8, 0.8)
        self.engine.record_evaluation(None, "a1", "economy", 0.6, 0.5, 0.7)

        # 确保分析师存在于 gfe_analyst_agents 表
        conn = db_conn()
        existing = conn.execute("SELECT COUNT(*) FROM gfe_analyst_agents WHERE agent_id = ?", ("a1",)).fetchone()[0]
        if not existing:
            conn.execute("INSERT INTO gfe_analyst_agents (agent_id, name, specialization, weight, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                         ("a1", "TestAnalyst1", "economy", 0.7, 0.75, time.time()))
            conn.commit()

        result = self.engine.update_analyst_weight("a1", "economy", "定期校准")
        self.assertIsNotNone(result)
        self.assertEqual(result["analyst_id"], "a1")
        self.assertIn("old_weight", result)
        self.assertIn("new_weight", result)
        self.assertIn("calibration_score", result)

        # 权重应在范围内
        self.assertGreaterEqual(result["new_weight"], WEIGHT_MIN)
        self.assertLessEqual(result["new_weight"], WEIGHT_MAX)

    def test_get_calibration_report(self):
        """测试校准报告生成。"""
        self.engine.record_evaluation("f1", "a1", "economy", 0.7, 0.8, 0.8)
        self.engine.record_evaluation("f2", "a2", "finance", 0.6, 0.5, 0.7)

        report = self.engine.get_calibration_report()
        self.assertIn("total_records", report)
        self.assertEqual(report["total_records"], 2)
        self.assertIn("overall_brier_score", report)
        self.assertIn("overall_calibration_score", report)
        self.assertIn("by_analyst", report)
        self.assertIn("by_domain", report)

    def test_persistence(self):
        """测试数据持久化。"""
        record = self.engine.record_evaluation("f1", "a1", "test", 0.7, 0.8, 0.8)
        self.assertIsNotNone(record)

        conn = db_conn()
        count = conn.execute("SELECT COUNT(*) FROM gfe_calibration_records").fetchone()[0]
        self.assertGreater(count, 0)

    def test_eventbus_topics_registered(self):
        """测试EventBus主题已注册。"""
        from eventbus import SYSTEM_EVENT_NAMES
        self.assertIn("gfe_forecast_calibrated", SYSTEM_EVENT_NAMES)
        self.assertIn("gfe_analyst_weight_updated", SYSTEM_EVENT_NAMES)

    def test_weight_bounds(self):
        """测试权重边界限制。"""
        # 模拟极端情况：校准度很低
        self.engine.record_evaluation(None, "a_extreme", "test", 0.9, 0.1, 0.5)

        # 确保分析师存在
        conn = db_conn()
        existing = conn.execute("SELECT COUNT(*) FROM gfe_analyst_agents WHERE agent_id = ?", ("a_extreme",)).fetchone()[0]
        if not existing:
            conn.execute("INSERT INTO gfe_analyst_agents (agent_id, name, specialization, weight, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                         ("a_extreme", "ExtremeAnalyst", "test", 0.5, 0.5, time.time()))
            conn.commit()

        result = self.engine.update_analyst_weight("a_extreme", "test", "边界测试")
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result["new_weight"], WEIGHT_MIN)
        self.assertLessEqual(result["new_weight"], WEIGHT_MAX)


class TestPhase149API(unittest.TestCase):
    """测试API端点。"""

    def test_api_endpoints_defined(self):
        """测试API端点定义。"""
        with open(os.path.join(os.path.dirname(__file__), "server.py"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("/api/gfe/calibration", content)


class TestPhase149SeedData(unittest.TestCase):
    """测试种子数据。"""

    def setUp(self):
        db_conn().close()

    def test_seed_data(self):
        """测试种子数据加载。"""
        engine = get_calibration_engine()
        engine.seed_data()
        conn = db_conn()
        count = conn.execute("SELECT COUNT(*) FROM gfe_calibration_records").fetchone()[0]
        self.assertGreater(count, 0)


if __name__ == "__main__":
    unittest.main()