# Phase 9 Proactive Intelligence Layer v1.0 — Audit Report

> 阶段：S0 Audit + Architecture Design
> 执行模式：Audit → Analysis → Design → Review
> 纪律：只读审计 / 禁止修改代码 / 禁止新增功能 / 禁止进入实现
> 日期：2026-08-04
> 目标：研究小6如何从 Reactive AI Assistant 升级为 Proactive AI Operating System

---

## 0. 审计范围与依据

| 审计对象 | 主文件 | 辅助文件 |
|---|---|---|
| Agent Runtime | `xiao6-ui/agent_runtime.py` | `agent_delegate.py`, `message_processor.py` |
| Goal System | `xiao6-ui/goals.py` | `goal_decision_engine.py` |
| Execution Guard | `xiao6-ui/policy_engine.py` | `permission_guard.py`, `capability_registry.py` |
| Memory System | `xiao6-ui/memory.py` | `db.py`, `memory_distiller.py`, `reflector.py`, `cognitive/` |
| EventBus | `xiao6-ui/eventbus.py` | — |
| Scheduler | `xiao6-ui/proactive.py` | `always_on.py`, `server.py` |
| Knowledge System | `xiao6-ui/knowledge.py` | `embed.py` |
| Task System | `xiao6-ui/tasks.py` | — |
| Companion Layer | `xiao6-ui/companion.js` | `companion.html`, `avatar-state.js`, `electron/main.js`, `electron/preload.js` |

**全局事实（审计前决条件）**
- 统一通信脊柱 = EventBus（`eventbus.py:56` 类 `EventBus`，进程单例 `bus` @`:156`）；领域事件 `DOMAIN_EVENT_NAMES`（`:177-220`），系统事件 `SYSTEM_EVENT_NAMES`（`:250-260`）；SSE 扇出 `TOPIC_SSE="zz.sse"`（`:26`）。
- 后端已存在主动智能模块 `proactive.py`（心跳 + 规则扫描 + 推送），是本次升级的核心基座。
- 配置开关：`FEATURE_EVENTBUS` 默认 ON；`FEATURE_AGENT_RUNTIME` 默认 ON；`FEATURE_PROACTIVE_V2`（停滞/周报建议）默认 ON；`FEATURE_ALWAYS_ON` 默认 **OFF**；`FEATURE_MEMORY_DISTILL` 默认 OFF（`config.py`）。

---

## 1. 现状分析（逐系统）

### 1.1 Agent Runtime — 目标驱动编排状态机
- 状态机 `IDLE→PLANNING→EXECUTING→REFLECTING`（`agent_runtime.py:23`）；`start()/stop()` 启动**后台 daemon 线程** `_loop`（`:59/67/98`）。
- 外部入口 `submit_goal(title, description, intent_id) -> Optional[int]`（`:73`）创建 Goal 并入队；`_run_goal`（`:119`）→ `_execute_task`（`:202`，经 `policy_engine.evaluate`）/ `_execute_computer_task`（`:252`，经 `permission_guard.guard`）。
- **主动能力**：被动——仅 `submit_goal` 被调用后运行；`_loop` 阻塞于 `Condition.wait(timeout=1.0)`（`:98`），**无定时器/无自触发**。运行态经 `_publish_state` 发 `agent_state`/`zz.hud.state`。
- **可复用**：`runtime.submit_goal(...)`（主动引擎提交目标走完整生命周期）；`bus.subscribe("agent:state"|TOPIC_HUD_STATE, cb)`。
- **缺口**：`_loop` 不主动发起 Goal；无"空闲时自动寻找可推进目标"逻辑。

