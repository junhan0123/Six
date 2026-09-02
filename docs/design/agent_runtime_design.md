# 小6 → JARVIS 级智能体 · Phase 8 架构设计（已定案 v2）

> 状态：**scope 已锁定，待编码确认。** 日期：2026-08-01
> 作者：Senior Developer（高级开发工程师）
> 决策来源：用户路线图 v1 + 实盘代码审计 + 用户定案修订（本次）

---

## 0. 一句话结论

小6已不是 0→1，而是到了 **Agent Runtime 整合阶段**。第一阶段**不新建 Planner / Executor / EventBus**（它们都已存在且比预期先进），只新建「编排层 + 授权内核 + 反思层」，把已有能力编排成一个**持续运行、能完成一件事的 Agent**。

> **复用全部已有底座，只补真正空白的三块，跑通一次 Goal→Plan→Execute→Reflect 闭环。**

---

## 1. 实盘底座盘点（已存在，直接复用，不推倒）

| 模块 | 文件 | 现状 | 第一阶段动作 |
|---|---|---|---|
| 通信脊柱 | `eventbus.py` | topic pub/sub + 重试 + 死信 + 单例 `bus` | **复用零改** |
| 策划服务 (Planner) | `goals.plan_goal()` | 已调 `agnes_completion` 把目标拆 3–8 步 | **升级**（补工具建议输出） |
| 执行服务 (Executor) | `tools.py` + `sandbox.py` + `tool_factory.py` + `db.tool_audit` | `execute_tool()` 中央分发器；`READONLY_TOOLS` 集合；危险命令拦截；内网/云元数据硬阻断；脱敏审计 | **升级**（加依赖/重试/超时编排），不新建 |
| 委托先例 | `agent_delegate.py` | `delegate(task, confirm=False)` + `config.AGENT_DELEGATE_AUTO` 已是「confirm 才执行」模式 | **同源先例**，Policy Engine  generalizes 它 |
| 前端弹窗通道 | `app.js` `xiao6_event==="modal"` → `openModal()` | 现成 SSE 弹窗渲染 | **复用**做审批框 |
| 世界模型雏形 | `data/worldaware_cache.json` | 已缓存世界感知 | 第二阶段再升 |

**关键纠偏（与用户路线图 v1 的差异）**：v1 把 Planner / Executor / Guard 都标「从零新建」，但实盘里策划与执行侧都已落地，「Execution Guard 已经开始」在执行层确实是真的（危险命令/内网/审计都有）——缺的只是 **Agent 级授权闸门**（该不该自动做）与**编排状态机**与**反思层**。

---

## 2. 第一阶段 Scope（已锁定 · 仅三块新建 + 集成）

### 2.1 `agent_runtime.py` — 编排状态机（核心新建）
- 管理 `Goal → Plan → Execute → Reflect` 生命周期，是**纯状态机，不做任何业务逻辑**。
- 常驻「目标驱动循环」（区别于 `proactive` 的 cron，它是目标驱动）。
- 状态机：
  ```
  IDLE → PLANNING → EXECUTING → REFLECTING → (IDLE | PLANNING)
  ```
- 经 EventBus 与所有已有模块通信，**不直调、不阻塞对话主链路**（`conversation_loop` 照常）。
- 多 Goal 排队、并发上限、超时/取消。

### 2.2 `policy_engine.py` — 授权内核（新建，最高价值，改名自 execution_guard）
> 你定案：不要叫 Guard，叫 **Policy Engine**——它不只判「能不能执行」，而是统一裁决：允许 / 需审批 / 危险 / 超预算 / 重复 / 越权。未来所有 Agent 都走它。

**四级权限模型（你定的）：**
| 等级 | 行为 | 触发后动作 |
|---|---|---|
| `auto` | 自动执行 | 直接 `tools.execute_tool()` |
| `confirm` | 弹窗确认 | 发 `modal(agent_approval)` → 用户点确认 → 执行 |
| `session` | 本会话记住 | 本次会话内该工具已批准则等同 `auto` |
| `never` | 永久禁止 | 永不执行（持久化黑名单） |

