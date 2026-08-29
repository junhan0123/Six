# Phase 2–6 · 实施报告（v5 全新构建）

> 从零建立 `xiao6-ui/v5/`，独立设计语言，不继承 v4 视觉。全部为表现层，零架构/零新功能/零新事件/零后端逻辑改动（仅追加一行静态路由）。

## 一、目录结构

```
xiao6-ui/v5/
├── index.html              全新 DOM（顶部/AI Core/Voice/Context/Intent/Ambient/Overlay）
├── css/ui-v5.css           全新设计语言（深色·留白·单色·微动效）
└── js/
    ├── data-adapter.js     复用 /api/* + 订阅既有 SSE（agent_state / wakeword_detected）
    ├── ai-core.js          8 态颜色 100% 来自 avatar-state.META；驱动 #presence[data-state]
    ├── context-layer.js    三句自然语言（正在/记得/理解），无卡片/无数字
    ├── intent-line.js      唯一入口；ZZIntentGateway.dispatch；setText 供语音
    ├── voice-presence.js   Voice Core 五态；/api/asr + 浏览器 STT 降级 + 唤醒
    ├── world.js            World Map（SVG 2D 关系网，默认隐藏）
    ├── overlay.js          Spotlight 式能力展开（⌘1–5）
    └── boot.js             接线：快照→态→Context→Overlay；时钟；SSE 订阅
```

共享库通过 `../` 只读引用（不复制、不修改）：`avatar-state.js` / `zz-events.js` / `sse-manager.js` / `intent-gateway.js`。

## 二、逐文件关键改动

### index.html（重写）
- 顶部：仅 `● 小6` + 时间。**删除**「AI OS / Presence Space」等一切自述。
- 中心：`.core__stage` 内含 `.orb`（aura/halo/ring/core/sat/particles 六层）+ `#voiceOrb`（Voice Core，贴附核心右下方）。
- Identity 区：小6 / 状态人话 / 当前任务。
- Context：三行 `ctx--doing/memory/knowledge`（行内 `<em>` 强调实体）。
- Intent：底部居中胶囊表单（`#intentInput` + `#intentSend`）。
- Ambient：5 个静默点（hover 显字）。
- Overlay：scrim + sheet（kicker/title/close/body）。

### ui-v5.css（重写，171 规则）
- 令牌：背景 `#06070b`；--core-* 由 JS 注入；系统字体 + 等宽数据。
- AI Core 六层：aura(呼吸) / halo(自转+脉动) / ring(conic 扫掠) / core(呼吸+内禀 shimmer) / sat(环绕卫星) / particles(微粒轨道)。
- 八态分档（`[data-state=...]`）：不只换色，改 aura/halo/ring 周期、particles 可见度与速度、core glow 强度。
- Voice Core：`.voice` 柔光按钮；`[data-voice=...]` 驱动 ring/wave 波纹、thinking 频率、speaking 声波、error 警示。
- Context / Intent / Ambient / Overlay 全套样式；`prefers-reduced-motion` 降级。

### ai-core.js
- `injectColor(state)`：从 `AvatarState.META[state].color` 取色，注入 `--core-color/--core-soft/--core-glow/--core-line`（唯一来源，不硬编码）。
- `applyState`：设 `#presence[data-state]`，同态不重注入防闪烁。
- `speak`：八态人话，首帧直落、后续 150ms 换气淡出。
- `setDoing`：当前任务乐观反馈。

### context-layer.js
- `pickGoal`（去重取进展最大者）、`cleanMemory`（去机器前缀）、`pickMemory`（salience 降序）、`domainLabels`（英文 slug 中文映射、丢纯 ASCII）、`progressWord`（措辞无数字）。
- 三句：`正在 <em>标题</em> · 措辞` / `记得 <em>记忆</em>` / `理解 你的世界包含 <em>域</em>…`。
- 5s 限频防跳动；导出内部函数供验证。

### intent-line.js
- `submit` → `ZZIntentGateway.dispatch(text)`（与语音同一链路）。
- `setText(value, interim)`：供语音实时填入；interim 不发送，终态发送。
- 中文输入法 `compositionstart/end` 拦截 Enter 误提交。
- 监听 `zz:command`（复用 command-dock 的 sendText 能力）。

### voice-presence.js
- 五态 `idle/listening/thinking/speaking/error`（`#voiceOrb[data-voice]`）。
- 优先后端 `/api/asr`（FunASR/Vosk/Whisper）；不可用时降级浏览器 `SpeechRecognition(zh-CN)`；`/api/asr/status` 探测。
- `wakeword_detected` SSE 命中 → 自动聆听。
- 识别文字 → `V5Intent.setText` → 唯一 Intent Line。
- 快捷键 Ctrl/Cmd+Shift+U。

### world.js
- `render(container)`：取 `/api/memories/graph`，SVG 2D 关系网（中心 小6 + 环绕节点 + 边），默认不渲染，仅 Overlay「世界」内展示。

### overlay.js
- `open(type)`：⌘1–5 / ambient 点击 / Esc 关闭。
- 每类首行引导语（sheet__lead）+ 行式列表；焦点管理（打开聚焦关闭键、关闭归还原焦点）。

### boot.js
- 定态 → 说话 → 420ms 后 Context → Overlay 取快照；实时订阅 `agent_state`；时钟。

## 三、server.py 改动（唯一后端改动，启用性）
`do_GET` 追加一行：
```python
if path in ("/v5", "/v5/"):
    return self._serve_file("v5/index.html")
```
与既有 `/v4/` 同模式，**不碰 Agent/Runtime/EventBus/API 逻辑**。运行时进程需重启一次才会启用 `/v5/` 干净 URL；当前可用兜底 `/v5/index.html`（server.py 自带静态兜底已 200 验证）。

## 四、红线遵守证据
| 红线 | 遵守 |
|---|---|
| 不新增 Runtime | 未写任何 runtime |
| 不新增 Event | v5 仅订阅既有 `agent_state`+`wakeword_detected`；唯一 `zz:command` 是既有事件兜底 |
| 不修改 Agent | 未动 `agent_runtime.py` |
| 不恢复旧导航/Galaxy/Dashboard/聊天 | 结构全新，无上述元素 |
| 不污染旧代码 | 旧文件只读引用；仅增一行静态路由 |
