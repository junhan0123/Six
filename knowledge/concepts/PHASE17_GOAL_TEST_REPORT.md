---
id: know-phase-17-0-goal-system
type: concept
---
# Phase 17.0 — Goal System 验收报告

> PersonalAIOS **v0.20.0**｜目标系统（最高管理抽象层）
> 验收时间：2026-08-07｜结论：**全部通过，0 FAIL**（已二次复现验证）

---

## 一、一句话结论

目标层已经建成，并且**它一行执行代码都没有**。

`core/goal/` 下 27 个逻辑模块、28 个源文件，负责理解目标、组织目标、维护 10 态生命周期、
产出 Workflow / Project / Team / Execution 四类**纯数据蓝图**，然后就停手。
真正动手的权力仍然只有一个入口：`Orchestrator → ExecutionSandbox`。

---

## 二、验收指标对照

| 验收项 | 要求 | 实际 | 结论 |
| --- | --- | --- | --- |
| 逻辑模块数 | 27 | **27** | ✅ |
| 源文件数 | — | 28（27 登记 + `GoalPure.js`） | ✅ |
| 生命周期状态 | 10 态 + 非法转移异常 | 10 态 + `IllegalGoalTransitionError` | ✅ |
| 禁止注入类目 | ≥ 60 | **77** | ✅ |
| 源码执行 token | 0 | **0**（`scan-goal-execution.js` 扫描 28 文件） | ✅ |
| 新增 EventBus 事件 | 18 | **18**（`EVENTS` 总数 225 → 243） | ✅ |
| 测试段数 | ≥ 70 | **80** | ✅ |
| 断言数 | ≥ 15000 | **18697** | ✅ |
| 本套件 FAIL | 0 | **0** | ✅ |
| Phase 5–16 回归 | 0 FAIL | **0 FAIL**（23 套全绿） | ✅ |
| 版本号 | v0.20.0 | **0.20.0** | ✅ |

---

## 三、模块清单（27 个）

**核心实体与状态机**
`Goal`、`GoalState`、`GoalLifecycle`、`GoalContext`、`GoalHistory`

**理解与规划**
`GoalParser`（10 类目标识别 + 优先级/风险分级）、`GoalPlanner`、`GoalBlueprint`

**治理**
`GoalPriority`、`GoalPolicy`、`GoalApproval`、`GoalConstraint`、`GoalRisk`、`GoalStakeholder`

**度量与评估**
`GoalEvaluator`（六维）、`GoalMetrics`、`GoalMilestone`、`GoalResult`

**存取与呈现**
`GoalRegistry`、`GoalSnapshot`、`GoalSerializer`、`GoalMemoryWriter`（7 分区只写）、`GoalTemplate`、`GoalDependency`、`GoalTag`

**基础设施**
`GoalPure`（纯数据工具，打破循环依赖）、`GoalManager`（统一门面）

---

## 四、状态机

```
CREATED ─→ UNDERSTANDING ─→ PLANNING ─→ WAITING_APPROVAL ─→ READY ─→ ACTIVE
                                 └────────→ READY ─────────┘         ↓  ↑
                                                                  PAUSED
                                                                     ↓
                                                                COMPLETED ─→ ARCHIVED
```

- 除三个终态外，**任何状态都可被取消**（用户有权在目标真正启动前反悔）。
- `ARCHIVED` 是唯一无出边的终态。
- 10×10 全组合可达性 + `assertGoalTransition` 全组合，共 454 条断言逐格校验。

---

## 五、执行隔离（本阶段的硬骨头）

三道锁，缺一不可：

1. **构造期硬闸** — 所有 26 个类在 `constructor` 第一行调用 `assertNoGoalInjected(opts, label)`，
   77 类执行句柄键一旦出现（不论值是对象 / 函数 / 数组 / 字符串）立即抛错。
   验收矩阵：**26 类 × 77 键 × 4 形态 = 8008 条断言，全部拒收成功**。
   显式写 `null` / `undefined` 视为"我没注入"，放行——否则调用方连默认配置都写不了。
