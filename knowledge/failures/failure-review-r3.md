---
id: failure-review-r3
type: failure
title: R3 — Hover 120ms 轮询微延迟
status: reviewed
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- review
- companion
provenance: BUG_WALL.md
---

编号：R3
优先级：P3
证据：CODE 确认
状态：LIVE 待观察

风险：点击穿透依赖 120ms 轮询 screen.getCursorScreenPoint，Hover 存在微延迟。

处置：体验打磨项，待 Beta 1.2 评估是否降级为事件驱动。
