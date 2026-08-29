# CURRENT_EXECUTION_ARCHITECTURE.md

> **Xiao6 AI OS — Execution Platform Sprint v1.0**
> **阶段：Audit（代码级审计，硬性闸门）**
> **审计方法：直接读源码 + 行号取证，不信文档**
> **审计范围（Sprint 强制）：** server.py / agent/ / planner/ / workflow/ / tasks.py / tools.py / context/ / goal/ / runtime / memory / knowledge / EventBus / Permission / Execution / Dispatcher 各自在哪里、如何协作
> **状态：✅ 审计完成 — 本文件是所有 Stage A–J 改码前的唯一事实基线。未经人工确认，禁止任何代码改动。**

---

## 0. 审计结论速览（TL;DR）

| 维度 | 现状 | 问题等级 |
|---|---|---|
| 执行入口 | 两条**并行**主链路：chat（`run_fc_loop`）与 goal（`agent_runtime`） | 🔴 双入口、语义分裂 |
| Tool 执行 | `execute_tool()` 单函数，但**无内部权限闸门** | 🔴 权限由调用方各自负责 |
| 权限策略 | `policy_engine`/`PermissionGuard` 仅在 goal/电脑能力路径调用 | 🔴 chat/reflector/social_inbound **裸调** `execute_tool` |
| 事件来源 | **三套**通道：EventBus / `proactive.SUBSCRIBERS` / chat `emit` 直推 SSE | 🔴 发散、有绕过 |
| 状态来源 | **四套**追踪：tasks 表 / goals 表 / agent_runtime 内存 / scheduler.TaskStatus | 🔴 无单一状态源 |
| 取消机制 | 基本缺失；仅 `computer_executor` 有真 cancel token | 🔴 chat 路径不可取消 |
| 恢复机制 | 仅 `tasks.recover_tasks()`（running→open）；无 checkpoint/resume | 🟠 弱 |
| timeout | `execute_tool` **无** timeout；仅 LLM 调用 timeout=90 | 🟠 工具可挂死 |
| retry | 仅 goal 路径（`_MAX_RETRIES=3`）；chat 路径无重试 | 🟠 不对称 |
| agent/planner/workflow/Dispatcher | **均不存在为模块**——内联在 `goals.plan_goal` + `agent_runtime._llm_dispatch` | 🟡 概念漂移 |
| 统一 Execution 内核 | **不存在**——`execute_tool` 是事实上的、但非收口的执行点 | 🔴 本次 Sprint 核心要建 |
| 红线合规（现有） | 单 EventBus 实例、单 PolicyEngine、单 PermissionGuard 单例 — 已守住 | 🟢 |

**一句话总判定：** 当前执行层是「两条并行链路 + 一个无闸门的工具函数 + 三套事件通道 + 四套状态源」的拼装体，不是统一内核。本次 Sprint 的目标不是加功能，而是**把这四套发散收口为单一 Execution Platform**（Single Runtime / State Writer / EventBus / Permission / Execution Path / Tool Entry / Context / Queue / Recovery / Metrics / Reflection）。

---

## 1. 模块定位确认（Sprint 强制清单逐条核验）

> 所有路径相对 `G:/xiao6/xiao6-ui/`。

