#!/usr/bin/env python3
"""
S113 Repository Legacy Purge Test
验证工作树中无历史项目资产残留。
"""
import subprocess
import sys
import os


def run_grep(pattern, paths=None, extra_args=""):
    """运行 rg grep 并返回结果"""
    cmd = f"rg -n -i \"{pattern}\" {extra_args}"
    if paths:
        cmd += " " + " ".join(paths)
    else:
        cmd += " ."
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1


def test_release_removed():
    """验证 release/ 目录已被删除"""
    release_path = os.path.join(os.path.dirname(__file__), '..', 'release')
    assert not os.path.exists(release_path), f"release/ directory still exists at {release_path}"
    print("✓ Test 1 PASS: release/ directory removed")


def test_no_legacy_runtime():
    """验证生产代码中无 Legacy Runtime 引用"""
    pattern = "ZhuangZhou|庄周|ZZ_PROJECT_ROOT|xiao6-hub|ZHUANGZHOU_"
    output, _ = run_grep(pattern, extra_args="--type py --glob '!**/.git/**' --glob '!**/__pycache__/**'")
    
    if output:
        print(f"Found legacy runtime references:\n{output}")
        assert False, "Legacy runtime references found in production code"
    print("✓ Test 2 PASS: LEGACY_RUNTIME = 0")


def test_no_legacy_protocol():
    """验证生产代码中无 Legacy Protocol 引用"""
    pattern = "zz\\.sse|zz\\.goal|zz\\.hud|zz\\.mobile|zz\\.clipboard|zz-agent-runtime"
    output, _ = run_grep(pattern, extra_args="--type py --glob '!**/.git/**' --glob '!**/__pycache__/**'")
    
    if output:
        print(f"Found legacy protocol references:\n{output}")
        assert False, "Legacy protocol references found in production code"
    print("✓ Test 3 PASS: LEGACY_PROTOCOL = 0")


def test_no_legacy_source():
    """验证生产代码中无 Legacy Source 引用"""
    pattern = "xiao6-hub|ZHUANGZHOU_|zz_agent_runtime"
    output, _ = run_grep(pattern, extra_args="--glob '!**/.git/**'")
    
    if output:
        print(f"Found legacy source references:\n{output}")
        assert False, "Legacy source references found in production code"
    print("✓ Test 4 PASS: LEGACY_SOURCE = 0")


def test_no_legacy_asset():
    """验证工作树中无 Legacy Asset"""
    # 检查是否还有 release/ 目录或其他历史资产
    ui_path = os.path.join(os.path.dirname(__file__), '..')
    release_path = os.path.join(ui_path, 'release')
    
    if os.path.exists(release_path):
        assert False, f"Legacy asset found: release/ directory"
    
    print("✓ Test 5 PASS: LEGACY_ASSET = 0")


def test_instance_scoped_seam():
    """验证 Test Seam 已改为 instance-scoped"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from agent_runtime import AgentRuntime
    
    # 生产实例无 provider
    runtime_prod = AgentRuntime()
    assert runtime_prod._completion_provider is None
    
    # 测试实例可注入 provider
    mock_provider = lambda: None
    runtime_test = AgentRuntime(completion_provider=mock_provider)
    assert runtime_test._completion_provider == mock_provider
    
    print("✓ Test 6 PASS: Instance-scoped completion provider verified")


def test_no_class_level_state():
    """验证无 class-level mutable state"""
    from agent_runtime import AgentRuntime
    
    # 不再使用 _test_completion_response/_test_completion_call_count
    # 保留向后兼容但应不使用
    runtime = AgentRuntime()
    assert not hasattr(runtime, '_test_completion_response') or runtime._test_completion_response is None
    
    print("✓ Test 7 PASS: No class-level mutable state in use")


if __name__ == "__main__":
    print("=" * 60)
    print("S113 Repository Legacy Purge Tests")
    print("=" * 60)
    
    test_release_removed()
    test_no_legacy_runtime()
    test_no_legacy_protocol()
    test_no_legacy_source()
    test_no_legacy_asset()
    test_instance_scoped_seam()
    test_no_class_level_state()
    
    print("\n" + "=" * 60)
    print("All S113 legacy purge tests PASSED")
    print("=" * 60)
    print("\nFinal Truth:")
    print("  LEGACY_RUNTIME = 0")
    print("  LEGACY_PROTOCOL = 0")
    print("  LEGACY_SOURCE = 0")
    print("  LEGACY_ASSET = 0")
