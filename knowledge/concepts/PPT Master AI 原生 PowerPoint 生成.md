---
id: know-ppt-master-ai-powerpoint
type: concept
---
# PPT Master — AI 生成原生 PowerPoint 工具

## 📌 项目概述

**PPT Master** 是一个开源的 AI 驱动工作流，能将 PDF、DOCX、网页等源文档或任意主题转化为**真正可编辑的原生 PowerPoint 演示文稿**。不是导出图片，不是套用模板，而是直接生成包含原生形状、图表、动画、母版布局的 .pptx 文件。

### 基本信息

- **仓库**: https://github.com/hugohe3/ppt-master
- **Stars**: 42,177+（截至 2026-07-31）
- **Forks**: 3,491
- **协议**: MIT
- **语言**: Python
- **创建时间**: 2025-12-10
- **作者**: Hugo He（投资/金融背景，CPA · CPV · Consulting Engineer）
- **主页**: https://hugohe3.github.io/ppt-master/
- **文档**: https://github.com/hugohe3/ppt-master/tree/main/docs

## 🔑 核心差异化

### 1. 原生深度 — 不是"可编辑"，是"原生"

这是 PPT Master 最核心的竞争力。大多数 AI PPT 工具只是导出可编辑的 .pptx 壳，但 PPT Master 直接生成 PowerPoint 的原生对象模型：

- **幻灯片母版与布局** — 真实的 `p:sldMaster` / `p:sldLayout` 继承结构
- **原生形状** — 预设几何图形（块箭头、V 形、标注、流程图节点…）、连接线、自由路径
- **原生图表与表格** — 数据驱动的 Chart / Table 对象（可选开启）
- **完整的文本/图片/填充/效果模型** — 段落格式、图片裁剪、渐变、阴影、辉光
- **转场、动画、演讲者备注→语音旁白** — 真实的 OOXML 时间轴
- **模板提炼** — 给一个现有 PPT，自动提取可复用的品牌/布局/演示模板

> **技术原理**: AI 生成受限 SVG → 脚本编译 SVG → DrawingML（PowerPoint 的 XML 格式）。SVG 和 DrawingML 本质是同一类东西——绝对坐标的 2D 矢量格式，矩形、路径、渐变、阴影一一对应，所以转换是"方言翻译"而非"格式桥接"。

### 2. 逻辑优先 — 先论证，后设计

在画任何一页之前，Strategist 会：
1. 阅读你的源材料
2. 确定核心论点
3. 选择叙事模式：
   - `pyramid`（金字塔）— 结论先行，分层支撑
   - `narrative`（叙事）— 故事线
   - `instructional`（教学）— 教学式
   - `showcase`（展示）— 震撼效果
   - `briefing`（简报）— 中立信息
4. 构建大纲和信息层级

**不同模式会生成完全不同的 PPT 骨架**，不是简单套用模板。

### 3. 透明成本 — 无订阅费

- PPT Master 本身免费开源
- 唯一成本是你自己的 AI 模型使用费
- 可以跑在带固定订阅的 AI IDE 上（生成无数 PPT 不额外收费）
- 也可以用按 token 计费的 API
- **无平台订阅、无专有积分、无按席位收费**

### 4. 数据隐私 — 100% 本地

- 源文件不出本机
- SVG 生成在本地
- PPTX 导出在本地
- 唯一外部通信是你和 AI 编辑器之间的调用

### 5. 完全开放 — 无锁定

- **编辑器**: Claude Code、Codex、Cursor、Windsurf、Gemini CLI 等都能驱动
- **模型**: Claude 效果最好，但 GPT、Gemini、Kimi 等都能用
- 质量差距在于排版精度，随模型迭代会缩小

## 🏗️ 技术架构

### 依赖

```
pip install -r requirements.txt
```

核心依赖包括 Python 3.10+、pptxgenlib（或 python-pptx）、SVG 处理库等。

### 运行方式

PPT Master 不是一个独立应用，而是一个**工作流（Skill）**，运行在任何具备 agent 能力的 AI 工具内部：

1. 安装 Python 3.10+
2. 安装 AI 工具（Claude Code / Cursor / Codex 等）
3. `git clone` + `pip install -r requirements.txt`
4. 在 AI 工具的聊天面板中对话，完成所有操作

### 推荐模型组合

| 角色 | 推荐模型 | 说明 |
|------|----------|------|
| 主模型 | Kimi K3 / Claude Opus | 大上下文窗口（~1M tokens）+ 视觉理解 |
| 图像生成 | gpt-image-2 / gemini-3.1-flash-image | AI 配图 |

> 作者原话："harness + model = agent" — PPT Master 只拥有工作流，模型决定天花板。

## 📋 功能清单

### 输入格式

