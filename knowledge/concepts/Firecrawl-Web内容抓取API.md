---
id: know-firecrawl-web-api
type: concept
---
# Firecrawl — Web 内容抓取 API

> **归档日期：** 2026-08-11
> **来源：** https://github.com/firecrawl/firecrawl
> **标签：** #Web抓取 #API #AI工具 #开源

## 项目信息

- **仓库：** [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl)（原名 mendableai/firecrawl）
- **Star：** 163k+ | **Fork：** 9.2k+
- **许可证：** AGPL-3.0（SDK 为 MIT）
- **最新提交：** 4 小时前，6,078 次 commit
- **官网：** firecrawl.dev
- **社区：** 1.25M+ 开发者，150k+ 公司使用（包括 Apple、Canva、Lovable）

## 是什么

Web 内容抓取 API — 搜索、抓取网页，将内容转换为干净的 Markdown 或结构化数据，供 AI Agent 直接使用。

## 核心能力

### 1. 单页抓取（Scrape）
- 将任意 URL 转为 Markdown 或结构化数据
- 支持 JS 渲染页面（浏览器模式）
- 支持 PDF、DOCX 等媒体文件解析

### 2. 批量抓取（Crawl）
- 递归抓取整个网站
- 自定义抓取规则（路径、深度、域名限制）

### 3. 搜索（Search）
- 搜索网页并提取内容
- 返回结构化搜索结果

### 4. 交互（Interact）
- 点击、滚动、写入、等待
- 抓取前可模拟用户操作

### 5. 地图（Map）
- 发现网站所有页面 URL

## API 端点

```
POST /scrape     # 单页抓取
POST /crawl      # 批量抓取
POST /search     # 网页搜索
POST /map        # 发现 URL
POST /extract    # 结构化数据提取
```

## 项目结构

```
firecrawl/
├── apps/                    # 应用核心
├── firecrawl-cli/           # 命令行工具
├── firecrawl-skills/        # Skills 集成
├── firecrawl-workflows/     # 工作流
├── examples/                # 示例代码
├── docker-compose.yaml      # 自部署配置
└── SELF_HOST.md             # 自部署文档
```

## 自部署

支持 Docker Compose 一键部署，包含 FoundationDB 依赖。

## SDK

多语言 SDK（Python、Node.js 等），每周下载量 2.5M+。

## 和我们有什么关系

### 与现有工具的对比

| 工具 | 优势 | 劣势 |
|------|------|------|
| **web_search** | 快速搜索 | 只能获取摘要 |
| **web_extract** | 提取页面内容 | 不支持 JS 渲染 |
| **Firecrawl** | JS 渲染、批量抓取、结构化数据 | 需要 API Key 或自部署 |

### 潜在应用场景

1. **替代 web_extract**
   - 对于 JS 渲染的页面（SPA 应用），Firecrawl 浏览器模式更可靠
   - 批量抓取整个网站内容

2. **AI Agent 数据源**
   - 为小6项目提供实时网页数据
   - 输出干净的 Markdown，适合 RAG 管道

3. **新闻抓取**
   - 批量抓取新闻网站
   - 结构化数据提取

4. **竞品监控**
   - 定期抓取目标网站变化
   - 对比分析

### 局限性

- AGPL-3.0 许可证有传染性（修改后需开源）
- 自部署需要 FoundationDB 依赖
- 云端 API 有免费额度限制

### 替代方案

- **Vakra Reader** — 开源替代，553 stars
- **Molx** — Rust 实现，更快更轻量
- **Aynclaw** — 开源 Web 基础设施

## 相关笔记

- Hermes Workflow — Hermes Agent 工作流
- GSAP AI Skills 官方编程技能包 — 前端技能
- 工具配置 — 工具链配置
