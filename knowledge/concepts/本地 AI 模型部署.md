---
date: 2026-07-23
tags:
  - 本地 AI
  - 模型部署
  - 技能参考
id: know-ai-4
type: concept
---
# 本地 AI 模型部署

> 对应 Hermes 技能：`local-ai-model-setup`

## 概述

本地 AI 模型部署覆盖 macOS/Apple Silicon 上开源模型的安装、配置、推理全流程。

## 支持模型

### 1. 语音模型
- **ChatTTS**：文本转语音，支持音色克隆
- **Piper TTS**：轻量级本地 TTS
- **IndexTTS2**：高质量语音合成

### 2. 图像模型
- **ComfyUI + FLUX**：高质量文生图
- **ComfyUI + SDXL**：通用生图
- **Real-ESRGAN**：超分辨率放大

### 3. 视频模型
- **WAN 2.2**：图生视频
- **Agnes AI**：全模态 API

## 部署步骤

### 1. 环境准备
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install torch torchvision torchaudio
pip install -r requirements.txt
```

### 2. 模型下载
- 从 Hugging Face 下载模型权重
- 放置到指定目录（如 `models/`）
- 配置模型路径

### 3. 服务启动
```bash
# ComfyUI
python main.py --listen 0.0.0.0 --port 8188

# oMLX 本地 LLM 服务器
omlx serve --model llama-3-8b --port 8000
```

### 4. SSL 配置
- 生成自签名证书
- 配置局域网访问
- 设置防火墙规则

## 🔗 相关笔记
- [[本机系统资产全景盘点]]
- [[ComfyUI 本地文生图 + 视频生成]]
- [[Hermes Agent 自动化工作流]]