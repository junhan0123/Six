# Xiao6 v1.0.0 — S89 Unified Agent Runtime Design & Integration Plan

**审计日期**: 2026-09-01
**审计性质**: 基于 S88 发现，验证当前集成状态，设计最终统一方案
**结论**: `PARTIAL — Architecture Unified, Migration Incomplete`

---

## 1. Executive Summary

### S88 结论校正

S88 报告声称 "Chat → AgentRuntime: NOT CONNECTED"，但**实际代码显示该结论已过时**。

当前状态（基于 `git log` 和代码审查）：

```
Commit 0f48262 (UI-R2-G): "final runtime and UI regression closure"
  - 新增 agent_runtime.run_chat_turn() 方法
  - 更新 server_handlers_chat.py 调用 run_chat_turn()
  
Commit 39bda30 (v1.0.0 production freeze):
  - run_chat_turn() 已稳定集成
```

### 当前集成状态

| 组件 | S88 结论 | 实际状态 | 差异 |
|------|---------|---------|------|
| Chat → AgentRuntime | NOT CONNECTED | **CONNECTED** | S88 过时 |
| run_fc_loop 调用 | 独立执行 | **被 run_chat_turn 包装** | 已改进 |
| State Machine | 无 | **已添加** (IDLE→EXECUTING→IDLE) | 已改进 |
| Memory Integration | 无 | **已添加** (_distill_chat_memory) | 已改进 |
| Recovery | 无 | **仍缺失** | 未改进 |
| ContextEngine | STUB | **仍为 STUB** | 未改进 |

### 核心问题

**`run_chat_turn()` 是包装器，不是真正的统一执行**

```python
# agent_runtime.py:134-139
def run_chat_turn(self, messages, emit, ...):
    self.state = EXECUTING
    # ...
    from tools import run_fc_loop as _run_fc_loop
    content, called = _run_fc_loop(  # ← 仍然调用旧路径
        messages, emit, tools=tools, ...
    )
    # ...
    self.state = IDLE
```

`run_chat_turn()` 只添加了状态转换和 Memory 蒸馏，**执行逻辑仍然是 `run_fc_loop()`**。

---

## 2. S88 Findings Recap

S88 正确识别了两条路径：

### Chat Fast Path
```
/api/chat → _handle_request() → run_fc_loop()
  → LLM function calling (max 5 rounds)
  → execute_tool_calls() → capability_runtime.execute()
  → ai_core.execution.run() ← Policy Gate
  → tools.execute_tool()
```

### AgentRuntime Path
```
Goal/Task → AgentRuntime._run_goal()
  → Plan Gate (Policy pre-approval)
  → _resolve_dispatch() → execute_tool()
  → ai_core.execution.run() ← Policy Gate
  → _observe() → _evaluate_round()
  → COMPLETE / CONTINUE / REPLAN / FAIL
  → _distill_memory()
```

**S88 正确结论**: 两条路径共享 Execution Core 和 Policy，但缺乏统一调度层。

---

## 3. AgentRuntime Capability Audit

### 当前接口

```python
class AgentRuntime:
    def __init__(self)
    def start(self)  # 启动后台线程
    def stop(self)   # 停止后台线程
    
    # Goal 执行入口
    def submit_goal(self, title, description, intent_id) -> int
    
    # Chat 执行入口（新增）
    def run_chat_turn(self, messages, emit, user_text, tools, ...) -> tuple
    
    # 状态查询
    def get_state(self) -> dict
    
    # 内部方法（不应公开）
    def _run_goal(self, goal_id)
    def _loop(self)
    def _plan_gate(self, goal_id, task_ids)
    def _evaluate_round(self, goal_id, executions, max_steps_exceeded)
    def _do_replan(self, goal_id)
    def _resolve_dispatch(self, task)
    def _llm_dispatch(self, task, goal_id)
    def _observe(self, goal_id, res)
    def _distill_memory(self, session_id)
    def _distill_chat_memory(self, user_text, called_tools)  # 新增
```

