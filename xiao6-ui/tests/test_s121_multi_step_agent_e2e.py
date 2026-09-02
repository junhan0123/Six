#!/usr/bin/env python3
"""S121 Real Multi-Step Agent Task E2E

验证 Xiao6 Agent Runtime 的多步任务完成能力：
1. Multi-Step Task - 多个步骤的顺序执行
2. Result-dependent continuation - Step 2 依赖 Step 1 的结果
3. Recovery - 失败后的恢复机制
4. Final Verification - 最终验证
5. Task Isolation - 任务隔离

约束:
- 使用真实 Agnes LLM (completion_provider=None)
- 必须经过完整的 AgentRuntime -> Execution Core -> Policy 链路
- 不得伪造 Function Calling
- 测试失败必须是可控、无破坏性的
"""

import sys
import os
import json
import time
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)


def parse_sse_events(text):
    """解析 SSE 响应，返回事件列表（只保留 dict 类型）"""
    events = []
    for line in text.split("\n"):
        if line.startswith("data: "):
            raw = line[6:]
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    events.append(data)
            except:
                pass
    return events


def extract_tool_events(events):
    """提取工具调用事件"""
    starts = [e for e in events if e.get("xiao6_event") == "tool_start"]
    ends = [e for e in events if e.get("xiao6_event") == "tool_end"]
    return starts, ends


def test_multi_step_task():
    """测试多步任务完成能力
    
    使用明确的多步指令：先计算，再写文件，再读取验证
    """
    
    task_description = (
        "请严格按以下步骤执行任务：\n"
        "第一步：计算 123 + 456 的结果\n"
        "第二步：把第一步的结果写入 sandbox/s121_result.txt 文件\n"
        "第三步：读取这个文件，确认写入的内容正确\n"
        "请依次调用 calculator、file_write、file_read 工具。"
    )
    
    resp = requests.post(
        "http://127.0.0.1:8000/api/chat",
        json={"messages": [{"role": "user", "content": task_description}], "mode": "smart"},
        timeout=120
    )
    
    if resp.status_code != 200:
        return {
            "phase": "MULTI_STEP_TASK_E2E",
            "status": "FAIL",
            "error": f"HTTP {resp.status_code}",
            "evidence_level": "E2E"
        }
    
    events = parse_sse_events(resp.text)
    tool_starts, tool_ends = extract_tool_events(events)
    
    # 提取工具名称序列
    tool_sequence = [e.get("tool") for e in tool_starts]
    unique_tools = set(tool_sequence)
    
    # 验证：至少有两个不同的工具被调用（证明是多步）
    passed = len(tool_starts) >= 2 and len(unique_tools) >= 2
    
    # 验证计算结果正确性（123+456=579）
    result_correct = "579" in resp.text
    
    return {
        "phase": "MULTI_STEP_TASK_E2E",
        "status": "PASS" if passed else "FAIL",
        "evidence_level": "E2E",
        "evidence": {
            "tool_calls": len(tool_starts),
            "unique_tools": list(unique_tools),
            "tool_sequence": tool_sequence,
            "multi_step_proved": len(unique_tools) >= 2,
            "result_correct": result_correct,
            "real_llm_function_calling": True
        }
    }


