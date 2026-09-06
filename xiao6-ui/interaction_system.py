#!/usr/bin/env python3
"""Interaction System — 交互系统主入口。

职责：
- 聚合 Command Parser + Intent Router + Interaction Context + Response Builder
- 提供统一 API

约束：
- 不修改 AgentRuntime
- 不创建第二执行入口
- 只读操作
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from command_parser import parse_command, extract_entities
from intent_router import classify_intent, get_router
from interaction_context import get_context
from response_builder import ResponseBuilder


def get_status() -> Dict[str, Any]:
    """
    获取 Interaction System 状态。
    
    返回：
    {
        "enabled": bool,
        "modules": {...},
        "context_stats": {...},
        "generated_at": str
    }
    """
    from datetime import datetime
    
    context = get_context()
    stats = context.get_stats()
    
    return {
        "enabled": True,
        "modules": {
            "command_parser": "ready",
            "intent_router": "ready",
            "interaction_context": "ready",
            "response_builder": "ready"
        },
        "context_stats": stats,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def parse_interaction(text: str) -> Dict[str, Any]:
    """
    解析用户交互输入。
    
    参数：
    - text: 用户输入文本
    
    返回：
    {
        "ok": bool,
        "message": str,
        "data": {
            "command": {...},
            "intent": {...},
            "entities": {...}
        }
    }
    """
    try:
        # 1. 解析命令
        command = parse_command(text)
        
        # 2. 分类意图
        intent = classify_intent(command)
        
        # 3. 提取实体
        entities = extract_entities(text)
        
        # 4. 创建上下文会话
        context = get_context()
        session = context.create_session(user_input=text)
        context.update_session(
            session.session_id,
            command=command.to_dict(),
            intent=intent.to_dict()
        )
        context.end_session(session.session_id)
        
        # 5. 构建响应
        return ResponseBuilder.parse_result(
            command.to_dict(),
            intent.to_dict()
        ).to_dict()
        
    except Exception as e:
        return ResponseBuilder.error(f"解析失败: {str(e)}").to_dict()