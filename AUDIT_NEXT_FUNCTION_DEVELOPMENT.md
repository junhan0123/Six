# 小6 · 下一阶段功能开发 — 第一阶段交付物（VERIFY / 功能矩阵 / Runtime 链路审计）

> 审计性质：**纯只读盘点 + 链路审计**。本阶段**未修改任何源码、未启动服务、未改动 UI**。
> 审计时间：2026-08-16（本地）｜项目根：`G:\xiao6`｜版本：`1.4.0`（VERSION 文件）
> 方法：以当前真实源码为准，禁止凭历史记忆判断。所有结论附 `file:line` 证据。

---

## 0. 审计前提与关键偏差（VERIFY 结论）

### 0.1 项目真实位置
提示词假设项目在 WorkBuddy session 目录或 `C:\Users\...\Xiao6`，但真实工程在 **`G:\xiao6`**（含 `.git`、2892 个 `.py`、前端 `index.html`/CSS/JS、Electron 壳、docs、knowledge vault）。`C:\Users\Administrator\Xiao6` 仅是少量 scratch 脚本（voiceorb、audit_db 等），**非主工程**。

### 0.2 Git 状态（真实）
- 分支 `main`，`Your branch is based on 'origin/main', but the upstream is gone`。
- 工作树有大量 `.md` 报告被标记为 **deleted**（BUG_WALL.md、CHANGELOG.md、CURRENT_STATE.md、CURRENT_PHASE.md、README.md、PHASE* 报告等）——即交接协议要求的**第一阅读文档（PROJECT_STATUS / CURRENT_STATE）当前不在工作树**，新 AI 无法按协议顺序入职。
- 存在 `.git.corrupted-backup-20260814-101703/`（历史 git 损坏备份）与残留的 `.git/index.lock`（0 字节，Aug-14）。
- 最近提交：`f9967f2 chore: 清理 Companion 注释与测试夹具中的「玄岱」指代 → 小6`。

### 0.3 提示词模块清单 vs 真实代码的偏差（重要）
提示词把架构设想为 `server.py / config.py / Agent Runtime / Context Engine / Planner / Capability Registry / Tool Runtime / EventBus / Memory / GoalSystem / WorldModel / MCP Host / Policy Engine / Provider / Voice-TTS / Dependency / Startup`。真实代码的对应情况：

| 提示词概念 | 真实存在？ | 真实位置 / 说明 |
|---|---|---|
| server.py | ✅ | `xiao6-ui/server.py`（170KB，HTTP 后端） |
| config.py | ✅ | `xiao6-ui/config.py`（42KB，含 FEATURE_* 开关） |
| Agent Runtime | ✅ | `agent_runtime.py`（59KB）— 但它是**目标编排覆盖层**，默认不接管 chat |
| Context Engine | ✅ | `context/`（builder/ranker/budget/sources/facade） |
| Planner | ⚠️ 部分 | `computer_action/planner.py`（仅电脑动作）；通用规划= `goals.plan_goal` + `capability_os` composer/router/matcher；默认 chat **无显式 Planner**（LLM function-calling） |
| Capability Registry | ✅（双份） | 权威=`capability_os/registry.py`；遗留视图=`capabilities.py` |
| Tool Runtime | ✅ | `tools.py`（189KB）+ `tool_factory.py` + 统一入口 `ai_core/execution/api.py:run` |
| EventBus | ✅ | `eventbus.py`（唯一 `EventBus`，无第二实现） |
| Memory | ✅（双份） | 线上=`memory.py`；实验=`memory_v2/`（flag 默认关） |
| GoalSystem | ✅ | `goals.py` + `goal_decision_engine.py` |
| WorldModel | ⚠️ 仅电脑域 | 无通用 WorldModel；只有 `COMPUTER_WORLD_SYNC` / `PerceptionWorldModelObserver`（`verification.py:135`，属电脑操作子系统） |
| MCP Host/Executor | ✅ | `mcp_host/`（host/executor/browser/transport/config/runtime） |
| Policy Engine | ✅ | `policy_engine.py`（模块级 `evaluate`/`request_approval`） |
| Provider/Model Runtime | ✅ | `provider_registry.py` + `llm.py`（live）；`identity/provider.py` 是人格注入（非模型运行时） |
| Voice/TTS Runtime | ⚠️ 双后端 | `server._tts_sovits`（GPT-SoVITS）+ `edge_tts` 兜底（`server.py:2989,3067,3102`）——**与"单 GPT-SoVITS TTS"指令冲突** |
| Dependency Manager | ⚠️ 仅前端 | 无 `dependency_manager.py`；只有 `dependency-manager.js`（前端）与 `self_diagnosis/` 诊断 |
| Startup/Boot/Diagnosis | ✅ | `start-xiao6.bat`、`beta_boot.py`、`first_launch.py`、`self_diagnosis/checker.py` |

