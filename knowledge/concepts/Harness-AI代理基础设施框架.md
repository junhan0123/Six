---
id: know-harness-ai
type: concept
---
# Harness — AI 代理基础设施框架

> **归档日期：** 2026-08-11
> **来源：** https://github.com/topics/harness
> **标签：** #AI代理 #代理基础设施 #AgentHarness #开源

## 项目信息

- **概念：** Agent Harness — 包裹 LLM 使其成为功能性代理的完整基础设施
- **核心仓库：**
  - [openai/openai-agents-python](https://github.com/openai/openai-agents-python) — 28.5k Stars
  - [thClaws/thClaws](https://github.com/thClaws/thClaws) — 1.2k Stars（Rust）
  - [HKUDS/OpenHarness](https://github.com/HKUDS/OpenHarness) — Python 实现
  - [strands-agents/harness-sdk](https://github.com/strands-agents/harness-sdk) — 6.9k Stars

## 是什么

Agent Harness 是一个**概念 + 技术框架**，定义包裹 LLM 使其成为功能性代理的完整基础设施：

> **Harness = Tools + Knowledge + Observation + Action + Permissions**

模型提供智能，Harness 提供双手、双眼、记忆和安全边界。

## 核心特性

### 1. 代理基础设施五要素
- **Tools（工具）：** 代理能执行的操作（API 调用、文件读写等）
- **Knowledge（知识）：** 代理能访问的信息（文档、记忆、上下文）
- **Observation（观察）：** 代理能感知的环境（屏幕、日志、状态）
- **Action（行动）：** 代理能改变环境的能力
- **Permissions（权限）：** 代理操作的安全边界

### 2. OpenHarness（港大实现）
- Python 实现，面向研究者和开发者
- 内置个人代理 Ohmo
- 支持飞书、Slack、Telegram、Discord
- 长会话助手，不是聊天机器人

### 3. thClaws（Rust 实现）
- 原生 Rust 实现
- 单一二进制输出 GUI、CLI、headless、WebApp
- 多提供商、MCP、技能、插件、代理团队

### 4. OpenAI Agents SDK
- 28.5k Stars，OpenAI 官方代理框架
- 定义代理的边界、工具、权限
- 与 OpenAI 模型深度集成

## 和我们有什么关系

### 与小6项目

Harness 是**代理基础设施层**，与小6项目的 AI 指挥中枢有直接关联：

| 维度 | Harness | 小6项目 |
|------|---------|---------|
| 定位 | 代理基础设施 | AI 智能指挥中枢 |
| 核心 | 工具+知识+观察+行动+权限 | 对话+能力模块+自主行动 |
| 层次 | 底层框架 | 上层应用 |

### 潜在应用场景

1. **小6项目的能力模块设计**
   - Harness 的五要素可作为小6能力模块的设计参考
   - 每个能力模块 = 一组工具 + 知识 + 权限

2. **Hermes 的代理架构**
   - Hermes 的技能和工具系统本质上就是一个 Harness
   - 可参考 Harness 的设计思路优化

3. **代理权限管理**
   - Harness 的 Permissions 概念可参考
   - 为小6项目设计代理操作的安全边界

### 局限性

- **概念性较强**：更多是设计理念，非完整产品
- **研究导向**：OpenHarness 面向学术研究
- **多实现分散**：没有统一的 Harness 标准

## 相关笔记

- 小6项目-AI智能指挥中枢 — 小6项目架构
- Multica-AI编码代理团队管理平台 — AI 代理团队管理
- Orca-并行AI编码代理编排器 — 并行代理编排器
- SmartAdmin-后台管理模板 — 后台管理模板
- HeyClicky-跨平台AI光标伴侣 — 跨平台 AI 光标伴侣
