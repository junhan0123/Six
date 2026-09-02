# Xiao6 v1.0.0 — S88 Architecture Truth Audit

**审计日期**: 2026-08-31
**审计性质**: 只读取证，禁止修改生产代码
**结论**: `ARCHITECTURAL SPLIT`

---

## 1. Executive Summary

Xiao6 v1.0.0 当前存在**两套独立的 Agent 执行体系**：

| 项目 | Chat Fast Path | AgentRuntime Path |
|------|----------------|-------------------|
| 定义文件 | `server_handlers_chat.py` | `agent_runtime.py` |
| 入口函数 | `run_fc_loop()` | `_run_goal()` / `submit_goal()` |
| 调度引擎 | LLM function calling (OpenAI compatible) | LLM task generation + 状态机 |
| 工具执行 | `execute_tool_calls()` → `capability_runtime.execute()` | `_resolve_dispatch()` → `execute_tool()` |
| Policy Gate | ✅ `ai_core.execution.run()` | ✅ Plan Gate → `ai_core.execution.run()` |
| Execution Core | ✅ `ai_core.execution.run()` | ✅ `ai_core.execution.run()` |
| EventBus | ✅ 只读（接收事件） | ✅ 读写（发布领域事件） |
| ContextEngine | ❌ 无 | ❌ 无（仅 stub） |
| Memory | ❌ 无自动集成 | ✅ `_distill_memory()` + `memory_distiller` |
| Recovery | ❌ 无（超轮次截断） | ✅ `_evaluate_round()` + `_do_replan()` |
| State Machine | ❌ 无 | ✅ IDLE/PLANNING/EXECUTING/OBSERVING/REFLECTING |
| Session 持久化 | ✅ `save_turn()` | ✅ Goal/Task DB 记录 |

**关键发现**：
1. Chat Fast Path 与 AgentRuntime 共享 `ai_core.execution.run()` 作为唯一 Execution Core 入口
2. 但 Chat Fast Path **完全绕过** AgentRuntime 的调度、状态机、Recovery、Memory 集成
3. 两者是**平行运行**的两套路径，而非统一架构
4. AgentRuntime 仅服务于长期目标（Goal System），不服务于 Chat 对话

**Architecture Verdict: C — ARCHITECTURAL SPLIT**

---

## 2. Current Runtime Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Input                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   /api/chat (POST)   │
              │   server.py:1184     │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  _handle_request()  │
              │  server_handlers_   │
              │  chat.py:160        │
              └──────────┬──────────┘
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
  ┌───────────────┐            ┌───────────────┐
  │ casual_chat   │            │ execution_    │
  │ path (tools=[])│            │ task path     │
  └───────┬───────┘            └───────┬───────┘
          │                             │
          ▼                             ▼
  ┌─────────────────────────────────────────────┐
  │              run_fc_loop()                  │
  │  server_handlers_chat.py:3360               │
  │  - LLM function calling (max 5 rounds)      │
  │  - 不经过 AgentRuntime                      │
  └──────────────────────┬──────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  execute_tool_calls │
              │  tools.py:3293      │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  capability_runtime │
              │  .execute()         │
              │  capability_runtime.│
              │  py:150             │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  ai_core.execution  │
              │  .run()             │
              │  api.py:28          │
              │  ← Policy Gate      │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  tools.execute_tool │
              │  tools.py:3930      │
              └─────────────────────┘

    ─────────────────────────────────────────────
    EventBus 侧（独立于 Chat）
    ─────────────────────────────────────────────
              ┌─────────────────────┐
              │  EventBus publish   │
              │  (chat → stream)    │
              └──────────┬──────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
    ┌───────────────┐      ┌───────────────┐
    │ AgentRuntime  │      │   SSE Stream   │
    │ (后台线程)     │      │  /api/stream   │
    │               │      │  EventSource   │
    │ 状态机：      │      └───────────────┘
    │ IDLE/PLAN/    │
    │ EXEC/OBS/     │
    │ REFLECT       │
    └───────┬───────┘
            │
            ▼
    ┌─────────────────────┐
    │ Goal System         │
    │ goals.create_goal() │
    └─────────────────────┘
