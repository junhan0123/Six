# PHASE 5.1-HOTFIX-UI-04 FINAL REPORT
# 小6 Xiao6 v1.4.0 · AGENT ACTIVITY / TOOL VISIBILITY ARCHITECTURE AUDIT
# 性质：READ-ONLY · ZERO WRITE · STOP

---

## 1. Executive Summary

内部 TOOL 事件泄漏到用户可见聊天，有两个**独立、且都在前端**的根因：

1. **模式前缀泄漏（主因，用户可见 `【联网搜索】`）**：`xiao6-space/js/zz-workspace.js` 的 `activePrefix()` 把当前开启的能力开关用 `【…】` 包裹，并**拼进用户自己发出的消息**。`web`（联网搜索）开关**默认开启**（`toolModes = { think:false, web:true, code:'auto' }`），所以每条用户消息都带 `【联网搜索】` 前缀。
2. **工具事件渲染为聊天气泡**：`/api/chat` 的 SSE 流把 `tool_start`/`tool_end` 作为结构化事件发给前端，前端 `onTool()` 把**原始工具名**（如 `web_search`）渲染成可见的 `tool` 类型聊天气泡；遗留渲染器 `gui/chat.html` 也独立渲染同样的事件。

后端**从不**把 `【工具名】` 拼进助手回复文本（grep 无匹配；后端工具汇总用的是 `「」` 全角引号，非 `【】`）。`【联网搜索】`/`【代码执行】` 这些字面量**全仓后端源码中不存在**，完全由前端构造。

桌面粒子球（orb）：`dyna-orb-voice.js` 自己 `fetch('/api/chat')` 并把 `tool_start/tool_end` 当成 `orb.setState('executing')` 的触发源 —— 即**工具执行（Activity）当前耦合进了 Voice/Presence 层**，违反"Activity ≠ Voice"的分离原则。

本阶段零代码改动。根因已用真实源码逐行确认，下一步进入 UI-05（Activity UX 设计）。

---

## 2. Real Source Map

| 层 | 文件 | 角色 |
|---|---|---|
| 入口/HTTP | `server.py:751,755` | `POST /api/chat` → `_handle_chat` |
| 聊天处理/SSE | `server_handlers_chat.py:146,192-199,300,436` | 读消息、跑 fc-loop、发射 SSE |
| Agent Loop（聊天） | `tools.py:3363 run_fc_loop` | function-calling 闭环，读取 `tool_calls` |
| 工具分发/执行 | `tools.py:3291 execute_tool_calls` → `:3314 _cap_execute` → `capability_runtime.execute` → `capability_os.invoke_capability` → `ai_core.execution.run`（policy 门） | 工具真正执行 |
| 目标/任务编排（非聊天） | `agent_runtime.py:1210-1229` | 发布 `agent:state`/`hud_state` 到 EventBus（**不处理聊天工具调用**） |
| 主聊天前端 | `xiao6-space/js/zz-workspace.js:222,242-272` | 消费 `/api/chat` SSE，渲染聊天 + 工具气泡 |
| 遗留聊天前端 | `gui/chat.html:467,492-501` | 第二个独立渲染器（同样消费 `/api/chat`） |
| 桌面 orb | `desktop-avatar/dyna-orb-voice.js:138,219-230` + `dyna-orb.js` | orb 订阅聊天 SSE，工具事件→`executing` 态 |
| Electron 壳 | `electron/main.js:134-143`、`preload.js`、`electron/avatar-window.js` | 窗口控制（拖拽/穿透，与本审计无直接关系） |

注意：`index.html:26` 直接 `window.location.replace('/xiao6-space/index.html')`；`index.html:63-64` 引用了 `runtime-visualization.js`/`execution-channel.js` 等"解耦 Monitor"文件，但**这些文件在磁盘上不存在**（已核实缺失）——即"工具执行与对话解耦到独立 Monitor"的设计**从未落地**，工具执行反而被内联渲染进聊天气泡。

---

## 3. Real Agent Message Flow

```
USER 输入
  → index.html 重定向到 /xiao6-space/index.html
  → zz-workspace.js:201 sendChat(text)
  → [LEAK A] activePrefix() 拼到用户文本前 (L205-206)
  → fetch POST /api/chat  (L222)
  → server.py:755 _handle_chat
  → server_handlers_chat.py:146 读 messages / user_text
  → tools.py:3363 run_fc_loop
       → 调模型 → 读 tool_calls (L3388-3391)
       → execute_tool_calls (L3291) → 执行 → 回填 messages (L3404)
       → emit 最终文本 SSE (server_handlers_chat.py:436)
  → 前端 handle(): choices.delta.content 流式进助手气泡 (zz-workspace.js:252-254)
```

---

## 4. Real Tool Call Flow

