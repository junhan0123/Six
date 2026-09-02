#!/usr/bin/env python3
"""Xiao6 · 电脑动作规划层（planner.py）—— Phase 21.1

意图/目标 → 白名单动作计划。裁决 100% 委托 os_bridge.action_plan
（→ permission_guard → policy_engine）。本模块只做：
  - 白名单前置校验（safety.assert_allowed）
  - 高层意图解析（关键词 → 白名单能力，无 LLM 依赖）
  - 统一的计划产物
"""
from __future__ import annotations


def _assert(cap):
    from .safety import assert_allowed
    assert_allowed(cap)


def plan(capability, target="", parameters=None, *, goal_id=None):
    """规划 + 裁决预览（绝不执行）。返回 os_bridge.action_plan 的预览结构。"""
    _assert(capability)
    from os_bridge import action_plan
    return action_plan(capability, target=target, parameters=parameters, goal_id=goal_id)


def observe_then_plan(capability, target="", parameters=None, *, goal_id=None, scope="window"):
    """观察 → 规划：先取环境快照，再产出动作预览（供 UI 渲染四态）。"""
    from .observer import observe
    obs = observe(scope=scope)
    preview = plan(capability, target=target, parameters=parameters, goal_id=goal_id)
    return {"observation": obs, "plan": preview}


def execute(action_id, confirmed=False, goal_id=None):
    """执行：委托 os_bridge.action_execute（用户确认 → 真实执行 → 验证）。"""
    from os_bridge import action_execute
    return action_execute(action_id, confirmed=confirmed, goal_id=goal_id)


# —— 高层意图解析（仅关键词 → 白名单，无 LLM 依赖）——
_INTENT_MAP = [
    ("搜索", "search"), ("查找", "search"), ("找文件", "search"), ("检索", "search"),
    ("打开文件夹", "open_folder"), ("打开目录", "open_folder"), ("打开项目", "open_folder"),
    ("打开文件", "open_file"), ("打开记事本", "open_application"),
    ("启动", "open_application"), ("复制", "copy_text"),
]


def resolve_intent(text):
    """把自然语言意图映射到一个白名单能力（匹配不到返回 None）。"""
    if not text:
        return None
    for kw, cap in _INTENT_MAP:
        if kw in text:
            return cap
    return None
