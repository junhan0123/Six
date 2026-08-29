---
id: concept-eventbus
type: concept
title: 事件总线
status: linked
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- concept
- eventbus
related_knowledge:
- decision-eventbus
- concept-single-runtime
---

领域事件（DOMAIN_EVENT_NAMES，当前 71）与系统/遥测事件（SYSTEM_EVENT_NAMES，当前 8）两个互斥命名空间，经 publish_domain()/publish_system() 发出，未登记名称抛 ValueError。前端 zz-events.js 与后端 eventbus.py 逐字对齐。见 [[DECISION_001 — EventBus 单一来源]]。
