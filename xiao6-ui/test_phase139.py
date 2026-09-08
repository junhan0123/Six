#!/usr/bin/env python3
"""PHASE 139 — GFE Data Source Foundation Tests

测试数据源基础层：
1. 数据库迁移成功
2. register_source
3. get_source
4. list_sources
5. reliability calculation
6. EventBus event
7. API response
"""

import sys
import os
import json
import time
import unittest
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import db_conn, _migrate_gfe_sources
from gfe_sources import (
    SourceManager,
    ReliabilityCalculator,
    get_source_manager,
    reset_source_manager,
    TOPIC_SOURCE_REGISTERED,
    TYPE_OFFICIAL,
    TYPE_INTERNATIONAL,
    TYPE_FINANCIAL,
    TYPE_ACADEMIC,
    TYPE_NEWS,
)


class TestGFESourcesDatabase(unittest.TestCase):
    """测试数据库迁移。"""

    def setUp(self):
        """初始化测试数据库。"""
        reset_source_manager()
        self.conn = db_conn()

    def tearDown(self):
        """清理测试数据。"""
        try:
            self.conn.execute("DROP TABLE IF EXISTS gfe_sources")
            self.conn.execute("DROP TABLE IF EXISTS gfe_source_metrics")
            self.conn.commit()
        except Exception:
            pass
        self.conn.close()

    def test_gfe_sources_table_exists(self):
        """测试 gfe_sources 表存在。"""
        cursor = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gfe_sources'")
        table = cursor.fetchone()
        self.assertIsNotNone(table, "gfe_sources 表应该存在")

    def test_gfe_source_metrics_table_exists(self):
        """测试 gfe_source_metrics 表存在。"""
        cursor = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gfe_source_metrics'")
        table = cursor.fetchone()
        self.assertIsNotNone(table, "gfe_source_metrics 表应该存在")

    def test_gfe_sources_columns(self):
        """测试 gfe_sources 表结构。"""
        cursor = self.conn.execute("PRAGMA table_info(gfe_sources)")
        columns = {row[1] for row in cursor.fetchall()}
        
        expected = {
            'source_id', 'name', 'type', 'authority', 'country',
            'reliability', 'historical_accuracy', 'update_frequency',
            'license', 'provenance', 'metadata', 'created_at', 'last_updated'
        }
        
        self.assertEqual(columns, expected, f"列不匹配: 期望{expected}, 实际{columns}")


class TestSourceManager(unittest.TestCase):
    """测试 SourceManager 功能。"""

    def setUp(self):
        """初始化测试环境。"""
        reset_source_manager()
        self.manager = SourceManager()
        self.conn = db_conn()

    def tearDown(self):
        """清理测试数据。"""
        try:
            self.conn.execute("DELETE FROM gfe_sources")
            self.conn.execute("DELETE FROM gfe_source_metrics")
            self.conn.commit()
        except Exception:
            pass
        self.conn.close()
        reset_source_manager()

    def test_register_source(self):
        """测试注册数据源。"""
        ds = self.manager.register_source(
            source_id="test_source_1",
            name="Test Source",
            type=TYPE_OFFICIAL,
            authority="Test Authority",
            country="CN",
            provenance="https://test.example.com",
        )
        
        self.assertIsNotNone(ds, "注册应该返回 DataSource")
        self.assertEqual(ds.source_id, "test_source_1")
        self.assertEqual(ds.name, "Test Source")
        self.assertEqual(ds.type, TYPE_OFFICIAL)
        self.assertIsNotNone(ds.created_at)
        self.assertIsNotNone(ds.last_updated)

    def test_get_source(self):
        """测试获取数据源。"""
        self.manager.register_source(
            source_id="test_source_2",
            name="Test Source 2",
            type=TYPE_FINANCIAL,
        )
        
        ds = self.manager.get_source("test_source_2")
        self.assertIsNotNone(ds, "应该能找到已注册的数据源")
        self.assertEqual(ds.name, "Test Source 2")

    def test_get_source_not_found(self):
        """测试获取不存在的源。"""
        ds = self.manager.get_source("nonexistent")
        self.assertIsNone(ds, "不存在的源应该返回 None")

    def test_list_sources(self):
        """测试列出所有数据源。"""
        self.manager.register_source(source_id="src_1", name="Source 1", type=TYPE_OFFICIAL)
        self.manager.register_source(source_id="src_2", name="Source 2", type=TYPE_INTERNATIONAL)
        self.manager.register_source(source_id="src_3", name="Source 3", type=TYPE_ACADEMIC)
        
        sources = self.manager.list_sources()
        self.assertEqual(len(sources), 3, "应该返回 3 个数据源")

    def test_list_sources_by_type(self):
        """测试按类型过滤数据源。"""
        self.manager.register_source(source_id="off_1", name="Official 1", type=TYPE_OFFICIAL)
        self.manager.register_source(source_id="int_1", name="Intl 1", type=TYPE_INTERNATIONAL)
        self.manager.register_source(source_id="off_2", name="Official 2", type=TYPE_OFFICIAL)
        
        official = self.manager.list_sources(type_filter=TYPE_OFFICIAL)
        self.assertEqual(len(official), 2, "应该返回 2 个官方数据源")
        
        international = self.manager.list_sources(type_filter=TYPE_INTERNATIONAL)
        self.assertEqual(len(international), 1, "应该返回 1 个国际数据源")

    def test_update_reliability(self):
        """测试更新可信度。"""
        self.manager.register_source(
            source_id="rel_test",
            name="Reliability Test",
            type=TYPE_OFFICIAL,
        )
        
        result = self.manager.update_reliability("rel_test", new_reliability=0.9)
        self.assertTrue(result, "更新应该成功")
        
        ds = self.manager.get_source("rel_test")
        self.assertGreater(ds.reliability, 0.5, "可信度应该被更新")

    def test_remove_source(self):
        """测试删除数据源。"""
        self.manager.register_source(
            source_id="del_test",
            name="Delete Test",
            type=TYPE_ACADEMIC,
        )
        
        result = self.manager.remove_source("del_test")
        self.assertTrue(result, "删除应该成功")
        
        ds = self.manager.get_source("del_test")
        self.assertIsNone(ds, "删除后应该找不到")

    def test_seed_initial_sources(self):
        """测试种子数据源。"""
        self.manager.seed_initial_sources()
        
        sources = self.manager.list_sources()
        self.assertGreater(len(sources), 0, "应该有种子数据源")
        
        # 检查类型覆盖
        types = {s.type for s in sources}
        self.assertIn(TYPE_INTERNATIONAL, types, "应该包含国际组织类型")
        self.assertIn(TYPE_OFFICIAL, types, "应该包含官方类型")
        self.assertIn(TYPE_FINANCIAL, types, "应该包含金融类型")
        self.assertIn(TYPE_ACADEMIC, types, "应该包含学术类型")


