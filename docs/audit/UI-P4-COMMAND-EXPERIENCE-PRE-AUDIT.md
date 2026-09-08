# UI-P4 Command Experience Pre-Audit 报告

**Date**: 2026-09-06  
**Scope**: Command Bar → Chat Streaming → Agent Execution Feedback 全链路  
**Constraint**: 只读审计，不修改任何代码  

---

## 一、全链路架构分析

### 用户输入 → Agent执行 → UI反馈 数据流

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           用户输入层                                        │
│                                                                             │
│   [Command Bar]                    [Chat Composer]                         │
│   ┌──────────────┐                ┌──────────────┐                        │
│   │ commandInput │                │ #input       │                        │
│   │ commandSend  │                │ btnVoice     │                        │
│   └──────┬───────┘                └──────┬───────┘                        │
│          │                               │                                │
│          └──────────┬────────────────────┘                                │
│                     ▼                                                     │
│            switchView('chat') → 填充 #input → submit()                   │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           请求层                                            │
│                                                                             │
│   POST /api/chat                                                            │
│   { messages: [{role, content}, ...] }                                      │
│                                                                             │
│   响应: SSE (text/event-stream)                                             │
│   data: { choices: [{delta: {content}}], xiao6_event, approval, ... }      │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           服务端处理                                        │
│                                                                             │
│   server.py:_handle_chat()                                                  │
│     ↓                                                                       │
│   Agnes LLM 调用 → Tool Execution → 结果回填                               │
│     ↓                                                                       │
│   SSE 流式返回                                                              │
│     - tool_start: {xiao6_event: "tool_start", tool: "name"}                │
│     - tool_end: {xiao6_event: "tool_end", tool: "name"}                    │
│     - approval: {ticket, approval: {...}}                                   │
│     - choices: {delta: {content: "..."}}                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           UI 渲染层                                         │
│                                                                             │
│   streamChat() → onEvent callback                                           │
│     ↓                                                                       │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │ 1. tool_start → addToolLine("正在调用...", "running")       │       │
│   │    → setAgentState("working")                                  │       │
│   │    → addAgentStep(tool, "running")                             │       │
│   ├─────────────────────────────────────────────────────────────────┤       │
│   │ 2. tool_end → addToolLine("完成", "done")                  │       │
│   │    → finishAgentStep(tool)                                     │       │
│   ├─────────────────────────────────────────────────────────────────┤       │
│   │ 3. approval → renderApprovalCard(m, ticket)                    │       │
│   │    → setAgentState("approval")                                 │       │
│   ├─────────────────────────────────────────────────────────────────┤       │
│   │ 4. choices.delta.content → 追加到 bubble.textContent           │       │
│   │    → chatScroll.scrollTop =.scrollHeight                     │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
│   finally: setAgentState("idle")                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DOM 节点                                          │
│                                                                             │
│   输入:                                                                     │
│   - #commandInput (首页 Command Bar)                                        │
│   - #input (Chat Composer)                                                  │
│                                                                             │
│   输出:                                                                     │
│   - #messages (消息列表容器)                                                │
│   - #chatScroll (滚动容器)                                                  │
│   - .bubble (消息气泡)                                                      │
│   - .tool-evt (工具调用事件行)                                              │
│   - .approval-card (审批卡片)                                               │
│                                                                             │
│   状态:                                                                     │
│   - #agentActivity (Agent Activity 状态条)                                  │
│   - #aaTitle (状态文本: "小6正在思考...")                                   │
│   - #aaSteps (工具调用步骤列表)                                             │
│   - .aa-pulse (脉冲圆点)                                                    │
│   - .aa-step (单步状态: running/done)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、关键模块审计

### 2.1 Command Bar (`ui/js/command_bar.js`)

**职责**：
- 解析用户输入
- 调用 `/api/interaction/parse` 获取意图
- 更新 Command Status 显示
- 记录交互活动

**当前实现**：
```javascript
STATE_IDLE = "idle"           // 输入指令，让小6帮你...
STATE_THINKING = "thinking"   // 小6正在理解...
STATE_UNDERSTANDING = "understanding"  // 识别意图...
STATE_READY = "ready"         // 准备执行
```

