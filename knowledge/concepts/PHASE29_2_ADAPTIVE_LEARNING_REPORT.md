---
id: know-phase-29-2-adaptive-reasoning-learning
type: concept
---
# Phase 29.2 自适应推理与学习层（Adaptive Reasoning & Learning）验收报告

> 实施者：Senior Developer（高级开发工程师，全栈 / Laravel-Livewire-FluxUI / 高级 CSS / Three.js / 性能优化方向）
> 承接：Phase 29.1「通用多轮推理层 Reasoning」已验收
> 性质：**学习 / 自适应层**，绝不重造 Phase 29.1 推理引擎
> 报告日期：2026-08-12
> 结论：**PHASE_29_2_COMPLETE**（七道闸门全部通过，双次复现；STOP_AT_PHASE_29_2）

---

## 1. 任务边界与核心定义

Phase 29.2 让「通用多轮推理层（Phase 29.1）」能够安全地从自己的历史推理周期里学习：成功 / 失败 / 循环 / 预算超限 / 用户修正 / 策略效果 / 能力-结果关联模式，并经既有 Memory / Learning Engine 形成「推理经验 → 学习记录 → 策略调整建议 → 后续推理使用」闭环。

本层是 **Learning ≠ Executor** 原则的具象化：学习层只分析 / 归纳 / 统计 / 生成纯数据 Pattern / Recommendation / Context，自身**零执行权、绝不执行**；唯一真实执行链仍是 Orchestrator → ExecutionSandbox。

## 2. 不变量（最高优先级）

- 不重造 Phase 29.1 推理引擎；只在其产物（ReasoningResult / ReasoningCycle）之上叠加学习与自适应。
- 唯一真实执行链：`Orchestrator → ExecutionSandbox`；学习层 `hasExecutionAuthority() === false` 恒成立。
- 禁止 `new ComputerAgent()` / `new ResearchAgent()` 等执行入口；禁止 `executionHandle` / `child_process` / `spawn` / `exec`。
- 学习只产出纯数据建议，绝不 `apply` 到真实配置或世界状态。
- 原始历史**永不删除**；衰减只降权，不删。

## 3. 架构兼容性结论（前序 Task #410 已交付）

实施前已完成 Architecture Compatibility Report，确认：
- 学习层可复用 Phase 29.1 的 `core/reasoning/result.js`（`createReasoningResult` / `isReasoningResult` / `REASONING_RESULT_STATUSES` 七枚举）与 `core/reasoning/cycle.js`（`isReasoningCycle`）。
- 学习层可复用既有 `LearningEngine` / `PatternExtractor` / `MemoryManager`（episodic / semantic / preference / learning 四分区）。
- 新增类 `hasExecutionAuthority()` 全部返回 `false`，`authorityHolder` 恒为 `execution-sandbox`。

## 4. 零执行权红线遵守（红线 1–6）

- **红线 1**：学习层不持有任何执行句柄；`AdaptiveReasoningLearning` 门面无 `acquireExecutionHandle` / `performExecution` / `apply` / `rollback` / `submitExecutionRequest` 等禁止方法。
- **红线 2**：构造期 `assertNoReasoningLearningInjected` 拒收 `executionHandle` / `executionSandbox` / `orchestrator` / `applicationAdapter` / `terminal` / `process` / `child_process` 等注入键。
- **红线 3**：`learnFromOutcome` 只调用 `extractor / patternExtractor / scorer / recommender / confidence / decay / contradiction / contextInjector / memoryBridge`（全部零执行权纯分析组件）。
- **红线 4**：`recommender.recommend` 与 `contextInjector.inject` 产出对象带 `isAdvisory: true` / `executionAuthority: false` / `authorityHolder: "execution-sandbox"`。
- **红线 5**：`memoryBridge.store` 在无 `memoryManager` 时返回 `{ stored: false, entries: 0, reason: "no-memory-manager" }`，不写盘、不执行。
- **红线 6**：外部依赖 0；不引入任何第三方测试框架（沿用自研 `core/test/Harness.js`）。