| Sprint 要求确认 | 实际位置 | 是否存在为模块 | 说明 |
|---|---|---|---|
| `server.py` | `server.py` | ✅ 文件 | HTTP 入口（`BaseHTTPRequestHandler`+`ThreadingHTTPServer`，**线程模型、非 asyncio**） |
| `agent/` | `agent_runtime.py` | ❌ 非独立包 | "Agent" 概念 = `agent_runtime.py` 单文件；`agent_delegate.py` 是第二 Agent 子进程 |
| `planner/` | `goals.plan_goal`（`goals.py:380`） | ❌ 非独立包 | "Planner" = `goals.plan_goal`（LLM 拆解，`:412`）；无独立 planner 模块 |
| `workflow/` | 内联 | ❌ 不存在 | 无 workflow 模块；DAG/顺序执行内联在 `agent_runtime._llm_dispatch` / `goals.create_task` |
| `tasks.py` | `tasks.py` | ✅ 文件 | 任务表 + 状态机 + `recover_tasks()` |
| `tools.py` | `tools.py` | ✅ 文件 | **Tool 注册表 + `execute_tool` + `run_fc_loop` + LLM 调用**，是事实执行中枢 |
| `context/` | `context/`（builder） | ✅ 目录 | 上下文**构建**（models/builder/facade/sources），**非执行**；`context/models.py:WORKFLOW` 仅为上下文来源标签枚举 |
| `goal/` | `goals.py` + `goal_decision_engine.py` | ❌ 非独立包 | 无 `goal/` 目录；目标决策引擎 `goal_decision_engine.py:268` 单例 |
| `runtime` | `agent_runtime.py` + `ai_core/lifecycle.py` | ✅（两处） | 执行运行时 = `agent_runtime`；启动就绪 = `ai_core/lifecycle.py` |
| `memory` | `memory.py`（顶层） | ✅ 文件 | 记忆后端（Python）；前端 `memory.js` |
| `knowledge` | `knowledge_runtime/`（包）+ `knowledge.py`（facade） | ✅ 包+facade | 知识层已完成 Platform Sprint，单一入口 `knowledge.*` |
| `EventBus` | `eventbus.py` | ✅ 文件 | `bus` 单例（`:156`）；`DOMAIN_EVENT_NAMES`/`SYSTEM_EVENT_NAMES` 契约 |
| `Permission` | `policy_engine.py` + `permission_guard.py` | ✅ 两文件 | PolicyEngine（裁决）+ PermissionGuard（电脑能力闭环）；单例 `guard:165` |
| `Execution` | `tools.execute_tool`（`tools.py:3955`） | ❌ 非收口模块 | **事实执行点但无统一内核/无收口 API** |
| `Dispatcher` | 内联 `agent_runtime._llm_dispatch` / `goals.plan_goal` | ❌ 不存在 | 无 Dispatcher 模块；分发逻辑散落 |

**核验结论：** Sprint 文档假设存在的 `agent/` `planner/` `workflow/` `Dispatcher` **在代码中均不存在**；它们是内联在 `goals.py` + `agent_runtime.py` 的概念。任何 Stage 设计都不得新建这些名字的模块（会制造第二套），而应把逻辑收口进新建的 `ai_core/execution/`。

---

## 2. 执行入口（Execution Entry Points）

后端是标准库 `http.server` 线程模型（非 asyncio），所有请求经 `server.py:Handler.do_POST:968` 路由。

### 2.1 Chat 入口（对话链路）
```
POST /api/chat            server.py:972
  └─ _handle_chat         server.py:1838
       ├─ run_intent_gateway   intent_gateway.py:37   (命令面板/意图网关，可选前置)
       ├─ run_fc_loop     tools.py:3328               (LLM function-calling 闭环)
       │    └─ run_one    tools.py:3283 → execute_tool tools.py:3955
       └─ 兜底强化块        server.py:1994-2008
            └─ execute_tool server.py:2006            (意图检测命中的工具直接执行)
```
- SSE 流式：`emit` 闭包定义于 `server.py:1891`；chat 内 `tool_start`/`tool_end` 经 `emit` **直推 SSE**（`tools.py:3366/3368`），**绕过 EventBus**。
- 远程会话：`remote_allowed` 白名单裁剪工具（`_remote_allowed_tools()`），仅约束 chat 路径。

### 2.2 Goal 入口（目标/执行链路）
```
POST /api/agent/goal      server.py:1034
  └─ submit_goal          server.py:1392
       └─ agent_runtime.start / _loop / _run_goal
            ├─ goals.plan_goal      goals.py:380  (LLM 拆任务 :412 → create_task :452)
            └─ _execute_task        agent_runtime.py:202
                 ├─ policy_engine.evaluate  :222  (权限裁决)
                 ├─ request_approval        :227  (confirm 级)
                 └─ execute_tool            :231
```
- 启动：`main:2601` → `recover_tasks():2606` → `agent_runtime` 启动 `:2673`。
- 就绪：`ai_core/lifecycle.py` `Lifecycle` 单例 `:72`，`run_boot_self_check:49`，状态仅「未就绪→就绪」一次跃迁（`is_ready:45`）。

### 2.3 其他入口（非主链路）
- `social_inbound.py`：社交入站 → `run_fc_loop:115` → `execute_tool:124`（**裸调，无权限闸门**）。
- `reflector.py`：`execute_tool("add_knowledge", ...):88`（**裸调，无权限闸门**）。
- `proactive.py`：`submit_goal:795`（复用 goal 链路）、`tick_loop` 主动触发。
- `scheduler.py`：定时任务第二套生命周期（`TaskStatus:38`），`cancel:270` 仅取消「已调度未触发」。