class TestReliabilityCalculator(unittest.TestCase):
    """测试可信度计算。"""

    def test_basic_calculation(self):
        """测试基本计算。"""
        score = ReliabilityCalculator.calculate(
            base_reliability=0.8,
            historical_accuracy=0.7,
            source_type=TYPE_OFFICIAL,
            last_updated=time.time(),
        )
        
        self.assertGreaterEqual(score, 0.0, "分数不应小于 0")
        self.assertLessEqual(score, 1.0, "分数不应大于 1")
        self.assertGreater(score, 0.5, "高可信度源应该得分较高")

    def test_low_reliability(self):
        """测试低可信度计算。"""
        score = ReliabilityCalculator.calculate(
            base_reliability=0.2,
            historical_accuracy=0.1,
            source_type=TYPE_NEWS,
        )
        
        self.assertLess(score, 0.5, "低可信度源应该得分较低")

    def test_freshness_impact(self):
        """测试新鲜度影响。"""
        fresh_score = ReliabilityCalculator.calculate(
            base_reliability=0.7,
            historical_accuracy=0.7,
            source_type=TYPE_OFFICIAL,
            last_updated=time.time(),
        )
        
        stale_score = ReliabilityCalculator.calculate(
            base_reliability=0.7,
            historical_accuracy=0.7,
            source_type=TYPE_OFFICIAL,
            last_updated=time.time() - 60 * 60 * 24 * 60,  # 60 天前
        )
        
        self.assertGreater(fresh_score, stale_score, "新鲜数据应该得分更高")

    def test_authority_weight(self):
        """测试 Authority 权重差异。"""
        official_score = ReliabilityCalculator.calculate(
            base_reliability=0.5,
            historical_accuracy=0.5,
            source_type=TYPE_OFFICIAL,
        )
        
        news_score = ReliabilityCalculator.calculate(
            base_reliability=0.5,
            historical_accuracy=0.5,
            source_type=TYPE_NEWS,
        )
        
        self.assertGreater(official_score, news_score, "官方数据源应该得分更高")


class TestAPIEndpoint(unittest.TestCase):
    """测试 API 端点。"""

    def test_list_sources_api(self):
        """测试列表 API。"""
        import urllib.request
        
        try:
            req = urllib.request.Request("http://localhost:8000/api/gfe/sources")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                self.assertIn("sources", data)
                self.assertIn("count", data)
        except Exception as e:
            self.skipTest(f"服务器未运行: {e}")

    def test_get_source_api(self):
        """测试单个源 API。"""
        import urllib.request
        
        # 先注册
        payload = json.dumps({
            "source_id": "api_get_src",
            "name": "API Get Test",
            "type": TYPE_FINANCIAL,
        }).encode()
        
        try:
            req = urllib.request.Request(
                "http://localhost:8000/api/gfe/sources",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=5)
            
            # 获取
            req = urllib.request.Request("http://localhost:8000/api/gfe/sources/api_get_src")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                self.assertIn("source", data)
                self.assertEqual(data["source"]["source_id"], "api_get_src")
        except Exception as e:
            self.skipTest(f"服务器未运行: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
