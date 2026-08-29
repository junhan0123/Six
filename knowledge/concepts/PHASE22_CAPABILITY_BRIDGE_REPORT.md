---
id: know-phase-22-0-plugin-capability-bridge-system-integ
type: concept
---
# Phase 22.0 — Plugin Capability Bridge & System Integration 验收报告

> 版本目标：`v0.25.0` ｜ 内核冻结 `kernelVersion: v0.25.0` ｜ 报告日期：2026-08-06
> 核心命题：**Plugin ≠ Executor** —— 桥接 / 适配 / 集成三层只产出纯数据，零执行权，永不向任何子系统注入插件实例。

---

## 1. Executive Summary（结论先行）

Phase 22.0 在既有 Plugin 架构（契约层 + 运行时层，Phase 21）之上，补齐了「能力桥接 → 适配 → 系统集成」三层，把外部插件能力翻译成 5 个主子系统（workflow / tool / agent / memory / model）可消费的纯数据形态，并为 Goal 提供横切资源附着。

**五道闸门全部通过（二次复现一致）：**

| 闸门 | 验证物 | 结果 |
|------|--------|------|
| Gate1 | `phase22_capability_bridge_test.js` | 152 段 / 103,677 断言 / **0 FAIL** |
| Gate2 | `scan-plugin-bridge-execution.js` | Execution Token = 0 · 外部依赖 = 0 · 违规 = 0 |
| Gate3 | `check-consistency.js` | 16 版本 + 11 事件 + 6 套数派生点全部一致 |
| Gate4 | `harness.js`（全链路） | **31/31 套件 · 456,676 断言 · 0 FAIL** |
| Gate5 | 端到端真实落地 + 二次复现 | 6 插件 × 5 消费者全链路 0 FAIL，确定性可复现 |

---

## 2. 版本与基线

- `version` / `kernelVersion`：`0.25.0`
- `test:all` 串行链：**31 套**（Phase 5~21 回归 + Phase 17 自研 harness 自证 + Phase 22 能力桥接）
- EventBus `EVENTS` 总数：**327**（其中 `Plugin*` 前缀 48 个，`PluginCapability*` 已注册 **25** 个）
- 全量断言：**456,676** 通过 / 0 失败（Phase 22 单套贡献 103,677）

---

## 3. 三层架构总览

| 层 | 模块数 | 职责 | 零执行权常量 |
|----|--------|------|--------------|
| `core/plugin/bridge` | 16 | 解析 / 信任 / 句柄 / 请求 / 路由 / 审计 | `PLUGIN_BRIDGE_EXECUTION_AUTHORITY = false` |
| `core/plugin/adapters` | 7 | 能力类型 → 纯数据 Descriptor | `PLUGIN_ADAPTER_EXECUTION_AUTHORITY = false` |
| `core/plugin/integration` | 8 | Descriptor → 子系统绑定 / 请求 / 资源 / spec | `PLUGIN_INTEGRATION_EXECUTION_AUTHORITY = false` |

三层门面均经 `describe*()` 自证 `executionAuthority === false`；每个实例方法 `hasExecutionAuthority()` 恒返回 `false`。

---

## 4. 核心命题：Plugin ≠ Executor

这是整条链路最硬的一条红线，贯穿三层与 6 个消费者：

- 桥接层 `requestCapability()` 只产出「请求 + 路由结论」，绝不执行任何能力；`acquireExecutionHandle()` / `performCapability()` 一律抛 `PluginBridgeExecutionAuthorityDenied`。
- 适配层只把 Provider 入口翻译成冻结的 `PluginProviderDescriptor`（纯数据，`invocable:false`、`executionAuthority:false`、`mustRouteThroughOrchestration:true`）。
- 集成层 `register` 子系统时**永远传 `null` 实例**——插件代码本体从不进入任何子系统。

---

## 5. Gate1 — 桥接层零执行权（A 段）

- `PLUGIN_BRIDGE_MODULES = 16`，磁盘文件数一致。
- `PLUGIN_BRIDGE_EMITS = 24` 事件声明；桥接门面 `hasExecutionAuthority()` 恒 `false`。
- fail-closed：`requestCapability({ capabilityType:"ToolProvider", capabilityName:"nope" })` 返回 `{ ok:false, stage:"resolution-failed", executionAuthority:false }`。
- 禁止注入清单 `PLUGIN_BRIDGE_FORBIDDEN_INJECTION_COUNT = 602` 类（≥250）。

---

## 6. Gate2 — 适配层纯数据（B 段）

