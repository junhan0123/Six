# Xiao6 AI OS · Ultimate UI 能力审计

> 审计日期：2026-08-10  
> 审计范围：前端 UI 文件、JS 模块、CSS、HTML；后端 server.py、Agent Runtime、Tools、Memory、Knowledge、Goals、EventBus、SSE。  
> 目标：为最终版 AI OS UI 重建提供真实能力边界，禁止在 UI 中伪造数据或新增 Runtime。

---

## 1. 当前 UI 现状与问题

### 1.1 已存在的 `xiao6-ui/final/`
当前 `final/` 是基于参考图 1 快速搭建的近似实现，存在以下结构性问题：

- **在旧架构上修补**：大量 CSS（`ui-final.css` 1500+ 行）直接堆叠在固定画框布局上，未形成可维护的设计系统。
- **能力总览做成了静态说明页**：`capability-view` 区块把 16 个能力做成图标卡片墙，本质是「功能说明书」，不是用户可触发、可感知的能力层。
- **左侧导航仍是传统菜单**：记忆 / 知识 / 任务 / 世界 / 设置，点击打开 overlay，但视觉上是左侧边栏，违背「One Space」理念。
- **World Model 未真实接入**：当前 `galaxy-view.js` / `world-map.js` 尚未真实消费 `/api/memories/graph` 与 computer world 事件。
- **Quick Actions 仍是按钮堆砌**：底部 5 个快捷按钮是功能入口，不是「能力感知」。
- **状态机正确但视觉表现力不足**：AI Core 已接 `avatar-state.js` 8 态，但光环、粒子、波形的高级感与参考图仍有差距。

### 1.2 与重建目标的差距
重建计划要求：
- 一个界面、一个 AI Core、一个 Intent Line。
- 无 Dashboard 卡片墙、无左侧传统导航、无 Galaxy 首页、无 Chat 页面。
- 所有已有能力必须可触发，但不全部展示。
- 能力以「感知」方式表达："我记得…"、"我理解…"、"我正在…"。

当前 `final/` 距离该目标还差一次从零开始的独立重建。

---

## 2. 后端能力审计

### 2.1 AI Core / 状态机

| 能力 | 来源 | 可用性 | 说明 |
|------|------|--------|------|
| Avatar 8 态派生 | `avatar-state.js` | 可用 | `IDLE/WAITING/THINKING/PLANNING/EXECUTING/COMPLETED/ERROR/OFFLINE`，带颜色 META |
| Agent Runtime 状态 | `agent_runtime.py` | 门控开启后可用 | `FEATURE_AGENT_RUNTIME` 默认 `False`；提供 `IDLE/PLANNING/EXECUTING/REFLECTING` |
| HUD 状态快照 | `/api/hud/state` | 可用 | 返回 `state/goal_id/progress` |
| Agent 状态遥测 | `/api/agent/state` | 可用 | runtime 当前状态快照 |
| 健康/就绪检查 | `/api/health`, `/api/ready` | 可用 | 含自检结果、特性开关 |

### 2.2 任务与目标

| 能力 | 来源 | 可用性 | 说明 |
|------|------|--------|------|
| 目标 CRUD | `goals.py` | 可用 | `create_goal/get_goal/update_goal/delete_goal`，状态：`active/paused/completed/archived` |
| 目标列表 | `/api/goals` | 可用 | 只读 GET，支持 `status/horizon/limit` |
| 目标拆解 | `goals.plan_goal()` | runtime 开启后可用 | 创建子 Task |
| 任务管理 | `tasks.py` | 可用 | `create_task/update_task_step/complete_task/get_tasks` |
| 任务列表 | `/api/tasks` | 可用 | `only_open=1` 过滤 |
| 目标进度聚合 | `goals.recalc_progress()` | 可用 | Task 完成自动刷新 Goal 进度 |

### 2.3 记忆

