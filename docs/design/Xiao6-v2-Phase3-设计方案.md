# 《Xiao6 v2 · Phase 3 设计方案：目标系统（Goal System）》

> 版本：v2-Phase3 设计稿（B 设计 · 待 C 批准）
> 作者：Senior Developer（高级开发工程师）
> 日期：2026-07-31
> 依据：《Xiao6-v2-核心架构规范.md》（最高宪法）+ 《Xiao6-v2-Phase2-设计方案.md》
> 前置：P0（Context Engine 骨架）+ P1（用户模型 + 情节记忆）+ P2（EventBus + 世界模型 + 人格引擎）已落地并通过真机验证

---

## 一、目标与范围

### 1.1 要解决什么

现有 `tasks.py` 已经能管理**多步骤执行单元**（创建任务、更新进度、完成），但它缺少一层**"为什么做这件事"**的语义：

- 用户说"帮我做一套个人网站"，应该产生一个 **Goal**，而不是一个 Task。
- Goal 应该能自顶向下拆解成多个 Task；Task 完成时 Goal 的进度自动推进。
- 多个 Goal 同时推进时，Xiao6 应该在每次对话前把**当前活跃目标**注入上下文，避免"聊完就忘"。
- 长期目标（如"今年减脂 5kg"）应随用户画像一起演化，成为主动提醒与决策的依据。

### 1.2 Phase 3 做哪些、不做哪些

**做**：

1. **Goal 数据模型与持久化**（`goals` 表 + `tasks.goal_id` 外键迁移）。
2. **Goal 管理模块**（`goals.py`）：增删改查、层级（parent/children）、进度聚合、生命周期。
3. **Goal → Context 注入**（`context/goal_source.py`）：按 `ContextSource.GOAL` 接入 Context Engine。
4. **LLM 工具暴露**（`set_goal` / `update_goal` / `list_goals` / `delete_goal` / `plan_goal`）。
5. **Tick 级主动检查**：未推进的活跃目标到期前主动提醒；已完成目标触发复盘提示。
6. **EventBus 事件**：`GoalCreated` / `GoalUpdated` / `GoalProgressChanged` / `GoalCompleted`。

**不做**（明确边界，避免范围膨胀）：

- 不实现自动规划调度器（Auto-Planner）：`plan_goal` 工具只负责**一次性 LLM 拆解**并写入子任务，不做持续重排。
- 不实现多目标冲突仲裁：本 Phase 仅注入上下文，由 LLM 在对话中自行权衡。
- 不改前端路由：仅复用现有 SSE/场景卡通道做主动提醒；前端 Goal 面板留待后续独立 PR。
- 不做 Knowledge Graph 实体关联：那是 Phase 4 候选。

### 1.3 与现有任务系统的关系

| 概念 | 粒度 | 生命周期 | 对应模块 |
|---|---|---|---|
| **Goal** | 用户意图/项目/长期方向 | 数天 ~ 数年 | `goals.py`（新增） |
| **Task** | Goal 拆解后的可执行步骤 | 数分钟 ~ 数天 | `tasks.py`（已有） |
| **Reminder** | 一次性时间触发 | 一次性 | `proactive.py`（已有） |

**约束**：一个 Task 可选归属一个 Goal；Goal 的进度由其下属 Task 的完成比例加权计算。没有子 Task 的 Goal 可手动维护 `progress`。

---

## 二、关键决策（6 项，待批准）

