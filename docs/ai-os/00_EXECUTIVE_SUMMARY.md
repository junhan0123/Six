# 小6 AI OS 2.0 架构设计 — Executive Summary

> Sprint: AI OS Architecture Sprint v1.0
> 身份: Chief AI Architect + Chief System Architect + Chief Product Architect + Chief Knowledge Architect
> 模式: Audit → Research → Architecture → Design → Verify → Report → STOP
> 性质: 纯架构设计（系统设计，**不含任何代码 / 配置 / Runtime 改动**）
> 日期: 2026-08-06
> 状态: ✅ 17 份文档已落盘（15 架构 + 本摘要 + Master Index）；**STOP 等待人工 Review**

---

## 0. 一句话结论

本 Sprint 输出了小6 AI OS 2.0 的完整技术架构蓝图：一个**本地优先（Local First）个人 AI 操作系统**，在单一 Runtime 内以 10 个职责分层组织记忆、知识、目标、工作流、智能体、主动智能、插件与本地基础设施，并以 8 条架构决策（ADR-001~008）固化不可动摇的纪律红线。全程零代码改动。

---

## 1. 背景与目的

- 小6不是聊天机器人 / Copilot / Agent Demo / ChatGPT 外壳，而是长期驻留、拥有记忆与知识、能主动规划并**安全执行**任务的本地优先个人 AI OS。
- v1.0 已落地：单 Runtime、AppState（单一状态写入口）、EventBus（单一通信通道）、PolicyEngine（单一权限）、Memory 单源、Galaxy Surface、Phase 9 薄主动层等冻结红线，但缺少 2.0 系统性架构蓝图。
- 本 Sprint **唯一目标**：设计 2.0 完整技术架构（设计，非开发），为后续开发 Sprint 提供权威约束。

---

## 2. 交付物清单（17 份，落盘 `G:/xiao6/docs/ai-os/`）

| 文件 | 标题 | 角色 |
|------|------|------|
| `00_EXECUTIVE_SUMMARY.md` | 本文件 | 高管摘要 |
| `01_AI_OS_ARCHITECTURE.md` | 总体架构（总纲） | Master Architecture，约束其余 14 份 |
| `02_MEMORY_ENGINE.md` | Memory Engine | 10 层 UMA 记忆引擎 |
| `03_KNOWLEDGE_ENGINE.md` | Knowledge Engine | Obsidian 知识层（非数据库） |
| `04_GOAL_ENGINE.md` | Goal Engine | 目标生命周期与优先级 |
| `05_WORKFLOW_ENGINE.md` | Workflow Engine | DAG-of-steps 工作流 |
| `06_AGENT_ENGINE.md` | Agent Engine | Supervisor + Specialist |
| `07_PROACTIVE_AI.md` | Proactive AI | 薄主动决策层 |
| `08_PLUGIN_SYSTEM.md` | Plugin / Extension System | 统一 Extension 抽象 |
| `09_LOCAL_FIRST.md` | Local First Infrastructure | 本地优先五大支柱 |
| `10_PRODUCT_POSITIONING.md` | Product Positioning | 产品定位与 OS 隐喻 |
| `11_COMPETITIVE_ANALYSIS.md` | Competitive Analysis | 竞品对标与护城河 |
| `12_IMPLEMENTATION_ROADMAP.md` | Implementation Roadmap | 12 个月 4 阶段 |
| `13_ARCHITECTURE_DECISIONS.md` | Architecture Decisions | 8 条 ADR |
| `14_RISK_ASSESSMENT.md` | Risk Assessment | 风险分级与红线映射 |
| `15_AI_OS_MASTER_PLAN.md` | AI OS 2.0 Master Plan | 综合总方案 |
| `99_ARCHITECTURE_MASTER_INDEX.md` | Architecture Master Index | 本文档导航 |

---

## 3. 核心架构决策（ADR-001 ~ 008）

| ADR | 决策 | 对应原则 / 红线 |
|-----|------|----------------|
| 001 单一 Runtime | 决策运行时唯一，禁第二 Runtime / Memory / EventBus / Permission | 冻结红线 |
| 002 知识即文件 | 知识以 Obsidian `.md` 为真相源，机器索引（SQLite+向量）为派生 | P12 |
| 003 薄主动层 | Proactive 只建议不执行，可撤销、低打扰 | P13 |
| 004 角色而非进程 | Specialist 为同一 Runtime 内的角色切换，非子进程 | P14 |
| 005 可崩溃恢复 | Goal/Workflow 可持久化快照，重启从检查点恢复，不丢不重 | P15 |
| 006 单一执行通道 | 所有动作汇入 Execution Channel → PermissionGuard → Executor | P11 |
| 007 统一 Extension | MCP/Tool/Connector/Plugin 收敛为单一 Extension + Registry + Policy 门控 | — |
| 008 Local First | 数据本地，云端 LLM 仅作计算，不持有状态 | 冻结红线 |

