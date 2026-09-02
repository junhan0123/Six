#!/usr/bin/env python3
"""S105 Real Agent E2E Evidence Test

测试真实 Agent Runtime E2E 链路:
User Intent → Chat API → AgentRuntime → Execution Core → Policy → Tool → Result

严格验证每个阶段真实发生，禁止伪造。
"""

import sys
import os
import json
import time
import requests

# 设置项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)


def test_e2_direct_tool():
    """E2: Direct Tool Invocation"""
    # 使用绝对导入避免与 Hermes tools 冲突
    import importlib.util
    spec = importlib.util.spec_from_file_location("tools", os.path.join(PROJECT_ROOT, "tools.py"))
    tools_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tools_mod)
    
    result = tools_mod.execute_tool("calculator", {"expr": "408 * 12"})
    
    return {
        "phase": "E2_DIRECT_TOOL",
        "tool": "calculator",
        "input": "408 * 12",
        "output": str(result),
        "contains_expected": "4896" in str(result),
        "status": "PASS" if "4896" in str(result) else "FAIL"
    }


def test_e3_policy_gate():
    """E3: Policy + Executor"""
    import importlib.util
    
    # 加载 policy_engine
    spec = importlib.util.spec_from_file_location("policy_engine", os.path.join(PROJECT_ROOT, "policy_engine.py"))
    policy_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy_mod)
    
    # 加载 execution api
    spec = importlib.util.spec_from_file_location("execution_api", os.path.join(PROJECT_ROOT, "ai_core/execution/api.py"))
    exec_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exec_mod)
    
    # 测试 Policy 闸门
    policy_result = policy_mod.evaluate("calculator", {"expr": "408 * 12"})
    
    # 测试 Execution Core 集成
    exec_result = exec_mod.run(
        "calculator",
        {"args": {"expr": "100 + 200"}},
        execution_id="s105-e3-test"
    )
    
    return {
        "phase": "E3_POLICY_EXECUTOR",
        "policy_decision": policy_result.get("decision"),
        "execution_success": exec_result.get("success"),
        "execution_result": exec_result.get("result"),
        "status": "PASS" if policy_result.get("decision") == "auto" and exec_result.get("success") else "FAIL"
    }


def test_e4_agent_runtime_e2e():
    """E4: AgentRuntime End-to-End via Chat API"""
    # 通过真实 Chat API 发送请求
    resp = requests.post(
        "http://127.0.0.1:8000/api/chat",
        json={
            "messages": [{"role": "user", "content": "计算 408 乘以 12"}],
            "mode": "smart"
        },
        timeout=30
    )
    
    if resp.status_code != 200:
        return {
            "phase": "E4_AGENT_RUNTIME_E2E",
            "status": "FAIL",
            "error": f"HTTP {resp.status_code}",
            "response_text": resp.text[:500]
        }
    
    # 解析 SSE 响应 - 处理可能的字符串格式
    events = []
    for line in resp.text.split("\n"):
        if line.startswith("data: "):
            raw = line[6:]
            # 尝试解析为JSON
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    events.append(data)
            except json.JSONDecodeError:
                pass
    
    # 查找 calculator 调用和结果
    tool_start = None
    tool_end = None
    final_response = None
    
    for event in events:
        event_type = event.get("type") or event.get("event") or event.get("xiao6_event")
        if event_type == "tool_start":
            tool_start = event
        elif event_type == "tool_end":
            tool_end = event
        elif event.get("choices"):
            final_response = event
    
    # 验证完整链路
    passed = (
        tool_start is not None and
        tool_end is not None and
        tool_start.get("tool") == "calculator" and
        tool_end.get("result") and
        "4896" in str(tool_end.get("result", ""))
    )
    
    return {
        "phase": "E4_AGENT_RUNTIME_E2E",
        "status": "PASS" if passed else "FAIL",
        "http_status": resp.status_code,
        "events_count": len(events),
        "tool_called": tool_start is not None,
        "tool_name": tool_start.get("tool") if tool_start else None,
        "tool_result_contains_4896": "4896" in str(tool_end.get("result", "")) if tool_end else False,
        "final_response_preview": final_response.get("choices", [{}])[0].get("delta", {}).get("content", "")[:100] if final_response else None
    }


def test_security_regression():
    """Security Regression: Policy bypass = 0"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("policy_engine", os.path.join(PROJECT_ROOT, "policy_engine.py"))
    policy_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy_mod)
    
    dangerous_tools = ["delete", "system", "network", "execute_command", "kill_process"]
    all_blocked = True
    
    for tool in dangerous_tools:
        result = policy_mod.evaluate(tool, {})
        if result.get("decision") != "block":
            all_blocked = False
            break
    
    return {
        "phase": "SECURITY_REGRESSION",
        "status": "PASS" if all_blocked else "FAIL",
        "dangerous_tools_blocked": all_blocked,
        "checked": dangerous_tools
    }


def main():
    print("=" * 60)
    print("S105 Real Agent E2E Evidence Test")
    print("=" * 60)
    
    results = []
    
    # Test E2
    print("\n[1/4] Testing E2: Direct Tool Invocation...")
    e2_result = test_e2_direct_tool()
    results.append(e2_result)
    print(f"      Status: {e2_result['status']}")
    
    # Test E3
    print("\n[2/4] Testing E3: Policy + Executor...")
    e3_result = test_e3_policy_gate()
    results.append(e3_result)
    print(f"      Status: {e3_result['status']}")
    
    # Test E4
    print("\n[3/4] Testing E4: AgentRuntime E2E...")
    e4_result = test_e4_agent_runtime_e2e()
    results.append(e4_result)
    print(f"      Status: {e4_result['status']}")
    
    # Security Regression
    print("\n[4/4] Testing Security Regression...")
    security_result = test_security_regression()
    results.append(security_result)
    print(f"      Status: {security_result['status']}")
    
    # Summary
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    e2_pass = e2_result["status"] == "PASS"
    e3_pass = e3_result["status"] == "PASS"
    e4_pass = e4_result["status"] == "PASS"
    security_pass = security_result["status"] == "PASS"
    
    print(f"\nE2 (Direct Tool): {'PASS' if e2_pass else 'FAIL'}")
    print(f"E3 (Policy + Executor): {'PASS' if e3_pass else 'FAIL'}")
    print(f"E4 (AgentRuntime E2E): {'PASS' if e4_pass else 'FAIL'}")
    print(f"Security Regression: {'PASS' if security_pass else 'FAIL'}")
    
    e4_count = 1 if e4_pass else 0
    
    print(f"\nE4_REAL_E2E = {e4_count}")
    print(f"\nE4 Capability: calculator")
    
    print("\n" + "=" * 60)
    
    # Output JSON
    print(json.dumps({
        "e4_real_e2e": e4_count,
        "e4_capability": ["calculator"] if e4_pass else [],
        "tests": results,
        "all_passed": e2_pass and e3_pass and e4_pass and security_pass
    }, indent=2))
    
    sys.exit(0 if all([e2_pass, e3_pass, e4_pass, security_pass]) else 1)


if __name__ == "__main__":
    main()
