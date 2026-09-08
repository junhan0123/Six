# UI-P2 · Activity 组件全链路审计报告

> 基线：UI-P0 ✅ / UI-P1 ✅ / Runtime Hotfix R1 ✅ · HEAD `b9c7239`
> 目标：将右栏 Agent Activity Center 从信息展示升级为 Personal AI OS 控制中心
> 约束：**不改 server.py / 不改 API contract / 不改 DB / 不改 Agent Runtime**，版本保持 Xiao6 v1.0.0

---

## 0. 审计链路图（API 字段 → JS 消费 → DOM 节点 → CSS 组件）

```
GET /api/interaction/activity                  GET /api/health + /api/ready
   │                                                    │
   ▼                                                    ▼
interaction_activity.py                        server.py: do_GET /api/health
   to_dict():                                               /api/ready
     activity_id, type, title, status,                       │
     description, intent_type,                              ▼
     timestamp, relative_time                       app.js: S.health, S.ready
   stats: {total, active,                                      │
           completed, max_activities}                         ▼
                                                          systemCard()
                                                              │
                                                              ▼
                                                    #acHealthBody (.ac-sec-body)
   │                                              ▲
   ▼                                              │
┌──────────────────────────────────────────────────────┐
│ JS 消费层                                            │
│   command_bar.js                                    │
│     renderActivityPanel(activities) ───────────────▶ #activityPanel
│     loadActivities() → fetch + render               （#acActivitySlot > #activityCenter > #activityList）
│   app.js                                            │
│     renderLiveCenter() ───────────────────────────▶ #acTasksBody
│     （当前数据源：S.tasks，不是 activity API ⚠️）      （.ac-live-body）
│     hotspotCard(h) ──────────────────────────────▶ #acHotspot
│     systemCard()  ───────────────────────────────▶ #acHealthBody
│     scheduleCard(t) ─────────────────────────────▶ #todayBody（今日日程卡）
│   index.html 底部 inline script                     │
│     loadFeed()        ───────────────────────────▶ #feedList（#intelligenceFeed）
│     loadForesight()   ───────────────────────────▶ #foresightList（#foresightPanel）
└──────────────────────────────────────────────────────┘
   │                                              ▲
   ▼                                              │
┌──────────────────────────────────────────────────────┐
│ DOM 节点层（#homeRight > .agent-center）              │
│   <section #acLive 常驻>                              │
│     ├─ sub-label "运行任务" → #acTasksBody            │
│     └─ sub-label "当前状态" → #acActivitySlot         │
│                            └─ #activityCenter         │
│                               └─ #activityPanel       │
│   <section #acInsight collapsible>                   │
│     ├─ #acHotspot                                     │
│     └─ #intelligenceFeed                              │
│   <section #acHealth collapsible> → #acHealthBody    │
│   <section #acForesight collapsible> → #foresightPanel│
└──────────────────────────────────────────────────────┘
   │                                              ▲
   ▼                                              │
┌──────────────────────────────────────────────────────┐
│ CSS 组件层（style.css L1314–1396）                    │
│   .home-grid (主区 1fr + 右栏 360px, gap sp-3)        │
│   .home-right / .agent-center (flex col, gap 14px)   │
│   .ac-section 卡片壳（bg/border/r-lg/sh-md）         │
│   .ac-sec-head / .ac-caret / .ac-sec-body             │
│   .ac-section.collapsed .ac-sec-body{display:none}  │
│   .ac-sub-label 子标题                                │
│   .ac-tasks / .ac-task / .ac-task-dot{.run/.pend}     │
│   .ac-task-title / .ac-task-st / .ac-empty           │
│   .activity-center / .activity-list / .activity-item  │
│     {.done/.run} / .activity-empty                    │
│   .agent-center .ac-hotspot .dash-card（降噪）        │
│   @media (max-width:1100px) 回退单列                  │
└──────────────────────────────────────────────────────┘
```

---

## 1. API 字段（`/api/interaction/activity`）

来源：`xiao6-ui/interaction_activity.py` + `xiao6-ui/server.py:425-437` / `server.py:1800-1820`

### 1.1 顶级响应

| 字段 | 类型 | 含义 | 前端消费 |
|---|---|---|---|
| `ok` | bool | 请求成功标志 | `command_bar.js`（`resp.ok`）/ `app.js`（隐式） |
| `activities` | Activity[] | 活动列表（最新在前，最多 50） | `renderActivityPanel` / `renderLiveCenter`（待切换） |
| `stats` | object | 统计 | **当前无前端消费**（P2 引入 Agent Status 会消费） |
| └ `total` | int | 总数 | Agent Status |
| └ `active` | int | `status==running` 数量 | Agent Status |
| └ `completed` | int | `status==completed` 数量 | Agent Status |
| └ `max_activities` | int | 上限 50 | 仅展示 |

