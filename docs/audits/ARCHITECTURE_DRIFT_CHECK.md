# Architecture Drift Check

> 架构漂移检测清单 | 防止长期维护过程中破坏已冻结架构。
> 用法：每次重大修改后逐项核对；任一项命中即视为 **DRIFT**，必须回滚或走 Freeze Rule 重新审批。
> 基线参照：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`

## Runtime Drift（运行时漂移）

检测目标：是否出现第二决策/执行回路。

- [ ] 是否存在 **第二 Runtime 类**（独立事件循环 / 决策循环，绕过 AgentRuntime）
- [ ] 是否存在 **第二 Agent Loop**（不经过 AgentRuntime 的决策流）
- [ ] 是否存在 **第二执行入口**（绕过 Executor 的直接动作触发）

检测方法：

- `Grep "class .*Runtime"` 确认仅 `AgentRuntime`（决策）+ `CaptureRuntime` / `PerceptionRuntime`（生产者，非决策）。
- 确认无新模块自带 `while True` / `asyncio` 永久循环充当决策。

## Event Drift（事件漂移）

检测目标：是否绕过 EventBus 单一通信。

- [ ] 是否 **绕过 EventBus**（模块间直接 import 调用而非发事件）
- [ ] 是否 **模块直接通信**（未经 EventBus 领域事件传递）
- [ ] 是否 **新增未登记 Event**（未同步 `eventbus.py` + `zz-events.js`）

检测方法：

- `Grep` 跨层直接 import（如 `perception_runtime.py` import `permission_guard` / `computer_executor` → 命中即漂移）。
- 确认所有 `publish_domain(name, ...)` 的 `name` ∈ `DOMAIN_EVENT_NAMES`（否则抛 ValueError，属绕过安全网）。
- 确认前端 `zz-events.js` 的 `EVENTS` 与后端逐字一致。

## Memory Drift（记忆漂移）

检测目标：是否出现第二记忆来源。

- [ ] 是否存在 **第二 Memory Source**（第二套持久化记忆系统）
- [ ] 是否 **绕过 Memory System**（直接写文件而非 `memory.py`）
- [ ] 是否 **数据来源不一致**（多处维护同一记忆副本）

检测方法：

- 确认记忆读写唯一入口为 `memory.py`。
- `Grep` 直接 `open(...).write` 记忆类 JSON → 命中即漂移。

## Policy Drift（权限漂移）

检测目标：权限逻辑是否分散。

- [ ] 是否 **权限逻辑分散**（多处自行判断能否执行）
- [ ] 是否 **绕过 Permission Policy**（高风险动作未经验证直接执行）

检测方法：

- 高风险动作均经 `PermissionGuard` 校验。
- 风险等级映射 `PolicyEngine.RISK_TIER`，无游离的 `if risk ...` 自行放行。

## State Drift（状态漂移）

检测目标：是否绕过 AppState 唯一写入口。

- [ ] 是否 **绕过 AppState**（直接修改前端状态核心对象）
- [ ] 是否 **私有状态系统**（新建状态权威而非投影）

检测方法：

- 新增状态视图须为订阅投影（`AppState.subscribe(...)`），**不**调用 `applyEvent` 写状态。
- 确认无新模块自建 `state = {...}` 并对外暴露为权威。

## Drift 处置流程

```
命中任一漂移项
  ↓
立即中断修改
  ↓
记录 AI_CHANGE_REVIEW（docs/decisions/AI_CHANGE_REVIEW_TEMPLATE.md）
  ↓
回滚 或 走 Freeze Rule 重新审批（Decision → Design → Approval → ...）
  ↓
复测 + 复审计 → 0 问题方可继续
```

> 关联：黄金基线 `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`；文档审计 `docs/reference/PROJECT_DOCUMENT_AUDIT.py`。
