# 小6 AI OS 2.0 — Phase A 核心审计（CORE_AUDIT）

> Sprint: **AI OS Phase A — Core Intelligence Sprint v1.0**
> 身份: Chief AI Architect + Senior AI Runtime Engineer + Senior System Architect
> 模式: **Audit → Plan → Execute → Verify → Report → STOP**
> 任务: Phase A 任务一（Audit）→ 输出本报告
> 权威来源: `docs/ai-os/` 全部 17 份架构文档（Architecture 高于一切）
> 日期: 2026-08-05
> 状态: ✅ 审计完成；本任务 STOP，待逐任务 Review

---

## 0. 审计范围与纪律声明

**本次审计目标**：在不动任何代码、仅做"扫描 + 记录"的前提下，摸清小6 AI Core 现状，为 Phase A 十个"统一"任务（生命周期 / Context Pipeline / Execution Pipeline / State / Error Recovery / Health Check / Metrics / Logging / Capability Registry / Boot Sequence）建立**基线事实**与**边界护栏**。

**已扫描对象**（Bash/Grep 实测，非推断）：
- 架构约束：`docs/ai-os/01_AI_OS_ARCHITECTURE.md`、`99_ARCHITECTURE_MASTER_INDEX.md`、`00_EXECUTIVE_SUMMARY.md`
- 单 Runtime 主干：`agent_runtime.py`(32.6KB, 728 行全读)、`eventbus.py`(12.5KB, 重点段全读)、`config.py`(FEATURE 旗全扫)、`server.py`(130KB, 启动段 Grep)
- 权限：`policy_engine.py`、`permission_guard.py`（存在性 + 调用链确认）
- 记忆/上下文：`memory.py`、`context/`(builder/models/ranker/budget/sources/cognitive_sources)、`cognitive/`(extractor/user_model/episodic)、`capabilities.py`、`capability_registry.py`
- 执行：`tools.py`(186KB, 仅确认 `TOOL_FUNCS`/`READONLY_TOOLS` 存在)、`computer_executor.py`、`reflector.py`

**未逐行通读的大文件**（仅 Grep 定位关键位点，审计结论中已标注）：`server.py`(130KB)、`tools.py`(186KB)、`app.js`(109KB)/`app-state.js`(32KB, 前端状态写入口)。

**纪律红线（全程恪守）**：
- 本审计 **零代码改动**；仅读 + 记录。
- 不新增第二 Runtime / Memory / EventBus / Permission；不借机优化、不进入实现。
- Phase A 仅建设 **AI Core（L5 AI Brain + 横切生命周期/健康/指标/日志/恢复/能力/Boot）**；**不得**开始 Knowledge(L6)/Memory(L7)/Goal(L2)/Workflow(L3)/Agent(L4) 引擎的"新建"，但须识别它们"已存在"的部分以免重复建设。

---

## 1. 执行摘要（Executive Summary）

小6 v1.0 已落地的"单 Runtime / 单 EventBus / 单 Permission / 单 Memory / Local First"骨架**基本合规**，且比架构文档描述的更超前——**L4 Agent Engine（`agent_runtime.py`）已实装并默认开启**。Phase A 的真正难点不是"从零建内核"，而是：

1. **在已存在 L4 Agent 编排状态机的前提下，厘清 L5 AI Brain 内核的边界**，避免生命周期/执行管道与 `AgentRuntime` 重复造轮子。
2. **收敛三处碎片化**：能力注册表有 2 套、上下文装配有 3 条路径、事件 SYSTEM 命名空间已超出冻结契约（8 → 14）。
3. **补齐四个横切子系统空白**：Health Check / Metrics / Logging Standard / Crash Recovery（当前为零或散兵游勇）。

**结论**：Phase A 可启动，但任务二（Lifecycle）/ 任务四（Execution Pipeline）必须与 `agent_runtime.py` 明确分层（L4 vs L5），任务五（Capability Registry）须把两套注册表合流，任务三（Context Pipeline）须把三条路径统一为唯一 `context/` 管线。

