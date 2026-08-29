# EXECUTION_DECISIONS.md

> **Xiao6 AI OS — Execution Platform Sprint v1.0**
> **文档类型：Phase 0 决策记录（Audit 之后、Implementation 之前敲定）**
> **身份：** Senior AI Systems Architect + Senior Python Architect + Senior Runtime Engineer
> **纪律基线：** Move Never Rewrite / Extract Never Redesign / Behavior Never Change / Single Execution Path/Entry/Context/Queue/State/EventBus/Permission/Metrics/Recovery/Reflection
> **配套审计基线：** `CURRENT_EXECUTION_ARCHITECTURE.md`（本目录）

---

## D0. 决策总表（一句话版）

| # | 决策 | 结论 | 红线影响 |
|---|---|---|---|
| D1 | 统一执行入口 | `Execution.run()` 为全项目唯一执行入口；`execute_tool` 仍是真正实现者（Router，不重写） | 无第二入口 ✅ |
| D2 | 事件命名契约 | spec 8 个 PascalCase 执行事件 → 映射为 `SYSTEM_EVENT_NAMES` 的 snake_case 系统事件（复用单 EventBus） | 不碰 DOMAIN/zz-events.js ✅ |
| D3 | 权限不对称收口 | `ExecutionPolicy` 100% 委托既有 `policy_engine`/`permission_guard`；chat 默认 NONE 保持现状绕过语义 | 无第二权限 ✅ |
| D4 | 异常语义 | `_execution_run` 为**透明路由**：异常原样上抛（记录后 re-raise），与直接调 `execute_tool` 逐字等价 | 行为不变 ✅ |
| D5 | 状态单一源 | `ExecutionState` 单例归一四套来源；`ExecutionQueue` 单例统一登记 | 单状态写源 ✅ |
| D6 | 取消/超时/重试 | 由 `ExecutionContext` 携带；默认 `retry=0`（不重试）、`timeout` 不注入 `execute_tool`、`cancel_token` 透传 `threading.Event` | 行为不变 ✅ |
| D7 | 恢复 | `ExecutionRecovery.recover()` 直接委托 `tasks.recover_tasks()`；checkpoint/resume/restart 仅簿记 | 无第二恢复 ✅ |
| D8 | Reflection | `ExecutionReflection` 追加写本地 `data/execution_reflections.jsonl`，非 Memory/Knowledge/DB/云 | 红线兼容 ✅ |

---

## D1. 统一执行入口（Single Execution Entry）

**问题（审计 §2/§12/§14）：** 5 处 `execute_tool` 裸调散落——`tools.run_one`(chat 主链路)、`server.py:2008`(chat 兜底)、`agent_runtime._execute_task`(goal)、`reflector.add_knowledge`、`social_inbound`(意图兜底)。权限语义分裂（goal 有闸门、其余无）。

**决策：**
- 新建 `ai_core/execution/api.py:run()` 作为**唯一执行入口**；内部仅调用 `execute_tool(name, args, allowed)`（M1 纯 Router）。
- 上述 5 处全部改为 `_execution_run(...)`，行为逐字等价（返回值、`allowed` 透传、异常语义一致）。
- `execute_tool` 本体**不改动**（仍为真正实现者），符合 Move Never Rewrite。
- 验证：`grep execute_tool\(` 全仓仅剩 `tools.py:3957`(定义) + `api.py:105`(内部 Router)。无第二入口残留。

---

## D2. 事件命名契约（Event Naming — SYSTEM 通道 vs DOMAIN 红线）

**冲突：** spec 要求 8 个执行事件（PascalCase：`ExecutionStarted` 等）。但 `eventbus.py` 硬纪律：`publish_domain` 拒绝未知事件名（`:234-235`），且 `DOMAIN_EVENT_NAMES` 须与前端 `zz-events.js` **逐字一致**，且「禁止新增同义事件名」（`:175-176`）。若新增 DOMAIN 名需改前端 = 违反「禁新增 UI」红线。

**决策：**
- 将 8 个执行事件映射为 `SYSTEM_EVENT_NAMES` 的 snake_case 系统事件（`execution_started` / `execution_updated` / `execution_completed` / `execution_cancelled` / `tool_started` / `tool_finished` / `retry_started` / `retry_finished`），已登记于 `eventbus.py:272-279`。
- 经 `publish_system` 扇出（单 EventBus SYSTEM 通道）。前端对未知 system 事件**忽略**，零 UI 改动、零 DOMAIN 契约变更。
- Chat SSE 保持兼容：chat 路径仍经 `server.py` 的 `emit` 闭包直推 `tool_start`/`tool_end`（前端已在用的协议），Execution 事件走 EventBus SYSTEM 通道，两者互不干扰。
- 映射表固化于 `events.py:SPEC_TO_IMPL`，供文档与调试追溯。

---

## D3. 权限不对称收口（Permission Asymmetry Closure）

**问题（审计 §14）：** goal/电脑能力路径经 `policy_engine`/`PermissionGuard`；chat/reflector/social_inbound 裸调绕过 PolicyEngine。

