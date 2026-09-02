---
tags:
  - 配置
  - oMLX
  - LLM
  - 本地部署
created: 2026-08-06
updated: 2026-08-06
id: know-omlx-llm
type: rule
---
# oMLX 本地 LLM 服务器配置

## 基本信息

- **版本**: 0.5.1
- **安装路径**: /opt/homebrew/bin/omlx
- **二进制文件**: ~/.omlx/bin/omlx
- **配置目录**: ~/.omlx/
- **数据目录**: ~/Library/Application Support/oMLX/
- **服务地址**: http://127.0.0.1:8000
- **OpenAI 兼容接口**: http://127.0.0.1:8000/v1

## 服务器配置 (settings.json)

### 网络
| 配置项 | 值 |
|--------|-----|
| host | 127.0.0.1 |
| port | 8000 |
| log_level | info |
| cors_origins | * |
| server_aliases | localhost, 127.0.0.1, 192.168.2.178, 192.168.2.178.local, 192.168.2.206 |
| sse_keepalive_mode | chunk |
| auto_start_on_launch | true |
| burst_decode_mode | balanced |
| preserve_mid_system_cache | true |

### 模型
| 配置项 | 值 |
|--------|-----|
| model_dirs | ~/.omlx/models |
| model_fallback | true |
| hide_helper_models | false |

### 内存管理
| 配置项 | 值 |
|--------|-----|
| prefill_memory_guard | false |
| memory_guard_tier | aggressive |
| memory_guard_custom_ceiling_gb | 48.0 |
| soft_threshold | 0.95 |
| hard_threshold | 0.99 |
| prefill_safe_zone_ratio | 0.9 |
| prefill_min_chunk_tokens | 128 |

### 调度器
| 配置项 | 值 |
|--------|-----|
| max_concurrent_requests | 2 |
| embedding_batch_size | 32 |
| chunked_prefill | true |

### 缓存
| 配置项 | 值 |
|--------|-----|
| enabled | true |
| hot_cache_only | false |
| ssd_cache_dir | ~/.omlx/cache |
| ssd_cache_max_size | auto |
| hot_cache_max_size | 1GB |
| initial_cache_blocks | 128 |

### 鉴权
| 配置项 | 值 |
|--------|-----|
| api_key | sk-omlx |
| skip_api_key_verification | false |

### 网络代理
| 配置项 | 值 |
|--------|-----|
| http_proxy | (空) |
| https_proxy | (空) |
| no_proxy | (空) |

### 采样参数
| 配置项 | 值 |
|--------|-----|
| max_context_window | 65536 |
| max_tokens | 16384 |
| temperature | 0.6 |
| top_p | 0.85 |
| top_k | 0 |
| repetition_penalty | 1 |

### HuggingFace
| 配置项 | 值 |
|--------|-----|
| endpoint | https://hf-mirror.com |
| hf_cache_enabled | false |

### 集成配置
| 配置项 | 值 |
|--------|-----|
| hermes_model | jundot-oq6 |
| openclaw_model | jundot-oq4 |
| markitdown_enabled | true |
| markitdown_expose_model | true |
| markitdown_max_file_size_mb | 25 |
| markitdown_max_files_per_request | 5 |

## 模型配置 (model_settings.json)

### jundot-oq6
- **来源**: Jundot/Qwen3.6-35B-A3B-oQ6-mtp
- **max_context_window**: 131072
- **max_tokens**: 98304

## 可用模型

通过 API 查询到的可用模型：
- **jundot-oq6** — 主模型，max_model_len: 131072
- **MarkItDown** — 文件处理模型

## 运行统计 (截至 2026-08-06)

| 指标 | 数值 |
|------|------|
| 总请求数 | 65,573 |
| 总 prompt tokens | 2,790,004,771 |
| 总 completion tokens | 73,977,422 |
| 总缓存 tokens | 2,285,438,976 |
| 总预填充时间 | 582,853 秒 |
| 总生成时间 | 1,480,377 秒 |

### 按模型统计

| 模型 | 请求数 | Prompt Tokens | Completion Tokens | 缓存 Tokens |
|------|--------|---------------|-------------------|-------------|
| jundot-oq6 | 56,197 | 2,443,912,863 | 56,381,798 | 1,993,390,080 |
| jundot-oq4 | 3,425 | 173,687,071 | 1,049,132 | 1,572,966,400 |
| Ornith-1.0-35B-oQ4e | 1,137 | 54,350,098 | 2,727,409 | 44,361,728 |
| qwen-oq6 | 4,771 | 117,288,860 | 13,792,946 | 89,980,928 |
| gemma-4-26b | 32 | 760,316 | 3,618 | 409,600 |
| o3 | 7 | 5,044 | 18,468 | 0 |
| default | 4 | 519 | 4,051 | 0 |

## 文件结构

```
~/.omlx/
├── settings.json              # 主配置
├── model_settings.json        # 模型配置
├── stats.json                 # 运行统计
├── monitor.sh                 # 监控脚本
├── omlx_server.log            # 服务器日志
├── bin/
│   └── omlx                   # 二进制文件
├── cache/                     # 缓存目录
├── logs/                      # 日志目录
│   ├── server.log             # 服务器日志
│   ├── crash.log              # 崩溃日志
│   └── ...
├── models/                    # 模型文件
│   └── jundot-oq6/
└── backups/                   # 备份目录
```

## 常用命令

```bash
# 查看版本
omlx --version

# 启动服务
omlx start

# 停止服务
omlx stop

# 重启服务
omlx restart

# 启动多模型服务器
omlx serve <model-name> --port 8000

# 启动诊断
omlx diagnose menubar
```

## 相关笔记

- [[Hermes Agent 配置]]
- [[本地 AI 模型部署]]
