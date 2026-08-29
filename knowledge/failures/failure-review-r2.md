---
id: failure-review-r2
type: failure
title: R2 — 交互抢占 OS 焦点
status: reviewed
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- review
- companion
provenance: BUG_WALL.md
---

编号：R2
优先级：P2
证据：CODE+LIVE（分析）
状态：LIVE 待验

风险：透明置顶窗在交互（菜单/命令气泡打开）时抢占 OS 焦点，无自动归还机制。

处置：不现场修复，待 Beta 1.2 统一迭代。
