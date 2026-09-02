---
id: know-phase-28-2-document-office-capability
type: concept
---
# Phase 28.2 — Document & Office Capability 验收报告

> 状态：**Phase 28.2 COMPLETE**
> 内核版本：`0.33.0`（与 Phase 28.1 持平，本回合未升版）
> EventBus 事件总数：`396 → 404`（新增 8 个 Document* 事件）
> 外部依赖：**0**（仅依赖 `electron` 运行时约定，无第三方文档库 / 无网络 / 无文件 IO）

---

## 1. 验收结论

Phase 28.2 在 `PersonalAIOS` 内核中以**纯数据、零执行权、离线确定性**的方式落地了文档与 Office 能力层 `core/document/`。文档层**绝不持有执行权**：真实外部动作（写盘 / 下载）继续唯一经 `Orchestrator → ExecutionSandbox`，文档层只产出「模型」「产物描述符」「渲染结果」与「交付请求」，交付审批经注入的 `orchestrator.submitExecutionRequest` 单一交接点。

**6 道自动化 Gate 全部通过；`test:all` 全量回归 41 套 0 FAIL；EventBus 396→404；外部依赖为 0。**

> 注：Gate 7（`PAIOS_MODEL=heuristic node main.js` 实时演示）本回合**未接入**——Phase 28.2 新增的是能力层 + 测试 + 扫描器，未在 `main.js` 增加 `[文档层演示]` 段；既有 `main.js` 仍可正常 EXIT 0。

---

## 2. 最高优先级约束遵守情况

| 约束 | 状态 | 说明 |
| --- | --- | --- |
| 仅实现 Phase 28.2 | ✅ | 完成即停在 `Phase 28.2 COMPLETE`，未触碰 Phase 28.3/28.4/29 或任何未授权 Kernel 重构 |
| Document ≠ Executor | ✅ | 所有组件 `hasExecutionAuthority() === false`；`acquireExecutionHandle/performExecution` 全抛 `DocumentExecutionAuthorityDenied` |
| 唯一执行链 | ✅ | 合法链唯一 = `Authorization → Approval → ExecutionRequest → Orchestrator → ExecutionSandbox`；无第二执行入口 |
| 模块边界 | ✅ | `core/document/` 17 文件（契约 + 运行时） |
| 外部依赖 = 0 | ✅ | 无网络 / 无文件 IO / 无文档库；离线 Provider 仅按元数据确定性合成 |
| 6 道 Gate | ✅ | Gate1~6 全绿（Gate4=test:all 41 套 0 FAIL） |

---

## 3. 目录结构（`core/document/`）

```
core/document/
├── 契约层（Contract，纯数据富模型）
│   ├── document-model.js        文档模型（23 字段 + documentModelFingerprint 确定性指纹）
│   ├── document-artifact.js     产物描述符 + 结果（二进制格式禁止携带字节）
│   ├── document-query.js        查询富模型（多类型 / 多支路）
│   ├── document-source.js       来源富模型（语义黑名单拒收像素/字节/句柄）
│   ├── document-context.js      文档上下文累积与压缩
│   ├── document-formats.js      格式常量（4 类二进制 + 文本类）
│   ├── document-template.js     渲染模板
│   ├── document-report.js       报告装配（纯数据）
│   └── document-error.js        错误族（DocumentValidationError / DocumentInjectionError / DocumentPurityError / DocumentPolicyDeniedError / DocumentCancelledError …）
└── 运行时层（Runtime）
    ├── document-converter.js    数据行 → 文档模型（createTable 补齐 rowCount）
    ├── document-provider.js     离线 Provider 边界（Static / Mock / Deterministic + 鸭子类型）
    ├── document-policy.js       策略判定书（query/source/format 多闸）
    ├── document-state.js        DocumentState（11 态 / 28 迁移）
    ├── document-agent.js        DocumentAgent 编排器（构建-审批-拒收-重试-取消闭环，零执行权）
    ├── document-renderer.js     模板渲染（纯数据结果）
    ├── document-delivery.js     交付流程（仅发起 ExecutionRequest）
    └── index.js                 统一导出 + verifyDocumentZeroAuthority() 自证
```

---

## 4. 模块清单与导出

