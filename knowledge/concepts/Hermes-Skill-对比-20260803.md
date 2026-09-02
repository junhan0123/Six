---
created: 2026-08-03
tags:
  - hermes/skill
  - skill/对比
  - skill/安装
id: know-hermes-humanizer-zh-ui-ux-pro-max
type: concept
---
# Hermes 技能对比：humanizer-zh、ui-ux-pro-max 与现有技能

## 调研背景

老板要求对比以下技能与现有技能的差异：
- agent-reach
- last30days
- serper-scrape
- markitdown
- humanizer-zh
- cerbot-ssl
- frontend-design
- ui-ux-pro-max
- superpowers

## 对比结果

### 1. agent-reach ✅ 已有（无需安装）
- **功能**：多平台社交工具安装配置（GitHub、YouTube、B站、小红书、微博等10+平台）
- **我们已有**：`agent-reach` 技能完全覆盖
- **结论**：无需安装

### 2. last30days ⚠️ 互补（可选）
- **功能**：搜索 Reddit、X、YouTube、Hacker News、Polymarket 等最近30天内容，生成研究报告
- **GitHub**：mvanhorn/last30days-skill（GitHub Trending #1）
- **对比我们**：
  - `news-aggregation`：多源新闻抓取
  - `ai-daily-news`：AI每日新闻简报
  - `github-trending`：GitHub排行榜
  - **没有**跨平台30天趋势聚合
- **结论**：如果要看海外平台趋势可装，中文平台现有够了

### 3. serper-scrape ❌ 不需要
- **功能**：通过 Serper API 进行网页抓取
- **对比我们**：
  - `searxng-search`：本地搜索引擎
  - `tavily`：Tavily 搜索
  - `web_search` / `web_extract`：浏览器工具
- **结论**：不需要，已有更好的本地搜索方案

### 4. markitdown ⚠️ 互补（可选）
- **功能**：文档转换（PDF、Word、Excel 等→纯文本）
- **对比我们**：
  - `pdf-excel-report`：PDF提取+Excel报表
  - **没有**通用的文档转文本能力
- **结论**：如果经常需要把 PDF/Word 转文本给 AI 看，可以考虑装

### 5. humanizer-zh ✅ 已安装
- **功能**：去除中文文本中的 AI 味
- **GitHub**：blader/humanizer（32.7k⭐）
- **对比我们**：
  - Hermes 自带 `humanizer`（英文去AI味）
  - **没有**中文专用版本
- **结论**：发微博/小红书刚需，已安装
- **安装方式**：`npx skills add blader/humanizer --global`

### 6. cerbot-ssl ❌ 不需要
- **功能**：Certbot SSL 证书管理
- **对比我们**：`docker-nginx-ssl`（Docker+Nginx+SSL 全流程）
- **结论**：不需要，功能已覆盖

### 7. frontend-design ❌ 不需要
- **功能**：前端设计模板（Airtable、Cal.com、Figma 等风格）
- **对比我们**：
  - `design-taste-frontend`：反模板化前端设计
  - `huashu-design`：花叔 Design，HTML 高保真原型
  - `gpt-taste`：精英 UX/UI + GSAP 动画
  - `minimalist-ui`：极简编辑器风格
- **结论**：不需要，已有更强大的前端设计技能

### 8. ui-ux-pro-max ✅ 已安装
- **功能**：161种产品类型推理规则、192种配色方案、74种字体搭配、98条UX规范
- **GitHub**：nextlevelbuilder/ui-ux-pro-max-skill（113k⭐）
- **对比我们**：
  - `impeccable`：前端界面设计/重构/评审/优化
  - `design-taste-frontend`：反模板化设计
  - `gpt-taste`：精英 UX/UI + GSAP 动画
  - **没有**系统化的 UI/UX 规则库（配色、无障碍、交互模式）
- **结论**：系统化 UI 规则补充，已安装
- **安装方式**：`git clone` 到 `~/.hermes/skills/ui-ux-pro-max`

### 9. superpowers ⚠️ 需进一步调研
- **功能**：工作流技能包（14个超级技能）
- **GitHub**：obra/superpowers
- **对比我们**：
  - `agent-execution-guard`：主循环超时检测
  - `hermes-planner-loop`：Planner 无限循环诊断
  - `simplify-code`：4-agent 并行代码清理
- **结论**：需要进一步调研其具体功能

## 已安装技能清单

| 技能 | 路径 | 用途 |
|------|------|------|
| humanizer | `~/.hermes/skills/humanizer/SKILL.md` | 去除文本中的 AI 味 |
| ui-ux-pro-max | `~/.hermes/skills/ui-ux-pro-max/SKILL.md` | UI/UX 设计智能数据库 |

## 搜索工具使用规范

**优先使用 Tavily，然后再考虑 SearXNG。**
- Tavily：`tavily-python`，API Key 已配置
- SearXNG：本地搜索引擎，偶尔 404

## 🔗 相关笔记
- Hermes Agent 技能管理
- Tavily 搜索配置
- SearXNG 本地搜索引擎
