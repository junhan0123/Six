---
id: know-gpt-sovits-tts
type: concept
---
# GPT-SoVITS — 少样本语音克隆 TTS

> **归档日期：** 2026-08-11
> **来源：** https://github.com/RVC-Boss/GPT-SoVITS
> **标签：** #语音合成 #声音克隆 #TTS #开源 #AI

## 项目信息

- **仓库：** [RVC-Boss/GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)
- **定位：** 少样本语音克隆 TTS 系统
- **核心能力：** 1 分钟语音数据即可训练高质量语音模型
- **特点：** 零样本语音合成、多说话人、情感控制

## 是什么

GPT-SoVITS 是一个开源的语音合成（TTS）系统，支持少样本声音克隆。只需约 1 分钟的参考语音，就能生成目标说话人的高质量语音。

## 核心特性

### 1. 语音克隆
- **少样本训练**：1 分钟参考语音即可训练
- **零样本合成**：无需训练，直接克隆
- **多说话人支持**：一个模型支持多个说话人

### 2. 技术架构
- **GPT 阶段**：将语义 token 转换为声学特征
- **SoVITS 阶段**：将声学特征转换为高质量梅尔谱图
- **Vocoder**：将梅尔谱图转换为波形

### 3. 支持的格式
- 中文、英文、日语
- 多说话人混合
- 情感控制

## 和我们有什么关系

### 与 Hermes 的对比

| 特性 | Hermes TTS | GPT-SoVITS |
|------|-----------|-----------|
| 方案 | Edge TTS / ChatTTS / CosyVoice | 本地声音克隆 |
| 音色 | 固定（Edge 女声、CosyVoice 预设） | 自定义（用户自己的声音） |
| 速度 | 快（云端/轻量本地） | 慢（需要训练/推理） |
| 质量 | 好 | 极好（克隆真实声音） |
| 资源 | 低 | 高（GPU 推荐） |

### 潜在应用场景

1. **小6项目 - 个性化语音**
   - 老板想要"自己的声音"做播报
   - GPT-SoVITS 可以克隆老板的声音

2. **Hermes 语音增强**
   - 当前 Edge TTS 音色固定
   - GPT-SoVITS 提供自定义音色方案

3. **视频配音**
   - 需要特定声音的视频内容
   - 克隆特定说话人

### 集成建议

```bash
# 安装（推荐 conda 环境）
conda create -n GPTSoVits python=3.9
conda activate GPTSoVits
pip install -r requirements.txt

# 使用 WebUI
python GPT_SoVITS/inference_webui.py
```

### 限制

- **需要 GPU**：推理速度较慢，推荐 NVIDIA GPU
- **macOS 支持有限**：主要支持 Windows + CUDA
- **资源占用高**：训练和推理都需要较多内存和显存
- **与 Hermes 集成复杂**：需要独立服务，通过 API 调用

## 相关笔记

- ChatTTS-本地配音全流程 — ChatTTS 使用方法
- CosyVoice-本地TTS部署 — CosyVoice 部署方法
- Edge TTS-免费语音合成 — Edge TTS 使用方法
- Hermes TTS 工具 — Hermes 内置 TTS 功能
