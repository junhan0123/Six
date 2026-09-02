# INTENT_LIFECYCLE_LOG · Phase 6 · Order 5 — Intent 生命周期专项日志

> 本文件记录 Intent Gateway 在 Phase 6 Order 5 中引入的 **6 个 Intent 生命周期事件** 的契约、状态投影、以及真实运行的完整证据链。
> 纪律：单一来源（`zz-events.js` == `eventbus.DOMAIN_EVENT_NAMES`，各 38 名）；不绕过 `publish_domain()` / Event Bridge / AppState / Galaxy State。

---

## 1. Intent 生命周期事件契约

| 事件名 | 触发点（后端 `intent_gateway.run_intent_gateway`） | 关键 payload | 前端 AppState 行为 |
|--------|------------------------------------------------------|--------------|--------------------|
| `INTENT_RECEIVED` | 入口收到用户文本，生成 `intent_id` | `intentId, text, source, ts` | `intents[intentId] = {type:'intent', status:'Received', source, createdAt}` |
| `INTENT_ANALYZING` | 进入 GDE 识别前 | `intentId` | `status='Analyzing'` |
| `INTENT_CLASSIFIED` | `GoalDecisionEngine.ingest()` 返回 | `intentId, classification, action, confidence, title, reason` | `status='Classified'` + 记录置信度/分类 |
| `INTENT_ACCEPTED` | `action∈{create, propose, resume}` | `intentId, action, needsConfirm` | `status='Accepted'` |
| `INTENT_REJECTED` | `action=skip` 或低置信 | `intentId, reason` | `status='Rejected'`（不建 Goal） |
| `INTENT_CONVERTED_TO_GOAL` | `action=create` 且 `submit` 前 | `intentId, goalId:null` | `status='Converted'` |

**状态机（纯数据，AppState 内 `intents` 子树）：**
```
Received → Analyzing → Classified → { Accepted → Converted →(GOAL_CREATED 回填 targetGoal)
                                   └ Rejected }
Accepted(needsConfirm) 为挂起态，待用户确认后转 Converted
```

**独立性原则：** Intent 子树与 `goals / agents / tasks / memory / knowledge` 完全独立，reducer 互不覆写；通过 `GOAL_CREATED.payload.intentId` 做**晚关联**（懒链接 `targetGoal`），不产生第二套事件。

---

## 2. Galaxy State 纯数据投影

`galaxy-state.js` 仅新增：
- `RUNTIME_MAP` 的 Intent 6 态：`Received / Analyzing / Classified / Accepted / Rejected / Converted`。
- `getIntentNodes()`：过滤 `nodes` 中 `type==='intent'` 返回，纯数据，**无任何 Three.js / DOM / 动画 / 视觉代码**。

投影链：Intent Node（Pending）→ 当 `GOAL_CREATED` 携带 `intentId` 时，银河侧可建立 `Intent Node → Goal Node` 的关联投影（由 Order 5 之后的银河交互层消费，本 Order 只保证数据就绪）。

---

## 3. 真实运行证据（Order 5 集成测试）

运行命令（系统 py3.11，因 `embed.py` 依赖 numpy）：
```
python tests/phase6-order5.integration.test.py
```
结果：**PASS (passed=17, failed=0)**，exit=0。

### 场景 A — create 路径（用户指定用例「分析当前项目状态」等价链路）
```
捕获序列（A）：
INTENT_RECEIVED -> INTENT_ANALYZING -> INTENT_CLASSIFIED -> INTENT_ACCEPTED
-> INTENT_CONVERTED_TO_GOAL -> GOAL_CREATED -> agent_state -> AGENT_CREATED
-> GOAL_STARTED -> GOAL_UPDATED -> agent_state -> AGENT_STARTED -> AGENT_THINKING
-> TASK_CREATED -> TASK_CREATED -> agent_state -> GOAL_RUNNING -> AGENT_WORKING
-> TASK_STARTED -> TASK_RUNNING -> GOAL_UPDATED -> TASK_COMPLETED -> TASK_STARTED
-> TASK_RUNNING -> GOAL_UPDATED -> TASK_COMPLETED -> agent_state -> AGENT_THINKING
-> REFLECTING -> MEMORY_CREATED -> MEMORY_STORED -> MEMORY_LINKED -> agent_state
-> GOAL_UPDATED -> AGENT_COMPLETED -> GOAL_COMPLETED -> goal_completed
```
断言要点（全部 PASS）：
- 必需事件齐发（真实运行，非伪造）；
- 顺序铁律 `INTENT_RECEIVED < INTENT_ANALYZING < INTENT_CLASSIFIED`；
- 顺序 `INTENT_CLASSIFIED < INTENT_ACCEPTED < INTENT_CONVERTED_TO_GOAL`；
- **铁律 `INTENT_CONVERTED_TO_GOAL < GOAL_CREATED`**（转换早于 Goal 创建）；
- `GOAL_CREATED < AGENT_CREATED < GOAL_COMPLETED`；
- 全部 Intent 事件共享同一 `intentId`；
- `GOAL_CREATED` 携带真实 `intentId` 与 `goalId`；
- Intent 事件名全部命中 `DOMAIN_EVENT_NAMES`（单一来源纪律）；
- 真实 DB：Goal 状态 = `completed`，`knowledge_docs` 已落库（Memory 链路贯通）。

### 场景 B — skip 路径
```
捕获序列（B）： INTENT_RECEIVED -> INTENT_ANALYZING -> INTENT_CLASSIFIED -> INTENT_REJECTED
```
断言：`action=skip`；仅 4 个 Intent 事件；无 `GOAL_CREATED`；未创建 Goal。

### 场景 C — propose 路径
```
捕获序列（C）： INTENT_RECEIVED -> INTENT_ANALYZING -> INTENT_CLASSIFIED -> INTENT_ACCEPTED
```
断言：`action=propose`；`INTENT_ACCEPTED` 标记 `needsConfirm=true`；无 `GOAL_CREATED`（不自动建 Goal，待用户确认）。

---

## 4. 前端状态机验证（Order 5 FE 单测）

运行：`node tests/phase6-order5.frontend.test.js` → **PASS 19/19**。
覆盖：6 个 Intent reducer 的状态流转、`targetGoal` 晚关联、`intents` 子树独立不覆写五套状态、`getIntentNodes()` 投影、`BATCH_5` 导出、REJECTED 路径、以及 `ZZIntentGateway.dispatch` 仅触发 `fetch` 不直写状态。

---

## 5. 结论

- Intent 生命周期事件已从「概念」变为**真实、可观测、可测试**的统一状态流一环。
- 用户意图 → 意图识别 → Goal Decision Engine → Goal → Agent → Task → 执行 → 事件 → 状态 的完整链路在场景 A 中**端到端真实贯通**。
- 单一来源、事件顺序铁律、前端不直连三项纪律均经测试固化。

**Order 5 已完成并验证。停止，不进入 Order 6，等待批准。**
