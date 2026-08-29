---
id: know-doc-d5d37e71
type: concept
---
# 任务追踪

> 最后更新：2026-07-19

## 当前任务列表

### 📋 meeting-minutes — 会议纪要功能（方案A）

**状态：** 待执行测试

**方案说明：** 本地语音/录音 → 结构化纪要

**管线设计：**
1. 音频预处理：`ffmpeg` 转 16kHz WAV
2. 语音转文字：`openai-whisper` `tiny` 模型（72.1MB，CPU 推理）
3. LLM 结构化：Markdown 模板输出

**环境验证：**
- `ffmpeg` 8.1.2 ✅
- `whisper` 20250625 ✅
- `openai-whisper` tiny 模型已成功加载至 CPU ✅
- `edge-tts` 7.2.8 ✅
- 转录测试通过（生成 1 秒静音 WAV，返回空字符串，FP32 兼容警告正常）

**落地脚本：** `~/.hermes/scripts/meeting-minutes.py`（4033 字节，Lint 通过）

**下一步：** 使用真实录音文件执行脚本测试，将结构化结果存入 Obsidian

**相关笔记：** Tool_Management

---

### 📋 code-simplifier-local — Code Simplifier 本地替代方案

**状态：** 待排期

**定位：** 用现有工具实现代码简化功能

**环境准备：**
- `simplify-code` 技能已就绪，支持并行三代理代码审查与清理
- 技能元数据已读取确认，环境依赖满足

**相关笔记：** Tool_Management

---

## 基础设施状态（2026-07-19）

| 组件 | 状态 |
|------|------|
| Hermes Gateway | 运行中（launchd 托管） |
| v5.0 规则 | 生效 |
| Tavily 搜索后端 | 活跃，凭证已验证 |
| oMLX 服务 | 运行中，模型列表为空 |
| 每日归档 cronjob | ok |
| 崩溃监控 cronjob | ok（模型漂移已修复） |

## 相关笔记

- Tool_Management
- Tool_Usage_Guide
- Task_Planning
- Task_Splitting
- Daily_Report

## 🔗 相关笔记
- Tool_Management
- Tool_Usage_Guide
- Task_Planning
- Task_Splitting
- Daily_Report
