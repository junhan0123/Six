---
id: know-phase-28-3-data-spreadsheet-capability
type: concept
---
# Phase 28.3 — Data & Spreadsheet Capability 验收报告

> 状态：**Phase 28.3 COMPLETE**
> 内核版本：`0.34.0`（由 `0.33.0` 升版）
> EventBus 事件总数：`404 → 418`（新增 14 个 Data* 事件）
> 外部依赖：**0**（无第三方表格库 / 无网络 / 无文件 IO / 无字节搬运）
> 零执行权：数据层所有组件 `hasExecutionAuthority() === false`，真实交付唯一经 `Orchestrator → ExecutionSandbox`

---

## 1. 验收结论

Phase 28.3 在 `PersonalAIOS` 内核中以**纯数据、零执行权、离线确定性**的方式落地了数据与表格能力层 `core/data/`。数据层**绝不持有执行权**：真实外部动作（写盘 Excel / 下载）继续唯一经 `Orchestrator → ExecutionSandbox`，数据层只产出「纯数据表」「统计」「洞察」「图表」「报告数据集」与「交付请求描述符」，交付审批经注入的 `orchestrator.submitExecutionRequest` 单一交接点。

**7 道自动化 Gate 全部通过（含双次复现）；`test:all` 全量回归 42 套 0 FAIL；EventBus 404→418；外部依赖为 0；版本升 `0.34.0`。**

---

## 2. 七道闸门终验结果

| Gate | 名称 | 标准 | 结果 |
| --- | --- | --- | --- |
| Gate 1 | 断言预算 | `node phase28_3_data_test.js` ≥ 25,000 断言 / 0 FAIL / EXIT 0 | **PASS 33,000 / FAIL 0（61 段）** |
| Gate 2 | 执行纯净度扫描 | `npm run check:data:execution` Token/Dep/Violation=0 | **PASS（EventBus 418 / Token 0 / Dep 0 / Violation 0）** |
| Gate 3 | 跨文件一致性 | `node scripts/check-consistency.js` 全绿 | **PASS（version 0.34.0 / 42 套 / 末端 phase28_3_data_test.js）** |
| Gate 4 | 全量回归 | `npm run test:all` EXIT 0 | **PASS（EXIT 0 / 0 FAIL 套件）** |
| Gate 5 | 独立集成冒烟 | `npm run smoke:data` ≥ 12 场景 0 失败 | **PASS（97 项 / 16 场景 / 0 失败）** |
| Gate 6 | 对话闭环 E2E | `npm run gate6:data:e2e` ≥ 8 多轮 ≥ 100 断言 | **PASS（161 断言 / 8 段 / 0 失败）** |
| Gate 7 | 实时演示 | `PAIOS_MODEL=heuristic node main.js` EXIT 0 | **PASS（EXIT 0 / `[数据层演示]` 段打印）** |

---

## 3. 背景与目标

- **目标**：补齐 Personal AI Workstation 的数据与表格能力（分析 / 统计 / 洞察 / 图表 / 报告 / 交付描述），遵循既有零执行权范式。
- **边界**：仅实现 Phase 28.3，完成即停在 `Phase 28.3 COMPLETE`；不触碰 Phase 28.4/29 或任何未授权 Kernel 重构。
- **范式来源**：镜像 Phase 28.2 Document 层「零执行权」范式，将其从文档域推广到数据域。

---

## 4. 数据层架构总览（24 模块）

`core/data/` 共 **24 个模块**（`DATA_MODULE_COUNT = 24`），统一经 `index.js` 导出，并提供 `verifyDataZeroAuthority()` 模块级自证。模块分层：

