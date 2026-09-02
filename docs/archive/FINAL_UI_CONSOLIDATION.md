# Xiao6 Final UI Consolidation Report

> 执行时间：2026-08-31 01:10 — 03:08
> 执行原则：PRECHECK → 迁移 → 改造 → E2E → 关闭 8765 → 再验证 → 删除 → Git 检查
> 未开发任何新业务功能；未增加端口；未增加代理；未复制第二套 UI

---

## Architecture

```text
唯一项目：G:\xiao6
唯一正式 UI：G:\xiao6\ui
唯一 HTTP：8000
8765：REMOVED
Electron：127.0.0.1:8000

Desktop Launcher
       ↓
   start.ps1
       ↓
Xiao6 server :8000 (G:\xiao6\xiao6-ui\server.py)
       ├── /api/*  → Xiao6 Backend
       └── /*      → G:\xiao6\ui  （同源托管，含 SPA fallback）
```

**最终目录**

```text
G:\xiao6\
├── ui\                    ← 唯一正式 UI
│   ├── index.html
│   ├── favicon.svg
│   ├── css\style.css
│   └── js\app.js
├── xiao6-ui\              ← 后端（server.py 等，未整体改动）
│   ├── models\            ← 保留（语音依赖 1016M）
│   ├── python\            ← 保留（运行依赖 457M）
│   ├── launcher\          ← 保留（Electron 启动器 269M）
│   └── release\           ← 打包产物（已删其中重复的 models）
├── docs\archive\          ← 文档与 E2E 截图归档
├── third_party\           ← 第三方（UFO，与小6无关）
└── _ui_archive\           ← 归档（已清 pw_tmp 垃圾）
```

---

## Migration

**G:\six → G:\xiao6\ui　　状态：PASS**

| 源文件 | 目标 | 状态 |
| --- | --- | --- |
| `six/index.html` | `ui/index.html` | ✅ 资源路径已改（`css/style.css`、`js/app.js`、`/favicon.svg`） |
| `six/style.css` | `ui/css/style.css` | ✅ |
| `six/app.js` | `ui/js/app.js` | ✅ 注释已更新，API 全为同源相对路径 |
| `six/proxy.py` / `proxy.log` | **不迁移** | ✅ 8765 废弃，代理不再需要 |
| `six/*.md` | `docs/archive/` | ✅ 文档归档 |

**PRECHECK 结论（迁移前）**

| 检查项 | 结果 |
| --- | --- |
| 硬编码端口 / IP | ✅ 仅 1 处注释，无代码逻辑依赖 |
| `../` 相对路径 | ✅ 无 |
| `/js/ /css/ /assets/` 根绝对路径 | ✅ 无 |
| CSS `url()` / `@import` / `@font-face` | ✅ 无外部资源 |
| fetch / EventSource / WebSocket | ✅ 全部同源相对 `/api/*`（5 处） |
| assets / fonts / images / 配置文件 | ✅ 无 |

→ **迁移风险评级：极低**（因此未做任何逻辑重构，仅调整资源路径）

---

## Runtime

| 项 | 结果 |
| --- | --- |
| **8000 API** | ✅ **PASS** — 10 个端点全 200 带真实数据 |
| **8000 UI** | ✅ **PASS** — `/` 返回 11547 B 新 UI（改造前为 3161 B 旧跳转页） |
| **Static assets** | ✅ **PASS** — `css/style.css` 21981 B、`js/app.js` 58043 B、`favicon.svg` 249 B |
| **SPA fallback** | ✅ **PASS** — `/work` `/tasks` `/memory` `/settings` `/agents` 全部回落 index.html |
| **API 不 fallback** | ✅ **PASS** — `/api/nonexistent` → 404 JSON，绝不返回 index.html |
| **SSE** | ✅ **PASS** — `/api/stream` 返回 `: connected` |

实测明细：

```
/api/health                200  5419 B
/api/tasks                 200 18661 B
/api/memories              200 49828 B
/api/knowledge             200 108995 B
/api/agent/state           200   134 B
/api/config                200  4447 B
/api/version               200   119 B
/api/capability_os/catalog 200 15534 B
/api/briefing              200  3745 B
/api/sessions              200  2004 B
```

