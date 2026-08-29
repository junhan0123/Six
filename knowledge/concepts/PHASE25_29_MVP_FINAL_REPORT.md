---
id: know-phase-25-29-mvp
type: concept
---
# Phase 25–29 MVP 最终产品化收口与端到端验收报告

> 状态：**通过全部五道验收闸门**  
> 版本：PersonalAIOS Kernel v0.29.0  
> 报告日期：2026-08-10  
> 执行者：Senior Developer（高级开发工程师）  
> 禁令声明：**本阶段未启动 Phase 30，未新增任何 Kernel Manager。**

---

## 1. 任务目标

把已有的后端能力（Phase 25.2 Conversation、26.2 Research、29.1 Reasoning，加 Phase 23 执行管线）收口成一个**可用的 Personal AI OS MVP**，由**一个真实用户任务**穿过完整闭环：

```text
User → Electron UI → Conversation → CEO → Planner → Goal → Research → Reasoning → Coding/Workflow → Authorization → Approval → ExecutionRequest → Orchestrator → ExecutionSandbox → Result → Memory → UI Push
```

同时坚守以下硬约束：

| # | 硬约束 | 结果 |
|---|---|---|
| 1 | 不新增 Kernel Manager | ✓ 未出现 SuperManager/MegaManager/AIManager |
| 2 | 唯一合法执行链 `Orchestrator → ExecutionSandbox` | ✓ 扫描器/运行期/真窗口三层验证 |
| 3 | 不改执行沙箱红线 | ✓ Node 不入 Renderer、terminal 不入 Agent |
| 4 | 不引入 Jest/Vitest | ✓ 只用 `core/test/Harness.js` |
| 5 | 不破坏既有 37 个测试套件 | ✓ `npm run test:all` EXIT=0 / FAIL=0 |
| 6 | **禁止启动 Phase 30** | ✓ 未启动 |

---

## 2. 本次改动清单

| 文件 | 改动类型 | 说明 |
|---|---|---|
| `phase25_29_mvp_e2e_test.js` | Gate 1 交付 | 16 section / 11446 断言 MVP 矩阵验收 |
| `scripts/mvp-e2e-smoke.js` | 新增 Gate 5 | 71 步真实闭环 E2E |
| `scripts/mvp-health-check.js` | 新增 | 4 维 23 项日常红线体检 |
| `ui/shared/mvp-state-projection.js` | 新增 | 只读状态投影聚合层 |
| `ui/electron/app-api.js` | 增强 | 新增 `getProjection()` 方法，边界层盖 `_readOnly`/`_source` 戳 |
| `main.js` | 增强 | 在 Phase 29.1 演示后追加 MVP 演示收口 |
| `phase25_ui_test.js` | 修复 + 增强 | `UI_API_METHOD_COUNT` 由 23 → 24，并断言新增者为 `getProjection`、方法名不含执行语义 |
| `scripts/check-consistency.js` | 增强 | 把 `UI_API_METHOD_COUNT` 纳入真源管理，避免未来再次漂移 |

---

## 3. 五道验收闸门结果

### Gate 1 — MVP 矩阵验收：`phase25_29_mvp_e2e_test.js`

| 维度 | 结果 |
|---|---|
| 命令 | `node phase25_29_mvp_e2e_test.js` |
| section 数 | 16（§1–§16） |
| 断言数 | **11,446**（≥ 10,000） |
| FAIL | **0** |
| EXIT | **0** |
| 耗时 | ~150 ms |

覆盖范围：会话输入矩阵（42 条）、Planner 90 任务 + 依赖图无环/无自环、Research 31 主题语料纯度、Reasoning 120 轮循环场景决定性、Reject/Approve 各 30 次、Memory 60 轮、Failure Recovery 40 轮、投影矩阵 240 轮（覆盖 i%7/i%5/i%3 全部相位）、二次复现不变量等。

### Gate 2 — 源码隔离扫描：执行权 Token = 0

| 扫描器 | 结果 |
|---|---|
| `scan-ui-execution.js` | Execution Token = 0 · exit=0 |
| `scan-reasoning-execution.js` | Execution Token = 0 · exit=0 |
| `scan-plugin-runtime-execution.js` | Execution Token = 0 · exit=0 |
| `scan-plugin-bridge-execution.js` | Execution Token = 0 · exit=0 |
| `scan-execution-pipeline.js` | Execution Token = 0 · exit=0 |

