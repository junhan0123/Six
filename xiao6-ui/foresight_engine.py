#!/usr/bin/env python3
"""S145 — Intelligence Foresight Layer 前瞻智能层。

职责：
- Trend Detection：趋势检测（rising/falling/stable/emerging）
- Early Warning：早期预警
- Prediction Ledger：预测账本记录

约束：
- 不修改 AgentRuntime
- 不修改 Planner
- 不修改 Tool Execution
- 不修改 Memory Schema
- 不新建数据库
- 不引入预测模型
- 只读现有数据，生成趋势信号
"""

from __future__ import annotations

import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

# 趋势类型
TREND_RISING = "rising"
TREND_FALLING = "falling"
TREND_STABLE = "stable"
TREND_EMERGING = "emerging"

# 预警级别
WARNING_LOW = "low"
WARNING_MEDIUM = "medium"
WARNING_HIGH = "high"

# 数据源
SOURCE_MEMORY = "memory"
SOURCE_KNOWLEDGE = "knowledge"
SOURCE_WORLD = "world"
SOURCE_PROACTIVE = "proactive"

# 内存存储键
FORECAST_KEY_PREFIX = "foresight_"
LEDGER_KEY_PREFIX = "ledger_"


@dataclass
class TrendSignal:
    """趋势信号。"""
    signal_id: str
    trend_type: str  # rising, falling, stable, emerging
    title: str
    confidence: float  # 0-1
    reason: str
    source: str
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "type": self.trend_type,
            "title": self.title,
            "confidence": round(self.confidence, 2),
            "reason": self.reason,
            "source": self.source,
            "timestamp": self.timestamp
        }


@dataclass
class EarlyWarning:
    """早期预警。"""
    warning_id: str
    warning_level: str  # low, medium, high
    message: str
    source: str
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "warning_id": self.warning_id,
            "level": self.warning_level,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp
        }


@dataclass
class ForesightRecord:
    """前瞻记录（Prediction Ledger）。"""
    record_id: str
    insight_id: str
    hypothesis: str
    confidence: float
    created_at: str
    status: str  # pending, active, archived
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "insight_id": self.insight_id,
            "hypothesis": self.hypothesis,
            "confidence": round(self.confidence, 2),
            "created_at": self.created_at,
            "status": self.status
        }


