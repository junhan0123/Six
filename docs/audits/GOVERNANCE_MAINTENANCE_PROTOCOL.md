# GOVERNANCE MAINTENANCE PROTOCOL

- **任务**：AI Operating System Governance Consolidation / Phase 8
- **日期**：2026-08-04
- **性质**：AI Maintainer 治理维护协议（执行者，非新权威）

## AI Maintainer 职责
- **读取**：仅经 `AI_OPERATING_SYSTEM_GOVERNANCE.md` 入口建立心智模型。
- **验证**：每次变更前运行 `docs/reference/PROJECT_DOCUMENT_AUDIT.py`，要求 **PROBLEMS=0**（WARNS 可记录，禁止自动修复治理基线外的东西）。
- **维护**：仅经 Change Control（`GOVERNANCE_CHANGE_CONTROL.md`）更新 Frozen 文档；**禁止直接改 Golden State**。
- **更新**：新增文档须登记 `docs/DOCUMENT_INVENTORY.md`，标注域 / 层级 / 状态 / 版本 / 日期。
- **审计**：周期性跑 `GOVERNANCE_INTEGRITY_AUDIT.md`（确认无第二治理 / 宪法 / 权威）。

## 操作清单（每次维护）
1. 读入口 → 2. 定位权威层级 → 3. 起草 Draft → 4. Review → 5. Approve → 6. Freeze → 7. 跑审计（PROBLEMS=0）→ 8. 更新索引。

## 验收（Onboarding）
- 新 AI Maintainer 须通过 `docs/reference/AI_ONBOARDING_TEST.md` 与 `GOVERNANCE_HANDOFF_SIMULATION.md` 验证：仅读入口即知阅读顺序 / 最高权威 / 禁止修改文档。

## 禁止（铁律）
- 禁止创建第二 Golden State / Constitution / Authority。
- 禁止复制规范内容（引用即可）。
- 禁止在 Frozen 文档上"就地修改"而不走 Change Control。
- 禁止将治理整合层（`GOVERNANCE_*.md`）误用为业务规范来源。

## Single Source Rule 遵守声明
本文件为协议文档；未定义业务规范，未复制规范内容。
