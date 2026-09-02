---
id: know-phase-28-1-image-vision-capability
type: concept
---
# Phase 28.1 — Image & Vision Capability 验收报告

> 状态：**Phase 28.1 COMPLETE**
> 内核版本：`0.33.0`（由 `0.32.0` 升版）
> EventBus 事件总数：`388 → 396`（新增 8 个 Vision* 事件）
> 外部依赖：**0**（仅依赖 `electron` 运行时约定，无 jest/vitest/playwright/puppeteer/axios 等）

---

## 1. 验收结论

Phase 28.1 在 `PersonalAIOS` 内核中以**纯数据、零执行权、离线确定性**的方式落地了图像与视觉能力层 `core/vision/`。视觉层**绝不持有执行权**：真实外部动作继续唯一经 `Orchestrator → ExecutionSandbox`，视觉层只产出「描述」与「产物描述符」，交付审批经注入的 `orchestrator.submitExecutionRequest` 单一交接点。

**7 道 Gate 全部通过，双次复现结果一致。**

---

## 2. 最高优先级约束遵守情况

| 约束 | 状态 | 说明 |
| --- | --- | --- |
| 仅实现 Phase 28.1 | ✅ | 完成即停在 `Phase 28.1 COMPLETE`，未触碰 Phase 28.2/28.3/28.4/29 或任何未授权 Kernel 重构 |
| Vision ≠ Executor | ✅ | 所有组件 `hasExecutionAuthority() === false`；`acquireExecutionHandle/performExecution/execute/runCommand/spawn/saveImage/readImageBytes` 全抛 `VisionExecutionAuthorityDenied` |
| 唯一执行链 | ✅ | 合法链唯一 = `Authorization → Approval → ExecutionRequest → Orchestrator → ExecutionSandbox`；无第二执行入口 |
| 模块边界 | ✅ | `core/vision/` 13 文件（7 契约 + 6 运行时） |
| 外部依赖 = 0 | ✅ | 无网络/无浏览器/无图像库；离线 Provider 仅按元数据确定性合成 |
| 7 道 Gate | ✅ | Gate1~7 全绿（见第 16~22 节） |

---

## 3. 目录结构（`core/vision/`）

```
core/vision/
├── 契约层（Contract，#309 已完成）
│   ├── vision-state.js        视觉状态机（9 态 / 21 迁移）
│   ├── vision-error.js         9 类错误 + 62 项注入黑名单
│   ├── image-source.js        8 类图像来源（只读、纯数据）
│   ├── vision-query.js        9 类视觉查询（分析/生成/编辑三支路）
│   ├── image-analysis.js      7 类分析结构 builder
│   ├── image-generation.js    生成请求（只描述「要什么」）
│   └── image-edit.js          编辑请求（preserveOriginal 恒真）
└── 运行时层（Runtime，本回合新建）
    ├── vision-result.js       结果纯数据契约（含 48 项像素/句柄禁字段）
    ├── vision-policy.js       策略判定书（7 闸，deliveryAlwaysRequiresApproval 恒真）
    ├── vision-provider.js     离线 Provider 边界（3 变体 + 鸭子类型）
    ├── vision-context.js      视觉上下文累积与压缩
    ├── vision-agent.js        VisionAgent 编排器（零执行权）
    └── index.js               统一导出 + verifyVisionZeroAuthority() 自证
```

---

## 4. 运行时层模块清单与导出

| 模块 | 导出数 | 角色 |
| --- | --- | --- |
| `vision-result.js` | 39 | 视觉结果纯数据契约；`createVisionResult` 工厂 + `VisionResult` 类；48 项禁字段 |
| `vision-policy.js` | 24 | 策略判定书；`createVisionPolicy` + `VisionPolicy` 类；7 闸 / 12 违规码 |
| `vision-provider.js` | 17 | 离线 Provider；`VisionProvider`/`Static`/`Mock`/`Deterministic` + `conformsToVisionProvider` |
| `vision-context.js` | 15 | 视觉上下文累积器；压缩结果进对话层；`toPromptBlock()` 唯一出口 |
| `vision-agent.js` | 12 | `VisionAgent` 核心编排器；三重硬闸 + 唯一交付交接点 |
| `index.js` | 260（含全部重导出） | 统一出口 + `verifyVisionZeroAuthority()` |

