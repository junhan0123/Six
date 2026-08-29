# Xiao6 v2 — Phase 1 实施分析（仅分析与设计，未改代码）

> 角色：Chief AI Architect + Principal Software Engineer + Senior Python Engineer
> 阶段：Phase 1 基础设施搭建（Context Engine / World Model / Agent Runtime 骨架）
> 约束：不增加功能、不重构现有逻辑、完全向后兼容、所有改动可 Rollback、禁止 God File
> 配套规范：《Xiao6 v2 核心架构规范》（已冻结，本文档严格遵守）

---

## ① 项目扫描（Phase 1 相关模块现状）

### 1.1 聊天相关核心文件

| 文件 | 行数(约) | 与聊天/上下文相关职责 |
|---|---|---|
| `server.py` | 1220 | HTTP 路由 + `_handle_chat` 编排 + SSE + TTS + 进程内调度 |
| `tools.py` | 1294 | `TOOLS`/`TOOL_FUNCS` 注册、`run_fc_loop`、`select_tools`、`detect_intents` |
| `memory.py` | 134 | `build_system_prompt` / `build_context_prefix` / `build_memory_block` / `compress_memory` |
| `config.py` | 293 | `SYSTEM_PROMPT`、`AI_DISPLAY_NAME` 全局单例 |
| `geo_weather.py` | 658 | `get_geo` / `get_weather` / `build_geo_block`（定位+天气） |
| `hotspots.py` | 595 | `get_hotspots` / `build_hotspot_context` / `archive_mentioned_hotspots` |
| `prefetch.py` | 139 | ACI 预热缓存（`format_prefetched_items` / `get_valid_prefetch`） |
| `focus.py` | 76 | `recent_foci`（焦点栈） |
| `tasks.py` | 201 | `get_open_tasks`（未完成任务） |
| `personalization.py` | 84 | `record` / `summary`（习惯画像） |
| `weather.py` | 206 | `last_weather()` / `_LAST` 模块全局态 |
| `sysmon.py` | 482 | 系统资源（CPU/GPU/内存/日志） |
| `devices.py` | 80 | 跨设备列表 |
| `proactive.py` | 317 | TICK 主动智能（独立线程，暂不在 Phase 1 改动） |
| `db.py` | 448 | `reminders` / `profile` / `memory_summary` / `chat_log` 表 |

### 1.2 现有“上下文/世界数据”提供方（World Model 可直接复用）

- 时间：在 `memory.build_context_prefix` 内 `datetime.now()` 现算。
- 位置/天气：`geo_weather.build_geo_block` / `weather.last_weather` / `get_weather`。
- 热点：`hotspots.build_hotspot_context` / `get_hotspots`。
- 提醒：`db` 的 `reminders` 表（已在 `build_context_prefix` 读）。
- 焦点：`focus.recent_foci`。
- 任务：`tasks.get_open_tasks`。
- ACI 预取：`prefetch.format_prefetched_items`。
- 系统资源：`sysmon`（CPU/GPU/内存）。
- 设备：`devices.list_devices`。
- 用户画像/长期记忆：`db` 的 `profile` / `memory_summary` / `chat_log`（在 `build_memory_block`）。

### 1.3 目前**缺失**（World Model 需新增采集器）

- Git 状态（分支/未提交/最近提交）——当前无。
- 当前项目（从 cwd / git root 推断）——当前无。
- 网络可达性/延迟/代理状态——零散在 `self_check`/`http_client`，未聚合。
- 运行软件清单——隐私敏感，可选，暂不强制。
- 工作/休息时间——依赖 User Model（Phase 1 不做，先留配置位）。

---

## ② 聊天请求完整生命周期（调用链）

