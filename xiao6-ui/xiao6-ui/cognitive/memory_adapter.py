#!/usr/bin/env python3
"""Xiao6 · 认知层 · Canonical Memory 适配器（P5.2 · FACADE ONLY）

唯一职责：把 Cognitive / Agent Runtime 的 legacy 记忆写入语义，**翻译**成既有
Canonical Memory API（`memory.py`）调用，使 Canonical Memory 成为认知侧
**唯一写入权威**。

目标架构（P5.2 §3）：

    Cognitive / Agent Runtime
        |
        v
    cognitive.memory_adapter        ← 本模块（极薄 FACADE）
        |
        v
    memory.py Canonical Memory API  ← 唯一写入权威
        |
        v
    memories 表 → P4 治理 / 检索 / 生命周期

铁律（P5.2 §3 / §5 / §10 / §16）：
  - 极薄：只做「参数翻译 + 稳定 source_ref 生成 + 投影副作用编排」；
  - 不拥有 检索 / 排序 / 合并 / 生命周期 / 冲突消解 / 存储 —— 全部归 P4；
  - 不自造去重：幂等完全复用 memory.py 既有 content_hash / mem_id 机制；
  - 无 SQL、不建连接、不管事务：legacy 投影持久化委托 `memory_projection`；
  - 不 import policy_engine / executor / capability_runtime（P5.2 零能力语义）。

错误语义（P5.2 §15）：Canonical 写入失败 → 显式日志 + 原样抛出。
**绝不**「canonical 失败就偷偷写 legacy 并返回成功」（那会造成 split-brain）。

回滚（P5.2 §14）：`config.FEATURE_CANONICAL_COGNITIVE_MEMORY`
  - true （默认）：Canonical 权威写入 + legacy 兼容投影；
  - false：单点回滚为「legacy 投影 only」，即 P5.2 前的等价行为。
"""

from __future__ import annotations

import hashlib
from datetime import datetime

# 命名空间（P5.2 §9 SOURCE_REF CONTRACT）
NS = "cognitive"
KIND_USER_MODEL = "user_model"
KIND_EPISODE = "episode"
KIND_CONVERSATION = "conversation"

# user_model 是单行投影（主键恒为 1），故其 canonical 记录亦为单一逻辑记录：
# mem_id 稳定 → 复用 memory.upsert_memory 的 PATCH 幂等语义，永不产生重复行。
USER_MODEL_MEM_ID = "%s:%s" % (NS, KIND_USER_MODEL)
USER_MODEL_SOURCE_REF = "%s:%s:1" % (NS, KIND_USER_MODEL)  # 1 = user_model 表既有稳定主键

MODE_CANONICAL = "canonical"
MODE_LEGACY = "legacy"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def source_ref(kind: str, key: str) -> str:
    """稳定 source_ref：`cognitive:<kind>:<stable-key>`（P5.2 §9）。"""
    return "%s:%s:%s" % (NS, kind, key)


def stable_key(*parts) -> str:
    """由逻辑内容派生的稳定键（同一逻辑写入 → 同一键；重试不产生新键）。

    P5.2 §9：禁止每次重试随机 UUID —— 那会摧毁幂等与迁移追溯。
    """
    raw = "\x1f".join((p or "") if isinstance(p, str) else str(p) for p in parts)
    return hashlib.sha1(raw.strip().encode("utf-8")).hexdigest()[:16]


def canonical_enabled() -> bool:
    """P5.2 特性开关（缺省 true；缺 config 时按默认新行为处理）。"""
    try:
        import config

        return bool(getattr(config, "FEATURE_CANONICAL_COGNITIVE_MEMORY", True))
    except Exception:
        return True


def _canonical_fail(what: str, exc: Exception):
    """P5.2 §15：显式区分 canonical 失败，绝不伪造成功、绝不静默降级。"""
    print("[memory_adapter] canonical %s 写入失败（不降级/不伪造成功）: %s" % (what, exc))
    raise exc


# ═══════════════════════════════════════════════════════════════════════════
# 1. 用户模型（cognitive/user_model.upsert_user_model 的写入出口）
# ═══════════════════════════════════════════════════════════════════════════