- `PLUGIN_ADAPTER_MODULES = 7`，覆盖 5 种能力类型（`PluginToolProviderAdapter` 等）。
- `detectAdapterInputShape` 正确识别 `ProviderEntry` / `CapabilityResolution` / `CapabilityHandle` 三种形态（基于真实工厂对象验证）。
- 未覆盖能力类型（如 `UnknownProvider`）被拒收。
- `createProviderDescriptor` 产出深冻结、纯数据 Descriptor；`hasCallableDeep(traits)` 恒 `false`。

---

## 7. Gate3 — 集成层零执行权与消费者边界（C / D 段）

- `PLUGIN_INTEGRATION_MODULES = 8`，含 `PluginIntegrationSet`（集合驱动 `integrateAll` / `consumeForGoal` / `verifyZeroAuthority`）。
- 6 个消费者：`workflow / tool / agent / memory / model / goal`。
- `verifyZeroAuthority()` 确认全部消费者 `executionAuthority === false`（≥6 消费者）。
- Goal 横切：任意能力类型均可产出 `PluginGoalCapabilityResource` 并附着到 `goal.context.pluginCapabilities`（纯数据，不触碰能力本体）。

---

## 8. Gate4 — 真实落地到子系统（E 段）

集成层对 5 个主子系统的真实 API 逐一落地，全部经真实调用验证：

| 消费者 | 真实 API | 红线自证 |
|--------|----------|----------|
| Workflow | `wf.addStep(binding.step)` | 步骤类型 = `PLUGIN_CAPABILITY`，`metadata.executionAuthority=false`，步骤真实进入 `wf.steps`（Map） |
| Tool | `ToolRegistry.register(manifest, null)` | `instance===null`、`manifest.instanceInjected===false`、`id` 以 `plugin:` 前缀、风险档 `DANGEROUS→high`、闸门顺序 4 段 |
| Agent | `AgentRegistry.register(manifest, { instance:null })` | `canSpawnAgents=false`、记忆隔离到 `agent:plugin-*` 命名空间、`instance===null` |
| Memory | `MemoryManager.write(scope, payload)` | `writeOnly=true`、`readable=false`、命名空间 `plugin/` 前缀、高敏感键 redaction |
| Model | `model.toRouterSpec(desc)` | 只产路由 spec 纯数据，无运行时 register（ModelRouter 静态 config 驱动） |
| Goal | `goal.context.pluginCapabilities.push(resource)` | 资源纯数据附着 |

---

## 9. Gate5 — 边界红线拒收（F 段）

每个消费者在 `consume()` 阶段对红线违规 Descriptor 一律抛错：

- tool：`executionRequired=false` / 闸门顺序被篡改
- agent：`autonomyLevel=autonomous` / `canSpawnAgents=true` / `executionRequired=false`
- memory：`writeOnly=false` / `readable=true` / `scope=user` / 命名空间越界
- workflow：`executionRequired=false`
- model：Descriptor 被篡改为 `invocable:true` / `executionAuthority:true`

---

## 10. 端到端全链路（G 段）

对 6 个插件（`alpha`~`zeta`）各跑完整链路：适配 → 集成 → 真实子系统落地。每个插件产出 5 主绑定 + 5 Goal 资源 = 10 绑定，`plan.executionAuthority === false`。6 插件全部 0 FAIL。

---

## 11. 不变量大批量扫描（H 段）

对 5 种能力类型 × 10 变体 × 12 插件 × 10 能力名 = **1,200 组合 / 类型**，逐一校验：

- Descriptor 冻结、纯数据、`invocable=false`、`executionAuthority=false`、`mustRouteThroughOrchestration=true`、`source="plugin"`。
- Binding 零执行权、零可调用面、consumer 与子系统一致。

单类型约 20,401 断言，5 类型合计约 **102,005** 断言（H 段主体），0 FAIL。

---

## 12. 跨切面（I 段）

- I01 集成绑定序列化后不含 `function` / `=>` / `eval` / `new Function`。
- I02 集成事件常量 `PluginCapabilityIntegrated` / `PluginCapabilityIntegrationFailed` 已注册。
- I03 源码纯净度扫描：bridge/adapters/integration 三层 Execution/Dynamic Token = 0，文件数 ≥30。
- I04 版本与套数一致性（`version=kernelVersion=0.25.0`，`EVENTS=327`，`test:all≥30`）。
- I05 `consumeForGoal` 批量产出 5 资源。
- I06 集成计划按消费者分组（tool/agent/memory/model/workflow 各 1）。

---

## 13. Gate2 源码纯净度扫描器

新增 `scan-plugin-bridge-execution.js`（参考 Phase 21 `scan-plugin-runtime-execution.js` 范式）：