---

## 3. Tool 路径（Tool Execution Path）

**唯一工具函数：`execute_tool(name, args, allowed=None)` — `tools.py:3955`。**

```python
def execute_tool(name, args, allowed=None):            # tools.py:3955
    if allowed is not None and name not in allowed:    # :3957 仅远程白名单
        return f"工具 {name} 在远程会话中不可用（受白名单限制）"
    fn = TOOL_FUNCS.get(name)                          # :3959 注册表查表
    if fn:
        try:
            return str(fn(args or {}))                 # :3962 直接调用，无权限/无超时
        except Exception as e:
            return f"工具执行失败：{e}"
    # 自定义工具（tool_factory）兜底                  # :3966-3969
    ...
```

**关键事实（红线相关）：`execute_tool` 内部没有任何权限裁决、没有 timeout、没有 retry、没有状态写入。** 它只是一个「查表→调用→吞异常」的薄壳。权限与生命周期完全由**调用方**负责。

- 注册表：`TOOLS:74`（schema）、`TOOL_FUNCS:3158`（实现映射）。
- `execute_tool_calls:3266` → `run_one:3283`（chat 路径封装）。
- 自定义工具：`tool_factory.execute_custom_tool`（动态 API 槽）。
- 电脑能力：`capability_registry.py`（`RISK_TIER:29`，`READONLY_TOOLS:122` 播种）→ 经 `PermissionGuard` 闭环，不直调 `execute_tool`。

---

## 4. Workflow 路径（Workflow Path）

**不存在独立 workflow 模块。** 任务序列执行内联在：
- `goals.plan_goal`（`goals.py:380`）：LLM 拆解目标为 task 列表（`create_task:452`）。
- `agent_runtime._run_goal`（`agent_runtime.py:108`）→ 顺序遍历 tasks → `_execute_task:202`。
- DAG/依赖：当前为**顺序执行**，无显式 DAG 调度器（除 `scheduler.py` 的定时触发，属第二套）。

→ 结论：Workflow 概念需要被新建的 `ExecutionQueue`/`ExecutionState`（Stage C/D）显式承载，而非继续内联。

---

## 5. Planner 路径（Planner Path）

**不存在独立 planner 模块。** 等价于：
- `goals.plan_goal`（`goals.py:380`）：组装 LLM prompt 拆解目标 → `create_task`。
- `agent_runtime._resolve_dispatch`（`agent_runtime.py:336`）→ `_llm_dispatch:344`：把 task 解析为具体 tool+args。

→ 本次 Sprint **严禁**修改 Planner/LLM 行为（红线）。Planner 输出（task 列表）只作为 `ExecutionQueue` 的输入，不被重写。

---

## 6. 生命周期（Lifecycle）

| 层 | 生命周期机制 | 位置 |
|---|---|---|
| 进程启动 | `main → recover_tasks → agent_runtime.start` | server.py:2601/2606/2673 |
| 就绪自检 | `Lifecycle` 单例，`self_check` 一次跃迁 | ai_core/lifecycle.py:49/72 |
| Chat 请求 | 单请求内 `run_fc_loop` 多轮（`MAX_ROUNDS=5:3332`），结束即消亡 | tools.py |
| Goal 任务 | `agent_runtime` 状态机 `{IDLE,PLANNING,EXECUTING,REFLECTING}:23`；`_cv.wait(timeout=1.0):102` | agent_runtime.py |
| Task 状态 | `tasks.py` 状态值 `:39/107/127`（open/running/done 等） | tasks.py |
| 电脑动作 | `PermissionGuard.plan → run` 构造+执行 | permission_guard.py:45/80 |

**缺口：** 没有统一的「Execution 生命周期」概念串联 chat 与 goal；chat 请求无持久生命周期对象，goal 生命周期与 task 表/`agent_runtime` 内存态三处各记一份。

---

## 7. 状态来源（State Sources）—— 四套，需收口

1. **tasks 表**（`tasks.py`）：持久化任务状态，`recover_tasks:165` 把 running→open。
2. **goals 表**（`goals.py` / db）：目标级状态。
3. **agent_runtime 内存态**（`agent_runtime.py:44-56`）：`_state`、`_consecutive_failures`、当前 task 指针——**进程重启即丢**。
4. **scheduler.TaskStatus**（`scheduler.py:38`）：定时任务的第二套生命周期。