### Chat 承载能力评估

| 能力 | 是否支持 | 证据 |
|------|---------|------|
| 短生命周期请求 | ✅ 是 | `run_chat_turn()` 同步执行，不依赖后台线程 |
| session_id | ⚠️ 部分 | `goal_id` 可选传入，但无独立 session 管理 |
| conversation history | ✅ 是 | `messages` 列表作为参数传入 |
| context | ⚠️ 部分 | 通过 `build_context_prompt()` 构建，非统一 ContextEngine |
| final response | ✅ 是 | 返回 `(content, called)` |
| tool events | ✅ 是 | 通过 `emit()` 回调推送 |
| state | ✅ 是 | 状态机转换 (IDLE→EXECUTING→IDLE) |
| trace | ⚠️ 部分 | ExecutionTrace 记录，但无跨请求追踪 |
| SSE | ✅ 是 | 通过 `emit()` 推送，EventBus 订阅 |
| 纯聊天 | ✅ 是 | `tools=[]` 时 LLM 直接回复 |
| 单工具 | ✅ 是 | LLM function calling |
| 多工具 | ✅ 是 | LLM function calling 循环 (max 5 rounds) |
| 多轮工具 | ✅ 是 | `run_fc_loop()` 支持最多 5 轮 |
| Recovery | ❌ 否 | 无重试/重规划逻辑 |
| Memory 自动集成 | ✅ 是 | `_distill_chat_memory()` 异步蒸馏 |
| ContextEngine | ❌ 否 | stub 未实现 |

### Goal/Task 强绑定逻辑分析

**Goal-specific（不可复用）**:

```python
# agent_runtime.py:83-95
def submit_goal(self, title, description, intent_id):
    from goals import create_goal  # ← Goal DB 写入
    g = create_goal(...)
    self._queue.append(g.id)  # ← 后台线程队列
```

 Goal 创建、队列管理、后台线程调度对 Chat 不适用。

**Generic Agent（可复用）**:

```python
# agent_runtime.py:538-569
def _evaluate_round(self, goal_id, executions, max_steps_exceeded) -> str:
    # 通用评估逻辑：COMPLETE/CONTINUE/REPLAN/FAIL
    # 不依赖 Goal DB，只依赖执行结果
```

```python
# agent_runtime.py:474-492
def _do_replan(self, goal_id) -> list:
    # 重规划逻辑
    # 依赖 goals.bump_revision + plan_goal
    # 对 Chat 不适用（Chat 不需要 revision 管理）
```

**关键洞察**: `_evaluate_round()` 的评估逻辑可以抽象为通用函数，但 Goal/Task 的持久化逻辑是 Chat 不需要的。

---

## 4. run_fc_loop Audit

### 当前实现

**File**: `G:/xiao6/xiao6-ui/tools.py:3360`

```python
def run_fc_loop(messages, emit, tools=None, temperature=0.7, 
                reasoning=None, allowed=None, mode="smart", goal_id=None):
    MAX_ROUNDS = 5
    called = set()
    effective_tools = tools if tools is not None else TOOLS
    
    for _ in range(MAX_ROUNDS):
        # 1. LLM 调用
        with agnes_completion(messages, tools=effective_tools, ...) as resp:
            data = json.loads(resp.read())
        
        tool_calls = msg.get('tool_calls') or []
        if not tool_calls:
            return content, called  # 最终回复
        
        # 2. 执行工具
        tool_msgs, events = execute_tool_calls(tool_calls, ...)
        messages.extend(tool_msgs)
    
    # 超轮次保护
    ...
```

### Chat-specific Responsibility 分析

