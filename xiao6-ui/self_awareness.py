#!/usr/bin/env python3
"""Self-Awareness Module — Read-only aggregation layer for Xiao6 runtime state.

This module provides observability into the current system state by reading
from existing, authoritative sources. It does NOT create or maintain its own
state — it aggregates from:
  - db.py (database rows)
  - tools.py (tool registry)
  - capability_os (capability registry)
  - config.py (configuration)
  - server handlers (health/ready endpoints)

This is a READ-ONLY observation layer, not a second runtime.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict


def _get_db_counts(conn) -> Dict[str, int]:
    """Get row counts from key tables."""
    counts = {}
    for table in ['memories', 'knowledge_docs', 'goals', 'tasks', 'notes',
                   'execution_requests', 'automation_audit']:
        try:
            cnt = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
            counts[table] = cnt
        except Exception:
            counts[table] = 0
    
    # Knowledge docs may be stored in filesystem via KnowledgeRuntime
    try:
        from knowledge import get_runtime
        runtime = get_runtime()
        if runtime and hasattr(runtime, 'stats'):
            counts['knowledge_docs'] = runtime.stats().get('docs', 0)
    except Exception:
        pass
    
    return counts


def _get_capability_status() -> Dict[str, Any]:
    """Aggregate capability status from capability_os."""
    from capability_os import list_capabilities, verification
    caps = list_capabilities()
    total = len(caps)

    # Use verification for accurate status
    try:
        results = verification.verify_all()
        if results:
            status_counts = {'ready': 0, 'partial': 0, 'blocked': 0, 'not_implemented': 0}
            for r in results:
                s = r.get('status', 'unknown')
                if s in status_counts:
                    status_counts[s] += 1
            print(f"[DEBUG-CAP] Marked with CORRECT values: {status_counts}")
            return {
                'total': total,
                'ready': status_counts['ready'],
                'partial': status_counts['partial'],
                'blocked': status_counts['blocked'],
                'not_implemented': status_counts['not_implemented'],
            }
    except Exception as e:
        print(f"[DEBUG-CAP] Verification failed: {e}")

    # Fallback: count by available flag
    status_counts = {'ready': 0, 'partial': 0, 'blocked': 0, 'not_implemented': 0}
    for cap in caps:
        if cap.available:
            status_counts['ready'] += 1
    print(f"[DEBUG-CAP] Fallback values: {status_counts}")
    return {
        'total': total,
        'ready': status_counts['ready'],
        'partial': status_counts['partial'],
        'blocked': status_counts['blocked'],
        'not_implemented': status_counts['not_implemented'],
    }


def _get_tool_status() -> Dict[str, Any]:
    """Get tool registry status."""
    try:
        import tools
        total = len(tools.TOOLS)
        # TOOL_FUNCS is the canonical implementation registry
        implemented = len(getattr(tools, 'TOOL_FUNCS', []))
        return {
            'total': total,
            'implemented': implemented,
        }
    except Exception as e:
        return {'total': 0, 'error': str(e)}


def _get_runtime_status() -> Dict[str, Any]:
    """Get runtime status indicators."""
    import socket
    runtime = {
        'port': 8000,
        'listening': False,
        'gpt_sovits': False,
        'whisper': False,
    }
    
    # Check if we're listening on port 8000
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 8000))
        runtime['listening'] = True
        s.close()
    except Exception:
        pass
    
    # Check GPT-SoVITS
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 9880))
        runtime['gpt_sovits'] = True
        s.close()
    except Exception:
        pass
    
    # Check Whisper
    try:
        import asr
        runtime['whisper'] = asr.whisper_available()
    except Exception:
        pass
    
    return runtime


def _get_perception_status() -> Dict[str, Any]:
    """Get perception capability status."""
    try:
        import perception
        windows = perception.get_all_windows()
        fg = perception.get_foreground_window()
        return {
            'windows_observed': len(windows.get('windows', [])),
            'foreground_ok': fg.get('ok', False),
            'screen_available': hasattr(perception, 'screen_observer'),
        }
    except Exception as e:
        return {'error': str(e)}


def _get_policy_status() -> Dict[str, Any]:
    """Get policy engine status."""
    try:
        import policy_engine as pe
        # Check what's available in policy_engine module
        has_policies = hasattr(pe, 'rules') or hasattr(pe, 'POLICIES')
        rules = []
        if hasattr(pe, 'rules'):
            rules = pe.rules
        elif hasattr(pe, 'POLICIES'):
            rules = pe.POLICIES
        return {
            'initialized': True,
            'rules_count': len(rules) if isinstance(rules, list) else 0,
        }
    except Exception as e:
        return {'error': str(e)}


def get_status() -> Dict[str, Any]:
    """Get comprehensive self-awareness status.
    
    Returns a structured JSON report of current system state.
    All data comes from live, authoritative sources — not cached or mocked.
    """
    import db as db_module
    
    result = {
        'ok': True,
        'timestamp': time.time(),
        'version': '1.0.0',
    }
    
    # Runtime state
    result['runtime'] = _get_runtime_status()
    
    # Database state
    try:
        conn = db_module.db_conn()
        result['db'] = _get_db_counts(conn)
    except Exception as e:
        result['db'] = {'error': str(e)}
    
    # Capability state
    result['capabilities'] = _get_capability_status()
    
    # Tool state
    result['tools'] = _get_tool_status()
    
    # Perception state
    result['perception'] = _get_perception_status()
    
    # Policy state
    result['policy'] = _get_policy_status()
    
    # Known limitations
    limitations = []
    if not result['runtime'].get('gpt_sovits'):
        limitations.append({
            'component': 'TTS',
            'status': 'blocked',
            'reason': 'GPT-SoVITS not deployed (port 9880 closed)',
        })
    if not result['perception'].get('screen_available'):
        limitations.append({
            'component': 'Perception.Screen',
            'status': 'partial',
            'reason': 'screen_observer not implemented',
        })
    result['limitations'] = limitations
    
    return result


if __name__ == '__main__':
    import json
    status = get_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))