**问题**：
| # | 问题 | 等级 | 说明 |
|---|------|------|------|
| P1 | State 与 Agent Activity 不联动 | 高 | Command Bar 有独立状态机，但 #agentActivity 由 app.js 控制，两者不同步 |
| P2 | parseInteraction 成功后未触发实际发送 | 中 | parse 后返回 intentType，但未自动调用 submit() |
| P3 | trackActivity 仅 POST 无实际存储 | 低 | 调用 /api/interaction/activity 仅刷新，无新记录写入 |

---

### 2.2 Chat Streaming (`ui/js/app.js` L2840-2887)

**职责**：
- SSE 流式接收 LLM 响应
- 渲染 tool_start/tool_end 事件
- 更新 Agent Activity 状态
- 处理 approval 卡片

**当前实现**：
```javascript
async function streamChat(messages, onEvent) {
  res = await fetch("/api/chat", { method: "POST", ... });
  reader = res.body.getReader();
  // 逐块解析 SSE
  while (true) {
    const { done, value } = await reader.read();
    // 解析 data: {...} 行
    // 调用 onEvent(payload)
  }
}
```

**事件处理**：
| 事件类型 | 处理函数 | 副作用 |
|----------|----------|--------|
| `xiao6_event: tool_start` | `addToolLine("正在调用...", "running")` | `setAgentState("working")`, `addAgentStep(tool, "running")` |
| `xiao6_event: tool_end` | `addToolLine("完成", "done")` | `finishAgentStep(tool)` |
| `approval` (ticket) | `renderApprovalCard(m, ticket)` | `setAgentState("approval")` |
| `choices[0].delta.content` | `bubble.textContent += content` | 滚动到底部 |

**问题**：
| # | 问题 | 等级 | 说明 |
|---|------|------|------|
| P4 | 无错误边界保护 | 中 | SSE 解析失败时 silently fail |
| P5 | tool_start 无去重 | 低 | 重复事件可能添加重复步骤 |
| P6 | 长文本无截断 | 低 | bubble.textContent 直接赋值，超长文本可能溢出 |

---

### 2.3 Agent Activity (`ui/js/app.js` L2728-2776)

**职责**：
- 显示 Agent 当前状态（thinking/working/approval/idle）
- 记录工具调用步骤
- 提供视觉反馈

**状态机**：
```
idle → thinking → working → done
              ↓
           approval → (用户确认) → working → done
```

**DOM 结构**：
```html
<div class="agent-activity idle" id="agentActivity">
  <div class="aa-side"><span class="aa-pulse"></span></div>
  <div class="aa-main">
    <div class="aa-title" id="aaTitle">小6已就绪</div>
    <div class="aa-steps" id="aaSteps"></div>
  </div>
</div>
```

**问题**：
| # | 问题 | 等级 | 说明 |
|---|------|------|------|
| P7 | aaSteps 无清除时机 | 中 | 新请求开始前不清除旧步骤，可能导致历史残留 |
| P8 | 状态切换无过渡动画 | 低 | setAgentState() 直接换 class，无 fade/slide 效果 |

---

### 2.4 CSS 样式审计

**Command Bar 样式** (L860-895):
```css
.command-bar { border-radius: 18px; box-shadow: var(--sh-md); }
.command-send { background: var(--brand); border-radius: 50%; }
.command-send:hover { background: #ff7875; } /* ⚠️ 硬编码 */
```

**Agent Activity 样式** (L901-931):
```css
.agent-activity { background: var(--bg-soft); border: 1px solid var(--line-soft); }
.aa-pulse { width: 9px; height: 9px; border-radius: 50%; }
.agent-activity.thinking .aa-pulse { animation: aaPulse 1.2s infinite; }
```

**问题**：
| # | 问题 | 等级 | 说明 |
|---|------|------|------|
| P9 | command-send hover 硬编码颜色 | 低 | `#ff7875` 应使用 Design Token |

---

## 三、UI-P4 升级方案

### 方案概述