### 1.2 Activity 字段（`to_dict()` L36-46）

| 字段 | 类型 | 取值/示例 | 前端当前消费 | P2 计划消费 |
|---|---|---|---|---|
| `activity_id` | string | `act_<ms>_<tid>` | 无 | 标识 |
| `type` | string | `parse/intent/analysis/command/interaction` | ✅ icon (L137) | ✅ |
| `title` | string | 活动标题 | ✅ L142 | ✅ 任务名称 |
| `status` | string | `idle/running/completed/error` | ✅ L138 done/run | ✅ 任务状态 |
| `description` | string | 描述 | ❌ 未消费 | 可选 |
| `intent_type` | string | 意图分类 | ✅ L143 | ✅ |
| `timestamp` | float | epoch 秒 | 无 | 可派生"已运行时长" |
| `relative_time` | string | `刚刚 / N 分钟前 / N 小时前 / N 天前` | ✅ L143 | ✅ |

### 1.3 状态机

```
idle ──▶ running ──▶ completed
            │
            └────▶ error
```

⚠️ **没有 `waiting/pending` 状态** —— 详见 §6 缺口 F1。

---

## 2. JS 消费层

### 2.1 `ui/js/command_bar.js`

| 函数 | 行号 | 行为 | 写入 DOM |
|---|---|---|---|
| `trackActivity(type,text,intent,data)` | L110-118 | 解析成功后 fetch activity 并重渲 | 调用 `renderActivityPanel` |
| `renderActivityPanel(activities)` | L121-149 | 渲染活动列表（图标+标题+meta） | `#activityPanel` |
| `loadActivities()` | L152-161 | 拉取并渲染（首页不调用） | `#activityPanel` |

**渲染规则**（L130-146）：
- 图标映射：`parse→🔍, intent→🎯, analysis→📊, command→⚡`，其他 → `•`
- 状态样式：`completed → .done`，`running → .run`，其他 → 空
- 空态：`<div class="activity-empty">暂无交互活动</div>`
- 元信息：`${act.intent_type || act.type} · ${act.relative_time}`

### 2.2 `ui/js/app.js`（右栏相关）

| 函数 | 行号 | 数据源 | 写入 DOM | 触发时机 |
|---|---|---|---|---|
| `loadDashboard()` | L255-286 | weather/tasks/hotspots | `#todayBody` `#acHotspot` `#acHealthBody` `#acTasksBody`(经 renderLiveCenter) | 进入首页 |
| `renderLiveCenter()` | L310-328 | **`S.tasks`**（/api/tasks）⚠️ | `#acTasksBody` | loadDashboard 内 |
| `systemCard()` | L645-660 | `S.health` + `S.ready` | 返回 HTML（被塞入 `#acHealthBody`） | loadDashboard 内 |
| `hotspotCard(h)` | (L276) | `/api/hotspots` | `#acHotspot` | loadDashboard 内 |
| `scheduleCard(t)` | L289-307 | `S.tasks` 派生 | `#todayBody`（Today Card 内） | loadDashboard 内 |

⚠️ **数据源错位**：`renderLiveCenter()` 当前用 `/api/tasks`（任务清单），而 P2 要求 Current Tasks **来自 activity**。需要切到 `/api/interaction/activity`。

### 2.3 `index.html` 底部 inline script（非 P1 修改）

- `loadFeed()` → `#feedList`（`/api/intelligence/feed`）
- `loadForesight()` → `#foresightList`（`/api/intelligence/foresight`）
- 保留 P1 已保留的 ID，**不要改动**。

---

## 3. DOM 节点层（`ui/index.html` L124-185）

```
<aside class="home-right" id="homeRight">
  <div class="agent-center">

    ┌─────────────────────────────────────────────────────────────┐
    │ <section class="ac-section" id="acLive">  ← 常驻，无折叠     │
    │   <div class="ac-sec-head">🤖 当前状态 / 运行任务</div>     │
    │   <div class="ac-live-body">                                │
    │     <div class="ac-sub-label">运行任务</div>                │
    │     <div id="acTasksBody"></div>            ← app.js        │
    │     <div class="ac-sub-label">当前状态</div>                │
    │     <div id="acActivitySlot">                               │
    │       <div class="activity-center" id="activityCenter">     │
    │         <div class="activity-header">…0 项活动</div>        │
    │         <div class="activity-list" id="activityPanel">      │
    │           ← command_bar.js renderActivityPanel              │
    │         </div>                                              │
    │       </div>                                                │
    │     </div>                                                  │
    │   </div>                                                    │
    └─────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────┐
    │ <section class="ac-section collapsible" id="acInsight">      │
    │   🔮 主动洞察 ▾                                              │
    │   #acHotspot  +  #intelligenceFeed                           │
    └─────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────┐
    │ <section class="ac-section collapsible" id="acHealth">       │
    │   ⚙️ 系统健康 ▾                                              │
    │   #acHealthBody                                             │
    └─────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────┐
    │ <section class="ac-section collapsible" id="acForesight">    │
    │   📊 未来关注 ▾                                              │
    │   #foresightPanel                                           │
    └─────────────────────────────────────────────────────────────┘
  </div>
</aside>
```

