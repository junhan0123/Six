#!/usr/bin/env python3
"""S146 — Global Intelligence Context Layer 全局智能上下文层。

职责：
- 融合已有 Intelligence 模块数据
- 生成统一 Context
- 建立事件关系映射
- 准备因果关系图基础结构

约束：
- 不修改 AgentRuntime
- 不修改 Planner
- 不修改 Tool Execution
- 不修改 Memory Schema
- 不新建数据库
- 不引入新 AI 模型
- 只读现有数据
"""

from __future__ import annotations

import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

# 关系类型
RELATION_RELATED = "related"
RELATION_IMPACTS = "impacts"
RELATION_FOLLOWS = "follows"
RELATION_SIMILAR = "similar"

# 上下文来源
SOURCE_WORLD = "world"
SOURCE_MEMORY = "memory"
SOURCE_KNOWLEDGE = "knowledge"
SOURCE_FORESIGHT = "foresight"

# 内存存储键
CONTEXT_KEY_PREFIX = "ctx_"
RELATIONSHIP_KEY_PREFIX = "rel_"
CAUSAL_KEY_PREFIX = "causal_"


@dataclass
class ContextEntity:
    """上下文实体。"""
    entity_id: str
    name: str
    type: str  # event, topic, factor
    source: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "type": self.type,
            "source": self.source
        }


@dataclass
class EventRelation:
    """事件关系。"""
    source: str
    target: str
    relation: str  # related, impacts, follows, similar
    confidence: float
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp
        }


@dataclass
class CausalLink:
    """因果关系链接。"""
    cause: str
    effect: str
    confidence: float
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cause": self.cause,
            "effect": self.effect,
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp
        }


@dataclass
class IntelligenceContext:
    """智能上下文。"""
    context_id: str
    topic: str
    entities: List[ContextEntity]
    relations: List[EventRelation]
    importance: float  # 0-1
    source: str
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "topic": self.topic,
            "entities": [e.to_dict() for e in self.entities],
            "relations": [r.to_dict() for r in self.relations],
            "importance": round(self.importance, 2),
            "source": self.source,
            "timestamp": self.timestamp
        }


