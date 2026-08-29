# 15 — AI OS 2.0 Master Plan（总体方案 · 综合）

> 综合：01–14 全部文档
> 性质：总纲落点 + 一页架构总览 + 12 月路线图汇总
> 模式：Audit → Research → Architecture → Design → Verify → Report → STOP

---

## 1. 一句话

小6 AI OS 2.0 = **本地优先的个人 AI 操作系统**：单 Runtime 内，记忆与知识双引擎驱动、薄主动层提议、目标/工作流/智能体形式化执行、统一权限门控、可崩溃恢复。

---

## 2. 一页架构总览

```
┌──────────────────────────────────────────────────────────────┐
│  L0  Surface / Workspace（Galaxy · Command · Dashboard · Overlay）│
├──────────────────────────────────────────────────────────────┤
│  L1  Proactive AI  ── 薄层：IGNORE/SUGGEST/NOTIFY/CREATE_GOAL   │
├──────────────────────────────────────────────────────────────┤
│  L2  Goal Engine    ── 目标生命周期 · 优先级 · Tree · 队列       │
├──────────────────────────────────────────────────────────────┤
│  L3  Workflow Engine ── DAG-of-steps · Checkpoint · HITL        │
├──────────────────────────────────────────────────────────────┤
│  L4  Agent Engine    ── Supervisor + Specialist（角色切换）      │
├──────────────────────────────────────────────────────────────┤
│  L5  AI Brain        ── LLM · Reasoning · Planning · 上下文管道  │
├──────────────────────────────────────────────────────────────┤
│  L6  Knowledge Engine ── Obsidian 知识层（非数据库）            │
├──────────────────────────────────────────────────────────────┤
│  L7  Memory Engine   ── 10 层 UMA · 单一逻辑源                  │
├──────────────────────────────────────────────────────────────┤
│  L8  Plugin System   ── 统一 Extension + Registry + 权限        │
├──────────────────────────────────────────────────────────────┤
│  L9  Local First Infra ── 本地持久化 · 离线降级 · 可选同步       │
└──────────────────────────────────────────────────────────────┘
        ⇅ 唯一通信：EventBus（DOMAIN + SYSTEM）⇅
        ⇅ 唯一写出口：Execution Channel → PermissionGuard → Executor ⇅
```

---

## 3. 八大决策（速记）

单 Runtime（001）· 知识即文件（002）· 薄主动层（003）· 角色而非进程（004）· 可崩溃恢复（005）· 单一执行通道（006）· 统一 Extension（007）· Local First（008）。

---

## 4. 12 个月路线图汇总

| 阶段 | 月份 | 主题 | 出口标准 |
|------|------|------|---------|
| A | M1–M3 | 地基与记忆 | 无网跑核心闭环 + 崩溃不丢目标 |
| B | M4–M6 | 知识与目标 | Goal/Workflow 形式化 + 可恢复 |
| C | M7–M9 | 智能体与主动 | Agent 执行 + 主动经统一权限 |
| D | M10–M12 | OS 体验与生态 | 统一 Surface + 可选同步 + GA |

**永远不做**：第二 Runtime / 云持有数据 / 自动执行敏感动作 / SQLite 重造知识 / 多进程 Agent / 牺牲恢复换并发 / 静默云覆盖。

---

## 5. 竞争力一句话

不与任何单点产品竞争，占据"**本地优先个人 AI 操作系统**"空白带——护城河来自架构纪律，而非炫技功能（见 11）。

---

## 6. 文档清单（15 + 元产物）

| 文档 | 主题 |
|------|------|
| 01 | 总体架构（分层 L0–L9 + 红线 + P11–P15） |
| 02 | Memory Engine（10 层 UMA） |
| 03 | Knowledge Engine（Obsidian 知识层） |
| 04 | Goal Engine（目标生命周期） |
| 05 | Workflow Engine（DAG + 检查点） |
| 06 | Agent Engine（Supervisor + Specialist） |
| 07 | Proactive AI（薄主动层） |
| 08 | Plugin System（统一 Extension） |
| 09 | Local First（本地优先基础设施） |
| 10 | Product Positioning（定位） |
| 11 | Competitive Analysis（竞品对标） |
| 12 | Implementation Roadmap（12 月路线图） |
| 13 | Architecture Decisions（ADR） |
| 14 | Risk Assessment（风险） |
| 15 | Master Plan（本文件） |
| + | Executive Summary + Architecture Master Index |

---

## 7. STOP

本 Sprint 为**纯架构设计**，未修改任何代码/配置/Runtime/DB。15 份文档 + 元产物已完成。

**下一步（待人工 Review 批准）**：方可进入 AI OS 2.0 开发 Sprint（按 12 路线图 Phase A 起），实现任一设计前须先 review 对应文档并确认不破红线。

> 等待人工 Review。未经批准，不得实现任何设计、不得修改任何代码。
