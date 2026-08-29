---
id: rule-context-loading-system
type: rule
title: 上下文加载系统
status: consolidated
created: '2026-08-06'
updated: '2026-08-06'
source: bootstrap
tags:
- rule
- context
provenance: personal-obsidian-00-system
---

# Context Loading System

任务开始前自动加载相关信息。

## 优先级

### Level 1 — 必须读取

`00_System/` — 系统规则

### Level 2 — 相关项目

`01_Projects/` — 对应项目上下文

### Level 3 — 历史经验

`02_Bug/` — 过往问题
`05_Library/` — 技术知识

### Level 4 — 工具资料

`03_Prompt/` — 提示词模板
`04_AI/` — AI 工具配置

## 原则

只加载相关内容。
避免无关信息污染上下文。