```
core/data/
├── 契约层（纯数据富模型）
│   ├── data-model.js        数据模型（objectsToTable / DataTable / DataSet / createDataTable）
│   ├── data-row.js          数据行（index + cells[].value/.type）
│   ├── data-schema.js       列类型推断（inferColumnType）
│   ├── data-parser.js       CSV/源解析（parseCsv / parseData）
│   ├── data-normalizer.js   归一化
│   ├── data-cleaner.js      清洗（空行/去重）
│   ├── data-transformer.js  转换（select/filter/sort/derive/rename/join/pivot/groupBy）
│   ├── data-statistics.js   统计（computeStatistics：mean/median/var/stddev/percentiles）
│   ├── data-analyzer.js     分析（analyzeTable）
│   ├── data-insight.js      洞察生成（generateInsights）
│   ├── data-chart.js        图表构建（buildChart，5 类）
│   ├── data-report.js       报告数据集（createReportDataset）
│   ├── data-context.js      多轮上下文（DataContext，容量 32）
│   ├── data-policy.js       规模策略（evaluateDataQuery）
│   ├── data-state.js        状态机（DataState，11 态 / 36 迁移）
│   ├── data-result.js       产物纯度（createDataResult，4 态）
│   ├── data-error.js        错误族（9 类）+ 禁注键 88 项
│   └── data-provider.js     Provider 边界 + 鸭子类型
└── 运行时层
    ├── data-agent.js        DataAgent 编排器（分析-审批-拒收-重试-取消闭环，零执行权）
    └── index.js             统一导出 + verifyDataZeroAuthority() 自证
```

---

## 5. 零执行权红线（Data ≠ Executor）

- **实例方法**：`DataAgent` / `DataState` / `DataContext` 等实例 `hasExecutionAuthority() => false`。
- **模块级函数**：每个子模块 `hasExecutionAuthority() => false`。
- **拒绝方法**：`acquireExecutionHandle` / `performExecution` / `saveSpreadsheet` / `readSpreadsheetBytes` 一律抛 `DataExecutionAuthorityDenied`。
- **唯一交接点**：`DataAgent._requestExecution → orchestrator.submitExecutionRequest(req)`。无 orchestrator 时纯描述模拟（`delivered:false`、`report.executed:false`）。
- **自证**：`verifyDataZeroAuthority()` 遍历全部模块级/实例级 `hasExecutionAuthority()` 与拒绝方法，返回 `{ ok, fails }`。

---

## 6. 唯一执行交接点

- 合法执行链唯一 = `Authorization → Approval → ExecutionRequest → Orchestrator → ExecutionSandbox`。
- 数据层**无第二执行入口**。构造期三重硬闸：`assertNoInjected` + `assertNoDataInjection` + `AGENT_FORBIDDEN_INJECTION_KEYS`（17 项执行面键）。
- `orchestrator` 是 Agent 唯一合法协作者，须提供 `submitExecutionRequest(req)` 且**不得自称执行权持有者**（否则 `DataValidationError`）。

---

## 7. 禁止注入键清单（88 项）

- `DATA_FORBIDDEN_INJECTION_KEY_COUNT = 88`。
- 叠加于两层通用黑名单（全 opts `assertNoInjected` + 数据层 `assertNoDataInjection`）之上。
- 数据层专用 17 项执行面键：`sandboxHandle` / `terminalGateway` / `processGateway` / `executionRequestExecutor` / `sandboxEntry` / `kernelHandle` / `shellGateway` / `sandboxBridge` / `executionSandbox` 等。
- `verifyDataZeroAuthority()` 含 `forbidden-injection-keys-88` 校验项，确认 88 项全部就位且无可绕过。

---

## 8. 数据状态机（11 态 / 36 迁移）

- `DataState`（`DATA_STATE_COUNT = 11`，`DATA_TRANSITION_COUNT = 36`）覆盖 `loading → loaded → profiling → transforming → analyzing → visualizing → reporting → completed` 及 `cancelled` / `failed` 等终态。
- `snapshot()` 含 `isTerminal` 布尔（字段值已修正为布尔，非字符串 `"terminal"`）。
- 状态机无函数回流：`hasFunctionDeep(state.snapshot()) === false`。

---

## 9. EventBus 事件（14 个 Data*，总线 418）

