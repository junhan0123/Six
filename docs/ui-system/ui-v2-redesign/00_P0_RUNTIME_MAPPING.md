# 00_P0 · Runtime & Data Boundary Audit（Goal / Memory / Knowledge）

> **P0-A 交付物 · 只读审计。**
> 本文件**不修改任何代码 / CSS / HTML，不新增事件，不新增 Runtime，不提交 Git**。
> 目标：确认 Goal / Memory / Knowledge 三类真实数据如何**安全映射**到 UI v2，并锁定 Runtime↔UI 的边界契约。
> 所有结论均来自对 `xiao6-ui/` 后端源码与前端事件契约的只读排查（行号已标注，可复核）。

---

## 0 · 一句话边界（先给红线）

> **UI v2 只做两件事接触真实数据：① 拉快照（REST GET）② 收事件（SSE 领域事件）。**
> **UI v2 永不直接写 Runtime / 数据库 / 文件。任何"创建目标 / 归档记忆 / 写知识"都经 Intent Gateway → Runtime 决策，UI 只发意图，不碰状态机。**

这是 `eventbus.py` 与 `zz-events.js` 已经建立、且被 readiness 规范强制的契约（见 §3），v2 只是**第一次把它用到 Goal/Memory/Knowledge 的呈现上**。

---

## 1 · 三类数据的真实来源与现状（审计事实）

| 域 | 后端真源 | 当前前端入口 | v2 映射目标 | 边界判定 |
|---|---|---|---|---|
| **Goal** | `goals.py`（完备）+ `goals` 表 | **无 REST 端点**（server.py 从不 import goals） | DOING 屏 | ⚠️ 唯一真实缺口 → 需新增只读 REST（见 §4.1） |
| **Memory** | `memories` 表 + `memory_summary` | `/api/memories`（已存在，GET 列表/图谱） | KNOWN「记忆」视图 | ✅ 只读复用，零后端改动 |
| **Knowledge** | `knowledge/*.md`（文件型，Local-First）+ `knowledge_manifest.json` | `/api/knowledge`（已存在，list_docs+stats） | KNOWN「知识」视图 | ✅ 只读复用，零后端改动 |

### 关键纠正（相对 07 路线图 P0 假设）
`07` 曾假设"46 篇知识文档不可见"是后端缺口——**实测否则**：`/api/knowledge` 已返回 `knowledge.list_docs()` + `stats()`（`server.py:399`），后端层完整。可见性缺口**仅在旧 UI 未消费该端点**，属前端接线问题，v2 直接复用即可。
同理 `/api/memories`（`server.py:352` / `_handle_memories:677`）已存在，支持列表与 `graph`（nodes+edges）。

→ **P0 三类数据的真实后端改动收敛为：仅 Goal 一处只读 REST 缺口。**

---

## 2 · Goal 域 — 数据形状与映射

### 2.1 真实数据模型（`goals.py:95` `Goal.to_dict()`）
```
id, title, description, status(active|paused|completed|archived),
priority(low|medium|high|critical), horizon(short|medium|long),
progress(0-100), parent_id, due_date, completed_at, created, updated
```
- 子任务经 `tasks.goal_id` 软外键归属（`_goal_tasks()`，`goals.py:294`）。
- 进度聚合：`recalc_progress()` 按子任务完成比例自动算，也可手填（`goals.py:289`）。

### 2.2 真实读 API（纯函数，安全复用）
- `get_goal(goal_id)` → 单条（`goals.py:170`）
- `list_goals(status=None, horizon=None, limit=50)` → 列表，按 due_date 升序（`goals.py:252`）
- `list_active_goals(limit=5)` → 活跃目标（`goals.py:273`）