```

---

## 3. /api/chat Real Call Chain

### 3.1 HTTP 入口

**File**: `G:/xiao6/xiao6-ui/server.py`

```python
# server.py:1184
@app.route('/api/chat', methods=['POST'])
def api_chat():
    # ...认证检查...
    data = request.get_json()
    messages = data.get('messages', [])
    user_text = messages[-1].get('content', '') if messages else ''
    
    # 意图分类
    intent = classify_intent(user_text)  # casual_chat / execution_task
    
    # 调用 handle_request
    return _handle_request(messages, user_text, intent, emit)
```

### 3.2 Request Handler

**File**: `G:/xiao6/xiao6-ui/server_handlers_chat.py`

```python
# server_handlers_chat.py:160
def _handle_request(messages, user_text, intent, emit):
    # ...
    if intent == "casual_chat":
        content, called = run_fc_loop(messages, emit, tools=[], ...)
    else:
        content, called = run_fc_loop(messages, emit, 
            tools=_cap_select(user_text), ...)
        # 兜底意图检测
        missed = [(name, args) for name, args in detect_intents(user_text) 
                  if name not in called]
    # ...
```

### 3.3 Function Calling Loop

**File**: `G:/xiao6/xiao6-ui/server_handlers_chat.py`

```python
# server_handlers_chat.py:3360
def run_fc_loop(messages, emit, tools=None, ...):
    MAX_ROUNDS = 5
    for _ in range(MAX_ROUNDS):
        # LLM 调用（OpenAI compatible）
        with agnes_completion(messages, tools=effective_tools, ...) as resp:
            data = json.loads(resp.read())
        
        tool_calls = msg.get('tool_calls') or []
        if not tool_calls:
            return content, called  # 最终回复
        
        # 执行工具调用
        tool_msgs, events = execute_tool_calls(tool_calls, ...)
        messages.extend(tool_msgs)
    # 超轮次保护
```

### 3.4 Tool Execution

**File**: `G:/xiao6/xiao6-ui/tools.py`

```python
# tools.py:3293
def execute_tool_calls(tool_calls, allowed=None, ...):
    for p in prepared:
        _res = capability_runtime.execute(p['name'], p['args'], ...)
    # ...
```

**File**: `G:/xiao6/xiao6-ui/capability_runtime.py`

```python
# capability_runtime.py:150
def execute(name, args, ...):
    from ai_core.execution import run as _execution_run
    raw = _execution_run(name, {"args": args}, ...)
    return CapabilityResult(...)
```

**File**: `G:/xiao6/xiao6-ui/ai_core/execution/api.py`

```python
# ai_core/execution/api.py:28
def run(task: str, context: dict = None, **kwargs) -> dict:
    # Step 1: Policy evaluation
    from policy_engine import evaluate, request_approval
    policy_result = evaluate(tool_name, tool_args, goal_id=goal_id, ...)
    
    # Step 2: Approval check (confirm level)
    if decision == "confirm":
        approval_result = request_approval(...)
    
    # Step 3: Execute tool
    from tools import execute_tool
    result = execute_tool(tool_name, tool_args, ...)
    
    # Step 4: Publish event
    ExecutionEvent.get().tool_finished(exec_session, ok=ok)
```

---

## 4. AgentRuntime Real Call Chain

### 4.1 启动入口

**File**: `G:/xiao6/xiao6-ui/server.py`

```python
# server.py:1192
agent_runtime.runtime.start()  # 后台线程启动
```

**File**: `G:/xiao6/xiao6-ui/agent_runtime.py`

```python
# agent_runtime.py:180
def start(self):
    self._thread = threading.Thread(target=self._loop, daemon=True)
    self._thread.start()
