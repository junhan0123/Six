#!/usr/bin/env python3
"""小6 · 持久 shell 会话（移植自参考实现 persistent-shell）

价值：维护一个长驻 shell 子进程，跨命令保持工作目录与环境变量，
避免每条命令冷启动 powershell 的 ~550ms 开销；同时让 `cd` / `$env:FOO=`
在会话内持续生效，像真终端一样连续干活。

实现要点（对应参考实现设计）：
- Windows 走 `powershell.exe -NoLogo -NoProfile -Command -`，stdin 喂命令，
  用唯一哨兵标记（`Write-Output "SENT_xxx:$LASTEXITCODE"` + stderr 哨兵）判结束并取退出码。
- 中文不乱码：进程启动即 `chcp 65001` + 设 UTF8 编码；命令经 UTF8→base64 经 stdin 传入（纯 ASCII）。
- 互斥：同一时刻只跑一条；忙时降级到独立子进程慢路径，不影响持久会话正确性。
- 软超时兜底：命令迟迟不结束 → 杀掉持久 shell 重建并返回超时提示，下次命令自动拉起。
- 读取用二进制管道 + read1()（有数据即返回，不等满缓冲区）+ 增量 UTF-8 解码，正确处理长驻进程与多字节字符。
- 任何异常都降级/兜底，绝不抛到主链路。
"""
import base64
import codecs
import os
import re
import subprocess
import threading
import uuid

IS_WIN = os.name == "nt"


def _no_window_flag():
    # Windows 上隐藏控制台窗口（避免弹黑框）；其它平台忽略
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


_STATE = {
    "proc": None,
    "ready": False,
    "ready_id": None,
    "ready_event": None,
    "busy": False,
    "lock": threading.Lock(),
    "stdout_buf": "",
    "stderr_buf": "",
    "current": None,      # {"out_re", "err_mark", "event", "result"}
    "cwd": None,          # 逻辑 cwd（仅用于展示 / 显式 cwd 时 Set-Location）
    "history": [],
}


def _prelude():
    return (
        "chcp 65001 > $null\n"
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8\n"
        "[Console]::InputEncoding=[Text.Encoding]::UTF8\n"
        "$OutputEncoding=[Text.Encoding]::UTF8\n"
        "$ProgressPreference='SilentlyContinue'\n"
    )


def _sandbox_root():
    try:
        import config
        return config.SANDBOX_ROOT
    except Exception:
        return os.getcwd()


# ── 读线程：二进制管道 + read1() 有数据即返回，增量解码后灌入缓冲 ──
def _pump(stream, bufname):
    dec = codecs.getincrementaldecoder("utf-8")(errors="replace")
    try:
        while True:
            chunk = stream.read1(65536)
            if not chunk:
                break
            text = dec.decode(chunk)
            if text:
                _on_data(bufname, text)
    except Exception:
        pass


def _on_data(bufname, chunk):
    with _STATE["lock"]:
        _STATE[bufname] += chunk
        # ready 哨兵检测（启动阶段，current 为空）
        if not _STATE["ready"] and _STATE["ready_id"]:
            ridx = _STATE["stdout_buf"].find(_STATE["ready_id"])
            if ridx != -1:
                _STATE["stdout_buf"] = _STATE["stdout_buf"][ridx + len(_STATE["ready_id"]):]
                _STATE["ready"] = True
                if _STATE["ready_event"]:
                    _STATE["ready_event"].set()
        _try_complete_locked()


def _try_complete_locked():
    cur = _STATE["current"]
    if not cur:
        return
    m = re.search(cur["out_re"], _STATE["stdout_buf"])
    if not m:
        return
    err_idx = _STATE["stderr_buf"].find(cur["err_mark"])
    if err_idx == -1:
        return
    exit_code = int(m.group(1))
    stdout = _STATE["stdout_buf"][: m.start()]
    stderr = _STATE["stderr_buf"][:err_idx]
    _STATE["stdout_buf"] = _STATE["stdout_buf"][m.end():]
    _STATE["stderr_buf"] = _STATE["stderr_buf"][err_idx + len(cur["err_mark"]):]
    _STATE["current"] = None
    _STATE["busy"] = False
    cur["result"] = {"exit": exit_code, "stdout": stdout, "stderr": stderr}
    cur["event"].set()


