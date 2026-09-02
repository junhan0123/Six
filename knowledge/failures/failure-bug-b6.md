---
id: failure-bug-b6
type: failure
title: B6 — 边缘吸附仅单轴
status: reviewed
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- bug
- companion
provenance: BUG_WALL.md
---

编号：B6
优先级：P3（可选）
证据：CODE 确认
状态：待处理

根因：main.js companion:drag-end 取 minH/minV 后只修正一个轴向，角落场景另一轴不吸附。

建议：角落场景双轴吸附（纯窗口几何，无业务变更）。与 R4 同源。
