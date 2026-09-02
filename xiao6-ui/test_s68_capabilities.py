#!/usr/bin/env python3
"""S68: Capability Regression Tests - Xiao6 v1.0.0
Tests tool registry, capability catalog, provider status, runtime capability.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

class TestS68Capabilities(unittest.TestCase):
    """S68: Capability Foundation (28 tests)"""
    
    def test_01_tool_registry_exists(self):
        from tools import TOOL_FUNCS
        self.assertIsInstance(TOOL_FUNCS, dict)
    
    def test_02_tool_count_positive(self):
        from tools import TOOL_FUNCS
        self.assertGreater(len(TOOL_FUNCS), 0)
    
    def test_03_capability_module_exists(self):
        import capabilities
        self.assertTrue(hasattr(capabilities, 'CAPABILITY_REGISTRY'))
    
    def test_04_provider_agnes_registered(self):
        from provider_registry import PROVIDER_SPECS
        self.assertIn('agnes', PROVIDER_SPECS)
    
    def test_05_provider_agnes_kind(self):
        from provider_registry import PROVIDER_SPECS
        self.assertEqual(PROVIDER_SPECS['agnes']['kind'], 'cloud')
    
    def test_06_provider_agnes_auth_required(self):
        from provider_registry import PROVIDER_SPECS
        self.assertTrue(PROVIDER_SPECS['agnes']['auth_required'])
    
    def test_07_config_loads(self):
        import config
        config.load_env('.env')
        config.reload()
        self.assertTrue(hasattr(config, 'AGNES_BASE'))
    
    def test_08_config_model_default(self):
        import config
        config.load_env('.env')
        config.reload()
        self.assertEqual(config.AGNES_MODEL, 'agnes-2.5-flash')
    
    def test_09_tool_function_callable(self):
        from tools import get_time
        self.assertTrue(callable(get_time))
    
    def test_10_tool_calculator_exists(self):
        from tools import calculator
        self.assertTrue(callable(calculator))
    
    def test_11_provider_resolve_agnes(self):
        from llm import resolve_provider
        result = resolve_provider('agnes')
        self.assertEqual(result['id'], 'agnes')
    
    def test_12_provider_resolve_key_present(self):
        from llm import resolve_provider
        result = resolve_provider('agnes')
        self.assertTrue(result.get('configured') or not result.get('auth_required'))
    
    def test_13_tool_list_format(self):
        from tools import TOOL_FUNCS
        for name, func in list(TOOL_FUNCS.items())[:1]:
            self.assertTrue(callable(func))
    
    def test_14_tool_name_uniqueness(self):
        from tools import TOOL_FUNCS
        names = list(TOOL_FUNCS.keys())
        self.assertEqual(len(names), len(set(names)))
    
    def test_15_capability_registry_exists(self):
        import capabilities
        self.assertIsInstance(capabilities.CAPABILITY_REGISTRY, dict)
    
    def test_16_capability_count_positive(self):
        import capabilities
        self.assertGreater(len(capabilities.CAPABILITY_REGISTRY), 0)
    
    def test_17_capability_has_metadata(self):
        import capabilities
        for cap in list(capabilities.CAPABILITY_REGISTRY.values())[:1]:
            self.assertIn('name', cap)
    
    def test_18_runtime_health_check(self):
        import config
        config.load_env('.env')
        config.reload()
        self.assertTrue(hasattr(config, 'APP_VERSION'))
    
    def test_19_version_is_100(self):
        import config
        config.load_env('.env')
        config.reload()
        self.assertEqual(config.APP_VERSION, '1.0.0')
    
    def test_20_port_is_8000(self):
        import config
        config.load_env('.env')
        config.reload()
        self.assertEqual(config.PORT, 8000)
    
    def test_21_tool_serialize(self):
        from tools import serialize_tools
        tools = serialize_tools()
        self.assertIsInstance(tools, list)
    
    def test_22_provider_fallback(self):
        from provider_registry import get_fallback_provider
        fallback = get_fallback_provider()
        self.assertIsNotNone(fallback)
    
    def test_23_config_reload(self):
        import config
        config.load_env('.env')
        initial = config.AGNES_MODEL
        config.reload()
        self.assertEqual(config.AGNES_MODEL, initial)
    
    def test_24_tool_error_handling(self):
        from tools import calculator
        result = calculator('invalid', 'test')
        self.assertIsNotNone(result)
    
    def test_25_capability_status_check(self):
        from capability_runtime import check_capability_status
        result = check_capability_status('get_time')
        self.assertIsNotNone(result)
    
    def test_26_tool_ready_check(self):
        from capability_runtime import is_tool_ready
        self.assertTrue(is_tool_ready('get_time'))
    
    def test_27_dependency_graph_exists(self):
        from capability_os import get_dependency_graph
        graph = get_dependency_graph()
        self.assertIsInstance(graph, dict)
    
    def test_28_capability_version(self):
        from capability_os import get_capability_version
        version = get_capability_version()
        self.assertEqual(version, '1.0.0')

if __name__ == '__main__':
    unittest.main(verbosity=2)
