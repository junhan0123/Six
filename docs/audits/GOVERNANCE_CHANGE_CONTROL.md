# GOVERNANCE CHANGE CONTROL

- **任务**：AI Operating System Governance Consolidation / Phase 7
- **日期**：2026-08-04
- **纪律**：Governance Single Source Rule（定义流程，禁重定义规范）

## 统一变更流程（Change Review → Approval → Freeze → Rollback）

### 1. Propose（提议）
- 在 `docs/` 提 **Draft**（不改动 Frozen 原文）。
- 使用 `docs/decisions/AI_CHANGE_REVIEW_TEMPLATE.md` 记录变更理由、影响域、权威层级。

### 2. Review（评审）
- 由 AI Maintainer / 对应 Decision 评审。
- 冻结期内（Review/Approved/Frozen）**禁止修改 Frozen 原文**。

### 3. Approve（批准，依权威层级）
- **L1–L6 变更**：可由 AI Maintainer 批准。
- **L0（Golden State）变更**：须显式声明，并经最高权威冲突校验——**Golden State 不可被任何下游文档推翻**（若变更意图弱化红线，须拒绝）。
- 涉及多域：更新 `GOVERNANCE_DOMAIN_MODEL` / `GOVERNANCE_AUTHORITY_HIERARCHY`（同样走本流程）。

### 4. Freeze（冻结）
- 批准后新版本 **Frozen**，旧版 **Superseded**。
- 更新 `docs/DOCUMENT_INVENTORY.md`（登记路径、域、层级、状态、版本、日期）。
- 更新 `AI_OPERATING_SYSTEM_GOVERNANCE.md` 阅读顺序（如必要）。

### 5. Rollback（回退）
- 若新版本引入回归，可回退至上一 **Frozen** 版本。
- 保留版本号与历史，不删除旧版（旧版转 Archived 或保留 Superseded）。

## 纪律（铁律）
- **禁止"边改边推翻"**：评审期禁止修改 Frozen 原文。
- **禁止绕过冻结**：任何实现不得引用未 Frozen 的规范。
- **Golden State 红线不可经变更流程弱化**（无第二 Runtime / Memory / EventBus / Permission；Vision 绝不控制；PolicyEngine 唯一权限；AppState 唯一写入口）。
- 每次变更记录于对应 CHANGELOG / 审计文件。

## Single Source Rule 遵守声明
本文件定义变更流程；未重定义任何规范内容，未创造新权威。
