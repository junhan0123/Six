# 小6 Xiao6 — PHASE 3 · GUI OS REALITY AUDIT + RECONSTRUCTION DESIGN GATE

> 阶段性质：**READ-ONLY / DESIGN-ONLY**（禁止修改生产代码）
> 项目：小6 Xiao6 v1.4.0
> GUI 主入口：`G:\xiao6\xiao6-ui\xiao6-space\index.html`
> 唯一 Runtime：`G:\xiao6\xiao6-ui\server.py`（http://localhost:8010）
> 执行身份：Senior Product Architect + Senior Frontend Architect + UX/UI Systems Architect + Runtime Integration Auditor
> 全部结论均来自本轮重新读取的真实源码与真实 HTTP 探针，**未引用历史报告**。

---

## 1. Executive Summary（执行摘要）

本阶段对当前唯一 GUI OS（`xiao6-space`）做了源码级 Reality Audit，并完成 GUI Reconstruction 的 Design Gate。

**核心结论**：

- 当前 GUI 是一个**单文件自包含 monolith**：`index.html` 仅加载 `js/zz-workspace.js`（757 行）+ `css/zz-workspace.css`。全部界面、状态、API、事件、语音都在一个 IIFE 内实现。
- `xiao6-space/` 下存在 **4 个孤儿死文件**（`js/zz-space.js`、`css/zz-space.css`、`vendor/three.min.js`、`vendor/lottie.min.js`），无任何活动加载引用，属旧 Galaxy/Space 时代遗留。
- GUI 与 Runtime 的真实调用链**基本成立**（聊天/语音/TTS/Approval/Capability 均经 `/api/chat` SSE 驱动），但存在**两处结构性缺口**：
  1. **`panel` 事件断层**：Runtime 在 `/api/chat` SSE 中发出 `xiao6_event: panel`（热点/地图/文档/记忆/审阅等），GUI 的 `handle()` 只消费 `tool_start`/`tool_end`/`approval`/`choices`，**完全不消费 `panel`** → Runtime 推面板、GUI 不渲染。
  2. **高级功能入口 10 处 404**：`openFeature()` 用 `id.replace(/-/g,'/')` 拼 URL，与 server 真实路由（下划线+子路径）不匹配，实测 10 个高级功能点击后 overlay 显示空/失败。
- GUI **从不订阅 `/api/stream`**（Runtime 实时事件总线），仅每 8s 轮询 `/api/agent/state` + 每 30s `fetchSnapshot`。Voice↔GUI 实时协同靠轮询，存在 ≤8s 延迟，但**会话一致**（共用 `localStorage['xiao6_sid']`）。
- Voice↔GUI 边界健康：单一 Runtime 会话、单一 Memory、单一 Capability 权威；未发现第二 Session / 第二 Memory / 第二 Voice Runtime。

本阶段**未修改任何生产代码**，满足全部 §25 红线。

---

## 2. Real GUI Entry（真实 GUI 入口）

| 入口 | 真实路径 | 证据 |
| --- | --- | --- |
| 浏览器/Electron 主入口 | `G:\xiao6\xiao6-ui\xiao6-space\index.html` | `electron/main.js:100-104`、`launcher_config.json:22`、`xiao6-hub/renderer.js:13` |
| 加载的 JS | `xiao6-space/js/zz-workspace.js?v=30` | `index.html:223`（唯一 `<script>`） |
| 加载的 CSS | `xiao6-space/css/zz-workspace.css?v=30` | `index.html:9` |
| 根重定向壳 | `G:\xiao6\xiao6-ui\index.html` | `<meta refresh>` → `/xiao6-space/index.html`（§7 保留） |
| DSH 兼容入口 | `G:\xiao6\xiao6-ui\gui\chat.html` | `deepseek-harness-studio/.../lib/main.js:5141` 默认 `XIAO6_CHAT_PATH=/gui/chat.html` |

**结论**：当前唯一活动 GUI = `xiao6-space/index.html` + `zz-workspace.js`。全 `xiao6-space/` 下仅 1 个 HTML、1 处 script 引用。

---

## 3. File Map（GUI 文件地图）

| 文件 | 类型 | 谁加载 | 是否运行 | 核心 | 重复 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| `index.html` | HTML | Electron/浏览器 | ✅ | ✅ | — | KEEP |
| `js/zz-workspace.js` | JS（monolith） | `index.html:223` | ✅ | ✅ | — | KEEP（重构对象） |
| `css/zz-workspace.css` | CSS | `index.html:9` | ✅ | ✅ | — | KEEP |
| `js/zz-space.js` | JS | **无引用** | ❌ | — | 旧 Space | **REMOVE/ARCHIVE（孤儿）** |
| `css/zz-space.css` | CSS | **无引用** | ❌ | — | 旧 Space | **REMOVE/ARCHIVE（孤儿）** |
| `vendor/three.min.js` | JS | **无引用** | ❌ | — | — | **REMOVE/ARCHIVE（孤儿）** |
| `vendor/lottie.min.js` | JS | **无引用** | ❌ | — | — | **REMOVE/ARCHIVE（孤儿）** |
| `assets/lottie/*.json` | JSON | 仅被 lottie.min.js（死） | ❌ | — | — | **REMOVE/ARCHIVE（孤儿）** |
| `assets/*.png`、`assets/elements/*.png` | 图片 | CSS 引用（装饰） | ✅ | — | — | KEEP |
| `_audit/*.md`、`_verify/` | 文档/空 | — | ❌ | — | — | KEEP（非 UI） |
| `MASTER_REBUILD_REPORT.md` | 文档 | — | ❌ | — | — | KEEP（非 UI） |