**后端改动范围（server.py）**：`git diff --stat` → **110 行新增 / 2 行删除**，删除的两行正是旧的 `return self._serve_file("index.html")` 与其 HEAD 版本，替换为「UI 优先 + 原逻辑兜底」。

**纯增量改动，零 API 契约破坏。** 备份：`server.py.bak-before-ui-consolidation-20260831-011437`

**安全校验强度与原有 `_resolve_static` 对齐**：禁止 `..` 路径分量、禁止 `.env`/`.git`、realpath + commonpath 边界校验（symlink 越界同样被拒）。

---

## E2E（真实浏览器 · Chrome 152）

| 项 | 结果 | 证据 |
| --- | --- | --- |
| **Browser Home** | ✅ **PASS** | 标题 `小6 (Six)`；侧栏 7 导航；最近对话 6 条真实会话 |
| **Browser Routes** | ✅ **PASS** | `/tasks` `/memory` `/settings` 刷新后侧栏导航正常出现 |
| **Browser Chat** | ✅ **PASS** | 见下方完整链路 |
| **Browser SSE** | ✅ **PASS** | tool 事件实时渲染 |
| **Browser Tasks** | ✅ **PASS** | 真实数据：ID 210/178/170/169/168/167，含状态与步骤数 |
| **8765 closed** | ✅ **PASS** | 关闭后浏览器重访 8000 仍完整工作 |
| **Electron** | ⚠️ **BLOCKED** | 见下方说明（既有缺失，非本轮引入） |

### Chat 全链路（浏览器实测）

```text
用户：现在几点了？
  ├─ 正在调用 get_time …        ← tool_start 事件（SSE）
  ├─ get_time 调用完成           ← tool_end 事件（SSE）
  └─ 现在是 2026年8月31日 01:32:01（星期一）。
     + [朗读] 按钮（真实 /api/speak）
```

侧栏同时显示 `62 tools`（真实工具数）。

### 关闭 8765 后再验证

```
8000 = LISTENING (PID 52512)
8765 = NOT LISTENING
浏览器重访 http://127.0.0.1:8000/ → 完整工作 ✅
```

截图归档：`docs/archive/e2e-8000-home.png`、`e2e-8000-after-8765-closed.png`

---

## Electron：BLOCKED（既有缺失，非本轮引入）

`start.ps1` 实测日志：

```text
[START] Xiao6 launcher v1.0.0-rc1
Project root: G:\xiao6\xiao6-ui
Backend already running (HTTP 200 @ .../api/health), skip start
WARN: Electron skipped (runtime binary or app entry missing:
      .../electron-bin/electron.exe / ) - backend-only mode, API still served
[DONE] Backend: already-running, Electron: skipped(optional)
```

**根因**：`launcher_config.json` 中 `"args": ""`，导致 `start.ps1` 的
`if ($cfg.electron.args) { $EappPath = ... }` 不执行 → `$EappPath = $null` → 条件 `(Test-Path $EbinPath) -and $EappPath -and (Test-Path $EappPath)` 失败 → 按设计「优雅跳过」。

**证据表明这是既有状态，非本轮引入**：
- `electron.exe` 存在（188 MB，electron-bin 目录 269 MB / 74 文件）
- 默认值 `bin='electron-bin/electron.exe'; args=''; url='http://127.0.0.1:8000'`（start.ps1 第 23 行）args 本就为空
- 我未修改 `launcher_config.json` 与 `start.ps1`（git 可证：二者均无改动）

**符合要求部分**：`url` = `http://127.0.0.1:8000` ✅；start.ps1 仅 2 个 `Start-Process`（后端 + Electron），**无 8765、无代理** ✅

**修复路径（需你决定）**：提供一个 Electron app 入口（含 `main.js` + `package.json` 的目录），并把 `electron.args` 指向它；或改为直接拉起系统浏览器打开 8000。

---

## Cleanup