**决策（严禁改权限裁决逻辑本身，红线）：**
- 新建 `ExecutionPolicy` facade（单例）：`evaluate`/`request_approval` 逐字委托 `policy_engine`；`plan_computer_action`/`run_computer_action` 委托 `permission_guard.guard`（单一执行权限闭环）。**无任何第二套权限语义。**
- 调用方语义保持：
  - **chat / reflector / social_inbound** → `_execution_run` 默认 `permission=NONE` → 内核**不裁决**，与现状绕过 PolicyEngine **逐字等价**（不改变哪些工具被允许/拦截的现有结果）。
  - **goal** → `agent_runtime._execute_task` 仍**显式**调用 `policy.evaluate` + `policy.request_approval`（同一 PolicyEngine，语义不变），随后 `_execution_run(tool, args)`（permission=NONE，不二次裁决）。权限检查**恰好一次**，无双重裁决、无行为变化。
- 此收口动作是「路由收口」而非「新建权限系统」，完全兼容单 Permission 红线。

---

## D4. 异常语义（Exception Semantics — 透明路由）

**决策：** `Execution.run()` 是 `execute_tool` 的**透明路由**。生产态下 `execute_tool` 自身吞异常返字符串（tools.py:3966），永不抛出，故 `_execution_run` 返回该字符串，与直接调用**逐字等价**。

- 仅在「工具真抛出」（如测试模拟、工具实现 bug）时，`_execution_run` 在**记录失败指标/复盘后 re-raise**，将异常原样上抛给调用方（如 `agent_runtime._execute_task` 的重试回路），与直接调 `execute_tool` 的异常传播语义一致。
- 此决策修复了初版「内核吞异常返字符串」导致的回归测试 `test_execute_task_retry` 失败：原 `_execute_task` 依赖 `execute_tool` 抛出的异常触发其重试回路；初版内核吞掉异常使重试失效。改为 re-raise 后该测试恢复 PASS，且生产行为零变化。

---

## D5. 状态 / 队列单一源（Single State / Queue Source）

- `ExecutionState`（单例）：`_SOURCE_MAP` 把 tasks 表 / goals 表 / agent_runtime 内存态 / scheduler.TaskStatus 四套原子状态归一为统一 `SessionState` 枚举。仅作运行时单一视图与映射，**不改底层持久层**。
- `ExecutionQueue`（单例）：FIFO/Priority/Retry/Resume/Delay/Cancel 统一登记；默认同步执行，不替换任务持久层（tasks 表 / scheduler）。
- 二者均为薄收口层，不引入第二套状态机/队列。

---

## D6. 取消 / 超时 / 重试（ carried by Context, default no-op）

- 全部由 `ExecutionContext` 携带字段：`timeout` / `retry` / `cancel_token`。
- **retry**：默认 `0` → `ExecutionPolicy.should_retry` 返回 False → 不重试（与现状一致）；仅当显式 `retry>0` 且未达上限才在内核重试循环触发。
- **timeout**：**不注入** `execute_tool`（execute_tool 无 timeout 参数，且红线禁改其行为）；`ExecutionContext.timeout` 仅作统一字段预留，当前不阻断执行。
- **cancel**：`cancel_token` 为 `threading.Event` 时，`ExecutionPolicy.is_cancelled` 读取其状态；当前调用方均未传入，故为 no-op（行为不变）。`ExecutionQueue.cancel/pause/resume` 提供会话级控制接口。

---

## D7. 恢复（Recovery — 复用既有）

- `ExecutionRecovery.recover()` 直接 `return tasks.recover_tasks()`（无参、返回恢复计数），既是现状也是唯一恢复入口。
- `checkpoint/resume/restart` 仅作簿记（内存登记 + 队列状态流转），不替换底层持久层恢复语义。`recover()` 在进程启动时由 `main` 调用（与现状一致）。

---

## D8. 复盘（Reflection — 非 Memory/Knowledge）

- `ExecutionReflection` 追加写本地 `data/execution_reflections.jsonl`（环形保留最近 200 条内存 + 落盘）。
- **不是** Memory（不进 `memory.py`）、**不是** Knowledge（不进 `knowledge/`）、非 DB、非云、非网络。仅一次执行总结，不影响返回值。

---

## D9. 实施纪律回执（Implementation Discipline Acknowledgement）

- ✅ Single Execution Path / Entry / Context / Queue / State / EventBus / Permission / Metrics / Recovery / Reflection。
- ✅ Move Never Rewrite（`execute_tool` 未改；agent_runtime 仅改路由）。
- ✅ Extract Never Redesign（组件从既有调用方行为抽取，无重新设计）。
- ✅ Behavior Never Change（返回值、`allowed`、异常语义、权限结果全部逐字等价）。
- ✅ Import Refactor Only（5 处 import 改为 `_execution_run`，无新增逻辑）。
- ✅ 禁新增 AI 功能 / Plugin / MCP / Workflow / Agent / Prompt / Tool / UI / DB / EventBus / Permission / Runtime / Memory / Knowledge / 网络通信 / 云能力 / 机会性优化。

---

*决策敲定版本：2026-08-06 · 与 `CURRENT_EXECUTION_ARCHITECTURE.md` 配套。所有决策均可在 `G:/xiao6/xiao6-ui/ai_core/execution/` 与已编辑的集成文件中逐行核对。*
