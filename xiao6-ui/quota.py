#!/usr/bin/env python3
"""庄周 · 配额 / 限流（对齐参考实现 quota.js）

滑动窗口统计 RPM（请求数 / 分钟）与 TPM（token / 分钟），在调用 LLM 前预占额度；
超阈值则阻塞等待窗口释放（避免撞 429）。服务端返回 429 时做指数退避并触发心跳降速。
"""

import json
import os
import threading
import time

import config

_lock = threading.Lock()
_rpm_ts = []          # 最近请求时间戳（秒）
_tpm_ts = []          # 与 _tpm_tokens 一一对应
_tpm_tokens = []      # 每次请求的 token 占用（输入 + 预留输出）

RPM_LIMIT = int(os.environ.get("AGNES_RPM_LIMIT", "60"))           # 每分钟最大请求数
TPM_LIMIT = int(os.environ.get("AGNES_TPM_LIMIT", "120000"))        # 每分钟最大 token 数（输入 + 预留输出）
_OUTPUT_RESERVE = int(os.environ.get("AGNES_TPM_RESERVE", "2048"))  # 每请求预留输出 token（估算）

# 服务端 429 退避（指数退避，封顶）
_backoff_until = 0.0
_backoff_step = 1.0
_MAX_BACKOFF = 120.0


def estimate_input_tokens(messages, tools=None):
    """粗略估算输入 token：中文约 1 token/字，英文约 4 字符/token。

    为安全（避免超额）取较宽估计：直接按字符数计，混排也不至于严重低估中文。
    """
    chars = 0
    for m in messages or []:
        c = m.get("content")
        if isinstance(c, str):
            chars += len(c)
        elif isinstance(c, list):
            for part in c:
                if isinstance(part, dict):
                    chars += len(str(part.get("text", "")))
    if tools:
        try:
            chars += len(json.dumps(tools, ensure_ascii=False))
        except Exception:
            chars += 0
    return max(chars, 1)


def _purge():
    """清理 60s 窗口外的统计。调用方需持 _lock。"""
    now = time.time()
    cutoff = now - 60.0
    while _rpm_ts and _rpm_ts[0] < cutoff:
        _rpm_ts.pop(0)
    while _tpm_ts and _tpm_ts[0] < cutoff:
        _tpm_ts.pop(0)
        if _tpm_tokens:
            _tpm_tokens.pop(0)


def wait_if_needed(est_tokens):
    """调用 LLM 前调用：若会超 RPM/TPM 阈值，阻塞到窗口释放。返回实际等待秒数。"""
    global _backoff_until
    waited = 0.0
    with _lock:
        # 服务端 429 退避优先于配额等待
        if _backoff_until > time.time():
            s = _backoff_until - time.time()
            time.sleep(s)
            waited += s
        _purge()
        need = est_tokens + _OUTPUT_RESERVE
        while (len(_rpm_ts) + 1 > RPM_LIMIT) or (sum(_tpm_tokens) + need > TPM_LIMIT):
            time.sleep(1.0)
            waited += 1.0
            _purge()
            if (len(_rpm_ts) + 1 <= RPM_LIMIT) and (sum(_tpm_tokens) + need <= TPM_LIMIT):
                break
    return waited


def record(est_tokens):
    """调用成功后记录一次请求（输入 token + 预留输出）。"""
    with _lock:
        _purge()
        _rpm_ts.append(time.time())
        _tpm_ts.append(time.time())
        _tpm_tokens.append(est_tokens + _OUTPUT_RESERVE)


def on_429():
    """服务端返回 429：指数退避并触发心跳降速（对齐参考实现 quota.js）。返回退避秒数。"""
    global _backoff_until, _backoff_step
    with _lock:
        _backoff_step = min(_backoff_step * 2.0, _MAX_BACKOFF)
        _backoff_until = time.time() + _backoff_step
    try:
        import proactive

        proactive.set_rate_limited(seconds=int(_backoff_step))
    except Exception:
        pass
    return _backoff_step


def usage():
    """返回当前 RPM/TPM 占用快照（供 /api/health 或调试）。"""
    with _lock:
        _purge()
        return {
            "rpm_limit": RPM_LIMIT,
            "rpm_used": len(_rpm_ts),
            "tpm_limit": TPM_LIMIT,
            "tpm_used": sum(_tpm_tokens),
            "backoff_until": _backoff_until,
        }
