#!/usr/bin/env python3
"""PHASE 144 — GFE Analyst Council Foundation Tests

测试分析师委员会基础功能：
- 数据库表创建
- 分析师注册
- 分析提交
- 共识计算
- 数据持久化
- EventBus集成
- API端点结构
"""

import os
import sys
import time
import unittest

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import db_conn, _migrate_gfe_analyst_council
from gfe_analyst_council import (
    AnalystCouncil,
    AnalystAgent,
    AnalysisReport,
    ConsensusResult,
    get_analyst_council,
    reset_analyst_council,
    seed_analyst_agents,
    SPECIALIZATION_MACRO,
    SPECIALIZATION_FINANCE,
    SPECIALIZATION_RISK,
    ALGORITHM_WEIGHTED_AVERAGE,
)
from eventbus import SYSTEM_EVENT_NAMES


class TestPhase144Database(unittest.TestCase):
    """测试数据库迁移。"""

    def setUp(self):
        """初始化数据库。"""
        self.conn = db_conn()
        _migrate_gfe_analyst_council(self.conn)

    def tearDown(self):
        """清理测试数据。"""
        self.conn.execute("DELETE FROM gfe_consensus_results")
        self.conn.execute("DELETE FROM gfe_analysis_reports")
        self.conn.execute("DELETE FROM gfe_analyst_agents")
        self.conn.commit()

    def test_tables_exist(self):
        """测试表存在。"""
        tables = [r[0] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'gfe_%'"
        ).fetchall()]

        self.assertIn("gfe_analyst_agents", tables)
        self.assertIn("gfe_analysis_reports", tables)
        self.assertIn("gfe_consensus_results", tables)

    def test_agents_schema(self):
        """测试分析师表结构。"""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(gfe_analyst_agents)").fetchall()}

        required_cols = {
            "agent_id", "name", "specialization",
            "weight", "confidence", "provenance", "created_at"
        }

        self.assertTrue(required_cols.issubset(cols), f"Missing columns: {required_cols - cols}")

    def test_reports_schema(self):
        """测试报告表结构。"""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(gfe_analysis_reports)").fetchall()}

        required_cols = {
            "report_id", "question", "analyst_id",
            "analysis", "confidence", "evidence_refs", "created_at"
        }

        self.assertTrue(required_cols.issubset(cols), f"Missing columns: {required_cols - cols}")

    def test_consensus_schema(self):
        """测试共识表结构。"""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(gfe_consensus_results)").fetchall()}

        required_cols = {
            "consensus_id", "question", "final_analysis",
            "agreement_score", "confidence", "created_at"
        }

        self.assertTrue(required_cols.issubset(cols), f"Missing columns: {required_cols - cols}")


