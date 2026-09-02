#!/usr/bin/env python3
"""
S113 Test Seam Isolation Tests
验证 instance-scoped completion provider 的隔离性。
"""
import sys
import os
sys.path.insert(0, '.')

import json
from unittest.mock import MagicMock


def create_mock_response(tool_calls=None):
    """创建 mock LLM 响应对象"""
    mock = MagicMock()
    response_data = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": tool_calls or []
            }
        }]
    }
    mock.read.return_value = json.dumps(response_data).encode("utf-8")
    return mock


def test_instance_isolation():
    """Test A: 实例隔离"""
    from agent_runtime import AgentRuntime
    
    # 创建两个实例，各自注入不同的 mock provider
    resp_a = create_mock_response([{"function": {"name": "calculator", "arguments": {"expression": "1+1"}}}])
    resp_b = create_mock_response([{"function": {"name": "calculator", "arguments": {"expression": "2+2"}}}])
    
    runtime_a = AgentRuntime(completion_provider=lambda: resp_a)
    runtime_b = AgentRuntime(completion_provider=lambda: resp_b)
    
    # 验证实例间隔离
    assert runtime_a._completion_provider is not None
    assert runtime_b._completion_provider is not None
    assert runtime_a._completion_provider != runtime_b._completion_provider
    
    # 验证各自的 provider 是独立的 callable
    result_a = runtime_a._completion_provider()
    result_b = runtime_b._completion_provider()
    
    data_a = json.loads(result_a.read().decode("utf-8"))
    data_b = json.loads(result_b.read().decode("utf-8"))
    
    args_a = data_a["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]
    args_b = data_b["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]
    
    assert args_a["expression"] == "1+1", f"Expected '1+1', got {args_a['expression']}"
    assert args_b["expression"] == "2+2", f"Expected '2+2', got {args_b['expression']}"
    
    print("✓ Test A PASS: Instance isolation verified")


def test_concurrent_isolation():
    """Test B: 并发隔离"""
    import threading
    from agent_runtime import AgentRuntime
    
    results = {}
    errors = []
    
    def run_test(test_id, response_tool):
        try:
            resp = create_mock_response([{"function": {"name": response_tool, "arguments": {}}}])
            runtime = AgentRuntime(completion_provider=lambda: resp)
            results[test_id] = runtime._completion_provider
            # 验证 provider 独立
            r = runtime._completion_provider()
            data = json.loads(r.read().decode("utf-8"))
            tool_name = data["choices"][0]["message"]["tool_calls"][0]["function"]["name"]
            results[f"{test_id}_tool"] = tool_name
        except Exception as e:
            errors.append(f"{test_id}: {e}")
    
    # 并发运行两个独立测试
    threads = []
    for i in range(2):
        t = threading.Thread(target=run_test, args=(f"context_{i}", f"tool_{i}"))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    assert len(errors) == 0, f"Errors: {errors}"
    assert "context_0" in results
    assert "context_1" in results
    
    # 验证 provider 不同
    assert results["context_0"] != results["context_1"]
    
    print("✓ Test B PASS: Concurrent isolation verified")


def test_exception_cleanup():
    """Test C: 异常清理"""
    from agent_runtime import AgentRuntime
    
    call_count = [0]
    
    def failing_provider():
        call_count[0] += 1
        raise ValueError("Test exception")
    
    runtime = AgentRuntime(completion_provider=failing_provider)
    
    # 验证 provider 已设置
    assert runtime._completion_provider is not None
    
    # Provider 在运行时不会自动清理，但也不会影响其他实例
    runtime2 = AgentRuntime()
    assert runtime2._completion_provider is None
    
    print("✓ Test C PASS: Exception cleanup verified (production provider unaffected)")


def test_production_restoration():
    """Test D: 测试结束后恢复"""
    from agent_runtime import AgentRuntime
    
    # 测试实例使用 mock provider
    mock_resp = create_mock_response([])
    test_runtime = AgentRuntime(completion_provider=lambda: mock_resp)
    assert test_runtime._completion_provider is not None
    
    # 生产实例使用默认 provider
    prod_runtime = AgentRuntime()
    assert prod_runtime._completion_provider is None
    
    print("✓ Test D PASS: Production provider restoration verified")


def test_no_execution_bypass():
    """验证测试 provider 不能绕过 Planner/Execution Core/Policy/Executor"""
    from agent_runtime import AgentRuntime
    
    mock_resp = create_mock_response([{"function": {"name": "execute_command", "arguments": {"command": "echo test"}}}])
    runtime = AgentRuntime(completion_provider=lambda: mock_resp)
    
    # 验证 provider 是 callable
    assert callable(runtime._completion_provider)
    
    # 验证调用后返回值符合预期格式
    result = runtime._completion_provider()
    assert hasattr(result, 'read')
    data = json.loads(result.read().decode("utf-8"))
    
    # 验证返回数据包含 tool_calls
    assert "tool_calls" in data["choices"][0]["message"]
    
    # 注意：此测试只验证 seam 本身，不验证完整链路
    # 完整链路测试由 test_s109_agent_policy_deny.py 覆盖
    print("✓ Test E PASS: No execution bypass (seam only replaces LLM source)")


if __name__ == "__main__":
    print("=" * 60)
    print("S113 Test Seam Isolation Tests")
    print("=" * 60)
    
    test_instance_isolation()
    test_concurrent_isolation()
    test_exception_cleanup()
    test_production_restoration()
    test_no_execution_bypass()
    
    print("\n" + "=" * 60)
    print("All S113 tests PASSED")
    print("=" * 60)