2. **运行期声明** — 每个类 `hasExecutionAuthority()` 恒返回 `false`。
3. **源码期扫描** — `scan-goal-execution.js` 对 28 个文件做 token 级正则扫描，
   `exec/spawn/child_process/require(/fetch(` 等一律计数，结果 **0**。

另外还有一层纯数据保证：所有对外产物（`toJSON` / Blueprint / 快照 / 记忆写入）
都经 `pureGoalCopy` 净化——**函数 → null，类实例 → 普通对象**，`hasFunctionDeep` 深度探测为 `false`。

---

## 六、测试分段（80 段 / 18697 断言）

规模最大的十段：

| 段 | 名称 | 断言 |
| --- | --- | --- |
| 8 | 26 类 × 77 注入 × 4 形态构造期拒收全矩阵 | 8008 |
| 14 | 100 个 Goal 走完整主干生命周期 | 1100 |
| 26 | GoalParser 批量解析压测 | 1050 |
| 9 | 无参构造与安全键放行 | 698 |
| 39 | GoalEvaluator 批量评估压测 | 600 |
| 67 | GoalManager 60 目标全生命周期压测 | 492 |
| 70 | `core/goal/` 源码零执行 token | 452 |
| 43 | GoalRegistry 200 目标压测 | 413 |
| 79 | GoalRisk 风险登记 | 411 |
| 45 | GoalSnapshot 批量快照压测 | 400 |

覆盖面：模块清单 → 状态机 → 注入硬闸 → 实体 → 解析 → 规划 → 蓝图 → 治理 →
评估 → 存取 → 记忆 → 纯数据工具 → Manager 端到端 → EventBus → 源码扫描 →
接线（Orchestrator / main.js / package.json）→ 架构红线 → Phase 5–16 回归 → 稳定性幂等。

---

## 七、过程中修掉的真实缺陷（10 个）

这一轮不是"写测试凑数"，是真的把模块打出了坑：

| # | 模块 | 问题 | 修复 |
| --- | --- | --- | --- |
| 1 | `GoalState` | 只有 `ACTIVE` 能取消，用户无法在启动前反悔 | 除终态外全部允许 `CANCELLED` |
| 2 | `GoalState` | 构造只收字符串，与全层 opts 风格不一致 | 兼容 `{ value }` 且同样过硬闸 |
| 3 | `GoalLifecycle` | `WAITING_APPROVAL` 误播为 `GoalPlanned`（事件重复） | 复用既有 `ApprovalRequested` |
| 4 | `GoalManager` | `goal_context` / `goal_history` 两个记忆分区从未写入 | 补 `writeContext` / `writeHistory`，7 分区全活 |
| 5 | `GoalParser` | "写一篇技术博客"→CUSTOM、"部署上线"→CUSTOM | 补 `WRITING` / `OPERATION` 关键词，去重 |
| 6 | `GoalParser` | "紧急！立刻修复严重故障"只判到 MEDIUM | 放宽紧急度/业务价值/风险信号正则 |
| 7 | `GoalHistory` | `recordStateChange(to, reason, from)` 参数序反直觉，导致历史记录中 from/to 颠倒 | 改为 `(from, to, reason)` 并同步调用点 |
| 8 | `GoalDependency` | 只认 `source/target`，传 `from/to` 被静默吞掉 | 增加别名 |
| 9 | `GoalConstraint` | 6 个操作符全塌成 `lte`（switch 复制粘贴错误），`operator` 键从不读取 | 补 `CONSTRAINT_OPERATORS` + `neq`，`op`/`operator` 双认 |
| 10 | `GoalTag` / `GoalContext` / `GoalBlueprint` | 标签名不规范化；`addEntity("e")` 变成 `{0:"e"}`；蓝图浅拷贝让函数活了下来 | 加 `normalizeTagName`；字符串原样存；蓝图各段统一走 `pureGoalCopy` |

> 第 9 条最阴险：`GoalConstraint` 表面上支持 6 种操作符，实际全部按 `lte` 判定。
> 单看代码不会发现，只有把 6 操作符 × 阈值矩阵铺开跑（第 57 段，115 断言）才会暴露。

---

## 八、本轮补齐的三个模块

原实现是 24 个逻辑模块，比规格少 3 个。补的不是凑数模块，是真缺口：