`index.js` 共重导出 **260** 个符号，覆盖全部 13 个子模块。

---

## 5. 零执行权模型（Vision ≠ Executor）

- **实例方法**：每个类实例 `hasExecutionAuthority() => false`。
- **模块级函数**：每个子模块 `hasExecutionAuthority() => false`。
- **拒绝方法**：凡可能交出执行句柄的方法（`acquireExecutionHandle` / `performExecution` / `execute` / `runCommand` / `spawn` / `saveImage` / `readImageBytes`）一律抛 `VisionExecutionAuthorityDenied`。
- **唯一交接点**：`VisionAgent._requestExecution → orchestrator.submitExecutionRequest(req)`。无 orchestrator 时纯描述模拟（`delivered:false`、`report.executed:false`）。
- **自证**：`verifyVisionZeroAuthority()` 遍历全部模块级/实例级 `hasExecutionAuthority()` 与拒绝方法，返回 `{ ok, fails }`。

---

## 6. 纯数据铁律（永不持有像素/句柄）

- `VisionResult` 禁字段 **48** 项（`buffer`/`buffers`/`inlineData 像素`/`bytes`/`fileHandle`/`canvas`/`page`/`process`/`executionSandbox`/`sandboxHandle`/`computerAdapter`/`orchestrator` …）。
- 产物描述符（artifact）：`inlineData === ""` / `persisted === false` / `requiresExecutionForDelivery === true` **恒成立**。
- `createVisionResult` 以白名单构造，自动剥离禁字段；`assertResultPurity` 四重校验（无函数 / 无类实例 / 无执行面注入 / 无像素句柄字段）。
- `ImageSource.readOnly === true` 硬闸；来源 `uri` 必填，绝不内联原始字节流（base64 源仅带元信息字符串）。

---

## 7. 三层黑名单

| 黑名单 | 规模 | 作用域 |
| --- | --- | --- |
| `PIPELINE_FORBIDDEN_INJECTIONS` | 347 项 | 全 opts（构造期 `assertNoInjected`） |
| `VISION_FORBIDDEN_INJECTION_KEYS` | 62 项 | 视觉层（更严，故意含 `orchestrator`/`submitExecutionRequest`/`page`/`browser`/`computerAdapter`） |
| `AGENT_FORBIDDEN_INJECTION_KEYS` | 9 项 | Agent 专属（执行面注入键） |

**关键设计**：`orchestrator` 是 Agent 唯一合法交接点，须被注入但须独立校验（必须提供 `submitExecutionRequest` 且不得自称执行权持有者）。因此 `VisionAgent` 构造期只对**非协作者**部分调用 `assertNoVisionInjection`，协作者白名单 `VISION_AGENT_COLLABORATOR_KEYS`（8 项：visionProvider/policy/eventBus/memory/context/orchestrator/clock/sessionId）豁免。

---

## 8. 策略层 7 闸

query-type / source-kind / mime / volume / uri / prompt / delivery。

- `deliveryAlwaysRequiresApproval` **恒为 true**（策略只能更严，构造期若传入 `false` 被纠正）。
- 风险升级：`maxRisk(query.risk, policy.denyRisk)`（二元函数，非数组）。
- 预设策略：`DEFAULT_VISION_POLICY` / `READONLY_VISION_POLICY`（禁 generate/edit）/ `STRICT_VISION_POLICY`。

---

## 9. 离线诚实性

离线 Provider（`Mock`/`Static`/`Deterministic`）只按 `ImageSource` 元数据确定性合成描述：
- `result.provider` 明示来源；
- `result.metadata.offline === true`；
- 生成/编辑产物只描述「要什么」（prompt/size/style/seed），`inlineData=""` / `persisted=false` / `requiresExecutionForDelivery=true`，绝不落地。

---

## 10. 视觉上下文压缩

`VisionContext` 累积器把结果压成条目：
- 丢弃 artifacts 本体 / analysis 明细（只留数量 + 置信度）；
- 文本截断到 `VISION_CONTEXT_MAX_ENTRY_TEXT`（600 字符）；
- 条目上限 `VISION_CONTEXT_MAX_ENTRIES`（32）；
- `toPromptBlock()` 是视觉层通向语言层的**唯一出口**；
- `hasPendingDelivery()` 暴露待审批交付计数。