将 Command Bar、Chat Streaming、Agent Activity 整合为统一的用户体验层，实现：

1. **状态联动** — Command Bar 状态 ↔ Agent Activity 状态实时同步
2. **视觉增强** — 输入焦点、发送状态、错误提示的完整视觉反馈
3. **流畅过渡** — 状态切换动画、消息出现动画
4. **智能预判** — 输入时显示意图预测、加载时显示进度

### Task 1: Command Bar 视觉升级

**目标**：
- 输入时显示"思考中"骨架屏
- 发送后按钮状态变化（loading spin）
- 错误时显示红色边框 + 提示

**实现**：
```css
.command-bar.loading { border-color: var(--brand); animation: barPulse 1s infinite; }
.command-send.loading { transform: rotate(360deg); transition: transform .6s; }
.command-bar.error { border-color: var(--danger); }
.command-hint-predict { font-size: 11px; color: var(--ink-3); margin-top: 4px; }
```

**JS 变更**：
```javascript
// 输入时显示预测
input.addEventListener('input', debounce(() => {
  predictIntent(input.value).then(intent => showPredict(intent));
}, 300));

// 发送时按钮状态
sendBtn.classList.add('loading');
// ... 完成后移除
sendBtn.classList.remove('loading');
```

---

### Task 2: Agent Activity 状态同步

**目标**：
- Command Bar 状态实时反映到 Agent Activity
- 清除历史步骤，避免残留
- 添加状态切换过渡

**实现**：
```javascript
// 同步函数
function syncAgentStateFromCommand(state, intent) {
  setAgentState(state); // app.js 已有函数
  if (intent) updateIntentDisplay(intent);
}

// 发送前清除旧步骤
function clearAgentStepsBeforeNewRequest() {
  clearAgentSteps();
  setAgentState('thinking', '小6正在理解...');
}
```

---

### Task 3: Chat 消息渲染增强

**目标**：
- 消息出现动画（slide-in + fade）
- 工具调用步骤可视化（时间轴风格）
- 错误状态友好提示

**实现**：
```css
@keyframes msgSlideIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.bubble { animation: msgSlideIn .3s ease-out; }

.tool-evt.running { background: var(--brand-tint); }
.tool-evt.done { opacity: 0.7; }
```

---

### Task 4: 硬编码颜色清理

**待替换**：
| 位置 | 当前值 | 建议值 |
|------|--------|--------|
| `command-send:hover` | `#ff7875` | `var(--brand-grad)` |
| `bubble 错误文本` | `#8a8a8a` | `var(--ink-3)` |
| `approval-card 背景` | 硬编码 | `var(--brand-tint)` |

---

## 四、约束检查

| 约束 | 状态 |
|------|------|
| 不修改 server.py | ✅ 仅前端 |
| 不修改 API contract | ✅ 接口不变 |
| 不修改 DB | ✅ 无变更 |
| 不修改 Agent Runtime | ✅ 仅 UI 层 |
| VERSION 保持 1.0.0 | ✅ |
| 无 ZZ/ZhuangZhou/庄周资产 | ✅ |

---

## 五、验收标准

| 检查项 | 标准 |
|--------|------|
| 输入响应 | 300ms 内显示预测 |
| 发送反馈 | 按钮 loading 状态，输入框禁用 |
| 状态同步 | Command Bar ↔ Agent Activity 一致 |
| 消息动画 | 出现时 slide-in + fade |
| 错误处理 | 友好提示，可重试 |
| 性能 | 无内存泄漏，步骤列表限制 6 条 |

---

## 六、风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| 动画影响性能 | 低 | 使用 CSS transform + opacity（GPU加速） |
| SSE 解析失败 | 中 | try-catch 包裹，显示错误提示 |
| 状态不同步 | 低 | 单一状态源，Command Bar 和 Agent Activity 共享状态 |

---

**审计结论**：Command Experience 链路功能完整，但存在状态不同步、视觉反馈不足、硬编码颜色等问题。建议按 Task 1-4 逐步升级，预计改动量：CSS ~50 行，JS ~80 行。

---

*本报告仅用于审计，未修改任何代码。*
