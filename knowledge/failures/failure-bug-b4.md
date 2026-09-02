---
id: failure-bug-b4
type: failure
title: B4 — 同一主动事件双提示
status: archived
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- bug
- companion
- proactive
provenance: BUG_WALL.md
---

编号：B4
优先级：P2（体验冗余）
证据：CODE 确认
状态：已解决（Beta 1.1）

根因：insight-panel.js 与 companion.js 各自订阅 ZZSSE.onMessage，独立呈现同一 proactive 事件，两窗同显时重复打扰。

修复（Beta 1.1）：主窗广播 companion:main-visible；Companion onProactiveMessage 加 if(mainVisible) return 守卫，主窗可见时由主窗 Toast 呈现。