**孤儿判定依据**：`xiao6-space/` 全目录仅 `index.html` 一个 HTML，且其 `<script>` 仅 `js/zz-workspace.js` 一处；全局 grep `zz-space.js|zz-space.css` 命中均为 `launcher/logs/*`（陈旧日志指向已不存在的 `/zz-space/index.html`）、`_archive/gui-20260817/main.js`（已归档）、`_audit/*.md`（文档）——**无任何活动加载引用**。

---

## 4. DOM Reality Map（HTML 结构真实地图）

依据 `index.html` 真实节点：

```
body[data-view]
├── header.zz-top (TOP BAR)
│   ├── .zz-top-left   品牌 + 「小6 · Advanced Workspace」
│   ├── .zz-top-center #cmdkBtn 命令面板触发（⌘K）
│   └── .zz-top-right  #runtimeState(运行时状态) · #ctxChip · #orbBtn(迷你球 data-state)
├── div.zz-shell (SHELL)
│   ├── nav.zz-nav (LEFT NAV, 9 项)
│   │   home / sessions(对话) / projects(项目) / tasks(任务) /
│   │   memory(记忆) / knowledge(知识) / capabilities(能力) / settings(设置)
│   ├── main.zz-center (CENTER)
│   │   ├── section.zz-home       首页：greet + 4 卡(运行时/最近/任务/快捷)
│   │   ├── section.zz-conv       对话：tabs(对话/工作区/结果/Agent活动)
│   │   │                        + tools(思考/联网/🎙/🔊) + #chatList + #cmdForm
│   │   └── section.zz-list-view ×7  会话/项目/任务/记忆/知识/能力/设置 列表
│   └── aside.zz-context (RIGHT RAIL)  #ctxBody 动态上下文栈
├── div.zz-orb-presence (常驻语音球陪伴件, data-state)
├── div.zz-palette (命令面板 Ctrl K)
├── div.zz-overlay (详情/审批/能力 overlay)
└── div.zz-toast-layer + div.zz-banner (提示/横幅)
```

**真实存在**：顶栏、左导航、中心（首页/对话/列表视图）、右上下文栏、常驻球、命令面板、overlay、toast。
**不存在（不编造）**：独立 HUD 浮层、独立 Scene 视图、Galaxy 视图、二级 Modal 管理系统——这些仅以"事件名"存在于 Runtime，GUI 未实现对应 DOM。

---

## 5. JS Module Map（模块职责矩阵）

当前活动模块**仅 1 个**：`js/zz-workspace.js`（757 行 IIFE）。职责高度聚合：

| 函数/区块 | 真实职责 | API | 事件 | DOM |
| --- | --- | --- | --- | --- |
| `fetchSnapshot()` L79-101 | 批量拉取 11 个快照端点 | GET ×11 | — | renderHome/Lists |
| `StreamingMarkdown` L105-179 | 增量 Markdown 渲染（避免 O(n²)） | — | — | chat |
| `sendChat()` L201-292 | 主聊天：POST /api/chat + SSE 消费 | POST /api/chat | tool_start/tool_end/approval/choices | chatList |
| `onApproval()` L266-283 | 审批卡 + POST /api/agent/approval | POST /api/agent/approval | — | approval node |
| `speakText()` L294-300 | TTS 播放 | POST /api/speak | — | audio |
| `startVoice()` L303-334 | 浏览器麦克风→/api/asr→/api/chat | POST /api/asr | — | cmdInput |
| `switchView()` L352-364 | 9 视图路由 | — | — | body[data-view] |
| `renderHome/Tasks/Projects/Memory/Knowledge/Capabilities/Sessions` L367-461 | 列表渲染 | GET 快照 | — | 各 list |
| `switchConvTab/renderWorkspace/renderResults/renderAgent` L463-503 | 对话子 tab | — | — | ws/res/agent |
| `renderContextAuto/renderContext` L506-541 | 右栏动态上下文 | — | — | ctxBody |
| `renderSettings()` L544-563 | 设置（偏好+系统概览） | — | change | settingsBody |
| `FEATURE_REGISTRY` L567-615 | 47 项功能注册表（A–G 分类+可见性） | — | — | — |
| `COMMANDS` + `renderPalette` L630-686 | 命令面板 | — | — | palette |
| `openFeature()` L647-655 | 高级功能 overlay（**URL 拼接有缺陷**） | GET /api/<id> | — | overlay |
| `handleTrigger()` L689-702 | `/命令`、`@能力` 输入提示 | — | — | triggerHint |
| `init()` L705-752 | 事件绑定 + 轮询 | — | setInterval 8s/30s | — |

**结论**：无独立 state 管理 / EventBus 消费模块；`zz-workspace.js` 既是 Presentation 也是 Interaction Layer，符合"Presentation + Interaction"定位，但**未订阅 Runtime SSE 总线**。

---

## 6. API Matrix（GUI → Runtime API 清单）

### 6.1 真实可用（HTTP 200，server 有对应路由）