### 1.2 Goal System — 目标系统
- `goals.create_goal(...)`（`:142`，发 `GOAL_CREATED`）；`recalc_progress`（`:292`）子任务全完成自动 `completed` 并发 `GoalCompleted`（`:344`）；`plan_goal`（`:380`）LLM 拆解。
- `goal_decision_engine.GoalDecisionEngine.ingest(user_text) -> Decision`（`:71`，两级决策门 A/B/C/D/E→create/propose/skip/resume/merge）；`submit(decision, intent_id)`（`:214`，唯一写出口，调 `runtime.submit_goal`）；单例 `engine`（`:268`）。
- **主动能力**：目标完成**自动**触发事件链；GDE 在用户长任务输入时**自动建 Goal**（C 类高置信度）。
- **可复用**：`goals.list_active_goals()/recalc_progress()`（发现停滞/临近目标）；`engine.ingest()+.submit()`（主动意图送入同一决策门，复用去重/置信度）。
- **缺口**：无"系统空闲时自动建议推进某目标"触发点；GDE 仅由用户文本触发。

### 1.3 Execution Guard — 执行护栏
- `policy_engine.evaluate(tool, args, goal_id, default_deny=True) -> {decision:auto|confirm|block, reason, permission}`（`:97`）。
- `request_approval(tool, args, ..., goal_id, default_deny=True) -> str`（`:138`，发 `modal` 卡，挂起等待，返回 approve/reject/timeout）；`resolve(ticket, decision)`（`:173`）。
- `permission_guard.PermissionGuard`（`:37`，单例 `guard` `:165`）：`.run(action, goal_id, ...)`（`:80`）完整链路，HIGH/CRITICAL 在 Guard 层直接 `deny`（`:62-68`）。
- `capability_registry`：13 项能力，LOW→AUTO / MEDIUM→CONFIRM / HIGH·CRITICAL→未实现（占位）。
- **可复用（关键）**：主动引擎执行的任何工具/能力**必须**经此 Gate——`policy_engine.evaluate` + `permission_guard.guard.run`。无第二权限系统。
- **缺口（对主动致命）**：`evaluate` 中 `if default_deny or not goal_id: return confirm`（`:119-120`）；`request_approval` 中 `if default_deny and not goal_id: return "reject"`（`:141-142`）。**主动动作若无 `goal_id` 会被拒绝/挂起**；`confirm` 会阻塞线程等审批（无人值守卡死）。

### 1.4 Memory System — 记忆系统
- `memory.build_memory_block/recode_learning/distill`；`memory_distiller.distill(session, messages)`（`:196`，启发式+LLM 提炼 habit/preference/event 写入 `memories`）；`reflector.reflect(goal, executions)`（`:21`，闭环后经验沉淀，发 `MEMORY_*`）。
- `cognitive/user_model.load_user_model/upsert_user_model`（`:32/66`）；`cognitive/episodic.add_episode/recall_episodes`（`:23/52`，语义+重要性+新鲜度召回）。
- **主动能力**：有蒸馏/反思/沉淀（非实时）；`agent_runtime._check_important_dates` 提前扫描重要日期并 `push_proactive("memory", ...)`。
- **可复用**：`memory_distiller.distill()`（周期触发提炼）；`user_model/recall_episodes`（为"该不该现在打扰"提供依据）；`memory.build_context_prefix()`（生成主动决策上下文）。
- **缺口**：记忆召回被对话触发，无后台"基于记忆主动联想"循环；`memories/episodes` 表**无"未消费/待提示"标记**，主动引擎无法知道哪些记忆值得主动提出。

### 1.5 EventBus — 事件总线（关键系统）
- `EventBus.subscribe(topic, cb, async_, priority) -> token`（`:74`）；`publish_domain(name, payload, source)`（`:223`，`name` 须 ∈ `DOMAIN_EVENT_NAMES`）；`publish_system(name, fields, source)`（`:263`，须 ∈ `SYSTEM_EVENT_NAMES`）。
- 已承载 Goal/Agent/Task/Memory/Computer/Perception/Intent 全生命周期事件；`proactive.py` 已 `bus.subscribe("zz.goal", _on_goal_event)`（`:760`）——证明"事件驱动主动感知"模式**已可行**。
- **可复用（核心接入点）**：`bus.subscribe(ANY_TOPIC, cb)` 订阅任意主题；`publish_domain/publish_system` 发事件；无需自建通信层。
- **缺口**：见 Q1——`ERROR_OCCURRED`（`:185`）已声明但**后端无生产者**；无"长任务进行中"专用事件。

