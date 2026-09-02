# 《Xiao6 v2 架构升级设计文档》

> 版本：v2 设计稿（草案，待评审）
> 角色：小6项目首席系统架构师（Chief AI Architect）
> 日期：2026-07-30
> 原则：**增量改造 · 低耦合 · 可维护 · 兼容已有 API 与数据库 · 不推翻已有系统**

---

## 0. 执行摘要（TL;DR）

小6 v1 已经是一个**功能完整、能跑**的本地个人 AI 副驾：六层模型、23 个工具、Function Calling 闭环、记忆压缩、ACI 预热、TICK 主动智能、3D 地球热榜、语音球、FunASR 本地转写、edge-tts 朗读、Electron 桌面壳等 34 项用户功能均已落地。

但 v1 的**架构骨架**是"单进程 + 全局可变 `config` + 手写 ReAct 循环 + 模块间直接函数互调"，缺少真正的 Agent Runtime、事件总线、世界模型、目标系统、用户模型、人格引擎、工作流与技能系统。这导致：

- `server.py`（1220 行）是事实上的 god-module，既管路由又管聊天运行时、TICK、TTS、调度；
- 运行时循环被劈成两半（`tools.run_fc_loop` 与 `server._handle_chat` 里的兜底/弹窗/压缩线程）；
- 上下文装配（`memory.build_context_prefix`）是手写硬编码链路，无法按 token 预算动态裁剪；
- 前端靠 `window.ZZ*` 全局对象做"伪事件总线"，`app.js` 是中心枢纽。

**v2 的目标**不是加功能数量，而是把这套能力**重构进一套可演进的 Agent OS 骨架**：引入 EventBus / Agent Runtime（Planner·Reasoning·Executor·Reflection）/ WorldModel / GoalSystem / UserModel / PersonalityEngine / ContextEngine / WorkflowEngine / SkillSystem，并将 `server.py` 拆为 `api/` 微服务式模块，同时补齐 CI/测试。

所有改造**保持 API 路径、数据库表、23 个工具行为、34 项用户功能全部向后兼容**。

---

## 1. 完整架构分析（v1 现状）

### 1.1 技术栈

| 层 | 实现 |
|---|---|
| 大脑 | `llm.py` 调 Agnes（`agnes-2.0-flash`）OpenAI 兼容 `/chat/completions`，带重试/最小间隔/代理降级 |
| 后端 | 纯标准库 `http.server` + `ThreadingHTTPServer`；`server.py` 1220 行 god-module |
| 数据 | SQLite（`db.py`，WAL 加固），单库 `xiao6.db` |
| 前端 | 原生 JS，部分 ES Module、部分经典 script；Three.js（vendor）用于 3D 地球与虚拟人 |
| 桌面 | **Electron 壳在仓库根 `G:/xiao6/electron/`（非 `xiao6-ui/`）**，拉起后端 + 托盘 + 单实例 + 原生桥 |

### 1.2 六层模型现状与偏差

理想六层：`LLM → Function Calling → Capability Registry → Tools → Memory → 主动智能`。
实际落地：**LLM 与 Tools 之间缺一个显式的"Agent Runtime"**——`run_fc_loop` 是简化 ReAct（LLM 自主选工具，最多 5 轮），无 Planner/Reasoning/Executor/Reflection 分层，无自我反思步骤（仅 `MAX_ROUNDS` 收尾）。"主动智能"（`proactive.tick_loop`）与"ACI 预热"（`prefetch`）是独立线程，与对话运行时通过全局队列/`SUBSCRIBERS` 与直接 import 耦合。

### 1.3 后端模块清单（实测行数）