| 功能 | Chat 必需？ | 归谁管理？ |
|------|-----------|-----------|
| LLM function calling 循环 | ✅ 是 | `run_fc_loop()` |
| Tool schema 下发 | ✅ 是 | `run_fc_loop()` |
| 工具执行 | ✅ 是 | `execute_tool_calls()` → `capability_runtime.execute()` |
| Policy Gate | ✅ 是 | `ai_core.execution.run()` |
| SSE emit | ✅ 是 | `emit()` 回调 |
| Conversation history | ✅ 是 | `messages` 列表 |
| Session 持久化 | ✅ 是 | `save_turn()` (在 handler 层) |
| Final answer formatting | ✅ 是 | LLM 返回 content |
| Tool fallback | ⚠️ 部分 | `_fc_fallback()` 在异常时 |
| 兜底意图检测 | ⚠️ 部分 | `detect_intents()` (在 handler 层) |
| 天气/热点弹窗 | ❌ 否 | handler 层处理 |
| Memory 压缩 | ❌ 否 | handler 层异步处理 |

### 结论

`run_fc_loop()` 承担了 Chat 的核心执行逻辑（LLM 循环 + Tool 执行），这些应该：
1. **保留**作为内部执行引擎
2. **但不应暴露为公共 API**
3. **应由 AgentRuntime 内部管理**

---

## 5. ContextEngine Audit

### 当前状态

**File**: `G:/xiao6/xiao6-ui/context/models.py`

```python
"""context.models — Context Models (stub for S79.7)
Minimal compatibility layer for context data structures.
"""
```

**只有数据结构，没有实现**。

**File**: `G:/xiao6/xiao6-ui/context/facade.py`

```python
def build_context_prompt(user_text: str = "") -> str:
    """Chat 系统提示词入口（与 legacy 实现同源：memory.build_system_prompt）。"""
    try:
        import memory
        return memory.build_system_prompt(user_text or "")
    except Exception:
        return ""

def build_cognitive_context(goal_id=None, task=None, mode="plan", tier=None) -> str:
    """P5.1：Agent Runtime 的 Planner Context 唯一入口。
    复用 Chat 同一 Context 组装（memory.build_system_prompt）...
    """
    # 实际实现...
```

### 结论

**ContextEngine = architectural dependency (STUB)**

- `context/models.py` 只有 stub
- `context/facade.py` 是 workaround（直接调用 `memory.build_system_prompt()`）
- 没有统一的 Context 管理
- Chat 和 AgentRuntime 都手动构建 context

**影响**: 这是 S89 的关键阻塞项。如果要实现真正的统一架构，需要：
1. 实现 ContextEngine 接口
2. 统一 Chat 和 AgentRuntime 的 context 来源

---

## 6. Memory Audit

### 当前状态

**Chat Fast Path**:
```python
# server_handlers_chat.py:518
threading.Thread(target=compress_memory, daemon=True).start()
```

异步压缩，无自动检索。

**AgentRuntime Path**:
```python
# agent_runtime.py:1051
def _distill_memory(self, session_id: str = "agent"):
    from memory_distiller import distill
    lessons = distill(messages)
    # 沉淀到 Memory
```

完整蒸馏 + 沉淀。

**run_chat_turn()**:
```python
# agent_runtime.py:171
def _distill_chat_memory(self, user_text, called_tools):
    from memory_distiller import distill
    lessons = _distill([{"role": "user", "content": user_text}])
    if lessons:
        from cognitive.memory_adapter import record_conversation_memory
        record_conversation_memory([...], session_id="chat")
```

新增的 Chat Memory 蒸馏。

### 问题

1. **三套 Memory 逻辑并存**:
   - `compress_memory()` (handler 层)
   - `_distill_memory()` (AgentRuntime Goal 路径)
   - `_distill_chat_memory()` (AgentRuntime Chat 路径)

2. **不统一**:
   - Chat 路径有蒸馏但无检索
   - Goal 路径有完整蒸馏 + 沉淀
   - 没有统一的 Memory lifecycle 管理

3. **重复代码**:
   - `_distill_memory()` 和 `_distill_chat_memory()` 逻辑相似

### 建议

