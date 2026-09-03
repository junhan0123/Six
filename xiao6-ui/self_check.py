#!/usr/bin/env python3
"""小6 · 启动自检：检查依赖、密钥、数据库、外部 API 可达性。

输出结构化结果，按「系统环境 / 凭证配置 / 外部服务」分组，
每项带 ok / detail / category / elapsed_ms，供自检报告页渲染。
"""

from __future__ import annotations

import os
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
from typing import Any

from config import AGNES_BASE, AGNES_KEY, DB_PATH, GPT_SOVITS_REF_AUDIO, GPT_SOVITS_URL, HOTDATA_KEY, TTS_BACKEND

# 缓存自检结果，避免每次 /api/health 都重复探测
_check_lock = threading.Lock()
_cached_result: dict[str, Any] | None = None
_cached_at = 0.0
_CACHE_TTL_SECONDS = 30

# 检查项 -> 分组（供报告页归类渲染）
_CATEGORY = {
    "_check_python": "系统环境",
    "_check_deps": "系统环境",
    "_check_tools_count": "系统环境",
    "_check_db": "系统环境",
    "_check_agnes_key": "凭证配置",
    "_check_tts": "凭证配置",
    "_check_agnes_reachable": "外部服务",
    "_check_openmeteo": "外部服务",
    "_check_hotspot_sources": "外部服务",
    "_check_feature_flags": "能力开关",
    "_check_knowledge_index": "能力开关",
    "_check_devices": "能力开关",
}


def _http_head(url: str, timeout: int = 8) -> tuple[bool, str]:
    """对给定 URL 发 HEAD/GET，返回 (ok, detail)。"""
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Xiao6/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        # 4xx/5xx 也算可达（对方在响应）
        return True, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)[:120]


def _timed(fn) -> dict[str, Any]:
    """包裹单个检查，记录耗时并补上分组字段。

    severity: "required"（默认，失败即阻断 readiness）| "optional"（失败仅记
    degraded，不阻断整体 health —— 用于可选外部能力/凭证缺失）。
    """
    s = time.time()
    try:
        result = fn()
    except Exception as e:  # 任何意外都不应让自检整体崩溃
        result = {"name": getattr(fn, "__name__", "?"), "ok": False, "detail": f"检查异常：{e}"}
    result["elapsed_ms"] = round((time.time() - s) * 1000, 1)
    result["category"] = _CATEGORY.get(fn.__name__, "其它")
    result.setdefault("severity", "required")
    return result


def _check_python() -> dict[str, Any]:
    return {"name": "Python 版本", "ok": sys.version_info >= (3, 11), "detail": sys.version.split()[0]}


def _check_deps() -> dict[str, Any]:
    """检查核心依赖（不含 TTS）。"""
    deps = ["llm", "db", "tools", "weather", "hotspots", "http_client"]
    missing = []
    for mod in deps:
        try:
            __import__(mod)
        except Exception as e:
            missing.append(f"{mod}: {e}")
    return {"name": "核心依赖", "ok": not missing, "detail": "全部就绪" if not missing else "; ".join(missing)}
    try:
        from tools import TOOL_FUNCS

        n = len(TOOL_FUNCS)
        return {"name": "本地工具注册", "ok": n > 0, "detail": f"{n} 个工具已挂载"}
    except Exception as e:
        return {"name": "本地工具注册", "ok": False, "detail": f"读取失败：{e}"}


def _check_tools_count() -> dict[str, Any]:
    try:
        from tools import TOOL_FUNCS

        n = len(TOOL_FUNCS)
        return {"name": "本地工具注册", "ok": n > 0, "detail": f"{n} 个工具已挂载"}
    except Exception as e:
        return {"name": "本地工具注册", "ok": False, "detail": f"读取失败：{e}"}


