---
id: know-openhands-ai
type: concept
---
# OpenHands 开源 AI 代码代理

## 项目概述

OpenHands 是一个开源 AI 代码代理，定位为 Devin/Cursor 的开源替代方案。它通过 Agent Canvas 进行任务拆解与可视化编排，底层通过 SWE-agent 衍生技术实现沙箱内代码执行与反馈循环，支持本地 Ollama 或云端 Bedrock 模型路由。

## 核心能力

- **Agent Canvas**：任务拆解与可视化编排
- **沙箱执行**：隔离环境内代码执行与反馈循环
- **多模型支持**：Ollama（本地）、OpenRouter、Bedrock 等
- **V1 SDK**：2025 年 11 月发布，从 V0 单体架构重构为模块化 SDK
- **自托管**：支持完全本地部署，无需云端服务

## 本地部署方式

### 1. Docker Compose（推荐）

```bash
git clone https://github.com/OpenHands/OpenHands.git
cd OpenHands
cp .env.template .env
docker compose up
```

- 一键启动，自动创建沙箱环境
- 默认占用约 2-4GB 内存
- 适合快速体验

### 2. 本地源码部署

```bash
pip install -e .
# 或
uv sync
```

- 需要 Python 3.12+
- 适合二次开发、修改源码
- 资源占用更低（无 Docker 开销）

### 3. 本地模型部署（Ollama）

```bash
# 先安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b

# 然后在 .env 中配置
LLM_BASE_URL=http://localhost:11434
LLM_API_KEY=***
LLM_MODEL=ollama/llama3.1:8b
```

- 完全离线，无需 API Key
- 需要 8GB+ 内存（8B 模型）
- 代码生成能力比云端模型弱一些

## 资源门槛

| 场景 | 内存 | CPU |
|------|------|-----|
| 最低（体验级） | 4GB | 2 核 |
| 推荐（正常使用） | 8GB | 4 核 |
| 本地模型（8B） | 8GB+ | - |
| 本地模型（13B） | 16GB+ | - |

## 与现有管线的集成潜力

OpenHands 与我们的 Python/FFmpeg/ComfyUI 管线形成互补关系：

- **OpenHands** 负责代码生成、任务规划、代理执行
- **ComfyUI** 负责图像/视频素材生成
- **FFmpeg** 负责视频剪辑合成
- **IndexTTS** 负责语音合成

OpenHands 可以作为"大脑"调度其他工具，实现更高级的自动化。

## 参考链接

- GitHub: https://github.com/OpenHands/OpenHands
- 官网: https://www.openhands.dev
- 自托管指南: 见项目文档

## 调研时间

2026-07-21

## 🔗 相关笔记
- [[本机系统资产全景盘点]]
- [[开源自动剪辑项目调研]]
- [[Pixelle-Video AI 全自动短视频引擎]]

- [[ComfyUI 本地文生图 + 视频生成]]
- [[FFmpeg 视频制作管线]]
- IndexTTS 本地语音合成
- [[AI 工具调研方法论]]
