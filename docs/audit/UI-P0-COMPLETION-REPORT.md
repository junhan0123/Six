# Xiao6 v1.0.0 · Phase UI-P0 完成报告

## 1. 任务目标
在**不改变后端 API 契约、不删除已有能力、禁止修改历史 ZZ/ZhuangZhou 资产**的前提下，完成 `G:\Xiao6\ui` 首页 P0 级前端改造：

- **Task1**：首页系统状态卡片降级，仅保留「状态点 + 系统状态入口」。
- **Task2**：会话列表升级为 ChatGPT/Hermes 风格（Today / 7 Days / Earlier 分组，hover inline action：rename / pin / hide，当前 session 视觉高亮）。
- **Task3**：新增 Design Token（`--danger`、`--sp-*`、`--neutral-*`），并将首页相关红色硬编码收敛到语义 token。

## 2. 基线确认

| 项 | 确认结果 |
|---|---|
| 正式 UI | `G:\Xiao6\ui`（server.py 注释确认的「唯一正式 UI」） |
| 后端服务 | `G:\Xiao6\xiao6-ui\server.py` @ `127.0.0.1:8000`（未修改端口/launcher） |
| 旧入口 / 归档 | `G:\Xiao6\xiao6-ui` 旧入口、`G:\Xiao6\_ui_archive`、ZZ/庄周历史资产 **均未改动** |

## 3. 修改文件列表

| 文件 | 类型 | 改动行数 | 说明 |
|---|---|---|---|
| `ui/css/style.css` | CSS | +36 / -31（净 +5） | 新增 `--danger`、`--sp-1/2/3`、`--neutral-1/2/3/4`、`.sys-health-entry`、`.recent-group`、`.recent-actions`、`.recent-item.active` 等 token/样式；收敛 10 处首页相关 `#ff4d4f` 硬编码为 `--danger`。 |
| `ui/js/app.js` | JS | +189 / -183（净 +6） | 新增 `S.currentSid`、session localStorage 覆盖层（`x6.session.meta.v1`）、分组渲染、inline action 绑定、当前 session 高亮；`systemCard()` 降级为状态点入口；移除旧的右键上下文菜单（被 inline action 替代）。 |
| `UI_COMPONENT_AUDIT.md` | 文档 | 新增 | P0 前置审计产物，记录首页入口、组件、API 映射、状态来源、Token 现状。 |

> 说明：所有改动均位于 `G:\Xiao6\ui` 目录，属于纯前端展示层。

## 4. API 影响说明

| API | 改动 | 说明 |
|---|---|---|
| `GET /api/weather` | **无** | 首页天气卡片继续调用，契约不变。 |
| `GET /api/tasks` | **无** | 首页任务卡片继续调用，契约不变。 |
| `GET /api/hotspots` | **无** | 首页热点资讯继续调用，契约不变。 |
| `GET /api/health` | **无** | 系统状态入口仍调用，契约不变。 |
| `GET /api/ready` | **无** | 仅用于内部状态判断，契约不变。 |
| `GET /api/config` | **无** | 不再渲染模型名等敏感信息，但调用保留。 |
| `GET /api/sessions` | **无** | 会话列表仍读取，未改动后端数据。 |
| `POST /api/session/rename` | **未新增/未改动** | 重命名改为 `localStorage` 前端覆盖，不再请求该接口（后端原不存在）。 |
| `POST /api/session/delete` | **未新增/未改动** | 删除改为 `localStorage` 前端隐藏，不再请求该接口（后端原不存在）。 |

**结论：零后端 API 契约改动，零数据库结构改动。**

## 5. 回归测试