- **`GoalMilestone`** — 此前评估器只有一个笼统的"完成度"，没有阶段锚点。
  现在支持 4 态（PENDING/REACHED/MISSED/SKIPPED）、加权进度、逾期判定；
  `SKIPPED` 不计入分母（避免"跳过即完成"的假阳性），无里程碑时进度为 0 而非 1。
- **`GoalRisk`** — 与 `GoalConstraint`（可机械判定的硬约束）互补，承载只有概率×影响的软风险。
  4 档分级复用 `GoalPolicy.RISK_LEVELS`（避免两套风险词表）、6 分类、4 状态。
  **只识别、只分级、只记录缓解建议文本——绝不执行缓解。**
- **`GoalStakeholder`** — 此前 `GoalApproval` 里的审批人只是一个裸字符串，没人知道他有没有资格批。
  现在有 5 种角色，`OWNER`/`APPROVER` 具备审批资格，`goal.canApproveBy(name)` 可判定。

三者已接入 `Goal` 实体、`GoalManager.describe()` 与 `main.js` 运行时汇报。

---

## 九、全量回归（23 套）

```
Phase  5    权限与工具         通过 34    失败 0
Phase  6    Skill/Manifest    通过 73    失败 0
Phase  7    Memory 三层        通过 88    失败 0
Phase  7.3  审批与风险         通过 118   失败 0
Phase  8    决策引擎           通过 103   失败 0
Phase  8.x  能力演进           通过 128   失败 0
Phase  9    知识与洞察         通过 147   失败 0
Phase  9.1  自主推理           通过 255   失败 0
Phase 10.1  Harness 自检       断言 174   FAIL 0
Phase 10.3  项目模型           PASS 272   FAIL 0
Phase 10.4  时间线             PASS 352   FAIL 0
Phase 10.5  预测引擎           PASS 983   FAIL 0
Phase 11.0  自主项目 OS        PASS 1384  FAIL 0
Phase 12.0  自主运行内核        PASS 1976  FAIL 0
Phase 13.0  自主执行沙箱        PASS 3115  FAIL 0
Phase 14.0  Agent 运行时       PASS 3559  FAIL 0
Phase 15.0  多 Agent 协作      PASS 6952  FAIL 0（40 段）
Phase 16.0  自主工作流引擎      PASS 9096  FAIL 0（52 段）
Phase 17.0  目标系统           PASS 18697 FAIL 0（80 段）★
Phase 17.0  自研 Test Harness  PASS 97    FAIL 0（8 段）
```

`npm run test:all` 退出码 **0**，共 23 个套件。

---

## 十、运行时验证

`node main.js` 退出码 0，横幅为 `[PersonalAIOS v0.20.0 Kernel]`，目标层汇报：

```
[目标系统] 目标 1（活跃 1） | 类型 10 种 | 模块 27 个
          | 建目标 1 / 规划 1 / 批准 1 / 驳回 0 / 完成 0 / 归档 0 / 评估 1
          | 均完成度 0.714 / 均置信 0.70
          | 记忆分区 7 个（写入 12 次）
          | 里程碑 2/3 达成 | 风险 1/1 未闭环 | 干系人 2 人
          | 禁止注入 77 类 | 执行权:无（唯一属于执行沙箱层）
```

EventBus 本次运行广播 14892 条事件，其中 Goal 相关事件（`GoalParsed` / `GoalPlanned` /
`GoalApproved` / `GoalStarted` / `GoalEvaluated` / `GoalBlueprintGenerated` /
`GoalMetricsUpdated` / `GoalUpdated`）均已实际触达。

---

## 十一、涉及文件

**新增**
`core/goal/GoalMilestone.js`、`core/goal/GoalRisk.js`、`core/goal/GoalStakeholder.js`、
`phase17_goal_test.js`

**修改**
`core/goal/`：`Goal.js`、`GoalState.js`、`GoalLifecycle.js`、`GoalManager.js`、`GoalParser.js`、
`GoalHistory.js`、`GoalDependency.js`、`GoalConstraint.js`、`GoalTag.js`、`GoalContext.js`、
`GoalBlueprint.js`、`index.js`
根目录：`core/events/EventBus.js`、`core/orchestrator/Orchestrator.js`、`main.js`、`package.json`、
`phase13/14/15/16_*_test.js`（同步事件总数 243、套件数 23、版本 0.20.0）