### 2.3 UI v2 映射（DOING 屏）
| 屏元素 | 数据源 | 取数方式 |
|---|---|---|
| 目标卡列表 | `list_goals()` | REST GET `/api/goals`（**需新增**，§4.1） |
| 单目标进度/子任务 | `get_goal()` + `_goal_tasks()` | REST GET `/api/goals/:id` |
| 实时进度/状态变化 | `GOAL_UPDATED` / `GOAL_COMPLETED` 领域事件 | SSE 订阅（§3） |

### 2.4 写边界（红线）
- UI **不**能直接调 `create_goal/update_goal`。创建目标走 **Intent Gateway**：用户意图 → `INTENT_RECEIVED` → `INTENT_CONVERTED_TO_GOAL` → `GOAL_CREATED`（`eventbus.py` `DOMAIN_EVENT_NAMES` + `zz-events.js:128` 注释）。
- v2 的 DOING 屏"新建目标"= 在 Intent Line 输入意图，Runtime 决策是否转 Goal。**UI 只发文本意图，不构造 Goal 对象。**

---

## 3 · Runtime ↔ UI 事件契约（单一来源，已强制）

### 3.1 契约定义
- 后端 `eventbus.py:177` `DOMAIN_EVENT_NAMES`：**领域事件名唯一真相源**，必须与前端 `zz-events.js` 逐字一致（注释："单一事件名来源纪律，readiness §5。修改须同步两端，禁止新增同义事件名"）。
- 信封格式（`eventbus.py:222`）：`{"xiao6_event": <name>, "payload": <dict>, "ts": <unix>}`。
- 扇出通道：`TOPIC_SSE = "zz.sse"`（`eventbus.py:26`）→ 前端经 SSE（`/api/stream`，`server.py:312`）消费 → `zz-events.js` 派发 → **前端 AppState 更新**。

### 3.2 三类数据已有的领域事件（直接可用）
| 域 | 事件名（前后端一致） | 用途 |
|---|---|---|
| Goal | `GOAL_CREATED / GOAL_UPDATED / GOAL_PLANNED / GOAL_STARTED / GOAL_RUNNING / GOAL_COMPLETED / GOAL_FAILED` | DOING 屏实时同步 |
| Memory | `MEMORY_CREATED / MEMORY_STORED / MEMORY_LINKED / MEMORY_ARCHIVED / MEMORY_UPDATED` | KNOWN「记忆」实时同步 |
| Knowledge | ⚠️ **无独立 KNOWLEDGE_* 事件** | 见 3.3 |

### 3.3 Knowledge 事件的重要纪律
`zz-events.js:119` 注释明示：**`MEMORY_LINKED` 取代预留的 `KNOWLEDGE_LINKED`（单一来源，禁第二套事件）**。
→ 知识的关系变化经 `MEMORY_LINKED` 表达，**不应**新造 `KNOWLEDGE_LINKED`。v2 的 KNOWN「关系」视图须复用既有的 `MEMORY_LINKED` + `KNOWLEDGE_LINKED` 取消的约定，不得擅自扩展事件名（违反 §3.1 单一来源）。

---

## 4 · 安全映射方案（给实施阶段，本期不执行）

### 4.1 Goal 只读 REST（v2 唯一后端改动）
新增 `GET /api/goals` 与 `GET /api/goals/<id>`，**仅**调用既有 `list_goals()` / `get_goal()` / `_goal_tasks()`，不加写、不加状态机。
- 字段直通 `Goal.to_dict()`（§2.1），不发明新字段。
- 不引入新事件；实时更新仍走既有 `GOAL_*` SSE。
- 这是 `07` P0-2 的精确落地，也是 P0 三类数据中**唯一**的真实后端动作。

### 4.2 Memory 只读复用（零改动）
- KNOWN「记忆」视图 → `GET /api/memories`（`get_memories(limit=500)`，`server.py:677`）。
- 记忆图谱（如需要）→ `GET /api/memories/graph`（`get_memory_graph()`，nodes+edges），可作为「关系」视图的记忆侧输入。
- 归档/恢复是**既有 POST**（`_handle_memories_post:701`，仅切 `archived` 位、不删数据）——v2 若暴露此操作，走该既有端点，不新建。

