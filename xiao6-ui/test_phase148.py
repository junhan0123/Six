#!/usr/bin/env python3
"""PHASE 148 — GFE Early Warning Foundation Tests

测试预警引擎基础功能：
- 数据库表创建
- 规则创建
- 风险评估
- 预警生成
- 状态更新
- 数据持久化
- EventBus集成
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from gfe_warning import (
    EarlyWarningEngine,
    WarningRule,
    WarningAlert,
    get_early_warning_engine,
    STATUS_ACTIVE,
    STATUS_ACKNOWLEDGED,
    STATUS_RESOLVED,
)
from db import db_conn


class TestPhase148Database(unittest.TestCase):
    """测试数据库结构。"""

    def setUp(self):
        # 初始化数据库（自动运行所有迁移）
        db_conn().close()

    def test_tables_exist(self):
        """测试表存在。"""
        conn = db_conn()
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'gfe_warning%'"
        ).fetchall()]
        self.assertIn("gfe_warning_rules", tables)
        self.assertIn("gfe_warning_alerts", tables)
        self.assertIn("gfe_warning_history", tables)

    def test_rules_schema(self):
        """测试规则表结构。"""
        conn = db_conn()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_warning_rules)").fetchall()}
        expected = {"rule_id", "name", "category", "conditions", "severity", "confidence", "enabled", "created_at"}
        self.assertEqual(cols, expected)

    def test_alerts_schema(self):
        """测试预警表结构。"""
        conn = db_conn()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_warning_alerts)").fetchall()}
        expected = {"alert_id", "country_code", "title", "description", "severity", "probability", "confidence", "trigger_refs", "status", "created_at"}
        self.assertEqual(cols, expected)

    def test_history_schema(self):
        """测试历史表结构。"""
        conn = db_conn()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(gfe_warning_history)").fetchall()}
        expected = {"history_id", "alert_id", "old_status", "new_status", "reason", "created_at"}
        self.assertEqual(cols, expected)


class TestPhase148Engine(unittest.TestCase):
    """测试预警引擎功能。"""

    def setUp(self):
        # 初始化数据库（自动运行所有迁移）
        db_conn().close()
        self.engine = get_early_warning_engine()
        # 清理测试数据
        conn = db_conn()
        conn.execute("DELETE FROM gfe_warning_history")
        conn.execute("DELETE FROM gfe_warning_alerts")
        conn.execute("DELETE FROM gfe_warning_rules")
        conn.commit()

    def tearDown(self):
        conn = db_conn()
        conn.execute("DELETE FROM gfe_warning_history")
        conn.execute("DELETE FROM gfe_warning_alerts")
        conn.execute("DELETE FROM gfe_warning_rules")
        conn.commit()

    def test_create_rule(self):
        """测试创建规则。"""
        rule = self.engine.create_rule(
            name="测试规则",
            category="economy",
            conditions={"inflation_rate": "> 5%"},
            severity=0.8,
            confidence=0.7
        )
        self.assertIsNotNone(rule)
        self.assertEqual(rule.name, "测试规则")
        self.assertEqual(rule.category, "economy")
        self.assertAlmostEqual(rule.severity, 0.8)

    def test_get_rules(self):
        """测试查询规则。"""
        self.engine.create_rule("规则1", "economy", {}, 0.5, 0.5)
        self.engine.create_rule("规则2", "finance", {}, 0.6, 0.6)
        rules = self.engine.get_rules()
        self.assertEqual(len(rules), 2)

    def test_get_rules_by_category(self):
        """测试按类别查询规则。"""
        self.engine.create_rule("经济规则", "economy", {}, 0.5, 0.5)
        self.engine.create_rule("金融规则", "finance", {}, 0.6, 0.6)
        econ_rules = self.engine.get_rules(category="economy")
        self.assertEqual(len(econ_rules), 1)
        self.assertEqual(econ_rules[0].category, "economy")

    def test_evaluate_risk(self):
        """测试风险评估。"""
        result = self.engine.evaluate_risk("CN")
        self.assertIn("country_code", result)
        self.assertEqual(result["country_code"], "CN")
        self.assertIn("risk_score", result)
        self.assertIn("severity", result)
        self.assertIn("risk_factors", result)

    def test_generate_alert(self):
        """测试生成预警。"""
        alert = self.engine.generate_alert(
            country_code="CN",
            title="高通胀预警",
            description="CPI超过5%",
            severity=0.8,
            probability=0.7,
            confidence=0.6,
            trigger_refs=["event_123", "forecast_456"]
        )
        self.assertIsNotNone(alert)
        self.assertEqual(alert.country_code, "CN")
        self.assertEqual(alert.status, STATUS_ACTIVE)
        self.assertEqual(alert.severity, 0.8)

    def test_get_alerts(self):
        """测试查询预警。"""
        self.engine.generate_alert("CN", "测试预警1", "描述1", 0.8, 0.7, 0.6, [])
        self.engine.generate_alert("US", "测试预警2", "描述2", 0.6, 0.5, 0.4, [])
        alerts = self.engine.get_alerts()
        self.assertEqual(len(alerts), 2)

    def test_get_alerts_by_country(self):
        """测试按国家查询预警。"""
        self.engine.generate_alert("CN", "中国预警", "描述", 0.8, 0.7, 0.6, [])
        self.engine.generate_alert("US", "美国预警", "描述", 0.6, 0.5, 0.4, [])
        cn_alerts = self.engine.get_alerts(country_code="CN")
        self.assertEqual(len(cn_alerts), 1)
        self.assertEqual(cn_alerts[0].country_code, "CN")

    def test_update_alert_status(self):
        """测试更新预警状态。"""
        alert = self.engine.generate_alert("CN", "测试", "描述", 0.8, 0.7, 0.6, [])
        self.assertTrue(self.engine.update_alert_status(alert.alert_id, STATUS_ACKNOWLEDGED, "已确认"))

        # 验证状态已更新
        alerts = self.engine.get_alerts()
        self.assertEqual(alerts[0].status, STATUS_ACKNOWLEDGED)

    def test_alert_history(self):
        """测试预警历史。"""
        alert = self.engine.generate_alert("CN", "测试", "描述", 0.8, 0.7, 0.6, [])
        self.engine.update_alert_status(alert.alert_id, STATUS_ACKNOWLEDGED, "测试原因")

        conn = db_conn()
        hist = conn.execute("SELECT * FROM gfe_warning_history").fetchall()
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0][2], STATUS_ACTIVE)  # old_status
        self.assertEqual(hist[0][3], STATUS_ACKNOWLEDGED)  # new_status

    def test_to_frontend_format(self):
        """测试前端格式转换。"""
        rule = self.engine.create_rule("测试", "economy", {"key": "value"}, 0.8, 0.7)
        from gfe_warning import rule_to_frontend
        frontend = rule_to_frontend(rule)
        self.assertEqual(frontend["name"], "测试")
        self.assertEqual(frontend["category"], "economy")
        self.assertEqual(frontend["conditions"], {"key": "value"})

        alert = self.engine.generate_alert("CN", "测试预警", "描述", 0.8, 0.7, 0.6, ["ref1"])
        from gfe_warning import alert_to_frontend
        frontend = alert_to_frontend(alert)
        self.assertEqual(frontend["title"], "测试预警")
        self.assertEqual(frontend["trigger_refs"], ["ref1"])
        self.assertEqual(frontend["status"], STATUS_ACTIVE)

    def test_persistence(self):
        """测试数据持久化。"""
        rule = self.engine.create_rule("持久化测试", "test", {}, 0.5, 0.5)
        alert = self.engine.generate_alert("CN", "持久化预警", "描述", 0.6, 0.5, 0.4, [])

        # 重新获取引擎（模拟重启）
        conn = db_conn()
        rule_count = conn.execute("SELECT COUNT(*) FROM gfe_warning_rules").fetchone()[0]
        alert_count = conn.execute("SELECT COUNT(*) FROM gfe_warning_alerts").fetchone()[0]
        self.assertGreater(rule_count, 0)
        self.assertGreater(alert_count, 0)

    def test_eventbus_topics_registered(self):
        """测试EventBus主题已注册。"""
        from eventbus import SYSTEM_EVENT_NAMES
        self.assertIn("gfe_warning_created", SYSTEM_EVENT_NAMES)
        self.assertIn("gfe_warning_updated", SYSTEM_EVENT_NAMES)


class TestPhase148API(unittest.TestCase):
    """测试API端点。"""

    def test_api_endpoints_defined(self):
        """测试API端点定义。"""
        # 通过检查server.py源码确认端点存在
        with open(os.path.join(os.path.dirname(__file__), "server.py"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("/api/gfe/warnings", content)


class TestPhase148SeedData(unittest.TestCase):
    """测试种子数据。"""

    def setUp(self):
        # 初始化数据库（自动运行所有迁移）
        db_conn().close()

    def test_seed_data(self):
        """测试种子数据加载。"""
        from gfe_warning import get_early_warning_engine
        engine = get_early_warning_engine()
        # 确保种子数据已加载
        engine.seed_data()
        rules = engine.get_rules()
        self.assertGreater(len(rules), 0)


if __name__ == "__main__":
    unittest.main()
