---
id: know-personalaios-phase-17-0-unified-test-harness
type: concept
---
# PersonalAIOS Phase 17.0 —— 自研 Unified Test Harness 测试报告

> 当前版本：**v0.19.0**
> 报告生成日期：2026-08-06
> 测试入口：`phase17_test.js`（8 段，97 断言，全 PASS）
> 全量回归：`node harness.js` / `npm run test:all`（22 套，EXIT=0，0 FAIL，29316 断言）

---

## 1. 概述与决策（自研 harness vs jest/vitest）

Phase 17.0 不引入任何第三方测试框架，落地**自研（零依赖）Unified Test Harness**，把 Phase 5~16 的既有回归套件与 Phase 17 自证套件统一到**同一条 `test:all` 链路**上，并给出 **0 FAIL 硬保证**。

用户决策（原话）：

> 测试：自研 harness（推荐）还是引入 jest/vitest？ —— 我强烈建议自研 harness，保证 Phase 5~16 回归与 Phase 17 在同一 `test:all` 链路上 0 FAIL。

核心动机：

- **不破坏既有投资**：Phase 5~16 共 21 个套件、约 29219 条断言，各自自包含 `sec/eq/ok` 与 `process.exit`，两两状态不共享；引入 jest/vitest 要么要改写全部既有套件，要么要搭建包裹层去做进程桥接，风险与成本都高。
- **保住 0 FAIL**：用**子进程隔离**（每个既有套件仍按原样 `node xxx_test.js` 跑）即可对旧测试**零改动、零破坏**，同时获得崩溃隔离与超时保护。
- **统一汇总 + 硬保证**：运行器解析各套件既有汇总行，统一累加（29316 断言），任一 FAIL/崩溃/超时即整体退出码 1。

版本号：Phase 17 仅改测试基础设施与 `package.json` 脚本，**产品代码未变**，故维持 **v0.19.0**。

---

## 2. 架构设计

三层结构，职责清晰、零第三方依赖（仅用 Node 内置 `node:child_process` / `node:fs` / `node:path` / `node:url`）：

```
core/test/Harness.js        自研断言库（实例工厂，同名兼容既有 sec/eq/ok）
core/test/harness-core.js   纯逻辑层（无副作用，可被单测 import）
harness.js                  CLI 运行器（子进程隔离 + 超时 + 着色 + 统一汇总）
phase17_test.js             自证套件（8 段 / 97 断言 / 0 FAIL）
```

| 维度 | 引入 jest/vitest 方案 | 自研 harness 方案（采用） |
| --- | --- | --- |
| 既有 21 套件 | 需改写或桥接进程 | **零改动**，子进程隔离原样跑 |
| 依赖 | + jest/vitest 等 | **0 新增依赖** |
| 失败隔离 | 进程内，单套挂可能拖垮 | 子进程，崩溃/超时单套隔离 |
| 汇总格式 | 统一（但需 21 套迁就） | 兼容 5 种历史汇总格式，原地解析 |
| 0 FAIL 保证 | 需额外配置 | 内建 `evaluate()` 硬保证 |
| 自证自身 | 难（测试框架测测试框架） | `createHarness()` 实例隔离沙箱，自证 0 FAIL |
| `test:all` | 可能需替换为框架入口 | **保持字面串行链**，harness 叠加其上（满足 Phase 13/14/15/16 护栏） |

关键设计点：

- **实例工厂 `createHarness()`**：每实例独立持有 `PASS/FAIL/分段` 计数。自证套件需要验证「失败确实会被计入 FAIL」，若直接在主计数器跑负向断言，会污染全局 FAIL 数、破坏 0 FAIL 硬保证。因此负向路径一律在隔离沙箱实例 `probe()`（`createHarness({ silent: true })`）中执行，主实例只断言「计数行为是否正确」—— 这是自证套件自身能保持 0 FAIL 的前提。
- **`test:all` 保持字面串行链**：既有 Phase 13/14 用 `split("&&").length` 硬校验「共 22 套」，Phase 15/16 校验 `test:all` 含 Phase 13~16 字面串。harness 在其之上运行/汇总，而非替换它；Phase 13/14 计数常量 21→22 同步更新。
- **5 种历史汇总格式全兼容**：项目在不同阶段沉淀了 5 种汇总行格式（见 §4），`parseSummary()` 用 `SUMMARY_PATTERNS`（5 正则）匹配，取**位置最靠后**的一次匹配，避免中间日志误命中。

---

## 3. 新增 / 修改文件清单

新增：

