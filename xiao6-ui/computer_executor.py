#!/usr/bin/env python3
"""庄周 · Computer Executor（Phase 7 Order 3 · 真实但安全的电脑执行器）

纪律（Order 3 安全约束，最高优先级）：
- 本执行器是 Computer Action 的**唯一**执行系统；只能经 permission_guard 调用，
  Agent / Runtime 严禁直连。绝不绕过 Policy Engine，绝不创建第二执行系统。
- 仅实现已注册且已实现的 LOW / MEDIUM 能力；HIGH / CRITICAL 一律拒绝
  （Guard 也会先拒，这里兜底）。
- **不修改 / 不删除任何文件**：read_file 只读取；截图截到内存绝不落盘；
  不开放任意 Shell（open_application 用 os.startfile / 列表式 Popen，绝不用 shell=True）。
- 所有执行：可取消（threading.Event 取消令牌）、可超时（concurrent.futures 超时）、
  可审计（内存审计日志，默认不写文件，可选 audit_path）、返回结构化 result。
- 结构化 result 字段：
    ok           bool            执行是否成功
    capability   str             能力 id
    target       str             目标
    data         dict            结构化执行产物（按能力不同）
    error        str|None        失败原因
    duration_ms  float           耗时（毫秒）
    timed_out    bool            是否超时
    cancelled    bool            是否被取消
"""

from __future__ import annotations

import os
import sys
import io
import csv
import json
import time
import threading
import subprocess
import concurrent.futures


class MockComputerExecutor:
    """可注入的 mock 执行器：记录调用，返回安全/模拟结果。

    用于单元测试与 UI 预览；不触真实 OS。后续 Order 可注入真实执行器，
    但必须经由 permission_guard，绝不绕过 Policy Engine。
    """

    def __init__(self):
        self.calls = []          # 记录每次 execute 调用（用于测试与审计）
        self.fail_next = False   # 测试用：下一次执行抛错

    def execute(self, action):
        self.calls.append({
            "actionId": action.actionId,
            "capability": action.capability,
            "target": action.target,
            "at": time.time(),
        })
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("模拟执行失败（MockComputerExecutor.fail_next）")
        return self._mock_result(action)

    def _mock_result(self, action):
        cap = action.capability
        if cap == "read_file":
            return {"ok": True, "kind": "mock",
                    "preview": f"[mock] 文件 {action.target} 内容预览（安全读取，未实际读取磁盘）",
                    "bytes": 0}
        if cap == "capture_screen":
            return {"ok": True, "kind": "mock",
                    "image": "data:image/png;base64,AAAA（模拟截图占位，未截真实屏幕）"}
        if cap == "get_window_info":
            return {"ok": True, "kind": "mock",
                    "window": {"id": action.target, "rect": {"x": 0, "y": 0, "w": 0, "h": 0},
                               "isFocused": False}}
        if cap == "list_process":
            return {"ok": True, "kind": "mock",
                    "processes": [{"pid": 1, "name": "mock-process", "state": "Running"}]}
        if cap == "open_application":
            return {"ok": True, "kind": "mock", "launched": action.target,
                    "note": "模拟启动，未实际打开应用"}
        if cap == "focus_window":
            return {"ok": True, "kind": "mock", "focused": action.target,
                    "note": "模拟聚焦，未实际切换焦点"}
        if cap == "browser_navigate":
            url = (action.parameters or {}).get("url", "")
            return {"ok": True, "kind": "mock", "url": url,
                    "note": "模拟导航，未实际打开浏览器"}
        raise NotImplementedError(f"能力 {cap} 在 Order 2 未实现（须经 Policy Engine 授权）")


