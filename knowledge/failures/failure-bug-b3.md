---
id: failure-bug-b3
type: failure
title: B3 — 主动建议不可执行
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

编号：B3
优先级：P2（体验）
证据：CODE 确认
状态：已解决（Beta 1.1）

根因：insight-panel.js 的「执行」走主窗 DOM（#input+#btnSend）；Companion onProactiveMessage 仅 showNotification，无执行入口。默认常驻表面（桌宠）无法就地执行建议。

修复（Beta 1.1）：showNotification 支持 opts.executable/execContent；非告警类经 bridge.action({type:'execute-suggestion'}) 复用既有聊天执行链路。无新 API。