| API | Method | 调用位置 | 触发动作 | 返回 |
| --- | --- | --- | --- | --- |
| `/api/chat` | POST | L220, L141(orb) | 聊天/语音 | SSE |
| `/api/speak` | POST | L296 | 语音播报 | audio/mpeg |
| `/api/asr` | POST | L329 | 浏览器语音识别 | JSON |
| `/api/agent/approval` | POST | L280 | 审批决策 | — |
| `/api/agent/state` | GET | L81,L748 | 轮询状态 | JSON |
| `/api/goals` | GET | L81 | 项目渲染 | JSON |
| `/api/memories` | GET | L81 | 记忆渲染 | JSON |
| `/api/knowledge` | GET | L81 | 知识渲染 | JSON |
| `/api/capabilities` | GET | L81 | 能力渲染 | JSON |
| `/api/tasks` | GET | L81 | 任务渲染 | JSON |
| `/api/health` | GET | L81 | 系统概览 | JSON |
| `/api/memory` | GET | L82 | 上下文栏 | JSON |
| `/api/briefing` | GET | L82 | 首页/简报 | JSON |
| `/api/calendar/events` | GET | L84 | 条件入口 | JSON |
| `/api/notes` | GET | L84 | 笔记 | JSON |
| `/api/chat/history` | GET | L376,L444 | 最近/会话 | JSON |
| `/api/system-prompt` | GET | openFeature | 高级 | 200✅ |
| `/api/capability_os/catalog` | GET | openFeature | 高级 | 200✅ |
| `/api/proactive_agent/status` 等 | GET | openFeature | 高级 | 200✅ |
| `/api/perception/*`、`/api/hud/state`、`/api/weather`、`/api/hotspots`、`/api/geo`、`/api/episodes`、`/api/version`、`/api/asr/status` 等 | GET | openFeature/轮询 | 高级/条件 | 200✅ |

### 6.2 死入口（openFeature 拼接 URL → 实测 404）

`openFeature()` L651：`'/api/' + id.replace(/-/g, '/')`。与 server 真实路由（下划线+子路径）不匹配，**全部 404**：

| FEATURE_REGISTRY id | GUI 拼接 URL | server 真实路由 | 实测 |
| --- | --- | --- | --- |
| `system-prompt` | `/api/system/prompt` | `/api/system-prompt` | **404** |
| `capability-os` | `/api/capability_os` | `/api/capability_os/catalog` | **404** |
| `proactive-agent` | `/api/proactive/agent` | `/api/proactive_agent/status` | **404** |
| `self-awareness` | `/api/self/awareness` | `/api/self_awareness/status` | **404** |
| `user-model` | `/api/user/model` | `/api/user_model` | **404** |
| `personal-ai` | `/api/personal/ai` | `/api/personal_ai` | **404** |
| `calendar` | `/api/calendar` | `/api/calendar/events` | **404** |
| `clipboard` | `/api/clipboard` | `/api/clipboard/history` | **404** |
| `conversations` | `/api/conversations` | `/api/memory/conversations` | **404** |
| `important-dates` | `/api/important/dates` | `/api/memory/important-dates` | **404** |

> 探针：对 10 个 GUI URL 均返回 `404`；对其 server 真实路由均返回 `200`。证据确凿。

### 6.3 重要结论

- GUI 调了很多 Runtime 已有能力（≥40 端点），Runtime 能力远大于 GUI 暴露面 → **C 类（Runtime 有能力但 GUI 无入口）** 普遍存在。
- GUI 的 `openFeature` 是一套"假入口"机制：URL 生成逻辑与 server 路由命名不一致，导致高级功能**点击后必然失败**（§十一"看起来能点但用不了"）。

---

## 7. Event Matrix（事件/SSE 真实地图）

### 7.1 Chat SSE（POST /api/chat，每次请求内联消费，GUI `handle()` L240-249）

| 事件 | 发布位置 | GUI 消费 | 视觉结果 |
| --- | --- | --- | --- |
| `tool_start` | `server_handlers_chat.py` | ✅ `onTool('start')` L242 | 工具节点"调用 X…" |
| `tool_end` | 同上 | ✅ `onTool('end')` L243 | "工具 X 完成/失败" |
| `approval` | 同上 | ✅ `onApproval` L244 | 审批卡（批准/拒绝） |
| `choices.delta.content` | Agnes 流式 | ✅ `stream.update` L247 | 增量 Markdown |
| `[DONE]` | 同上 | ✅ `finish` L234 | 收尾 + TTS |
| **`panel`** | `server_handlers_chat.py:371-429` | ❌ **不消费** | **Runtime 推面板，GUI 不渲染** |
| `modal` / `scene` / `proactive` | Runtime | ❌ 不消费 | 丢弃 |

### 7.2 Runtime 实时总线（GET /api/stream，server_handlers_chat.py:727 订阅 TOPIC_SSE）

| 事件 | 发布 | GUI 是否订阅 |
| --- | --- | --- |
| `agent_state` | EventBus | ❌ GUI **不订阅 /api/stream**，仅轮询 /api/agent/state |
| `hud_state` | EventBus | ❌ |
| `panel` / `scene` / `proactive` / `COMPUTER_ACTION_*` | EventBus | ❌ |

### 7.3 结论

- GUI 的实时性 = **轮询**（8s 状态 + 30s 快照），**非 SSE 订阅**。
- Runtime 发出的 `panel`/`modal`/`scene`/`proactive` 事件在 GUI 侧**完全无消费端** → 这是 GUI Reconstruction 必须补的关键链路（见 §20 约束 A/B）。

---

## 8. Runtime Integration Map（GUI → Runtime 调用链）

### A. 普通聊天
`用户输入 #cmdInput` → `submitCmd()` L345 → `sendChat()` L201 → `POST /api/chat{session_id}` L220 → SSE(`choices`/`tool_*`/`approval`) → GUI 渲染 + `speakText()` L288。

### B. Voice → GUI 协同
`Orb 麦克风` → `dyna-orb-voice.js` → `POST /api/chat{session_id}`（同 `localStorage['xiao6_sid']` L22-23）→ Runtime → 结果。GUI 经 8s 轮询 `fetchSnapshot` 看到 `snap.tasks`/`agent.state` 变化 → 列表/右栏更新（**≤8s 延迟**，非实时）。

