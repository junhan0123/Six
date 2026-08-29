---
id: know-agnes-ai-api
type: concept
---
# Agnes AI API 迁移记录

## 迁移概要

- **时间**: 2026-07-29
- **旧域名**: `apihub.agnes-ai.com`
- **新域名**: `api.agnes-ai.cn`
- **新 API Key**: `sk-WwzfF83uhV5Ewl8RD2XpLbwB0Lp3aE8cxfULkSCmAhdbNHEQ`
- **官方网址**: https://agnes-ai.cn/
- **迁移原因**: Agnes AI 官方更换域名和 API Key

## 可用模型

| 模型 ID | 用途 |
|---------|------|
| `agnes-2.5-flash` | 文本对话 |
| `agnes-2.5-pro-alpha` | 文本对话（Pro） |
| `agnes-image-2.1-flash` | 文生图 |
| `agnes-video-v2.0` | 文生视频/图生视频 |

## 配置修改清单

### 1. Skill 文件
- 文件: `~/.hermes/skills/agnes-ai/SKILL.md`
- 修改内容: 所有 `apihub.agnes-ai.com` → `api.agnes-ai.cn`（共 8 处）
- 包括: Base URL、Python 示例、curl 命令、视频下载 URL 等

### 2. 环境变量
- 文件: `~/.hermes/.env`
- 修改内容: `AGNES_API_KEY` 更新为新 Key

## 验证结果

```bash
curl -s https://api.agnes-ai.cn/v1/models \
  -H "Authorization: Bearer <key>"
```

返回 4 个模型，状态正常 ✅

## 注意事项

- 旧域名 `apihub.agnes-ai.com` 可能已失效，所有工具调用需使用新域名
- 新域名 `api.agnes-ai.cn` 的下载 URL 格式可能变化（`platform-outputs.agnes-ai.cn` 替代 `platform-outputs.agnes-ai.space`）
- 新 API Key 已写入 `.env`，所有 Cron 任务自动生效

## 相关笔记

- [[Hermes Agent 自动化工作流]]
- [[AI 视频生成管线设计与质量优化]]
- [[本地 AI 模型部署]]