| # | 决策 | 理由 / 依据 |
|---|---|---|
| D1 | **Goal System 默认 ON（`FEATURE_GOAL_SYSTEM=true`），关闭即不注册 `GoalSource`，工具列表中不出现 goal 工具** | 沿用 P1/P2 Flag 范式；新增能力默认开以便验收，用户路径零变化（无 goal 时 Prompt 不注入目标块）。 |
| D2 | **Goal 与 Task 分表；Task 加 `goal_id` 列作为软外键** | 复用并强化已有 `tasks` 表，避免推倒重来；`goal_id` 通过 `_migrate_tasks` 静默添加，向后兼容（§1.6）。 |
| D3 | **Goal 进度优先由子 Task 自动聚合；也允许用户/LLM 手动覆盖** | 大多数目标需要拆解执行，自动聚合减少人工维护；手动覆盖保留灵活性。 |
| D4 | **目标层级仅支持 2 层（Goal → Task），不实现无限嵌套子目标** | 降低首次实现的复杂度与查询成本；如后续需要，可通过 `parent_id` 扩展。 |
| D5 | **Context 注入只取「活跃（active）+ 近期有进展」的目标，最多 3 个，硬上限约 300 token** | 避免 Prompt 爆炸；宪法 §4.1 要求 Context 来源受 Budget 约束。 |
| D6 | **主动提醒由 Tick 每 5 分钟扫描一次；只在用户在线且目标到期前 ≤24h 未推进时推送一次** | 避免过度打扰；利用已有 `proactive.py` TICK 机制，不新增后台线程。 |

---

## 三、架构总览

```
┌────────────────────────────────────────────────────────────────┐
│  UI Layer（Electron / Browser）                                 │
│  聊天框 ← 用户说"帮我做个人网站"                                │
├────────────────────────────────────────────────────────────────┤
│  API Layer（server.py）                                         │
│  `/api/chat` → Agent Runtime → Context Engine                   │
├────────────────────────────────────────────────────────────────┤
│  Cognitive Services                                             │
│  Context Engine                                                 │
│    SourceRegistry                                               │
│      ├─ MemorySource                                            │
│      ├─ UserModelSource         (P1)                            │
│      ├─ EpisodicSource          (P1)                            │
│      ├─ WorldStateSource        (P2)                            │
│      ├─ PersonalitySource       (P2)                            │
│      └─ GoalSource          ★新增 (FEATURE_GOAL_SYSTEM)        │
│           └─ 读取 goals.py 的 active_goals_snapshot()          │
├────────────────────────────────────────────────────────────────┤
│  Goal System（新增，扁平目录）                                   │
│    goals.py                                                     │
│      ├─ Goal dataclass                                          │
│      ├─ CRUD + progress aggregation                             │
│      ├─ plan_goal() 一次性 LLM 拆解                             │
│      └─ publish GoalCreated/Updated/Progress/Completed          │
├────────────────────────────────────────────────────────────────┤
│  Capability & Execution                                         │
│    tools.py 新增 goal 工具（在 Feature Flag 下注册）             │
│    tasks.py 复用并扩展 goal_id 关联                              │
├────────────────────────────────────────────────────────────────┤
│  Event Bus（eventbus.py，P2 已建）                               │
│    GoalCreated / GoalUpdated / GoalProgressChanged              │
│    GoalCompleted → 可被 proactive / scene / SSE 桥消费          │
├────────────────────────────────────────────────────────────────┤
│  Data Layer                                                     │
│    xiao6.db                                                │
│      ├─ goals（新表）                                           │
│      └─ tasks.goal_id（迁移新增列）                             │
└────────────────────────────────────────────────────────────────┘
```

依赖方向（DAG，无环）：

- `context/goal_source.py` → `goals.py`（读取快照）
- `goals.py` → `eventbus.py`（发布事件）
- `goals.py` → `db.py`（持久化）
- `tools.py` → `goals.py`（调用 API）
- `tasks.py` → 可选接受 `goal_id`，但不反向依赖 `goals.py`（避免环）
- `proactive.py` → `goals.py`（扫描到期目标）

---

## 四、数据模型

### 4.1 `goals` 表（新增）