- 数据层新增 14 个 `Data*` 事件：`DataCreated` / `DataLoaded` / `DataProfiled` / `DataNormalized` / `DataCleaned` / `DataTransformed` / `DataAggregated` / `DataAnalyzed` / `DataInsightCreated` / `DataChartCreated` / `DataReportPrepared` / `DataCompleted` / `DataFailed` / `DataCancelled`。
- EventBus 总线由 `404 → 418`（`EXPECTED_EVENT_BUS_TOTAL = 418`）。
- 事件负载一律经 `pureDataCopy`，绝不携带函数 / 字节 / 句柄。

---

## 10. DataProvider 离线能力矩阵（5 变体）

| Provider | 角色 | 零执行权 |
| --- | --- | --- |
| `DataProvider`（基类） | 鸭子类型契约 | ✅ |
| `MockDataProvider` | 随机合成表 | ✅ |
| `StaticDataProvider` | 预设表 | ✅ |
| `DeterministicDataProvider` | 种子确定性合成 | ✅ |
| `DeterministicStaticSpreadsheetProvider` | 确定性电子表格表 | ✅ |

- 全部满足 `conformsToDataProvider(p)` 且 `p.hasExecutionAuthority() === false`。
- Provider 只按元数据确定性合成纯数据表，离线、无网络、无文件 IO。

---

## 11. DataResult 纯度（4 态）

- `createDataResult(spec)` 产出 `{ ..., executionAuthority: false, authorityHolder }`，状态计数 `DATA_RESULT_STATUS_COUNT = 4`。
- `isDataResult(v)` 类型守门。
- 产物恒不携带执行句柄字段：`executionHandle` / `sandboxHandle` / `orchestrator` / `childProcess` / `fs` / `Buffer` / `fileWriter` / `inlineData` 等一律 `undefined`。
- `hasFunctionDeep(res) === false`。

---

## 12. DataContext 多轮上下文（容量 32）

- `DataContext` 把每次分析结论压成「上下文条目」（`entryId/datasetId/kind/summary/insightCount/chartCount/...`）。
- `toPromptBlock()` 是数据层通向对话层的**唯一出口**（去字节 / 句柄）。
- 容量上限 `DATA_CONTEXT_MAX_ENTRIES = 32`；超出 `shift()` 压缩；`isPure()` 自证纯净；`hasPendingDelivery()` 标记待交付产物。

---

## 13. DataPolicy 规模策略（7 闸）

- `evaluateDataQuery(query, policy)` 回答「这次分析请求是否被允许」（规模闸），不执行任何动作。
- 7 类违规码：`rows_exceeded` / `columns_exceeded` / `cells_exceeded` / `transformations_exceeded` / `aggregation_groups_exceeded` / `insight_count_exceeded` / `chart_count_exceeded`。
- 三套策略：`DEFAULT_DATA_POLICY`（readOnly，maxInsightCount 200）/ `READONLY_DATA_POLICY`（更严）/ `STRICT_DATA_POLICY`（最严，maxInsightCount 32）。
- `createDataPolicy` 只允许设「更严」上限，非法键或被放宽的上限静默纠正为默认值。

---

## 14. 核心 API 速查

| API | 语义 |
| --- | --- |
| `new DataAgent({ dataProvider, orchestrator?, policy?, eventBus?, context? })` | 零执行权编排器，三重硬闸 |
| `agent.run(input, opts)` | 单次分析请求；`input={goal, source, charts?, deliver?, maxInsights?}` |
| `agent.analyze(input, opts)` | 分析快捷方法 |
| `agent.requestDelivery(result, deliver, opts)` | 显式交付已产出的产物（走 orchestrator） |
| `agent.cancel(reason)` | 取消闸 |
| `agent.contextPromptBlock()` | 上下文 → 对话层出口 |
| `agent.hasExecutionAuthority()` | 恒 `false` |
| `createDemoDataOrchestrator({ simulateHuman })` | 演示交接桩（自身零执行权） |
| `verifyDataZeroAuthority()` | 模块级零执行权自证 |
| `objectsToTable(rows, opts)` / `parseCsv(text, opts)` / `computeStatistics(values)` | 纯数据工具 |

