# Xiao6 v1.0.0 — Frontend ↔ Backend Capability Map

> **审计类型**：只读审计（Read-only Audit）
> **审计时间**：2026-09-02 00:05 – 00:20 (UTC+8)
> **基线**：`G:\xiao6` @ v1.0.0 · 唯一 UI `G:\xiao6\ui` · 唯一入口 `127.0.0.1:8000`
> **Production Changes**：**0**
> **数据来源**：(a) 前端源码通读 `ui/index.html` / `ui/css/style.css` / `ui/js/app.js`；(b) 运行时真实 API 探测（仅 GET 只读端点，未触发任何写操作）
> **方法说明**：本报告不引用任何历史文档结论，全部字段以当前代码 + 当前运行时响应为准。

---

## 0. 审计前置说明：对 2026-09-01 UI 建议的修正

2026-09-01 的 UI 升级建议基于**截图推断**，本次代码审计后发现 3 处判断错误，在此显式修正：

| 原判断（截图推断） | 实际情况（代码事实） | 结论 |
|---|---|---|
| "缺阴影 / 圆角不统一 / 无状态色" | `style.css:4-27` 已存在完整 Design Token 体系（`--brand` / `--ink-1..4` / `--r-sm|md|lg|xl` / `--sh-sm|md|pop` / `--ok` / `--warn`） | **原判断错误**，设计系统已完备 |
| "能力区空白，需新建能力广场" | `app.js:315-344` 已实现 `loadAbilities()`，数据源为真实 `/api/capability_os/catalog`；截图空白是**数据渲染时机**问题 | **原判断错误**，功能已存在 |
| "简报 JSON 直出 = 后端只给原始 JSON" | 后端 `/api/weather` 已返回**完美卡片结构** `card` + `forecast`；是**前端** `app.js:292` 用 `JSON.stringify()` 丢弃了结构 | **归因错误**，问题在前端不在后端 |

**核心结论**：小6 UI 的短板不在"设计系统缺失"，而在**前端未消费后端已提供的结构化数据**。改造重心应为"数据接线"而非"视觉重做"。

---

## 1. Current UI Architecture

### 1.1 文件构成

| 文件 | 大小 | 职责 |
|---|---|---|
| `ui/index.html` | 11.5 KB | 单页骨架，7 个 view 容器，内联 SVG 图标 |
| `ui/css/style.css` | 22.0 KB | Design Tokens + 全部样式 + 8 组动画 + 3 个响应式断点 |
| `ui/js/app.js` | 58.0 KB | 单一 IIFE，全部逻辑（无模块拆分） |

**总计 91.5 KB，零构建、零依赖、零框架。**

### 1.2 架构特征

| 维度 | 现状 | 评价 |
|---|---|---|
| 框架 | 无。原生 ES2017 + IIFE | 轻量，适合当前规模 |
| 构建工具 | 无。`index.html` 直接 `<script src>` | 改完即生效，无编译风险 |
| 组件化 | 无。字符串模板 + `innerHTML` 拼接 | 技术债，但当前 7 个 view 可控 |
| 路由 | 无路由库。`class="view active"` 切换（`app.js:145-160`） | 够用，但无 URL 深链 |
| 状态管理 | 单一全局 `S` 对象（`app.js:52-75`），21 个字段 | 简单可追溯 |
| API 层 | `api()` / `getJSON()` / `postJSON()`（`app.js:34-49`） | 统一，含错误详情提取 |
| 错误态 | `LOADING` / `empty()` / `errorBox()` 三态齐全（`app.js:25-31`） | **优秀**，无假成功 |
| 转义 | `esc()` 全量 XSS 转义（`app.js:13-14`） | 安全 |

### 1.3 数据流（7 个 view × 数据源）

| View | 挂载点 | 触发时机 | 数据源 |
|---|---|---|---|
| chat（首页） | `#hero` + `#messages` | `boot()` 立即加载 | health + catalog + sessions + briefing + weather + hotspots + tasks |
| tasks | `#tasksBody` `#goalsBody` | 进入 view 时 | `/api/tasks` `/api/goals` `/api/activity` `/api/trace` |
| knowledge | `#knowledgeBody` | 进入 view 时 | `/api/knowledge`（329 条，全量渲染） |
| memory | `#memoryBody` | 进入 view 时 | 7 个端点串行聚合 |
| tools | `#toolsBody` | 进入 view 时 | `/api/health.tools` + `/api/capability_os/catalog` |
| agents | `#agentsBody` | 进入 view 时 | `/api/agent/state` |
| settings | `#settingsBody` | 进入 view 时 | config + version + user_model + ready + sysmon + logs |

### 1.4 SSE / 流式（两处，契约不同）

| 通道 | 实现 | 位置 | 用途 |
|---|---|---|---|
| `/api/stream` | **原生 `EventSource`** | `app.js:968-984` | 主动推送 + 审批请求（长连接） |
| `/api/chat` | **`fetch` + `ReadableStream` 手动解析** | `app.js:1238-1282` | 对话流式输出 + 工具事件 |

两者均为真实 SSE，无轮询模拟。`streamChat()` 手工切分 `\n\n` 并跳 `[DONE]`，实现正确。

### 1.5 架构总评

**这是本次审计最正面的发现。** 前端代码质量显著高于截图呈现的观感：

- 文件头注释明确写入红线："无任何 mock / 假数据"（`app.js:5`）
- 审批流程实现 **truthful 红线**：只有后端返回 `{ok:true}` 才置终态，否则**恢复按钮等重试，绝不假成功**（`app.js:1054-1071`）
- "深度思考"按钮诚实提示 `/api/models → 404`，**不做假装实现**（`app.js:862-865`）
- 每处数据加载都有 loading → 成功/错误/空态四态

**结论：不需要重写，需要"接线 + 抛光"。**

---

## 2. API Inventory

> 全部端点经 `curl` 实测。仅调用 GET 只读端点；`/api/chat` `/api/asr` `/api/speak` `/api/agent/approval` 为已验证契约（源自代码），本次**未触发**以避免副作用。

### 2.1 已接入（34 个）

| # | Method | Endpoint | 响应顶层键 | 实测 |
|---|---|---|---|---|
| 1 | GET | `/api/health` | status, ok, model, provider, tts_backend, ai_name, theme, memory_graph, key_present, **tools[62]**, features, self_check | 200 |
| 2 | GET | `/api/capability_os/catalog` | total=33, available=27, groups[10] | 200 |
| 3 | GET | `/api/sessions` | ok, sessions[15] | 200 |
| 4 | POST | `/api/session/resume` | ok, resume | 契约 |
| 5 | GET | `/api/chat/history?limit=20` | list | 契约 |
| 6 | POST | `/api/chat` | SSE stream（delta + tool_start/tool_end） | 契约 |
| 7 | GET | `/api/stream` | SSE 长连接 | 契约 |
| 8 | POST | `/api/agent/approval?ticket=&decision=` | ok | 契约 |
| 9 | GET | `/api/agent/state` | enabled, state, current_goal, queue, running, last_report, consecutive_failures | 200 |
| 10 | GET | `/api/briefing` | date, generatedAt, weather, hotspots, tasks, suggestions | 200 |
| 11 | GET | `/api/weather` | ok, fetchedAt, stale, refreshMinutes, city, mode, **card**, **forecast[3]** | 200 |
| 12 | GET | `/api/hotspots` | ok, fetchedAt, stale, refreshMinutes, **platforms{}**, status, geo | 200 |
| 13 | GET | `/api/tasks` | list[50] | 200 |
| 14 | GET | `/api/goals` | list[50] | 200 |
| 15 | GET | `/api/activity` | ok, activity{session_id, conversation_turns, active_goals, active_tasks, has_checkpoint, runtime_running, current_goal, queue_len} | 200 |
| 16 | GET | `/api/trace` | ok, trace{session_id, trace[], count} | 200 |
| 17 | GET | `/api/knowledge` | docs[329] | 200 |
| 18 | GET | `/api/memories` | list[124] | 200 |
| 19 | GET | `/api/memory` | profile[5], note_count, log_count, **summary**, reminders[] | 200 |
| 20 | GET | `/api/notes` | list[31] | 200 |
| 21 | GET | `/api/learnings` | ok, learnings[50], count | 200 |
| 22 | GET | `/api/episodes` | ok, episodes[18] | 200 |
| 23 | GET | `/api/memory/conversations` | ok, conversations[41] | 200 |
| 24 | GET | `/api/memory/important-dates` | ok, dates[4] | 200 |
| 25 | POST | `/api/memory/query` | results | 契约 |
| 26 | GET | `/api/config` | ai_name, theme, build_channel, memory_graph, llm, providers, active_provider, fallback_enabled, provider_probe, tts, media, web_search, social, tool_factory, agent_delegate, remote | 200 |
| 27 | GET | `/api/version` | ok, app_name, version, check_url | 200 |
| 28 | GET | `/api/user_model` | ok, model{identity, projects, preferences, working_style, interaction_pattern, expertise, communication_style, recurring_projects, values, feedback} | 200 |
| 29 | GET | `/api/ready` | ok, ready, key_present, degraded, self_check{checks[12]} | 200 |
| 30 | GET | `/api/sysmon` | ok, ts, fallback, cpu, **mem**, disks, net, topCpu, topMem, uptimeSec, gpu | 200 |
| 31 | GET | `/api/logs` | ok, lines[200], total=6599 | 200 |
| 32 | POST | `/api/asr?ext=.wav` | text（multipart 字段名 `audio`） | 契约 |
| 33 | POST | `/api/speak` | audio/mpeg（body `{text, stream:false}`） | 契约 |
| 34 | GET | `/` `/css/*` `/js/*` | 静态托管 | 200 |

