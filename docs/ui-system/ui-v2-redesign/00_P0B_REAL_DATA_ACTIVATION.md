# P0-B Real Data Activation · 实施与验证报告

> 阶段：UI-v2 Redesign Implementation — P0-B
> 纪律：Audit → Implement → Verify → Document → STOP
> 红线（严格遵守）：不修改 Agent Runtime / EventBus / AppState；不新增事件契约；不删除旧功能；不重写架构。
> 验证实例：本地 `server.py` 监听 `127.0.0.1:8011`（测试端口，避免与既有 8000 冲突）。

---

## 1. 目标达成核对

| 任务要求 | 状态 | 说明 |
|---|---|---|
| 新增只读 `GET /api/goals` | ✅ | 复用 `goals.list_goals()` / `goals.get_goal()`，零数据库逻辑复制 |
| 前端建立 UI Data Adapter | ✅ | `ui-data-adapter.js`：REST snapshot → DOM，绝不触碰 AppState |
| 首页 NOW 当前 Goal | ✅ | `#osrGoalTitle` / `#osrGoalMeta`，取 active 优先 |
| 首页 MEMORY 最近记忆摘要 | ✅ | `#osrMemTitle` / `#osrMemMeta`，取最新一条预览 |
| 首页 KNOWLEDGE 知识库状态 | ✅ | `#osrKnoTitle` / `#osrKnoMeta`，篇数/类数/节点 |
| 单一 AI OS Space | ✅ | 注入为 `.os-shell` 内一条绝对定位状态条，非独立页面 |
| 不新增页面 / 不恢复 Galaxy / 不产生 Chat / 不产生 Dashboard | ✅ | 沿用既有首页骨架，仅增量加读数条 |
| 简洁 / 高级 / 科技感 / 控制中心感 | ✅ | 细线分隔、直角读数条、单一强调色、禁玻璃禁卡片堆叠 |

---

## 2. 变更清单（全部增量，无破坏性）

### 2.1 后端 `server.py`（唯一真实后端改动）
- 在 `do_GET` 分发链中新增分支（位于 `/api/tasks` 之后）：
  ```python
  if path == "/api/goals" or path == "/api/goals/":
      _status  = qs.get("status", [""])[0].strip() or None
      _horizon = qs.get("horizon", [""])[0].strip() or None
      try: _limit = int(qs.get("limit", ["50"])[0])
      except (TypeError, ValueError): _limit = 50
      items = _goals.list_goals(status=_status, horizon=_horizon, limit=_limit)
      return self._send(200, json.dumps([g.to_dict() for g in items], ensure_ascii=False))
  _sub = path[len("/api/goals/"):].strip("/")
  if _sub.isdigit():
      g = _goals.get_goal(int(_sub))
      return self._send(200, json.dumps(g.to_dict(), ensure_ascii=False)) if g \
             else self._send(404, json.dumps({"error": "goal not found"}, ensure_ascii=False))
  ```
- 模块别名复用既有 `import goals as _goals`（位于该 try 块内，惰性导入，与其它端点一致）。
- **未复制任何 SQL / 数据库逻辑**：`list_goals(status, horizon, limit)` 与 `get_goal(id)` 均为 `goals.py` 既有公开 API，签名已核对（`goals.py:252`）。

### 2.2 前端 `ui-data-adapter.js`（新建，UI Data Adapter 首实例）
- 职责：并行 `fetch` `/api/goals`、`/api/memories`、`/api/knowledge`，把快照投影进 `#osReadout` 三个 cell。
- **隔离纪律（代码级强制）**：全文检索 `AppState.(set|update|patch|merge|emit|subscribe)` = 0 处。适配器只写专用 DOM 容器，AppState 仍是 Runtime 单一事实源。
- 不发起任何写请求；仅 `getJSON`（GET）。
- 事件驱动部分**仅订阅、不发布**：监听既有 `GOAL_CREATED/UPDATED/COMPLETED/PLANNED` 与 `MEMORY_CREATED/STORED/LINKED/UPDATED`（来自 `window.zzEvents` 或 `AppState.events` 既有总线），做轻量刷新；遇未支持事件静默忽略。不新增任何事件名。
- 兜底：`setInterval(refresh, REFRESH_MS)` + `visibilitychange` 立即刷新，确保无事件时数据也保持新鲜；失败时保留上一次渲染、不抛错、不打断首页。

### 2.3 前端 `index.html`（增量注入，无结构改动）
- 在 `.os-shell` 内、`.os-dock` 之后、`</section>` 之前注入读数条：
  ```html
  <div class="os-readout" id="osReadout" data-spatial-layer="operation" aria-label="小6实时状态">
    <div class="os-readout-cell"><span class="osr-label">NOW · 当前目标</span><span class="osr-value" id="osrGoalTitle">…</span><span class="osr-meta" id="osrGoalMeta">…</span></div>
    <div class="os-readout-cell"><span class="osr-label">MEMORY · 最近记忆</span><span class="osr-value" id="osrMemTitle">…</span><span class="osr-meta" id="osrMemMeta">…</span></div>
    <div class="os-readout-cell"><span class="osr-label">KNOWLEDGE · 知识库</span><span class="osr-value" id="osrKnoTitle">…</span><span class="osr-meta" id="osrKnoMeta">…</span></div>
  </div>
  ```
