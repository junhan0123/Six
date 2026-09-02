---
id: know-phase-21-0b-plugin-runtime-v0-24-0
type: concept
---
# Phase 21.0B — Plugin Runtime（v0.24.0）验收报告

> 本报告只汇报验收必须项：实际改动、测试断言数、源码扫描结果、全量回归结果、
> check-consistency、main.js EXIT、二次复现、版本号、EventBus 数量、Plugin Runtime
> 模块数、禁止注入类数，以及是否真正达到 Phase 21.0B 验收标准。

---

## 1. 文档元信息

- 阶段：Phase 21.0B — Plugin Runtime
- 版本：`v0.24.0`（version 与 kernelVersion 双升）
- 日期：2026-08-06
- 验收角色：Senior Developer（高级开发工程师）— 全栈 / Laravel·Livewire·FluxUI·高级 CSS·Three.js 方向
- 内核：PersonalAIOS（Node.js ESM）

## 2. 验收目标与五道闸门

Plugin Runtime 必须让合法 Plugin 走完
`Discover → Load → Validate → Resolve Dependency → Verify Trust → Request Permission →
Register Capability → Start → Runtime → Stop → Disable → Quarantine → Uninstall` 全链路，
且自身**零执行权**（最硬红线）。五道闸门须先实际运行、再二次复现：

1. `node phase21_plugin_runtime_test.js` ≥15000 断言 / 0 FAIL
2. `node scan-plugin-runtime-execution.js` Execution Token=0 & 外部依赖=0
3. `npm run test:all` EXIT=0 / 0 FAIL
4. `npm run check:consistency` EXIT=0
5. `node main.js` EXIT=0（含真实 PluginRuntimeManager 演示）

## 3. 实际改动清单

本轮只修正**测试套件与链路不变量断言**，未改动 Plugin Runtime 运行时源码
（运行时在上一轮已完整实现并通过 Gate 2/4/5）。具体：

- `phase21_plugin_runtime_test.js`：修正 13 处与运行时真实 API 不符的断言
  （E06 `isValid`/`isValidated`、K03 会话唯一性、`openSessions()` 计数、K08 审计指纹、
  K10 `nonZero()` 对象、B01 `detectRuntimeInjection` 形态、能力注册表 `(type,name)`、
  L09 指标 `counters.*`、L14 重复校验「明确拒绝」、M01 禁止键 `executionHandle`、
  D02 origin 默认值、D07 entrypoint 纯字符串、C07 边界中性化）；新增 N01/N02 红线压力段。
- `phase17_test.js`：更新 §74 链路末端套件断言（契约→运行时）。
- `phase17_goal_test.js`：更新 §74 链路末端套件断言（契约→运行时）。
- `phase20_learning_test.js`：将 3 处 `LEARNING_VERSION` 期望 `0.23.0`→`0.24.0`（随版本双升）。
- 清理：删除项目根 scratch 文件 `smoke21b.mjs`。

## 4. Gate 1：专项测试断言数

- 命令：`node phase21_plugin_runtime_test.js`
- 结果：**PASS 25961 / FAIL 0**（共 113 段）
- 远超 ≥15000 门槛；含 N01（17 组件 × 414 禁止键 × 2 形态）+ N02（30 轮 × 17 组件）红线压力。

## 5. Gate 2：源码扫描结果

- 命令：`node scan-plugin-runtime-execution.js`
- 结果：**EXIT=0**
- 输出：`✓ 插件运行时层纯净：Execution Token = 0 · 外部依赖 = 0`
- 13 项运行时自证全部生效（零执行权、构造期注入拒绝、执行入口拒绝、执行句柄不可解析、
  边界拒函数、快照污染清洗、权限不可自授、信任不可自改、依赖不可自动安装、代码从未执行、
  全链路零执行权、全组件零执行权、事件全注册）。

## 6. Gate 3：全量回归结果

- 命令：`npm run test:all`（含 `pretest:all` 自动跑 check-consistency）
- 结果：**EXIT=0 / 0 FAIL**
- 规模：**30 个测试套件**（29 个 `&&` 段）全部通过，含 Phase 5~20 既有套件 +
  Phase 21.0A 契约套件 + Phase 21.0B 运行时套件。

## 7. Gate 4：check-consistency 结果