### 2.2 后端源码位置（已定位）

**`G:\xiao6\xiao6-ui\`**（经 `git status` 暴露 + 目录结构确认，监听进程 PID 16876）

| 域 | 关键模块 |
|---|---|
| Agent Runtime | `agent_runtime.py` `agent_delegate.py` |
| Capability OS | `capability_os/`（registry / router / matcher / discovery / execution_mapping / executor_callable / composer / capability_state）、`capabilities.py` `capability_runtime.py` |
| Policy | `permission_guard.py` |
| Computer Use | `computer_action_model.py` `computer_executor.py` `os_bridge.py` |
| Memory | `memory.py` `memory_query.py` `memory_audit.py` `memory_distiller.py` `memory_projection.py` |
| Perception | `ocr_provider.py` |
| 数据源 | `goals.py` `knowledge.py` `notes.py` `hotspots.py` `geo_weather.py` `devices.py` `media.py` `asr.py` `llm.py` `db.py` |

### 2.3 路由表全景（源码 ~90 个路径字符串 vs 运行时实测）

源码中 `"/api/..."` 字面量约 **90 个**，但**并非全部注册到当前 server**。实测分为四层：

| 层 | 数量 | 去向 |
|---|---|---|
| ✅ 已接入前端 | **34** | §2.1 |
| 🟢 **可用但前端未接入**（实测 200） | **18** | §2.4 |
| 🟠 **已挂载但故障**（实测 500） | **5** | §2.5 |
| ⚪ 源码有字符串、运行时 404 / 无响应 | **~33** | §2.6 |

> **方法红线**：源码路径字符串 ≠ 已注册路由。本报告**全部以运行时实测状态码为准**，不因"源码里出现过"就判定能力存在。

### 2.4 可用但前端未接入（18 个 · 全部实测 200）

| Endpoint | 能力归属 | 未接入影响 |
|---|---|---|
| `/api/tools/list` | 工具完整清单 | 工具页仅用 `health.tools`（62），未用此端点 |
| `/api/capabilities` | 能力总览（区别于 `capability_os/catalog`） | 未用 |
| `/api/session` | 单会话详情 | 未用 |
| `/api/calendar/events` · `/api/calendar/next` | 日历 | **可接**：`health.features.calendar_sense=false`，但端点已就绪 |
| `/api/clipboard/history` | 剪贴板历史 | **可接**：`clipboard_sense=false`，但端点已就绪 |
| `/api/focus/app` | 前台应用焦点 | **可接**：`app_focus=false`，但端点已就绪 |
| `/api/geo` · `/api/geo/reverse` | 地理编码 | 未用 |
| `/api/proactive/status` | 主动推送状态 | 未用 |
| `/api/startup_diagnosis` | 启动诊断 | 未用（设置页已有 `/api/ready`） |
| `/api/memory_audit` | 记忆审计 | 未用 |
| `/api/hud/state` · `/api/hud/config` | HUD 状态 | 未用 |
| `/api/devices` | 设备列表（当前空数组） | 未用 |
| `/api/notes/delete` | 笔记删除 | 未用（UI 为只读） |
| `/api/notes/write` | 笔记（GET 返回列表） | 未用，写入语义需后端确认 |
| `/api/data/export` | 数据导出 | 未用 |
| `/api/wakeword` | 唤醒词 | 未用 |
| `/api/boot/state` | 启动状态 | 未用 |
| `/api/audit` | 审计 | 未用 |

**重要洞察**：`health.features` 中 `calendar_sense` / `clipboard_sense` / `app_focus` 均标记 `false`，但**对应端点实测 200 可用**。
这属于**「功能开关关闭 ≠ 能力不存在」** —— 是产品策略性关闭，不是技术缺失。若未来要开启，前端接线成本极低。

### 2.5 已挂载但故障（5 个 · 实测 500）

| Endpoint | 错误 | 影响 |
|---|---|---|
| `/api/perception` · `/api/perception/status` | `No module named 'perception'` | **catalog 标 `available=true` → 声明失真。能力广场必须排除此项** |
| `/api/memory/truth` | 500 | 记忆真值校验不可用 |
| `/api/memory/backfill` | 500 | 记忆回填不可用 |
| `/api/self_awareness/status` | 500 | 自我意识状态不可用 |
| `/api/proactive_agent/status` | 500 | 主动 Agent 状态不可用 |

### 2.6 源码有字符串但运行时不可达

| 状态 | 端点 |
|---|---|
| **404**（未注册到当前 server） | `/api/model` `/api/models` `/api/memory/write` `/api/focus/window` `/api/action/execute` `/api/action/plan` `/api/agent/goal` `/api/agent/intent` `/api/vision/capture` `/api/capability_os/match` `/api/capability_os/plan` `/api/memory/confirm` `/api/kws` `/api/transcribe` `/api/tools`（注：`/api/tools/**list**` 存在） |
| **000**（无响应 / 超时） | `/api/action/capabilities` `/api/action/observe` `/api/vision/displays` `/api/selfcheck` `/api/personal_context` `/api/doc` |

**三条关键结论**：

1. **`/api/memory/write` → 404**。源码含该字符串，但当前 server 未注册。
   → **Memory 写入能力实际不可用**，UI 不得提供记忆写入入口（只读展示）。
2. **`/api/models`（复数）与 `/api/model`（单数）均 404**。
   → "深度思考"确认无后端支撑，前文判断成立。
3. **电脑操作链大量不可达**（`/api/action/*` 4 项中 3 项 404/000、`/api/vision/*` 2 项全不可达）。
   → catalog 中 **Computer Action 21 项的运行时支撑存疑**。虽然 `computer_action` 标 `available=true`，但其执行链路（`/api/action/execute`）未注册。
   → **建议：在向用户展示"电脑操作"能力前，先由后端确认 `/api/action/execute` 的注册状态。**

---

## 3. API → UI Mapping

> 五态判定：`已使用` / `未使用` / `使用但不完整` / `UX 不合理` / `字段错配（BUG）`

| API | 当前用途 | UI 位置 | 数据真实 | 当前 UI 展示方式 | 判定 | 可优化度 |
|---|---|---|---|---|---|---|
| `/api/health` | 探活 + 工具数 | `#liveDot` `#toolBadge` `#heroSub` | ✅ 真实 62 tools | 文本 "62 tools" | **UX 不合理** | 高 |
| `/api/capability_os/catalog` | 首页能力 + 工具页分组 | `#abilityGrid` `#toolsBody` | ✅ 33/27/10 组 | 卡片 grid，取前 6 | **使用但不完整** | 高 |
| `/api/sessions` | 最近对话 | `#recentList` | ✅ 15 条 | 截取前 6，截断 20 字符 | 已使用 | 中 |
| `/api/session/resume` | 恢复会话 | 侧栏点击 | 契约 | toast 提示 | 已使用 | 低 |
| `/api/chat/history` | 渲染历史 | `#messages` | 契约 | 逐条 addMsg | 已使用 | 中 |
| `/api/chat` (SSE) | 对话主链路 | `#messages` | ✅ 真实流式 | 流式文本 + 工具事件条 | 已使用 | 中 |
| `/api/stream` (SSE) | 主动推送 + 审批 | `#proactiveFeed` / 审批卡 | 契约 | 卡片插入 | 已使用 | 中 |
| `/api/agent/approval` | 审批决策 | `.approval-card` | 契约 | 批准/拒绝按钮 + truthful 终态 | 已使用 | 低（质量高） |
| `/api/agent/state` | Agent 状态 | `#agentsBody` | ✅ state=IDLE | 单行 row-card | **使用但不完整** | 中 |
| `/api/briefing` | 今日简报 | `#briefingBox` | ✅ 6 字段完整 | **fallback 到 `JSON.stringify(weather)`** | **字段错配** | **极高** |
| `/api/weather` | 天气 | `#briefingBox` | ✅ card + forecast | **`JSON.stringify(d).slice(0,300)`** | **字段错配** | **极高** |
| `/api/hotspots` | 热点 | `#briefingBox` | ✅ platforms{douyin[14],weibo[14]} | **读 `h.items`/`h.hotspots` → 恒空，永不渲染** | **字段错配** | **极高** |
| `/api/tasks` | 任务预览 + 任务页 | `#taskPreview` `#tasksBody` | ✅ 50 条 | row-card 列表 | 已使用 | 中 |
| `/api/goals` | 目标 | `#goalsBody` | ✅ 50 条 | row-card 列表 | 已使用 | 中 |
| `/api/activity` | 运行状况 | `#runtimeExtra` | ✅ 8 字段 | **只展示 3 字段**（session/turns/active_goals） | **使用但不完整** | 中 |
| `/api/trace` | 执行追踪 | `#runtimeExtra` | ✅ | 最近 15 条倒序 | 已使用 | 低 |
| `/api/knowledge` | 知识库 | `#knowledgeBody` | ✅ 329 条 | **全量渲染，无分页/虚拟滚动** | **UX 不合理** | 高 |
| `/api/memories` | 记忆条目 | `#memoryBody` | ✅ 124 条 | 读 `m.created_at`/`m.source` → **字段不存在** | **字段错配** | **高** |
| `/api/memory` | 用户画像 | `#memoryBody` | ✅ profile/summary/reminders | **只用 profile，`summary` 未展示** | **使用但不完整** | 高 |
| `/api/notes` | 笔记 | `#memoryBody` | ✅ 31 条 | 前 20 条 | 已使用 | 中 |
| `/api/learnings` | 学习记录 | `#memoryBody` | ✅ 50 条 | 前 20 条 | 已使用 | 低 |
| `/api/episodes` | 事件 | `#memoryBody` | ✅ 18 条 | 前 20 条 | 已使用 | 低 |
| `/api/memory/conversations` | 对话历史 | `#memoryBody` | ✅ 41 条 | 前 20 条 | 已使用 | 低 |
| `/api/memory/important-dates` | 重要日期 | `#memoryBody` | ✅ 4 条 | 列表 | 已使用 | 低 |
| `/api/memory/query` | 记忆检索 | `#memSearch` | 契约 | 后端优先，失败降级本地过滤 | 已使用 | 低（降级设计好） |
| `/api/config` | 设置 | `#settingsBody` | ✅ 16 字段 | **只展示 8 项** | **使用但不完整** | 中 |
| `/api/version` | 版本 | `#settingsBody` | ✅ | kv 展示 | 已使用 | 低 |
| `/api/user_model` | 用户模型 | `#settingsBody` | ✅ 10 个维度 | **只展示 identity + 字段名列表** | **使用但不完整** | 高 |
| `/api/ready` | 自检 | `#settingsBody` | ✅ 12 项全通过 | 列表 | 已使用 | 低 |
| `/api/sysmon` | 系统监控 | `#settingsBody` | ✅ cpu/**mem**/disks/net | **读 `sm.memory`（真实为 `sm.mem`）→ 内存恒不显示** | **字段错配** | 中 |
| `/api/logs` | 后端日志 | `#settingsBody` | ✅ 6599 行 | 最后 15 行 | 已使用 | 低 |
| `/api/asr` | 语音输入 | `#btnVoice` | 契约 | MediaRecorder → 填入输入框 | 已使用 | 低 |
| `/api/speak` | TTS 朗读 | `.speak-btn` | 契约 | 每条回答挂"朗读" | 已使用 | 低 |
| `/api/devices` | — | **未接入** | ✅ 空数组 | 无 | **未使用** | 待定 |
| `/api/notes/write` | — | **未接入** | ✅ 列表 | 无 | **未使用** | 待定 |
| `/api/perception` | — | **未接入** | ❌ 500 | 无 | **未使用（且失效）** | 禁接 |