PDF、DOCX、PPTX、EPUB、HTML、LaTeX、RST、Markdown、网页 URL、微信公众号文章、纯文本

### 输出格式

- **幻灯片比例**: 16:9、4:3、Xiaohongshu 3:4、微信/Instagram 1:1、竖屏 Story 9:16、A4 打印
- **输出文件**: .pptx（原生 PowerPoint）、.pdf、图片

### 视觉风格（18 种内置）

`swiss-minimal`、`editorial`、`dark-tech`、`brutalist`、`ink-wash`（水墨）等，每种都有 `custom` 自定义选项。叙事模式 × 视觉风格可自由组合。

### 示例项目

examples/ 目录包含：
- 政府财政分析
- AI 架构（Attention Is All You Need）
- 编辑杂志（普利兹克建筑奖）
- 数据新闻（Bloomberg 风格暗色仪表盘）
- 瑞士网格排版
- Memphis 波普风
- Risograph 独立书店指南
- Glassmorphism SaaS

### 高级功能

- **模板提炼**: 给现有 PPT，提取可复用品牌/布局/演示模板
- **内容填充**: 用新内容填充现有 .pptx，保留设计
- **转场/动画/旁白**: 为已完成 PPT 添加原生转场、动画、语音旁白
- **语音旁白**: 演讲者备注 → 音频旁白 → 视频（可选）

## 🎯 适用场景

### 适合

1. **需要快速将文档转为 PPT** — PDF/DOCX → 可编辑 .pptx
2. **对 PPT 编辑深度有要求** — 需要原生图表、母版、动画
3. **数据敏感** — 需要 100% 本地运行
4. **已有 AI IDE 订阅** — Claude Code/Cursor 等，批量生成不额外花钱
5. **品牌一致性** — 提炼模板后批量生成统一风格 PPT

### 不适合

1. **零设置浏览器生成** — 需要本地 Python 环境
2. **实时多人协作** — 不是协作工具
3. **一键完美成品** — 输出是高质量草稿，仍需人工精修
4. **没有 AI 工具使用经验** — 有学习曲线

## 💡 与竞品对比

| 项目 | 模式 | 原生深度 | 开源 | 本地 | 价格 |
|------|------|----------|------|------|------|
| **PPT Master** | Agent 工作流 | ⭐⭐⭐⭐⭐ 原生对象模型 | MIT | ✅ 100% | 免费（仅模型费） |
| Gamma | SaaS | ⭐ 模板填充 | ❌ | ❌ | 免费+付费 |
| Tome | SaaS | ⭐ 模板填充 | ❌ | ❌ | 免费+付费 |
| Beautiful.ai | SaaS | ⭐⭐ 智能布局 | ❌ | ❌ | $12/月起 |
| MindShow | SaaS | ⭐ 模板填充 | ❌ | ❌ | 免费+付费 |
| WPS AI | 集成 | ⭐⭐ 有限 | ❌ | ❌ | WPS 会员 |

**核心差异**: 几乎所有竞品都是"模板填充"或"网页生成"，只有 PPT Master 直接生成 PowerPoint 原生对象模型。

## 📦 安装与使用

### 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/hugohe3/ppt-master.git
cd ppt-master

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 AI 工具（推荐 Claude Code）
#    或使用 Cursor / Codex / Windsurf 等

# 4. 打开 ppt-master 文件夹，在 AI 聊天面板中对话
#    例如: "Please create a PPT from projects/q3-report/sources/report.pdf"
```

### 安装方式

1. **Git clone**（推荐）— 可随时更新
2. **下载 ZIP** — 无需 Git，适合快速试用
3. **Skill 市场安装** — Claude Code 插件市场：
   ```bash
   npx skills add hugohe3/ppt-master
   ```

### 更新

```bash
python3 skills/ppt-master/scripts/update_repo.py
```

## ⚠️ 能力边界

### 暂不支持

- **SmartArt** — 故意不实现（封闭、脆弱的对象模型，用原生形状重建更好）
- **部分装饰效果** — WordArt、反射、柔边
- **嵌入式对象** — OLE、视频、宏、原生公式

### 诚实的自我定位

> "This is a tool, not a wishing well" — 这不是许愿井。期望一次生成完美 PPT 是不现实的。工具的价值是帮你完成大部分繁琐工作，剩下的精修是用户的工作。

> "Making a deck is just the excuse; what I'm really pushing is Python and agents" — 做 PPT 只是借口，真正想推广的是 Python 和 AI Agent 的使用能力。

## 🔗 相关笔记

- [[CRMEB 开源商城系统调研报告]]
- World Monitor 贾维斯系统免费复刻攻略
- Mate-Engine 桌面虚拟宠物
- ToolKnit 多功能工具箱
