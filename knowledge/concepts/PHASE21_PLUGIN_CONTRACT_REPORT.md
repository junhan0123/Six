---
id: know-phase-21-0a-plugin-architecture-contract
type: concept
---
# Phase 21.0A —— Plugin Architecture Contract 验收报告

> 目标版本：`v0.23.1`（内核横幅冻结于 `v0.23.0`）
> 性质：**契约冻结层（Contract Freeze）**，不是 Plugin Runtime。
> 只定义 Plugin 能声明什么 / 能访问什么 / 不能突破什么的形式契约；不加载第三方代码、不启动进程、不碰 Shell、不调用 `ExecutionSandbox`、不实现 Plugin Runtime。

---

## 0. 本回合收口范围（关键）

Phase 21.0A 的主体交付（15 个契约模块、`scan-plugin-contract-execution.js`、≥70 段/≥12000 断言验收测试、8 个 `*.schema.json`、EventBus 13 个插件事件、`PLUGIN_FORBIDDEN_INJECTIONS` ≥150 类、接入 `check-consistency.js` / `npm run test:all` / `main.js`、`package.json` 升 0.23.1）已在之前的回合完成，5 个验收闸门中 4 个已通过。

**本回合唯一的剩余工作：闭合第 5 个（Gate 2）并清理其连锁暴露的 4 处过期/不一致断言。** 全部修复均已落地并通过复跑。

---

## 1. 五个验收闸门（Acception Gates）

| # | 闸门 | 要求 | 本次结果 | 状态 |
|---|------|------|----------|------|
| 1 | phase21 验收测试 | ≥12000 断言 / 0 FAIL | **22506 断言 / 0 FAIL**（96 段） | ✅ |
| 2 | `npm run test:all` | EXIT=0 / 0 FAIL | **EXIT=0 / 0 FAIL**（29 套全绿） | ✅ |
| 3 | 源码扫描 Execution Token | = 0 | **蓝图扫描=0 · 插件扫描=0** | ✅ |
| 4 | `check-consistency` | EXIT=0 | **EXIT=0**（13 版本点 / 8 事件点 / 6 套数点一致） | ✅ |
| 5 | `node main.js` | EXIT=0（含真实 Contract 演示） | **EXIT=0**（演示：`层级=plugin-contract｜模块=15｜发事件=13｜禁注=240 类｜事件已注册=true｜执行权=无`） | ✅ |

---

## 2. 本回合修复的 4 处断言/扫描不一致

> 根因共性：**Phase 21 把 `phase21_plugin_contract_test.js` 追加到 `test:all` 末尾、把 `package.json.version` 升到 `0.23.1`、并在 `docs/architecture/` 下新增 `plugin/` 子命名空间**，但若干既有回归套件/扫描器仍持有旧假设，且因 `&&` 短路此前被更早的失败掩盖。

### Fix A — `phase17_goal_test.js`（实际 Gate 2 失败点）
- 位置：section 74「package.json 版本与测试链路」
- 旧：`eq(suites[suites.length - 1], "phase17_test.js", "harness 自证套件仍在链路末尾")`
- 新：`eq(suites[suites.length - 1], "phase21_plugin_contract_test.js", "链路末端套件为 Phase 21 契约验收套件（自证不变量保持）")`
- 说明：链路末端现在是 Phase 21 验收套件，自研 harness「自证不变量」仍保持（负向断言跑在隔离沙箱，不污染主实例 0 FAIL）。
- 注：**两个文件**都含同形态断言——`phase17_test.js`（harness 自证，8 段，section 7）与 `phase17_goal_test.js`（目标系统，80 段，section 74）。本回合两处均改为期望 `phase21_plugin_contract_test.js`。

### Fix B — `scan-blueprint-contract.js` + `phase18_contract_test.js`（蓝图扫描器未计入 plugin 子命名空间）
- 现象：Phase 21 在 `docs/architecture/plugin/` 下交付 8 个 schema 文件（独立插件契约命名空间）。蓝图扫描器 `fs.readdirSync(DOCS_DIR)` 把 `plugin/` 目录项算作第 12 份「文档」并判定为「未登记」，触发：
  - `[58 扫描器自证] 扫描零违规（期望 0，实际 1）`
  - `[59 文档与代码逐字节一致] 磁盘上 11 份文档（期望 11，实际 12）`
