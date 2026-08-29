---
created: 2026-08-03
tags:
  - AI/模型
  - 计算机视觉
  - 目标检测
  - NVIDIA
id: know-locateanything-nvidia
type: concept
---
# LocateAnything - NVIDIA 视觉语言目标检测模型

## 简介

**LocateAnything** 是 NVIDIA 开源的视觉语言模型（VLM），专注于**视觉定位**和**目标检测**。它能让 AI 系统精确地找到图片中的物体、UI 元素、文字等，并返回边界框坐标。

**核心定位**：告别 YOLO，用自然语言描述找到目标。

## 核心能力

1. **目标定位** — 输入图片和文字描述，返回边界框坐标
2. **密集检测** — 一次检测多个物体
3. **点定位** — 找到目标内的精确点
4. **GUI 理解** — 识别界面元素
5. **OCR 文字定位** — 找到图片中的文字位置
6. **开放词汇检测** — 不限于预定义类别

## 模型信息

| 项目 | 详情 |
|------|------|
| 模型名 | LocateAnything-3B |
| 参数量 | 30 亿 |
| 训练数据 | 1200 万张图片，1.38 亿个查询，7.85 亿个边界框 |
| 论文 | [arXiv:2605.27365](https://arxiv.org/abs/2605.27365) |
| 论文链接 | [NVIDIA 实验室](https://research.nvidia.com/labs/lpr/locate-anything) |
| HuggingFace | [nvidia/LocateAnything-3B](https://huggingface.co/nvidia/LocateAnything-3B) |

## 数据集规模

训练数据集涵盖 6 大领域：
- 自然场景（66.9% 查询）
- 机器人操作
- 自动驾驶
- GUI 交互
- 文档理解
- 其他领域

## 技术亮点

- **并行框解码（PBD）** — 将边界框和点作为原子单元一次性解码，保持框内几何一致性
- **无需 GPU** — C++ 推理版本可在 CPU 上运行
- **开放词汇** — 不限于预定义类别，用自然语言描述即可
- **多模态 Agent 基础** — 已集成到 NVIDIA Nemotron 3 Nano Omni 等生产级 VLM 中

## 部署方案

### 1. 官方 PyTorch 实现
```bash
pip install locate-anything
```

### 2. locate-anything.cpp（C++ 推理）
- GitHub：[mudler/locate-anything.cpp](https://github.com/mudler/locate-anything.cpp)
- 基于 ggml 构建，C++17 实现
- 无需 Python 运行时
- 支持 CPU 和 GPU 推理
- 由 LocalAI 团队开发

### 3. GGUF 量化版本
- HuggingFace：[mudler/locate-anything.cpp-gguf](https://huggingface.co/mudler/locate-anything.cpp-gguf)
- 量化后可在 Mac Studio 上运行

### 4. LocalAI 集成
- LocalAI 已原生支持 LocateAnything
- 安装 LocalAI 后即可使用

## 与 YOLO 对比

| 特性 | YOLO | LocateAnything |
|------|------|----------------|
| 检测类别 | 预定义（80 类） | 开放词汇 |
| 输入方式 | 纯图像 | 图像 + 文字描述 |
| 精度 | 高 | 更高（VLM 基础） |
| 灵活性 | 低 | 高（自然语言描述） |
| 参数量 | 小（0.5-60M） | 大（3B） |
| 推理速度 | 快 | 中等 |

## 适用场景

- **图片标注** — 自动标注大量图片
- **GUI 自动化** — 识别界面元素，驱动 UI 操作
- **机器人视觉** — 空间理解和物体定位
- **内容审核** — 检测图片中的特定内容
- **文档理解** — 定位文档中的关键信息

## 与我们的关系

- Mac Studio M4 Max 64GB 可以运行（GGUF 量化版）
- 可用于游戏开发中的自动标注
- 可用于 UI 自动化测试
- 可与小6 Agent 集成，增强视觉理解能力

## 🔗 相关笔记
- 小6项目 - 能力模块系统
- ComfyUI 本地文生图
- AGENTS.md