将 Memory 蒸馏统一为 AgentRuntime 的方法：
```python
def distill_memory(self, messages, session_id="default"):
    """统一 Memory 蒸馏入口。"""
    from memory_distiller import distill
    lessons = distill(messages)
    if lessons:
        from cognitive.memory_adapter import record_conversation_memory
        record_conversation_memory(messages, session_id=session_id)
```

然后 `run_chat_turn()` 调用此方法，而不是有自己的 `_distill_chat_memory()`。

---

## 7. Recovery Audit

### 当前状态

**Chat Fast Path**:
```python
# tools.py:3376
except urllib.error.HTTPError as e:
    emit({"error": f"核心调用失败（HTTP {e.code}）"})
    fb = _fc_fallback(messages, emit)
    return (fb if fb else "（抱歉，核心暂时无法响应）"), called
```

简单 fallback，无重试、无分类。

**AgentRuntime Path**:
```python
# agent_runtime.py:441
def _evaluate_round(self, goal_id, executions, max_steps_exceeded) -> str:
    # 返回: COMPLETE / CONTINUE / REPLAN / BLOCK / FAIL

# agent_runtime.py:474
def _do_replan(self, goal_id) -> list:
    # 重规划：递增 revision，创建新任务列表
```

完整 Recovery 机制。

### 问题

Chat 路径**完全没有 Recovery**。工具失败后直接返回错误，没有：
- 重试
- 替代方案
- 状态恢复
- 用户通知

### 建议

为 Chat 路径添加最小 Recovery：
```python
def run_chat_turn(self, messages, emit, ...):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            content, called = self._execute_chat_turn(messages, emit, ...)
            if self._is_success(content):
                return content, called
            # 失败，重试
            messages.append({"role": "assistant", "content": f"[尝试 {attempt+1} 失败，重试...]})
        except Exception as e:
            if attempt == max_retries - 1:
                emit({"error": f"执行失败：{e}"})
                return f"（抱歉，处理出错：{e}）", set()
```

---

## 8. Planner Audit

### 当前状态

**Chat Fast Path**:
- **无显式 Planner**
- LLM function calling 直接决策工具调用
- 没有任务拆解、没有计划生成

**AgentRuntime Path**:
```python
# agent_runtime.py:927
def _resolve_dispatch(self, task):
    tool, args = self._llm_dispatch(task, goal_id)
    return tool, args

def _llm_dispatch(self, task, goal_id):
    # LLM 根据任务生成工具调用
```

LLM dispatch 是 Planner 的简化版本，但不是完整的 Planning。

### 问题

Chat 路径缺少：
1. 任务拆解（复杂请求 → 子任务）
2. 执行计划（顺序/并行/依赖）
3. 进度跟踪

### 建议

为 Chat 添加轻量 Planner：
```python
def _plan_chat_turn(self, user_text, tools):
    """轻量 Planner：判断是否需要拆解任务。"""
    # 简单规则：
    # - 单工具请求 → 直接执行
    # - 多工具请求 → LLM 拆解为子任务
    # - 简单聊天 → 不下发工具
    if is_simple_chat(user_text):
        return [{"type": "direct", "tools": []}]
    elif is_multi_step(user_text):
        return self._llm_plan(user_text, tools)
    else:
        return [{"type": "direct", "tools": tools}]
```

---

## 9. Session/Transport Audit

### 当前状态

**Session 管理**:
- Chat: `save_turn(session_id, "xiao6", content)` 在 handler 层
- AgentRuntime: Goal/Task DB 记录
- 无统一 Session 概念

**Transport 耦合**:
```python
# server_handlers_chat.py:352
content, called = _ar.runtime.run_chat_turn(
    messages, emit,  # ← emit 是 HTTP response 回调
    ...
)
```

`emit` 参数将 HTTP transport 耦合进 AgentRuntime。

### 问题

1. **Transport 耦合**: AgentRuntime 依赖 HTTP `emit` 回调
2. **Session 分散**: Chat session 和 Agent session 分开管理
3. **无统一 abstraction**: 没有 ExecutionContext 概念

### 建议

