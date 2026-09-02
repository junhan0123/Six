---
tags:
  - ai-agent
  - cli
  - python
  - github
created: 2026-07-27
source: https://github.com/HKUDS/CLI-Anything
license: Apache-2.0
stars: 46113
id: know-cli-anything
type: concept
---
# CLI-Anything

## 项目简介

香港大学开源项目，目标是将所有软件变为 **Agent-Native**（智能体原生）。

> 让任何软件都能被 AI Agent 直接操控。

## 核心能力

- **CLI-Hub 插件系统**：通过 `pip install cli-anything-hub` 安装扩展
- **100% 测试覆盖**：2461 个测试用例全部通过
- **学术论文**：arXiv: 2606.03854

## 技术栈

- Python >= 3.10
- CLI-Hub 插件化架构

## 安装方式

```bash
# 创建虚拟环境（推荐 Python 3.11+）
python3 -m venv cli-any-venv
source cli-any-venv/bin/activate

# 安装 CLI-Hub
pip install cli-anything-hub

# 验证安装
cli-hub --help
```

## 项目指标

| 指标 | 数值 |
|------|------|
| Stars | 46,113 |
| Forks | 4,303 |
| 语言 | Python |
| License | Apache-2.0 |

## 注意事项

- 需要 Python >= 3.10，系统自带 3.9 需通过 pyenv 切换
- 外网 SSL 阻断环境下，需使用 `curl --insecure` 绕过证书校验
- 内置 registry/matrix 拉取命令会触发 SSL 错误，需探索离线模式

## 相关链接

- GitHub: [[CLI-Anything]]
- 官网: https://clianything.cc/
- 论文: arXiv: 2606.03854

---
*归档时间：2026-07-27*
