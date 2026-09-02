---
id: decision-memory-single-source
type: decision
title: DECISION_003 — 记忆单一来源
status: consolidated
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- decision
- governance
provenance: docs/decisions
---

# DECISION_003 — Memory 单一来源

## 背景
系统需要短期上下文、工作记忆、长期记忆、项目记忆、知识记忆等多层记忆。早期曾出现多处各自缓存「记忆」导致不一致。

## 问题
- 多个记忆实现并存 → 数据分叉、难以对齐。
- Knowledge / RAG 若自成记忆系统，会与主记忆割裂。

## 候选方案
1. **A. 各能力域自管记忆**（分叉风险）。
2. **B. 单一 Memory 系统 + 分层视图**（采用）。

## 最终选择
**B**：`memory.py` 为**唯一**记忆系统（profile / memory_summary / learnings / reminders 等）。知识层（Knowledge Workspace）仅定义**接口**，复用同一记忆底座，不新建第二 Memory 系统。

## 原因
- 单一来源保证记忆一致性，避免「小6记得 A 却用 B」。
- 分层（短期/工作/长期/项目/知识）通过同一系统的不同访问视图实现，而非多系统。
- 兼容现有 Memory System，降低迁移成本。

## 影响范围
- 所有持久化记忆经 `memory.py`。
- Knowledge Workspace（Phase 9）只建接口，索引指向同一记忆底座。
- 禁止新增 `memory2.py` 或平行记忆存储。

## 未来限制
- 禁止引入第二 Memory 系统（含第二 RAG 存储）。
- 禁止在感知/上下文层缓存可写记忆副本。
