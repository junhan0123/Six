---
id: know-see-through-ai
type: concept
---
# See-Through - 动漫角色图层分解AI工具

## 项目概述

See-Through 是一个开源AI工具，将单张动漫插画自动分解为最多23层的分层PSD文件。每层都有完整修复（如头发拆开后露出的脸会自动补全）。

**论文：** See-through: Single-image Layer Decomposition for Anime Characters
**发表：** ACM SIGGRAPH 2026 Conference Papers（计算机图形学顶会）

## 核心功能

- 上传一张动漫角色图，AI自动分析深度和图层关系
- 分解为最多23个语义图层：头发、脸、眼睛、衣服、配饰、背景等
- 每层自动完整修复（透明层生成）
- 导出为分层PSD文件，可直接在Photoshop中编辑

## 技术架构

| 模型 | 用途 |
|------|------|
| LayerDiff 3D | 透明图层生成（基于SDXL） |
| Marigold Depth | 动漫伪深度估计（微调版） |
| SAM Body Parsing | 语义身体部位分割 |

## 系统要求

| 配置 | 显存需求 | 说明 |
|------|----------|------|
| 默认 | 12-16GB VRAM | bf16精度，1280分辨率 |
| Group Offload | ~10GB VRAM | 12GB GPU可用，速度降低1.5倍 |
| NF4量化 | ~8GB VRAM | 8GB GPU可用，质量接近全精度 |
| Block Swap | ~8GB VRAM | bf16精度，1280分辨率 |

## 安装方法

```bash
# 1. 创建环境
conda create -n see_through python=3.12 -y
conda activate see_through

# 2. 安装PyTorch (CUDA 12.8)
pip install torch==2.8.0+cu128 torchvision==0.23.0+cu128 torchaudio==2.8.0+cu128 \
  --index-url https://download.pytorch.org/whl/cu128

# 3. 安装依赖
pip install -r requirements.txt

# 4. 创建资源链接
ln -sf common/assets assets

# 5. 运行推理
python inference/scripts/inference_psd.py \
  --srcp assets/test_image.png \
  --save_to_psd
```

## 在线演示（免费）

| 平台 | 地址 | 说明 |
|------|------|------|
| ModelScope | 魔搭社区在线演示 | 中国大陆用户可用，完全免费 |
| HuggingFace | HuggingFace Space | 需注册，每天1-2次免费 |

## 项目信息

- **GitHub：** https://github.com/shitagaki-lab/see-through
- **Star：** 3.4k
- **Fork：** 311
- **License：** Apache-2.0
- **ComfyUI插件：** https://github.com/jtydhr88/ComfyUI-See-through

## 注意事项

- 官方声明：这是开源研究项目，没有付费服务。如果有人收费，与他们无关。
- 需要GPU运行，8GB显存以上即可。
- 中国大陆用户推荐使用ModelScope在线演示。

## 🔗 相关笔记

- [[ComfyUI 本地文生图 + 视频生成]]
- FLUX 像素游戏素材生成完整工作流
- Agnes AI 生成游戏 sprite 素材全流程
