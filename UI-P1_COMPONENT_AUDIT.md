# Xiao6 v1.0.0 — UI-P1 Component Audit（VERIFY-BEFORE-CHANGE）

> 基线：UI-P0 PASS（commit `a31d7b2`）。本文件为 P1 执行前审计，列出 8 个组件 → JS state → API → 目标迁移位置。
> 规则红线：不改 `server.py`、不改 API 契约、不改数据库、不改 session 系统、不改版本号、不引入 ZZ/ZhuangZhou/庄周 资产。
> 状态：审计完成，**待老板确认后再动代码**。

---

## 0. 当前布局事实（实测）

- `.app` = grid：`[sidebar] 1fr` → 左 `.sidebar`（导航+最近对话）+ 右 `.main`。
- `.main` 内 `#view-dashboard` 当前是**单列滚动**：`.page` 内顺序堆叠 `.page-head` → `#dashGrid` → `#activityCenter` → `#intelligenceFeed` → `#foresightPanel` → context/reasoning/decision/prediction/learning 面板。
- **关键发现 F1：当前 dashboard 没有「右栏」**。P1 要新建二栏布局（左=chat-first 主区，右=Agent Activity Center）。
- **关键发现 F3：首页已有全局 Command Bar（`#commandInput`，S125.1）**，但被放在页面**底部**（`.dashboard-command-wrap`），已通过 `switchView('chat')`+填充`#input`+`submit()` 实现 chat-first 复用。P1 把它**提升为页面顶部 hero 输入框**即可，无需新写输入逻辑。

渲染触发点（实测）：
| 组件 | 函数 | 触发 |
|---|---|---|
| dashGrid | `loadDashboard()` app.js:245 | init app.js:135 / 切view app.js:181 / 刷新 app.js:206 |
| commandInput | `bindCommandBar()` app.js:2354 | init app.js:131 |
| activityCenter | `renderActivityPanel()` command_bar.js:121 ← `loadActivities()` command_bar.js:152/191 | init command_bar.js:191 |
| intelligenceFeed / foresightPanel | `loadGfeDashboard()` gfe-dashboard.js:268 ← `/api/gfe/dashboard` | app.js:187 (view=gfe) + gfe-dashboard.js:287 自启 |
| GFE 子面板 | `showPanel()` index.html:546 | tab 点击 |

---

## 1. 八组件审计表（Component ↓ State ↓ API ↓ Target）

### 1. dashGrid
- **位置**：`#dashGrid` (index.html:94)；渲染函数 `loadDashboard()` app.js:245
- **JS state**：`w=/api/weather`、`t=/api/tasks`、`h=/api/hotspots`，并依赖 `S.health/S.ready/S.config`
- **API**：`/api/weather` `/api/tasks` `/api/hotspots` `/api/health` `/api/ready` `/api/config`（全部复用）
- **目标迁移**：**解散并重组**。单栏 `#dashGrid` 容器替换为二栏布局 `#homeMain`（hero + Today Card）+ `#homeRight`（Agent Activity Center）。函数重写为渲染新结构。

### 2. weatherCard
- **位置**：`weatherCard()` app.js:307
- **JS state**：`w`（来自 `/api/weather`）
- **API**：`/api/weather`（保留）
- **目标迁移**：→ **Today Card 的「天气」子块**（主栏）。原函数复用，内嵌进 Today Card。

### 3. taskCard
- **位置**：`taskCard()` app.js:352
- **JS state**：`t`（→ `S.tasks`）
- **API**：`/api/tasks`（保留）
- **目标迁移**：→ **Today Card 的「任务」子块**（主栏）。原函数复用，内嵌进 Today Card。

### 4. hotspotCard
- **位置**：`hotspotCard()` app.js:440
- **JS state**：`h`（来自 `/api/hotspots`）
- **API**：`/api/hotspots`（**保留，仅改展示位置**）；保存动作 `/api/knowledge`（保留）
- **目标迁移**：→ **右栏「主动洞察 / Insight-Foresight 入口」子块**。渲染位置从 `#dashGrid` 移到 `#homeRight` 的洞察区；「阅读全文 / 保存知识库 / 让小6总结」三个动作保留。

### 5. systemCard
- **位置**：`systemCard()` app.js:543（P0 已降为「状态点+系统状态入口」）
- **JS state**：`S.health` `S.ready` `S.config`
- **API**：`/api/health` `/api/ready` `/api/config`（保留）
- **目标迁移**：→ **右栏「系统健康」子块**（Agent Activity Center）。复用状态点+入口逻辑。

### 6. activityCenter
- **位置**：`#activityCenter`/`#activityPanel` (index.html:99)；`renderActivityPanel()` command_bar.js:121
- **JS state**：`activities`（来自 `/api/interaction/activity`）
- **API**：`/api/interaction/activity`（保留）
- **目标迁移**：→ **右栏「当前状态 / 运行任务」子块**。活动流作为当前状态展示；运行任务从 `S.tasks`（running 子集）呈现。API 调用不变。

### 7. intelligenceFeed
- **位置**：`#intelligenceFeed` (index.html:113)；gfe-dashboard.js 经 `/api/gfe/dashboard` 渲染
- **JS state**：GFE 数据（来自 `/api/gfe/dashboard`）
- **API**：`/api/gfe/dashboard`（保留）
- **目标迁移**：→ **右栏「主动洞察 / Insight 引擎」**。保留为右栏洞察区的主内容（洞察 tab）。

