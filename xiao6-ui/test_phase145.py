#!/usr/bin/env python3
"""PHASE 145 — GFE Scenario Engine Foundation Tests

测试情景引擎基础功能：
- 数据库表创建
- 情景创建
- 假设保存
- 影响计算
- 多情景对比
- 数据持久化
- EventBus集成
"""

import os
import sys
import time
import unittest

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import db_conn, _migrate_gfe_scenario_engine
from gfe_scenario import (
    ScenarioEngine,
    Scenario,
    ScenarioImpact,
    ScenarioPath,
    get_scenario_engine,
    reset_scenario_engine,
    seed_scenarios,
    DIMENSION_ECONOMY,
    DIMENSION_FINANCE,
    DIMENSION_TECHNOLOGY,
    DIRECTION_POSITIVE,
    DIRECTION_NEGATIVE,
)
from eventbus import SYSTEM_EVENT_NAMES


class TestPhase145Database(unittest.TestCase):
    """测试数据库迁移。"""

    def setUp(self):
        """初始化数据库。"""
        self.conn = db_conn()
        _migrate_gfe_scenario_engine(self.conn)

    def tearDown(self):
        """清理测试数据。"""
        self.conn.execute("DELETE FROM gfe_scenario_paths")
        self.conn.execute("DELETE FROM gfe_scenario_impacts")
        self.conn.execute("DELETE FROM gfe_scenarios")
        self.conn.commit()

    def test_tables_exist(self):
        """测试表存在。"""
        tables = [r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'gfe_%'"
        ).fetchall()]

        self.assertIn("gfe_scenarios", tables)
        self.assertIn("gfe_scenario_impacts", tables)
        self.assertIn("gfe_scenario_paths", tables)

    def test_scenarios_schema(self):
        """测试情景表结构。"""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(gfe_scenarios)").fetchall()}

        required_cols = {
            "scenario_id", "question", "name", "description",
            "assumptions", "probability", "confidence", "created_at"
        }

        self.assertTrue(required_cols.issubset(cols), f"Missing columns: {required_cols - cols}")

    def test_impacts_schema(self):
        """测试影响表结构。"""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(gfe_scenario_impacts)").fetchall()}

        required_cols = {
            "impact_id", "scenario_id", "dimension",
            "direction", "strength", "reason", "confidence", "created_at"
        }

        self.assertTrue(required_cols.issubset(cols), f"Missing columns: {required_cols - cols}")

    def test_paths_schema(self):
        """测试路径表结构。"""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(gfe_scenario_paths)").fetchall()}

        required_cols = {
            "path_id", "scenario_id", "source_node",
            "target_node", "impact_score", "time_horizon", "created_at"
        }

        self.assertTrue(required_cols.issubset(cols), f"Missing columns: {required_cols - cols}")


