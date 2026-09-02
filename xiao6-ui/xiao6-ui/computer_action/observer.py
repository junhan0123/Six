#!/usr/bin/env python3
"""Xiao6 · 电脑动作观察层（observer.py）—— Phase 21.1

包装 Phase 20 perception，作为动作闭环的「观察」环节；同时提供兼容
VerificationLayer 的 Observer 可调用对象（统一观察源，消除 RealObserver 重复实现，修复 R3）。
"""
from __future__ import annotations


def _enabled():
    try:
        import config
        if not getattr(config, "FEATURE_COMPUTER_ACTION", True):
            return False
        if not getattr(config, "FEATURE_PERCEPTION", True):
            return False
    except Exception:
        pass
    return True


def observe(scope="window"):
    """归一化观察快照，供规划/验证使用（只读，不触发任何写/自动化）。"""
    if not _enabled():
        return {"ok": False, "reason": "disabled", "active_window": None,
                "windows": [], "screen": None, "ocr_text": [], "environment": {}}
    try:
        import perception
        snap = perception.observe(scope=scope, with_ocr=True)
        active = (snap.get("active_window") or {})
        windows = snap.get("windows") or []
        screen = snap.get("screen") or {}
        ocr = snap.get("ocr") or {}
        ocr_text = [s.get("text", "") for s in (ocr.get("spans") or []) if s.get("text")]
        return {
            "ok": True,
            "active_window": active.get("name"),
            "active_process": active.get("process"),
            "windows": [w.get("name") for w in windows if w.get("name")],
            "screen": {"width": screen.get("width"), "height": screen.get("height"),
                       "monitors": screen.get("monitors")},
            "ocr_text": ocr_text,
            "environment": {"os": _os_name()},
            "timestamp": snap.get("timestamp"),
        }
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def _os_name():
    import sys
    return sys.platform


class Observer:
    """兼容 VerificationLayer(observer=...) 的可调用观察源（统一走 perception）。"""

    def __init__(self, scope="window"):
        self.scope = scope

    def __call__(self):
        o = observe(self.scope)
        if not o.get("ok"):
            return None
        return {
            "processes": [{"name": w} for w in (o.get("windows") or [])],
            "applications": [{"name": w} for w in (o.get("windows") or [])],
            "focused_window": {"title": o.get("active_window")},
            "visionFacts": o.get("ocr_text") or [],
        }