```sql
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,              -- 目标标题（如"搭建个人网站"）
    description TEXT DEFAULT '',      -- 补充描述
    status TEXT DEFAULT 'active',     -- active / paused / completed / archived
    priority TEXT DEFAULT 'medium',   -- low / medium / high / critical
    horizon TEXT DEFAULT 'short',     -- short(本周) / medium(本月) / long(长期)
    progress INTEGER DEFAULT 0,       -- 0-100
    parent_id INTEGER DEFAULT NULL,   -- 预留：父目标ID（D4 本期只存 NULL）
    due_date TEXT DEFAULT NULL,       -- 截止日期（ISO 日期或 datetime）
    completed_at TEXT DEFAULT NULL,   -- 完成时间
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);
```

### 4.2 `tasks` 表迁移

通过 `_migrate_tasks` 追加：

```sql
ALTER TABLE tasks ADD COLUMN goal_id INTEGER DEFAULT NULL;
```

已有 Task 不受影响；新增 Task 可指定归属 Goal。

### 4.3 Python 值对象（`goals.py`）

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Goal:
    id: int
    title: str
    description: str = ""
    status: str = "active"          # active / paused / completed / archived
    priority: str = "medium"        # low / medium / high / critical
    horizon: str = "short"          # short / medium / long
    progress: int = 0               # 0-100
    parent_id: Optional[int] = None
    due_date: Optional[str] = None
    completed_at: Optional[str] = None
    created: str = ""
    updated: str = ""
```

---

## 五、模块设计

### 5.1 `goals.py` — 核心服务

**职责**：Goal 的 CRUD、进度聚合、一次性 LLM 拆解、事件发布。

**对外 API**：

```python
def create_goal(title: str, description: str = "", priority: str = "medium",
                horizon: str = "short", due_date: Optional[str] = None) -> Goal: ...

def update_goal(goal_id: int, **fields) -> Goal: ...

def delete_goal(goal_id: int) -> bool: ...

def get_goal(goal_id: int) -> Optional[Goal]: ...

def list_goals(status: Optional[str] = None, horizon: Optional[str] = None,
               limit: int = 50) -> list[Goal]: ...

def list_active_goals(limit: int = 5) -> list[Goal]: ...

def recalc_progress(goal_id: int) -> int:
    """根据子 Task 完成比例重新计算目标进度，返回 0-100。"""
    ...

def plan_goal(goal_id: int) -> list[int]:
    """调用 LLM 把 Goal 拆解为若干 Task，写入 tasks 表并关联 goal_id，返回 task_id 列表。"""
    ...
```

**事件发布**：

```python
from eventbus import bus

def _emit(event_type: str, goal: Goal, extra: dict | None = None):
    bus.publish("zz.goal", {
        "event": event_type,
        "goal_id": goal.id,
        "title": goal.title,
        "status": goal.status,
        "progress": goal.progress,
        **(extra or {})
    }, source="goals")
```

事件类型：`GoalCreated`, `GoalUpdated`, `GoalProgressChanged`, `GoalCompleted`。

### 5.2 `context/goal_source.py` — Context 适配器

```python
from context.interfaces import ContextSourceProvider
from context.models import ContextItem, ContextSource

class GoalSource(ContextSourceProvider):
    name = "goal"

    def collect(self, ctx) -> list[ContextItem]:
        try:
            import goals
            snapshot = goals.active_goals_snapshot(limit=3)
            if not snapshot:
                return []
            content = "【当前目标】\n" + snapshot
            return [ContextItem(source=ContextSource.GOAL, content=content,
                                priority=0.7, recency=0.8, importance=0.7,
                                token_est=300)]
        except Exception as e:
            # 单源失败隔离，不影响其他来源
            return []
