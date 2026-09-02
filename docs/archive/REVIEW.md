# 小6项目 · 全面审查报告

> 审查时间：2026-08-31 00:56 — 01:06
> 范围：UI 唯一性 / 后端运行时 / 前端现状 / 桌面启动链路 / 目录与空间 / 可恢复性
> 本轮**只审查，未做任何功能改动**（仅清理了我自己留下的 3 个临时文件）

---

## 〇、结论速览

| 项目 | 状态 |
| --- | --- |
| 活跃 UI | ✅ **只有 1 个**（`G:\six`） |
| 后端 | ✅ 满血（62 工具、自检全过、Agent 在线） |
| 前端对接 | ✅ 33 个真实端点，零 mock |
| **桌面客户端启动** | ⚠️ **断链**（启动器不拉起代理） |
| 旧 UI 残留 | ⚠️ `G:\xiao6-hub` 仍在（独立 Electron） |
| 空间 | ⚠️ 可安全回收 **约 1.7 GB** |
| 可恢复性 | ✅ Git 有 17 个 `D` 标记未提交，随时可还原 |

---

## 一、UI 唯一性审查

### 全盘 index.html 清点

| 路径 | 大小 | 判定 |
| --- | --- | --- |
| `six/index.html` | 11.5 KB | ✅ **唯一活跃 UI** |
| `xiao6/xiao6-ui/index.html` | 3.2 KB | ✅ 跳转页（探测 8765 → 跳新 UI），非独立 UI |
| `xiao6-hub/renderer/index.html` | 7.8 KB | ⚠️ **残留的旧 Electron UI** |
| `xiao6-ui/_ui_archive/xiao6-space-backup-20260831-0000/` | 230 KB | ✅ 我的备份（有意保留） |
| `xiao6-ui/_audit/snapshot_20260818_*/index.html` ×3 | 12 KB×3 | 归档快照（8-18） |
| `xiao6/docs/ui-consolidation/.bak/index.html` | 97.7 KB | 文档目录 .bak |
| `xiao6/third_party/UFO/**` | — | 第三方 UFO 项目，与小6无关 |
| `xiao6-ui/python/Doc/**`、`release/python/Doc/**` | — | Python 自带文档，非 UI |

### 结论

**运行时只有一套 UI**：`G:\six`（8765）+ 后端根路径跳转页（8000）。

但仍存在 **1 套未被清理的独立旧客户端**：

```
G:\xiao6-hub\
├── main.js / preload.js / renderer/index.html
├── node_modules/（含 electron）
└── 最后修改：2026-08-17（已停更 14 天）
```

**待你决定**：`G:\xiao6-hub` 是否一并删除（它是独立于 `xiao6-ui` 的旧 Electron 客户端，与现行架构无关）。

---

## 二、⚠️ 核心风险：桌面客户端启动链路已断

### 问题链条

```
双击 launcher/start.ps1
  → 启动后端 server.py（8000）
  → 等待 /api/health
  → 启动 Electron，打开 http://127.0.0.1:8000   ← launcher_config.json 写死
  → 8000 根路径 = 我写的智能跳转页
  → 跳转页 fetch http://127.0.0.1:8765/api/health
  → ✗ 8765 代理没启动（start.ps1 里根本没有这一步）
  → 显示「新界面未启动」指引页
```

`start.ps1` 第 2 行注释自述流程：
```
resolve paths -> check backend -> start backend if needed -> wait health -> start Electron -> logs/PID
```
**全程没有代理**。已验证 `start.ps1` 中无任何 `proxy` / `8765` 字样。

### 影响

- 浏览器直接访问 `http://127.0.0.1:8765/` → ✅ 正常
- **双击桌面启动器** → ❌ 打不开新 UI，停在指引页

### 三个修复方案（需你拍板）

| 方案 | 做法 | 优点 | 缺点 |
| --- | --- | --- | --- |
| **A（推荐）** | 改 `start.ps1` 增加「启动代理」步骤；`launcher_config.json` 的 `electron.url` 改为 `http://127.0.0.1:8765` | `G:\six` 仍是唯一真身，架构清晰 | 多一个进程 |
| **B** | 把 `G:\six` 三个文件同步进 `xiao6-ui/six/`，让 8000 直接 serve，弃用代理 | 只需一个服务，无跨域 | 两份文件（需同步脚本） |
| **C** | 桌面端弃用 Electron 壳，直接用浏览器打开 8765 | 最简单 | 失去桌面客户端形态 |

---

## 三、后端状态（满血）