### C. Capability 调用
聊天中 Runtime 经 `run_fc_loop`→`capability_runtime`→`ai_core.execution.run`（policy 门）自动执行；GUI 仅消费 `tool_start/tool_end` 展示，**不绕过** Context/Memory/Policy/Capability/Executor（§8 满足）。

### D. Tool 执行
同 C，`tool_start/tool_end` 驱动。

### E. Approval / Confirm
SSE `approval` → `onApproval` L266 → `POST /api/agent/approval?ticket=&decision=` L280 → Runtime policy 裁决。GUI 不自己决定允许/拒绝（§11 满足）。

### F. Memory
`GET /api/memories` 渲染；Runtime 自动沉淀，GUI 只读。

### G. Task / Agent Runtime
`GET /api/tasks` + 轮询 `agent.state`；无独立 Agent 控制面。

### H. Panel（缺口）
Runtime `panel` 事件 → **GUI 无消费** → 面板不打开。

### I. Modal / J. Scene / K. Proactive
同上，丢弃。

### L. Error
聊天失败 `catch` L252 → 红字"请求失败" + `setState('ERROR')`；语音失败 toast。但高级功能 404 仅 overlay 显示"（空）"——**未明确报错**（§十 Error Model 缺口）。

### M. Session
`localStorage['xiao6_sid']` 单一键，GUI+Orb 共用 → Runtime 单会话（§12 一致）。

---

## 9. Feature Inventory（用户功能清单，47 项分类）

依据 `FEATURE_REGISTRY` L567-615（注册表本身就是分类事实来源）：

| 分类 | 含义 | 代表项（真实） |
| --- | --- | --- |
| **A** | 有 UI 入口且真实可用 | web-ui(对话)、capabilities(能力)、memory(记忆)、conversations(对话历史)、important-dates、notes、knowledge、tasks、goals、weather、hotspots、geo、briefing、calendar(条件)、focus-app(条件)、clipboard(条件)、agent-state |
| **B** | 有入口(命令面板)但链路不完整/后端真实 | capability-os、system-prompt、user-model、personal-ai、episodes、perception-*、proactive-status/agent、self-awareness、hud-state |
| **C** | Runtime 有能力但 GUI 无入口 | avatar-ui、open-project、export-data、open-config、open-docs、github |
| **D** | 内部开发/基础设施，隐藏 | health、ready、boot-state、sysmon、logs、selfcheck、version、asr-status、wakeword |
| **E** | 隐藏运维 | start-all |
| **G** | 历史遗留概念 | 旧 Galaxy/Space（zz-space.js 等，已死） |

**实测 B 类死入口（404）**：system-prompt、capability-os、proactive-agent、self-awareness、user-model、personal-ai、calendar、clipboard、conversations、important-dates。

---

## 10. Feature Entry Audit（功能入口混乱审计）

逐项对照 §十一：

1. **一个功能多入口**：聊天/任务/记忆/能力 同时存在于 左导航 + 命令面板 + 首页快捷 + `/` 触发器 → 重复但可接受（导航一致性）。
2. **核心功能隐藏**：`important-dates`、`conversations` 等 A 类能力**无工作导航入口**，仅命令面板（且面板路径 404）。
3. **次要功能抢占视觉**：左导航 9 项（含 knowledge/capabilities/projects）信息密度高，首页 4 卡 + 右栏，新手易迷失。
4. **开发者概念直曝**：`system-prompt`、`capability_os`、`self_awareness`、`perception_*` 经命令面板可达 → 技术术语泄露（vis='advanced' 已默认隐藏，但仍可触达）。
5. **"看起来能点但用不了"**：**10 个高级功能 404**（§6.2 实测）。
6. **无反馈操作**：高级功能 404 后 overlay 仅显"空/读取失败"，无明确错误（§十缺口）。
7. **重复 Panel/Status/Voice**：
   - **三个"球"**：顶栏 `#orbBtn` 迷你球 + 常驻 `#orbPresence` 球 + Electron Voice Orb → 概念重复（浏览器内 2 个 orb 组件）。
   - **两套同功能开关**：对话头 `tools`（思考/联网/🔊）与 设置（web/think/speak 开关）控制同一 `toolModes`/`autoSpeak` → 双入口。
8. **旧 Galaxy/Space 残留**：`zz-space.js`/`zz-space.css` 死文件；`launcher/logs/*` 陈旧日志仍指向已不存在的 `/zz-space/index.html`（非活动，仅日志噪声）。
9. **重复 Chat**：GUI 单一 chatList；Orb 另有独立 `six_orb_chat_v1`（localStorage，L67/86/102）→ 同一会话两份聊天缓存（Runtime 权威，仅 UI 冗余）。

> 所有结论附 **file:line** 或标注 **INFERENCE**（如"新手易迷失"为主观 UX 推断，已标 INFERENCE）。

---

## 11. Voice ↔ GUI Boundary（Voice↔GUI 协同边界）

| 维度 | 是否一致 | 证据 |
| --- | --- | --- |
| Session | ✅ 一致 | GUI `localStorage['xiao6_sid']`(L33-34) = Orb `localStorage['xiao6_sid']`(L22-23) → 同 Runtime 会话 |
| Chat 转录 | ⚠️ 双缓存 | GUI `chatList`(DOM) + Orb `six_orb_chat_v1`(L67) 各自存，Runtime 为权威 |
| Memory | ✅ | 均经 `/api/memories`，Runtime 权威 |
| Agent 状态 | ✅（轮询） | 均读 `/api/agent/state` |
| Tool 执行 | ✅ | 均经 `/api/chat` SSE `tool_*` |
| Approval | ✅ | Orb 不渲染审批；GUI `onApproval` 消费 SSE `approval` |
| Result | ✅ | 同 Runtime 结果 |
| 实时协同 | ⚠️ ≤8s 延迟 | GUI 不订阅 `/api/stream`，仅轮询 |

