# Xiao6 v1.0.0 R8-UI Runtime Recovery — FINAL REPORT

> 阶段目标：恢复 Xiao6 v1.0.0 产品 UI，使现有 UI 完整控制已稳定的 Agent Runtime。
> 约束遵守：未修改 ai_core.execution.run() / Policy / PermissionGuard / Recovery Router /
> Agent Runtime；未新增 Agent 能力；未重新设计 UI 架构（恢复既有 Six Space 工作台）；
> 未做大改前端框架（仅 1 个 JS 文件内追加绑定 + 后端 API 表面修复）。
> 按任务要求停止；未执行版本修改 / Git 清理 / 发布打包。

---

## 一、UI 现状调查（任务 1：UI 状态报告）

### 1.1 调查结论
| 检查项 | 结果 |
|---|---|
| 当前 UI 是否存在 | ❌ 工作树中无 UI（`index.html`/`app.js` 被移除；服务器 `_serve_file("index.html")` 404） |
| UI 来源 | ✅ 拆分前备份 `G:\ZhuangZhou-backup-20260817\zhuangzhou-ui\zz-space\`（完整 Six Space 工作台：index.html 12KB + zz-workspace.js 51KB + zz-workspace.css 26KB） |
| API 地址配置 | 相对路径（`fetch('/api/...')`，同源），无需改动 |
| 已有页面结构 | 单页工作台：TopBar（命令面板/运行时/语音球）+ 左导航（首页/对话/项目/任务/记忆/知识/能力/设置）+ 中央视图（Home 卡片 / 对话四 Tab：对话·工作区·结果·Agent 活动 / 列表视图）+ 右上下文栏 + 命令面板 + 覆盖层（审批卡）+ Toast |
| 缺失文件 | 整个 `zz-space/` 目录 + 根入口 `index.html` |

### 1.2 已有 API 调用（备份 JS 中已实现，无需重写）
- `POST /api/chat`（fetch + ReadableStream SSE 解析：内容增量 / tool_start / tool_end / approval）✅
- `POST /api/agent/approval?ticket=&decision=`（审批卡 approve/reject）✅
- `GET /api/agent/state`（8s 轮询 + snapshot）✅
- fetchSnapshot：goals/memories/knowledge/capabilities/tasks/health/memory/briefing/calendar/notes ✅
- `/api/speak`、`/api/asr`、`/api/chat/history` ✅

### 1.3 缺失的 UI→API 绑定（本阶段补齐）
- `POST /api/agent/goal`（目标创建 UI 不存在）
- `POST /api/agent/intent`（意图识别 UI 不存在）
- `EventSource('/api/stream')` 实时通道（审批 modal / execution / GOAL·TASK·INTENT 事件监听不存在）

---

## 二、恢复内容（任务 2/3/4）

### 2.1 UI 资产恢复（静态，不改架构）
| 文件 | 说明 |
|---|---|
| `xiao6-ui/index.html` | 根入口 → 302 重定向到 `/zz-space/index.html`（与原版入口模式一致） |
| `xiao6-ui/zz-space/index.html` | Six Space 工作台页面（原版恢复） |
| `xiao6-ui/zz-space/css/zz-workspace.css` | 样式（原版恢复） |
| `xiao6-ui/zz-space/js/zz-workspace.js` | 应用逻辑（原版恢复 + 追加绑定） |

### 2.2 zz-workspace.js 追加绑定（仅 UI→API 对接，5 处增量）
1. **`EventSource('/api/stream')` 实时通道**（任务 3）：
   - `modal` + `kind=agent_approval` → 审批卡（批准/拒绝按钮，复用既有 `.zz-approval-card` 样式与 `POST /api/agent/approval` 路径）→ Agent 活动记录 + toast
   - `tool_started` / `tool_finished` → Agent 活动时间线（执行状态实时）
   - `execution_started/completed/cancelled` → Agent 活动
   - `GOAL_*` / `TASK_*` / `INTENT_*` / `AGENT_*` 领域事件 → Agent 活动 + 终态 toast + `fetchSnapshot()` 刷新（goal/execution 状态实时）
2. **Goal 绑定**（任务 2）：命令面板 `新建目标` + 首页快捷动作 → 覆盖层表单（title/description）→ `POST /api/agent/goal` → 显示 goalId/状态 + toast + 刷新
3. **Intent 绑定**（任务 2）：命令面板 `意图识别` → 覆盖层表单 → `POST /api/agent/intent` → 显示 classification / confidence / action / goalId
4. **postJSON** 辅助（既有 getJSON 对称补充）
5. Chat / Approval / Agent State 绑定原版已具备，未改动

### 2.3 后端 API 表面修复（P1 页面数据端点，悬空 Handler 恢复）
调查发现 UI fetchSnapshot 依赖的 4 个数据端点为**悬空/缺陷**（与 R8-P3 同类问题，非 Runtime 内核）：
| 端点 | 问题 | 修复 |
|---|---|---|
| `GET /api/memory` | `do_GET` 内 `/api/memory/truth` 分支的局部 `from db import db_conn` 遮蔽全函数 `db_conn` → UnboundLocalError | 移除冗余局部导入（模块级已导入） |
| `GET /api/tasks` | `_handle_tasks` 缺失（TasksMixin 为空 stub）→ AttributeError | 恢复 `server_handlers_tasks.py`（TasksMixin：_handle_tasks / _handle_notes / _handle_notes_post，拆分前备份同源），`server_handlers.py` 改从该模块导入 |
| `GET /api/notes`（+graph/tags/search/backlinks） | `_handle_notes` 缺失 → AttributeError | 同上 |
| `GET /api/knowledge` | 知识后端为 S79.7 stub（`knowledge_runtime.cache` 空模块）→ 500 | 优雅降级：后端未就绪时返回 `{"docs": [], "stats": {}}`（UI 显示"知识库为空"，不 500） |

---

## 三、验证结果（任务 5）

### 3.1 UI 运行时验证（test_ui_runtime.py，自启服务器 :8034）→ ALL PASS ✅
```
[PASS] 服务器启动
[PASS] 静态资源 入口 / → 200（重定向入口）
[PASS] 静态资源 index.html / css / js → 200
[PASS] GET /api/agent/state → enabled+state（Agent 状态绑定数据源）
[PASS] Chat 普通聊天（SSE 流）        ← "你好，介绍一下自己"
[PASS] Chat 工具调用事件（tool_start/tool_end）  ← "帮我查询当前时间"
[PASS] Goal 创建 → goalId 生成        ← goalId=21
[PASS] /api/stream 实时收到 GOAL_CREATED（goal 状态实时通道）
```

### 3.2 Approval 流程（真实服务器 :8035，r8_ui_approval_probe.py）→ ALL PASS ✅
```
[goal try 0] POST /api/agent/goal（run_shell confirm 级）→ goalId=19
✅ /api/stream 收到 modal(kind=agent_approval) ticket=01c1665c…
✅ POST /api/agent/approval?ticket=…&decision=approve → 200 {"ok": true}
✅ POST /api/agent/approval?ticket=…&decision=reject  → 200 {"ok": true}
```
即 UI 审批卡完整路径：stream 事件 → 审批卡 → approve/reject 均有效。

### 3.3 UI 数据端点全量扫描（fetchSnapshot 集合）→ 全部 200
`/api/agent/state /api/goals /api/memories /api/knowledge /api/capabilities /api/tasks /api/health /api/memory /api/briefing /api/calendar/events /api/notes /api/chat/history /api/notes/graph` — 修复前 4 个失败（tasks/memory/notes/knowledge），修复后全 200。

### 3.4 回归
- R8-P3 API Surface 套件（approval 闭环 / intent / goal / 错误返回）：**ALL PASS ✅**（后端修复无回归）
- JS 语法：`node --check` 通过
- 页面结构（P0/P1）：Chat（对话四 Tab）✅ / Agent 状态（TopBar 运行时 + Agent 活动）✅ / Goal 列表（项目视图）✅ / Memory ✅ / Tasks ✅ / Activity（Agent 活动）✅

---

## 四、已知问题（如实记录）

1. **知识后端为 S79.7 stub**：`knowledge_runtime/cache.py` 空模块（DocCache 缺失）→ 知识页显示"知识库为空"（本阶段优雅降级，不 500）；知识子系统恢复属独立阶段。
2. **wakeword 线程缺 numpy**（非致命，启动噪音）；edge_tts / Open-Meteo / 热点源 401 为既有环境项。
3. **UI 未做浏览器实机点击验证**（无 headless 浏览器接入）：验证采用真实 HTTP/SSE 同路径断言（与 UI 绑定完全相同的端点与载荷），DOM 交互（审批卡点击、表单提交）逻辑经 `node --check` + 同路径 API 验证覆盖。
4. **`/api/knowledge` 错误字段**随优雅降级返回（`error` 键），前端忽略未知字段，无影响。

---

## 五、修改文件

| 文件 | 变更 |
|---|---|
| `xiao6-ui/index.html` | **新增**：根入口（重定向 → /zz-space/） |
| `xiao6-ui/zz-space/index.html` | **新增**：Six Space 工作台页面（原版恢复） |
| `xiao6-ui/zz-space/css/zz-workspace.css` | **新增**：样式（原版恢复） |
| `xiao6-ui/zz-space/js/zz-workspace.js` | **新增**：应用逻辑（原版恢复 + EventSource 实时通道 / Goal / Intent 绑定） |
| `xiao6-ui/server.py` | 修复 `/api/memory` 的 `db_conn` 局部导入遮蔽；`/api/knowledge` 优雅降级 |
| `xiao6-ui/server_handlers_tasks.py` | **新增**：TasksMixin（_handle_tasks / _handle_notes / _handle_notes_post，备份同源恢复） |
| `xiao6-ui/server_handlers.py` | TasksMixin 改从 server_handlers_tasks 导入（去 stub） |
| `xiao6-ui/tests/r8_agent_benchmark/test_ui_runtime.py` | **新增**：UI 运行时验证套件 |
| `xiao6-ui/r8_ui_approval_probe.py` | **新增**：Approval-over-Stream 验证探针（LLM 方差容错） |

---

## 六、按任务要求未执行（等待下一阶段）

- ❌ 版本修改
- ❌ Git 清理
- ❌ 发布打包