**问题：** 同一「执行进度」四套源各记各的，无单一写出口。→ Stage D（ExecutionState）必须成为**唯一状态写源**，其余三套改为它的投影/只读镜像。

---

## 8. 事件来源（Event Sources）—— 三套通道，需统一

| 通道 | 位置 | 用途 | 问题 |
|---|---|---|---|
| **EventBus**（规范通道） | `eventbus.py` `bus` 单例 `:156`；`publish_domain:223` / `publish_system:271` | 领域/系统事件规范出口 | 规范，但**未被所有路径遵守** |
| **`proactive.SUBSCRIBERS`** 遗留队列 | `proactive.py:24` + `SUBSCRIBERS_LOCK` | SSE 订阅者直发（EventBus 失败时的 fallback） | `proactive.py`/`scene.py`/`server.py SSE fallback` 直接遍历此队列 `:247-248/:66-67/:2528` |
| **chat `emit` 直推 SSE** | `server.py:1891` 闭包 + `tools.py:3366/3368` | `tool_start`/`tool_end` 实时进度 | **绕过 EventBus**，前端靠 `event-bridge.js` 直接接 SSE |

**关键红线判定：** 现有代码**已守住**「单 EventBus 实例」红线（`eventbus.py:156` 全局单例，无第二 `EventBus` 类）。问题不是第二 EventBus，而是 **chat 路径与 proactive fallback 不经由 EventBus 发出事件**。→ Stage E 必须让所有执行事件**复用既有 EventBus**（禁新建第二 EventBus、禁扩 DOMAIN/SYSTEM 命名空间契约），legacy `SUBSCRIBERS` 仅作降级保留。

---

## 9. 取消机制（Cancellation）—— 基本缺失

| 路径 | 取消能力 |
|---|---|
| Chat 路径 | ❌ 无。请求在 `run_fc_loop` 内阻塞，前端无法中途取消单个工具调用；`execute_tool` 无 cancel 接口 |
| Goal 路径 | ⚠️ `agent_runtime.stop:67` **仅置 `_running=False`**，循环下次 `_cv.wait` 退出；不中断正在执行的 `execute_tool` 调用 |
| 电脑能力 | ✅ `computer_executor.cancel` 用 `threading.Event:112-135` + `fut.result(timeout=self.timeout):124` + subprocess timeout `:167`，**唯一真实可取消** |
| `agent_delegate` | ⚠️ `proc.communicate(timeout=...):78` 有超时但无主动 cancel |
| `scheduler` | ⚠️ `cancel:270` 仅取消「已调度未触发」的任务 |

**缺口：** 没有贯穿执行内核的 Cancel Token。`execute_tool` 不接受 cancel 信号。→ Stage F（ExecutionPolicy）须定义统一取消契约（可传播至 `execute_tool` 调用方与电脑能力），但**不得改变既有行为语义**，仅做收口与透传。

---

## 10. 恢复机制（Recovery）—— 弱

- **唯一恢复点：** `tasks.recover_tasks()`（`tasks.py:165`）——进程重启时把 `running` 任务回置 `open`，等重新调度。
- **无 checkpoint：** chat 路径无任何断点续传；goal 路径无中间 checkpoint（内存态重启即丢）。
- **无失败重试恢复策略：** goal 路径有 `_MAX_RETRIES=3`（`agent_runtime.py:54`），但 chat 路径无；无「重试后归档/升级人工」的统一定义。
- `goal_decision_engine._pre_approve:228-243` 仅做目标级预批准，非恢复。

→ Stage H（ExecutionRecovery）须建统一 Checkpoint/Resume/Recover/Restart，但**只能做收口与复用**，不能改 `recover_tasks` 既有语义（Move Never Rewrite）。

---

## 11. Timeout 与 Retry

### Timeout
- `execute_tool`：**无** timeout（工具可无限挂死，尤其中 `run_shell` 类）。
- LLM 调用：`agnes_completion(timeout=90)`（`tools.py:3340`、`context/llm.py:83`）。
- 兜底：`_fc_fallback timeout=60`（`tools.py:3320`）。
- 电脑能力：`computer_executor.timeout`（subprocess timeout `:167`）。
- 审批：`request_approval(timeout=300)`（`policy_engine.py:138`）。