### 0.4 治理文档与代码代差
`ARCHITECTURE_MAP.md`（v1.0）只覆盖到 **Phase 8（电脑操作层）**；`DEVELOPMENT_PROGRESS.md` 记录到 v1.3，标注 "Phase 9 未启动"。但**真实代码已演进到 Phase 40+**（Capability Platform、MCP Host、Context Engine、Memory V2、Session Checkpoint、Goal Round-Replan）。即：**治理文档严重落后于代码**，交接协议引用的 `PROJECT_STATUS/CURRENT_STATE/GOLDEN_STATE` 多处缺失或已删除。

---

## 1. FUNCTION-INVENTORY（功能真实状态表）

分类：A 完成正常 / B 完成部分失效 / C 已开发未接入 / D 重复 / E 废弃 / F 规划 / G 缺失。

### AI / Agent
- **对话（Context + LLM 流式）**：**A**。默认路径 `server.py:2504 build_context_prompt` → `run_fc_loop`（`tools.py:3355`）→ 流式 LLM。有 `test_pure` 等通过。
- **意图识别**：**B**。普通 chat 走 `tools.detect_intent`（`tools.py`，`test_pure` 覆盖）；但 `intent_gateway.run_intent_gateway` 仅在 `FEATURE_GOAL_DECISION` 且 runtime 已运行时介入（`server.py:2563`）。
- **Planner（任务拆解/选能力）**：**C/B**。通用 Planner 仅存在于**目标模式**（`agent_runtime._run_goal` + `capability_os` composer/router），默认 chat 由 LLM 自行 function-calling，**无确定式 Planner**。
- **多轮 / 长任务**：**B**。`run_fc_loop` 支持多轮工具调用；但长任务/后台执行依赖 `agent_runtime`（默认关）。
- **错误恢复**：**B/C**。目标模式有 replan（`agent_runtime.py:303-306` `_MAX_REPLANS`/`_do_replan`）；默认 chat 无恢复，仅 best-effort 后台线程（`compress_memory`）。

### Memory
- **Memory（memory.py）**：**A**。线上记忆层（`build_system_prompt`/`build_context_prefix`/`save_turn`/`compress_memory`）。但 `test_memory.py` **collection ERROR**（导入不存在的 `worldcup` 模块）。
- **Memory V2**：**C（flag 关）**。`memory_v2/` 不被 `server.py`/`agent_runtime.py` 引用，仅 `context/builder.py:100-102` 在 `MEMORY_V2_ENABLE` 时条件引入，**默认关闭**——属第二/实验实现。
- **记忆读取/写入/压缩**：**A**（memory.py）。
- **记忆与 Agent Runtime 真实连接**：**B（薄）**。仅 `context.budget.ContextBudget` 被 `agent_runtime` 使用（agent 报告），记忆主体由 chat 路径的 `save_turn/compress_memory` 直接落库，**agent_runtime 不直接读写 memory**。

### Goal / Task
- **GoalSystem（goals.py + goal_decision_engine.py）**：**A**。数据+决策层，`intent_gateway.py:60` 接线 → `runtime.submit_goal`（`server.py:1939`）。
- **goals.db 持久化 / 状态机**：**A**。`agent_runtime` 收敛到四终态 `completed/failed/max_steps_exceeded/blocked_by_policy`（`agent_runtime.py:153`）。`phase44_session_checkpoint` 13 passed。
- **失败/恢复/重规划**：**B**。`phase46_goal_round_replan` 19 passed/3 skip（replan 验证）；但无独立单测覆盖 `policy_engine`/`permission_guard`。

### World Model
- **通用 WorldModel**：**G（缺失）**。无统一世界模型；仅有电脑域 `COMPUTER_WORLD_SYNC` / `PerceptionWorldModelObserver`（`verification.py:135`，`perception_runtime.py:154`）。