```
端口     : 8000 LISTENING (PID 7020)
代理     : 8765 LISTENING (PID 46940)
模型     : agnes-2.5-flash @ agnes
AI       : 小6 · theme=light
工具     : 62 个已挂载
自检     : ok=True  degraded=[]  failed=[]
Agent    : enabled=true  state=IDLE  running=true  consecutive_failures=0
```

后端全程未被修改、未重启。

---

## 四、前端现状（`G:\six`）

```
index.html   11.5 KB   结构（7 个页面视图）
style.css    22   KB   six 视觉语言 + 红心 6 态
app.js       58   KB   真实对接逻辑
proxy.py     6.5  KB   静态 serve + /api 转发（SSE 流式透传）
AUDIT.md / CAPABILITY_MAP.md   文档
proxy.log    运行日志（可删，会自动重建）
```

**已接真实端点：33 个**，覆盖：

| 能力块 | 端点 |
| --- | --- |
| 对话 | chat(SSE) · chat/history · sessions · session/resume |
| 语音 | asr（multipart `audio`）· speak（TTS）· asr/status |
| 实时 | **stream**（EventSource 主动推送）· **agent/approval**（审批） |
| 能力 | capability_os/catalog（33 项）· health.tools（62 个） |
| 记忆 | memories · memory · memory/query · memory/conversations · memory/important-dates · notes · learnings · episodes |
| 任务 | tasks · goals · activity · trace |
| 知识 | knowledge |
| 设置 | config · version · user_model · ready · sysmon · logs |
| 环境 | briefing · weather · hotspots |

**诚实标注的未接**：`memory/write`（记忆页仍只读）、`calendar/*`、感知类（`perception/*`、`vision/*`、`kws`、`wakeword`）。

---

## 五、目录与空间审查

```
G:\xiao6\xiao6-ui\      3.0 GB   ← 主项目
  ├─ release/           1.2 GB   ← 打包产物
  │   └─ models/        1016 MB  ← ⚠️ 与上层 models 重复
  ├─ models/            1.0 GB   ← 本地 ASR 模型（语音依赖，不可删）
  │   ├─ whisper/        928 MB
  │   ├─ vosk/            66 MB
  │   └─ embed/           24 MB
  ├─ python/             457 MB  ← 嵌入式 Python（运行依赖）
  ├─ launcher/           270 MB  ← Electron 启动器（桌面端依赖）
  └─ node_modules/        19 MB
G:\xiao6\_ui_archive\    755 MB
  └─ pw_tmp/             720 MB  ← ⚠️ Playwright 临时文件，纯垃圾
G:\xiao6\third_party\    328 MB  ← 第三方 UFO（与小6无关）
G:\xiao6\screenshots\    234 MB  ← 历史截图
```

### 可安全回收（约 1.7 GB）

| 项 | 大小 | 说明 |
| --- | --- | --- |
| `_ui_archive/pw_tmp/` | 720 MB | Playwright 临时目录，纯垃圾 |
| `release/models/` | ~1 GB | 与 `models/` 内容重复的第二份副本 |

> `models/`、`python/`、`launcher/` **不可删** —— 分别是语音能力、运行环境和桌面端启动器的依赖。

---

## 六、可恢复性（三层保险）

| 层 | 状态 |
| --- | --- |
| ① 我的目录备份 | `_ui_archive/xiao6-space-backup-20260831-0000/`（17/17 文件，230 KB）✅ |
| ② Git 版本控制 | 17 个 `xiao6-space/**` 文件标记为 `D`，**尚未 commit** → `git checkout` 即可还原 ✅ |
| ③ 实时验证 | 删除后 `8000`/`8765`/后端 health 全部正常 ✅ |

---

## 七、遗留事项

1. **`G:\xiao6-hub`**（旧 Electron，7.8 KB renderer）仍在 —— 删不删等你定
2. **94 份 md 报告**堆在 `G:\xiao6` 根目录（AUDIT / PHASE / BETA / REPORT…）
3. **桌面启动链路断链**（见第二节，最高优先级）
4. `G:\xiao6` 根目录无 package.json，仍是"文档堆 + 多套前端"的历史遗留结构
5. Git 工作区有 23 项未提交变更（含我删的 17 个文件 + 改的 index.html）

---

## 八、建议的下一步（等你指令）

按优先级：

1. **修桌面启动链路**（方案 A/B/C 选一个）—— 否则桌面客户端打不开新 UI
2. **清理 `xiao6-hub`** —— 完成"只留一个 UI"
3. **回收 1.7 GB** —— 删 `pw_tmp` 与重复的 `release/models`
4. **补记忆写入** `memory/write` —— 记忆页从只读变可写
5. **整理 94 份 md 报告** —— 归档进 `docs/archive/`，让根目录清爽

**我现在停在这里，等你下指令。**