---

## 4. 分层模型（L0–L9，单 Runtime 内职责分层，非进程边界）

```
┌──────────────────────────────────────────────────────────────┐
│  L0  Surface / Workspace（Galaxy · Command · Dashboard · Overlay）│  ← 用户可见层（已有，2.0 收口）
├──────────────────────────────────────────────────────────────┤
│  L1  Proactive AI（薄决策层：IGNORE/SUGGEST/NOTIFY/CREATE_GOAL）  │
├──────────────────────────────────────────────────────────────┤
│  L2  Goal Engine（目标生命周期 · 优先级 · Goal Tree · 队列）      │
├──────────────────────────────────────────────────────────────┤
│  L3  Workflow Engine（DAG-of-steps · Checkpoint · HITL · 自动化） │
├──────────────────────────────────────────────────────────────┤
│  L4  Agent Engine（Supervisor 编排 + Specialist 角色切换）        │
├──────────────────────────────────────────────────────────────┤
│  L5  AI Brain（LLM · Reasoning · Planning · Reflection · 上下文管道）│
├──────────────────────────────────────────────────────────────┤
│  L6  Knowledge Engine（Obsidian 知识层 · 非数据库）              │
├──────────────────────────────────────────────────────────────┤
│  L7  Memory Engine（10 层 UMA · 单一逻辑源）                    │
├──────────────────────────────────────────────────────────────┤
│  L8  Plugin / Extension System（统一 Extension 抽象 + Registry + 权限）│
├──────────────────────────────────────────────────────────────┤
│  L9  Local First Infrastructure（本地持久化 · 离线降级 · 可选同步） │
└──────────────────────────────────────────────────────────────┘
        ⇅ 唯一通信：EventBus（DOMAIN + SYSTEM）⇅
```

---

## 5. 真正的核心竞争力（Moat）

四者**统一**构成护城河——单点可被竞品复制，组合不可：

1. **Local First × 隐私架构**：数据不出本机、最小上下文外传、用户为唯一事实源。
2. **记忆 × 知识双引擎**：UMA 10 层记忆 + Obsidian 文件即真相的知识层，长期且可导航。
3. **克制的主动智能**：薄层、低打扰、可撤销，宁可不打扰也不误执行。
4. **OS 级执行内核**：单一执行通道 + PolicyEngine，把"安全执行"做成系统能力而非个案。

- **必须做到世界级**：记忆一致性 / 知识导航 / 执行安全感 / 离线可用 / 打扰克制。
- **绝不抄袭**：无限自动执行 Agent / 云持有数据 / 黑箱知识库 / 多 Runtime 智能体 / 脆弱不可恢复的执行。

---

## 6. 12 个月路线图（4 阶段）

| 阶段 | 月份 | 主题 | 关键交付 |
|------|------|------|---------|
| A | M1–3 | 地基与记忆 | 单 Runtime 收口、UMA 持久化、崩溃恢复原型 |
| B | M4–6 | 知识与目标 | Obsidian 知识层、Goal Engine 形式化生命周期 |
| C | M7–9 | 智能体与主动 | Agent Supervisor/Specialist、Proactive 克制策略 |
| D | M10–12 | OS 体验与生态 | Surface 收口、Plugin System、可选同步 |

**顺序约束**：地基先于体验 / 数据先于智能 / 形式化先于自动化 / 权限先于放权 / 可恢复先于并发。
**Never-Do**：不引第二 Runtime / 不云持有数据 / 不自动执行敏感 / 不 SQLite 重造知识 / 不多进程 Agent / 不牺牲恢复换并发 / 不静默云覆盖。

---

## 7. 纪律红线合规声明

- ✅ 全程纯设计：零代码、零配置、零 Runtime / Agent / Planner / Tool / UI / Memory / EventBus / DB 改动。
- ✅ 完全兼容 L0 冻结红线（单 Runtime / 单 Memory / 单 EventBus / 单 Permission / 事件契约 DOMAIN=71 SYSTEM=8 / Local First / No God Module / 增量演进）。
- ✅ 设计为 v1.0 的演进延展，未推翻任何既有运行时。
- ✅ 未借机优化、未进入实现阶段。

---

## 8. 状态与下一步

- 本 Sprint 已停止（**STOP**）。所有产出为设计文档，待人工 Review 批准。
- 批准后方可进入 AI OS 2.0 **开发 Sprint**，按 Roadmap 从 Phase A 起，严格遵守冻结红线与 8 条 ADR。
- 未经批准：不得实现任何设计、不得修改任何代码 / 配置、不得进入开发阶段。

> 详细导航见 `99_ARCHITECTURE_MASTER_INDEX.md`。