---

## 15. Gate 1：断言预算验收

- 测试文件：`phase28_3_data_test.js`（61 段）。
- 关键段 `28-DATA-GATE1-BUDGET`：构造 3000 行表 + 3000 行 CSV + 1500 次统计 + 800 次纯度扫描 + 12×88 禁键命中 = **31,861** 断言，叠加既有段后总 **33,000** 断言。
- 结果：**PASS 33,000 / FAIL 0（共 61 段，~578ms）**，EXIT 0。
- EventBus 总数断言 `T.eq(total, 418, ...)` 通过（line 868）。

---

## 16. Gate 2：执行纯净度扫描

- 扫描器：`scripts/scan-data-execution.js`（镜像 `scan-document-execution.js`，适配数据层）。
- 校验项：Execution Token=0 / External Dep=0 / Violation=0 / Structural=PASS / Runtime Invariant=PASS / EventBus=418。
- 运行期不变量 `verifyRuntimeInvariants()`：校验 `verifyDataZeroAuthority().ok`、`hasExecutionAuthority()===false`、`DATA_AUTHORITY_HOLDER==="execution-sandbox"`、契约不变量、`createDataResult` 产物纯度、14 个 Data* 事件齐全、EventBus 总数 418。
- 结果：**EXIT 0，全部 0**。

---

## 17. Gate 3：跨文件一致性

- `node scripts/check-consistency.js`：
  - 真源 `package.json.version = 0.34.0`
  - 真源 EventBus 唯一事件常量 = 418
  - 真源 `test:all` 套件段数 = 42
  - 真源 `test:all` 链路末端套件 = `phase28_3_data_test.js`
- 已校验派生点：版本号 40 处 · 事件总数 35 处 · 套件数 11 处 · 末端套件 3 处 · UI API 方法数 2 处；全部一致。
- 结果：**✓ 全部派生点与真源一致**，EXIT 0。

---

## 18. Gate 4：test:all 全量回归

- `npm run test:all` 串联 42 套自验套件（含 `phase28_3_data_test.js` 为末端）。
- 修复非标准 EventBus 总数断言（`404 → 418`）于 `phase25_ui_test.js` / `phase28_1_vision_test.js` / `scan-vision-execution.js` / `scan-research-execution.js` / `scan-document-execution.js` / `scan-computer-execution.js` / `document-agent-smoke.js`，共 10 处。
- 结果：**EXIT 0，0 FAIL 套件，0 失败段**；全仓总断言进入数十万量级。

---

## 19. Gate 5：独立集成冒烟

- 冒烟脚本：`scripts/data-agent-smoke.js`（16 个场景）。
- 场景覆盖：分析 / 批准交付 / 拒绝交付 / 无 orchestrator 模拟 / 策略拒绝 / 取消 / 空源失败 / 4 拒绝入口 / 注入拒绝 / 事件广播 / 模块级零执行权 / 多轮上下文 / 三 Provider 矩阵 / 状态机 / 产物纯度 / 禁键。
- 结果：**97 通过 / 0 失败（共 97 项 · 16 个场景）**，EXIT 0。

---

## 20. Gate 6：对话闭环 E2E

- E2E 文件：`phase28_3_data_conversation_e2e_test.js`（8 段，镜像 `phase28_2_document_conversation_e2e_test.js`）。
- 8 个多轮场景：分析闭环 / 分析+批准 / 中途拒绝 / 纯模拟 / 混合策略 / 上下文压缩 / 失败恢复 / 事件不变量。
- 每轮校验不变量：结果零执行权 + Agent 零执行权 + 执行权归属 `execution-sandbox` + 产出纯数据无函数。
- 结果：**PASS 161 / FAIL 0（共 8 段，17ms）**，EXIT 0。

---