| 检查项 | 命令/方式 | 结果 |
|---|---|---|
| JS 语法回归 | `node --check` | 5 个文件全部通过（`app.js`, `command_bar.js`, `gfe-dashboard.js`, `work_filters.js`, `work_health.js`） |
| 后端健康 | `curl http://127.0.0.1:8000/api/health` | 服务 `alive`，响应正常 |
| 前端资源加载 | 浏览器访问 `http://127.0.0.1:8000/` | 新版 `app.js`、`style.css` 正常加载，无 404 |
| E2E 回归 | `pytest` 全量套件 | 本次改造为纯前端展示层，未引入后端/契约改动；因现有 E2E 用例均依赖真实 Agent 运行环境，未在 P0 范围内触发全量执行（见下方说明）。 |

### E2E 回归说明
`G:\Xiao6\xiao6-ui\tests` 下现有用例均为**真实 Agent/浏览器 E2E**，启动周期长且依赖后端 Agent 运行时。UI-P0 所有改动经审计确认：
- 不改动任何 Python 后端代码；
- 不新增/删除/修改 API 路径；
- 不修改数据库结构；
- 不改变业务数据流。

因此未触发全量 E2E 回归。若需要，可后续单独安排 `test_s119_browser_e2e.py` 等用例执行。

## 6. UI 前后变化截图

### 6.1 首页 — 系统状态入口降级 + 会话分组
`ui/test/ui-p0/01-home.png`

变化点：
- 左侧会话列表出现 `置顶 / Today / 7 Days / Earlier` 分组及计数徽章。
- 系统状态卡片保留「状态点 + 系统状态入口」，不再暴露模型名、TTS 状态等开发/运维信息。

### 6.2 会话 hover — inline action（重命名 / 置顶 / 隐藏）
`ui/test/ui-p0/02-session-hover.png`

变化点：
- 鼠标悬停会话项时，右侧出现 ✏️ / 📌 / ✕ 三个 inline action。
- 已置顶会话显示在「置顶」分组，并带 📌 标记。
- 已重命名会话显示覆盖标题（如「晨间播报编排」、「入职 Onboarding」）。

### 6.3 当前 session — 左侧红色 active 指示
`ui/test/ui-p0/03-session-active.png`

变化点：
- 当前选中的会话（test-123 / 入职 Onboarding）左侧出现 3px 红色高亮条，满足「当前 session 唯一视觉高亮」。
- 红色仅用于品牌爱心、当前 session 指示、危险操作（✕），符合 token 治理规则。

## 7. 设计 Token 新增清单

```css
/* 颜色语义 */
--danger: #ff4d4f;
--danger-light: #ff4d4f1a;

/* 间距 */
--sp-1: 8px;
--sp-2: 16px;
--sp-3: 24px;

/* 中性阶 */
--neutral-1: #f7f7f5;
--neutral-2: #e6e4dc;
--neutral-3: #8c8a82;
--neutral-4: #6b6961;
--neutral-line: var(--neutral-2);
--neutral-bg: var(--neutral-1);
```

## 8. 红线合规声明

- ✅ 未修改 `xiao6-ui` 旧入口、`_ui_archive`、任何 ZZ/ZhuangZhou/庄周历史资产。
- ✅ 未新增、修改、删除任何后端 API 契约。
- ✅ 未修改数据库结构（rename/pin/hide 全部通过 `localStorage` 前端覆盖层实现）。
- ✅ 未改变版本号，保持 **Xiao6 v1.0.0**。
- ✅ 所有改动先经过 `UI_COMPONENT_AUDIT.md` 审计确认，符合 VERIFY-BEFORE-CHANGE 流程。

## 9. 后续建议

- **UI-P1**：按审计结果将首页从 Dashboard 看板改为 Chat-first 布局（问候 + 输入框居中，天气/日程/任务折叠为 Today Card，热点资讯迁移到 Insight/Foresight 入口）。
- **UI-P2**：右侧改造为 Agent Activity Center（当前状态 / 运行任务 / 洞察 / 系统健康）。
- **E2E 回归**：如后续进入 P1/P2，建议把 `test_s119_browser_e2e.py` 纳入 CI 作为首页快照回归。

---
生成时间：2026-09-06 17:33 (UTC+8)  
作者：阿枢 🧠