**每个工具声明 `permission`**（Policy Engine 内 `TOOL_POLICY` 注册表）：
- 自动种子：所有 `READONLY_TOOLS` 成员 → `auto`（直接复用 `tools.READONLY_TOOLS`，零重复）。
- 默认：非常读工具 → `confirm`（写操作/外部副作用一律先问）。
- 显式覆盖表：`dangerous`（如 `kill_process`、含危险参数的 `run_shell`）→ `never`；与 `sandbox.is_dangerous_command` / `tool_factory` 网络拦截**复用**，不重实现。
- 裁决函数：`evaluate(tool, args, context) -> Decision(auto|confirm|block)`，综合：工具声明 + 参数（命令内容）+ 用户设置 + 当前状态。
- `session` 缓存：当前进程内存 `set`，首次 `confirm` 通过后加入。
- `never` 黑名单：持久化（建议 `data/policy_store.json`，零密钥、纯本地）。

**Confirm 闭环（复用前端 modal 通道）：**
1. `policy_engine` 判定 `confirm` → 生成 ticket + 预览 payload，通过 EventBus 发 `{"xiao6_event":"modal","kind":"agent_approval","ticket":...,"tool":...,"args_preview":...}`。
2. `app.js` 渲染审批卡（工具名 + 参数预览 + 「批准 / 拒绝」按钮）。
3. 按钮 → `POST /api/agent/approval?ticket=...&decision=approve|reject`。
4. 后端用 `threading.Event` / `Future` 唤醒 `agent_runtime` 中挂起的执行。

### 2.3 `reflector.py` — 反思层（新建，差异化能力）
- 目标/任务结束后自动反思：完成度？遗漏？更好方案？是否更新知识库？
- 产出 `Execution Report`（成功 / 失败 / 经验），经验沉淀回记忆/规则/知识（**仅写入被允许的存储**）。
- 这是普通 Agent 没有、你强调的长期竞争力来源。

### 2.4 集成（不新建，只接线）
- **策划服务**：`agent_runtime` 调 `goals.plan_goal(goal_id)`；升级点——让 plan 额外标注每个 Task 建议调用的工具名（写入 task 备注）。
- **执行服务**：每个 Task 的工单经 `policy_engine.evaluate` 后，调 `tools.execute_tool(name, args)`，自然落入 `tool_audit`。
- **EventBus**：runtime 发布进度/状态事件（`agent:state`、`agent:approval_request`）；订阅对话主链路的 Goal 创建事件。

---

## 3. 命名澄清（避免新建冗余文件）
- `execution_guard.py` → **`policy_engine.py`**（授权内核，未来涵盖 allow/approve/danger/budget/dedup/authorize）。
- `goals.plan_goal` 概念上升为 **Planning Service**（内部 = LLM + 规则 + 历史经验 + Memory，实现不限制）。
- `tools.*` + `sandbox` + `tool_factory` 概念上升为 **Execution Service**（Task→Tool/Skill/Agent/Workflow 都可接）。
- 二者第一阶段**不单独成文件**，只做「升级 + 接线」。

---

## 4. 明确不做（后移至第二阶段及以后）
按你定案，下列**全部推迟**——Agent Runtime 没跑通前都是空中楼阁：
- ❌ Multi Agent（内部 Research/Coding/… Agent 群）
- ❌ World Model 2.0（`world/` 体系）
- ❌ Capability 重构（`capabilities/` manifest 体系）
- ❌ Vector DB / 混合知识系统
- ❌ 新 Memory 体系
- ❌ Computer Vision / 屏幕理解 / 摄像头
- ❌ UI 大改（仅加**最小**审批弹窗 + 遥测状态点）
- ❌ Observer 升级（先让小6学会完成一件事，再让它主动找事做——否则只会产生越来越多未闭环的 Goal）

---

## 5. 闭环验收标准（Phase 1 唯一里程碑）
不以「代码写完」为完成标志，以**完整闭环稳定跑通**为准。

