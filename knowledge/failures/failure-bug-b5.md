---
id: failure-bug-b5
type: failure
title: B5 — 自动隐藏时长不可配置
status: reviewed
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- bug
- companion
provenance: BUG_WALL.md
---

编号：B5
优先级：P3（可选）
证据：CODE 确认
状态：待处理

根因：companion.js 中 IDLE_HIDE_MS = 45000 硬编码，用户无法调整自动隐藏阈值。

建议：纳入 Companion 偏好（存 companion.json，无新 API），提供 15s/30s/45s/关闭 选项。与 B7、R4 同源，待 Beta 1.2 统一迭代。
