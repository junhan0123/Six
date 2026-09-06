#!/usr/bin/env python3
"""Proactive Engine — 主动智能聚合层。

职责：
- 聚合 observation_loop
- 聚合 suggestion_engine
- 聚合 proactive_policy

约束：
- 不修改 AgentRuntime
- 不创建第二执行入口
- 不自动调用工具
- 不绕过 Policy Engine
- 所有输出 dry-run
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Any, List


def status() -> Dict[str, Any]:
    """
    返回 Proactive Intelligence 状态。
    
    返回：
    {
        "enabled": bool,
        "mode": str,
        "observations_count": int,
        "suggestions_count": int,
        "policy": dict,
        "generated_at": str
    }
    """
    try:
        import observation_loop as ol
        observations = ol.collect_observations()
        obs_count = len(observations)
    except Exception:
        observations = []
        obs_count = 0
    
    try:
        import suggestion_engine as se
        result = se.analyze_observations(observations)
        sug_count = result.get("suggestions_count", 0)
    except Exception:
        sug_count = 0
    
    try:
        import proactive_policy as pp
        policy = pp.get_policy_status()
    except Exception:
        policy = {}
    
    return {
        "enabled": True,
        "mode": "dry_run",
        "observations_count": obs_count,
        "suggestions_count": sug_count,
        "policy": policy,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def analyze(dry_run: bool = True) -> Dict[str, Any]:
    """
    执行主动智能分析。
    
    参数：
    - dry_run: 是否仅分析不执行（强制为 True）
    
    返回：
    {
        "mode": "dry_run",
        "observations": [...],
        "suggestions": [...],
        "filtered_by_policy": int,
        "analysis_summary": {...},
        "generated_at": str
    }
    """
    # 强制 dry-run
    dry_run = True
    
    # 收集观察
    try:
        import observation_loop as ol
        observations = ol.collect_observations()
    except Exception as e:
        observations = []
    
    # 应用防骚扰策略
    try:
        import proactive_policy as pp
        filtered_count = 0
        valid_observations = []
        
        for obs in observations:
            topic = obs.get("type", "unknown")
            if pp.should_send(topic, pp.get_daily_suggestion_count()):
                valid_observations.append(obs)
            else:
                filtered_count += 1
        
        # 生成建议
        try:
            import suggestion_engine as se
            result = se.analyze_observations(valid_observations)
            suggestions = result.get("suggestions", [])
        except Exception:
            suggestions = []
            
    except Exception:
        suggestions = []
        filtered_count = 0
    
    # 标记已发送（仅用于计数，不实际发送）
    try:
        import proactive_policy as pp
        for obs in valid_observations:
            topic = obs.get("type", "unknown")
            pp.mark_topic_sent(topic)
        pp.increment_daily_count()
    except Exception:
        pass
    
    return {
        "mode": "dry_run",
        "observations": observations,
        "suggestions": suggestions,
        "filtered_by_policy": filtered_count,
        "analysis_summary": {
            "total_observations": len(observations),
            "valid_observations": len(valid_observations) if 'valid_observations' in dir() else len(observations),
            "high_importance": len([o for o in observations if o.get("importance", 0) >= 0.7]),
            "suggestions_generated": len(suggestions)
        },
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }