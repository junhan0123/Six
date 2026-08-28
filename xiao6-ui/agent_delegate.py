#!/usr/bin/env python3
"""庄周 · 本地 Agent 委托（借力 Claude Code via agnes-proxy:8090）

安全模型：
- 默认关闭（AGENT_DELEGATE_ENABLED）。
- 委托 = 独立子进程跑 claude.exe（一次性 -p 打印模式），带超时强杀（杀进程树）。
- 默认 AGENT_DELEGATE_AUTO=false：每次必须显式 confirm=true 才真正执行（预览不执行）。
- 子进程继承当前环境，并注入本地 agnes-proxy 的 ANTHROPIC_BASE_URL/ANTHROPIC_AUTH_TOKEN
  （若尚未设置），使其借力本地 Agnes 大脑；不向外部泄露任何本地密钥。
"""

import glob
import os
import subprocess

import config


def _default_cli():
    if config.AGENT_DELEGATE_CLI and os.path.isfile(config.AGENT_DELEGATE_CLI):
        return config.AGENT_DELEGATE_CLI
    # 已知默认路径（Claude Code 扩展内）
    fixed = os.path.expandvars(
        r"%USERPROFILE%\.vscode\extensions\anthropic.claude-code-2.1.168-win32-x64\resources\native-binary\claude.exe"
    )
    if os.path.isfile(fixed):
        return fixed
    # 退而求其次：在 .vscode/extensions 下模糊搜索 claude.exe
    try:
        hits = glob.glob(
            os.path.expandvars(r"%USERPROFILE%\.vscode\extensions\*\resources\native-binary\claude.exe")
        )
        if hits:
            return hits[0]
    except Exception:
        pass
    # 最后退回 PATH
    return "claude"


def enabled():
    return config.AGENT_DELEGATE_ENABLED in ("1", "true", "yes")


# —— Phase C · G3 · 委托累计闸门（进程内；FAIL CLOSED）——
# 复用既有 agent_delegate 模块，不新建第二委托类。累计次数超限即拒绝，
# 防止失控的递归委托调用外部 Claude 子进程。
_delegation_count = 0


def _delegation_limit() -> int:
    try:
        return int(config.AGENT_MAX_DELEGATIONS)
    except Exception:
        return 2


def _reset_delegation_count() -> None:
    global _delegation_count
    _delegation_count = 0


def _register_delegation() -> None:
    global _delegation_count
    _delegation_count += 1


def delegation_gate_ok() -> bool:
    """是否仍可发起一次委托（未达 AGENT_MAX_DELEGATIONS 上限）。"""
    limit = _delegation_limit()
    if limit <= 0:
        return True
    return _delegation_count < limit


def delegate(task, confirm=False):
    if not enabled():
        return "本地 Agent 委托未启用（在设置中开启 AGENT_DELEGATE_ENABLED 后可用）。"
    # —— Phase C · G3 · 委托次数闸门（FAIL CLOSED）——
    if not delegation_gate_ok():
        return (
            f"⚠️ 本地 Agent 委托次数已达上限（AGENT_MAX_DELEGATIONS={_delegation_limit()}），"
            "已拒绝本次委托（FAIL CLOSED）。"
        )
    task = (task or "").strip()
    if not task:
        return "错误：未提供要委托的任务描述"
    # 默认每次确认（除非显式开启自动）
    if not confirm and config.AGENT_DELEGATE_AUTO not in ("1", "true", "yes"):
        return (
            "⚠️ 即将委托本地 Agent（Claude Code）独立执行以下任务：\n"
            f"「{task}」\n"
            "此操作会启动独立进程，可能读取/修改你的文件，并消耗外部 API 额度。\n"
            "请回复「确认执行」，或重新调用 delegate_agent 并传入 confirm=true 以继续。"
        )
    cli = _default_cli()
    timeout = max(10, min(int(config.AGENT_DELEGATE_TIMEOUT or 120), 600))
    # —— Phase C · G3 · 实际发起委托前登记一次（仅真实 spawn 才计数）——
    _register_delegation()
    env = os.environ.copy()
    # 注入本地代理（若未设置），借力 Agnes；绝不读取/转发其他密钥
    if not env.get("ANTHROPIC_BASE_URL"):
        env["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:8090"
    if not env.get("ANTHROPIC_AUTH_TOKEN"):
        env["ANTHROPIC_AUTH_TOKEN"] = "dummy-key"
    try:
        proc = subprocess.Popen(
            [cli, "-p", task, "--output-format", "text"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
    except Exception as e:
        return f"启动 Agent 失败：{e}"
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        return f"委托执行超时（>{timeout}s），已强制终止进程树。"
    if proc.returncode != 0:
        return f"Agent 退出码 {proc.returncode}：\n{(err or out or '').strip()[:2000]}"
    text = (out or "").strip()
    if len(text) > 6000:
        text = text[:6000] + f"\n…（截断，原长 {len(out)} 字符）"
    return "【本地 Agent 委托结果】\n" + text


def _kill_tree(proc):
    """超时强杀：用 taskkill 杀掉整个进程树（含 claude 拉起的 node 子进程）。"""
    try:
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