### Capability
- **Capability Registry（capability_os/registry.py）**：**A（权威）**。被 `agent_runtime`/`permission_guard`/`mcp_host`/`os_bridge`/`skills`/`computer_action` 广泛引用。`phase40-capability-foundation` 测试**因文件名带点未被默认 pytest 收集**。
- **capabilities.py（遗留视图）**：**D（重复/遗留）**。仍被 `capability_os/execution_mapping.py:68-69` 消费 `CAPABILITIES[id].build_context`，属历史视图，应与 Registry 收敛。

### Tools
- **Tool Registry/Runtime**：**A（统一入口）**。`ai_core/execution/api.py:run` 为全项目唯一执行入口，强制 `policy.evaluate(default_deny=True)`（`api.py:84`）+ `request_approval`（`api.py:92`）。`tools.py` 持有 `TOOL_FUNCS`/`execute_tool`。**无 `test_tools` 单测**。
- **逐个 Tool 校验/超时/日志/权限**：**B**。权限由 `ai_core.execution` 统一兜底；但单 Tool 级超时/结构化错误日志缺统一框架（散落在各 `TOOL_FUNCS`）。

### MCP
- **MCP Host/Security Boundary**：**A（边界完整）**。`mcp_host/config.py:19 COMMAND_ALLOWLIST`、`:31 ALLOWED_BROWSERS`、`:72 validate` 强制 stdio + 白名单；`executor.py:28 _authorize` → `policy_engine.evaluate(default_deny=True)`（`:40`），`confirm` 级一律 `request_approval`（`:48`），`auto_approve` **不绕过** confirm。**但 phase41/42/47.4 测试因文件名带点未被默认 pytest 收集**——保护形同虚设。

### Voice / TTS
- **TTS 架构**：**B（双后端，与指令冲突）**。存在 **GPT-SoVITS（`server._tts_sovits`，9880）** 与 **edge-tts 兜底**（`server.py:2989,3067,3102`，`FEATURE_TTS_STREAM` 默认开）。提示词要求"保持 GPT-SoVITS 单 TTS，不要重新引入 Edge TTS"——当前**代码含 edge-tts 兜底**，需确认是否降级为纯 Sovits 或明确兜底为 legacy。
- **思考过程不进 TTS**：**A**。`agent_runtime.py:879-884` 仅对"目标完成汇报"走 TTS，且受 `FEATURE_TTS_STREAM` 控制；思考/工作过程不进 TTS。
- **ASR/KWS/唤醒词**：**A/C**。`asr.py`/`kws.py`/`wakeword.py` 存在，但依赖 torch/funasr（可选，缺失降级）。

### Provider / Model
- **Provider 探测 / Model 配置 / 失败恢复**：**A**。`provider_registry.py` + `llm.py`（`agnes_completion`/`resolve_provider`）。`test_provider_platform` 9 passed。

### Startup / Dependency / Diagnosis
- **启动 / 依赖诊断 / Provider 检测 / Runtime Ready / 错误诊断 / 自动恢复**：**B/A**。`self_diagnosis/checker.py` 做模块健康检查；`recovery_advisor.py` **仅给建议，绝不自动修复/启动未知服务**（红线）。`beta_health.py` 探测语音/ASR。**自动恢复=缺失**：无自动修复，仅建议。

### 测试体系
- **单元/集成/E2E/回归**：**B（存在但健康度差）**。51 个 `.py` + 23 个 `.js` 测试；但 **17 个 `.py` 文件名带点（`*.test.py`）默认 pytest 不收集**；`test_memory.py` 导入损坏；Context 引擎/persona 有真实失败。详见 §7/§8。

---

## 2. RUNTIME-CONSOLIDATION（Runtime 收口情况）

### 2.1 存在**两套执行范式**（核心收口缺口）
- **范式① 默认 chat（同步流式）**：`/api/chat` → `_handle_chat`（`server.py:2488`）→ `build_context_prompt`（Context Engine）→ `run_fc_loop`（`tools.py:3355`）→ `execute_tool_calls`（`:3290`）→ `_execution_run` = `ai_core.execution.run`（`:21,3311`）→ `policy.evaluate(default_deny=True)` → `execute_tool` → 结果。
  - **Intent Gateway / Planner / Capability Registry 在此路径默认不介入**；LLM 自己决定调哪个 Tool。
  - 安全边界**有**（`ai_core.execution.run` 强制 policy）。