| 文件 | 行 | 职责 | 关键依赖 |
|---|---|---|---|
| `server.py` | 1220 | HTTP 路由 + 聊天编排 + SSE + TTS + 进程内调度 | 几乎全部模块 |
| `tools.py` | 1294 | TOOLS 声明 / TOOL_FUNCS 注册 / `run_fc_loop` / 意图兜底 | config,asr,llm,media,memory,notes,sandbox,social,tasks |
| `geo_weather.py` | 658 | 定位采集 + 天气面板数据（IP/浏览器反查 + wttr+open-meteo） | config,http_client |
| `hotspots.py` | 595 | 实时热榜多源聚合 + 地域打点 + ACI 注入 | config,http_client |
| `notes.py` | 564 | 笔记 Vault / 画像 / 提醒 / 每日笔记 / 人物抽取 | db,llm |
| `sysmon.py` | 482 | 系统资源监控 + 服务端日志 | config |
| `db.py` | 448 | SQLite 数据层 + 建表 + 笔记/记忆/任务/审计 | config |
| `proactive.py` | 317 | TICK 心跳 + 预判注入 + 主动推送（SSE） | db,(lazy)hotspots,geo_weather |
| `config.py` | 293 | 全局配置单例 + `.env` 热更新 | 无 |
| `weather.py` | 206 | 天气 Provider（Open-Meteo 免密钥） | 无 |
| `self_check.py` | 213 | 启动自检（依赖/密钥/外部可达） | config |
| `tasks.py` | 201 | 多步任务（可续跑、重启恢复） | db |
| `capabilities.py` | 113 | 能力声明式注册表（仅 2 项，装饰性，未接入注入链） | (lazy)hotspots,prefetch |
| `prefetch.py` | 139 | ACI 预热缓存（天气/新闻 cron 落盘） | db |
| `memory.py` | 134 | 记忆压缩 + 上下文注入（`build_context_prefix`/`build_system_prompt`） | db,focus,geo_weather,llm,tasks |
| `focus.py` | 76 | 焦点栈（指代消解 + ACI 注入） | db |
| `asr.py` | 171 | FunASR 本地优先 + 云端兜底 | config |
| `sandbox.py` | 126 | 安全沙箱 + 工具审计（脱敏/危险命令） | config,db |
| `personalization.py` | 84 | 习惯画像（hints.json 计数） | 无 |
| `devices.py` | 80 | 跨设备脚手架（devices.json） | 无 |
| `message_processor.py` | 67 | 消息处理器面板数据 | db |
| `social.py` | 101 / `media.py` 106 / `worldcup.py` 119 / `http_client.py` 35 | 各自 Provider | config |

### 1.4 聊天请求链路（现状痛点集中处）

```
前端 /api/chat (SSE)
  → server._handle_chat()
      ├─ build_system_prompt()        # 手写拼装
      ├─ select_tools()               # 意图裁剪
      ├─ run_fc_loop()                 # tools.py：LLM↔工具 多轮 ReAct
      ├─ detect_intents()              # 正则兜底（LLM 没调工具时）
      ├─ 发射 modal.kind=hotspots      # 热点弹窗（硬编码在 server）
      ├─ compress_memory() 后台线程    # 记忆压缩
      ├─ extract_daily_note/profile/persons # 画像抽取
      ├─ personalization.record/summary
      ├─ import weather; weather._LAST=None  # 直接变异模块全局 ⚠
      └─ save_turn()                  # 落库
```

**问题**：Agent 运行时逻辑（兜底/弹窗/压缩/画像/个性化）散落在 `server.py`，与 HTTP/SSE 传输层强耦合，无法独立单测或复用。

### 1.5 前端架构

- ES Module：`main-orb.js`、`main-cognitive.js`、`hotspot.js`、`weather.js`、`sysmon.js`、`terminal-stream.js`、`world-clock.js`、`command-palette.js`、`memory.js`、`settings.js`、`sysprompt.js`
- 经典 script：`app.js`、`tasks.js`、`capabilities-view.js`、`china_regions.js`
- **耦合**：所有面板通过 `window.ZZ*`（ZZAvatar/ZZEarth/ZZModal/ZZTasks/ZZSysmon/ZZTerminal/ZZWorldClock/ZZSettings/ZZCognitiveFeed…）点对点调用；`app.js` 是中心枢纽。无真正发布订阅。

---

## 2. 发现的所有问题