并额外复跑全部 **12 个源码扫描器**，Token 全为 0。

### Gate 3 — 跨文件常量一致性：`npm run check:consistency`

| 真源 | 值 |
|---|---|
| package.json.version | 0.29.0 |
| EventBus 唯一事件常量 | 370 |
| test:all 套件段数 | 37 |
| test:all 链路末端套件 | phase25_ui_test.js |
| UI API 对外方法数 | 24 |

结果：**✓ 全部派生点与真源一致** · EXIT=0

> 本轮把 `UI_API_METHOD_COUNT` 新纳入真源管理，正是因为最初它被遗漏导致 Gate 4 出现 1 个 FAIL。

### Gate 4 — 全量回归：`npm run test:all`

| 项目 | 值 |
|---|---|
| 套件段数 | 37 |
| `[FAIL]` 行数 | 0 |
| EXIT | 0 |
| 顶层套件 PASS 合计 | 79,515 |
| 顶层套件 FAIL 合计 | 0 |

### Gate 5 — 真实 E2E 闭环：`scripts/mvp-e2e-smoke.js`

| 项目 | 值 |
|---|---|
| 命令 | `PAIOS_MODEL=heuristic node scripts/mvp-e2e-smoke.js` |
| 闭环站数 | 15 |
| 步骤数 | 71 |
| 通过 / 失败 | 71 / 0 |
| 通过率 | 100% |
| EXIT | 0 |
| 证据链 | `docs/gate5/mvp-e2e-evidence.json`（15 条链路记录） |
| 真实用户任务 | “帮我把这个项目的调研结论整理成一份文档，并更新到 src/report.js” |

---

## 4. 执行权红线核验

### 4.1 源码扫描层

全部 12 个扫描器 `Execution Token = 0`（Gate 2 已给出明细）。

### 4.2 运行期自证

`scripts/mvp-health-check.js` 维度 B「运行期自证」逐层调用 `hasExecutionAuthority()`，全部返回 `false`：

- UIApplicationAPI
- ConversationManager
- ResearchAgent
- ReasoningLoop
- AgentRuntime
- WorkflowManager
- PluginManager / Bridge
- GoalManager

### 4.3 真实窗口自证

真实 Electron 窗口走查（Step 11）显示：

```text
✓ 渲染进程无 Node 能力（require/process/module/Buffer 全无）
✓ 桥只暴露约定的命名空间
✓ 桥自述零动手权  runAuthority=false
✓ 窗口里找不到任何动手面入口
```

窗口截图保存于：

- `docs/gate5/ui-smoke-approvals.png`
- `docs/gate5/ui-smoke-tasks.png`

### 4.4 唯一执行入口

Gate 5 证据链终点站：

```json
{
  "from": "human-gate(approve)",
  "to": "execution-sandbox",
  "fact": "sandboxRequestId=req-msncujwf-1"
}
```

MVP Health Check 同时断言：`stage === "submitted"` 时执行权归属沙箱。

---

## 5. 真实 E2E 闭环关键证据

证据文件：`docs/gate5/mvp-e2e-evidence.json`

链路快照：

| 链路节点 | 物证 |
|---|---|
| boot → ready | `kernel=0.29.0` |
| user → conversation | `session=conv-msncujvw-1` |
| conversation → ceo | `intent=generic` |
| ceo → planner | `tasks=1` |
| planner → research | `sources=2` |
| research → reasoning | `status=completed` |
| reasoning → coding | `files=3` |
| coding → authorization | `decision=requires-approval` |
| authorization → human-gate(reject) | `task task-2 → failed` |
| human-gate(reject) → human-gate(approve) | `approval apr-3 → approved` |
| human-gate(approve) → execution-sandbox | `sandboxRequestId=req-msncujwf-1` |
| execution-sandbox → result | `state=QUEUED` |
| result → memory | `records=16` |
| memory → ui | `events 1→70` |
| ui → authority-check | `all layers zero-authority` |

该证据链用**真实模块**装配，而非测试替身；所有中间对象（会话、任务、审批、执行请求、记忆记录、事件）均来自内核真实状态。

