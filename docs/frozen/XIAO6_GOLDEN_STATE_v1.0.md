# Xiao6 Golden State v1.0

> 黄金基线（Golden State） | 保存当前 Xiao6 正确、冻结的状态。
> 用途：未来任何修改都必须与本基线逐项对比，检测「架构漂移（Drift）」。
> 生成依据：Phase 8 Final Gate PASS + v1.0 架构审查 PASS + v1.1/v1.2 文档治理完成。

## 项目标识

- **Project**: Xiao6
- **定位**: Local Personal AI Operating System（本地个人 AI 操作系统）
- **Version**: v1.0
- **基线生成日期**: 2026-08-04
- **冻结范围**: Phase 6 / 7 / 8（后续 Phase 9+ 模块可存在但未冻结，不计入基线）

## 冻结状态总览

| 维度 | 状态 | 说明 |
|------|------|------|
| Architecture | FROZEN | 模块层级冻结；无第二 Runtime / Memory / EventBus / Permission |
| Runtime | FROZEN | AgentRuntime 唯一决策运行时；Capture / Perception 仅观察生产者 |
| Event Contract | FROZEN | DOMAIN = 71 / SYSTEM = 8，前后端逐字一致 |
| Memory | FROZEN | `memory.py` 单一来源 |
| Policy | FROZEN | `PermissionGuard` + `PolicyEngine` 唯一权限 |
| State | FROZEN | `AppState` 唯一写入口；4 个只读投影层 |
| Tests | PASS | Phase 6/7/8 共 28 测试文件，全绿 |
| Documentation | COMPLETE | v1.1 + v1.2 治理完整 |

## 关键量化基线

- 领域事件 `DOMAIN_EVENT_NAMES` = **71**
- 系统事件 `SYSTEM_EVENT_NAMES` = **8**
- EventBus 内部 `TOPIC_*` = 5（`TOPIC_DOMAIN` / `TOPIC_SYSTEM` / `TOPIC_SSE` / `TOPIC_ALL` / `TOPIC_RAW`，以实际为准）
- Runtime 数量：决策运行时 **1**（AgentRuntime）+ 观察生产者 **2**（CaptureRuntime / PerceptionRuntime）
- State：权威核心 **1**（AppState，11 子树）+ 只读投影 **4**（GalaxyState / OverlayRuntime / ComputerState / PerceptionState）
- 测试：Phase 6 = 16 / Phase 7 = 8 / Phase 8 = 4 → 共 **28**，全部 PASS
- 仓库模块（xiao6-ui 顶层）：后端 `.py` **85** / 前端 `.js` **49**（冻结核心 = Phase 6/7/8；Phase 9+ 模块存在但未冻结）

## 不可逾越红线（与基线对比即知漂移）

- 禁止第二 Runtime / Memory / EventBus / Permission System
- 禁止绕过 AppState（状态变更必须经 `applyEvent → reducers`）
- 禁止绕过 EventBus（跨模块通信必须发领域事件）
- 禁止直接调用 Executor（必经 `PermissionGuard` 校验）
- 禁止修改 Galaxy 语义（银河本体视觉资产 100% 保留）
- 禁止 Vision 直接控制电脑（OBSERVATION ONLY，绝不产生 Action）

## 对比方法（每次重大修改后执行）

1. 跑 `docs/reference/PROJECT_DOCUMENT_AUDIT.py` → 文档一致性 0 问题。
2. 逐条核对 `docs/audits/ARCHITECTURE_DRIFT_CHECK.md` → 无 Runtime/Event/Memory/Policy/State 漂移。
3. 全量测试回归 → Phase 6/7/8 须 0 FAIL / 0 Regression。
4. 与本基线逐项对比，差异即 Drift，须回滚或走 Freeze Rule 重审。

> 本文件属于 `docs/frozen/`，为最高权威；任何冲突以本基线优先。