## 5. 九大核心能力映射

| # | 能力 | 实现模块 | 是否纯 advisory |
|---|------|----------|------------------|
| ① | ReasoningOutcomeExtractor | `outcome-extractor.js` | 是（只读抽取） |
| ② | PatternExtractor（推理专属） | `pattern-extractor.js` | 是（纯统计） |
| ③ | StrategyScorer | `strategy-scorer.js` | 是（打分） |
| ④ | ReasoningStrategyRecommender | `recommender.js` | 是（**advisory only**） |
| ⑤ | Reasoning Context Injection | `context-injector.js` | 是（**纯 advisory**） |
| ⑥ | Learning Confidence | `confidence.js` | 是（分级） |
| ⑦ | Learning Decay | `decay.js` | 是（只降权不删） |
| ⑧ | Contradictory Learning | `contradiction.js` | 是（降级矛盾证据） |
| ⑨ | Memory Partition | `memory-bridge.js` | 是（复用四分区） |

## 6. 能力① 推理结果抽取器

`extractReasoningFeatures(result)` 把 `ReasoningResult` 翻译为富特征（goalId / status / outcome / rounds / capabilitiesUsed / decisionKinds / correctionStrategies / capabilityResultMap / loopDetected / budgetExceeded / userCorrection / correctionsUsed / replansUsed 等）。`toObservationSample(result, features)` 将特征编译为既有 `LearningEngine.observe()` 接受的样本（kind=`reasoning_result`、tags 含 `loop`/`budget`/`human`/`decision:*`/`strategy:*`）。拒绝含函数的结果（疑似执行句柄）。

## 7. 能力② 推理专属模式抽取器

`ReasoningPatternExtractor.extract(featuresList)` 按 `goalId` 分组，抽取 8 类推理专属模式：`reasoning_loop` / `budget_overrun` / `user_correction` / `success_pattern` / `correction_storm` / `progress_stall` / `strategy_effectiveness` / `capability_correlation`。`ReasoningPattern` 实例 `toJSON()` 含 `executionAuthority: false`，且**实例无 `executionAuthority` 属性**（仅序列化时出现），以满足零执行权深度校验。模式按 `strength()` 降序输出。

## 8. 能力③ 策略打分器

`scoreStrategies(history)` 返回 `{ strategies, decisionKinds, preferredStrategy, preferredPolicyMode, sampleCount }`。`_inferPolicyMode`：若历史含 `loops>0` → `single_round`；若含 `corr>0`（用户修正）→ `multi_round`；否则 `balanced`。纯统计，不执行。

## 9. 能力④ 策略推荐器（advisory only）

`recommend(goalContext, learned)` 遍历模式产出 `suggestedPolicyMode` / `suggestedCorrectionStrategy` / `avoidCapabilities` / `preferCapabilities` / `notes` / `sourcePatternIds`，并带 `isAdvisory: true` / `executionAuthority: false`。调用方自行决定是否、如何采纳；本模块**永不主动执行**。

## 10. 能力⑤ 上下文注入器（纯 advisory）

`inject(goalContext, learned)` 产出可注入未来 ReasoningLoop 的纯数据上下文（`recommendedPolicyMode` / `recommendedCorrectionStrategy` / `learningNotes` / `confidenceLevel` / `consumedBy: "reasoning-loop-context-only"`）。它**绝不**调用任何执行器，也**绝不**替 ReasoningLoop 做决策。

## 11. 能力⑥ 学习置信度分级

`classify(n, consistency)`：`n<3 → insufficient`；`n<6 或 c<0.6 → emerging`；`n<12 或 c<0.85 → supported`；否则 `strong`。**严禁「1 次成功即最佳」**——单样本恒定 `insufficient`（已通过 `verifyReasoningLearningZeroAuthority` Item 8 硬校验）。

## 12. 能力⑦ 学习衰减

