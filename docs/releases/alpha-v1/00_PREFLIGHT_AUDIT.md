# 00 · AI OS Alpha Stabilization — Phase 0 Preflight Audit（红线锚定）

> 专项：AI OS Alpha Stabilization Program v1.0
> 身份：Senior QA Architect + Senior Product Architect + Senior UX Engineer + AI OS Release Manager
> 阶段：Phase 0 Preflight Audit（重读冻结/权威文档，锚定红线）
> 日期：2026-08-06
> 纪律：纯审计/锚定；零代码改动；不新增任何能力。

---

## 0. 目的

进入 Alpha Stabilization 之前，先真实重读所有冻结/权威文档，把"不可逾越的红线"逐条列清，作为 P1–P10 全过程的对照基线。任何后续动作若触碰以下任一条，即视为架构漂移（Drift），须回滚。

---

## 1. 已重读的权威文档（9 类，全部真实落盘确认）

| # | 类别 | 文档 | 结论 |
|---|------|------|------|
| 1 | Golden State（L0 最高） | `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` | ✅ 已读 |
| 2 | 治理入口（Constitution） | `docs/audits/AI_OPERATING_SYSTEM_GOVERNANCE.md` | ✅ 已读 |
| 3 | 架构真相 | Golden State + `EXECUTION 15_EXECUTION_SUMMARY` + `KNOWLEDGE_PLATFORM_SUMMARY`（架构以 L0 为准） | ✅ 已读 |
| 4 | Execution Platform | `docs/ai-os/execution-platform/15_EXECUTION_SUMMARY.md` | ✅ 已读 |
| 5 | Knowledge Platform | `docs/ai-os/knowledge-engine/KNOWLEDGE_PLATFORM_SUMMARY.md` | ✅ 已读 |
| 6 | Capability Platform | `docs/capability-platform/00_EXECUTIVE_SUMMARY.md` | ✅ 已读 |
| 7 | Product Constitution | `docs/product-constitution/00,03,04,05,06` | ✅ 已读 |
| 8 | Unified Workspace | `docs/sprints/ai-os-workspace-v2/99_FINAL_REPORT.md` | ✅ 已读 |
| 9 | AI Bootstrap | `G:/xiao6/AI_BOOTSTRAP.md` | ✅ 已读 |

> 工具说明：Glob 不遍历 `/g/` 挂载盘，已用 `Bash ls/find` 真实确认全部文档存在（非 summary 臆测）。

---

## 2. 不可逾越红线（来自 L0 Golden State + Governance）

### 2.1 架构红线（单点真相，禁止第二套）
- 禁止第二 **Runtime**（决策运行时仅 `AgentRuntime`；观察生产者 `CaptureRuntime`/`PerceptionRuntime` 仅观察）。
- 禁止第二 **Memory**（单一来源 `memory.py`）。
- 禁止第二 **EventBus**（跨模块通信必须经 `eventbus`；DOMAIN=71 / SYSTEM=8 逐字一致）。
- 禁止第二 **Permission**（唯一 `PolicyEngine` + `PermissionGuard`）。
- 禁止第二 **State 写入口**（状态变更必须经 `applyEvent → reducers`；`AppState` 唯一写源）。
- 禁止 **God Module**（无巨文件、无上帝对象）。
- 禁止绕过 `Execution.run()` 直接调 `Executor`（必经 `PermissionGuard`）。
- 禁止修改 Galaxy 语义（银河本体视觉资产 100% 保留）。
- 禁止 Vision 直接控制电脑（OBSERVATION ONLY，绝不产生 Action）。

### 2.2 纪律红线（Alpha Stabilization 最高禁止）
- **禁止新增任何业务能力 / Tool / API / Runtime / Agent / Planner / Workflow / Memory 类型 / Knowledge 类型 / Capability / Prompt 行为**。
- **禁止修改** Golden State / Constitution / Architecture / Capability Platform / Product Constitution / Permission / EventBus / 数据库 Schema / 冻结治理文档。
- **禁止进入** Electron / Mobile / Voice / Perception（含真实感知接线）/ Automation / 任何新能力开发。
- 不得为通过验证而新增功能（禁止"为达标而造功能"）。
- 禁止提交 Git（本专项各 Phase 均 STOP 等 Review，与前置 Sprint 一致）。

