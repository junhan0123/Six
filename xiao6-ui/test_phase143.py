#!/usr/bin/env python3
"""PHASE 143 — GFE Causal Graph Foundation Tests

测试因果图谱基础功能：
- 数据库表创建
- 节点CRUD
- 边CRUD
- 图遍历
- 路径查找
- 影响路径计算
- EventBus集成
- API端点结构
"""

import os
import sys
import time
import unittest

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import db_conn, _migrate_gfe_causal_graph
from gfe_causal import (
    CausalGraphEngine,
    CausalNode,
    CausalEdge,
    CausalPath,
    get_causal_graph_engine,
    reset_causal_graph_engine,
    seed_causal_graph,
    RELATIONSHIP_CAUSE,
    RELATIONSHIP_LEAD_TO,
    CATEGORY_ENERGY,
    CATEGORY_FINANCE,
    CATEGORY_ECONOMY,
    CATEGORY_TECHNOLOGY,
)
from eventbus import SYSTEM_EVENT_NAMES


class TestPhase143Database(unittest.TestCase):
    """测试数据库迁移。"""

    def setUp(self):
        """初始化数据库。"""
        self.conn = db_conn()
        _migrate_gfe_causal_graph(self.conn)

    def tearDown(self):
        """清理测试数据。"""
        self.conn.execute("DELETE FROM gfe_causal_edges")
        self.conn.execute("DELETE FROM gfe_causal_nodes")
        self.conn.commit()

    def test_tables_exist(self):
        """测试表存在。"""
        tables = [r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'gfe_%'"
        ).fetchall()]

        self.assertIn("gfe_causal_nodes", tables)
        self.assertIn("gfe_causal_edges", tables)

    def test_nodes_schema(self):
        """测试节点表结构。"""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(gfe_causal_nodes)").fetchall()}

        required_cols = {
            "node_id", "name", "category", "description",
            "entity_type", "provenance", "created_at"
        }

        self.assertTrue(required_cols.issubset(cols), f"Missing columns: {required_cols - cols}")

    def test_edges_schema(self):
        """测试边表结构。"""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(gfe_causal_edges)").fetchall()}

        required_cols = {
            "edge_id", "source_node", "target_node",
            "relationship_type", "strength", "confidence",
            "time_delay", "evidence_refs", "provenance", "created_at"
        }

        self.assertTrue(required_cols.issubset(cols), f"Missing columns: {required_cols - cols}")