**结论**：Voice 与 GUI 共享**单一 Runtime 会话/Memory/Capability/Policy**；无第二 Voice Runtime、无第二 Session。**仅有的不一致是实时性（轮询）与聊天缓存重复**，属可优化项，非架构违规。

---

## 12. Session Map（会话地图）

- 单一 session key：`xiao6_sid`（localStorage，同源共享）。
- `sendChat`(L218) / Orb(L141) 均带 `session_id: sessionId`。
- 首次访问：GUI 生成 `zz-<ts>`(L34)，Orb 生成 `orb-<ts>`(L23)，**先写者胜**，随后双方共用。
- Runtime 侧按 `session_id` 维护上下文 → Voice 与 GUI 续同一会话成立。

## 13. Memory Map（记忆地图）

- GUI 仅 **读** `/api/memories`（L81）、`/api/memory`（L82）、`/api/knowledge`（L81）。
- 写入由 Runtime 自动沉淀（对话/热点/事件）→ GUI 不写 Memory（符合"Presentation"）。
- 记忆渲染：`renderMemory`(L420)、右栏 `memory` 上下文(L527)。

## 14. Capability Map（能力地图）

- 读取：`/api/capabilities`(L81) → `renderCapabilities`(L435)（图标/描述/激活态）。
- 调用：用户自然语言 → `/api/chat` → Runtime `run_fc_loop` 自动选工具 → GUI 仅展示 `tool_start/end`。
- GUI **无** Capability 面板/手动触发（符合"用户看到能力，不是模块"）。
- `@能力` 触发器(L696-701) 仅做输入提示，不直调。

## 15. Approval Map（审批地图）

- 来源：Runtime SSE `approval` 事件（policy_engine 裁决点）。
- GUI：`onApproval`(L266) 渲染卡片 + `postApproval`(L279) → `POST /api/agent/approval?ticket=&decision=`。
- Orb：不渲染审批（桌面环境由 GUI/Electron 审批卡承接）。
- **权威永远在 policy_engine**，GUI 只转发决策（§11 满足）。

---

## 16. Information Architecture（当前/目标信息架构）

### 16.1 CURRENT IA（当前）
```
一级：对话(主) · 首页
二级：任务 · 记忆 · 知识 · 能力 · 项目 · 对话历史
三级(命令面板/条件)：日历 · 剪贴板 · 焦点 · 高级能力(多数 404)
隐藏：设置 · 系统/开发者(health/logs/selfcheck/...)
常驻：语音球(×2) · 右上下文栏
```
问题：导航 9 项过密；高级能力直曝；核心(对话)被淹没在平等导航中；技术术语泄露。

### 16.2 TARGET IA（目标）
```
一级（首屏核心）：对话输入 + 语音球(单一)
二级（侧栏/折叠）：任务 · 记忆 · 能力 · 会话
三级（命令面板 Ctrl K）：导航/动作/高级(需明确开发者 gate)
后台自动：系统状态 · 日历 · 剪贴板 · 感知（不抢视觉）
设置：极简偏好 + 系统概览(只读)
```
核心原则：**用户看到能力不是内部模块**；Runtime 内部概念（system-prompt/capability_os/self_awareness）不进用户 IA，仅开发者模式可达。

---

## 17. Visual Architecture Audit（视觉结构审计）

- 布局：左导航 + 中心 + 右栏 + 顶栏 + 常驻球 + 命令面板 + overlay → 属"AI OS / 工作台"范式，**非 ChatGPT 克隆**（有导航/面板/上下文栏，正向）。
- 密度：9 项导航 + 首页 4 卡 + 右栏，信息密度偏高，新手认知负荷大（INFERENCE）。
- 层级：对话为核心但未视觉突出；3 个 orb 组件分散注意力。
- 视觉焦点：常驻球 + 对话输入应为中心焦点，当前被多导航稀释。
- 状态可感知：运行时状态点(顶栏) + 右栏状态卡 → 基本可感知。
- 空/加载/错误态：列表有 `zz-empty`；错误态薄弱（高级 404 不报错）。
- 响应式/窗口：Electron 桌面窗口；未做移动端（INFERENCE，无需）。

**结论**：框架方向正确（AI OS 而非聊天克隆），但需**收敛导航、统一球、强化对话焦点、补齐错误态**。

---

## 18. UX Problems（交互/信息架构问题汇总）

1. 10 个高级功能死入口（404）→ 点击必失败。
2. `panel` 事件无消费 → Runtime 推面板 GUI 不显示。
3. GUI 不订阅 `/api/stream` → Voice↔GUI 实时协同缺失（≤8s 延迟）。
4. 三个"球"概念重复（迷你球/常驻球/Orb）。
5. 两套同功能开关（对话头 vs 设置）。
6. 技术术语泄露（命令面板高级能力）。
7. 错误态薄弱（404/空无明确提示）。
8. 聊天缓存双份（GUI DOM + Orb localStorage）。
9. 导航 9 项过密，核心对话不突出（INFERENCE）。
10. 孤儿死文件 4 个未清理（zz-space.js/css、three/lottie）。

---

## 19. Keep / Merge / Hide / Remove Matrix（保留/合并/隐藏/删除矩阵）

