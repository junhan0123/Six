---
id: know-personalaios
type: concept
---
# PersonalAIOS 项目文档

> 归档日期：2026-08-15
> 当前版本：**v0.39.0**
> 最新阶段：**Phase 31.2 已收口（STOP_AT_PHASE_31_2 = true）**

## 项目概述

PersonalAIOS 是一个**零外部运行时依赖、零测试框架、全链路零执行权**的个性化 AI 操作系统内核。

## 架构分层

- `core/capability/` — 能力 OS / 统一能力路由
- `core/autonomous/` — 统一自主工作闭环
- `core/reasoning/` — 多轮推理与自主调试
- `core/learning/` — 自适应学习
- `core/continuity/` — 长程连续工作
- `core/runtime/` — 统一运行时内核
- `core/orchestrator/` — 编排器
- `core/execution/` + `core/sandbox/` — ExecutionSandbox（唯一真实执行边界）

## 当前状态

| 项 | 值 |
|---|---|
| EventBus 事件总数 | **490** |
| test:all 套数 | **55**（Exit 0 / 0 FAIL） |
| 内核运行时依赖 | **0** |

## 阶段报告索引

- Phase 101: PHASE10_1_TEST_REPORT.md
- Phase 102: PHASE10_2_TEST_REPORT.md
- Phase 103: PHASE10_3_TEST_REPORT.md
- Phase 104: PHASE10_4_TEST_REPORT.md
- Phase 105: PHASE10_5_TEST_REPORT.md
- Phase 11: PHASE11_TEST_REPORT.md
- Phase 12: PHASE12_TEST_REPORT.md
- Phase 13: PHASE13_TEST_REPORT.md
- Phase 14: PHASE14_TEST_REPORT.md
- Phase 15: PHASE15_TEST_REPORT.md
- Phase 16: PHASE16_TEST_REPORT.md
- Phase 17: PHASE17_GOAL_TEST_REPORT.md
- Phase 17: PHASE17_TEST_REPORT.md
- Phase 18: PHASE18_CONTRACT_REPORT.md
- Phase 18: PHASE18_RUNTIME_REPORT.md
- Phase 19: PHASE19_MEMORY_INTELLIGENCE_REPORT.md
- Phase 20: PHASE20_LEARNING_REPORT.md
- Phase 21: PHASE21_PLUGIN_CONTRACT_REPORT.md
- Phase 21: PHASE21_PLUGIN_RUNTIME_REPORT.md
- Phase 22: PHASE22_CAPABILITY_BRIDGE_REPORT.md
- Phase 23: PHASE23_EXECUTION_PIPELINE_REPORT.md
- Phase 251: PHASE25_1_ELECTRON_UI_REPORT.md
- Phase 2529: PHASE25_29_MVP_FINAL_REPORT.md
- Phase 2529: PHASE25_29_MVP_REPORT.md
- Phase 253: PHASE25_3_MVP_INTEGRATION_REPORT.md
- Phase 261: PHASE26_1_WEB_BROWSER_REPORT.md
- Phase 262: PHASE26_2_RESEARCH_AGENT_REPORT.md
- Phase 27: PHASE27_COMPUTER_AGENT_REPORT.md
- Phase 281: PHASE28_1_VISION_REPORT.md
- Phase 282: PHASE28_2_DOCUMENT_REPORT.md
- Phase 283: PHASE28_3_DATA_CAPABILITY_REPORT.md
- Phase 284: PHASE28_4_AUTOMATION_CAPABILITY_REPORT.md
- Phase 285: PHASE28_5_ORCHESTRATION_CAPABILITY_REPORT.md
- Phase 286: PHASE28_6_AUTONOMOUS_CAPABILITY_REPORT.md
- Phase 291: PHASE29_1_MULTI_ROUND_REASONING_REPORT.md
- Phase 292: PHASE29_2_ADAPTIVE_LEARNING_REPORT.md
- Phase 293: PHASE29_3_ARCHITECTURE_BASELINE.md
- Phase 293: PHASE29_3_UNIFIED_AUTONOMOUS_WORK_LOOP_REPORT.md
- Phase 294: PHASE29_4_LONG_HORIZON_CONTINUITY_REPORT.md
- Phase 30: PHASE30_ARCHITECTURE_BASELINE.md
- Phase 30: PHASE30_CAPABILITY_OS_ARCHITECTURE_REPORT.md
- Phase 311: PHASE31_1_UNIFIED_RUNTIME_REPORT.md
- Phase 312: PHASE31_2_AUTONOMOUS_TASK_REPORT.md
- Phase 312: PHASE31_2_RUNTIME_CONTROL_PLANE_REPORT.md
- Phase 4: Phase4_Work_Summary.md
- Phase 6: Phase6_Work_Summary.md

## 运行方式

```bash
node main.js "创建一个简单React Todo应用"     # 内核 CLI 演示
npm run test:all                             # 55 套全量回归
npm start                                    # Electron UI（需先 npm install）
```

## 零执行权安全边界

**唯一真实执行链**：`Orchestrator → ExecutionSandbox`
- 任何 Runtime / Recovery / Coordination 层**不得**直调 terminal·app·browser·file executor
- 所有 Phase 31.2 组件 `hasExecutionAuthority() === false`

## 继承要点

- **EventBus 490 纪律**：不得因新层随意加事件
- **test:all 是字面 && 链**：任一 Gate FAIL 即中止后续所有套件
- **禁测试框架**：沿用自研 harness，不得引入 jest/vitest
