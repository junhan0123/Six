---
id: failure-bug-b1
type: failure
title: B1 — 桌宠生命感动画不可见
status: archived
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- bug
- companion
provenance: BUG_WALL.md
---

编号：B1
优先级：P1（体验回归）
证据：CODE 确认
状态：已解决（Beta 1.1）

根因：avatar-renderer.js 默认 SVG 资产无内部动画；CSS 生命动画（av-blink/av-look/av-focus/av-effort）命中降级脸（fallbackFace）空集，桌宠「脸」为静态 SVG，核心/环/光环的包裹动画仍可见。

影响范围：Companion 桌宠全部 8 态「脸」表现层（Phase 10.2 生命感）失效。

修复（Beta 1.1）：8 个 SVG 重写注入语义类（av-eye/av-mouth/av-face），companion.css 改为transform-box: fill-box + transform 基契约；LIVE 待老板目测眨眼/观察/执行提示是否可见。