### 3.1 五态汇总

| 状态 | 数量 | 清单 |
|---|---|---|
| 已使用 | 21 | health, sessions, resume, chat/history, chat, stream, approval, tasks, goals, trace, notes, learnings, episodes, conversations, important-dates, memory/query, version, ready, logs, asr, speak |
| 使用但不完整 | 6 | catalog, agent/state, activity, memory, config, user_model |
| 字段错配（BUG） | 5 | **briefing, weather, hotspots, memories, sysmon** |
| UX 不合理 | 2 | health（62 tools 误导）, knowledge（329 条全量渲染） |
| **可用但完全未接入** | **18** | tools/list, capabilities, session, calendar×2, clipboard/history, focus/app, geo×2, proactive/status, startup_diagnosis, memory_audit, hud×2, devices, notes/delete, notes/write, data/export, wakeword, boot/state, audit |
| **已挂载但故障** | **5** | perception×2（500）, memory/truth（500）, memory/backfill（500）, self_awareness/status（500）, proactive_agent/status（500） |
| 源码有但运行时 404/000 | ~33 | model(s), memory/write, action/*, vision/*, capability_os/match&#124;plan, agent/goal, agent/intent, kws, transcribe, selfcheck … |

> **未接入 18 项 = 零后端成本的 UI 增量空间**；**故障 5 项 = 需在能力展示中显式排除**；**404 项 = 不得据源码字符串宣称能力存在**。

---

## 4. Capability Map

### 4.1 全量 33 项能力（实测 `/api/capability_os/catalog`）

`total=33` · `available=27` · `groups=10`

| # | capability id | name | group | avail | risk | permission | implemented |
|---|---|---|---|---|---|---|---|
| 1 | voice | 语音 | Voice | ✅ | LOW | auto | ✅ |
| 2 | memory | 记忆 | Memory | ✅ | LOW | auto | ✅ |
| 3 | knowledge | 知识库 | Knowledge | ✅ | LOW | auto | ✅ |
| 4 | goals | 目标 | Goals | ✅ | LOW | auto | ✅ |
| 5 | perception | 屏幕感知 | Perception | ⚠️ | LOW | auto | ✅ |
| 6 | computer_action | 电脑操作 | Computer Action | ✅ | MEDIUM | confirm | ✅ |
| 7 | delete | 删除 | Computer Action | ❌ | CRITICAL | **block** | ❌ |
| 8 | system | 系统操作 | Computer Action | ❌ | CRITICAL | **block** | ❌ |
| 9 | network | 网络操作 | Computer Action | ❌ | CRITICAL | **block** | ❌ |
| 10 | read_file | 读取文件 | Computer Action | ✅ | LOW | auto | ✅ |
| 11 | capture_screen | 截取屏幕 | Computer Action | ✅ | LOW | auto | ✅ |
| 12 | get_window_info | 获取窗口信息 | Computer Action | ✅ | LOW | auto | ✅ |
| 13 | list_process | 列举进程 | Computer Action | ✅ | LOW | auto | ✅ |
| 14 | perception.screen | 屏幕感知 | Computer Action | ✅ | LOW | auto | ✅ |
| 15 | perception.window | 窗口感知 | Computer Action | ✅ | LOW | auto | ✅ |
| 16 | perception.ocr | 屏幕文字识别 | Computer Action | ✅ | LOW | auto | ✅ |
| 17 | open_folder | 打开文件夹 | Computer Action | ✅ | MEDIUM | confirm | ✅ |
| 18 | open_file | 打开文件 | Computer Action | ✅ | MEDIUM | confirm | ✅ |
| 19 | search | 搜索文件 | Computer Action | ✅ | LOW | auto | ✅ |
| 20 | copy_text | 复制文本 | Computer Action | ✅ | LOW | auto | ✅ |
| 21 | open_application | 打开应用 | Computer Action | ✅ | MEDIUM | confirm | ✅ |
| 22 | focus_window | 聚焦窗口 | Computer Action | ✅ | MEDIUM | confirm | ✅ |
| 23 | browser_navigate | 浏览器导航 | Computer Action | ✅ | MEDIUM | confirm | ✅ |
| 24 | modify_file | 修改文件 | Computer Action | ❌ | HIGH | **block** | ❌ |
| 25 | execute_command | 执行命令 | Computer Action | ❌ | HIGH | **block** | ❌ |
| 26 | kill_process | 结束进程 | Computer Action | ❌ | HIGH | **block** | ❌ |
| 27 | tools | 工具 | Tools | ✅ | LOW | auto | ✅ |
| 28 | time | 时间 | Tools | ✅ | LOW | auto | ✅ |
| 29 | world_pulse | 世界脉动 | World Pulse | ✅ | LOW | auto | ✅ |
| 30 | hotspot | 热点上下文 | World Pulse | ✅ | LOW | auto | ✅ |
| 31 | prefetch | 预取背景（天气/新闻） | World Pulse | ✅ | LOW | auto | ✅ |
| 32 | user_model | 用户画像 | User Model | ✅ | LOW | auto | ✅ |
| 33 | self_diagnosis | 启动自检 | Self Diagnosis | ✅ | LOW | auto | ✅ |

### 4.2 分组分布

| Group | 数量 | 构成 |
|---|---|---|
| Computer Action | **21** | 占 64%，其中 6 项 blocked、8 项 MEDIUM/confirm |
| World Pulse | 3 | world_pulse, hotspot, prefetch |
| Tools | 2 | tools, time |
| Voice / Memory / Knowledge / Goals / Perception / User Model / Self Diagnosis | 各 1 | — |

### 4.3 关键架构洞察：62 tools ≠ 62 能力

| 层 | 数量 | 语义 | 谁在用 |
|---|---|---|---|
| **Tools** | 62 | Agent 可调用的函数注册表 | Agent 内部 |
| **Capabilities** | 33（27 可用） | 用户可理解的能力门面 + **Policy 门控** | 应面向用户 |
| **Blocked** | 6 | Policy Engine 拦截：`delete` `system` `network` `modify_file` `execute_command` `kill_process` | 不可执行 |

**这是 Policy Engine 在 Capability 层拦截的明证**：
- `health.tools` 确实包含 `run_shell` / `kill_process` / `file_write` / `file_delete`（函数已注册）
- 但对应 capability `execute_command` / `kill_process` / `modify_file` / `delete` 标记 `available=false`、`permission=block`、`implemented=false`
- 即：**函数存在，但能力被 Policy 熔断**

**结论：首页展示 "62 tools" 具有误导性** —— 它把被 Policy 熔断的危险操作也算作"能力"。
**建议改为：展示「27 项可用能力」（或「33 项能力 · 27 项可用」），62 tools 下沉到工具页作为技术细节。**

### 4.4 能力 → Tool → API → UI → 状态（完整链路）

```
能力：记忆
  ↓ capability: memory (available, LOW, auto)
  ↓ tools:      remember, memory_search, profile_set, profile_get
  ↓ API:        /api/memories(124) /api/memory(profile+summary) /api/memory/query
  ↓ 当前 UI:     memory 页 · renderMemoryHTML
  ↓ 状态:        ✅ 后端数据充分；❌ 前端字段错配（created_at/source 不存在）
                 ⚠️ 未展示 memory.summary（最可读的画像摘要）

能力：知识库
  ↓ capability: knowledge (available, LOW, auto)
  ↓ tools:      add_knowledge, archive_knowledge
  ↓ API:        /api/knowledge (329 docs)
  ↓ 当前 UI:     知识库页全量渲染
  ↓ 状态:        ✅ 数据真实且丰富；❌ 无分页/无搜索/无分组（性能与可用性风险）

能力：语音
  ↓ capability: voice (available, LOW, auto)
  ↓ entry:      asr.transcribe / server._tts_sovits(GPT_SOVITS_URL)
  ↓ tools:      asr_transcribe
  ↓ API:        POST /api/asr?ext=.wav · POST /api/speak (tts_backend=edge)
  ↓ 当前 UI:     麦克风按钮 + 每条回答"朗读"
  ↓ 状态:        ✅ 输入输出双向完整，是全项目完成度最高的能力

能力：目标与任务
  ↓ capability: goals (available, LOW, auto)
  ↓ tools:      set_goal, plan_goal, update_goal, list_goals, set_task, complete_task, task_list
  ↓ API:        /api/goals(50) /api/tasks(50) /api/activity /api/trace
  ↓ 当前 UI:     任务页 + 首页任务预览
  ↓ 状态:        ✅ 完整；⚠️ activity 8 字段只用了 3 个

能力：世界脉动（天气 / 热点）
  ↓ capability: world_pulse, hotspot, prefetch (all available)
  ↓ tools:      get_weather, get_hotspots, manage_prefetch_task
  ↓ API:        /api/weather(card+forecast) /api/hotspots(platforms+geo+status) /api/briefing
  ↓ 当前 UI:     首页简报区
  ↓ 状态:        ⚠️ 后端数据**极其充分**（card 13 字段 / forecast 3 天 / geo 28 地域）
                 ❌ 前端 100% 未消费，全部降级为 JSON.stringify 或恒空

能力：电脑操作
  ↓ capability: computer_action + 20 子能力 (available, MEDIUM, **confirm**)
  ↓ tools:      scan_desktop, scan_installed_software, play_video, open_doc_panel ...
  ↓ API:        经 /api/chat SSE 的 tool_start/tool_end + /api/agent/approval
  ↓ 当前 UI:     工具事件条 + 审批卡
  ↓ 状态:        ✅ 审批链路完整且 truthful；⚠️ 首页无任何入口

能力：屏幕感知
  ↓ capability: perception (available=true, LOW, auto)
  ↓ tools:      scan_desktop, capture_screen
  ↓ API:        /api/perception
  ↓ 当前 UI:     无
  ↓ 状态:        ❌ **catalog 标 available=true，但 /api/perception → 500 "No module named 'perception'"**
                 → catalog 与运行时不一致，属**能力声明失真**

能力：执行/删除/网络（6 项）
  ↓ capability: delete, system, network, modify_file, execute_command, kill_process
  ↓ 状态:        ❌ Policy blocked（available=false, permission=block, implemented=false）
                 → 用户不可用，不应出现在任何"能力"展示中
```

---

## 5. Home Information Architecture

### 5.1 Welcome（欢迎区）

**现状**（`index.html:78-90`）：
- 104px 红心（带眼睛 + 微笑，`style.css:131-164`）
- `.greeting` 30px："你好，我是**小6**"
- `#heroSub` 由 JS 覆写为 "你的专属 AI 助手 · agnes-2.5-flash · 已挂载 62 个工具"
- 4 个快捷胶囊（`app.js:882-887` 硬编码）

**问题**：
1. 问候语"你好"为静态，未做时段感知（后端已有 `/api/briefing.generatedAt = 00:08`，时间源充足）
2. `#heroSub` 未使用 `user_model.identity.name`（后端已有用户身份），也未用 `memory.summary`
3. "62 个工具" 属**技术细节，且含被 Policy 熔断的危险能力**，不适合作为首屏卖点
4. 4 个胶囊硬编码，与 33 项真实能力无关联

**真正需要展示的**（按信息价值排序）：

| 优先级 | 内容 | 数据源 | 现状 |
|---|---|---|---|
| P0 | 时段化问候 + 用户称谓 | `user_model.identity.name` + 本地时钟 | ❌ 未做 |
| P0 | 可用能力数（27）而非工具数（62） | `catalog.available` | ❌ 展示错误数字 |
| P1 | 今日待办 / 建议 | `briefing.suggestions[3]` | ❌ 完全未用（后端已有 3 条自然语言建议） |
| P1 | 快捷入口与真实能力绑定 | `catalog.groups` | ❌ 硬编码 |
| P2 | 连接状态 | `liveDot` | ✅ 已有 |

### 5.2 Briefing（今日简报）— **本次审计最大发现**

**真实数据源全表**：

| 数据 | 端点 | 字段 | 实测值 | 更新 | 可靠性 |
|---|---|---|---|---|---|
| 日期 | `/api/briefing` | `date` | `2026-09-02` | 每日 | ✅ |
| 生成时间 | `/api/briefing` | `generatedAt` | `00:08` | 每次生成 | ✅ |
| 天气摘要 | `/api/briefing` | `weather{city,condition,temp,high,low}` | 郑州/晴/25/29/21 | 30 分钟 | ✅ |
| 热点摘要 | `/api/briefing` | `hotspots[{platform,rank,text,heat,url}]` | 抖音 + 微博各 14 条 | 实时 | ✅ |
| 任务 | `/api/briefing` | `tasks[]` | 空 | — | ✅ |
| **建议** | `/api/briefing` | `suggestions[3]` | "⏸️ #66 GUI链路验证…已 11 天没动静…" | 每次生成 | ✅ **未用** |
| 天气卡 | `/api/weather` | `card{variant,city,temp,condition,feel,high,low,humidity,wind,visibility,wind_dir,wind_kmh,aqi}` | 13 字段 | `refreshMinutes=30` | ✅ **未用** |
| 预报 | `/api/weather` | `forecast[3]` | 今天/明天/后天 | 30 分钟 | ✅ **未用** |
| 新鲜度 | `/api/weather` | `ok, fetchedAt, stale, refreshMinutes` | `stale=False` | — | ✅ **未用** |
| 热点分平台 | `/api/hotspots` | `platforms{douyin[14],xiaohongshu[0],wechat[0],weibo[14]}` | 抖音 + 微博 | 实时 | ✅ **未用** |
| 热点源状态 | `/api/hotspots` | `status{douyin:{ok,count:49,source:xxapi}, xiaohongshu:{ok:false}, wechat:{ok:false}, weibo:{...}}` | 2/4 平台可用 | — | ✅ **未用** |
| 热点地域 | `/api/hotspots` | `geo{total:28, regions[]}` | 28 地域 | — | ✅ **未用** |

**是否可以卡片化：完全可以，且后端零改动。**

后端 `weather.card` 已是成品卡片结构（13 字段），`weather.forecast` 已是 3 天数组，`hotspots.platforms` 已按平台分组并带 `url`/`heat`/`trend`。

**当前为何呈现为 JSON**：
```js
// app.js:279-284  ← briefing 无 summary/content/text 字段 → 恒为 ""
let body = b.summary || b.content || b.text || "";
if (!body && b.weather) body = JSON.stringify(w);   // fallback 到 JSON 直出
// app.js:292      ← weather 直接 stringify，丢弃 card/forecast
'<div class="pc-body">' + esc(JSON.stringify(d).slice(0, 300)) + "</div>"
```
**这正是截图中 JSON 直出的根因 —— 100% 前端问题。**

### 5.3 Recent Conversations

- **数据源**：`GET /api/sessions` → `{ok, sessions[15]}`，字段 `session_id, created_at, updated_at, status`
- **真实**：15 条，含 `test-123` 等真实会话
- **问题**：
  - 前端 `app.js:196` 用正则剥前缀 `^p\d+_` 与 `_stale` → 显示名大量退化为难以辨认的 ID 片段（如 `080c460456_get`）
  - 无摘要预览（后端 `sessions` 无摘要字段，但 `/api/memory/conversations` 有 `topic`/`key_points`，可作为关联数据源）
  - 点击恢复依赖 `/api/session/resume`，无 checkpoint 时 toast 提示"无检查点"（诚实，但体验生硬）

### 5.4 Capabilities（首页"小6 的能力"）

**应展示哪一种？**

| 候选 | 数量 | 是否适合首页 | 理由 |
|---|---|---|---|
| Tools（工具） | 62 | ❌ | 技术细节，含被熔断项，用户无法理解 |
| Capabilities（能力） | 33 / 27 可用 | ✅ **推荐** | 用户语义，带 Policy 门控语义 |
| 状态 | IDLE 等 | ⚠️ | 属 Agent 域，不宜混在能力区 |
| 数量 | 27 | ⚠️ | 可作为副标题，不作主体 |

**结论：首页应展示 Capability（27 项可用能力），按 10 个 group 归类，不展示 62 tools 原始函数名。**

---

## 6. Chat Input Capability（逐项后端验证）

> 原则：**不为 UI 显示一个按钮而制造不存在的能力。**

| 功能 | 后端支持 | 端点 / 证据 | 当前 UI | 是否可直接做 |
|---|---|---|---|---|
| 多行输入 | N/A（纯前端） | `app.js:849-852`，`max-height:200px` 已实现 | ✅ 已实现，自适应高度 | ✅ **已完成** |
| 文本发送 | ✅ | `POST /api/chat` SSE | ✅ | ✅ 已完成 |
| **Enter / Shift+Enter** | N/A | `app.js:853-855` | ✅ | ✅ 已完成 |
| **附件上传** | ❌ **无后端支撑** | 无 `/api/upload`（404）；`app.js:899-904` 仅 toast 提示"上传链路需后端端点支持" | ⚠️ 按钮存在但只弹提示 | ❌ **不可做**，需新增后端端点 |
| **图片理解** | ❌ **无能力支撑** | 33 项 capability 中无 vision/image 项；62 tools 中无 image understand | 无入口 | ❌ **绝不可加**（无中生有） |
| 文件解析 | ⚠️ 间接 | `read_file` capability（available）；`file_read` tool；沙箱限制 | 无输入框入口 | ⚠️ 仅可在确认沙箱路径后做 |
| **麦克风 / 语音输入** | ✅ **完全支持** | `POST /api/asr?ext=.wav`（multipart 字段 `audio`）；capability `voice` | ✅ MediaRecorder 已实现 | ✅ 已完成 |
| **TTS 朗读** | ✅ **完全支持** | `POST /api/speak`（body `{text, stream:false}`）；`health.tts_backend=edge` | ✅ 每条回答挂"朗读" | ✅ 已完成 |
| **联网搜索** | ✅ 支持（tool 层） | tool `web_search` 在 `health.tools[62]` 中；前端 `app.js:1166` 前缀注入 "请使用 web_search 工具联网检索后回答：" | ✅ 已实现（软提示方式） | ✅ 已完成，但实现为"提示词注入"而非参数化 |
| **深度思考** | ❌ **无后端支撑** | `/api/models` → **404**；`app.js:864` 已诚实 toast 提示 | ⚠️ 按钮存在但为**死按钮** | ❌ **不可做**（需后端） |
| 思考深度档位 | ❌ | 同上，无参数化端点 | 无 | ❌ 不可做 |
| 发送按钮 | ✅ | `.send-btn`，`app.js:1175` busy 时 disable | ✅ | ✅ 已完成 |
| 停止生成 | ❌ | `streamChat` 无 AbortController | ❌ 缺失 | ⚠️ 可纯前端做（AbortController） |
| 审批（高风险动作） | ✅ **完全支持** | `/api/stream` 推送 ticket → `POST /api/agent/approval` | ✅ truthful 实现 | ✅ 已完成，质量高 |

### 6.1 结论

| 分类 | 项数 | 清单 |
|---|---|---|
| 已完成 | 7 | 多行输入、发送、Enter 语义、麦克风、朗读、联网搜索、审批 |
| 可纯前端补 | 1 | 停止生成（AbortController） |
| **需后端才能做** | 3 | 附件上传、深度思考、思考深度档位 |
| **绝不可做（无中生有）** | 1 | **图片理解**（catalog 无 vision 能力，tools 无对应函数） |

**关键红线**：我 2026-09-01 建议中的"图片理解"和"附件"**均无后端支撑**，必须从能力广场与输入框改造中**剔除**。

---

## 7. Memory UX Capability

### 7.1 七个端点真实状态（实测）

| 端点 | 结构 | 数量 | 前端消费 | 状态 |
|---|---|---|---|---|
| `/api/memories` | `list[124]`，字段 `id, event_type, title, content, mem_id, entities, tags, links, salience, source_ref` | 124 | 读 `m.title`/`m.event_type`/`m.content`/`m.mem_id`/**`m.created_at`**/**`m.source`** | ❌ **后两字段不存在** → 时间与来源恒空 |
| `/api/memory` | `profile[5], note_count=31, log_count=16, summary, reminders[0]` | — | **只用 `profile`** | ⚠️ `summary`（最可读的画像摘要）**未展示** |
| `/api/notes` | `list[31]`，字段 `id, ts, title, markdown, tags, links, folder, aliases` | 31 | 前 20 条 | ✅ |
| `/api/learnings` | `{ok, learnings[50], count}`，字段 `id, type, content, weight, created, last_used` | 50 | 前 20 条 | ⚠️ `weight` 未展示 |
| `/api/episodes` | `{ok, episodes[18]}`，字段 `id, title, summary, category, importance, created, access_count, project, source, event` | 18 | 前 20 条 | ⚠️ `importance` / `access_count` 未展示 |
| `/api/memory/conversations` | `{ok, conversations[41]}`，字段 `id, date, topic, key_points, sentiment, created` | 41 | 前 20 条 | ⚠️ `sentiment` 未展示 |
| `/api/memory/important-dates` | `{ok, dates[4]}`，字段 `id, date, type, description, reminder_days, created` | 4 | 全部 | ✅ |

