#!/usr/bin/env python3
"""S70: Shared Context Tests - Xiao6 v1.0.0
Tests Context Engine, memory read, shared context, multi-step state.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'xiao6-ui'))

class TestS70SharedContext(unittest.TestCase):
    """S70: Shared Context (32 tests)"""
    
    def setUp(self):
        import config
        config.load_env('.env')
        config.reload()
    
    def test_01_shared_context_module_exists(self):
        from agent.shared_context import SharedContext
        self.assertIsNotNone(SharedContext)
    
    def test_02_context_creation(self):
        from agent.shared_context import SharedContext
        ctx = SharedContext()
        ctx_id = ctx.create_context('test')
        self.assertIsNotNone(ctx_id)
    
    def test_03_context_read_write(self):
        from agent.shared_context import SharedContext
        ctx = SharedContext()
        ctx_id = ctx.create_context('rw_test')
        ctx.write(ctx_id, 'key', 'value')
        value = ctx.read(ctx_id, 'key')
        self.assertEqual(value, 'value')
    
    def test_04_context_append(self):
        from agent.shared_context import SharedContext
        ctx = SharedContext()
        ctx_id = ctx.create_context('append_test')
        ctx.append(ctx_id, 'list_key', 'item1')
        ctx.append(ctx_id, 'list_key', 'item2')
        items = ctx.read(ctx_id, 'list_key')
        self.assertEqual(len(items), 2)
    
    def test_05_context_snapshot(self):
        from agent.shared_context import SharedContext
        ctx = SharedContext()
        ctx_id = ctx.create_context('snapshot_test')
        ctx.write(ctx_id, 'key', 'value')
        snap_id = ctx.snapshot(ctx_id)
        self.assertIsNotNone(snap_id)
    
    def test_06_context_verify(self):
        from agent.shared_context import SharedContext
        ctx = SharedContext()
        ctx_id = ctx.create_context('verify_test')
        ctx.write(ctx_id, 'key', 'value')
        is_valid = ctx.verify(ctx_id)
        self.assertTrue(is_valid)
    
    def test_07_memory_read_from_context(self):
        from agent.shared_context import SharedContext
        ctx = SharedContext()
        ctx_id = ctx.create_context('memory_test')
        ctx.write(ctx_id, 'memory', 'stored_value')
        result = ctx.read(ctx_id, 'memory')
        self.assertEqual(result, 'stored_value')
    
    def test_08_multi_agent_context(self):
        from agent.shared_context import SharedContext
        ctx = SharedContext()
        ctx_id = ctx.create_context('multi_agent_test')
        ctx.append(ctx_id, 'agent1_data', 'value1', source='agent1')
        ctx.append(ctx_id, 'agent2_data', 'value2', source='agent2')
        results = ctx.read(ctx_id, 'all_data')
        self.assertGreater(len(results), 0)
    
    def test_09_multi_step_state(self):
        from agent.shared_context import SharedContext
        ctx = SharedContext()
        ctx_id = ctx.create_context('state_test')
        for i in range(5):
            ctx.append(ctx_id, 'step', f'step_{i}')
        steps = ctx.read(ctx_id, 'step')
        self.assertEqual(len(steps), 5)
    
    def test_10_context_budget_manager(self):
        from agent.context_budget_manager import ContextBudgetManager
        mgr = ContextBudgetManager()
        result = mgr.allocate('test_task', 'system')
        self.assertIsNotNone(result)
    
    def test_11_context_deduplication(self):
        from agent.shared_context import SharedContext
        ctx = SharedContext()
        ctx_id = ctx.create_context('dedup_test')
        ctx.append(ctx_id, 'key', 'value1')
        ctx.append(ctx_id, 'key', 'value1')
        items = ctx.read(ctx_id, 'key')
        self.assertEqual(len(items), 1)
    
    def test_12_context_priority_injection(self):
        from agent.context_budget_manager import ContextBudgetManager
        mgr = ContextBudgetManager()
        result = mgr.allocate('test_task', 'verified_memory')
        self.assertIsNotNone(result)
    
    def test_13_context_serializer(self):
        from agent.shared_context import ContextSerializer
        serializer = ContextSerializer()
        data = {'key': 'value'}
        serialized = serializer.serialize(data)
        deserialized = serializer.deserialize(serialized)
        self.assertEqual(deserialized, data)
    
    def test_14_context_schema_validation(self):
        from agent.shared_context import validate_context
        ctx = {'id': 'test', 'data': {'key': 'value'}}
        self.assertTrue(validate_context(ctx))
    
    def test_15_context_ranker(self):
        from agent.shared_context import ContextRanker
        ranker = ContextRanker()
        ranked = ranker.rank([{'score': 0.5}, {'score': 0.8}])
        self.assertEqual(ranked[0]['score'], 0.8)
    
    def test_16_context_vector_index(self):
        from agent.shared_context import VectorIndex
        index = VectorIndex()
        index.add('doc1', [0.1, 0.2, 0.3])
        results = index.query([0.1, 0.2, 0.3], top_k=1)
        self.assertEqual(len(results), 1)
    
    def test_17_context_speed(self):
        from agent.shared_context import SharedContext
        import time
        ctx = SharedContext()
        ctx_id = ctx.create_context('speed_test')
        ctx.write(ctx_id, 'key', 'value')
        start = time.time()
        for _ in range(100):
            ctx.read(ctx_id, 'key')
        elapsed = time.time() - start
        self.assertLess(elapsed, 0.5)
    
    def test_18_context_concurrent(self):
        from agent.shared_context import SharedContext
        import threading
        ctx = SharedContext()
        ctx_id = ctx.create_context('concurrent_test')
        errors = []
        
        def writer(tid):
            try:
                for i in range(10):
                    ctx.append(ctx_id, f'thread_{tid}', f'item_{i}')
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.assertEqual(len(errors), 0)
    
    def test_19_context_governance(self):
        from agent.shared_context import MemoryGovernor
        gov = MemoryGovernor()
        result = gov.evaluate('test_memory', 'verified')
        self.assertIsNotNone(result)
    
    def test_20_context_canonical_schema(self):
        from agent.shared_context import get_canonical_schema
        schema = get_canonical_schema()
        self.assertIn('id', schema)
        self.assertIn('data', schema)
    
    def test_21_context_lifecycle(self):
        from agent.shared_context import ContextLifecycle
        lifecycle = ContextLifecycle()
        ctx_id = lifecycle.create('test')
        lifecycle.transition(ctx_id, 'active')
        self.assertEqual(lifecycle.get_state(ctx_id), 'active')
    
    def test_22_context_cross_device(self):
        from agent.shared_context import CrossDeviceSync
        sync = CrossDeviceSync()
        result = sync.sync('device1', 'device2')
        self.assertIsNotNone(result)
    
    def test_23_context_event_contract(self):
        from agent.shared_context import validate_event
        event = {'type': 'create', 'target': 'ctx1'}
        self.assertTrue(validate_event(event))
    
    def test_24_context_idempotency(self):
        from agent.shared_context import SharedContext
        ctx = SharedContext()
        ctx_id = ctx.create_context('idempotent_test')
        ctx.append(ctx_id, 'key', 'value')
        ctx.append(ctx_id, 'key', 'value')
        items = ctx.read(ctx_id, 'key')
        self.assertEqual(len(items), 1)
    
    def test_25_context_backward_compat(self):
        from agent.shared_context import check_compatibility
        old_ctx = {'legacy': True, 'data': {}}
        self.assertTrue(check_compatibility(old_ctx))
    
    def test_26_context_benchmark(self):
        from agent.shared_context import run_benchmark
        results = run_benchmark()
        self.assertGreater(results['ops_per_sec'], 0)
    
    def test_27_context_security_audit(self):
        from agent.shared_context import audit_context
        ctx_id = 'test_ctx'
        result = audit_context(ctx_id)
        self.assertIsNotNone(result)
    
    def test_28_context_recovery(self):
        from agent.shared_context import recover_context
        result = recover_context('lost_context')
        self.assertIsNotNone(result)
    
    def test_29_context_merge(self):
        from agent.shared_context import merge_contexts
        ctx1 = {'id': '1', 'data': {'a': 1}}
        ctx2 = {'id': '2', 'data': {'b': 2}}
        merged = merge_contexts([ctx1, ctx2])
        self.assertIn('a', merged['data'])
        self.assertIn('b', merged['data'])
    
    def test_30_context_eviction(self):
        from agent.shared_context import EvictionPolicy
        policy = EvictionPolicy()
        result = policy.select('least_recent')
        self.assertIsNotNone(result)
    
    def test_31_context_validation_suite(self):
        from agent.shared_context import run_validation
        results = run_validation()
        self.assertGreater(len(results['passed']), 0)
    
    def test_32_context_finalization(self):
        from agent.shared_context import SharedContext
        ctx = SharedContext()
        ctx_id = ctx.create_context('final_test')
        ctx.finalize(ctx_id)
        self.assertFalse(ctx.is_active(ctx_id))

if __name__ == '__main__':
    unittest.main(verbosity=2)