class ForesightEngine:
    """前瞻智能引擎。
    
    职责：
    - 从已有 Intelligence 模块读取数据
    - 检测趋势信号
    - 生成早期预警
    - 管理预测账本
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        # 趋势缓存
        self._trends: Dict[str, TrendSignal] = {}
        # 预警缓存
        self._warnings: Dict[str, EarlyWarning] = {}
        # 预测账本
        self._ledger: Dict[str, ForesightRecord] = {}
        # 最后更新时间
        self._last_update = 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """获取前瞻引擎状态。"""
        return {
            "ok": True,
            "engine": "foresight",
            "version": "1.0.0",
            "trends_count": len(self._trends),
            "warnings_count": len(self._warnings),
            "ledger_count": len(self._ledger),
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
    
    def get_signals(self, limit: int = 20) -> Dict[str, Any]:
        """获取趋势信号列表。"""
        signals = list(self._trends.values())
        # 按置信度排序
        signals.sort(key=lambda x: x.confidence, reverse=True)
        return {
            "ok": True,
            "signals": [s.to_dict() for s in signals[:limit]],
            "total": len(signals)
        }
    
    def get_warnings(self, limit: int = 10) -> Dict[str, Any]:
        """获取早期预警列表。"""
        warnings = list(self._warnings.values())
        # 按级别排序（high > medium > low）
        level_order = {WARNING_HIGH: 0, WARNING_MEDIUM: 1, WARNING_LOW: 2}
        warnings.sort(key=lambda x: level_order.get(x.warning_level, 3))
        return {
            "ok": True,
            "warnings": [w.to_dict() for w in warnings[:limit]],
            "total": len(warnings)
        }
    
    def add_ledger_record(self, insight_id: str, hypothesis: str, confidence: float) -> Optional[Dict[str, Any]]:
        """添加预测账本记录。"""
        if confidence < 0 or confidence > 1:
            return None
        
        record_id = f"{LEDGER_KEY_PREFIX}{int(time.time())}_{len(self._ledger)}"
        record = ForesightRecord(
            record_id=record_id,
            insight_id=insight_id,
            hypothesis=hypothesis,
            confidence=confidence,
            created_at=datetime.utcnow().isoformat() + "Z",
            status="pending"
        )
        
        with self._lock:
            self._ledger[record_id] = record
        
        return record.to_dict()
    
    def update_trend(self, signal_id: str, trend_type: str, title: str, 
                     confidence: float, reason: str, source: str) -> Optional[TrendSignal]:
        """更新或创建趋势信号。"""
        if confidence < 0 or confidence > 1:
            return None
        
        signal = TrendSignal(
            signal_id=signal_id,
            trend_type=trend_type,
            title=title,
            confidence=confidence,
            reason=reason,
            source=source,
            timestamp=time.time()
        )
        
        with self._lock:
            self._trends[signal_id] = signal
            self._last_update = time.time()
        
        return signal
    
    def update_warning(self, warning_id: str, warning_level: str, 
                       message: str, source: str) -> Optional[EarlyWarning]:
        """更新或创建预警。"""
        if warning_level not in [WARNING_LOW, WARNING_MEDIUM, WARNING_HIGH]:
            return None
        
        warning = EarlyWarning(
            warning_id=warning_id,
            warning_level=warning_level,
            message=message,
            source=source,
            timestamp=time.time()
        )
        
        with self._lock:
            self._warnings[warning_id] = warning
            self._last_update = time.time()
        
        return warning
    
    def refresh_from_intelligence(self, memory: Dict[str, Any], knowledge: Dict[str, Any],
                                   world: Dict[str, Any], proactive: Dict[str, Any]) -> Dict[str, Any]:
        """从已有 Intelligence 模块刷新趋势和预警。"""
        updated = 0
        warned = 0
        
        # 1. World Model 趋势检测
        world_risk = world.get("risk_level", "medium")
        world_events = world.get("events", [])
        
        if world_risk == "high":
            self.update_warning("world-high-risk", WARNING_HIGH, 
                              f"世界风险提升至 {world_risk}，需重点关注", SOURCE_WORLD)
            warned += 1
        elif world_risk == "medium":
            self.update_warning("world-medium-risk", WARNING_MEDIUM,
                              f"世界风险维持 {world_risk}，持续观察", SOURCE_WORLD)
            warned += 1
        
        # 检测风险趋势
        if len(world_events) > 5:
            self.update_trend("world-trend-rising", TREND_RISING,
                            "世界事件增多", 0.75, 
                            f"检测到 {len(world_events)} 个世界事件", SOURCE_WORLD)
            updated += 1
        
        # 2. Memory Intelligence 趋势
        memory_count = memory.get("total", 0)
        recent_logs = memory.get("recent_logs", [])
        
        if memory_count > 30:
            self.update_trend("memory-trend-rising", TREND_RISING,
                            "记忆增长", 0.65,
                            f"记忆库已积累 {memory_count} 条记录", SOURCE_MEMORY)
            updated += 1
        
        # 3. Knowledge Intelligence 趋势
        knowledge_docs = knowledge.get("total", 0)
        if knowledge_docs > 300:
            self.update_trend("knowledge-trend-stable", TREND_STABLE,
                            "知识库稳定", 0.8,
                            f"知识库包含 {knowledge_docs} 文档", SOURCE_KNOWLEDGE)
            updated += 1
        
        # 4. Proactive Intelligence 趋势
        observations = proactive.get("observation_sources", 0)
        high_importance = proactive.get("high_importance_observations", 0)
        
        if high_importance > 0:
            self.update_trend("proactive-trend-emerging", TREND_EMERGING,
                            "主动关注点出现", 0.7,
                            f"检测到 {high_importance} 个高优先级观察", SOURCE_PROACTIVE)
            updated += 1
        
        if observations > 0:
            self.update_warning("proactive-observations", WARNING_MEDIUM,
                              f"主动观察系统运行中，{observations} 个观察源活跃", SOURCE_PROACTIVE)
            warned += 1
        
        self._last_update = time.time()
        
        return {
            "updated": updated,
            "warned": warned,
            "total_signals": len(self._trends),
            "total_warnings": len(self._warnings)
        }


# ============================================================
# Singleton
# ============================================================

_instance: Optional[ForesightEngine] = None
_instance_lock = threading.Lock()


def get_foresight_engine() -> ForesightEngine:
    """获取单例前瞻引擎。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = ForesightEngine()
        return _instance


def reset_foresight_engine():
    """重置单例（用于测试）。"""
    global _instance
    with _instance_lock:
        _instance = None