### 7.2 核心问题：展示的是"数据库结构"，不是"用户理解的记忆"

当前 Memory 页按**后端表结构**分 7 段堆叠：记忆条目 / 画像 / 笔记 / 学习记录 / 事件 / 对话历史 / 重要日期。
用户看到的是 7 个"数据库表"，而不是"小6 记得关于我的什么"。

**例证**：`/api/memory.summary` 已给出人类可读的画像：
```
1. 偏好：江苏风、极简、隐私优先、本地AI副驾及简体中文朗读
2. 安全：DuckDB v2.0与Snowflake Jira有泄露风险，v1.4.1严禁改动
...
```
这条**最能回答"小6 懂我什么"**的数据，被完全隐藏。

### 7.3 信息架构建议（不写代码）

**推荐改为三层，而非七表堆叠**：

```
第一层：小6 眼中的我        ← /api/memory.summary + user_model.preferences/working_style/values
        （卡片：一段可读的画像摘要 + 关键偏好标签）

第二层：记得的事            ← 以时间轴 / 重要性聚合
        ① 重要日期         ← /api/memory/important-dates (4)
        ② 高价值记忆       ← /api/memories 按 salience 排序（当前未用 salience）
        ③ 关键事件         ← /api/episodes 按 importance 排序（当前未用 importance）

第三层：原始记录（可折叠）  ← 笔记 / 学习 / 对话历史 / 记忆条目全量
        （供需要时下钻，默认收起）
```

