# Xiao6 AI OS · Final Interface Reconstruction v6 — Phase 0 · Audit

> 目标：彻底重建小6 AI OS 主界面（`final/`），不继承 v5/v4/旧 UI 设计语言。
> 本次审计只确认「可复用资产」与「不可逾越红线」，为设计与实现定界。

---

## 1. 可复用资产（只读引用，禁止修改）

所有共享库位于 `xiao6-ui/` 根目录，v6 通过 `../xxx.js` 引用，**只读**。

| 资产 | 路径 | 作用 | v6 用法 |
|---|---|---|---|
| avatar-state.js | `xiao6-ui/avatar-state.js` | **8 态唯一权威**（IDLE/WAITING/THINKING/PLANNING/EXECUTING/COMPLETED/ERROR/OFFLINE），含 `META[state].color` / `.label` | AI Core 与 Voice Core 的**全部颜色/标签唯一来源**，不自行定义色值 |
| zz-events.js | `xiao6-ui/zz-events.js` | 事件名单一来源；系统事件 `SYSTEM_EVENTS.AGENT_STATE='agent_state'`、`WAKEWORD_DETECTED='wakeword_detected'` | 仅作为 SSE 解析的字段常量参考 |
| sse-manager.js | `xiao6-ui/sse-manager.js` | 全局单例 SSE：`ZZSSE.onMessage(cb)`（原始 JSON 串来自 `/api/stream`），`ZZSSE.onState(cb)`，`ZZSSE.getState()` | 订阅 `agent_state` + `wakeword_detected` |
| intent-gateway.js | `xiao6-ui/intent-gateway.js` | `ZZIntentGateway.dispatch(text)` → `POST /api/agent/intent` | Intent Channel 与 Voice 识别文字落点唯一出口 |
| command-dock.js | `xiao6-ui/command-dock.js` | 旧输入条（`#input`/`#btnSend` DOM + `zz:command` 兜底） | **仅复用其 dispatch 契约思路**，不加载其 DOM（会污染新设计）；v6 直接走 `ZZIntentGateway.dispatch` |

---

## 2. 后端 / 数据契约（经验证，v5 已确认）

| 端点 | 方法 | 返回形态 | v6 用途 |
|---|---|---|---|
| `/api/agent/state` | GET | `{enabled, state, current_goal, ...}`；runtime 关闭时 `{enabled:false, state:"disabled"}` | 首屏/快照 runtime 态 |
| `/api/goals` | GET | 数组，`g.to_dict()`：`{id,title,description,status,progress,horizon,...}` | 上下文「正在」 |
| `/api/memories` | GET | 数组（记忆行）：`{id, content/text/memory, salience, type, ...}` | 上下文「记得」 |
| `/api/knowledge` | GET | `{docs:[{domain/type,...}], stats:{...}}` | 上下文「理解」 |
| `/api/memories/graph` | GET | `{nodes:[...], edges:[...]}` | World Understanding Map |
| `/api/asr` | POST | 音频字节 → `{text/transcript}` | Voice Core 后端转写（降级用） |
| `/api/asr/status` | GET | `{enabled:bool}` | 探测后端 ASR 能力 |
| `/api/agent/intent` | POST | `{text}` → intent 网关 | 意图投递（唯一写入口） |
| `/api/stream` | SSE | `data: {"xiao6_event":"agent_state","state":"...",...}` 等 | 实时态回流 |

**SSE 解析约定（沿用 v5 已验证）**：`m.xiao6_event || m.event` 取事件名；`agent_state` 读 `m.state`，`wakeword_detected` 直接透传。

---

## 3. 服务器（server.py）静态托管

- `do_GET` 末尾 catch-all（约 L478-480）：`fp = os.path.join(root, path.lstrip("/")); if os.path.isfile(fp): _serve_file(...)`。
- 结论：**任何真实文件均可被静态托管**，无需改动后端。
- `/final/index.html`、`/final/css/*`、`/final/js/*`、`/final/components/*` 均可直接访问。
- 干净 URL `/final` 需一行路由（与 `/v4` `/v5` 同构）；但用户明确「禁止修改 Backend 逻辑」，**本次不改 server.py**，入口定为 `/final/index.html`（catch-all 已可服务）。

---

## 4. 红线（Hard Constraints）

1. ❌ 不新建 Runtime / EventBus / AppState / 后端逻辑。
2. ❌ 不新增任何事件（不 `publish`、不 `new CustomEvent` 业务语义、不扩展 zz-events）。
3. ✅ SSE **仅订阅** `agent_state` + `wakeword_detected`（系统事件，非领域事件）。
4. ✅ 数据 **只读 Adapter**：只 `fetch` `/api/*` 与订阅既有 SSE。
5. ❌ 不加载旧 UI 脚本（app.js / main-orb / galaxy / three / solar-system / companion）。
6. ❌ 不复制旧 UI 视觉（玻璃卡片、Dashboard、左导航、太阳系、多 Panel）。
7. ✅ 颜色/标签唯一来源 = `avatar-state.js` `META`。

---

## 5. 与 v5 的关键差异（避免继承旧设计语言）

| 维度 | v5 | v6 / final |
|---|---|---|
| Ambient | 底部横向 5 项文字导航 | **环绕 AI Core 的少量光点**（记忆/知识/任务/世界），hover 显字，点击原地展开 Overlay |
| AI Core | 6 层 orb | 「存在体」：核心光体 + 呼吸系统 + 状态/声音/思考反馈，**8 态差异更强**（粒子数/速度/亮度/声音） |
| 声音 | 无 | **Web Audio 轻量声音反馈**（状态切换柔和音 + 语音态），受用户手势 + 静音开关约束 |
| Overlay | Spotlight 表单 | Spotlight + 世界理解图（2D 关系网）内置「世界」面板 |
| 视觉 | 深色但偏装饰 | Apple Intelligence / Nothing OS / Linear / Claude / JARVIS：克制、留白、比例、空间；无彩色渐变、无玻璃卡片、无重阴影 |

---

## 6. 结论

可在 **不触碰后端、不新增事件、不修改共享库** 的前提下，于 `xiao6-ui/final/` 完整实现 v6。所有数据通道与视觉权威均已就绪。