引入 ExecutionContext:
```python
@dataclass
class ExecutionContext:
    session_id: str
    user_id: str
    tools: list
    goal_id: Optional[int]
    emit: Optional[Callable]  # 可选，用于 SSE
    memory_session: str = "default"

class AgentRuntime:
    def run_chat_turn(self, ctx: ExecutionContext) -> ChatResult:
        """统一 Chat 执行入口。"""
```

---

## 10. Proposed Unified Architecture

### 目标架构

```
User
 ↓
/api/chat
 ↓
_handle_request() (Transport Layer)
 ↓
AgentRuntime.run_chat_turn(ctx) (Execution Layer)
 ↓
┌─────────────────────────────────────────┐
│  Unified Chat Execution                 │
│                                         │
│  1. Light-weight Planner                │
│     - 判断任务复杂度                     │
│     - 决定工具集合                       │
│                                         │
│  2. State Machine                       │
│     IDLE → PLANNING → EXECUTING → IDLE  │
│                                         │
│  3. Execution Loop (原 run_fc_loop)      │
│     - LLM function calling              │
│     - Tool execution                    │
│     - Policy gate                       │
│                                         │
│  4. Recovery                            │
│     - 失败重试                          │
│     - 降级处理                          │
│                                         │
│  5. Memory Distillation                 │
│     - 统一蒸馏入口                      │
│     - 异步沉淀                          │
└─────────────────────────────────────────┘
 ↓
Execution Core (ai_core.execution.run)
 ↓
Policy (PolicyEngine)
 ↓
Tools
 ↓
Response
```

### 关键设计决策

1. **`run_fc_loop()` 保留但内部化**
   - 改为 `AgentRuntime._execute_fc_loop()`
   - 不再作为 public API
   - 减少代码重复

2. **新增 `run_chat_turn()` 的真正实现**
   - 不再包装 `run_fc_loop()`
   - 使用统一的状态机
   - 添加 Recovery 和轻量 Planner

3. **统一 Memory 蒸馏**
   - 删除 `_distill_chat_memory()`
   - 复用 `_distill_memory()` 逻辑
   - 添加 session_id 参数

4. **解耦 Transport**
   - 移除 `emit` 参数
   - 使用 ExecutionContext 抽象
   - Handler 层负责 SSE 转换

---

## 11. Exact Code Changes

### 变更 1: 内部化 run_fc_loop

**File**: `G:/xiao6/xiao6-ui/tools.py`

```python
# 当前（第 3360 行）
def run_fc_loop(messages, emit, tools=None, ...):
    ...

# 修改为
def _run_fc_loop(messages, emit, tools=None, ...):
    """Internal: LLM function calling loop. Use AgentRuntime.run_chat_turn() instead."""
    ...
```

**File**: `G:/xiao6/xiao6-ui/server_handlers_chat.py`

```python
# 当前（第 40 行）
from tools import TOOL_FUNCS, TOOLS, detect_intents, run_fc_loop, ...

# 修改为
from tools import TOOL_FUNCS, TOOLS, detect_intents, _run_fc_loop, ...
```

### 变更 2: 重写 run_chat_turn

**File**: `G:/xiao6/xiao6-ui/agent_runtime.py`

