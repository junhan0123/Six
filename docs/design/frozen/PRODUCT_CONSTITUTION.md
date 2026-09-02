# PRODUCT_CONSTITUTION — Design Canon（设计解释层）

> 性质：**设计解释层（Design Interpretation Layer）**，**不属于 L0/L1 权威层**。
> 本文件**不覆盖、不替代** Golden State / Decision / Governance；仅冻结对既有产品定位的解释与权威映射。
> 创建：2026-08-04 · 方式：冻结规范 + 来源引用 + 权威映射（方案 1）

## Source Authority（权威来源）
- **最高权威**：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`（L0）§项目标识 ——「Local Personal AI Operating System（本地个人 AI 操作系统）」。
- **产品演进意图**：`docs/design/Xiao6-v2-智能贾维斯-演进路线.md`（JARVIS 成熟度模型 L0→L5，现存设计语料，非冻结规范）。
- **治理入口**：`docs/audits/AI_OPERATING_SYSTEM_GOVERNANCE.md` §0 三句话。

## Related Documents（关联文档）
- `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`
- `docs/design/Xiao6-v2-架构升级设计文档.md`（v2 升级草案，待评审，非冻结）
- `docs/design/Xiao6-v2-智能贾维斯-演进路线.md`
- `docs/audits/GOVERNANCE_AUTHORITY_HIERARCHY.md`

## Frozen Status（冻结状态）
- 本文件（解释层）：**FROZEN**（落盘即冻结；仅经主理人确认 + `GOVERNANCE_CHANGE_CONTROL.md` 可改）。
- 引用权威冻结态：Golden State FROZEN（L0）；JARVIS 演进路线为**设计意图（未冻结）**，仅作背景参考，不具规范效力。

## Scope（范围）
- 解释「小6是什么、为谁、边界在哪」——基于 Golden State 已冻结定位的词义澄清与权威映射。
- 提供「产品理念 → 权威文件」的可追溯索引。

## Non-goals（非目标）
- **不创造新的产品理念或新方向**（用户约束 3）。
- 不重定义 Golden State 的「定位 / 版本 / 冻结范围」。
- 不把 JARVIS 演进路线提升为冻结规范（它仍是设计意图）。

## Design Interpretation（设计解释）

### 1. 已冻结的产品身份（来自 L0，不可改）
| 维度 | 冻结值（Golden State §项目标识） |
|---|---|
| Project | Xiao6 |
| 定位 | Local Personal AI Operating System（本地个人 AI 操作系统） |
| Version | v1.0 |
| 冻结范围 | Phase 6 / 7 / 8（Phase 9+ 存在但未冻结，不计入基线） |

### 2. 设计意图中的演进方向（来自 JARVIS 路线，未冻结，仅参考）
- 目标五维跃迁：被动对话 → 主动常驻 → 多模态 → 执行者 → 懂你（人格一致）。
- 成熟度 L0（命令行/网页）→ L1（个人副驾，≈当前）→ L2（常驻语音）→ L3（环境感知）→ L4（自主执行）→ L5（智能贾维斯）。
- 该路线**不改变** Golden State 的「本地优先个人 AI OS」定位，只是能力成熟度描述。

### 3. 权威映射（冲突裁决路径）
- 任何「产品定位」争议 → 以 `XIAO6_GOLDEN_STATE_v1.0.md` 为准。
- 任何「是否引入新能力方向」→ 先对照 Golden State 红线 + `docs/decisions/`；超出红线须走 Decision 流程。

> 本文件是解释层；若未来出现与 Golden State 不一致的「产品理念」表述，一律以 Golden State 优先，本文件须回退修订。
