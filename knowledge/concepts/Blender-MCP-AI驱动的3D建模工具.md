---
id: know-blender-mcp-ai-3d
type: concept
---
# Blender MCP — AI 驱动的 3D 建模工具

> **归档日期：** 2026-08-11
> **来源：** https://github.com/ahujasid/blender-mcp
> **标签：** #Blender #MCP #3D建模 #AI代理 #Python

## 项目信息

- **主要仓库：** [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp)（开源，支持任意 LLM）
- **Blender 官方实验室：** [Blender MCP Server](https://www.blender.org/lab/mcp-server)
- **其他实现：** [djeada/blender-mcp-server](https://github.com/djeada/blender-mcp-server)（27 工具，7 命名空间）
- **技术栈：** Blender Python + Node.js MCP Server + WebSocket

## 是什么

Blender MCP 是一个 **Model Context Protocol (MCP) 服务器**，让 AI 助手（Claude、Cursor、Gemini 等）通过自然语言直接控制 Blender 进行 3D 建模。

## 核心功能

### 1. 对象操作
- 创建、移动、缩放、删除 3D 对象
- 通过自然语言指令操作场景

### 2. 材质控制
- 应用、修改、生成材质和颜色
- 支持程序化材质生成

### 3. 场景检查
- 获取完整场景状态（对象、灯光、相机）
- 场景摘要、对象摘要

### 4. 视口截图
- AI 能看到 Blender 视口画面
- 双向通信：AI 看场景 → 场景被 AI 修改

### 5. Python 脚本执行
- 同步执行 Python 脚本
- 异步执行长脚本（返回 job_id）
- 查询任务状态、取消任务

### 6. 渲染与导出
- 渲染图像
- 导出场景

## 技术架构

```
AI 助手 (Claude/Cursor/Gemini)
       ↕ MCP 协议
Blender MCP Server (Node.js)
       ↕ WebSocket
Blender 插件 (Python)
       ↕
Blender 3D 场景
```

## 安装方式

### 方式 1：uvx（推荐）
```bash
uvx blender-mcp --python 3.11
```

### 方式 2：pipx
```bash
pipx install blender-mcp
pipx ensurepath
```

### Claude Desktop 配置
```json
{
  "mcpServers": {
    "blender": {
      "command": "uvx",
      "args": ["blender-mcp"]
    }
  }
}
```

### Cursor 配置
1. Blender 中安装插件（Preferences → Add-ons → Install）
2. 3D 视图侧边栏（N 键）找到 BlenderMCP 标签
3. 点击 Connect
4. Cursor 中配置 MCP Server

## 支持的 AI 客户端

- Claude Desktop（原生 MCP 支持）
- Claude Code CLI
- Cursor AI
- VS Code（通过 Cline/Roo Code）
- Google Gemini CLI
- Ollama（本地模型）

## 和我们有什么关系

### 与小6项目

Blender MCP 是**3D 建模 AI 代理**，与小6项目定位不同：

| 维度 | Blender MCP | 小6项目 |
|------|-------------|---------|
| 定位 | 3D 建模工具 | AI 智能指挥中枢 |
| 交互 | 自然语言 → 3D 场景 | 对话 → 能力模块 |
| 技术 | Blender Python + MCP | Vue3/React + Python |
| 用途 | 3D 内容生成 | 多系统管理 |

### 潜在应用场景

1. **小6项目的 3D 可视化**
   - 小6项目如果需要 3D 场景展示（如游戏预览），可集成 Blender MCP
   - AI 自动生成 3D 资产

2. **Hermes 的 3D 能力扩展**
   - Hermes 通过 MCP 协议连接 Blender
   - 自然语言生成 3D 模型

3. **MCP 协议参考**
   - Blender MCP 的架构可作为 Hermes 接入其他工具的参考
   - WebSocket 桥接模式

### 局限性

- **3D 专用**：功能范围有限，非通用平台
- **Blender 依赖**：需要安装 Blender
- **MCP 协议**：需要额外的协议层

## 相关笔记

- 小6项目-AI智能指挥中枢 — 小6项目架构
- Multica-AI编码代理团队管理平台 — AI 代理团队管理
- Orca-并行AI编码代理编排器 — 并行代理编排器
- Harness-AI代理基础设施框架 — AI 代理基础设施框架