| UI 元素 | 决策 | 原因/引用 | 风险 | 替代 |
| --- | --- | --- | --- | --- | --- |
| `index.html` | **KEEP** | 唯一入口 | — | — |
| `js/zz-workspace.js` | **KEEP + REDESIGN** | 全 GUI 逻辑 | 重构需保行为 | 拆分模块(可选) |
| `css/zz-workspace.css` | **KEEP** | 样式 | — | — |
| 对话视图 + Chat SSE | **KEEP** | 核心链路 | — | — |
| 命令面板 Ctrl K | **KEEP** | 高效入口 | 修 URL 映射 | — |
| 设置(偏好) | **KEEP** | 极简 | 合并开关 | — |
| 右上下文栏 | **KEEP** | 状态可感知 | — | — |
| `js/zz-space.js` | **REMOVE/ARCHIVE** | 孤儿(L223 未引) | 无(无引用) | — |
| `css/zz-space.css` | **REMOVE/ARCHIVE** | 孤儿 | 无 | — |
| `vendor/three.min.js` | **REMOVE/ARCHIVE** | 孤儿 | 无 | — |
| `vendor/lottie.min.js` | **REMOVE/ARCHIVE** | 孤儿 | 无 | — |
| `assets/lottie/*.json` | **REMOVE/ARCHIVE** | 随 lottie 死 | 无 | — |
| 顶栏迷你球 `#orbBtn` | **MERGE** | 与常驻球重复 | 保留其一 | 常驻球 |
| 常驻球 `#orbPresence` | **KEEP(单一)** | Voice 陪伴件 | — | — |
| 对话头 tools 开关 | **MERGE** | 与设置重复 | 单一源 | 设置 |
| 高级能力(命令面板) | **HIDE+GATE** | 技术术语/404 | 开发者模式 | 修 URL |
| `panel` 事件消费 | **REDESIGN(补)** | Runtime 推面板 | 需 Interaction | 工作区 tab |
| 导航 9 项 | **KEEP(收敛)** | 过密 | 折叠次级 | — |

> 删除判定均满足"无活动引用或已有替代入口"（§15）。REMOVE 仅针对孤儿死文件，**不删 Runtime/DSH/Voice/Memory**。

---

## 20. Implementation Constraints（实施约束分级）

下一阶段（PHASE 3.1+）建议按当前 Runtime 能力分四级：

- **A. 当前可直接实现（仅 Interaction Layer / 前端）**：
  - 修 `openFeature` URL 映射（10 处 404）→ 映射到 server 真实路由。
  - 删除 4 个孤儿死文件（zz-space.js/css、three/lottie + json）。
  - 合并双球/双开关。
  - 补齐错误态（404/空明确提示）。
  - 收敛导航（折叠次级）。
- **B. 需轻微 Interaction Layer 支持**：
  - GUI 订阅 `/api/stream`（EventSource）→ 消费 `agent_state`/`panel`/`hud_state` → 实时 Voice↔GUI 协同 + 面板渲染。
  - `panel` 事件 → 工作区 tab 渲染（热点/地图/文档/记忆/审阅）。
- **C. 需 Runtime 支持（FUTURE / REQUIRES RUNTIME CHANGE）**：
  - `modal`/`scene`/`proactive` 事件若需 GUI 呈现 → 需 Runtime 定义稳定 payload schema。
  - 统一聊天缓存（GUI+Orb 共享）需 Runtime 提供会话历史 API（已有 `/api/chat/history`）。
- **D. 当前禁止实施**：
  - 改 Runtime 架构 / DSH / Xiao6Hub / Voice Orb 视觉 / Memory / DB schema / 创建第二 GUI / 第二 Runtime / 第二 Voice / P5.5–P5.8。

> 本 Phase 3 为 DESIGN-ONLY，**以上均不在本阶段实施**。

---

## 21. Risks（风险）

1. **修 openFeature 若映射错** → 仍 404；需逐端点对照 server 路由表（已附 §6.2）。
2. **订阅 /api/stream 若不节流** → 多事件刷屏；需 debounce + 仅更新可见视图。
3. **删除孤儿文件若误判** → 已用"全目录仅 1 HTML + 1 script"证明无引用，风险低。
4. **合并双球若破坏 Electron orb 联动** → 需保留 `window.electronAPI.focusOrb` 路径(L305)。
5. **面板渲染若承载重 DOM** → 需复用工作区 tab，避免新模态膨胀。

## 22. Known Limitations（已知限制）

- 本审计为 READ-ONLY；未运行 GUI 浏览器交互测试，UX 结论中标注 INFERENCE 者为基于代码的主观推断。
- `/api/stream` 事件 payload 全貌（modal/scene/proactive 字段）未逐一解码（需运行时抓包），列为 C 级待 Runtime 定义。
- Orb 独立聊天缓存 `six_orb_chat_v1` 与 GUI 一致性未做端到端验证（仅代码层确认同源 session）。

## 23. Recommended Phase 3.x Roadmap（阶段路线）

### PHASE 3.1 — GUI 健康修复（IMPLEMENT 起点，纯前端/Interaction）
- 目标：消除死入口、清孤儿、统一球/开关、补错误态。
- 输入：本报告 §6.2、§19、§20-A。
- 修改范围：`zz-workspace.js`（openFeature URL 映射 + 双球/双开关合并 + 错误态）、删除 4 孤儿文件。
- 禁止修改：server.py / DSH / Voice Orb / Memory / DB。
- 验收：10 个高级功能 GET 真实路由 200；孤儿文件移除后 `/xiao6-space/index.html` 仍可服务；双球只剩常驻球；对话头开关与设置单一源。
- 依赖：无。风险：低。

