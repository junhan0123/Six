#!/usr/bin/env python3
"""Intelligence Feed — 统一智能信息流。

职责：
- 聚合所有 Intelligence 模块数据
- 生成统一格式的 Feed
- 按优先级排序

约束：
- 只读聚合，不修改原模块
- 不创建数据库
- 不引入新执行系统
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Any, List, Optional


# Feed 类型常量
FEED_TYPE_MEMORY = "memory"
FEED_TYPE_KNOWLEDGE = "knowledge"
FEED_TYPE_WORLD = "world"
FEED_TYPE_PROACTIVE = "proactive"

# 优先级范围
PRIORITY_HIGH = 8   # 重要提醒
PRIORITY_MEDIUM = 5  # 普通洞察
PRIORITY_LOW = 1     # 信息展示


class FeedItem:
    """Feed 条目模型。"""
    
    def __init__(
        self,
        item_id: str,
        feed_type: str,
        priority: int,
        title: str,
        content: str,
        source: str,
        timestamp: Optional[float] = None
    ):
        self.item_id = item_id
        self.feed_type = feed_type
        self.priority = max(1, min(10, priority))  # 限制 1-10
        self.title = title
        self.content = content
        self.source = source
        self.timestamp = timestamp or time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.item_id,
            "type": self.feed_type,
            "priority": self.priority,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp,
            "relative_time": self._relative_time()
        }
    
    def _relative_time(self) -> str:
        """计算相对时间。"""
        ago = time.time() - self.timestamp
        if ago < 60:
            return "刚刚"
        elif ago < 3600:
            return f"{int(ago // 60)} 分钟前"
        elif ago < 86400:
            return f"{int(ago // 3600)} 小时前"
        else:
            return f"{int(ago // 86400)} 天前"


def get_feed(limit: int = 20, feed_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """获取统一智能 Feed。
    
    Args:
        limit: 返回条目数量限制
        feed_types: 过滤类型，None 表示全部
    
    Returns:
        {
            "ok": bool,
            "feed": [...],
            "stats": {...},
            "generated_at": str
        }
    """
    feed_items: List[FeedItem] = []
    
    # 1. Memory Feed
    try:
        feed_items.extend(_collect_memory_feed())
    except Exception as e:
        pass
    
    # 2. Knowledge Feed
    try:
        feed_items.extend(_collect_knowledge_feed())
    except Exception as e:
        pass
    
    # 3. World Model Feed
    try:
        feed_items.extend(_collect_world_feed())
    except Exception as e:
        pass
    
    # 4. Proactive Feed
    try:
        feed_items.extend(_collect_proactive_feed())
    except Exception as e:
        pass
    
    # 过滤类型
    if feed_types:
        feed_items = [item for item in feed_items if item.feed_type in feed_types]
    
    # 按优先级排序（高优先级在前）
    feed_items.sort(key=lambda x: (-x.priority, -x.timestamp))
    
    # 限制数量
    feed_items = feed_items[:limit]
    
    # 统计信息
    stats = {
        "total_items": len(feed_items),
        "by_type": _count_by_type(feed_items),
        "by_priority": _count_by_priority(feed_items),
        "high_priority": len([i for i in feed_items if i.priority >= PRIORITY_HIGH]),
        "medium_priority": len([i for i in feed_items if PRIORITY_MEDIUM <= i.priority < PRIORITY_HIGH]),
        "low_priority": len([i for i in feed_items if i.priority < PRIORITY_MEDIUM])
    }
    
    return {
        "ok": True,
        "feed": [item.to_dict() for item in feed_items],
        "stats": stats,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def _collect_memory_feed() -> List[FeedItem]:
    """收集 Memory Feed。"""
    items = []
    
    try:
        from memory_intelligence import get_intelligence_status
        status = get_intelligence_status()
        
        # 高重要性记忆
        total = status.get("total", 0)
        avg_importance = status.get("average_importance", 0)
        
        if total > 0:
            items.append(FeedItem(
                item_id=f"memory-stats-{int(time.time())}",
                feed_type=FEED_TYPE_MEMORY,
                priority=int(avg_importance * 4) + 3,  # 0-10 映射
                title=f"记忆统计: {total} 条",
                content=f"平均重要性: {avg_importance:.2f}",
                source="Memory Intelligence",
                timestamp=time.time()
            ))
        
        # 新增/更新的记忆
        recent = status.get("recent_events", [])
        for evt in recent[:5]:
            items.append(FeedItem(
                item_id=f"memory-{evt.get('id', 'unknown')}",
                feed_type=FEED_TYPE_MEMORY,
                priority=PRIORITY_MEDIUM,
                title=evt.get("title", "新记忆"),
                content=evt.get("detail", "")[:100],
                source="Memory Intelligence",
                timestamp=evt.get("timestamp", time.time())
            ))
            
    except Exception:
        pass
    
    return items


def _collect_knowledge_feed() -> List[FeedItem]:
    """收集 Knowledge Feed。"""
    items = []
    
    try:
        from knowledge_intelligence import get_status as get_knowledge_status
        status = get_knowledge_status()
        
        total_docs = status.get("total_documents", 0)
        quality_score = status.get("quality_score", 0)
        topics = status.get("topics", {})
        
        if total_docs > 0:
            items.append(FeedItem(
                item_id=f"knowledge-stats-{int(time.time())}",
                feed_type=FEED_TYPE_KNOWLEDGE,
                priority=PRIORITY_LOW,
                title=f"知识库: {total_docs} 文档",
                content=f"质量评分: {quality_score:.2f}",
                source="Knowledge Intelligence",
                timestamp=time.time()
            ))
        
        # 高频主题
        for topic, count in list(topics.items())[:3]:
            items.append(FeedItem(
                item_id=f"knowledge-topic-{topic}",
                feed_type=FEED_TYPE_KNOWLEDGE,
                priority=PRIORITY_LOW,
                title=f"热门主题: {topic}",
                content=f"{count} 个文档",
                source="Knowledge Intelligence",
                timestamp=time.time()
            ))
            
    except Exception:
        pass
    
    return items


def _collect_world_feed() -> List[FeedItem]:
    """收集 World Model Feed。"""
    items = []
    
    try:
        from gfe_intelligence import status as get_world_status
        status = get_world_status()
        
        total_events = status.get("total_events", 0)
        risk_level = status.get("risk_level", "unknown")
        severity = status.get("overall_severity", 0)
        
        # 世界风险等级
        priority = int(severity * 5) + 3  # 0-5 映射到 3-8
        items.append(FeedItem(
            item_id=f"world-risk-{int(time.time())}",
            feed_type=FEED_TYPE_WORLD,
            priority=priority,
            title=f"世界风险: {risk_level}",
            content=f"严重度: {severity:.2f}, 事件数: {total_events}",
            source="World Model",
            timestamp=time.time()
        ))
        
        # 趋势类别
        trending = status.get("trending_categories", [])
        for cat in trending[:2]:
            cat_name = cat.get("category", "unknown") if isinstance(cat, dict) else str(cat)
            cat_count = cat.get("count", 0) if isinstance(cat, dict) else 0
            items.append(FeedItem(
                item_id=f"world-trend-{cat_name}",
                feed_type=FEED_TYPE_WORLD,
                priority=PRIORITY_MEDIUM,
                title=f"趋势类别: {cat_name}",
                content=f"{cat_count} 个相关事件",
                source="World Model",
                timestamp=time.time()
            ))
            
    except Exception:
        pass
    
    return items


def _collect_proactive_feed() -> List[FeedItem]:
    """收集 Proactive Feed。"""
    items = []
    
    try:
        from proactive_intelligence import status as get_proactive_status
        status = get_proactive_status()
        
        observations_count = status.get("observations_count", 0)
        suggestions_count = status.get("suggestions_count", 0)
        
        items.append(FeedItem(
            item_id=f"proactive-stats-{int(time.time())}",
            feed_type=FEED_TYPE_PROACTIVE,
            priority=PRIORITY_MEDIUM,
            title=f"主动智能: {observations_count} 观察",
            content=f"{suggestions_count} 条建议待处理",
            source="Proactive Intelligence",
            timestamp=time.time()
        ))
        
        # 高重要性观察
        high_obs = status.get("high_importance_observations", [])
        for obs in high_obs[:3]:
            items.append(FeedItem(
                item_id=f"proactive-obs-{obs.get('type', 'unknown')}",
                feed_type=FEED_TYPE_PROACTIVE,
                priority=int(obs.get("importance", 0.5) * 6) + 4,
                title=f"重要观察: {obs.get('type', 'unknown')}",
                content=obs.get("detail", "")[:80],
                source="Proactive Intelligence",
                timestamp=obs.get("timestamp", time.time())
            ))
            
    except Exception:
        pass
    
    return items


def _count_by_type(feed_items: List[FeedItem]) -> Dict[str, int]:
    """按类型统计。"""
    counts = {}
    for item in feed_items:
        counts[item.feed_type] = counts.get(item.feed_type, 0) + 1
    return counts


def _count_by_priority(feed_items: List[FeedItem]) -> Dict[str, int]:
    """按优先级统计。"""
    counts = {"high": 0, "medium": 0, "low": 0}
    for item in feed_items:
        if item.priority >= PRIORITY_HIGH:
            counts["high"] += 1
        elif item.priority >= PRIORITY_MEDIUM:
            counts["medium"] += 1
        else:
            counts["low"] += 1
    return counts


# 模块入口
if __name__ == "__main__":
    result = get_feed(limit=10)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