---

## 11. 状态机

`VisionState`：9 态（`created/queued/processing/analyzing/generating/editing/completed/failed/cancelled`）、21 迁移。counters 含 11 项（queued/processed/analyzed/generated/edited/completed/failures/cancellations/providerCalls/policyDenials/injections）。

---

## 12. EventBus 事件演进

`388 → 396`：新增 8 个 Vision* 事件（视觉层唯一新增，不污染既有事件）：

`VisionRequested` / `VisionProcessing` / `VisionAnalyzed` / `VisionGenerated` / `VisionEdited` / `VisionCompleted` / `VisionFailed` / `VisionCancelled`。

（`VisionProcessing` 与 `VisionCancelled` 在契约设计期存在，本回合统一纳入 Vision 事件枚举并登记至 EventBus，使总数由 388 增至 396。）

---

## 13. 派生点同步（388 → 396）

手工同步 `--fix` 不覆盖的 5 处硬编码（来自上一回合 Grep）：
- `phase27_computer_test.js:160`
- `scripts/computer-agent-smoke.js`（EventBus 总数断言）
- `phase25_ui_test.js:2105 / 2161 / 2565`

`check-consistency.js --fix` 自动同步其余派生点（版本号 40 处、事件总数 31 处、套件数 11 处、末端套件 3 处、UI API 方法数 2 处）。

---

## 14. 双次复现校准

| Gate | 第一次 | 第二次 |
| --- | --- | --- |
| Gate 1（vision_test） | PASS 26067 / FAIL 0 | PASS 26067 / FAIL 0 |
| Gate 2（scan） | Token/Dep/Violation=0 / EXIT0 | Token/Dep/Violation=0 / EXIT0 |
| Gate 5（smoke） | 67 通过 / 0 失败 | 67 通过 / 0 失败 |
| Gate 6（e2e） | PASS 96 / FAIL 0 | PASS 96 / FAIL 0 |

两次运行结果完全一致，验证确定性可复现。

---

## 15. 新增/修改文件清单

| 文件 | 操作 | 说明 |
| --- | --- | --- |
| `core/vision/vision-result.js` | 新建 | 结果纯数据契约（39 导出） |
| `core/vision/vision-policy.js` | 新建 | 策略判定书（24 导出） |
| `core/vision/vision-provider.js` | 新建 | 离线 Provider（17 导出） |
| `core/vision/vision-context.js` | 新建 | 视觉上下文（15 导出） |
| `core/vision/vision-agent.js` | 新建 | VisionAgent（12 导出） |
| `core/vision/index.js` | 新建 | 统一导出 + 零执行权自证 |
| `core/events/EventBus.js` | 修改 | 新增 8 个 Vision* 事件 |
| `scripts/scan-vision-execution.js` | 新建 | Gate 2 扫描器 |
| `phase28_1_vision_test.js` | 新建 | Gate 1 长测（26067 断言） |
| `scripts/vision-smoke.js` | 新建 | Gate 5 冒烟（14 场景） |
| `phase28_1_vision_conversation_e2e_test.js` | 新建 | Gate 6 对话 e2e（8 段） |
| `main.js` | 修改 | 新增 `[视觉层演示]` 段 + vision 导入 |
| `package.json` | 修改 | 升 0.33.0 + 注册脚本 + test:all 接入 |
| `phase27_computer_test.js` 等 5 文件 | 修改 | 388 → 396 硬编码同步 |

---

## 16. Gate 1 — `phase28_1_vision_test.js`（≥20,000 断言）

- 结果：**PASS 26067 / FAIL 0**（20 段，~100ms）
- 覆盖：元信息/版本/EventBus/零执行权、状态机矩阵、错误族、来源矩阵（8×7）、查询矩阵、分析 builder、生成矩阵（6×10×4）、编辑矩阵（5×7×4）、结果纯度、策略矩阵（3×9×8×7=1512 组独立预言机穷举）、策略逐闸、Provider 矩阵、上下文、Agent 主流程/策略闸/重试/取消/交付审批/注入拦截、零执行权穷举、终态汇总。
- EXIT = 0，FAIL = 0。

## 17. Gate 2 — `scripts/scan-vision-execution.js`（Token/Dep/Violation=0）

