#!/usr/bin/env python3
"""Intelligence Memory Loop — 智能洞察反馈与沉淀循环。

职责：
- 收集用户对 Intelligence Feed 的反馈
- 将有用洞察沉淀为 Memory
- 管理 Feed 生命周期状态
- 准备 Prediction Ledger 基础结构

约束：
- 不修改 AgentRuntime
- 不修改 Planner
- 不修改 Tool Execution
- 不修改 Memory Schema
- 不新建数据库
- 只使用现有 Memory Intelligence 能力
"""

from __future__ import annotations

import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


# 反馈类型
FEEDBACK_USEFUL = "useful"
FEEDBACK_IGNORE = "ignore"
FEEDBACK_PROCESSED = "processed"

# Feed 生命周期状态
STATUS_NEW = "new"
STATUS_SEEN = "seen"
STATUS_ACKNOWLEDGED = "acknowledged"
STATUS_ACTIONED = "actioned"
STATUS_ARCHIVED = "archived"

# 内存存储键
FEEDBACK_KEY_PREFIX = "intel_feedback_"
MEMORY_TYPE_INTELLIGENCE = "intelligence_feedback"


class IntelligenceMemoryLoop:
    """智能记忆循环管理器。"""
    
    def __init__(self):
        self._lock = threading.Lock()
        # 反馈存储: item_id -> {feedback, timestamp, status}
        self._feedbacks: Dict[str, Dict[str, Any]] = {}
        # Feed 状态跟踪: item_id -> status
        self._feed_statuses: Dict[str, str] = {}
        # Prediction Ledger 基础结构
        self._prediction_ledger: List[Dict[str, Any]] = []
    
    def get_feedback(self, item_id: str) -> Optional[Dict[str, Any]]:
        """获取指定条目的反馈。"""
        with self._lock:
            return self._feedbacks.get(item_id)
    
    def set_feedback(self, item_id: str, feedback: str, insight: str = "") -> Dict[str, Any]:
        """设置用户反馈。"""
        if feedback not in [FEEDBACK_USEFUL, FEEDBACK_IGNORE, FEEDBACK_PROCESSED]:
            raise ValueError(f"Invalid feedback type: {feedback}")
        
        with self._lock:
            self._feedbacks[item_id] = {
                "item_id": item_id,
                "feedback": feedback,
                "insight": insight,
                "timestamp": time.time(),
                "status": self._get_feedback_status(feedback)
            }
            
            # 更新 Feed 生命周期状态
            self._update_feed_status(item_id, feedback)
            
            # 如果是 useful 或 processed，生成 Memory
            if feedback in [FEEDBACK_USEFUL, FEEDBACK_PROCESSED]:
                self._create_memory_record(item_id, feedback, insight)
        
        return self._feedbacks[item_id]
    
    def get_all_feedbacks(self) -> List[Dict[str, Any]]:
        """获取所有反馈。"""
        with self._lock:
            return list(self._feedbacks.values())
    
    def get_feed_status(self, item_id: str) -> str:
        """获取 Feed 生命周期状态。"""
        with self._lock:
            return self._feed_statuses.get(item_id, STATUS_NEW)
    
    def _get_feedback_status(self, feedback: str) -> str:
        """根据反馈类型确定状态。"""
        status_map = {
            FEEDBACK_USEFUL: STATUS_ACKNOWLEDGED,
            FEEDBACK_IGNORE: STATUS_ARCHIVED,
            FEEDBACK_PROCESSED: STATUS_ACTIONED
        }
        return status_map.get(feedback, STATUS_SEEN)
    
    def _update_feed_status(self, item_id: str, feedback: str):
        """更新 Feed 生命周期状态。"""
        self._feed_statuses[item_id] = self._get_feedback_status(feedback)
    
    def _create_memory_record(self, item_id: str, feedback: str, insight: str):
        """创建 Memory Intelligence 记录。
        
        使用现有 memory 模块写入，不修改表结构。
        """
        try:
            from memory import add_memory
            content = f"智能洞察反馈: {feedback}"
            title = f"Insight: {item_id[:8]}"
            
            add_memory(
                event_type=MEMORY_TYPE_INTELLIGENCE,
                content=content,
                title=title,
                tags=["intelligence", "feedback", feedback],
                visibility=1
            )
        except Exception as e:
            # 记录失败但不影响主流程
            pass
    
    def add_prediction_ledger_entry(self, insight_id: str, prediction: str, confidence: float = 0.5) -> Dict[str, Any]:
        """添加 Prediction Ledger 条目（基础结构）。"""
        entry = {
            "prediction_id": f"pred_{int(time.time() * 1000)}",
            "insight_id": insight_id,
            "prediction": prediction,
            "confidence": confidence,
            "created_at": time.time(),
            "status": "pending"
        }
        with self._lock:
            self._prediction_ledger.append(entry)
        return entry
    
    def get_prediction_ledger(self) -> List[Dict[str, Any]]:
        """获取 Prediction Ledger。"""
        with self._lock:
            return list(self._prediction_ledger)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息。"""
        with self._lock:
            feedback_count = len(self._feedbacks)
            useful_count = sum(1 for f in self._feedbacks.values() if f["feedback"] == FEEDBACK_USEFUL)
            ignore_count = sum(1 for f in self._feedbacks.values() if f["feedback"] == FEEDBACK_IGNORE)
            processed_count = sum(1 for f in self._feedbacks.values() if f["feedback"] == FEEDBACK_PROCESSED)
            
            return {
                "total_feedbacks": feedback_count,
                "useful": useful_count,
                "ignore": ignore_count,
                "processed": processed_count,
                "prediction_ledger_size": len(self._prediction_ledger),
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }


# 单例
_loop: Optional[IntelligenceMemoryLoop] = None
_loop_lock = threading.Lock()


def get_memory_loop() -> IntelligenceMemoryLoop:
    """获取 Intelligence Memory Loop 单例。"""
    global _loop
    with _loop_lock:
        if _loop is None:
            _loop = IntelligenceMemoryLoop()
        return _loop


def handle_feedback(item_id: str, feedback: str, insight: str = "") -> Dict[str, Any]:
    """处理用户反馈。"""
    loop = get_memory_loop()
    result = loop.set_feedback(item_id, feedback, insight)
    return {
        "ok": True,
        "feedback": result
    }


def get_status() -> Dict[str, Any]:
    """获取 Intelligence Memory Loop 状态。"""
    loop = get_memory_loop()
    return {
        "ok": True,
        "module": "intelligence_memory_loop",
        "version": "1.0.0",
        "stats": loop.get_stats(),
        "feedbacks": loop.get_all_feedbacks(),
        "prediction_ledger": loop.get_prediction_ledger(),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


# 模块入口
if __name__ == "__main__":
    import json
    result = get_status()
    print(json.dumps(result, ensure_ascii=False, indent=2))
