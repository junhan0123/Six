# 05 — Workflow Engine（工作流引擎）

> 依赖：01（分层 L3）、04（Goal 上游）、06（Agent 执行步骤）、P11（单一执行通道）
> 红线：所有步骤动作经 Execution Channel + PermissionGuard；无步骤级硬编码执行。

---

## 1. 设计目标

Workflow 是 Goal 的**执行蓝图**：将"已批准的目标"拆解为可编排、可检查点、可人机协同、可崩溃恢复的步骤集合。Workflow Engine 负责步骤 DAG 的编排、调度、检查点与重试，但**不负责"做决策"**（Goal 负责）也**不负责"具体执行"**（Agent/Executor 负责）。

---

## 2. Workflow = DAG-of-steps

一个 Workflow 对应一个 `active/executing` 的 Goal，由若干 Step 组成，Step 间构成有向无环图（DAG）。

```
Goal(approved)
   └─ Workflow
        ├─ Step A（depends_on: []）
        ├─ Step B（depends_on: [A]）
        ├─ Step C（depends_on: [A]）   ← B、C 可并行
        └─ Step D（depends_on: [B, C]）
```

### 2.1 Step 数据模型

| 字段 | 说明 |
|------|------|
| `step_id` | 全局唯一 |
| `goal_id` | 所属 Goal |
| `type` | `llm` / `tool` / `agent` / `human` / `condition` / `parallel` |
| `depends_on` | 前置步骤 id 列表（空=可立即执行） |
| `status` | 见 §3 状态机 |
| `checkpoint` | 执行前/后的状态快照指针（本地） |
| `retry` | 重试策略（max / backoff） |
| `idempotency_key` | 幂等标记（崩溃恢复用） |
| `assigned_to` | 执行者（Agent Specialist / Human / Tool） |

---

## 3. Step 状态机

```
 pending ──▶ ready ──▶ running ──▶ done
    │          │          │          │
    │          │       failed     skipped(条件不满足)
    │          │          │
    │          └───── retry ──▶ running（受 retry 策略约束）
    │                        │
    └────────────────── blocked(依赖未完成)
                (任意变更 publish workflow:step_changed)
```

- **pending**：已定义，依赖未满足。
- **ready**：依赖满足，等待调度。
- **running**：执行中（经 Execution Channel）。
- **done**：成功且幂等标记置位。
- **failed / blocked / skipped**：异常或终态分支。

---

## 4. Human-in-the-Loop（HITL）

- `type: human` 步骤显式暂停 Workflow，经 Surface 请求用户操作/确认。
- 敏感步骤（写文件、外发、删除）由 Goal 的 `risk_level` 决定是否需要 HITL（见 04 §3 + 08 Policy）。
- HITL 期间 Workflow 进入 `paused`，不占用执行通道；用户响应后恢复。
- HITL 结果作为事件 `workflow:human_input {step_id, payload}` 回灌，继续 DAG。

---

## 5. 检查点与崩溃恢复（P15）

- Workflow 每进入/完成一个 Step，将其 DAG 状态 + `idempotency_key` 快照至本地（见 09 Local First）。
- 进程崩溃重启：
  1. 从最近快照重建 Goal/Workflow DAG。
  2. 已完成步骤（`done` + 幂等标记）**跳过不重复**（P15 不重复执行）。
  3. `running` 中步骤按 `idempotency_key` 查询执行器状态；若外部副作用已发生则标记 `done`，否则重启。
- 恢复后发布 `workflow:recovered`，Surface 提示"已恢复至检查点 X"。

> 重试（§3 `retry`）与恢复（本节）都必须保证**外部副作用幂等**：同一 `idempotency_key` 重复触发不得产生双重写入/双重发送。

---

## 6. 自动化 vs 手动

- Workflow 可声明 `mode: automated`（无人值守，满足条件即执行）或 `mode: supervised`（每步/关键步需确认）。
- Proactive 提出的 Goal 默认 `supervised`，且首步不得为自动化敏感动作（薄主动层，见 07）。
- 自动化 Workflow 的敏感步骤仍受 PolicyEngine 门控（见 04 §3），高风险动作强制 HITL。

---

## 7. 单一执行通道（P11）

- Workflow Engine **不直接调用** Executor / Agent / Tool。
- 每个 `ready` 步骤经 `subscribe(goal:execute)` / 内部调度 → 进入 Execution Channel。
- Execution Channel：`step → PermissionGuard → PolicyEngine → Executor`（或 Agent Supervisor 认领）。
- 结果以事件扇出：`workflow:step_done` / `memory:written` / `knowledge:suggested`。

```
[Workflow 调度] → Execution Channel → PermissionGuard → Executor / Agent
                                            │
                              ┌─────────────┴─────────────┐
                         [Tool/系统动作]            [Agent Specialist 执行]
                                            │
                              └── 事件扇出 → Memory/Knowledge/Surface ──┘
```

---

## 8. 与 Agent Engine 的边界

- Workflow 决定"做什么、按什么顺序"（DAG + 依赖）。
- Agent 决定"怎么做"（Supervisor 拆解 Step 为动作、调用 Specialist 角色）。
- 一个 Step 可由一个 Agent Supervisor 认领，Supervisor 在 Step 内做角色切换（见 06，P14）。
- Workflow 不感知 Specialist 内部；只接收 Step `done/failed`。

---

## 9. 接口（事件）

```text
publish(workflow:created     {goal_id, dag})        ← Goal approved 后
publish(workflow:step_changed {step_id, status})    ← 状态机
publish(workflow:human_input  {step_id, payload})   ← HITL 回灌
publish(workflow:recovered    {goal_id, checkpoint})← 崩溃恢复
subscribe(workflow:execute    {step_id})            → Execution Channel
```

---

## 10. 红线

- 禁止 Workflow 私建执行路径（必须经 Execution Channel）。
- 禁止 Step 无 `idempotency_key`（不可恢复）。
- 禁止自动化 Workflow 绕开 PolicyEngine 执行敏感步骤。
- 禁止 DAG 成环（入队前检测，拒绝循环依赖）。

> 目标态设计；实现由 Workflow Sprint 承接，本 Sprint 不写代码。