**次要建议**：
- 修复 `memories` 字段错配（`created_at` → 无；`source` → `source_ref`）
- 检索入口保留 `/api/memory/query`（当前后端优先 + 本地降级，设计良好）
- 124 条记忆 + 41 条对话 + 31 条笔记应引入分页或分组折叠

---

## 8. Agent UX Capability

### 8.1 真实暴露状态（`/api/agent/state` 实测）

```json
{
  "enabled": true,
  "state": "IDLE",
  "current_goal": null,
  "queue": [],
  "running": true,
  "last_report": null,
  "consecutive_failures": 0
}
```

| 字段 | 实测值 | 语义 | 是否该给用户看 |
|---|---|---|---|
| `enabled` | `true` | Agent 总开关 | ✅ 是（"已启用"） |
| `state` | `IDLE` | 状态机当前态 | ✅ 是（**主要展示项**） |
| `current_goal` | `null` | 当前目标 | ✅ 是（有值时展示） |
| `queue` | `[]` | 待执行队列 | ⚠️ 仅展示长度 `queue_len` |
| `running` | `true` | Runtime 是否在跑 | ❌ **否**（内部字段；`state=IDLE` + `running=true` 对用户是矛盾信息） |
| `last_report` | `null` | 上次报告原文 | ❌ 否（调试字段） |
| `consecutive_failures` | `0` | 连续失败次数 | ⚠️ 仅当 > 0 时告警 |