| 文件 | 职责 |
| --- | --- |
| `core/test/Harness.js` | 自研断言库：`createHarness()` 工厂 + 默认单例；`section/sec/ok/eq/deepEq/deepEqual/throws/noThrow/count/failures/sectionResults/elapsedMs/summary/exitCode`；纯函数 `deepEqual`（结构比较 + 循环保护）/ `safeStr` |
| `core/test/harness-core.js` | 纯逻辑层：`parseSuites()` / `buildSuiteList()` / `parseSummary()` / `evaluate()`；导出 `ROOT` / `SUMMARY_PATTERNS` |
| `harness.js` | CLI 运行器：`runSuite()` 子进程隔离 + 超时 SIGKILL、`--only/--timeout/--bail/--list` 参数、TTY 着色自动降级、统一汇总与整体退出码 |
| `phase17_test.js` | 自证套件（8 段 / 97 断言 / 0 FAIL） |

修改：

- `package.json`：`test:all` 由 21 段升级为 **22 段串行链**（Phase 5~16 + 末位 `node phase17_test.js`）；新增 `test:harness`（`node harness.js`）、`test:harness:list`（`node harness.js --list`）、`test:phase17`（`node phase17_test.js`）。
- `phase13_execution_sandbox_test.js`：套件计数断言 `eq(suites, 21, …)` → `eq(suites, 22, …)`。
- `phase14_agent_runtime_test.js`：同上 21 → 22。

未改动：Phase 5~12、15、16 的 19 个既有套件（维持 0 FAIL，证明 harness 升级零破坏）。

---

## 4. 核心模块详解

### 4.1 `core/test/Harness.js` — 断言库（实例工厂）

- `createHarness(options)`：返回独立实例，`options.silent` 抑制打印（用于沙箱）。
- 导出默认值单例 `_default` 及其命名导出，便捷用法 `import { ok, eq, deepEq } from "./core/test/Harness.js"`。
- 同名兼容既有约定：`section`/`sec`/`ok`/`eq` 与旧套件一致；新增 `deepEq`、`throws`、`noThrow`、`count`、`failures`、`sectionResults`、`elapsedMs`、`summary`、`exitCode`。
- **不调用 `process.exit`**：退出码 `exitCode() => FAIL>0 ? 1 : 0` 由调用方/运行器统一控制。
- `deepEqual(a, b, seen)`：支持对象/数组/Date/Map/Set 结构比较，带 `WeakMap` 循环引用保护。

### 4.2 `core/test/harness-core.js` — 纯逻辑层（无副作用）

- `parseSuites(testAllScript)`：正则 `/node\s+([A-Za-z0-9_./-]+\.js)/g` 提取 `node <file>` 顺序。
- `buildSuiteList({ pkgPath, extra, scriptKey })`：解析 `test:all` 套件列表，确保 Phase 17 自证套件在链路末端；套件顺序唯一真源是 `scripts["test:all"]`（兼容既有护栏）。
- `parseSummary(stdout)`：用 5 个正则匹配以下历史格式，取位置最靠后的匹配：
  - **A**（Phase 5~9）：`通过: 34  失败: 0`
  - **B**（Phase 10.1）：`断言总数: 174  |  PASS: 174  |  FAIL: 0`
  - **C**（Phase 10.2）：`断言 227 | 通过 227 | 失败 0`
  - **D**（Phase 10.3）：`PASS=272 FAIL=0`
  - **E**（Phase 10.4+）：`PASS 87 / FAIL 0（共 9 段）`
  - 解析不到返回 `null`，交由退出码兜底。
- `evaluate(results)`：0 FAIL 硬保证判定；任一 suite 退出码非 0 或 `fail>0` 即整体失败；返回 `{ allPass, exitCode, totalPass, totalFail, suites, details }`。

### 4.3 `harness.js` — CLI 运行器

- `runSuite(file, timeoutMs)`：`spawn(process.execPath, [file], { cwd: ROOT })`，`setTimeout` + `child.kill("SIGKILL")` 超时保护；返回 `{ file, exitCode, pass, fail, ms, stdout, stderr, timedOut, parsed }`。
- **兜底防误判**：超时/崩溃且无汇总行时，记 1 个 FAIL（`fail = timedOut || code!==0 ? 1 : 0`），避免「无输出被误判 0 FAIL」。
- 参数：`--only <substr>`（子串匹配，可多次）、`--timeout <秒>`（默认 180）、`--bail`（首个失败即中止）、`--list`（仅列套件）。
- 着色：`process.stdout.isTTY && !NO_COLOR` 自动降级，非 TTY 去色。
- 退出码：`main()` 返回 `verdict.exitCode`，置 `process.exitCode`。

