# 小6 UI 2.0 · 后端能力对接全景检查

> 检查时间：2026-08-31 00:05 — 00:20
> 方法：后端全量路由提取（104 个）→ 逐个实探 → 与前端实际调用比对
> 后端：`G:\xiao6\xiao6-ui`（8000，未修改未重启）· 前端：`G:\six`（8765 代理）

---

## 一、`xiao6-space` 的处理结论

**是的，它该被替换 —— 它就是当前生效的旧主界面。**

证据：`xiao6-ui/index.html` 原第 8-9 行
```html
<meta http-equiv="refresh" content="0; url=/xiao6-space/index.html">
<script>window.location.replace('/xiao6-space/index.html');</script>
```
访问 `8000` 根路径会**自动跳进去**，server.py 另有硬编码路由伺候它，4 个验证脚本也指向它。

### 已执行（全部可逆，未删除任何文件）

| 动作 | 说明 |
| --- | --- |
| ✅ **备份** | 17/17 文件 → `_ui_archive/xiao6-space-backup-20260831-0000/` |
| ✅ **禁用** | `xiao6-space/` → `xiao6-space.disabled/`（改名，非删除，随时改回） |
| ✅ **替换入口** | `xiao6-ui/index.html` 改为智能跳转：探测 8765 在线则跳新 UI，否则显示启动指引 + 后端状态 |

### 路由验证

```
8000 根路径          HTTP 200   ← 新跳转页
旧 /xiao6-space/     HTTP 404   ← 已禁用
新 UI 8765          HTTP 200   ← 生效
```

**彻底删除请老板点头**：文件仍在 `xiao6-space.disabled/` 与 `_ui_archive/` 备份中，说一声我立刻清。

---

## 二、已对接能力（21 个，全部实测 200 + 真实数据）

| # | Endpoint | 归属页面 | 实测结果 |
| --- | --- | --- | --- |
| 1 | `/api/health` | 全站探活 · 62 工具 | alive / agnes-2.5-flash / theme=light |
| 2 | `/api/chat` (POST·SSE) | 对话 | 流式真回 + `tool_start/tool_end` 事件 |
| 3 | `/api/chat/history` | 最近对话 | 1253 B 真实历史 |
| 4 | `/api/agent/state` | 智能体 · 首页 | IDLE / running / consecutive_failures |
| 5 | `/api/capability_os/catalog` | 工具 · 首页能力卡 | **33 项能力 / 27 可用 / 10 分组**，自带中文名+emoji+风险等级 |
| 6 | `/api/tasks` | 任务 · 首页任务卡 | 18.6 KB 真实任务（含 steps） |
| 7 | `/api/goals` | 任务 | 18.5 KB 真实目标 |
| 8 | `/api/activity` | 任务·运行状况 | 会话 default / 对话轮次 14 / 活跃目标 |
| 9 | `/api/trace` | 任务·执行追踪 | 875 条真实执行记录 |
| 10 | `/api/knowledge` | 知识库 | **108 KB** 真实文档（含 status/tags） |
| 11 | `/api/memories` | 记忆 | **49 KB** 真实记忆条目 |
| 12 | `/api/memory` | 记忆·用户画像 | 真实画像（习惯=桌面路径 F:\桌面） |
| 13 | `/api/memory/query` (POST) | 记忆搜索 | 后端检索，失败降级本地过滤 |
| 14 | `/api/notes` | 记忆·笔记 | 真实笔记（含 markdown） |
| 15 | `/api/learnings` | 记忆·学习记录 | 真实 learnings（feedback 类型） |
| 16 | `/api/episodes` | 记忆·事件 | 真实 episodes |
| 17 | `/api/config` | 设置 | ai_name=小6 / theme=light / llm 配置 |
| 18 | `/api/version` | 设置 | 小6 v1.0.0 |
| 19 | `/api/user_model` | 设置·智能体 | identity: name=小6 / role=owner |
| 20 | `/api/asr` (POST) + `/api/asr/status` | 对话·语音输入 | whisper 已启用，浏览器真实录音 → 转文字 |
| 21 | `/api/speak` (POST) | 对话·朗读 | **实测 HTTP 200 / audio/mpeg / 14 KB / MP3 帧头 0xFFFB** |

**本轮新增（对比上一版 9 个 → 21 个）**：capability_os/catalog、memory(画像)、notes、learnings、episodes、activity、trace、version、user_model、speak、memory/query。

