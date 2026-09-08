#!/usr/bin/env python3
"""PHASE 146 — GFE Forecast Engine Foundation Tests

测试预测引擎基础功能：
- 数据库表创建
- 预测创建
- 证据添加
- 置信度计算
- 预测更新
- 数据持久化
- EventBus集成
"""

import os
import sys
import time
import unittest

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import db_conn, _migrate_gfe_forecast_engine
from gfe_forecast import (
    ForecastEngine,
    Forecast,
    ForecastEvidence,
    ForecastVersion,
    get_forecast_engine,
    reset_forecast_engine,
    seed_forecasts,
    SOURCE_WORLD_STATE,
    SOURCE_EVENTS,
    SOURCE_HISTORIES,
    SOURCE_CAUSAL,
    SOURCE_ANALYSTS,
    SOURCE_SCENARIOS,
    STATUS_DRAFT,
    STATUS_REVIEWED,
    STATUS_FINAL,
)
from eventbus import SYSTEM_EVENT_NAMES


class TestPhase146Database(unittest.TestCase):
    """测试数据库迁移。"""

    def setUp(self):
        """初始化数据库。"""
        self.conn = db_conn()
        _migrate_gfe_forecast_engine(self.conn)

    def tearDown(self):
        """清理测试数据。"""
        self.conn.execute("DELETE FROM gfe_forecast_versions")
        self.conn.execute("DELETE FROM gfe_forecast_evidence")
        self.conn.execute("DELETE FROM gfe_forecasts")
        self.conn.commit()

    def test_tables_exist(self):
        """测试表存在。"""
        tables = [r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'gfe_%'"
        ).fetchall()]

        self.assertIn("gfe_forecasts", tables)
        self.assertIn("gfe_forecast_evidence", tables)
        self.assertIn("gfe_forecast_versions", tables)

    def test_forecasts_schema(self):
        """测试预测表结构。"""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(gfe_forecasts)").fetchall()}

        required_cols = {
            "forecast_id", "question", "target", "prediction",
            "probability", "confidence", "time_horizon",
            "status", "created_at", "updated_at"
        }

        self.assertTrue(required_cols.issubset(cols), f"Missing columns: {required_cols - cols}")

    def test_evidence_schema(self):
        """测试证据表结构。"""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(gfe_forecast_evidence)").fetchall()}

        required_cols = {
            "evidence_id", "forecast_id", "source_type",
            "source_ref", "weight", "impact", "confidence", "created_at"
        }

        self.assertTrue(required_cols.issubset(cols), f"Missing columns: {required_cols - cols}")

    def test_versions_schema(self):
        """测试版本表结构。"""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(gfe_forecast_versions)").fetchall()}

        required_cols = {
            "version_id", "forecast_id",
            "previous_prediction", "new_prediction",
            "change_reason", "created_at"
        }

        self.assertTrue(required_cols.issubset(cols), f"Missing columns: {required_cols - cols}")