### 8.2 `/api/activity` 的完整 8 字段

`session_id, conversation_turns, active_goals, active_tasks, has_checkpoint, runtime_running, current_goal, queue_len`

前端只用了 3 个（`session_id` / `conversation_turns` / `active_goals`），**遗漏 5 个**。
其中 `active_tasks` / `has_checkpoint` 对用户判断"小6 现在能不能继续上次的事"很有价值。

### 8.3 SSE 事件中的 Agent 信号（`/api/chat`）

| 事件 | 前端处理 | 位置 | 状态 |
|---|---|---|---|
| `xiao6_event: tool_start` | 工具事件条（running 黄点） | `app.js:1194-1198` | ✅ |
| `xiao6_event: tool_end` | 工具事件条（done 绿点） | `app.js:1199-1201` | ✅ |
| `choices[0].delta.content` | 流式文本 | `app.js:1185-1192` | ✅ |
| 审批 ticket | 审批卡 + truthful 终态 | `app.js:1017-1072` | ✅ |

**缺失**：无 `planning` / `error` / `recovery` 事件处理；失败信息仅通过 toast 呈现。

### 8.4 建议：该看什么 / 不该看什么

| 展示给用户 | 不展示（内部 Runtime 调试字段） |
|---|---|
| 状态机（IDLE / 工作中 / 等待确认） | `running` 布尔量 |
| 当前目标标题 | `last_report` 原文 |
| 队列长度（"还有 N 件事"） | `consecutive_failures` 原始数字（仅 >0 时转告警文案） |
| 当前工具调用（工具事件条） | 内部 ticket 字符串 |
| 失败 → 人话告警 + 重试 | 堆栈 / trace 原文（保留在设置页日志区即可） |

**结论：Agent 页应做成"状态 + 目标 + 队列"三栏，而非 dump 内部 state JSON。当前 `loadAgents()` 已接近此形态，只需补充 `queue_len` 与错误态文案化，并移除 `running` 的矛盾展示。**

---

## 9. Real Data Audit

**结论先行：全部 UI 动态信息均可追溯到真实 Runtime/API，未发现任何 fabricated data。**

| 检查项 | 结果 | 证据 |
|---|---|---|
| 真实 API 调用 | ✅ 34 个端点全部指向 `127.0.0.1:8000` 同源 | `app.js:4` 注释 + 全量 grep |
| 硬编码后端地址 | ✅ 无（无 8765 残留，无跨端口） | grep `:8765` → 0 命中 |
| 数据源 | ✅ 全部 live API，无本地缓存伪装 | 全文件扫描 |
| 工具数量 | ✅ 62 来自 `health.tools.length` 实时计算 | `app.js:114` |
| 能力数量 | ✅ 33/27 来自 catalog 实时 | `app.js:81` |
| 任务/目标/记忆/知识 | ✅ 全部实时 | 实测 50/50/124/329 |
| 错误态 | ✅ 无假成功，审批强制校验 `ok===true` | `app.js:1054` |

**未发现**：mock 数据、静态 JSON 兜底、假统计、假工具数量、假状态、假消息。

---

## 10. Mock / Placeholder Audit

虽无 mock，但存在 **9 处 hardcoded / 死代码 / 失效声明**，需清理：

| # | 类型 | 位置 | 内容 | 影响 | 严重度 |
|---|---|---|---|---|---|
| 1 | **死代码** | `app.js:244-251` | `ABILITY_DEF`：6 个能力定义（memory_search/file_write/add_knowledge/run_shell/web_search/media_generate） | **从未被引用**，`loadAbilities()` 走 catalog | 中（误导维护者） |
| 2 | **死代码** | `app.js:252-259` | `ICONS`：6 个 SVG path | **从未被引用**（实际用 `c.icon`） | 中 |
| 3 | **硬编码数字** | `index.html:188` | `placeholder="筛选 62 个已挂载工具…"` | 后端工具数变化时不更新，且渲染在加载前 | 中 |
| 4 | **硬编码文案** | `app.js:882-887` | `QUICK` 4 条快捷问题硬编码 | 与 33 项真实能力无关联 | 中 |
| 5 | **硬编码身份** | `index.html:64-66` | 头像 "S" / "Six 用户" 写死 | 后端 `user_model.identity.name` 已存在却未用 | 中 |
| 6 | **字段错配** | `app.js:292` | `JSON.stringify(weather).slice(0,300)` | 丢弃 `card` 13 字段 + `forecast` | **高（首屏观感）** |
| 7 | **字段错配** | `app.js:279-280` | briefing 无 `summary`/`content`/`text` → fallback JSON | 简报区实际是 JSON dump | **高** |
| 8 | **字段错配** | `app.js:300` | 读 `h.items`/`h.hotspots`，真实为 `h.platforms` | **热点区恒空，永不渲染** | **高** |
| 9 | **能力声明失真** | catalog `perception` | `available=true`，但 `/api/perception` → **500 No module named 'perception'** | catalog 与运行时不一致 | **高（能力广场必须排除）** |