---

## 2. L0 冻结红线合规记分卡

| # | 红线 | 状态 | 证据与说明 |
|---|------|------|-----------|
| 1 | 单一 Runtime（决策运行时唯一） | ✅ 合规 | 决策 Runtime 唯一实例 `agent_runtime.runtime`（`agent_runtime.py:727`）。`capture_runtime.py`/`always_on.py` 是**辅助采集/常驻线程**，非第二决策 Runtime，符合 P14。 |
| 2 | 单一状态写入口（`applyEvent→reducers`） | ⚠️ 部分 | 前端 `AppState.applyEvent` 为 UI 状态唯一写入口（工作记忆确认）。**后端**无统一 reducer：goals/tasks 经 `goals.update_goal` 等模块函数直写 DB。`agent_runtime` 仅经事件扇出，不直接写 UI 状态。后端状态写路径非单一，但受模块函数封装，Phase A 须沿用既有模块，禁开新写路径。 |
| 3 | 单一通信通道（EventBus） | ✅ 合规 | `eventbus.py:56 class EventBus`、`eventbus.py:156 bus = EventBus()` 进程级单例。`mobile.py` 的 `bus=None` 是回退局部变量，非第二总线。 |
| 4 | 单一权限（PermissionGuard + PolicyEngine） | ✅ 合规 | `policy_engine.py` + `permission_guard.py`（guard 单例）。`agent_runtime` 的执行全经 `policy_engine.evaluate` / `request_approval` / `guard.plan→guard.run`，无第二权限系统。 |
| 5 | 事件契约冻结（DOMAIN=71 / SYSTEM=8，逐字一致） | ⚠️ **漂移** | `DOMAIN_EVENT_NAMES` 实测 **71** 个（与红线吻合 ✅）；但 `SYSTEM_EVENT_NAMES` 实测 **14** 个（红线写 8）。SYSTEM 命名空间在冻结后扩至 14 且**无 Migration 记录**，违反"未走 Migration 不得破坏"。详见发现 F1。 |
| 6 | Local First（数据本地，云仅计算） | ✅ 合规 | 记忆/目标/对话落本地 SQLite（`db.py`）；LLM 仅经 `llm.agnes_completion` 计算调用，不持有状态。 |
| 7 | No God Module（单文件不兼任路由/编排/执行/持久化/分发） | ⚠️ 风险 | `server.py`(130KB)/`tools.py`(186KB) 体量过大，虽职责尚可分辨，但属架构气味。Phase A 新模块须严格遵守单一职责，不向巨型文件堆砌。 |
| 8 | 增量演进（新能力以新增模块/事件/Skill 加入） | ✅ 合规 | 全量 FEATURE 旗驱动（`config.py:210-263`），旧路径可瞬时回退（`FEATURE_CONTEXT_ENGINE=false` 回退 `memory.build_system_prompt`）。 |

**总评**：8 条红线中 5 条完全合规、3 条部分/漂移（#2 后端写入口、#5 SYSTEM 漂移、#7 体量气味）。无"推翻式"违规，Phase A 可在合规基线上推进。

---

## 3. 子系统逐一审记

### 3.1 通信主干 — EventBus（L0 通道）✅
- 单例 `bus = EventBus()`（`eventbus.py:156`）。
- `publish_domain`（`:223`）校验 `DOMAIN_EVENT_NAMES`（`:177`，71 个），未知名 `raise ValueError`（`:235`）——**单一来源 + 强校验**，符合红线。
- `publish_system`（`:271`）校验 `SYSTEM_EVENT_NAMES`（`:250`，14 个），与 DOMAIN 互斥（`:249` 注释）。
- 前端 `event-bridge.js` 消费 SSE 信封 `{"xiao6_event", "payload", "ts"}`（`publish_domain:238`）。
- **Phase A 影响**：横切事件（健康/指标/日志/启动）必须登记进 `DOMAIN_EVENT_NAMES` 或 `SYSTEM_EVENT_NAMES`，**禁止裸 `bus.publish`**（`:248` 纪律）。任务九（Logging）/ 任务六（Health）的新事件须在此登记。

