#!/usr/bin/env python3
"""Xiao6 · 电脑动作执行层（executor.py）—— Phase 21.1

仅白名单执行（open_application / open_folder / open_file / search / copy_text）
+ 安全只读辅助（read_file 等供验证/复制源）。继承既有 RealComputerExecutor 的安全纪律：
  - 可取消（threading.Event 取消令牌）、可超时（concurrent.futures）、可审计（内存 + 可选 JSONL）
  - 结构化 result（ok/capability/target/data/error/duration_ms/timed_out/cancelled）
  - 不写文件、不删文件、不开 shell（os.startfile / 列表式 Popen，绝不用 shell=True）
  - 所有入口经 safety.assert_allowed 闸门（白名单外动作在入口即拒，双重于 capability_registry）

设计：不继承 RealComputerExecutor，避免其 _op_focus_window / _op_browser_navigate 等
超出 Phase 21 白名单的操作被误调用；白名单由 safety 层统一把守。
"""
from __future__ import annotations

import os
import sys
import io
import time
import json
import threading
import subprocess
import concurrent.futures


class ComputerExecutor:
    def __init__(self, timeout: float = 30.0, max_read_bytes: int = 200_000,
                 audit_path: str = None, max_search_results: int = 200):
        self.timeout = timeout
        self.max_read_bytes = max_read_bytes
        self.audit_path = audit_path
        self.max_search_results = max_search_results
        self.audit_log = []

    # —— 结构化结果构造 ——
    def _mk(self, ok, data=None, error=None, extra=None):
        r = {"ok": ok, "capability": None, "target": None,
             "data": data if data is not None else {}, "error": error}
        if extra:
            r.update(extra)
        return r

    # —— 入口：白名单闸门 + 取消/超时包装 ——
    def execute(self, action, cancel: threading.Event = None):
        from .safety import assert_allowed
        cap = action.capability
        try:
            assert_allowed(cap)  # 白名单 / halt / 风险 闸门（非白名单在此即拒）
        except Exception as e:
            res = self._mk(False, error=f"安全拒绝: {e}")
            res["capability"] = cap
            res["target"] = action.target
            self._audit(action, res, 0.0)
            return res

        start = time.time()
        cancel = cancel or threading.Event()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(self._dispatch, action, cancel)
                res = fut.result(timeout=self.timeout)
        except concurrent.futures.TimeoutError:
            cancel.set()
            res = self._mk(False, error=f"执行超时（>{self.timeout}s）",
                           extra={"timed_out": True, "cancelled": False,
                                  "duration_ms": (time.time() - start) * 1000})
        except Exception as e:
            res = self._mk(False, error=f"执行异常: {e}")
        res["capability"] = cap
        res["target"] = action.target
        res["duration_ms"] = round((time.time() - start) * 1000, 2)
        res.setdefault("timed_out", False)
        res.setdefault("cancelled", False)
        self._audit(action, res, res["duration_ms"])
        return res

    def _dispatch(self, action, cancel):
        fn = getattr(self, "_op_" + action.capability, None)
        if fn is None:
            return self._mk(False, error="未实现的白名单操作: " + action.capability)
        return fn(action, cancel)

    # —— 白名单操作 ——
    def _op_open_application(self, action, cancel):
        t = action.target
        if not t:
            return self._mk(False, error="open_application 需要 target（应用路径/命令）")
        try:
            if sys.platform.startswith("win"):
                os.startfile(t)            # 不经 shell
            else:
                subprocess.Popen([t])      # 列表式，不经 shell
            return self._mk(True, data={"launched": t})
        except Exception as e:
            return self._mk(False, error=f"打开应用失败: {e}")

    def _op_open_folder(self, action, cancel):
        t = action.target
        if not t:
            return self._mk(False, error="open_folder 需要 target（文件夹路径）")
        try:
            if sys.platform.startswith("win"):
                os.startfile(t)
            else:
                subprocess.Popen(["xdg-open", t])
            return self._mk(True, data={"folder": t})
        except Exception as e:
            return self._mk(False, error=f"打开文件夹失败: {e}")

    def _op_open_file(self, action, cancel):
        t = action.target
        if not t:
            return self._mk(False, error="open_file 需要 target（文件路径）")
        try:
            if sys.platform.startswith("win"):
                os.startfile(t)
            else:
                subprocess.Popen(["xdg-open", t])
            return self._mk(True, data={"file": t})
        except Exception as e:
            return self._mk(False, error=f"打开文件失败: {e}")

    def _op_search(self, action, cancel):
        params = action.parameters or {}
        root = params.get("root") or action.target or "."
        query = (params.get("query") or "").lower()
        hits = []
        try:
            for dirpath, _dirnames, filenames in os.walk(root):
                if cancel and cancel.is_set():
                    break
                for fn in filenames:
                    if query and query not in fn.lower():
                        continue
                    hits.append(os.path.join(dirpath, fn))
                    if len(hits) >= self.max_search_results:
                        break
                if len(hits) >= self.max_search_results:
                    break
        except Exception as e:
            return self._mk(False, error=f"搜索失败: {e}")
        return self._mk(True, data={"query": query, "root": root,
                                    "count": len(hits), "hits": hits[:self.max_search_results]})

    def _op_copy_text(self, action, cancel):
        params = action.parameters or {}
        text = params.get("text")
        if not text and action.target:
            # 从文件读取前 N 字符作为副本（只读，不修改源文件）
            try:
                with open(action.target, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read(self.max_read_bytes)
            except Exception as e:
                return self._mk(False, error=f"读取复制源失败: {e}")
        if not text:
            return self._mk(False, error="copy_text 需要 text 参数或可读的 target 文件")
        try:
            self._to_clipboard(text)
            return self._mk(True, data={"chars": len(text)})
        except Exception as e:
            return self._mk(False, error=f"复制失败: {e}")

    # —— 剪贴板（优先 pyperclip，回退 Windows ctypes；不修改任何文件）——
    def _to_clipboard(self, text):
        try:
            import pyperclip
            pyperclip.copy(text)
            return
        except Exception:
            pass
        if sys.platform.startswith("win"):
            try:
                import ctypes
                cf = ctypes.windll.user32
                if not cf.OpenClipboard(0):
                    raise RuntimeError("OpenClipboard 失败")
                try:
                    cf.EmptyClipboard()
                    encoded = text.encode("utf-16-le")
                    h = ctypes.windll.kernel32.GlobalAlloc(0x42, len(encoded) + 2)
                    p = ctypes.windll.kernel32.GlobalLock(h)
                    ctypes.cdll.msvcrt.memcpy(p, encoded, len(encoded))
                    ctypes.windll.kernel32.GlobalUnlock(h)
                    cf.SetClipboardData(13, h)  # CF_UNICODETEXT
                finally:
                    cf.CloseClipboard()
                return
            except Exception:
                raise
        raise RuntimeError("无可用剪贴板后端（需 pyperclip 或 Windows）")

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
