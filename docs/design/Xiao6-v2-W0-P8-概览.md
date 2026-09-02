# W0 世界态势 + P8-1 常驻语音 · 落地概览

> 提交：`4dcb3f8`（纯本地，未 push）｜ 日期：2026-08-01

## 已完成

### W0-1 世界态势后端 `worldaware.py`
- 零密钥数据源聚合：**GDELT**（冲突新闻热度+语调）、**USGS**（M4.5+ 地震）、**OpenSky**（航班采样，匿名限速 10min 缓存）、**NASA GIBS**（真彩瓦片模板，零密钥）。
- 3 层缓存（内存热缓存 + `data/worldaware_cache.json` + 失败回退上次缓存）；任一源失败优雅降级，绝不抛异常中断主链路。
- 启发式**世界紧张指数 0–100**：新闻负面语调(35) + 地震显著度(30) + 常态底噪(15)；标签 平静/留意/紧张/高危。GDELT 无 tone 时退化为标题冲突词强度。
- 验证：`py_compile` 通过；离线 mock 测试确认降级路径与指数计算正确。

### W0-2 server 接入
- `GET /api/worldaware[?refresh=1]` 仿 `_handle_worldcup` 模式；import + 路由 + handler 三步就位。

### W0-3 前端面板 `world-monitor.js`
- `window.ZZWorld.open(data)`：后端推送则直渲，否则自取 `/api/worldaware`。
- 玻璃拟态面板：紧张指数仪表（变色彩条+分解）、地震列表（震级着色）、冲突新闻（语调标签）、航空脉搏（航班数+呼号）、卫星源信息、数据源状态徽章、刷新键。
- 接入：app.js panel 派发、command-palette.js「打开 世界态势」、index.html 引入并 bump 版本、styles.css 全套 `.world-*` 样式（响应式 760px 单列）。
- 验证：`node --check` 通过。

### P8-1 常驻语音唤醒词脚手架 `wakeword.py`
- 惰性导入 `openwakeword` + `sounddevice`（缺失不致命）；`FEATURE_ALWAYS_ON_VOICE` 缺失时默认关闭。
- `AlwaysOnVoice.start(detach_callback)` / `stop()`：监听线程用 sounddevice 取 int16 帧喂 openwakeword，超阈值 0.5 触发回调。
- server 接入 `GET /api/wakeword[?action=start|stop]` 状态/控制。
- 验证：导入安全、flag 缺失时 `start()` 优雅返回「未开启」，不崩溃。

## 待办 / 边界
- **W0-4** 主动智能推送（地震/紧张指数突变 → proactive；每日简报合并段）。
- **SAT-1** 卫星 GIBS 前端图层叠加（map.js WMTS 零密钥）。
- **P8-2** 流式 TTS + 打断续接。
- **P8-1 真机激活**：用户机器 `pip install openwakeword sounddevice` + 麦克风；在 `config.ENV_KEYS` / `reload()` 同步新增 `FEATURE_ALWAYS_ON_VOICE=true`；阈值需真机校准。
- **LLM-LOCAL** Ollama 离线大脑（`FEATURE_LLM_LOCAL` 复用多 LLM 脚手架）。

## 生效前提
后端为旧进程，需**用户重启 Electron + 前端 Ctrl+F5** 后加载新代码（含世界态势面板、唤醒词状态端点）。
