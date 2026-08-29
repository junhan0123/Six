#!/usr/bin/env python3
"""小6 · 电脑动作安全层（safety.py）—— Phase 21.1

集中承载：动作白名单边界、风险等级、用户确认、紧急停止。
底层裁决 100% 委托 policy_engine，无第二权限系统。

白名单（Phase 21 规格「Hand」）：
  open_application / open_folder / open_file / search / copy_text
只读辅助（验证/规划用，零副作用，仍受 capability_registry 实现/风险约束）：
  read_file / list_process / capture_screen / get_window_info /
  perception.screen / perception.window / perception.ocr
"""
from __future__ import annotations

import threading

try:
    from capability_os.registry import is_implemented, risk_of
except Exception:  # pragma: no cover - 纯隔离测试场景
    def is_implemented(c):
        return True

    def risk_of(c):
        return "LOW"


# —— Phase 21 规格白名单 ——
WHITELIST = {
    "open_application",
    "open_folder",
    "open_file",
    "search",
    "copy_text",
}

# 额外允许的只读观测能力（用于验证/规划辅助，零副作用）
_READONLY_ALLOWED = {
    "read_file",
    "list_process",
    "capture_screen",
    "get_window_info",
    "perception.screen",
    "perception.window",
    "perception.ocr",
}


class SafetyViolation(Exception):
    """动作不在白名单 / 已 halt / 风险越界时抛出。"""


# 进程级紧急停止开关
_halt_event = threading.Event()


def is_halted() -> bool:
    return _halt_event.is_set()


def halt() -> None:
    """触发全局紧急停止：拒绝新动作 + 中止在途动作（执行器检查 cancel 令牌）。"""
    _halt_event.set()


def resume() -> None:
    """解除紧急停止。"""
    _halt_event.clear()


def is_allowed(cap: str) -> bool:
    if cap not in WHITELIST and cap not in _READONLY_ALLOWED:
        return False
    return bool(is_implemented(cap)) and risk_of(cap) in ("LOW", "MEDIUM")


def risk_level(cap: str) -> str:
    return risk_of(cap)


def needs_confirm(cap: str) -> bool:
    """MEDIUM 能力需用户确认（与 policy_engine CONFIRM 确定性映射一致）。"""
    return risk_of(cap) == "MEDIUM"


def assert_allowed(cap: str) -> bool:
    """白名单闸门：任何非白名单 / 越界 / 已 halt 的动作在此即拒。"""
    if is_halted():
        raise SafetyViolation(f"紧急停止已触发，动作被拒绝: {cap}")
    if not is_implemented(cap):
        raise SafetyViolation(f"能力未实现或未知: {cap}")
    r = risk_of(cap)
    if r in ("HIGH", "CRITICAL"):
        raise SafetyViolation(f"风险等级 {r} 不在 Hand 白名单内: {cap}")
    if cap not in WHITELIST and cap not in _READONLY_ALLOWED:
        raise SafetyViolation(f"能力不在 Hand 白名单内: {cap}")
    return True


def request_confirm(cap: str, params=None, **kw):
    """委托既有 policy_engine 确认通道（无第二权限系统）。"""
    from policy_engine import request_approval
    return request_approval(cap, params or {}, **kw)