class TestPhase143Engine(unittest.TestCase):
    """测试核心引擎功能。"""

    def setUp(self):
        """初始化测试环境。"""
        reset_causal_graph_engine()
        self.engine = get_causal_graph_engine()
        self.conn = db_conn()
        _migrate_gfe_causal_graph(self.conn)

    def tearDown(self):
        """清理测试数据。"""
        self.conn.execute("DELETE FROM gfe_causal_edges")
        self.conn.execute("DELETE FROM gfe_causal_nodes")
        self.conn.commit()

    def test_add_node(self):
        """测试添加节点。"""
        node = self.engine.add_node(
            name="Test Node",
            category=CATEGORY_ECONOMY,
            description="A test node",
            provenance="test_source"
        )

        self.assertIsNotNone(node)
        self.assertEqual(node.name, "Test Node")
        self.assertEqual(node.category, CATEGORY_ECONOMY)
        self.assertIsNotNone(node.node_id)
        self.assertGreater(node.created_at, 0)

    def test_add_edge(self):
        """测试添加边。"""
        source = self.engine.add_node(name="Source", category=CATEGORY_ECONOMY, provenance="test")
        target = self.engine.add_node(name="Target", category=CATEGORY_FINANCE, provenance="test")

        edge = self.engine.add_edge(
            source_node=source.node_id,
            target_node=target.node_id,
            relationship_type=RELATIONSHIP_CAUSE,
            strength=0.8,
            confidence=0.9,
            provenance="test"
        )

        self.assertIsNotNone(edge)
        self.assertEqual(edge.source_node, source.node_id)
        self.assertEqual(edge.target_node, target.node_id)
        self.assertEqual(edge.strength, 0.8)

    def test_get_nodes(self):
        """测试查询节点。"""
        self.engine.add_node(name="Node A", category=CATEGORY_ECONOMY, provenance="test")
        self.engine.add_node(name="Node B", category=CATEGORY_FINANCE, provenance="test")
        self.engine.add_node(name="Node C", category=CATEGORY_ENERGY, provenance="test")

        nodes = self.engine.get_nodes(limit=10)
        self.assertEqual(len(nodes), 3)

    def test_get_edges(self):
        """测试查询边。"""
        source = self.engine.add_node(name="Source", category=CATEGORY_ECONOMY, provenance="test")
        target = self.engine.add_node(name="Target", category=CATEGORY_FINANCE, provenance="test")
        self.engine.add_edge(source.node_id, target.node_id, RELATIONSHIP_CAUSE, 0.8, provenance="test")

        edges = self.engine.get_edges(limit=10)
        self.assertEqual(len(edges), 1)

    def test_find_path(self):
        """测试路径查找。"""
        # 构建简单图：A -> B -> C
        a = self.engine.add_node(name="A", category=CATEGORY_ECONOMY, provenance="test")
        b = self.engine.add_node(name="B", category=CATEGORY_FINANCE, provenance="test")
        c = self.engine.add_node(name="C", category=CATEGORY_ENERGY, provenance="test")

        self.engine.add_edge(a.node_id, b.node_id, RELATIONSHIP_CAUSE, 0.8, provenance="test")
        self.engine.add_edge(b.node_id, c.node_id, RELATIONSHIP_CAUSE, 0.7, provenance="test")

        path = self.engine.find_path(a.node_id, c.node_id)

        self.assertIsNotNone(path)
        self.assertEqual(path.start_node, a.node_id)
        self.assertEqual(path.end_node, c.node_id)
        self.assertEqual(len(path.nodes), 3)
        self.assertEqual(path.nodes[0], a.node_id)
        self.assertEqual(path.nodes[2], c.node_id)

    def test_find_path_not_exist(self):
        """测试不存在的路径。"""
        a = self.engine.add_node(name="A", category=CATEGORY_ECONOMY, provenance="test")
        b = self.engine.add_node(name="B", category=CATEGORY_FINANCE, provenance="test")

        path = self.engine.find_path(a.node_id, b.node_id)
        self.assertIsNone(path)

    def test_calculate_impact_path(self):
        """测试影响路径计算。"""
        # 构建链式图
        nodes = []
        for i in range(5):
            node = self.engine.add_node(name=f"Node{i}", category=CATEGORY_ECONOMY, provenance="test")
            nodes.append(node)

        for i in range(len(nodes) - 1):
            self.engine.add_edge(nodes[i].node_id, nodes[i + 1].node_id, RELATIONSHIP_CAUSE, 0.8, provenance="test")

        impacts = self.engine.calculate_impact_path(nodes[0].node_id)

        self.assertEqual(len(impacts), 4)  # 5个节点，排除自身

    def test_get_node_by_name(self):
        """测试按名称获取节点。"""
        node = self.engine.add_node(name="UniqueNode", category=CATEGORY_ECONOMY, provenance="test")

        found = self.engine.get_node_by_name("UniqueNode")
        self.assertIsNotNone(found)
        self.assertEqual(found.node_id, node.node_id)

    def test_eventbus_topics_registered(self):
        """测试EventBus主题已注册。"""
        required_topics = [
            "gfe_causal_node_added",
            "gfe_causal_edge_added",
            "gfe_causal_path_generated"
        ]

        for topic in required_topics:
            self.assertIn(topic, SYSTEM_EVENT_NAMES, f"Topic {topic} not registered")

    def test_to_frontend_format(self):
        """测试前端格式转换。"""
        node = CausalNode(
            node_id="test_1",
            name="Test Node",
            category=CATEGORY_ECONOMY,
            description="A test",
            entity_type="indicator",
            provenance="test_source"
        )

        frontend = node.to_frontend()
        self.assertIn("node_id", frontend)
        self.assertIn("name", frontend)
        self.assertIn("category", frontend)

    def test_path_strength_calculation(self):
        """测试路径强度计算。"""
        a = self.engine.add_node(name="A", category=CATEGORY_ECONOMY, provenance="test")
        b = self.engine.add_node(name="B", category=CATEGORY_FINANCE, provenance="test")
        c = self.engine.add_node(name="C", category=CATEGORY_ENERGY, provenance="test")

        self.engine.add_edge(a.node_id, b.node_id, RELATIONSHIP_CAUSE, 0.8, provenance="test")
        self.engine.add_edge(b.node_id, c.node_id, RELATIONSHIP_CAUSE, 0.6, provenance="test")

        path = self.engine.find_path(a.node_id, c.node_id)
        self.assertIsNotNone(path)
        self.assertGreater(path.total_strength, 0)
        self.assertLessEqual(path.total_strength, 1.0)


class TestPhase143API(unittest.TestCase):
    """测试API端点结构。"""

    def test_api_endpoints_defined(self):
        """测试API端点定义。"""
        from gfe_causal import get_causal_graph_engine

        engine = get_causal_graph_engine()
        self.assertIsNotNone(engine)


class TestPhase143SeedData(unittest.TestCase):
    """测试种子数据。"""

    def setUp(self):
        """初始化数据库。"""
        self.conn = db_conn()
        _migrate_gfe_causal_graph(self.conn)

    def test_seed_data(self):
        """测试种子数据加载。"""
        reset_causal_graph_engine()
        engine = get_causal_graph_engine()
        engine._conn = lambda: self.conn

        seed_causal_graph()

        nodes = engine.get_nodes()
        self.assertGreater(len(nodes), 0)

        edges = engine.get_edges()
        self.assertGreater(len(edges), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