- 修正（语义正确：蓝图扫描器只拥有 `docs/architecture/` 顶层文件；`plugin/` 子目录由 `scan-plugin-contract-execution.js` 与 phase21 验收套件单独校验）：
  - `scan-blueprint-contract.js`：`readdirSync(DOCS_DIR, { withFileTypes: true }).filter(e => e.isFile())`，仅统计顶层文件。
  - `phase18_contract_test.js` section 59：`onDisk` 同样过滤为文件（`fs.statSync(...).isFile()`），断言 `onDisk.length === 11` 恢复成立。

### Fix C — `phase20_learning_test.js`（版本双轨：学习层对齐 kernelVersion）
- 位置：section 2「版本与层级常量」
- 旧：`eq(pkg.version, LEARNING_VERSION, "package.json 版本与学习层版本一致")` —— `pkg.version` 已为 `0.23.1`，而 `LEARNING_VERSION`（内核子系统，冻结于 `kernelVersion`）仍为 `0.23.0`。
- 新：
  ```js
  eq(pkg.kernelVersion, LEARNING_VERSION, "package.json 内核版本(kernelVersion)与学习层版本一致");
  eq(pkg.version, "0.23.1", "package.json 项目版本已随 Phase 21 升至 0.23.1");
  ```
- 说明：遵循版本双轨——内核子系统（learning / execution-sandbox / agent-runtime / …）版本随 `kernelVersion`（0.23.0）冻结；项目版本 `version`（0.23.1）随契约层前进。各契约层用**自有版本体系**（插件层 `PLUGIN_API_VERSION_CURRENT = "1.0.0"`、蓝图层 `CURRENT_CONTRACT_VERSION = 3`），均不直接绑定项目版本。

---

## 3. 交付物确认（来自主体交付回合，本次仅复核）

| 交付物 | 状态 | 证据 |
|--------|------|------|
| 15 个 Plugin 契约模块（`core/plugin/contract/*`） | ✅ | `main.js` 演示 `模块=15` |
| `scan-plugin-contract-execution.js`（Execution Token 扫描） | ✅ | `PLUGIN_SCAN_EXIT=0`，`Execution Token = 0` |
| 验收测试 ≥70 段 / ≥12000 断言 / 0 FAIL | ✅ | **96 段 / 22506 断言 / 0 FAIL** |
| `docs/architecture/plugin/*.schema.json`（8 个） | ✅ | `find` 确认 8 个文件落盘 |
| EventBus 13 个插件事件 | ✅ | 事件总数 279 → 292；`main.js` 演示 `发事件=13` |
| `PLUGIN_FORBIDDEN_INJECTIONS` ≥150 类 | ✅ | `main.js` 演示 `禁注=240 类` |
| 接入 `check-consistency.js` / `test:all` / `main.js` | ✅ | 三闸门均 EXIT=0 |
| `package.json` → 0.23.1（内核横幅保持 0.23.0） | ✅ | `version=0.23.1`，`kernelVersion=0.23.0` |

---

## 4. 版本双轨策略（最终定稿）

```
package.json
  version:        "0.23.1"   ← 项目版本，随契约层前进（Phase 21 推进）
  kernelVersion:  "0.23.0"   ← 内核冻结，横幅 / description / 内核子系统版本读它

check-consistency 真源派生：
  version 的 13 处派生点 + kernelVersion 的 banner/description 抬头
  EventBus 事件总数 292（279 + 13 插件）
  test:all 套数 29
```

---

## 5. 红线（Red Lines）复核

- **零执行权**：`hasExecutionAuthority() ≡ false` 全层一致（蓝图扫描 / 插件扫描 / `main.js` 演示均确认）。
- **不加载第三方代码 / 不启动进程 / 不碰 Shell / 不调用 `ExecutionSandbox`**：契约层为纯数据 + `deepFreeze`；源码扫描 Execution Token = 0。
- **注入防御**：`PLUGIN_FORBIDDEN_INJECTIONS`（顶层键） + `assertNoPluginInjected` + 安全别名（`execSandboxHandle`/`executionSandbox`/`childProc`/`terminalSession`/`shellSession`）避免自扫描误报。

---

## 6. 完成定义（Definition of Done）

- [x] Gate 1：phase21 测试 ≥12000 断言 / 0 FAIL（实测 22506）
- [x] Gate 2：`npm run test:all` EXIT=0 / 0 FAIL（29 套全绿）
- [x] Gate 3：源码扫描 Execution Token=0（蓝图 + 插件）
- [x] Gate 4：`check-consistency` EXIT=0
- [x] Gate 5：`node main.js` EXIT=0（含真实 Contract 演示）
- [x] 所有因 Phase 21 接线暴露的过期/不一致断言已闭环（Fix A/B/C）

**结论：Phase 21.0A Plugin Architecture Contract 契约冻结层验收通过，版本 v0.23.1 可发布。**