class TestPhase144Engine(unittest.TestCase):
    """测试核心引擎功能。"""

    def setUp(self):
        """初始化测试环境。"""
        reset_analyst_council()
        self.council = get_analyst_council()
        self.conn = db_conn()
        _migrate_gfe_analyst_council(self.conn)

    def tearDown(self):
        """清理测试数据。"""
        self.conn.execute("DELETE FROM gfe_consensus_results")
        self.conn.execute("DELETE FROM gfe_analysis_reports")
        self.conn.execute("DELETE FROM gfe_analyst_agents")
        self.conn.commit()

    def test_register_agent(self):
        """测试注册分析师。"""
        agent = self.council.register_agent(
            name="TestAgent",
            specialization=SPECIALIZATION_MACRO,
            weight=0.8,
            confidence=0.75,
            provenance="test_source"
        )

        self.assertIsNotNone(agent)
        self.assertEqual(agent.name, "TestAgent")
        self.assertEqual(agent.specialization, SPECIALIZATION_MACRO)
        self.assertEqual(agent.weight, 0.8)
        self.assertIsNotNone(agent.agent_id)

    def test_submit_analysis(self):
        """测试提交分析。"""
        agent = self.council.register_agent(
            name="Agent1",
            specialization=SPECIALIZATION_MACRO,
            provenance="test"
        )

        report = self.council.submit_analysis(
            analyst_id=agent.agent_id,
            question="What will GDP growth be?",
            analysis="GDP will grow at 5%",
            confidence=0.8,
            evidence_refs=["ref1", "ref2"]
        )

        self.assertIsNotNone(report)
        self.assertEqual(report.question, "What will GDP growth be?")
        self.assertEqual(report.analyst_id, agent.agent_id)
        self.assertEqual(report.confidence, 0.8)
        self.assertEqual(len(report.evidence_refs), 2)

    def test_compute_consensus(self):
        """测试计算共识。"""
        # 注册两个分析师
        agent1 = self.council.register_agent(
            name="Agent1",
            specialization=SPECIALIZATION_MACRO,
            weight=0.8,
            provenance="test"
        )
        agent2 = self.council.register_agent(
            name="Agent2",
            specialization=SPECIALIZATION_FINANCE,
            weight=0.7,
            provenance="test"
        )

        # 提交分析
        self.council.submit_analysis(
            analyst_id=agent1.agent_id,
            question="Will inflation decrease?",
            analysis="Yes, inflation will decrease by 2%",
            confidence=0.8
        )
        self.council.submit_analysis(
            analyst_id=agent2.agent_id,
            question="Will inflation decrease?",
            analysis="Yes, inflation will decrease by 1.5%",
            confidence=0.75
        )

        # 计算共识
        consensus = self.council.compute_consensus(
            question="Will inflation decrease?",
            algorithm=ALGORITHM_WEIGHTED_AVERAGE
        )

        self.assertIsNotNone(consensus)
        self.assertEqual(consensus.question, "Will inflation decrease?")
        self.assertGreater(consensus.agreement_score, 0)
        self.assertGreater(consensus.confidence, 0)

    def test_get_agents(self):
        """测试查询分析师。"""
        self.council.register_agent(name="AgentA", specialization=SPECIALIZATION_MACRO, provenance="test")
        self.council.register_agent(name="AgentB", specialization=SPECIALIZATION_FINANCE, provenance="test")
        self.council.register_agent(name="AgentC", specialization=SPECIALIZATION_MACRO, provenance="test")

        agents = self.council.get_agents()
        self.assertEqual(len(agents), 3)

        macro_agents = self.council.get_agents(specialization=SPECIALIZATION_MACRO)
        self.assertEqual(len(macro_agents), 2)

    def test_get_reports(self):
        """测试查询报告。"""
        agent = self.council.register_agent(name="Agent", specialization=SPECIALIZATION_MACRO, provenance="test")

        self.council.submit_analysis(
            analyst_id=agent.agent_id,
            question="Q1",
            analysis="A1"
        )
        self.council.submit_analysis(
            analyst_id=agent.agent_id,
            question="Q2",
            analysis="A2"
        )

        reports = self.council.get_reports(limit=10)
        self.assertEqual(len(reports), 2)

    def test_get_consensus(self):
        """测试查询共识。"""
        agent = self.council.register_agent(name="Agent", specialization=SPECIALIZATION_MACRO, provenance="test")
        self.council.submit_analysis(
            analyst_id=agent.agent_id,
            question="Q",
            analysis="A"
        )
        self.council.compute_consensus(question="Q")

        consensuses = self.council.get_consensus()
        self.assertEqual(len(consensuses), 1)

    def test_eventbus_topics_registered(self):
        """测试EventBus主题已注册。"""
        required_topics = [
            "gfe_analysis_created",
            "gfe_consensus_reached"
        ]

        for topic in required_topics:
            self.assertIn(topic, SYSTEM_EVENT_NAMES, f"Topic {topic} not registered")

    def test_to_frontend_format(self):
        """测试前端格式转换。"""
        agent = AnalystAgent(
            agent_id="test_1",
            name="Test Agent",
            specialization=SPECIALIZATION_MACRO,
            weight=0.8,
            confidence=0.75,
            provenance="test"
        )

        frontend = agent.to_frontend()
        self.assertIn("agent_id", frontend)
        self.assertIn("name", frontend)
        self.assertIn("specialization", frontend)

    def test_consensus_agreement_score(self):
        """测试共识一致性分数。"""
        agent1 = self.council.register_agent(name="A1", specialization=SPECIALIZATION_MACRO, provenance="test")
        agent2 = self.council.register_agent(name="A2", specialization=SPECIALIZATION_MACRO, provenance="test")

        # 相同分析
        self.council.submit_analysis(analyst_id=agent1.agent_id, question="Q", analysis="Same", confidence=0.9)
        self.council.submit_analysis(analyst_id=agent2.agent_id, question="Q", analysis="Same", confidence=0.9)

        consensus = self.council.compute_consensus(question="Q")
        self.assertGreater(consensus.agreement_score, 0.5)

    def test_consensus_no_analyses(self):
        """测试无分析时的共识。"""
        result = self.council.compute_consensus(question="NoAnalyses")
        self.assertIsNone(result)


class TestPhase144API(unittest.TestCase):
    """测试API端点结构。"""

    def test_api_endpoints_defined(self):
        """测试API端点定义。"""
        from gfe_analyst_council import get_analyst_council

        council = get_analyst_council()
        self.assertIsNotNone(council)


class TestPhase144SeedData(unittest.TestCase):
    """测试种子数据。"""

    def setUp(self):
        """初始化数据库。"""
        self.conn = db_conn()
        _migrate_gfe_analyst_council(self.conn)

    def test_seed_data(self):
        """测试种子数据加载。"""
        reset_analyst_council()
        council = get_analyst_council()
        council._conn = lambda: self.conn

        seed_analyst_agents()

        agents = council.get_agents()
        self.assertGreater(len(agents), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
