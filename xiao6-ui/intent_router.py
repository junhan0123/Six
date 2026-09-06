#!/usr/bin/env python3
"""Intent Router — 意图路由层。

职责：
- 根据 Command 分类意图
- 路由到对应的处理器
- 输出结构化 Intent

约束：
- 不修改 AgentRuntime
- 不创建新数据库
- 只读操作
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable

from command_parser import Command


@dataclass
class Intent:
    """解析后的意图。"""
    command: Command
    intent_type: str = "unknown"
    intent_category: str = "general"
    priority: int = 5
    confidence: float = 0.5
    routing_target: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    routed_at: float = field(default_factory=datetime.now().timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type,
            "intent_category": self.intent_category,
            "priority": self.priority,
            "confidence": self.confidence,
            "routing_target": self.routing_target,
            "context": self.context,
            "raw_command": self.command.to_dict(),
            "routed_at": self.routed_at
        }


class IntentRouter:
    """意图路由器。"""

    # 意图类型常量
    INTENT_WEATHER = "weather"
    INTENT_SEARCH = "search"
    INTENT_TASK = "task"
    INTENT_NOTE = "note"
    INTENT_REMEMBER = "remember"
    INTENT_TIME = "time"
    INTENT_HELP = "help"
    INTENT_STATUS = "status"
    INTENT_CHAT = "chat"
    INTENT_UNKNOWN = "unknown"

    # 意图分类
    CATEGORY_TOOL = "tool"
    CATEGORY_INFO = "info"
    CATEGORY_CHAT = "chat"
    CATEGORY_CONTROL = "control"
    CATEGORY_UNKNOWN = "unknown"

    def __init__(self):
        self._routes: Dict[str, Callable] = {}
        self._register_defaults()

    def _register_defaults(self):
        """注册默认路由。"""
        self.route(self.INTENT_WEATHER, self.CATEGORY_INFO)
        self.route(self.INTENT_SEARCH, self.CATEGORY_INFO)
        self.route(self.INTENT_TASK, self.CATEGORY_CONTROL)
        self.route(self.INTENT_NOTE, self.CATEGORY_CONTROL)
        self.route(self.INTENT_REMEMBER, self.CATEGORY_CONTROL)
        self.route(self.INTENT_TIME, self.CATEGORY_INFO)
        self.route(self.INTENT_HELP, self.CATEGORY_INFO)
        self.route(self.INTENT_STATUS, self.CATEGORY_INFO)
        self.route(self.INTENT_CHAT, self.CATEGORY_CHAT)

    def route(self, intent_type: str, category: str):
        """注册意图路由。"""
        self._routes[intent_type] = category

    def classify(self, command: Command) -> Intent:
        """
        分类命令为意图。
        
        返回：
        Intent 对象
        """
        intent = Intent(command=command)
        
        action = command.action.lower() if command.action else ""
        command_name = command.command.lower() if command.command else ""
        
        # 精确匹配
        if action in self._routes:
            intent.intent_type = action
            intent.intent_category = self._routes[action]
            intent.confidence = 0.9
        elif command_name in self._routes:
            intent.intent_type = command_name
            intent.intent_category = self._routes[command_name]
            intent.confidence = 0.8
        # 模糊匹配
        elif action or command_name:
            intent.intent_type = self._fuzzy_match(action + command_name)
            intent.intent_category = self._routes.get(intent.intent_type, self.CATEGORY_UNKNOWN)
            intent.confidence = 0.5
        else:
            intent.intent_type = self.INTENT_CHAT
            intent.intent_category = self.CATEGORY_CHAT
            intent.confidence = 0.3
        
        # 设置路由目标
        intent.routing_target = self._get_routing_target(intent.intent_type)
        
        # 设置优先级
        intent.priority = self._get_priority(intent.intent_type)
        
        # 构建上下文
        intent.context = self._build_context(command, intent)
        
        return intent

    def _fuzzy_match(self, text: str) -> str:
        """模糊匹配意图类型。"""
        text_lower = text.lower()
        
        weather_keywords = ["天气", "weather", "温度", "rain", "snow"]
        search_keywords = ["搜索", "search", "找", "query", "查"]
        task_keywords = ["任务", "task", "todo", "todo", "待办"]
        note_keywords = ["笔记", "note", "memo", "记录"]
        time_keywords = ["时间", "time", "几点了", "clock"]
        help_keywords = ["帮助", "help", "怎么用", "how"]
        
        for kw in weather_keywords:
            if kw in text_lower:
                return self.INTENT_WEATHER
        for kw in search_keywords:
            if kw in text_lower:
                return self.INTENT_SEARCH
        for kw in task_keywords:
            if kw in text_lower:
                return self.INTENT_TASK
        for kw in time_keywords:
            if kw in text_lower:
                return self.INTENT_TIME
        for kw in help_keywords:
            if kw in text_lower:
                return self.INTENT_HELP
        
        return self.INTENT_CHAT

    def _get_routing_target(self, intent_type: str) -> str:
        """获取路由目标。"""
        targets = {
            self.INTENT_WEATHER: "/api/weather",
            self.INTENT_SEARCH: "/api/search",
            self.INTENT_TASK: "/api/tasks",
            self.INTENT_NOTE: "/api/notes",
            self.INTENT_TIME: "/api/time",
            self.INTENT_HELP: "/api/help",
            self.INTENT_STATUS: "/api/health",
            self.INTENT_CHAT: "/api/chat"
        }
        return targets.get(intent_type, "/api/chat")

    def _get_priority(self, intent_type: str) -> int:
        """获取优先级 (1-10, 10 最高)。"""
        priorities = {
            self.INTENT_TIME: 3,
            self.INTENT_WEATHER: 3,
            self.INTENT_SEARCH: 4,
            self.INTENT_HELP: 2,
            self.INTENT_STATUS: 2,
            self.INTENT_TASK: 7,
            self.INTENT_NOTE: 5,
            self.INTENT_CHAT: 1
        }
        return priorities.get(intent_type, 5)

    def _build_context(self, command: Command, intent: Intent) -> Dict[str, Any]:
        """构建上下文。"""
        context = {
            "raw_text": command.raw_text,
            "intent_type": intent.intent_type,
            "arguments": command.args,
            "kwargs": command.kwargs
        }
        return context


# 全局路由器实例
_router = IntentRouter()


def get_router() -> IntentRouter:
    """获取全局路由器实例。"""
    return _router


def classify_intent(command: Command) -> Intent:
    """便捷函数：分类意图。"""
    return _router.classify(command)