`decayFactor(now, at)` / `effectiveConfidence(p, now)` / `applyToPatterns(patterns, now)`。衰减只降低模式 `confidence`，**不改原模式、不删原始历史**；`decayFloor=0.05` 为衰减下限。

## 13. 能力⑧ 矛盾学习

`detect(patterns)`：正反比例相当（diff < `contradictionTolerance=0.25`）→ `mixed`；悬殊 → `uncertain`；并对矛盾证据施加 `confidencePenalty=0.5` 降权。避免矛盾模式被过度信任。

## 14. 能力⑨ 记忆分区桥

`memoryBridge.store(result, patterns, scores, conf)` 复用既有 `MemoryManager` 的 episodic / semantic / preference / learning 四分区。无 `memoryManager` 时禁用路径返回 `{ stored: false, entries: 0, reason: "no-memory-manager" }`（**entries 为 0 而非数组**），不写盘。

## 15. 引擎门面串联九能力

`AdaptiveReasoningLearning.learnFromOutcome(result, opts)` 流程：校验 `isReasoningResult` → 抽取特征 → 转样本并 `learningEngine.observe` → 推送 `_history`/`_samples` → 推理专属模式 → 通用模式（复用既有 `PatternExtractor`）→ 策略打分 → 置信度 → 矛盾检测 → 衰减（只降权不删）→ 推荐（纯建议）→ 上下文注入（纯 advisory）→ 记忆桥落盘（不执行）→ 返回冻结的 `LearningReport`。

## 16. 历史永不删除

`_history` / `_samples` 只在末尾追加，从不 `splice`/`pop`；`getHistory()` 返回 `deepFreeze(pureLearningCopy(...))` 只读纯数据拷贝。衰减与矛盾检测只影响输出中的 `confidence`，不触及原始记账。

## 17. EventBus 纪律（权威总数 471）

本层**零新增** EventBus 事件；Gate 2 扫描器动态取自真源，确认 `EventBus Total = 471`（非硬编码）。Phase 29.1-29.2 累计沿用既有 Learning 事件（Phase 20 登记 13 个）与 Reasoning 事件（Phase 29.1 登记 7 个，总计 464→471），未突破 471 上限。

## 18. 禁止修改范围遵守

未修改 `core/execution/` / `core/orchestrator/` / `core/sandbox/` / `core/agent/reasoning/`（agent 级旧层）/ Phase 29.1 核心行为。仅新增 `core/learning/reasoning-learning/` 纯 advisory 学习层 + 对应测试 / 扫描器 / main.js 演示段。

## 19. 模块清单（13 文件，与 `REASONING_LEARNING_MODULES` 冻结数组一致）

`forbidden.js` / `policy.js` / `outcome-extractor.js` / `pattern-extractor.js` / `strategy-scorer.js` / `recommender.js` / `confidence.js` / `decay.js` / `contradiction.js` / `memory-bridge.js` / `context-injector.js` / `engine.js` / `index.js`。Gate 2 确认 `Module Count = 13 个源文件`，`REASONING_LEARNING_MODULE_COUNT = 13`。

## 20. 禁止注入键

合并 `REASONING_LEARNING_FORBIDDEN_INJECTION_KEYS`（Learning153 类）与 `REASONING_FORBIDDEN_INJECTION_KEYS`（Reasoning99 类），构造期与序列化期双重拒绝执行句柄字段。`verifyReasoningLearningZeroAuthority` Item 4 确认禁止键非空。

## 21. 七道闸门总览

| Gate | 制品 | 通过标准 | 结果 |
|------|------|----------|------|
| 1 | `phase29_2_learning_test.js` | ≥45000 断言 / ≥70 段 / 0 FAIL | PASS 51927 / 79 段 / 0 FAIL |
| 2 | `scripts/scan-learning-execution.js` | Token=0 / Dep=0 / Violation=0 | EXIT 0 · 全 PASS |
| 3 | `check-consistency --fix` | EXIT 0 | EXIT 0 · 派生点一致 |
| 4 | `npm run test:all` | 套件+1 / 0 FAIL | EXIT 0 · 全量 0 FAIL |
| 5 | `scripts/learning-smoke.js` | ≥20 场景 | 96 通过 / 25 场景 / 0 失败 |
| 6 | `phase29_2_learning_conversation_e2e_test.js` | ≥12 多轮 / ≥180 断言 | 378 / 13 段 / EXIT 0 |
| 7 | `main.js [学习层演示]` | 真实运行 EXIT 0 | EXIT 0 ×2 |

