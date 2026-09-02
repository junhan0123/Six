---
id: decision-galaxy-boundary
type: decision
title: DECISION_004 — 星系边界
status: consolidated
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- decision
- governance
provenance: docs/decisions
---

# DECISION_004 — Galaxy 边界

## 背景
Galaxy（太阳系可视化）是小6的标志性表现层：太阳=小6核心、轨道=Goal、星球=能力域、卫星=Agent、环=Memory、流星=主动推送。它既是品牌资产也是状态可视化。

## 问题
- 若把业务逻辑/状态权威塞进 Galaxy，会破坏「AppState 唯一写入口」纪律。
- 若把 Galaxy 当交互层滥用，会偏离其「可视化」本职，造成架构耦合。

## 候选方案
1. **A. Galaxy 承载业务逻辑**（破坏单一状态入口）。
2. **B. Galaxy = 纯可视化 + 受控交互层**（采用，依据 Product Constitution）。

## 最终选择
**B**：Galaxy 是**表现层**。状态权威永远在 `AppState`；Galaxy 通过 `GalaxyState`（只读投影）订阅渲染。Galaxy 可从「展示层升为交互层」（点击行星→能力面板、拖动轨道→调 Goal），但**不改银河本体**、不持有业务状态。

## 原因
- 保护品牌资产（自转/公转/星空/点击聚焦）与 OS 重构互不冲突、可并行。
- 只读投影模式与 ComputerState/PerceptionState 一致，架构统一。
- 受控交互（galaxy-overlay 叠加层）不污染银河本体。

## 影响范围
- Galaxy 不读写业务状态，只渲染 `AppState` 投影。
- 任何 Galaxy 交互须经 `galaxy-overlay` 叠加层，不改动 `solar-system.js` 本体。
- Overlay Runtime 与 Galaxy 渲染解耦。

## 未来限制
- 禁止让 Galaxy 直接修改 `AppState` 或持有可写状态。
- 禁止改动银河本体视觉资产（除非品牌重构专项）。
