# 小6 AI OS 2.0 — Phase A 任务八：崩溃恢复（RECOVERY_REPORT）

> Sprint: AI OS Phase A — Core Intelligence Sprint v1.0
> 任务: 任务八（Crash Recovery / P15）→ 输出本报告
> 上游: `CORE_AUDIT.md`（F4/F6 横切缺口）、`CORE_LIFECYCLE_REPORT.md`（RECOVERING 态）、`METRICS_REPORT.md`（recovery.count 钩子）
> 日期: 2026-08-05
> 状态: ✅ 设计完成；本任务 STOP，待逐任务 Review

---

## 1. 目的与范围

**目标**：落实 ADR-006 / 红线 P15「Crash-Recoverable」——进程崩溃或重启后，AI Core 能从持久化检查点恢复**进行中**的工作，满足 **无丢失、无重复、幂等** 三条铁律。

**关键边界**：
- 本任务是**横切子系统**（与 Lifecycle / Health / Metrics / Logging 同级），不属于 L2 Goal / L3 Workflow / L4 Agent 引擎本身（那些已存在或属后续 Phase）。
- **增量原则**：崩溃恢复逻辑**已部分实装**（`tasks.py:recover_tasks`，`server.py:2606` 启动调用）。本设计是**扩展**而非重建，严禁另起一套恢复机制造成重复。
- 不在范围：Knowledge/Memory 引擎的恢复（Phase B/C）；文件系统/数据库本身的灾备（由 `db.py` SQLite 事务保证）。

---

## 2. 现状审计（已落地 vs 缺口）

### 2.1 已落地（复用，不重建）

| 能力 | 位置 | 语义 |
|------|------|------|
| 任务级检查点 | `tasks.py` `tasks` 表（status: `open`/`running`/`paused`/`done`/`failed`） | 多步任务持久化于 SQLite，进程重启仍在 |
| 启动恢复 | `tasks.py:165 recover_tasks()` | 把 `running` 翻回 `open`，使其可被续跑 |
| 启动钩子 | `server.py:2606` | `main()` 启动即调用 `recover_tasks()`，返回恢复数并日志提示 |
| 续跑上下文 | `tasks.py:get_open_tasks()` → ACI 注入「未完成任务」 | 下一轮对话中小6可接着干 |

### 2.2 缺口（F4/F6 横切缺失，本任务补）

1. **G1 — Goal 级未恢复**：`AgentRuntime._queue` 为纯内存列表（`agent_runtime.py:46 []`），`start()`（`:59`）**不**从 DB 重读 `active` 目标。进程崩溃时正在自主编排的 `active` 目标（已出队、正在执行）重启后**不会**被重新入队 → 静默丢弃自主执行资格（其下属 tasks 虽被 `recover_tasks` 翻回 `open`，但 AgentRuntime 不会自动接管）。
2. **G2 — 未接入 RECOVERING 态**：`recover_tasks()` 在 `main()` 里裸跑，`CORE_LIFECYCLE_REPORT` 定义的 `RECOVERING` 态（任务二 §2/§7）无对应执行体，内核走 `BOOT→READY` 而跳过恢复语义。
3. **G3 — 无恢复度量**：缺 `recovery.count` / `recovery.last_outcome`（任务七 `METRICS_REPORT` 已预留钩子，未接线）。
4. **G4 — 失败无治理**：`recover_tasks()` 异常静默返回 0（`tasks.py:176`），DB 损坏等致命情况不阻断启动，内核带病 READY。

---

## 3. 设计：三层恢复 + 生命周期接入

### 3.1 恢复流程（接入 RECOVERING 态）

```
main():
  listen(port)
  ai_core_lifecycle.boot()                 # BOOT：子系统自检（任务六）
  n_task = recover_tasks()                 # 既有：tasks 表 running→open
  n_goal = ai_core_recover_goals()         # 新增：active 目标重入队（G1）
  recovery.record(n_task + n_goal)         # 度量钩子（G3，任务七）
  ai_core_lifecycle.mark_ready_or_stop()   # 成功→READY；致命失败→STOPPING（G4）
  if FEATURE_AGENT_RUNTIME: agent_runtime.runtime.start()
  serve_forever()
```

- `BOOT → RECOVERING`：当 `recover_tasks()` 或 `ai_core_recover_goals()` 返回 `n>0`（检测到中断痕迹），内核经 `RECOVERING` 态执行恢复；`n==0` 则直通 `READY`。
- `RECOVERING → READY`：恢复成功（含「无可恢复」的 0 情况）。
- `RECOVERING → STOPPING`：恢复抛致命异常（如 DB 不可打开）→ 拒绝服务、有序退出（G4）。

### 3.2 Goal 级恢复（补 G1，幂等重入队）

新增 `ai_core/recovery.py`（与 `lifecycle.py` 同进程、同 Runtime，ADR-001），核心是**复用既有目标行、不新建**——避免与 `submit_goal`（会 `create_goal` 新建行）重复：

