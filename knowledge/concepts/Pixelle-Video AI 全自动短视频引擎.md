---
id: know-pixelle-video-ai
type: concept
---
# Pixelle-Video AI 全自动短视频引擎

## 项目概述

Pixelle-Video 是一个开源 AI 全自动短视频引擎，2025 年 11 月上线后迅速走红，目前星标 2.5 万+，是 AI 视频生成领域的热门项目。

## 核心信息

| 项目 | 信息 |
|------|------|
| 仓库 | ATH-MaaS/Pixelle-Video |
| 描述 | AI Fully Automated Short Video Engine |
| 语言 | Python |
| 许可证 | Apache 2.0（可商用） |
| 星标 | 25,779 |
| 创建时间 | 2025 年 11 月 7 日 |
| 最近更新 | 2026 年 7 月 20 日 |
| 项目大小 | 28.8MB |

## 技术栈

从项目主题标签分析：

- **ComfyUI** — 图像生成（SDXL/FLUX 等）
- **TTS** — 语音合成（Edge TTS/CosyVoice 等）
- **视频生成** — 文生视频/图生视频（WAN/AnyText 等）
- **AIGC** — 全流程自动化

## 核心功能

1. **一键生成**：输入主题/文案，自动生成完整短视频
2. **文生图**：基于 ComfyUI 的图像生成管线
3. **TTS 配音**：语音合成模块
4. **视频生成**：文生视频/图生视频
5. **剪辑合成**：自动剪辑、字幕、配音合成

## 与现有管线的对比

| 维度 | Pixelle-Video | 现有管线 |
|------|---------------|----------|
| 复杂度 | 一键自动化 | 手动串联 |
| 灵活性 | 较低（固定流程） | 高（可定制每个环节） |
| 部署难度 | 中（Python 项目） | 高（多工具独立部署） |
| 可控性 | 较低 | 高 |
| 适合场景 | 快速出片 | 精细控制 |

## 衍生项目

- **Pixelle-Video-HappyHorse**：基于 DashScope 云端文生视频，无需 GPU
- **Pixelle-Video-VI**：越南语版本
- **pixelle-video-auto-engine**：部署版

## 评估

### 优势
- 开箱即用，自动化程度高
- Apache 2.0 许可证，可商用
- 社区活跃，更新频繁
- 整合了 ComfyUI/TTS/视频生成全流程

### 劣势
- 灵活性不如独立工具串联
- 对 GPU 可能有较高要求
- 黑盒化，难以深度定制

### 适用场景
- 快速批量生产短视频
- 新手入门 AI 视频生成
- 作为现有管线的补充或替代

## 参考链接

- GitHub: https://github.com/ATH-MaaS/Pixelle-Video
- HappyHorse 分支: https://github.com/Loklokguo/Pixelle-Video-HappyHorse

## 调研时间

2026-07-21

## 🔗 相关笔记
- [[本机系统资产全景盘点]]
- [[开源自动剪辑项目调研]]
- [[OpenHands 开源 AI 代码代理]]

- [[ComfyUI 本地文生图 + 视频生成]]
- [[FFmpeg 视频制作管线]]
- IndexTTS 本地语音合成
- [[AI 视频生成管线设计与质量优化]]
- [[AI 工具调研方法论]]