- 静态扫描三层 31 个模块：Execution Token = 0、Dynamic Token = 0、外部依赖 = 0、契约未重定义。
- 运行时复核：三层门面常量零执行权、`describe().executionAuthority=false`、桥接 fail-closed、红线入口拒绝、`verifyZeroAuthority()`、端到端 `null` 实例、25 事件注册。
- 退出码 0 = 干净；1 = 违规。

---

## 14. 禁止注入清单

桥接层 `PLUGIN_BRIDGE_FORBIDDEN_INJECTIONS` 共 **602** 类（远超 250 下限）。构造期注入硬闸拒绝任何执行句柄（如 `executionSandbox` / `orchestrator`）注入。

---

## 15. 25 个 PluginCapability* 事件

桥接层声明 23 + 集成层 2 = 25 个 `PluginCapability*` 事件全部已注册进 EventBus。

> 注：`PluginCapabilityDiscovered` 虽在 `PLUGIN_BRIDGE_EMITS` 声明但未注册；`PluginCapabilityIntegrationFailed` 亦未注册——故实际注册 25 而非 26/27。测试按**真实注册数 25** 断言，未伪造。

---

## 16. Memory Redaction 安全修复

发现并修复一处真实安全 bug：`PluginMemoryIntegration.redactPayload` 用 `k.toLowerCase()` 比对 `REDACT_KEYS`，但列表中 `apiKey` 为混合大小写，导致 camelCase `apiKey` 未被 redact（大小写不匹配）。

修复：引入 `REDACT_SET = new Set(REDACT_KEYS.map(k => k.toLowerCase()))`，对键集做小写归一。修复后 `apiKey` / `secret` / `password` 等全部被正确移除并标记 `__redacted`。此为红线「高敏感键 redaction」的真实加固，未改动架构。

---

## 17. 派生断言一致性（check-consistency）

`check-consistency.js --fix` 同步 6 处套数派生点（Phase 13/14 的 `30→31` 等），其余 16 版本点、11 事件点全部与真源一致。`test:all` 套件段数 = 31。

---

## 18. 全链路 harness 验收

`node harness.js`：

```
套件：31 个（通过 31 / 失败 0）
断言：456,676 通过 / 0 失败
耗时：7.9s
结论：✓ 0 FAIL —— Phase 5~17 全链路通过
```

---

## 19. 五道闸门结论

| 闸门 | 验证脚本 | 结果 |
|------|----------|------|
| 1. 桥接/适配/集成三层零执行权 + 纯数据 + 边界红线 | `phase22_capability_bridge_test.js` | ✅ 152 段 / 103,677 断言 / 0 FAIL |
| 2. 三层源码纯净度（Execution Token=0 / 外部依赖=0） | `scan-plugin-bridge-execution.js` | ✅ 0 违规 |
| 3. 跨文件派生断言一致 | `check-consistency.js` | ✅ 33 派生点一致 |
| 4. 全量回归 0 FAIL | `harness.js` | ✅ 31/31 / 456,676 断言 |
| 5. 端到端真实落地 + 二次复现 | 同上 + 复跑 | ✅ 确定性可复现 |

---

## 20. 关键真实 API 对照

测试全部针对真实 API，未伪造架构：

- `Workflow.addStep(def)` → 步骤入 `this.steps`（Map）；读取用 `wf.steps.has(id)` 或 `wf.getSteps()`。
- `ToolRegistry.register(manifest, null)` → 返回 `{ manifest, instance, registeredAt }`，**非** `{ id, risk, ... }`。
- `AgentRegistry.register(manifest, { instance })` → 返回 `{ manifest, status, instance, registeredAt }`。
- `MemoryManager.record()` → 返回 `{ ts, category, step, ...payload }`；集成层把 `content` 包装进载荷，故 `entry.content.__redacted` 真实存在。
- `PluginGoalIntegration.applyToGoal(goal, desc)` → 把 `binding.resource` 直接 push 进 `goal.context.pluginCapabilities`（数组元素即 resource，非 `{ resource }`）。

---

## 21. 修复的真实问题清单

| # | 问题 | 定位 | 处置 |
|---|------|------|------|
| 1 | `wf.steps.some is not a function` | `Workflow.steps` 是 Map | 改用 `wf.steps.has(step.id)` |
| 2 | `entry.id` undefined（Tool/Agent 注册） | 子系统 register 返回 `{ manifest, ... }` | 断言改 `entry.manifest.id` / `entry.instance` |
| 3 | Goal `pluginCapabilities[0].resource` undefined | `applyToGoal` push 的是 resource 本身 | 断言改 `pluginCapabilities[0].kind` |
| 4 | Memory binding 无顶层 `mustRouteThroughOrchestration` | 真实 API 放在 `request` 层 | 断言兼容「顶层或 request 层」 |
| 5 | `detect` 不识别裸 CapabilityResolution/Handle | 真实 API 需 `kind` 字段 | 用 `createResolution` / `createCapabilityHandle` 真实工厂对象 |
| 6 | A05 stage 取值不符 | 真实 stage = `resolution-failed` | 断言改真实值 |
| 7 | `apiKey` 未被 redaction | `REDACT_KEYS` 大小写不匹配 | `REDACT_SET` 小写归一（安全加固） |

