# Xiao6 v1.0.0 — UI Component Audit（Phase UI-P0 前置）

- 审计日期：2026-09-06
- 目标版本：**Xiao6 v1.0.0**（HEAD `9d5c690` / tag v1.0.0 → f5080e5）
- 审计范围：首页（Dashboard）相关前端资产、状态来源、API 映射
- 原则：不改后端契约 / 不删已有能力 / VERIFY-BEFORE-CHANGE / 不引入 ZZ·ZhuangZhou·庄周 历史资产
- 状态：**审计完成，等待确认后动手**

---

## 0. 结论先行 —— 2 个阻塞项（必须先拍板）

| # | 阻塞项 | 证据 | 影响 |
|---|--------|------|------|
| **B1** | 老板提供的截图 UI **与当前代码库不一致** | 截图导航为「首页/对话/工作/**通讯录**/记忆/**拓展中心**/**全局搜索**/系统状态/关于小6」，且存在**右栏**（今日日程 / 循环任务 / 系统状态）；而 `G:\Xiao6\ui\index.html` 导航为「首页/对话/工作/知识库/记忆/能力中心/全球洞察/系统状态/关于小6」，**无右栏**，全站 grep `通讯录` / `拓展中心` 命中 0，`今日日程` 在 index.html 命中 0 | 若按截图改，会改错文件。需确认改造目标是否为 `G:\Xiao6\ui`（现唯一正式 UI），或另有运行中的构建 |
| **B2** | 会话 rename / archive / delete **前端已调用、后端未实现** | `js/app.js:740` POST `/api/session/rename`、`:786` `/api/session/archive`、`:796` `/api/session/delete`；而 `server.py` 的 `do_POST` 仅有 `/api/sessions` `/api/session` `/api/session/resume`（1833/1835/1837），全仓 `*.py` grep `session/rename|archive|delete` 命中 **0** | 任务2 的 rename / delete 目前会 404。需选择：A) 新增最小 POST 端点（= 后端改动，需另开审批），B) 前端本地覆盖层（localStorage，不动 DB/契约） |

> 补充待确认：后端端口在 `launcher/launcher_config.json` 为 **8000**，而桌面启动脚本 `F:\桌面\小6启动.bat` 写的是 **8010**；`xiao6-space/` 静态目录已不存在（bat 中的 old URL 会 404）。

---

## 1. 首页入口文件

| 路径 | 角色 | 说明 |
|------|------|------|
| `G:\Xiao6\ui\index.html`（47.6 KB） | **唯一正式首页入口** | `server.py` 注释「UI CONSOLIDATION：优先托管唯一正式 UI（G:\xiao6\ui\index.html）」(`server.py:1743`)，`_resolve_ui()` 优先解析该目录 |
| `G:\Xiao6\xiao6-ui\server.py`（115.7 KB） | 后端 + 静态托管 | do_GET / do_POST 单体实现 |
| `G:\Xiao6\xiao6-ui\index.html` | 遗留入口 | 与 `xiao6-ui/` 同级，疑为历史 UI，**未确认是否废弃**（UI CONSOLIDATION 后应不再首选） |
| `G:\Xiao6\xiao6-ui\launcher\electron-app\main.js` | Electron 壳 | `TARGET_URL = http://127.0.0.1:8000/` |
| `G:\Xiao6\xiao6-ui\_ui_archive\` | 归档 UI 备份 | 禁止作为改造基线 |

---

## 2. 首页 DOM 结构（`ui/index.html`）

| 区块 | 容器 | 行号 | P0 归属 |
|------|------|------|---------|
| 侧边栏 · 品牌行 + 连接指示灯 | `.brand-row` / `#liveDot` | 20–23 | 任务3（红/绿语义） |
| 侧边栏 · 主导航 | `#nav` | 25–62 | — |
| 侧边栏 · **最近对话（= 会话列表）** | `#recentList` | 65–68 | **任务2** |
| 首页 · 页面头 | `.page-head` | 90–93 | 任务1 |
| 首页 · Dashboard 卡片网格 | `#dashGrid` | 94–96 | **任务1 / 任务3** |
| 首页 · Agent Activity Center | `#activityCenter` / `#activityPanel` / `#activityCount` | 99–110 | P2（保留） |
| 首页 · AI Insight Center | `#intelligenceFeed` / `#feedList` | 113–130 | P1（迁移到 Insight/Foresight 入口） |
| 首页 · 未来关注 Foresight | `#foresightPanel` | 133+ | P1 |
| 首页 · 快捷入口 | `#quickChips` | — | P1 |

---

## 3. JS 组件清单