```
[浏览器 / Electron]
   │  POST /api/chat  (JSON: messages, images, session_id, temperature, reasoning)
   ▼
server.do_POST (server.py:519)
   │  ppath = path.split("?")[0]
   │  if ppath == "/api/chat": return self._handle_chat()
   ▼
server._handle_chat (server.py:849)
   ├─ 1. _read_json() 解析 payload，校验 messages 非空
   ├─ 2. 若无 system 消息：prepend config.SYSTEM_PROMPT.format(name=AI_DISPLAY_NAME)
   ├─ 3. 取最后一条 user 消息 → user_text
   ├─ 4. messages[0]["content"] = build_system_prompt(user_text)   ★ System Prompt 装配
   ├─ 5. 图像多模态：若 payload.images 存在，把最后 user 消息 content 改为
   │        [{"type":"text",...}, {"type":"image_url",...}]  (最多 4 张)
   ├─ 6. personalization.record(user_text)                     (best-effort)
   ├─ 7. personalization.summary() 追加到 system prompt 末尾     (best-effort)
   ├─ 8. 设置 SSE 响应头（text/event-stream）
   ├─ 9. 定义 emit(obj) → 写 "data: ...\n\n" 并 flush
   ├─10. save_turn(session_id, "user", user_text)
   ├─11. capture_foci(user_text)                                (焦点栈)
   ├─12. hotspots.archive_mentioned_hotspots(user_text)         (best-effort)
   ├─13. weather._LAST = None                                   (清上一轮天气态 ⚠ 全局变异)
   ├─14. run_fc_loop(messages, emit,
   │        tools=select_tools(user_text), temperature, reasoning)
   │        ▼
   │      tools.run_fc_loop (tools.py:1043)
   │        ├─ MAX_ROUNDS=5
   │        ├─ for _ in range(5):
   │        │    agnes_completion(messages, tools, stream=False, timeout=90)
   │        │    解析 tool_calls → called 集合
   │        │    append assistant msg
   │        │    if 无 tool_calls: return (content, called)   ← 终态自然语言
   │        │    execute_tool_calls → emit tool_start/tool_end；append tool_msgs
   │        └─ 超轮次：再调一次无工具 LLM 强制收尾
   ├─15. detect_intents(user_text) → missed（LLM 没调但意图明显的工具）
   │        for name,args in missed:
   │            emit tool_start → execute_tool(name,args) → emit tool_end
   │        若仅 get_hotspots 直接返回；否则二次 LLM 汇总（build_system_prompt 第二次调用）
   ├─16. weather.last_weather() 若 ok → emit modal(weather)
   ├─17. 若调用过 get_hotspots → emit modal(hotspots)
   ├─18. emit({"choices":[{"delta":{"content":content}}]}); emit("[DONE]")
   ├─19. save_turn(session_id, "xiao6", content)
   └─20. 后台线程：compress_memory / extract_daily_note / extract_profile / extract_persons
```

**每一步均未遗漏**。关键耦合点：步骤 4/7/15 多次拼装 System Prompt；步骤 13 直接变异 `weather._LAST`；步骤 14/15 两次可能调用 LLM；步骤 16/17 运行时弹窗与 Prompt 无关但是“副作用”。

---

## ③ Prompt 生成分析（注入点 / 重复 / 耦合 / 迁移）

### 3.1 各片段注入位置

| Prompt 片段 | 当前位置 | 注入方式 |
|---|---|---|
| System Prompt 基础 | `config.SYSTEM_PROMPT` | `_handle_chat` 步骤 2 预置，步骤 4 被 `build_system_prompt` 覆盖 |
| 时间 / 提醒 / 焦点 / 任务 / 位置 / 热点 / ACI 预取 | `memory.build_context_prefix` | `build_system_prompt` 内拼接 |
| 用户画像 / 长期记忆摘要 / 近期对话 | `memory.build_memory_block` | `build_system_prompt` 内拼接 |
| 个性化习惯画像 | `personalization.summary()` | `_handle_chat` 步骤 7 额外追加到 system |
| 用户消息 + 图像 | `payload.messages` / `images` | 步骤 3/5 |
| 兜底汇总时的 system | `build_system_prompt(user_text)` | 步骤 15 二次调用 |

### 3.2 重复与耦合

- **重复调用**：`build_system_prompt` 在步骤 4 与步骤 15 各调用一次（两次 LLM 之外的拼接成本）。
- **耦合**：`server.py` 直接 `import weather; weather._LAST = None` 与 `weather.last_weather()`——运行时与天气模块全局态强耦合（规范 P3）。
- **分散**：个性化画像在 server 注入，记忆/上下文在 memory 注入，二者不统一；未来人格/用户模型扩展会更难。
- **无预算**：所有片段无条件全量拼接，无 Token 上限、无重要度排序、无裁剪——正是 Context Engine 要解决的。
- **热点双写**：`build_hotspot_context`（Prompt 内）与 `get_hotspots`（运行时弹窗）两份逻辑，未来统一到 World/Context。

