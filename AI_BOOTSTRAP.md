# Xiao6 AI Bootstrap

> 固定入口。任何 AI（Workbuddy / Claude Code / Cursor / ChatGPT）打开本文件即可快速进入状态。
> 权威治理文档见 `docs/audits/AI_OPERATING_SYSTEM_GOVERNANCE.md`（L0–L6）；设计真相见 `xiao6-ui/DESIGN.md`。

---

## 项目身份

项目名称：
Xiao6（小6）

定位：
本地个人 AI 操作系统（Personal AI OS）

不是：
- 聊天机器人
- 普通工具箱

目标：
成为个人长期 AI 副驾。

---

## 当前版本

Version:
1.0.0

---

## 当前阶段

Current Sprint:

Capability Platform Phase v1.1（Governance Integration — 能力治理层建立）

状态：

Capability Platform Phase v1.0（纯审计/建档，14 份 SSOT 文档）已完成、STOP 等 Review。
现 v1.1 基于 v1.0 建立**能力治理层（Capability Governance Layer）**：4 份治理文档落 docs/capability-platform/v1.1/（01 注册表 Schema / 02 变更协议 / 03 AI 开发前核查 / 04 治理模型），并于本文件写入"能力现实认知规范"。纯治理、零代码改动；STOP 等待人工 Review。
此前 Phase 3 Execution Platform 实现已完成、STOP 等 Review。

---

## 已完成阶段

### Architecture

✅ 六层架构设计

### Agent Runtime

✅ Planner
✅ Executor
✅ Reflection
✅ Execution Guard

### Memory

✅ Context Engine
✅ User Memory
✅ Project Memory

### UI Foundation

✅ Design Token
✅ Motion System
✅ Icon System
✅ Focus System

### Release

✅ Portable Beta
✅ GA Preparation

### Execution Platform (Phase 3)

✅ 统一执行内核 ai_core/execution/（11 文件）
✅ Execution.run() 全项目唯一执行入口（Router，不重写 execute_tool）
✅ 5 处执行入口收口（tools.run_one / server 兜底 / agent_runtime / reflector / social_inbound）
✅ 统一 Context / Session / Queue / State / Event / Policy / Metrics / Recovery / Reflection
✅ 事件复用单 EventBus SYSTEM 通道（8 执行事件，零 UI 改动）
✅ 权限收口（ExecutionPolicy 100% 委托 PolicyEngine/PermissionGuard）

### Capability Platform (Phase)

✅ 全项目能力审计（19 分类 ~135 能力条目）
✅ 唯一能力真相 SSOT 建立（01 清单 + 08 能力书 + 02 分类 + 03 入口 + 04 生命周期）
✅ 重复审计（Toast 5+/Overlay 12+/天气/KWS/跨端/蒸馏/人格/JSON 抽取共 11 组）
✅ 死代码/孤儿审计（~12 死文件 + scheduler 孤儿 + perception_* 未接线 + 悬空开关）
✅ 能力关系图 + 用户/开发者指南 + 统计 + 终审
✅ 14 份文档落 docs/capability-platform/（00–12 + 99）
⚠ 关键纠正：Electron 外壳不存在（实为浏览器+http.server）；Planner/Workflow 仅为蓝图（代码无模块）

### Capability Platform Phase v1.1（Governance Integration）

✅ 能力治理层（Capability Governance Layer）建立（基于 v1.0 SSOT）
✅ 能力注册表 Schema 契约（v1.1/01_CAPABILITY_REGISTRY_SPEC）
✅ 能力变更协议 / 评审闸门（v1.1/02_CAPABILITY_CHANGE_PROTOCOL）
✅ AI 开发前能力核查协议 / 强制预检（v1.1/03_AGENT_CAPABILITY_CHECK_PROTOCOL）
✅ 能力治理模型 / L0–L6 衔接（v1.1/04_CAPABILITY_GOVERNANCE_MODEL）
✅ 本文件写入"能力现实认知规范"段（任何 AI 动手前强制约束）
⚠ 严守红线：纯治理、零代码改动（不碰 .py/.js/.css/.html/Runtime/Agent/UI/配置）

---

## 当前任务

已完成（本会话）：

Capability Platform Phase v1.1（Governance Integration，零代码改动）— 基于 v1.0 SSOT 建立能力治理层

成果：

- 阅读 v1.0 全 14 份文档（00–12 + 99）作为设计事实基础
- 4 份治理文档落 docs/capability-platform/v1.1/：
  - 01_CAPABILITY_REGISTRY_SPEC（能力注册表 Schema 契约：CapabilityRecord + Registry Container + 校验规则）
  - 02_CAPABILITY_CHANGE_PROTOCOL（能力变更协议：CCR 模板 + 8 阶段流程 + 生命周期迁移 + 升级矩阵）
  - 03_AGENT_CAPABILITY_CHECK_PROTOCOL（AI 开发前强制预检：Read Gate + G1–G8 闸门 + 预检报告）
  - 04_CAPABILITY_GOVERNANCE_MODEL（能力治理模型：L0–L6 定位 + 角色 + 治理闭环 + 纪律）
- 更新本文件：新增"能力现实认知规范"段（任何 AI 动手前强制约束：必读 SSOT + 跑 03 预检 + 变更走 02 CCR）
- 治理层定位：L6 实现参考治理子层，不创造第二权威；红线（单执行/事件/权限/状态/Runtime）来自 L0 不可破

