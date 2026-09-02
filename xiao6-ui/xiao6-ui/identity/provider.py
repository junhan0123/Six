#!/usr/bin/env python3
"""Xiao6 · 身份与自我模型层（Identity & Self Model Layer）—— Phase 26

单一身份来源（Single Source of Truth）：
- identity.json 是Xiao6「是谁」的唯一权威定义（Agent Identity / User Relationship /
  Project Understanding / Behavior Style / Long Term Objectives）；
- 每条事实带 source / confidence / updated / status，可验证、可追溯来源、可评可信度；
- 只有可信度 >= MIN_INJECT_CREDIBILITY 的事实才允许进入系统提示（Context Engine），
  低可信（inference）信息被拦截，不能污染身份。

零侵入：本模块不修改 Agent Runtime / Planner / Executor / EventBus / Memory 核心；
仅被 Context Engine 的 IdentitySource 与 persona_engine 读取（单向依赖）。

依赖：仅标准库（json / os / datetime），零新第三方依赖。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_IDENTITY_PATH = os.path.join(_HERE, "identity.json")
DEFAULT_SCHEMA_PATH = os.path.join(_HERE, "identity_schema.json")

# ── 来源可信度等级（用于无显式 confidence 时的回退）──
CRED_SOURCE_LEVELS = {
    "system_declared": 1.0,   # 系统声明（身份层作者），最高可信
    "user_confirmed": 1.0,    # 用户明确确认
    "config": 0.9,            # 配置 / 项目真实状态
    "project_state": 0.9,     # 项目真实状态（Git/工作区）
    "conversation": 0.7,      # 长期对话沉淀
    "inference": 0.4,         # 模型推断（低可信，禁止注入系统提示）
}

# 允许进入系统提示的最低可信度（低于此被拦截，不能污染身份）
MIN_INJECT_CREDIBILITY = 0.6

# 进程内缓存（identity.json 为静态权威文件，缓存安全）
_CACHE: dict = {}


class IdentityError(Exception):
    """身份数据非法 / 加载失败。"""
    pass


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def load_identity(path: str = DEFAULT_IDENTITY_PATH) -> dict:
    """读取并校验 identity.json；返回数据字典。任何异常转为 IdentityError。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise IdentityError("identity.json 不存在: %s" % path)
    except json.JSONDecodeError as e:
        raise IdentityError("identity.json 不是合法 JSON: %s" % e)
    issues = validate_identity(data)
    if issues:
        raise IdentityError("identity.json 校验失败: " + "; ".join(issues))
    return data


def validate_identity(data: dict) -> list[str]:
    """手动校验（零第三方依赖）。返回问题列表，空列表表示通过。"""
    issues: list[str] = []
    if not isinstance(data, dict):
        return ["identity 顶层必须是对象"]
    for k in ("schema_version", "agent"):
        if k not in data:
            issues.append("缺少顶层字段 %s" % k)
    agent = data.get("agent") or {}
    if not isinstance(agent, dict):
        issues.append("agent 必须是对象")
    else:
        for k in ("name", "role", "self_statement"):
            if not agent.get(k):
                issues.append("agent.%s 缺失或非空" % k)
    for sec_key in ("agent", "user_relationship", "project_understanding", "behavior_style"):
        sec = data.get(sec_key)
        if isinstance(sec, dict):
            cf = sec.get("confidence")
            if cf is not None and not (isinstance(cf, (int, float)) and 0.0 <= float(cf) <= 1.0):
                issues.append("%s.confidence 超出 [0,1]: %r" % (sec_key, cf))
            src = sec.get("source")
            if src is not None and src not in CRED_SOURCE_LEVELS:
                issues.append("%s.source 非法: %s" % (sec_key, src))
    lto = data.get("long_term_objectives")
    if lto is not None and not isinstance(lto, list):
        issues.append("long_term_objectives 必须是数组")
    elif isinstance(lto, list):
        for i, obj in enumerate(lto):
            if not isinstance(obj, dict) or not obj.get("objective"):
                issues.append("long_term_objectives[%d] 缺 objective" % i)
    return issues