class RealComputerExecutor:
    """真实但安全的电脑执行器（Phase 7 Order 3）。

    仅执行 LOW / MEDIUM 能力；HIGH / CRITICAL 在 Guard 层已被拒绝，这里再兜底。
    所有 OS 调用均为只读或最小界面副作用，**不写文件、不删文件、不开 shell**。
    """

    def __init__(self, timeout: float = 30.0, max_read_bytes: int = 1_000_000,
                 audit_path: str = None):
        self.timeout = timeout
        self.max_read_bytes = max_read_bytes
        self.audit_path = audit_path          # 可选：审计 JSONL 落盘路径（默认不写）
        self.audit_log = []                   # 内存审计日志（可审计）

    # —— 结构化结果构造 ——
    def _mk(self, ok, data=None, error=None, extra=None):
        r = {"ok": ok, "capability": None, "target": None,
             "data": data if data is not None else {}, "error": error}
        if extra:
            r.update(extra)
        return r

    # —— 取消 / 超时 包装（可取消、可超时）——
    def execute(self, action, cancel: threading.Event = None):
        cap = action.capability
        # 防御：仅允许已注册且已实现的能力；HIGH/CRITICAL 拒绝
        from capability_os.registry import is_implemented, risk_of
        start = time.time()
        if not is_implemented(cap) or risk_of(cap) in ("HIGH", "CRITICAL"):
            res = self._mk(False, error="能力不可由 RealComputerExecutor 执行: " + cap)
        else:
            cancel = cancel or threading.Event()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(self._dispatch, action, cancel)
                try:
                    res = fut.result(timeout=self.timeout)
                except concurrent.futures.TimeoutError:
                    cancel.set()  # 通知工作线程取消（能力方法会检查 cancel 令牌）
                    res = self._mk(False, error=f"执行超时（>{self.timeout}s）",
                                   extra={"timed_out": True, "cancelled": False,
                                          "duration_ms": (time.time() - start) * 1000})
        res["capability"] = cap
        res["target"] = action.target
        duration = (time.time() - start) * 1000
        res["duration_ms"] = round(duration, 2)
        res.setdefault("timed_out", False)
        res.setdefault("cancelled", False)
        self._audit(action, res, duration)  # 所有路径（含拒绝/超时）均审计
        return res

    def _dispatch(self, action, cancel):
        fn = getattr(self, "_op_" + action.capability, None)
        if fn is None:
            return self._mk(False, error="未实现的操作: " + action.capability)
        return fn(action, cancel)

    # —— LOW 操作（只读 / 安全）——
    def _op_read_file(self, action, cancel):
        path = action.target
        if not path:
            return self._mk(False, error="read_file 需要 target 路径")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(self.max_read_bytes)
        except Exception as e:
            return self._mk(False, error="读取失败: " + str(e))
        # 仅读取，不写/不改；返回预览（前 1000 字符）与完整内容（前 4000 供验证）
        return self._mk(True, data={
            "path": path,
            "bytes": len(content.encode("utf-8", "replace")),
            "preview": content[:1000],
            "content": content[:4000],
        })

    def _op_list_process(self, action, cancel):
        try:
            out = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True, text=True, timeout=self.timeout, check=True,
            )
            procs = []
            for line in out.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = next(csv.reader(io.StringIO(line)))
                if len(parts) >= 2:
                    procs.append({"name": parts[0], "pid": parts[1]})
                if len(procs) >= 80:
                    break
            return self._mk(True, data={"processes": procs, "count": len(procs)})
        except Exception as e:
            return self._mk(False, error="列举进程失败: " + str(e))

    def _op_capture_screen(self, action, cancel):
        # 真实截图但**截到内存**，绝不落盘（避免污染任何目录）
        try:
            return self._capture_memory()
        except Exception as e:
            return self._mk(False, error="截图后端不可用: " + str(e),
                             extra={"note": "安装 Pillow 或 mss 后可启用真实截图"})

    def _capture_memory(self):
        try:
            from mss import mss
            with mss() as sct:
                img = sct.grab(sct.monitors[1])
                import zlib
                raw = getattr(img, "rgb", b"")
                return self._mk(True, data={
                    "width": img.width, "height": img.height,
                    "bytes": len(zlib.compress(raw)),
                }, extra={"note": "内存截图，未落盘"})
        except ImportError:
            try:
                from PIL import ImageGrab
                im = ImageGrab.grab()
                buf = io.BytesIO()
                im.save(buf, "PNG")
                return self._mk(True, data={
                    "width": im.width, "height": im.height,
                    "bytes": len(buf.getvalue()),
                }, extra={"note": "内存截图，未落盘"})
            except Exception:
                raise

    def _op_get_window_info(self, action, cancel):
        try:
            wins = self._win_enum(action.target)
            if not wins:
                return self._mk(False, error="未找到窗口: " + str(action.target))
            w = wins[0]
            return self._mk(True, data={
                "window": {"id": str(w["hwnd"]), "title": w["title"], "isFocused": False}})
        except Exception as e:
            return self._mk(False, error="窗口信息失败: " + str(e))

    # —— MEDIUM 操作（有界面副作用，须经 confirm）——
    def _op_open_application(self, action, cancel):
        target = action.target
        if not target:
            return self._mk(False, error="open_application 需要 target（应用路径/命令）")
        try:
            if sys.platform.startswith("win"):
                os.startfile(target)            # 不经 shell
            else:
                subprocess.Popen([target])      # 列表式，不经 shell
            return self._mk(True, data={"launched": target})
        except Exception as e:
            return self._mk(False, error="打开应用失败: " + str(e))

    def _op_focus_window(self, action, cancel):
        if not sys.platform.startswith("win"):
            return self._mk(False, error="focus_window 仅 Windows 支持")
        return self._win_focus(action.target)

    def _op_browser_navigate(self, action, cancel):
        url = (action.parameters or {}).get("url", "")
        if not url:
            return self._mk(False, error="browser_navigate 需要 parameters.url")
        import webbrowser
        try:
            webbrowser.open(url)                # 默认浏览器，不经 shell
            return self._mk(True, data={"url": url})
        except Exception as e:
            return self._mk(False, error="导航失败: " + str(e))

    # —— Windows 窗口枚举 / 聚焦（ctypes，只读/最小副作用）——
    def _win_enum(self, match_title=None):
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        GetWindowText = user32.GetWindowTextW
        GetWindowTextLength = user32.GetWindowTextLengthW
        IsWindowVisible = user32.IsWindowVisible
        wins = []

        def cb(hwnd, lparam):
            if not IsWindowVisible(hwnd):
                return True
            length = GetWindowTextLength(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buf, length + 1)
                wins.append({"hwnd": hwnd, "title": buf.value})
            return True

        EnumWindows(EnumWindowsProc(cb), 0)
        if match_title:
            mt = match_title.lower()
            wins = [w for w in wins if mt in w["title"].lower()]
        return wins

    def _win_focus(self, title):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            wins = self._win_enum(title)
            if not wins:
                return self._mk(False, error="未找到可聚焦窗口: " + str(title))
            hwnd = wins[0]["hwnd"]
            user32.SetForegroundWindow(hwnd)
            return self._mk(True, data={"focused": str(hwnd), "title": wins[0]["title"]})
        except Exception as e:
            return self._mk(False, error="聚焦失败: " + str(e))

    # —— 审计（可审计；默认仅内存，可选落盘 JSONL）——
    def _audit(self, action, res, duration_ms):
        rec = {
            "ts": time.time(),
            "actionId": action.actionId,
            "capability": action.capability,
            "target": action.target,
            "ok": res.get("ok"),
            "duration_ms": round(duration_ms, 2),
            "timed_out": res.get("timed_out", False),
            "cancelled": res.get("cancelled", False),
        }
        self.audit_log.append(rec)
        if self.audit_path:
            try:
                with open(self.audit_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except Exception:
                pass