```

### 4.2 主循环

```python
# agent_runtime.py:200
def _loop(self):
    while self._running:
        if not self._queue:
            self.state = IDLE
            time.sleep(0.5)
            continue
        
        goal_id = self._queue.popleft()
        self.state = PLANNING
        self._run_goal(goal_id)
```

### 4.3 Goal 执行

```python
# agent_runtime.py:520
def _run_goal(self, goal_id):
    self.state = EXECUTING
    round_index = 0
    while round_index < MAX_ROUNDS:
        # 1. Plan Gate（Policy 预批准）
        self._plan_gate(goal_id, task_ids)
        
        # 2. 执行任务
        executions = []
        for t in tasks:
            tool, args = self._resolve_dispatch(t)
            res = execute_tool(tool, args)  # ← 进入 Execution Core
            executions.append(res)
            self._observe(goal_id, res)
        
        # 3. 评估轮次
        round_outcome = self._evaluate_round(goal_id, executions, ...)
        
        # 4. 状态收敛
        if round_outcome == "COMPLETE": break
        elif round_outcome == "REPLAN":
            new_ids = self._do_replan(goal_id)
        # ...
    
    # 5. Reflecting
    self.state = REFLECTING
    report = reflect(goal_id, executions_all)
    self._distill_memory("goal")  # ← Memory 集成
```

### 4.4 Tool Dispatch（AgentRuntime 路径）

```python
# agent_runtime.py:927
def _resolve_dispatch(self, task):
    tool, args = self._llm_dispatch(task, goal_id)
    return tool, args

def _llm_dispatch(self, task, goal_id):
    # LLM 决定调用哪个工具
    response = agnes_completion(messages, tools=..., ...)
    return tool_name, tool_args
```

---

## 5. run_fc_loop Analysis

**Definition**: `server_handlers_chat.py:3360`

```python
def run_fc_loop(messages, emit, tools=None, temperature=0.7, 
                reasoning=None, allowed=None, mode="smart", goal_id=None):
```

### 调用关系矩阵

| 组件 | 是否调用 | 证据 |
|------|---------|------|
| Planner | ⚠️ 间接 | LLM function calling 模拟 Planner，但无独立 Planner 模块 |
| Execution Core | ✅ 是 | `execute_tool_calls()` → `ai_core.execution.run()` |
| Policy | ✅ 是 | 通过 `ai_core.execution.run()` 中的 `evaluate()` |
| AgentRuntime | ❌ 否 | 无任何调用 |
| EventBus | ⚠️ 部分 | 只通过 `emit()` 推送工具事件，不直接访问 EventBus |
| ContextEngine | ❌ 否 | 无调用 |
| Memory | ❌ 否 | 无自动 Memory 集成 |
| Recovery | ❌ 否 | 仅超轮次截断，无真实 Recovery |

### 关键观察

```python
# run_fc_loop 内部：直接 LLM → Tool → LLM 循环
for _ in range(MAX_ROUNDS):  # 最多 5 轮
    # 1. LLM 调用（OpenAI compatible）
    with agnes_completion(messages, tools=effective_tools, ...) as resp:
        data = json.loads(resp.read())
    
    tool_calls = msg.get('tool_calls') or []
    if not tool_calls:
        return content, called  # 直接返回，不经过 AgentRuntime
    
    # 2. 执行工具
    tool_msgs, events = execute_tool_calls(tool_calls, ...)
    messages.extend(tool_msgs)
```

**结论**：`run_fc_loop` 是一个**独立的 LLM function calling 循环**，不依赖 AgentRuntime 的状态机或调度。

---

## 6. Execution Core Analysis

**File**: `G:/xiao6/xiao6-ui/ai_core/execution/api.py`

```python
def run(task: str, context: dict = None, **kwargs) -> dict:
    """Unified execution entry point with policy gate."""
    
    # Step 1: Policy evaluation
    policy_result = evaluate(tool_name, tool_args, goal_id=goal_id, ...)
    
    # Step 2: Approval check
    if decision == "confirm":
        approval_result = request_approval(...)
    
    # Step 3: Execute tool
    result = execute_tool(tool_name, tool_args, ...)
    
    # Step 4: Publish event
    ExecutionEvent.get().tool_finished(exec_session, ok=ok)
