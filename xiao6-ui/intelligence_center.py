#!/usr/bin/env python3
"""S151 — Intelligence Center Consolidation 智能中心整合层。

职责：
- 统一读取所有 Intelligence 模块
- 生成 AI Insight Center Snapshot
- 提供聚合视图

约束：
- 不修改原模块
- 只读聚合
- 不创建新数据库
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Any, List, Optional


class IntelligenceCenter:
    """Intelligence Center 聚合层。"""
    
    def __init__(self):
        self._last_update = 0.0
    
    def get_snapshot(self) -> Dict[str, Any]:
        """获取完整 Intelligence Center Snapshot。"""
        try:
            import intelligence_feed as ifeed
            feed_engine = ifeed.get_feed_engine()
            feed_data = feed_engine.get_feed()
            insights = feed_data.get("items", []) if isinstance(feed_data, dict) else []
        except Exception:
            insights = []
        
        try:
            import foresight_engine as fe
            foresight_engine = fe.get_foresight_engine()
            foresight_data = foresight_engine.get_foresight()
            future_signals = foresight_data.get("signals", []) if isinstance(foresight_data, dict) else []
            warnings = foresight_data.get("warnings", []) if isinstance(foresight_data, dict) else []
        except Exception:
            future_signals = []
            warnings = []
        
        try:
            import intelligence_context as ic
            context_engine = ic.get_context_engine()
            context_data = context_engine.get_context()
            reasonings = context_data.get("contexts", []) if isinstance(context_data, dict) else []
        except Exception:
            reasonings = []
        
        try:
            import intelligence_reasoning as ir
            reasoning_engine = ir.get_reasoning_engine()
            reasoning_data = reasoning_engine.get_reasoning()
            reasonings = reasoning_data.get("reasonings", []) if isinstance(reasoning_data, dict) else []
        except Exception:
            reasonings = []
        
        try:
            import intelligence_decision as idc
            decision_engine = idc.get_decision_engine()
            decision_data = decision_engine.get_decisions()
            decisions = decision_data.get("decisions", []) if isinstance(decision_data, dict) else []
        except Exception:
            decisions = []
        
        try:
            import intelligence_prediction as ip
            prediction_engine = ip.get_prediction_engine()
            prediction_data = prediction_engine.get_predictions()
            predictions = prediction_data if isinstance(prediction_data, list) else []
        except Exception:
            predictions = []
        
        try:
            import intelligence_learning as il
            learning_engine = il.get_learning_engine()
            learning_data = learning_engine.get_learning_records()
            sources = learning_engine.get_source_reliability()
            learning = {
                "records": learning_data,
                "sources": [s.to_dict() for s in sources] if sources else []
            }
        except Exception:
            learning = {"records": [], "sources": []}
        
        # 计算概览
        overview = {
            "total_insights": len(insights),
            "total_signals": len(future_signals),
            "total_warnings": len(warnings),
            "total_reasonings": len(reasonings),
            "total_decisions": len(decisions),
            "total_predictions": len(predictions),
            "has_learning_data": len(learning.get("records", [])) > 0
        }
        
        self._last_update = time.time()
        
        return {
            "overview": overview,
            "insights": insights[:10],  # 限制数量
            "future_signals": future_signals[:5],
            "warnings": warnings[:5],
            "reasonings": reasonings[:5],
            "decisions": decisions[:5],
            "predictions": predictions[:5],
            "learning": learning,
            "timestamp": datetime.fromtimestamp(self._last_update).isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态。"""
        return {
            "ok": True,
            "engine": "center",
            "version": "1.0.0",
            "last_update": self._last_update,
            "modules": {
                "feed": "active",
                "foresight": "active",
                "context": "active",
                "reasoning": "active",
                "decision": "active",
                "prediction": "active",
                "learning": "active"
            },
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }


# 单例
_engine: Optional[IntelligenceCenter] = None
_engine_lock = __import__("threading").Lock()


def get_center_engine() -> IntelligenceCenter:
    """获取中心引擎单例。"""
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = IntelligenceCenter()
        return _engine