class TestPhase145Engine(unittest.TestCase):
    """测试核心引擎功能。"""

    def setUp(self):
        """初始化测试环境。"""
        reset_scenario_engine()
        self.engine = get_scenario_engine()
        self.conn = db_conn()
        _migrate_gfe_scenario_engine(self.conn)

    def tearDown(self):
        """清理测试数据。"""
        self.conn.execute("DELETE FROM gfe_scenario_paths")
        self.conn.execute("DELETE FROM gfe_scenario_impacts")
        self.conn.execute("DELETE FROM gfe_scenarios")
        self.conn.commit()

    def test_create_scenario(self):
        """测试创建情景。"""
        scenario = self.engine.create_scenario(
            question="What will happen?",
            name="Test Scenario",
            description="A test scenario",
            assumptions={"key": "value"},
            probability=0.6,
            confidence=0.7
        )

        self.assertIsNotNone(scenario)
        self.assertEqual(scenario.name, "Test Scenario")
        self.assertEqual(scenario.question, "What will happen?")
        self.assertEqual(scenario.probability, 0.6)
        self.assertEqual(scenario.confidence, 0.7)
        self.assertEqual(scenario.assumptions, {"key": "value"})
        self.assertIsNotNone(scenario.scenario_id)

    def test_add_impact(self):
        """测试添加影响。"""
        scenario = self.engine.create_scenario(
            question="Q", name="S", probability=0.5, confidence=0.5
        )

        impact = self.engine.add_impact(
            scenario_id=scenario.scenario_id,
            dimension=DIMENSION_ECONOMY,
            direction=DIRECTION_NEGATIVE,
            strength=0.8,
            reason="Test reason",
            confidence=0.75
        )

        self.assertIsNotNone(impact)
        self.assertEqual(impact.dimension, DIMENSION_ECONOMY)
        self.assertEqual(impact.direction, DIRECTION_NEGATIVE)
        self.assertEqual(impact.strength, 0.8)

    def test_add_path(self):
        """测试添加路径。"""
        scenario = self.engine.create_scenario(
            question="Q", name="S", probability=0.5, confidence=0.5
        )

        path = self.engine.add_path(
            scenario_id=scenario.scenario_id,
            source_node="node_a",
            target_node="node_b",
            impact_score=0.7,
            time_horizon=365
        )

        self.assertIsNotNone(path)
        self.assertEqual(path.source_node, "node_a")
        self.assertEqual(path.target_node, "node_b")
        self.assertEqual(path.impact_score, 0.7)

    def test_get_scenario(self):
        """测试获取情景。"""
        scenario = self.engine.create_scenario(
            question="Q", name="S", probability=0.5, confidence=0.5
        )

        found = self.engine.get_scenario(scenario.scenario_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.scenario_id, scenario.scenario_id)

    def test_get_scenarios(self):
        """测试查询情景。"""
        self.engine.create_scenario(question="Q1", name="S1", probability=0.5, confidence=0.5)
        self.engine.create_scenario(question="Q2", name="S2", probability=0.6, confidence=0.6)
        self.engine.create_scenario(question="Q1", name="S3", probability=0.7, confidence=0.7)

        scenarios = self.engine.get_scenarios(limit=10)
        self.assertEqual(len(scenarios), 3)

        q1_scenarios = self.engine.get_scenarios(question="Q1")
        self.assertEqual(len(q1_scenarios), 2)

    def test_get_impacts(self):
        """测试查询影响。"""
        scenario = self.engine.create_scenario(question="Q", name="S", probability=0.5, confidence=0.5)
        self.engine.add_impact(scenario.scenario_id, DIMENSION_ECONOMY, DIRECTION_NEGATIVE, 0.8)
        self.engine.add_impact(scenario.scenario_id, DIMENSION_FINANCE, DIRECTION_NEGATIVE, 0.7)

        impacts = self.engine.get_impacts(scenario.scenario_id)
        self.assertEqual(len(impacts), 2)

    def test_get_paths(self):
        """测试查询路径。"""
        scenario = self.engine.create_scenario(question="Q", name="S", probability=0.5, confidence=0.5)
        self.engine.add_path(scenario.scenario_id, "a", "b", 0.7)
        self.engine.add_path(scenario.scenario_id, "b", "c", 0.6)

        paths = self.engine.get_paths(scenario.scenario_id)
        self.assertEqual(len(paths), 2)

    def test_evaluate_scenario(self):
        """测试评估情景。"""
        scenario = self.engine.create_scenario(
            question="Q", name="S", probability=0.6, confidence=0.7
        )
        self.engine.add_impact(scenario.scenario_id, DIMENSION_ECONOMY, DIRECTION_NEGATIVE, 0.8, confidence=0.75)
        self.engine.add_impact(scenario.scenario_id, DIMENSION_FINANCE, DIRECTION_NEGATIVE, 0.7, confidence=0.7)

        result = self.engine.evaluate_scenario(scenario.scenario_id)

        self.assertIsNotNone(result)
        self.assertEqual(result["scenario_id"], scenario.scenario_id)
        self.assertEqual(len(result["impacts"]), 2)
        self.assertGreater(result["overall_score"], 0)

    def test_compare_scenarios(self):
        """测试对比情景。"""
        s1 = self.engine.create_scenario(question="Q", name="S1", probability=0.6, confidence=0.7)
        s2 = self.engine.create_scenario(question="Q", name="S2", probability=0.8, confidence=0.8)

        self.engine.add_impact(s1.scenario_id, DIMENSION_ECONOMY, DIRECTION_NEGATIVE, 0.6)
        self.engine.add_impact(s2.scenario_id, DIMENSION_ECONOMY, DIRECTION_NEGATIVE, 0.9)

        comparisons = self.engine.compare_scenarios([s1.scenario_id, s2.scenario_id])

        self.assertEqual(len(comparisons), 2)
        # 按得分排序，S2 应该排第一
        self.assertGreater(comparisons[0]["overall_score"], comparisons[1]["overall_score"])

    def test_eventbus_topics_registered(self):
        """测试EventBus主题已注册。"""
        required_topics = [
            "gfe_scenario_created",
            "gfe_scenario_evaluated"
        ]

        for topic in required_topics:
            self.assertIn(topic, SYSTEM_EVENT_NAMES, f"Topic {topic} not registered")

    def test_to_frontend_format(self):
        """测试前端格式转换。"""
        scenario = Scenario(
            scenario_id="test_1",
            question="Q",
            name="Test",
            description="A test scenario",
            assumptions={"key": "value"},
            probability=0.6,
            confidence=0.7
        )

        frontend = scenario.to_frontend()
        self.assertIn("scenario_id", frontend)
        self.assertIn("name", frontend)
        self.assertIn("assumptions", frontend)

    def test_scenario_persistence(self):
        """测试情景持久化。"""
        scenario = self.engine.create_scenario(
            question="Persist Test",
            name="Persistent",
            probability=0.5,
            confidence=0.5
        )

        # 重新获取
        found = self.engine.get_scenario(scenario.scenario_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Persistent")


class TestPhase145API(unittest.TestCase):
    """测试API端点结构。"""

    def test_api_endpoints_defined(self):
        """测试API端点定义。"""
        from gfe_scenario import get_scenario_engine

        engine = get_scenario_engine()
        self.assertIsNotNone(engine)


class TestPhase145SeedData(unittest.TestCase):
    """测试种子数据。"""

    def setUp(self):
        """初始化数据库。"""
        self.conn = db_conn()
        _migrate_gfe_scenario_engine(self.conn)

    def test_seed_data(self):
        """测试种子数据加载。"""
        reset_scenario_engine()
        engine = get_scenario_engine()
        engine._conn = lambda: self.conn

        seed_scenarios()

        scenarios = engine.get_scenarios()
        self.assertGreater(len(scenarios), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