### 1.6 Scheduler / 周期任务 — 后台执行机制
- **已存在明确心跳调度器**：`proactive.tick_loop()`（`proactive.py:316-330`），由 `server.py:2582` 以 daemon 线程启动。
- 自适应间隔 `_next_interval()`（`:125-142`）：到期提醒→0s；限流→600s；唤醒期→10s；空闲自适应 10/20/30s。
- 哨兵 `_tick_sentinel()`（`:169`，>60s 降级）；抢占 `request_immediate_scan(kind)`（`:150`，已被 `tools.tool_tick_now` `tools.py:2138` 调用）。
- `agent_runtime._loop`（`:98`）、`perception_runtime.start(ttl_ms)`（`:175`，需宿主驱动）为辅。
- `always_on.AlwaysOnController`（`always_on.py:48`）是 **CPU 门控控制器**，`start()` 在沙箱仅置位不 spawn 真实线程（`:65-72`）；`FEATURE_ALWAYS_ON` 默认 OFF——**真实常驻心跳未落地**（但 tick_loop 已满足时间驱动需求，非必需）。
- **可复用**：`proactive.tick_loop` 作时间驱动锚点；`request_immediate_scan` 作即时触发（无需自建定时器）。
- **缺口**：无 cron/APScheduler 式"指定时间触发"原语（`rules` 表 `time` 触发由 `_check_rules` 在 tick 内轮询 `:714`）；`always_on` 真心跳空壳。

### 1.7 Knowledge System — 知识系统
- `knowledge.ingest_document`（`:92`，切分+本地 ONNX 向量+落库）；`semantic_query(query, top_k, min_score)`（`:141`，本地 RAG 余弦召回）。
- **主动能力**：被动 RAG 召回（被对话/注入调用），无后台"知识主动应用"循环。
- **可复用**：`semantic_query`（检索用户背景/历史决策以支撑是否打扰/建议）；`ingest_document`（沉淀主动发现）。
- **缺口**：无"知识到期/冲突/待复核"事件；向量检索未与主动触发器挂钩。

### 1.8 Task System — 任务系统
- `tasks.create_task(title, steps, goal_id)`（`:23`）；`complete_task`（`:96`）→ `recalc_progress` 联动 Goal；`recover_tasks`（`:165`）把 `running` 翻回 `open`（**可恢复性**，对主动续跑重要）。
- **可复用**：`get_open_tasks(limit, goal_id)`（发现未完成任务并建议推进）；`create_task(goal_id=...)`（主动引擎创建子任务）。
- **缺口**：任务无 `owner/来源` 标记区分用户 vs 系统创建；无"用户未确认则过期"语义。

### 1.9 Companion Layer — 桌面伴侣层（Phase 8）
- `companion.js render()`（`:51`）从 AppState+ExecutionChannel+ZZSSE 派生（单一来源）；`showNotification(kind, text)`（`:163`）完成/异常通知，**`if (prefs.dnd) return;`（`:165`）DND 抑制所有通知**；`togglePref/prefs`（`:30/:197`）；`handleAction`（`:223`）本地控制 vs 系统动作经 `bridge.action`。
- IPC 桥（preload.js `:36-46`）：`action/setPref/getPrefs/setCompanionVisible/onCompanionExec`；Electron 主进程（main.js `:274/283/290/293`）转发；`companion.json` schema `{pos, ui:{hidden,paused,dnd}}`（`:86-108`）。
- **可复用**：`bridge.action({type})`（主动引擎如需"点击伴侣开面板/执行指令"走此桥而非自建 API）；Companion 是既有**通知面**。
- **缺口（见 Q5）**：**DND 仅在 companion 前端强制**（`companion.js:165`），**后端 `push_proactive` 无 DND 感知**（`proactive.py:252/265` 无差别下发）；`pending_proactive` 表无 quiet 标记。

---

## 2. 能力矩阵

