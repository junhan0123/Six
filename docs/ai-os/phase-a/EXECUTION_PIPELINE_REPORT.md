# 小6 AI OS 2.0 — Phase A 任务四：Execution Pipeline（EXECUTION_PIPELINE_REPORT）

> Sprint: AI OS Phase A — Core Intelligence Sprint v1.0
> 任务: 任务四（Execution Pipeline）→ 输出本报告
> 上游: `CORE_AUDIT.md`（F4：与 L4 编排机划界）、任务三（Context Pipeline）
> 日期: 2026-08-05
> 状态: ✅ 设计完成；本任务 STOP，待逐任务 Review

---

## 1. 目的与范围

**目标**：定义 **L5 AI Brain 的执行内环**——单次"理解→推理→调用→反思→回应"的标准链路，使 Brain 的能力可被 Agent(L4)/Proactive(L1)/对话主链路一致复用。

**关键边界（F4）**：
- **L4 外环**（已存在，`agent_runtime.py`）：`submit_goal → plan_goal → 逐 Task 执行 → reflect`，跨多任务、跑后台线程、带队列与重试——是**编排级**循环。
- **L5 内环**（本设计）：单请求/单步内的 `Input→Reasoning→Tool→Reflection→Response`，是**推理执行级**循环。
- 二者**正交**：L4 外环在拆解出的每个 Task 上，可调用 L5 内环完成"该步该怎么想/怎么调工具/怎么反思"。L5 不持有目标队列、不替代 L4。

**不在范围**：Goal/Workflow 拆解（L2/L3，已存在/Phase C）；Agent 角色切换（L4 Supervisor/Specialist，Phase C）。

---

## 2. 内环相位图

```
 ┌──────────────────────────────────────────────────────────────┐
 │  INPUT      解析 user_text；经任务三 ContextBuilder 组装上下文   │
 │             → BuildContext(user_text, tier) → ContextBundle    │
 └───────────────────────────┬──────────────────────────────────┘
                             ▼
 ┌──────────────────────────────────────────────────────────────┐
 │  REASONING  llm.agnes_completion(system+context+user)          │
 │             产出：自然语言回应 或 结构化动作意图(tool/args/plan)  │
 └──────────┬─────────────────────────────────────┬─────────────┘
            │ 含动作意图                            │ 纯文本回应
            ▼                                      ▼
 ┌──────────────────────────┐              ┌────────────────────┐
 │  TOOL     经单一执行通道： │              │  RESPONSE（透传）   │
 │  policy_engine.evaluate  │              └─────────┬──────────┘
 │  → confirm? request_approval                ┌──────┴───────┐
 │  → tools.execute_tool / guard.run          │             │
 │  （电脑能力闭环，F4/L8）     │              │             ▼
 └──────────┬────────────────┘              │      ┌────────────────────┐
            ▼                               │      │ REFLECTION（见下）  │
 ┌──────────────────────────┐              │      └─────────┬──────────┘
 │  REFLECTION 复用 reflector.reflect       │                ▼
 │  沉淀经验/记忆（best-effort）            │         ┌────────────────────┐
 └──────────┬────────────────┘              │         │  RESPONSE 回写用户  │
            └───────────────┬───────────────┘         │  (SSE / stream)     │
                            ▼                          └────────────────────┘
                   ┌────────────────────┐
                   │  RESPONSE 统一出口  │
                   └────────────────────┘
```

---

## 3. 相位职责

| 相位 | 输入 | 输出 | 复用既有 |
|------|------|------|---------|
| INPUT | `user_text`, `tier` | `ContextBundle` | 任务三 `ContextBuilder` |
| REASONING | `ContextBundle` + 用户消息 | 文本 或 结构化动作意图 | `llm.agnes_completion`（llm.py） |
| TOOL | 动作意图 `{tool, args}` | 执行结果 | `policy_engine.evaluate` / `request_approval`、`tools.execute_tool`、`permission_guard.guard.run`（电脑能力闭环） |
| REFLECTION | 执行轨迹 | 经验/记忆沉淀 | `reflector.reflect`（reflector.py）、`memory_distiller` |
| RESPONSE | 文本/结果 | SSE 流 | 既有对话响应通道 |

---

## 4. 与 L4 外环的协作契约

- **对话主链路（非目标）**：直接跑 L5 内环（无 L4 介入），一次请求一内环。
- **目标驱动（L4 介入）**：`AgentRuntime._execute_task`（agent_runtime.py:202）在每步调用 L5 内环完成"该 Task 的推理+工具+反思"，外环负责队列/重试/进度。L5 内环**不感知**自己在被 L4 调用。
- **禁止**：L5 内环内部再起目标队列、再调 `submit_goal` 自循环（避免与 L4 职责重叠，违反 No God Module / 单一编排）。L5 若需"建目标"，经 Proactive 薄层（L1）提议，由 L4 认领（架构 01 §5.1）。

---

## 5. 事件发射纪律

- 内环各相位经**既有事件名**广播，不新造：
  - 推理中 → `AGENT_THINKING`（agent_runtime.py:126 既有）
  - 工具调用 → `TOOL_CALLED` / `TOOL_DONE`（DOMAIN_EVENT_NAMES:183）
  - 等待确认 → `AGENT_WAITING`（agent_runtime.py:226）
  - 反思 → `REFLECTING`（DOMAIN_EVENT_NAMES:185）
- 新增相位事件须先按 F1 处置契约漂移；优先复用既有名。

---

## 6. 错误处理

- LLM 调用失败：退避重试（参考 `agent_runtime._execute_task` 的 `_classify_error`/退避，agent_runtime.py:322-249），网络类短退避、权限/工具类不重试。
- 工具执行失败：返回结构化 `{ok:False, category, error}`，由调用方（L4 或对话链路）决定重试/降级。
- 内环异常**不崩溃进程**：顶层 try/except 兜底，发 `ERROR_OCCURRED`（DOMAIN_EVENT_NAMES:185）并降级为安全回应。

---

## 7. 红线合规

| 红线 | 合规性 | 说明 |
|------|--------|------|
| 单 Runtime | ✅ | 内环为同进程函数流，无新 Runtime |
| 单执行通道(P11) | ✅ | TOOL 相位 100% 经 `policy_engine`/`guard`，无私建路径 |
| 单 Permission | ✅ | 复用 `policy_engine` + `permission_guard`，无第二权限 |
| 单 EventBus | ✅ | 复用 `publish_domain` 既有名 |
| No God Module | ✅ | 内环只编排推理/工具/反思，不含持久化/路由 |
| 增量演进 | ✅ | 复用 reflector/tools/guard/llm，无重写 |

---

## 8. 实现清单

1. 新增 `ai_core/execution.py`：`run_inner_loop(user_text, tier) -> response`，实现五相位。
2. 对话主链路调用点改为经 `execution.run_inner_loop`（非目标路径）。
3. `agent_runtime._execute_task` 内每步委托 `execution.run_inner_loop`（保留 L4 队列/重试外壳）。
4. REFLECTION 相位复用 `reflector.reflect`，不新建反思逻辑。
5. 单测：纯文本回应路径、带工具路径（mock tools）、confirm 阻塞路径、异常兜底。

**本任务为设计交付；代码落地待 Phase A 实现阶段（经 Review 批准）。**

**STOP**：任务四设计完成。待 Review 批准后进入任务五（Capability Registry）。未经批不得修改代码、不得扩大范围。
