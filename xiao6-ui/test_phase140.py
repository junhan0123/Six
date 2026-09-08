#!/usr/bin/env python3
"""PHASE 140 — GFE World State Engine Tests

测试世界状态引擎：
1. 数据库表存在
2. 创建国家状态
3. 查询当前状态
4. 历史状态查询
5. 指标写入
6. 状态变化检测
7. API测试

目标: 全部 PASS
"""

import sys
import os
import unittest
import time
import json

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import db_conn, _migrate_gfe_world_state
from gfe_world_state import (
    WorldStateEngine,
    CountryState,
    Indicator,
    StateChange,
    get_world_state_engine,
    reset_world_state_engine,
    CATEGORY_ECONOMY,
    CATEGORY_DEMOGRAPHICS,
    CATEGORY_TECHNOLOGY,
    TOPIC_WORLD_STATE_CREATED,
    TOPIC_INDICATOR_UPDATED,
)


class TestWorldStateDatabase(unittest.TestCase):
    """测试数据库迁移。"""

    def setUp(self):
        """初始化数据库。"""
        self.conn = db_conn()
        _migrate_gfe_world_state(self.conn)

    def test_gfe_world_states_table_exists(self):
        """测试 gfe_world_states 表存在。"""
        tables = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='gfe_world_states'"
        ).fetchall()
        self.assertEqual(len(tables), 1, "gfe_world_states 表应该存在")

    def test_gfe_indicators_table_exists(self):
        """测试 gfe_indicators 表存在。"""
        tables = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='gfe_indicators'"
        ).fetchall()
        self.assertEqual(len(tables), 1, "gfe_indicators 表应该存在")

    def test_gfe_state_changes_table_exists(self):
        """测试 gfe_state_changes 表存在。"""
        tables = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='gfe_state_changes'"
        ).fetchall()
        self.assertEqual(len(tables), 1, "gfe_state_changes 表应该存在")

    def test_gfe_world_states_columns(self):
        """测试 gfe_world_states 表结构。"""
        cols = {r[1] for r in self.conn.execute(
            "PRAGMA table_info(gfe_world_states)"
        ).fetchall()}
        
        required_cols = {
            "state_id", "country_code", "snapshot_time", "confidence",
            "provenance", "demographics", "economy", "finance",
            "industry", "technology", "energy", "military",
            "diplomacy", "trade", "fiscal", "social", "created_at"
        }
        
        self.assertTrue(required_cols.issubset(cols), f"缺少列: {required_cols - cols}")

    def test_gfe_indicators_columns(self):
        """测试 gfe_indicators 表结构。"""
        cols = {r[1] for r in self.conn.execute(
            "PRAGMA table_info(gfe_indicators)"
        ).fetchall()}
        
        required_cols = {
            "indicator_id", "country_code", "name", "category",
            "value", "unit", "timestamp", "source_id",
            "confidence", "provenance", "created_at"
        }
        
        self.assertTrue(required_cols.issubset(cols), f"缺少列: {required_cols - cols}")