| 能力 | 来源 | 可用性 | 说明 |
|------|------|--------|------|
| 长期记忆列表 | `/api/memories` | 可用 | 支持 `type/archived` 过滤 |
| 记忆图谱 | `/api/memories/graph` | 可用 | `nodes + edges`，供 World Model 2D 图 |
| 用户画像 | `/api/memory` | 可用 | profile + note_count + summary + reminders |
| 重要日期 | `/api/memory/important-dates` | 可用 | CRUD |
| 对话记忆 | `/api/memory/conversations` | 可用 | 历史对话摘要 |
| 语义查询 | `/api/memory/query` | 可用 | `memory_query.query_memory()` |
| 记忆压缩/蒸馏 | `memory.py` | 自动 | 对话超阈值自动压缩， distill learnings |

### 2.4 知识

| 能力 | 来源 | 可用性 | 说明 |
|------|------|--------|------|
| 知识文档列表 | `/api/knowledge` | 可用 | `docs + stats` |
| 文件型知识库 | `knowledge_runtime/` | 可用 | `list_docs/stats/search/resolve/related/ingest/delete` |
| 笔记系统 | `/api/notes` | 可用 | 列表/单条/图/标签/搜索/反向链接 |

### 2.5 工具与执行

| 能力 | 来源 | 可用性 | 说明 |
|------|------|--------|------|
| 工具注册表 | `/api/capabilities` | 可用 | `capabilities.capability_details()` |
| Function Calling 工具 | `tools.py` `TOOLS` | 可用 | 时间/计算/记忆/笔记/任务/文件/Shell/搜索/媒体等 |
| 执行策略/权限 | `ai_core.execution.policy` | 可用 | `ExecutionPolicy.evaluate/request_approval` |
| 电脑能力 | `capability_registry.py` | 可用 | `is_known/risk_of`，MEDIUM 需确认 |
| 审计日志 | `/api/audit` | 可用 | 工具调用审计 |

### 2.6 语音

| 能力 | 来源 | 可用性 | 说明 |
|------|------|--------|------|
| ASR 转写 | `/api/asr` | 门控 | 本地 FunASR 或云端；默认常不可用 |
| ASR 状态 | `/api/asr/status` | 可用 | 探测本地模型是否就绪 |
| 唤醒词 | `/api/wakeword` | 门控 | `XIAO6_KWS_ENABLED` 默认 `true`，但依赖 `openwakeword/sounddevice` |
| 唤醒事件 | SSE `wakeword_detected` | 可用 | `publish_system` 发出 |
| TTS | `/api/speak` | 可用 | edge-tts 合成 mp3 |
| 浏览器 STT 兜底 | `SpeechRecognition` | 可用 | 前端可直接用 |

### 2.7 世界模型 / 感知

| 能力 | 来源 | 可用性 | 说明 |
|------|------|--------|------|
| 世界观测事件 | `eventbus.DOMAIN_EVENT_NAMES` | 可用 | `COMPUTER_WORLD_SYNC/WINDOW_OPENED/APP_LAUNCHED/FILE_CREATED/PROJECT_DETECTED` 等 |
| 屏幕采集 | `SCREEN_CAPTURED` | 门控 | Phase 8，当前未真实运行 |
| 感知遥测 | `PERCEPTION_*` | 门控 | Phase 8 MVP |
| 记忆图谱 | `/api/memories/graph` | 可用 | 可替代 Galaxy 太阳系视觉 |

### 2.8 通信与实时推送

| 能力 | 来源 | 可用性 | 说明 |
|------|------|--------|------|
| SSE 流 | `/api/stream` | 可用 | EventBus 模式默认 ON，fallback SUBSCRIBERS |
| 事件总线 | `eventbus.py` | 可用 | topic pub/sub，domain/system 事件分离 |
| 领域事件 | `zz-events.js` ↔ `eventbus.DOMAIN_EVENT_NAMES` | 可用 | Goal/Agent/Task/Memory/Intent/Computer 生命周期 |
| 系统事件 | `zz-events.js.SYSTEM_EVENTS` | 可用 | proactive/scene/agent_state/modal/wakeword_detected 等 |
| 意图网关 | `/api/agent/intent` | 可用 | `intent_gateway.run_intent_gateway()` → Goal Decision Engine |
| 目标创建 | `/api/agent/goal` | runtime 开启后可用 | 直接 submit_goal |
| 审批 | `/api/agent/approval` | 可用 | Policy Engine 票据审批 |

