#!/usr/bin/env python3
"""Xiao6 · 电脑动作验证层（verifier.py）—— Phase 21.1

复用 verification.VerificationLayer（Action → Observe → Verify 闭环），补充白名单
算子的 _verify_* 规则。

修复（继承而非组合）：原实现将 VerificationLayer 作为 self._base 组合，verify() 委托
到 self._base.verify()，而 self._base 是 VerificationLayer 实例、并不持有本类的
_verify_open_folder/_verify_search 等方法 —— 导致白名单验证规则成为死代码，
os.path.isdir 等真实复核被绕过。改为继承 VerificationLayer 后，verify() 内
getattr(self, "_verify_<cap>") 能同时命中基类通用规则与本类白名单规则。

纪律（沿用 verification）：不重复执行任何 OS 动作，只读取观测与执行 result。
"""
from __future__ import annotations

import os
from verification import VerificationLayer


class ComputerVerifier(VerificationLayer):
    """验证层：继承 VerificationLayer 以复用通用 verify 调度与既有 _verify_*。"""

    def __init__(self, observer=None):
        super().__init__(observer=observer)

    # —— 白名单算子验证规则（补充）——
    def _verify_open_folder(self, action, data, obs):
        if not data.get("folder"):
            return (False, "未返回打开的文件夹")
        if not os.path.isdir(action.target or ""):
            return (False, "目标目录不存在: " + str(action.target))
        return (True, "文件夹已打开: " + str(action.target))

    def _verify_open_file(self, action, data, obs):
        if not data.get("file"):
            return (False, "未返回打开的文件")
        if not os.path.isfile(action.target or ""):
            return (False, "目标文件不存在: " + str(action.target))
        return (True, "文件已打开: " + str(action.target))

    def _verify_search(self, action, data, obs):
        return (True, "搜索完成，命中 %d 项" % data.get("count", 0))

    def _verify_copy_text(self, action, data, obs):
        if not data.get("chars"):
            return (False, "未复制任何文本")
        return (True, "已复制 %d 字符到剪贴板" % data.get("chars", 0))