**结构约束**：
- `#acLive` **常驻**（无 `[data-toggle]`，无 `.ac-caret`）
- 其它三个 `<section>` 均 `collapsible`，有 `[data-toggle]` head
- 折叠交互由 `app.js bindHomeCollapsibles()` 绑定

---

## 4. CSS 组件层（`ui/css/style.css` L1314-1396）

| 选择器 | 行号 | 职责 | P2 是否要改 |
|---|---|---|---|
| `.home-grid` | L1314-1320 | 主区+右栏 360px grid | 否（保留 P1） |
| `.home-right / .agent-center` | L1345-1346 | 右栏容器 | 否 |
| `.ac-section` | L1347-1353 | 卡片壳 | 否 |
| `.ac-sec-head` | L1354-1359 | 标题栏 | 否 |
| `.ac-caret` + `.collapsed` | L1360-1362 | 折叠箭头 | 否 |
| `.ac-sub-label` | L1364-1365 | 子标题 | 否 |
| `.ac-tasks / .ac-task / .ac-task-dot{.run/.pend} / .ac-task-title / .ac-task-st` | L1367-1372 | **运行任务** 行 | **微调**：加 `.progress` 进度条样式 + `.ac-task-dot.run/.pend/.done/.error` 四态 |
| `.activity-item{.done/.run} / .activity-empty` | (既有 .activity-* 块) | 当前状态/活动列表 | 否（复用） |
| `.agent-center .ac-hotspot .dash-card` 等 | L1375-1382 | 降噪嵌套 | 否 |
| `@media (max-width:1100px)` | L1393-1395 | 窄屏回退 | 否（保留 P1） |

**P2 需要新增的 CSS**：
- `.ac-status` 容器（Agent Status 大卡片）
- `.ac-status-dot` + 状态色变体 `.idle / .run / .wait`
- `.ac-status-label` 文案
- `.ac-task-progress` 进度条（`background: var(--bg-soft)` 底 + `var(--brand)` 填充，宽度由 JS 设置）
- `.ac-task-progress.indeterminate` 动画条（keyframe 1.4s）
- `.ac-task-status-tag` 状态标签（`.running/.completed/.idle/.error` 四色）

---

## 5. P2 目标 ↔ 现状映射

| P2 目标 | 现状 | 改造点 |
|---|---|---|
| **Agent Status**（空闲/运行中/等待确认） | ❌ 无此视图 | 新增 DOM/CSS/JS；数据源 `stats.active` + `stats.total` |
| **Current Tasks**（任务名称/状态/进度，**来自 activity**） | ⚠️ 当前用 `S.tasks`（/api/tasks），不是 activity | 切数据源到 `/api/interaction/activity`；新增进度条 UI |
| **Insight**（接入已有 intelligence feed） | ✅ `#acInsight` 已包含 `#intelligenceFeed` | 不动 |
| **System Health**（health/ready） | ✅ `systemCard()` 已渲染 | 不动 |

---

## 6. 数据缺口（需在确认时定方案）

### F1 · Agent Status「等待确认」态

- **现状**：Activity 状态枚举 `idle/running/completed/error`，**没有 `waiting/pending/confirming`**。
- **影响**：UI 需要三态视觉，但数据只支持两态。
- **方案 A（推荐）**：本轮实现 Agent Status 块，但**只渲染 空闲/运行中 两态**（`stats.active>0` → 运行中，否则空闲）。`等待确认` 作为预留 UI（CSS 钩子 `.ac-status-dot.wait`），无数据时**不渲染**，等待后续 Activity Manager 扩展支持 `awaiting_confirm` 状态后启用。✅ 零契约变更。
- **方案 B**：扩展后端 `Activity.status` 增加 `awaiting_confirm` 枚举 + `add_activity` 支持。❌ 违反「不改 Agent Runtime / API contract」。
- **结论**：采用方案 A。

### F2 · Current Tasks「进度」字段