---

## 5. Phase 17 自证套件分段汇总（8 段 / 97 断言 / 0 FAIL）

| # | 测试段 | 关键验证点 | 断言数 | 结果 |
| --- | --- | --- | --- | --- |
| 1 | 断言计数与失败捕获 | `ok(true)` 计 PASS；负向路径在 `probe()` 沙箱计 FAIL；失败明细带分段名/消息；`sec` 是 `section` 别名 | 11 | PASS |
| 2 | 实例隔离（0 FAIL 保证前提） | `createHarness()` 各实例 FAIL/PASS 互不污染；退出码由自身 FAIL 决定；沙箱 `summary` 静默且返回结构正确 | 11 | PASS |
| 3 | 深度相等 deepEq | 嵌套对象/数组/Map/Set/Date 相等；4 类不等场景全计 FAIL；循环引用不抛 | 13 | PASS |
| 4 | throws / noThrow | 抛错/类型检查/不抛；负向路径在沙箱验证（未抛/类型不符/抛错计入 FAIL） | 10 | PASS |
| 5 | evaluate —— 0 FAIL 硬保证 | 全 0 退出→allPass；有 1→非 allPass；空结果→allPass；**防御：FAIL>0 即使 exit 0 也判失败**；崩溃套件（无汇总行）仍判失败 | 13 | PASS |
| 6 | parseSummary 输出解析 | 5 种历史格式全解析正确；非 0 FAIL 可识别；取最靠后一次匹配；跨格式混排取最靠后；无匹配返回 null | 17 | PASS |
| 7 | 套件清单完整性 | Phase 5~16 回归 + Phase 17 同链路；全部 scripts/依赖不含 jest/vitest/mocha/chai；`test:all` 串 phase17、仍含 phase5/phase16；存在 `test:phase17`/`test:harness` 入口；`&&` 段数 = 解析数（护栏同步）；Phase 17 在链路末端、无重复、全部文件存在 | 14 | PASS |
| 8 | parseSuites 解析正确性 | 解析 `node phaseA && node phaseB && …` 顺序；空脚本/无 node 调用返回空；支持带路径套件 | 8 | PASS |
| **合计** | **8 段** | — | **97** | **0 FAIL** |

---

## 6. 0 FAIL 硬保证与隔离机制验证

| 验证维度 | 结果 | 覆盖断言 |
| --- | --- | --- |
| 子进程隔离：21 个既有套件原样跑，零改动零破坏 | PASS（全链路 0 FAIL） | 全链路 |
| 实例隔离：自证负向路径在沙箱，主实例保持 0 FAIL | PASS | 段 2：11 |
| 0 FAIL 硬保证：任一 FAIL/崩溃/超时→整体 exit 1 | PASS | 段 5：13 |
| 防御：FAIL>0 但 exit 0 仍判失败（以 fail 数为准） | PASS | 段 5：13 |
| 超时兜底：无汇总行记 1 FAIL，防误判 | PASS（设计 + `runSuite` 逻辑） | 段 5：13 |
| 5 种历史汇总格式全兼容 | PASS | 段 6：17 |
| 护栏同步：`test:all` 段数 = harness 解析数 | PASS | 段 7：14 |

---

## 7. 全量回归状态（22 套 / 29316 断言 / 0 FAIL）

运行 `node harness.js`（等价于 `npm run test:all`）的最终结果：

```
套件：22 个（通过 22 / 失败 0）
断言：29316 通过 / 0 失败
耗时：3.2s
结论：✓ 0 FAIL —— Phase 5~17 全链路通过
```

各套件断言明细（PASS / FAIL）：

| # | 套件 | 断言数 | 结果 |
| --- | --- | --- | --- |
| 1 | phase5_test.js | 34 | PASS |
| 2 | phase6_test.js | 73 | PASS |
| 3 | phase7_decision_test.js | 88 | PASS |
| 4 | phase7_2_decision_manager_test.js | 80 | PASS |
| 5 | phase7_full_cognition_test.js | 118 | PASS |
| 6 | phase8_1_dynamic_planner_test.js | 103 | PASS |
| 7 | phase8_2_multi_agent_test.js | 103 | PASS |
| 8 | phase8_3_evolution_test.js | 128 | PASS |
| 9 | phase8_4_knowledge_test.js | 147 | PASS |
| 10 | phase9_1_autonomy_test.js | 255 | PASS |
| 11 | phase10_1_project_test.js | 174 | PASS |
| 12 | phase10_2_scheduler_test.js | 227 | PASS |
| 13 | phase10_3_workspace_test.js | 272 | PASS |
| 14 | phase10_4_timeline_test.js | 352 | PASS |
| 15 | phase10_5_forecast_test.js | 983 | PASS |
| 16 | phase11_system_test.js | 1384 | PASS |
| 17 | phase12_runtime_test.js | 1976 | PASS |
| 18 | phase13_execution_sandbox_test.js | 3115 | PASS |
| 19 | phase14_agent_runtime_test.js | 3559 | PASS |
| 20 | phase15_collaboration_test.js | 6952 | PASS |
| 21 | phase16_workflow_test.js | 9096 | PASS |
| 22 | phase17_test.js | 97 | PASS |
| **合计** | **22 套** | **29316** | **0 FAIL** |

