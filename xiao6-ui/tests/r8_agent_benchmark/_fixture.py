# -*- coding: utf-8 -*-
"""共享 fixture：合成工具注册 + 清理 + 结果汇总。

合成工具临时挂到 tools.TOOL_FUNCS（经真实 execute_tool → TOOL_FUNCS 路径），
用完在 finally 恢复，确保不污染全局、不绕过任何门。
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import tools  # noqa: E402


class Probe:
    """记录被测工具收到的 args 与调用次数。"""

    def __init__(self):
        self.calls = []  # [{args, ts}]

    def make_fn(self, retval, *, raises=None, delay=0.0):
        """生成一个合成工具函数：记 args、可注入返回值/异常/延迟。"""

        def _fn(args):
            self.calls.append({"args": dict(args or {}), "ts": time.time()})
            if delay:
                time.sleep(delay)
            if raises is not None:
                raise raises
            return retval

        return _fn

    @property
    def last_args(self):
        return self.calls[-1]["args"] if self.calls else None

    @property
    def call_count(self):
        return len(self.calls)


class ToolRegistry:
    """临时注册合成工具到 tools.TOOL_FUNCS，用完恢复（支持 with 语法）。"""

    def __init__(self):
        self._added = []
        self._added_low_risk = False
        self._orig_readonly = set(tools.READONLY_TOOLS)
        self._orig_low_risk = set(tools.LOW_RISK_TOOLS)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.restore()
        return False

    def register(self, name, fn, *, readonly=False, low_risk=False):
        tools.TOOL_FUNCS[name] = fn
        self._added.append(name)
        if readonly:
            tools.READONLY_TOOLS.add(name)
        if low_risk:
            tools.LOW_RISK_TOOLS.add(name)

    def register_readonly_only(self, name):
        """只把 name 加入 READONLY_TOOLS（不注册 TOOL_FUNCS）——模拟「计划了不存在的工具」。"""
        tools.READONLY_TOOLS.add(name)
        self._added.append(name)

    def restore(self):
        for name in self._added:
            tools.TOOL_FUNCS.pop(name, None)
        tools.READONLY_TOOLS = set(self._orig_readonly)
        tools.LOW_RISK_TOOLS = set(self._orig_low_risk)
        self._added = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  -> {detail}" if detail else ""))
    return bool(cond)


def warn(name, detail=""):
    """已知问题/当前行为观察（不判 PASS/FAIL，仅记录供报告引用）。"""
    print(f"  [WARN] {name}" + (f"  -> {detail}" if detail else ""))
    return False


def section(title):
    print(f"\n===== {title} =====")
