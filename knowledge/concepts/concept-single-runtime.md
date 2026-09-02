---
id: concept-single-runtime
type: concept
title: 单一运行时内核
status: linked
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- concept
- runtime
related_knowledge:
- decision-no-second-runtime
- decision-eventbus
---

系统只存在唯一运行时内核，所有状态变更经 EventBus → AppState.applyEvent 单一写入口。禁止第二 Runtime / Memory / EventBus / Permission（见 [[DECISION_002 — 禁止第二运行时]] 与 [[DECISION_001 — EventBus 单一来源]]）。这是 L0 冻结红线之一。