def _kill():
    with _STATE["lock"]:
        proc = _STATE["proc"]
        _STATE["proc"] = None
        _STATE["ready"] = False
        _STATE["ready_id"] = None
        if _STATE["ready_event"]:
            _STATE["ready_event"].clear()
        _STATE["current"] = None
        _STATE["busy"] = False
        _STATE["stdout_buf"] = ""
        _STATE["stderr_buf"] = ""
    if proc:
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def _start():
    _kill()
    root = _sandbox_root()
    try:
        if IS_WIN:
            proc = subprocess.Popen(
                ["powershell.exe", "-NoLogo", "-NoProfile", "-Command", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=root,
                bufsize=-1,
                creationflags=_no_window_flag(),
            )
        else:
            proc = subprocess.Popen(
                ["bash", "--norc", "-i"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=root,
                bufsize=-1,
            )
    except Exception:
        return
    with _STATE["lock"]:
        _STATE["proc"] = proc
        _STATE["ready"] = False
        _STATE["ready_id"] = (
            "READY_" + uuid.uuid4().hex[:12] + "\r\n"
            if IS_WIN
            else "READY_" + uuid.uuid4().hex[:12] + "\n"
        )
        _STATE["ready_event"] = threading.Event()
        _STATE["cwd"] = root
    threading.Thread(target=_pump, args=(proc.stdout, "stdout_buf"), daemon=True).start()
    threading.Thread(target=_pump, args=(proc.stderr, "stderr_buf"), daemon=True).start()
    try:
        if IS_WIN:
            proc.stdin.write((_prelude() + 'Write-Output "' + _STATE["ready_id"].rstrip("\r\n") + '"\n').encode("utf-8"))
        else:
            proc.stdin.write(('echo "' + _STATE["ready_id"].rstrip("\n") + '"\n').encode("utf-8"))
        proc.stdin.flush()
    except Exception:
        _kill()


def _ensure_started():
    with _STATE["lock"]:
        ok = _STATE["proc"] is not None and _STATE["proc"].poll() is None
    if not ok:
        _start()


def _fallback(command, cwd, timeout):
    """独立子进程慢路径：持久 shell 忙/不可用时降级，保证命令仍能执行。"""
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd or _STATE["cwd"] or _sandbox_root(),
            capture_output=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "exit": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "fallback": True,
        }
    except subprocess.TimeoutExpired:
        return {"exit": -1, "stdout": "", "stderr": f"执行超时（{timeout}s）", "fallback": True}
    except Exception as e:
        return {"exit": -1, "stdout": "", "stderr": f"执行失败：{e}", "fallback": True}


def run_in_session(command, cwd=None, timeout=60, record=True):
    """在持久 shell 上执行一条命令，保持 cwd/环境变量跨命令生效。

    - cwd 为 None 时不强制切换，沿用持久进程当前目录（实现会话内 `cd` 持续生效）。
    - 返回 {"exit", "stdout", "stderr", "fallback"?(bool)}。
    """
    timeout = max(5, min(int(timeout or 60), 180))
    # 同步抢占 busy：在任何 IO/等待之前，防并发调用交错写入共享 stdin
    with _STATE["lock"]:
        if _STATE["busy"]:
            return _fallback(command, cwd, timeout)
        _STATE["busy"] = True
    try:
        _ensure_started()
        ev = _STATE["ready_event"]
        if ev is None or not ev.wait(timeout=10):
            with _STATE["lock"]:
                _STATE["busy"] = False
            return {"exit": -1, "stdout": "", "stderr": "持久 shell 启动超时，请稍后重试"}
        with _STATE["lock"]:
            proc = _STATE["proc"]
            alive = proc is not None and proc.poll() is None
        if not alive:
            with _STATE["lock"]:
                _STATE["busy"] = False
            return _fallback(command, cwd, timeout)
        # 构造哨兵命令
        sid = "SENT_" + uuid.uuid4().hex[:12]
        out_re = re.compile(re.escape(sid) + r":(-?\d+)\r?\n")
        err_mark = (sid + "ERR\r\n") if IS_WIN else (sid + "ERR\n")
        event = threading.Event()
        current = {"out_re": out_re, "err_mark": err_mark, "event": event, "result": None}
        with _STATE["lock"]:
            _STATE["current"] = current
        try:
            target_cwd = cwd or _STATE["cwd"] or _sandbox_root()
            if IS_WIN:
                cmd_b64 = base64.b64encode(command.encode("utf-8")).decode()
                cwd_b64 = base64.b64encode(target_cwd.encode("utf-8")).decode()
                payload = "$global:LASTEXITCODE=0\n"
                if cwd:
                    payload += (
                        "Set-Location -LiteralPath "
                        "([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('%s')))\n" % cwd_b64
                    )
                payload += (
                    "Invoke-Expression "
                    "([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('%s')))\n" % cmd_b64
                    + 'Write-Output "%s:$LASTEXITCODE"\n' % sid
                    + '[Console]::Error.WriteLine("%sERR")\n' % sid
                    + "[Console]::Out.Flush()\n[Console]::Error.Flush()\n"
                )
            else:
                payload = ""
                if cwd:
                    import shlex
                    payload += "cd %s\n" % shlex.quote(target_cwd)
                payload += (
                    command + "\n"
                    + 'echo "%s:$?"\n' % sid
                    + 'echo "%sERR" >&2\n' % sid
                )
            proc.stdin.write(payload.encode("utf-8"))
            proc.stdin.flush()
        except Exception as e:
            with _STATE["lock"]:
                _STATE["busy"] = False
                _STATE["current"] = None
            return {"exit": -1, "stdout": "", "stderr": f"写入持久 shell 失败：{e}"}
        if not event.wait(timeout=timeout):
            _kill()  # 软超时：杀掉重建
            return {"exit": -1, "stdout": "", "stderr": f"命令执行超时（{timeout}s），已重置持久 shell"}
        result = current["result"] or {"exit": -1, "stdout": "", "stderr": "未知错误"}
        with _STATE["lock"]:
            if record:
                _STATE["history"].append(command)
                if len(_STATE["history"]) > 100:
                    _STATE["history"].pop(0)
            if cwd:
                _STATE["cwd"] = cwd
        return result
    except Exception as e:
        with _STATE["lock"]:
            _STATE["busy"] = False
            _STATE["current"] = None
        return {"exit": -1, "stdout": "", "stderr": f"持久 shell 异常：{e}"}


def session_state():
    with _STATE["lock"]:
        proc = _STATE["proc"]
        alive = proc is not None and proc.poll() is None
        ready = _STATE.get("ready", False)
        busy = _STATE["busy"]
        hist = list(_STATE["history"])
        cwd = _STATE["cwd"]
    platform = "Windows (PowerShell)" if IS_WIN else "Linux/macOS (bash)"
    if not alive:
        return "持久 shell 会话：未启动 / 已退出（平台 %s）。发送任意命令会自动拉起一个干净的 shell。" % platform
    lines = [
        "持久 shell 会话状态：%s%s"
        % ("就绪" if ready else "启动中", "（有命令执行中）" if busy else ""),
        "平台：%s" % platform,
        "沙箱根：%s" % _sandbox_root(),
        "已执行命令数：%d" % len(hist),
    ]
    if cwd:
        lines.append("会话目录：%s" % cwd)
    if hist:
        lines.append("上一条命令：%s" % hist[-1][:120])
    # 实时取当前目录（命令内 cd 后也能反映）
    try:
        res = run_in_session("Get-Location" if IS_WIN else "pwd", timeout=5, record=False)
        if res and res.get("exit") == 0 and res.get("stdout"):
            lines.append("当前目录：" + res["stdout"].strip().splitlines()[-1])
    except Exception:
        pass
    return "\n".join(lines)


def reset_session():
    _kill()
    return "持久 shell 会话已重置（进程已终止，下条命令会重新拉起一个干净的 shell）。"


def shutdown():
    _kill()
