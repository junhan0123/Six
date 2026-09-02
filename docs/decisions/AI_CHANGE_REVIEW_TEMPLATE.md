# AI Change Review Template

> AI 变更评审模板 | 区别于 `CHANGELOG_AI.md`（记录「发生了什么」），本模板记录**「为什么允许发生」**。
> 用法：每次重大修改必填一份，与 CHANGELOG 条目一一对应；存入 `docs/decisions/` 或在 CHANGELOG 中引用 Change ID。

## 字段定义

- **Change ID**: `CR-YYYYMMDD-NNN`（如 CR-20260804-001）
- **AI**: 执行 AI 的身份（如 Senior Developer / UI Designer）
- **Date**: `YYYY-MM-DD`
- **Task**: 任务来源（如 Phase 9 Step 2 / v1.2 治理）
- **Reason**: 为什么需要做此修改（业务/治理动机）
- **Affected Area**: 受影响的模块 / 文档 / 路径
- **Architecture Impact**: 对架构的影响，是否触及红线（见 DECISION_001..006）
- **Event Impact**: 事件契约变化（DOMAIN / SYSTEM 增删）
- **Memory Impact**: 记忆系统变化（是否触达 `memory.py`）
- **Policy Impact**: 权限 / 策略变化（是否触达 `PermissionGuard` / `PolicyEngine`）
- **Risk**: 风险等级（Low / Medium / High）与说明
- **Rollback Plan**: 回滚步骤（git revert / 文件恢复 / 配置还原）
- **Test Result**: 测试结果（如 `Phase 6/7/8 全量 0 FAIL / 0 Regression`）
- **Documentation Updated**: 已更新文档清单（CHANGELOG / Decision / Inventory / Status）
- **Approval**: 批准人 / 批准方式（用户明确批准 / Freeze Rule）

## 示例（v1.2 治理变更）

```
Change ID: CR-20260804-001
AI: Senior Developer（治理模式）
Date: 2026-08-04
Task: v1.2 治理 — 建立 Golden State 基线
Reason: 为长期维护提供可对比的正确状态锚点，防止架构漂移
Affected Area: docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md（新增）
Architecture Impact: 无（纯文档，未改代码/架构）
Event Impact: 无
Memory Impact: 无
Policy Impact: 无
Risk: Low
Rollback Plan: 删除新增文件（git rm / 移至 archive）
Test Result: 文档审计 0 问题（PROJECT_DOCUMENT_AUDIT.py）
Documentation Updated: CHANGELOG_AI.md / DEVELOPMENT_PROGRESS.md / DOCUMENT_INVENTORY.md
Approval: 用户授权 v1.2 治理任务
```

> 架构级决策同构于 `docs/decisions/DECISION_001..006.md`；日常小修改可仅在 CHANGELOG 注明 Reason，重大修改必须独立 Review。
