---
id: failure-bug-b2
type: failure
title: B2 — 透明置顶窗点击穿透
status: archived
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- bug
- companion
provenance: BUG_WALL.md
---

编号：B2
优先级：P1（若真机确认阻断点击则升 P0）
证据：CODE+LIVE
状态：已解决（Beta 1.1，LIVE 待确认）

根因：electron/main.js 创建 Companion 窗仅设 transparent+alwaysOnTop，全仓无 ignoreMouseEvents / setIgnoreMouseEvents / clickThrough 逻辑；透明窗默认捕获矩形内所有鼠标事件，下方应用收不到点击。

修复（Beta 1.1）：createCompanionWindow 后 setIgnoreMouseEvents(true,{forward:true}) + 120ms 轮询命中矩形恢复交互；新增 IPC companion:set-clickthrough（true/false/auto）。LIVE 待老板确认覆盖区点击穿透。