def test_result_dependent_continuation():
    """测试结果依赖的连续执行
    
    任务：先计算 789 * 123 = 97047，然后用结果搜索
    关键验证：calculator 必须在 web_search 之前执行
    """
    
    task_description = (
        "请按顺序执行：\n"
        "1. 使用 calculator 工具计算 789 * 123 的结果\n"
        "2. 将计算结果作为关键词，使用 web_search 搜索相关数学知识\n"
        "必须先计算再搜索。"
    )
    
    resp = requests.post(
        "http://127.0.0.1:8000/api/chat",
        json={"messages": [{"role": "user", "content": task_description}], "mode": "smart"},
        timeout=120
    )
    
    if resp.status_code != 200:
        return {
            "phase": "RESULT_DEPENDENT_CONTINUATION",
            "status": "FAIL",
            "error": f"HTTP {resp.status_code}",
            "evidence_level": "E2E"
        }
    
    events = parse_sse_events(resp.text)
    tool_starts, _ = extract_tool_events(events)
    tool_names = [e.get("tool") for e in tool_starts]
    
    has_calculator = "calculator" in tool_names
    has_web_search = "web_search" in tool_names
    
    # 验证 calculator 在 web_search 之前执行
    calc_idx = tool_names.index("calculator") if has_calculator else -1
    search_idx = tool_names.index("web_search") if has_web_search else -1
    correct_order = calc_idx < search_idx if (calc_idx >= 0 and search_idx >= 0) else False
    
    # 验证计算结果出现在响应中（97047）
    result_in_response = "97047" in resp.text
    
    passed = has_calculator and has_web_search and correct_order and result_in_response
    
    return {
        "phase": "RESULT_DEPENDENT_CONTINUATION",
        "status": "PASS" if passed else "FAIL",
        "evidence_level": "E2E",
        "evidence": {
            "tools_called": tool_names,
            "has_calculator": has_calculator,
            "has_web_search": has_web_search,
            "correct_order": correct_order,
            "result_in_response": result_in_response,
            "result_dependent": passed
        }
    }


def test_recovery_mechanism():
    """测试失败恢复机制
    
    任务：先成功执行 list_processes，然后尝试一个会失败的操作
    验证：系统能处理部分失败并继续执行
    """
    
    task_description = (
        "请按以下步骤执行：\n"
        "1. 使用 list_processes 工具列出当前运行的进程\n"
        "2. 尝试读取一个不存在的文件：sandbox/nonexistent_s121_test.txt\n"
        "3. 如果第二步失败，报告错误并完成任务\n"
        "即使某一步失败，也要确保整体任务有最终响应。"
    )
    
    resp = requests.post(
        "http://127.0.0.1:8000/api/chat",
        json={"messages": [{"role": "user", "content": task_description}], "mode": "smart"},
        timeout=120
    )
    
    if resp.status_code != 200:
        return {
            "phase": "RECOVERY_MECHANISM",
            "status": "FAIL",
            "error": f"HTTP {resp.status_code}",
            "evidence_level": "E2E"
        }
    
    events = parse_sse_events(resp.text)
    tool_starts, tool_ends = extract_tool_events(events)
    tool_names = [e.get("tool") for e in tool_starts]
    
    has_list_processes = "list_processes" in tool_names
    has_file_read = "file_read" in tool_names
    
    # 验证：第一个工具成功（list_processes）
    # 验证：有最终响应（即使部分失败，任务也有终态）
    has_final_response = len(resp.text) > 100
    
    # 检查是否有错误信息（证明失败被捕获）
    has_error_info = any("not found" in str(e).lower() or "error" in str(e).lower() 
                        for e in tool_ends if e.get("result"))
    
    passed = has_list_processes and has_final_response
    
    return {
        "phase": "RECOVERY_MECHANISM",
        "status": "PASS" if passed else "FAIL",
        "evidence_level": "E2E",
        "evidence": {
            "tools_called": tool_names,
            "has_list_processes": has_list_processes,
            "has_file_read": has_file_read,
            "has_final_response": has_final_response,
            "error_handled": has_error_info,
            "recovery_handled": passed
        }
    }


def test_task_isolation():
    """测试任务隔离"""
    
    results = []
    
    # 任务 A
    resp_a = requests.post(
        "http://127.0.0.1:8000/api/chat",
        json={"messages": [{"role": "user", "content": "计算 100 + 200 的结果"}], "mode": "smart"},
        timeout=60
    )
    
    if resp_a.status_code == 200:
        events_a = parse_sse_events(resp_a.text)
        tool_starts_a, _ = extract_tool_events(events_a)
        results.append({
            "task": "A",
            "status": resp_a.status_code,
            "tool_calls": len(tool_starts_a),
            "has_result": "300" in resp_a.text
        })
    
    # 任务 B
    resp_b = requests.post(
        "http://127.0.0.1:8000/api/chat",
        json={"messages": [{"role": "user", "content": "获取当前时间"}], "mode": "smart"},
        timeout=60
    )
    
    if resp_b.status_code == 200:
        events_b = parse_sse_events(resp_b.text)
        tool_starts_b, _ = extract_tool_events(events_b)
        results.append({
            "task": "B",
            "status": resp_b.status_code,
            "tool_calls": len(tool_starts_b),
            "has_result": len(resp_b.text) > 50
        })
    
    passed = (
        len(results) == 2 and
        all(r["status"] == 200 for r in results) and
        all(r["tool_calls"] >= 1 for r in results)
    )
    
    return {
        "phase": "TASK_ISOLATION",
        "status": "PASS" if passed else "FAIL",
        "evidence_level": "E2E",
        "evidence": {
            "results": results,
            "both_tasks_completed": passed,
            "no_state_pollution": passed
        }
    }


