---
id: concept-local-first
type: concept
title: 本地优先架构
status: linked
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- concept
- local-first
related_knowledge:
- concept-knowledge-as-files
---

小6 AI OS 的核心约束：所有用户数据与知识以本地文件为唯一事实源，不依赖云计算、不联网同步、不使用云端数据库。云仅用于模型推理计算。

Local First 保证隐私与可审计性，所有变更可通过 git 追踪，符合小6 AI OS 2.0 的总体定位。