### 4.3 Knowledge 只读复用（零改动）
- KNOWN「知识」视图 → `GET /api/knowledge` → `knowledge.list_docs()` + `stats()`（`server.py:399`）。
- 文档结构（实测 `knowledge_runtime/engine.py:266` `list_docs` 返回）：`id, title, category, path, summary, tags, updated, links...`。
- 目录树 8 类（`G:/xiao6/knowledge/`）：`concepts / daily / decisions / experiences / failures / people / projects / rules` + `index.md`。
- 关系数据：`knowledge_manifest.json` 含 `nodes` + **35 条 `relations`**（`by_domain` / `by_type` / `bad_links` / `validation_ok`）；运行时 `knowledge_runtime/links.py:55` `related()` 提供文档间关联。

### 4.4 KNOWN「关系」视图的数据合成（Galaxy 重生）
`05` 裁定：关系投影数据层（`galaxy-state.js`）保留重生。其输入在后端已齐备，**无需新建 Runtime**：
- 记忆侧：`get_memory_graph()`（nodes+edges）
- 知识侧：`knowledge_manifest.relations`（35 条）+ `links.related()`
- 目标侧：`goals.parent_id` + `_goal_tasks()` 的 goal↔task 边
- 合成原则：v2 的「关系」视图在**前端/轻量层**把以上三源投影为统一节点图（力导向，无 3D），**不**新增后端服务、不新增事件（§3.3 纪律）。

---

## 5 · 边界红线清单（实施阶段必须守住）

| # | 红线 | 依据 | 违反后果 |
|---|---|---|---|
| B1 | UI 只 GET 快照 + 收 SSE，不直接读后端内部表 | `eventbus.py:222` 注释"UI 永不直接读后端内部数据" | 破坏单一状态源 |
| B2 | UI 写操作只经 Intent Gateway，不发 Goal/Memory 构造 | `zz-events.js:128` 意图流 | Runtime 状态机被绕过 |
| B3 | 领域事件名只能在 `DOMAIN_EVENT_NAMES` 内，禁新增同义 | `eventbus.py:177,235` | 前后端契约漂移 |
| B4 | Knowledge 关系复用 `MEMORY_LINKED`，禁造 `KNOWLEDGE_LINKED` | `zz-events.js:119` | 第二套事件污染 |
| B5 | Goal REST 仅读，不含写/状态机/新事件 | `goals.py` 读 API 完备 | 重蹈"前端直改状态" |
| B6 | 关系图合成在前端轻量层，不新增后端 Runtime | `05` G4–G5 | 架构膨胀 |
| B7 | Memory/Knowledge 端点**复用既有**，不为 v2 新建写路径 | `server.py:352,399` 已存在 | 重复实现 |

---

## 6 · 审计结论（对应 P0-A 目标）

1. **Goal/Memory/Knowledge 真实数据均可安全映射到 UI v2**，且后端 90% 能力已就绪。
2. **唯一真实后端缺口 = Goal 只读 REST**（`07` P0-2 精确成立）；Memory/Knowledge 缺口纯属旧 UI 未消费既有端点，**零后端改动**即可接管。
3. **Runtime↔UI 边界已由 eventbus/zz-events 契约锁定**：快照(GET) + 事件(SSE) + 意图(Intent Gateway) 三通道，v2 严格遵循即可保证"UI 是观察者，Runtime 是决策者"。
4. **KNOWLEDGE 事件纪律**（B4）与 **事件名单一来源**（B3）是实施时最易踩的坑，已显式标红。

> 本报告为只读审计产物。下一动作（实施）须待人工 Review 通过，且仍受 `07` 阶段纪律约束：**先 P0-1~4 接数据，再 P1 拆结构**。

---

*P0-A 完成。STOP —— 等待人工 Review，不进入代码。*