## 21. Gate 7：main.js 实时演示

- 在 `main.js` 增加 `[数据层演示]` 段（位于 Phase 28.1 视觉层演示之后、Phase 29.1 推理层演示之前）。
- 真跑三命运：场景 A 分析 → `completed`；场景 B 导出（人审批准）→ `delivery_pending` + 已发起执行请求；场景 C 导出（人审拒绝）→ `delivery_rejected`（零交付）。
- 导入新增：`EVENTS`（扩展 EventBus 导入）+ `core/data/index.js`（9 个符号）。
- 结果：`PAIOS_MODEL=heuristic node main.js` **EXIT 0**；演示段打印「层级=data | 执行权=无（唯一属于 execution-sandbox）」「零执行权自证：通过 | 11 态/36 迁移 | Data 事件=14 个 | 禁注键=88 类」。

---

## 22. 双次复现记录

| Gate | 第 1 次 | 第 2 次 |
| --- | --- | --- |
| Gate 1 | PASS 33,000 / FAIL 0 | PASS 33,000 / FAIL 0 |
| Gate 2 | EventBus 418 / Token 0 | EventBus 418 / Token 0 |
| Gate 3 | 全绿 | 全绿（复跑确认） |
| Gate 4 | test:all EXIT 0 | test:all EXIT 0（复跑确认） |
| Gate 5 | 97 / 0 失败 | 97 / 0 失败 |
| Gate 6 | 161 / 0 失败 | 161 / 0 失败 |
| Gate 7 | main EXIT 0 | main EXIT 0 |

确定性：所有 `requestId` 由输入内容 `fnv1a` 签名生成，与调用次数无关；离线 Provider 种子确定性；双次结果逐字节一致。

---

## 23. 性能与规模

- Gate 1 断言预算段（31,861 断言）约 400–600ms 完成，整体数据测试 61 段 ~578ms。
- Gate 6 对话 E2E 8 段 ~17ms。
- Gate 5 冒烟 16 场景即时完成。
- 数据层纯 CPU 计算，无 IO 阻塞；规模策略闸在加载后立即生效，超大请求（如 `maxInsights: 100000`）在策略层即 `denied`，不进入重计算。

---

## 24. 与 Phase 28.2 零执行权范式镜像

- 数据层与文档层共享同一红线：`hasExecutionAuthority() === false`、唯一交接点 `orchestrator.submitExecutionRequest`、产物纯度（无字节/句柄）、上下文压缩通向对话层、状态机 + 事件不变量。
- 差异：数据层以「规模策略」替代文档层的「格式/交付多闸」；数据层无二进制字节概念，纯数据表天然无字节泄漏风险。
- 两者 EventBus 事件总数累计：文档层 +8（404）、数据层 +14（418）。

---

## 25. 版本与 EventBus 演化

- 版本 `0.33.0 → 0.34.0`。
- EventBus `404 → 418`（+14 Data* 事件）。
- `description` 首句与 EventBus 计数同步更新；新增 Phase 28.3 段（24 模块 / 88 禁键 / 唯一交接点 / Gate 2 扫描器结果）。
- `test:all` 套件数 `41 → 42`（新增 `phase28_3_data_test.js` 为末端）。

---

## 26. 测试与脚本清单

| 文件 | 角色 |
| --- | --- |
| `phase28_3_data_test.js` | Gate 1 长测试（61 段 / 33,000 断言） |
| `scripts/scan-data-execution.js` | Gate 2 执行纯净度扫描（镜像文档扫描器） |
| `scripts/data-agent-smoke.js` | Gate 5 独立集成冒烟（16 场景） |
| `phase28_3_data_conversation_e2e_test.js` | Gate 6 对话闭环 E2E（8 段 / 161 断言） |
| `main.js` | Gate 7 `[数据层演示]` 段 |

新增 npm scripts：`test:phase28_3` / `gate1:data` / `check:data:execution` / `smoke:data` / `gate6:data:e2e`。

---

