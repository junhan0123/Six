---
id: know-toolknit
type: concept
---
# ToolKnit — 多功能工具箱

## 基本信息

- **GitHub**：ZihangDong/toolknit-desktop
- **Stars**：124 · Forks：13
- **License**：MIT
- **创建时间**：2026-07-30
- **作者**：董子航（Zihang Dong）
- **网页端**：[toolknit.com](https://toolknit.com)
- **桌面端**：[GitHub Releases](https://github.com/ZihangDong/toolknit-desktop/releases/latest)

## 核心定位

一个 exe 替代 20+ 在线工具网站，全部本地运行，文件不上传，隐私安全。

是 ToolKnit 网页端（toolknit.com）的桌面开源版配套项目。

## 功能模块

### 文档工具（Document Studio）
- PDF 合并 / 拆分 / 旋转 / 加密 / 解密 / 压缩 / 增强

### 图片工具（Pixel Lab）
- 图片格式转换（JPG/PNG/WebP/BMP/GIF）
- 图片压缩
- 图标生成

### 音视频工具（Sound Studio）
- 音频格式转换
- BPM 节拍检测
- 音频裁剪
- 视频转音频提取
- 视频格式转换

### AI 工具
- AI 润色 / 翻译 / 文档处理 / 表格处理
- 支持模型：DeepSeek / OpenAI / 通义千问 / Moonshot
- 用户自行配置 API Key，数据直连模型厂商

### 文本与小工具
- 颜色提取 / 文本统计 / 文本格式化 / 打字测试
- BMI 计算器 / 时间戳转换

## 技术栈

| 分类 | 技术 |
|------|------|
| 桌面框架 | Tauri 2.x（Rust） |
| 前端 | 原生 JavaScript + Vite |
| 音视频处理 | ffmpeg（内置打包） |
| AI 模型 | DeepSeek / OpenAI / 通义千问 / Moonshot |
| ML 模型 | whisper（语音识别）、yolov8（水印检测） |

## 注意事项

1. **仅支持 Windows**（桌面端），依赖 Rust + Node.js 18+ 构建环境
2. **需要自行下载 ffmpeg.exe**（GitHub 单文件 100MB 限制）
3. **刚创建不到一天**，项目非常新
4. 网页端功能更完整、跨平台、免安装

## 相关笔记

- Mate-Engine 桌面虚拟宠物
- AI 工具调研
