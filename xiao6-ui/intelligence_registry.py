#!/usr/bin/env python3
"""Intelligence Registry — 统一智能聚合层。

职责：
- 聚合所有 Intelligence 模块状态
- 提供统一数据协议
- 只读聚合，不修改业务逻辑

约束：
- 不创建第二 Runtime
- 不创建第二 Memory
- 不创建第二 Knowledge
- 不创建新数据库
- 不绕过 EventBus
- 不绕过 Policy Engine
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Any, List


# 统一数据协议
DATA_PROTOCOL_VERSION = "1.0.0"
DATA_PROTOCOL_NAME = "Xiao6 Intelligence Protocol"


def get_status() -> Dict[str, Any]:
    """
    获取统一 Intelligence 状态。
    
    聚合：
    - Memory Intelligence
    - Knowledge Intelligence
    - World Model (GFE)
    - Proactive Intelligence
    
    返回：
    {
        "protocol": str,
        "version": str,
        "memory": {...},
        "knowledge": {...},
        "world_model": {...},
        "proactive": {...},
        "generated_at": str,
        "summary": {...}
    }
    """
    status = {
        "protocol": DATA_PROTOCOL_NAME,
        "version": DATA_PROTOCOL_VERSION,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "memory": {},
        "knowledge": {},
        "world_model": {},
        "proactive": {},
        "summary": {}
    }
    
    # 1. Memory Intelligence
    try:
        import memory_intelligence as mi
        status["memory"] = mi.get_intelligence_status()
    except Exception as e:
        status["memory"] = {"error": str(e)}
    
    # 2. Knowledge Intelligence
    try:
        import knowledge_intelligence as ki
        status["knowledge"] = ki.get_status()
    except Exception as e:
        status["knowledge"] = {"error": str(e)}
    
    # 3. World Model (GFE)
    try:
        import gfe_intelligence as gi
        status["world_model"] = gi.status()
    except Exception as e:
        status["world_model"] = {"error": str(e)}
    
    # 4. Proactive Intelligence
    try:
        import proactive_intelligence as pi
        status["proactive"] = pi.status()
    except Exception as e:
        status["proactive"] = {"error": str(e)}
    
    # 5. 汇总统计
    status["summary"] = _build_summary(status)
    
    return status


def _build_summary(status: Dict[str, Any]) -> Dict[str, Any]:
    """构建汇总统计。"""
    summary = {
        "total_modules": 4,
        "healthy_modules": 0,
        "modules_with_data": 0,
        "overall_health": "unknown",
        "data_protocol": DATA_PROTOCOL_NAME
    }
    
    for module_name in ["memory", "knowledge", "world_model", "proactive"]:
        module_status = status.get(module_name, {})
        
        # 检查是否健康
        if "error" not in module_status:
            summary["healthy_modules"] += 1
        
        # 检查是否有数据
        if module_status.get("total") or module_status.get("total_documents") or \
           module_status.get("total_events") or module_status.get("observations_count"):
            summary["modules_with_data"] += 1
    
    # 计算整体健康度
    if summary["healthy_modules"] == 4:
        summary["overall_health"] = "healthy"
    elif summary["healthy_modules"] >= 3:
        summary["overall_health"] = "degraded"
    else:
        summary["overall_health"] = "warning"
    
    return summary


def get_observation_type_schema() -> Dict[str, Any]:
    """返回 Observation 数据协议。"""
    return {
        "type": "Observation",
        "version": DATA_PROTOCOL_VERSION,
        "fields": {
            "type": {"type": "string", "description": "观察类型", "required": True},
            "source": {"type": "string", "description": "数据来源", "required": True},
            "importance": {"type": "float", "description": "重要性评分 0-1", "required": True},
            "timestamp": {"type": "float", "description": "时间戳", "required": True},
            "detail": {"type": "string", "description": "详细描述", "required": False}
        }
    }


def get_suggestion_type_schema() -> Dict[str, Any]:
    """返回 Suggestion 数据协议。"""
    return {
        "type": "Suggestion",
        "version": DATA_PROTOCOL_VERSION,
        "fields": {
            "type": {"type": "string", "description": "建议类型", "required": True},
            "content": {"type": "string", "description": "建议内容", "required": True},
            "priority": {"type": "int", "description": "优先级 1-10", "required": True},
            "reasoning": {"type": "string", "description": "推理依据", "required": True},
            "suggested_action": {"type": "string", "description": "建议动作", "required": False}
        }
    }


def get_prediction_type_schema() -> Dict[str, Any]:
    """返回 Prediction 数据协议（预留）。"""
    return {
        "type": "Prediction",
        "version": DATA_PROTOCOL_VERSION,
        "note": "Prediction 协议预留，尚未实现",
        "fields": {
            "type": {"type": "string", "description": "预测类型", "required": True},
            "prediction": {"type": "string", "description": "预测内容", "required": True},
            "probability": {"type": "float", "description": "概率 0-1", "required": True},
            "confidence": {"type": "float", "description": "置信度 0-1", "required": True},
            "basis": {"type": "string", "description": "依据", "required": True},
            "time_horizon": {"type": "string", "description": "时间范围", "required": False}
        }
    }


def validate_observation(obs: Dict[str, Any]) -> bool:
    """验证 Observation 是否符合协议。"""
    required = ["type", "source", "importance", "timestamp"]
    return all(k in obs for k in required) and isinstance(obs.get("importance", 0), (int, float))


def validate_suggestion(sug: Dict[str, Any]) -> bool:
    """验证 Suggestion 是否符合协议。"""
    required = ["type", "content", "priority", "reasoning"]
    return all(k in sug for k in required) and isinstance(sug.get("priority", 0), int)