```

`active_goals_snapshot()` 输出示例：

```
- [#3] 搭建个人网站（进度 40%，截止 2026-08-15，优先级 high）
  子任务：买域名 ✓；搭框架 ✓；写内容 □；部署上线 □
- [#1] 读完《设计心理学》（进度 25%，长期目标）
  最近推进：2026-07-30 读完第一章
```

### 5.3 `tools.py` — 新增工具（Feature Flag 注册）

| 工具名 | 作用 | 是否危险 |
|---|---|---|
| `set_goal` | 创建目标 | 否 |
| `update_goal` | 更新目标状态/进度/优先级 | 否 |
| `list_goals` | 列出目标 | 否 |
| `delete_goal` | 删除目标 | 中（需二次确认） |
| `plan_goal` | 拆解目标为任务 | 否（仅写入 Task） |

工具 schema 示例（`set_goal`）：

```json
{
  "name": "set_goal",
  "description": "为用户创建一个中长期目标。",
  "parameters": {
    "type": "object",
    "properties": {
      "title": {"type": "string"},
      "description": {"type": "string"},
      "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
      "horizon": {"type": "string", "enum": ["short", "medium", "long"]},
      "due_date": {"type": "string", "description": "YYYY-MM-DD 或 ISO datetime，可选"}
    },
    "required": ["title"]
  }
}
```

### 5.4 `tasks.py` — 复用并扩展

- `set_task()` 增加 `goal_id: Optional[int] = None` 参数。
- `update_task_step()` 当 Task 完成时，自动调用 `goals.recalc_progress(task.goal_id)`。
- `get_open_tasks()` 支持按 `goal_id` 过滤。

**注意**：`tasks.py` 不 `import goals`，避免潜在循环依赖。进度回调通过 EventBus 订阅 `GoalProgressChanged` 或 tools 层显式调用。为保持简单，本方案采用：**tools.py 在 `tool_complete_task` 完成时显式调用 `goals.recalc_progress()`**。

### 5.5 `proactive.py` — 主动提醒集成

在现有 TICK 扫描中增加 `check_goal_deadlines()`：

```python
def _check_goal_deadlines():
    """扫描 24h 内到期且近 7 天无进展的活跃目标，推送一次主动提醒。"""
    ...
```

提醒内容经 SSE 推送到前端，格式沿用 `xiao6_proactive`。

---

## 六、Context 集成与 Prompt 影响

### 6.1 注册方式

在 `context/builder.py` 中追加：

```python
if getattr(config, "FEATURE_GOAL_SYSTEM", False):
    from context.goal_source import GoalSource
    registry.register(GoalSource())
```

### 6.2 Prompt 注入位置

目标块放在【用户模型】之后、【世界状态】之前，与现有 Source 顺序保持一致：

```
【身份】...
【用户模型】...
【当前目标】...        ← 新增
【世界状态】...
【人格】...
【情节记忆】...
【对话历史】...
```

### 6.3 Budget 约束

- `GoalSource` 产出 `token_est=300`，被 `ContextBudget` 统一裁剪。
- 若总预算紧张，目标块优先级 `0.7` 高于情节记忆（`0.5`），低于用户模型（`0.9`）。

---

## 七、与现有工具/工作流的集成

### 7.1 意图路由

在 `tools.py` 的 `detect_intents()` 中识别目标相关意图：

- "定一个目标 / 我想做 X / 帮我规划 X" → 调用 `set_goal`
- "拆成几步 / 怎么推进 X" → 调用 `plan_goal`
- "我有什么目标 / 进度怎样" → 调用 `list_goals`
- "完成了 / 放弃 X" → 调用 `update_goal(status=completed/archived)`

### 7.2 与 Daily Briefing 联动

每日简报可追加一句：

```
- 今日到期目标：#3 搭建个人网站（进度 40%）
```

由 `proactive.py` 的 briefing 生成逻辑调用 `goals.list_active_goals(status='active', horizon='short')`。

---

## 八、兼容、回退与迁移

### 8.1 向后兼容

- 新增 `goals` 表：不影响旧数据。
- `tasks.goal_id` 列：默认 `NULL`，旧 Task 不受影响。
- 工具注册：由 `FEATURE_GOAL_SYSTEM` 控制；关闭时 `tools.py` 不注册 goal 工具，`Context Builder` 不注册 `GoalSource`。
- SSE 事件格式：无变化；Goal 主动提醒复用 `xiao6_proactive`。

### 8.2 Rollback

1. **配置回退**：`.env` 中 `FEATURE_GOAL_SYSTEM=false`，重启后端，Goal 能力瞬时消失，用户路径与 Phase 2 一致。
2. **代码回退**：revert 本 Phase 提交；数据库新增表/列保留但不再被读取，安全。

### 8.3 数据库迁移

- `db.py` 中新增 `goals` 表创建。
- `_migrate_tasks` 追加 `goal_id` 列迁移。
- 全部使用 `IF NOT EXISTS` / `ALTER TABLE ADD COLUMN`，支持热升级（重启时自动迁移）。

---

## 九、测试与验收

### 9.1 单元测试

- `goals.py`：CRUD、进度聚合、日期解析。
- `context/goal_source.py`：无活跃目标时返回空；异常时隔离。
- `tools.py`：goal 工具 schema 注册与参数校验。

### 9.2 集成测试

- 用户说"我想在 8 月 15 日前搭好个人网站" → 应创建 Goal，且 Prompt 中注入目标块。
- 调用 `plan_goal` → 应生成子 Task 并关联 `goal_id`。
- 完成一个子 Task → Goal 进度自动更新。
- 目标到期前未推进 → Tick 触发一次主动提醒。

### 9.3 验收标准

| 验收项 | 通过标准 |
|---|---|
| Goal CRUD | `set_goal`/`list_goals`/`update_goal`/`delete_goal` 工具可用 |
| 上下文注入 | 有活跃目标时，Prompt 中出现【当前目标】块 |
| 进度聚合 | 完成子 Task 后，Goal 进度按任务比例更新 |
| 主动提醒 | 到期前 ≤24h 未推进的目标触发一次 `xiao6_proactive` |
| 回退 | `FEATURE_GOAL_SYSTEM=false` 后系统行为与 Phase 2 一致 |

---

## 十、风险与缓解

| 风险 | 等级 | 缓解 |
|---|---|---|
| Prompt 过长 | 中 | `GoalSource` 硬上限 300 token，最多 3 个目标；受 Budget 裁剪。 |
| 目标创建过度打扰 | 中 | LLM 不会自动创建目标，只在用户明确表达意图或调用工具时创建。 |
| Task 完成 → Goal 进度聚合失败 | 低 | `tool_complete_task` 中显式 `try/except` 调用 `recalc_progress`，失败不影响 Task 完成。 |
| 循环依赖 | 低 | `tasks.py` 不导入 `goals.py`；进度回调由 tools 层触发。 |
| 数据库迁移冲突 | 低 | 使用标准 `ALTER TABLE ADD COLUMN` + `_migrate_tasks` 模式，与已有迁移一致。 |

---

## 十一、实现步骤建议（D 实现阶段）

按依赖顺序，每步可独立提交：

1. **Step 3.1**：数据库层 — 新增 `goals` 表、`tasks.goal_id` 迁移。
2. **Step 3.2**：`goals.py` 核心服务 — CRUD + 进度聚合 + 事件发布。
3. **Step 3.3**：`context/goal_source.py` + `builder.py` 注册 + `config.py` `FEATURE_GOAL_SYSTEM`。
4. **Step 3.4**：`tools.py` 新增 goal 工具 + `detect_intents` 目标意图识别。
5. **Step 3.5**：`tasks.py` 扩展 `goal_id` + 完成时自动刷新 Goal 进度。
6. **Step 3.6**：`proactive.py` TICK 接入目标到期提醒。
7. **Step 3.7**：单元/集成测试 + 真机验证。

每步均符合 v2 宪法 "增量演进" 原则，可独立回滚。

---

## 十二、待批准问题

1. D1–D6 是否全部批准？特别是 **D4（仅 2 层目标层级）** 与 **D6（24h 主动提醒阈值）**。
2. `plan_goal` 拆解是否默认调用 LLM（消耗 Agnes token），还是允许纯规则拆解？
3. 是否需要在每日简报中默认展示今日到期目标？

批准后即可进入 D 实现阶段。