| # | 问题 | 证据 | 严重度 |
|---|---|---|---|
| P1 | `server.py` god-module：路由 + 聊天运行时 + TICK + TTS + 调度全塞一处 | 1220 行；import 近全模块 | 高 |
| P2 | 运行时循环劈两半：`run_fc_loop` vs `_handle_chat` 兜底/弹窗/压缩线程 | 1.4 链路图 | 高 |
| P3 | 模块直接互调 + 全局变量变异：`weather._LAST`、`config` 全局单例原地改写 | server 直接 `import weather; _wmod._LAST=None` | 高 |
| P4 | 缺 EventBus：后端靠 `proactive.SUBSCRIBERS` 队列，前端靠 `window.ZZ*` | 无统一 pub/sub | 高 |
| P5 | 缺 ContextEngine：上下文手写硬编码，无法按 token 预算裁剪 | `build_context_prefix` 是手工链路 | 高 |
| P6 | 缺 WorldModel：定位/天气/焦点/记忆各自孤立，无统一世界状态 | 散落模块全局 | 中 |
| P7 | 缺 GoalSystem：`tasks.py` 是线性任务，非目标驱动 | 无目标分解/达成判定 | 中 |
| P8 | 缺 UserModel：profile 表 + habits.json + extract_profile 三处分散 | 无统一用户模型 | 中 |
| P9 | 缺 PersonalityEngine：仅 `config.SYSTEM_PROMPT` 名字替换 | 无人格参数/状态 | 低 |
| P10 | 缺 Workflow / Skill 系统：任务是顺序步骤，无 DAG/分支/技能生命周期 | 无 workflow/skills 目录 | 中 |
| P11 | 常量/逻辑重复：`PLATFORM_LABELS` 三处；ACI 注入在 `memory` 与 `capabilities` 重复 | hotspots/tools/server 各定义 | 低 |
| P12 | 安全风险：`do_GET` 末尾对未知路径直接 `_serve_file`（潜在任意文件读取），与 `sandbox.py` 解耦 | server.py 路由尾 | 中 |
| P13 | 测试/CI 缺失：仅 `tests/` 5 文件 + 无 GitHub Actions；managed venv 未装 pytest | 仅本地历史 62 用例 | 中 |
| P14 | 前端桥脆弱：ES Module 顶层函数不挂 window 则跨脚本不可达（历史踩坑） | MEMORY 记录 | 中 |

> 注：Electron 桌面壳**确实存在**（仓库根 `electron/`），但 `/api/external` 返回的 `desktop.built` 是静态声明，需在 v2 验收时实测原生桥是否真正打通（不视为已完备）。

---

## 3. 优化方案（总览）

### 3.1 设计原则

1. **不推翻**：所有 `/api/*` 路径、SQLite 表、`TOOLS` 行为、34 项功能保持不变。
2. **先解耦后增强**：先落地 EventBus / WorldModel / ContextEngine / Server 模块化（地基），再上 Agent Runtime / Goal / UserModel / Personality（智能层），最后 Workflow / Skill / CI（生态层）。
3. **配置注入化**：`config` 全局单例改为可注入的 `ConfigService`，消除原地改写。
4. **事件驱动**：模块间禁止直接互调，统一走 EventBus。
5. **新增库独立**：`goals.db`、`user_profile.db` 为新建独立库，绝不改动 `xiao6.db` 现有表。

### 3.2 目标架构（v2 分层）

```
┌─────────────────────────────────────────────────────────────┐
│  入口层：server.py（极薄启动器） → api/*（路由委托）          │
├─────────────────────────────────────────────────────────────┤
│  Agent Runtime（agent/）                                    │
│    Planner → Reasoning → Executor → Reflection → Reply      │
│    （取代手写 run_fc_loop + server 兜底，统一闭环）           │
├──────────────┬──────────────┬──────────────┬───────────────┤
│ Capability   │  Workflow     │  Skill        │  Tool Registry│
│ Registry     │  Engine       │  System       │ (23 工具重注册)│
├──────────────┴──────────────┴──────────────┴───────────────┤
│  ContextEngine（动态拼 Prompt，token 预算裁剪）              │
│    ← WorldModel + GoalSystem + UserModel + Personality        │
│    ← Memory(已有) + 最近聊天 + Tool 状态                     │
├─────────────────────────────────────────────────────────────┤
│  EventBus（所有模块解耦的公共脊柱）                          │
├─────────────────────────────────────────────────────────────┤
│  Memory(已有) · goals.db(新) · user_profile.db(新) · SQLite  │
└─────────────────────────────────────────────────────────────┘
        ↑ TICK/主动智能、前端 SSE 均改为订阅 EventBus 事件
```

### 3.3 核心抽象与 12 目标映射