```

### Caller Map

| Caller | 调用方式 | 文件 |
|--------|---------|------|
| `capability_runtime.execute()` | `from ai_core.execution import run as _execution_run` | `capability_runtime.py:160` |
| `execute_tool_calls()` fallback | `from ai_core.execution import run as _execution_run` | `tools.py:3316` |
| `agent_runtime._run_goal()` | 间接通过 `_resolve_dispatch()` → `execute_tool()` | `agent_runtime.py:927` |

**结论**：`ai_core.execution.run()` 是**唯一的 Policy Gate 和执行入口**，被两条路径共享。

---

## 7. Policy Analysis

### Chat Fast Path Policy

```python
# ai_core/execution/api.py:76
policy_result = evaluate(tool_name, tool_args, goal_id=goal_id, 
                         default_deny=True, mode=mode)
```

### AgentRuntime Path Policy

```python
# agent_runtime.py:427（Plan Gate）
dec = _evaluate(tool, args, goal_id=goal_id, default_deny=True)
if dec.get("decision") == "confirm":
    d = _request(tool, args, summary=..., goal_id=goal_id, default_deny=True)
    if d == "approve":
        _approve(goal_id, tool)  # 预批准，后续执行命中缓存
```

### Policy 一致性

| 方面 | Chat | AgentRuntime |
|------|------|--------------|
| Policy Engine | ✅ 同一实例 | ✅ 同一实例 |
| default_deny | ✅ True | ✅ True |
| confirm 审批 | ✅ `request_approval()` | ✅ `request_approval()` + 预批准缓存 |
| 权限级别 | auto/confirm/session/never | auto/confirm/session/never |

**结论**：Policy 是**统一的**，两条路径都经过同一个 `PolicyEngine`。

---

## 8. Tool Execution Analysis

### Chat Fast Path Tool 调用链

```
run_fc_loop()
  ↓
execute_tool_calls()          # tools.py:3293
  ↓
capability_runtime.execute()  # capability_runtime.py:150
  ↓
ai_core.execution.run()       # policy gate
  ↓
tools.execute_tool()          # tools.py:3930
  ↓
CapabilityOS / MCP / 直接调用
```

### AgentRuntime Path Tool 调用链

```
_run_goal()
  ↓
_resolve_dispatch()           # agent_runtime.py:927
  ↓
_llm_dispatch()               # LLM 决定工具
  ↓
execute_tool()                # tools.py:3930
  ↓
capability_runtime.execute()  # fallback
  ↓
ai_core.execution.run()       # policy gate
```

### 差异

| 方面 | Chat Fast Path | AgentRuntime |
|------|---------------|--------------|
| 工具选择 | LLM function calling | LLM dispatch + Plan Gate |
| 并发执行 | ✅ ThreadPoolExecutor (readonly) | ❌ 顺序执行 |
| 结果包装 | CapabilityResult | 原始 str |
| 事件推送 | ✅ emit() | ❌ 通过 EventBus |

---

## 9. EventBus Analysis

### 订阅关系

**File**: `G:/xiao6/xiao6-ui/eventbus.py`

```python
# EventBus topics
TOPIC_SSE = "zz.sse"
TOPIC_HUD_STATE = "zz.hud.state"
TOPIC_GOAL_UPDATE = "zz.goal"
TOPIC_MOBILE_SYNC = "zz.mobile.sync"
TOPIC_CLIPBOARD = "zz.clipboard"
```

### Chat Fast Path 使用

```python
# server_handlers_chat.py:790
_sse_tokens.append(bus.subscribe(TOPIC_SSE, lambda ev: _sse_put(q, ev.payload)))
_sse_tokens.append(bus.subscribe(TOPIC_HUD_STATE, lambda ev: _sse_put(q, ev.payload)))
```

Chat 是 EventBus 的**消费者**，订阅 SSE 和 HUD 状态事件。

### AgentRuntime 使用

```python
# agent_runtime.py:1176
def _emit_agent_domain(self, name, goal_id=None):
    publish_domain(name, payload, source="agent_runtime")
