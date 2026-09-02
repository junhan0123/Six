---
date: 2026-07-23
tags:
  - ComfyUI
  - 文生图
  - 视频生成
  - 技能参考
id: know-comfyui
type: concept
---
# ComfyUI 本地文生图 + 视频生成

> 对应 Hermes 技能：`comfyui-image-gen`

## 概述

ComfyUI 本地文生图 + 视频生成覆盖 macOS 启动、FLUX/SDXL 模型调用、WAN 2.2 视频生成等核心功能。

## 环境配置

### 1. ComfyUI 安装
```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt
```

### 2. 模型管理
- FLUX 1.0：高质量文生图
- SDXL 1.0：通用生图
- WAN 2.2：图生视频

### 3. macOS 优化
- MPS 加速启用
- 内存管理配置
- 显存优化参数

## 常用工作流

### 文生图
1. 输入提示词
2. 选择模型（FLUX/SDXL）
3. 设置采样器、步数、CFG
4. 生成图片
5. 高清修复（可选）

### 图生视频
1. 输入底图
2. 选择视频模型（WAN 2.2）
3. 设置时长、帧率
4. 生成视频
5. 后处理（配音、剪辑）

## 🔗 相关笔记
- [[AI 视频生成管线设计与质量优化]]
- [[FFmpeg 视频制作管线]]
- [[本机系统资产全景盘点]]