| 能力 | 状态 | 复用接口（已有） | 备注 |
|---|---|---|---|
| 时间驱动触发 | ✅ | `proactive.tick_loop` + `request_immediate_scan` | 心跳已存在，自适应间隔 |
| 事件驱动订阅 | ✅ | `bus.subscribe(topic, cb)` | pub/sub 成熟，proactive 已订阅 `zz.goal` |
| 意图决策门 | ✅ | `run_intent_gateway` + `GoalDecisionEngine` | 程序可调用，零新增决策逻辑 |
| 目标提交/执行 | ✅ | `runtime.submit_goal` → AgentRuntime 状态机 | 主动引擎提交新目标走完整生命周期 |
| 权限裁决 | ✅ | `policy_engine.evaluate` / `permission_guard.guard.run` | 唯一 Gate，无第二权限系统 |
| 用户模型/记忆上下文 | ✅ | `cognitive/user_model`, `cognitive/episodic.recall_episodes`, `memory_distiller` | 支撑"该不该现在打扰" |
| 知识检索 | ✅ | `knowledge.semantic_query` | 本地 RAG |
| 感知输入 | 🟡 | `perception_runtime` + `perception_alert` | 存在；持续循环与 server.py 串联待确认 |
| 伴侣通知面 | ✅ | Companion + `bridge.action` | DND 仅前端 |
| 长任务进行中事件 | ❌ | — | 无专用 `LONG_RUNNING`；需复用 `AGENT_WORKING`+超时推断 |
| `ERROR_OCCURRED` 后端生产者 | ❌ | 事件名已声明无生产者 | 工具/任务级异常未路由到该事件 |
| 后端 DND/quiet 感知 | ❌ | `companion.json ui.dnd`（仅前端读） | `push_proactive` 无 quiet 检查 |
| 主动决策 LLM 智能裁决层 | ❌ | — | 当前纯规则/阈值，缺"何时该主动"的智能裁决 |
| `always_on` 真实常驻 | ❌ | CPU 门控控制器（非调度器） | 空壳，FEATURE 默认 OFF；tick_loop 已够 |
| 记忆"待提示"标记 | ❌ | — | 无未消费/待提示标记 |
| 任务 owner/来源标记 | ❌ | — | 无用户 vs 系统创建区分 |

---

## 3. 缺口分析（GAP）

- **G1 主动决策层缺失**：现有 `proactive.py` 是"条件命中即推"的纯规则/阈值驱动，**无 LLM 对"时机/价值/用户状态"的智能裁决**。这是 Phase 9 核心补强点。
- **G2 后端用户控制缺失**：DND/quiet 只在 Companion 前端强制，后端 `push_proactive`/`flush_pending` 无差别下发（验证 `proactive.py:252/265`）。需后端化。
- **G3 事件缺口**：`ERROR_OCCURRED`（`:185`）声明但无后端生产者；无 `LONG_RUNNING` 专用事件（长任务"进行中"需复用 `AGENT_WORKING`+超时推断）。
- **G4 `always_on` 真实常驻未落地**：但非必需——`proactive.tick_loop` 已满足时间驱动需求，设计不应重建调度器。
- **G5 PerceptionRuntime 持续循环串联待确认**：`perception_runtime.start` 需宿主 server.py 驱动，grep 未命中 `PerceptionRuntime(` 在 server.py，可能未串联；设计不应强依赖。
- **G6 记忆"待提示"标记缺失**：`memories/episodes` 无未消费标记，主动引擎无法筛选"值得主动提出"的记忆。
- **G7 任务 owner/来源标记缺失**：无法区分用户 vs 系统创建的主动任务，影响可解释性与回收。

---

## 4. 五个重点问题回答（摘要）

**Q1 事件驱动主动感知——EventBus 是否支持任务完成/异常/状态变化/长运行事件？**
支持。可订阅：`GOAL_COMPLETED`/`TASK_COMPLETED`/`AGENT_COMPLETED`（完成）、`TASK_FAILED`/`AGENT_FAILED`/`GOAL_FAILED`/`COMPUTER_ACTION_FAILED`/`COMPUTER_ACTION_DENIED`（异常）、`GOAL_UPDATED`/`FOCUS_CHANGED`/`STATE_SYNC`/`agent_state`（状态）、`AGENT_THINKING/WORKING/WAITING`/`TASK_STARTED`（进行中，代理态）。**缺口**：`ERROR_OCCURRED` 无后端生产者；无 `LONG_RUNNING` 专用事件。

