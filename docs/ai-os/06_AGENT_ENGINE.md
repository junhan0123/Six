# 06 — Agent Engine（智能体引擎）

> 依赖：01（分层 L4）、05（Workflow 步骤执行）、P14（角色而非进程）
> 红线：Agent 是同一 Runtime 内的角色切换；禁止第二 Runtime / 子进程 Agent。

---

## 1. 设计目标

Agent Engine 是 Goal/Workflow 的**执行引擎**：将 Workflow 的一个 Step 落地为具体动作序列。它采用 **Supervisor（单一编排器）+ Specialist（角色）** 模型——所有角色运行在**同一个 Runtime 进程内**，通过角色切换而非进程隔离来承载不同能力。

---

## 2. Supervisor + Specialist 模型（P14）

```
                    ┌──────────────────────────┐
                    │   Agent Supervisor        │
                    │  (编排 / 拆解 / 分派 / 监控) │
                    └──────────┬───────────────┘
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐     ┌──────────┐
        │ Research │    │  Coding  │     │  Review  │   ← Specialist 角色
        ├──────────┤    ├──────────┤     ├──────────┤
        │Knowledge │    │ Memory   │     │ Planning │
        └──────────┘    └──────────┘     └──────────┘
              全部在同一 Runtime 内，按需切换角色上下文
```

- **Supervisor**：接收 Step → 规划动作序列 → 调用合适 Specialist → 汇总结果 → 返回 Step `done/failed`。
- **Specialist**：具备特定能力的**角色上下文**（系统提示 + 工具集 + 记忆视图），不是独立进程。
- **P14 角色而非进程**：切换 Specialist = 切换上下文配置，不是 spawn 子进程 / 微服务。

---

## 3. Specialist 角色清单

| 角色 | 职责 | 主要工具/接口 |
|------|------|--------------|
| Research | 检索、调研、信息聚合 | Knowledge Engine / Web(可选) / Memory |
| Coding | 代码生成与修改（本地项目） | File/Shell(受 Policy 门控) |
| Review | 自审、差异检查、质量门 | Diff / Test / Memory L7 |
| Knowledge | 知识整理、链接、蒸馏 | Obsidian Vault / Sync Bridge |
| Memory | 记忆读写与蒸馏 | Memory Engine（L1–L10） |
| Planning | 目标/步骤再规划、反思 | Brain 上下文管道 / Goal |

> 角色可扩展；新增角色 = 注册一份上下文配置，不新增 Runtime。

---

## 4. 上下文与角色交接

- 所有 Specialist 共享**同一份运行上下文**（Goal、Workflow DAG、Memory 视图、Knowledge 视图）。
- 角色切换时传递**结构化 handoff**（已完成动作、中间产物、待决问题），而非重新加载全部历史。
- 上下文窗口由 Brain 上下文管道（见 05/L5）按需裁剪，避免无限增长。

---

## 5. 单一执行通道（P11）

- Agent 执行的每个动作（文件写、命令、外发）都必须经 Execution Channel。
- 流程：`Specialist 动作 → Execution Channel → PermissionGuard → PolicyEngine → Executor`。
- Agent **不能**直接调用 Executor；所有副作用都走统一出口（见 01 §5.2、05 §7）。
- 违反 Policy 的动作在 `PermissionGuard` 被拒，Agent 收到 `denied` 并重新规划。

---

## 6. 与 Brain 的关系（L5）

- Agent 调用 Brain 获得推理/规划/反思能力（LLM）。
- Brain 是**只读上下文聚合器**：从 Memory/Knowledge/State 拉取，组装提示词喂 LLM，不持有状态（见 01 §5.2）。
- Agent 不直接持有 LLM 会话；通过 Brain 接口请求推理。

---

## 7. 反思与自纠错（Reflection）

- 每个 Step 完成后，Supervisor 可触发 `Review` Specialist 做自审。
- 失败步骤：Supervisor 读 Memory L7（反思/教训）调整策略后重试（受 §3 retry 约束）。
- 反思产物写入 Memory L7，供未来 Goal/Workflow 规避同类失败（见 04 §8）。

---

## 8. 接口（事件）

```text
publish(agent:step_claimed  {step_id, supervisor})  ← 认领 Step
publish(agent:role_switched {step_id, role})        ← 角色切换
publish(agent:action        {step_id, action})      → Execution Channel
publish(agent:step_result   {step_id, result})      ← 返回 Step 结果
subscribe(goal:execute / workflow:execute)          → 接收待执行 Step
```

---

## 9. 红线

- 禁止引入第二 Runtime / 子进程 Agent（P14）。
- 禁止 Agent 直接调用 Executor（必经 Execution Channel）。
- 禁止 Specialist 跨进程共享状态（同 Runtime 内上下文是唯一真相）。
- 禁止 Agent 绕过 PolicyEngine 执行敏感动作。

> 目标态设计；实现由 Agent Sprint 承接，本 Sprint 不写代码。
