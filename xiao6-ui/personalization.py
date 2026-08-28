#!/usr/bin/env python3
"""庄周 · 个性化学习（模块5）：基于用户习惯优化回复。

- 记录每次对话的文本信号：高频意图关键词、活跃时段。
- 汇总为简洁中文习惯画像，注入系统提示词，使回复随使用习惯优化。
- 数据存于本地 habits.json，绝不外传。
"""

import json
import os
import threading
import time
from collections import Counter

_HABITS_PATH = os.path.join(os.path.dirname(__file__), "habits.json")
_lock = threading.Lock()

# 常见意图关键词（用于提炼用户高频关注点）
_INTENT_WORDS = [
    "天气", "新闻", "热点", "提醒", "笔记", "日程", "任务", "搜索", "翻译",
    "代码", "股票", "健康", "日历", "邮件", "总结", "计划", "查询", "庄周",
]

_state = {"cmds": Counter(), "hours": Counter(), "updated": 0}


def _load():
    global _state
    try:
        with open(_HABITS_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        _state["cmds"] = Counter(d.get("cmds", {}))
        _state["hours"] = Counter(d.get("hours", {}))
        _state["updated"] = d.get("updated", 0)
    except Exception:
        pass


def _save():
    try:
        with open(_HABITS_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "cmds": dict(_state["cmds"].most_common(30)),
                    "hours": dict(_state["hours"]),
                    "updated": _state["updated"],
                },
                f,
                ensure_ascii=False,
            )
    except Exception:
        pass


def record(text):
    """记录一条用户对话信号（best-effort，绝不抛错）。"""
    if not text or not isinstance(text, str):
        return
    text = text.strip()
    if len(text) > 2000:
        text = text[:2000]
    with _lock:
        _load()
        for w in _INTENT_WORDS:
            if w in text:
                _state["cmds"][w] += 1
        _state["hours"][time.localtime().tm_hour] += 1
        _state["updated"] = int(time.time())
        _save()


def summary():
    """返回注入系统提示词的简短习惯画像；无数据返回空串。"""
    with _lock:
        _load()
        cmds = _state["cmds"].most_common(5)
        if not cmds:
            return ""
        top = "、".join(f"{w}({c})" for w, c in cmds)
        hrs = _state["hours"].most_common(3)
        if hrs:
            hs = "、".join(f"{h}:00({c})" for h, c in hrs)
            return f"【用户习惯】高频关注：{top}；活跃时段：{hs}。"
        return f"【用户习惯】高频关注：{top}。"
