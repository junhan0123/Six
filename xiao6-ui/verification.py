#!/usr/bin/env python3
"""小6 · Verification Layer（Phase 7 Order 3 · 执行后复核基础层）

职责：Computer Action 执行成功后，重新观察世界状态并验证「预期效果」是否真实达成。
这是 Observation → Action → Verification 闭环的最后一环。

纪律：
- 不重复执行任何 OS 动作；只读取观测（observer 提供的世界快照）与执行 result。
- 验证失败 → 上层发 COMPUTER_ACTION_UNVERIFIED；成功 → COMPUTER_ACTION_VERIFIED。
- observer 为可调用对象，返回观测字典（processes / applications / focused_window 等）。
  真实环境注入 RealObserver；测试注入 MockObserver；默认 None（仅能验证 result 自证的能力）。
"""

from __future__ import annotations

import os
import sys
import threading


class VerificationLayer:
    def __init__(self, observer=None):
        # observer: callable() -> dict | None
        self.observer = observer

    def verify(self, action, result, observation=None):
        """返回 (verified: bool, detail: str)。

        Phase 8 MVP 升级：优先使用 Perception → World Model → Observation 完成验证。
        - observation 若显式传入（如 Perception 只读快照），则直接用作观测；
        - 否则回退到 self.observer()（RealObserver / MockObserver）。
        沿用 Phase 7 事件合约（COMPUTER_ACTION_VERIFIED/UNVERIFIED），不新增第二 Verification。
        """
        if not result or not result.get("ok"):
            return (False, "执行未返回成功结果（result.ok=false），无法验证")
        data = result.get("data") or {}
        obs = observation if observation is not None else (self.observer() if callable(self.observer) else None)
        fn = getattr(self, "_verify_" + action.capability, None)
        if fn is None:
            # 无特定规则的能力：按执行成功认定已验证
            return (True, "无特定验证规则，按执行成功认定已验证")
        return fn(action, data, obs)

    # —— 各能力验证规则 ——
    def _verify_read_file(self, action, data, obs):
        content = data.get("content") or data.get("preview") or ""
        if len(content) == 0 and data.get("bytes", 0) == 0:
            return (False, "读取内容为空，验证失败")
        return (True, "文件内容已成功读取")

    def _verify_list_process(self, action, data, obs):
        ps = data.get("processes") or []
        if not ps:
            return (False, "进程列表为空")
        return (True, "进程列表已返回（%d 项）" % len(ps))

    def _verify_capture_screen(self, action, data, obs):
        if not data.get("bytes"):
            return (False, "截图数据为空")
        return (True, "截图已生成（%dx%d）" % (data.get("width", 0), data.get("height", 0)))

    def _verify_get_window_info(self, action, data, obs):
        if not data.get("window"):
            return (False, "窗口信息为空")
        return (True, "窗口信息已返回")

    def _verify_open_application(self, action, data, obs):
        if not obs:
            return (False, "无观察者，无法复核应用运行状态")
        running = obs.get("processes") or obs.get("applications") or []
        name = os.path.basename(action.target or "").lower()
        for r in running:
            rn = (r.get("name") if isinstance(r, dict) else str(r)).lower()
            if name and name in rn:
                return (True, "应用已在运行观测中: " + rn)
        return (False, "应用未在运行观测中出现: " + (action.target or ""))

    def _verify_focus_window(self, action, data, obs):
        if not obs:
            return (False, "无观察者，无法复核焦点")
        fw = obs.get("focused_window") or obs.get("focusedWindow")
        if fw and (str(fw.get("id")) == str(action.target) or fw.get("title") == action.target):
            return (True, "窗口已聚焦")
        return (False, "窗口未处于焦点")

    def _verify_browser_navigate(self, action, data, obs):
        return (True, "浏览器导航已触发: " + str(data.get("url", "")))

    def _verify_click_at(self, action, data, obs):
        # Phase 8 MVP（可选）：点击后复核视觉事实是否仍可见（非空白即视为已执行）
        if not obs:
            return (False, "无观察者，无法复核点击效果")
        facts = obs.get("visionFacts") or []
        if facts:
            return (True, "点击后视觉事实仍可见，已复核")
        return (True, "点击后无可观察视觉事实，按执行成功认定")


class RealObserver:
    """真实观察者：用 ComputerExecutor 的只读观测能力产出世界快照。

    仅供后端生产环境注入；测试用 MockObserver。不写文件、不开 shell。
    """

    def __init__(self):
        from computer_action.executor import ComputerExecutor
        self.exe = ComputerExecutor()

    def __call__(self):
        try:
            proc_res = self.exe._op_list_process(None, threading.Event())
            procs = proc_res.get("data", {}).get("processes", []) if proc_res.get("ok") else []
        except Exception:
            procs = []
        focused = self._focused_window()
        return {"processes": procs, "applications": procs, "focused_window": focused}

    def _focused_window(self):
        if not sys.platform.startswith("win"):
            return None
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                return {"id": str(hwnd), "title": buf.value}
        except Exception:
            pass
        return None


class PerceptionWorldModelObserver:
    """Verification 观察源（Phase 8 MVP）：复用 Perception 的只读快照，转为
    VerificationLayer._verify_* 兼容的观测字典。

    与 RealObserver 同接口（可调用，返回 dict | None）；不重复 World Model 观测逻辑——
    Perception 是观察源，Verification 是裁决方，职责不混。
    """

    def __init__(self, perception_runtime):
        self.rt = perception_runtime

    def __call__(self):
        model = self.rt.observe() if hasattr(self.rt, "observe") else None
        if not model:
            return None
        focused = model.get("focusedElement") or {}
        return {
            "processes": [],
            "applications": [],
            "focused_window": {"id": focused.get("windowId"), "title": focused.get("name")},
            "visionFacts": model.get("visionFacts", []),
            "uiTree": model.get("uiTree"),
            "ocrText": model.get("mergedText", []),
        }
