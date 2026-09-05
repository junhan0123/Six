#!/usr/bin/env python3
"""Memory Intelligence Layer — 只读分析，不修改数据库。

职责：
- 读取已有 memories 表数据
- 计算重要性评分 (Importance Scoring)
- 计算衰减 (Memory Decay)
- 分类记忆 (Classification)

约束：
- 不创建第二 Memory System
- 不修改 memory.py 核心逻辑
- 不创建新数据库
- 不修改现有表结构
- 只读操作，禁止写数据库
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# 重要性评分 (Importance Scoring)
# ═══════════════════════════════════════════════════════════════════════════

# base_score 映射：event_type → 基础分
_BASE_SCORES: dict[str, float] = {
    "user_explicit": 10.0,      # 用户明确标记
    "person": 8.0,               # 人物相关
    "project": 7.0,              # 项目相关
    "decision": 6.0,             # 决策记录
    "preference": 6.0,           # 偏好
    "correction": 5.0,           # 纠错
    "feedback": 4.0,             # 反馈
    "task": 3.0,                 # 任务
    "log": 2.0,                  # 日志
    "note": 1.0,                 # 普通笔记
    "transient": 0.5,            # 临时信息
}

# 默认 base_score
_DEFAULT_BASE = 3.0


def _get_base_score(event_type: str, salience: int, source: str = "") -> float:
    """计算基础分。"""
    # 优先使用 event_type 映射
    if event_type in _BASE_SCORES:
        base = _BASE_SCORES[event_type]
    elif source and source in _BASE_SCORES:
        base = _BASE_SCORES[source]
    else:
        base = _DEFAULT_BASE

    # salience 加成 (0-10 → +0~+2)
    if salience:
        base += min(float(salience) / 5.0, 2.0)

    return base


def _get_time_factor(age_days: float) -> float:
    """时间因子：越新越重要。"""
    if age_days < 1:
        return 1.5
    elif age_days < 7:
        return 1.0
    elif age_days < 30:
        return 0.8
    else:
        return 0.5


def _get_relevance_factor(memory: dict) -> float:
    """相关性因子（基于 tags 和 entities）。"""
    tags = memory.get("tags") or []
    entities = memory.get("entities") or []
    if isinstance(tags, str):
        try:
            import json
            tags = json.loads(tags)
        except Exception:
            tags = []
    if isinstance(entities, str):
        try:
            import json
            entities = json.loads(entities)
        except Exception:
            entities = []

    # 有标签/实体 → 更高相关性
    score = 1.0
    if tags:
        score += 0.1 * min(len(tags), 5)
    if entities:
        score += 0.1 * min(len(entities), 5)
    return min(score, 1.5)


def _get_emotion_factor(memory: dict) -> float:
    """情感因子。"""
    # 简单启发：negative 相关词加权
    content = (memory.get("content") or "").lower()
    negative_words = {"错误", "失败", "问题", "bug", "异常", " crash", "error"}
    positive_words = {"成功", "完成", "优化", "改进", "提升"}

    has_negative = any(w in content for w in negative_words)
    has_positive = any(w in content for w in positive_words)

    if has_negative and not has_positive:
        return 1.3  # 负面记忆更持久
    elif has_positive:
        return 1.1
    return 1.0


def calculate_importance(memory: dict) -> dict:
    """计算单条记忆的重要性评分。

    公式：
      importance = base_score × time_factor × relevance_factor × emotion_factor

    返回：
      {
        "memory_id": ...,
        "base_score": float,
        "time_factor": float,
        "relevance_factor": float,
        "emotion_factor": float,
        "importance": float,
        "category": str  # CORE / ACTIVE / CONTEXT / TRANSIENT / ARCHIVE
      }
    """
    now = datetime.now()
    created = memory.get("timestamp")
    if created:
        try:
            dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
            age_days = (now - dt).total_seconds() / 86400
        except Exception:
            age_days = 0
    else:
        age_days = 0

    event_type = memory.get("event_type") or "note"
    salience = memory.get("salience") or 0
    source = memory.get("source") or ""

    base = _get_base_score(event_type, salience, source)
    time_f = _get_time_factor(age_days)
    rel_f = _get_relevance_factor(memory)
    emo_f = _get_emotion_factor(memory)

    importance = base * time_f * rel_f * emo_f

    # 分类
    category = classify_memory(importance, age_days, event_type, memory.get("status"))

    return {
        "memory_id": memory.get("id"),
        "mem_id": memory.get("mem_id"),
        "base_score": round(base, 2),
        "time_factor": round(time_f, 2),
        "relevance_factor": round(rel_f, 2),
        "emotion_factor": round(emo_f, 2),
        "importance": round(importance, 2),
        "age_days": round(age_days, 1),
        "category": category,
        "event_type": event_type,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 衰减计算 (Memory Decay)
# ═══════════════════════════════════════════════════════════════════════════

# decay_rate λ 映射：category → λ
_DECAY_RATES = {
    "CORE": 0.001,       # 极慢衰减
    "ACTIVE": 0.1,       # 快速衰减
    "CONTEXT": 0.05,     # 中等衰减
    "TRANSIENT": 1.0,    # 立即衰减
    "ARCHIVE": 0.0001,   # 几乎不衰减
}


def calculate_decay(memory: dict, importance: float) -> dict:
    """计算记忆衰减。

    公式：
      importance(t) = importance(0) × e^(-λt)

    返回：
      {
        "current_importance": float,
        "initial_importance": float,
        "decay_rate": float,
        "half_life_days": float,
        "status": str  # active / decaying / decayed / archived
      }
    """
    now = datetime.now()
    created = memory.get("timestamp")
    if created:
        try:
            dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
            age_days = (now - dt).total_seconds() / 86400
        except Exception:
            age_days = 0
    else:
        age_days = 0

    category = classify_memory(importance, age_days, memory.get("event_type"), memory.get("status"))
    lam = _DECAY_RATES.get(category, 0.1)

    # 指数衰减
    current = importance * math.exp(-lam * age_days)

    # 半衰期：ln(2) / λ
    half_life = math.log(2) / lam if lam > 0 else float("inf")

    # 状态判断
    if current < 0.01:
        status = "decayed"
    elif current < 0.1:
        status = "decaying"
    else:
        status = "active"

    # 特殊保护：用户手动标记或核心记忆
    if category == "CORE" or memory.get("status") == "user_explicit":
        status = "protected"
        current = importance  # 不衰减

    return {
        "current_importance": round(current, 2),
        "initial_importance": round(importance, 2),
        "decay_rate": lam,
        "half_life_days": round(half_life, 1),
        "age_days": round(age_days, 1),
        "category": category,
        "status": status,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 分类 (Classification)
# ═══════════════════════════════════════════════════════════════════════════

def classify_memory(importance: float, age_days: float, event_type: str, status: str = "") -> str:
    """分类记忆。

    分类规则：
      - CORE: 用户显式标记 或 高重要性(>8) 且 老记忆(<90天)
      - ACTIVE: 重要性(4-8) 或 新记忆(<7天)
      - CONTEXT: 重要性(2-4) 或 中期记忆(7-30天)
      - TRANSIENT: 低重要性(<2) 或 超期长记忆(>30天)
      - ARCHIVE: 已归档 或 超过180天
    """
    # 已归档优先
    if status in ("deprecated", "decayed", "consolidated", "archived"):
        return "ARCHIVE"

    # 用户显式标记
    if status == "user_explicit":
        return "CORE"

    # 高重要性 + 核心类型
    core_types = {"person", "project", "decision", "preference", "correction"}
    if event_type in core_types and importance >= 6:
        return "CORE"

    # 超高重要性
    if importance >= 8:
        return "CORE"

    # 新记忆 → ACTIVE
    if age_days < 7 and importance >= 3:
        return "ACTIVE"

    # 中高重要性
    if importance >= 4:
        return "ACTIVE"

    # 中期记忆
    if 7 <= age_days <= 30:
        return "CONTEXT"

    # 中等重要性
    if importance >= 2:
        return "CONTEXT"

    # 长期低重要性 → TRANSIENT
    if age_days > 30:
        return "TRANSIENT"

    # 低重要性
    if importance < 2:
        return "TRANSIENT"

    # 超长记忆 → ARCHIVE
    if age_days > 180:
        return "ARCHIVE"

    return "CONTEXT"


# ═══════════════════════════════════════════════════════════════════════════
# 聚合分析 (Aggregation)
# ═══════════════════════════════════════════════════════════════════════════

def analyze_memories(memories: list[dict]) -> dict:
    """批量分析所有记忆，返回统计摘要。"""
    results = []
    for m in memories:
        imp = calculate_importance(m)
        decay = calculate_decay(m, imp["importance"])
        results.append({
            **imp,
            **decay,
        })

    # 统计
    total = len(results)
    categories = {"CORE": 0, "ACTIVE": 0, "CONTEXT": 0, "TRANSIENT": 0, "ARCHIVE": 0}
    total_importance = 0.0
    decaying_count = 0

    for r in results:
        cat = r.get("category", "CONTEXT")
        categories[cat] = categories.get(cat, 0) + 1
        total_importance += r.get("current_importance", 0)
        if r.get("status") == "decaying":
            decaying_count += 1

    avg_importance = total_importance / total if total > 0 else 0

    return {
        "total": total,
        "categories": categories,
        "average_importance": round(avg_importance, 2),
        "decaying_count": decaying_count,
        "results": results,
    }


def get_statistics(memories: list[dict]) -> dict:
    """返回简化统计（用于 /api/memory/intelligence/status）。"""
    analysis = analyze_memories(memories)
    return {
        "total_memories": analysis["total"],
        "categories": analysis["categories"],
        "average_importance": analysis["average_importance"],
        "decaying_count": analysis["decaying_count"],
        "scoring_model": "importance = base × time × relevance × emotion",
        "decay_model": "exponential: I(t) = I(0) × e^(-λt)",
    }
