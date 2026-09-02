# 小6 v2 · W0-4 主动推送 + SAT-1 卫星图层 — 落地概览

> 承接 W0-1~3（世界态势后端+面板）与 P8-1（常驻语音脚手架），本轮把「世界态势」做成可主动感知、可叠加真彩卫星影像的完整能力。
> 提交：`0a85c56`（W0-4+SAT-1 源码与文档）。

## 一、世界态势面板在哪看

- **命令面板** → 输入/选择「打开 世界态势」（🌍 图标）。
- 或任意位置代码触发 `window.ZZWorld.open()`；后端主动推送世界事件时也会自动打开并直渲 payload。
- ⚠️ 当前你是旧后端进程：需**重启 Electron**（`F:\桌面\start-xiao6.bat` 双击）+ 前端 **Ctrl+F5** 强刷，才能拉到新代码与 `/api/worldaware` 后端。

## 二、W0-4 主动智能推送（proactive.py）

**触发机制**： heartbeat 每 `WORLDAWARE_INTERVAL`(默认 600s=10min) 扫描一次世界态势，受新开关 `FEATURE_WORLD_AWARE_PUSH`（默认开，可 `/api/config` 或 `.env` 瞬切关闭）门控。

**两类推送**（去重、绝不刷屏、源降级则静默）：

1. **地震预警**：USGS 中 M6.0+ 地震，按 `地点|震级|时间` 签名去重（meta 保留最近 30 条）；同一地震只推一次。
2. **紧张指数突变**：与上次分数比对，Δ≥15 或跨档升入「紧张/高危」（≥55）才推；首轮建立基线不误报。

**每日简报**新增世界态势段（紧张指数 + 过去 24h 最大地震），失败静默跳过。

**前端**：主动消息 `kindLabel` 增加 `world: '世界态势'`，世界事件在对话流/日志以专属标签呈现。

## 三、SAT-1 卫星 GIBS 图层（world-monitor.js + styles.css）

- 面板内新增「🛰️ 卫星影像」区块与开关按钮。
- 点击「显示卫星真彩图层」→ 拉取 `/api/worldaware` 的 GIBS 模板，将 `Level9` 降为 `Level2`，渲染 **4×4=16 张全球真彩瓦片**（NASA MODIS Terra True Color，零密钥）。
- 瓦片 `loading=lazy`、单张失败 `onerror` 隐藏；再次点击收起。开关始终渲染（即便经推送打开、无 gibs 数据也能用）。
- **合规设计**：离线地图 `map.js` 仍保持纯文字、零瓦片；卫星作为世界态势面板内的**显式 opt-in 网络功能**叠加，不触碰合规底线。

## 四、文件改动清单

| 文件 | 改动 |
|---|---|
| `xiao6-ui/proactive.py` | 新增 `WORLDAWARE_INTERVAL` 常量、`_scan_worldaware()`；接入 `_tick_once`；`make_daily_briefing()` 加世界态势段 |
| `xiao6-ui/config.py` | 注册 `FEATURE_WORLD_AWARE_PUSH`（声明/global/reload/ENV_KEYS 四处同步，默认开） |
| `xiao6-ui/app.js` | 主动消息 `kindLabel` 加 `world`；bump 版本 |
| `xiao6-ui/world-monitor.js` | 卫星图层开关 + GIBS 瓦片网格渲染；`worldSat` 始终渲染；bump 版本 |
| `xiao6-ui/styles.css` | `.world-sat-btn/.world-sat-grid/.world-sat-tile`（2:1 玻璃网格）；bump 版本 |
| `xiao6-ui/index.html` | bump app/world-monitor/styles 三处版本号 |

## 五、验证

- `py_compile`（config/proactive/worldaware/server）✅；`node --check`（world-monitor/app）✅。
- 离线冒烟：M7 地震首扫推 1 条、二扫去重 0 条；源不可用静默 0 条 ✅。
- 已提交 `0a85c56`（精确排除 `geo-weather.json`/`habits.json`/`devices.json` 等运行时数据）。

## 六、下一步

- **P8-2** 流式 TTS + 打断续接
- **LLM-LOCAL** Ollama 离线大脑（`FEATURE_LLM_LOCAL`）
- W0 面板真机验证（你重启 Elect地的 + Ctrl+F5 后看效果）