## 22. Gate 1 详情（单元长测）

`phase29_2_learning_test.js`：79 个 section，累计 **51927** 断言，0 FAIL。覆盖九能力单元、零执行权 8 项硬 invariant、模块常量、构造拒注入、衰减只降权、矛盾降级、置信度分级禁用「1 次成功即最佳」、记忆桥禁用路径、推荐/上下文纯 advisory、历史不删、引擎 `toJSON` 等。

## 23. Gate 2 详情（纯净度扫描）

`scripts/scan-learning-execution.js`：Structural = PASS；Runtime Invariant = PASS；Module Count = 13；EventBus Total = 471（动态取自真源）。Token = 0 / Dep = 0 / Violation = 0。

## 24. Gate 3 详情（一致性校验）

`node scripts/check-consistency.js --fix`：EXIT 0；校验派生点（版本号 38 处 · 事件总数 65 处 · 套件数 11 处 · 末端套件 3 处 · UI API 方法数 2 处）全部与真源一致；1 处旧值否定断言为刻意保留（phase17_goal_test.js 的 0.19.0），正确跳过。

## 25. Gate 4 详情（全量回归）

`npm run test:all`：EXIT 0。Phase 29.2 套件接入 `test:all`（套件 +1），末段 `Phase 29.2 自适应推理学习层 Gate 1：PASS 51927 / FAIL 0（共 79 段，2740ms）`，全量 0 FAIL。

## 26. Gate 5 详情（冒烟，25 场景）

`scripts/learning-smoke.js`：25 个场景，96 通过 / 0 失败。覆盖零执行权自证、describe、模块常量、单成功、单失败、禁「1 次即最佳」、12 样本→strong、循环模式、预算模式、用户修正模式、能力关联、策略打分、矛盾（mixed + uncertain）、衰减、记忆桥禁用、推荐纯 advisory、上下文纯 advisory、历史不删、构造拒注入、端到端闭环、EventBus 471、九能力、置信度分级、engine.toJSON、安全闸。

## 27. Gate 6 详情（真实多轮对话 E2E）

`phase29_2_learning_conversation_e2e_test.js`：**13 段**，累计 **378** 断言，0 FAIL，EXIT 0。经真实 `ConversationGateway`（`core/integration/ConversationGateway.js`）`boot()` 装配真实内核，驱动 `gateway.host.reasoningLoop.run({goal, modifications}, {maxIterations, maxRetries})` 跑真实多轮推理（clean / repair / denied / broken / loop / budget 等场景），输出经忠实纯数据归一化 `toReasoningResult(...)` 映射为合法 `createReasoningResult`（status 映射：COMPLETED→success、ABORTED+REQUIRES_HUMAN→blocked、MAX_ITERATIONS/MAX_RETRIES/NON_RETRYABLE→failed；agent cycles 映射为 `isReasoningCycle` 兼容结构），再喂 `learnFromOutcome`。验证零执行权、模式抽取、strong 置信度、历史不删。

## 28. Gate 6 关键发现：网关推理环形态不兼容