### 3.2 权限 — PolicyEngine + PermissionGuard（L0 权限）✅
- `policy_engine` 提供 `evaluate` / `request_approval` / `AUTO` / `CONFIRM` / `NEVER` / `SESSION` 词汇。
- `permission_guard.guard` 单例封装 `plan()`（构造 ComputerAction）→ `run()`（Policy 裁决 → Executor → Verification）。
- `capability_registry.RISK_TIER` 直接复用 `AUTO/CONFIRM`（`capability_registry.py:26-32`），**零新增权限逻辑**——符合 ADR-001 复用纪律。
- **Phase A 影响**：任务五（Capability Registry）只声明元数据 + 风险映射，裁决一律委托 PolicyEngine，**绝不新建第二权限表**。

### 3.3 AI Runtime / Agent Engine（L4）⚠️ 已存在，须划界
- `agent_runtime.py`：`AgentRuntime` 状态机 `IDLE→PLANNING→EXECUTING→REFLECTING`（`agent_runtime.py:23`）。
- 后台 daemon 线程 `_loop`（`:98`），队列 + `Condition` 同步（`:46-48`）。
- `submit_goal`（`:73`）→ `goals.create_goal`（L2 Goal 引擎调用）→ 入队。
- 执行链 `_execute_task`（`:202`）：`policy_engine.evaluate` 裁决 → `tools.execute_tool`；电脑能力经 `_execute_computer_task`（`:252`）→ `guard.plan/run`（L8 Extension 闭环）。
- 反射 `_distill_memory` / `_check_important_dates`（`:421`/`:474`）——已部分触达 L7 Memory / P12 人格蒸馏。
- **门控漂移**：docstring 称"默认 off"，但 `config.py:233 FEATURE_AGENT_RUNTIME` 默认 `"true"`；`server.py:2686-2690` 注释亦称"默认关闭"却实际默认开启。→ **L4 Agent 引擎默认在线**。
- **Phase A 影响（关键边界）**：L4 已提供"目标→规划→执行→反思"编排生命周期与执行循环。Phase A 的 **L5 AI Brain 内核** 必须定位为"被 L4 调用的推理/上下文/规划/反思能力"，而非再造一套编排机。任务二（Lifecycle）应定义**全局 AI Core 生命周期（Boot/Ready/Busy/Waiting/Stopping/Recovering/Shutdown）**，与 `AgentRuntime` 的**任务级**状态机正交；任务四（Execution Pipeline）应定义**单次请求内的 Input→Reasoning→Tool→Reflection→Response 内环**，与 `AgentRuntime` 的**跨任务编排外环**正交。详见发现 F4。

### 3.4 Conversation Loop（对话主链路）
- 主对话链路在 `server.py` + `llm.py`，由 `FEATURE_EVENTBUS` 扇出。Phase A **不改对话主链路**（红线：不改 UI/对话）。
- **Phase A 影响**：Context Pipeline（任务三）是对话链路的"上游喂料"，可收敛但不改调用方。

### 3.5 Planner（规划）— 存在于 L2 Goal 引擎
- `goals.plan_goal`（`agent_runtime.py:127` 调用）负责目标拆解 Task；`task.note` 写入 `suggested_tool`（Round 2 格式，`_parse_suggested:693`）。
- LLM 派发 `_llm_dispatch`（`:344`）作回退。
- **Phase A 影响**：规划是 L2/L4 职责，**Phase A 不新建 Planner**；但 L5 的"推理/规划提示词组装"属于 Context Pipeline + Brain 内环，可在任务三/四内收敛。

### 3.6 Reflection（反思）— `reflector.py` 已存在
- `reflector.reflect(goal_id, executions)`（`agent_runtime.py:186`）产出 Execution Report + 经验沉淀，并经 `_feed_memory` 发射 `MEMORY_CREATED`。
- **Phase A 影响**：反思是 L5 Brain 内环一环，已部分实现；任务四（Execution Pipeline）可把"反思"标准化为内环固定阶段，复用 `reflector`，不重写。

