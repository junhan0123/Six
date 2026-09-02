# 小6 AI OS 2.0 — Phase A 任务二：AI Core 生命周期（CORE_LIFECYCLE_REPORT）

> Sprint: AI OS Phase A — Core Intelligence Sprint v1.0
> 任务: 任务二（AI Core Lifecycle）→ 输出本报告
> 上游: `CORE_AUDIT.md`（发现 F4/F7 直接驱动本设计）
> 日期: 2026-08-05
> 状态: ✅ 设计完成；本任务 STOP，待逐任务 Review

---

## 1. 目的与范围

**目标**：定义小6 **AI Core（L5 + 横切）的全局生命周期**，使内核具备可观测、可恢复、可有序关闭的运行态。

**关键边界（来自审计 F4）**：
- 现有 `agent_runtime.py` 的 `IDLE→PLANNING→EXECUTING→REFLECTING` 是 **L4 Agent Engine 的任务级状态机**，已实装且默认在线（F5）。
- 本设计定义的 **全局 AI Core 生命周期** 与 L4 状态机**正交**——前者描述"整个内核是否在跑/能否接活/正在恢复"，后者描述"某个具体目标正在被编排到哪一步"。
- **绝不**在 L5 重造编排机；AI Core 生命周期只做"内核级"状态治理。

**不在范围**：L2 Goal / L3 Workflow / L4 Agent 的生命周期（已存在）；Knowledge/Memory 引擎生命周期（Phase B/C）。

---

## 2. 状态模型（7 态）

```
        ┌─────────────┐
        │   BOOT      │  内核进程启动 → 子系统自检/初始化
        └──────┬──────┘
               │ 全部子系统就绪 (_boot_ready_event 置位)
               ▼
        ┌─────────────┐
        │   READY     │  可接活；空闲等待请求
        └──────┬──────┘
       ┌───────┴───────┐
       │ 有请求/有任务  │  无请求且收到停机信号
       ▼               ▼
 ┌─────────────┐  ┌─────────────┐
 │    BUSY     │  │  STOPPING   │  拒绝新请求，排空在途，释放资源
 └──────┬──────┘  └──────┬──────┘
       │ 需人工确认/外部  │               │ 排空完成
       │ 阻塞（如 confirm）│               ▼
       ▼               ┌─────────────┐
 ┌─────────────┐       │  SHUTDOWN   │  进程退出
 │  WAITING    │       └─────────────┘
 └──────┬──────┘
       │ 阻塞解除
       ▼
    (回到 BUSY)
       │ 执行异常/崩溃捕获
       ▼
 ┌─────────────┐
 │  RECOVERING │  从检查点恢复（P15）；成功→READY，失败→STOPPING
 └─────────────┘
```

| 状态 | 含义 | 是否接新请求 | 是否允许在途执行 |
|------|------|------------|----------------|
| BOOT | 启动初始化中 | 否 | 否 |
| READY | 空闲就绪 | 是 | 否（无在途） |
| BUSY | 正在处理请求/任务 | 是（排队） | 是 |
| WAITING | 阻塞等待外部（用户 confirm / IO / 锁） | 否（本请求挂起） | 是（本请求在途） |
| STOPPING | 有序停机中 | 否 | 是（排空在途） |
| RECOVERING | 崩溃后从检查点恢复 | 否 | 否 |
| SHUTDOWN | 已退出 | 否 | 否 |

---

## 3. 状态职责与守卫

- **BOOT → READY**：所有登记子系统（EventBus / Permission / Memory / Context / LLM / Executor / Boot，见任务六）健康检查通过，且 `_boot_ready_event` 置位（`server.py:2596`）。任一子系统自检失败 → 停留在 BOOT 并广播 `error`，不强行 READY。
- **READY → BUSY**：收到用户请求或 `AgentRuntime` 入队目标（`submit_goal`）。
- **BUSY → WAITING**：执行内环遇到需人工确认（`policy_engine` 返回 `confirm`）或外部阻塞；**复用既有 `AGENT_WAITING` 语义**（`agent_runtime.py:226,281`），不新造事件。
- **BUSY/WAITING → RECOVERING**：捕获未预期异常 / 进程重启检测（P15 检查点）；进入恢复流程（任务八）。
- **任意态 → STOPPING**：收到 SIGINT/SIGTERM 或显式 `shutdown()`；新请求拒绝（返回 503 类语义），在途请求给宽限排空。
- **STOPPING → SHUTDOWN**：在途排空完成 / 宽限超时 → 释放资源退出。

---

## 4. 实现骨架（不新开 Runtime）

新增模块 **`ai_core/lifecycle.py`**（位于 `xiao6-ui/ai_core/`，与 `agent_runtime.py` 同进程、同 Runtime，符合 ADR-001）：

