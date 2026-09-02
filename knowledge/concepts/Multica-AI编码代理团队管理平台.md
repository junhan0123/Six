---
id: know-multica-ai
type: concept
---
# Multica — AI 编码代理团队管理平台

> **归档日期：** 2026-08-11
> **来源：** https://github.com/multica-ai/multica
> **标签：** #AI代理 #编码代理 #团队管理 #多代理 #开源

## 项目信息

- **仓库：** [multica-ai/multica](https://github.com/multica-ai/multica)
- **Stars：** 45.2k
- **Fork：** 5.8k
- **License：** Apache-2.0
- **活跃开发：** 2097 分支，143 标签，4665 次提交

## 定位

Multica 是一个开源平台，把 AI 编码代理当作**团队成员**来管理。你像分配 GitHub issue 一样把任务指派给代理，代理自主执行、写代码、报告进度、标记阻塞。

## 核心特性

### 1. Issue-Driven 工作流
- 从 GitHub issue 创建任务
- 代理自动认领、执行、更新状态
- 实时进度流式传输

### 2. 多代理并行
- 多个代理运行在不同 workspace
- 每个 workspace 独立：issue、代理、设置隔离
- 支持 Squads（代理组），由路由代理领导

### 3. 供应商中立
- 支持 Claude Code、Codex、OpenCode、OpenClaw、Hermes、Gemini、Pi、Cursor Agent 等
- 任何终端运行的代理都能管理

### 4. 架构
- **前端：** Next.js + Electron 桌面应用
- **后端：** Go + WebSocket
- **数据库：** PostgreSQL + pgvector
- **部署：** Docker Compose、单二进制、Kubernetes

### 5. 自部署
- 完全开源，可自托管
- Docker Compose 一键部署
- 数据和代码不离开你的基础设施

## 和我们有什么关系

### 与 Hermes 的对比

| 特性 | Hermes | Multica |
|------|--------|---------|
| 定位 | 个人 AI 助手 | 团队代理管理平台 |
| 代理管理 | 单代理 + 子代理 | 多代理 + Squads |
| 工作流 | 对话驱动 | Issue 驱动 |
| 部署 | 本地 | 本地/云端 |
| 支持代理 | 内置 | 第三方代理 |

### 潜在应用场景

1. **小6项目 - 多代理协作**
   - Multica 的 Squads 架构可参考
   - Issue 驱动的工作流思路

2. **Hermes 技能扩展**
   - 可参考 Multica 的代理路由机制
   - 多代理并行执行模式

3. **与 Multica 共存**
   - Multica 支持 Hermes 作为代理运行时
   - 可作为 Hermes 的"上层管理平台"

## 相关笔记

- Pi-Agent-极简AI编码代理 — Pi Agent 极简设计理念
- Agency-Agents-AI多代理角色框架 — AI 多代理角色框架
- GPT-SoVITS-少样本语音克隆TTS — 语音克隆 TTS
- AnyDoc-文档解析引擎 — 文档解析引擎