### 3.7 Executor / Tool（执行 / 工具）⚠️ 两条执行路径
- `tools.execute_tool`（`:231`）——通用工具执行。
- `computer_executor.execute` + `VerificationLayer`（`:262` 注释）——电脑能力执行 + 验证，经 `guard.run` 闭环。
- `tools.TOOL_FUNCS`（`:313` 引用）、`tools.READONLY_TOOLS`（`:129` 引用，auto 种子）。
- **Phase A 影响**：两条路径已统一收口于 PermissionGuard，合规。任务五（Capability Registry）须把"能力元数据"与"工具函数"解耦注册，避免 `capabilities.py` 与 `capability_registry.py` 与 `tools.py` 三处各说各话。

### 3.8 Capability Registry（能力注册表）❌ 碎片化（发现 F2）
- **注册表 A** `capabilities.py`：上下文增强型能力（hotspot/prefetch），`build_context` 注入系统上下文（Phase 5 轻量对齐白龙马）。`active_capability_blocks`（`:67`）收集非空块。
- **注册表 B** `capability_registry.py`：电脑能力（read_file/…/delete/…），含风险等级 LOW/MEDIUM/HIGH/CRITICAL，映射 Policy 层级（Phase 7 Order 2）。
- 二者**无继承/聚合关系**，ID 空间可能撞名（如未来都加 `weather`）。
- **Phase A 影响（任务五核心）**：须按 ADR-007（统一 Extension）收敛为**单一 Capability Registry**，区分 `kind∈{context_enhancement, computer_action, tool}` 且共享 `id/label/risk/tier/build_or_execute` 元模型；旧两套保留适配器向后兼容（增量演进红线）。

### 3.9 Context Pipeline（上下文管道）❌ 碎片化（发现 F3）
- **路径 A** `context/LegacyContextBuilder`（builder.py:27）：五阶段 `Collect→Rank→Budget→Bundle→Build`（`:75`），来源注册 `MemorySource/UserModelSource/EpisodicSource/PersonalitySource/GoalSource/KnowledgeSource`（`:42-65`），默认**无限预算**（`:71`）。这是架构目标态的主管线。
- **路径 B** `capabilities.active_capability_blocks`（capabilities.py:67）：能力驱动的上下文块，与管线 A 并行注入，无排序/预算统一。
- **路径 C** `memory.build_system_prompt`（旧路径，FEATURE_CONTEXT_ENGINE=false 回退）：builder 注释（builder.py:13）明确其存在。
- **Phase A 影响（任务三核心）**：须以 `context/` 为**唯一**上下文管线（ADR 单一来源），把路径 B 的能力块改造成 `context/` 的一个 `Source`（如 `CapabilitySource`），路径 C 作为回退保留但不并行。预算档位 `BudgetTier`（models.py:33）已定义 T16K~T96K，应**启用真实裁剪**（当前默认无限，属未兑现能力）。

### 3.10 Knowledge（L6）/ Memory（L7）/ Goal（L2）/ Workflow（L3）— 已部分存在，Phase A 不新建
- Knowledge：`context/knowledge_source.py`（RAG 召回，FEATURE_KNOWLEDGE_RAG）、`knowledge.py`（Obsidian 层）。→ L6 属 Phase B，本报告仅登记。
- Memory：`memory.py`（单源，`build_system_prompt`）、`cognitive/`(user_model/episodic/extractor)。→ L7 属 Phase B。
- Goal：`goals.py`（目标生命周期，被 agent_runtime 调用）。→ L2 已存在。
- Workflow：DAG 工作流引擎未在本次扫描文件内显式出现（可能在 `goals`/`tasks` 内隐含）；属 L3，Phase C。
- **Phase A 影响**：以上**不在 Phase A 新建范围**；审计仅确认其存在以免重复。但 L5 Brain 内环会**只读聚合** Memory/Knowledge（架构 01 §5.2：Brain 上下文管道是只读聚合器），故任务三须通过 Source 接口消费，不持有状态。