| 模块 | 导出数 | 角色 |
| --- | --- | --- |
| `document-model.js` | 53 | 文档模型富模型；`createDocumentModel` + `documentModelFingerprint`（确定性 fnv1a+stableStringify） |
| `document-artifact.js` | 41 | 产物描述符 / 结果；二进制格式字节泄漏拦截；`assertResultPurity` |
| `document-error.js` | 22 | 错误族 + 注入黑名单 `DOCUMENT_FORBIDDEN_INJECTION_KEYS` |
| `document-policy.js` | 24 | 策略判定书；`createDocumentPolicy` + `DocumentPolicy` |
| `document-provider.js` | 16 | 离线 Provider；`Static`/`Mock`/`Deterministic` + `conformsToDocumentProvider` |
| `document-query.js` | 20 | 查询富模型；`createDocumentQuery` |
| `document-source.js` | 12 | 来源富模型；`guardSource` 语义黑名单扫描 |
| `document-context.js` | 15 | 文档上下文累积器；`toPromptBlock()` 唯一出口 |
| `document-converter.js` | 7 | 数据行 → 模型（`createTable` 补齐 `rowCount`） |
| `document-agent.js` | 12 | `DocumentAgent` 核心编排器；三重硬闸 + 唯一交付交接点 |
| `document-state.js` | 15 | `DocumentState`（11 态 / 28 迁移） |
| `document-renderer.js` | 6 | 模板渲染（纯数据结果） |
| `document-template.js` | 12 | 渲染模板定义 |
| `document-report.js` | 20 | 报告装配（纯数据） |
| `document-formats.js` | 10 | 格式常量（pdf/docx/pptx/xlsx + markdown/html…） |
| `document-delivery.js` | 10 | 交付流程（仅发起 ExecutionRequest） |
| `index.js` | 278（含全部重导出） | 统一出口 + `verifyDocumentZeroAuthority()` |

`index.js` 共重导出 **277** 个符号，覆盖全部 17 个子模块。

---

## 5. 零执行权模型（Document ≠ Executor）

- **实例方法**：每个类实例 `hasExecutionAuthority() => false`。
- **模块级函数**：每个子模块 `hasExecutionAuthority() => false`。
- **拒绝方法**：凡可能交出执行句柄的方法（`acquireExecutionHandle` / `performExecution` / `execute` / `runCommand` / `spawn` / `writeFile` / `readFileBytes`）一律抛 `DocumentExecutionAuthorityDenied`。
- **唯一交接点**：`DocumentAgent._requestExecution → orchestrator.submitExecutionRequest(req)`。无 orchestrator 时纯描述模拟（`delivered:false`、`report.executed:false`）。
- **自证**：`verifyDocumentZeroAuthority()` 遍历全部模块级/实例级 `hasExecutionAuthority()` 与拒绝方法，返回 `{ ok, fails }`。

---

## 6. 纯数据铁律（永不搬运字节/句柄）

- 二进制格式（pdf/docx/pptx/xlsx）产物**禁止携带任何字节**：`content===""` / `inlineData===""` / `persisted===false` / `requiresExecutionForDelivery===true` **恒成立**。
- `createDocumentArtifact` 以白名单构造，二进制字节泄漏拦截置于归一化**之前**（原实现在 `content` 已被置空后才检查，永不触发 —— 本回合修正）。
- `assertNoDocumentInjection`（`DOCUMENT_FORBIDDEN_INJECTION_KEYS`）+ `findSourceBannedFieldsDeep` + `findQueryBannedFieldsDeep` 三重语义扫描，拒收 `buffer`/`fileHandle`/`canvas`/`page`/`process`/`executionSandbox`/`sandboxHandle` 等像素 / 字节 / 句柄语义字段。
- `hasFunctionDeep` / `hasClassInstanceDeep` 校验结果对象无函数、无类实例。

---

## 7. 三层黑名单

| 黑名单 | 规模 | 作用域 |
| --- | --- | --- |
| `PIPELINE_FORBIDDEN_INJECTIONS` | 347 项 | 全 opts（构造期 `assertNoInjected`） |
| `DOCUMENT_FORBIDDEN_INJECTION_KEYS` | 文档层专用（含 `executionSandbox`/`orchestrator`/`page`/`computerAdapter`） | 文档层（更严，故意含协作者键以便独立校验） |
| `AGENT_FORBIDDEN_INJECTION_KEYS` | Agent 专属（执行面注入键） | DocumentAgent |

