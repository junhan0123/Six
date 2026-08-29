---
id: know-world-monitor-ai
type: concept
---
# World Monitor — 桌面级 AI 战术中心免费复刻攻略

## 📌 项目背景

抖音博主 `@InteriorArchitectXie` 展示了一个类似《钢铁侠》贾维斯系统的桌面级 AI 战术中心，实际基于开源项目 **World Monitor**。该项目原作者 Elie Habib 收费 $39.99/月（Pro 版），但源码开源，博主表示"完全复刻一个然后找旧卫星可免费接"。

---

## 一、World Monitor 项目概况

| 项目 | 信息 |
|------|------|
| **GitHub** | [koala73/worldmonitor](https://github.com/koala73/worldmonitor) |
| **Stars** | 77,306 |
| **Forks** | 11,546 |
| **License** | AGPL-3.0-only |
| **语言** | TypeScript |
| **作者** | Elie Habib |
| **官网** | [worldmonitor.app](https://www.worldmonitor.app) |
| **创建时间** | 2026-01-08 |
| **最新 Release** | v2.5.23 (2026-03-01) |

---

## 二、收费 vs 免费的核心区别

### 收费版（Pro $39.99/月）提供什么？

1. **WM Analyst Chat** — AI 智能对话，接入 30+ 实时情报服务，带引用来源
2. **Scenario Engine** — 情景推演引擎
3. **AI 摘要** — 每日/每周 AI 简报（通过 Slack/Discord/Telegram/Email/Webhook 推送）
4. **自定义仪表盘** — 10 个自定义 Widget
5. **MCP 访问** — 59 个工具接口，50 次调用/天
6. **数据导出** — CSV/JSON/PDF 报告

### 免费版（$0，无需注册）提供什么？

1. **56 种地图图层** — 3D 地球 + WebGL 平面地图
2. **500+ 精选新闻源** — 15 个分类
3. **国家不稳定指数（CII）** — 31 个一级国家的压力评分
4. **热点区域、海峡要道、级联分析**
5. **突发警报和关注列表**
6. **3 个仪表盘 Tab**

**关键结论**：免费版已经包含了核心的地图可视化、情报展示、新闻聚合功能。**收费的主要是 AI 对话、情景推演、数据导出和 MCP 接口。**

---

## 三、技术架构拆解

### 前端技术栈

| 层级 | 技术 |
|------|------|
| **UI 框架** | 原生 TypeScript（无 React/Vue，纯 Vanilla JS） |
| **构建工具** | Vite |
| **3D 地图** | globe.gl + Three.js |
| **2D 地图** | deck.gl + MapLibre GL |
| **可视化** | D3.js（时间线、雷达图、柱状图） |

### 桌面端

- **Tauri 2**（Rust 壳 + Node.js 侧边进程）
- 支持 macOS（Apple Silicon/Intel）、Windows、Linux
- API Key 存储在系统密钥链（Keychain/Credential Manager）
- 本地侧边进程运行 60+ API 处理器

### AI 系统（四层降级架构）

```
Tier 1: Ollama / LM Studio（本地，无云端）
    ↓ 超时/失败
Tier 2: Groq（Llama 3.1 8B，云端快速推理）
    ↓ 超时/失败
Tier 3: OpenRouter（多模型兜底）
    ↓ 超时/失败
Tier 4: Transformers.js（浏览器端 T5 模型，纯前端）
```

**免费关键**：全部使用本地 Ollama 或浏览器端推理，**不需要任何 API Key**。

### 后端架构

| 组件 | 说明 |
|------|------|
| **Vercel Edge Functions** | 60+ 边缘函数，静态 SPA |
| **Railway Relay** | WebSocket 中继、RSS 代理、Telegram 情报 |
| **Redis (Upstash)** | 三层缓存 |
| **Protocol Buffers** | 290 个 proto 文件，35 个服务 |
| **65+ 外部数据源** | 地缘政治、金融、能源、气候、航空、网络、军事等 |

---

## 四、免费复刻完整攻略

### 方案 A：直接使用 World Monitor（零成本，最快）

**适用**：只想用，不想自己开发

#### 步骤 1：部署 Web 版（免费）

```bash
git clone https://github.com/koala73/worldmonitor.git
cd worldmonitor
npm install
npm run dev
# 打开 http://localhost:3000
```

**无需任何 API Key**，直接运行。核心功能（地图、新闻、热点、不稳定指数）全部可用。

#### 步骤 2：部署桌面版（免费）

从 [worldmonitor.app](https://www.worldmonitor.app) 下载对应平台的桌面客户端：
- Windows: `.exe`
- macOS: `.dmg`（Apple Silicon / Intel）
- Linux: `.AppImage`

#### 步骤 3：接入本地 AI（可选）

安装 Ollama：
```bash
brew install ollama
ollama pull llama3.1:8b
```

在 World Monitor 设置中配置 Ollama 端点，即可使用本地 AI 对话，**零云端费用**。

#### 步骤 4：接入数据源（可选增强）

`.env.example` 中列出了所有可选的数据源凭证。免费使用不需要配置任何数据源，系统会使用默认的公共新闻源。

如果需要更专业的情报数据（卫星、军事基地、核设施等），可以：
- 使用公开 API（OpenStreetMap、OpenSky Network、GDELT 等）
- 配置 Telegram OSINT 频道

---

### 方案 B：完全自建（博主说的"完全复刻"）

**适用**：想要完全控制、接入卫星数据、去除所有云端依赖

#### 核心模块拆解

##### 1. 地图引擎（核心视觉）

```typescript
// 3D 地球 - globe.gl
import globe from 'globe.gl';

const world = new Globe()
  .globeImageUrl('/earth-blue-marble.jpg')
  .backgroundImageUrl('/space.jpg')
  .atmosphereColor('#3a228a')
  .atmosphereAltitude(0.2);

// 2D 地图 - deck.gl + MapLibre
import { MapView } from '@deck.gl/mapbox';
import { ScatterplotLayer } from '@deck.gl/layers';
```

**免费替代方案**：
- 地图底图：OpenStreetMap（免费）
- 卫星图：Sentinel-2（ESA 免费，通过 [Copernicus Browser](https://browser.dataspace.copernicus.eu/) 获取）
- 3D 地球：Three.js + NASA Blue Marble 贴图

##### 2. 新闻聚合

```python
# 免费新闻源
sources = {
    "RSS": ["BBC", "Reuters", "AP News", "Al Jazeera"],
    "API": ["GDELT 2.0", "NewsAPI (免费50次/天)", "Currents API"],
    "Telegram": ["OSINT 频道列表"],
    "Twitter/X": ["公共时间线爬虫"],
}
```

**关键免费数据源**：
- **GDELT 2.0** — 全球最大的事件监测数据库，完全免费（[gdeltproject.org](https://gdeltproject.org)）
- **OpenStreetMap** — 开源地图数据
- **OpenSky Network** — 全球航班追踪（免费 API，有速率限制）
- **Windy/Open-Meteo** — 气象数据
- **USGS** — 地震监测

##### 3. AI 分析引擎

```python
# 本地 AI 方案（零费用）
from ollama import chat

response = chat(
    model='llama3.1:8b',
    messages=[
        {
            'role': 'system',
            'content': '你是一个地缘政治情报分析师...'
        },
        {
            'role': 'user',
            'content': '分析以下新闻事件的地缘政治影响：...'
        }
    ]
)
```

**模型选择**：
- 快速推理：`llama3.1:8b`（8GB 显存）
- 高质量推理：`llama3.1:70b`（40GB+ 显存，或量化版 20GB）
- 浏览器端：`Transformers.js` + T5（无需 GPU）

##### 4. 卫星数据接入（博主说的"旧卫星"）

这是博主提到的下一步方向。免费卫星数据源：

| 卫星数据 | 获取方式 | 更新频率 |
|---------|---------|---------|
| **Sentinel-1**（SAR） | Copernicus Open Access Hub | 6 天 |
| **Sentinel-2**（光学） | Copernicus Open Access Hub | 5 天 |
| **Landsat 9** | USGS Earth Explorer | 16 天 |
| **NOAA**（气象） | NOAA CLASS | 实时 |
| **ISS 观测** | [spotthestation.nasa.gov](https://spotthestation.nasa.gov) | 可见时段 |

**关键**：不需要"旧卫星"，ESA 的 Sentinel 系列和 NASA 的 Landsat 都是**完全免费**的，分辨率足够做可视化。

##### 5. 情报信号检测

```python
# 使用 GDELT 的 GKG（全球知识图谱）检测热点
import requests

# GDELT 2.0 Event API（免费）
url = "https://api.gdeltproject.org/api/v2/doc/doc"
params = {
    "mode": "list",
    "maxrank": "1",
    "tonetransform": "0",
    "themelist": "1303,1304,1305",  # 军事冲突主题
    "timefilter": "24hour",
    "format": "json"
}
response = requests.get(url, params=params)
```

##### 6. 实时视频流

```html
<!-- 免费公开摄像头 -->
<video src="https://webcam-stream-url.m3u8"></video>

# 免费公开摄像头源：
# - www.livecam.io（全球数千个免费摄像头）
# - EarthCam（部分免费）
# - 政府公开摄像头（海关、港口等）
```

---

## 五、完整技术栈清单（全免费）

| 模块 | 技术选型 | 成本 |
|------|---------|------|
| 前端框架 | Vanilla TypeScript + Vite | 免费 |
| 3D 地图 | globe.gl + Three.js | 免费 |
| 2D 地图 | deck.gl + MapLibre GL + OSM | 免费 |
| 图表 | D3.js | 免费 |
| 桌面端 | Tauri 2 | 免费 |
| AI 推理 | Ollama + llama3.1:8b | 免费（需本地 GPU） |
| 新闻聚合 | GDELT + RSS + Telegram | 免费 |
| 卫星数据 | Sentinel/Landsat | 免费 |
| 航班追踪 | OpenSky Network | 免费（有限制） |
| 气象数据 | Open-Meteo | 免费 |
| 地震监测 | USGS API | 免费 |
| 部署 | Vercel / 自托管 | 免费（个人使用） |
| 缓存 | Redis (Upstash 免费层) | 免费（10MB） |

**总成本：$0**（前提是本地有 GPU 跑 Ollama）

---

## 六、商业模式分析

### World Monitor 为什么收费？

1. **云端基础设施成本** — 65+ 数据源 API 调用、Redis 缓存、Edge Functions
2. **AI 推理成本** — Groq/OpenRouter 的 API 费用
3. **数据许可证** — 部分专业数据源需要付费
4. **企业客户** — Enterprise 方案提供 SSO/RBAC/私有部署

### 免费用户的价值

- 对博主（抖音创作者）：免费 Web 版 + 桌面版已经足够做内容展示
- 对个人用户：核心功能（地图、新闻、热点）完全够用
- 对开发者：AGPL 协议允许自由修改和部署

### 博主说的"找旧卫星可免费接"

博主的意思是：
1. **先完全复刻** World Monitor 的开源部分
2. **再接入免费卫星数据**（Sentinel/Landsat 等）
3. 最终实现一个**完全免费、无云端依赖**的贾维斯系统

这是一个非常合理的技术路线。

---

## 七、一键部署脚本

```bash
#!/bin/bash
# World Monitor 快速部署脚本

# 1. 克隆项目
git clone https://github.com/koala73/worldmonitor.git
cd worldmonitor

# 2. 安装依赖
npm install

# 3. 可选：安装 Ollama 本地 AI
brew install ollama
ollama pull llama3.1:8b

# 4. 启动
npm run dev

# 5. 打开浏览器
open http://localhost:3000
```

---

## 八、与竞品对比

| 功能 | World Monitor | Palantir Foundry | MGRS | 自建方案 |
|------|:---:|:---:|:---:|:---:|
| 开源 | ✅ | ❌ | ❌ | ✅ |
| 免费使用 | ✅ | ❌ | ❌ | ✅ |
| 桌面端 | ✅ | ❌ | ❌ | ✅ |
| 本地 AI | ✅ | ❌ | ❌ | ✅ |
| 卫星数据 | 部分 | ✅ | ✅ | 需自建 |
| 企业级 | 需付费 | ✅ | ✅ | 需自建 |
| 上手难度 | 中 | 高 | 高 | 高 |

---

## 九、总结

**World Monitor 的"免费"实现逻辑**：

1. **核心功能开源** — 地图、新闻、热点全部免费，吸引用户
2. **AI 功能本地化** — 支持 Ollama，消除云端依赖
3. **收费的是增值服务** — AI 对话、情景推演、数据导出、企业部署
4. **数据源分层** — 免费层用公开数据，付费层用专业数据
5. **AGPL 协议** — 鼓励社区贡献，同时保护代码不被闭源商用

**博主的复刻路线完全可行**，而且成本极低。核心难点不在技术，而在**数据源的持续维护**和**AI 推理的本地化部署**。
