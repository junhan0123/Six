# 小6 AI OS 2.0 — Architecture Master Index

> 本文档是 `docs/ai-os/` 系列的总导航。所有 15 份架构文档 + 本索引 + Executive Summary 均已落盘。
> 阅读顺序建议：先看 `00_EXECUTIVE_SUMMARY.md` → `01_AI_OS_ARCHITECTURE.md` → 按兴趣/职责深入 `02`–`15` → 回到 `15_AI_OS_MASTER_PLAN.md` 收束。

---

## 1. 文档目录（Document Catalog）

| # | 文件 | 标题 | 一句话 | 关键章节 |
|---|------|------|--------|---------|
| 00 | `00_EXECUTIVE_SUMMARY.md` | Executive Summary | 高管摘要：结论 / 交付物 / ADR / Moat / 路线图 / 合规 | 8 节：结论·背景·交付物·ADR·分层·Moat·路线图·合规 |
| 01 | `01_AI_OS_ARCHITECTURE.md` | 总体架构 | 总纲，定义分层模型与冻结红线，约束其余 14 份 | 定位重申 · 冻结红线 · 分层 L0–L9 · P11–P15 · 数据流 |
| 02 | `02_MEMORY_ENGINE.md` | Memory Engine | 10 层 UMA 记忆引擎，单一逻辑源 `memory.py` | 十层 UMA · 单源 · 事件接口 · 生命周期 · 检索语义 · 治理 |
| 03 | `03_KNOWLEDGE_ENGINE.md` | Knowledge Engine | Obsidian 知识层，文件即真相，机器索引为派生 | 三件套 · Vault 约定 · Sync Bridge · RAG+Embedding · 边界 |
| 04 | `04_GOAL_ENGINE.md` | Goal Engine | 目标状态机 + 优先级 + Goal Tree + 崩溃恢复 | 状态机 · 优先级 Policy · Goal Tree · 队列 · 依赖 · 恢复 |
| 05 | `05_WORKFLOW_ENGINE.md` | Workflow Engine | Goal 的执行蓝图 = DAG-of-steps + Checkpoint + HITL | DAG · Step 状态机 · HITL · 检查点恢复 · 单执行通道 |
| 06 | `06_AGENT_ENGINE.md` | Agent Engine | Supervisor 编排 + Specialist 角色切换（非进程） | Supervisor+Specialist · 角色清单 · 交接 · 单执行通道 · 反思 |
| 07 | `07_PROACTIVE_AI.md` | Proactive AI | 薄决策层：IGNORE/SUGGEST/NOTIFY/CREATE_GOAL | 薄层 · 触发器 · 只读评估 · 打扰预算 · 可撤销审计 |
| 08 | `08_PLUGIN_SYSTEM.md` | Plugin / Extension | 统一 Extension 抽象收敛 MCP/Tool/Connector/Plugin | 统一抽象 · Registry · Policy 门控 · MCP 适配器 · 生命周期 |
| 09 | `09_LOCAL_FIRST.md` | Local First Infra | 本地优先五大支柱：驻留/离线/无硬云依赖/可选同步/隐私 | 五大支柱 · 数据驻留 · 离线降级 · 可选同步 · 隐私架构 |
| 10 | `10_PRODUCT_POSITIONING.md` | Product Positioning | 产品定位 + OS 隐喻映射 | 一句话定位 · 目标用户 · 价值主张 · Not-What · OS 隐喻 |
| 11 | `11_COMPETITIVE_ANALYSIS.md` | Competitive Analysis | 对标 10 类竞品，定义护城河与绝不抄袭项 | 差异化矩阵 · Moat · 世界级项 · 不抄袭项 · 结论 |
| 12 | `12_IMPLEMENTATION_ROADMAP.md` | Roadmap | 12 个月 4 阶段 + Never-Do + 关键路径 | 顺序约束 · 4 阶段 · Never-Do · 关键路径 · Gate |
| 13 | `13_ARCHITECTURE_DECISIONS.md` | ADR | 8 条架构决策记录（含否决方案） | ADR-001~008 · 决策索引（ADR↔原则↔层） |
| 14 | `14_RISK_ASSESSMENT.md` | Risk Assessment | 风险分级 + 风险—红线映射 + 门禁建议 | 分级 · 技术/架构/产品风险 · 红线映射 · 门禁 |
| 15 | `15_AI_OS_MASTER_PLAN.md` | Master Plan | 综合总方案：一页总览 + 决策速记 + 路线图汇总 | 一句话 · 一页总览 · 八决策 · 路线图 · 文档清单 · STOP |
| 99 | `99_ARCHITECTURE_MASTER_INDEX.md` | Master Index | 本文档：导航与速查 | 目录 · 阅读路径 · 概念映射 · 速查卡 |