**最小场景**：用户：「整理这个项目并生成总结。」

系统须自动完成：
1. 创建 Goal（`PLANNING`）。
2. 用现有 Planning Service 拆解 Task（升级后带工具提示）。
3. 依次调用已有 Tools 完成任务（经 `tools.execute_tool`）。
4. 遇高风险操作触发 Policy Engine → `confirm` 弹窗 → 用户批准。
5. Reflector 输出 `Execution Report`（成功/失败/经验）。
6. 更新 Memory / Knowledge（仅允许写入的部分）。
7. Goal 标记 `completed`，回到 `IDLE`。

> 这条链路稳定跑通 = 小6完成从「对话助手」到「Agent」的第一次真正跃迁。后续 Observer / World Model 2.0 / 多 Agent 都建立在这个稳定内核之上。

---

## 6. 与现有架构的兼容约束（不破坏）
- 不动 `conversation_loop`（对话主链路照常）。
- 不引入新依赖（纯标准库）。
- `FEATURE_AGENT_RUNTIME` 门控（默认 env **off**，瞬切，符合 P5 纪律）；`AGENT_RUNTIME_AUTO` 控制默认是否自动跑闭环（默认 off，需显式目标触发）。
- Agent loop 跑后台线程，经 EventBus 通信，不阻塞对话。
- 所有 Agent 动作走 `tool_audit` 审计。
- Policy Engine 的 `never`/`dangerous` 复用 `sandbox.is_dangerous_command` + `tool_factory` 网络拦截，不重复实现。
- `agent_delegate.py` 的 confirm 逻辑第一阶段**保留不动**，后续轮次再统一收敛到 Policy Engine。

---

## 7. 实施计划（分轮，遵守 P5/P6 纪律：每轮 ≤3 已有 / ≤5 新文件 / ≤500 行，纯本地 git）

### Round 1 — 内核 + 开关（后端）
- 新建 `policy_engine.py`（权限注册表 + `evaluate` + ticket/审批 await + session/never 缓存）。
- 新建 `agent_runtime.py`（状态机 + loop + EventBus 接线 + 调 `goals.plan_goal` / `tools.execute_tool`）。
- 新建 `reflector.py`（基础反思 + 经验沉淀）。
- 修改 `config.py`：加 `FEATURE_AGENT_RUNTIME`、`AGENT_RUNTIME_AUTO`、`AGENT_POLICY_DEFAULT`（默认 off）。

### Round 2 — 接线 + 端点
- 修改 `goals.py`：`plan_goal` 升级输出「建议工具」到 task 备注（小幅）。
- 修改 `server.py`：新增 `POST /api/agent/goal`（建目标并触发 runtime）、`GET /api/agent/state`（遥测用）、`POST /api/agent/approval`（解 confirm）；启动时按 `FEATURE_AGENT_RUNTIME` 起 runtime 线程。

### Round 3 — 最小前端（仅必要 UI）
- 修改 `app.js`：响应 `modal(kind=agent_approval)` 渲染审批卡（批准/拒绝 → POST approval）；遥测面板新增「Agent 状态」点。
- （可选）`index.html` 遥测区加一个 `#agentState` 元素。
- 不改视觉体系、不摊大饼。

### 验证
- 跑通第 5 节闭环场景，输出 `Execution Report`，确认 `confirm` 弹窗出现且批准/拒绝生效，`never` 工具被拦，`tool_audit` 有痕。

---

## 8. 待确认（仅剩 1 个实质开放项）
1. **审批 UI 形态**：默认建议复用现有 `modal` 通道弹「批准/拒绝」卡（与天气/热点弹窗同源，零新机制）。是否同意？
2. 其余你已拍板：默认开关 off、`confirm` 弹窗、Observer 暂缓、World Model 不升、闭环验收——均按你定案落地。

> 确认第 1 项后，我开始按 Round 1→3 编码（纯本地 git，每轮提交，后端重启验证）。
