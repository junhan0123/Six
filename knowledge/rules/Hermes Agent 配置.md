---
tags:
  - 配置
  - Hermes
  - Agent
  - 本地部署
created: 2026-08-06
updated: 2026-08-06
id: know-hermes-agent-2
type: rule
---
# Hermes Agent 配置

## 基本信息

- **配置文件**: ~/.hermes/config.yaml
- **模型**: jundot-oq6 (custom provider)
- **模型地址**: http://127.0.0.1:8000/v1
- **API Key**: sk-omlx
- **上下文长度**: 65536
- **最大输出 tokens**: 16384

## 模型配置

| 配置项 | 值 |
|--------|-----|
| model.default | jundot-oq6 |
| model.provider | custom |
| model.base_url | http://127.0.0.1:8000/v1 |
| model.api_key | sk-omlx |
| model.context_length | 65536 |
| model.max_tokens | 16384 |
| fallback_providers | [] |

## Agent 配置

| 配置项 | 值 |
|--------|-----|
| agent.max_turns | 200 |
| agent.gateway_timeout | 1800 |
| agent.restart_drain_timeout | 0 |
| agent.api_max_retries | 3 |
| agent.service_tier | (空) |
| agent.tool_use_enforcement | auto |
| agent.task_completion_guidance | true |
| agent.parallel_tool_call_guidance | true |
| agent.environment_probe | true |
| agent.environment_hint | (空) |
| agent.coding_context | auto |
| agent.verify_on_stop | auto |
| agent.gateway_timeout_warning | 900 |
| agent.clarify_timeout | 3600 |
| agent.gateway_notify_interval | 180 |
| agent.gateway_auto_continue_freshness | 3600 |
| agent.image_input_mode | auto |
| agent.disabled_toolsets | [] |
| agent.reasoning_effort | high |
| agent.verbose | false |

## 人格 (personalities)

| 人格 | 描述 |
|------|------|
| catgirl | 猫娘风格，加"nya"和颜文字 |
| concise | 简洁回复 |
| creative | 创意风格，创新方案 |
| helpful | 友好助人 |
| hype | 超兴奋风格 |
| kawaii | 可爱风格 |
| noir | 黑色电影侦探风格 |
| philosopher | 哲学家风格 |
| pirate | 海盗风格 |
| shakespeare | 莎士比亚风格 |
| surfer | 冲浪者风格 |
| teacher | 耐心教师风格 |
| technical | 技术专家风格 |
| uwu | 软萌风格 |

## 终端配置

| 配置项 | 值 |
|--------|-----|
| terminal.backend | local |
| terminal.modal_mode | auto |
| terminal.cwd | . |
| terminal.timeout | 180 |
| terminal.daemon_term_grace_seconds | 2 |
| terminal.env_passthrough | [] |
| terminal.home_mode | auto |
| terminal.shell_init_files | [] |
| terminal.auto_source_bashrc | true |
| terminal.docker_image | nikolaik/python-nodejs:python3.11-nodejs20 |
| terminal.docker_forward_env | [] |
| terminal.singularity_image | docker://nikolaik/python-nodejs:python3.11-nodejs20 |
| terminal.modal_image | docker://nikolaik/python-nodejs:python3.11-nodejs20 |
| terminal.daytona_image | docker://nikolaik/python-nodejs:python3.11-nodejs20 |
| terminal.container_cpu | 1 |
| terminal.container_memory | 5120 |
| terminal.container_disk | 51200 |
| terminal.container_persistent | true |
| terminal.docker_volumes | [] |
| terminal.docker_mount_cwd_to_workspace | false |
| terminal.docker_extra_args | [] |
| terminal.docker_run_as_host_user | false |
| terminal.persistent_shell | true |
| terminal.lifetime_seconds | 300 |

## Web 配置

| 配置项 | 值 |
|--------|-----|
| web.backend | (空) |
| web.search_backend | (空) |
| web.extract_backend | (空) |

## 浏览器配置

| 配置项 | 值 |
|--------|-----|
| browser.inactivity_timeout | 120 |
| browser.command_timeout | 30 |

## 工具集 (toolsets)

- hermes-cli

## 文件结构

```
~/.hermes/
├── config.yaml              # 主配置
├── AGENTS.md                # 项目级行为规范
├── profiles/
│   └── default/
│       └── config.yaml      # 默认 profile 配置（不存在）
├── skills/                  # 技能目录
├── plugins/                 # 插件目录
├── cron/                    # 定时任务
└── memories/                # 记忆目录
```

## 相关笔记

- [[oMLX 本地 LLM 服务器配置]]
- [[本地 AI 模型部署]]