### Retry
- Goal 路径：`_MAX_RETRIES=3`（`agent_runtime.py:54`）；网络错误退避重试 `:237-239`；文件错误尝试替代工具 `:240-245`；其余失败不重试 `:246-247`。
- Chat 路径：**无重试**，单轮失败即返回错误字符串。
- EventBus：`_dispatch` 重试+死信，`_MAX_RETRIES=2`（`eventbus.py:38/135`）。
- LLM：`context/llm.py` retries=2。

**不对称：** 同一 `execute_tool` 在两条链路上的 timeout/retry 语义完全不同，源于「调用方各自负责」。→ Stage F 必须把 timeout/retry 提升为**执行策略**（调用方注入），而非散落各处。

---

## 12. 完整调用链（End-to-End Call Chains）

### 12.1 Chat → Tool（无权限闸门）
```
_handle_chat (server.py:1838)
  → run_fc_loop (tools.py:3328)
      → execute_tool_calls (tools.py:3266) → run_one (tools.py:3283)
          → execute_tool (tools.py:3955)   [无 policy_engine，仅 remote_allowed 白名单]
              → TOOL_FUNCS[name](args)      [直接调用，无 timeout/retry/状态写入]
      → emit tool_start/end (tools.py:3366/3368)  [直推 SSE，绕过 EventBus]
  （兜底）server.py:2006 execute_tool   [同样无闸门]
```

### 12.2 Goal → Tool（有权限闸门）
```
submit_goal (server.py:1392)
  → agent_runtime._run_goal (agent_runtime.py:108)
      → goals.plan_goal (goals.py:380) → create_task (:452)   [不改 Planner 行为]
      → _execute_task (agent_runtime.py:202)
          → policy_engine.evaluate (agent_runtime.py:222)     [权限裁决]
          → request_approval (:227)                           [confirm 级]
          → execute_tool (:231)                               [共享同一 execute_tool]
          → _MAX_RETRIES 重试循环 (:221)
      → _emit_agent_domain("AGENT_WAITING"/"AGENT_DONE")      [经 EventBus]
```

### 12.3 Goal → Computer Capability（独立闭环）
```
_execute_task (:202) → is_known(tool) → _execute_computer_task (:215)
  → guard.plan (permission_guard.py:45)   [构造 ComputerAction]
  → guard.run  (:80) → policy_engine.decide/request_approval
  → computer_executor (唯一执行器，经 guard 调用)
```

**核心洞察：** 两条链路**共享** `execute_tool`，但**权限语义不同**——这是本次 Sprint 必须统一的第一要务：所有 `execute_tool` 调用都必须经由统一 Execution 内核，内核统一注入权限/超时/重试/状态/事件，调用方不再各自负责。

---

## 13. 重复风险与发散点（Duplication / Divergence Risks）

| 风险 | 证据 | 收口方向 |
|---|---|---|
| 双执行入口 | chat(`run_fc_loop`) vs goal(`agent_runtime`)，权限语义分裂 | Stage J：`Execution.run(...)` 统一收口 |
| 四套状态源 | §7 | Stage D：ExecutionState 唯一写源 |
| 三套事件通道 | §8 | Stage E：复用 EventBus，legacy 降级 |
| `execute_tool` 无闸门 | §3 | Stage J/F：内核注入权限 |
| 两套任务生命周期 | `tasks.py` vs `scheduler.TaskStatus` | Stage C：ExecutionQueue 统一队列语义 |
| 两套 LLM 封装 | `tools.agnes_completion` vs `context/llm.agnes_completion` | **本次 Sprint 禁改 LLM（红线）**，仅记录 |
| `reflector`/`social_inbound` 裸调 | §2.3 | Stage J：改经统一内核（行为不变，仅路由） |
| 概念漂移（agent/planner/workflow/Dispatcher 不存在） | §1 | 不新建这些名字；逻辑收口进 `ai_core/execution/` |

---

## 14. 权限策略（Permission Policy）—— 不对称，是头号风险

### 现有机制（已守住的红线）
- **单 PolicyEngine**：`policy_engine.py`，四级 `AUTO/CONFIRM/SESSION/NEVER`（`:28-31`）；`evaluate:97` / `request_approval:138` / `set_never:184`。
- **单 PermissionGuard 单例**：`permission_guard.py:165` `guard`；`plan:45` / `decide:55` / `run:80`；电脑能力唯一执行闭环。
- 无第二权限系统（capability_registry 仅声明，裁决委托 policy_engine）。

