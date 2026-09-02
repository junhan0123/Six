#!/usr/bin/env python3
"""Unified Regression Runner for Xiao6 v1.0.0
Supports: S68, S69, S70, S71, S77, S78
"""

import sys
import os
import unittest
from datetime import datetime

# Add xiao6-ui to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'xiao6-ui'))

def run_phase(phase_name, test_file):
    """Run a specific test phase"""
    if not os.path.exists(test_file):
        return {'phase': phase_name, 'expected': 0, 'actual': 0, 'status': 'MISSING'}
    
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.dirname(test_file), os.path.basename(test_file))
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total - failures - errors
    
    # Known limitations
    known_failures = {
        'S71': 1,  # S71-04: Memory injection blocked for VERIFIED state (design)
    }
    
    expected_known = known_failures.get(phase_name, 0)
    actual_total = passed + failures + errors
    
    status = 'PASS' if failures == 0 and errors == 0 else 'FAIL'
    
    return {
        'phase': phase_name,
        'expected': total,
        'actual': passed,
        'failures': failures,
        'errors': errors,
        'known_limitations': expected_known,
        'status': status,
        'file': test_file
    }

def main():
    print("=" * 60)
    print("Xiao6 v1.0.0 Regression Test Suite")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    phases = [
        ('S68', 'test_s68_capabilities.py', 28),
        ('S69', 'test_s69_session_integrity.py', 27),
        ('S70', 'test_s70_shared_context.py', 32),
        ('S71', 'test_s71_prompt_architecture.py', 41),
        ('S77', 'test_s77_llm_provider.py', 5),  # If exists
        ('S78', 'test_s78_auth_recovery.py', 5),  # If exists
    ]
    
    results = []
    for phase_name, test_file, expected in phases:
        test_path = os.path.join(os.path.dirname(__file__), 'xiao6-ui', test_file)
        result = run_phase(phase_name, test_path)
        result['expected'] = expected
        results.append(result)
        
        print(f"\n{phase_name}: {result['actual']}/{result['expected']} {result['status']}")
        if result['failures'] > 0:
            print(f"  Failures: {result['failures']}")
        if result['errors'] > 0:
            print(f"  Errors: {result['errors']}")
    
    print("\n" + "=" * 60)
    print("REGRESSION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for r in results:
        if r['status'] == 'FAIL':
            all_passed = False
        print(f"{r['phase']}: {r['actual']}/{r['expected']} {r['status']}")
    
    print("=" * 60)
    if all_passed:
        print("OVERALL: ALL PASS ✅")
    else:
        print("OVERALL: SOME FAILURES ❌")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