**关键设计**：`orchestrator` 是 Agent 唯一合法交接点，须被注入但须独立校验（必须提供 `submitExecutionRequest` 且不得自称执行权持有者）。`DocumentAgent` 构造期只对**非协作者**部分调用 `assertNoDocumentInjection`，协作者白名单豁免。

---

## 8. 策略层

`DocumentPolicy`：query-type / source-kind / format / volume / delivery 多闸。
- `deliveryAlwaysRequiresApproval` **恒为 true**（策略只能更严）。
- 违规码含 `query_kind_not_allowed`（冒烟场景 8 验证 Provider 零调用 + 判定书带违规码）。
- 预设策略：`DEFAULT_DOCUMENT_POLICY` / `READONLY_DOCUMENT_POLICY` / `STRICT_DOCUMENT_POLICY`。

---

## 9. 离线诚实性

离线 Provider（`Mock`/`Static`/`Deterministic`）只按 `DocumentSource` 元数据确定性合成描述：
- `result.provider` 明示来源；
- `result.metadata.offline === true`；
- 构建/转换产物只描述「要什么」，`inlineData=""` / `persisted=false` / `requiresExecutionForDelivery=true`，绝不落地字节。

---

## 10. 文档上下文压缩

`DocumentContext` 累积器把结果压成条目：
- 丢弃 artifacts 本体 / 渲染明细（只留数量 + 置信度）；
- 文本截断到 `DOCUMENT_CONTEXT_MAX_ENTRY_TEXT`；
- 条目上限 `DOCUMENT_CONTEXT_MAX_ENTRIES`；
- `toPromptBlock()` 是文档层通向语言层的**唯一出口**；
- `hasPendingDelivery()` 暴露待审批交付计数。

---

## 11. 状态机

`DocumentState`：**11 态**（`created/queued/planning/building/rendering/reviewing/delivery_pending/delivery_rejected/completed/failed/cancelled`）、**28 迁移**。counters 含 providerCalls / policyDenials / retries / cancellations / injections 等。

---

## 12. EventBus 事件演进

`396 → 404`：新增 8 个 Document* 事件（文档层唯一新增，不污染既有事件）：

`DocumentRequested` / `DocumentProcessing` / `DocumentRendered` / `DocumentReviewed` / `DocumentCompleted` / `DocumentDelivered` / `DocumentFailed` / `DocumentCancelled`。

（注：错误名 `DocumentPolicyDenied` / `DocumentCancelledError` 等**不是** EventBus 事件，仅作错误族；事件枚举严格为上述 8 个。）

---

## 13. 派生点同步（396 → 404，套数 40 → 41，末端 phase28_2）

- `check-consistency.js --fix` 自动同步 **44 处**派生点：事件总数 34 处、套件数 11 处、末端套件 3 处、版本号 40 处、UI API 方法数 2 处。
- **手动补同步 `--fix` 未覆盖的非标准 396 断言**（与 Phase 21 plugin 的 `split("&&").length` 同理，`--fix` 正则只认标准 `eq(...,N,...)` 形态）：
  - `phase25_ui_test.js`：`Object.keys(host.EVENTS).length` / `before.eventTypes` / `scanSrc.includes("EXPECTED_EVENT_BUS_TOTAL = 396")` 三处（host 前缀 / 属性 / 字符串字面量，`--fix` 正则不匹配）。
  - `phase28_1_vision_test.js`：`T.eq(keys.length, 396, …)`（`keys` 变量别名）。
  - `phase27_computer_test.js`：`T.eq(total, 396, …)`（`total` 变量别名）。
  - `scripts/scan-vision-execution.js` / `scan-computer-execution.js` / `scan-research-execution.js`：`EXPECTED_EVENT_BUS_TOTAL = 396` → 404（三套既有扫描器的总线总数常量，Phase 28.2 加事件后须跟进）。
- `package.json` 手工：test:all 接入（40→41 套）、新增 5 脚本、description 增 Phase 28.2 条款 + EventBus 396→404。

---

## 14. 双次复现校准