| 目标 | 新增模块 | 落地方式 |
|---|---|---|
| 1 Agent Runtime | `agent/{runtime,planner,reasoning,executor,reflection}.py` | 抽离 `server._handle_chat` 运行时逻辑 |
| 2 Goal System | `goals/{manager,db,models}.py` + `goals.db` | 新增独立库，不碰 xiao6.db |
| 3 World Model | `world_state.py` | 聚合时间/天气/位置/系统/Git/项目/网络/作息 |
| 4 Context Engine | `context_engine.py` | 取代手写 `build_context_prefix`，按 16/32/64/96K 裁剪 |
| 5 Event Bus | `eventbus.py` | 取代 `SUBSCRIBERS` 与 `window.ZZ*` |
| 6 Reflection | `agent/reflection.py` | 每轮结束产出 `ReflectionResult` |
| 7 User Model | `user_model.py` + `user_profile.db` | 合并 profile 表 + habits + extract_* |
| 8 Personality | `personality.py` | 人格参数动态注入 |
| 9 Workflow | `workflow/{engine,loader,steps}.py` + yaml | DAG/Condition/Loop/Retry/Timeout |
| 10 Skill | `skills/{registry,loader}.py` + `skills/builtin/` | Prompt+Workflow+Memory+Goal+Tools 包 |
| 11 Server 模块化 | `api/{chat,memory,settings,tools,system,notification,static}.py` | server.py 仅启动 + 委托 |
| 12 工程质量 | `.github/workflows/ci.yml` + `pyproject.toml` 扩展 | pytest/coverage/ruff/black/mypy/perf |

---

## 4. 升级路线图（Phase 1 / 2 / 3）

> 每步均含：**为什么改 / 影响文件 / 新增文件 / 兼容点 / 风险 / Rollback**。

### Phase 1 — 地基解耦（让一切可插拔）

**Step 1.1 引入 EventBus**
- 为什么：P4 根因，所有后续模块（Goal/World/Reflection/通知）都依赖它解耦。
- 新增：`eventbus.py`（sync + async pub/sub，`subscribe(topic, cb)` / `publish(topic, payload)`，内置默认线程池）。
- 影响：无（纯新增，零侵入）。
- 兼容：不影响任何现有 API/DB。
- 风险：低。异步派发若阻塞需限流。
- Rollback：删除 `eventbus.py` 即可，无引用。

**Step 1.2 WorldModel（`world_state.py`）**
- 为什么：P6，把散落的天气/位置/系统/Git/项目/网络/作息聚成统一世界状态，供 ContextEngine 注入。
- 新增：`world_state.py`（采集器 + 缓存 + `snapshot()`），并把 `weather._LAST` 等模块全局态迁移进 WorldModel。
- 影响：`geo_weather.py`（只读其输出）、`sysmon.py`、`proactive.py`（改为读 WorldModel）。
- 兼容：`server` 仍调原 `/api/weather` 等，内部数据来源不变。
- 风险：中（迁移全局态需小心 `server` 现有 `import weather; _LAST=None` 调用点）。
- Rollback：保留旧全局态读取分支，feature flag 切换。

**Step 1.3 ContextEngine 重构上下文装配**
- 为什么：P5，取代手写 `memory.build_context_prefix`，支持 token 预算与重要度排序。
- 新增：`context_engine.py`（TokenBudget + 排序器 + 动态组装），保留 `build_system_prompt` 作为兼容门面。
- 影响：`memory.py`（删硬编码链路，改调 ContextEngine）、`server._handle_chat`（改为调 ContextEngine）。
- 兼容：`/api/system-prompt` 输出结构不变。
- 风险：中（上下文质量回归需 A/B 验证）。
- Rollback：保留 `build_context_prefix` 旧函数，开关切换。

**Step 1.4 Server 模块化（`api/`）**
- 为什么：P1，拆 1220 行 god-module，API 完全兼容。
- 新增：`api/{chat,memory,settings,tools,system,notification,static}.py`；`server.py` 瘦身为启动器 + 路由委托。
- 影响：`server.py` 大改但**仅内部转发**；所有 `/api/*` 路径与响应体不变。
- 兼容：全部 HTTP 契约不变（前端零改动）。
- 风险：高（路由重构易漏），须逐端点 curl 回归（历史教训：`do_GET` 的 `qs` 共享变量曾导致 500）。
- Rollback：保留 `server.py` 旧版副本，一键还原。

**Step 1.5 ConfigService 注入化**
- 为什么：P3，消除 `config` 全局单例原地改写。
- 新增：`config.py` 内 `ConfigService` 类（读取 `.env` 返回不可变快照 + 订阅变更事件）。
- 影响：各模块 `import config; config.X` 改为 `config.get("X")` 或通过构造注入。
- 兼容：`.env` 字段名不变；`update_env_file` 行为不变。
- 风险：中（改动面大，需逐模块替换）。
- Rollback：保留模块级变量，双轨并存过渡。