- `tools.py:3363 run_fc_loop` 是聊天路径真正的 Agent Loop。
- `tools.py:3388-3391` 读取 `msg.tool_calls`，逐个 `fn.name` 收集。
- `tools.py:3291 execute_tool_calls(tool_calls)` → `run_one(p)` (`:3308`) → `_cap_execute(p.name, p.args)` (`:3314`)。
- 事件在 `run_fc_loop` 内发射：`tools.py:3399-3403` —— `kind=='start'` → `emit({"xiao6_event":"tool_start",...})`；`else` → `emit({"xiao6_event":"tool_end",...})`。
- 另有兜底意图路径 `server_handlers_chat.py:308-322` 也 `_cap_execute` + `emit tool_start/tool_end`。

---

## 5. Real Tool Result Flow

- 后端回填：`tools.py:3328/3333` 构造 `{"role":"tool","tool_call_id":...,"content":res}`；`run_fc_loop:3404` `messages.extend(tool_msgs)`。这仅进入后端 `messages` 上下文，**不直接对用户可见**。
- 用户可见的最终文本：`server_handlers_chat.py:436` `emit({"choices":[{"delta":{"content":...}}]})`。
- 后端工具汇总文本用的是 `「{name}」返回结果：{result}`（`server_handlers_chat.py:332`，注意 `「」` 非 `【】`，且仅用于回喂模型，不作聊天前缀）。

---

## 6. Real SSE / WebSocket / EventBus Flow

- **主通道 = SSE**：`/api/chat` 返回 `text/event-stream`（`server_handlers_chat.py:192-197`）。
- `emit(obj)` 直接 `wfile.write("data: "+json+"\n\n")`（`server_handlers_chat.py:199`）。
- 工具事件 = `{"xiao6_event":"tool_start"/"tool_end","tool":name,...}`（`tools.py:3401/3403`）。
- **EventBus 不承载工具事件**：全仓 grep `bus.publish(TOPIC_SSE …` 仅命中 `eventbus.py` 通用发布与 `server_handlers_chat.py:735` 的订阅；无工具事件 `bus.publish`。所以 `tool_start/tool_end` **只走 `/api/chat` SSE**，不走 EventBus。
- 第二条通道 `/api/stream`（`server.py:379` → `server_handlers_chat.py:727`）订阅 `TOPIC_SSE`/`TOPIC_HUD_STATE`，但工具事件不在其扇出内。

---

## 7. Real Frontend Rendering Flow

**主聊天 UI** `zz-workspace.js`：
- `:222` `fetch('/api/chat')`；`:242 handle()` 路由：
  - `:244-245` `tool_start`→`onTool('start',…)`；`tool_end`→`onTool('end',…)`
  - `:252-254` `choices.delta.content` → 流式助手气泡
- `:261-272 onTool()`：**把工具渲染成聊天气泡** `addNode('tool')`，气泡内含原始工具名 `esc(tool)`（`:264,268`）。

**遗留渲染器** `gui/chat.html`：
- `:467` 同样 `fetch('/api/chat')`；`:492-501` 把 `tool_start/tool_end` 渲染成工具卡片 `makeToolCard(obj.tool)`。

**桌面 orb** `dyna-orb-voice.js`：
- `:138` 自己 `fetch('/api/chat')`；`:219-230 handleExecEvent` → `orb.setState('executing')` + 桌面执行对话框显示工具名。

结论：**前端把工具名/结果渲染成聊天气泡/卡片/桌面对话框**，且存在三处独立渲染。

---

## 8. Root Cause of「【联网搜索】」「代码执行】

两个独立泄漏，均在前端：

**(A) 模式前缀泄漏（用户消息上出现 `【联网搜索】`）**
`zz-workspace.js:193-199`：
```js
function activePrefix() {
  var order = ['think', 'web', 'code'];
  var on = order.filter(function (k) { return toolModes[k]; });
  if (!on.length) return '';
  var names = { think: '深度思考', web: '联网搜索', code: '代码执行' };
  return '【' + on.map(function (k) { return names[k]; }).join('】【') + '】';
}
```
`sendChat` L205-206 把它**拼到用户自己消息前**：
```js
var prefix = activePrefix();
if (prefix && text.indexOf('【') !== 0) text = prefix + text;
```
`toolModes` 在 `zz-workspace.js:30` 为 `{ think:false, web:true, code:'auto' }` → `web` 默认开 → **每条用户消息默认带 `【联网搜索】`**。

**(B) 工具事件成聊天气泡（出现 `web_search` 等原始工具名）**
`zz-workspace.js:244-245,261-272` `onTool()` 渲染 `addNode('tool')` 气泡，内容含 `esc(tool)` 原始名。

后端**不**产生 `【工具名】`：`server_handlers_chat.py` / `tools.py` 中 grep `【工具` 无匹配；后端工具汇总仅用 `「」`（`:332`）。`【联网搜索】`/`【代码执行】` **仅由前端 `activePrefix()` 产生**。