### 2.3 现实事实（来自 Capability Platform 审计，动手前必知）
- **Electron 外壳不存在**：实为浏览器 + `python -m http.server` 静态托管；无托盘/IPC/原生菜单。
- **Planner / Workflow 仅为蓝图**：代码无独立模块，不得对外宣称"具备"。
- **单执行/事件/权限/状态红线来自 L0 不可破**。
- **重复系统已存在**：Toast（5+）/ Overlay-Modal-Dialog（12+）权威为 `OverlayManager`；天气双源、KWS 三文件、JSON 抽取三份——勿再加。
- **死代码/孤儿**：`personalization.py`、`perception_*.py`、`scheduler.py`(孤儿) 、`.tmp`/`.bak.zzstep1`、悬空开关 `FEATURE_PERCEPTION`/幻影 `FEATURE_PROACTIVE_ENGINE`——勿依赖/复活/引用。
- **Feature Flag 声明≠运行时默认**：`config.py` 顶部多为 `False`，但 `reload()` 以 `os.environ.get("FEATURE_X","true")` 覆盖 → 绝大多数实际默认开启；判断以运行时为准。
- **知识层已冻结**（Knowledge Platform v1.0）：无 RAG/向量库/第二 Runtime；新增知识只写 markdown（Obsidian 或 `knowledge.ingest_document`）。

---

## 3. 允许范围（仅稳定性 / 体验修复）

可在 **UI 层** 做下列修复，且不得触碰 2.1/2.2 任何红线：
- Bug 修复、体验修复、一致性修复。
- 状态恢复 / Workspace / Overlay / Keyboard / Focus / Companion / Panel / Command Palette 修复。
- Loading / Empty State / Skeleton / Animation / Performance（仅 UI 层）修复。
- 文档更新、测试补充（纯测试文件 / 验收脚本）。

> 任一修复若"顺手"扩张了能力、新增了入口、改了行为语义，即越界，须停止。

---

## 4. Release Gate（9 条件，全部满足方可宣布 Alpha Ready）

| # | 条件 | Phase 0 锚定状态 |
|---|------|------------------|
| 1 | Architecture 未违反 | 🔒 基线干净（单 Runtime/状态/EventBus/Permission） |
| 2 | Capability 未违反 | 🔒 仅引用 SSOT，不暴露 missing/dead |
| 3 | Workspace 未回退 | 🔒 v2.0 收口完成，10 Verify PASS |
| 4 | Companion 未扩张 | 🔒 仅转发（Companion 职责矩阵） |
| 5 | Golden State 未违反 | 🔒 L0 红线已锚定 |
| 6 | Product Constitution 未违反 | 🔒 六态/暴露级别/交互宪法已读 |
| 7 | Daily Workflow 可连续完成 | ⏳ P2 验证 |
| 8 | User Journey 无 P0 | ⏳ P1 验证 |
| 9 | Regression 全 PASS | ⏳ P7 验证 |

---

## 5. Phase 0 结论

✅ **Preflight Audit PASS**。红线已逐条锚定，9 类权威文档全部真实重读。

- 后续 P1–P10 的每一次修改，都须回对本文件 §2 红线逐项核对。
- 当前代码基线（git working tree）已快照：`panel-manager.js` `node --check` PASS；不动任何冻结文档、不提交。
- 已知 working tree 含大量未提交历史改动（多 Phase 累积），属前置 Sprint 的 STOP 态，本专项**不代为提交、不回滚、不整理**，仅在其上做允许的 UI/状态修复。

**进入 Phase 1：End-to-End User Journey Audit。**