```python
def run_chat_turn(self, messages, emit, user_text="", tools=None,
                  temperature=0.7, reasoning=None, allowed=None,
                  mode="smart", goal_id=None) -> tuple:
    """Unified chat execution through AgentRuntime.
    
    真正统一执行：
    1. 轻量 Planner：判断任务复杂度
    2. 状态机：IDLE → PLANNING → EXECUTING → IDLE
    3. Execution Loop：LLM function calling + Tool execution
    4. Recovery：失败重试
    5. Memory：统一蒸馏
    """
    # 1. 状态转换
    prev_state = self.state
    self.state = PLANNING
    self._publish_state(PLANNING)
    
    try:
        # 2. 轻量 Planner
        plan = self._plan_chat_turn(user_text, tools)
        
        # 3. 执行（使用内部 run_fc_loop）
        self.state = EXECUTING
        self._publish_state(EXECUTING)
        
        content, called = self._execute_chat_turn(
            messages, emit, plan, temperature, reasoning,
            allowed, mode, goal_id
        )
        
        # 4. 发布完成事件
        self._emit_agent_domain("AGENT_COMPLETED", goal_id)
        
        # 5. Memory 蒸馏（统一入口）
        if user_text:
            self._distill_memory([{"role": "user", "content": user_text}], session_id="chat")
        
        return content, called
        
    except Exception as e:
        self._emit_agent_domain("AGENT_FAILED", goal_id, error=str(e))
        emit({"error": f"执行失败：{e}"})
        return f"（抱歉，处理出错：{e}）", set()
    
    finally:
        self.state = IDLE
        self._publish_state("idle")
        if prev_state and prev_state != IDLE:
            self.state = prev_state


def _plan_chat_turn(self, user_text, tools):
    """轻量 Planner：判断任务复杂度。"""
    # 简单聊天：不下发工具
    if self._is_simple_chat(user_text):
        return {"type": "direct", "tools": [], "steps": 1}
    
    # 复杂任务：使用提供的工具
    return {"type": "function_calling", "tools": tools or TOOLS, "steps": 5}


def _is_simple_chat(self, text):
    """判断是否为简单聊天。"""
    simple_patterns = [
        r"^(你好|您好|嗨|hello|hi|在吗|谢谢|你好呀)",
        r"^(你是谁|介绍一下自己|自我介绍)",
        r"^(几点了|现在时间|今天星期)",
    ]
    for pattern in simple_patterns:
        if re.match(pattern, text.strip()):
            return True
    return False


def _execute_chat_turn(self, messages, emit, plan, temperature, reasoning, 
                       allowed, mode, goal_id):
    """执行 Chat turn（内部方法）。"""
    if plan["type"] == "direct" and not plan["tools"]:
        # 简单聊天：不下发工具
        return self._run_fc_loop(messages, emit, tools=[],
                                  temperature=temperature, reasoning=reasoning,
                                  allowed=allowed, mode=mode, goal_id=goal_id)
    else:
        # 复杂任务：使用 function calling
        return self._run_fc_loop(messages, emit, tools=plan["tools"],
                                  temperature=temperature, reasoning=reasoning,
                                  allowed=allowed, mode=mode, goal_id=goal_id)


def _distill_memory(self, messages, session_id="default"):
    """统一 Memory 蒸馏入口。"""
    try:
        from memory_distiller import distill as _distill
        lessons = _distill(messages)
        if lessons:
            from cognitive.memory_adapter import record_conversation_memory
            record_conversation_memory(messages, session_id=session_id)
    except Exception:
        pass  # best-effort


# 删除旧的 _distill_chat_memory 方法
# def _distill_chat_memory(self, user_text, called_tools):
#     ...
```

### 变更 3: 简化 server_handlers_chat.py

**File**: `G:/xiao6/xiao6-ui/server_handlers_chat.py`

```python
# 当前（第 349-381 行）
if _intent == "casual_chat":
    try:
        import agent_runtime as _ar
        content, called = _ar.runtime.run_chat_turn(...)
    except Exception as _e:
        content, called = run_fc_loop(...)  # fallback
    missed = []
else:
    try:
        import agent_runtime as _ar
        content, called = _ar.runtime.run_chat_turn(...)
    except Exception as _e:
        content, called = run_fc_loop(...)  # fallback
    # 兜底意图检测...

# 修改为：移除 fallback，统一走 AgentRuntime
if _intent == "casual_chat":
    content, called = agent_runtime.runtime.run_chat_turn(
        messages, emit, user_text=user_text, tools=[],
        temperature=temperature, reasoning=reasoning, 
        allowed=remote_allowed, mode=mode, goal_id=goal_id,
    )
    missed = []
else:
    content, called = agent_runtime.runtime.run_chat_turn(
        messages, emit, user_text=user_text,
        tools=_cap_select(user_text, allowed=remote_allowed),
        temperature=temperature, reasoning=reasoning, 
        allowed=remote_allowed, mode=mode, goal_id=goal_id,
    )
    # 兜底意图检测...
```

