# Task F — GA 后路线图 | 小6 GA Gate Review

> **身份**：Chief Software Architect + Chief Release Engineer + QA Director + Project Governance Auditor
> **Sprint**：Xiao6 GA Gate Review Sprint v1.0
> **执行模式**：Audit → Verify → Decision → Report → STOP
> **日期**：2026-08-05
> **性质**：仅规划，不开发；若 GA 裁定允许，本文为 GA 后迭代的路线参考。

---

## 0. 定位

本路线图在 **GA 允许进入** 的假设下，规划 GA 之后的演进。分三阶段：**UI/UX Polish（打磨）→ 体验优化（粘性）→ 新功能规划（增长）**。所有条目仅规划，不在本 Sprint 执行，且须遵守既有治理纪律（无第二 Runtime/EventBus/Memory/Permission；AppState 唯一写入口；PolicyEngine 唯一权限）。

> 本文件为「规划文档」，不替代 PM Agent 的迭代排期；实际执行须新开开发 Sprint 并由人工 Review。

---

## 阶段一：UI/UX Polish（GA 后第一优先，约 1–2 个迭代）

目标：闭合 `RELEASE_CHECKLIST §1.3/§1.8` 与 `UI_CONSISTENCY_REPORT.md` 的一致性缺口，使产品从「Beta 级可用」升至「GA 级精致」。

| # | 条目 | 来源 | 说明 |
|---|---|---|---|
| U-1 | 图标风格全局统一 | UI_CONSISTENCY U1 | 主界面/设置/托盘图标统一为 `.ic` 体系；消除混用 |
| U-2 | Focus 环统一 | UI_CONSISTENCY U6 / RELEASE_CHECKLIST §1.8 | 全站 `:focus-visible` 工具类 + `--focus-ring` 令牌，WCAG AA |
| U-3 | 动效令牌路由 | UI_CONSISTENCY U7 / MOTION_SYSTEM | 150+ 硬编码 transition 路由至 `--motion-*`/`--ease-*`；消突兀时长 |
| U-4 | 设置 9 分类重组 | PRODUCT_READINESS / NEXT_RC §2.1 | 13 Tab 归 9 分类，降低用户找功能成本 |
| U-5 | 记忆/人格恢复兜底文案 | RELEASE_CHECKLIST §1.5 | 恢复失败时用户可见提示，而非静默 |
| U-6 | 卸载-重装真机冒烟 | CLEAN_ENVIRONMENT_REPORT 建议 | 在真机完成最终卸载-重装端到端验证 |

---

## 阶段二：体验优化（粘性增强，约 2–3 个迭代）

目标：在架构纪律内提升日常使用质感与可靠性。

| # | 条目 | 说明 |
|---|---|---|
| E-1 | 后端崩溃恢复压测闭环 | ≥3 次 `kill -9` 自动恢复压测纳入发布门禁（当前 🟡） |
| E-2 | 性能实测与基线 | 首屏（Companion 显）≤1.5s、主界面打开 ≤800ms、动效 60fps 量化并固化基线 |
| E-3 | 代码签名接入 | 获取 OV/EV 证书或 Azure Trusted Signing，消除 SmartScreen 拦截（见 `SIGNING_PREPARATION_REPORT.md`） |
| E-4 | 发布校验和与下载页指引 | 提供 `小6-1.4.0-x64.exe` / `小6-Setup-1.4.0-x64.exe` SHA-256 + 未签名提示 |
| E-5 | 自动更新通道（可选） | 评估内置更新（electron-updater）或文档化手动升级流程 |
| E-6 | 矢量 Logo 补充 | `assets/logo.svg` 用于关于框/文档（当前仅内联 SVG） |
| E-7 | 弱默认令牌轮换 | `SOCIAL_INBOUND_TOKEN` 改为随机生成或强默认（P-10） |

---

## 阶段三：新功能规划（增长探索，需新 Sprint + 架构评审）

目标：在 Golden State 纪律边界内探索能力增长。仅列出方向，不进入实现。

| # | 方向 | 约束提醒 |
|---|---|---|
| N-1 | 记忆图谱可视化 | 复用 `memory.py` 单一来源；禁止第二 Memory |
| N-2 | 多模态/图像生成接入 | 经既有 Tool API；不新增第二 Runtime |
| N-3 | 主动智能情境扩展 | ProactiveEngine 仅决策；所有执行经 `submit_goal`+Policy Guard |
| N-4 | 跨设备/云同步（远期） | 须走 GOVERNANCE_CHANGE_CONTROL 重审数据边界 |
| N-5 | Phase 12 对话记忆沉淀 | `context/models.py:ConversationMemory` 已预留数据结构，落地时仍经 `memory.py` |

> 所有新功能须先经 DECISION 流程与 Golden State 冲突校验，禁止引入第二 Runtime/EventBus/Memory/Permission。

---

## 纪律提醒

- 任何新 Phase / 新能力不得违反 Golden State 红线（无第二 Runtime/EventBus/Memory/Permission）。
- 改动须走 `GOVERNANCE_CHANGE_CONTROL.md`；设计意图以 Design Canon（解释层）落盘，不覆盖 Golden State。
- 发布门禁（`RELEASE_CHECKLIST`）须每版复核。

---

**Task F 状态：✅ 完成（规划文档，不开发）。**