def record_user_model(model: dict, *, content: str = "", confidence: float | None = None,
                      bump_confidence: bool = True, updated: str | None = None) -> dict:
    """记录一次用户模型演化。

    - Canonical（权威）：`memory.upsert_memory` 按稳定 mem_id PATCH 单一逻辑记录；
    - Projection（兼容）：`memory_projection.write_user_model` 维持 O(1) 读模型
      （canonical Memory 目前无法复现「单行合并 JSON + confidence」这一查询形状，
       故投影必须保留 —— 详见 P5.2 报告 §5）。
    """
    import memory_projection

    mode = MODE_CANONICAL if canonical_enabled() else MODE_LEGACY
    sref = USER_MODEL_SOURCE_REF
    canonical_ref = None
    if mode == MODE_CANONICAL:
        import memory

        try:
            canonical_ref = memory.upsert_memory({
                "mem_id": USER_MODEL_MEM_ID,
                "content": content or "",
                "event_type": KIND_USER_MODEL,
                "title": "用户模型",
                "source_ref": sref,
                "source": "%s:%s" % (NS, KIND_USER_MODEL),
                "confidence": confidence,
                "status": "active",
            })
        except Exception as e:  # noqa: BLE001 — 显式失败语义
            _canonical_fail("user_model", e)
    conf = memory_projection.write_user_model(
        _dumps(model), bump_confidence=bump_confidence, updated=updated,
    )
    return {
        "mode": mode,
        "canonical_mem_id": canonical_ref,
        "source_ref": sref,
        "projection_confidence": conf,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 2. 情节记忆（cognitive/episodic.add_episode 的写入出口）
# ═══════════════════════════════════════════════════════════════════════════

def record_episode(*, title: str, summary: str, category: str = "fact",
                   importance: float = 0.5, project: str = "",
                   source: str = "system", event: str = "",
                   created: str | None = None) -> dict:
    """记录一条情节记忆。

    - Canonical（权威）：`memory.create_memory`，content=summary，
      幂等由既有 content_hash 唯一约束保证（同内容重复写不产生重复行）；
    - Projection（兼容）：`memory_projection.insert_episode` 维持 episodes 读模型，
      其自增 id 是 embed 向量索引 scope='episode' 的既有引用键，必须保留。
    """
    import memory_projection

    created = created or _now()
    sref = source_ref(KIND_EPISODE, stable_key(title, summary, category))
    mode = MODE_CANONICAL if canonical_enabled() else MODE_LEGACY
    canonical_id = None
    if mode == MODE_CANONICAL:
        import memory

        try:
            canonical_id = memory.create_memory(
                summary,
                event_type=KIND_EPISODE,
                title=title,
                source_ref=sref,
                source="%s:episodic" % NS,
                confidence=importance,
                status="active",
                tags={"category": category, "project": project,
                      "origin": source, "event": event},
                timestamp=created,
            )
        except Exception as e:  # noqa: BLE001 — 显式失败语义
            _canonical_fail("episode", e)
    eid = memory_projection.insert_episode(
        title=title, summary=summary, category=category, importance=importance,
        created=created, project=project, source=source, event=event,
    )
    return {
        "mode": mode,
        "canonical_id": canonical_id,
        "source_ref": sref,
        "projection_id": eid,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 3. 对话沉淀（agent_runtime._record_conversation_memory 的写入出口）
# ═══════════════════════════════════════════════════════════════════════════

def record_conversation_memory(*, date: str, topic: str, key_points,
                               sentiment: str = "neutral",
                               created: str | None = None) -> dict:
    """记录一条对话沉淀（P12-3 ConversationMemory）。

    - Canonical（权威）：`memory.create_memory`，content=key_points 拼接文本，
      sentiment/date 落 tags，幂等由 content_hash 保证；
    - Projection（兼容）：`memory_projection.insert_conversation_memory` 维持既有
      conversation_memories 读模型（含重复插入语义，与迁移前一致）。
    """
    import memory_projection

    created = created or _now()
    points = [p for p in (key_points or []) if p]
    content = "\n".join(points) if points else (topic or "")
    sref = source_ref(KIND_CONVERSATION, "%s:%s" % (date, stable_key(topic, *points)))
    mode = MODE_CANONICAL if canonical_enabled() else MODE_LEGACY
    canonical_id = None
    if mode == MODE_CANONICAL and content:
        import memory

        try:
            canonical_id = memory.create_memory(
                content,
                event_type=KIND_CONVERSATION,
                title=topic or "",
                source_ref=sref,
                source="%s:%s" % (NS, KIND_CONVERSATION),
                tags={"sentiment": sentiment, "date": date,
                      "kind": "conversation_memory"},
                timestamp=created,
            )
        except Exception as e:  # noqa: BLE001 — 显式失败语义
            _canonical_fail("conversation_memory", e)
    rid = memory_projection.insert_conversation_memory(
        date=date, topic=topic, key_points=points,
        sentiment=sentiment, created=created,
    )
    return {
        "mode": mode,
        "canonical_id": canonical_id,
        "source_ref": sref,
        "projection_id": rid,
    }


def _dumps(obj) -> str:
    """JSON 序列化（投影列所需的纯格式转换；非持久化逻辑）。"""
    import json

    return json.dumps(obj, ensure_ascii=False)
