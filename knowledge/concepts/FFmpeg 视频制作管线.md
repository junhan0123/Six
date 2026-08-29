---
date: 2026-07-23
tags:
  - FFmpeg
  - 视频制作
  - 管线
  - 技能参考
id: know-ffmpeg-2
type: concept
---
# FFmpeg 视频制作管线

> 对应 Hermes 技能：`ffmpeg-video-production`

## 概述

FFmpeg 视频制作管线是一套完整的视频制作工作流，覆盖背景图生成、配音合成、视频合成、字幕叠加等环节。

## 管线架构

```
Pillow 生成背景图 → Edge TTS 配音 → FFmpeg 合成 → 字幕叠加 → 输出
```

## 核心步骤

### 1. 背景图生成
```python
from PIL import Image, ImageDraw, ImageFont
# 创建指定分辨率背景
# 添加文字、图形元素
```

### 2. 配音合成
```bash
edge-tts --text "配音内容" --voice zh-CN-XiaoxiaoNeural --write-media audio.mp3
```

### 3. FFmpeg 合成
```bash
ffmpeg -loop 1 -i bg.png -i audio.mp3 -t {duration} -c:v libx264 -c:a aac -pix_fmt yuv420p output.mp4
```

### 4. 字幕叠加
```bash
ffmpeg -i output.mp4 -vf "subtitles=subs.srt" output_sub.mp4
```

## 优化要点

1. **Ken Burns 效果**：背景图缓慢缩放/平移增加动感
2. **转场效果**：淡入淡出、交叉溶解
3. **音频同步**：确保配音时长与视频时长匹配
4. **输出参数**：根据平台要求调整分辨率、码率、编码格式

## 🔗 相关笔记
- [[AI 视频生成管线设计与质量优化]]
- [[FFmpeg 命令行视频处理]]
- [[开源自动剪辑项目调研]]