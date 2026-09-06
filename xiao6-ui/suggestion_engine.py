#!/usr/bin/env python3
"""Suggestion Engine — 建议生成引擎。

职责：
- 根据 observation 生成建议
- 只有 importance >= 0.7 才生成建议
- 输出结构化建议

约束：
- 不修改 AgentRuntime
- 不自动执行
- dry-run 模式
"""

from __future__ import annotations

from typing import List, Dict, Any


IMPORTANCE_THRESHOLD = 0.7


def generate_suggestion(observation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    根据观察生成建议。
    
    规则：
    - importance >= 0.7 才生成
    - 输出结构化建议
    
    返回：
    {
        "type": str,
        "content": str,
        "priority": int,
        "reasoning": str,
        "suggested_action": str
    }
    """
    importance = observation.get("importance", 0)
    
    if importance < IMPORTANCE_THRESHOLD:
        return None
    
    obs_type = observation.get("type", "")
    detail = observation.get("detail", "")
    source = observation.get("source", "")
    
    suggestion = {
        "type": obs_type,
        "content": detail,
        "priority": int(importance * 10),
        "reasoning": f"Importance {importance:.2f} exceeds threshold {IMPORTANCE_THRESHOLD}",
        "suggested_action": _suggest_action(obs_type, source)
    }
    
    return suggestion


def _suggest_action(obs_type: str, source: str) -> str:
    """根据观察类型生成建议动作。"""
    actions = {
        "memory_concentration": "检查高浓度记忆类别是否需要整理",
        "world_event": "查看世界事件详情，评估风险",
        "goal_activity": "检查停滞目标，考虑推进",
        "task_activity": "查看开放任务列表",
        "knowledge_activity": "评估知识质量"
    }
    
    return actions.get(obs_type, f"查看 {source} 详情")


def analyze_observations(observations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    分析观察数据，生成建议列表。
    
    返回：
    {
        "mode": "dry_run",
        "observations_count": int,
        "suggestions_count": int,
        "suggestions": [...],
        "high_importance_count": int
    }
    """
    suggestions = []
    high_importance = []
    
    for obs in observations:
        imp = obs.get("importance", 0)
        if imp >= 0.7:
            high_importance.append(obs)
        
        sug = generate_suggestion(obs)
        if sug:
            suggestions.append(sug)
    
    return {
        "mode": "dry_run",
        "observations_count": len(observations),
        "suggestions_count": len(suggestions),
        "high_importance_count": len(high_importance),
        "suggestions": suggestions
    }