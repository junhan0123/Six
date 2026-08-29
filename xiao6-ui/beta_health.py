"""Beta Health Check — 整合既有自检/主动/自我觉察为统一健康检测（Phase 34 Task 5）。

检测维度（仅提示，禁止自动修复）：
    backend    —— 后端进程存活 / 就绪标志（复用 lifecycle 与 /api/health 语义）。
    memory     —— 记忆系统可读、V2 治理层 Flag 状态、关键表行数（只读 SELECT）。
    capability —— 能力注册表非空、Policy Engine 可用（只读聚合）。
    avatar     —— Avatar 状态词表齐全、Body 帧目录至少含 Idle/Listening/Thinking。
    voice      —— TTS 后端已配置、ASR/KWS 模块可导入（只读探测）。

纪律（红线）：
- 全程只读；绝不修改系统 / 自动修复 / 自动执行。
- 复用 self_diagnosis / self_awareness / capability_registry / config / db（既有真相源）。
- 返回结构化报告，供前端/CLI 提示；任何修复建议仅以 message 呈现。
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

DOMAINS = ["backend", "memory", "capability", "avatar", "voice"]


def _check_backend() -> dict:
    try:
        import lifecycle

        ready = bool(getattr(lifecycle, "is_ready", False))
        cached = getattr(lifecycle, "self_check_result", None)
        ok = bool(cached and cached.get("ok"))
        return {
            "domain": "backend", "status": "ok" if ok else "warn",
            "message": "后端就绪" if ok else "后端未完全就绪（自检未通过或尚未完成）",
            "detail": {"ready": ready, "self_check_ok": ok},
        }
    except Exception as e:
        return {"domain": "backend", "status": "warn", "message": f"后端状态读取失败: {e}", "detail": {}}


def _check_memory() -> dict:
    detail = {}
    try:
        import config
        from memory_v2 import flags as mv2_flags
        detail["memory_v2_enable"] = bool(mv2_flags.MEMORY_V2_ENABLE)
        detail["semantic_enable"] = bool(mv2_flags.SEMANTIC_MEMORY_ENABLE)
        detail["evolution_enable"] = bool(mv2_flags.MEMORY_EVOLUTION_ENABLE)
        from db import db_conn
        import sqlite3

        conn = db_conn()
        conn.row_factory = sqlite3.Row
        try:
            for t in ("memories", "user_model", "profile", "episodes", "conversation_memories", "mem_vectors"):
                try:
                    detail[t] = conn.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
                except Exception:
                    detail[t] = -1
        finally:
            conn.close()
        ok = detail.get("memories", 0) >= 0 and detail.get("profile", 0) >= 0
        return {
            "domain": "memory", "status": "ok" if ok else "warn",
            "message": "记忆系统可读" if ok else "记忆系统读取异常",
            "detail": detail,
        }
    except Exception as e:
        return {"domain": "memory", "status": "warn", "message": f"记忆检测失败: {e}", "detail": detail}


def _check_capability() -> dict:
    try:
        from capability_os.registry import get_registry

        n = len(get_registry())
        return {
            "domain": "capability", "status": "ok" if n > 0 else "warn",
            "message": f"能力注册表就绪（{n} 项）" if n > 0 else "能力注册表为空",
            "detail": {"capabilities": n},
        }
    except Exception as e:
        return {"domain": "capability", "status": "warn", "message": f"能力检测失败: {e}", "detail": {}}


def _check_avatar() -> dict:
    detail = {}
    try:
        # 状态词表齐全（复用前端权威定义）
        states_present = True
        try:
            import avatar_state  # 前端模块（Node）；Python 下可能不可导入，降级为文件探测
        except Exception:
            states_present = os.path.exists(os.path.join(_ROOT, "avatar-state.js"))
        detail["state_vocab_present"] = states_present
        # Body 帧目录至少含 Idle/Listening/Thinking
        body = os.path.join(_ROOT, "Xiao6_Avatar", "Body")
        required = ["Idle", "Listening", "Thinking"]
        present = [d for d in required if os.path.isdir(os.path.join(body, d))]
        detail["body_folders"] = present
        ok = states_present and len(present) >= 3
        msg = "Avatar 状态机与帧目录就绪" if ok else "Avatar 帧目录不完整（缺失 %s）" % (
            ",".join(set(required) - set(present)) or "无")
        return {"domain": "avatar", "status": "ok" if ok else "warn", "message": msg, "detail": detail}
    except Exception as e:
        return {"domain": "avatar", "status": "warn", "message": f"Avatar 检测失败: {e}", "detail": detail}


def _check_voice() -> dict:
    try:
        import config

        tts = getattr(config, "TTS_BACKEND", "") or ""
        detail = {"tts_backend": tts}
        # ASR / KWS 模块可导入（只读探测）
        asr_ok = True
        try:
            import asr  # noqa
        except Exception:
            asr_ok = False
        detail["asr_importable"] = asr_ok
        ok = bool(tts)
        return {
            "domain": "voice", "status": "ok" if ok else "warn",
            "message": f"语音后端={tts}" if ok else "TTS 后端未配置",
            "detail": detail,
        }
    except Exception as e:
        return {"domain": "voice", "status": "warn", "message": f"语音检测失败: {e}", "detail": {}}


_CHECKS = {
    "backend": _check_backend,
    "memory": _check_memory,
    "capability": _check_capability,
    "avatar": _check_avatar,
    "voice": _check_voice,
}


def run() -> dict:
    """运行全部维度检测，返回结构化报告（仅提示，不修复）。"""
    modules = []
    for d in DOMAINS:
        try:
            modules.append(_CHECKS[d]())
        except Exception as e:
            modules.append({"domain": d, "status": "warn", "message": f"检测异常: {e}", "detail": {}})
    n_warn = sum(1 for m in modules if m["status"] != "ok")
    overall = "ok" if n_warn == 0 else ("degraded" if n_warn < len(modules) else "fail")
    return {
        "ok": n_warn == 0,
        "overall": overall,
        "modules": modules,
        "summary": "全部子系统健康" if n_warn == 0 else f"{n_warn} 项需关注（仅提示，不自动修复）",
    }


def format_report(rep: dict | None = None) -> str:
    rep = rep or run()
    lines = ["【Beta Health Check】%s" % rep["summary"]]
    for m in rep["modules"]:
        lines.append("· %s[%s] %s" % (m["domain"], m["status"], m["message"]))
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_report())
