#!/usr/bin/env python3
"""Intelligence Feed Enhancement — 智能洞察驾驶舱。

职责：
- Feed Ranking Engine（Insight Score）
- Feed 内容增强（summary/impact/recommendation）
- Activity Center 联动
- 保持 API 兼容

约束：
- 只读聚合，不修改原模块
- 不创建数据库
- 不引入新 AI 模型
"""

from __future__ import annotations

import time
import math
from datetime import datetime
from typing import Dict, Any, List, Optional


# Feed 类型常量
FEED_TYPE_MEMORY = "memory"
FEED_TYPE_KNOWLEDGE = "knowledge"
FEED_TYPE_WORLD = "world"
FEED_TYPE_PROACTIVE = "proactive"
FEED_TYPE_INTELLIGENCE = "intelligence"  # 新增

# 优先级范围
PRIORITY_HIGH = 8
PRIORITY_MEDIUM = 5
PRIORITY_LOW = 1

# 时间衰减因子（天）
FRESHNESS_DECAY_DAYS = 7


class FeedItem:
    """增强的 Feed 条目模型。"""
    
    def __init__(
        self,
        item_id: str,
        feed_type: str,
        priority: int,
        title: str,
        content: str,
        source: str,
        timestamp: Optional[float] = None,
        summary: str = "",
        impact: str = "",
        recommendation: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.item_id = item_id
        self.feed_type = feed_type
        self.priority = max(1, min(10, priority))
        self.title = title
        self.content = content
        self.source = source
        self.timestamp = timestamp or time.time()
        self.summary = summary
        self.impact = impact
        self.recommendation = recommendation
        self.metadata = metadata or {}
        
        # 计算 Insight Score
        self.score = self._calculate_insight_score()
        self.rank_reason = self._generate_rank_reason()
    
    def _calculate_insight_score(self) -> float:
        """计算 Insight Score。
        
        score = priority + freshness + impact + relevance
        """
        # Priority 贡献 (0-10)
        priority_score = self.priority
        
        # Freshness 贡献 (0-2)
        freshness_score = self._calculate_freshness()
        
        # Impact 贡献 (0-2)
        impact_score = self._calculate_impact()
        
        # Relevance 贡献 (0-1)
        relevance_score = self._calculate_relevance()
        
        return round(min(15.0, priority_score + freshness_score + impact_score + relevance_score), 1)
    
    def _calculate_freshness(self) -> float:
        """计算新鲜度得分 (0-2)。"""
        ago = time.time() - self.timestamp
        days = ago / 86400
        
        if days < 0.1:  # 1小时内
            return 2.0
        elif days < 1:  # 1天内
            return 1.5
        elif days < FRESHNESS_DECAY_DAYS:
            return max(0, 2.0 * (1 - days / FRESHNESS_DECAY_DAYS))
        else:
            return 0
    
    def _calculate_impact(self) -> float:
        """计算影响度得分 (0-2)。"""
        if self.priority >= PRIORITY_HIGH:
            return 2.0
        elif self.priority >= PRIORITY_MEDIUM:
            return 1.5
        else:
            return 1.0
    
    def _calculate_relevance(self) -> float:
        """计算相关性得分 (0-1)。"""
        # 基于来源类型
        relevance_map = {
            FEED_TYPE_WORLD: 1.0,
            FEED_TYPE_PROACTIVE: 0.9,
            FEED_TYPE_MEMORY: 0.7,
            FEED_TYPE_KNOWLEDGE: 0.6
        }
        return relevance_map.get(self.feed_type, 0.5)
    
    def _generate_rank_reason(self) -> str:
        """生成排序理由。"""
        parts = []
        
        if self.priority >= PRIORITY_HIGH:
            parts.append("高优先级")
        elif self.priority >= PRIORITY_MEDIUM:
            parts.append("中优先级")
        
        freshness = self._calculate_freshness()
        if freshness >= 1.5:
            parts.append("近期变化")
        
        if self.impact:
            parts.append("高影响")
        
        return " + ".join(parts) if parts else "综合评分"
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（保持向后兼容）。"""
        result = {
            "id": self.item_id,
            "type": self.feed_type,
            "priority": self.priority,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp,
            "relative_time": self._relative_time(),
            # 新增字段
            "score": self.score,
            "rank_reason": self.rank_reason,
            "summary": self.summary,
            "impact": self.impact,
            "recommendation": self.recommendation
        }
        return result
    
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
    
    def to_activity(self) -> Dict[str, Any]:
        """转换为 Activity 格式（用于联动）。"""
        return {
            "activity_id": self.item_id,
            "type": "intelligence",
            "title": self.title,
            "status": "completed",
            "description": self.summary or self.content,
            "intent_type": self.feed_type,
            "timestamp": self.timestamp,
            "metadata": {
                "score": self.score,
                "priority": self.priority,
                "source": self.source,
                "impact": self.impact,
                "recommendation": self.recommendation
            }
        }


def get_feed(limit: int = 20, feed_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """获取增强版智能 Feed。"""
    feed_items: List[FeedItem] = []
    
    # 收集所有来源数据
    feed_items.extend(_collect_memory_feed())
    feed_items.extend(_collect_knowledge_feed())
    feed_items.extend(_collect_world_feed())
    feed_items.extend(_collect_proactive_feed())
    
    # 过滤类型
    if feed_types:
        feed_items = [item for item in feed_items if item.feed_type in feed_types]
    
    # 排序：第一 score，第二 priority，第三 timestamp
    feed_items.sort(key=lambda x: (-x.score, -x.priority, -x.timestamp))
    
    # 限制数量
    feed_items = feed_items[:limit]
    
    # 统计信息
    stats = {
        "total_items": len(feed_items),
        "by_type": _count_by_type(feed_items),
        "by_priority": _count_by_priority(feed_items),
        "by_score_range": _count_by_score(feed_items),
        "high_priority": len([i for i in feed_items if i.score >= 10]),
        "medium_priority": len([i for i in feed_items if 7 <= i.score < 10]),
        "low_priority": len([i for i in feed_items if i.score < 7])
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
        
        total = status.get("total", 0)
        avg_importance = status.get("average_importance", 0)
        
        if total > 0:
            items.append(FeedItem(
                item_id=f"memory-stats-{int(time.time())}",
                feed_type=FEED_TYPE_MEMORY,
                priority=int(avg_importance * 4) + 3,
                title=f"记忆统计: {total} 条",
                content=f"平均重要性: {avg_importance:.2f}",
                source="Memory Intelligence",
                summary=f"记忆系统运行正常，共 {total} 条记录",
                impact="影响用户上下文理解能力",
                recommendation="定期清理低重要性记忆"
            ))
        
        recent = status.get("recent_events", [])
        for evt in recent[:3]:
            items.append(FeedItem(
                item_id=f"memory-{evt.get('id', 'unknown')}",
                feed_type=FEED_TYPE_MEMORY,
                priority=PRIORITY_MEDIUM,
                title=evt.get("title", "新记忆"),
                content=evt.get("detail", "")[:80],
                source="Memory Intelligence",
                summary=evt.get("summary", ""),
                impact="增强记忆检索能力",
                recommendation="继续观察记忆增长趋势"
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
                summary=f"知识库包含 {total_docs} 个文档",
                impact="影响知识检索和推理能力",
                recommendation="定期更新高质量文档"
            ))
        
        for topic, count in list(topics.items())[:2]:
            items.append(FeedItem(
                item_id=f"knowledge-topic-{topic}",
                feed_type=FEED_TYPE_KNOWLEDGE,
                priority=PRIORITY_LOW,
                title=f"热门主题: {topic}",
                content=f"{count} 个文档关联",
                source="Knowledge Intelligence",
                summary=f"主题 '{topic}' 活跃度较高",
                impact="反映用户关注领域",
                recommendation="可针对热门主题生成深度分析"
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
        
        priority = int(severity * 5) + 3
        items.append(FeedItem(
            item_id=f"world-risk-{int(time.time())}",
            feed_type=FEED_TYPE_WORLD,
            priority=min(10, priority),
            title=f"世界风险: {risk_level}",
            content=f"严重度: {severity:.2f}, 事件数: {total_events}",
            source="World Model",
            summary=f"检测到 {total_events} 个相关事件",
            impact="可能影响未来趋势判断",
            recommendation="继续观察相关事件发展"
        ))
        
        trending = status.get("trending_categories", [])
        for cat in trending[:1]:
            cat_name = cat.get("category", "unknown") if isinstance(cat, dict) else str(cat)
            cat_count = cat.get("count", 0) if isinstance(cat, dict) else 0
            items.append(FeedItem(
                item_id=f"world-trend-{cat_name}",
                feed_type=FEED_TYPE_WORLD,
                priority=PRIORITY_MEDIUM,
                title=f"趋势类别: {cat_name}",
                content=f"{cat_count} 个相关事件",
                source="World Model",
                summary=f"类别 '{cat_name}' 近期活跃",
                impact="反映领域动态变化",
                recommendation="关注该领域最新发展"
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
            summary=f"系统已发现 {observations_count} 个重要观察",
            impact="影响系统主动决策能力",
            recommendation="检查并处理高优先级建议"
        ))
        
        high_obs = status.get("high_importance_observations", [])
        for obs in high_obs[:2]:
            importance = obs.get("importance", 0.5)
            items.append(FeedItem(
                item_id=f"proactive-obs-{obs.get('type', 'unknown')}",
                feed_type=FEED_TYPE_PROACTIVE,
                priority=int(importance * 6) + 4,
                title=f"重要观察: {obs.get('type', 'unknown')}",
                content=obs.get("detail", "")[:80],
                source="Proactive Intelligence",
                summary=obs.get("summary", ""),
                impact="可能需要用户关注",
                recommendation=obs.get("recommendation", "继续观察")
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


def _count_by_score(feed_items: List[FeedItem]) -> Dict[str, int]:
    """按分数区间统计。"""
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for item in feed_items:
        if item.score >= 10:
            counts["critical"] += 1
        elif item.score >= 7:
            counts["high"] += 1
        elif item.score >= 4:
            counts["medium"] += 1
        else:
            counts["low"] += 1
    return counts


def get_feed_for_activity(limit: int = 10) -> List[Dict[str, Any]]:
    """获取可导入 Activity Center 的 Feed 条目。"""
    feed_data = get_feed(limit=limit)
    activities = []
    
    for item_dict in feed_data.get("feed", []):
        item = FeedItem(
            item_id=item_dict["id"],
            feed_type=item_dict["type"],
            priority=item_dict["priority"],
            title=item_dict["title"],
            content=item_dict["content"],
            source=item_dict["source"],
            timestamp=item_dict.get("timestamp", time.time()),
            summary=item_dict.get("summary", ""),
            impact=item_dict.get("impact", ""),
            recommendation=item_dict.get("recommendation", ""),
            metadata={"score": item_dict.get("score", 0)}
        )
        activities.append(item.to_activity())
    
    return activities


# 模块入口
if __name__ == "__main__":
    result = get_feed(limit=10)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