`gateway.host.reasoningLoop` 是 **agent 级推理环**（`core/agent/reasoning/reasoning-loop.js`，即 Coding Agent 多轮环），其 `run` 要求 `{goal, modifications}`、输出 `status` 取 `REASONING_STATES`（COMPLETED/ABORTED 等），与 Phase 29.1 `core/reasoning/result.js` 的 `ReasoningResult`（7 枚举 + executionAuthority + authorityHolder + cycles）**形状完全不同**。学习层 `learnFromOutcome` 严格 `isReasoningResult()` 校验会拒收 agent 环输出。解决方案：编写忠实纯数据归一化函数 `toReasoningResult(agentResult, goalContext)`，把 agent 环真实输出映射为合法 Phase 29.1 形态后再学习——既满足「经真实 ConversationGateway 启动推理链」「从真实多轮推理历史提取模式」，又严守零执行权与输入校验。

## 29. Gate 7 详情（main.js 演示，真实运行）

`main.js` 新增 `[学习层演示]` 段（紧随 `[多轮推理层演示]` 之后），`PAIOS_MODEL=heuristic node main.js` 真实运行 EXIT 0，未伪造成功。演示产出：
- 层级 `adaptive-reasoning-learning` / 版本 0.35.0 / 模块 13 / 禁注 13 文件 / 执行权=无（唯一属于 execution-sandbox）。
- 批次 A（12 成功 + 1 循环）：置信度快照 `level=strong` / 样本 14 / 一致性 0.929。
- 最终（追加失败/预算/用户修正）：已学 18 个结果 / 置信度 `supported` / 一致性 0.778（真实反映一致性下降）。
- 推理专属模式 8 类：`capability_correlation` ×2 / `success_pattern` / `reasoning_loop` / `budget_overrun` / `user_correction` / `strategy_effectiveness` ×2。
- 策略建议 policyMode=`single_round`（因历史含 loops>0，符合 `_inferPolicyMode`）；上下文注入 advisory 提示「复用历史高成功路径」「对循环敏感目标采用 single_round 策略」。
- 记忆桥 `stored=false / entries=0`；矛盾检测已执行。
- 零执行权自证：模块级 ok=true / 门面级 ok=true / 历史永不删（长度 18 == 已学 18）。

## 30. 双次复现记录

- Gate 1 / 2 / 3 / 5 / 6 / 7 各运行 **2 次**，结果完全一致（Gate 1 由 test:all 直接承载并确认首次通过；Gate 2/3/5/6/7 复现 0 FAIL / EXIT 0）。
- Gate 4 确认首次 `test:all` EXIT 0 后，本次最终复跑再次 EXIT 0、全量 0 FAIL。

## 31. 性能与质量

- Gate 1 单测 51927 断言耗时 ~2740ms（test:all 内）；Gate 5 冒烟 25 场景毫秒级；Gate 7 真实 main.js 全链路 EXIT 0。
- 全为零依赖纯数据计算，无网络 / 无子进程 / 无外部 I/O 阻塞。
- 未引入第三方测试框架；复用自研 `core/test/Harness.js` 的 `createHarness()`（section/ok/eq/deepEq/throws 各计 1 断言，不调用 process.exit）。

## 32. 执行纪律遵守

- 不为了通过测试而迎合错误实现；优先修真实源码 bug。
- 本阶段 2 处早期 Gate 5 失败属**测试断言假设错误**（衰减纯对象无 `executionAuthority` 字段、矛盾用例正反比例误算），已据真实行为**修正断言（非降低要求）**，无源码缺陷。
- Gate 6 早期失败为 **API 误用**（误把 agent 级环当 Phase 29.1 通用环），通过忠实归一化层解决，未降低断言门槛。
- 未自动进入 Phase 29.3；完成后显式 `PHASE_29_2_COMPLETE` / `STOP_AT_PHASE_29_2`。

## 33. 验收结论

Phase 29.2 自适应推理与学习层**全部七道闸门通过、双次复现一致、零执行权红线严守、EventBus 权威 471 未突破、九大核心能力完整落地、复用既有 Learning/Memory 引擎未重造推理引擎**。本层为 Phase 29.1 通用多轮推理层叠加了「从自身历史学习并自我调优」的闭环能力，且始终恪守 Learning ≠ Executor 原则。

**PHASE_29_2_COMPLETE**
**STOP_AT_PHASE_29_2**