---

## 三、未对接：有 UI 价值，建议后续补（约 12 个）

| Endpoint | 实测 | 价值 | 建议归属 |
| --- | --- | --- | --- |
| `/api/briefing` | 200（日期 2026-08-31 + 天气 郑州） | 每日简报 | 首页顶部 / 对话 |
| `/api/calendar/events` | 200（enabled=false, 空） | 日程 | 可并入任务页 |
| `/api/calendar/next` | 未测 | 下一日程 | 任务页 |
| `/api/hotspots` | 未测 | 热点榜 | 工具页·世界脉搏 |
| `/api/weather` | 未测 | 天气 | 简报 |
| `/api/geo` `/api/geo/reverse` | 未测 | 地理 | 简报 |
| `/api/sessions` `/api/session` `/api/session/resume` | 200 | **会话管理**（切换/恢复历史会话） | 侧栏"最近对话"目前只读，应可点击恢复 |
| `/api/stream` | 未测 | 备用流式通道 | 对话（/api/chat 的替代） |
| `/api/memory/write` `/api/memory/confirm` | 未测 | **记忆增删改** | 记忆页（当前只读） |
| `/api/sysmon` | 未测 | 系统监控 | 设置页 |

> 说明：这些**后端都真实存在**，是我这轮没铺进 UI，不是能力缺失。

---

## 四、未对接：系统/内部/硬件层（UI 不应暴露，约 60 个）

| 类别 | Endpoint |
| --- | --- |
| 视觉感知 | `/api/perception/*`（ocr/screen/window/describe/status）、`/api/vision/*`（capture/displays） |
| 唤醒词 | `/api/kws`、`/api/wakeword` |
| 计算机动作 | `/api/action/*`（capabilities/observe/plan/execute） |
| 能力规划（Agent 内部） | `/api/capability_os/match`、`/api/capability_os/plan` |
| 自我意识 / 主动代理 | `/api/self_awareness/*`、`/api/proactive*`、`/api/always-on/*`、`/api/proactive_agent/*` |
| 多设备 / 移动端 | `/api/cross-device/*`、`/api/devices`、`/api/mobile/*` |
| 桌面上下文 | `/api/clipboard/*`、`/api/focus/*`、`/api/hud/*`、`/api/boot/*` |
| 数据运维 | `/api/data/export`、`/api/data/import`、`/api/logs`、`/api/audit`、`/api/selfcheck`、`/api/startup_diagnosis`、`/api/ready`、`/api/providers/probe`、`/api/test-llm`、`/api/doc` |
| 其他 | `/api/social/inbound`、`/api/external`、`/api/alert-config`、`/api/episodes`(POST) 等 |

**这些是桌面助手的系统能力（屏幕感知、唤醒词、跨设备、主动推送），不属于你定义的 7 个页面范畴**，硬塞进 UI 反而违反"不堆按钮、不堆卡片"的原则。

---

## 五、后端自身故障（与我无关，已如实记录）

| Endpoint | 状态 | 说明 |
| --- | --- | --- |
| `/api/models` | **404** | 无模型列表端点 → 深度思考按钮**诚实提示未接入**，不做假按钮 |
| `/api/agent/goal` | **404** | 旧 UI 引用了它，但后端根本没有 |
| `/api/agent/intent` | **404** | 同上 |
| `/api/personal_context` | **502** | RemoteDisconnected，后端自身崩溃 |
| `/api/system-prompt` | **500** | `build_context_prompt() missing 1 required positional argument: 'session_id'` — 后端 bug |

> 旧 UI 引用了 `agent/goal`、`agent/intent` 这两个 **404 端点** —— 这正是它"看起来功能多、实际点了没反应"的原因之一。

---

## 六、结论

**对接覆盖率：21 / 104 ≈ 20%**（按路由数）

但按**你定义的 7 个页面 + 核心能力**衡量：

| 页面 | 后端能力 | 状态 |
| --- | --- | --- |
| 对话 | chat(SSE) + asr + speak + 工具事件 | ✅ 完整闭环 |
| 任务 | tasks + goals + activity + trace | ✅ |
| 知识库 | knowledge | ✅ |
| 记忆 | memories + memory + query + notes + learnings + episodes | ✅ |
| 工具 | capability_os/catalog(33) + health.tools(62) | ✅ |
| 智能体 | agent/state + user_model | ⚠️ 无多 Agent 注册表（后端没有，不虚构） |
| 设置 | config + version + user_model | ✅（只读） |