```python
# ai_core/recovery.py（设计骨架，Phase A 实现落地）
from goals import list_goals
from agent_runtime import runtime as _rt

def ai_core_recover_goals() -> int:
    """把 DB 中 active、但不在 AgentRuntime 实时队列里的目标，幂等重入队。"""
    recovered = 0
    try:
        for g in list_goals(status="active"):        # goals.py:252 已支持 status 过滤
            if g.id not in _rt._queue:               # 内存队列无此目标 → 崩溃时丢失资格
                _rt.requeue_goal(g.id)               # ← 新增：重入队既有 id，不新建行
                recovered += 1
    except Exception:
        raise                                        # 上抛给 lifecycle 决策 STOPPING（G4）
    return recovered
```

`AgentRuntime` 需补一个**轻量**方法（不改动 `submit_goal` 的写入语义）：

```python
# agent_runtime.py 新增（不新建 goal 行）
def requeue_goal(self, goal_id: int) -> None:
    if goal_id not in self._queue:
        self._queue.append(goal_id)                  # 仅入队既有 id，幂等
```

**幂等性论证**：`recover_tasks()` 仅把 `running→open`，翻完后无 `running` 残留，二次启动不再翻转；`requeue_goal` 仅当 `id ∉ _queue` 才追加，二次启动 `_queue` 已被填充，不会重复入队。两路均满足**幂等**。

### 3.3 度量与事件（G3 / F1）

- **度量**：`recovery.count`（累计恢复对象数）、`recovery.last_outcome`（`ok`/`fail`）。经任务七 `MetricsCollector` 的环形缓冲采集，暴露 `GET /metrics`。恢复调用处 `recovery.record(...)` 即写入。
- **事件（F1 契约漂移规避）**：恢复状态变化**不新增** SYSTEM 事件名，复用 `publish_system("agent_state", {…, "core_state": "recovering"/"ready", "recovery": {"tasks": n_task, "goals": n_goal}})` 信封（同 `CORE_LIFECYCLE_REPORT` §5）。如需专属事件必须先按 F1 修正契约文档的 SYSTEM 计数。

---

## 4. 实现骨架（不新开 Runtime / Memory / EventBus）

新增 `ai_core/recovery.py`（与 `lifecycle.py`、`metrics.py` 并列，单进程）：

```python
class Recovery:
    def __init__(self): self._count = 0; self._last = None
    def run(self) -> dict:
        """返回 {tasks, goals, outcome}；致命异常上抛。"""
        n_task = recover_tasks()                     # 既有，零改动调用
        n_goal = ai_core_recover_goals()             # 新增，G1
        self._count += n_task + n_goal
        self._last = "ok"
        return {"tasks": n_task, "goals": n_goal, "outcome": "ok"}
    def record(self, d: dict): ...                  # 钩子：写 MetricsCollector

ai_core_recovery = Recovery()
```

**单例共存纪律**：`ai_core_recovery`（恢复执行体）与 `agent_runtime.runtime`（L4 编排机）、`ai_core_lifecycle`（全局态）三者同跑唯一 Runtime 进程，职责不交叉、互不替代。

---

## 5. 与既有模块的接线点

| 接线 | 模块 | 改动性质 |
|------|------|----------|
| 启动调用 | `server.py:2606` 区块 | 包裹进 `ai_core_recovery.run()` + lifecycle 决策 |
| Goal 重入队 | `agent_runtime.py` 新增 `requeue_goal` | 新增方法，不改 `submit_goal`/`_loop` 既有语义 |
| Goal 读取 | `goals.py:list_goals(status="active")` | **零改动**（已支持 status 过滤） |
| 任务恢复 | `tasks.py:recover_tasks()` | **零改动**（已幂等） |
| 度量 | `metrics.py` `MetricsCollector` | 新增 `recovery.*` 指标类（任务七已预留） |
| 生命周期 | `lifecycle.py` `RECOVERING` 态 | 触发 `recovery.run()`，结果驱动 READY/STOPPING |

---

## 6. 红线合规

| 红线 | 合规性 | 说明 |
|------|--------|------|
| 单 Runtime | ✅ | 恢复逻辑同进程，无第二 Runtime |
| 单 EventBus | ✅ | 复用 `publish_system("agent_state")` |
| 单 Permission | ✅（无关） | 恢复不裁决权限，仅重入队 |
| No God Module | ✅ | `recovery.py` 仅协调既有 `recover_tasks`/`requeue_goal`，不含执行/持久化主体 |
| 增量演进 | ✅ | 复用 `recover_tasks`/`list_goals`，仅补 `requeue_goal` 薄方法 + 新增协调单例 |
| Local First | ✅ | 恢复源为本地 SQLite（`xiao6.db`），无外部依赖 |
| 事件契约 | ✅ | 复用既有事件名，不扩 SYSTEM 命名空间（F1） |
| 无重复/无丢失/幂等 | ✅ | `recover_tasks` 幂等；`requeue_goal` 按 `_queue` 存在性去重；不新建 goal 行 |

---

## 7. 后续动作

- 实现：`ai_core/recovery.py` + `agent_runtime.requeue_goal` + `server.main()` 启动包裹（任务十 Boot 顺序细化）。
- 联调：与任务二 `RECOVERING` 态、任务六 Health（DB 探针）、任务七 `recovery.count` 度量对接。
- **本任务为设计交付；实际代码落地待 Phase A 实现阶段（经 Review 批准）。**

**STOP**：任务八设计完成。待 Review 批准后进入任务九（Logging Standard）。未经批不得修改代码、不得扩大范围。