| Gate | 本次（修正后） | test:all 内复现 | 结论 |
| --- | --- | --- | --- |
| Gate 1（document_test） | PASS 29200 / FAIL 0 | PASS 29200 / FAIL 0 | 一致 |
| Gate 2（scan） | Token/Dep/Violation=0 / EXIT0 | （同扫描器） | 一致 |
| Gate 5（smoke） | 76 通过 / 0 失败 | — | 确定性 |
| Gate 6（e2e） | PASS 102 / FAIL 0 | — | 确定性 |

Gate 1 在 `test:all` 全量链末端被**再次**执行，结果完全一致（29200/0），验证确定性可复现；Gate 2/5/6 离线、零 I/O、零网络，连跑结果一致。

---

## 15. 新增/修改文件清单

| 文件 | 操作 | 说明 |
| --- | --- | --- |
| `core/document/*.js`（17 个） | 新建 | Document & Office 能力层（277 导出） |
| `core/events/EventBus.js` | 修改 | 新增 8 个 Document* 事件（396→404） |
| `scripts/scan-document-execution.js` | 新建 | Gate 2 扫描器 |
| `phase28_2_document_test.js` | 新建 | Gate 1 长测（29200 断言 / 21 段） |
| `phase28_2_document_conversation_e2e_test.js` | 新建 | Gate 6 对话 e2e（8 段） |
| `scripts/document-agent-smoke.js` | 新建 | Gate 5 冒烟（15 场景） |
| `package.json` | 修改 | 接入 test:all（41 套）+ 注册 5 脚本 + description 增 Phase 28.2 条款 |
| `phase25_ui_test.js` / `phase28_1_vision_test.js` / `phase27_computer_test.js` | 修改 | 396→404 非标准断言同步 |
| `scripts/scan-vision-execution.js` / `scan-computer-execution.js` / `scan-research-execution.js` | 修改 | `EXPECTED_EVENT_BUS_TOTAL` 396→404 同步 |

---

## 16. Gate 1 — `phase28_2_document_test.js`（≥20,000 断言）

- 结果：**PASS 29200 / FAIL 0**（21 段，~175ms）
- 覆盖：模型常量 / 字段数(23) / 指纹确定性、模型校验（非法 type 抛错）、产物/结果纯度（二进制禁字节）、Provider 矩阵（Static/Mock/Deterministic）、查询矩阵、来源语义黑名单、上下文、转换（createTable rowCount）、来源-交付-模板-渲染、状态机矩阵、事件点名（404）、Fuzz 模型(3000)/渲染(22000)/策略(2000)/Agent(1050)、零执行权穷举、断言计数。
- EXIT = 0，FAIL = 0。

## 17. Gate 2 — `scripts/scan-document-execution.js`（Token/Dep/Violation=0）

- 结果：**Execution Token = 0 / External Dep = 0 / Violation = 0 / EXIT = 0**
- 结构断言 OK；交接点仅 `document-agent.js` 2 处调用（orchestrator 成员调用 ✓），`index.js` 仅 `typeof` 存在性检查；
- 运行期自证 OK；Document Events = 8；EventBus Total = 404；State Machine = 11 态 / 28 迁移。

## 18. Gate 3 — `node scripts/check-consistency.js --fix`（EXIT0）

- 结果：**全部派生点与真源一致（EXIT 0）**
- 校验：`版本号 40 处 · 事件总数 34 处 · 套件数 11 处 · 末端套件 3 处 · UI API 方法数 2 处`。
- 非 `--fix` 复验同样全绿。

## 19. Gate 4 — `npm run test:all`（EXIT0 / FAIL0）

- 结果：**EXIT = 0 / 0 失败套件 / 0 非零失败段**
- 全量回归（含全部 phase 测试 + `phase28_2_document_test.js` 末端套件）通过；
- 41 套串行链字面串，符合 Phase 13/14 硬校验；`pretest:all` 已先跑 `check-consistency` 通过。

## 20. Gate 5 — `npm run smoke:document`（≥12 场景）

- 结果：**76 通过 / 0 失败（共 76 项 · 15 个场景）/ EXIT = 0**
- 场景：构建闭环 / 批准发起 ExecutionRequest / 拒绝零交付 / 纯模拟 / 重试 / 耗尽 / 取消 / 策略拒 / 事件广播 / 注入拦截 / 零执行权自证 / 上下文压缩 / 三套 Provider 矩阵 / 状态机 / 报告装配。

