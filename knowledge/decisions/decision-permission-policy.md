---
id: decision-permission-policy
type: decision
title: DECISION_005 — 权限策略
status: consolidated
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- decision
- governance
provenance: docs/decisions
---

# DECISION_005 — Permission / Policy 唯一权限

## 背景
Computer Operating Layer 能执行鼠标/键盘/应用等高风险动作。权限判断若分散在 Executor / Agent / UI 多处，会出现「有的地方拦、有的地方放」的漏洞。

## 问题
- 权限逻辑分散 → 安全策略不可审计、易绕过。
- 风险分级（risk tier）若与 Capability 脱节，会误放行高危能力。

## 候选方案
1. **A. 各执行点自判权限**（漏洞）。
2. **B. PolicyEngine + PermissionGuard 唯一权限闸门**（采用）。

## 最终选择
**B**：`PolicyEngine` 定义风险分级与策略，`PermissionGuard` 是**唯一**权限闸门。所有 Computer Action 必须经 `PermissionGuard` 校验后才可经 `Executor` 执行；`AgentRuntime` 不直接放行动作。

## 原因
- 单一闸门让安全策略可集中审计与评审。
- Capability 的 `risk` 字段经 `RISK_TIER` 映射到 PolicyEngine，形成「能力→风险→策略」闭环。
- Verification Loop 在动作后复核，与权限闸门前后呼应。

## 影响范围
- 任何 Computer Action 不得绕过 `PermissionGuard`。
- 新增能力须声明 `risk`，由 PolicyEngine 评估。
- UI 不直接触发执行，只经事件 → Agent → PermissionGuard → Executor。

## 未来限制
- 禁止新增第二 Permission 系统或第二 Policy 系统。
- 禁止 Executor 跳过 PermissionGuard 直接执行。