---

## 2. 推荐阅读路径（Reading Paths）

- **高管 / Review 快速通道**：`00` → `10` → `11` → `12` → `15`（30 分钟看懂全貌与价值）
- **架构师深读**：`01` → `02` → `03` → `04` → `05` → `06` → `07` → `08` → `09` → `13`
- **开发 Sprint 承接**：`12`（路线图）→ `13`（ADR）→ `14`（风险门禁）→ 对应模块文档
- **定位 / 竞品对齐**：`10` → `11`

---

## 3. 概念 → 文档映射（Concept → Doc）

| 概念 | 权威定义文档 |
|------|------------|
| 分层模型 L0–L9 | `01` §3 |
| 冻结红线（L0） | `01` §2 |
| P11 单一执行通道 | `01` §4 / `05` §7 / `06` §5 / `13` ADR-006 |
| P12 知识即文件 | `01` §4 / `03` / `13` ADR-002 |
| P13 薄主动层 | `01` §4 / `07` / `13` ADR-003 |
| P14 角色而非进程 | `01` §4 / `06` / `13` ADR-004 |
| P15 可崩溃恢复 | `01` §4 / `04` §7 / `05` §5 / `13` ADR-005 |
| 10 层 UMA 记忆 | `02` |
| Obsidian 知识层 | `03` |
| Goal/Workflow 生命周期 | `04` / `05` |
| 统一 Extension + MCP 适配器 | `08` / `13` ADR-007 |
| Local First 五大支柱 | `09` / `13` ADR-008 |
| 护城河 / 竞品 | `11` |
| 12 个月路线图 | `12` |
| 8 条 ADR | `13` |

---

## 4. 速查卡（Quick Reference）

**10 层职责分层（L0 顶 → L9 底，单 Runtime 内职责分层）：**
Surface/Workspace → Proactive AI → Goal Engine → Workflow Engine → Agent Engine → AI Brain → Knowledge Engine → Memory Engine → Plugin/Extension → Local First Infrastructure

**5 条 2.0 增补原则：**
P11 单一执行通道 · P12 知识即文件 · P13 薄主动层 · P14 角色而非进程 · P15 可崩溃恢复

**8 条 ADR：** 001 单 Runtime · 002 知识即文件 · 003 薄主动层 · 004 角色而非进程 · 005 可崩溃恢复 · 006 单一执行通道 · 007 统一 Extension · 008 Local First

**L0 冻结红线（不可逾越）：** 单 Runtime / 单状态写入口(applyEvent→reducers) / 单通信通道(EventBus) / 单权限(PermissionGuard+PolicyEngine) / 事件契约 DOMAIN=71 SYSTEM=8 / Local First / No God Module / 增量演进

**唯一通信：** EventBus（DOMAIN + SYSTEM 事件）；**唯一写动作出口：** Execution Channel → PermissionGuard → Executor

---

## 5. 状态与纪律

- 本系列为 **AI OS Architecture Sprint v1.0** 纯设计产出（17 份文档）。
- ✅ 全程零代码 / 零配置改动，完全兼容 L0 冻结红线，为 v1.0 演进延展。
- 🛑 **STOP**：待人工 Review 批准后方可进入开发 Sprint。未经批准不得实现任何设计、不得修改代码。
- 详细摘要见 `00_EXECUTIVE_SUMMARY.md`；综合总方案见 `15_AI_OS_MASTER_PLAN.md`。
