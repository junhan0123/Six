# EXPERIENTIAL_PROTOTYPE_SPEC — Design Canon（设计解释层）

> 性质：**设计解释层**，**不属于 L0/L1 权威层**。不覆盖/替代 Golden State / Decision / Governance。本文件**不覆盖、不替代** Golden State / Decision / Governance；仅冻结规范 + 来源引用 + 权威映射（方案 1）。
> 创建：2026-08-04 · 方式：冻结规范 + 来源引用 + 权威映射（方案 1）

## Source Authority（权威来源）
- **体验演进意图**：`docs/design/Xiao6-v2-智能贾维斯-演进路线.md`（JARVIS 成熟度 L0→L5 + 阶段路线图）。
- **分阶段设计语料**：`docs/design/Xiao6-v2-P1-设计方案.md`（用户模型/情节记忆体验）、`Xiao6-v2-Phase2-设计方案.md`（EventBus/世界模型体验）、`Xiao6-v2-架构升级设计文档.md` §10 功能保全清单（34 项体验）。
- **L0 定位**：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`（本地个人 AI OS）。

## Related Documents（关联文档）
- `docs/design/Xiao6-v2-智能贾维斯-演进路线.md`
- `docs/design/Xiao6-v2-P1-设计方案.md` / `Xiao6-v2-Phase2-设计方案.md`
- `docs/design/frozen/PRODUCT_CONSTITUTION.md`（兄弟文档）
- `docs/design/frozen/INTERACTION_SYSTEM_SPEC.md`（兄弟文档）

## Frozen Status（冻结状态）
- 本文件（解释层）：**FROZEN（解释层）**。
- 引用权威：JARVIS 路线为**设计意图（未冻结）**；34 项功能为已实现能力（v2 §10）。

## Scope（范围）
- 解释小6「体验原型」的演进路线与分阶段体验目标（从副驾到贾维斯）。
- 把分散的体验设计收敛为可引用的解释索引。

## Non-goals（非目标）
- **不创造新的体验方向或新功能清单**（用户约束 3）。
- 不把 JARVIS 路线提升为冻结规范（仍是设计意图）。
- 不重定义 34 项功能（权威在 v2 §10 功能保全清单）。

## Design Interpretation（设计解释）

### 1. 体验成熟度模型（来自 JARVIS 路线，未冻结，仅参考）
| 等级 | 体验目标 | 归属阶段 |
|---|---|---|
| L0 | 命令行/网页聊天（已越过） | — |
| L1 | 个人副驾：记忆+主动提醒+多端同步+RAG（≈当前） | Phase 1–6 |
| L2 | 常驻语音副驾：唤醒词+语音优先+可打断 | Phase 8 |
| L3 | 环境感知副驾：日历/应用/屏幕上下文 | Phase 9 |
| L4 | 自主执行副驾：长任务循环+自我修正 | Phase 10 |
| L5 | 智能贾维斯：全息 HUD+跨端无感+人格一致 | Phase 11–13 |

### 2. 体验原则（归纳自路线 + 实现）
- **零密钥优先 / 隐私优先**：感知能力默认关、强开关、可审计（JARVIS §五）。
- **常驻 ambient**：后台运行、主动感知时机（JARVIS §一）。
- **多模态**：语音+视觉+文本并存（JARVIS §一）。
- **体验保全**：升级不遗漏 34 项现有功能（v2 §10）。

### 3. 权威映射
- 体验方向争议 → 以 Golden State「本地个人 AI OS」定位为边界；具体阶段目标以 JARVIS 路线为参考（未冻结，可经主理人调整）。
