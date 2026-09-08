#!/usr/bin/env python3
"""PHASE 141 — GFE Event Intelligence Tests

测试事件智能层：
1. 数据库表存在
2. 创建事件
3. 事件分类
4. 影响分析
5. 风险信号生成
6. EventBus 发布
7. API 结构

目标: 核心测试全部 PASS
"""

import sys
import os
import unittest
import time

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import db_conn, _migrate_gfe_events
from gfe_events import (
    EventIntelligenceEngine,
    GFEEvent,
    EventImpact,
    RiskSignal,
    get_event_intelligence_engine,
    reset_event_intelligence_engine,
    CATEGORY_ECONOMY,
    CATEGORY_FINANCE,
    CATEGORY_TECHNOLOGY,
    CATEGORY_ENERGY,
    CATEGORY_DIPLOMACY,
    STATUS_DETECTED,
    STATUS_ANALYZED,
    DIRECTION_NEGATIVE,
    DIRECTION_POSITIVE,
    SIGNAL_TYPE_ANOMALY,
    SIGNAL_TYPE_SHOCK,
    TOPIC_EVENT_DETECTED,
    TOPIC_EVENT_ANALYZED,
    TOPIC_RISK_SIGNAL_CREATED,
)


class TestEventDatabase(unittest.TestCase):
    """测试数据库迁移。"""

    def setUp(self):
        """初始化数据库。"""
        self.conn = db_conn()
        _migrate_gfe_events(self.conn)

    def tearDown(self):
        """清理测试数据。"""
        try:
            self.conn.execute("DELETE FROM gfe_risk_signals")
            self.conn.execute("DELETE FROM gfe_event_impacts")
            self.conn.execute("DELETE FROM gfe_events")
            self.conn.commit()
        except Exception:
            pass

    def test_gfe_events_table_exists(self):
        """测试 gfe_events 表存在。"""
        tables = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='gfe_events'"
        ).fetchall()
        self.assertEqual(len(tables), 1, "gfe_events 表应该存在")

    def test_gfe_event_impacts_table_exists(self):
        """测试 gfe_event_impacts 表存在。"""
        tables = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='gfe_event_impacts'"
        ).fetchall()
        self.assertEqual(len(tables), 1, "gfe_event_impacts 表应该存在")

    def test_gfe_risk_signals_table_exists(self):
        """测试 gfe_risk_signals 表存在。"""
        tables = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='gfe_risk_signals'"
        ).fetchall()
        self.assertEqual(len(tables), 1, "gfe_risk_signals 表应该存在")

    def test_gfe_events_columns(self):
        """测试 gfe_events 表结构。"""
        cols = {r[1] for r in self.conn.execute(
            "PRAGMA table_info(gfe_events)"
        ).fetchall()}

        required_cols = {
            "event_id", "source_id", "title", "summary", "category",
            "country_code", "region", "severity", "confidence",
            "impact", "status", "provenance", "event_time", "created_at"
        }

        self.assertTrue(required_cols.issubset(cols), f"缺少列: {required_cols - cols}")

    def test_gfe_risk_signals_columns(self):
        """测试 gfe_risk_signals 表结构。"""
        cols = {r[1] for r in self.conn.execute(
            "PRAGMA table_info(gfe_risk_signals)"
        ).fetchall()}

        required_cols = {
            "signal_id", "country_code", "signal_type", "description",
            "severity", "probability", "confidence", "source_event_ids",
            "status", "created_at"
        }

        self.assertTrue(required_cols.issubset(cols), f"缺少列: {required_cols - cols}")