### 3.11 Plugin / Extension（L8）— 仅电脑能力半实现
- 当前 Extension 概念仅落地于 `capability_registry` + `permission_guard` + `computer_executor`。MCP/Tool/Connector 统一抽象（ADR-007）尚未成形。
- **Phase A 影响**：任务五（Capability Registry）是统一 Extension 的**最小可行第一步**，但不必在本 Phase 完成 MCP 适配器全集（留给后续）。

---

## 4. Phase A 范围边界判定

| 维度 | Phase A **建设**（IN） | 已存在·须复用·**禁重复**（REUSE） | 已存在·**不在 Phase A**（OUT） |
|------|----------------------|--------------------------------|------------------------------|
| 生命周期 | 全局 AI Core 生命周期（Boot/Ready/Busy/Waiting/Stopping/Recovering/Shutdown） | `AgentRuntime` 任务级状态机（L4） | — |
| Context Pipeline | 统一为唯一 `context/` 管线；启用预算裁剪；能力块改造为 Source | `context/LegacyContextBuilder`、`memory.build_system_prompt`（回退） | — |
| Execution Pipeline | L5 Brain 内环（Input→Reasoning→Tool→Reflection→Response） | `reflector`、`tools.execute_tool`、`guard.run` | `AgentRuntime` 跨任务编排外环（L4） |
| State | 沿用 `applyEvent`(前端)/模块函数(后端)；定义 AI Core 内部状态契约 | AppState / goals / tasks 模块 | Memory 单源引擎（L7，Phase B） |
| Error Recovery | Checkpoint/Restart 框架（P15） | `agent_runtime` 重试 + 连续失败检测（部分） | Goal/Workflow 持久化快照（L2/L3，Phase B/C） |
| Health Check | 七子系统健康探针 + 就绪信号 | `_boot_ready_event`(server.py:2596) | — |
| Metrics | Latency/Memory/ToolCount/ContextSize/Recovery 指标埋点 | — | — |
| Logging | AI Core 统一日志规范 | — | — |
| Capability Registry | 单一注册表 + 元模型 + 适配器 | `capabilities.py`、`capability_registry.py`（适配） | MCP 全集（后续） |
| Boot Sequence | 子系统初始化顺序 + 就绪门控 | `server.main()`(2601) 启动骨架 | — |

---

## 5. 关键发现（Critical Findings）

- **F1 — SYSTEM 事件契约漂移（红线 #5 违约风险）**：`SYSTEM_EVENT_NAMES` 实测 14 个，超出冻结 `SYSTEM=8`；DOMAIN 71 吻合。扩展发生在冻结后且**无 Migration 文档**。`publish_system`（`:277`）强校验未知名，但"数量"未约束。
  → **处置**：Phase A 任务九/六新增系统事件前，先补一份《事件契约 Migration 说明》把 14 个 SYSTEM 事件正式入账，或回退多余事件；红线文档 `01` 的 "SYSTEM=8" 须同步修正为实际值，避免"冻结契约"与代码长期背离。

- **F2 — 双能力注册表（ADR-007 违和）**：`capabilities.py`(上下文增强) 与 `capability_registry.py`(电脑能力) 并存、无聚合。→ 任务五须合流为单一 Registry。

- **F3 — 三上下文装配路径**：`context/LegacyContextBuilder` + `capabilities.active_capability_blocks` + `memory.build_system_prompt`。→ 任务三须收敛为唯一管线，能力块降级为 Source。

- **F4 — 生命周期层级错配**：全局 AI Core 生命周期缺位，仅有 `AgentRuntime` 任务级状态机。任务二须明确定义**全局**生命周期（Boot→…→Shutdown），与 L4 任务级正交，避免 Phase A 在 L5 重造编排机。