- **范式② 目标模式（异步后台）**：`FEATURE_GOAL_DECISION=True` 且 `agent_runtime.runtime._running` → `intent_gateway` → `agent_runtime`（Planner：`plan_goal` + `capability_os` composer/router）→ Capability Registry → Permission Guard → Executor → EventBus → Memory。
  - 这是提示词设想的"真正连通 Agent Runtime"，**但默认不激活**，需单独 `start`（`server.py:3326`）。

**结论**：小6"已连通的 Agent Runtime"存在于范式②，但用户默认命中范式①（更简单、绕过 Planner/Capability Registry 的函数调用）。这就是"模块彼此孤立、未串通"的根源——**不是模块缺失，而是默认路径未走统一编排层**。

### 2.2 安全边界（Policy / Permission）
- ** intact **。`ai_core/execution/api.py:run` 是全项目唯一执行入口，强制 `policy.evaluate(default_deny=True)`（`api.py:84`）与 `request_approval`（`api.py:92`）；`ai_core/execution/policy.py` 是 `policy_engine`/`permission_guard` 的纯门面（`:7,34,48,52`），**无第二策略系统**。MCP 路径额外经 `capability_os.execute_capability` → `permission_guard`。
- 默认 chat 路径经 `_execution_run`（= `ai_core.execution.run`），**同样过 policy 门**——§六.4 要求满足。

### 2.3 EventBus-first
- **基本满足**。`eventbus.py:56` 唯一 `EventBus`，`bus=EventBus()`（`:156`）；`ai_core/execution/events.py:51` 复用 `eventbus.publish_system`（明确"禁止第二 EventBus"）。但**默认 chat 路径几乎不发领域事件**（仅 goal 模式与电脑操作子系统发 `PERCEPTION_*`/`COMPUTER_WORLD_SYNC`/`GOAL_*`）。

### 2.4 无第二 Runtime / Memory / EventBus / Permission
- **满足**（详见 §5 重复检测）：无第二 EventBus、无第二 Permission/Policy、Memory 第二实现（`memory_v2`）已 flag 关、Capability 第二视图（`capabilities.py`）仍被消费待收敛。

---

## 3. CAPABILITY-MATRIX（Capability / Tool / Policy / Runtime 对应）

| 能力类型 | 注册/发现 | 决策/选能 | 安全闸门 | 执行入口 | 结构化结果 | 测试 |
|---|---|---|---|---|---|---|
| 原生 Tool（`TOOL_FUNCS`） | `tools.py` 字典 | LLM function-calling（chat）/ `capability_os` 路由（goal） | `ai_core.execution.run`→`policy.evaluate` | `execute_tool`（`tools.py:3982`） | 字符串/JSON（非统一 schema） | `test_pure`✅；无 `test_tools` |
| MCP 外部能力（`external.mcp.*`） | `mcp_host/host.py` | `capability_os` | `executor._authorize`→`policy.evaluate`+`request_approval` | `mcp_host.MCPExecutor` | JSON | phase41/42/47.4 ⚠️未被收集 |
| 电脑动作（Computer Action） | `capability_os` + `computer_action` | `os_bridge`（`GROUP_COMPUTER_ACTION`） | `permission_guard.guard` | `computer_action/executor.py` | Observation | phase8 测试 ⚠️未被收集 |
| Skill | `skills.py`/`skills/` | `tools.execute_skill` | 经 `execute_tool`→policy | `skills.execute_skill` | 文本/指令包 | `test_skills`✅(8) |
| Knowledge | `knowledge_runtime/engine.py` | `/api/knowledge` | 无 | — | 检索结果 | 无后端单测 |
| Goal（目标） | `goals.py` | `goal_decision_engine`→`agent_runtime` | `policy`/`permission`（执行步） | `agent_runtime._run_goal` | 四终态 | phase44/46 ✅ |

**关键缺口**：原生 Tool 返回为自由文本/JSON，**无统一结构化结果契约**；Tool 级超时/权限/日志无统一框架。

---

## 4. MEMORY-INTEGRATION（Memory 与 Runtime 实际连接）