### 2.9 主动智能 / 简报

| 能力 | 来源 | 可用性 | 说明 |
|------|------|--------|------|
| 每日简报 | `/api/briefing` | 可用 | 天气+热点+待办 |
| 主动消息 | SSE `proactive` | 可用 | `proactive.py` 推送 |
| 场景卡 | SSE `scene` | 可用 | `scene.py` 世界态势 |
| DND 状态 | `/api/proactive/status` | 可用 | 勿扰模式 |

### 2.10 系统与外部

| 能力 | 来源 | 可用性 | 说明 |
|------|------|--------|------|
| 系统状态 | `/api/sysmon` | 可用 | CPU/内存/磁盘等 |
| 日志 | `/api/logs` | 可用 | 最近日志 |
| 天气 | `/api/weather` | 可用 | wttr.in |
| 热点 | `/api/hotspots` | 可用 | 抖音/微博/微信/小红书 |
| 地理定位 | `/api/geo` | 可用 | IP 定位 |
| 多端协同 | `/api/devices` | 门控 | `FEATURE_MULTI_DEVICE` |
| 常驻伴随 | `/api/always-on/status` | 门控 | `FEATURE_ALWAYS_ON` |
| 应用焦点 | `/api/focus/app` | 门控 | `FEATURE_APP_FOCUS` |
| 剪贴板历史 | `/api/clipboard/history` | 门控 | `FEATURE_CLIPBOARD_SENSE` |

---

## 3. 前端共享库现状

| 模块 | 路径 | 状态 | 用途 |
|------|------|------|------|
| avatar-state.js | `xiao6-ui/avatar-state.js` | 稳定 | 8 态 META 颜色权威 |
| zz-events.js | `xiao6-ui/zz-events.js` | 稳定 | 单一事件名来源 |
| sse-manager.js | `xiao6-ui/sse-manager.js` | 稳定 | 全局 SSE 单例 |
| intent-gateway.js | `xiao6-ui/intent-gateway.js` | 稳定 | POST `/api/agent/intent` |

这些共享库必须在最终 UI 中只读复用，不可修改。

---

## 4. 关键约束（重建红线）

1. **不新增 Runtime**：不创建新的 Python 后端模块或事件。
2. **不绕过 EventBus**：所有实时状态变更必须经 SSE/EventBus 消费。
3. **不伪造数据**：UI 展示的数据必须来自真实 `/api/*` 或 SSE。
4. **不修改共享库**：`avatar-state.js` / `zz-events.js` / `sse-manager.js` / `intent-gateway.js` 只读引用。
5. **保留旧代码**：旧 `index.html` / `v4/` / `v5/` / `final/` 当前实现保留，新 UI 在独立目录重建。
6. **Feature 门控尊重**：Agent Runtime / ASR / KWS / 多端 / 焦点等能力需根据 `config` 开关优雅降级。

---

## 5. 对最终 UI 设计的影响

### 必须真实接入的 API
- 首屏：`/api/health` + `/api/hud/state` + `/api/agent/state`
- 上下文卡：`/api/memory` + `/api/tasks` + `/api/briefing`
- 能力触发：`/api/agent/intent`（唯一入口）
- 实时状态：SSE `/api/stream`（`agent_state` / `wakeword_detected` / 领域事件）
- Overlay 数据：
  - Memory: `/api/memories`, `/api/memories/graph`
  - Knowledge: `/api/knowledge`, `/api/notes/graph`
  - Goals: `/api/goals`, `/api/tasks`
  - World: `/api/memories/graph` + computer world events

### 需要被「隐藏式」呈现的能力
项目管理、知识管理、记忆系统、任务执行、文件操作、代码开发、系统控制、网络搜索、数据分析、设备控制、日程管理、自动化、语音交互、AI 对话、插件系统、设置配置。

这些能力不应以按钮卡片墙展示，而应通过：
- 自然语言 Intent Line 触发；
- 上下文卡中的动态文案暗示（"我可以帮你分析项目结构"）；
- ⌘1-5 Overlay 在需要时浮现；
- AI Core 状态变化时的微文案反馈。
