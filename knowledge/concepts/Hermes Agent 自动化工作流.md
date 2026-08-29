---
date: 2026-07-23
tags:
  - Hermes
  - 自动化
  - 工作流
  - 技能参考
id: know-hermes-agent
type: concept
---
# Hermes Agent 自动化工作流

> 对应 Hermes 核心功能

## 概述

Hermes Agent 自动化工作流是一套基于 Hermes Agent 的自动化任务执行框架，覆盖技能管理、定时任务、多平台集成等环节。

## 核心架构

```
用户指令 → Hermes Agent → 技能执行 → 工具调用 → 结果返回
```

## 主要技能

### 1. 开发工具（dev-tools）
- `github-trending`：GitHub Trending 排行榜抓取
- `ai-daily-news`：AI 每日新闻简报生成
- `web_search`：网络搜索（Tavily 后端）
- `web_extract`：网页内容提取

### 2. 运维工具（devops）
- `watchers`：RSS/API 轮询与水印去重
- `macos-setup`：macOS 权限管理、Docker 安装
- `qq-bot-platform`：QQ Bot 机器人开发

### 3. AI 工具（ai-tools）
- `tts-tools`：文本转语音工具集
- `comfyui-image-gen`：ComfyUI 文生图
- `comfyui-troubleshooting`：ComfyUI 故障排查

### 4. 游戏开发（game-dev）
- `pygame-game-dev`：Pygame 图形游戏开发
- `unity-game-dev`：Unity 2D 游戏开发
- `godot-migration`：Unity 到 Godot 迁移

## 定时任务（Cronjob）

```bash
hermes cron create --name "每日新闻" --schedule "0 8 * * *" --prompt "生成 AI 每日新闻简报"
```

## 🔗 相关笔记
- 00_System/Index
- 00_System/Daily_Review
- 00_System/Knowledge_Rules
- [[本机系统资产全景盘点]]