#!/usr/bin/env python3
"""小6 · 本地资源扫描器（纯标准库、零副作用、只读）

用途：
    在不执行任意代码、不打开端口、不启动线程的前提下，只读地清点当前机器上
    对用户可能相关的本地资源，供 agent 直接回复或作为工具上下文。

覆盖维度（见 scan_resources 的返回字段）：
    - desktop    ：桌面目录下的文件名
    - installed  ：已装软件（winget）名称
    - ssh_hosts  ：~/.ssh/config 中定义的主机别名
    - git_repos  ：常见目录下含 .git 的仓库根

设计要点：
    - 纯标准库（os / subprocess / re / pathlib / json），无外部依赖。
    - import 时零副作用：顶层只做 import 与常量定义，不扫描、不联网、不启动进程。
    - 全程异常静默兜底（try/except 包住），任何单维度失败都不影响其余维度。
    - 纯只读、只读一层目录、列表上限 40（git 仓库上限 30），绝不递归过深或执行内容。
"""

import os
import re
import subprocess
from pathlib import Path

MAX_ITEMS = 40
MAX_REPOS = 30

# 桌面可能的目录名（Windows 下中文系统常用“桌面”）
_DESKTOP_CANDIDATES = ["~/Desktop", "~/桌面"]
# git 仓库扫描的候选根位置（存在才扫，每层只进一层）
_REPO_ROOTS = ["~/source", "~/projects", "~/Documents/GitHub"]


def _scan_desktop():
    """返回桌面目录下的文件名列表（只读一层，最多 MAX_ITEMS 个）。"""
    names = []
    for cand in _DESKTOP_CANDIDATES:
        try:
            base = Path(os.path.expanduser(cand))
            if not base.is_dir():
                continue
            for entry in os.scandir(base):
                # 只列名字，不读内容；子目录也列其名（不递归）
                names.append(entry.name)
                if len(names) >= MAX_ITEMS:
                    break
        except (OSError, PermissionError):
            pass
        if len(names) >= MAX_ITEMS:
            break
    return names[:MAX_ITEMS]


def _scan_installed():
    """用 winget 列出已装软件名称，失败则静默返回 []。"""
    try:
        proc = subprocess.run(
            ["winget", "list", "--disable-interactivity"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        out = proc.stdout or ""
    except (OSError, FileNotFoundError, subprocess.TimeoutExpired, WindowsError):
        # winget 不可用 / 超时 → 静默降级
        return []

    packages = []
    lines = out.splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # 跳过表头（含 Name / Id / 版本 等列名行）
        if stripped.lower().startswith(("name", "名称")) or "id" in stripped.lower() and "版本" in stripped:
            continue
        # 取第一列（包名）作为软件名
        first = stripped.split()[0] if stripped.split() else ""
        if first and first not in packages:
            packages.append(first)
        if len(packages) >= MAX_ITEMS:
            break
    return packages[:MAX_ITEMS]


def _scan_ssh_hosts():
    """解析 ~/.ssh/config，提取 Host 别名（排除含通配符 * ? 的条目）。"""
    hosts = []
    try:
        cfg = Path(os.path.expanduser("~/.ssh/config"))
        if not cfg.is_file():
            return []
        text = cfg.read_text(encoding="utf-8", errors="ignore")
    except (OSError, PermissionError):
        return []

    pat = re.compile(r"^\s*Host\s+(.+)$", re.IGNORECASE)
    for line in text.splitlines():
        m = pat.match(line)
        if not m:
            continue
        # 一行可能列多个别名
        for token in m.group(1).split():
            if "*" in token or "?" in token:
                continue
            if token not in hosts:
                hosts.append(token)
        if len(hosts) >= MAX_ITEMS:
            break
    return hosts[:MAX_ITEMS]


def _scan_git_repos():
    """在候选根位置查找含 .git 子目录的仓库，返回仓库根 basename（最多 MAX_REPOS）。"""
    names = []
    roots = list(_REPO_ROOTS)
    # 当前工作目录向上两级
    try:
        cwd = Path(os.getcwd()).resolve()
        roots.append(str(cwd))
        parent = cwd.parent
        if parent != cwd:
            roots.append(str(parent))
    except (OSError, RuntimeError):
        pass

    for root in roots:
        try:
            base = Path(os.path.expanduser(root))
            if not base.is_dir():
                continue
            for entry in os.scandir(base):
                if not entry.is_dir():
                    continue
                git_dir = Path(entry.path) / ".git"
                if git_dir.is_dir():
                    names.append(entry.name)
                if len(names) >= MAX_REPOS:
                    break
        except (OSError, PermissionError):
            pass
        if len(names) >= MAX_REPOS:
            break
    return names[:MAX_REPOS]


def scan_resources(scope="all"):
    """扫描本地资源，返回结构化 dict。

    参数:
        scope: "all"(默认) 全扫；"desktop"/"software"/"ssh"/"git" 只扫对应维度。

    返回 dict，键固定为:
        desktop    (list[str])：桌面文件名
        installed  (list[str])：已装软件名（winget 不可用则为空）
        ssh_hosts  (list[str])：~/.ssh/config 主机别名
        git_repos  (list[str])：仓库根目录名
    任何维度异常均静默降级为空列表，绝不抛出、绝不执行任意代码。
    """
    results = {"desktop": [], "installed": [], "ssh_hosts": [], "git_repos": []}
    try:
        if scope in ("all", "desktop"):
            results["desktop"] = _scan_desktop()
        if scope in ("all", "software"):
            results["installed"] = _scan_installed()
        if scope in ("all", "ssh"):
            results["ssh_hosts"] = _scan_ssh_hosts()
        if scope in ("all", "git"):
            results["git_repos"] = _scan_git_repos()
    except Exception:
        # 整体兜底：任何意外都不应中断调用方
        pass
    return results


def format_scan(results):
    """把 scan_resources 的 dict 格式化成简洁中文摘要，供 agent 直接回复。

    例如：「桌面文件 12 项、已装软件 38 款、SSH 主机 5 个、Git 仓库 9 个」，
    并各列前几个名字；某项为空写「无」。
    """
    desktop = results.get("desktop", [])
    installed = results.get("installed", [])
    ssh_hosts = results.get("ssh_hosts", [])
    git_repos = results.get("git_repos", [])

    def preview(items, n=3):
        if not items:
            return "无"
        head = items[:n]
        suffix = " 等" if len(items) > n else ""
        return "、".join(head) + suffix

    parts = [
        f"桌面文件 {len(desktop)} 项（{preview(desktop)}）",
        f"已装软件 {len(installed)} 款（{preview(installed)}）",
        f"SSH 主机 {len(ssh_hosts)} 个（{preview(ssh_hosts)}）",
        f"Git 仓库 {len(git_repos)} 个（{preview(git_repos)}）",
    ]
    return "；".join(parts) + "。"


if __name__ == "__main__":
    # 仅本地手动调试用，import 时不触发
    res = scan_resources("all")
    print(format_scan(res))