前置已完成（本仓库）：

- Phase 3 Execution Platform（统一执行内核 ai_core/execution/，STOP 等 Review）
- Capability Platform Phase v1.0（14 份 SSOT 文档，STOP 等 Review）

禁止（本阶段纪律红线，全程未违反）：

修改业务代码 / 修改 Runtime / 修改 Agent 执行逻辑 / 修改 UI / 新增能力 / 删除代码 / 重构任何模块
任何功能实现 / 代码改动 / Rename / 顺手修 Bug / 进入实现（仅审计/设计/文档/Verify）

---

## 核心架构规则

1.
EventBus 是唯一通信层。

2.
Memory 单一来源。

3.
禁止 God File。

4.
Context 必须由 Context Engine 生成。

5.
升级必须兼容旧系统。

---

## AI 工作纪律

身份：

Senior Developer

执行模式：

Audit
→
Plan
→
Execute
→
Verify
→
Report

禁止：

- 自行扩大需求
- 顺手优化
- 修改架构

---

## 能力现实认知规范（Capability Reality Cognition）

> 任何 AI（WorkBuddy / Claude Code / Cursor / ChatGPT / Gemini）打开本仓库即受此约束。
> 目的：在动手前先认清小6"真正拥有什么能力"，避免重复造轮子、误建第二系统、踩已知坑。

### 能力真相来源（必读，且在动手前）

- **能力真相 SSOT**：`docs/capability-platform/01_CAPABILITY_INVENTORY.md`（全量能力字段表，唯一真值）
- 分类法（19 类）：`docs/capability-platform/02_CAPABILITY_CLASSIFICATION.md`
- 入口地图：`docs/capability-platform/03_ENTRY_MAP.md`
- 生命周期：`docs/capability-platform/04_CAPABILITY_LIFECYCLE.md`
- 重复清单（勿再复制）：`docs/capability-platform/05_DUPLICATE_REPORT.md`
- 死代码/孤儿（勿依赖/复活）：`docs/capability-platform/06_UNUSED_REPORT.md`
- 关系图 / 能力书 / 用户手册 / 开发者手册 / 统计 / 终审 / 索引：`docs/capability-platform/08..12` + `99`
- **治理层（v1.1）**：`docs/capability-platform/v1.1/01..04`

### 动手前强制预检（GO / NO-GO 闸门）

任何涉及"增 / 改 / 删 / 生命周期迁移 / Flag 变更"能力的任务，**必须先跑**
`docs/capability-platform/v1.1/03_AGENT_CAPABILITY_CHECK_PROTOCOL.md` 的八道闸门
（G1 存在性 / G2 单一来源红线 / G3 重复防治 / G4 死代码隔离 / G5 分类合法 / G6 入口合规 / G7 生命周期诚实 / G8 文档义务）。
**NO-GO 下禁止实现**；变更须走 `v1.1/02_CAPABILITY_CHANGE_PROTOCOL.md` 的 CCR 评审闸门（Document-First：先更 SSOT 后改代码）。

### 不可遗忘的现实事实（来自 v1.0 审计）

- **Electron 外壳不存在**：所有"桌面应用"实为浏览器渲染 + Python `http.server` 静态托管；无托盘/IPC/原生菜单，不得假设。
- **Planner / Workflow 仅为蓝图**：代码无独立模块，Goal 的"怎么做"由 `plan_goal`+`_llm_dispatch` 内联；不得对外宣称"具备"。
- **单一来源红线（来自 Golden State L0）**：唯一执行入口 `Execution.run`、唯一事件总线 `eventbus`、唯一权限 `PolicyEngine+PermissionGuard`、单一状态写源 `ExecutionState`；禁止第二套。
- **重复系统已存在**：Toast（5+）/ Overlay-Modal-Dialog（12+）权威为 `OverlayManager`；天气双源、KWS 三文件、JSON 抽取三份等（D1–D11）——勿再加。
- **死代码/孤儿**：`personalization.py`、`perception_*.py`、`scheduler.py`(孤儿)、各类 `.tmp`/`.bak.zzstep1`、悬空开关 `FEATURE_PERCEPTION`/幻影 `FEATURE_PROACTIVE_ENGINE`——勿依赖、勿复活、勿引用。
- **Feature Flag 声明≠运行时默认**：`config.py` 顶部多为 `False`，但 `reload()` 以 `os.environ.get("FEATURE_X","true")` 覆盖 → 绝大多数实际默认开启；判断以运行时为准。

---

## 当前下一步

Capability Platform Phase v1.1 已完成（能力治理层建立）：

进入：

人工 Review（批准 v1.1 四份治理文档 + AI_BOOTSTRAP 认知规范更新；一并批准 v1.0 SSOT 文档集作为全项目 SSOT、批准 Execution Platform 内核冻结）

随后（待 Review 批准，按治理层执行）：

任何能力变更须走 v1.1/02 变更协议（CCR 评审闸门，Document-First）；任何 AI 动手前须跑 v1.1/03 预检（GO/NO-GO）。
按 12_FINAL_REVIEW 建议推进 — UI 子系统收口(Toast/Overlay→OverlayManager) / Feature Flag 一致性 / 去重 / 死代码清理 / 感知真实化 / Planner-Workflow 落地决策（每项均先过 02/03）。

再后：

Overlay/OS Experience 实施 Sprint（此前已批准放行，待 GUI 验收）