def get_provider(path: str = DEFAULT_IDENTITY_PATH) -> "IdentityProvider":
    """返回（带缓存的）IdentityProvider 单例；identity.json 变更后调用 reload() 失效。"""
    key = os.path.abspath(path)
    p = _CACHE.get(key)
    if p is None:
        p = IdentityProvider(path)
        _CACHE[key] = p
    return p


def reload(path: str = DEFAULT_IDENTITY_PATH) -> "IdentityProvider":
    """丢弃缓存并重新加载（用于配置热更新场景）。"""
    key = os.path.abspath(path)
    _CACHE.pop(key, None)
    return get_provider(path)


class IdentityProvider:
    """身份与自我模型提供者。"""

    def __init__(self, path: str = DEFAULT_IDENTITY_PATH) -> None:
        self._path = path
        self._data = load_identity(path)
        self._loaded_at = _now()

    # ── 基本访问 ──
    def get_identity(self) -> dict:
        return self._data

    def get_agent(self) -> dict:
        return self._data.get("agent") or {}

    def get_agent_name(self, fallback: str = "小6") -> str:
        return (self.get_agent().get("name") or fallback).strip() or fallback

    # ── 可信度 ──
    def _conf_of_section(self, section: dict) -> float:
        cf = section.get("confidence")
        if isinstance(cf, (int, float)):
            return float(cf)
        return float(CRED_SOURCE_LEVELS.get(section.get("source", ""), CRED_SOURCE_LEVELS["inference"]))

    def is_trusted(self, section_key: str, min_credibility: float = MIN_INJECT_CREDIBILITY) -> bool:
        sec = self._data.get(section_key)
        if not isinstance(sec, dict):
            return False
        return self._conf_of_section(sec) >= float(min_credibility)

    def trace(self, section_key: str) -> dict:
        """返回某段的来源/可信度/时间/状态/溯源，用于 Context 元数据与可观测。"""
        sec = self._data.get(section_key) or {}
        return {
            "section": section_key,
            "source": sec.get("source", ""),
            "confidence": self._conf_of_section(sec),
            "updated": sec.get("updated", ""),
            "status": sec.get("status", ""),
            "provenance": "%s#%s" % (os.path.basename(self._path), section_key),
        }

    def get_behavior_style(self) -> dict:
        """返回行为风格（供 persona_engine 单一来源读取）。"""
        bs = self._data.get("behavior_style") or {}
        if not isinstance(bs, dict):
            return {}
        return {
            "tone": bs.get("tone"),
            "style": bs.get("style"),
            "boundaries": bs.get("boundaries") or [],
            "quirks": bs.get("quirks") or [],
        }

    # ── 渲染（仅可信段进入系统提示）──
    def render_identity_block(self, min_credibility: float = MIN_INJECT_CREDIBILITY) -> str:
        """渲染【身份】块；低可信段被拦截，空内容返回 ''。"""
        if not self.is_trusted("agent", min_credibility):
            return ""
        agent = self.get_agent()
        name = agent.get("name", "小6")
        role = agent.get("role", "")
        self_stmt = agent.get("self_statement", "")
        lines = ["【身份 · %s】" % name]
        opener = "你是%s" % name
        if role:
            opener += "，%s" % role
        opener += "。"
        lines.append(opener)
        if self_stmt:
            lines.append(self_stmt)
        # 用户关系（可信才注入）
        ur = self._data.get("user_relationship") or {}
        if self.is_trusted("user_relationship", min_credibility) and ur.get("relationship"):
            rel = "· 与用户关系：%s" % ur["relationship"]
            if ur.get("address_as"):
                rel += "（称呼：%s）" % ur["address_as"]
            lines.append(rel)
        # 项目理解
        pu = self._data.get("project_understanding") or {}
        if self.is_trusted("project_understanding", min_credibility) and pu.get("primary_project"):
            proj = "· 当前项目：%s" % pu["primary_project"]
            if pu.get("nature"):
                proj += "（%s）" % pu["nature"]
            lines.append(proj)
        # 长期目标（逐条按可信度过滤）
        lto = self._data.get("long_term_objectives") or []
        trusted_objs = [
            o.get("objective", "")
            for o in lto
            if isinstance(o, dict) and o.get("objective") and self._conf_of_section(o) >= float(min_credibility)
        ]
        if trusted_objs:
            lines.append("· 长期目标：" + "；".join(trusted_objs))
        return "\n".join(lines) + "\n"