---

## 12. Migration Strategy

### Phase 1: 内部化 run_fc_loop (低风险)

1. 重命名 `run_fc_loop` → `_run_fc_loop`
2. 更新所有导入
3. 验证无 breaking changes

### Phase 2: 添加轻量 Planner (中风险)

1. 实现 `_plan_chat_turn()`
2. 实现 `_is_simple_chat()`
3. 测试简单聊天和复杂任务

### Phase 3: 统一 Memory 蒸馏 (低风险)

1. 删除 `_distill_chat_memory()`
2. 统一使用 `_distill_memory()`
3. 验证 Memory 蒸馏正常工作

### Phase 4: 移除 fallback (中风险)

1. 移除 `server_handlers_chat.py` 中的 try/except fallback
2. 验证 AgentRuntime 稳定性
3. 监控错误日志

---

## 13. Compatibility

### 向后兼容

- ✅ `run_chat_turn()` 签名不变
- ✅ 返回类型不变 `(content, called)`
- ✅ SSE 事件格式不变
- ✅ Policy Gate 保持不变
- ✅ Tool execution 保持不变

### 行为变更

- ⚠️ `run_fc_loop()` 变为内部方法（`_run_fc_loop()`）
- ⚠️ 简单聊天可能不下发工具（由 Planner 判断）
- ⚠️ Memory 蒸馏统一入口（可能影响蒸馏频率）

### 测试覆盖

必须验证：
1. 简单聊天：`"hello"` → LLM 直接回复
2. 单工具：`"3 + 5"` → calculator 执行
3. 多工具：`"10 × 10"` → 多轮 function calling
4. Goal 创建：`"创建一个任务..."` → submit_goal
5. SSE：EventSource 连接正常
6. Memory：蒸馏异步执行

---

## 14. Security

### Policy Gate

- ✅ 所有工具执行经过 `ai_core.execution.run()`
- ✅ `default_deny=True` 保持不变
- ✅ confirm 级别工具需要审批

### 输入验证

- ✅ `user_text` 长度限制
- ✅ `tools` schema 验证
- ✅ `goal_id` 权限检查

### 资源限制

- ✅ `MAX_ROUNDS = 5` 防止无限循环
- ✅ `MAX_STEPS = 16` 防止过度执行
- ✅ 超时处理

---

## 15. Test Results

### 当前测试结果（S89 开始前）

| 测试 | 状态 | 备注 |
|------|------|------|
| /api/chat hello | ✅ PASS | LLM 直接回复 |
| /api/chat 3 + 5 | ✅ PASS | calculator 执行 |
| /api/stream | ✅ PASS | SSE 事件正常 |
| /api/agent/state | ✅ PASS | 状态 IDLE |
| /api/tools/list | ✅ PASS | 62 tools |
| /api/memory/query | ✅ PASS | 返回空结果 |
| /api/models | ✅ PASS | 9 models |
| /api/capability_os/catalog | ✅ PASS | 33 total, 27 available |

### 待验证测试（S89 修改后）

- [ ] 简单聊天（无工具）
- [ ] 单工具调用
- [ ] 多工具调用（10×10）
- [ ] Goal 创建和执行
- [ ] SSE 事件推送
- [ ] Memory 蒸馏
- [ ] Policy 审批流程
- [ ] 错误恢复

---

## 16. Before/After Call Graph

### Before (当前)

```
User → /api/chat → _handle_request()
  ├── casual_chat → run_fc_loop() → LLM → Tool → Response
  └── execution_task → run_fc_loop() → LLM → Tool → Response
                      ↓ fallback
                      run_fc_loop() (直接调用)

User → Goal → AgentRuntime.submit_goal()
  → _run_goal() → Plan Gate → _resolve_dispatch() → Tool → Response
```