```

AgentRuntime 是 EventBus 的**生产者**，发布领域事件。

### 事件流

```
AgentRuntime ──publish_domain()──→ EventBus ──subscribe()──→ Chat SSE
                                      ↑
                              /api/stream 消费者
```

**结论**：EventBus 是两条路径的**通信桥梁**，但 Chat 不通过 EventBus 触发 AgentRuntime。

---

## 10. ContextEngine Analysis

### 当前状态

**File**: `G:/xiao6/xiao6-ui/context/models.py`

```python
"""context.models — Context Models (stub for S79.7)
Minimal compatibility layer for context data structures.
"""
```

这是一个**stub**文件，只有数据结构定义，没有实际实现。

### Chat Fast Path Context

```python
# server_handlers_chat.py:394
{"role": "system", "content": build_context_prompt(user_text)}
```

手动拼接 system prompt，无 ContextEngine。

### AgentRuntime Context

无 ContextEngine 调用，直接通过 DB 读取 Goal/Task 状态。

**结论**：ContextEngine **未实现**，两条路径都未使用。

---

## 11. Memory Analysis

### Chat Fast Path Memory

```python
# server_handlers_chat.py:307
threading.Thread(target=compress_memory, daemon=True).start()
```

仅在异步线程中压缩记忆，**不自动检索历史记忆**。

### AgentRuntime Memory

```python
# agent_runtime.py:1051
def _distill_memory(self, session_id: str = "agent"):
    from memory_distiller import distill
    lessons = distill(messages)
    # 沉淀到 Memory
```

AgentRuntime 有**完整的 Memory 蒸馏和沉淀机制**。

**结论**：Memory 集成是**非对称的**，AgentRuntime 有 Memory 支持，Chat 没有。

---

## 12. Planner Analysis

### Chat Fast Path Planner

**不存在独立 Planner**。LLM function calling 直接承担 Planning 职责：

```python
# run_fc_loop 内部
with agnes_completion(messages, tools=effective_tools, ...) as resp:
    tool_calls = msg.get('tool_calls') or []
```

LLM 自己决定下一步调什么工具，没有显式的任务拆解/计划。

### AgentRuntime Planner

```python
# agent_runtime.py:937
def _llm_dispatch(self, task: dict, goal_id: int = None):
    # LLM 根据任务生成工具调用
    response = agnes_completion(messages, tools=..., ...)
```

AgentRuntime 有**显式的任务拆解和调度逻辑**：

```python
# _run_goal 内部
task_ids = plan_goal(goal_id)  # 创建任务列表
# 每轮执行所有 open 任务
for t in tasks:
    tool, args = self._resolve_dispatch(t)
```

**结论**：Planner 在 Chat 路径中是**隐式的（LLM 直接决策）**，在 AgentRuntime 路径中是**显式的（任务列表 + 状态机）**。

---

## 13. Recovery Analysis

### Chat Fast Path Recovery

```python
# server_handlers_chat.py:3376
except urllib.error.HTTPError as e:
    emit({"error": f"核心调用失败（HTTP {e.code}）"})
    fb = _fc_fallback(messages, emit)
    return (fb if fb else "（抱歉，核心暂时无法响应）"), called
```

**仅简单 fallback**，无重试、无分类、无状态恢复。

### AgentRuntime Recovery

```python
# agent_runtime.py:441
def _evaluate_round(self, goal_id, executions, max_steps_exceeded) -> str:
    # 返回: COMPLETE / CONTINUE / REPLAN / BLOCK / FAIL
    