def _check_db() -> dict[str, Any]:
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return {"name": "SQLite 数据库", "ok": True, "detail": DB_PATH}
    except Exception as e:
        return {"name": "SQLite 数据库", "ok": False, "detail": str(e)[:120]}


def _check_agnes_key() -> dict[str, Any]:
    ok = bool(AGNES_KEY)
    return {
        "name": "Agnes API 密钥",
        "ok": ok,
        "detail": "已配置" if ok else "未配置（请检查 .env 或环境变量 AGNES_API_KEY）",
    }


def _check_tts() -> dict[str, Any]:
    """检查 TTS（GPT-SoVITS = 唯一正式 TTS）。"""
    # 检查 GPT-SoVITS
    import os as _os
    import config as _config
    sovits_installed = _os.path.exists('G:/xiao6/gpt-sovits') or _os.path.exists('G:/xiao6/xiao6-ui/gpt-sovits')
    sovits_configured = bool(getattr(_config, 'GPT_SOVITS_URL', None))
    sovits_reachable = False
    if sovits_installed and sovits_configured:
        try:
            import requests
            result = requests.get(f"{_config.GPT_SOVITS_URL}/", timeout=2)
            sovits_reachable = result.status_code in [200, 400]  # 400 = OK (no ref audio provided)
        except:
            pass

    if sovits_reachable:
        return {"name": "TTS 语音合成", "ok": True, "detail": "GPT-SoVITS 已部署并可用"}
    elif sovits_configured:
        return {"name": "TTS 语音合成", "ok": False, "detail": "GPT-SoVITS 已配置但不可达"}
    else:
        return {"name": "TTS 语音合成", "ok": False, "detail": "GPT-SoVITS 未部署"}


def _check_agnes_reachable() -> dict[str, Any]:
    """只检查 Agnes base URL 是否可达，不消耗 key/积分。"""
    ok, detail = _http_head(AGNES_BASE, timeout=10)
    return {"name": "Agnes API 可达", "ok": ok, "detail": detail}


def _check_openmeteo() -> dict[str, Any]:
    url = "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current=temperature_2m&forecast_days=1"
    ok, detail = _http_head(url, timeout=8)
    return {"name": "天气源 Open-Meteo", "ok": ok, "detail": detail}


def _check_hotspot_sources() -> dict[str, Any]:
    """检查各热点源是否可达；抖音用公开 API，其余需要 HOTDATA_KEY。

    HOTDATA_KEY 属**可选**外部凭证：未配置时公开抖音源仍可用，属于合法部署状态，
    只记 degraded（severity=optional），不阻断整体 health.ok；
    仅当公开源本身不可达才判为真实故障（severity=required）。
    """
    sources = [
        ("抖音(haotechs)", "https://www.haotechs.cn/ljh-wx/api/douyinHot"),
        ("抖音(xxapi)", "https://v2.xxapi.cn/api/douyinhot"),
    ]
    key_missing = not HOTDATA_KEY
    if not key_missing:
        sources.extend(
            [
                ("小红书(hotdata)", "https://w-hotdata.aipromptnav.com/api/hot-data/xiaohongshu"),
                ("微信(hotdata)", "https://w-hotdata.aipromptnav.com/api/hot-data/wxhottopic"),
                ("微博(hotdata)", "https://w-hotdata.aipromptnav.com/api/hot-data/weibohot"),
            ]
        )

    results = []
    public_ok = True
    for name, url in sources:
        ok, detail = _http_head(url, timeout=8)
        results.append(f"{name}: {'OK' if ok else 'FAIL'} {detail}")
        if not ok:
            public_ok = False
    if key_missing:
        results.append("热点源(HOTDATA_KEY): 未配置（可选能力，已降级）")

    return {
        "name": "热点数据源",
        "ok": public_ok,
        "detail": "; ".join(results),
        # 公开源可用 + 可选 key 缺失 = 降级而非故障；公开源不可达 = 真实故障
        "severity": "optional" if (public_ok and key_missing) else "required",
    }


