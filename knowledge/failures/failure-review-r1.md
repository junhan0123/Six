---
id: failure-review-r1
type: failure
title: R1 — 缩放/多显示器点击穿透坐标一致性
status: reviewed
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- review
- companion
provenance: BUG_WALL.md
---

编号：R1
优先级：P1
证据：CODE（分析）
状态：LIVE 待验（Beta 1.1 Real World Review 新识别）

风险：B2 的代码修复依赖 getCursorScreenPoint 与 getPosition 坐标空间一致；150% 缩放 / 多显示器下必须真机首验，否则点击穿透坐标错位。

处置：不现场修复，纳入 NEXT_ITERATION_PLAN 等待 Beta 1.2。
