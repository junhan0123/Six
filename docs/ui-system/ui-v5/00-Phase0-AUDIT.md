# Phase 0 · 能力审计（v5 全新构建前）

> 本阶段只审计、不改动。确认 v5 能复用哪些既有能力，划清红线边界。

## 一、可复用资产（只读引用，不复制、不修改）

| 资产 | 路径 | 角色 | 复用方式 |
|---|---|---|---|
| avatar-state.js | `xiao6-ui/avatar-state.js` | 8 态唯一颜色权威 | `<script src="../avatar-state.js">`；`AvatarState.META[state].color` 取色 |
| zz-events.js | `xiao6-ui/zz-events.js` | 事件名常量 + 事件总线封装 | `SYSTEM_EVENTS.AGENT_STATE` / `WAKEWORD_DETECTED` |
| sse-manager.js | `xiao6-ui/sse-manager.js` | 全局单例 SSE（连 `/api/stream`） | `ZZSSE.onMessage(cb)` 收原始 JSON；`ZZSSE.onState(cb)` 收连接态 |
| intent-gateway.js | `xiao6-ui/intent-gateway.js` | 意图派发 | `ZZIntentGateway.dispatch(text)` → `POST /api/agent/intent` |

**事件契约（不新增任何事件）**
- `agent_state`：SSE 推送，payload `{ state, goal_id?, progress? }`（runtime 态大写 IDLE/…；HTTP `/api/agent/state` 返回小写 `idle/…` 或 `disabled`）。
- `wakeword_detected`：SSE 推送，唤醒词命中。

## 二、API 端点（复用，不新增）

| 端点 | 用途 | v5 用法 |
|---|---|---|
| `GET /api/agent/state` | runtime 当前态 | 快照初始化 + 离线判定 |
| `GET /api/goals` | 目标列表（数组） | Context「正在」+ Overlay「目标」 |
| `GET /api/memories` | 记忆列表（数组） | Context「记得」+ Overlay「记忆」 |
| `GET /api/knowledge` | 知识 `{ docs:[...] }` | Context「理解」+ Overlay「知识」 |
| `GET /api/memories/graph` | 关系图 `{ nodes, edges }` | World Map |
| `POST /api/asr` | 前端录音字节 → 后端 FunASR/Vosk/Whisper 转写 | Voice Core 主路径（环境无模型时降级浏览器 STT） |
| `POST /api/kws` | 短音频唤醒判定（命中发 `wakeword_detected`） | 唤醒 |
| `GET /api/asr/status` | ASR 能力探针 `{ enabled }` | 决定走后端 ASR 还是浏览器 STT |
| `POST /api/agent/intent` | 意图入口 | Intent Line + 语音识别文字统一落点 |

## 三、静态服务与路由

- server.py 第 476–478 行是兜底静态服务：`os.path.join(dir, path)` 直接服务 `xiao6-ui/` 下任意真实文件。
- 因此建 `xiao6-ui/v5/` 后，`/v5/index.html`、`/v5/css/*`、`/v5/js/*` **自动可用**。
- 仅需在 `do_GET` 补一行 `if path in ("/v5","/v5/"): return self._serve_file("v5/index.html")`（与既有 `/v4/` 同模式）。属「启用性改动」，不碰 Agent / 事件 / 后端逻辑 / 旧代码。

## 四、关于 command-dock.js 的复用决策

`command-dock.js` 的 `sendText(text)` 逻辑：查找旧 UI 的 `#input/#btnSend`，命中则填入并点击；否则派发 `zz:command` 钩子事件。其 `init()` 会构建 `.os-dock-bar` 旧样式 DOM（属旧设计语言）。

**决策**：v5 是干净重写、不继承旧设计语言，因此**不加载 command-dock.js 的 DOM**。改为：
1. 复用其「意图派发契约」——v5 Intent Line 直接调用 `ZZIntentGateway.dispatch(text)`（与 command-dock 实际走的后端同一条路：`/api/agent/intent`）。
2. v5 监听 `window` 上的 `zz:command` 事件 → 转交 `ZZIntentGateway.dispatch`，使外部（含 command-dock）的 `sendText` 在 v5 仍生效。

→ 既"复用 command-dock 的 sendText 能力"，又不污染 v5 视觉。

## 五、红线边界（本任务严禁）

- ❌ 不新建 EventBus / State System / Runtime / Memory。
- ❌ 不新增 SSE 事件名（仅订阅既有 `agent_state` + `wakeword_detected`）。
- ❌ 不修改 `agent_runtime.py` / `eventbus.py` / `AppState` / `Goal` / `Memory` / `Knowledge` / `server.py` 的业务逻辑（仅追加一行静态路由）。
- ❌ 不恢复旧导航 / Galaxy 首页 / Dashboard / 聊天窗口。
- ❌ 不引入第二个聊天框；语音识别文字进入唯一 Intent Line。

## 六、v5 与 v4 的关系

- v4 保留不动（渐进替换）。v5 是独立目录、独立设计语言。
- v5 复用 v4 验证过的「数据真实形态」经验：记忆/目标返回数组、知识返回 `{docs}`、英文 slug 需中文映射、进度译成措辞不出现数字。

## 七、审计结论

能力齐备，无需重造任何 runtime。v5 只需：独立目录 + 复用共享库 + 复用 API + 订阅既有 SSE。可进入 Phase 1 设计规范。