---

## 十二、跨文件常量漂移防护（本次新增）

Phase 16 → 17 升版时踩过一个坑：`package.json` 改成 0.20.0，但 phase13/14 里硬编码的
`"0.19.0"` 断言没跟着改，回归突然 2 FAIL。这类 bug 的要害是**改动点和爆炸点隔着好几个文件**，
靠人眼 review 必漏。本次把它固化成工程手段。

### 新增 `scripts/check-consistency.js`

| 真源（运行时计算，不写死） | 派生点 | 数量 |
| --- | --- | --- |
| `package.json.version` | `main.js` 横幅、`description` 抬头、5 个测试文件各 2 处断言 | **12** |
| `EventBus.js` 的 `EVENTS` 唯一值数 | 4 个测试文件的 `eq(all.length, N)` | **4** |

```bash
npm run check:consistency        # 校验，不一致 exit 1
npm run check:consistency:fix    # 自动同步派生点
node scripts/check-consistency.js --json   # CI 看板消费
```
已挂 `pretest:all` 钩子——**每次 `npm run test:all` 自动先校验**，不合格直接阻断，
不依赖任何人「记得跑」。

### 为什么不用 `grep -c "0.20.0" | wc -l`

1. **数量对 ≠ 值对**：半数写 `v0.20.0`、半数写 `0.20.0` 也能凑够计数。
2. **新增测试文件即误报**，维护成本转嫁给下一个人。
3. **没有定位能力**：报错后还得自己再 grep 一遍。本脚本直接给 `文件:行号 + 期望 + 实际`。

### 两个真实踩到的坑（已在脚本中处理）

- **否定断言误伤**：`ok(!/v0\.19\.0 Kernel/.test(src), "旧版本号已移除")` 里的 0.19.0 是
  **期望不出现的值**。无脑同步会把它改成 `!/v0.20.0/`，等于断言「当前版本必须不存在」，
  测试当场爆炸。脚本用 `NEGATION_RE` 识别并跳过，同时把跳过项透明列出来。
- **全文替换连坐**：早期用 `split(m[0]).join(...)` 做 `--fix`，会把否定断言里恰好相同的
  片段一起改掉，属于「修一个坏一双」。改为按索引**倒序精确替换**。

### 验证方式（故障注入）

| 注入 | 结果 |
| --- | --- |
| `version` 改 0.21.0 | 精确报出 11 处不一致，`--fix` 后 Phase 13 实跑 3115 PASS / 0 FAIL |
| 往返 0.20.0 → 0.21.0 → 0.22.0 → 0.20.0 | 与备份 **逐字节一致**，证明 `--fix` 幂等无损 |
| `EVENTS` 注入 1 个探针事件 | 精确报出 4 处 `all.length` 断言不一致 |
| 否定断言行 | 三轮 `--fix` 后仍为 `0.19.0`，未被误伤 |

顺带修掉一处一直没人发现的漂移：`package.json.description` 抬头还写着
`Personal AI OS v0.19.0 Kernel`，内容停留在 Phase 16。它不参与任何断言，
坏了也没人报错，只会在 `npm view` / README 生成时露出过期版本号——现已纳入校验。

---

## 十三、遗留与后续

- 目标层已完备，**下一步不是继续往目标层加东西**，而是打通"目标 → 工作流 → 执行沙箱"的
  端到端链路演示：让 `GoalBlueprint` 真正被 `WorkflowManager` 消费，再由 `ExecutionSandbox` 落地。
- `GoalEvaluator` 目前是六维评估，`GoalMilestone` 的加权进度尚未并入评估维度——
  并入会改变既有六维断言，建议留到 Phase 18 一并处理。
- 一致性校验目前覆盖 2 类真源。若后续再出现「一处改、多处跟」的常量（如模块数 27、
  禁注类目 77），按 `buildRules()` 里的规则表格式追加即可，**真源必须运行时算出来，
  不能写死在脚本里——否则脚本自己也会漂移**。