### Phase 2 — 智能层（Agent Runtime + Goal + User + Personality）

**Step 2.1 Agent Runtime（agent/）**
- 为什么：目标 1 + P2，把运行时从 `server` 与 `tools` 中抽离为四段式闭环。
- 新增：`agent/runtime.py`、`planner.py`、`reasoning.py`、`executor.py`、`reflection.py`、`types.py`。
- 影响：`tools.run_fc_loop` 收敛为 `executor` 内部；`server._handle_chat` 改为调 `AgentRuntime.run(turn)`。
- 兼容：聊天 SSE 事件格式（`tool_start/tool_end/xiao6_event`）保持不变。
- 风险：高（核心闭环改写）。
- Rollback：保留 `run_fc_loop`，runtime 与旧循环双跑对照。

**Step 2.2 Goal System（goals/ + goals.db）**
- 为什么：目标 2，让 Agent 每轮考虑长期/短期目标。
- 新增：`goals/manager.py`、`goals/db.py`、`goals/models.py`，独立 `goals.db`。
- 影响：无现有表改动；`AgentRuntime` 每轮读 GoalManager 注入 ContextEngine。
- 兼容：`xiao6.db` 完全不动。
- 风险：低（纯新增库）。
- Rollback：删除 goals 目录即可。

**Step 2.3 User Model（user_model.py + user_profile.db）**
- 为什么：目标 7 + P8，合并三处分散的用户画像。
- 新增：`user_model.py`（confidence/last_update/source/importance + 自动遗忘/更新），独立 `user_profile.db`。
- 影响：`personalization.py`、`notes.extract_profile/persons` 改为写入 UserModel。
- 兼容：旧 `habits.json` / `profile` 表仍可读取做迁移。
- 风险：中（迁移既有画像数据）。
- Rollback：旧写入路径保留，双写过渡。

**Step 2.4 Personality Engine（personality.py）**
- 为什么：目标 8，人格参数动态生成。
- 新增：`personality.py`（专业度/主动度/解释长度/严肃度/技术深度 → 每轮拼 Prompt）。
- 影响：`config.SYSTEM_PROMPT` 模板改为由 Personality 驱动。
- 兼容：默认参数 = 当前行为，无感切换。
- 风险：低。
- Rollback：回退到固定模板。

### Phase 3 — 生态层（Workflow + Skill + 工程化）

**Step 3.1 Workflow Engine（workflow/）**
- 为什么：目标 9，支持 DAG/Condition/Loop/Retry/Timeout，落地 daily_review/git_summary/project_scan/meeting_summary。
- 新增：`workflow/{engine,loader,steps}.py` + `workflow/workflows/*.yaml`。
- 影响：无现有功能改动；可由命令面板或 TICK 触发。
- 兼容：纯新增能力。
- 风险：中（yaml 执行引擎安全沙箱）。
- Rollback：不启用 workflow 路由即可。

**Step 3.2 Skill System（skills/）**
- 为什么：目标 10，把"能力"升级为可安装技能包（Prompt+Workflow+Memory+Goal+Tools）。
- 新增：`skills/{registry,loader}.py` + `skills/builtin/{unity,python,ai,pixelart,gamedev}/`。
- 影响：`capabilities.py` 演进为 Skill 注册表的视图层；23 工具重注册到 Skill 体系（行为不变）。
- 兼容：工具 name/参数/返回不变。
- 风险：中（技能加载隔离）。
- Rollback：保留旧 `capabilities.py`。

**Step 3.3 工程质量（CI + 测试）**
- 为什么：目标 12 + P13。
- 新增：`.github/workflows/ci.yml`（pytest + coverage + ruff + black + mypy + 性能基准）；`tests/` 扩充（eventbus/context_engine/agent_runtime 单测）；`pyproject.toml` 加 coverage/perf 配置。
- 影响：无运行时改动。
- 兼容：本地 lint 门禁已存在（PR-1.5），CI 仅自动化它。
- 风险：低。
- Rollback：移除 workflow 文件。

---

## 5. 新目录结构（xiao6-ui 目标态）