补充（中低优先级）：

| # | 类型 | 位置 | 内容 |
|---|---|---|---|
| 10 | 字段错配 | `app.js:820` | 读 `sm.memory`，真实为 `sm.mem` → 设置页内存恒不显示 |
| 11 | 字段错配 | `app.js:603-605` | 读 `m.created_at`（不存在）/ `m.source`（真实为 `source_ref`）→ 记忆时间/来源恒空 |
| 12 | emoji 图标 | `app.js:281,291,302,997,1028,1057` | ☀️ 🌤 🔥 📡 ⏰ 💬 ⚠️ ✓ 混用于功能图标（非装饰性语境） |
| 13 | 死按钮 | `app.js:862-865` | "深度思考"点击仅弹 toast（诚实但体验差） |
| 14 | 死按钮 | `app.js:866,899-904` | "附件"点击选文件后仅 toast，无上传链路 |

---

## 11. Design System Recommendations

### 11.1 现状：Design Token 体系已完备（`style.css:4-27`）

| 类别 | 现有 Token | 值 |
|---|---|---|
| 品牌 | `--brand` / `--brand-soft` / `--brand-tint` / `--brand-glow` | `#ff4d4f` / `#ffe7e7` / `#fff1f0` / `rgba(255,77,79,.16)` |
| 文字 | `--ink-1..4` | `#1a1a1a` `#4a4a4a` `#8a8a8a` `#b0b0b0` |
| 背景 | `--bg` / `--bg-soft` | `#ffffff` / `#f7f7f9` |
| 描边 | `--line` / `--line-soft` | `#ececef` / `#f1f1f3` |
| 圆角 | `--r-sm/md/lg/xl` | `8 / 12 / 16 / 22 px` |
| 阴影 | `--sh-sm` / `--sh-md` / `--sh-pop` | 3 级 |
| 状态 | `--ok` / `--warn` | `#52c41a` / `#faad14` |
| 布局 | `--sidebar-w` | `248px` |

**已有动画 8 组**：`breathe`（idle 呼吸）、`pulseFast`（listening）、`think`、`speak`、`pulse`（审批红点）、`fadeUp`（消息入场）、`blink`（typing）、`spin`（loading）
**已有响应式 3 断点**：1400 / 1100 / 860

### 11.2 建议（在不推翻现有体系的前提下增补）

| 维度 | 现状 | 建议 | 约束 |
|---|---|---|---|
| **颜色** | 单红 + 中性灰，状态色仅 2 | 保持 `#ff4d4f` 为**唯一品牌强调色**；补充 `--info`（蓝，用于"运行中/信息"）与 `--danger`（复用 brand）；**不引入第二品牌色** | 红色唯一 |
| **字体** | `-apple-system, PingFang SC, Microsoft YaHei, Segoe UI, Helvetica, Arial` | **保持**，中文渲染已优；仅建议补 `font-variant-numeric: tabular-nums` 到更多数字区（当前仅 `.progress-pct` 有） | 不换字体族 |
| **字号** | greeting 30 / h1 22 / title 14.5 / body 14.5 / desc 13 / foot 12 / hint 11.5 | 收敛为 **7 级**：28 / 22 / 16 / 14.5 / 13 / 12 / 11.5；移除 13.5 与 14.5 的混用 | 保持层级 |
| **字重** | 400 / 500 / 600 / 700 混用 | 收敛为 **400（正文）+ 600（标题）** 两级；`brand-name b{700}` 与 `user-avatar{700}` 降级为 600 | 双字重 |
| **圆角** | `--r-sm/md/lg/xl` 8/12/16/22 | 保持；但 `.chip`/`.pill-btn` 用 `999px`、卡片用 `--r-md(12)`、大容器用 `--r-lg(16)` 应形成明确规则 | 已有体系 |
| **间距** | 无 spacing token，散落 6/8/10/12/14/16/18/26/30/34 | **建议引入** `--sp-1..6` = 4/8/12/16/24/32，替换魔数 | 最大可改进项 |
| **阴影** | `--sh-sm/md/pop` 3 级 | 保持，**不新增**；`--sh-pop` 仅用于红心与发送按钮 | 克制 |
| **图标** | 内联 SVG（stroke 2 / 2.6）+ emoji 混用 | **统一为内联 SVG**，`stroke-width:1.75`，尺寸 14/16/18；**移除功能语境 emoji**（☀️🌤🔥📡⏰⚠️✓）；catalog 的 `icon` 字段本身是 emoji（🎙️🧠📚🎯），UI 层应做 emoji→SVG 映射表或直接使用文字 | 一致性 |
| **状态色** | `--ok` / `--warn` | 补充 `--info:#378ADD`（执行中）；block 态用中性灰 + 锁形图标，不用红色（避免与品牌色混淆） | 语义清晰 |
| **动画** | 8 组，均 ≤3.4s | 保持；建议补 `prefers-reduced-motion` 媒体查询兜底 | 可访问性 |

**总评：设计系统无需重建，仅需 (a) 引入 spacing token、(b) 收敛字重/字号、(c) 去 emoji 化。三项均为低风险增量。**

---

## 12. Technical Stack Assessment

### 12.1 针对我 2026-09-01 提议的 4 项技术栈，逐项评估

| 提议 | 当前是否需要 | 评估 |
|---|---|---|
| **React** | ❌ **不需要** | 当前 7 个 view、91.5KB 代码、单 IIFE。引入 React 需构建链（打包器 + JSX + HMR + 路由），收益（组件复用）在当前规模下低于成本（构建复杂度 + 迁移风险 + 91.5KB 全部重写） |
| **Tailwind** | ❌ **不需要** | `style.css` 已有完整 Design Token + 428 行语义化类。引入 Tailwind 意味着**推翻已有 token 体系**并内联 class，与"clean / minimal"背道而驰 |
| **lucide-react** | ❌ **不需要**（且不适用） | 项目无 React；图标已内联 SVG（7 个 nav + toolbar）。如需统一，直接内联 lucide 的 SVG path 即可，**无需引入依赖** |
| **React Query** | ❌ **不需要** | 当前为"进入 view 时拉取 + 手动刷新按钮"模式，无复杂缓存失效/乐观更新需求。引入会引入 30KB+ 依赖与 Provider 包裹层 |

### 12.2 兼容性事实

| 项 | 事实 |
|---|---|
| 构建工具 | 无。`index.html` 直连 `js/app.js`，改完刷新即生效 |
| 包管理 | 无 `package.json`（`ui/` 下无 node_modules） |
| 模块系统 | 无。单一 IIFE，无 import/export |
| 浏览器 API | 用了 `EventSource` / `fetch` + `ReadableStream` / `MediaRecorder` / `URL.createObjectURL` / `FormData` —— 全部现代浏览器原生支持 |
| 服务端耦合 | 后端同源托管静态文件，无 CORS、无代理 |

### 12.3 明确结论

> **UI 改造应在当前技术栈原地升级。不存在必须迁移的技术原因。**

理由：
1. 无构建链 = 零编译风险、零依赖漏洞面、改完即验证
2. Design Token 体系已完备，无需 CSS 框架
3. 逻辑集中在 1 个 1283 行文件，可定位、可增量修改
4. 引入 React/Vite/Tailwind 会使"91.5KB 零依赖"退化为"数百 MB node_modules + 构建产物"，与项目"本地优先、隐私优先、离线可用"的定位冲突

**唯一建议的技术增量**（均为零依赖）：
- `AbortController`（停止生成）—— 原生
- `IntersectionObserver` 或简单分页（知识库 329 条）—— 原生
- `prefers-reduced-motion` 媒体查询 —— 原生 CSS

---

## 13. UI Improvement Priority

