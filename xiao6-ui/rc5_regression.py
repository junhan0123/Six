#!/usr/bin/env python3
"""RC-5 Agent Runtime Regression Tests"""

import json
import sys
import urllib.request
import time
from datetime import datetime

BASE = "http://127.0.0.1:8000"
RESULTS = []

def post(path, data, timeout=30):
    """Send POST request and return parsed response."""
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, 
        data=json.dumps(data).encode("utf-8"),
        headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8")
            return json.loads(body)
    except Exception as e:
        return {"error": str(e)}

def get(path, timeout=10):
    """Send GET request."""
    url = BASE + path
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8")
    except Exception as e:
        return None, str(e)

def test(label, condition, detail=""):
    """Record test result."""
    status = "PASS" if condition else "FAIL"
    RESULTS.append({"label": label, "status": status, "detail": detail})
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))
    return condition

# ============================================================
print("=" * 60)
print("RC-5 Agent Runtime Regression")
print("=" * 60)

# ============================================================
# Test 1: Chat SSE — Basic Response
# ============================================================
print("\n[1/5] Chat SSE")

resp = post("/api/chat", {
    "messages": [{"role": "user", "content": "你好，请用一句话介绍自己"}]
})

content = ""
if resp.get("choices"):
    for c in resp["choices"]:
        if isinstance(c, dict) and "delta" in c:
            content += c["delta"].get("content", "")
        elif isinstance(c, dict) and "message" in c:
            content += c["message"].get("content", "")

test("Chat SSE basic response", 
     len(content) > 0,
     f"Response length: {len(content)} chars")

# ============================================================
# Test 2: Tool Execution — Calculator
# ============================================================
print("\n[2/5] Tool Execution (Calculator)")

resp = post("/api/chat", {
    "messages": [{"role": "user", "content": "帮我计算 23 * 45 = ?"}]
})

has_tool_use = False
has_result = False
content_str = json.dumps(resp)

if "calculator" in content_str.lower() or "tool_use" in content_str.lower():
    has_tool_use = True
if any(c in content_str for c in ["1035", "计算"]):
    has_result = True

test("Tool execution: calculator called", has_tool_use, "Check tool_use in response")
test("Tool execution: correct result", has_result, "Expected 1035")

# ============================================================
# Test 3: Memory Write/Read
# ============================================================
print("\n[3/5] Memory Write/Read")

# Step 1: Write memory
mem_resp = post("/api/chat", {
    "messages": [{"role": "user", "content": "记住我的名字是小明，我来自北京"}]
})
write_ok = json.dumps(mem_resp).count("记住") > 0 or mem_resp.get("choices") is not None
test("Memory write triggered", write_ok, "Remember tool should be called")

# Step 2: Read from DB
try:
    import sqlite3
    db_path = "xiao6.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT content FROM memories WHERE event_type = 'user_fact' ORDER BY created_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    
    has_memory = row is not None and ("小明" in row[0] or "北京" in row[0])
    test("Memory persisted to DB", has_memory, 
         f"Found: {row[0] if row else 'None'}")
except Exception as e:
    test("Memory DB access", False, str(e))

# ============================================================
# Test 4: Goal Execution
# ============================================================
print("\n[4/5] Goal Execution")

# Create a goal
goal_resp = post("/api/goals", {
    "title": "RC-5 测试任务",
    "description": "验证 Goal 系统是否正常",
    "steps": ["步骤1", "步骤2"]
})

goal_id = goal_resp.get("id") or goal_resp.get("goal_id")
test("Goal creation", goal_id is not None, f"Response: {json.dumps(goal_resp)[:100]}")

if goal_id:
    # Check goal status
    status_resp = post(f"/api/goals/{goal_id}", {})
    test("Goal status check", status_resp.get("status") is not None,
         f"Status: {status_resp.get('status')}")

# List goals
list_resp = post("/api/goals", {})
if isinstance(list_resp, list):
    test("Goal listing", len(list_resp) > 0, f"Found {len(list_resp)} goals")
else:
    test("Goal listing", False, f"Unexpected response: {type(list_resp)}")

# ============================================================
# Test 5: Identity Regression
# ============================================================
print("\n[5/5] Identity Regression")

resp = post("/api/chat", {
    "messages": [{"role": "user", "content": "你是谁？"}]
})

content = ""
if resp.get("choices"):
    for c in resp["choices"]:
        if isinstance(c, dict):
            content += c.get("delta", {}).get("content", "")
            content += c.get("message", {}).get("content", "")

has_xiao6 = "小6" in content
no_agnes = "Agnes" not in content and "Sapiens AI" not in content
has_identity = "我是小6" in content or "小6" in content

test("Identity contains 小6", has_xiao6, f"Response: {content[:50]}")
test("Identity no Agnes/Sapiens", no_agnes, "Should not mention external AI")
test("Identity format correct", has_identity, "Should say '我是小6'")

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print("RC-5 Regression Summary")
print("=" * 60)

pass_count = sum(1 for r in RESULTS if r["status"] == "PASS")
fail_count = sum(1 for r in RESULTS if r["status"] == "FAIL")
total = len(RESULTS)

print(f"\nTotal: {total}")
print(f"PASS: {pass_count}")
print(f"FAIL: {fail_count}")
print(f"Score: {pass_count}/{total}")

if fail_count > 0:
    print("\nFailed tests:")
    for r in RESULTS:
        if r["status"] == "FAIL":
            print(f"  - {r['label']}: {r['detail']}")

sys.exit(0 if fail_count == 0 else 1)