```
xiao6-ui/
├── server.py                 # 极薄：启动 ThreadingHTTPServer + 委托 api/
├── api/                      # 新增：server.py 拆分（API 兼容）
│   ├── __init__.py
│   ├── chat.py               # _handle_chat → AgentRuntime.run
│   ├── memory.py             # /api/memories, /api/notes
│   ├── settings.py           # /api/config, /api/alert-config
│   ├── tools.py              # /api/models, /api/test-llm, 工具分发
│   ├── system.py             # /api/health, /api/selfcheck, /api/system-prompt, /api/capabilities
│   ├── notification.py       # /api/stream (SSE) + 主动推送
│   └── static.py             # /static + 沙箱化文件服务（修 P12）
├── agent/                    # 新增：Agent Runtime（目标 1）
│   ├── __init__.py
│   ├── runtime.py            # 编排 Planner→Reasoning→Executor→Reflection
│   ├── planner.py            # 目标拆解
│   ├── reasoning.py          # 思考 / 决策
│   ├── executor.py           # 执行（含 run_fc_loop 收敛）
│   ├── reflection.py         # 复盘 → ReflectionResult（目标 6）
│   └── types.py              # Plan / Step / ReflectionResult
├── eventbus.py               # 新增：事件总线（目标 5）
├── world_state.py            # 新增：世界模型（目标 3）
├── context_engine.py         # 新增：上下文引擎（目标 4）
├── user_model.py             # 新增：用户模型（目标 7, +user_profile.db）
├── personality.py            # 新增：人格引擎（目标 8）
├── goals/                    # 新增：目标系统（目标 2）
│   ├── manager.py            # GoalManager
│   ├── db.py                 # goals.db schema/migration
│   └── models.py             # Goal / 优先级 / 截止 / 状态
├── workflow/                 # 新增：工作流引擎（目标 9）
│   ├── engine.py
│   ├── loader.py             # yaml 加载
│   ├── steps.py              # Condition/Loop/Retry/Timeout/Tool/LLM/Memory
│   └── workflows/
│       ├── daily_review.yaml
│       ├── git_summary.yaml
│       ├── project_scan.yaml
│       └── meeting_summary.yaml
├── skills/                   # 新增：技能系统（目标 10）
│   ├── registry.py
│   ├── loader.py
│   └── builtin/
│       ├── unity/  python/  ai/  pixelart/  gamedev/
├── tools.py                  # 瘦身：保留 TOOLS/TOOL_FUNCS（行为不变）
├── llm.py  memory.py  db.py  config.py  capabilities.py
├── geo_weather.py  hotspots.py  notes.py  sysmon.py  proactive.py
├── prefetch.py  focus.py  asr.py  sandbox.py  personalization.py
├── devices.py  media.py  social.py  worldcup.py  http_client.py
├── message_processor.py  self_check.py  weather.py  tasks.py
├── data/                     # xiao6.db（不动）+ goals.db + user_profile.db（新）
├── tests/                    # 扩充单测（eventbus/context_engine/agent_runtime…）
├── app.js  styles.css  index.html  main-orb.js  hotspot.js  weather.js …
└── vendor/three/
```

> 仓库根 `electron/` 保持不变；`server._handle_external` 的 `desktop` 声明需在 v2 验收时实测原生桥。

---

## 6. 新增模块职责详述