| 文件 | 大小 | 职责 | 首页相关关键函数（行号） |
|------|------|------|--------------------------|
| `ui/js/app.js` | 138.6 KB | 主逻辑：视图切换、Dashboard、会话、右键菜单 | `loadDashboard()` 238–256<br>`weatherCard()` 300–343<br>`taskCard()` 345–392<br>`hotspotCard()` 433–470<br>**`systemCard()` 533–563**<br>`dashCard()` 570–576<br>**`loadRecent()` 581–609**<br>`cleanSessionLabel()` 286–290<br>`deriveSessionTitle()` 611–622<br>`enrichRecent()` 624–637<br>`resumeSession()` 639–652<br>`createContextMenu()` 660+（rename 740 / archive 786 / delete 796） |
| `ui/js/command_bar.js` | 6.7 KB | 底部指令条 | 与首页输入框并存，P1 需定主次 |
| `ui/js/gfe-dashboard.js` | 11.3 KB | 全球洞察面板 | 非首页首屏，P1 迁移目标 |
| `ui/js/work_filters.js` / `work_health.js` | 7.7 / 4.5 KB | 工作区筛选与健康 | 不直接影响首页 |
| 全局状态 | — | `const S = {...}` | **app.js:79–96** |

---

## 4. CSS 依赖

| 文件 | 大小 | 内容 | 备注 |
|------|------|------|------|
| `ui/css/style.css` | 59.8 KB | **Design Token（`:root` 4–29）+ 全站样式** | 101 处 `border-radius`、57 处硬编码色值；红色硬编码 10 处 |
| `ui/css/gfe-dashboard.css` | 6.1 KB | 全球洞察 | `:root` 无自建 |
| `ui/css/s142-system.css` | 4.4 KB | 系统状态页 | `:root` 无自建 |
| `ui/css/s144-command.css` | 14.7 KB | 指令条 | `:root` 无自建 |

---

## 5. API 映射（首页相关）

| 前端调用 | 后端实现 | 状态落点 | 任务影响 |
|----------|----------|----------|----------|
| `GET /api/weather` (app.js:244) | `server.py:753` | 本地变量 `w` → `weatherCard()` | P1 并入 Today Card |
| `GET /api/tasks` (app.js:245) | `server.py:1160` | `S.tasks`（app.js:349） | P1 并入 Today Card |
| `GET /api/hotspots` (app.js:246) | `server.py:751` | 本地变量 `h` → `hotspotCard()` | P1 迁移到 Insight/Foresight 入口（**不删除**） |
| `GET /api/health` | `server.py:280` | `S.health` | **任务1**：`systemCard()` 读取 `self_check.checks`，是「需要检查」红字来源 |
| `GET /api/ready` | `server.py:330` | `S.ready` | 任务1：仅用于健康入口判定 |
| `GET /api/config` | `server.py:1791` | `S.config` | **任务1**：`llm.model` 被直接显示在首页（模型名属开发态信息） |
| `GET /api/sessions` (app.js:584) | `server.py:1833` | `S.sessions` | **任务2**：会话列表数据源（当前 `slice(0,6)`、无分组） |
| `GET /api/session?session_id=` (app.js:626) | `server.py:1835` | `enrichRecent()` 补全标题 | 任务2：自动生成标题的数据基础 |
| `POST /api/session/resume` (app.js:641) | `server.py:1837` | — | 任务2：保留 |
| `POST /api/session/rename` (app.js:740) | **不存在** | — | **B2** |
| `POST /api/session/archive` (app.js:786) | **不存在** | — | **B2** |
| `POST /api/session/delete` (app.js:796) | **不存在** | — | **B2** |
| `GET /api/version` (x2) | `server.py:669` | 版本号展示 | 保持 v1.0.0 |
| `GET /api/capability_os/catalog` | `server.py:1344` | 能力中心 | 不受影响 |
| `GET /api/self_awareness/status` | `server.py:1372` | 自省状态 | 不受影响 |

> 结论：P0 三个任务**均可在不改后端契约的前提下完成**，唯一例外是任务2 的 rename/delete（见 B2）。

---

## 6. Design Token 现状（`ui/css/style.css:4–29`）

| 类别 | 现状 | 目标 | 差距 |
|------|------|------|------|
| 品牌色 | `--brand:#ff4d4f` / `--brand-soft` / `--brand-tint` / `--brand-glow` | `brand` | ✅ 已有 |
| 中性色 | `--ink-1..4`、`--bg`、`--bg-soft`、`--line`、`--line-soft` | `neutral` | ✅ 已有（无统一前缀，建议加 `--neutral-*` 别名） |
| 语义色 | `--ok:#52c41a`、`--warn:#faad14`、`--info:#1890ff` | `warning` / `danger` | ⚠️ **`--danger` 缺失**，危险态直接硬编码 `#ff4d4f`（style.css:109/110/456） |
| 圆角 | `--r-sm:8px`、`--r-md:12px`、`--r-lg:16px`、`--r-xl:22px` | 8 / 12 / 16 | ⚠️ `--r-xl:22px` 越界（需收敛或限定用途），另全文件 101 处 `border-radius` 硬编码待治理 |
| 间距 | **无 spacing token**（`--sp*` 命中 0） | 8 / 16 / 24 | ❌ 需新增 `--sp-1/2/3` |
| 红色使用 | 10 处硬编码 `255,77,79 / #ff4d4f` | 仅品牌强调 / 当前 session / 危险操作 | ⚠️ 需逐个判定：品牌爱心、`.live-dot.offline`（style.css:56）、`status-warn`、context-menu danger、hotspot rank 等 |

