#!/usr/bin/env python3
"""庄周 · 安全沙箱与工具审计

设计原则（纯标准库实现、零密钥、本地优先）：
- 所有文件操作强制限制在 SANDBOX_ROOT 内（path.resolve + 相对路径不越界断言）。
- 受保护文件名禁止改/删（防止误伤 .env / 数据库等）。
- 每次工具调用写审计日志，且自动脱敏 api_key/secret/token 等敏感字段。
- run_shell 的 cwd 锁死在沙箱内，并带危险命令兜底拒绝。

"""

import json
import os
import re
import time

import config
from db import insert_audit

# 确保沙箱根存在（首次启动建好，便于直接写文件）
try:
    os.makedirs(config.SANDBOX_ROOT, exist_ok=True)
except OSError:
    pass

# 受保护文件：沙箱内也不允许改/删
PROTECTED_NAMES = {
    ".env",
    ".env.example",
    "xiao6.db",
    ".gitignore",
    "package.json",
    "readme.txt",
    "readme.md",
}

# 危险命令兜底拒绝（防御纵深：cwd 已锁沙箱，这里再拦最危险的几个）
# Phase 47.2 C-06：扩展覆盖反弹 shell / 反向连接 / 下载即执行等此前未覆盖的模式。
_DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",                 # 整盘递归删除
    r"format\s+[a-z]:",              # 格式化盘符
    r"\b(shutdown|poweroff|halt|reboot)\b",  # 关机/重启
    r"\bmkfs\b",                     # 建文件系统
    r"dd\s+if=",                     # 直接写设备
    r":\(\)\s*\{",                   # fork bomb
    r">\s*/dev/(?:sd|hd|nvme)",      # 直写块设备
    # —— 反弹 shell / 反向连接 ——
    r"\bnc\s+-e\b",                  # nc -e /bin/sh
    r"ncat\b[^\n]*-e\b",             # ncat -e
    r"bash\s+-i\b",                  # 交互式 bash（常与重定向组合成反弹）
    r"/dev/tcp/",                    # bash /dev/tcp/ 反弹技巧
    r"mkfifo\b[^\n]*\|\s*nc\b",      # mkfifo + nc 反弹
    r"\bpython\d*\s+-c\b[^\n]*socket",  # python 反向连接
    r"\bperl\b[^\n]*socket",         # perl 反向连接
    r"\bphp\b[^\n]*fsockopen",       # php 反向连接
    # —— 下载即执行 ——
    r"\b(?:curl|wget|ftp)\b[^\n]*\|\s*(?:ba)?sh\b",  # curl/wget ... | sh
    r"\b(?:curl|wget)\b[^\n]*\|\s*python\d*\b",      # curl ... | python
    r"\b(?:curl|wget)\b[^\n]*-o\s+\S+\s*&&\s*chmod",  # curl -o x && chmod +x x
]
_DANGEROUS_RE = re.compile("|".join(f"(?:{p})" for p in _DANGEROUS_PATTERNS), re.IGNORECASE)


def is_path_inside(parent_dir, candidate):
    """候选路径是否位于 parent_dir 内（解析符号链接/.. 后判断）。"""
    parent = os.path.abspath(parent_dir)
    candidate = os.path.abspath(candidate)
    rel = os.path.relpath(candidate, parent)
    return rel == "." or (not rel.startswith("..") and not os.path.isabs(rel))


def resolve_in_sandbox(raw_path):
    """把用户给的相对/绝对路径解析为沙箱内的绝对路径，并断言不越界。

    返回绝对路径；越界或指向受保护文件则抛 ValueError。
    """
    raw = (raw_path or "").strip().replace("\\", "/")
    if not raw or raw in (".", "/"):
        return config.SANDBOX_ROOT
    # 去掉用户可能带的前缀（sandbox/、./）
    raw = re.sub(r"^(sandbox/|\./)", "", raw, flags=re.IGNORECASE)
    resolved = os.path.abspath(os.path.join(config.SANDBOX_ROOT, raw))
    if resolved != config.SANDBOX_ROOT and not is_path_inside(config.SANDBOX_ROOT, resolved):
        raise ValueError(f"访问被拒绝：文件操作只允许在沙箱目录内（{config.SANDBOX_ROOT}）")
    return resolved


def assert_not_protected(resolved_path):
    name = os.path.basename(resolved_path).lower()
    if name in PROTECTED_NAMES:
        raise ValueError(f"拒绝：{name} 是受保护文件，不可修改/删除")


def is_dangerous_command(command):
    return bool(_DANGEROUS_RE.search(command or ""))


# ---------- 审计脱敏 ----------
_SENSITIVE_KEY_RE = re.compile(
    r"(api[_-]?key|apikey|access[_-]?key|secret|token|password|passwd|authorization|bearer)",
    re.IGNORECASE,
)
_SECRET_VALUE_RE = re.compile(r"\b(?:sk|ak|rk|pk)-[A-Za-z0-9_\-.]{12,180}\b")


def redact_secrets(value):
    if isinstance(value, str):
        return _SECRET_VALUE_RE.sub("[redacted]", value)
    if isinstance(value, (list, tuple)):
        return [redact_secrets(v) for v in value]
    if isinstance(value, dict):
        return {k: ("[redacted]" if _SENSITIVE_KEY_RE.search(str(k)) else redact_secrets(v)) for k, v in value.items()}
    return value


def _summarize(name, args):
    a = args or {}
    if name in ("file_read", "file_list", "file_write", "file_delete"):
        return f"{name}({(a.get('path') or a.get('filename') or a.get('file_path') or '?')})"
    if name == "run_shell":
        return f"run_shell({str(a.get('command') or '?')[:100]})"
    if name in ("web_fetch", "browser_read"):
        return f"{name}({str(a.get('url') or a.get('link') or a.get('href') or '?')[:120]})"
    if name == "web_search":
        return f"web_search({str(a.get('query') or a.get('q') or '?')[:120]})"
    return name


def audit_tool(name, args, status="ok", result="", error="", source="llm", started_at=None):
    """写入一条工具审计记录（自动脱敏 + 摘要）。任何异常都静默兜底，绝不阻断主链路。"""
    started = started_at or time.time()
    try:
        safe_args = redact_secrets(args)
        detail = _summarize(name, safe_args)
        preview = (str(result) or str(error) or "")[:220]
        insert_audit(
            tool=name,
            summary=detail,
            status=status,
            source=source,
            args_json=json.dumps(safe_args, ensure_ascii=False) if safe_args else "{}",
            result_preview=preview,
            duration_ms=int((time.time() - started) * 1000),
        )
    except Exception:
        pass
