---
id: know-muse-maskgit
type: concept
---
# Muse (MaskGIT) — 文生图模型

## 基本信息

- **论文**：*Muse: Text-To-Image Generation via Masked Generative Transformers*
- **作者**：Google Research（Huiwen Chang, Han Zhang, William T. Freeman 等）
- **发表**：2023 年
- **GitHub 实现**：lucidrains/muse-maskgit-pytorch
- **Stars**：918 · Forks：86
- **License**：MIT
- **语言**：Python
- **最新 Release**：v0.3.5（2024-02-27）
- **项目地址**：https://github.com/lucidrains/muse-maskgit-pytorch

## 核心思路

Muse 用 **掩码生成 Transformer（MaskGIT）** 做文生图，不是扩散模型那一套。

**关键区别**：
- 扩散模型：从纯噪声一步步去噪 → 生成图像（迭代次数多）
- Muse/MaskGIT：从全掩码 token 开始，逐步预测并替换未掩码位置的 token → 更快收敛

## 架构详解

Muse 是**两级生成**架构：

### 第一级：基础生成（Base MaskGIT）

1. **训练 VQGan VAE**
   - 把图片压缩成离散 token（codebook）
   - 例如：codebook_size = 65536（2^16，每个像素位置用 16 bit 编码）
   - 把 256×256 图像压缩为 16×16 = 256 个 token 序列

2. **训练 MaskGit Transformer**
   - Transformer 输入：文本（T5 编码）+ 掩码图像 token
   - 输出：预测每个位置的 token
   - 逐步迭代：每次预测一部分未掩码位置，直到全部生成
   - 使用 classifier-free guidance（条件缩放 cond_scale = 3.0）

### 第二级：超分辨率（Super-Res MaskGIT）

1. 以第一级生成的 256×256 图为条件
2. 生成 512×512 高分辨率图像
3. 需要设置 `cond_image_size = 256`（低分辨率条件图尺寸）

## 关键参数

| 参数 | 说明 | 典型值 |
|------|------|--------|
| `dim` | 模型维度 | 512 |
| `depth` | Transformer 层数 | 8 |
| `dim_head` | 注意力头维度 | 64 |
| `heads` | 注意力头数 | 8 |
| `ff_mult` | FFN 扩展倍数 | 4 |
| `num_tokens` | 码本大小（必须与 VAE 一致） | 65536 |
| `seq_len` | 序列长度 | 256（256×256）/ 1024（512×512） |
| `t5_name` | 文本编码器 | t5-small / t5-base / t5-large |
| `cond_drop_prob` | 条件丢弃概率（classifier-free guidance） | 0.25 |
| `cond_scale` | 条件缩放强度（推理时） | 3.0 |

## 训练流程

```
1. 训练 VQGan VAE
   └─ 输入：大量图片
   └─ 输出：VAE 权重（.pt 文件）

2. 训练 Base MaskGIT
   └─ 输入：文本 + 图片配对数据
   └─ 用 VAE 把图片编码为 token
   └─ 训练 Transformer 从文本预测 token
   └─ 输出：base.pt

3. 训练 Super-Res MaskGIT
   └─ 输入：低分辨率图 + 文本 + 高分辨率图
   └─ 以 base 生成的图为条件
   └─ 输出：superres.pt

4. 组合
   └─ Muse(base=base_maskgit, superres=superres_maskgit)
   └─ 输入文本 → 直接输出高分辨率图像
```

## 使用示例

```python
from muse_maskgit_pytorch import Muse

base_maskgit.load('./path/to/base.pt')
superres_maskgit.load('./path/to/superres.pt')

muse = Muse(base=base_maskgit, superres=superres_maskgit)

images = muse([
    'a whale breaching from afar',
    'young girl blowing out candles on her birthday cake',
    'fireworks with blue and green sparkles'
])
# 返回 List[PIL.Image.Image]
```

## 优势

1. **推理速度快**：迭代次数远少于扩散模型（通常 10-20 步 vs 50-1000 步）
2. **并行生成**：每次迭代可以并行预测多个 token 位置
3. **自回归 + 掩码结合**：兼顾序列建模能力和生成效率
4. **灵活的条件控制**：支持文本条件、图像条件（超分）、多模态条件

## 局限

1. **训练门槛高**：需要大量图文配对数据 + GPU 资源
2. **质量不及 SOTA**：2023 年论文发表时，DALL-E 2/Imagen 等扩散模型质量更高
3. **依赖 VAE 质量**：VAE 的码本大小和重建质量直接影响最终效果
4. **社区实现较少**：lucidrains 的 PyTorch 实现是主流，但预训练权重不公开
5. **后续被扩散模型超越**：2024 年后，SD3、FLUX 等扩散模型在质量和速度上双杀

## 与扩散模型对比

| 维度 | Muse (MaskGIT) | 扩散模型 (SD/Imagen) |
|------|---------------|---------------------|
| 生成方式 | 掩码 token 逐步预测 | 噪声逐步去噪 |
| 推理速度 | 快（10-20 步） | 慢（50-1000 步） |
| 生成质量（2023） | 中等 | 高 |
| 训练数据 | 图文配对 | 大规模图文配对 |
| 社区生态 | 较小 | 极大（SD 生态成熟） |
| 预训练权重 | 不公开 | 大量开源 |
| 当前状态 | 研究导向 | 工业级应用 |

## 实际价值

**学术研究价值高**：
- 展示了掩码生成 Transformer 在图像生成的可行性
- 为后续研究（如 MaskGIT 改进、多模态生成）提供了基础

**实际落地价值有限**：
- 没有公开预训练权重，难以复现
- 扩散模型生态更成熟，SD/FLUX 等已经覆盖了大部分应用场景
- lucidrains 的实现主要用于学习和研究，不是生产级工具

## 相关笔记

- AI 文生图模型对比
- ComfyUI 工作流
- FLUX 文生图
