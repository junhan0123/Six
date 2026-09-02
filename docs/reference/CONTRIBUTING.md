# 小6 · 贡献指南（CONTRIBUTING）

> 本文档是团队工程基线。所有改动请先读《代码质量评审与团队提升方案》与《代码审查清单》。

## 一、开发环境

- **Python**：≥ 3.10（推荐 3.11+）；依赖隔离用 venv，不要污染系统 Python。
- **依赖**：`requirements.txt` 标注运行时依赖；`psutil` 为可选（sysmon 需要），`edge-tts` 为可选（TTS 需要）。
- **密钥**：**只放在 `xiao6-ui/.env`**（已被 `.gitignore` 忽略）。绝不在源码硬编码密钥。
  - 必需：`AGNES_API_KEY`
  - 可选：`HOTDATA_KEY`（热榜）、`Xiao6_TTS_VOICE`（TTS 音色）、`Xiao6_PORT`（端口）

## 二、项目结构（模块化后）

```
xiao6-ui/
├── server.py          # 薄入口：HTTP Handler + main()
├── config.py          # 配置与常量（含 .env 加载）
├── db.py              # SQLite 层（WAL 并发加固）
├── llm.py             # Agnes 大模型调用（重试/限流）
├── http_client.py     # 通用 HTTP JSON 客户端
├── notes.py           # 笔记/画像/提醒/每日笔记
├── memory.py          # 记忆压缩与上下文注入（ACI）
├── geo_weather.py     # 定位 & 天气
├── hotspots.py        # 实时热榜
├── sysmon.py          # 系统监控 + 日志
├── proactive.py       # 主动智能/SSE/心跳
├── tools.py           # 工具系统（声明/执行/FC闭环/意图兜底）
└── tests/             # pytest 单测
```

> **铁律**：不要把以上模块再塞回 `server.py`。新增能力请落到对应模块；跨模块通用逻辑进 `http_client` / `db` / `config`。

## 三、提交流程

1. 从 `main`（或任务分支）切出特性分支：`feature/xxx`。
2. 本地跑门禁：`bash scripts/ci.sh`（等价于 CI）。
3. 提交信息用中文或英文祈使句，说明「为什么」：`fix: 修 get_geo 文件句柄泄漏`。
4. 发起 PR，**至少 1 人 review**；涉及工具沙箱 / 密钥 / 并发 的改动**必须双人复核**。
5. review 通过后由负责人合入。

## 四、质量门禁（必须全绿）

- `ruff check .` 零告警（规则见 `pyproject.toml`）。
- `ruff format --check .` 格式一致。
- `python -m py_compile` 全部模块通过。
- `pytest` 单测通过（纯函数必须有测试）。

## 五、安全红线（不可逾越）

- 🔴 **密钥永不进仓库**：只用 `.env` + 环境变量。
- 🔴 **新增文件/Shell/Web 工具必须有沙箱**：路径白名单 + 危险操作拦截 + 行动审计日志。
- 🔴 **禁止 `eval` / `exec`** 执行外部输入；计算器已用纯 AST 安全求值器，新增类似能力须同等处理。
- 🔴 **外部 provider 失败必须优雅降级**，不能拖垮主链路。
- 🟠 并发写共享状态需加锁（参考 `_cache_lock` 模式）。