# agent_runtime.py:474
def _do_replan(self, goal_id) -> list:
    # 重规划：递增 revision，创建新任务列表
    new_rev = bump_revision(goal_id)
    new_ids = plan_goal(goal_id, replan=True)
```

**完整的 Recovery 机制**：重试、重规划、状态机收敛。

**结论**：Recovery 是**非对称的**，AgentRuntime 有完整 Recovery，Chat 没有。

---

## 14. State Machine Analysis

### Chat Fast Path State

**无状态机**。每次请求独立处理，不保持跨请求状态：

```python
# run_fc_loop 是无状态的循环
for _ in range(MAX_ROUNDS):
    # LLM → Tool → LLM → Tool → ...
    # 结束后直接返回
```

### AgentRuntime State

**完整状态机**：

```python
# agent_runtime.py:30-40
STATE_IDLE = "IDLE"
STATE_PLANNING = "PLANNING"
STATE_EXECUTING = "EXECUTING"
STATE_OBSERVING = "OBSERVING"
STATE_REFLECTING = "REFLECTING"

# 状态转换
self.state = PLANNING   # 规划阶段
self.state = EXECUTING  # 执行阶段
self.state = OBSERVING  # 观察阶段（隐含在 _evaluate_round）
self.state = REFLECTING # 反思阶段
```

---

## 15. Chat vs AgentRuntime Comparison

| 组件 | Chat Fast Path | AgentRuntime | 差异 |
|------|---------------|--------------|------|
| **调度引擎** | LLM function calling | LLM task generation + FSM | 完全不同 |
| **Execution Core** | ✅ `ai_core.execution.run()` | ✅ `ai_core.execution.run()` | 共享 |
| **Policy Gate** | ✅ `evaluate()` | ✅ Plan Gate + `evaluate()` | 共享，AgentRuntime 多预批准 |
| **Tools** | ✅ 62 tools | ✅ 62 tools | 共享注册表 |
| **EventBus** | ✅ 订阅者 | ✅ 发布者 | 互补 |
| **ContextEngine** | ❌ 无 | ❌ 无 | 都缺失 |
| **Memory** | ❌ 无自动检索 | ✅ `_distill_memory()` | 非对称 |
| **Planner** | ❌ 隐式（LLM 直接决策） | ✅ 显式（任务列表） | 不同抽象层级 |
| **Recovery** | ❌ 仅 fallback | ✅ 重规划 + 状态收敛 | 非对称 |
| **State Machine** | ❌ 无 | ✅ IDLE/PLAN/EXEC/OBS/REFLECT | 关键差异 |
| **并发执行** | ✅ ThreadPoolExecutor | ❌ 顺序执行 | 不同策略 |
| **Session 持久化** | ✅ `save_turn()` | ✅ Goal/Task DB | 不同粒度 |

---

## 16. Multi-step Execution Evidence

### Chat Fast Path Multi-step

```python
# run_fc_loop 支持 5 轮 LLM-Tool 循环
for _ in range(MAX_ROUNDS):  # MAX_ROUNDS = 5
    # LLM 返回 tool_calls
    # execute_tool_calls() 执行
    # 结果回灌 messages
    # 下一轮 LLM 继续决策
```

**验证**：`10 × 10 = 100` 测试 PASS，证明 Chat Fast Path 支持多步工具调用。

**但**：这是 LLM function calling 的原生能力，**不是 AgentRuntime 的状态机驱动**。

### AgentRuntime Multi-step

```python
# _run_goal 内部轮循环
while round_index < MAX_ROUNDS:  # MAX_ROUNDS = 8
    # 1. Plan Gate（Policy 预批准）
    # 2. 执行所有 open 任务
    # 3. 评估轮次结果
    # 4. 状态收敛（COMPLETE/REPLAN/CONTINUE）