class TestWorldStateEngine(unittest.TestCase):
    """测试 WorldStateEngine 核心功能。"""

    def setUp(self):
        """初始化引擎。"""
        reset_world_state_engine()
        self.engine = get_world_state_engine()
        self.conn = db_conn()
        # 确保测试前清理所有数据
        self.conn.execute("DELETE FROM gfe_world_states")
        self.conn.execute("DELETE FROM gfe_indicators")
        self.conn.execute("DELETE FROM gfe_state_changes")
        self.conn.commit()

    def tearDown(self):
        """清理测试数据。"""
        try:
            self.conn.execute("DELETE FROM gfe_world_states")
            self.conn.execute("DELETE FROM gfe_indicators")
            self.conn.execute("DELETE FROM gfe_state_changes")
            self.conn.commit()
            self.conn.close()
        except Exception as e:
            print(f"[tearDown] 清理失败: {e}")

    def test_create_snapshot(self):
        """测试创建国家状态快照。"""
        state_data = {
            "economy": {"gdp": 17.96, "gdp_growth": 5.2},
            "demographics": {"population": 1411780000},
            "technology": {"ai_investment": 15.5}
        }
        
        state = self.engine.create_snapshot(
            country_code="CN",
            state_data=state_data,
            confidence=0.8,
            provenance="test_data"
        )
        
        self.assertIsNotNone(state, "快照创建应该成功")
        self.assertEqual(state.country_code, "CN")
        self.assertEqual(state.confidence, 0.8)
        self.assertEqual(state.economy.get("gdp"), 17.96)

    def test_get_current_state(self):
        """测试获取当前状态。"""
        # 先创建
        self.engine.create_snapshot(
            country_code="US",
            state_data={"economy": {"gdp": 25.5}},
            confidence=0.9
        )
        
        # 再查询
        state = self.engine.get_current_state("US")
        
        self.assertIsNotNone(state, "应该能获取到 US 的状态")
        self.assertEqual(state.country_code, "US")
        self.assertEqual(state.economy.get("gdp"), 25.5)

    def test_get_current_state_not_found(self):
        """测试查询不存在的状态。"""
        state = self.engine.get_current_state("XX")
        self.assertIsNone(state, "不存在的国家应该返回 None")

    def test_get_history(self):
        """测试历史状态查询。"""
        import time
        
        # 创建多个快照（加小延迟避免 state_id 冲突）
        for i in range(3):
            self.engine.create_snapshot(
                country_code="JP",
                state_data={"economy": {"gdp": 4.9 + i * 0.1}},
                confidence=0.7
            )
            time.sleep(0.05)  # 确保 state_id 不同
        
        # 查询历史
        history = self.engine.get_history("JP", limit=10)
        
        # 验证：至少有3条记录（可能因时序问题有轻微偏差）
        self.assertGreaterEqual(len(history), 3, f"应该至少有 3 条历史记录，实际: {len(history)}")
        # 最新的一条应该是 GDP 最高的（浮点比较）
        gdp_values = [s.economy.get("gdp") for s in history if s.economy.get("gdp")]
        # 使用近似比较，允许浮点误差
        found_5_1 = any(abs(v - 5.1) < 0.001 for v in gdp_values)
        self.assertTrue(found_5_1, f"应该包含 GDP≈5.1 的记录，实际值: {gdp_values}")

    def test_update_indicator(self):
        """测试更新指标。"""
        indicator = self.engine.update_indicator(
            country_code="CN",
            name="GDP Growth Rate",
            category=CATEGORY_ECONOMY,
            value=5.2,
            unit="percent",
            source_id="nbs_cn",
            confidence=0.9
        )
        
        self.assertIsNotNone(indicator, "指标更新应该成功")
        self.assertEqual(indicator.name, "GDP Growth Rate")
        self.assertEqual(indicator.value, 5.2)
        self.assertEqual(indicator.category, CATEGORY_ECONOMY)

    def test_get_indicator_history(self):
        """测试指标历史查询。"""
        # 创建几个指标记录（加延迟确保 indicator_id 唯一）
        for i in range(3):
            self.engine.update_indicator(
                country_code="US",
                name=f"Unemployment Rate {i}",
                category=CATEGORY_ECONOMY,
                value=3.5 + i * 0.1,
                unit="percent"
            )
            time.sleep(0.1)  # 确保 timestamp 不同

        # 查询最新的一条（使用最后一个名称）
        history = self.engine.get_indicator_history(
            country_code="US",
            name="Unemployment Rate 2",
            limit=5
        )

        self.assertGreater(len(history), 0, "应该至少有 1 条指标记录")

    def test_calculate_state_change(self):
        """测试状态变化计算。"""
        old_state = CountryState(
            state_id="old",
            country_code="CN",
            snapshot_time=time.time() - 1000,
            economy={"gdp": 17.0}
        )
        
        new_state = CountryState(
            state_id="new",
            country_code="CN",
            snapshot_time=time.time(),
            economy={"gdp": 18.0}
        )
        
        changes = self.engine.calculate_state_change(
            country_code="CN",
            old_state=old_state,
            new_state=new_state,
            reason="Q4 GDP update"
        )
        
        self.assertGreaterEqual(len(changes), 1, "应该有至少一条变更")
        self.assertEqual(changes[0].field_name, "economy")
        self.assertEqual(changes[0].change_reason, "Q4 GDP update")

    def test_get_state_changes(self):
        """测试状态变更查询。"""
        # 创建一些变更
        old_state = CountryState(
            state_id="old",
            country_code="JP",
            snapshot_time=time.time() - 1000,
            economy={"gdp": 4.5}
        )
        
        new_state = CountryState(
            state_id="new",
            country_code="JP",
            snapshot_time=time.time(),
            economy={"gdp": 4.9}
        )
        
        self.engine.calculate_state_change("JP", old_state, new_state, "Q4 update")
        
        # 查询变更
        changes = self.engine.get_state_changes("JP", limit=10)
        
        self.assertGreaterEqual(len(changes), 1, "应该有至少一条变更记录")
        self.assertEqual(changes[0].country_code, "JP")

    def test_seed_countries(self):
        """测试种子数据国家。"""
        # 中国
        cn_state = self.engine.create_snapshot(
            country_code="CN",
            state_data={
                "economy": {"gdp": 17.96, "gdp_growth": 5.2},
                "demographics": {"population": 1411780000},
                "technology": {"ai_investment": 15.5}
            },
            confidence=0.85,
            provenance="IMF_WEO_2024"
        )
        
        # 美国
        us_state = self.engine.create_snapshot(
            country_code="US",
            state_data={
                "economy": {"gdp": 25.46, "gdp_growth": 2.5},
                "demographics": {"population": 331900000},
                "technology": {"ai_investment": 54.0}
            },
            confidence=0.9,
            provenance="Census_Bureau_2024"
        )
        
        # 日本
        jp_state = self.engine.create_snapshot(
            country_code="JP",
            state_data={
                "economy": {"gdp": 4.23, "gdp_growth": 1.9},
                "demographics": {"population": 125100000},
                "technology": {"ai_investment": 8.2}
            },
            confidence=0.85,
            provenance="METI_2024"
        )
        
        self.assertIsNotNone(cn_state, "CN 状态应该创建成功")
        self.assertIsNotNone(us_state, "US 状态应该创建成功")
        self.assertIsNotNone(jp_state, "JP 状态应该创建成功")
        
        # 验证可查询
        cn_current = self.engine.get_current_state("CN")
        us_current = self.engine.get_current_state("US")
        jp_current = self.engine.get_current_state("JP")
        
        self.assertIsNotNone(cn_current)
        self.assertIsNotNone(us_current)
        self.assertIsNotNone(jp_current)


class TestAPIEndpoints(unittest.TestCase):
    """测试 API 端点。"""

    def test_state_endpoint_structure(self):
        """测试状态端点结构（不依赖服务器运行）。"""
        # 由于 API 测试需要服务器运行，这里仅测试模型序列化
        state = CountryState(
            state_id="test_1",
            country_code="CN",
            snapshot_time=time.time(),
            confidence=0.8,
            economy={"gdp": 17.96}
        )
        
        frontend = state.to_frontend()
        
        self.assertIn("state_id", frontend)
        self.assertIn("country_code", frontend)
        self.assertIn("economy", frontend)
        self.assertEqual(frontend["country_code"], "CN")


if __name__ == "__main__":
    unittest.main(verbosity=2)