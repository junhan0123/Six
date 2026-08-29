#!/usr/bin/env python3
"""S81 Real Chat E2E Test Script"""

import json
import subprocess
import sys
import time
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    """Test /api/health"""
    try:
        resp = urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=5)
        data = json.loads(resp.read())
        print(f"✅ /api/health: {data.get('status', 'unknown')}")
        return True
    except Exception as e:
        print(f"❌ /api/health failed: {e}")
        return False

def test_chat():
    """Test real chat with new key"""
    payload = json.dumps({
        "messages": [
            {"role": "user", "content": "你好，请介绍一下你自己。"}
        ]
    }).encode('utf-8')
    
    req = urllib.request.Request(
        f"{BASE_URL}/api/chat",
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        status = resp.status
        data = json.loads(resp.read())
        
        print(f"\n✅ Chat Response: HTTP {status}")
        print(f"Response: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # Check for session/trace
        session_id = data.get('session_id')
        trace_id = data.get('trace_id')
        
        print(f"\n📊 Session ID: {session_id or 'N/A'}")
        print(f"📊 Trace ID: {trace_id or 'N/A'}")
        
        return status == 200 and 'response' in data
    except urllib.error.HTTPError as e:
        print(f"❌ Chat HTTP {e.code}: {e.reason}")
        body = e.read().decode('utf-8', errors='replace')
        print(f"Body: {body[:500]}")
        return False
    except Exception as e:
        print(f"❌ Chat ERROR: {type(e).__name__}: {str(e)[:200]}")
        return False

def test_tool_dispatch():
    """Check tool dispatch signature issue"""
    try:
        # Try to list tools
        resp = urllib.request.urlopen(f"{BASE_URL}/api/tools", timeout=5)
        data = json.loads(resp.read())
        print(f"\n✅ Tools endpoint: {len(data.get('tools', []))} tools")
        return True
    except urllib.error.HTTPError as e:
        print(f"\n⚠️ Tools endpoint HTTP {e.code}: {e.reason}")
        return False
    except Exception as e:
        print(f"\n⚠️ Tools check: {type(e).__name__}")
        return False

def main():
    print("=" * 60)
    print("S81 Real Chat E2E Validation")
    print("=" * 60)
    
    # Wait for server
    print("\n⏳ Waiting for server...")
    for i in range(10):
        try:
            urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=2)
            print(f"✅ Server ready after {i+1}s")
            break
        except:
            time.sleep(1)
    else:
        print("❌ Server not ready")
        return 1
    
    # Run tests
    results = []
    
    print("\n--- Test 1: Health ---")
    results.append(("health", test_health()))
    
    print("\n--- Test 2: Real Chat ---")
    results.append(("chat", test_chat()))
    
    print("\n--- Test 3: Tool Dispatch ---")
    results.append(("tools", test_tool_dispatch()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:12s}: {status}")
    
    all_passed = all(r[1] for r in results)
    print(f"\nOverall: {'✅ REAL_CHAT_COMPLETE' if all_passed else '⚠️ PARTIAL'}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
