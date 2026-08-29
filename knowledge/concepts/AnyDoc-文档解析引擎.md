---
id: know-anydoc-firecrawl
type: concept
---
# AnyDoc — Firecrawl 开源文档解析引擎

> **归档日期：** 2026-08-11
> **来源：** https://www.firecrawl.dev/blog/anydoc-and-pdf-inspector
> **标签：** #文档解析 #Rust #Markdown #开源 #Firecrawl

## 项目信息

- **仓库：** [firecrawl/anydoc](https://github.com/firecrawl/anydoc)
- **PDF 解析：** [firecrawl/pdf-inspector](https://github.com/firecrawl/pdf-inspector)
- **定位：** Rust 编写的开源文档解析引擎
- **速度：** 亚毫秒级（< 5ms median）
- **格式支持：** 14 种格式 → 统一 Markdown 输出

## 是什么

AnyDoc 是 Firecrawl 团队开源的文档解析引擎，用 Rust 从头编写，支持 14 种文档格式转换为统一的 Markdown 格式。

## 核心特性

### 1. 格式支持
- **PDF** — 智能检测扫描版 vs 文本版 PDF
- **Word** — .docx, .doc
- **PowerPoint** — .pptx, .ppt
- **Excel** — .xlsx, .xls
- **OpenDocument** — .odt
- **RTF** — .rtf
- **EPUB** — .epub
- **CSV** — .csv
- **HTML** — .html

### 2. 统一输出
- GitHub-Flavored Markdown
- 结构化 JSON
- 表格转义一致
- 标题结构统一

### 3. 性能
- Rust 编写，亚毫秒级解析
- 内容检测（不依赖文件扩展名）
- 浏览器 WebAssembly 版本（离线运行）

### 4. 多语言绑定
- **Rust** — 原生 crate
- **Node.js** — libuv 多线程
- **Python** — 释放 GIL
- **CLI** — 命令行工具
- **WASM** — 浏览器端运行

## 和我们有什么关系

### 与 Hermes 的对比

| 特性 | Hermes | AnyDoc |
|------|--------|--------|
| 定位 | AI Agent 平台 | 文档解析引擎 |
| 语言 | Python | Rust |
| 能力 | 搜索、浏览、文件、cron 等 | 14 种格式 → Markdown |
| 适用场景 | 综合自动化 | 文档转 Markdown |

### 潜在应用场景

1. **Hermes 文件工具增强**
   - 当前 Hermes 的 `read_file` 对 PDF、Word、Excel 等格式支持有限
   - AnyDoc 可以补充这些格式的解析能力
   - 特别是 PDF、Word、Excel 等常见办公文档

2. **小6项目 - 文档处理能力**
   - 如果小6需要文档解析，AnyDoc 是高性能选择
   - Rust 编写的性能优势明显

3. **PDF 智能检测**
   - pdf-inspector 可以智能检测扫描版 vs 文本版 PDF
   - 支持智能路由（扫描版走 OCR，文本版直接提取）

### 集成建议

#### 方式 1: CLI（已安装，推荐）
```bash
npx @firecrawl/anydoc document.docx
npx @firecrawl/anydoc report.pdf
npx @firecrawl/anydoc data.xlsx -o output.md
```

#### 方式 2: Python 封装脚本
```python
# 脚本位置: ~/.hermes/scripts/anydoc_tool.py
from hermes.scripts.anydoc_tool import convert_to_markdown

md = convert_to_markdown('report.docx')
print(md)

# 字节数据转换
md = convert_to_markdown_bytes(data, format_hint='csv')
```

#### 方式 3: Python SDK（需要 PyO3 编译，暂不可用）
```bash
pip install firecrawl-anydoc  # 需要 Python >= 3.10 + PyO3
```

## 相关笔记

- Firecrawl-Web内容抓取API — Web 内容抓取
- 工具配置 — 工具链配置
- Hermes Workflow — Hermes Agent 工作流
