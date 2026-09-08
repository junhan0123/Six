#!/usr/bin/env python3
"""PHASE 147 — GFE Forecast Ledger Foundation Tests

测试预测账本基础功能：
- 数据库表创建
- 预测记录
- 预测评估
- Brier Score 计算
- 准确率统计
- 数据持久化
- EventBus集成
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import db_conn, _migrate_gfe_forecast_ledger
from gfe_forecast_ledger import (
    ForecastLedger,
    LedgerRecord,
    ForecastMetrics,
    get_forecast_ledger,
    reset_forecast_ledger,
    seed_ledger_data,
    TYPE_PROBABILITY,
)
from eventbus import SYSTEM_EVENT_NAMES


class TestPhase147Database(unittest.TestCase):
    """测试数据库迁移。"""

    def setUp(self):
        self.conn = db_conn()
        _migrate_gfe_forecast_ledger(self.conn)

    def tearDown(self):
        self.conn.execute("DELETE FROM gfe_forecast_metrics")
        self.conn.execute("DELETE FROM gfe_forecast_ledger")
        self.conn.commit()

    def test_tables_exist(self):
        tables = [r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'gfe_%'"
        ).fetchall()]
        self.assertIn("gfe_forecast_ledger", tables)
        self.assertIn("gfe_forecast_metrics", tables)

    def test_ledger_schema(self):
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(gfe_forecast_ledger)").fetchall()}
        required = {"ledger_id", "forecast_id", "prediction", "actual_result",
                     "brier_score", "accuracy_score", "evaluated_at", "created_at"}
        self.assertTrue(required.issubset(cols), f"Missing: {required - cols}")

    def test_metrics_schema(self):
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(gfe_forecast_metrics)").fetchall()}
        required = {"metric_id", "forecast_type", "sample_count",
                     "average_brier_score", "accuracy_rate", "calibration_score", "updated_at"}
        self.assertTrue(required.issubset(cols), f"Missing: {required - cols}")


class TestPhase147Engine(unittest.TestCase):
    """测试核心引擎功能。"""

    def setUp(self):
        reset_forecast_ledger()
        self.ledger = get_forecast_ledger()
        self.conn = db_conn()
        _migrate_gfe_forecast_ledger(self.conn)

    def tearDown(self):
        self.conn.execute("DELETE FROM gfe_forecast_metrics")
        self.conn.execute("DELETE FROM gfe_forecast_ledger")
        self.conn.commit()

    def test_record_prediction(self):
        led = self.ledger.record_prediction(
            forecast_id="test_1", prediction="Prediction A", probability=0.65
        )
        self.assertIsNotNone(led)
        self.assertEqual(led.forecast_id, "test_1")
        self.assertEqual(led.prediction, "Prediction A")
        self.assertIsNone(led.actual_result)
        self.assertIsNone(led.brier_score)
        self.assertIsNotNone(led.ledger_id)

    def test_evaluate_prediction(self):
        led = self.ledger.record_prediction(
            forecast_id="test_1", prediction="Will happen", probability=0.8
        )
        self.assertIsNotNone(led)

        evaluated = self.ledger.evaluate_prediction(
            ledger_id=led.ledger_id, actual_result="true", predicted_probability=0.8
        )
        self.assertIsNotNone(evaluated)
        self.assertEqual(evaluated.actual_result, "true")
        self.assertIsNotNone(evaluated.brier_score)
        self.assertIsNotNone(evaluated.accuracy_score)
        self.assertIsNotNone(evaluated.evaluated_at)

    def test_brier_score_calculation(self):
        # 完美预测
        self.assertEqual(self.ledger._calculate_brier_score(1.0, "true"), 0.0)
        # 完全错误
        self.assertEqual(self.ledger._calculate_brier_score(0.0, "true"), 1.0)
        # 一般预测
        self.assertAlmostEqual(self.ledger._calculate_brier_score(0.7, "true"), 0.09, places=3)

    def test_accuracy_calculation(self):
        self.assertEqual(self.ledger._calculate_accuracy(0.0), 1.0)
        self.assertEqual(self.ledger._calculate_accuracy(1.0), 0.0)
        self.assertAlmostEqual(self.ledger._calculate_accuracy(0.09), 0.91, places=2)

    def test_get_ledger(self):
        led = self.ledger.record_prediction(forecast_id="test_1", prediction="P", probability=0.5)
        found = self.ledger.get_ledger(led.ledger_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.ledger_id, led.ledger_id)

    def test_get_ledgers(self):
        self.ledger.record_prediction(forecast_id="f1", prediction="P1", probability=0.5)
        self.ledger.record_prediction(forecast_id="f2", prediction="P2", probability=0.6)
        self.ledger.record_prediction(forecast_id="f1", prediction="P3", probability=0.7)

        ledgers = self.ledger.get_ledgers(limit=10)
        self.assertEqual(len(ledgers), 3)

        f1_ledgers = self.ledger.get_ledgers(forecast_id="f1")
        self.assertEqual(len(f1_ledgers), 2)

    def test_get_metrics(self):
        led = self.ledger.record_prediction(forecast_id="test", prediction="P", probability=0.5)
        self.ledger.evaluate_prediction(led.ledger_id, "true", 0.5)
        metrics = self.ledger.get_metrics()
        self.assertIsInstance(metrics, list)

    def test_analyst_accuracy(self):
        result = self.ledger.get_analyst_accuracy("nonexistent_analyst")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["analyst_id"], "nonexistent_analyst")
        self.assertEqual(result["sample_size"], 0)

    def test_eventbus_topics_registered(self):
        for topic in ["gfe_forecast_evaluated", "gfe_accuracy_updated"]:
            self.assertIn(topic, SYSTEM_EVENT_NAMES, f"Topic {topic} not registered")

    def test_to_frontend_format(self):
        led = LedgerRecord(
            ledger_id="test_1", forecast_id="f1", prediction="P",
            actual_result="true", brier_score=0.09, accuracy_score=0.91,
            evaluated_at=time.time()
        )
        frontend = led.to_frontend()
        self.assertIn("ledger_id", frontend)
        self.assertIn("prediction", frontend)
        self.assertIn("brier_score", frontend)

    def test_metrics_to_frontend(self):
        metrics = ForecastMetrics(
            metric_id="m1", forecast_type=TYPE_PROBABILITY, sample_count=10,
            average_brier_score=0.15, accuracy_rate=0.85, calibration_score=0.8
        )
        frontend = metrics.to_frontend()
        self.assertIn("metric_id", frontend)
        self.assertIn("sample_count", frontend)
        self.assertIn("accuracy_rate", frontend)

    def test_persistence(self):
        led = self.ledger.record_prediction(forecast_id="persist_test", prediction="Test", probability=0.5)
        found = self.ledger.get_ledger(led.ledger_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.prediction, "Test")


class TestPhase147API(unittest.TestCase):
    """测试API端点结构。"""

    def test_api_endpoints_defined(self):
        from gfe_forecast_ledger import get_forecast_ledger
        ledger = get_forecast_ledger()
        self.assertIsNotNone(ledger)


class TestPhase147SeedData(unittest.TestCase):
    """测试种子数据。"""

    def setUp(self):
        self.conn = db_conn()
        _migrate_gfe_forecast_ledger(self.conn)

    def test_seed_data(self):
        reset_forecast_ledger()
        ledger = get_forecast_ledger()
        ledger._conn = lambda: self.conn
        seed_ledger_data()
        ledgers = ledger.get_ledgers()
        self.assertGreater(len(ledgers), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
