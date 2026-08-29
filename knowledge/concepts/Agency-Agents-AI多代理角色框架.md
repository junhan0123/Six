---
id: know-agency-agents-ai
type: concept
---
# Agency Agents — AI 多代理角色框架

> **归档日期：** 2026-08-11
> **来源：** https://github.com/msitarzewski/agency-agents
> **标签：** #AI代理 #多代理 #角色框架 #开源

## 项目信息

- **仓库：** [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents)
- **中文适配版：** [jnMetaCode/agency-agents-zh](https://github.com/jnMetaCode/agency-agents-zh) — 19k stars
- **定位：** AI 代理角色框架 — 提供即插即用的 AI 专家角色

## 是什么

一套完整的 AI Agency 角色框架，每个代理都是具有独特人格、流程和交付物的专业专家。

## 核心能力

### 1. 角色代理（Role Agents）
- **前端代理** — 前端开发专家
- **Reddit 社区代理** — 社区运营专家
- **创意注入代理** — 创意策划专家
- **现实检查代理** — 质量评估专家
- **财务代理** — 会计/付款处理
- **身份图谱代理** — 多代理身份解析

### 2. 即插即用
- 每个角色独立运行
- 支持 Hermes Agent / Claude Code 等框架
- 267 个预设角色（中文版）

### 3. 多代理协作
- 代理之间可以协作完成任务
- 支持角色分工和流程编排

## 和我们有什么关系

### 潜在应用场景

1. **小6项目 - 能力模块扩展**
   - 可以参考其角色设计思路
   - 为小6的能力模块添加更细粒度的角色分工

2. **Hermes 技能系统**
   - agency-agents-zh 已适配 Hermes Agent
   - 可以直接加载这些角色作为技能

### 局限性

- 主要是**角色定义框架**，不是完整的代理运行框架
- 需要配合其他框架（Hermes、Claude Code 等）使用
- 中文版 19k stars 说明社区认可度高

### 替代方案

- **Hermes 自有技能系统** — 更贴合当前架构
- **Pi Agent** — 更轻量的编码代理框架

## 相关笔记

- Hermes Workflow — Hermes Agent 工作流
- Firecrawl-Web内容抓取API — Web 内容抓取
- 工具配置 — 工具链配置