- **现状**：Activity 无 `progress` 字段。
- **方案（推荐）**：前端派生：
  - `completed` → 进度 100%，状态标签绿色"已完成"
  - `running` → 进度 indeterminate（动画横条），状态标签主色"运行中"
  - `idle` → 进度 0%，状态标签灰色"待启动"
  - `error` → 进度 0%（或保留 indeterminate），状态标签 danger 红"失败"
  - 数据源全部来自 `stats` + `activities[].status`，**零后端改动**。
- **结论**：采用派生方案。后续若需真实进度，需后端在 `Activity` 加 `progress: float`（范围 0–1），届时再扩展。

### F3 · 数据源切换（Current Tasks 由 tasks 切到 activity）

- **现状**：`renderLiveCenter()` 用 `S.tasks`（任务清单）。
- **冲突**：右栏会同时存在 `#activityPanel`（活动轨迹）和 `#acTasksBody`（任务列表）。两者职责需切清。
- **方案（推荐）**：
  - `#acTasksBody` 改名为职责定位：**Current Tasks（来自 activity）**，每条 = 一个进行中的活动/任务卡（标题 + 状态 + 进度 + 相对时间）。
  - `#activityPanel` 保留作为**最近活动轨迹**（轻量，只显示最近 N 条 completed/running 项，无进度条）。
  - 两者职责不重叠，避免视觉重复。
- **结论**：采用方案（细分职责）。

### F4 · 折叠交互

- **现状**：`#acLive` 常驻，`#acInsight/#acHealth/#acForesight` 折叠。
- **P2 要求**：保持常驻，不隐藏右栏。
- **结论**：不动。

---

## 7. 修改范围（仅前端，零后端）

| 文件 | 修改 |
|---|---|
| `ui/index.html` | 在 `#acLive` 顶部新增 `.ac-status` Agent Status 块；微调 `.ac-live-body` 结构，新增任务卡槽位 |
| `ui/js/app.js` | 新增 `renderAgentStatus()`；改造 `renderLiveCenter()` 数据源 → activity；新增进度派生与渲染；保持 `systemCard()`/`hotspotCard()` 不变；保持 `loadDashboard()` 编排 |
| `ui/css/style.css` | 新增 `.ac-status*`、`.ac-task-progress*`、`.ac-task-status-tag*` 等组件样式 |
| `UI-P2_ACTIVITY_COMPONENT_AUDIT.md` | 本报告 |

**不动**：`xiao6-ui/server.py`、`interaction_activity.py`（R1 已修复，不再改）、所有其他端点、DB、Agent Runtime 核心流程。

---

## 8. API 影响说明

**零契约变更**。P2 复用以下既有端点：

| 端点 | 用途 | 新增字段? |
|---|---|---|
| `GET /api/interaction/activity` | Agent Status + Current Tasks | ❌ |
| `GET /api/health` | System Health | ❌ |
| `GET /api/ready` | System Health | ❌ |
| `GET /api/intelligence/feed` | Insight | ❌ |
| `GET /api/intelligence/foresight` | Foresight | ❌ |
| `GET /api/hotspots` | Insight（acHotspot） | ❌ |
| `GET /api/weather` / `/api/tasks` | Today Card | ❌ |

**统计字段消费扩展**：前端新增读取 `stats.{total,active,completed}` 用于 Agent Status。**这是只读消费扩展，非契约变更**（字段已存在）。

---

## 9. 验收映射（按用户清单）

| 用户要求 | 本审计对应 |
|---|---|
| 1. 审计报告 | 本文件 |
| 2. 修改文件 | §7 三文件 + 本审计 |
| 3. API 影响说明 | §8 零契约 |
| 4. 截图 | 待实现后产出（home + acLive 展开） |
| 5. 回归测试 | 待实现后产出（`node --check` + Playwright） |
| 6. git commit | 待实现后产出（独立 commit，不 amend 不 force） |

---

## 10. 待确认事项（请老板定夺）

**F1 · 等待确认**：方案 A（前轮只渲染空闲/运行中，预留 UI）—— 默认推荐，**无 API 改动**。

**F2 · 进度派生**：前端派生（completed=100, running=indeterminate, idle=0, error=0/danger）—— 默认推荐，**无 API 改动**。

**F3 · 双区块职责划分**：
- `#acTasksBody` = Current Tasks（activity 驱动的任务卡，含进度）
- `#activityPanel` = 最近活动轨迹（轻量列表，无进度条）

**以上三项如无异议，下一轮按本审计落地代码。**

---

**审计完成，等待老板确认。版本保持 Xiao6 v1.0.0。未触碰任何代码。**