- **F5 — FEATURE_AGENT_RUNTIME 默认语义三处不一致**：`agent_runtime.py` docstring、server.py:2686 注释均称"默认关闭"，但 `config.py:233` 默认 `"true"`。→ L4 Agent 实际默认在线，Phase A 的"不启动 Agent 引擎"边界须理解为"不**新建**/不**改** L4"，其既存在线态需在架构文档中如实记录。建议修正 docstring/注释与 config 一致。

- **F6 — 四个横切子系统空白**：Health Check / Metrics / Logging Standard / Crash Recovery 当前为零或散兵（仅 `agent_runtime` 有 try/except + 重试 + 连续失败清空队列）。任务六/七/九/八须从零建立，且须符合"Local First / 可崩溃恢复 / 不新开 God Module"。

- **F7 — Boot 序列散落 server.main()**：启动骨架（端口监听 + 后台自检 + `_boot_ready_event` 置位 + Agent Runtime 启动）全在 `server.py:2601-2690`。任务十（Boot Sequence）须把 AI Core 子系统初始化顺序外提为显式 Boot 编排（仍留在 server 启动上下文，不新开进程），并产出就绪信号契约。

---

## 6. 对 Phase A 后续任务的建议（供任务二~十参考）

1. **任务二 Lifecycle**：定义全局 AI Core 状态枚举（Boot/Ready/Busy/Waiting/Stopping/Recovering/Shutdown），用 `publish_system("agent_state")` 既有通道广播；与 `AgentRuntime` 状态机共存、不替代。
2. **任务三 Context Pipeline**：确立 `context/` 为唯一管线；新增 `CapabilitySource` 收纳 `capabilities.py` 块；默认预算从"无限"切到 `BudgetTier`（先 T32K）；保留 `memory.build_system_prompt` 回退。
3. **任务四 Execution Pipeline**：定义 L5 内环（Input→Reasoning→Tool→Reflection→Response），复用 `reflector`/`tools`/`guard`，不碰 `AgentRuntime` 外环。
4. **任务五 Capability Registry**：单一 Registry 元模型（`id/label/kind/risk/tier/build_or_execute`），两套旧注册表作适配器；裁决全委托 PolicyEngine。
5. **任务六 Health Check**：七子系统探针（EventBus / Permission / Memory / Context / LLM / Executor / Boot），复用 `_boot_ready_event` 作为就绪信号源之一。
6. **任务七 Metrics**：Latency（LLM/工具）、Memory Usage、Tool Count、Context Size、Recovery Count 五类埋点；指标经 `publish_system` 上报，不直写 UI。
7. **任务八 Recovery**：Checkpoint（目标/任务进度可持久化）+ Restart（从检查点恢复，不丢不重，P15）；先覆盖 `AgentRuntime` 任务级，再外溢全局。
8. **任务九 Logging**：统一 AI Core 日志规范（级别/格式/字段/落盘本地），与现有 `print("[runtime]…")` 散日志收敛；敏感字段（args/result）脱敏。
9. **任务十 Boot Sequence**：显式初始化顺序 + 就绪门控，外提自 `server.main()`；输出 Boot 契约文档。
10. **贯穿**：所有新增事件先登记 `DOMAIN/SYSTEM_EVENT_NAMES`（F1）；不向 `server.py`/`tools.py` 堆砌（F7/红线#7）。

---

## 7. 合规结论与 STOP

- ✅ 单 Runtime / 单 EventBus / 单 Permission / 单 Memory / Local First / 增量演进 **基础合规**。
- ⚠️ 三处需 Phase A 内处置：SYSTEM 契约漂移（F1）、双能力注册表（F2）、三上下文路径（F3）。
- ⚠️ 四横切子系统空白（F6）须本 Phase 从零建立。
- ✅ 本审计零代码改动，未扩大范围，未触碰 UI/Electron/Design。

**STOP**：本报告为 Phase A 任务一交付物。待 Review 批准后，方可进入任务二（AI Core Lifecycle）。未经批准不得修改任何代码 / 配置、不得进入实现阶段、不得扩大 Phase A 范围。