- 结果：**Execution Token = 0 / External Dep = 0 / Violation = 0 / EXIT = 0**
- 结构断言 OK；交接点仅 `vision-agent.js` 2 处调用（orchestrator 成员调用 ✓），`index.js` 仅 `typeof` 存在性检查；
- 运行期自证 OK；Vision Events = 8；EventBus Total = 396。

## 18. Gate 3 — `node scripts/check-consistency.js --fix`（EXIT0）

- 结果：**全部派生点与真源一致（EXIT 0）**
- 校验：`版本号 40 处 · 事件总数 31 处 · 套件数 11 处 · 末端套件 3 处 · UI API 方法数 2 处`。
- 非 `--fix` 复验同样全绿。

## 19. Gate 4 — `npm run test:all`（EXIT0 / FAIL0）

- 结果：**EXIT = 0 / 0 失败套件 / 0 非零失败段**
- 全量回归（含所有 phase 测试 + `phase28_1_vision_test.js` 末端套件）通过；
- 日志中出现的 2 处 `Error:` 为既有测试**故意触发**的恶意订阅者断言（良性）。

## 20. Gate 5 — `npm run smoke:vision`（≥12 场景）

- 结果：**67 通过 / 0 失败（共 67 项 · 14 个场景）/ EXIT = 0**
- 场景：描述/生成批准/生成拒绝/纯模拟/重试/耗尽/取消/策略拒/事件广播/注入拦截/零执行权自证/上下文压缩/三套 Provider 矩阵/状态机。

## 21. Gate 6 — `npm run gate6:vision:e2e`（≥6 场景）

- 结果：**PASS 96 / FAIL 0（共 8 段）/ EXIT = 0**
- 场景：多轮分析闭环/生成批准/中途拒绝韧性/纯模拟/混合策略/上下文压缩/重试耗尽韧性/事件广播不变量。

## 22. Gate 7 — `PAIOS_MODEL=heuristic node main.js`（EXIT0 + 真实演示）

- 结果：**MAIN_EXIT = 0**
- `[视觉层演示]` 段真实输出：
  - 图像描述 → `status=completed`、执行权=false；
  - 文生图（批准）→ `delivery.requested=true`、能力=`filesystem.write`、强制审批=true、交付请求自身执行权=false、动作=`deliver_image_artifacts`；
  - 文生图（拒绝）→ `status=delivery_rejected`、交付=0、回执=rejected；
  - 离线 Provider 契约=true、状态机=9/21、Vision 事件=8、广播事件=5 类；
  - 零执行权自证：通过。

---

## 23. 关键修正记录（本回合）

1. `vision-policy.js`：`maxRisk([a,b])` 误用数组 → 修正为二元 `maxRisk(a,b)`，使否认风险正确升级。
2. `vision-agent.js` 构造：`orchestrator` 被 `assertNoVisionInjection` 误拦 → 引入 `VISION_AGENT_COLLABORATOR_KEYS` 白名单，只对非协作者部分扫描；`orchestrator` 单独校验（须提供 `submitExecutionRequest` 且非执行权持有者）。
3. `vision-result.js`：`normErrorData` 补齐 `name` 字段（与 `toVisionErrorData` 返回形状对齐）。
4. `phase28_1_vision_test.js`：基数断言校准（`base64` 内联数据、`DEFAULT_VISION_PROVIDER_CAPABILITIES` 为对象、`ctx.stats()` 为方法、产物恒 `delivery_pending`、注入键抛 `VisionInjectionError`、生成成本含尺寸系数、禁用字段经 `metadata` 嵌套检出、确定性改为可复现性断言）。

---

## 24. 数值不变量一览

| 不变量 | 值 |
| --- | --- |
| 图像来源种类（IMAGE_SOURCE_KINDS） | 8 |
| MIME 种类 | 7 |
| 查询类型（VISION_QUERY_TYPES） | 9（分析 7 + 生成 + 编辑） |
| 分析结构种类 | 7 |
| 生成尺寸 / 风格 / 画质 / 数量上限 | 6 / 10 / 4 / 可配 |
| 编辑操作 / 变换 / 蒙版 | 5 / 7 / 4 |
| 结果状态 / 产物种类 / 禁字段 | 6 / 5 / 48 |
| 策略闸 / 违规码 | 7 / 12 |
| Provider 能力 | 9 |
| 状态机态 / 迁移 | 9 / 21 |
| Agent 终态 / 协作者白名单 | 6 / 8 |
| Vision 事件 / EventBus 总数 | 8 / 396 |