```

**验证**：Goal #77 `R1B契约验证：查询当前时间一次` 状态 `completed`。

---

## 17. Dual Runtime Assessment

### 是否存在两套 Runtime？

**答案：是**

| 维度 | 证据 |
|------|------|
| 独立入口 | `run_fc_loop()` vs `_run_goal()` |
| 独立调度 | LLM function calling vs 状态机 FSM |
| 独立生命周期 | 请求级 vs Goal 级 |
| 共享基础设施 | PolicyEngine、Execution Core、EventBus |
| 不共享组件 | ContextEngine（都缺失）、Memory（仅 AgentRuntime）、Recovery（仅 AgentRuntime） |

### 架构分裂程度

**HIGH**

原因：
1. Chat Fast Path 完全绕过了 AgentRuntime 的调度、状态机、Recovery
2. 两条路径的工具执行虽然共享 Execution Core，但调用链不同
3. Memory 和 Recovery 等非对称集成增加了维护复杂度
4. 没有统一的"Agent 入口"，开发者需要知道应该走哪条路径

---

## 18. Architecture Verdict

### 判定：C — ARCHITECTURAL SPLIT

**证据**：

1. **Chat Fast Path 是独立于 AgentRuntime 的执行体系**
   - 不经过 `AgentRuntime` 实例
   - 不使用 `AgentRuntime` 的状态机
   - 不使用 `AgentRuntime` 的 Recovery 机制

2. **共享基础设施不足以构成"统一架构"**
   - 共享 `ai_core.execution.run()` 和 `PolicyEngine` 是好的设计
   - 但缺少共享的调度层、状态管理层、Recovery 层

3. **非对称集成增加维护风险**
   - Memory：仅 AgentRuntime 有
   - Recovery：仅 AgentRuntime 有
   - Context：都缺失（未来需要统一）

4. **缺乏统一入口**
   - 开发者需要判断：这个请求应该走 Chat 还是 AgentRuntime？
   - 没有统一的 `Agent.dispatch()` 或类似接口

### 为什么不是其他 verdict？

| Verdict | 为什么不符合 |
|---------|-------------|
| A (UNIFIED) | Chat 和 AgentRuntime 不是共享统一执行核心，而是各自有独立调度 |
| B (VALID DUAL-PATH) | 虽然共享部分基础设施，但缺少关键的统一层（调度、状态、Recovery） |
| D (BROKEN) | AgentRuntime 功能完整，只是没有被 Chat 使用，不是"断裂" |

---

## 19. Risks

### 高风险

1. **维护债务**
   - 两条路径的工具执行逻辑需要分别维护
   - Policy 虽然在 Execution Core 统一，但 Chat 的 fallback 路径可能绕过

2. **功能不一致**
   - Chat Fast Path 没有 Memory 集成
   - Chat Fast Path 没有 Recovery 机制
   - 用户在使用 Chat 时体验与使用 Goal 时体验不同

3. **调试困难**
   - 问题可能出现在任意一条路径
   - 需要同时理解两套执行模型

### 中风险

4. **AgentRuntime 利用率低**
   - 如果 Chat 是主要入口，AgentRuntime 的大部分功能未被使用
   - 可能造成资源浪费

5. **架构演进阻力**
   - 未来统一两条路径需要重构 Chat Fast Path

### 低风险

6. **性能差异**
   - Chat Fast Path 并发执行（ThreadPoolExecutor）
   - AgentRuntime 顺序执行
   - 可能导致行为不一致

---

## 20. Recommended Next Phase

### Phase S89: Unified Agent Entry

**目标**：建立统一的 Agent 入口，让 Chat 和 AgentRuntime 共享同一套调度、状态、Recovery 机制。

**方案**：

```
User
 ↓
/api/chat
 ↓
UnifiedAgent.dispatch()          # 新增统一入口
 ↓