### 3.3 必须迁移到 Context Engine 的点

1. `build_system_prompt` 的全部拼接逻辑 → `ContextSerializer` + `ContextBuilder`。
2. `build_context_prefix` 的各子块 → 各自成为 `ContextSource`（Time/Reminder/Focus/Task/Geo/Hotspot/ACI）。
3. `build_memory_block` → `MemorySource`（Profile/Summary/RecentChat）。
4. `personalization.summary` → 暂作为 `UserModelStubSource`（Phase 1 仍调原函数，未来切 User Model）。
5. `select_tools` / `detect_intents` 的“上下文相关工具裁剪” → 未来由 Decision/Context 提供，但 Phase 1 不改。

---

## ④ Context Engine 设计（仅设计，兼容当前 Prompt）

### 4.1 组件划分（对应规范要求）

| 组件 | 职责 | Phase 1 实现策略 |
|---|---|---|
| `ContextSource`（抽象） | 定义 `gather(budget_hint) -> List[ContextItem]`；每个源有 `source_id`、TTL、权重 | 抽象基类 + 若干具体源，初期直接包装现有函数 |
| `ContextItem`（DTO） | `source_id, content, relevance, recency, importance, reliability, token_estimate, ttl` | dataclass |
| `ContextRanker` | 确定性评分：`score = 0.35*relevance + 0.25*recency + 0.25*importance + 0.15*reliability` | 纯函数，不调 LLM |
| `ContextBudget` | 档位 16K/32K/64K/96K；先保留 SystemBase+最近 N 轮，再按 score 填充，每源上限 | 配置化 |
| `ContextSerializer` | 把排序后的 items 拼成与当前 `build_system_prompt` **完全等价**的字符串 | 首要保证零回归 |
| `ContextCache` | 按 source_id + TTL 缓存（时间/天气/位置/热点/ACI） | 内存 dict + 过期 |
| `ContextBuilder` | 编排：加载 sources → ranker → budget → serializer → 返回 `ContextSnapshot` | 对外唯一入口 `assemble(turn)` |

### 4.2 源清单（Phase 1 映射现有数据）

- `SystemBaseSource`：读 `config.SYSTEM_PROMPT.format(name=...)`（不变）。
- `TimeSource`：从 WorldModel 取时间（Phase 1 可暂用 datetime，后续归 WorldModel）。
- `ReminderSource`：`db.reminders`（复用现有 SQL）。
- `FocusSource`：`focus.recent_foci(6)`。
- `TaskSource`：`tasks.get_open_tasks(5)`。
- `GeoSource`：`geo_weather.build_geo_block()`。
- `HotspotSource`：`hotspots.build_hotspot_context(message)`。
- `ACISource`：`prefetch.format_prefetched_items(...)`。
- `MemorySource`：`build_memory_block()`（Profile/Summary/RecentChat）。
- `UserModelStubSource`：`personalization.summary()`（未来替换为 User Model）。
- `PersonalitySource` / `GoalSource` / `KnowledgeSource`：Phase 1 仅留空实现（返回空），不破坏现有行为。

### 4.3 兼容性保证

- `ContextBuilder.assemble()` 的首个版本**内部直接调用 `memory.build_system_prompt`** 作为输出，确保与现有 Prompt 字节级一致；随后逐步用 Source 组装替换内部实现，每替换一个源就做 A/B 文本比对。
- `ContextSnapshot` 至少包含 `system_prompt: str` 与 `meta`（各源占比、token 估算），供 Developer Dashboard 未来消费。
- 不删除 `build_system_prompt`，保留为兼容门面。

---

## ⑤ World Model 设计（复用优先）

### 5.1 `WorldModel` 接口（设计）

- `snapshot() -> WorldSnapshot`：聚合所有域，返回只读 DTO。
- `refresh(domain=None)`：按需刷新某域（带 TTL）。
- 各域采集器独立，失败不影响其他域。

