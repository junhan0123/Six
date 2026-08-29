---
id: know-superpowers-ai
type: concept
---
# Superpowers — AI 编码代理技能框架

> **归档日期：** 2026-08-11
> **来源：** GitHub Trending
> **标签：** #AI工具 #Agent #编码辅助 #技能框架

## 项目信息

- **仓库：** [obra/superpowers](https://github.com/obra/superpowers)
- **作者：** obra（Jesse Vincent，老牌开源开发者）
- **Star：** 270k+ | **Fork：** 24.2k+
- **许可证：** MIT
- **首发：** 2025 年 10 月
- **最新提交：** 2 周前（680 commits）

## 是什么

Superpowers 是一个为 AI 编码代理（Coding Agent）设计的**技能框架 + 软件开发方法论**。它通过一组可组合的 Skills 和初始指令，强制 AI 代理遵循专业开发流程，而不是直接跳到写代码。

## 支持的平台

Claude Code、Cursor、Codex App、Codex CLI、Gemini CLI、Kimi Code、OpenCode、Pi、GitHub Copilot CLI、Factory Droid、Antigravity 等。

## 核心机制

### 1. 启动时不急着写代码
AI 代理看到项目后，**不会直接开始写代码**，而是先问你在做什么，帮你梳理需求。

### 2. 需求确认
把 spec 分段展示给你审阅，确保理解正确。

### 3. 实现计划
设计清晰到"热情但品味差、没上下文的初级工程师"都能跟着做。强调：
- **TDD**（测试驱动开发）
- **YAGNI**（不会需要的就别做）
- **DRY**（不要重复自己）

### 4. 子代理驱动开发（Subagent-Driven Development）
- 每个工程任务分配给独立子代理
- 子代理自主检查 + 审查自己的工作
- 可以连续几小时不偏离计划自主工作

### 5. 技能自动触发
Skills 配置后自动生效，不需要手动干预。

## 项目结构

```
superpowers/
├── skills/              # 可组合的技能集合（核心）
├── docs/                # 文档
├── hooks/               # 钩子脚本
├── scripts/             # 辅助脚本
├── tests/               # 测试
├── .cursor-plugin/      # Cursor 插件
├── .claude-plugin/      # Claude Code 插件
├── .codex-plugin/       # Codex 插件
├── .gemini-plugin/      # Gemini CLI 插件
├── AGENTS.md            # Agent 指令
├── CLAUDE.md            # Claude 指令
├── GEMINI.md            # Gemini 指令
└── package.json
```

## 社区评价

- GitHub Trending 霸榜项目
- 知乎、CSDN、什么值得买都有深度解析
- 被称为"给编程智能体装上最佳实践"
- 核心卖点：强制 AI 遵循 TDD、代码审查等最佳实践，告别代码收拾残局

## 和我们有什么关系

### 与 Hermes Agent 的关联
- Superpowers 的 **skills 设计模式** 可作为 Hermes Agent 技能开发的参考
- **Subagent-Driven Development** 理念与 Hermes 的 `delegate_task` 批量子代理机制有相似之处
- 但 Superpowers 主要面向 Claude Code/Cursor 等**商业 IDE 插件**，Hermes 是**自主 Agent 系统**，两者定位不同

### 潜在借鉴点
1. **Skills 组合方式** — 如何将复杂开发流程拆解为可组合的小技能
2. **强制规范机制** — 通过指令让 AI 代理必须遵循 TDD/YAGNI/DRY
3. **子代理分工** — 大任务拆分成独立子代理并行执行

### 局限性
- Superpowers 不直接支持 Hermes Agent
- 需要自行适配到 Hermes 的技能系统
- 其 skills 数量还在增长中，稳定性待观察

## 相关笔记

- Hermes Workflow — Hermes Agent 工作流
- 技术决策-自研AI智能体平台-20260803 — 小6项目技术决策
- Agent_Core — Agent 核心规范
- GSAP AI Skills 官方编程技能包 — AI 编程技能包