- **`eventbus.py`**：统一发布订阅。Topics 含 `ConversationStarted/Finished`、`GoalUpdated`、`MemoryUpdated`、`WeatherUpdated`、`ToolFinished`、`TaskCreated/Completed`、`WorldStateChanged`、`PersonalityChanged`。支持 sync/async 订阅者，内置线程池避免阻塞发布者。取代 `proactive.SUBSCRIBERS` 与前端 `window.ZZ*`。
- **`agent/runtime.py`**：`AgentRuntime.run(turn)` 编排 `Planner.plan → Reasoning.decide → Executor.execute → Reflection.reflect → Reply`；产出标准 SSE 事件流，向后兼容现有 `tool_start/tool_end/xiao6_event`。
- **`agent/planner.py`**：把用户目标/请求拆解为有序 Plan（Step 列表），可调用 GoalManager 关联长期目标。
- **`agent/reasoning.py`**：负责"思考"——决定下一步调用哪些工具、是否需要追问、是否达终态。
- **`agent/executor.py`**：执行 Plan Step，内部收敛现有 `run_fc_loop`（只读工具并行、写操作串行），统一 emit SSE。
- **`agent/reflection.py`**：每轮结束分析工具是否失败、回答是否完整、是否需学习/记忆/更新 Goal，输出 `ReflectionResult` 并写回 Memory/Goal/UserModel。
- **`world_state.py`**：维护时间/日期/天气/位置/CPU/GPU/内存/运行软件/Git 状态/当前项目/网络/设备/工作·休息时间；`snapshot()` 供 ContextEngine 注入；取代 `weather._LAST` 等模块全局态。
- **`context_engine.py`**：Token 预算（16K/32K/64K/96K 自动裁剪）+ 重要度排序，动态拼装 System Prompt（Goal + Memory + 最近聊天 + WorldState + UserModel + Personality + Tool 状态），取代手写 `build_context_prefix`。
- **`goals/manager.py`**：长期/短期目标、截止时间、优先级、完成状态、自动关联任务；每轮对话经 ContextEngine 注入。
- **`user_model.py`**：工作/开发习惯、常用软件、偏好、项目、联系人、兴趣、学习方向；每条记录带 confidence/last_update/source/importance；支持自动遗忘（低 confidence+久未更新）与自动更新。
- **`personality.py`**：专业程度/主动程度/解释长度/严肃程度/技术深度 五维参数，每轮动态生成人格 Prompt。
- **`workflow/engine.py`**：解析 yaml 工作流，支持 Condition/Loop/Retry/Timeout 与 Tool/LLM/Memory 节点；沙箱化执行。
- **`skills/registry.py`**：技能生命周期（注册/发现/加载/版本），技能 = Prompt+Workflow+Memory+Goal+Tools 组合包。
- **`api/*`**：纯路由委托层，每个文件对应一组 `/api/*` 端点，逻辑转发到对应领域模块；`static.py` 加沙箱限制修 P12 任意文件读取。

---

## 7. 兼容性分析

| 维度 | 兼容性保证 |
|---|---|
| **HTTP API** | 所有 `/api/*` 路径与响应体**完全不变**；`server.py` 仅改为委托 `api/`，前端零改动。 |
| **数据库** | `xiao6.db` 现有表（memories/notes/tasks/audit/prefetch_cache…）**不改动**；`goals.db`、`user_profile.db` 为新建独立库。 |
| **23 个工具** | name/parameters/返回结构不变；仅注册位置从 `tools.TOOL_FUNCS` 迁移到 Skill/Registry 体系（行为等价）。 |
| **前端** | `window.ZZ*` 桥保留兼容别名，逐步被 EventBus 客户端订阅替代；语音球/地球/面板行为不变。 |
| **Electron** | 桌面壳（`electron/`）继续拉起后端，API 契约不变即天然兼容。 |
| **TICK/主动智能** | `proactive.tick_loop` 改为订阅 EventBus 事件驱动，对外 SSE 推送格式不变。 |
| **配置** | `.env` 字段名不变；`update_env_file` 行为不变；ConfigService 仅改变内部读取方式。 |

---

## 8. 风险评估

| 风险 | 等级 | 缓解 |
|---|---|---|
| 核心闭环改写（AgentRuntime 取代 run_fc_loop）引入对话回归 | 高 | 双跑对照 + 端到端 e2e 脚本（已有 `e2e_*.py`）逐轮比对 |
| Server 模块化路由漏端点（历史 500 教训） | 高 | 逐端点 curl 回归清单 + CI 冒烟测试 |
| ConfigService 注入改造面大 | 中 | 双轨并存过渡，逐模块替换 |
| EventBus 异步派发阻塞/丢失 | 中 | 内置线程池 + 失败重试 + 关键事件持久化 |
| 上下文质量回归（ContextEngine 裁剪） | 中 | 保留旧 `build_context_prefix` 开关对照 + token 预算默认值保守 |
| DB 迁移既有画像/习惯数据 | 中 | 双写 + 只读旧源做回退 |
| Workflow yaml 执行安全 | 中 | 复用 `sandbox.py` 审计 + 禁用危险节点 |
| CI 首次接入耗时 | 低 | 复用已落地的 ruff/black/mypy 配置 |

---

## 9. 工作量评估（粗略，单开发视角）

| 阶段 | 模块 | 估时 |
|---|---|---|
| P1 | EventBus | 1 d |
| P1 | WorldModel | 2 d |
| P1 | ContextEngine | 3 d |
| P1 | Server 模块化 | 4 d |
| P1 | ConfigService | 2 d |
| P2 | Agent Runtime | 5 d |
| P2 | Goal System | 2 d |
| P2 | User Model | 2 d |
| P2 | Personality Engine | 1 d |
| P3 | Workflow Engine | 4 d |
| P3 | Skill System | 3 d |
| P3 | CI/测试 | 2 d |
| — | 联调/回归/e2e | 5 d |
| **合计** | | **~36 人·天** |

