---
id: know-heyclicky-ai
type: concept
---
# HeyClicky — 跨平台 AI 光标伴侣

> **归档日期：** 2026-08-11
> **来源：** https://github.com/topics/heyclicky
> **标签：** #AI伴侣 #光标助手 #跨平台 #Rust #Tauri

## 项目信息

- **仓库：** [farzaa/clicky](https://github.com/farzaa/clicky)（原始 macOS 版）
- **跨平台版：** [heyclicky](https://github.com/topics/heyclicky)
- **技术栈：** Rust + Tauri
- **平台：** Windows、Linux、macOS

## 是什么

HeyClicky 是 OpenClicky 的跨平台 AI 伴侣移植版。它是一个**生活在光标旁边的 AI 小助手**，可以：

- 看到你的屏幕内容
- 和你对话（语音）
- 在屏幕上指向按钮、绘制箭头
- 本地运行，无需 API Key

## 核心特性

### 1. 光标伴侣
- AI 助手跟随光标移动
- 按住快捷键提问，关于当前屏幕内容
- 语音回答，指向屏幕元素

### 2. 跨平台
- 原始 Clicky 是 macOS Swift 应用
- HeyClicky 用 Rust + Tauri 移植到 Windows、Linux、macOS
- Flicky 是用 Electron 重写的另一个跨平台版本

### 3. 本地优先
- 支持 Ollama 本地模型
- 无需 API Key
- 本地配置，密钥加密存储

### 4. 技术栈
- **语言：** Rust
- **框架：** Tauri（跨平台桌面）
- **AI：** OpenAI、Anthropic、Ollama
- **语音：** Whisper、ElevenLabs

## 和我们有什么关系

### 与小6项目

HeyClicky 是**桌面级 AI 伴侣**，与小6项目的 AI 指挥中枢定位不同：

| 维度 | HeyClicky | 小6项目 |
|------|-----------|---------|
| 定位 | 光标旁的小助手 | AI 智能指挥中枢 |
| 交互 | 语音 + 屏幕感知 | 对话 + 能力模块 |
| 范围 | 当前屏幕内容 | 多系统、多任务 |
| 技术 | Rust + Tauri | Vue3/React + Python |

### 潜在应用场景

1. **小6项目的桌面集成**
   - HeyClicky 的光标伴侣交互模式可参考
   - 屏幕感知 + 语音交互思路

2. **Hermes 的桌面扩展**
   - 如果 Hermes 需要桌面伴侣，可参考 HeyClicky 的架构
   - Tauri + Rust 是轻量级桌面方案

### 局限性

- **桌面应用**：不是 Web 服务，与小6的 Web 架构不匹配
- **单屏幕感知**：功能范围有限
- **Rust 技术栈**：与小6的 Python 后端不匹配

## 相关笔记

- 小6项目-AI智能指挥中枢 — 小6项目架构
- Multica-AI编码代理团队管理平台 — AI 代理团队管理
- Orca-并行AI编码代理编排器 — 并行代理编排器
- SmartAdmin-后台管理模板 — 后台管理模板
