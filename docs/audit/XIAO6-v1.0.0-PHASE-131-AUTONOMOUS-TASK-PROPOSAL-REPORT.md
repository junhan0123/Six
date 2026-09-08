# Xiao6 v1.0.0 — PHASE 131 Autonomous Task Proposal Layer Report

**日期**: 2026-09-04
**版本**: v1.0.0
**状态**: 已完成

---

## 1. 架构设计

### 1.1 完整数据流

```
Observation → Suggestion → Proposal → User Approval → Create Task
     ↓            ↓           ↓            ↓              ↓
  Health      Rules       Rules        Human          Task
 Analysis     Engine      Engine        In Loop        Created
```

### 1.2 分层结构

| 层 | 模块 | 职责 |
|---|------|------|
| Observation | `observation_service.py` | 监听 EventBus，分析任务健康度 |
| Suggestion | `suggestion_service.py` | 根据 Observation 生成建议 |
| Proposal | `proposal_service.py` | 根据 Suggestion 生成可执行方案 |

---

## 2. 新增/修改文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `proposal_service.py` | 新增 | Proposal 层核心（486行） |
| `db.py` | 修改 | 添加 `task_proposals` 表和迁移函数 |
| `server.py` | 修改 | 添加 `/api/proposals/*` 端点 |

---

## 3. Data Model

### 3.1 TaskProposal

```python
@dataclass
class TaskProposal:
    id: str                          # 提案 ID
    suggestion_id: str               # 关联 Suggestion
    type: str                        # TASK_RESTORE / FAILURE_ANALYSIS / GOAL_REROUTE
    title: str                       # 提案标题
    description: str                 # 描述
    steps: List[Dict]                # 执行步骤 [{title, action}]
    estimated_cost: float            # 预估 tokens
    risk: str                        # low / medium / high
    status: str                      # pending / approved / rejected / created
    created_at: float
```

### 3.2 SQLite Schema

```sql
CREATE TABLE task_proposals (
    id TEXT PRIMARY KEY,
    suggestion_id TEXT UNIQUE,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    steps TEXT,
    estimated_cost INTEGER DEFAULT 5,
    risk TEXT DEFAULT 'low',
    status TEXT DEFAULT 'pending',
    created TEXT,
    approved_at TEXT,
    rejected_at TEXT,
    task_id INTEGER
);
```

---

## 4. Proposal Generator Rules

| 规则 | Suggestion Type | Proposal Type | Steps | Risk |
|------|-----------------|---------------|-------|------|
| 1 | TASK_STALE | TASK_RESTORE | 4步检查恢复方案 | medium |
| 2 | TASK_FAILED | FAILURE_ANALYSIS | 4步错误分析 | high |
| 3 | GOAL_STUCK | GOAL_REROUTE | 4步重新规划 | medium |

**规则特点**：
- 每个步骤包含 `title` 和 `action`
- 禁止生成虚假执行结果
- 风险级别基于建议类型

---

## 5. API Endpoints

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/proposals` | 获取待审批提案列表 |
| POST | `/api/proposals/{id}/approve` | 用户批准提案 |
| POST | `/api/proposals/{id}/reject` | 用户拒绝提案 |

**Approve 流程**：
```python
1. 验证提案存在且状态为 pending
2. 更新状态为 approved + approved_at
3. 返回成功
（不自动创建 Task，仅标记状态）
```

---

## 6. 测试结果

```
=== PHASE 131 Proposal Layer Tests ===

Test 1: STALE Suggestion generates proposal
  PASS: type=TASK_RESTORE, steps=4

Test 2: FAILED Suggestion generates proposal
  PASS: type=FAILURE_ANALYSIS, risk=high

Test 3: Unknown suggestion generates no proposal
  PASS: no proposal generated

Test 4: Database persistence
  PASS: pending count=2

Test 5: Service integration
  PASS: stats={'generated': 0, 'approved': 0, 'rejected': 0, 'errors': 0}

=== All Tests Complete ===
```

**测试覆盖**: 5/5 PASS

---

## 7. 约束满足

| 约束 | 状态 |
|------|------|
| 不修改 ai_core.execution.run | ✓ |
| 不修改 planner | ✓ |
| 不修改 policy_engine | ✓ |
| 不修改 tool executor | ✓ |
| 不自动执行任务 | ✓ |
| Human in the Loop | ✓ |
| 版本 v1.0.0 | ✓ |

---

## 8. 与 PHASE 129/130 的集成

```
PHASE 129: ObservationService
    ↓ publishes TASK_COMPLETED/TASK_FAILED
PHASE 130: SuggestionService
    ↓ listens to observations
PHASE 131: ProposalService
    ↓ listens to suggestions
User: Approves/Rejects via UI
    ↓
Status Update (no auto-execution)
```

---

## 9. Git Diff Summary

```
xiao6-ui/db.py            | +35 lines
xiao6-ui/server.py        | +31 lines (proposals API)
xiao6-ui/proposal_service.py | +486 lines (new)
```

---

## 10. 下一步

PHASE 131 已完成稳定化收口。

**等待下一阶段指令**。

---

*报告生成时间: 2026-09-04T06:30:00+08:00*