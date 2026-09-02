---
id: decision-no-second-runtime
type: decision
title: DECISION_002 — 禁止第二运行时
status: consolidated
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- decision
- governance
provenance: docs/decisions
related_knowledge:
- decision-eventbus
- decision-memory-single-source
- decision-permission-policy
- decision-galaxy-boundary
- decision-langchain-position
---

# DECISION_002 — 禁止第二 Runtime

## 背景
系统含多种「后台循环」：`AgentRuntime`（决策）、`CaptureRuntime` / `PerceptionRuntime`（观察生产者）、Galaxy 渲染循环。混用「runtime」一词易引发「是否新增决策运行时」的歧义。

## 问题
- 若允许任意模块自创「Runtime」并做 Goal→Action 决策，会打破唯一编排入口，产生并行决策冲突。
- Perception/Vision 若被允许决策，会越权控制电脑（安全红线）。

## 候选方案
1. **A. 每个能力层自管 Runtime**（危险）—— 并行决策、失控。
2. **B. 单一决策 Runtime + 观察生产者分离**（采用）。

## 最终选择
**B**：`AgentRuntime` 是**唯一**能做「Goal → Capability → Executor」决策的运行时。`CaptureRuntime` / `PerceptionRuntime` 仅为**观察生产者**——采集、融合、发 `PERCEPTION_*` 事件，**绝不构造 `ComputerAction`、绝不调用 Executor**。

## 原因
- 单一决策入口确保权限/策略在唯一位置生效（PolicyEngine + PermissionGuard）。
- 观察与决策分离是安全闭环的基础（Vision 永远只能 Observation，不能 Control）。
- 渲染循环（Galaxy Three.js）属于表现层，不算决策 Runtime。

## 影响范围
- 任何「理解/规划/执行」逻辑必须运行在 `AgentRuntime` 内。
- Perception/World Model 只产出 Observation/State，不产出 Action。
- Phase 9 Context Engine 只汇编上下文，不新增决策 Runtime。

## 未来限制
- 禁止新增任何以「Runtime」命名且具备决策能力的模块。
- 禁止让观察生产者跨入 Action 构造。
