# DOMAIN_MODEL — Design Canon（设计解释层）

> 性质：**设计解释层**，**不属于 L0/L1 权威层**。不覆盖/替代 Golden State / Decision / Governance。本文件**不覆盖、不替代** Golden State / Decision / Governance；仅冻结规范 + 来源引用 + 权威映射（方案 1）。
> 创建：2026-08-04 · 方式：冻结规范 + 来源引用 + 权威映射（方案 1）

## Source Authority（权威来源）
- **L0 量化基线**：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` §关键量化基线（Runtime/State/Event 数）。
- **架构地图**：`ARCHITECTURE_MAP.md`（模块职责 / 数据方向 / 红线速查）。
- **Galaxy 隐喻**：`docs/decisions/DECISION_004_GALAXY_BOUNDARY.md`（太阳/轨道/星球/卫星/环/流星）。
- **注意区分**：`docs/audits/GOVERNANCE_DOMAIN_MODEL.md` 是**治理领域（8 治理域）模型**，与本文件（产品/AI-OS 业务领域模型）不同层，不冲突。

## Related Documents（关联文档）
- `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`
- `ARCHITECTURE_MAP.md`
- `docs/decisions/DECISION_004_GALAXY_BOUNDARY.md`
- `docs/audits/GOVERNANCE_DOMAIN_MODEL.md`（治理域模型，区分参照）
- `docs/design/Xiao6-v2-架构升级设计文档.md` §3.3（目标-模块映射）

## Frozen Status（冻结状态）
- 本文件（解释层）：**FROZEN**。
- 引用权威：Golden State 量化基线 FROZEN（L0）；架构模块职责 FROZEN（L3 架构规范 + ARCHITECTURE_MAP）。

## Scope（范围）
- 解释小6**产品/AI-OS 业务领域模型**：核心实体（Goal/Orbit/Planet/Agent/Satellite/Memory Ring/Meteor）与后端领域（Runtime/State/Event/Policy）的映射。
- 提供「业务概念 ↔ 架构模块 ↔ 权威文件」的可追溯索引。

## Non-goals（非目标）
- **不创造新的领域实体或新架构方向**（用户约束 3）。
- 不重定义 AppState 子树 / EventBus 契约（权威在 Golden State + DECISION_001）。
- 不与治理域模型（`GOVERNANCE_DOMAIN_MODEL.md`）混淆——二者层级不同。

## Design Interpretation（设计解释）

### 1. 业务领域模型（Galaxy 隐喻，来自 DECISION_004）
| 概念 | 含义 | 后端对应 |
|---|---|---|
| 太阳 | 小6核心 | AgentRuntime（唯一决策） |
| 轨道 | Goal | Goal System |
| 星球 | 能力域 | Capability Registry 域 |
| 卫星 | Agent | 子 Agent / Skill |
| 环 | Memory | memory.py 单一来源 |
| 流星 | 主动推送 | proactive / SYSTEM 事件 |

### 2. 架构领域模型（来自 Golden State + ARCHITECTURE_MAP）
| 维度 | 冻结值 |
|---|---|
| Runtime | 决策运行时 1（AgentRuntime）+ 观察生产者 2（Capture/Perception） |
| State | 权威核心 1（AppState, 11 子树）+ 只读投影 4（Galaxy/Overlay/Computer/Perception） |
| Event | DOMAIN=71 / SYSTEM=8，前后端逐字对齐 |
| Policy | PolicyEngine + PermissionGuard 唯一权限 |
| Memory | memory.py 单一来源 |

### 3. 权威映射
- 领域模型争议 → 以 Golden State 量化基线 + ARCHITECTURE_MAP 模块职责为准。
- 业务概念（Galaxy 隐喻）仅作可视化映射，不承载状态权威（DECISION_004）。