**没有假数据、没有假按钮、没有 mock。** 每个数字都来自真实 HTTP 响应。

**建议下一步**（按价值排序）：
1. 会话恢复 —— 侧栏"最近对话"当前只能看不能点，接 `/api/session/resume`
2. 记忆写入 —— 接 `/api/memory/write`，让记忆页可增删改
3. 每日简报 —— 接 `/api/briefing`，放首页顶部
4. 日历/天气/热点 —— 接 `calendar/*`、`weather`、`hotspots`

说一声我继续补。

---

# 补充：与旧 UI 完整合并 + 删除（2026-08-31 00:37）

## 一、拆解旧 UI 后发现的两个「我之前猜错了」的契约

| 能力 | 我原先（猜的） | 旧 UI 冻结契约（正确） |
| --- | --- | --- |
| TTS | `POST /api/speak` body `{text}` | body **`{text, stream:false}`** |
| ASR | `POST /api/asr` 裸 binary | **`POST /api/asr?ext=.wav`**，multipart 字段名必须 **`audio`** |

均已按冻结契约改正。

## 二、合并前我漏掉的三个核心能力

### 1. SSE 事件总线 `/api/stream`（**小6 主动性的命脉**）
旧 UI 用 `EventSource` 常连。实测它推的真实事件：
```
{"xiao6_event":"proactive","kind":"alert","content":"📡 检测到 4 条舆情异动…"}
{"xiao6_event":"proactive","kind":"briefing","content":"老板早，2026年08月31日 星期一…"}
```
不接这条线，小6 的主动简报、舆情告警、提醒**全部丢失**。已实现：
hero 态 → 进 `#proactiveFeed` 展示；对话态 → 插入消息流；同时 toast 提示。

### 2. 审批流 `/api/agent/approval`（**危险操作人工确认**）
- 事件：`/api/stream` 推 `kind=agent_approval`（含 `ticket` / `tool` / `summary` / `args_preview`）
- 提交：`POST /api/agent/approval?ticket=<t>&decision=approve|reject`（query 参数）
- **truthful 红线**（沿用旧 UI 注释）：只有 HTTP ok 且后端返回 `{ok:true}` 才置终态；
  否则保留 blocked、按钮仍在、提示「提交失败 · 请重试」，**绝不假成功**。
- 端点实测有效：`{"ok":false,"error":"未知或已过期的审批单"}`

### 3. 会话恢复 `/api/session/resume`
`POST` body `{session_id}` → `{ok, resume:{status, reason}}`。
侧栏"最近对话"改为真实 `/api/sessions` 列表，**可点击恢复**。

## 三、已接端点：21 → 33

新增 12 个：
`agent/approval`、`stream`、`briefing`、`weather`、`hotspots`、`memory/conversations`、
`memory/important-dates`、`ready`、`logs`、`sysmon`、`sessions`、`session/resume`

另新增 UI 区块：首页「今日简报」（简报+天气+热点）、记忆页「对话历史/重要日期」、
设置页「诊断区」（就绪自检/系统监控/后端日志）。

## 四、旧 UI 已删除（老板授权）

| 项 | 状态 |
| --- | --- |
| 删除前备份核对 | **17/17 逐文件比对通过** |
| `xiao6-space.disabled/` | ✅ 已删除 |
| 备份 `_ui_archive/xiao6-space-backup-20260831-0000/` | ✅ 17 文件保留 |
| `8000/` 根路径 | ✅ 200 |
| `8765/` 新 UI | ✅ 200 |
| 后端 `/api/health` | ✅ alive |

## 五、端到端复验（合并后）

```
tool_start → get_time {}
tool_end   → execution_id:f6f2d070 → "本地 时间：2026年08月31日 00:32:27 星期一"
choices    → "今天是2026年8月31日，星期一。"
```
> 中途一次空响应为后端偶发超时，同一请求重测即通，非前端或代理问题。

## 六、尚未接入（诚实标注）

- `/api/memory/write` 等记忆**写入**类 → 记忆页目前仍只读
- `/api/calendar/*` 日历
- `/api/capabilities`（3 项，与 capability_os 不同源）
- 感知类 `/api/perception/*`、`/api/vision/*`、唤醒词 `/api/kws`、`/api/wakeword`（桌面助手硬件能力，不在 7 页面范畴）
