---
created: 2026-08-03
tags:
  - AI/Agent
  - YC
  - 多Agent
  - 协作平台
  - 开源
id: know-qm-yc-agent
type: concept
---
# QM - YC 开源多玩家 Agent 工作平台

## 简介

**QM** 是 Y Combinator 开源的内部多 Agent 协作平台，定位为"多玩家 Agent 工作平台"。支持 Slack 和 Web 双界面，专为创业公司设计，让每个员工都有独立的 AI Agent 工作空间，同时支持团队协作。

- **GitHub**: [yc-software/qm](https://github.com/yc-software/qm)
- **⭐**: 9,342（上线 5 天）
- **Forks**: 978
- **License**: MIT
- **语言**: TypeScript
- **创建**: 2026-07-29

## 核心定位

大多数 Agent 被设计为个人助手。QM 被设计为**公司级协作平台**——员工各自拥有独立工作空间，互不影响，同时可以在频道、群组和项目中与 Agent 协作。

## 功能特性

### 1. 个人与共享范围
- 每个人可以自定义专属 Agent
- 支持 Slack 频道和群组消息中的协作
- 项目级别的共享工作空间

### 2. 双界面支持
- **Slack 集成**：在 Slack 中直接使用
- **Web 界面**：独立的 Web UI
- 身份和配置在两个界面间无缝同步

### 3. 管理控制
- 组织级配置
- 安全策略设定
- 可用 Harness 和模型的权限管理

### 4. 自定义应用
- 创建内部应用并定向发布给指定人员
- 保持数据实时更新

### 5. 共享技能包
- 技能包按范围所有，可授权共享
- 管理员可提升到全组织
- 支持从 Git 仓库导入技能包

### 6. 后台任务
- Crons 和 Watches 支持无人值守的后台工作

## 典型应用场景

- 搜索内部笔记、邮件、文档、数据库和网页
- 从公司知识库检索信息
- 构建内部应用并发布给相关人员
- 学习你的写作风格，定时处理邮箱（自动打标签和起草回复）
- 在现有代码库中工作：运行测试、开 PR、监控 CI、查看系统日志
- 在共享频道中跟踪项目并发送更新和后续任务

## 架构设计

### 核心组件

```
┌─────────────────────────────────────────────────┐
│                   Postgres DB                    │
│         sessions · memory · queue                │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│              Headless Core                       │
│  ┌─────────────┐    ┌──────────────────────┐    │
│  │   API        │◄──►│   Agent Loop          │    │
│  │ identity     │    │ (Pi, OpenCode,        │    │
│  │ policy       │    │  Claude Code)         │    │
│  │ scheduler    │    └──────────┬───────────┘    │
│  └─────────────┘               │                │
└────────────────────────────────┼────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Per-Scope Sandbox       │
                    │  files · tools · services│
                    └─────────────────────────┘
```

### 技术栈

| 组件 | 技术 |
|------|------|
| 核心语言 | TypeScript (Node.js) |
| HTTP 框架 | Fastify |
| 数据库 | Postgres |
| Web UI | Vite + Lit |
| Slack 插件 | Bolt |
| 部署目标 | Fly.io / AWS |

### 核心设计原则

1. **通用核心**：核心本身不绑定任何特定公司或模型
2. **可插拔架构**：每个子系统（Harness、Session Store、Sandbox、Memory）都通过接口抽象，可通过一个配置文件替换
3. **部署目录**：所有公司特定配置（组织配置、自定义工具/技能、沙箱镜像、基础设施）都放在 `deploy/layers/<org>/` 目录中
4. **CLI 验证**：通过 `qm` CLI 验证和部署

## 安全与权限

### 三种安全模式

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| **Strict** | 每次工具调用暂停等待人工审批（除两个无效果的结束操作外） | 高合规要求 |
| **Auto**（默认） | 分类器筛选带来源标记的外部数据和工具结果 | 大多数场景 |
| **Dangerous** | 无内容筛选，工具调用间无暂停 | 内部实验 |

### 命令策略

预声明的命令策略（审批规则和硬拒绝）在所有模式下生效，包括 Dangerous：
- 递归删除：硬拒绝
- 破坏性 SQL：硬拒绝
- 其他危险操作：需审批

### 审计

- 每个 Agent 作为被代表的人行动，使用其凭证和权限
- 所有操作均可审计

## 部署方式

### 方式一：标准部署（推荐）

```bash
npm exec --yes --package=@yc-software/qm@latest -- \
  qm init . --org <slug> --target <fly-or-aws>
npm install
```

初始化流程：
1. 创建 Agent 技能包
2. 配置基础设施
3. 设置 Web 登录
4. 配置连接器凭证
5. 可选配置 Slack 接入
6. 部署并验证

### 方式二：私有 Fork（深度定制）

```bash
# 创建私有仓库
gh repo create <org>/qm-private --private

# 克隆 QM 作为种子
git clone --bare git@github.com:yc-software/qm qm-seed.git
git -C qm-seed.git push --mirror git@github.com:<org>/qm-private
rm -rf qm-seed.git

# 克隆并设置上游
git clone git@github.com:<org>/qm-private
git -C qm-private remote add upstream git@github.com:yc-software/qm
```

**注意**：不是用 GitHub 的 Fork 按钮，而是用普通克隆。因为：
- GitHub Fork 继承可见性，无法从公开仓库创建私有 Fork
- GitHub Fork 共享对象网络，推送的 commit 可从公开侧获取
- 普通克隆是独立仓库，上游 CI 会在你自己的账号中运行

### 同步机制

| 技能 | 方向 | 功能 |
|------|------|------|
| `update-qm` | 上游 → 私有 | 合并上游 QM 到私有 Fork，打开同步 PR |
| `upstream-pr` | 私有 → 上游 | 发送组织无关的修复到 QM 主仓库 |

## 仓库结构

```
├── .claude/          # Claude 配置
├── .codex/           # Codex 配置
├── adrs/             # 架构决策记录（人工贡献）
├── aws/              # AWS 部署配置
├── cli/              # QM CLI 工具
├── deploy/           # 部署目录
│   └── layers/       # 各组织配置层
├── docs/             # 文档
├── fly/              # Fly.io 部署配置
├── local/            # 本地开发配置
├── plugins/          # 插件（Slack、Web UI、Admin、Portal）
├── .env.example      # 环境变量示例
├── package.json      # 依赖
├── SECURITY.md       # 安全模型
├── deployment.md     # 部署指南
└── CONTRIBUTING.md   # 贡献指南
```

## 贡献方式

QM 采用独特的贡献模式：**只接受人工编写的文本，不接受代码 PR**。

- 在 `adrs/` 目录中提交 `.txt` 或 `.md` 文件描述你想做的改动
- 如果社区对齐，由维护者自行实现
- 漏洞通过 `SECURITY.md` 中描述的私有渠道报告

## 与小6项目的关系

### 相似点
- 都是多 Agent 协作平台
- 都支持组织级管理
- 都强调 Agent 的隔离性和安全性

### 差异点
| 维度 | QM | 小6 |
|------|-----|------|
| 定位 | 内部办公 Agent 平台 | 智能指挥中枢 |
| 界面 | Slack + Web | 赛博朋克风格 Web |
| Agent 引擎 | 可切换（Pi/OpenCode/Codex/Claude） | 自研 |
| 部署 | 标准化部署目录 | 自研架构 |
| 安全 | 三档安全策略 | 自研安全模型 |

### 集成可能性
- QM 的 Agent Loop 可接入 Agnes AI 作为后端模型
- QM 的部署目录结构可参考小6的配置管理
- QM 的共享技能包机制可借鉴到小6的能力模块系统

## 参考链接

- [GitHub 仓库](https://github.com/yc-software/qm)
- [Getting Started](https://github.com/yc-software/qm/blob/main/docs/getting-started.md)
- [CLI 文档](https://github.com/yc-software/qm/blob/main/cli/README.md)
- [部署目录详解](https://github.com/yc-software/qm/blob/main/docs/deploy-directory.md)
- [安全模型](https://github.com/yc-software/qm/blob/main/SECURITY.md)

## 相关笔记

- OSIRIS-开源全球情报平台
- PLFM_RADAR-AERIS10-开源相控阵雷达
- 小6-项目架构