- **线上记忆 = `memory.py`**（`save_turn`/`compress_memory`/`record_learning`/`build_system_prompt`）。
- **与 chat 路径连接：强**（每次对话落 `save_turn`、后台 `compress_memory`、习惯 `personalization`）。
- **与 agent_runtime 连接：薄**。`agent_runtime` 仅用 `context.budget.ContextBudget`（`agent_runtime.py:180`）；记忆读写主要由 chat 路径直接完成，**agent_runtime 不主动读写 memory**。
- **Context Engine 与 Memory**：`context/` 通过 `memory_recall_source`/`personal_context_source` 等从 memory 取数，`build_context_prompt` 汇编；但 `memory_v2/` 默认关，形成**两套记忆路径并存**（线上 memory.py + 实验 memory_v2，靠 `MEMORY_V2_ENABLE` 切换）。
- **结论**：Memory 与 Runtime 的连接是"够用但不统一"——chat 路径强，agent_runtime 弱；第二实现 `memory_v2` 需明确"废弃或扶正"，否则持续漂移。

---

## 5. TASK-AUTOMATION（Task / Goal / Event / Recovery 状态）

- **Goal 生命周期**：`goals.py` + `goal_decision_engine.py`，四终态完备（`agent_runtime.py:153`）。
- **Background Task**：≈ `agent_runtime` 目标循环（需 `_running`）。默认 chat **无后台任务概念**（同步流式）。
- **Recovery**：
  - 目标级 replan：`_do_replan`/`_MAX_REPLANS`（`agent_runtime.py:303-306`）——**有**。
  - Session Checkpoint：`phase44` Facade，checkpoint 仅存引用、resume 不重执行——**有**（13 passed）。
  - 自诊断：`self_diagnosis/recovery_advisor.py` **仅建议，不自动修复**（红线）——**部分**。
  - 通用"保存状态/避免重复执行/记录失败原因"的**自动恢复框架：缺失**。
- **Event-driven**：`EventBus` 存在，但默认 chat 不发领域事件；事件驱动复用度低。
- **Scheduler**：顶层 `scheduler.py` 为**生产孤儿**（仅测试引用，`proactive_agent/scheduler.py` 注释"既有 scheduler 单例未被 server 启动"）。

---

## 6. API-CONTRACT（新增/修复的 API）

> 仅审计阶段已验证的端点；**完整 API 枚举是下一阶段任务**（需系统扫描 `server.py` 所有路由）。

| API | 真实位置 | 状态 | 说明 |
|---|---|---|---|
| `POST /api/chat` | `server.py:2488 _handle_chat` | A | 默认对话主链路（SSE 流式）。Input: `{messages, session_id, images?, temperature?, reasoning?}`；Output: SSE `data: {...}`；异常降级普通聊天。 |
| `GET /api/agent-runtime` (state) | `server.py:1873` | A | 返回 `agent_runtime.runtime.get_state()`（需 import）。 |
| `POST .../agent-runtime/start` | `server.py:3326` | A | `agent_runtime.runtime.start()` 激活目标模式。 |
| `POST .../submit_goal` | `server.py:1939` | A | `runtime.submit_goal(title, description)`。 |
| `POST /api/knowledge` | `server.py:562,1832` | A/C | `knowledge_runtime` 驱动；**无后端单测**。 |
| Intent Gateway 事件 | `intent_gateway.py` | B | 经 `publish_domain()` 单一来源；仅 `FEATURE_GOAL_DECISION` 激活。 |

**契约缺口**：原生 Tool 无统一输入/输出/错误/超时/权限/生命周期/Event/Persistence 契约（返回自由文本）；MCP 有契约但测试未跑。

---

## 7. TEST-EVIDENCE（真实测试结果）

> 环境：`G:\xiao6\xiao6-ui\python\python.exe`（3.11.9）。为出真实证据，已在该 python 安装 `pytest` 并实跑。

