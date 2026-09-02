# 小6 UI 增强交付总览（2026-07-27）

提交：`7c8f48a` · 分支：`master` · 工作树干净

## 本次完成的内容

### 1. 天气 — 先定位再拉取 + 修复"请求异常"
- 前端 `weather.js`：打开天气面板先用 `navigator.geolocation` 定位（超时 8s 回退 `/api/geo` IP 定位，再回退默认城市），把 `lat/lon` 拼到 `/api/weather?lat=&lon=`。
- 后端 `server.py` `_handle_weather` 接收 `lat/lon`，覆盖 city 为 `"lat,lon"`。
- **修复 null 报错**：`renderCard` 全部写入改用 `safeSet`/`safeHtml` 防御式封装，消除 `Cannot set properties of null (textContent)` 崩溃。
- **修复坐标退化 bug（关键）**：`get_weather` 原先用 `urllib.parse.quote(city)`，把坐标逗号变成 `%2C`，wttr.in 无法识别 → 退化为服务端 IP 城市。改为坐标形式（`^\d+(\.\d+)?,\d+(\.\d+)?$`）**原样拼 URL**。实测 `39.9,116.4`→北京、`31.2,121.5`→上海（白莲泾）。

### 2. 语音球优化（参考白龙马）
- 主球放大；**外圈装饰环固定纤细**（不随主球放大，`border-width:.8px`）。
- idle 状态 Y 轴自转加速（×2.6）+ CSS 呼吸动画，无活动时也自转。
- 开启对话后 `.app.has-messages .orb-wrap` 自动移至左下角（38px、160px）并保持可见，不再被消息流遮挡。

### 3. 设置菜单（在白龙马基础上增量）
- 新增 `settings.js` + 设置面板（外观 / 语音 / 模型 / 天气 / 系统 / 快捷键 6 个 tab）。
- 主题三选项（深空/极光/跟随系统）、动画级别、TTS 音色/语速/自动朗读、模型 `temperature` 滑块（实时回写并透传到聊天请求与后端 `run_fc_loop`）、默认城市、主动推送开关、常用功能快捷入口卡片（记忆/热点/天气/自检/看板）、清除会话。
- 全局快捷键：`Ctrl/Cmd+N` 新建、`Ctrl/Cmd+,` 设置、`Ctrl/Cmd+/` 聚焦输入。

### 4. 右侧面板改造
- 改为白龙马风格"自主行动机制 · Tick"面板（状态/节点/连线/tok·s/召回·h/抽取·h + 流），认知指标收敛为 约束/记忆/知识/衰减 4 项。
- 后端 `_handle_chat` 收 `temperature` → `llm.py agnes_completion(temperature)` → `tools.py run_fc_loop(temperature)` 全链路透传。

## 验证结果
- `node --check`：app.js / main-cognitive.js / voice-orb-simple.js / weather.js / settings.js / main-orb.js 全部通过。
- `py_compile`：llm.py / server.py / tools.py / geo_weather.py 通过。
- 后端实测：index.html / styles.css / settings.js / weather.js 均 200；`/api/weather?lat=39.9&lon=116.4` 返回北京（坐标生效）。
- `pytest tests/`：**62 passed**（managed venv，仅 sandbox 回收站告警，无失败）。
- ID 一致性：`settings.js` + `main-cognitive.js` 引用的全部 DOM id 在 `index.html` 中均存在（无 null 风险）。
- `ruff check` 通过（2 文件 format）。

## 需注意
- **本机正在运行的 server 是改前的旧实例**（sandbox 内 pkill/ps 不可靠，无法安全重启）。请在本地手动重启后端，才能生效 `geo_weather.py` 的坐标修复与 temperature 透传。
- 设置中的 TTS 音色/语速当前仅存 `localStorage`（`xiao6_settings_v1`），尚未回写到 `/api/speak` 的 voice/rate 参数 —— 若需"设置真正改变朗读音色"需再改 `_handle_speak`。
