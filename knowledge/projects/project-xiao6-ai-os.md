---
id: project-xiao6-ai-os
type: project
title: Xiao6 AI OS 2.0
status: consolidated
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- project
- ai-os
related_knowledge:
- concept-local-first
- concept-single-runtime
- concept-knowledge-as-files
- concept-eventbus
- concept-proactive-thin-layer
- decision-eventbus
- decision-no-second-runtime
- decision-memory-single-source
- decision-galaxy-boundary
- decision-permission-policy
- decision-langchain-position

- person-owner
---

小6：本地优先的个人 AI OS。后端 monolith（server.py）+ 前端原生 JS/Three.js + Electron 壳，Agnes 为模型，FunASR + edge-tts 为语音，GDELT/USGS/OpenSky/Open-Meteo 为态势源。

设计原则：[[本地优先架构]]、[[单一运行时内核]]、[[知识即文件]]、[[事件总线]]、[[主动智能薄层]]。治理入口 AI_BOOTSTRAP.md；L0 冻结红线（单 Runtime / 单状态写入口 / 单 EventBus / 单 Permission / Local First / 无 God Module）。
