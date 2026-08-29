# 00 · 小6 AI OS 产品宪法 — 执行摘要（Executive Summary）

> 阶段：AI OS Product Constitution Phase v1.0
> 身份：Senior Product Architect + AI Operating System Chief Designer + Product Governance Lead
> 模式：Audit → Research → Design → Product Governance → Documentation → Verification → STOP
> 性质：**纯设计 / 纯产品治理 / 零代码改动**（严守纪律红线：Design Only / Documentation Only）
> 日期：2026-08-06
> 总治理入口：`docs/audits/AI_OPERATING_SYSTEM_GOVERNANCE.md`（L0–L6 单一入口）

---

## 一、本阶段做了什么

建立小6 AI OS 的**唯一产品真相（Single Source of Product Truth）**，冻结**产品层**。
此后 **UI / Overlay / Galaxy / Companion / Dock / Command Palette / Prompt / Capability / Memory / Knowledge** 全部**引用**本产品宪法，而非各自重述产品意图。

本阶段**不是开发、不是新功能、不是代码改动**。它把散落在以下位置的产品意图收口为一份权威宪法：

- `docs/ai-os/10_PRODUCT_POSITIONING.md`（架构系列的产品定位声明）
- `docs/design/frozen/PRODUCT_CONSTITUTION.md`（设计解释层 Design Canon，已冻结）
- `docs/design/frozen/DOMAIN_MODEL.md`（设计解释层 Domain Model）
- 各交互/体验设计文档（COMPANION_*、PHASE7/9 设计、UI Foundation 等）

并明确与底层技术真相的关系：

- **架构真相**：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`（L0）+ `ARCHITECTURE_MAP.md` + `docs/ai-os/01_AI_OS_ARCHITECTURE.md`
- **能力真相**：`docs/capability-platform/01_CAPABILITY_INVENTORY.md`（SSOT）+ v1.1 治理层
- **执行真相**：`docs/ai-os/execution-platform/`（Phase 3 统一执行内核）
- **知识真相**：`docs/ai-os/knowledge-engine/`（Knowledge Platform Sprint）
- **治理真相**：`docs/audits/AI_OPERATING_SYSTEM_GOVERNANCE.md` + `GOVERNANCE_AUTHORITY_HIERARCHY.md`

---

## 二、唯一产品真相的定位（权威关系，重要）

> **本文件集不创造第二权威。它创造的是"产品/体验层"的单一真相源，引用而非重定义任何技术真相。**

| 真相层 | 权威文档 | 与产品宪法关系 |
|---|---|---|
| **L0** Golden State | `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` | 最高权威。产品宪法任何表述与之冲突以 L0 为准。 |
| L1 Decision Records | `docs/decisions/DECISION_001..006` | 不可逆决策，产品宪法遵守。 |
| L2/L3/L4/L5 | 架构/知识/边界规范 | 产品宪法引用，不重定义。 |
| L6 实现参考 | `docs/audits/*`、`docs/capability-platform/*`、`docs/ai-os/*` | 产品宪法引用其事实（如"Electron 不存在""Planner/Workflow 仅蓝图"）。 |
| 设计解释层（非权威） | `docs/design/frozen/`（含旧 `PRODUCT_CONSTITUTION.md`） | **旧 `PRODUCT_CONSTITUTION.md` 设计 Canon 仍为冻结解释层，但此后应视为本产品宪法的"解释/索引"子文档**；本宪法是产品意图的权威源。 |
| **本产品宪法（新）** | `docs/product-constitution/00..11+99` | **产品/体验层单一真相源**。 |

**冲突裁决路径**：产品层争议 → 以本宪法为准；本宪法与架构/能力/执行/知识/治理争议 → 以各自真相源 + Golden State（L0）为准。

> ⚠️ **注册缺口（诚实声明）**：本产品宪法目前**尚未**正式登记进 `GOVERNANCE_AUTHORITY_HIERARCHY.md` 与 `AI_OPERATING_SYSTEM_GOVERNANCE.md`（二者为冻结治理文档，修改须经 `GOVERNANCE_CHANGE_CONTROL.md`）。本阶段仅创建产品层真相，不改动任何治理文档。建议 Review 批准后，由维护者通过变更控制流程将 `docs/product-constitution/` 登记为"产品治理层"。

---

## 三、交付物（13 份，详见 99_MASTER_INDEX）

`00_EXECUTIVE_SUMMARY` · `01_PRODUCT_VISION` · `02_PRODUCT_PHILOSOPHY` · `03_EXPERIENCE_PRINCIPLES` · `04_DAILY_USER_JOURNEY` · `05_CAPABILITY_EXPOSURE_RULES` · `06_INTERACTION_CONSTITUTION` · `07_INFORMATION_ARCHITECTURE` · `08_USER_MENTAL_MODEL` · `09_AI_BEHAVIOUR_CONSTITUTION` · `10_PRODUCT_ROADMAP` · `11_PRODUCT_GOVERNANCE` · `99_MASTER_INDEX`

---

## 四、红线复核（本阶段未违反任何一条）

- ✅ 未新增功能 / 未修改业务逻辑 / 未修改 Runtime / Planner / Goal / Workflow / Memory / Knowledge / Plugin / Permission / EventBus / Prompt / Agent / API / UI / CSS / JS / Python / 配置 / 任何代码。
- ✅ 未进入任何实现阶段（Overlay / Electron / Planner / Workflow 均未触碰）。
- ✅ 全阶段仅 Audit / Research / Design / Product Governance / Documentation / Verification。
- ✅ 未修改任何既有冻结/治理文档（Design Canon、Golden State、Governance 均保持原状）。
- ✅ 未提交 Git。

---

## 五、状态

🛑 **Product Constitution Phase v1.0 已完成、13 份文档齐备、Verify 通过（无第二权威、不违反任何底层真相）—— 统一 STOP，等待人工 Review。**

Review 批准后建议动作：
1. 通过 `GOVERNANCE_CHANGE_CONTROL.md` 将 `docs/product-constitution/` 登记为产品治理层。
2. 将 `docs/design/frozen/PRODUCT_CONSTITUTION.md` 标注为"指向本产品宪法的解释子文档"（经变更控制）。
3. 更新 `AI_BOOTSTRAP.md`，使任何 AI 进入即读产品宪法（同 Capability/Knowledge 现实认知规范）。