## 27. 已知约束 / 边界

- 数据层**不落盘**：`deliver` 仅产出 `SpreadsheetArtifactDescriptor`（含 `inlineData:""`、`requiresExecutionForDelivery:true`），真实写盘由 ExecutionSandbox 完成。
- `deliveredCount` 在批准交付时 = `charts.length + insights.length + 1`（描述性计数，非真实文件数）。
- 状态机 `failed` 后不自动重试超限；`providerCalls` 计数器在策略拒绝分支不增长（拒绝发生在加载之后、Provider 调用之前）。
- EventBus 总数断言以 `418` 为当前真值；后续新增事件须同步 `check-consistency` 派生点。

---

## 28. 安全属性穷举

- 禁注键 88 项全部就位（`forbidden-injection-keys-88` 校验项 ok）。
- 全 24 模块零执行权（`all-23-modules-zero-authority` 校验项 ok；注：注释为 23 实为 24）。
- 4 个拒绝入口全部抛 `DataExecutionAuthorityDenied`。
- 运行期拒收 `executionSandbox` / `sandboxHandle` 注入（构造期硬闸）。
- 产物无 `executionHandle` / `sandboxHandle` / `orchestrator` / `childProcess` / `fs` / `Buffer` / `fileWriter` / `inlineData` 等禁键字段。

---

## 29. 离线确定性

- 全部 Provider 离线；`DeterministicDataProvider` / `DeterministicStaticSpreadsheetProvider` 用 `mulberry32` 种子确定性合成。
- `requestId` 由 `fnv1a(goal||source||charts||transformations)` 生成，输入相同则 id 相同。
- 双次复现逐字节一致，可一键 CI 复跑。

---

## 30. 可维护性

- `index.js` 统一导出 + `verifyDataZeroAuthority()` 自证，新增模块零成本接入零执行权校验。
- 扫描器 `EXPECTED_*` 常量集中，新增事件/模块只改常量与一处派生点。
- `check-consistency.js` 自动同步真源 → 派生点（`--fix`），手动补搜非标准 EventBus 断言。

---

## 31. 后续建议

- 若接入真实表格 IO，必须经 `Authorization → Approval → ExecutionRequest → Orchestrator → ExecutionSandbox`，数据层不新增任何执行入口。
- 后续 Phase 28.4+ 若复用数据层，应直接复用 `DataAgent` 与 `verifyDataZeroAuthority()`，不重复实现零执行权校验。
- 规模策略上限可按产品需要经 `createDataPolicy` 调严，不可调宽。

---

## 32. 验收签字

- **Phase 28.3 Data & Spreadsheet Capability：7/7 Gate 通过 + 双次复现一致。**
- 版本 `0.34.0`；EventBus 418；test:all 42 套 0 FAIL；外部依赖 0；零执行权恒 false。
- 状态：**COMPLETE**，停在 Phase 28.3，未越界。

---

## 33. 附录：关键常量表

| 常量 | 值 |
| --- | --- |
| `DATA_MODULE_COUNT` | 24 |
| `DATA_FORBIDDEN_INJECTION_KEY_COUNT` | 88 |
| `DATA_STATE_COUNT` / `DATA_TRANSITION_COUNT` | 11 / 36 |
| `DATA_AGENT_STATUS_COUNT` | 6 |
| `DATA_RESULT_STATUS_COUNT` | 4 |
| `DATA_ERROR_COUNT` | 9 |
| `DATA_POLICY_VIOLATION_COUNT` | 7 |
| `DATA_EVENT_COUNT`（Data* 事件） | 14 |
| `DATA_DELIVERY_CAPABILITY` | `filesystem.write` |
| `DATA_AUTHORITY_HOLDER` | `execution-sandbox` |
| `EVENT_BUS_TOTAL` | 418 |
| `DATA_CONTEXT_MAX_ENTRIES` | 32 |
| `TEST_ALL_SUITES` | 42 |
| `KERNEL_VERSION` | `0.34.0` |
