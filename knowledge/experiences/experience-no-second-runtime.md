---
id: experience-no-second-runtime
type: experience
title: 为什么不做第二运行时
status: reviewed
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- experience
- architecture
related_knowledge:
- decision-no-second-runtime
- concept-single-runtime
---

早期模块曾各自维护私有状态，导致状态不一致、调试困难、事件命名漂移。收敛为单一运行时内核 + EventBus 单一写入口后，状态可追溯、前后端对称。教训：任何「再开一个 Runtime/Memory/EventBus」的冲动都应被 [[DECISION_002 — 禁止第二运行时]] 挡回。
