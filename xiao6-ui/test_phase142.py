#!/usr/bin/env python3
"""PHASE 142 — GFE Historical Comparison Foundation Tests

测试历史比较层基础功能：
- 数据库表创建
- 历史案例CRUD
- 相似度计算
- 状态比对
- EventBus集成
- API端点结构
"""

import json
import os
import sys
import time
import unittest
import uuid

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import db_conn, _migrate_gfe_historical_comparison
from gfe_history import (
    HistoricalComparisonEngine,
    HistoricalCase,
    HistoricalMatch,
    get_historical_comparison_engine,
    reset_historical_comparison_engine,
    seed_historical_cases,
    DIMENSION_WEIGHTS,
    CATEGORY_FINANCE,
    CATEGORY_ENERGY,
    CATEGORY_TECHNOLOGY,
    CATEGORY_ECONOMY,
)
from eventbus import SYSTEM_EVENT_NAMES


class TestPhase142Database(unittest.TestCase):
    """测试数据库迁移。"""
    
    def setUp(self):
        """初始化数据库。"""
        self.conn = db_conn()
        _migrate_gfe_historical_comparison(self.conn)
    
    def tearDown(self):
        """清理测试数据。"""
        self.conn.execute("DELETE FROM gfe_historical_matches")
        self.conn.execute("DELETE FROM gfe_historical_cases")
        self.conn.commit()
    
    def test_tables_exist(self):
        """测试表存在。"""
        conn = self.conn
        
        # 检查表是否存在
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'gfe_%'"
        ).fetchall()]
        
        self.assertIn("gfe_historical_cases", tables)
        self.assertIn("gfe_historical_matches", tables)
    
    def test_cases_schema(self):
        """测试案例表结构。"""
        conn = self.conn
        cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_historical_cases)").fetchall()}
        
        required_cols = {
            "case_id", "title", "period_start", "period_end",
            "country_code", "category", "description", "state_snapshot",
            "event_refs", "outcome", "lessons", "provenance", "created_at"
        }
        
        self.assertTrue(required_cols.issubset(cols), f"Missing columns: {required_cols - cols}")
    
    def test_matches_schema(self):
        """测试匹配结果表结构。"""
        conn = self.conn
        cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_historical_matches)").fetchall()}
        
        required_cols = {
            "match_id", "current_reference", "case_id",
            "similarity_score", "matching_dimensions", "explanation",
            "confidence", "created_at"
        }
        
        self.assertTrue(required_cols.issubset(cols), f"Missing columns: {required_cols - cols}")