### 5.2 域映射

| 域 | 数据源（现有/新增） | 说明 |
|---|---|---|
| time | 新增（datetime 封装） | 从 `build_context_prefix` 抽出 |
| location | `geo_weather.get_geo` | 复用 |
| weather | `weather.last_weather` / `get_weather` | 复用，消除 `_LAST` 全局态 |
| hotspots | `hotspots.get_hotspots` | 复用 |
| reminders | `db.reminders` | 复用 |
| foci | `focus.recent_foci` | 复用 |
| tasks | `tasks.get_open_tasks` | 复用 |
| cpu/gpu/memory | `sysmon` | 复用 |
| devices | `devices.list_devices` | 复用 |
| network | `self_check` / `http_client` 聚合 | 部分新增封装 |
| git_status | **新增** `git` 子进程调用（Git Bash 可用） | 新增采集器 |
| current_project | **新增**（cwd / git root 推断） | 新增采集器 |
| work_hours/rest_hours | 配置占位（User Model 接入前） | 占位 |

### 5.3 与现状的关系

- WorldModel **不取代**各提供方，而是聚合 + 缓存 + 统一快照。
- 第一步：WorldModel 内部仍调用 `geo_weather` / `weather` / `hotspots` 等，仅把 `weather._LAST` 这类模块全局态迁移进 WorldModel 实例字段（消除 P3 耦合）。
- WorldModel 快照供 Context Engine 的 `TimeSource` / `GeoSource` 等消费，逐步替代 `build_context_prefix` 内的散落读取。
- Phase 1 **不**引入 EventBus 发布 `WorldStateChanged`（EventBus 不在本次允许清单；留待后续步骤，WorldModel 先提供 `snapshot()` 方法即可）。

---

## ⑥ Agent Runtime 骨架设计（仅接口，可插拔）

### 6.1 包结构（新增 `agent/`）

```
agent/
├── __init__.py
├── types.py          # TurnRequest / Plan / Step / ReasoningResult / Decision / ExecutionResult / ReflectionResult / CognitiveState
├── runtime.py        # AgentRuntime（编排器）
├── planner.py        # PlannerInterface + PassthroughPlanner
├── reasoning.py      # ReasoningInterface + PassthroughReasoning
├── decision.py       # DecisionInterface + DefaultDecision
├── executor.py       # ExecutorInterface + LegacyExecutor（包装 run_fc_loop+detect_intents）
└── reflection.py     # ReflectionInterface + MinimalReflection
```

### 6.2 接口定义（抽象，不含复杂逻辑）

- **AgentSession**：持有 `session_id`、Working Memory、CognitiveState；`run(turn: TurnRequest) -> SessionResult`。
- **PlannerInterface.plan(turn, context) -> Plan**：Phase 1 返回单步 Plan（“执行传统聊天流程”）。
- **ReasoningInterface.think(plan, context) -> ReasoningResult**：Phase 1 返回 `next_action=EXECUTE`、confidence=1.0。
- **DecisionInterface.decide(reasoning) -> Decision**：Phase 1 返回 `action=EXECUTE_LEGACY`。
- **ExecutorInterface.execute(decision) -> ExecutionResult**：Phase 1 内部调用现有 `run_fc_loop` + `detect_intents` + 弹窗逻辑（通过兼容适配器，保证 SSE 事件格式不变）。
- **ReflectionInterface.reflect(result) -> ReflectionResult**：Phase 1 仅记录最小元数据，不写库（避免改变现有后台线程行为）。

### 6.3 当前流程如何“旁边建立未来架构”

- `AgentRuntime.run()` 在 Phase 1 **默认不接管** `_handle_chat`；它作为独立可调用入口存在，内部各接口实现就是“调用现有函数”的适配器。
- 验证方式：新增隐藏端点或单测直接调用 `AgentRuntime.run()`，对比其输出与现有 `_handle_chat` 是否一致。
- 待 Phase 1 稳定后，再在 `_handle_chat` 中加 Feature Flag 切换；切换前现有路径完全不变。

---

## ⑦ Phase 1 文件改动清单

> 原则：新增文件为主，修改文件极少且仅加兼容层；数据库零改动。

### 7.1 新增文件