| 排名 | 项 | 类型 | 后端改动 | 前端工作量 | 影响 | 依据 |
|---|---|---|---|---|---|---|
| **1** | **修复 5 处字段错配**（weather / briefing / hotspots / memories / sysmon） | BUG | **0** | 中 | **极高** | 后端数据 100% 就绪，纯前端接线；直接消除"JSON 直出"与"热点恒空" |
| **2** | **首页简报卡片化**（消费 `weather.card` + `forecast` + `hotspots.platforms` + `briefing.suggestions`） | 增强 | **0** | 中 | **极高** | 后端已给成品结构；首屏从"开发者视角"变"用户视角" |
| **3** | **能力区改为真实能力**（27 项可用 capability 按 10 组分类，替换 "62 tools" 表述） | 增强 | **0** | 中 | 高 | catalog 已提供 group/icon/description/risk/permission |
| **4** | **清理 9 处 hardcoded / 死代码**（ABILITY_DEF / ICONS / 62 硬编码 / QUICK / 身份硬编码 等） | 清理 | **0** | 低 | 中 | 技术债，影响可维护性 |
| **5** | **Memory 页 IA 重构**（七表 → 三层：画像摘要 / 重要事项 / 原始记录） | 重构 | **0** | 中 | 中 | 从"数据库结构"转"用户理解的记忆" |

**次优先（P2）**：
6. 知识库 329 条分页 / 分组 / 搜索
7. 停止生成（AbortController）
8. 移除非支撑按钮（深度思考 / 附件）或明确标注"未启用"
9. 设计系统微调（spacing token / 字重收敛 / 去 emoji）
10. Agent 页补 `queue_len` 与错误文案化，移除 `running` 矛盾展示

---

## 14. Backend Dependencies

**优先项 1–5 全部为「后端零改动」**，这是本次审计最重要的结论。

### 14.1 无需后端改动（可直接做）

| 项 | 依赖的现有后端能力 |
|---|---|
| 简报卡片化 | `/api/weather.card` + `.forecast` + `/api/hotspots.platforms` + `/api/briefing.suggestions` |
| 能力区重做 | `/api/capability_os/catalog`（33/27/10 组 + icon + description + risk + permission） |
| 字段错配修复 | 全部为前端读取字段名错误 |
| Memory IA 重构 | `/api/memory.summary` + `user_model` + `memories.salience` + `episodes.importance` |
| 清理死代码 | 无依赖 |
| 停止生成 | 无依赖（AbortController） |
| 知识库分页 | 无依赖（前端切片） |

### 14.2 需要后端配合（仅当要做时）

| 需求 | 缺口 | 建议 |
|---|---|---|
| 附件上传 | 无 `/api/upload`（404） | 新增端点 + 沙箱目录策略；**非必需** |
| 深度思考 | `/api/models` 404，无参数化推理档位 | 新增模型/推理参数端点；**非必需** |
| 图片理解 | catalog 无 vision 能力、tools 无对应函数 | **不建议做**（违背"不为按钮制造能力"） |
| 会话摘要 | `/api/sessions` 无摘要字段 | 可复用 `/api/memory/conversations.topic` 关联；或后端补 `summary` 字段 |
| perception 能力 | catalog 标 `available=true`，但 `/api/perception` → 500 | **后端需修正 catalog 声明或修复模块**，否则能力广场必须排除此项 |

### 14.3 后端一致性风险（需老板/Hermes 决策）

| 风险 | 描述 | 建议 |
|---|---|---|
| **perception 声明失真** | catalog `available=true` vs 端点 500 | 二选一：修复 `perception` 模块，或将 catalog 该能力置 `available=false` |
| **62 tools vs 27 可用能力** | 工具层注册了 Policy 已熔断的能力 | 前端展示应以 capability 为准；如需展示 62，需明确标注"含受控能力" |
| **`/api/notes/write` 命名歧义** | GET 返回列表，语义不明 | 后端确认写入契约后再接入 |

---

## 15. Recommended Implementation Order

> 全部阶段 **后端零改动**，可独立验收，可随时停止而不留半成品。

### Phase 1 — 数据接线（消除 JSON 直出与恒空）

**目标**：让首页显示后端已经提供的数据。
**后端改动**：0

1. `app.js:288-295` 天气卡：改用 `w.card`（13 字段）+ `w.forecast[3]` + `w.fetchedAt` / `w.stale`
2. `app.js:271-285` 简报卡：改用 `b.date` / `b.generatedAt` / `b.suggestions[3]` / `b.hotspots[]`
3. `app.js:297-308` 热点卡：字段 `h.items|h.hotspots` → **`h.platforms`**（含 douyin/weibo 各 14 条 + `url` + `heat`）
4. `app.js:820` 系统监控：`sm.memory` → **`sm.mem`**
5. `app.js:603-605` 记忆卡：移除不存在的 `created_at`/`source`，改用 `salience` / `source_ref`

**验收**：首页无 JSON 字符串；天气卡显示 13 字段中的核心 6 项；热点卡显示抖音/微博榜单；设置页显示内存。

### Phase 2 — 能力区重做 + 清理

**目标**：首页展示真实能力，清除误导与死代码。
**后端改动**：0

1. `loadAbilities()` 改为按 `catalog.groups` 的 10 组分类展示，标注 `available` / `risk` / `permission`
2. 首页文案：`62 tools` → `27 项可用能力`（工具页保留 62 明细）
3. 移除 `ABILITY_DEF` / `ICONS` 死代码（`app.js:244-259`）
4. `index.html:188` 移除硬编码 `62`，改为 JS 注入
5. `QUICK` 胶囊改为从 catalog 的 `available` 能力派生（或保持固定但标注为"常用指令"）
6. 头像 / 用户名改用 `user_model.identity.name`

**验收**：首页能力全部来自 catalog；无死代码；无硬编码数字。

### Phase 3 — Memory IA 重构

**目标**：从"七张数据库表"转为"小6 记得什么"。
**后端改动**：0

1. 顶层展示 `/api/memory.summary` 画像摘要 + `user_model.preferences`
2. 中层：`important-dates(4)` + `memories` 按 `salience` 排序 + `episodes` 按 `importance` 排序
3. 底层：笔记 / 学习 / 对话历史 / 全量记忆，默认折叠
4. 保留 `/api/memory/query` 检索（后端优先 + 本地降级，当前设计良好）

**验收**：用户打开 Memory 页第一屏看到的是"小6 对我的理解"，而非表结构。

### Phase 4 — 体验补丁（可选）

1. 停止生成（AbortController）
2. 知识库 329 条分页 + 搜索 + 类型筛选（后端已有 `type`/`tags`/`status` 字段）
3. 深度思考 / 附件按钮：标注"未启用"或移除（避免死按钮）
4. 设计系统微调：spacing token / 字重收敛 / 功能图标去 emoji
5. Agent 页：补 `queue_len`，移除 `running` 矛盾展示，错误文案化

### 阶段依赖

```
Phase 1 (接线)  ──┐
                  ├── 互相独立，可并行或任意顺序
Phase 2 (能力)  ──┤
                  │
Phase 3 (Memory) ─┘
                  ↓
Phase 4 (补丁) ← 建议在 1/2 完成后做，避免返工
```

---

## 附录 A：审计方法

| 步骤 | 工具 | 结果 |
|---|---|---|
| 前端通读 | `Read` index.html / style.css / app.js 全文 | 219 + 1283 行全部覆盖 |
| API 提取 | `Grep /api/*` on app.js | 60 处命中 |
| 端点存在性 | `curl -o /dev/null -w %{http_code}` × 49 | 全量状态码 |
| 结构探测 | Python urllib 解析 JSON 顶层键 / 长度 / 样本 | 30+ 端点结构 |
| 能力清单 | `/api/capability_os/catalog` 全量 33 项 | id/name/group/avail/risk/perm/impl |

**未做（避免副作用）**：未调用 `/api/chat`、`/api/asr`、`/api/speak`、`/api/agent/approval`、任何 POST 写端点。

## 附录 B：Production Changes 声明

```
修改代码：        0
修改 CSS：        0
修改 HTML：       0
修改 JS：         0
安装依赖：        0
删除文件：        0
新增文件：        1（仅本报告）
改端口：          0
改 API：          0
改 AgentRuntime： 0
改版本：          0
commit：          0

Production Changes = 0
```

---

*报告生成：2026-09-02 00:20 (UTC+8) · 审计人：阿枢 (WorkBuddy) · 基线：Xiao6 v1.0.0*
