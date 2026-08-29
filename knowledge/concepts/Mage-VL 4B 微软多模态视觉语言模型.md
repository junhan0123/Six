---
id: know-mage-vl-4b
type: concept
---
# Mage-VL 4B — 微软多模态视觉语言模型

## 📌 项目概述

**Mage-VL** 是微软开源的 4B 参数多模态视觉语言模型（VLM），支持**图片理解 + 视频分析**二合一。基于 Qwen3-4B 文本骨干 + 自研 Mage-ViT 视觉编码器，采用 Codec-ViT 架构。Apache-2.0 协议。

### 基本信息

- **原仓**: [microsoft/Mage-VL](https://huggingface.co/microsoft/Mage-VL) (HuggingFace)
- **MLX Python 端口**: [rsravanreddy/Mage-VL-MLX](https://github.com/rsravanreddy/Mage-VL-MLX) (Apache-2.0)
- **MLX Swift 端口**: [xocialize/mage-vl-swift](https://github.com/xocialize/mage-vl-swift) (Apache-2.0)
- **参数量**: 4B（文本）+ 1B（视觉）≈ 5B 总参
- **许可证**: Apache-2.0（可商用）

## 🏗️ 架构

### 文本骨干
- Qwen3-4B（纯 1D 位置编码，无需 3D M-RoPE）
- 可直接复用 mlx-vlm 的 qwen3 实现

### 视觉编码器
- **Mage-ViT**（Codec-ViT）：从零训练的视觉编码器
- Conv2d patch-embed（kernel=stride=16）
- 3D RoPE 4:6:6（t,h,w 方向）
- 块对角注意力（4 帧窗口）
- 2 层 MLP merger（2×2 patch 块融合到 2560-dim 文本空间）

### 流式事件门控（streammind_gate）
- 核心创新：主动式、事件门控的流式推理
- 架构：PreNet → Mamba-1 SSM → PostNet → 4 层 Qwen3 分类器
- 每帧输出 silent/speak 分数
- 视频分析时只在事件发生时生成描述

## ⚡ 性能数据

### Apple Silicon（M4, 16GB, 4-bit）

| 量化 | 权重大小 | 文本解码 | 图片解码 | 图片预填充 | 峰值内存 |
|------|---------|---------|---------|-----------|---------|
| 4-bit | 3.1 GB | 33.5 tok/s | **30.6 tok/s** | 167 tok/s | **4.65 GB** |
| 8-bit | 5.0 GB | 19.8 tok/s | 19.1 tok/s | 184 tok/s | 6.55 GB |

### Apple Silicon（M5 Max, int8）

| 模式 | 补丁数 | 视觉 token | 基线内存 | 峰值内存 | 解码速度 |
|------|--------|-----------|---------|---------|---------|
| 图片 | 8,192 | 2,048 | 5.00 GB | 8.01 GB | **85.7 tok/s** |
| 视频 16 帧 | 16,128 | 4,032 | 5.00 GB | 10.80 GB | 80.0 tok/s |
| 视频 32 帧 | 15,360 | 3,840 | 5.00 GB | 10.58 GB | 82.7 tok/s |

**MLX-Swift 端口性能碾压 Python 端口**（85.7 vs 30.6 tok/s），因为 Swift 直接调用 MLX Metal 后端，无 Python 开销。

## 📦 MLX 端口对比

| 特性 | MLX Python | MLX Swift |
|------|-----------|-----------|
| 语言 | Python | Swift |
| 图片解码 | 30.6 tok/s | **85.7 tok/s** |
| 视频解码 | 11.2 tok/s | **80.0 tok/s** |
| 内存（int8） | 6.55 GB | 5.00 GB 基线 |
| Token 对齐 | 未验证 | **48/48 与 PyTorch 完全一致** |
| 视频事件门控 | ✅ 已移植 | ❌ 未实现（Mamba-1 SSM 不在 MLX-Swift） |
| Codec 视频 | 部分支持 | 未实现 |
| 适用场景 | 研究/验证 | 生产/集成 |

## 🔧 安装（Python 版）

```bash
uv venv .venv && uv pip install --python .venv/bin/python mlx mlx-lm mlx-vlm safetensors pillow numpy av

# 注册到 mlx-vlm 模型注册表
ln -sf "$PWD/mage_vl" .venv/lib/python3.12/site-packages/mlx_vlm/models/mage_vl

# 下载权重 + 转换
cd reference && git lfs pull && cd ..
python scripts/convert.py --hf-path reference --out mage-vl-mlx-4bit --bits 4

# 推理
python scripts/generate.py --mlx mage-vl-mlx-4bit \
    --image dog.jpg --prompt "What animal is this?"
```

## 🎯 关键特性

1. **Codec-ViT 视觉编码器**：从零训练，非微调 SigLIP/Qwen2-VL
2. **流式事件门控**：视频分析时只在事件发生时生成描述，大幅节省计算
3. **图片 + 视频统一架构**：模型层面视频就是图片序列，时间通过文本标签携带
4. **低内存占用**：4-bit 量化后仅 3.1GB，16GB Mac 可流畅运行
5. **全开源**：代码 + 权重均为 Apache-2.0

## 🤔 和我们有什么关系

### 直接有用

1. **本地图片/视频理解**
   - 16GB Mac 可跑 4-bit 量化版
   - 图片理解 30 tok/s，视频分析 11 tok/s
   - 可用于内容审核、图片描述、视频摘要

2. **小红书配图质量评估**
   - 本地运行 Mage-VL 自动评估配图质量
   - 替代 Agnes AI 502 时的降级方案

3. **小6项目多模态能力**
   - 如果小6需要图片/视频理解能力，Mage-VL 是低资源占用的好选择
   - 比 Qwen2-VL 7B 更轻量（4B vs 7B）

### 注意事项
- MLX 端口生态还不成熟（2026-07 刚创建）
- Swift 端口缺少事件门控功能
- Python 端口性能一般（30 tok/s），适合理解不适合实时
- 需要下载 ~3GB 权重文件
