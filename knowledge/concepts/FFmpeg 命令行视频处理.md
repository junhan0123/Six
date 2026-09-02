---
date: 2026-07-23
tags:
  - FFmpeg
  - 视频处理
  - 命令行
  - 技能参考
id: know-ffmpeg
type: concept
---
# FFmpeg 命令行视频处理

> 对应 Hermes 技能：`ffmpeg-video-production`

## 概述

FFmpeg 命令行视频处理是一套基于 FFmpeg 的视频处理工作流，覆盖背景图生成、配音合成、视频合成等环节。

## 核心命令

### 1. 视频合成
```bash
ffmpeg -loop 1 -i bg.png -i audio.mp3 -t 10 -c:v libx264 -c:a aac output.mp4
```

### 2. 格式转换
```bash
ffmpeg -i input.mp4 -c:v libx264 -crf 23 output.mp4
```

### 3. 分辨率调整
```bash
ffmpeg -i input.mp4 -vf "scale=1920:1080" output.mp4
```

### 4. 音频提取
```bash
ffmpeg -i video.mp4 -vn -acodec copy audio.aac
```

## 视频制作管线

1. **Pillow 生成背景图**：创建静态背景
2. **Edge TTS 配音**：生成音频文件
3. **FFmpeg 合成**：背景图 + 音频 + 转场效果
4. **输出**：根据平台要求调整编码参数

## 🔗 相关笔记
- [[AI 视频生成管线设计与质量优化]]
- [[开源自动剪辑项目调研]]
- [[本机系统资产全景盘点]]