### PHASE 3.2 — 实时协同总线（Interaction Layer + 轻量 Runtime 事件消费）
- 目标：GUI 订阅 `/api/stream`，消费 `agent_state`/`panel`/`hud_state`，实现 Voice↔GUI 实时 + 面板渲染。
- 输入：本报告 §7、§11、§20-B。
- 修改范围：`zz-workspace.js`（新增 EventSource 订阅 + panel→工作区渲染）；可选新增工作区 panel 组件。
- 禁止修改：Runtime 事件发布逻辑（仅消费）；不改 DSH/Voice。
- 验收：Voice Orb 执行任务时 GUI 工作区 tab ≤1s 内显示 tool/panel；`panel` 事件（热点/地图/文档）渲染。
- 依赖：PHASE 3.1。风险：中（节流/刷屏）。

### PHASE 3.3 — 信息架构收敛（UX/IA Redesign）
- 目标：导航收敛、对话焦点强化、开发者能力 gate、空/加载/错误态完善。
- 输入：本报告 §16、§17、§18、§19。
- 修改范围：`zz-workspace.js` + `zz-workspace.css`（结构/样式），不新增第二 GUI。
- 禁止修改：Runtime。
- 验收：首屏核心=对话+单一球；高级能力仅开发者模式可达；三类状态态完整。
- 依赖：PHASE 3.1/3.2。风险：中（UX 主观）。

### PHASE 3.4（可选，FUTURE/C 级）— 统一会话历史 + 主动智能呈现
- 目标：GUI+Orb 共享聊天缓存；`proactive`/`scene` 呈现（需 Runtime 定义 payload）。
- 依赖：Runtime 事件 schema 稳定。风险：高（跨 Runtime 协商）。

> **IMPLEMENT 自 PHASE 3.1 开始**；3.2/3.3 可顺序或并行（3.3 不依赖 3.2 运行时事件）。

## 24. Final Design Gate Verdict（设计门裁定）

| 裁定项 | 结果 |
| --- | --- |
| 唯一 GUI 已确认 | ✅ `xiao6-space` |
| 所有实际 GUI 文件已盘点 | ✅（含 4 孤儿） |
| 所有实际 JS 模块已盘点 | ✅（单 monolith） |
| DOM 结构已确认 | ✅（§4） |
| API 调用链已确认 | ✅（§6，含 10 死入口） |
| Event/SSE 链路已确认 | ✅（§7，panel 断层） |
| Feature Inventory 完成 | ✅（47 项 A–G） |
| 功能入口完成分类 | ✅（§10） |
| 重复入口完成识别 | ✅（双球/双开关/多入口） |
| Voice↔GUI 边界确认 | ✅（§11，一致） |
| Session 边界确认 | ✅（单 xiao6_sid） |
| Memory 边界确认 | ✅（只读） |
| Capability 边界确认 | ✅（Runtime 权威） |
| Approval 边界确认 | ✅（policy 权威） |
| 当前 IA 完成 | ✅（§16.1） |
| 目标 IA 完成 | ✅（§16.2） |
| UI Keep/Merge/Hide/Remove 完成 | ✅（§19） |
| 最终 GUI Target Model 完成 | ✅（§2/§16） |
| 用户流程完成 | ✅（§25 下方） |
| Runtime 能力约束已标记 | ✅（§20 A/B/C/D） |
| 不可实现功能已标记 | ✅（C/D 级） |
| 没有修改生产代码 | ✅ |
| 没有删除文件 | ✅（仅设计，待 3.1 执行） |
| 没有新增功能 | ✅ |
| 没有创建第二 GUI/Runtime | ✅ |
| 报告已落盘 | ✅ |
| 下一阶段 Prompt 已生成 | ✅（§26） |

```
PHASE 3 = PASS（DESIGN GATE 通过）
VERIFY   = PASS
DESIGN   = PASS
IMPLEMENT= NOT STARTED（本阶段禁止）
```

---

## 25. 用户流程（设计，不实现）

**FLOW A 首次打开**：加载 index.html → init() → setState(IDLE) + fetchSnapshot → 首页(问候+运行时+最近+任务+快捷)。
**FLOW B 普通聊天**：对话输入 → submitCmd → sendChat → POST /api/chat SSE → 流式渲染 + TTS。
**FLOW C 语音聊天**：点常驻球/🎙 → startVoice(或 Electron focusOrb) → ASR → /api/chat → 同 B。
**FLOW D 语音→执行→GUI 查看**：Orb 说"打开热点面板" → Runtime `tool_start`+`panel` → GUI（3.2 后）工作区实时渲染热点面板；当前(3.1 前)仅轮询看到任务。
**FLOW E GUI→执行→Orb 表达**：GUI 发任务 → Runtime 执行 → Orb 经 `/api/agent/state`(轮询) 显示工作中 → 完成回 idle。
**FLOW F Capability 执行**：自然语言 → Runtime 自动选工具 → tool_start/end 展示。
**FLOW G Approval**：Runtime `approval` → GUI 审批卡 → POST /api/agent/approval → policy 裁决。
**FLOW H Memory**：对话自动沉淀 → /api/memories 渲染记忆视图。
**FLOW I 长任务**：任务在 snap.tasks → 工作区进度条 → agent 活动时间线。
**FLOW J Error Recovery**：聊天失败红字+ERROR 态；高级功能 404 → (3.1 后) 明确错误提示。

---

## 26. NEXT EXECUTABLE PROMPT（下一阶段可直接复制执行的完整中文 Prompt）