| 测试文件 | 结果 | 分类 |
|---|---|---|
| `test_pure.py` | **15 passed** | 通过 |
| `test_context_serializer_cache.py` | **12 passed** | 通过 |
| `test_context_dedup_scope.py` | **6 passed** | 通过 |
| `test_provider_platform.py` | **9 passed** | 通过 |
| `test_skills.py` | **8 passed** | 通过 |
| `phase44_session_checkpoint.py` | **13 passed** | 通过 |
| `phase46_2_tool_baseline.py` | **9 passed** | 通过 |
| `phase46_goal_round_replan.py` | **19 passed / 3 skip** | 通过 |
| `test_context_engine.py` | **3 failed / 12 passed** | 真实失败（legacy 对齐） |
| `test_context_facade.py` | **3 failed / 2 passed** | 真实失败 |
| `test_context_ranker_budget.py` | **1 failed / 18 passed** | 真实失败 |
| `test_context_sources.py` | **1 failed / 14 passed** | 真实失败 |
| `test_goal_decision_engine.py` | **8 failed / 29 passed** | 真实失败（persona） |
| `test_memory.py` | **ERROR（collection）** | 测试缺陷（import `worldcup` 不存在） |
| `phase40-capability-foundation.test.py` | **ERROR（collection）** | 测试缺陷（文件名带点） |
| `phasec_native_runtime.test.py` | **ERROR（collection）** | 测试缺陷（文件名带点） |

**失败根因（已确认）**：
1. **Context 引擎"与 legacy 逐字节一致"测试失败**：`test_context_engine.py:131` 期望 `legacy_prompt == 'FIXED_EMPTY_USER_PROMPT'`（**占位 stub**），新 builder 返回真实 prompt（`【当前状态 · 实时推导...`）。即"字节一致"保证**未被真实校验**（基线为 stub）。
2. **persona style 覆盖失效**：`persona_engine.get_persona_prompt({"style":"storytelling"})` 仍渲染 `concise`——`_resolve()`（`persona_engine.py:57-69`）优先 `get_provider().get_behavior_style()`（identity.json），**忽略显式 style 参数**（真实产品 bug）。
3. **`test_memory.py` 导入 `worldcup` 模块不存在**：测试文件损坏。
4. **17 个 `*.test.py` 文件名带点，默认 `pytest` import-mode 无法收集**（见 §8）。

---

## 8. REGRESSION（历史能力是否保持）

### 8.1 真实回归风险
- **Context Engine 一致性回归**：提示词 §十一要求保护既有能力；当前 `FEATURE_CONTEXT_ENGINE=True`（线上主路径），但其"与 legacy 逐字节一致"的自证测试**已全部失败**——说明该不变式已破坏或测试已 stale，需立即定性（产品变更 vs 测试过期）。
- **Persona 覆盖 bug**：`get_persona_prompt` 的 style 覆盖失效（`test_goal_decision_engine` 8 失败），影响人格一致性。

### 8.2 历史 Phase 测试"保护"形同虚设（重大发现）
提示词 §十一点名保护：**Phase 47.3 MCP Security Boundary、Phase 46 Recovery、Capability Platform、Memory V2、Beta Integration、既有 Tool Policy、Browser/MCP E2E**。但：
- `run_all.py`（`tests/run_all.py:43`）用 `pytest tests -q --continue-on-collection-errors`，**默认 import-mode** 下：
  - `phase40-capability-foundation.test.py`、`phase41-mcp-browser.test.py`、`phase42_e2e_browser.py`（注：此文件名无点，但 phase41/40 有）、`phase47.4-electron-security.test.js` 等 **17 个 `*.test.py` 因文件名带点无法收集，被 `--continue-on-collection-errors` 静默跳过**。
  - 即：**Capability Platform（phase40）、MCP Browser/Security（phase41/42/47.4）的后端测试在标准运行器下从不执行**——"不得降低安全标准/删除测试"的要求在 CI 层面无实际守护。

### 8.3 已验证保持的能力
- Provider 平台（`test_provider_platform` 9✅）、Skills（`test_skills` 8✅）、Tool baseline（`phase46_2` 9✅）、Goal replan（`phase46_goal_round_replan` 19✅）、Session checkpoint（`phase44` 13✅）、Context 序列化/去重（18✅）均通过。

---

## 9. UI-INTEGRATION-CONTRACT（仅描述后续 UI Agent 需接入的接口）

> 本阶段**不修改 UI**（UI 由 DeepSeek 重做）。以下为后端暴露给前端的契约摘要，供 UI Agent 对接：

