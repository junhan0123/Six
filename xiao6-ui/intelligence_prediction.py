#!/usr/bin/env python3
"""S149 — Intelligence Prediction Ledger Layer 预测账本层。

职责：
- 管理预测生命周期
- 建立预测→记录→验证→学习闭环
- 记录置信度演化

约束：
- 不修改 AgentRuntime
- 不修改 Planner
- 不修改 Tool Execution
- 不修改 Memory Schema
- 不创建新数据库
- 不引入新 AI 模型
- 不自动执行预测动作
- 不修改用户数据结构
"""

from __future__ import annotations

import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

# 内存存储键
PREDICTION_KEY_PREFIX = "pred_"
VERIFICATION_KEY_PREFIX = "ver_"

# 预测状态
STATUS_PENDING = "pending"
STATUS_ACTIVE = "active"
STATUS_RESOLVED = "resolved"
STATUS_EXPIRED = "expired"

# 验证结果
OUTCOME_CORRECT = "correct"
OUTCOME_PARTIAL = "partial"
OUTCOME_FAILED = "failed"


@dataclass
class PredictionRecord:
    """预测记录。"""
    prediction_id: str
    source_insight_id: str
    topic: str
    hypothesis: str
    confidence: float
    created_at: float
    expected_time: Optional[float]
    status: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "source_insight_id": self.source_insight_id,
            "topic": self.topic,
            "hypothesis": self.hypothesis,
            "confidence": round(self.confidence, 2),
            "created_at": self.created_at,
            "expected_time": self.expected_time,
            "status": self.status,
            "timestamp": datetime.fromtimestamp(self.created_at).isoformat()
        }


@dataclass
class OutcomeVerification:
    """结果验证。"""
    verification_id: str
    prediction_id: str
    outcome: str  # correct, partial, failed
    result: str
    confidence_change: float
    verified_at: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "verification_id": self.verification_id,
            "prediction_id": self.prediction_id,
            "outcome": self.outcome,
            "result": self.result,
            "confidence_change": round(self.confidence_change, 2),
            "verified_at": self.verified_at,
            "timestamp": datetime.fromtimestamp(self.verified_at).isoformat()
        }


class PredictionEngine:
    """预测引擎。"""
    
    def __init__(self):
        self._predictions: Dict[str, PredictionRecord] = {}
        self._verifications: Dict[str, OutcomeVerification] = {}
        self._lock = threading.Lock()
        self._last_id = 0
    
    def _next_id(self) -> int:
        self._last_id += 1
        return self._last_id
    
    def create_prediction(self, 
                          topic: str,
                          hypothesis: str,
                          source: str = "prediction_ledger",
                          confidence: float = 0.7,
                          expected_time: Optional[float] = None) -> PredictionRecord:
        """创建预测记录。"""
        with self._lock:
            pred_id = f"{PREDICTION_KEY_PREFIX}{int(time.time())}_{self._next_id()}"
            record = PredictionRecord(
                prediction_id=pred_id,
                source_insight_id="",
                topic=topic,
                hypothesis=hypothesis,
                confidence=confidence,
                created_at=time.time(),
                expected_time=expected_time,
                status=STATUS_PENDING
            )
            self._predictions[pred_id] = record
            return record
    
    def activate_prediction(self, prediction_id: str) -> bool:
        """激活预测。"""
        with self._lock:
            if prediction_id in self._predictions:
                self._predictions[prediction_id].status = STATUS_ACTIVE
                return True
            return False
    
    def resolve_prediction(self, 
                           prediction_id: str, 
                           outcome: str,
                           result: str) -> bool:
        """解决预测。"""
        with self._lock:
            if prediction_id in self._predictions:
                self._predictions[prediction_id].status = STATUS_RESOLVED
                return True
            return False
    
    def verify_outcome(self, 
                       prediction_id: str, 
                       outcome: str,
                       result: str,
                       confidence_delta: float = 0.0) -> Optional[OutcomeVerification]:
        """验证预测结果。"""
        with self._lock:
            if prediction_id not in self._predictions:
                return None
            
            # 更新置信度
            pred = self._predictions[prediction_id]
            if outcome == OUTCOME_CORRECT:
                pred.confidence = min(1.0, pred.confidence + abs(confidence_delta))
            elif outcome == OUTCOME_FAILED:
                pred.confidence = max(0.0, pred.confidence - abs(confidence_delta))
            
            # 创建验证记录
            ver_id = f"{VERIFICATION_KEY_PREFIX}{int(time.time())}_{self._next_id()}"
            verification = OutcomeVerification(
                verification_id=ver_id,
                prediction_id=prediction_id,
                outcome=outcome,
                result=result,
                confidence_change=confidence_delta,
                verified_at=time.time()
            )
            self._verifications[ver_id] = verification
            
            return verification
    
    def get_predictions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取预测列表。"""
        with self._lock:
            result = []
            for pred in self._predictions.values():
                if status and pred.status != status:
                    continue
                result.append(pred.to_dict())
            return result
    
    def get_verification(self, prediction_id: str) -> List[Dict[str, Any]]:
        """获取验证记录。"""
        with self._lock:
            return [v.to_dict() for v in self._verifications.values() 
                    if v.prediction_id == prediction_id]
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态。"""
        with self._lock:
            predictions = list(self._predictions.values())
            return {
                "ok": True,
                "engine": "prediction",
                "version": "1.0.0",
                "prediction_count": len(predictions),
                "active_count": sum(1 for p in predictions if p.status == STATUS_ACTIVE),
                "resolved_count": sum(1 for p in predictions if p.status == STATUS_RESOLVED),
                "pending_count": sum(1 for p in predictions if p.status == STATUS_PENDING),
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }


# 单例
_engine: Optional[PredictionEngine] = None
_engine_lock = threading.Lock()


def get_prediction_engine() -> PredictionEngine:
    """获取预测引擎单例。"""
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = PredictionEngine()
        return _engine


def reset_prediction_engine():
    """重置引擎（测试用）。"""
    global _engine
    with _engine_lock:
        _engine = PredictionEngine()