- 回归套件（Phase 5~16）= 21 套 / 29219 断言；自证套件（Phase 17）= 1 套 / 97 断言。
- 既有 19 个未改动套件全部 0 FAIL，确认 harness 升级对既有行为零破坏。
- 独立 `npm run test:all` 重跑：`TESTALL_EXIT=0`，FAIL 扫描 0 条。

---

## 8. 与 jest/vitest 不选用的理由（决策复核）

| 维度 | 结论 |
| --- | --- |
| 既有 21 套件保护 | 子进程隔离 = 零改动，jest/vitest 必然涉及迁移成本与回归风险，否决 |
| 依赖膨胀 | 自研 0 新增依赖；jest/vitest 引入成十依赖，与「零依赖核心」理念冲突 |
| 0 FAIL 硬保证 | 内建 `evaluate()` 统一判定；jest/vitest 需额外配置多项目/多 runner |
| 异构汇总兼容 | `parseSummary` 兼容 5 种历史格式；jest/vitest 强制统一报告格式，须迁就 |
| 自证（测试框架测自己） | `createHarness()` 实例沙箱，自证 0 FAIL；jest/vitest 自测自身成本高且易循环 |
| `test:all` 字面链护栏 | 保持字面链满足 Phase 13/14/15/16 既有护栏；框架入口会破坏这些护栏 |
| 运行开销 | 全链路 3.2s；引入打包/转译层只会更慢 |

**结论：自研 harness 在「保护既有投资、零依赖、0 FAIL 硬保证、自证可行性、满足历史护栏」五个维度上全面优于引入 jest/vitest，决策成立。**

---

## 9. 下一步建议与验收标准核对

| 验收项 | 要求 | 实测 | 结论 |
| --- | --- | --- | --- |
| 不引入第三方测试框架 | 坚持自研 | 0 新增测试依赖（jest/vitest/mocha/chai 全无） | ✅ |
| Phase 5~17 同一链路 0 FAIL | 全绿 | `test:all` / `harness.js` 均 EXIT=0，0 FAIL | ✅ |
| 套件数 | 22 套（21 回归 + 1 自证） | 22 套 | ✅ |
| 总断言数 | — | 29316 | — |
| 自证套件 | 0 FAIL | 8 段 / 97 断言 / 0 FAIL | ✅ |
| 0 FAIL 硬保证 | 有 | `evaluate()` 内建 + 超时兜底 | ✅ |
| 崩溃/超时隔离 | 有 | 子进程 + SIGKILL + 兜底 FAIL | ✅ |
| 历史汇总格式兼容 | 5 种 | `SUMMARY_PATTERNS` 全匹配 | ✅ |
| `test:all` 字面链护栏 | 不破坏 | Phase 13/14 计数 22 同步、15/16 字面串保留 | ✅ |

下一步建议：

1. **CI 接入**：将 `node harness.js`（或 `npm run test:all`）设为 CI 必过门槛，`exitCode` 直接驱动流水线红绿。
2. **`--bail` 开发流**：本地迭代用 `node harness.js --only phase17 --bail` 快速验证自证套件。
3. **新增 Phase 18+ 套件**：写新 `phaseXX_test.js` 后，把 `node phaseXX_test.js` 加入 `test:all` 串行链、并把计数常量（Phase 13/14 的 `eq(suites, 22, …)`）同步 +1；`harness.js` 自动纳入汇总，无需改运行器。
4. **超时调参**：若未来套件变重，`node harness.js --timeout 300` 提升单套上限；默认仍 180s。
5. **不引入 jest/vitest 的红线**：后续测试基础设施一律沿用本 harness，避免第三方框架破坏既有 0 FAIL 链路。

**结论：Phase 17.0 自研 Unified Test Harness 达成全部目标——Phase 5~17 同一 `test:all` 链路 0 FAIL（22 套 / 29316 断言 / EXIT=0），且对既有 21 套件零破坏。**