def _check_feature_flags() -> dict[str, Any]:
    from config import (
        FEATURE_PREMIUM_UI,
        FEATURE_KNOWLEDGE_PLATFORM,
        FEATURE_PROACTIVE_V2,
        FEATURE_MULTI_DEVICE,
    )
    flags = {
        "沉浸视觉": FEATURE_PREMIUM_UI,
        "知识平台": FEATURE_KNOWLEDGE_PLATFORM,
        "主动智能V2": FEATURE_PROACTIVE_V2,
        "多端同步": FEATURE_MULTI_DEVICE,
    }
    detail = "；".join(f"{k}:{'开' if v else '关'}" for k, v in flags.items())
    return {"name": "Phase 4 功能开关", "ok": True, "detail": detail}


def _check_knowledge_index() -> dict[str, Any]:
    from config import FEATURE_KNOWLEDGE_PLATFORM

    if not FEATURE_KNOWLEDGE_PLATFORM:
        return {"name": "知识索引", "ok": True, "detail": "未启用（FEATURE_KNOWLEDGE_PLATFORM）"}
    try:
        import knowledge

        stats = knowledge.reload()  # 扫描+建索引+校验（不启动 Watcher）
        ok = bool(stats.get("validation_ok"))
        nodes = stats.get("nodes", 0)
        relations = stats.get("relations", 0)
        detail = "节点 %d / 关系 %d / 校验 %s" % (nodes, relations, "通过" if ok else "失败")
        return {"name": "知识索引", "ok": ok, "detail": detail}
    except Exception as e:
        return {"name": "知识索引", "ok": False, "detail": f"加载失败：{e}"}


def _check_devices() -> dict[str, Any]:
    from config import FEATURE_MULTI_DEVICE

    if not FEATURE_MULTI_DEVICE:
        return {"name": "已注册设备", "ok": True, "detail": "未启用（FEATURE_MULTI_DEVICE）"}
    try:
        from devices import list_devices

        arr = list_devices() or []
        return {"name": "已注册设备", "ok": True, "detail": f"{len(arr)} 台"}
    except Exception as e:
        return {"name": "已注册设备", "ok": False, "detail": f"读取失败：{e}"}


def _group_checks(checks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for c in checks:
        groups.setdefault(c.get("category", "其它"), []).append(c)
    return groups


def run_self_check(force: bool = False) -> dict[str, Any]:
    """执行启动自检，返回结构化结果。结果会缓存 30 秒。"""
    global _cached_result, _cached_at
    with _check_lock:
        if not force and _cached_result and (time.time() - _cached_at) < _CACHE_TTL_SECONDS:
            return _cached_result

    t0 = time.time()
    raw = [
        _check_python,
        _check_deps,
        _check_tools_count,
        _check_db,
        _check_agnes_key,
        _check_tts,
        _check_agnes_reachable,
        _check_openmeteo,
        _check_hotspot_sources,
        _check_feature_flags,
        _check_knowledge_index,
        _check_devices,
    ]
    checks = [_timed(fn) for fn in raw]
    elapsed = round((time.time() - t0) * 1000, 1)
    # 总体 ok 只由 required 检查项决定；optional 项失败记为 degraded（可选能力降级），
    # 不阻断 readiness —— 避免「可选外部凭证未配置」被误判为整个运行时不健康。
    failed_required = [c["name"] for c in checks if not c["ok"] and c.get("severity") != "optional"]
    degraded = [c["name"] for c in checks if not c["ok"] and c.get("severity") == "optional"]
    overall = not failed_required
    result = {
        "ok": overall,
        "degraded": degraded,
        "failed": failed_required,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "elapsed_ms": elapsed,
        "checks": checks,
        "groups": _group_checks(checks),
    }
    with _check_lock:
        _cached_result = result
        _cached_at = time.time()
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(run_self_check(force=True), ensure_ascii=False, indent=2))
