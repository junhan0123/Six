# Xiao6 Future Task Queue

> **Governance Document** — Maintenance Governance Task (Long Running Task Queue Governance)
> **Execution Mode**: Documentation Governance Only (Audit → Queue → Freeze → Wait)
> **Created**: 2026-08-04
> **Authority**: This queue is the single source of truth for *future* Xiao6 intelligence work. It records direction, priority order, and entry conditions only. It executes **no development**.
> **Red Line Compliance**: Must not violate `XIAO6_GOLDEN_STATE_v1.0.md` or `DECISION_001`–`DECISION_006`. No second Runtime / Memory / EventBus / Permission. PolicyEngine is the only authority. AppState is the only write entry.

---

## Active Task

### v1.4 Cognitive Boundary Governance

| Field | Value |
|-------|-------|
| **Status** | RUNNING |
| **Priority** | P0 |
| **Execution Mode** | Documentation Governance Only |
| **Goal** | 建立 Memory / Knowledge / World Model / Context Boundary |
| **Deliverables** | 13 documents (Phase 1–13): cognitive boundary specs, authority matrix, lifecycle, AI maintenance protocol, knowledge-graph extension, audits |
| **Audit Result** | `PROJECT_DOCUMENT_AUDIT.py` → PROBLEMS = 0 |

**Completion Conditions (all required):**

- [x] 文档完成（13 份交付文档已写入 `docs/design/` + `docs/audits/`）
- [x] 审计通过（`PROJECT_DOCUMENT_AUDIT.py` PROBLEMS = 0）
- [x] Golden State 无变化（未触碰 GOLDEN_STATE / DECISION / 架构红线）
- [x] PROJECT_DOCUMENT_AUDIT PASS

> **Gate Rule**: 任何 Queued Task 在 v1.4 完成条件全部满足前 **禁止进入执行阶段**。

---

## Queued Tasks

Tasks are ordered strictly by dependency. Lower priority number = higher urgency.

### Priority 1 — v1.4.1 Knowledge Contract Freeze

| Field | Value |
|-------|-------|
| **Trigger** | v1.4 完成后 |
| **Goal** | 冻结 Knowledge Unit / Metadata / Authority / Lifecycle 契约 |
| **Forbidden** | 新增知识系统能力（no new knowledge-system capabilities） |

> Scope: Convert the v1.3 / v1.3.1 Knowledge Unit contract (12 Metadata + Payload), Authority L100–L30, and Lifecycle into a *frozen* immutable baseline. Governance-only; no functional change.

---

### Priority 2 — v1.5 Context Intelligence Layer

| Field | Value |
|-------|-------|
| **Trigger** | 认知边界稳定（v1.4 + v1.4.1 完成） |
| **Goal** | 设计 Context Assembly / Context Priority / Context Compression |
| **Forbidden** | 修改 Context Engine 实现（no modification of Context Engine implementation） |

> Scope: Design-only specification of how assembled context is prioritized and compressed. Must build on the v1.4 `CONTEXT_ASSEMBLY_GOVERNANCE.md` boundary, not re-implement the engine.

---

### Priority 3 — v1.6 Agent Reliability Governance

| Field | Value |
|-------|-------|
| **Trigger** | Context Layer 完成（v1.5 完成） |
| **Goal** | 增强 Execution Guard / Reflection / Checkpoint / Failure Recovery |
| **Forbidden** | 改变 Agent Runtime 架构（no change to Agent Runtime architecture） |

> Scope: Reliability governance *around* the existing `agent_runtime.py`. Design guardrails, reflection checkpoints, and failure-recovery protocols without altering the runtime architecture.

---

### Priority 4 — v1.7 Autonomous Maintenance System

| Field | Value |
|-------|-------|
| **Trigger** | Agent Reliability 稳定（v1.6 完成） |
| **Goal** | 设计 自动审计 / 自动报告 / 知识维护 / 项目健康检查 |
| **Forbidden** | 引入自主执行能力（no autonomous execution beyond governance scope） |

> Scope: Design an autonomous *maintenance/audit* subsystem (wraps `PROJECT_DOCUMENT_AUDIT.py` + knowledge upkeep). Must not become a second Runtime or alter Golden State.

---

### Priority 5 — Future Intelligence Layer

| Field | Value |
|-------|-------|
| **Status** | **IDEA ONLY** |
| **Contains** | RAG / Graph Retrieval / Embedding / Multi Agent / Self Improvement |
| **Current State** | **禁止进入设计**（must not enter design phase） |

> Hard Block: These capabilities are explicitly deferred. They may not be designed, prototyped, or scheduled until all prior dependencies (v1.3 → v1.7) are satisfied **and** a `DECISION_*` approval is granted. This block is consistent with `DECISION_006_LANGCHAIN_POSITION.md` (no premature RAG / embedding / framework introduction).

---

## 任务依赖检查 (Dependency Graph)

```
v1.3 Knowledge Foundation
        ↓
v1.4 Cognitive Boundary          [ACTIVE / RUNNING]
        ↓
v1.4.1 Knowledge Contract Freeze [P1]
        ↓
v1.5 Context Intelligence        [P2]
        ↓
v1.6 Agent Reliability           [P3]
        ↓
v1.7 Autonomous Maintenance      [P4]
        ↓
Future Intelligence Layer        [P5 · IDEA ONLY · BLOCKED]
```

**Rule**: 任何后续任务 **不得绕过依赖**。 A task may not start before every task above it in the graph is COMPLETE.

---

## 执行规则 (Execution Discipline)

When a new task request arrives in the future, the system MUST check, in order:

1. **是否存在 Active Task？** — If an Active Task exists and is not complete, new execution is rejected (queued or refused).
2. **是否满足依赖？** — Verify the dependency graph above; reject if predecessors are incomplete.
3. **是否违反 Golden State？** — Reject if it would create a second Runtime / Memory / EventBus / Permission, alter PolicyEngine authority, or bypass AppState write entry.
4. **是否需要 Decision Approval？** — If it touches architecture, introduces new capability categories (e.g. RAG / embedding), or changes frozen contracts, require a new `DECISION_*` approval first.

**If any check fails → 拒绝进入执行阶段 (reject entering execution).** The request is recorded, not executed.

---

## 禁止事项 (Prohibited Actions)

This governance task and all queued tasks are bound by the following hard prohibitions:

- ❌ 修改当前 v1.4 任务（do not modify the active v1.4 task）
- ❌ 插入新功能（do not insert new features）
- ❌ 提前设计 RAG（do not design RAG prematurely）
- ❌ 提前设计 Agent 自我进化（do not design agent self-evolution prematurely）
- ❌ 修改 Phase 状态（do not modify Phase status）
- ❌ 修改架构（do not modify architecture）
- ❌ 创建重复规范（do not create duplicate specifications）

---

## 冻结声明 (Freeze Statement)

This document (`FUTURE_TASK_QUEUE.md`) is **frozen** as the authoritative future-task registry upon creation.

- It may only be modified through the same governance process (Audit → Queue → Freeze → Wait) with explicit user instruction.
- Queue reordering, priority changes, or new task insertion require re-running this governance task — not ad-hoc edits.
- Until v1.4 completion is confirmed, **no Queued Task may be promoted to Active**.

---

*End of Xiao6 Future Task Queue — Maintenance Governance Task. Stop and wait for next instruction.*
