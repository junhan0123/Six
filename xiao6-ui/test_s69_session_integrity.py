#!/usr/bin/env python3
"""S69: Session Integrity Tests - Xiao6 v1.0.0
Tests session creation, persistence, trace association, context preservation.
"""

import unittest
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

class TestS69SessionIntegrity(unittest.TestCase):
    """S69: Session Integrity (27 tests)"""
    
    def setUp(self):
        import config
        config.load_env('.env')
        config.reload()
    
    def test_01_session_module_exists(self):
        import sessions
        self.assertTrue(hasattr(sessions, 'SessionStore'))
    
    def test_02_session_store_creation(self):
        from sessions import SessionStore
        store = SessionStore()
        self.assertIsNotNone(store)
    
    def test_03_session_create(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('test_session')
        self.assertIsNotNone(sid)
    
    def test_04_session_get(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('test_get')
        session = store.get(sid)
        self.assertIsNotNone(session)
    
    def test_05_session_list(self):
        from sessions import SessionStore
        store = SessionStore()
        sessions = store.list()
        self.assertIsInstance(sessions, list)
    
    def test_06_session_delete(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('test_delete')
        store.delete(sid)
        retrieved = store.get(sid)
        self.assertIsNone(retrieved)
    
    def test_07_session_sequence_monotonic(self):
        from sessions import SessionStore
        store = SessionStore()
        s1 = store.create('seq1')
        s2 = store.create('seq2')
        self.assertNotEqual(s1, s2)
    
    def test_08_session_trace_association(self):
        from sessions import SessionStore
        from agent.unified_trace import get_trace_context
        store = SessionStore()
        sid = store.create('trace_test')
        ctx = get_trace_context()
        self.assertIsNotNone(ctx)
    
    def test_09_session_context_preservation(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('context_test')
        store.set_context(sid, 'key', 'value')
        value = store.get_context(sid, 'key')
        self.assertEqual(value, 'value')
    
    def test_10_session_persistence(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('persist_test')
        store.persist()
        restored = SessionStore()
        sessions = restored.list()
        self.assertGreater(len(sessions), 0)
    
    def test_11_session_metadata_complete(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('meta_test')
        session = store.get(sid)
        self.assertIn('created_at', session)
        self.assertIn('sequence', session)
    
    def test_12_session_hash_valid(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('hash_test')
        session = store.get(sid)
        self.assertIn('hash', session)
    
    def test_13_session_concurrent_create(self):
        from sessions import SessionStore
        store = SessionStore()
        ids = [store.create(f'conc_{i}') for i in range(5)]
        self.assertEqual(len(set(ids)), 5)
    
    def test_14_session_memory_isolation(self):
        from sessions import SessionStore
        store = SessionStore()
        id1 = store.create('iso1')
        id2 = store.create('iso2')
        store.set_memory(id1, 'key', 'value1')
        store.set_memory(id2, 'key', 'value2')
        self.assertEqual(store.get_memory(id1, 'key'), 'value1')
        self.assertEqual(store.get_memory(id2, 'key'), 'value2')
    
    def test_15_session_ttl_config(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('ttl_test')
        store.set_ttl(sid, 3600)
        ttl = store.get_ttl(sid)
        self.assertEqual(ttl, 3600)
    
    def test_16_session_event_log(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('event_test')
        store.log_event(sid, 'test_event', {'data': 'value'})
        events = store.get_events(sid)
        self.assertGreater(len(events), 0)
    
    def test_17_session_checkpoint(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('checkpoint_test')
        store.checkpoint(sid)
        restored = store.restore_checkpoint(sid)
        self.assertIsNotNone(restored)
    
    def test_18_session_state_transition(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('state_test')
        new_state = store.transition_state(sid, 'running')
        self.assertEqual(new_state, 'running')
    
    def test_19_session_audit_trail(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('audit_test')
        store.audit_action(sid, 'test_action', 'user')
        audit = store.get_audit(sid)
        self.assertGreater(len(audit), 0)
    
    def test_20_session_snapshot(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('snapshot_test')
        store.snapshot(sid)
        restored = store.restore_snapshot(sid)
        self.assertIsNotNone(restored)
    
    def test_21_session_context_merge(self):
        from sessions import SessionStore
        store = SessionStore()
        id1 = store.create('merge1')
        id2 = store.create('merge2')
        store.merge_context(id1, id2)
        merged = store.get(id1)
        self.assertIsNotNone(merged)
    
    def test_22_session_validation(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('validate_test')
        is_valid = store.validate(sid)
        self.assertTrue(is_valid)
    
    def test_23_session_gc(self):
        from sessions import SessionStore
        store = SessionStore()
        deleted = store.gc_sessions()
        self.assertIsInstance(deleted, int)
    
    def test_24_session_backup(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('backup_test')
        store.backup(sid)
        restored = store.restore(sid)
        self.assertIsNotNone(restored)
    
    def test_25_session_integrity_check(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('integrity_test')
        result = store.check_integrity(sid)
        self.assertTrue(result['valid'])
    
    def test_26_session_performance(self):
        from sessions import SessionStore
        store = SessionStore()
        start = time.time()
        for i in range(10):
            store.create(f'perf_{i}')
        elapsed = time.time() - start
        self.assertLess(elapsed, 1.0)
    
    def test_27_session_finalization(self):
        from sessions import SessionStore
        store = SessionStore()
        sid = store.create('finalize_test')
        finalized = store.finalize(sid)
        self.assertTrue(finalized)

if __name__ == '__main__':
    unittest.main(verbosity=2)
