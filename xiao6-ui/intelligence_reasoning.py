#!/usr/bin/env python3
"""S147 — Intelligence Reasoning Layer 智能推理层。

职责：
- 读取已有 Intelligence 模块数据
- 生成解释结果
- 建立证据链
- 提供推理快照

约束：
- 不修改 AgentRuntime
- 不修改 Planner
- 不修改 Tool Execution
- 不修改 Memory Schema
- 不新建数据库
- 不引入新 AI 模型
- 不自动执行动作
"""

from __future__ import annotations

import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

# 证据类型
EVIDENCE_WORLD = "world"
EVIDENCE_KNOWLEDGE = "knowledge"
EVIDENCE_MEMORY = "memory"
EVIDENCE_FORESIGHT = "foresight"

# 来源常量
SOURCE_WORLD = "world"
SOURCE_KNOWLEDGE = "knowledge"
SOURCE_MEMORY = "memory"
SOURCE_FORESIGHT = "foresight"

# 内存存储键
REASONING_KEY_PREFIX = "reason_"
EVIDENCE_KEY_PREFIX = "ev_"


@dataclass
class EvidenceItem:
    """证据项。"""
    evidence_id: str
    evidence_type: str  # world, knowledge, memory, foresight
    content: str
    source: str
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "type": self.evidence_type,
            "content": self.content,
            "source": self.source,
            "confidence": round(self.confidence, 2)
        }


@dataclass
class ReasoningSnapshot:
    """推理快照。"""
    topic: str
    reasoning: str
    why: str
    impact: str
    confidence: float
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "reasoning": self.reasoning,
            "why": self.why,
            "impact": self.impact,
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp
        }


@dataclass
class ReasoningResult:
    """推理结果。"""
    reasoning_id: str
    topic: str
    explanation: str
    evidence: List[EvidenceItem]
    snapshot: Optional[ReasoningSnapshot]
    confidence: float
    source: str
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "reasoning_id": self.reasoning_id,
            "topic": self.topic,
            "explanation": self.explanation,
            "evidence": [e.to_dict() for e in self.evidence],
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
            "confidence": round(self.confidence, 2),
            "source": self.source,
            "timestamp": self.timestamp
        }