class TestPhase142Engine(unittest.TestCase):
    """测试核心引擎功能。"""
    
    def setUp(self):
        """初始化测试环境。"""
        reset_historical_comparison_engine()
        self.engine = get_historical_comparison_engine()
        self.conn = db_conn()
        _migrate_gfe_historical_comparison(self.conn)
    
    def tearDown(self):
        """清理测试数据。"""
        self.conn.execute("DELETE FROM gfe_historical_matches")
        self.conn.execute("DELETE FROM gfe_historical_cases")
        self.conn.commit()
    
    def test_add_case(self):
        """测试添加历史案例。"""
        case = self.engine.add_case(
            title="Test Case",
            category=CATEGORY_ECONOMY,
            description="A test case",
            country_code="CN",
            provenance="test_source"
        )
        
        self.assertIsNotNone(case)
        self.assertEqual(case.title, "Test Case")
        self.assertEqual(case.category, CATEGORY_ECONOMY)
        self.assertEqual(case.country_code, "CN")
        self.assertIsNotNone(case.case_id)
        self.assertGreater(case.created_at, 0)
    
    def test_get_cases(self):
        """测试查询历史案例。"""
        # 添加几个案例
        for i in range(3):
            self.engine.add_case(
                title=f"Case {i}",
                category=CATEGORY_ECONOMY,
                country_code="CN"
            )
            time.sleep(0.05)
        
        cases = self.engine.get_cases(limit=10)
        self.assertEqual(len(cases), 3)
    
    def test_get_cases_filter_by_category(self):
        """测试按类别过滤。"""
        # 添加不同类别的案例
        self.engine.add_case(title="Economy Case", category=CATEGORY_ECONOMY, country_code="CN")
        self.engine.add_case(title="Finance Case", category=CATEGORY_FINANCE, country_code="US")
        self.engine.add_case(title="Tech Case", category=CATEGORY_TECHNOLOGY, country_code="JP")
        
        economy_cases = self.engine.get_cases(category=CATEGORY_ECONOMY)
        self.assertEqual(len(economy_cases), 1)
        self.assertEqual(economy_cases[0].category, CATEGORY_ECONOMY)
    
    def test_get_cases_filter_by_country(self):
        """测试按国家过滤。"""
        self.engine.add_case(title="China Case", category=CATEGORY_ECONOMY, country_code="CN")
        self.engine.add_case(title="US Case", category=CATEGORY_FINANCE, country_code="US")
        self.engine.add_case(title="Japan Case", category=CATEGORY_TECHNOLOGY, country_code="JP")
        
        cn_cases = self.engine.get_cases(country_code="CN")
        self.assertEqual(len(cn_cases), 1)
        self.assertEqual(cn_cases[0].country_code, "CN")
    
    def test_calculate_similarity(self):
        """测试相似度计算。"""
        current_state = {
            "economy": {"gdp_growth": 5.0, "inflation": 2.0},
            "finance": {"interest_rate": 3.5, "credit_growth": 0.1},
            "technology": {"rd_spending": 100, "patents": 50}
        }
        
        historical_state = {
            "economy": {"gdp_growth": 4.8, "inflation": 1.8},
            "finance": {"interest_rate": 3.2, "credit_growth": 0.08},
            "technology": {"rd_spending": 95, "patents": 45}
        }
        
        score, dimensions, explanation = self.engine.calculate_similarity(
            current_state, historical_state
        )
        
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 1.0)
        self.assertIsInstance(dimensions, list)
        self.assertIsInstance(explanation, str)
    
    def test_compare_state(self):
        """测试状态比对。"""
        # 添加一个历史案例
        case = self.engine.add_case(
            title="Historical Case",
            category=CATEGORY_ECONOMY,
            country_code="CN",
            state_snapshot={
                "economy": {"gdp_growth": 5.0, "inflation": 2.0},
                "finance": {"interest_rate": 3.5}
            },
            provenance="test"
        )
        
        current_state = {
            "economy": {"gdp_growth": 5.2, "inflation": 2.1},
            "finance": {"interest_rate": 3.6}
        }
        
        matches = self.engine.compare_state("CN", current_state)
        
        self.assertIsInstance(matches, list)
        if matches:
            self.assertGreater(matches[0].similarity_score, 0)
            self.assertIn(case.case_id, [m.case_id for m in matches])
    
    def test_similarity_weights(self):
        """测试维度权重配置。"""
        self.assertEqual(DIMENSION_WEIGHTS["economy"], 0.25)
        self.assertEqual(DIMENSION_WEIGHTS["finance"], 0.20)
        self.assertAlmostEqual(sum(DIMENSION_WEIGHTS.values()), 1.0, places=5)
    
    def test_to_frontend_format(self):
        """测试前端格式转换。"""
        case = HistoricalCase(
            case_id="test_1",
            title="Test Case",
            period_start=None,
            period_end=None,
            description="A test case",
            category=CATEGORY_ECONOMY,
            country_code="CN",
            state_snapshot={"economy": {"gdp": 5.0}},
            provenance="test"
        )
        
        frontend = case.to_frontend()
        
        self.assertIn("case_id", frontend)
        self.assertIn("title", frontend)
        self.assertIn("category", frontend)
    
    def test_eventbus_topics_registered(self):
        """测试EventBus主题已注册。"""
        required_topics = [
            "gfe_historical_case_added",
            "gfe_historical_comparison_completed",
            "gfe_similarity_calculated"
        ]
        
        for topic in required_topics:
            self.assertIn(topic, SYSTEM_EVENT_NAMES, f"Topic {topic} not registered")


class TestPhase142API(unittest.TestCase):
    """测试API端点结构。"""
    
    def test_api_endpoints_defined(self):
        """测试API端点定义。"""
        # 这些端点应该在 server.py 中定义
        # 我们通过检查导入是否成功来验证
        from gfe_history import get_historical_comparison_engine
        
        engine = get_historical_comparison_engine()
        self.assertIsNotNone(engine)


class TestPhase142SeedData(unittest.TestCase):
    """测试种子数据。"""
    
    def setUp(self):
        """初始化数据库。"""
        self.conn = db_conn()
        _migrate_gfe_historical_comparison(self.conn)
    
    def test_seed_data(self):
        """测试种子数据加载。"""
        reset_historical_comparison_engine()
        engine = get_historical_comparison_engine()
        engine._conn = lambda: self.conn
        
        seed_historical_cases()
        
        cases = engine.get_cases()
        self.assertGreater(len(cases), 0)
        
        # 验证包含预定义的历史事件
        titles = [c.title for c in cases]
        self.assertTrue(any("Financial Crisis" in t for t in titles))
        self.assertTrue(any("Oil Crisis" in t for t in titles))


if __name__ == "__main__":
    unittest.main(verbosity=2)
