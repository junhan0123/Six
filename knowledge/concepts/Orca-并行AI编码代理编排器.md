---
id: know-orca-ai
type: concept
---
# Orca — 并行 AI 编码代理编排器

> **归档日期：** 2026-08-11
> **来源：** https://github.com/stablyai/orca
> **标签：** #AI代理 #编码代理 #并行代理 #ADE #开源

## 项目信息

- **仓库：** [stablyai/orca](https://github.com/stablyai/orca)
- **Stars：** 40.9k
- **Fork：** 2.8k
- **License：** MIT
- **Y Combinator 支持**
- **首次稳定发布：** 2026 年 3 月

## 定位

Orca 是一个 **ADE（Agent Development Environment）**，用于在单个界面中编排多个 CLI 编码代理。它不生产自己的模型或代理，而是驱动你已使用的 CLI 代理。

## 核心特性

### 1. 并行代理
- 使用并行 git worktrees 让多个代理同时工作
- 每个代理隔离在独立的 git worktree，避免代码冲突
- 支持 30+ CLI 代理

### 2. 支持的代理
- Claude Code、Codex、Cursor、OpenCode、Copilot、Grok、Kimi、Cline、Goose 等
- 使用用户自己的订阅，不经过 Orca 服务器

### 3. 内置开发环境
- Monaco 编辑器
- 内置浏览器（元素选择器、截图标注工具）
- 拆分终端
- 点击 UI 元素发送给代理

### 4. 跨平台
- macOS、Windows、Linux 桌面应用
- iOS、Android 移动端
- VPS 部署

### 5. 架构
- 不托管自己的模型/代理
- 驱动用户已有的 CLI 代理
- 中央界面追踪所有代理操作

## 和我们有什么关系

### 与 Hermes 的对比

| 特性 | Hermes | Orca |
|------|--------|------|
| 定位 | 个人 AI 助手 | 代理编排器 |
| 代理管理 | 内置代理 | 第三方代理 |
| 并行 | 子代理（串行） | 并行 git worktrees |
| 界面 | CLI/聊天 | 桌面 IDE |
| 订阅 | 自有 | 用户自有 |

### 潜在应用场景

1. **小6项目 - 代理编排**
   - Orca 的并行 worktree 机制可参考
   - 多代理同时工作的模式

2. **Hermes 性能优化**
   - 并行代理执行思路
   - 避免代码冲突的工作流

3. **与 Orca 共存**
   - Orca 可驱动 Hermes（如果 Hermes 有 CLI 接口）
   - 作为 Hermes 的"前端编排层"

## 相关笔记

- Multica-AI编码代理团队管理平台 — AI 代理团队管理
- Pi-Agent-极简AI编码代理 — Pi Agent 极简设计理念
- Agency-Agents-AI多代理角色框架 — AI 多代理角色框架
- GPT-SoVITS-少样本语音克隆TTS — 语音克隆 TTS
- AnyDoc-文档解析引擎 — 文档解析引擎