---

## 9. Current Visibility Model（实测）

| 类别 | 当前实际可见性 | 真实来源 |
|---|---|---|
| USER_MESSAGE | VISIBLE | 正常 |
| ASSISTANT_FINAL | VISIBLE | SSE `choices.delta` |
| 模式指示（联网搜索…） | **VISIBLE（拼进用户气泡）** ❌ | `activePrefix()` 误用为消息前缀 |
| TOOL_CALL | **VISIBLE（聊天气泡）** ❌ | `onTool()` |
| TOOL_RESULT | **VISIBLE（聊天气泡/卡片）** ❌ | `onTool()` / `gui/chat.html` |
| ACTIVITY | **混入聊天 + 桌面对话框** ❌ | `onTool` + `dyna-orb-voice.js` |
| INTERNAL_REASONING | 不可见 | 无 |
| DEBUG / AUDIT | 不可见 | 无 |

---

## 10. Recommended Visibility Model

| 类别 | 建议可见性 | 落点 |
|---|---|---|
| USER_MESSAGE | VISIBLE | 聊天 |
| ASSISTANT_FINAL | VISIBLE | 聊天 |
| 模式指示（联网搜索…） | **MINIMAL / 非消息**（状态条或输入框提示） | 移出气泡 |
| ACTIVITY（小6 处理中） | VISIBLE / MINIMAL（聚合指示器） | Activity 层 |
| TOOL_CALL | BACKGROUND | Agent Work 层 |
| TOOL_RESULT | BACKGROUND | Agent Work 层 |
| INTERNAL_REASONING | HIDDEN | — |
| DEBUG / AUDIT | DEV/AUDIT ONLY | — |

核心原则：Tool Name ≠ User Message；Tool Result ≠ User Message；Activity ≠ Tool Log；Final Response ≠ Tool Result。

---

## 11. User-Facing Layer

- **Conversation**：用户消息 + 小6 最终回答（唯一应出现在聊天的两类）。
- **Activity**：`小6 正在处理…` 一类**最小化聚合指示器**（不逐条暴露 read/search/list），可放在状态条或聊天顶部 chip。
- **Voice**：语音对话态（listening/thinking/speaking）。
- **Desktop Presence**：桌面 orb 的"在场"表现，应与 Activity 解耦（见 §14）。

---

## 12. Agent Work Layer

- **Planning / Tool Call / Tool Execution / Tool Result / Agent Loop**：全部后台。用户聊天区**完全看不到**这些内部步骤也属正常。
- 工具名/原始结果只允许进入 Activity 层的聚合指示，不进入 Conversation。

---

## 13. Internal Layer

- **Runtime / Policy / Memory / Executor / Scheduler**：完全内部，仅 DEV/AUDIT 可见。
- `agent_runtime.py:1210-1229` 已有的 `agent:state` / `hud_state` EventBus 发布，是 Activity 信号的**正确通道**（当前 orb 未使用，反而去解析聊天 SSE）。

---

## 14. Desktop Orb Interaction Audit

- `dyna-orb.js`：纯渲染器，**不订阅任何事件总线**（`grep subscribe/EventSource/bus./addEventListener` 全无），状态完全由 `dyna-orb-voice.js` 的 `orb.setState()` 驱动。
- `dyna-orb-voice.js:138` 自己 `fetch('/api/chat')`，`:219-230 handleExecEvent`：
  ```js
  if (type === 'tool_start') { currentTool = ev.tool || '工具';
      execStepEl.textContent = '→ ' + currentTool + ' 执行中…'; orb.setState('executing'); }
  else if (type === 'tool_end') { execStepEl.textContent = '✓ ' + currentTool + ' 完成'; orb.setState('executing'); }
  ```
  → **球会因工具执行切换到 `executing` 态，并在桌面对话框显示工具名**。

**问题**：工具执行（Activity）被当成了 Voice 状态（`executing`）驱动源，且把工具名暴露进桌面对话框。这违反 UI-04 §8 的"Activity UI 与 Desktop Presence 是两个不同表现层"。
**建议（UI-07）**：orb 的 `executing`/presence 应订阅 `agent_runtime.py` 已存在的 `agent:state`/`hud_state` 总线（Activity 信号），**而非重新解析 `/api/chat` SSE**；桌面对话框不显示原始工具名，改为聚合的"处理中"提示。

---

## 15. Files That Would Need Modification Later