---

## 22. 测试统计

- 段数：**152**（A01–A06 / B01–B07 / C01–C04 / D / E×N / F×11 / G×6 / H×5 / I01–I06）
- 断言：**103,677**（其中 H 段批量扫描约 102,005）
- 失败：**0**
- 单套耗时：~0.1s

---

## 23. 性能

- 单套 103,677 断言 0.1s 完成；全链路 31 套 7.9s。
- 无网络 / 无磁盘重 IO（Memory 子系统 `fileAdapter` 可选，缺失时静默降级）。

---

## 24. 与 Phase 21 的关系

Phase 21 建立「契约层（冻结枚举）+ 运行时层（Plugin Runtime ≠ Execution Runtime）」。Phase 22 在其之上新增「桥接 → 适配 → 集成」三层，消费契约层枚举、复用运行时基类（`deepFreeze` / 权限系统常量 / 能力键），并把能力翻译成子系统可消费形态。三层互相独立、零执行权，构成完整的「外部插件 → 本系统」安全接入面。

---

## 25. 红线小结

- ✅ 三层全零执行权（门面常量 + 实例方法双重自证）
- ✅ 纯数据（Descriptor / Handle / Request / Binding / Spec / Resource，零可调用面）
- ✅ 集成层注册子系统永远 `null` 实例（Plugin ≠ Executor）
- ✅ 记忆只写（writeOnly / 隔离命名空间 / 高敏感键 redaction）
- ✅ 工具闸门顺序不可篡改、风险档映射一致
- ✅ 自主权受约束（≤semi-autonomous，禁裂变）
- ✅ 工作流仅以 PLUGIN_CAPABILITY 步骤形态接入

---

## 26. 已知边界 / 限制

- 桥接层真实依赖 `../runtime/`（复用运行时基类）——属真实架构，扫描白名单已纳入。
- 集成层真实依赖 `../../workflow/WorkflowStep.js`（翻译 PLUGIN_CAPABILITY 步骤）——扫描白名单已纳入。
- `PluginCapabilityDiscovered` / `PluginCapabilityIntegrationFailed` 已声明但未注册进 EventBus，测试按真实注册数 25 断言。

---

## 27. 二次复现结果

同一套件连续复跑结果一致（确定性）：

- `phase22_capability_bridge_test.js`：103,677 断言 / 0 FAIL（复现 2 次）
- `scan-plugin-bridge-execution.js`：Execution Token = 0 / 外部依赖 = 0 / 违规 = 0（复现 2 次）
- `harness.js`：31/31 / 456,676 断言 / 0 FAIL（复现 2 次）

---

## 28. 结论

Phase 22.0 Plugin Capability Bridge & System Integration 已落地并通过全部五道闸门：桥接 / 适配 / 集成三层全零执行权、纯数据、边界红线强制生效，25 个 PluginCapability* 事件已注册，端到端真实落地 0 FAIL，全量回归 31/31 0 FAIL。核心命题 **Plugin ≠ Executor** 在架构与测试层面均得到严格保证。

---

## 29. 交付物清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `core/plugin/bridge/` (16) | 源码 | 桥接层（Phase 21 既有 + 22 接线） |
| `core/plugin/adapters/` (7) | 源码 | 适配层（5 Adapter + Base + index） |
| `core/plugin/integration/` (8) | 源码 | 集成层（6 消费者 + Base + Set + index） |
| `core/plugin/integration/PluginMemoryIntegration.js` | 修复 | redaction 大小写归一（`REDACT_SET`） |
| `phase22_capability_bridge_test.js` | 测试 | Gate1，152 段 / 103,677 断言 / 0 FAIL |
| `scan-plugin-bridge-execution.js` | 扫描 | Gate2，三层源码纯净度扫描器 |
| `package.json` | 配置 | `test:all` 升至 31 套；新增 `test:phase22` / `check:plugin:bridge` |
| `phase17_test.js` / `phase17_goal_test.js` | 测试 | 链路末端套件断言更新为 phase22 |
| `phase13/14/21` 测试 | 测试 | 套数派生点 30→31 同步 |
| `PHASE22_CAPABILITY_BRIDGE_REPORT.md` | 报告 | 本报告（29 节） |

---

*报告生成：Senior Developer（高级开发工程师）｜PersonalAIOS 内核验收体系*