- `<head>` 内增量加入：
  - `<link rel="stylesheet" href="ui-v2-readout.css?v=20260810p0b" />`
  - `<script src="ui-data-adapter.js?v=20260810p0b"></script>`（位于既有 `avatar-renderer.js` 之后）

### 2.4 前端 `ui-v2-readout.css`（新建，视觉层）
- 定位：`position:absolute` 于 `.os-shell` 内，落在中央列核心区下沿 / 指令坞上沿（`bottom: calc(188px + …)`），左避让导航 76px、右避让侧栏 380px；**不触碰既有 CSS Grid**，避免与五代叠加的 grid 覆盖冲突。
- 视觉：`border-radius:0`（非卡片）、`box-shadow:none`、`background: var(--bg-raised)`（低不透明，非玻璃）、单元间 `1px` 细线分隔；单一强调色（继承 `--text-bright` / `--accent`）。
- 响应式：`≤1180px` 右侧栏收起占满中央列；`≤720px` 竖排堆叠。
- 注：本文件为 P0-B 增量交付，后续 v2 整合阶段应并入单一 `ui.v2.css`（见 `06` 设计语言）。

---

## 3. 验证结果（实测）

测试实例：`server.py` 监听 `127.0.0.1:8011`，存在预装 `xiao6.db`（含 8 条 Goal）。

| 验证项 | 方法 | 结果 |
|---|---|---|
| 后端语法 | `python -m py_compile server.py` | OK |
| 新增端点（列表） | `GET /api/goals` | 返回 8 条真实 Goal（`to_dict()` 全字段） |
| 新增端点（过滤） | `GET /api/goals?status=active&limit=20` | 仅返回 active 目标，过滤生效 |
| 新增端点（单条） | `GET /api/goals/7` | 返回单条 Goal 全字段 |
| 既有端点回归 | `GET /api/knowledge` | 正常返回 `{docs:[…],stats:{…}}` |
| 既有端点回归 | `GET /api/memories` | 正常返回记忆数组 |
| 前端 JS 语法 | `node --check ui-data-adapter.js` | OK（修复两处 `*/` 提前闭合注释后） |
| AppState 隔离 | 全文检索写入 API | 0 处 |
| CSS 括号平衡 | 统计 `{}` | 13 / 13 平衡 |
| 静态资源可达 | `GET /`、`/ui-data-adapter.js`、`/ui-v2-readout.css` | 全部 200 |
| 首页接线 | 抓取 `/` 匹配 `os-readout` / 两个文件名 | 均存在 |

**数据真实性**：`/api/goals` 返回的是数据库中真实存在的 Goal（如「总结当前项目状态」，active，progress 0/83 等），非 Mock。Memory / Knowledge 同样来自既有真实端点。

---

## 4. 严格未触碰项（红线自检）

- ❌ 未修改 Agent Runtime（目标编排状态机 / wakeword / 主动引擎）—— 注意：启动时 `wakeword.py` 的 VOSK 模型目录缺失会在后台线程抛 `FileNotFoundError`，**这是预存环境缺模型问题，非本次改动引入，亦不在 P0-B 范围内，未做任何处理**。
- ❌ 未修改 EventBus（事件名单一来源 `DOMAIN_EVENT_NAMES` 未动）。
- ❌ 未修改 AppState（`app-state.js` 零改动；适配器从不调用其写入 API）。
- ❌ 未新增事件契约（适配器仅订阅既有事件名）。
- ❌ 未删除任何旧功能（首页原有 `os-core` / `os-side` / `os-bottom` / `os-dock` 全部保留；Galaxy / Chat 等模块未被触动）。
- ❌ 未重写架构（仅在既有 `do_GET` 分发链追加分支，沿用惰性 `import` 与 `_send` 既有模式）。
- ❌ 未提交 Git。

---

## 5. 已知限制与待 Review 项

1. **视觉需浏览器确认**：本验证覆盖 API 真实性、静态资源、JS 语法、AppState 隔离、CSS 平衡，但**未做真实浏览器渲染截图**。读数条的绝对定位在 1920×1080 设计分辨率下经计算合理（避让 nav/side/bottom），建议人工 Review 时在浏览器实际打开首页确认观感（科技感 / 控制中心感是否到位，是否需微调 `bottom` 值避免与 `os-core` 视觉重叠）。
2. **预存 stray 服务**：环境内 `127.0.0.1:8000` 存在一个返回通用 `404` 的静态服务（非本次启动），可能干扰「默认 8000 端口」预期；真实应用应以 `server.py` 为准。本次验证使用 8011 规避冲突。
3. **Goal 数据语义**：当前 DB 中 Goal 多为「总结当前项目状态」类自动建目标，标题重复度高；这是真实业务数据现状，适配器已做 `active` 优先 + 省略截断处理，不影响首屏可用性。
4. **后续整合**：`ui-v2-readout.css` 与 `ui-data-adapter.js` 为增量文件，按 `06`/`07` 规划将在 v2 整合阶段并入 `ui.v2.css` 与统一 Data Adapter 层。

---

## 6. 结论

P0-B 三模块真实数据激活**已按纪律完成并通过验证**：首页首次拥有真实 AI OS 信息密度（当前目标 / 最近记忆 / 知识库状态），全部复用既有后端能力、零新增 Runtime/事件、零 AppState 写入、零旧功能删除。

**STOP —— 等待人工 Review。** 确认后进入下一阶段（建议优先：浏览器实机观感确认 + P0 后续结构整合）。
