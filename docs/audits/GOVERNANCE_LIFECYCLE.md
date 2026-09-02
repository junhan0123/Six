# GOVERNANCE LIFECYCLE

- **任务**：AI Operating System Governance Consolidation / Phase 6
- **日期**：2026-08-04
- **纪律**：Governance Single Source Rule（描述状态机，禁重定义规范）

## 状态机
```
Draft ──提交──▶ Review ──批准──▶ Approved ──冻结──▶ Frozen
                                                       │
                                          ┌────────────┴────────────┐
                                     Superseded              (Change Control)
                                                          │            │
                                                          ▼            ▼
                                                  Frozen'(新版本)   Rollback→上一 Frozen
                                                       │
                                                  Archived（不再适用）
```

## 状态定义
- **Draft（草稿）**：撰写中，未评审。可被任意修改。
- **Review（评审中）**：已提交评审，等待 AI Maintainer / Decision 批准。冻结期内禁止修改原文。
- **Approved（已批准）**：评审通过，待正式冻结。
- **Frozen（已冻结）**：不可变，是引用基准。任何修改必须经 Change Control（Phase 7）。治理文档的默认稳定态。
- **Superseded（已替代）**：被新版本 / 新决策替代。保留以追溯，标注替代者。
- **Archived（已归档）**：不再适用，移入 `docs/archive/`。保留历史。

## 转换规则
- Draft → Review：作者提交。
- Review → Approved：维护者 / 决策者批准。
- Approved → Frozen：正式冻结，登记 `DOCUMENT_INVENTORY`，标注版本与日期。
- Frozen → Superseded：新文档 Frozen 且声明替代本文件。
- Frozen →（Change Control）→ Frozen'：经 Phase 7 流程的修订后重新冻结，旧版转 Superseded。
- Any → Archived：确认不再适用。

## Frozen 纪律（铁律）
- **Frozen 文档是引用基准。** 下游文档必须引用 Frozen 版本，不得引用 Draft / Review。
- **修订 = 新 Frozen 版本 + 旧版 Superseded**，不得"就地改 Frozen 原文"。
- 本 Consolidation 全部 `GOVERNANCE_*.md` 在终报后进入 **Frozen**。

## Single Source Rule 遵守声明
本文件描述生命周期状态机；未定义任何业务规范，未复制规范内容。
