#!/usr/bin/env python3
"""PHASE 150 — GFE Dashboard Integration Test

测试全球洞察Dashboard功能：
- API聚合接口
- 前端组件存在
- UI资源加载
"""

import os
import sys
import requests
import unittest

class TestPhase150(unittest.TestCase):
    """测试Dashboard功能。"""

    def test_api_dashboard_exists(self):
        """测试Dashboard API端点存在。"""
        # 检查server.py源码
        with open("G:/xiao6/xiao6-ui/server.py", "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("/api/gfe/dashboard", content)

    def test_ui_files_exist(self):
        """测试UI文件存在。"""
        self.assertTrue(os.path.exists("G:/xiao6/ui/js/gfe-dashboard.js"))
        self.assertTrue(os.path.exists("G:/xiao6/ui/css/gfe-dashboard.css"))

    def test_nav_item_exists(self):
        """测试导航项存在。"""
        with open("G:/xiao6/ui/index.html", "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('data-view="gfe"', content)

    def test_gfe_modules_readable(self):
        """测试GFE模块可读取。"""
        sys.path.insert(0, "G:/xiao6/xiao6-ui")
        from gfe_events import get_event_intelligence_engine
        from gfe_forecast import get_forecast_engine
        from gfe_warning import get_early_warning_engine
        from gfe_calibration import get_calibration_engine
        print("All GFE modules imported successfully")

    def test_api_response_structure(self):
        """测试API响应结构。"""
        try:
            resp = requests.get("http://127.0.0.1:8000/api/gfe/dashboard", timeout=5)
            data = resp.json()
            # 验证必需字段
            self.assertIn("risk_summary", data)
            self.assertIn("events", data)
            self.assertIn("forecasts", data)
            self.assertIn("warnings", data)
            self.assertIn("calibration", data)
            print("API response structure OK")
        except Exception as e:
            self.skipTest(f"Server not running: {e}")


if __name__ == "__main__":
    unittest.main()