## 21. Gate 6 — `npm run gate6:document:e2e`（≥6 场景）

- 结果：**PASS 102 / FAIL 0（共 8 段）/ EXIT = 0**
- 场景：多轮构建闭环(26) / 生成批准(22) / 中途拒绝韧性(13) / 纯模拟(13) / 混合策略(6) / 上下文压缩(5) / 重试耗尽韧性(11) / 事件广播不变量(6)。

## 22. Gate 7 — `PAIOS_MODEL=heuristic node main.js`（未接入）

- 本回合未在 `main.js` 增加 `[文档层演示]` 段，故无文档层专属实时演示。既有 `main.js` 仍可正常 EXIT 0（与 Phase 28.2 验收无冲突）。
- 若后续需要，可参照 Phase 28.1 的 `[视觉层演示]` 段新增 `[文档层演示]`。

---

## 23. 关键修正记录（本回合）

**Gate 1 源码修正（5 处真实 bug）：**
1. `document-model.js`：`documentModelFingerprint` 改用 `pipelineFingerprint`（fnv1a+stableStringify，确定性）替代非确定性 `nextPipelineId`；`createDocumentModel` 非法 `type` 改为抛 `DocumentValidationError`（不再默认 `"report"` 静默吞掉）。
2. `document-artifact.js`：二进制格式字节泄漏拦截移至归一化**之前**（原检查在 `content` 已被置空后运行，永不触发）。
3. `document-source.js`：`guardSource` 增加原始输入语义黑名单扫描（`assertNoDocumentInjection` + `findSourceBannedFieldsDeep`）。
4. `document-converter.js`：`dataRowsToModel` 改用 `createTable` 补齐 `rowCount`（原手建 table 缺 `rowCount` 致 `tables[0].rowCount` 为 undefined）。
5. `document-provider.js`：`DeterministicDocumentProvider.build` 不再把 `query.kind` 当 `model.type`，按 `DOCUMENT_MODEL_TYPES` 校验/默认 `"report"`（此修正同时消除了一个原会令整套 Gate 1 崩溃的 `DocumentValidationError`）。

**Gate 1 测试对齐（5 处）：**
6. `DOCUMENT_MODEL_FIELD_COUNT` 22 → 23。
7. `m.blockCount` / `extractBlocks(m).length` 4 → 3（模型实际 3 个块）。
8. `createDocumentArtifact` 补 `sizeHint`（默认 0 → 2048，与 fuzz 路径一致）。
9. 注入拦截断言改抛 `DocumentInjectionError`（语义键 `executionSandbox` 走 `assertNoDocumentInjection`，非 `DocumentPurityError`）。
10. 上下文循环用真实 artifacts 构造 `createOkResult`（让 `pendingArtifactCount` 累计到 64）。

**收口修正（本会话）：**
11. `package.json`：接入 `test:all`（40→41 套）、新增 `gate1:document`/`check:document:execution`/`smoke:document`/`gate6:document:e2e`/`test:phase28_2`、description 增 Phase 28.2 条款 + EventBus 396→404。
12. `check-consistency --fix` 同步 44 派生点（396→404、套数 40→41、末端 phase28_2）。
13. 补同步 `--fix` 未覆盖的非标准 396 断言（phase25_ui / phase28_1 / phase27 + 三套扫描器 `EXPECTED_EVENT_BUS_TOTAL`），详见第 13 节。

---

## 24. 数值不变量一览

| 不变量 | 值 |
| --- | --- |
| DocumentModel 字段数（DOCUMENT_MODEL_FIELD_COUNT） | 23 |
| 文档类型（DOCUMENT_MODEL_TYPES） | 8 |
| 二进制格式（pdf/docx/pptx/xlsx） | 4 |
| 富模型 | Model / Artifact / Result / Query / Source / Context |
| Provider 实现 | 3（Static / Mock / Deterministic） |
| 状态机态 / 迁移 | 11 / 28 |
| Agent 终态 | 6 |
| Document 事件 / EventBus 总数 | 8 / 404 |
| Fuzz 规模 | models 3000 / render 22000 / policy 2000 / agent 1050 |
| Gate 1 断言 / 段 | 29200 / 21 |