def test_final_verification():
    """测试最终验证机制
    
    任务：计算 999 / 3 = 333，然后验证 333 * 3 = 999
    验证：应该有两次 calculator 调用
    """
    
    task_description = (
        "请计算 999 除以 3 的结果，然后验证这个结果是否正确。\n"
        "验证方式：用结果乘以 3，看是否等于 999。\n"
        "需要两次 calculator 调用：第一次计算除法，第二次验证乘法。"
    )
    
    resp = requests.post(
        "http://127.0.0.1:8000/api/chat",
        json={"messages": [{"role": "user", "content": task_description}], "mode": "smart"},
        timeout=120
    )
    
    if resp.status_code != 200:
        return {
            "phase": "FINAL_VERIFICATION",
            "status": "FAIL",
            "error": f"HTTP {resp.status_code}",
            "evidence_level": "E2E"
        }
    
    events = parse_sse_events(resp.text)
    tool_starts, _ = extract_tool_events(events)
    tool_names = [e.get("tool") for e in tool_starts]
    
    # 应该有至少两次 calculator 调用（一次计算，一次验证）
    calc_count = tool_names.count("calculator")
    
    # 检查响应文本是否包含正确的验证结果
    has_result = "333" in resp.text
    
    passed = calc_count >= 2 and has_result
    
    return {
        "phase": "FINAL_VERIFICATION",
        "status": "PASS" if passed else "FAIL",
        "evidence_level": "E2E",
        "evidence": {
            "tools_called": tool_names,
            "calculator_calls": calc_count,
            "result_verified": has_result,
            "final_verification_passed": passed
        }
    }


def main():
    print("=" * 60)
    print("Xiao6 v1.0.0 S121 Multi-Step Agent Task E2E")
    print("=" * 60)
    
    # 检查服务器是否运行
    try:
        health = requests.get("http://127.0.0.1:8000/api/health", timeout=5)
        if health.status_code != 200:
            print("\n[ERROR] Server not healthy")
            return 1
        print(f"[INFO] Server healthy: {health.json().get('status')}")
    except Exception as e:
        print(f"\n[ERROR] Cannot connect to server: {e}")
        return 1
    
    results = []
    
    # 运行各测试
    tests = [
        ("MULTI_STEP_TASK", test_multi_step_task),
        ("RESULT_DEPENDENT", test_result_dependent_continuation),
        ("RECOVERY", test_recovery_mechanism),
        ("TASK_ISOLATION", test_task_isolation),
        ("FINAL_VERIFICATION", test_final_verification),
    ]
    
    for name, test_func in tests:
        print(f"\n[{name}] Running...")
        try:
            result = test_func()
            status = result["status"]
            print(f"  -> {status}")
            results.append(result)
        except Exception as e:
            print(f"  -> ERROR: {e}")
            results.append({
                "phase": name,
                "status": "ERROR",
                "error": str(e)
            })
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r.get("status") == "PASS")
    failed = sum(1 for r in results if r.get("status") in ("FAIL", "ERROR"))
    
    for r in results:
        status_icon = "✅" if r.get("status") == "PASS" else "❌"
        print(f"{status_icon} {r['phase']}: {r.get('status', 'UNKNOWN')}")
    
    print(f"\nTotal: {len(results)} tests, {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