### After (目标)

```
User → /api/chat → _handle_request()
  └── AgentRuntime.run_chat_turn()
        ├── _plan_chat_turn() → 简单聊天/复杂任务
        ├── _execute_chat_turn()
        │     └── _run_fc_loop() → LLM → Tool → Response
        └── _distill_memory() → Memory

User → Goal → AgentRuntime.submit_goal()
  → _run_goal() → Plan Gate → _resolve_dispatch() → Tool → Response
```

**关键变化**:
- `run_fc_loop()` 变为内部方法 `_run_fc_loop()`
- `run_chat_turn()` 真正统一管理执行流程
- Memory 蒸馏统一入口

---

## 17. Remaining Risks

### 高风险

1. **Planner 判断错误**
   - 可能导致简单聊天被错误分类为复杂任务
   - 或复杂任务被错误分类为简单聊天
   - **缓解**: 保守策略，默认使用 function calling

2. **Memory 蒸馏频率变化**
   - 统一入口可能改变蒸馏时机
   - **缓解**: 保持异步执行，不阻塞响应

### 中风险

3. **fallback 移除后错误处理**
   - 如果 `run_chat_turn()` 失败，没有 fallback
   - **缓解**: 添加必要的错误处理，但不回到旧路径

4. **状态机转换时机**
   - IDLE → PLANNING → EXECUTING → IDLE 可能引入延迟
   - **缓解**: 快速状态转换，不阻塞执行

### 低风险

5. **导入循环**
   - `agent_runtime` 导入 `tools`，`tools` 可能导入 `agent_runtime`
   - **缓解**: 使用局部导入（已在代码中存在）

6. **测试覆盖不足**
   - 现有测试可能不完整
   - **缓解**: 添加针对性测试

---

## 18. Final Verdict

### 当前状态: PARTIAL

**已完成**:
- ✅ Chat → AgentRuntime 连接（`run_chat_turn()` 已存在）
- ✅ 状态机集成（IDLE → EXECUTING → IDLE）
- ✅ Memory 蒸馏（`_distill_chat_memory()` 已添加）
- ✅ Execution Core 共享
- ✅ Policy Gate 共享

**未完成**:
- ❌ `run_fc_loop()` 仍是独立 public API
- ❌ `run_chat_turn()` 只是包装器，不是真正统一
- ❌ Recovery 机制缺失
- ❌ ContextEngine 仍是 stub
- ❌ Memory 蒸馏三套逻辑并存

### Architecture Verdict: PARTIAL UNIFICATION

Chat 已经通过 `run_chat_turn()` 连接到 AgentRuntime，但执行逻辑仍然是旧的 `run_fc_loop()`。这是一个**过渡状态**，需要进一步工作才能实现真正的统一。

---

## 19. Recommended Next Steps

### Option A: 完整统一（推荐）

执行上述所有变更，实现真正的统一架构。

**工作量**: 2-3 天
**风险**: 中
**收益**: 架构清晰，维护简单

### Option B: 最小改进

只内部化 `run_fc_loop()`，不改变其他逻辑。

**工作量**: 0.5 天
**风险**: 低
**收益**: 减少 public API，但不改变执行逻辑

### Option C: 保持现状

S88/S89 的工作已经完成（`run_chat_turn()` 已集成），可以标记为 COMPLETE。

**工作量**: 0 天
**风险**: 低
**收益**: 快速交付，但架构分裂持续

---

**我的建议**: Option A（完整统一）

理由:
1. S88 已经识别了架构分裂问题
2. `run_chat_turn()` 的现有实现是过渡方案
3. 完整统一能解决根本问题
4. 风险可控（向后兼容）

---

**报告路径**: `G:\xiao6\docs\XIAO6-S89-UNIFIED-AGENT-ARCHITECTURE.md`
**生产代码修改**: 0（仅设计文档）
**等待指令**: 是否执行 Option A/B/C？
