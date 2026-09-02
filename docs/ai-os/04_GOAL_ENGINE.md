# 04 — Goal Engine（目标引擎）

> 依赖：01（分层 L2）、08（Policy 门控）
> 红线：所有目标动作经 Execution Channel + PermissionGuard；无自主执行。

---

## 1. 设计目标

将"用户意图"形式化为可追踪、可优先级化、可恢复、可学习的**目标（Goal）**生命周期。Goal 是 Proactive 与用户指令的共同入口，是 Workflow 的上游。

---

## 2. 目标状态机

```
 proposed ──▶ approved ──▶ active ──▶ executing ──▶ completed
    │            │           │            │              │
    │          rejected   paused       failed         cancelled
    │            │           │            │              │
    └────────────┴───────────┴────────────┴──────────────┘
              (任意变更 publish goal:state_changed)
```

- **proposed**：由用户指令或 Proactive（CREATE_GOAL）提出，待 Policy 门控 + 用户确认。
- **approved**：通过 Policy 与用户确认。
- **active**：已激活，等待/正在拆解。
- **executing**：Workflow DAG 执行中。
- **completed / failed / cancelled / paused / rejected**：终态或挂起。

---

## 3. 优先级与 Policy 门控

- 每个 Goal 带 `priority`（P0–P3）+ `risk_level`。
- 进入 `approved` 前须经 `PolicyEngine` 校验：敏感目标（如写文件、外发）需用户确认或显式授权。
- Proactive 提出的 Goal 默认 `priority ≤ P2` 且需用户确认才转 `approved`（薄主动层原则，见 07）。

---

## 4. Goal Tree（目标树）

- Goal 可分解子目标，形成树：`parent_goal_id` 关联。
- 父目标 `completed` 依赖所有子目标 `completed`。
- 树的展示可见于 Dashboard；崩溃恢复按树重建。

---

## 5. 队列与调度

- 活跃 Goal 进入调度队列，按 `priority` + `dependency` 排序。
- 单 Runtime 内串行/受限并发执行（受 Execution Channel 吞吐约束）。
- 队列状态持久化，进程重启可重建（见 §7）。

---

## 6. 依赖（Dependency）

- Goal 可声明前置依赖（`depends_on: [goal_id...]`）。
- 依赖未满足前不进入 `executing`。
- 循环依赖由 Goal Engine 在入队时检测并拒绝。

---

## 7. 崩溃恢复（Crash Recovery）

- Goal + 其 Workflow 状态定期快照至本地（见 09 Local First）。
- 进程重启：从最近快照恢复 `active/executing` 目标，**不重复已完成步骤**（步骤级幂等标记）。
- 恢复后发布 `goal:recovered`，Surface 提示用户"已从检查点恢复"。

---

## 8. 完成与学习（Learning Distillation）

- Goal `completed` 时触发蒸馏：
  - 成功经验 → Memory L7（Reflection）/ L5（Long-term，若涉及稳定偏好）。
  - 新知识产出 → Knowledge Engine `inbox/`（建议，用户确认入 Vault）。
  - 失败教训 → Memory L7（Reflection），供未来 Goal 规划规避。
- 蒸馏经 `memory:written` / `knowledge:suggested` 事件落盘。

---

## 9. 接口（事件）

```text
publish(goal:proposed   {goal_id, source, priority})   ← 用户/Proactive
publish(goal:approved   {goal_id})                      ← Policy+用户
publish(goal:state_changed {goal_id, state})            ← 状态机
subscribe(goal:execute   {goal_id})                     → Workflow 拆解
```

---

## 10. 红线

- 禁止 Goal 绕过 PolicyEngine 直接执行。
- 禁止 Proactive 自动将 Goal 转 `approved`（须用户确认）。
- 禁止丢目标/重复执行（崩溃恢复必须幂等）。

> 目标态设计；实现由 Goal Sprint 承接，本 Sprint 不写代码。
