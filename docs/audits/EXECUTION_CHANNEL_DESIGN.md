# Execution Channel Separation — 架构设计 (Phase 6 Order 7)

**目标**：建立 Conversation Channel（用户消息 + AI 最终回复）与 Execution Channel（任务状态 / 工具状态 / 执行进度）的双通道，使执行过程与用户对话完全解耦。

**纪律边界（强制）**：
- 不修改业务能力（`tools.py` / `run_fc_loop` / `execute_tool_calls` 不动）。
- 不新增 Runtime / Memory / EventBus。
- 不改变 Agent 执行逻辑。
- 工具调用信息**不直接进入聊天正文**；执行日志进入 **Execution Event / Execution Monitor**。

---

## 1. 双通道模型

```
┌─────────────────────────────┐         ┌─────────────────────────────┐
│   Conversation Channel       │         │     Execution Channel        │
├─────────────────────────────┤         ├─────────────────────────────┤
│ 表面：聊天窗口 #messages      │         │ 表面：Execution Monitor 面板  │
│ 内容：                        │         │ 内容：                        │
│  - 用户消息 (user)           │         │  - 执行 episode 边界          │
│  - AI 最终回复 (xiao6)  │         │  - 工具步骤 (tool.start/end)  │
│ 事件：无（仅正文）            │         │  - 进度 / 状态 / 参数 / 结果  │
│ 承载：state.messages         │         │ 事件：tool_start/tool_end     │
│                             │         │      (+ 前端推导的边界事件)    │
└─────────────────────────────┘         └─────────────────────────────┘
            │                                          │
            │                                          │
            └────────── 共享单一 SSE 扇出 ──────────────┘
                  (eventbus TOPIC_SSE → app.js 统一监听)
```

**关键纪律**：两个 Channel 共享**同一个 SSE 监听器**（`app.js` 既有 `handleToolEvent` / `send()` 流式读取），**不新建任何 SSE 通道、不新建 EventBus**。区别仅在「渲染归宿」：
- `tool_*` 等执行事件 → ExecutionChannel（Monitor）。
- `choices[].delta.content` → 聊天窗口（仅最终正文）。

---

## 2. 事件流设计（语义层 → 传输层映射）

任务要求的语义事件流：

```
execution.started
      ↓
phase.changed
      ↓
tool.started
      ↓
tool.completed
      ↓
execution.completed
```

**映射规则（零后端改动）**：既有传输事件已覆盖工具级；边界事件由前端生命周期推导，不新增线缆事件名（严守「不新增 EventBus / 不新增后端逻辑」）。

| 语义事件 | 传输事件（既有） | 触发点（前端） |
|---|---|---|
| `execution.started` | —（前端推导） | `send()` 用户请求发出时 → `ExecutionChannel.startExecution(text)` |
| `tool.started` | `tool_start`（系统事件） | `handleToolEvent` 捕获 → `ExecutionChannel.onToolStart(ev)` |
| `tool.completed` | `tool_end`（系统事件） | `handleToolEvent` 捕获 → `ExecutionChannel.onToolEnd(ev)` |
| `phase.changed` | —（前端推导） | 每个 tool step 的开始/结束，更新 step.phase 标签 |
| `execution.completed` | —（前端推导） | `send()` 最终回复渲染完成 → `ExecutionChannel.completeExecution()` |

> 注：若未来需要后端权威边界事件，可在 `server.py` 的 `/api/chat` 起止处经 `publish_system("execution", {...})` 发出（需登记 `SYSTEM_EVENT_NAMES`）。本 Order 为最小解耦，**不强制后端改动**。

---

## 3. 前端模块设计：`execution-channel.js`

纯前端、只读事件、无后端直连（与 `runtime-visualization.js` 同纪律）。

### 3.1 数据模型

```js
ExecutionChannel = {
  executions: [            // 历史 episode（仅内存，非 Memory 层）
    {
      id, startedAt, completedAt, status,   // 'running' | 'completed'
      prompt,                                 // 用户原始请求（Conversation 侧引用，不渲染进聊天）
      steps: [
        { tool, label, args, status, result, startedAt, completedAt }
        // status: 'running' | 'completed'
      ]
    }
  ],
  current: null,           // 进行中的 episode
  subs: []                 // 渲染订阅者
}
```

### 3.2 API

- `startExecution(prompt)` — 开新 episode（若无进行中）。
- `onToolStart(ev)` — `ev.tool`/`ev.args` → 追加/更新 step，`status='running'`。
- `onToolEnd(ev)` — `ev.tool`/`ev.result` → 对应 step `status='completed'`。
- `completeExecution()` — 当前 episode `status='completed'`。
- `getExecutions()` / `getCurrent()` — 只读快照。
- `subscribe(cb)` — 变更通知（供 Monitor 重渲）。
- `mount()` / `boot()` — 挂载 `#execution-monitor` 面板（DOM 渲染，浏览器内）。

### 3.3 纪律约束（自检项）

- 不调用 `addMessage`、不写 `state.messages` → **不污染 Conversation Channel**。
- 无 `fetch` / `XMLHttpRequest` / `/api/` → **不直连后端**。
- 不创建新 EventBus / 新 Runtime / 新 Memory → 仅内存数组 + DOM。
- 事件来源仅为 app.js 转发的既有 `tool_start`/`tool_end` → **单一来源**。

---

## 4. 前端呈现：Execution Monitor

- 新增固定面板 `#execution-monitor`（默认 viewport 左下，与右下 `#runtime-viz` 对称），玻璃质感，沿用 premium 设计体系（青色高亮 / Orbitron / Rajdhani）。
- 渲染当前 episode 的 step 列表：图标 + 工具中文名（`TOOL_LABELS`）+ 状态（执行中旋转 / 完成对勾）+ 折叠的结果摘要。
- 多 episode 可滚动回溯（持久化于会话生命周期，非持久化存储）。
- 与聊天窗口零耦合：Monitor 永不向 `#messages` 写入。

---

## 5. 改动清单（最小面）

| 文件 | 改动 | 类型 |
|---|---|---|
| `execution-channel.js`（新建） | ExecutionChannel 模块 + Monitor 渲染 | 前端新增（非 Runtime） |
| `execution-channel.css`（新建） | Monitor 样式 | 前端样式 |
| `index.html` | 引入 `execution-channel.js`/`css`，版本 bump | 装配 |
| `app.js` | `handleToolEvent` 转发 `tool_start/end` 到 `ExecutionChannel`；`send()` 起止调用 `startExecution`/`completeExecution` | 接线（不改执行逻辑） |

**不涉及**：`server.py` / `tools.py` / `eventbus.py` / `run_fc_loop` / Agent 执行逻辑 / AppState 合约。

---

## 6. 验证判据（→ Phase 4）

以「分析当前项目」为任务：

- **Conversation Channel（聊天窗口）**：仅出现
  1. 用户消息「分析当前项目」
  2. AI 最终回复（汇总结论）
  → 不含任何 `file_read` / `run_shell` / 内部状态文本。
- **Execution Channel（Monitor）**：出现步骤
  1. 读取文件（`file_read`）
  2. 分析项目（对应 LLM/工具阶段）
  3. 生成报告（`media_generate` / 汇总）
  → 每步有 start/complete 状态，episode 有 started/completed 边界。

→ 详见 `EXECUTION_CHANNEL_TEST_REPORT.md`。
