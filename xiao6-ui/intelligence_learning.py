#!/usr/bin/env python3
"""S150 — Intelligence Learning Feedback Layer 学习反馈层。

职责：
- 分析 Prediction Ledger 历史结果
- 计算预测准确率
- 建立来源可靠性统计
- 生成洞察质量评分

约束：
- 不修改 AgentRuntime
- 不修改 Planner
- 不修改 Tool Execution
- 不修改 Memory Schema
- 不创建新数据库
- 不引入新 AI 模型
- 不自动执行学习动作
- 不修改模型参数
"""

from __future__ import annotations

import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict

# 内存存储键
LEARNING_KEY_PREFIX = "learn_"


@dataclass
class LearningRecord:
    """学习记录。"""
    learning_id: str
    source_type: str
    topic: str
    prediction_count: int
    correct_count: int
    failed_count: int
    accuracy: float
    confidence_delta: float
    created_at: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "learning_id": self.learning_id,
            "source_type": self.source_type,
            "topic": self.topic,
            "prediction_count": self.prediction_count,
            "correct_count": self.correct_count,
            "failed_count": self.failed_count,
            "accuracy": round(self.accuracy, 2),
            "confidence_delta": round(self.confidence_delta, 2),
            "created_at": self.created_at,
            "timestamp": datetime.fromtimestamp(self.created_at).isoformat()
        }


@dataclass
class SourceReliability:
    """来源可靠性。"""
    source: str
    accuracy: float
    total_predictions: int
    correct_predictions: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "accuracy": round(self.accuracy, 2),
            "total_predictions": self.total_predictions,
            "correct_predictions": self.correct_predictions
        }


class LearningEngine:
    """学习引擎。"""
    
    def __init__(self):
        self._records: Dict[str, LearningRecord] = {}
        self._source_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
        self._lock = threading.Lock()
        self._last_id = 0
    
    def _next_id(self) -> int:
        self._last_id += 1
        return self._last_id
    
    def analyze_predictions(self, predictions: List[Dict[str, Any]], 
                            verifications: List[Dict[str, Any]]) -> List[LearningRecord]:
        """分析预测历史记录。"""
        with self._lock:
            # 按主题和来源分组统计
            stats: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
                lambda: defaultdict(lambda: {"total": 0, "correct": 0})
            )
            
            for ver in verifications:
                pred_id = ver.get("prediction_id", "")
                outcome = ver.get("outcome", "")
                
                # 找到对应的预测记录
                for pred in predictions:
                    if pred.get("prediction_id") == pred_id:
                        topic = pred.get("topic", "unknown")
                        source = pred.get("source", "unknown")
                        key = f"{source}:{topic}"
                        
                        stats[key]["total"] += 1
                        if outcome == "correct":
                            stats[key]["correct"] += 1
                        
                        # 更新来源统计
                        self._source_stats[source]["total"] += 1
                        if outcome == "correct":
                            self._source_stats[source]["correct"] += 1
                        break
            
            # 生成学习记录
            records = []
            for key, topic_stats in stats.items():
                source, topic = key.split(":", 1)
                total = topic_stats["total"]
                correct = topic_stats["correct"]
                accuracy = correct / total if total > 0 else 0.0
                
                record = LearningRecord(
                    learning_id=f"{LEARNING_KEY_PREFIX}{int(time.time())}_{self._next_id()}",
                    source_type=source,
                    topic=topic,
                    prediction_count=total,
                    correct_count=correct,
                    failed_count=total - correct,
                    accuracy=accuracy,
                    confidence_delta=accuracy - 0.5,  # 基准0.5
                    created_at=time.time()
                )
                records.append(record)
                self._records[record.learning_id] = record
            
            return records
    
    def get_source_reliability(self) -> List[SourceReliability]:
        """获取来源可靠性统计。"""
        with self._lock:
            result = []
            for source, stats in self._source_stats.items():
                total = stats["total"]
                correct = stats["correct"]
                accuracy = correct / total if total > 0 else 0.0
                
                result.append(SourceReliability(
                    source=source,
                    accuracy=accuracy,
                    total_predictions=total,
                    correct_predictions=correct
                ))
            return result
    
    def calculate_insight_quality_score(self, 
                                         prediction_accuracy: float,
                                         user_feedback_score: float = 0.5,
                                         confidence_history: Optional[List[float]] = None) -> float:
        """计算洞察质量评分 (0-100)。"""
        # 权重分配
        accuracy_weight = 0.5
        feedback_weight = 0.3
        confidence_weight = 0.2
        
        # 置信度历史平均分
        avg_confidence = 0.5
        if confidence_history and len(confidence_history) > 0:
            avg_confidence = sum(confidence_history) / len(confidence_history)
        
        # 计算得分
        score = (
            prediction_accuracy * accuracy_weight * 100 +
            user_feedback_score * feedback_weight * 100 +
            avg_confidence * confidence_weight * 100
        )
        
        return min(100.0, max(0.0, score))
    
    def get_learning_records(self, source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取学习记录。"""
        with self._lock:
            result = []
            for record in self._records.values():
                if source_type and record.source_type != source_type:
                    continue
                result.append(record.to_dict())
            return result
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态。"""
        with self._lock:
            records = list(self._records.values())
            total_accuracy = 0.0
            if records:
                total_accuracy = sum(r.accuracy for r in records) / len(records)
            
            return {
                "ok": True,
                "engine": "learning",
                "version": "1.0.0",
                "records_count": len(records),
                "accuracy": round(total_accuracy, 2),
                "sources_analyzed": len(self._source_stats),
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }


# 单例
_engine: Optional[LearningEngine] = None
_engine_lock = threading.Lock()


def get_learning_engine() -> LearningEngine:
    """获取学习引擎单例。"""
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = LearningEngine()
        return _engine


def reset_learning_engine():
    """重置引擎（测试用）。"""
    global _engine
    with _engine_lock:
        _engine = LearningEngine()