class TestPhase146Engine(unittest.TestCase):
    """测试核心引擎功能。"""

    def setUp(self):
        """初始化测试环境。"""
        reset_forecast_engine()
        self.engine = get_forecast_engine()
        self.conn = db_conn()
        _migrate_gfe_forecast_engine(self.conn)

    def tearDown(self):
        """清理测试数据。"""
        self.conn.execute("DELETE FROM gfe_forecast_versions")
        self.conn.execute("DELETE FROM gfe_forecast_evidence")
        self.conn.execute("DELETE FROM gfe_forecasts")
        self.conn.commit()

    def test_create_forecast(self):
        """测试创建预测。"""
        forecast = self.engine.create_forecast(
            question="What will happen?",
            target="test_target",
            prediction="Test prediction",
            probability=0.6,
            confidence=0.7,
            time_horizon=365,
            status=STATUS_DRAFT
        )

        self.assertIsNotNone(forecast)
        self.assertEqual(forecast.question, "What will happen?")
        self.assertEqual(forecast.target, "test_target")
        self.assertEqual(forecast.prediction, "Test prediction")
        self.assertEqual(forecast.probability, 0.6)
        self.assertEqual(forecast.confidence, 0.7)
        self.assertEqual(forecast.time_horizon, 365)
        self.assertIsNotNone(forecast.forecast_id)

    def test_add_evidence(self):
        """测试添加证据。"""
        forecast = self.engine.create_forecast(
            question="Q", target="T", prediction="P",
            probability=0.5, confidence=0.5
        )

        evidence = self.engine.add_evidence(
            forecast_id=forecast.forecast_id,
            source_type=SOURCE_WORLD_STATE,
            source_ref="test_ref",
            weight=0.8,
            impact=0.7,
            confidence=0.75
        )

        self.assertIsNotNone(evidence)
        self.assertEqual(evidence.source_type, SOURCE_WORLD_STATE)
        self.assertEqual(evidence.weight, 0.8)
        self.assertEqual(evidence.impact, 0.7)

    def test_update_forecast(self):
        """测试更新预测。"""
        forecast = self.engine.create_forecast(
            question="Q", target="T", prediction="Old prediction",
            probability=0.5, confidence=0.5
        )

        updated = self.engine.update_forecast(
            forecast_id=forecast.forecast_id,
            prediction="New prediction",
            change_reason="Updated based on new evidence"
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated.prediction, "New prediction")
        self.assertEqual(updated.status, STATUS_DRAFT)

    def test_calculate_confidence(self):
        """测试置信度计算。"""
        forecast = self.engine.create_forecast(
            question="Q", target="T", prediction="P",
            probability=0.5, confidence=0.5
        )

        self.engine.add_evidence(
            forecast_id=forecast.forecast_id,
            source_type=SOURCE_WORLD_STATE,
            weight=0.8, confidence=0.9
        )
        self.engine.add_evidence(
            forecast_id=forecast.forecast_id,
            source_type=SOURCE_EVENTS,
            weight=0.6, confidence=0.7
        )

        confidence = self.engine.calculate_confidence(forecast.forecast_id)
        self.assertIsNotNone(confidence)
        self.assertGreater(confidence, 0)
        self.assertLessEqual(confidence, 1.0)

    def test_get_forecast(self):
        """测试获取预测。"""
        forecast = self.engine.create_forecast(
            question="Q", target="T", prediction="P",
            probability=0.5, confidence=0.5
        )

        found = self.engine.get_forecast(forecast.forecast_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.forecast_id, forecast.forecast_id)

    def test_get_forecasts(self):
        """测试查询预测列表。"""
        self.engine.create_forecast(question="Q1", target="T1", prediction="P1", probability=0.5, confidence=0.5)
        self.engine.create_forecast(question="Q2", target="T2", prediction="P2", probability=0.6, confidence=0.6)
        self.engine.create_forecast(question="Q1", target="T3", prediction="P3", probability=0.7, confidence=0.7)

        forecasts = self.engine.get_forecasts(limit=10)
        self.assertEqual(len(forecasts), 3)

        q1_forecasts = self.engine.get_forecasts(question="Q1")
        self.assertEqual(len(q1_forecasts), 2)

    def test_get_evidence(self):
        """测试查询证据。"""
        forecast = self.engine.create_forecast(question="Q", target="T", prediction="P", probability=0.5, confidence=0.5)
        self.engine.add_evidence(forecast.forecast_id, SOURCE_WORLD_STATE, weight=0.8)
        self.engine.add_evidence(forecast.forecast_id, SOURCE_EVENTS, weight=0.6)

        evidence = self.engine.get_evidence(forecast.forecast_id)
        self.assertEqual(len(evidence), 2)

    def test_get_versions(self):
        """测试查询版本历史。"""
        forecast = self.engine.create_forecast(question="Q", target="T", prediction="P1", probability=0.5, confidence=0.5)
        self.engine.update_forecast(forecast.forecast_id, prediction="P2", change_reason="Update 1")
        self.engine.update_forecast(forecast.forecast_id, prediction="P3", change_reason="Update 2")

        versions = self.engine.get_versions(forecast.forecast_id)
        self.assertEqual(len(versions), 2)

    def test_eventbus_topics_registered(self):
        """测试EventBus主题已注册。"""
        required_topics = [
            "gfe_forecast_created",
            "gfe_forecast_updated"
        ]

        for topic in required_topics:
            self.assertIn(topic, SYSTEM_EVENT_NAMES, f"Topic {topic} not registered")

    def test_to_frontend_format(self):
        """测试前端格式转换。"""
        forecast = Forecast(
            forecast_id="test_1",
            question="Q",
            target="T",
            prediction="P",
            probability=0.6,
            confidence=0.7,
            time_horizon=365,
            status=STATUS_DRAFT,
            created_at=time.time()
        )

        frontend = forecast.to_frontend()
        self.assertIn("forecast_id", frontend)
        self.assertIn("prediction", frontend)
        self.assertIn("probability", frontend)

    def test_forecast_persistence(self):
        """测试预测持久化。"""
        forecast = self.engine.create_forecast(
            question="Persist Test",
            target="PersistTarget",
            prediction="PersistPrediction",
            probability=0.5,
            confidence=0.5
        )

        found = self.engine.get_forecast(forecast.forecast_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.prediction, "PersistPrediction")

    def test_merge_evidence(self):
        """测试证据融合。"""
        forecast = self.engine.create_forecast(
            question="Q", target="T", prediction="P",
            probability=0.5, confidence=0.5
        )

        result = self.engine.merge_evidence(forecast.forecast_id)
        self.assertIsInstance(result, dict)
        self.assertIn("forecast_id", result)
        self.assertIn("sources", result)
        self.assertIn("total_evidence", result)
        self.assertIn("fused_confidence", result)


class TestPhase146API(unittest.TestCase):
    """测试API端点结构。"""

    def test_api_endpoints_defined(self):
        """测试API端点定义。"""
        from gfe_forecast import get_forecast_engine

        engine = get_forecast_engine()
        self.assertIsNotNone(engine)


class TestPhase146SeedData(unittest.TestCase):
    """测试种子数据。"""

    def setUp(self):
        """初始化数据库。"""
        self.conn = db_conn()
        _migrate_gfe_forecast_engine(self.conn)

    def test_seed_data(self):
        """测试种子数据加载。"""
        reset_forecast_engine()
        engine = get_forecast_engine()
        engine._conn = lambda: self.conn

        seed_forecasts()

        forecasts = engine.get_forecasts()
        self.assertGreater(len(forecasts), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
