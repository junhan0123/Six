---
id: concept-proactive-thin-layer
type: concept
title: 主动智能薄层
status: linked
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- concept
- proactive
---

ProactiveEngine 是薄决策层（IGNORE/SUGGEST/NOTIFY/CREATE_GOAL），只做判断不执行；所有执行经 submit_goal（必带 goal_id）+ Policy Guard。克制主动，避免打扰，是小6区别于通用助手的定位之一。
