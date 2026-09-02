# GALAXY_INTERACTION_SPEC — Design Canon（设计解释层）

> 性质：**设计解释层**，**不属于 L0/L1 权威层**。不覆盖/替代 Golden State / Decision / Governance。本文件**不覆盖、不替代** Golden State / Decision / Governance；仅冻结规范 + 来源引用 + 权威映射（方案 1）。
> 创建：2026-08-04 · 方式：冻结规范 + 来源引用 + 权威映射（方案 1）

## Source Authority（权威来源）
- **L1 边界决策**：`docs/decisions/DECISION_004_GALAXY_BOUNDARY.md`（Galaxy = 表现层 + 受控交互层，不改银河本体）。
- **L0 红线**：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` §不可逾越红线-5「禁止修改 Galaxy 语义（银河本体视觉资产 100% 保留）」。
- **本体语义**：DECISION_004 原文隐喻——太阳=小6核心、轨道=Goal、星球=能力域、卫星=Agent、环=Memory、流星=主动推送。

## Related Documents（关联文档）
- `docs/decisions/DECISION_004_GALAXY_BOUNDARY.md`
- `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`
- `ARCHITECTURE_MAP.md`（Galaxy Three.js 行）
- `docs/design/frozen/INFORMATION_ARCHITECTURE.md`（兄弟文档）
- `docs/design/frozen/INTERACTION_SYSTEM_SPEC.md`（兄弟文档）

## Frozen Status（冻结状态）
- 本文件（解释层）：**FROZEN**。
- 引用权威：DECISION_004 FROZEN（L1）；银河本体视觉资产 100% 保留（L0 红线）。

## Scope（范围）
- 解释银河（太阳系可视化）的**交互边界**：哪些交互被允许、哪些被禁止。
- 把「展示层升为交互层」的受控方式冻结为可引用规范。

## Non-goals（非目标）
- **不创造新的银河语义或新隐喻**（用户约束 3）。
- 不把银河改为业务状态持有者（违反 DECISION_004）。
- 不动 `solar-system.js` 本体视觉资产（L0 红线）。

## Design Interpretation（设计解释）

### 1. 银河本体语义（冻结，来自 DECISION_004）
| 元素 | 含义 |
|---|---|
| 太阳 | 小6核心 |
| 轨道 | Goal |
| 星球 | 能力域 |
| 卫星 | Agent |
| 环 | Memory |
| 流星 | 主动推送 |

### 2. 允许的交互（受控交互层，来自 DECISION_004）
- 点击行星 → 展开能力面板（经 `galaxy-overlay` 叠加层）。
- 拖动轨道 → 调 Goal（经叠加层，不改本体）。
- 工具调用 → 光点沿轨道流转（可视化反馈）。

### 3. 禁止的交互/改造（红线）
- 银河**不得**直接修改 `AppState` 或持有可写状态。
- **不得**改动银河本体视觉资产（自转/公转/星空/点击聚焦），除非品牌重构专项。
- 任何 Galaxy 交互须经 `galaxy-overlay` 叠加层，不改动 `solar-system.js` 本体。
- Overlay Runtime 与 Galaxy 渲染解耦。

### 4. 权威映射
- 任何「银河能否做 X 交互」争议 → 以 `DECISION_004` + Golden State 红线-5 为准。
- 银河资产养护（自转/公转/星空）与 OS 重构互不冲突、可并行。