| 文件 | 改什么 | 阶段 |
|---|---|---|
| `xiao6-space/js/zz-workspace.js` | `activePrefix()`(193-199) 不再拼进用户消息；`onTool()`(261-272) 改为 Activity 指示而非聊天气泡；`handle()`(242-245) 路由调整 | UI-06 |
| `gui/chat.html` | 遗留重复渲染器：确认生产是否可达，可达则对齐/废弃（UI-06 一并处理，避免双渲染） | UI-06 |
| `desktop-avatar/dyna-orb-voice.js` | `handleExecEvent`(219-230) + `chatStream`(138)：orb 改订阅 `agent:state`/`hud_state` 总线，不再解析聊天 SSE；桌面对话框去工具名 | UI-07 |
| `index.html` | 移除对缺失的 `runtime-visualization.js`/`execution-channel.js` 等引用（或真正实现解耦 Monitor） | UI-06/07 |
| `server_handlers_chat.py`（可选） | 若需独立的 Activity 事件类型，可发射 `xiao6_event:"activity"`（不强制） | UI-06 |

---

## 16. Minimal Future Change Strategy

1. **单一聊天渲染面**：只保留 `zz-workspace.js`；`gui/chat.html` 若确认孤儿则删除，避免双渲染。
2. **模式指示移出气泡**：`toolModes` 开关保留，但 `【联网搜索】` 之类只作为**输入框提示/状态条**展示，绝不 prepend 到用户文本。
3. **工具事件→Activity 层**：`onTool` 不再 `addNode('tool')` 聊天气泡，改为顶部一个最小化 `Activity` chip（如"小6 正在处理…"），不暴露原始工具名。
4. **orb 解耦**：orb 订阅 `agent_runtime` 的 `agent:state`/`hud_state` 总线表达 presence/activity，不再 `fetch('/api/chat')` 解析工具事件。
5. **后端零改**：工具名/事件是后端正确发出的结构化数据，问题全在前端呈现；后端 `tool_start/tool_end` 可保持不变。

---

## 17. Red-Line Audit

- **本阶段 ZERO WRITE**：未修改任何生产文件。
- 仅新增（均位于 `_ui_archive/` 非生产区）：`UI04_movable_verify.cjs`（拖拽验证脚本）、本报告。
- 球体"可移动/不穿透"请求经真实 Chromium 验证**已正确实现、无需改动**（`dyna-orb.html` hash 仍为 `40b8404a73ac535b`，与 UI-03 基线一致）。
- 禁止文件（`server.py`、任意 `.py`、`agent_runtime.py`、`tools.py`、Electron 壳、`dyna-orb.js`、`dyna-orb-voice.js`、`zz-workspace.js`、`gui/chat.html` 等）**全程零写入**。

---

## 18. Proposed PHASE 5.1-HOTFIX-UI-05~08

- **UI-05 · Agent Activity UX Design**：定义 Xiao6 Activity Model（8 类事件分类）；设计 Activity 表现面（最小 chip / 状态条 / orb presence）；确定模式指示的放置位置。**纯设计，零代码。**
- **UI-06 · Agent Activity Minimal Implementation**：`zz-workspace.js` 落地 §16 的 2–3（去前缀、工具事件转 Activity 指示）；废弃/对齐 `gui/chat.html`；清理 `index.html` 缺失引用。最小 diff。
- **UI-07 · Desktop Presence / Fullscreen Game Policy**：正式化 orb 状态机——voice 态（listening/thinking/speaking）与 presence/activity 态（executing）分离；orb 改订阅 `agent:state`/`hud_state` 总线；定义全屏/游戏策略（如有）。
- **UI-08 · Full Interaction Verification**：真实 Chromium + Electron 验证——聊天中不再出现 `【联网搜索】`/原始工具名；模式指示移到非消息面；orb `executing` 与聊天 SSE 解耦。

若 UI-06 核实 `gui/chat.html` 确为孤儿（生产不可达），则该步可"直接删除"替代"对齐"，工作量更小——以 UI-06 实测可达性为准。

---

## 19. Known Limitations

- 本审计为 READ-ONLY；orb 耦合 `executing` 经源码确认，未跑真实 Electron 运行验证。
- 验证 harness 出现的 1 个 404 为 favicon/可选资源请求，非 JS 异常，与拖拽/审计无关。
- `gui/chat.html` 是否在生产实际加载未能静态确认（`index.html` 重定向到 `xiao6-space/`）；UI-06 需实测其可达性再决定删除或对齐。
- 后端 `tool` 字段为原始名（`web_search` 等）；`【】` 标签纯前端构造，故修复前端即可，后端不动。

---

## 20. STOP / GO Decision

- **STOP（本阶段）**：仅审计，未实施任何修改，未跨任何红线。
- **GO（下一步 UI-05）**：根因已用真实源码逐行确认，且问题清晰可分离（前端呈现层），建议进入 UI-05 设计。
- 不自行进入实现；待老板授权 UI-05 后按 Design → Minimal Implement → Verify → Document 推进。

---

*审计完成 · VERIFIED-BY-REAL-SOURCE · ZERO WRITE · STOP*
