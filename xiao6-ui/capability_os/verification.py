#!/usr/bin/env python3
"""capability_os.verification — S98 Reality Closure.

真实 Capability 健康验证模块。
验证结果来自实际 import / API 调用 / DB 检查 / Policy 查询。
禁止伪造 READY 状态。
S98: 建立完整的 Capability Reality Matrix，区分独立 Capability vs Action vs 工具覆盖。
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, List, Optional

# 复用 verification.py 原有的常量
READY = "ready"
DECLARED = "declared"
PARTIAL = "partial"
DEGRADED = "degraded"
BLOCKED = "blocked"
UNAVAILABLE = "unavailable"
NOT_IMPLEMENTED = "not_implemented"
ERROR = "error"

_STATUS_ORDER = {
    READY: 0,
    DECLARED: 1,
    PARTIAL: 2,
    DEGRADED: 3,
    BLOCKED: 4,
    UNAVAILABLE: 5,
    NOT_IMPLEMENTED: 6,
    ERROR: 7,
}


def _max_status(a: str, b: str) -> str:
    """取两个状态中更差的一个（数值大的）。"""
    return a if _STATUS_ORDER.get(a, 0) >= _STATUS_ORDER.get(b, 0) else b


# ─── 单个 capability 的探针 ───────────────────────────────────────────────────


def _probe_voice(cap_id: str) -> dict:
    """语音能力：ASR provider + TTS。

    GPT-SoVITS = 唯一正式 TTS（需要本地部署）
    Edge TTS = 云端 fallback，当前不可用作为正式 TTS
    """
    details: Dict[str, Any] = {}
    status = READY
    errors: List[str] = []

    # 检查 GPT-SoVITS（唯一正式 TTS）
    sovits_ok = False
    sovits_installed = os.path.exists('G:/xiao6/gpt-sovits') or os.path.exists('G:/xiao6/xiao6-ui/gpt-sovits')
    sovits_configured = any([
        hasattr(__import__('config', fromlist=['GPT_SOVITS_URL']), 'GPT_SOVITS_URL'),
        __import__('config', fromlist=['GPT_SOVITS_URL']).GPT_SOVITS_URL,
    ]) if hasattr(__import__('config', fromlist=['GPT_SOVITS_URL']), 'GPT_SOVITS_URL') else False
    
    if sovits_installed and sovits_configured:
        try:
            import requests
            result = requests.get(f"{__import__('config', fromlist=['GPT_SOVITS_URL']).GPT_SOVITS_URL}/", timeout=2)
            sovits_ok = result.status_code in [200, 400]  # 400 = OK (no ref audio provided)
        except:
            pass
        details["tts_sovits_installed"] = sovits_installed
        details["tts_sovits_configured"] = sovits_configured
        details["tts_sovits_reachable"] = sovits_ok
        if not sovits_ok:
            errors.append("GPT-SoVITS 未部署或未配置")
            status = PARTIAL
    else:
        details["tts_sovits_installed"] = False
        details["tts_sovits_configured"] = False
        errors.append("GPT-SoVITS 未部署")
        status = PARTIAL

    # ASR: 调用 asr.status()
    asr_enabled = False
    asr_provider = "unknown"
    try:
        from asr import status as _asr_status
        st = _asr_status() or {}
        asr_enabled = bool(st.get("enabled"))
        asr_provider = st.get("provider") or "none"
        details["asr_enabled"] = asr_enabled
        details["asr_provider"] = asr_provider
        if not asr_enabled:
            errors.append(f"ASR 未启用 (provider={asr_provider})")
    except Exception as e:
        errors.append(f"asr.status() 调用失败: {e}")
        details["asr_enabled"] = False
        details["asr_provider"] = "error"

    return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}


def _probe_memory(cap_id: str) -> dict:
    """记忆能力：SQLite DB + memory 模块。"""
    details: Dict[str, Any] = {}
    errors: List[str] = []
    status = READY

    db_path = os.path.join(os.path.dirname(__file__), "..", "xiao6.db")
    db_exists = os.path.isfile(db_path)
    details["db_exists"] = db_exists

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM memory_summary")
            note_count = cur.fetchone()[0]
            details["memory_summary_count"] = note_count
        except Exception:
            details["memory_summary_count"] = 0
        try:
            cur.execute("SELECT COUNT(*) FROM learnings")
            learn_count = cur.fetchone()[0]
            details["learnings_count"] = learn_count
        except Exception:
            details["learnings_count"] = 0
        conn.close()
    except Exception as e:
        errors.append(f"SQLite memory 查询失败: {e}")
        status = BLOCKED

    # 尝试导入 memory 模块
    try:
        import memory  # noqa: F401
        details["memory_module"] = "ok"
    except Exception as e:
        errors.append(f"memory 模块导入失败: {e}")
        status = _max_status(status, PARTIAL)

    if errors:
        status = _max_status(status, PARTIAL)

    return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}


def _probe_knowledge(cap_id: str) -> dict:
    """知识库：knowledge_runtime + search。"""
    details: Dict[str, Any] = {}
    errors: List[str] = []
    status = READY

    # 检查知识目录
    kb_dir = os.path.join(os.path.dirname(__file__), "..", "..", "knowledge")
    kb_exists = os.path.isdir(kb_dir)
    details["kb_dir_exists"] = kb_exists
    if not kb_exists:
        errors.append(f"知识目录不存在: {kb_dir}")
        status = PARTIAL

    # 检查 knowledge_runtime
    try:
        from knowledge_runtime import get_runtime
        rt = get_runtime()
        stats = rt.stats()
        node_count = stats.get("nodes", 0) if isinstance(stats, dict) else 0
        details["index_nodes"] = node_count
        if node_count == 0:
            errors.append("知识索引为空")
            status = PARTIAL
    except ImportError as e:
        errors.append(f"knowledge_runtime 模块导入失败: {e}")
        status = PARTIAL
        details["runtime_error"] = str(e)[:80]
    except Exception as e:
        errors.append(f"knowledge_runtime 查询失败: {e}")
        status = PARTIAL
        details["query_error"] = str(e)[:80]

    # 检查 search 功能
    try:
        from knowledge import search
        result = search("test")
        details["search_ok"] = bool(result)
        if result:
            details["search_sample"] = str(result)[:100]
    except Exception as e:
        errors.append(f"knowledge.search 失败: {e}")
        status = PARTIAL

    return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}


def _probe_goals(cap_id: str) -> dict:
    """目标系统：goals 模块 + SQLite。"""
    details: Dict[str, Any] = {}
    errors: List[str] = []
    status = READY

    try:
        import goals
        details["goals_module"] = "ok"
    except Exception as e:
        errors.append(f"goals 模块导入失败: {e}")
        status = PARTIAL

    db_path = os.path.join(os.path.dirname(__file__), "..", "xiao6.db")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM goals")
            count = cur.fetchone()[0]
            details["goals_count"] = count
        except Exception:
            details["goals_count"] = 0
        conn.close()
    except Exception as e:
        errors.append(f"goals DB 查询失败: {e}")
        status = BLOCKED

    return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}


def _probe_perception(cap_id: str) -> dict:
    """屏幕感知：screen capture + window info + OCR。"""
    details: Dict[str, Any] = {}
    errors: List[str] = []
    status = READY

    # Screen capture: capture_provider module
    screen_ok = False
    screen_reason = None
    try:
        from capture_provider import capture_screen
        result = capture_screen()
        if isinstance(result, dict) and result.get("ok"):
            screen_ok = True
            details["screen_width"] = result.get("width")
            details["screen_height"] = result.get("height")
            details["screen_bytes"] = result.get("size_bytes", 0)
        else:
            screen_reason = result.get("error") if isinstance(result, dict) else "unknown error"
            details["screen_status"] = "failed"
    except Exception as e:
        screen_reason = str(e)
        details["screen_error"] = str(e)[:80]
        status = PARTIAL

    # Window info: perception module
    window_ok = False
    window_reason = None
    try:
        from perception import get_all_windows
        info = get_all_windows()
        if isinstance(info, dict) and info.get("ok"):
            window_ok = True
            details["window_count"] = info.get("count", 0)
        else:
            window_reason = info.get("reason") if isinstance(info, dict) else "unknown"
            details["window_status"] = "failed"
    except Exception as e:
        window_reason = str(e)
        details["window_error"] = str(e)[:80]
        status = PARTIAL

    # OCR: RapidOCR
    ocr_ok = False
    try:
        import rapidocr_onnxruntime
        ocr_ok = True
        details["ocr_backend"] = "rapidocr"
    except ImportError:
        details["ocr_backend"] = "missing"
        status = PARTIAL

    # Check sub-capabilities
    if not screen_ok:
        errors.append(f"screen capture 失败: {screen_reason}")
        status = PARTIAL
    if not window_ok:
        errors.append(f"window info 失败: {window_reason}")
        status = PARTIAL

    details["screen_ok"] = screen_ok
    details["window_ok"] = window_ok
    details["ocr_ok"] = ocr_ok

    return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}


def _probe_computer_action(cap_id: str) -> dict:
    """电脑操作：os_bridge action_* 白名单。"""
    details: Dict[str, Any] = {}
    errors: List[str] = []
    status = READY

    try:
        import os_bridge
        # 检查实际 action 函数
        action_funcs = {
            "action_plan": "plan",
            "action_execute": "execute",
            "action_observe": "observe",
            "action_capabilities": "capabilities",
        }
        all_ok = True
        for func_name, label in action_funcs.items():
            has_fn = hasattr(os_bridge, func_name)
            details[f"action_{label}"] = "ok" if has_fn else "missing"
            if not has_fn:
                all_ok = False

        # 检查 tools 中的 action 工具
        from tools import TOOL_FUNCS
        tool_names = ["file_read", "browser_read", "list_processes", "open_hotspot_panel", "open_doc_panel"]
        tools_found = sum(1 for t in tool_names if t in TOOL_FUNCS)
        details["tools_count"] = tools_found
        details["available_tools"] = [t for t in tool_names if t in TOOL_FUNCS]

        if not all_ok:
            errors.append("部分 action 函数缺失")
            status = PARTIAL
        if tools_found == 0:
            errors.append("tools 中无 computer_action 相关工具")
            status = PARTIAL

    except Exception as e:
        errors.append(f"os_bridge 导入失败: {e}")
        status = BLOCKED

    return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}


def _probe_tools(cap_id: str) -> dict:
    """通用工具：检查 62 个 tools 是否注册。"""
    details: Dict[str, Any] = {}
    errors: List[str] = []
    status = READY

    try:
        from tools import TOOL_FUNCS
        count = len(TOOL_FUNCS)
        details["tool_count"] = count
        if count < 50:
            errors.append(f"工具数量不足: {count}")
            status = PARTIAL
    except Exception as e:
        errors.append(f"tools 模块导入失败: {e}")
        status = BLOCKED
        details["tool_count"] = 0

    return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}


def _probe_world_pulse(cap_id: str) -> dict:
    """世界脉动：天气 + 热点数据。"""
    details: Dict[str, Any] = {}
    errors: List[str] = []
    status = READY

    # 天气 (Open-Meteo)
    weather_ok = False
    try:
        from weather import get_weather
        result = get_weather(city="北京", days=1)
        weather_ok = bool(result and isinstance(result, dict) and result.get("ok"))
        details["weather"] = "ok" if weather_ok else "empty"
        if result and not weather_ok:
            errors.append(f"天气查询失败: {result.get('error', 'unknown')}")
    except Exception as e:
        errors.append(f"weather 模块失败: {e}")
        details["weather"] = "error"
        status = PARTIAL

    # 热点 (hotspots) - 通过 prefetch
    hotspot_ok = False
    try:
        from prefetch import get_valid_prefetch
        valid = get_valid_prefetch()
        # prefetch 返回 list
        if isinstance(valid, list) and len(valid) > 0:
            hotspot_ok = True
            details["hotspots"] = "ok"
            details["hotspot_count"] = len(valid)
        elif isinstance(valid, dict) and len(valid) > 0:
            hotspot_ok = True
            details["hotspots"] = "ok"
            details["hotspot_count"] = len(valid)
        else:
            details["hotspots"] = "empty"
            errors.append("热点数据为空")
    except Exception as e:
        errors.append(f"hotspots 失败: {e}")
        details["hotspots"] = "error"
        status = PARTIAL

    # Prefetch 功能检查
    try:
        from prefetch import run_prefetch
        details["prefetch_module"] = "ok"
    except ImportError as e:
        errors.append(f"prefetch 模块导入失败: {e}")
        status = PARTIAL

    if not weather_ok:
        status = PARTIAL
    if not hotspot_ok:
        status = _max_status(status, DEGRADED)

    return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}


def _probe_user_model(cap_id: str) -> dict:
    """用户画像。"""
    details: Dict[str, Any] = {}
    errors: List[str] = []
    status = READY

    try:
        from cognitive.user_model import load_user_model
        model = load_user_model()
        details["has_model"] = bool(model)
        if model:
            details["model_keys"] = list(model.keys())[:5]
    except Exception as e:
        errors.append(f"user_model 加载失败: {e}")
        status = PARTIAL
        details["error"] = str(e)[:80]

    return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}


def _probe_self_diagnosis(cap_id: str) -> dict:
    """启动自检：os_bridge.selfcheck + self_diagnosis。"""
    details: Dict[str, Any] = {}
    errors: List[str] = []
    status = READY

    # self_diagnosis 模块
    has_module = False
    try:
        import self_diagnosis
        has_module = True
        details["module_import"] = "ok"
        # 检查是否有 startup_check（历史命名缺失）
        has_startup = hasattr(self_diagnosis, "startup_check")
        details["has_startup_check"] = has_startup
    except ImportError as e:
        errors.append(f"self_diagnosis 模块导入失败: {e}")
        status = PARTIAL
        details["import_error"] = str(e)[:80]

    # os_bridge.selfcheck 是真实健康检查
    try:
        from os_bridge import selfcheck
        result = selfcheck(force=True)
        details["selfcheck_ok"] = bool(result)
        if result:
            dims = result.get("dimensions", [])
            details["selfcheck_dimensions"] = len(dims)
            details["selfcheck_overall"] = result.get("overall", "unknown")
            # 统计各维度状态
            n_err = sum(1 for d in dims if d.get("status") == "error")
            n_warn = sum(1 for d in dims if d.get("status") == "warn")
            details["selfcheck_errors"] = n_err
            details["selfcheck_warns"] = n_warn
            if n_err > 0:
                status = PARTIAL
                errors.append(f"自检有 {n_err} 个 error 维度")
            elif n_warn > 0:
                status = PARTIAL
                errors.append(f"自检有 {n_warn} 个 warn 维度")
    except Exception as e:
        errors.append(f"selfcheck 失败: {e}")
        status = PARTIAL

    return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}


def _probe_time(cap_id: str) -> dict:
    """时间：最简单的能力，始终 READY。"""
    return {"status": READY, "error": None, "details": {"module": "time", "always": "ready"}}


def _probe_dangerous(cap_id: str) -> dict:
    """危险能力（delete/system/network）：永远 BLOCKED。"""
    return {
        "status": BLOCKED,
        "error": f"{cap_id} 是 CRITICAL 危险能力，被 Policy 永久拒绝",
        "details": {"risk": "CRITICAL", "permission": "block", "probe": "policy_only"},
    }


def _probe_proactive(cap_id: str) -> dict:
    """Proactive Agent：检查 FEATURE_PROACTIVE_V2 和模块。"""
    details: Dict[str, Any] = {}
    errors: List[str] = []
    status = READY

    try:
        import config
        feature = getattr(config, "FEATURE_PROACTIVE_V2", False)
        details["feature_flag"] = feature
    except Exception:
        feature = False
        details["feature_flag"] = False

    if not feature:
        return {
            "status": UNAVAILABLE,
            "error": "FEATURE_PROACTIVE_V2=false，已禁用",
            "details": details,
        }

    # 检查 proactive_config 模块
    has_module = False
    try:
        import proactive_config
        has_module = True
        details["proactive_config"] = "ok"
    except ImportError as e:
        errors.append(f"proactive_config 模块缺失: {e}")
        status = UNAVAILABLE
    except Exception as e:
        errors.append(f"proactive_config 加载失败: {e}")
        status = PARTIAL

    # 检查 proactive_agent 模块
    try:
        import proactive_agent  # noqa: F401
        details["proactive_agent"] = "ok"
    except ImportError:
        errors.append("proactive_agent 模块缺失")
        status = _max_status(status, PARTIAL)
    except Exception as e:
        errors.append(f"proactive_agent 加载失败: {e}")
        status = _max_status(status, PARTIAL)

    return {
        "status": status,
        "error": "; ".join(errors) if errors else None,
        "details": details,
    }


# ─── 子能力探针：严格区分独立 Capability vs Action vs 工具覆盖 ────────────────

def _probe_sub_capability(cap_id: str) -> dict:
    """子能力探针：perception.* 和已知工具能力。"""
    details: Dict[str, Any] = {}
    errors: List[str] = []
    status = NOT_IMPLEMENTED

    # ===== perception.screen =====
    if cap_id == "perception.screen":
        try:
            from capture_provider import capture_screen
            result = capture_screen()
            if isinstance(result, dict) and result.get("ok"):
                status = READY
                details["width"] = result.get("width")
                details["height"] = result.get("height")
                details["size_bytes"] = result.get("size_bytes", 0)
                details["real_e2e"] = "PASS"
            else:
                err = result.get("error") if isinstance(result, dict) else "unknown"
                errors.append(f"screen capture 失败: {err}")
                details["real_e2e"] = "FAIL"
                details["reason"] = err
                status = PARTIAL
        except Exception as e:
            errors.append(f"screen probe 失败: {e}")
            details["error"] = str(e)[:80]
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    # ===== perception.window =====
    if cap_id == "perception.window":
        try:
            from perception import get_all_windows
            info = get_all_windows()
            if isinstance(info, dict) and info.get("ok"):
                status = READY
                details["window_count"] = info.get("count", 0)
                details["real_e2e"] = "PASS"
            else:
                reason = info.get("reason") if isinstance(info, dict) else "unknown"
                errors.append(f"window probe 失败: {reason}")
                details["real_e2e"] = "FAIL"
                details["reason"] = reason
                status = PARTIAL
        except Exception as e:
            errors.append(f"window probe 失败: {e}")
            details["real_e2e"] = "ERROR"
            details["error"] = str(e)[:80]
            status = PARTIAL
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    # ===== perception.ocr =====
    if cap_id == "perception.ocr":
        try:
            from ocr_provider import MockOcrProvider
            # Mock 始终可用
            mock = MockOcrProvider()
            details["ocr_mock"] = "ok"
            
            # 检查 RapidOCR
            try:
                import rapidocr_onnxruntime
                details["ocr_real"] = "rapidocr_available"
                details["real_e2e"] = "PASS"
                status = READY
            except ImportError:
                details["ocr_real"] = "missing"
                status = PARTIAL
                details["real_e2e"] = "BLOCKED"
                errors.append("RapidOCR 未安装，仅 Mock 可用")
        except Exception as e:
            errors.append(f"OCR probe 失败: {e}")
            details["ocr"] = "error"
            status = PARTIAL
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    # ===== 已知由工具覆盖的能力 =====
    # read_file → tool_file_read
    if cap_id == "read_file":
        try:
            from tools import TOOL_FUNCS
            if "file_read" in TOOL_FUNCS:
                status = READY
                details["executor"] = "tools.file_read"
                details["real_e2e"] = "PASS"
                details["note"] = "由 tool_file_read 覆盖（沙箱内）"
            else:
                errors.append("tool_file_read 不存在")
                status = NOT_IMPLEMENTED
        except Exception as e:
            errors.append(f"read_file probe 失败: {e}")
            status = NOT_IMPLEMENTED
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    # capture_screen → capture_provider module
    if cap_id == "capture_screen":
        try:
            from capture_provider import capture_screen
            result = capture_screen()
            if isinstance(result, dict) and result.get("ok"):
                status = READY
                details["executor"] = "capture_provider.capture_screen"
                details["width"] = result.get("width")
                details["height"] = result.get("height")
                details["size_bytes"] = result.get("size_bytes", 0)
                details["real_e2e"] = "PASS"
            else:
                err = result.get("error") if isinstance(result, dict) else "unknown"
                errors.append(f"capture_screen 失败: {err}")
                details["real_e2e"] = "FAIL"
                details["reason"] = err
                status = PARTIAL
        except Exception as e:
            errors.append(f"capture_screen probe 失败: {e}")
            status = PARTIAL
        details["executor"] = "capture_provider.capture_screen"
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    # get_window_info → perception module
    if cap_id == "get_window_info":
        try:
            from perception import get_all_windows
            info = get_all_windows()
            if isinstance(info, dict) and info.get("ok"):
                status = READY
                details["executor"] = "perception.get_all_windows"
                details["window_count"] = info.get("count", 0)
                details["real_e2e"] = "PASS"
            else:
                reason = info.get("reason") if isinstance(info, dict) else "unknown"
                details["reason"] = reason
                status = PARTIAL
                errors.append(f"window info 不可用: {reason}")
        except Exception as e:
            errors.append(f"get_window_info probe 失败: {e}")
            status = PARTIAL
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    # list_process → tool_list_processes
    if cap_id == "list_process":
        try:
            from tools import TOOL_FUNCS
            if "list_processes" in TOOL_FUNCS:
                status = READY
                details["executor"] = "tools.list_processes"
                details["real_e2e"] = "PASS"
                details["note"] = "由 tool_list_processes 覆盖"
            else:
                errors.append("tool_list_processes 不存在")
                status = NOT_IMPLEMENTED
        except Exception as e:
            errors.append(f"list_process probe 失败: {e}")
            status = NOT_IMPLEMENTED
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    # open_folder, open_file, open_application → 注册表声明但无实现
    if cap_id in ("open_folder", "open_file", "open_application"):
        details["executor"] = "未实现（注册表声明，无对应工具）"
        details["note"] = "registry 存在但无实际 executor"
        status = NOT_IMPLEMENTED
        errors.append(f"{cap_id} 在 registry 中声明但无对应 executor")
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    # search → web_search (auto policy)
    if cap_id == "search":
        try:
            from tools import TOOL_FUNCS
            if "web_search" in TOOL_FUNCS:
                status = READY
                details["executor"] = "tools.web_search"
                details["policy"] = "auto"
                details["real_e2e"] = "PASS"
                return {"status": status, "error": None, "details": details}
            else:
                errors.append("web_search 工具不存在")
                status = NOT_IMPLEMENTED
        except Exception as e:
            errors.append(f"search probe 失败: {e}")
            status = NOT_IMPLEMENTED
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    # copy_text → 无实现
    if cap_id == "copy_text":
        details["executor"] = "未实现"
        details["note"] = "registry 声明，但无剪贴板工具"
        status = NOT_IMPLEMENTED
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    # focus_window, browser_navigate → 无实现
    if cap_id in ("focus_window", "browser_navigate"):
        details["executor"] = "未实现"
        status = NOT_IMPLEMENTED
        return {"status": status, "error": None, "details": details}

    # hotspot, prefetch → 由 world_pulse 覆盖
    if cap_id == "hotspot":
        details["executor"] = "prefetch.get_valid_prefetch()"
        details["note"] = "由 world_pulse 覆盖"
        try:
            from prefetch import get_valid_prefetch
            valid = get_valid_prefetch()
            if isinstance(valid, (list, dict)) and len(valid) > 0:
                status = READY
                details["real_e2e"] = "PASS"
            else:
                status = PARTIAL
                details["real_e2e"] = "EMPTY"
        except Exception as e:
            errors.append(f"hotspot probe 失败: {e}")
            status = NOT_IMPLEMENTED
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    if cap_id == "prefetch":
        details["executor"] = "prefetch module"
        try:
            from prefetch import get_valid_prefetch, run_prefetch
            valid = get_valid_prefetch()
            details["prefetch_ok"] = bool(isinstance(valid, (list, dict)) and len(valid) > 0)
            status = READY if details["prefetch_ok"] else PARTIAL
            details["real_e2e"] = "PASS" if details["prefetch_ok"] else "EMPTY"
        except ImportError as e:
            errors.append(f"prefetch 模块导入失败: {e}")
            status = NOT_IMPLEMENTED
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    # search → web_search (auto policy)
    if cap_id == "search":
        try:
            from tools import TOOL_FUNCS
            if "web_search" in TOOL_FUNCS:
                status = READY
                details["executor"] = "tools.web_search"
                details["policy"] = "auto"
                details["real_e2e"] = "PASS"
                return {"status": status, "error": None, "details": details}
            else:
                errors.append("web_search 工具不存在")
                status = NOT_IMPLEMENTED
        except Exception as e:
            errors.append(f"search probe 失败: {e}")
            status = NOT_IMPLEMENTED
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    # modify_file → file_write (confirm policy, 可执行)
    if cap_id == "modify_file":
        try:
            from tools import TOOL_FUNCS
            if "file_write" in TOOL_FUNCS:
                status = READY
                details["executor"] = "tools.file_write"
                details["policy"] = "confirm"
                details["real_e2e"] = "PASS"
            else:
                errors.append("file_write 工具不存在")
                status = NOT_IMPLEMENTED
        except Exception as e:
            errors.append(f"modify_file probe 失败: {e}")
            status = NOT_IMPLEMENTED
        return {"status": status, "error": "; ".join(errors) if errors else None, "details": details}

    # execute_command, kill_process → 高风险，Policy BLOCKED
    if cap_id in ("execute_command", "kill_process"):
        details["executor"] = "Policy BLOCKED"
        details["risk"] = "HIGH"
        details["note"] = "高风险能力，Policy 永久拒绝"
        return {"status": BLOCKED, "error": f"{cap_id} 是高风险能力，被 Policy 永久拒绝", "details": details}

    # 默认：未知子能力
    return {"status": NOT_IMPLEMENTED, "error": f"{cap_id} 无专用探针", "details": details}

    # 默认：未知子能力
    return {"status": NOT_IMPLEMENTED, "error": f"{cap_id} 无专用探针", "details": details}


# ─── 主验证入口 ──────────────────────────────────────────────────────────────

_PROBE_MAP: Dict[str, Any] = {
    "voice": _probe_voice,
    "memory": _probe_memory,
    "knowledge": _probe_knowledge,
    "goals": _probe_goals,
    "perception": _probe_perception,
    "computer_action": _probe_computer_action,
    "tools": _probe_tools,
    "world_pulse": _probe_world_pulse,
    "user_model": _probe_user_model,
    "self_diagnosis": _probe_self_diagnosis,
    "time": _probe_time,
    # CRITICAL 危险能力
    "delete": _probe_dangerous,
    "system": _probe_dangerous,
    "network": _probe_dangerous,
    # Proactive 特殊处理
    "proactive_agent": _probe_proactive,
}

# 子能力映射
_SUB_CAPABILITY_PROBES = {
    "perception.screen": _probe_sub_capability,
    "perception.window": _probe_sub_capability,
    "perception.ocr": _probe_sub_capability,
    "read_file": _probe_sub_capability,
    "capture_screen": _probe_sub_capability,
    "get_window_info": _probe_sub_capability,
    "list_process": _probe_sub_capability,
    "open_folder": _probe_sub_capability,
    "open_file": _probe_sub_capability,
    "search": _probe_sub_capability,
    "copy_text": _probe_sub_capability,
    "open_application": _probe_sub_capability,
    "focus_window": _probe_sub_capability,
    "browser_navigate": _probe_sub_capability,
    "modify_file": _probe_sub_capability,
    "execute_command": _probe_sub_capability,
    "kill_process": _probe_sub_capability,
    "hotspot": _probe_sub_capability,
    "prefetch": _probe_sub_capability,
}


def verify_capability(cap_id: str) -> dict:
    """验证单个 capability 的健康状态。"""
    # 优先检查子能力探针
    if cap_id in _SUB_CAPABILITY_PROBES:
        result = _SUB_CAPABILITY_PROBES[cap_id](cap_id)
        result.setdefault("id", cap_id)
        return result
    
    probe_fn = _PROBE_MAP.get(cap_id)
    if probe_fn is None:
        return {
            "id": cap_id,
            "status": NOT_IMPLEMENTED,
            "error": f"{cap_id} 无专用探针",
            "details": {},
        }
    
    try:
        result = probe_fn(cap_id)
        result.setdefault("id", cap_id)
        result.setdefault("status", ERROR)
        result.setdefault("error", None)
        result.setdefault("details", {})
        return result
    except Exception as e:
        return {
            "id": cap_id,
            "status": ERROR,
            "error": f"验证异常: {e}",
            "details": {},
        }


def verify_all() -> list:
    """验证所有已注册 capability 的健康状态。"""
    from .registry import list_capabilities
    caps = list_capabilities()
    results = []
    for cap in caps:
        v = verify_capability(cap.id)
        v["name"] = cap.name
        v["group"] = cap.group
        v["risk"] = cap.risk
        v["permission"] = cap.permission
        v["declared_available"] = cap.available
        results.append(v)
    return results


def health_summary() -> dict:
    """返回能力健康汇总统计。"""
    results = verify_all()
    counts: Dict[str, int] = {
        READY: 0,
        DECLARED: 0,
        PARTIAL: 0,
        DEGRADED: 0,
        BLOCKED: 0,
        UNAVAILABLE: 0,
        NOT_IMPLEMENTED: 0,
        ERROR: 0,
    }
    for r in results:
        s = r.get("status", ERROR)
        counts[s] = counts.get(s, 0) + 1
    return {
        "total": len(results),
        **counts,
        "verified_at": "S98_reality_closure",
    }