class ContextEngine:
    """全局智能上下文引擎。
    
    职责：
    - 从已有 Intelligence 模块读取数据
    - 生成统一 Context
    - 建立事件关系映射
    - 准备因果关系结构
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        # 上下文缓存
        self._contexts: Dict[str, IntelligenceContext] = {}
        # 事件关系
        self._relations: List[EventRelation] = []
        # 因果关系
        self._causal_links: List[CausalLink] = []
        # 最后更新时间
        self._last_update = 0.0
    
    def get_status(self) -> Dict[str, Any]:
        """获取上下文引擎状态。"""
        return {
            "ok": True,
            "engine": "context",
            "version": "1.0.0",
            "contexts_count": len(self._contexts),
            "relations_count": len(self._relations),
            "causal_count": len(self._causal_links),
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
    
    def get_contexts(self, limit: int = 20) -> Dict[str, Any]:
        """获取上下文列表。"""
        contexts = list(self._contexts.values())
        # 按重要性排序
        contexts.sort(key=lambda x: x.importance, reverse=True)
        return {
            "ok": True,
            "contexts": [c.to_dict() for c in contexts[:limit]],
            "total": len(contexts)
        }
    
    def add_context(self, topic: str, entities: List[ContextEntity],
                    importance: float, source: str) -> Optional[IntelligenceContext]:
        """添加上下文。"""
        if importance < 0 or importance > 1:
            return None
        
        context_id = f"{CONTEXT_KEY_PREFIX}{int(time.time())}_{len(self._contexts)}"
        context = IntelligenceContext(
            context_id=context_id,
            topic=topic,
            entities=entities,
            relations=[],
            importance=importance,
            source=source,
            timestamp=time.time()
        )
        
        with self._lock:
            self._contexts[context_id] = context
            self._last_update = time.time()
        
        return context
    
    def add_relation(self, source: str, target: str, relation: str, 
                     confidence: float) -> Optional[EventRelation]:
        """添加事件关系。"""
        if relation not in [RELATION_RELATED, RELATION_IMPACTS, RELATION_FOLLOWS, RELATION_SIMILAR]:
            return None
        if confidence < 0 or confidence > 1:
            return None
        
        relation_obj = EventRelation(
            source=source,
            target=target,
            relation=relation,
            confidence=confidence,
            timestamp=time.time()
        )
        
        with self._lock:
            self._relations.append(relation_obj)
            self._last_update = time.time()
        
        return relation_obj
    
    def add_causal_link(self, cause: str, effect: str, confidence: float) -> Optional[CausalLink]:
        """添加因果关系。"""
        if confidence < 0 or confidence > 1:
            return None
        
        link = CausalLink(
            cause=cause,
            effect=effect,
            confidence=confidence,
            timestamp=time.time()
        )
        
        with self._lock:
            self._causal_links.append(link)
            self._last_update = time.time()
        
        return link
    
    def refresh_from_intelligence(self, memory: Dict[str, Any], knowledge: Dict[str, Any],
                                   world: Dict[str, Any], foresight: Dict[str, Any]) -> Dict[str, Any]:
        """从已有 Intelligence 模块刷新上下文。"""
        updated = 0
        
        # 1. World Model 上下文
        world_events = world.get("events", [])
        world_risk = world.get("risk_level", "medium")
        
        if world_events:
            entities = []
            for event in world_events[:5]:
                entities.append(ContextEntity(
                    entity_id=f"world_{event.get('id', '')}",
                    name=event.get("title", "世界事件"),
                    type="event",
                    source=SOURCE_WORLD
                ))
            
            if entities:
                importance = 0.7 if world_risk == "high" else 0.5
                self.add_context(f"世界风险: {world_risk}", entities, importance, SOURCE_WORLD)
                updated += 1
                
                # 添加因果关系
                if len(world_events) > 1:
                    self.add_causal_link(
                        world_events[0].get("title", "事件A"),
                        world_events[1].get("title", "事件B"),
                        0.6
                    )
        
        # 2. Memory Intelligence 上下文
        memory_count = memory.get("total", 0)
        if memory_count > 0:
            entities = [ContextEntity(
                entity_id="memory_main",
                name="用户记忆库",
                type="topic",
                source=SOURCE_MEMORY
            )]
            self.add_context(f"记忆积累: {memory_count} 条", entities, 0.4, SOURCE_MEMORY)
            updated += 1
        
        # 3. Knowledge Intelligence 上下文
        knowledge_docs = knowledge.get("total", 0)
        if knowledge_docs > 0:
            entities = [ContextEntity(
                entity_id="knowledge_main",
                name="知识库",
                type="topic",
                source=SOURCE_KNOWLEDGE
            )]
            self.add_context(f"知识储备: {knowledge_docs} 文档", entities, 0.3, SOURCE_KNOWLEDGE)
            updated += 1
        
        # 4. Foresight 上下文
        signals = foresight.get("signals", [])
        warnings = foresight.get("warnings", [])
        
        if signals or warnings:
            entities = []
            for sig in signals[:3]:
                entities.append(ContextEntity(
                    entity_id=f"signal_{sig.get('signal_id', '')}",
                    name=sig.get("title", "趋势信号"),
                    type="event",
                    source=SOURCE_FORESIGHT
                ))
            
            if entities:
                importance = max([s.get("confidence", 0.5) for s in signals]) if signals else 0.5
                self.add_context("前瞻信号汇总", entities, importance, SOURCE_FORESIGHT)
                updated += 1
        
        # 建立事件关系
        if len(signals) >= 2:
            self.add_relation(
                signals[0].get("title", ""),
                signals[1].get("title", ""),
                RELATION_RELATED,
                0.7
            )
        
        self._last_update = time.time()
        
        return {
            "updated": updated,
            "total_contexts": len(self._contexts),
            "total_relations": len(self._relations),
            "total_causal": len(self._causal_links)
        }


# ============================================================
# Singleton
# ============================================================

_instance: Optional[ContextEngine] = None
_instance_lock = threading.Lock()


def get_context_engine() -> ContextEngine:
    """获取单例上下文引擎。"""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = ContextEngine()
        return _instance


def reset_context_engine():
    """重置单例（用于测试）。"""
    global _instance
    with _instance_lock:
        _instance = None
