#!/usr/bin/env python3
"""Command Parser — 用户输入解析器。

职责：
- 解析用户输入文本
- 提取命令、参数、上下文
- 输出结构化 Command 对象

约束：
- 不修改 AgentRuntime
- 不创建新数据库
- 只读操作
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


@dataclass
class Command:
    """解析后的用户命令。"""
    raw_text: str
    command: str = ""
    action: str = ""
    args: List[str] = field(default_factory=list)
    kwargs: Dict[str, str] = field(default_factory=dict)
    confidence: float = 0.5
    parsed_at: float = field(default_factory=datetime.now().timestamp)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "command": self.command,
            "action": self.action,
            "args": self.args,
            "kwargs": self.kwargs,
            "confidence": self.confidence,
            "parsed_at": self.parsed_at
        }


def parse_command(text: str) -> Command:
    """
    解析用户输入。
    
    支持格式：
    - 自然语言："帮我查一下今天天气"
    - 命令式："weather beijing"
    - 关键词式："天气 北京"
    
    返回：
    Command 对象
    """
    if not text or not text.strip():
        return Command(raw_text=text or "", confidence=0.0)
    
    text = text.strip()
    result = Command(raw_text=text)
    
    # 1. 尝试命令模式解析 (command arg1 arg2 ...)
    parts = text.split()
    if len(parts) >= 1:
        result.command = parts[0].lower()
        result.args = parts[1:] if len(parts) > 1 else []
        
        # 检测已知命令
        known_commands = {
            "weather", "天气", "search", "搜索", "task", "任务",
            "note", "笔记", "remember", "记住", "goal", "目标",
            "time", "时间", "help", "帮助", "list", "列表"
        }
        
        if result.command in known_commands:
            result.confidence = 0.8
            result.action = result.command
        elif result.command.startswith("/"):
            result.command = result.command[1:]
            result.confidence = 0.7
        else:
            # 2. 尝试自然语言解析
            result = _parse_natural_language(text)
    
    return result


def _parse_natural_language(text: str) -> Command:
    """解析自然语言输入。"""
    result = Command(raw_text=text, confidence=0.5)
    
    # 意图关键词匹配
    patterns = [
        (r"(天气|怎么样|多少度).*?(北京|上海|广州|深圳|杭州|成都|武汉|西安|重庆|南京)", "weather", "location"),
        (r"(搜索|找一下|查一下).*?(ai|人工智能|大模型|llm|gpt)", "search", "topic"),
        (r"(记住|保存|记录).*?(.+)", "remember", "content"),
        (r"(创建|新建|设置).*?(任务|目标|待办).*?(.+)", "create_task", "title"),
        (r"(完成|结束|关闭).*?(任务|工作|项目).*?(.+)", "complete_task", "target"),
        (r"(帮助|怎么用|怎么弄|help)", "help", ""),
        (r"(时间|几点了|现在)", "time", ""),
    ]
    
    for pattern, action, param_name in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result.action = action
            result.confidence = 0.6
            if param_name and match.groups():
                result.kwargs[param_name] = match.group(1).strip()
            break
    
    return result


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    从文本中提取实体。
    
    返回：
    {
        "locations": ["北京", "上海"],
        "topics": ["AI", "大模型"],
        "actions": ["天气", "搜索"]
    }
    """
    entities = {
        "locations": [],
        "topics": [],
        "actions": []
    }
    
    # 地点实体
    location_patterns = [
        r"(北京|上海|广州|深圳|杭州|成都|武汉|西安|重庆|南京|天津|苏州|长沙|郑州)",
        r"([\u4e00-\u9fa5]{2,4}省|[\u4e00-\u9fa5]{2,4}市)"
    ]
    for pattern in location_patterns:
        matches = re.findall(pattern, text)
        entities["locations"].extend(matches)
    
    # 主题实体
    topic_patterns = [
        r"(AI|人工智能|大模型|LLM|GPT|Claude|通义|文心|豆包)",
        r"(代码|编程|Python|JavaScript|React|Vue)"
    ]
    for pattern in topic_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities["topics"].extend(matches)
    
    # 动作实体
    action_keywords = ["天气", "搜索", "任务", "笔记", "帮助", "时间"]
    for keyword in action_keywords:
        if keyword in text:
            entities["actions"].append(keyword)
    
    return entities