---

## 6. 失败、定位与修复

### 6.1 Gate 4 1 个 FAIL：UI API 方法数漂移

- 现象：`25.1-TRANSLATE-TABLES` 报 `UI Application API 方法 23 个（期望 23，实际 24）`
- 根因：Step 4 新增 `getProjection()` 后，`phase25_ui_test.js` 中的硬编码数字未同步；该常量此前未被 `check-consistency.js` 登记。
- 修复：
  1. 把测试断言从 23 更新为 24，并补充说明「第 24 个口子是只读投影入口 getProjection」。
  2. 新增约束：方法名不得含 `exec/execute/run/spawn/invoke/shell/terminal/write/delete/kill` 语义。
  3. 把 `UI_API_METHOD_COUNT` 纳入 `scripts/check-consistency.js` 真源管理。
- 验证：故意把 24 改回 23 跑一致性校验，校验器准确报出 2 处漂移；再用 `--fix` 自动还原。

### 6.2 Electron 窗口走查首次 CDP 超时

- 现象：`Runtime.enable` 60 秒超时。
- 根因：当前 shell 已被外层沙箱包住，Chromium 自己的 OS 级进程沙箱无法启动，连带 GPU/网络服务进程异常，渲染进程卡死。
- 修复：设置 `PAIOS_UI_NO_CHROMIUM_SANDBOX=1` 重跑；`webPreferences.sandbox` 红线未被破坏。
- 验证：走查 30 步全绿。

---

## 7. 二次复现

| 项目 | 一次 | 二次 | 结论 |
|---|---|---|---|
| Gate 1 | 11446 / 0 FAIL | 11446 / 0 FAIL | 不变量可复现 |
| Gate 5 | 71 / 71 · 100% | 71 / 71 · 100% | 真实闭环可复现 |
| Health Check | 23/23 绿 | 23/23 绿 | 日常红线体检可复现 |
| Gate 3 | EXIT=0 | EXIT=0 | 常量一致性可复现 |
| Gate 4 | 37 段 / 0 FAIL | 37 段 / 0 FAIL | 全量回归可复现 |

---

## 8. 未启动 Phase 30 声明

本次会话严格限制在 Phase 25–29 MVP 收口范围内：

- 未新增任何 Kernel Manager。
- 未新增阶段目录（Phase 30、31…）。
- 未新增 `phase30_*` 测试文件。
- 未修改 `package.json` 版本号之外的长期路线。
- 唯一改动是**把现有能力接成闭环并加固边界**。

---

## 9. 交付物列表

| 交付物 | 路径 |
|---|---|
| Gate 1 MVP 矩阵验收 | `phase25_29_mvp_e2e_test.js` |
| Gate 5 真实闭环 E2E | `scripts/mvp-e2e-smoke.js` |
| 日常红线体检 | `scripts/mvp-health-check.js` |
| 只读投影聚合层 | `ui/shared/mvp-state-projection.js` |
| UI 边界 API 增强 | `ui/electron/app-api.js` |
| MVP 演示收口 | `main.js` |
| 一致性校验增强 | `scripts/check-consistency.js` |
| 窗口 E2E 截图 | `docs/gate5/ui-smoke-approvals.png`、`docs/gate5/ui-smoke-tasks.png` |
| Gate 5 证据 JSON | `docs/gate5/mvp-e2e-evidence.json` |
| 本报告 | `PHASE25_29_MVP_FINAL_REPORT.md` |

---

## 10. 结论

PersonalAIOS Phase 25–29 MVP 收口任务**通过全部五道验收闸门**：

1. **Gate 1**：11,446 断言、0 FAIL、EXIT=0。
2. **Gate 2**：12/12 源码扫描器 `Execution Token = 0`。
3. **Gate 3**：跨文件常量一致性 EXIT=0。
4. **Gate 4**：37 套件全量回归 0 FAIL、EXIT=0。
5. **Gate 5**：真实任务走完完整闭环，71/71 步、100% PASS、EXIT=0。

执行权红线、渲染层隔离、人在环闸门、沙箱唯一执行入口等核心约束均经源码扫描、运行期自证与真实 Electron 窗口三重验证。**Phase 30 未启动**。

MVP 就绪。