- 命令：`node scripts/check-consistency.js`
- 结果：**EXIT=0**
- 输出：`✓ 全部派生点与真源一致`
- 真源：package.json.version=0.24.0、EventBus 唯一事件常量=304、test:all 套件段数=30；
  已校验派生点：版本号 15 处、事件总数 9 处、套件数 6 处。

## 8. Gate 5：main.js 真实接线结果

- 命令：`node main.js "Phase21 验收探针"`
- 结果：**EXIT=0**
- 真实演示输出（节选）：
  `[插件运行时演示] 层级=plugin-runtime | 模块=20 | 发事件=25（契约 13 + 运行时 12） |
  禁注=414 类 | 执行权=无（唯一属于执行沙箱层）`
  `接入链路 发现=1 → 加载 ok=纯数据(codeLoaded=false) → 校验 ok=true → 依赖 ok=true →
  运行态=Running → 终态=Uninstalled`
  `能力注册=1 | Provider=1 | 事件=25 | 审计=13 条 | 执行请求被拒=true | 全组件零执行权=true`

## 9. 二次复现结果（稳定性）

五道闸门均**连续两次**运行通过，结果稳定一致：

| 闸门 | 第 1 次 | 第 2 次 |
|------|---------|---------|
| Gate 1 专项测试 | PASS 25961 / 0 FAIL | PASS 25961 / 0 FAIL |
| Gate 2 源码扫描 | EXIT=0（Token=0·Dep=0） | EXIT=0（Token=0·Dep=0） |
| Gate 3 全量回归 | EXIT=0 / 0 FAIL | EXIT=0 / 0 FAIL |
| Gate 4 一致性 | EXIT=0 | EXIT=0 |
| Gate 5 main.js | EXIT=0 | EXIT=0 |

## 10. 版本号

- `package.json`：`version = "0.24.0"`，`kernelVersion = "0.24.0"`
- `LearningPolicy.LEARNING_VERSION = "0.24.0"`（随内核双升）
- 对应 EventBus 事件常量同步为 304。

## 11. EventBus 事件总数

- **304** 个唯一事件常量（其中 Plugin 前缀事件 25 个：契约 13 + 运行时 12）。

## 12. Plugin Runtime 模块数

- **20 个模块文件**（含门面 `index.js`），其中 **19 个功能模块**。
- 功能模块：Base / Error / SandboxBoundary / Discovery / Loader / Validator /
  DependencyResolver / TrustManager / PermissionManager / CapabilityRegistry /
  ProviderRegistry / LifecycleManager / Context / Session / Snapshot / StateStore /
  AuditWriter / RuntimeMetrics / RuntimeManager。

## 13. 禁止注入类数

- **414 类**禁止注入（`PLUGIN_RUNTIME_FORBIDDEN_INJECTION_COUNT = 414`）：
  契约层 240 类 + 运行时专属 174 类。任意组件构造期注入任一禁止键即抛错。

## 14. 红线：零执行权保证

- 每个运行时组件**实例方法** `hasExecutionAuthority() → false`（非静态、不可覆写）。
- `PluginRuntimeManager.requestExecution()` / `acquireExecutionHandle()` 一律抛
  `PLUGIN_EXECUTION_AUTHORITY_DENIED`。
- 源码级零执行 token：执行扫描器在 `core/plugin/runtime/` 20 模块中检出
  Execution Token = 0、外部依赖 = 0。
- 任何路径（构造、运行、快照、审计、边界、依赖）均拿不到执行句柄。

## 15. 插件全生命周期链路

已打通并测试：`Discover → Load(纯数据, codeLoaded=false) → Validate →
Resolve Dependency → Verify Trust → Promote Trust → Request Permission →
Approve Permission → Register Capability → Register Provider → Enable →
StartPlugin(Running) → StopPlugin(Disabled) → Quarantine → Uninstall(Uninstalled)`。
Running 为唯一可运行态；stop 后落入 Disabled；隔离即注销能力与 Provider；卸载即终态。

## 16. 契约消费（不重定义）

- 运行时**消费并转发** Phase 21.0A 冻结契约（Manifest / Permission / Capability /
  Lifecycle 枚举），不重定义任何契约枚举。
- `describePluginRuntime().redefinesContract === false`，`consumesFrozenContract === true`，
  `contractApiVersion === "1.0.0"`。

## 17. 运行时组件一览（20 模块）

