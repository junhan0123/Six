---
tags:
  - ai-agent
  - gui
  - electron
  - typescript
  - github
created: 2026-07-27
source: https://github.com/bytedance/UI-TARS-desktop
license: Apache-2.0
stars: 38304
id: know-ui-tars-desktop
type: concept
---
# UI-TARS-desktop

## 项目简介

字节跳动开源的**多模态 AI Agent 栈**，包含两个核心项目：
- **Agent TARS**：底层 Agent 框架
- **UI-TARS Desktop**：桌面端 GUI Agent 应用

> 用视觉语言模型理解并操作图形界面。

## 核心能力

1. **GUI Agent**：理解并操作图形界面
2. **Browser Use**：浏览器自动化操作
3. **MCP Server**：支持 Model Context Protocol
4. **VLM 视觉理解**：基于视觉语言模型的界面理解

## 技术栈

- TypeScript
- Electron（桌面应用框架）
- VLM（视觉语言模型）

## 安装方式

```bash
# 需要 Node.js 环境
# 具体安装步骤见官方文档
git clone https://github.com/bytedance/UI-TARS-desktop.git
cd UI-TARS-desktop
npm install
npm run dev
```

## 项目指标

| 指标 | 数值 |
|------|------|
| Stars | 38,304 |
| Forks | 3,853 |
| 语言 | TypeScript |
| License | Apache-2.0 |

## 与 CLI-Anything 的互补关系

| 维度 | UI-TARS-desktop | CLI-Anything |
|------|-----------------|--------------|
| 定位 | GUI Agent / 桌面应用 | CLI Agent / 软件原生化 |
| 擅长 | 图形界面操作、浏览器自动化 | 命令行工具增强、软件 Agent 化 |
| 技术栈 | Electron + VLM | Python + CLI-Hub |

## 相关链接

- GitHub: [[UI-TARS-desktop]]
- 与 CLI-Anything 对比: [[CLI-Anything]]

---
*归档时间：2026-07-27*