class ReasoningEngine:
    """智能推理引擎。
    
    职责：
    - 从已有 Intelligence 模块读取数据
    - 生成解释结果
    - 建立证据链
    - 提供推理快照
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        # 推理结果缓存
        self._reasonings: Dict[str, ReasoningResult] = {}
        # 证据链
        self._evidence_chain: List[EvidenceItem] = []
        # 最后更新时间
        self._last_update = 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """获取推理引擎状态。"""
        return {
            "ok": True,
            "engine": "reasoning",
            "version": "1.0.0",
            "reasonings_count": len(self._reasonings),
            "evidence_count": len(self._evidence_chain),
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
    
    def get_reasonings(self, limit: int = 20) -> Dict[str, Any]:
        """获取推理结果列表。"""
        reasonings = list(self._reasonings.values())
        # 按置信度排序
        reasonings.sort(key=lambda x: x.confidence, reverse=True)
        return {
            "ok": True,
            "reasonings": [r.to_dict() for r in reasonings[:limit]],
            "total": len(reasonings)
        }
    
    def add_evidence(self, evidence_type: str, content: str, 
                     source: str, confidence: float) -> Optional[EvidenceItem]:
        """添加证据。"""
        if confidence < 0 or confidence > 1:
            return None
        
        evidence_id = f"{EVIDENCE_KEY_PREFIX}{int(time.time())}_{len(self._evidence_chain)}"
        evidence = EvidenceItem(
            evidence_id=evidence_id,
            evidence_type=evidence_type,
            content=content,
            source=source,
            confidence=confidence
        )
        
        with self._lock:
            self._evidence_chain.append(evidence)
            self._last_update = time.time()
        
        return evidence
    
    def add_reasoning(self, topic: str, explanation: str, evidence: List[EvidenceItem],
                      snapshot: Optional[ReasoningSnapshot], confidence: float,
                      source: str) -> Optional[ReasoningResult]:
        """添加推理结果。"""
        if confidence < 0 or confidence > 1:
            return None
        
        reasoning_id = f"{REASONING_KEY_PREFIX}{int(time.time())}_{len(self._reasonings)}"
        result = ReasoningResult(
            reasoning_id=reasoning_id,
            topic=topic,
            explanation=explanation,
            evidence=evidence,
            snapshot=snapshot,
            confidence=confidence,
            source=source,
            timestamp=time.time()
        )
        
        with self._lock:
            self._reasonings[reasoning_id] = result
            self._last_update = time.time()
        
        return result
    
    def refresh_from_intelligence(self, memory: Dict[str, Any], knowledge: Dict[str, Any],
                                   world: Dict[str, Any], foresight: Dict[str, Any],
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """从已有 Intelligence 模块刷新推理。"""
        updated = 0
        
        # 1. World Model 推理
        world_events = world.get("events", [])
        world_risk = world.get("risk_level", "medium")
        
        if world_events:
            # 添加世界事件证据
            for event in world_events[:3]:
                self.add_evidence(
                    EVIDENCE_WORLD,
                    event.get("title", "世界事件"),
                    SOURCE_WORLD,
                    0.8
                )
            
            # 生成推理
            explanation = f"检测到 {len(world_events)} 个世界事件，风险等级为 {world_risk}"
            why = "世界风险评估基于历史数据和当前事件趋势分析"
            impact = "可能影响未来趋势判断和资源分配"
            
            snapshot = ReasoningSnapshot(
                topic=f"世界风险: {world_risk}",
                reasoning=explanation,
                why=why,
                impact=impact,
                confidence=0.75 if world_risk == "high" else 0.6,
                timestamp=time.time()
            )
            
            evidence = self._evidence_chain[-3:] if len(self._evidence_chain) >= 3 else self._evidence_chain.copy()
            self.add_reasoning(
                f"世界风险: {world_risk}",
                explanation,
                evidence,
                snapshot,
                0.75,
                SOURCE_WORLD
            )
            updated += 1
        
        # 2. Memory Intelligence 推理
        memory_count = memory.get("total", 0)
        if memory_count > 0:
            self.add_evidence(
                EVIDENCE_MEMORY,
                f"用户记忆库包含 {memory_count} 条记录",
                SOURCE_MEMORY,
                0.9
            )
            
            explanation = f"用户记忆库已积累 {memory_count} 条记录，反映用户兴趣和行为模式"
            why = "记忆积累帮助用户理解 Xiao6 的长期学习过程"
            impact = "可用于个性化推荐和上下文理解"
            
            snapshot = ReasoningSnapshot(
                topic="记忆积累分析",
                reasoning=explanation,
                why=why,
                impact=impact,
                confidence=0.85,
                timestamp=time.time()
            )
            
            self.add_reasoning(
                "记忆积累分析",
                explanation,
                [e for e in self._evidence_chain if e.evidence_type == EVIDENCE_MEMORY][-1:],
                snapshot,
                0.85,
                SOURCE_MEMORY
            )
            updated += 1
        
        # 3. Knowledge Intelligence 推理
        knowledge_docs = knowledge.get("total", 0)
        if knowledge_docs > 0:
            self.add_evidence(
                EVIDENCE_KNOWLEDGE,
                f"知识库包含 {knowledge_docs} 篇文档",
                SOURCE_KNOWLEDGE,
                0.85
            )
            
            explanation = f"知识库已积累 {knowledge_docs} 篇文档，覆盖多个领域知识"
            why = "知识储备是 Xiao6 提供准确回答的基础"
            impact = "影响问答质量和推荐精准度"
            
            snapshot = ReasoningSnapshot(
                topic="知识储备评估",
                reasoning=explanation,
                why=why,
                impact=impact,
                confidence=0.8,
                timestamp=time.time()
            )
            
            self.add_reasoning(
                "知识储备评估",
                explanation,
                [e for e in self._evidence_chain if e.evidence_type == EVIDENCE_KNOWLEDGE][-1:],
                snapshot,
                0.8,
                SOURCE_KNOWLEDGE
            )
            updated += 1
        
        # 4. Foresight 推理
        signals = foresight.get("signals", [])
        warnings = foresight.get("warnings", [])
        
        if signals or warnings:
            signal_titles = [s.get("title", "") for s in signals[:2]]
            if signal_titles:
                self.add_evidence(
                    EVIDENCE_FORESIGHT,
                    f"检测到 {len(signals)} 个趋势信号: {', '.join(signal_titles)}",
                    SOURCE_FORESIGHT,
                    0.7
                )
            
            if warnings:
                warn_levels = [w.get("level", "") for w in warnings[:2]]
                self.add_evidence(
                    EVIDENCE_FORESIGHT,
                    f"存在 {len(warnings)} 个预警: {', '.join(warn_levels)}",
                    SOURCE_FORESIGHT,
                    0.6
                )
            
            if signals:
                explanation = f"前瞻系统检测到 {len(signals)} 个趋势信号，表明系统正在积累智能洞察"
                why = "趋势信号来自对世界状态、知识库和记忆的持续分析"
                impact = "帮助用户了解系统关注的重点和未来方向"
                
                snapshot = ReasoningSnapshot(
                    topic="前瞻趋势分析",
                    reasoning=explanation,
                    why=why,
                    impact=impact,
                    confidence=0.7,
                    timestamp=time.time()
                )
                
                self.add_reasoning(
                    "前瞻趋势分析",
                    explanation,
                    [e for e in self._evidence_chain if e.evidence_type == EVIDENCE_FORESIGHT][-2:],
                    snapshot,
                    0.7,
                    SOURCE_FORESIGHT
                )
                updated += 1
        
        # 5. Context 推理
        contexts = context.get("contexts", [])
        if contexts:
            topic_names = [c.get("topic", "") for c in contexts[:2]]
            if topic_names:
                self.add_evidence(
                    EVIDENCE_KNOWLEDGE,
                    f"上下文引擎识别到 {len(contexts)} 个主题关联: {', '.join(topic_names)}",
                    SOURCE_KNOWLEDGE,
                    0.65
                )
                
                explanation = f"全局上下文引擎已识别 {len(contexts)} 个关联主题，建立了事件间的联系"
                why = "上下文融合帮助理解事件之间的深层关系"
                impact = "支持更精准的洞察推荐和决策辅助"
                
                snapshot = ReasoningSnapshot(
                    topic="上下文关联分析",
                    reasoning=explanation,
                    why=why,
                    impact=impact,
                    confidence=0.65,
                    timestamp=time.time()
                )
                
                self.add_reasoning(
                    "上下文关联分析",
                    explanation,
                    [e for e in self._evidence_chain if e.evidence_type == EVIDENCE_KNOWLEDGE][-1:],
                    snapshot,
                    0.65,
                    SOURCE_KNOWLEDGE
                )
                updated += 1
        
        self._last_update = time.time()
        
        return {
            "updated": updated,
            "total_reasonings": len(self._reasonings),
            "total_evidence": len(self._evidence_chain)
        }


# ============================================================
# Singleton
# ============================================================

_instance: Optional[ReasoningEngine] = None
_instance_lock = threading.Lock()


def get_reasoning_engine() -> ReasoningEngine:
    """获取单例推理引擎。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = ReasoningEngine()
        return _instance


def reset_reasoning_engine():
    """重置单例（用于测试）。"""
    global _instance
    with _instance_lock:
        _instance = None