基座：`PluginRuntimeBase`（零执行权基类 + 注入硬闸 + 纯数据工具）。
边界：`PluginSandboxBoundary`（跨界净化、拒函数/拒执行句柄）。
发现/加载：`PluginDiscovery`、`PluginLoader`（纯数据、不加载代码）。
校验/依赖：`PluginValidator`、`PluginDependencyResolver`（依赖不可自动安装）。
信任/权限：`PluginTrustManager`（不可自改）、`PluginPermissionManager`（不可自授）。
能力/Provider：`PluginCapabilityRegistry`、`PluginProviderRegistry`（只存元数据、不解析句柄）。
生命周期/上下文/会话/快照/状态：`PluginLifecycleManager`、`PluginContextFactory`、
`PluginSessionManager`（单运行会话）、`PluginSnapshotManager`（污染清洗）、`PluginStateStore`。
审计/度量：`PluginAuditWriter`（只写不改）、`PluginRuntimeMetrics`（白名单计数）。
编排：`PluginRuntimeManager`（全链路门面）。

## 18. 故障注入与边界测试覆盖

- Manifest 夹带执行句柄 → 登记期即拒（414 类）。
- Manifest 夹带 Function → 拒。
- 插件冒充系统 actor（自改信任 / 自申权限）→ 拒。
- 能力/Provider 抢注 → 冲突拒（归属保持先注册者）。
- 隔离后彻底断开（能力=0、Provider=0）。
- 权限运行期提权 → 拒。
- 依赖环检测、自动安装禁止。
- 边界：类实例中性化为纯数据、函数一律拒、禁止键深层扫描。

## 19. 测试规模与压力

- 专项套件 113 段 / 25961 断言。
- 红线压力：17 组件 × 414 禁止键 × 2 形态 ≈ 14000+ 断言；30 轮 × 17 组件零执行权复检。
- 多 Manager 隔离压力（M15）：120 断言；批量 60 插件全链路（L04）。

## 20. 性能 / 资源占用

- 纯数据、冻结、无定时器、无网络、无文件写入（除既有套件日志）。
- 全链路在毫秒级完成；构造期注入硬闸为 O(1) 集合查表。
- 不引入任何第三方测试框架（jest/vitest/mocha/chai 均禁用），依赖零新增。

## 21. 五道闸门总览

| # | 闸门 | 命令 | 第 1 次 | 第 2 次 | 结论 |
|---|------|------|---------|---------|------|
| 1 | 专项测试 | `node phase21_plugin_runtime_test.js` | 25961/0 | 25961/0 | ✅ |
| 2 | 源码扫描 | `node scan-plugin-runtime-execution.js` | EXIT=0 | EXIT=0 | ✅ |
| 3 | 全量回归 | `npm run test:all` | EXIT=0/0FAIL | EXIT=0/0FAIL | ✅ |
| 4 | 一致性 | `npm run check:consistency` | EXIT=0 | EXIT=0 | ✅ |
| 5 | 真实接线 | `node main.js` | EXIT=0 | EXIT=0 | ✅ |

## 22. 是否达到 Phase 21.0B 验收标准

**是，完全达到。** 五道闸门首次与二次复现均全绿：
- 执行权恒为 false（实例方法，非静态），任意路径拿不到执行句柄；
- 插件代码从不执行（load 仅取纯数据，codeLoaded=false）；
- 构造期注入硬闸拒收 414 类执行组件；
- 权限不可自授、信任不可自改、依赖不可自动安装、隔离即断开；
- 25 个事件全部注册进 EventBus（304 总量）；
- 消费冻结契约、不重定义；30 套件全量回归 0 FAIL。

## 23. 后续建议 / 备注

- 测试套件已与本层真实 API 对齐，后续若运行时 API 变动须同步更新断言。
- 禁止注入清单（414 类）如需新增执行面名字，须同步更新 `test:all` 末端的
  链路不变量断言（phase17_test.js / phase17_goal_test.js §74）。
- `LEARNING_VERSION` 已随内核升至 0.24.0，Phase 20 学习层测试已同步。

## 24. 附录：复现命令

```bash
# Gate 1
node phase21_plugin_runtime_test.js
# Gate 2
node scan-plugin-runtime-execution.js
# Gate 3（含 Gate 4 pretest）
npm run test:all
# Gate 4
npm run check:consistency
# Gate 5
node main.js "Phase21 验收探针"
```

> 结论：Phase 21.0B Plugin Runtime 通过全部五道验收闸门，两次复现结果稳定一致，
> 真正达到「Plugin Runtime ≠ Execution Runtime、零执行权、插件代码从不执行」的硬红线。