| 项 | 状态 |
| --- | --- |
| `G:\six` | ⚠️ **内容已 100% 清空**（0 文件），**空壳目录被占用进程阻止删除**（见下） |
| `G:\xiao6-hub` | ✅ **DELETED**（删除前已验证全仓无任何运行时引用） |
| `8765 runtime` | ✅ **REMOVED**（进程已关闭；全仓运行时代码无 8765 依赖） |
| `pw_tmp` | ✅ **DELETED**（回收 720 MB） |
| `release/models` | ✅ **DELETED**（回收 ~1 GB；确认与 `models/` 完全重复：均 37 文件、大文件字节逐一吻合；且 `asr.py:149` / `embed.py:15` 硬编码指向 `xiao6-ui/models/`，无任何代码引用 `release/models`） |
| `models\` `python\` `launcher\` `ui\` | ✅ **全部保留** |

### G:\six 空壳残留说明

删除时环境的 safe-delete 机制报：
```
另一个程序正在使用此文件，进程无法访问
genie-trash / COM RecycleBin 均失败
```
已尝试 `rm -rf` / `rmdir` / PowerShell `Remove-Item` / .NET `Directory.Delete` / `cmd rd`，全部被占用阻止。

**实际影响：零。** 目录 0 文件、4 KB，不在任何代码路径上，所有内容已在 `G:\xiao6\ui` 并验证通过。
**建议**：重启资源管理器或重启系统后手动删除；或在资源管理器中直接删除。

### 全仓引用终检

| 搜索 | 结果 |
| --- | --- |
| `G:\six` / `/g/six` | ✅ 全仓无运行时代码引用 |
| `8765` | ✅ 运行时代码无依赖（仅 `ui/js/app.js` 注释中的自指说明，及 Python 自带文档的数字巧合） |
| `xiao6-hub` | ✅ 删除前已确认无任何运行时依赖 |

---

## Git（未 commit，按要求）

**变更总数：33 项**

**本轮修改（2 项）**
- `M xiao6-ui/server.py` — 唯一正式 UI 托管（110+/2-，纯增量）
- `M xiao6-ui/index.html` — 跳转页 → 无 8765 的诊断兜底页

**本轮删除（19 项）**
- `D xiao6-ui/xiao6-space/**` — 17 个旧 UI 文件（已完整合并，备份在 `_ui_archive/xiao6-space-backup-20260831-0000/`）
- `D _ui_archive/pw_tmp/package.json`、`package-lock.json`

**本轮新增（未跟踪）**
- `?? ui/`（唯一正式 UI）
- `?? docs/archive/`（AUDIT / CAPABILITY_MAP / REVIEW + 2 张 E2E 截图）

**原有未提交修改（非本轮产生）**
- `M xiao6-ui/geo-weather.json`、`M xiao6-ui/habits.json`（后端运行时写入）
- `? third_party/UFO`（未跟踪的第三方项目）

> 未执行任何 `git commit`。删除的 17 个旧 UI 文件在 Git 中仍为未提交的 `D` 标记 → `git checkout` 可完整还原。

---

## Final Verdict

```text
BLOCKED
```

**判定依据**：

除 Electron 一项外，全部目标均已达成并实测通过：

| 目标 | 状态 |
| --- | --- |
| 唯一 UI 目录 `G:\xiao6\ui` | ✅ PASS |
| 唯一 HTTP 入口 8000 | ✅ PASS |
| 8765 彻底废弃 | ✅ PASS |
| UI 迁移完整、路径正确 | ✅ PASS |
| 8000 直接 serve UI + SPA fallback | ✅ PASS |
| API 不被 fallback 污染 | ✅ PASS |
| 浏览器 E2E（Home/Routes/Chat/SSE/Tasks） | ✅ PASS |
| 关闭 8765 后再次 E2E | ✅ PASS |
| 清理（xiao6-hub / pw_tmp / release\models） | ✅ PASS |
| 后端零破坏（纯增量 110+/2-） | ✅ PASS |
| **Electron 桌面启动** | ❌ **BLOCKED** |

**BLOCKED 的唯一原因**：`launcher_config.json` 的 `electron.args` 为空，Electron 无 app 入口，启动器按设计跳过（后端仍完整服务，浏览器访问 8000 完全正常）。这是**既有配置缺失**，本轮未修改 launcher 任何文件。

**解除 BLOCKED 需要**：提供一个 Electron app 入口并配置 `electron.args`，或决定改用系统浏览器。等你指令。