### 8. foresightPanel
- **位置**：`#foresightPanel` (index.html:133)；gfe-dashboard.js 经 `/api/gfe/dashboard` 渲染
- **JS state**：GFE 预测数据（来自 `/api/gfe/dashboard`）
- **API**：`/api/gfe/dashboard`（保留）
- **目标迁移**：→ **右栏「Insight / Foresight 入口」的「未来关注」tab**。保留。

---

## 2. 关键 Gap 与决策点（F2 / F4 / F5）

- **F2 — 无「日程」端点（重要）**：`/api/tasks` 返回 50 条扁平任务，仅含 `id/title/status/created/updated`，**无 due-date / schedule 字段**，全仓无 `/api/schedule`。
  - **处置（提议，不阻塞）**：Today Card 的「日程」子块 = 从 `/api/tasks` 派生「今日安排」：取 `created`/`updated` 日期==今天的任务，以时间线呈现；若无今日任务则显示空态引导。不改 API、不加端点。
  - **需老板确认**：① 接受「日程=今日任务派生」映射；② 还是希望「日程」先留空态占位（后续接真实日历源）。
- **F4 — `#commandInput` 提升**：把 `.dashboard-command-wrap` 从页面底部移到 hero 顶部；bind 按 `#commandInput` id 仍有效（init 时已绑）。需同步把 `.command-hints` 预置按钮并入 hero 快捷动作。
- **F5 — 红色治理延续**：P1 新增 UI 一律复用 P0 token（`--brand --ink-* --neutral-* --danger --sp-*`），不重新硬编码红色；新组件用语义 token。

---

## 3. 目标布局（P1 后）

```
#view-dashboard
├─ .home-grid (二栏: 1fr + 360px)
│  ├─ #homeMain (左)
│  │  ├─ .home-hero        ← 小6问候 + #commandInput(提升) + 快捷动作 chips
│  │  └─ .today-card       ← [天气 weatherCard] [任务 taskCard] [日程 派生]
│  └─ #homeRight (右, Agent Activity Center)
│     ├─ 当前状态/运行任务  ← activityCenter + S.tasks(running)
│     ├─ 主动洞察          ← hotspotCard(迁移) + intelligenceFeed(GFE)
│     ├─ 系统健康          ← systemCard
│     └─ Foresight 入口    ← foresightPanel(GFE 未来关注)
```

---

## 4. 拟定改动文件（执行时再细化，本表供验收 #2 参考）

| 文件 | 改动性质 | 是否改 API |
|---|---|---|
| `ui/index.html` | 重组 `#view-dashboard`：hero + `#homeMain`(Today Card) + `#homeRight`(Agent Center)；移动/合并 `#dashGrid/#activityCenter/#intelligenceFeed/#foresightPanel` | 否 |
| `ui/js/app.js` | 重写 `loadDashboard()` 渲染新结构；新增 `renderTodayCard()`、`renderAgentCenter()`；复用 `weatherCard/taskCard/hotspotCard/systemCard`；保留 `bindCommandBar()` | 否 |
| `ui/js/command_bar.js` | `renderActivityPanel()` 渲染目标改为右栏状态/任务区；`loadActivities()` 不变 | 否 |
| `ui/js/gfe-dashboard.js` | 渲染目标选择器改为右栏洞察容器（如 `#homeRight` 内 insight 节点）；逻辑不变 | 否 |
| `ui/css/style.css` | 新增 `.home-grid` 二栏、`.home-hero`、`.today-card`、`.agent-center` 样式；复用 token | 否 |
| `css/gfe-dashboard.css` `css/s142-system.css` `css/s144-command.css` | 视容器变动做选择器/间距微调；不新增 token | 否 |

---

## 5. API 影响说明（验收 #3 预填）

**零契约变更。** 8 组件全部复用既有端点，无新增、无删除、无参数改动：
`/api/weather` `/api/tasks` `/api/hotspots` `/api/health` `/api/ready` `/api/config` `/api/interaction/activity` `/api/gfe/dashboard`，以及既有动作 `/api/knowledge`（热点保存）。数据库、session 系统、版本号均不变。

---

## 6. 回归与验收计划（验收 #4/#5/#6）

1. `node --check` 校验 `app.js` `command_bar.js` `gfe-dashboard.js`（+P0 其余文件）。
2. Playwright 截图：① 首页（hero+Today Card+右栏）② 会话 hover ③ 会话 active；与 P0 脚本同目录 `ui/test/ui-p1/`。
3. 断言：9 个既有端点仍在调用、无新增端点（grep 校验）。
4. 单 commit，不 amend / 不 force，版本保持 `Xiao6 v1.0.0`。
5. 附 `UI-P1-COMPLETION-REPORT.md`。

---

## 7. 阻塞确认项（请老板拍板后开工）

- [ ] **F2 日程映射**：接受「日程=今日任务派生」？
- [ ] 右栏四区优先级/可见性：是否默认全展开，还是「当前状态/运行任务」常驻、「主动洞察/系统健康/Foresight」可折叠？
- [ ] 快捷动作来源：复用 `QUICK`(app.js:2332) 四词，还是要换一组首页专属短语？
- [ ] 二栏右栏宽度（提议 360px）是否合适，窄屏（<1100px）是否回退单列？