---

## 7. 任务级改动面（确认后执行的具体位置）

### 任务1 · 首页开发信息清理
- 主要对象：`app.js:533–563 systemCard()`
  - 移除/收敛：模型名 `llm.model`（550）、「需要检查」文案（549/551）、`failed.length ? "需要关注"`（552）、`[查看]` 跳转（559）
  - 目标形态：仅保留 **系统健康状态入口**（一个状态点 + 跳转「系统状态」页），详情全部下沉到 `#view-system`
- 次要：`#liveDot` 离线红点（style.css:56）→ 改为中性/琥珀，红色留给品牌与危险操作
- 不改：`/api/health`、`/api/config`、`/api/ready` 契约与调用（仅改渲染）

### 任务2 · Session 列表升级（ChatGPT/Hermes 风格）
- 渲染：`app.js:593–603`（当前 `slice(0,6)`、无分组、无 hover 操作入口，仅右键菜单）
- 标题：`cleanSessionLabel()` 286–290（正则清洗）+ `deriveSessionTitle()` 611–622 + `enrichRecent()` 624–637（异步补全）→ 统一为「自动生成标题」策略
- 分组：新增 Today / 7 Days / Earlier（基于 `s.updated_at || s.created_at`）
- hover 操作：rename / pin / delete
  - rename：依赖 B2 方案（后端缺失）
  - pin：**无后端字段**，按「不改 DB」要求 → 前端 localStorage 置顶集合（会话 id 列表）
  - delete：依赖 B2 方案
- 当前 session 高亮：新增 `.recent-item.active`（左侧红色指示条，红色受限用途之一）
- **不修改数据库结构、不改 `/api/sessions` 契约**

### 任务3 · UI Design Token
- 文件：`ui/css/style.css:4–29`
- 新增：`--danger`、`--sp-1:8px` / `--sp-2:16px` / `--sp-3:24px`、`--neutral-*` 别名
- 收敛：`--r-xl:22px` → 归入 16px 或限定用途并注释
- 红色治理：10 处硬编码逐条判定，非「品牌/当前 session/危险操作」场景改中性或琥珀
- 同步：`s144-command.css` / `s142-system.css` / `gfe-dashboard.css` 无自建 token，可继承

---

## 8. 红线自检

| 红线 | 状态 |
|------|------|
| 不改后端 API 契约 | ✅ P0 三任务均为渲染层；B2 需单独审批 |
| 不删除已有能力 | ✅ 热点资讯属 P1 **迁移**而非删除；系统状态卡片下沉为入口 |
| VERIFY-BEFORE-CHANGE | ✅ 本文档即为前置物，确认后再改 |
| 保持 Xiao6 v1.0.0 | ✅ 不触碰 `VERSION` / 版本号逻辑 |
| 禁止引入 ZZ / ZhuangZhou / 庄周 资产 | ✅ 本次不引用任何历史资产；`LEGACY_NAME_REGISTER.md` 作为校验基线 |

---

## 9. 回归与验收准备

- 回归测试位置：`G:\Xiao6\xiao6-ui\tests\`（pytest 套件，含 e2e / agent / policy）
- 静态自检：`node --check` 对 `ui/js/*.js`；`ui/test/` 目录含 `test_context_menu.html`（右键菜单用例，任务2 必跑）
- 验收产出（P0 完成时）：
  1. 修改文件清单（含行号级 diff 摘要）
  2. API 影响检查（本次：无契约变更；B2 若选 A 则单列）
  3. UI 前后对比截图（首页 + 会话列表 hover/active 三态）
  4. 回归测试结果（测试命令需老板确认基线命令）
  5. 单个 git commit（不 amend、不 force）

---

## 10. 待确认（请老板拍板后开工）

1. **B1**：改造目标确认为 `G:\Xiao6\ui` 吗？截图那套 UI（含右栏、通讯录、拓展中心）在哪台/哪个目录运行？
2. **B2**：会话 rename / delete 走 A（新增后端端点，需另批）还是 B（前端 localStorage 覆盖，零后端改动）？
3. 后端端口 8000 还是 8010？（影响截图验收时访问哪个地址）
4. P0 是否允许同时落地任务3 的 token 新增（纯新增变量，不改视觉语义）？