class TestEventIntelligenceEngine(unittest.TestCase):
    """测试 EventIntelligenceEngine 核心功能。"""

    def setUp(self):
        """初始化引擎。"""
        reset_event_intelligence_engine()
        self.engine = get_event_intelligence_engine()
        self.conn = db_conn()
        # 确保测试前清理所有数据
        self.conn.execute("DELETE FROM gfe_risk_signals")
        self.conn.execute("DELETE FROM gfe_event_impacts")
        self.conn.execute("DELETE FROM gfe_events")
        self.conn.commit()

    def tearDown(self):
        """清理测试数据。"""
        try:
            self.conn.execute("DELETE FROM gfe_risk_signals")
            self.conn.execute("DELETE FROM gfe_event_impacts")
            self.conn.execute("DELETE FROM gfe_events")
            self.conn.commit()
        except Exception as e:
            print(f"[tearDown] 清理失败: {e}")

    def test_ingest_event(self):
        """测试摄入事件。"""
        event = self.engine.ingest_event(
            title="Federal Reserve Raises Interest Rates",
            category=CATEGORY_FINANCE,
            summary="The Fed raised interest rates by 25 basis points",
            country_code="US",
            provenance="Federal Reserve"
        )

        self.assertIsNotNone(event, "事件摄入应该成功")
        self.assertEqual(event.title, "Federal Reserve Raises Interest Rates")
        self.assertEqual(event.category, CATEGORY_FINANCE)
        self.assertEqual(event.country_code, "US")
        self.assertEqual(event.status, STATUS_DETECTED)

    def test_classify_event(self):
        """测试事件分类。"""
        event = GFEEvent(
            event_id="test_1",
            source_id=None,
            title="China imposes new tariff on US goods",
            summary="New trade restrictions announced",
            category=CATEGORY_ECONOMY,
            country_code="CN",
            region="Asia"
        )

        # 分类应该识别贸易相关的经济事件
        classified = self.engine.classify_event(event)

        # 分类可能根据关键词调整（tariff 可能匹配 policy 或 economy）
        self.assertIsNotNone(classified)
        # 接受合理分类：economy, diplomacy, policy 都是可能的
        self.assertIn(classified.category, [CATEGORY_ECONOMY, CATEGORY_DIPLOMACY, "policy"])

    def test_analyze_impact(self):
        """测试影响分析。"""
        event = self.engine.ingest_event(
            title="Central Bank Rate Hike",
            category=CATEGORY_FINANCE,
            country_code="US"
        )

        self.assertIsNotNone(event)

        # 分析影响
        impacts = self.engine.analyze_impact(event)

        self.assertGreaterEqual(len(impacts), 1, "应该至少有一条影响记录")
        self.assertEqual(impacts[0].event_id, event.event_id)

    def test_create_risk_signal(self):
        """测试创建风险信号。"""
        signal = self.engine.create_risk_signal(
            country_code="CN",
            signal_type=SIGNAL_TYPE_ANOMALY,
            description="Unusual trade flow pattern detected",
            severity=0.7,
            probability=0.6,
            confidence=0.8,
            source_event_ids=["evt_001"]
        )

        self.assertIsNotNone(signal, "风险信号创建应该成功")
        self.assertEqual(signal.country_code, "CN")
        self.assertEqual(signal.signal_type, SIGNAL_TYPE_ANOMALY)
        self.assertEqual(signal.severity, 0.7)

    def test_get_events(self):
        """测试查询事件。"""
        # 创建几个事件
        for i in range(3):
            self.engine.ingest_event(
                title=f"Test Event {i}",
                category=CATEGORY_ECONOMY,
                country_code="US"
            )

        # 查询事件
        events = self.engine.get_events(country_code="US", limit=10)

        self.assertGreaterEqual(len(events), 3, "应该至少有 3 条事件记录")

    def test_get_risk_signals(self):
        """测试查询风险信号。"""
        # 创建几个风险信号
        for i in range(2):
            self.engine.create_risk_signal(
                country_code="JP",
                signal_type=SIGNAL_TYPE_SHOCK,
                description=f"Test signal {i}",
                severity=0.5 + i * 0.1,
                probability=0.6,
                confidence=0.7
            )

        # 查询风险信号
        signals = self.engine.get_risk_signals(country_code="JP", limit=10)

        self.assertGreaterEqual(len(signals), 2, "应该至少有 2 条风险信号")

    def test_event_lifecycle(self):
        """测试事件完整生命周期。"""
        # 1. 摄入事件
        event = self.engine.ingest_event(
            title="GDP Growth Exceeds Expectations",
            category=CATEGORY_ECONOMY,
            country_code="CN",
            provenance="NBS China"
        )
        self.assertIsNotNone(event)
        self.assertEqual(event.status, STATUS_DETECTED)

        # 2. 分类
        classified = self.engine.classify_event(event)
        self.assertIsNotNone(classified)

        # 3. 影响分析
        impacts = self.engine.analyze_impact(classified)
        self.assertGreaterEqual(len(impacts), 1)

        # 4. 验证事件状态已更新
        updated_events = self.engine.get_events(
            country_code="CN",
            status=STATUS_ANALYZED
        )
        self.assertGreaterEqual(len(updated_events), 1)

    def test_impact_persistence(self):
        """测试影响持久化。"""
        event = self.engine.ingest_event(
            title="Energy Crisis",
            category=CATEGORY_ENERGY,
            country_code="EU"
        )

        impacts = self.engine.analyze_impact(event)

        # 验证数据库中有关联的影响记录
        count = self.conn.execute(
            "SELECT COUNT(*) FROM gfe_event_impacts WHERE event_id = ?",
            (event.event_id,)
        ).fetchone()[0]

        self.assertGreaterEqual(count, len(impacts), "影响记录应该持久化到数据库")


class TestAPIEndpoints(unittest.TestCase):
    """测试 API 端点结构。"""

    def test_event_frontend_format(self):
        """测试事件前端格式。"""
        event = GFEEvent(
            event_id="test_evt",
            source_id=None,
            title="Test Event",
            summary="Test summary",
            category=CATEGORY_ECONOMY,
            country_code="US",
            region="NA",
            severity=0.7,
            confidence=0.8
        )

        frontend = event.to_frontend()

        self.assertIn("event_id", frontend)
        self.assertIn("title", frontend)
        self.assertIn("category", frontend)
        self.assertIn("severity", frontend)
        self.assertEqual(frontend["country_code"], "US")

    def test_risk_signal_frontend_format(self):
        """测试风险信号前端格式。"""
        signal = RiskSignal(
            signal_id="test_sig",
            country_code="CN",
            signal_type=SIGNAL_TYPE_ANOMALY,
            description="Test anomaly",
            severity=0.8,
            probability=0.6,
            confidence=0.9
        )

        frontend = signal.to_frontend()

        self.assertIn("signal_id", frontend)
        self.assertIn("country_code", frontend)
        self.assertIn("signal_type", frontend)
        self.assertEqual(frontend["severity"], 0.8)


if __name__ == "__main__":
    unittest.main(verbosity=2)