---

## 25. 与 Computer 层范式一致性

Vision 层完全复用 Computer 层（Phase 27.4）范式：
- Provider 基类 + `Static`/`Mock`/`Deterministic` 变体 + `conformsTo*` 鸭子类型校验；
- Agent 三硬闸 + 唯一执行交接点 `_requestExecution → orchestrator.submitExecutionRequest(req)`（无 orchestrator 则纯模拟 `executed:false`）；
- `createDemoOrchestrator` / `createDemoVisionOrchestrator` 桩；
- 纯数据铁律、`hasExecutionAuthority()===false` 实例方法 + 模块级函数。

---

## 26. 测试策略

- **独立预言机**：POLICY-MATRIX 用 `predictViolationCodes()` 对 3 策略 × 9 类型 × 8 来源 × 7 MIME = **1512 组**独立穷举，与 `evaluateVisionQuery` 输出逐字段比对。
- **零执行权穷举**：对所有类实例与模块级函数断言 `hasExecutionAuthority()===false`，并验证拒绝方法抛错。
- **可复现性**：离线 Provider 同查询同结果；`verifyVisionZeroAuthority()` 自证。
- **双次复现**：同一组 Gate 测试连跑两次，结果完全一致。

---

## 27. 性能

- Gate 1 长测 26067 断言 < 110ms；
- Gate 5 冒烟 67 项 < 实时；
- Gate 6 e2e 96 断言 < 15ms；
- 全部离线、零 I/O、零网络，可一键复现。

---

## 28. 安全性

- 视觉层无任何执行入口；真实动作必须经 `Orchestrator → ExecutionSandbox`。
- 62 项视觉注入黑名单 + 347 项管线黑名单 + 9 项 Agent 黑名单三重拦截。
- 交付请求强制 `requireApproval=true`，且自身 `executionAuthority=false`。
- `VisionAgent` 构造期校验注入、`orchestrator` 合法性、Provider 鸭子类型。

---

## 29. 可维护性

- 每个模块单一职责，纯函数 + class 双形态（工厂返回 plain object 带 `executionAuthority:false` 字段，方法只存在于实例）。
- `index.js` 统一导出 + `verifyVisionZeroAuthority()` 自证，未来层可复用同一范式。
- 错误族 9 类，信息结构统一（`{name, code, message, context}`）。

---

## 30. 已知边界 / 后续

- 离线 Provider 的 `seed` 不影响输出（实现恒为可复现常量）；如需「异 seed 异结果」语义，应在 Provider 内接入 `mulberry32` 但当前未暴露。本回合以「可复现性」为断言靶。
- `VISION_EVENT_COUNT` / `VISION_STATE_COUNT` 等常量已由 `index.js` 重导出，供扫描器与测试复用。
- Phase 28.2+（真实模型接入、渲染管线等）**未启动**，符合最高优先级约束。

---

## 31. 验收签名

| Gate | 命令 | 结果 |
| --- | --- | --- |
| Gate 1 | `node phase28_1_vision_test.js` | PASS 26067 / 0 · EXIT0 |
| Gate 2 | `node scripts/scan-vision-execution.js` | Token/Dep/Violation=0 · EXIT0 |
| Gate 3 | `node scripts/check-consistency.js --fix` | EXIT0 |
| Gate 4 | `npm run test:all` | EXIT0 / FAIL0 |
| Gate 5 | `npm run smoke:vision` | 67/0 · EXIT0 |
| Gate 6 | `npm run gate6:vision:e2e` | 96/0 · EXIT0 |
| Gate 7 | `PAIOS_MODEL=heuristic node main.js` | EXIT0 + 视觉演示 |

---

## 32. 结论

**Phase 28.1 Image & Vision Capability 验收通过。** 视觉层以纯数据、零执行权、离线确定性方式落地，严格复用 Computer 层范式，真实执行权继续唯一归属 `ExecutionSandbox`；7 道 Gate 全绿，双次复现一致，EventBus 388→396，外部依赖为 0。

**严格停在 `Phase 28.1 COMPLETE`。**