### 不对称（关键风险）
| 调用方 | 是否经 policy_engine/PermissionGuard | 行号 |
|---|---|---|
| `agent_runtime._execute_task`（goal 普通工具） | ✅ `evaluate` + `request_approval` | agent_runtime.py:218-231 |
| `agent_runtime._execute_computer_task`（电脑能力） | ✅ `guard.plan→run→policy_engine` | agent_runtime.py:277-286 |
| `server.py:2006`（chat 兜底工具） | ❌ 仅 `remote_allowed` 白名单 | server.py:2006 |
| `tools.run_one` → `execute_tool`（chat 主链路） | ❌ 无 | tools.py:3284 |
| `reflector.py:88`（`add_knowledge`） | ❌ 无 | reflector.py:88 |
| `social_inbound.py:124` | ❌ 无 | social_inbound.py:124 |

**判定：** `execute_tool` 本身无权限语义（§3），权限完全取决于调用方。chat/reflector/social_inbound 路径**绕过了 PolicyEngine**。这在「统一执行内核」视角下是最高优先级债务——但**本次 Sprint 严禁改权限裁决逻辑本身**（红线：不改 Policy/Permission 契约），只把「调用方各自负责」改为「Execution 内核统一注入权限评估」，且对 chat 路径保持行为等价（即不改变哪些工具被允许/拦截的现有结果，仅把散落的评估点收口到内核）。

---

## 15. 与既有冻结红线的兼容性判定

| 冻结红线（L0 / 通用） | 当前代码 | Audit 结论 |
|---|---|---|
| 单 Runtime | agent_runtime 单例 + 线程模型 | ✅ 未违规（但执行入口分裂，需收口非新建） |
| 单 Memory | memory.py | ✅ |
| 单 EventBus | eventbus.py:156 单例 | ✅ 未新建第二 EventBus |
| 单 Permission | policy_engine + guard 单例 | ✅ 未新建第二权限 |
| 事件契约 DOMAIN/SYSTEM 不扩张 | `publish_domain/publish_system` | ✅ 本次 Stage E 不扩命名空间 |
| 禁 RAG/Embedding/向量/DB | knowledge 层已闭合 | ✅ 不涉及 |
| 不改 Planner/Workflow/Goal/Agent/Tool 行为 | — | ⚠️ Stage A–J 只 Move/Extract，不改行为 |
| 禁云同步/联网/新 AI 功能 | — | ✅ 不涉及 |

**总判定：** 现有代码**已守住**单 Runtime/单 EventBus/单 Permission 红线；本次 Sprint 的收口动作（建 `ai_core/execution/`）**不引入第二套任何东西**，完全兼容。唯一需纠正的是「chat 路径绕过 PolicyEngine」——纠正方式为**收口路由**，不是新建权限系统。

---

## 16. Audit 交付物与下一步闸门

**本文件 = 硬性闸门交付物。** 依据 Sprint 指令「没有确认之前不得改代码」，以下动作**必须等待人工 Review 批准**后方可执行：

- Stage A：`ai_core/execution/context.py`（ExecutionContext）
- Stage B：`ai_core/execution/session.py`（ExecutionSession，单一状态源）
- Stage C：`ai_core/execution/queue.py`（ExecutionQueue）
- Stage D：`ai_core/execution/state.py`（ExecutionState）
- Stage E：`ai_core/execution/events.py`（复用 EventBus）
- Stage F：`ai_core/execution/policy.py`（Timeout/Retry/Permission/Interrupt/Cancel）
- Stage G：`ai_core/execution/metrics.py`
- Stage H：`ai_core/execution/recovery.py`
- Stage I：`ai_core/execution/reflection.py`
- Stage J：`ai_core/execution/api.py`（`Execution.run(...)` 统一收口）

**🛑 STOP — 等待 Review 批准。** 请确认本审计结论（特别是 §14 权限不对称、§7 四套状态源、§8 三套事件通道）作为 Stage A–J 的事实基线。批准后我将按 Move-Never-Rewrite / Extract-Never-Redesign / Behavior-Never-Change / Import-Refactor-Only 纪律逐 Stage 推进，并产出 15 份文档（01–15）落 `docs/ai-os/execution-platform/`。

---

*审计基线版本：2026-08-06 · 基于 `G:/xiao6/xiao6-ui` 当前工作树（unsaved 状态以磁盘为准）。所有行号取证于本会话实际读取，非推断。*
