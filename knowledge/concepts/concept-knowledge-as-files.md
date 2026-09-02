---
id: concept-knowledge-as-files
type: concept
title: 知识即文件
status: linked
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- concept
- knowledge
---

知识层以 .md 文件为唯一事实源，不使用 RAG / 嵌入 / 向量库 / 数据库。统一入口为 Knowledge Runtime，所有 Agent / Workflow / Planner / Memory Builder 经 knowledge.* 调用，不得直接读取 markdown。详见 [[知识即文件]] 实践与 [[DECISION_003 — 记忆单一来源]]。