> 可并行：P1.1 EventBus 与 P1.2 WorldModel 可并行；P2.2/2.3/2.4 可并行；P3.1/3.2 可并行。压缩后关键路径约 5–6 周。

---

## 10. 功能保全清单（34 项，v2 全部保留）

> 升级**不遗漏任何已有功能**，下列每项在 v2 中由对应模块承载，行为不变：

1. 聊天多轮（SSE + 记忆压缩 + 系统提示拼装）→ `api/chat` + `agent` + `context_engine`
2. 图像多模态输入 → `agent/executor`（vision content 注入）
3. 实时搜索兜底（Bing/Baidu/DDG + 可选 key）→ `tools.web_search`（重注册）
4. 语音球（点阵/Three.js 虚拟人）→ 前端 `main-orb`/`avatar`，桥保留
5. FunASR 本地转写（`/api/asr`、`/api/transcribe`）→ `asr.py` 不变
6. edge-tts 朗读（`/api/speak`）→ `api/notification` 或保持 `server` 委托
7. 音视频字幕 → `asr.transcribe_bytes`
8. 媒体生成（MiniMax）→ `media.py`
9. 所在地定位（`/api/geo`、`/api/geo/reverse`）→ `geo_weather` + WorldModel
10. 天气面板（3/7 天/AQI/指数）→ `weather`/`geo_weather` + WorldModel
11. 热点看板 + 3D 地球热榜 → `hotspot.js` + `hotspots.py`
12. 聚合热点弹窗 SSE 推送 → EventBus `HotspotsPushed` → 前端
13. TICK 主动智能推送 → `proactive` 改订阅 EventBus
14. ACI 预热缓存 → `prefetch` + ContextEngine 注入
15. 舆情告警（`/api/alert-config`）→ `proactive` + 设置面板
16. 记忆节点图（`/api/memories/graph`）→ `memory` + `api/memory`
17. 笔记 Vault（`/api/notes`）→ `notes` + `api/memory`
18. 每日笔记自动抽取 → `notes.extract_daily_note`
19. 用户画像/人物抽取 → 并入 `user_model.py`
20. 个性化习惯画像 → `user_model.py`（原有 habits 迁移）
21. 任务弹窗（`/api/tasks`，可续跑/重启恢复）→ `tasks` + `api/*`
22. 跨设备脚手架（`/api/devices`）→ `devices.py`
23. 能力清单面板（`/api/capabilities`）→ `capabilities` → Skill 视图层
24. 认知界面（`main-cognitive.js`）→ 订阅 EventBus 认知流
25. 自检页（`/api/health`、`selfcheck.html`）→ `api/system`
26. 设置面板（`/api/config`）→ `api/settings` + ConfigService
27. 系统监控面板（`/api/sysmon`）→ `sysmon` + WorldModel
28. 终端日志流（`/api/logs`）→ `api/notification` 或 `system`
29. 世界时钟（`world-clock.js`）→ 纯前端
30. 系统提示词预览（`/api/system-prompt`）→ `api/system` + ContextEngine
31. 模型列表/连通测试（`/api/models`、`/api/test-llm`）→ `api/tools`
32. 世界杯/赛事面板（`/api/worldcup`）→ `worldcup` + dashboard 聚合
33. 社交推送（`social.py`）→ 经 EventBus 触发
34. 安全沙箱 + 工具审计（`sandbox.py` + `tool_audit`）→ 不变，Workflow 复用

---

## 11. 结论与下一步

小6 v1 是"功能完备但骨架偏过程式"的系统。v2 不追求功能数量增长，而是通过 **EventBus 解耦 + Agent Runtime 分层 + World/Goal/User/Personality 模型 + ContextEngine 动态拼装 + Workflow/Skill 生态 + Server 模块化 + CI 工程化**，把它演进为真正可长期生长的 **Personal AI Operating System**。

建议评审顺序：**先确认 Phase 1（地基）范围与 `server.py` 模块化切分粒度** → 再启动 Phase 2 智能层 → 最后 Phase 3 生态与工程化。每一 Phase 内按 Step 的"为什么/影响/新增/兼容/风险/Rollback"逐条落地，保证全程可回退、零功能回归。

**本设计为草案，待你（老板）评审拍板后，我再进入 Plan/实施模式按 Phase 逐步进码。**
