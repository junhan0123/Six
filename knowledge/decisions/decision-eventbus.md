---
id: decision-eventbus
type: decision
title: DECISION_001 — EventBus 单一来源
status: consolidated
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- decision
- governance
provenance: docs/decisions
---

# DECISION_001 — EventBus 单一来源

## 背景
Xiao6 是多模块协作系统（Agent / Computer / Perception / Galaxy / Overlay / Memory）。早期各模块曾各自直接调用对方方法或维护私有状态，导致状态不一致、调试困难、事件命名漂移。

## 问题
- 状态变更缺乏统一通道，难以追踪「谁改了什么」。
- 前后端事件名称容易不一致（后端 `eventbus.py` vs 前端 `zz-events.js`）。
- 未知事件名可静默流入，造成难以排查的 bug。

## 候选方案
1. **A. 各模块自由调用 + 私有事件**（原始方式）—— 灵活但失控。
2. **B. EventBus 单一来源 + 注册表校验**（采用）。
3. **C. 消息队列（Kafka/RabbitMQ）**—— 过度工程，本地项目不需要。

## 最终选择
**B**：`eventbus.py` 定义 `DOMAIN_EVENT_NAMES`（领域事件）与 `SYSTEM_EVENT_NAMES`（系统/遥测事件）两个互斥命名空间；`publish_domain()` / `publish_system()` 对未登记名称抛 `ValueError`；前端 `zz-events.js` 的 `EVENTS` / `SYSTEM_EVENTS` 与后端**逐字对齐**（当前 71 + 8）。

## 原因
- 单一注册表让「新增事件」成为显式、可审查的变更。
- 校验强制前后端对称，消除漂移。
- DOMAIN / SYSTEM 分离避免状态事件与遥测事件混淆。

## 影响范围
- 所有状态变化必须经 EventBus → AppState（`applyEvent` 唯一写入口）。
- 任何模块不得自行维护跨模块可见的可变状态。
- 新增事件须同步修改 `eventbus.py` 与 `zz-events.js` 并补测试。

## 未来限制
- 禁止引入第二事件总线或第二 SSE 通道承载领域事件。
- 禁止绕过 `publish_domain`/`publish_system` 直接 `emit` 领域事件。
- 事件总数需受控（Phase 9 预算 ≤10 新增），避免爆炸。