```python
# ai_core/lifecycle.py（设计骨架，Phase A 实现任务落地）
from enum import Enum, unique
from dataclasses import dataclass, field

@unique
class CoreState(Enum):
    BOOT = "boot"; READY = "ready"; BUSY = "busy"
    WAITING = "waiting"; STOPPING = "stopping"
    RECOVERING = "recovering"; SHUTDOWN = "shutdown"

class AICoreLifecycle:
    """全局 AI Core 生命周期单例（与 AgentRuntime 任务级状态机正交）。"""
    def __init__(self):
        self._state = CoreState.BOOT
        self._lock = threading.Lock()
        self._transitions = { ... }   # 合法转移表（守卫）
        self._subscribers = []

    @property
    def state(self): return self._state

    def transition(self, to: CoreState, reason: str = "") -> bool:
        # 校验 _transitions 守卫；非法转移 raise/记录；广播变更
        ...

    def boot(self):       # 由 server.main() 调用（F7）
        self.transition(CoreState.BOOT)
        # 触发各子系统自检（委托任务六 Health Check）
        ...
        self.transition(CoreState.READY)

    def mark_busy(self, reason): ...
    def mark_waiting(self, reason): ...
    def mark_recovering(self, checkpoint): ...   # P15
    def shutdown(self, graceful=True): ...

# 进程级单例（与 agent_runtime.runtime 同列，不冲突）
ai_core_lifecycle = AICoreLifecycle()
```

**单例共存纪律**：`ai_core_lifecycle`（全局内核态）与 `agent_runtime.runtime`（L4 编排机）是两个不同职责的单例，均跑在唯一 Runtime 进程内，互不替代。

---

## 5. 事件广播（处理 F1 契约漂移）

生命周期变更经 **既有 `publish_system("agent_state", …)`** 通道广播（`agent_runtime.py:658-669` 已用此通道发 `state/hud_state`），**不新增系统事件名**，从而避免扩大 SYSTEM 命名空间（F1）。

建议扩展 `agent_state` 信封，新增字段（向后兼容，旧消费者忽略新字段）：
```python
publish_system("agent_state", {
    "core_state": ai_core_lifecycle.state.value,   # 新增：全局内核态
    "event": event, "state": self.state,            # 沿用既有 AgentRuntime 字段
    "current_goal": ..., "reason": reason,
})
```
**若确需新增专属系统事件**（如 `ai_core_lifecycle`），必须先按 F1 处置：把 SYSTEM 事件总数正式入账并更新 `01` 红线文档的 "SYSTEM=8" → 实际值，不得绕过 `SYSTEM_EVENT_NAMES` 校验。

---

## 6. 与 server.main() 启动集成（F7）

`server.py:2601 main()` 当前流程：端口监听 → 后台自检线程 → `_boot_ready_event.set()`(`:2639`) → （若启用）`agent_runtime.runtime.start()`(`:2686-2690`)。

**改造（任务十 Boot Sequence 细化，此处先定接口）**：
```
main():
  listen(port)                         # 立即监听
  ai_core_lifecycle.boot()             # ← 新增：置 BOOT，跑子系统自检
  # 后台自检线程置 _boot_ready_event（沿用）
  # boot() 内部等待 _boot_ready_event → READY
  if FEATURE_AGENT_RUNTIME: agent_runtime.runtime.start()   # L4 编排机在核心就绪后启动
  serve_forever()
```
生命周期单例在 `agent_runtime.runtime` 之前进入 READY，保证"内核就绪"先于"接活编排"。

---

## 7. 崩溃恢复态（P15 前置）

`RECOVERING` 态为任务八（Error Recovery）预留钩子：
- 进程启动检测未消费检查点 → 进 RECOVERING；
- 从检查点恢复 Goal/Task 进度（委托 `agent_runtime` 既有队列 + 任务八的持久化快照）；
- 恢复成功 → READY；恢复失败 → STOPPING。
本任务不实现恢复逻辑，仅定义状态与转移入口。

---

## 8. 红线合规

| 红线 | 合规性 | 说明 |
|------|--------|------|
| 单 Runtime | ✅ | 生命周期单例同进程，无第二 Runtime |
| 单 EventBus | ✅ | 复用 `publish_system("agent_state")` |
| 单 Permission | ✅（无关） | 生命周期不直接裁决，阻塞经既有 Permission 通道 |
| No God Module | ✅ | `lifecycle.py` 仅状态治理，不含路由/执行/持久化 |
| 增量演进 | ✅ | 新增模块 + 扩展既有信封字段，旧路径保留 |
| 事件契约 | ⚠️→✅ | 复用既有事件名规避 F1；新增须先修正契约文档 |

---

## 9. 后续动作

- 实现：`ai_core/lifecycle.py` + `server.main()` 接入（任务十细化 Boot 顺序）。
- 联调：与任务六（Health Check）自检、任务八（Recovery）RECOVERING 钩子对接。
- **本任务为设计交付；实际代码落地待 Phase A 实现阶段（经 Review 批准）。**

**STOP**：任务二设计完成。待 Review 批准后进入任务三（Context Pipeline）。未经批不得修改代码、不得扩大范围。