| 文件 | 作用 | 为什么 | 影响 |
|---|---|---|---|
| `context_engine.py`（或 `context/` 包） | ContextBuilder + Sources + Ranker + Budget + Serializer + Cache | 规范第四章，统一 Prompt 装配 | 仅被新代码引用，不影响现有 |
| `world_state.py` | WorldModel 聚合快照 | 规范第六章，消除全局态耦合 | 仅被新代码引用 |
| `agent/types.py` | 运行时 DTO | 规范第三章 | 无业务影响 |
| `agent/runtime.py` | AgentRuntime 编排器（接口串联） | 规范第三章 | 默认不接管 |
| `agent/planner.py` `reasoning.py` `decision.py` `executor.py` `reflection.py` | 各接口 + 兼容适配器 | 规范第三章骨架 | 默认不接管 |

### 7.2 修改文件（最小）

| 文件 | 改动 | 为什么 | 风险 |
|---|---|---|---|
| `server.py` | **仅**新增 import 与可选 Flag（默认 False）；不改动 `_handle_chat` 主流程 | 为后续切换留缝，但不改变当前行为 | 极低 |
| `config.py` | 可选新增 `CONTEXT_BUDGET_TIER` 配置项（默认 16K） | 支持预算档位 | 极低 |
| `memory.py` | 不改动；`build_system_prompt` 保留为门面 | 兼容 | 无 |

### 7.3 不改动

- `tools.py`、`geo_weather.py`、`hotspots.py`、`prefetch.py`、`focus.py`、`tasks.py`、`personalization.py`、`weather.py`、`db.py`、前端所有文件、Electron、数据库文件。

---

## ⑧ 风险分析

| 风险 | 等级 | 缓解 |
|---|---|---|
| R1 ContextEngine 输出与现有 Prompt 不一致导致 LLM 行为回归 | 高 | 首版直接委托 `build_system_prompt`；逐源替换 + 文本 A/B 比对；Flag 默认关 |
| R2 WorldModel 采集器引入外部调用延迟 | 中 | 复用现有函数 + TTL 缓存；不新增阻塞调用 |
| R3 AgentRuntime 适配器意外改变 SSE 事件格式 | 中 | Executor 适配器原样 emit `tool_start/tool_end/modal/[DONE]`；单测比对 |
| R4 新模块循环导入 | 中 | 所有跨模块 import 改为函数内 lazy import |
| R5 新文件超 500 行（God File） | 低 | `context/` 若过大则按 Source 拆子文件；Agent 各接口单文件 |
| R6 误改 `_handle_chat` 导致线上回归 | 低 | Phase 1 主流程零改动，仅加 Flag |

---

## ⑨ Rollback 方案

1. **新增文件可整体删除**：Phase 1 所有新文件未被现有代码强制依赖（`server.py` 仅可选 import），删除即回退。
2. **Flag 切换**：若 `AgentRuntime` 实验路径异常，将 Flag 置 False 即回到原 `_handle_chat`，无需删文件。
3. **数据库零改动**：Phase 1 不涉及任何表结构或数据迁移，无数据 Rollback 需求。
4. **Context Engine 回退**：若 `ContextBuilder` 替换实现出问题，将其内部实现瞬切回 `build_system_prompt` 调用（保留该函数）。
5. **WorldModel 回退**：若聚合快照异常，调用方回退为直接调用原 `geo_weather` / `weather` 等函数（原函数不变）。
6. **提交策略**：每新增一个文件即小步 commit；任一文件出问题 `git revert` 单笔即可，不影响其他。

---

## 结论

Phase 1 的任务是**在完全不触动现有聊天逻辑的前提下，于“旁边”建立三套可插拔基础设施**：
- Context Engine（统一 Prompt 装配，未来接管 `build_system_prompt`）
- World Model（聚合时间/位置/天气/系统/Git/项目等，消除 `weather._LAST` 式全局耦合）
- Agent Runtime 骨架（Planner/Reasoning/Decision/Executor/Reflection 接口 + 现有流程兼容适配器）

所有新增均为**纯增量、零功能回归、可独立测试、可一键 Rollback**。待你确认后，我再按“小步提交、每步可运行、每步可 Rollback”的原则进入真正编码阶段。
