# Execution Channel Separation — 现状审计 (Phase 6 Order 7)

**任务等级**：CRITICAL ARCHITECTURE EXPERIENCE TASK
**日期**：2026-08-04
**执行者**：Senior Developer（高级开发工程师）
**纪律边界**：禁止修改业务能力 / 新增 Runtime / 新增 Memory / 新增 EventBus / 改变 Agent 执行逻辑。目标仅为「执行过程与用户对话解耦」。

---

## 1. 审计范围与方法

逐层追踪一条「复杂任务」从用户输入到前端呈现的完整链路：

| 层 | 文件 | 角色 |
|---|---|---|
| 入口 | `xiao6-ui/server.py` `/api/chat` | 接收用户消息，驱动 function-calling 闭环 |
| 执行 | `xiao6-ui/tools.py` `run_fc_loop()` / `execute_tool_calls()` | LLM 决策 → 本地执行工具 → 回填 → 多轮 |
| 事件 | `xiao6-ui/eventbus.py` `publish_sse` / `publish_system` | SSE 统一扇出（`TOPIC_SSE`） |
| 前端消费 | `xiao6-ui/app.js` `send()` + `handleToolEvent()` | 流式渲染聊天 + 处理工具事件 |
| 前端渲染 | `addMessage()`（聊天）/ `showToolOverlay()`（浮层） | 两条不同的呈现路径 |

> 说明：任务描述中的 `conversation_loop.py` 在本仓库中实际为 `server.py` 的 `/api/chat` + `tools.run_fc_loop()` 闭环（仓库无独立 `conversation_loop.py`）。审计以真实代码为准。

---

## 2. 三个核心问题的结论

### Q1. tool_call 如何进入前端？

工具调用**不直接进入聊天正文**，而是走独立事件通道：

- 后端 `tools.py:3364-3368` 在工具执行前后经 `emit()` 推送两条 SSE 事件：
  - `{"xiao6_event": "tool_start", "tool": <name>, "args": <payload>}`
  - `{"xiao6_event": "tool_end", "tool": <name>, "result": <payload>}`
- 前端 `app.js:426-429`（`handleToolEvent`）捕获后调用 `showToolOverlay()`，**仅渲染一个 2.6 秒后自动消失的浮层**，不调用 `addMessage()`。
- 同一事件也被 `main-cognitive.js:157-159` 消费（另一渲染入口，同样不走聊天历史）。

✅ **结论**：聊天正文（`#messages`）当前**只包含** `user` 消息与最终 `xiao6` 回复（`addMessage` 仅被 `send()` 调用）。工具调用未进聊天正文。

### Q2. execution 事件在哪里产生？

执行事件产生于**两个位置**，但都属「系统事件」通道（`SYSTEM_EVENT_NAMES`），与领域事件（`DOMAIN_EVENT_NAMES` / AppState）分离：

1. **工具级**：`tool_start` / `tool_end`（见 Q1）。
2. **Agent 编排态**：`agent_runtime.py:660-665` 经 `publish_system("agent_state", fields)` 推送 Agent 编排快照。
3. **领域生命周期**（可选/平行）：`GOAL_*` / `AGENT_*` / `TASK_*` 经 `publish_domain()` 进 AppState（被 Phase 6 Order 5 的 `runtime-visualization.js` 投影为 Execution Timeline）。

⚠️ **缺口**：
- 没有「执行开始 / 执行完成」的**边界事件**（`execution.started` / `execution.completed`），无法界定一次用户请求对应的完整执行 episode。
- `tool_start` / `tool_end` 仅驱动**瞬时浮层**，无**持久化执行监视面**（Execution Monitor）。执行过程在 2.6 秒后即不可见、不可回溯。

### Q3. chat 消息与 execution 消息是否混合？

- **内容层面**：未混合（Q1 结论）。
- **体验层面**：混而未分——执行信息没有专属、持久、可回溯的「Execution Plane」归宿：
  - 用户看到的执行反馈仅是转瞬即逝的浮层；
  - Phase 6 Order 5 的 Execution Timeline 是**纯状态投影**，未订阅真实的 `tool_start`/`tool_end` 流，与实时执行脱节；
  - 聊天窗口（`#messages`）与执行浮层在视觉上同处中央主区，用户感知上「执行过程和对话挤在一起」。

✅ **结论**：Conversation Plane 与 Execution Plane **未完全分离**——根因不是「工具文本进了聊天」，而是**执行过程缺乏独立、持久、可回溯的呈现载体**（Execution Channel 缺位）。

---

## 3. 现状链路图

```
用户输入
  │  POST /api/chat
  ▼
server.py /api/chat
  │  run_fc_loop(messages, emit, ...)
  ▼
tools.py: LLM 决策 → execute_tool_calls()
  │  emit tool_start / tool_end   ──┐ (SSE 系统事件)
  ▼                                │
最终 content（自然语言）            │
  │  emit choices[].delta.content  │
  ▼                                ▼
app.js send() 流式读取     app.js handleToolEvent()
  │                                │
  ▼                                ▼
addMessage('user')          showToolOverlay()  → 2.6s 瞬时浮层
addMessage('xiao6')          ❌ 无持久 Execution Monitor
  │
  ▼
聊天窗口 #messages（仅对话）
```

---

## 4. 纪律符合性自检（审计阶段）

| 红线 | 现状 | 结论 |
|---|---|---|
| 禁止修改业务能力 | 本次仅读代码 | ✅ 未触碰 |
| 禁止新增 Runtime | 无新运行时 | ✅ |
| 禁止新增 Memory | 无新记忆层 | ✅ |
| 禁止新增 EventBus | 复用既有 `TOPIC_SSE` + `publish_system` | ✅ |
| 禁止改变 Agent 执行逻辑 | `run_fc_loop` / `execute_tool_calls` 未改 | ✅ |

---

## 5. 审计结论与改造切入点

**Execution Channel 应从「瞬时浮层」升级为「持久监视面」**，且不改动任何后端执行逻辑：

1. 复用既有 `tool_start` / `tool_end` 系统事件（不新增后端逻辑）。
2. 新增前端 `ExecutionChannel` 模块：把每条 `tool_start`/`tool_end` 归入一个「执行 episode」，渲染到**独立的 Execution Monitor 面板**。
3. 用前端生命周期（用户请求开始 → 首次工具 → 末次工具 → 最终回复完成）推导 `execution.started` / `tool.started` / `tool.completed` / `execution.completed` 语义，无需后端改事件。
4. 聊天窗口维持「只显示用户级内容」现状（已满足），作为 Conversation Channel。

→ 详见 `EXECUTION_CHANNEL_DESIGN.md`。