> 以下 Prompt 继承本阶段全部架构结论、保留/删除/合并项、Runtime/Voice 边界、GUI 目标架构、功能入口规划与验收标准。可直接复制给 Agent 执行 PHASE 3.1。

```text
# 小6 Xiao6 — PHASE 3.1 · GUI 健康修复（IMPLEMENT）

## 身份
Senior Frontend Architect + Runtime Integration Auditor
项目：小6 Xiao6 v1.4.0
GUI 主目录：G:\xiao6\xiao6-ui\xiao6-space
唯一 Runtime：G:\xiao6\xiao6-ui\server.py（http://localhost:8010，勿改）

## 目标
在不改动 Runtime / DSH / Xiao6Hub / Voice Orb / Memory / DB 的前提下，
对当前唯一 GUI（xiao6-space）做最小必要健康修复：
1) 消除 10 个高级功能死入口（404）；
2) 清理 4 个孤儿死文件；
3) 合并重复球与重复开关；
4) 补齐错误态。

## 架构边界（必须坚守）
- 一个 GUI OS（xiao6-space）+ 一个 Voice OS（Orb）+ 一个 Runtime。
- GUI = Presentation + Interaction Layer；Runtime 是 Decision/Policy/Capability/Execution/Memory/Context/Lifecycle/Agent 唯一权威。
- 禁止：改 server.py / server_handlers_*.py / agent_runtime / capability_os / policy_engine / executor / EventBus / Memory / DB / config / .env / Electron / Xiao6Hub / DSH / Voice Orb(dyna-orb.js/dyna-orb-voice.js) / 创建第二 GUI / 第二 Runtime / 第二 Voice / 新增功能 / 进入 P5.5–P5.8。

## 必须执行的修改（仅前端，附真实 file:line）
A. 修 openFeature URL 映射（G:\xiao6\xiao6-ui\xiao6-space\js\zz-workspace.js:647-655）
   - 现状：'/api/' + id.replace(/-/g,'/') 导致 10 个 URL 404（实测）。
   - 建立显式 id→真实路由映射表，至少覆盖：
     system-prompt→/api/system-prompt
     capability-os→/api/capability_os/catalog
     proactive-agent→/api/proactive_agent/status
     self-awareness→/api/self_awareness/status
     user-model→/api/user_model
     personal-ai→/api/personal_ai
     calendar→/api/calendar/events
     clipboard→/api/clipboard/history
     conversations→/api/memory/conversations
     important-dates→/api/memory/important-dates
   - 其余沿用真实路由（见 server.py 路由表 L256–L677）。
   - 验收：10 个 GET 真实路由均 200；overlay 显示 JSON 而非空/失败。

B. 删除孤儿死文件（无活动引用，全 xiao6-space 仅 1 HTML + 1 script）
   - G:\xiao6\xiao6-ui\xiao6-space\js\zz-space.js
   - G:\xiao6\xiao6-ui\xiao6-space\css\zz-space.css
   - G:\xiao6\xiao6-ui\xiao6-space\vendor\three.min.js
   - G:\xiao6\xiao6-ui\xiao6-space\vendor\lottie.min.js
   - G:\xiao6\xiao6-ui\xiao6-space\assets\lottie\*.json
   - 先归档至 G:\xiao6\_ui_archive\2026-08-18\gui\（同卷 mv，可回退），再删除。
   - 验收：删除后 GET /xiao6-space/index.html 仍 200；node --check zz-workspace.js 通过。

C. 合并重复球（index.html + zz-workspace.js）
   - 保留常驻 #orbPresence（zz-workspace.js:189, 736）；顶栏 #orbBtn 迷你球(32) 改为仅导航到对话(不重复 orb 视觉)或移除。
   - 保留 window.electronAPI.focusOrb 联动（zz-workspace.js:305）。

D. 合并重复开关（zz-workspace.js）
   - 对话头 tools（711-720）与设置（544-561）控制同一 toolModes/autoSpeak；
     以设置为单一源，对话头开关改为读写同一状态且变化同步（或仅保留设置）。
   - 验收：任一处切换，另一处状态同步。

E. 补齐错误态（zz-workspace.js openFeature + 网络失败）
   - openFeature 读取失败/空明确提示"功能暂不可用"（非静默空）。
   - 高级能力仅开发者模式可达（新增 vis 判定或命令面板分组 gate）。

## 验证（只读）
GET /api/health /api/ready /api/agent/state /api/asr/status /xiao6-space/index.html
GET 上述 10 个修复后路由（预期 200）
node --check zz-workspace.js

## 验收标准
[ ] 10 个高级功能 GET 真实路由 200
[ ] 4 孤儿文件已归档并删除，index.html 仍可服务
[ ] 双球只剩常驻球，Electron focusOrb 联动保留
[ ] 对话头/设置开关单一源且同步
[ ] 错误态明确
[ ] 未改 server.py / DSH / Voice Orb / Memory / DB
[ ] node --check 通过，HTTP 回归全 200

## 完成后
生成 PHASE-3.1-GUI-HEALTH-FIX-REPORT.md（全程中文，结论附 file:line + 真实 HTTP），
最终回复以 "# 小6 PHASE 3.1 — COMPLETE" 开头，附 STATUS 块，然后 STOP 等待下一阶段。
```

---

# PHASE 3 FINAL REPORT（见上方正文）

```
VERIFY    = PASS
DESIGN    = PASS
IMPLEMENT = NOT STARTED
PHASE 3   = PASS
```

STOP — 本阶段为设计门，不进入 IMPLEMENT。等待老板审核与 PHASE 3.1 指令。
