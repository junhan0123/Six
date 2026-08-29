---
id: know-pi-agent-ai
type: concept
---
# Pi Agent — 极简 AI 编码代理

> **归档日期：** 2026-08-11
> **来源：** https://github.com/earendil-works/pi
> **标签：** #AI代理 #编码代理 #TypeScript #开源

## 项目信息

- **仓库：** [earendil-works/pi](https://github.com/earendil-works/pi)
- **Star：** 86.2k | **Fork：** 10.7k
- **作者：** Mario Zechner（libGDX 框架作者，ID: badlogic）
- **许可证：** MIT
- **官网：** pi.dev
- **网站：** shittycodingagent.ai（作者幽默）

## 是什么

一个极简的、开源的 AI 编码代理，在终端中运行，自动化软件开发任务。

## 核心架构

### 1. Pi 单体仓库（Monorepo）
```
pi/
├── pi-coding-agent    # 交互式编码代理 CLI
├── pi-agent-core      # 代理运行时（工具调用 + 状态管理）
├── pi-ai              # 统一多提供商 LLM API
├── pi-tui             # 终端 UI
```

### 2. 核心特性
- **极简设计** — 只使用必要的组件
- **多 LLM 支持** — OpenAI、Anthropic、Google 等
- **终端交互** — 基于 TUI 的命令行界面
- **工具调用** — 支持文件读写、命令执行等
- **状态管理** — 代理状态持久化

### 3. 设计理念
- 不追求功能堆砌
- 专注于编码任务
- 高度可定制
- 作者认为"大多数编码代理都过度设计"

## 和我们有什么关系

### 与 Hermes 的对比

| 特性 | Hermes | Pi Agent |
|------|--------|----------|
| 定位 | 通用 AI Agent 平台 | 专注编码的代理 |
| 语言 | Python | TypeScript |
| 能力 | 搜索、浏览、文件、cron 等 | 文件读写、命令执行 |
| 架构 | 多工具集 | 极简单体 |
| 适用场景 | 综合自动化 | 纯编码任务 |

### 潜在应用场景

1. **编码任务辅助**
   - 对于纯编码任务，Pi Agent 可能更轻量高效
   - 可以作为 Hermes 的补充工具

2. **架构参考**
   - Pi 的极简设计理念值得学习
   - Hermes 的技能系统可以参考其"最小必要"原则

3. **与 OpenClaw 的关系**
   - Pi 是 OpenClaw 的核心组件
   - OpenClaw 基于 Pi 构建更完整的代理系统

### 局限性

- 仅支持编码任务，不能做网页搜索、文件管理等
- TypeScript 生态，与 Hermes Python 生态不同
- 需要配置 LLM API Key

## 相关笔记

- Hermes Workflow — Hermes Agent 工作流
- Firecrawl-Web内容抓取API — Web 内容抓取
- 工具配置 — 工具链配置
