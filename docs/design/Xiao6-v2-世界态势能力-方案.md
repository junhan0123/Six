# 小6 v2 · 世界态势（World Awareness）能力方案

> 背景：用户研究开源项目 World Monitor（github.com/koala73/worldmonitor，Elie Habib，AGPL-3.0，~63k stars），
> 希望借鉴其「免费数据源 + 本地 AI」思路，构建**完全免费、无云端依赖的贾维斯世界态势感知**能力。
> 本文给出可行性结论 + 落到小6/JARVIS 架构的分阶段方案。本文件为**方案（Plan）**，未含代码改动。

## 0. World Monitor 核实结论（已联网核实）
- 真实项目：github.com/koala73/worldmonitor，作者 Elie Habib（koala73）✓
- Star：GitHub 实时检索 ~63.1k（用户引用的 77,306 为偏高快照/估计；其他源 56k/24.7k，量级一致 6 万+）
- 协议：**AGPL-3.0-only** ✓
- 技术栈：**Vite + 原生 TypeScript + Tauri2(Rust sidecar) + globe.gl/Three.js + deck.gl/MapLibre GL**，**非 Next.js**。
  AI/ML：Ollama / Groq / OpenRouter + Transformers.js（浏览器端）。`npm install && npm run dev` 正确（Vite）。
- 数据：聚合 65+ 提供商 / 500+ 精选 feed；航班数据**实际来自 Wingbits（商业 ADS-B）**，非直接 OpenSky；多变体 world/tech/finance/commodity/happy/energy。
- 关键修正：
  - 「完全不需要云端 Key」**仅在选 Ollama 本地路径时成立**；默认/Pro 用云端（Groq/OpenRouter）。
  - 卫星 Sentinel/Landsat 免费可获取，但需账号 + 处理管线（GDAL/瓦片化），非开箱即用。
  - 用户引用的免费数据源（GDELT/OpenSky/USGS/Open-Meteo/Sentinel/Landsat/Ollama）**全部真实免费**，是「免费贾维斯」的真正地基，与 World Monitor 代码归属无关。

## 1. 可行性结论
✅ **能做。** 核心数据层（GDELT / OpenSky / USGS / Open-Meteo）全部免费真实可用；本地 AI（Ollama + llama3.1:8b）真实可行。
⚠️ 但「完全免费 + 零云端」需同时满足：
  (a) LLM 切本地 Ollama（放弃 Agnes 云端大脑的质量/速度）；
  (b) TTS 也本地化（当前 edge_tts 是云端，需换本地 TTS 模型）；
  (c) 卫星影像 v1 **不建议**做（处理重、投入产出低）。
✅ 我们已有大量底座可复用：离线合规地图（map.js 无在线瓦片）、Open-Meteo 天气、本地 RAG（ONNX 零网络）、本地 ASR（faster-whisper）、HackerNews 热点、多 LLM 脚手架、主动智能 V2 引擎。

## 2. 关键决策（先定方向再动手）
- **D1 实现方式：不 fork，独立模块。**
  World Monitor 是 AGPL-3.0，fork 后若分发须开源对应改动。个人本地用虽无碍，但最干净的做法是：**学习其架构，在小6后端正写「世界态势」模块**（Python），前端新建面板复用现有 map.js / Three.js。避免许可证纠缠，且贴合小6既有一体化架构。
- **D2 LLM：默认保留 Agnes，新增本地 Ollama 作为「离线模式」可选大脑。**
  新增 `FEATURE_LLM_LOCAL` → 复用现有多 LLM 脚手架接 Ollama（llama3.1:8b）。这样「免费路径」存在但不强制牺牲体验；用户可随时切回 Agnes。
- **D3 路线位置：本能力 = P9 环境感知的核心组成；P8 常驻语音仍是「贾维斯常驻」的使能器。**
  建议 W0 数据层先落（低风险、高可见价值），P8 语音并行启动；两者叠加才是完整 JARVIS。

## 3. 分阶段计划
### Phase W0 · 数据层接入（后端 Python，尽量零新依赖）
- W0-1 **GDELT**：实时事件 + GKG/Tone 数据 → 热点事件流 + 国家不稳定性指数（CII 类，本地计算，无需云端）
- W0-2 **USGS 地震**：GeoJSON feed（无 Key）→ 事件流 + 地图标记 + 主动告警
- W0-3 **OpenSky**：states REST（匿名限速）→ 航班地图层（缓存 + 抽样，避免触发限流）
- W0-4 **Open-Meteo 扩展**（已有）→ 极端天气/灾害告警
- （W0-5 **Sentinel/Landsat**：暂缓，需 STAC API + 处理管线，v2 再评估）

### Phase W1 · 本地 AI 路径（可选离线大脑）
- `FEATURE_LLM_LOCAL`：Ollama(llama3.1:8b) 接入，复用多 LLM 脚手架
- 本地 TTS 选项评估（如本地语音模型）实现**真正零云端**语音闭环

### Phase W2 · 前端「世界态势」面板
- 复用 map.js（离线合规）+ 玻璃拟态令牌；新增地震 / 航班 / 热点标记层
- 不稳指数仪表 + 事件流时间线（premium.css 玻璃卡）
- 可选 lightweight 3D 地球（已有 Three.js，可加 globe.gl 或自绘点云地球）

### Phase W3 · 接入主动智能
- 不稳指数突变 / 强震 / 极端天气 → proactive 推送「老板，XX 发生 6.2 级地震」
- 与每日简报合并「今日世界态势」段

## 4. 风险与边界
- Ollama 8B 质量/速度依赖本机 GPU；纯 CPU 较慢（首 token 数秒~十几秒）
- OpenSky 匿名限速严苛，航班层可能稀疏（可接受，作为补充）
- GDELT 数据量大，需缓存 + 节流（可借鉴 World Monitor 的 3-tier 缓存思路）
- AGPL：个人本地用无碍；若日后分发须开源对应改动 → 故选独立模块自写
- 「零云端」硬要求需本地 TTS，否则语音仍走 edge_tts 云端

## 5. 与 P8 的关系
- **P8 常驻语音**：让贾维斯「随时在」（唤醒词 + 流式 TTS + 打断）
- **世界态势（本方案）**：让贾维斯「懂世界」（全球事件/灾害/不稳感知）
- 两者叠加 = JARVIS 的「常驻 + 主动 + 懂世界」。建议 W0 数据层先落，P8 语音并行。

## 6. 下一步（待用户拍板 D1/D2/D3 后启动）
- 若批准：先落 W0-1（GDELT）+ W0-2（USGS）作为最小可见闭环，真机验证后推进 W0-3/W0-4。
- 同步可并行启动 P8 语音脚手架（唤醒词 openwakeword）。