1. **对话**：`POST /api/chat`（SSE）。前端订阅 `data:` 增量；支持 `images`（多模态）、`session_id`、`reasoning`。
2. **状态/事件**：前端只读投影经 `EventBus` 契约（`eventbus.py` `DOMAIN_EVENT_NAMES`/`SYSTEM_EVENT_NAMES` 与 `zz-events.js` `EVENTS`/`SYSTEM_EVENTS` 逐字对齐）。关键事件：`GOAL_*`（目标生命周期）、`PERCEPTION_*`、`COMPUTER_WORLD_SYNC`、`AGENT_RUNTIME_*`（`started/idle/planning/executing/reflecting`）。
3. **Agent Runtime**：`GET /api/agent-runtime`（state）、`POST .../start`、`POST .../submit_goal`。前端据 `get_state()` 展示运行时状态。
4. **能力/工具**：Capability 列表经 `capability_os/registry.py`（`discovery.dispatch_tool_list`，`agent_runtime.py:841`）；权限/风险在 `capability_os/registry.py` 的 `Permission` 枚举与 `risk_of`。
5. **记忆/人格**：`persona_engine.get_persona_prompt`（`style` 覆盖当前**有 bug**，UI 暂勿依赖 style 覆盖）；记忆读取走 `memory.py` API。
6. **TTS**：`server._tts_sovits`（GPT-SoVITS 9880）为主；`edge_tts` 为兜底。**UI 语音播放不应假设单一后端**；思考过程绝不进 TTS。

---

## 10. NEXT-STEP（仅真正必要的下一阶段任务）

按"最小必要 + 可回滚 + 已记录"原则，建议下一阶段（IMPLEMENT）只做以下事项，按优先级：

1. **【P0·测试健康】修复测试收集与损坏用例**（不降安全标准）：
   - 重命名 17 个 `*.test.py` 为 `-test.py`（或加 `conftest.py` 设 `importmode=importlib`），使 Capability/MCP 测试可被 `pytest` 收集；在 `run_all.py` 加 `--import-mode=importlib`。
   - 修复 `test_memory.py` 对不存在 `worldcup` 的导入。
   - 定性 Context 引擎"逐字节一致"失败：若是产品变更则更新基线 stub；若是回归则修复 builder。

2. **【P0·产品 bug】修复 `persona_engine` style 覆盖**（`persona_engine.py:57-69`）：显式 `style` 参数应优先于 identity.json behavior_style，否则 `get_persona_prompt({"style":...})` 静默失效。

3. **【P1·Runtime 收口】统一默认 chat 与目标模式的执行范式**：将默认 `/api/chat` 的工具调用也经 `capability_os` 路由（或至少在 chat 路径显式接入 Planner 概念），消除"模块孤立"。**此步必须保持安全边界不降级**（`ai_core.execution.run` 已兜底，可在此基础上收敛）。

4. **【P1·TTS 架构澄清】** 明确 GPT-SoVITS 单 TTS 指令与现有 `edge_tts` 兜底的关系：要么移除 edge-tts 兜底（纯 Sovits），要么把兜底显式标记为 legacy 且默认关，避免与"单 TTS"指令冲突。

5. **【P2·重复收敛】** 明确 `memory_v2/` 与 `memory.py` 的权威（扶正其一、废弃其一）；`capabilities.py` 遗留视图收敛进 `capability_os/registry.py`；删除生产孤儿 `scheduler.py`（或接回 `proactive_agent/scheduler.py`）。

6. **【P2·治理补完】** 恢复/重建 `PROJECT_STATUS.md` / `CURRENT_STATE.md`（交接协议第一阅读文档已缺失）；将 `ARCHITECTURE_MAP.md` 更新至 Phase 40+（Capability Platform / MCP Host / Context Engine / Memory V2）；清理工作树 deleted 的 `.md` 报告或恢复。

7. **【P3·API 契约补全】** 系统扫描 `server.py` 全部路由，为原生 Tool 建立统一输入/输出/错误/超时/权限/生命周期/Event/Persistence 契约（当前返回自由文本，缺结构化结果）。

> **本阶段最终判断（§十七标准）**：小6**已具备**一个真正连通的 Agent Runtime（范式②：Intent→Context→Planner→Capability→Policy→Tool/MCP→EventBus→Memory→Response，且安全边界 intact），但**默认用户路径（范式①）绕过 Planner/Capability Registry**，导致"模块未串通"的观感。链路在目标模式下可跑通、异常可 replan，但默认 chat 路径的"理解→规划→选能→执行→状态/记忆→恢复"并不完整。**因此本阶段不能宣称'小6已是连通 Runtime'——需完成上述 P0/P1 后方可。**