**Q2 周期任务能力——是否存在 Scheduler / Background Worker / Heartbeat？**
存在。`proactive.tick_loop()`（`proactive.py:316`）为主心跳（daemon 线程，`server.py:2582` 启动），自适应间隔 + 哨兵 + `request_immediate_scan` 抢占插队。`agent_runtime._loop`、感知循环为辅。`always_on` 是 CPU 门控控制器而非调度器（真实心跳空壳）。

**Q3 主动决策入口——AI 何时可主动行动？**
现有 3 类触发：①定时器（`tick_loop` 周期扫描规则）②事件（`bus.subscribe("zz.goal")` 目标完成→复盘提示）③抢占（`request_immediate_scan` 由命令触发）。决策逻辑为纯规则/阈值（如 `_check_goal_stalled` 超 5 天、`_check_goal_deadlines` ≤24h、`_scan_anomaly` 关键词/排名突增），**无 LLM 智能裁决**。最干净的复用入口 = `run_intent_gateway(text)` + `GoalDecisionEngine` + `runtime.submit_goal`。

**Q4 权限边界——主动行为须经什么 Guard？**
任何主动执行动作必须过 `policy_engine.evaluate` / `permission_guard.guard.run`（唯一 Gate）。关键约束：无 `goal_id` 时 `evaluate` 返回 `confirm`（`:119-120`）、`request_approval` 直接 `reject`（`:141-142`）；`confirm` 会阻塞线程等审批。**主动执行必须携带 `goal_id`（即经 `submit_goal` 提交）**，且无人值守时 `confirm` 类动作需降级为"仅建议"避免卡死。HIGH/CRITICAL 能力在 Guard 层拒绝，主动引擎不可触达。

**Q5 用户控制——静默模式/通知策略/确认机制？**
前端已有：Companion DND（`prefs.dnd`，`companion.js:165` 抑制所有通知）、paused、hidden，持久化到 `companion.json ui.{hidden,paused,dnd}`。**后端缺口**：`push_proactive` 不检查 DND，无后端 quiet 接口，无"免打扰时段/专注模式"。Phase 9 需把用户控制后端化（DND 检查 + 分级通知 + 确认降级）。

---

## 5. 复用优先结论

| 主动引擎所需能力 | 直接复用（不造第二系统） |
|---|---|
| 时间驱动触发 | `proactive.tick_loop` + `request_immediate_scan` |
| 事件订阅 | `eventbus.bus.subscribe` + `publish_domain/publish_system` |
| 提交并执行目标 | `runtime.submit_goal` → AgentRuntime 状态机 |
| 意图决策门 | `run_intent_gateway` / `GoalDecisionEngine.ingest` |
| 权限裁决 | `policy_engine.evaluate` / `permission_guard.guard.run` |
| 用户上下文/记忆 | `cognitive.user_model` / `cognitive.episodic.recall_episodes` / `memory_distiller` |
| 知识检索 | `knowledge.semantic_query` |
| 感知输入 | `perception_runtime` + `perception_alert` |
| 伴侣通知面 | `bridge.action` IPC + Companion DND 控制 |

**结论**：小6已具备从 Reactive 升级为 Proactive 的绝大部分基座（心跳、事件总线、决策门、执行 Guard、记忆/知识/感知、伴侣通知面）。Phase 9 的增量是**一层"主动决策"（何时该主动）+ 后端用户控制（DND/分级）+ 少量事件生产者补全**，全部挂载现有管道，**不新增第二 Runtime/Memory/EventBus/State**。

---

## 6. 纪律自检

- 无第二 Runtime：✔（复用 `proactive.tick_loop` 线程，不新进程）
- 无第二 Memory：✔（复用 `memories/episodes/user_model`，仅建议加标记，不新建存储）
- 无第二 EventBus：✔（复用 `eventbus.bus` 订阅/发布）
- 无第二 State：✔（复用 AppState + 既有模块，不复制状态系统）
- 所有设计复用已有系统：✔（见第 5 节）
- 本阶段仅审计/设计，未修改任何代码：✔