---

## 25. 与 Vision / Computer 层范式一致性

Document 层完全复用 Computer（Phase 27.4）/ Vision（Phase 28.1）范式：
- Provider 基类 + `Static`/`Mock`/`Deterministic` 变体 + `conformsTo*` 鸭子类型校验；
- Agent 三硬闸 + 唯一执行交接点 `_requestExecution → orchestrator.submitExecutionRequest(req)`（无 orchestrator 则纯模拟 `executed:false`）；
- `createDemoOrchestrator` 桩；
- 纯数据铁律、`hasExecutionAuthority()===false` 实例方法 + 模块级函数；
- 状态机（11/28）与事件枚举（8 个 Document*）登记至 EventBus。

---

## 26. 测试策略

- **独立预言机**：策略矩阵用 `predictViolationCodes()` 对多策略 × 多类型 × 多来源穷举，与 `evaluateDocumentQuery` 输出逐字段比对。
- **零执行权穷举**：对所有类实例与模块级函数断言 `hasExecutionAuthority()===false`，并验证拒绝方法抛错。
- **可复现性**：离线 Provider 同查询同结果；`verifyDocumentZeroAuthority()` 自证。
- **双次复现**：Gate 1 在 `test:all` 链路末端被再次执行，结果完全一致（29200/0）。

---

## 27. 性能

- Gate 1 长测 29200 断言 < 185ms；
- Gate 5 冒烟 76 项 < 实时；
- Gate 6 e2e 102 断言 < 20ms；
- Gate 2 扫描 < 实时；
- 全部离线、零 I/O、零网络，可一键复现。

---

## 28. 安全性

- 文档层无任何执行入口；真实动作必须经 `Orchestrator → ExecutionSandbox`。
- 347 项管线黑名单 + 文档层专用黑名单 + Agent 黑名单三重拦截。
- 交付请求强制 `requireApproval=true`，且自身 `executionAuthority=false`。
- `DocumentAgent` 构造期校验注入、`orchestrator` 合法性、Provider 鸭子类型。

---

## 29. 可维护性

- 每个模块单一职责，纯函数 + class 双形态（工厂返回 plain object 带 `executionAuthority:false` 字段，方法只存在于实例）。
- `index.js` 统一导出 + `verifyDocumentZeroAuthority()` 自证，未来层可复用同一范式。
- 错误族统一（`{name, code, message, context}`）。

---

## 30. 已知边界 / 后续

- 离线 Provider 的 `seed` 不影响输出（实现恒为可复现常量）；如需「异 seed 异结果」语义，应在 Provider 内接入 `mulberry32` 但当前未暴露。本回合以「可复现性」为断言靶。
- `DOCUMENT_EVENT_COUNT` / `DOCUMENT_STATE_COUNT` 等常量已由 `index.js` 重导出，供扫描器与测试复用。
- Phase 28.3+（真实模型接入、富渲染管线、Office 二进制生成等）**未启动**，符合最高优先级约束。

---

## 31. 验收签名

| Gate | 命令 | 结果 |
| --- | --- | --- |
| Gate 1 | `node phase28_2_document_test.js` | PASS 29200 / 0 · EXIT0 |
| Gate 2 | `node scripts/scan-document-execution.js` | Token/Dep/Violation=0 · EXIT0 |
| Gate 3 | `node scripts/check-consistency.js --fix` | EXIT0 |
| Gate 4 | `npm run test:all` | EXIT0 / FAIL0（41 套） |
| Gate 5 | `npm run smoke:document` | 76/0 · EXIT0 |
| Gate 6 | `npm run gate6:document:e2e` | 102/0 · EXIT0 |
| Gate 7 | `PAIOS_MODEL=heuristic node main.js` | 未接入文档演示段（既有 main 仍可 EXIT0） |

---

## 32. 结论

**Phase 28.2 Document & Office Capability 验收通过。** 文档层以纯数据、零执行权、离线确定性方式落地，严格复用 Computer / Vision 层范式，真实执行权继续唯一归属 `ExecutionSandbox`；6 道自动化 Gate 全绿，`test:all` 全量回归 41 套 0 FAIL，EventBus 396→404，外部依赖为 0。

**严格停在 `Phase 28.2 COMPLETE`。**