┌──────────────────────────────┐
│  Intent Classification       │
│  - casual_chat → LLM only    │
│  - execution_task → AgentRuntime │
│  - long_term_goal → Goal System │
└──────────────────────────────┘
 ↓
AgentRuntime._run_goal()       # 统一使用 AgentRuntime
 ↓
Execution Core                 # 共享
 ↓
Policy                         # 共享
 ↓
Tool                           # 共享
```

**具体步骤**：

1. **改造 `run_fc_loop()`**
   - 让 Chat 请求也经过 `AgentRuntime.submit_goal()`
   - 或让 `run_fc_loop()` 调用 `AgentRuntime` 的调度逻辑

2. **统一 Memory 集成**
   - Chat Fast Path 也需要自动检索历史记忆
   - 使用 `memory_distiller` 或类似机制

3. **统一 Recovery 机制**
   - Chat Fast Path 的工具失败需要进入 Recovery
   - 复用 `AgentRuntime._evaluate_round()` 的逻辑

4. **实现 ContextEngine**
   - 当前是 stub，需要实现真正的上下文管理
   - 统一 Chat 和 AgentRuntime 的上下文来源

5. **状态机统一**
   - Chat 也需要有状态（当前对话的上下文、工具调用链）
   - 可以复用 `AgentRuntime` 的状态机或简化版本

**预计工作量**：中等（2-3 天）

**风险**：可能影响现有 Chat 行为，需要充分测试

---

## 21. Git / Modification Check

```bash
$ git status --short
?? docs/XIAO6-S88-ARCHITECTURE-TRUTH-AUDIT-2026-08-31.md

$ git diff --stat
(no output - no production code changes)
```

**结论**：本次审计**未修改任何生产代码**，仅生成本报告。

---

## 附录 A：关键代码位置索引

| 组件 | 文件 | 行号 |
|------|------|------|
| Chat Handler | `server_handlers_chat.py` | 160-863 |
| run_fc_loop | `server_handlers_chat.py` | 3360-3411 |
| execute_tool_calls | `tools.py` | 3293-3332 |
| capability_runtime.execute | `capability_runtime.py` | 150-182 |
| ai_core.execution.run | `ai_core/execution/api.py` | 28-197 |
| AgentRuntime.start | `agent_runtime.py` | 180-195 |
| AgentRuntime._loop | `agent_runtime.py` | 200-360 |
| AgentRuntime._run_goal | `agent_runtime.py` | 520-620 |
| AgentRuntime._plan_gate | `agent_runtime.py` | 408-439 |
| AgentRuntime._evaluate_round | `agent_runtime.py` | 441-472 |
| AgentRuntime._do_replan | `agent_runtime.py` | 474-495 |
| PolicyEngine.evaluate | `policy_engine.py` | 需确认 |
| EventBus.publish_domain | `eventbus.py` | 需确认 |
| ContextEngine (stub) | `context/models.py` | 1-52 |

---

## 附录 B：状态机对照

### Chat Fast Path（无状态机）

```
请求到达
 ↓
run_fc_loop()
 ↓
[LLM → Tool → LLM → Tool → ...] (最多5轮)
 ↓
返回响应
 ↓
请求结束
```

### AgentRuntime（完整状态机）

```
IDLE
 ↓ submit_goal()
PLANNING
 ↓ plan_goal()
EXECUTING
 ↓ _run_goal()
 ├── OBSERVING（隐含）
 ├── EVALUATING（隐含）
 ├── COMPLETE → 终态
 ├── CONTINUE → EXECUTING（下一轮）
 ├── REPLAN → PLANNING（新 revision）
 └── FAIL → 终态
 ↓ reflect()
REFLECTING
 ↓ _distill_memory()
IDLE（或保持终态）
```

---

**审计完成**
**报告路径**: `G:\xiao6\docs\XIAO6-S88-ARCHITECTURE-TRUTH-AUDIT-2026-08-31.md`
**生产代码修改**: 0
**等待下一阶段指令**
