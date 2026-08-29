# 01 — Xiao6 AI OS 2.0 总体架构（AI OS Architecture）

> 文档类型：主架构（Master Architecture）
> 身份：Chief AI Architect + Chief System Architect + Chief Product Architect + Chief Knowledge Architect
> 模式：Audit → Research → Architecture → Design → Verify → Report → STOP
> 效力：本文件为 `docs/ai-os/` 系列的总纲；其余 14 份文档均以此文件的分层模型与红线为约束。
> 兼容性：本设计是 `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` 与 `docs/frozen/Xiao6-v2-核心架构规范.md` 的**演进延展**，不推翻、不违背任何冻结红线。

---

## 1. 定位重申（不变量）

Xiao6 不是聊天机器人、不是 Copilot、不是 Agent Demo、不是另一个 ChatGPT 外壳。

它是 **本地优先（Local First）的个人 AI 操作系统（Personal AI Operating System）**——一个长期驻留、拥有记忆与知识、能主动规划并执行任务、以用户本地数据为唯一事实源的计算环境。

所有 2.0 设计围绕这一句话展开。任何功能若不能强化"OS"或"Local First"属性，则不在核心范围内。

---

## 2. 冻结红线（L0，不可逾越）

以下继承自 Golden State v1.0，2.0 **必须**继续遵守：

- **单一 Runtime**：决策运行时唯一（AgentRuntime）。禁止引入第二套 Runtime / Memory / EventBus / Permission System。
- **单一状态写入口**：状态变更必须经 `applyEvent → reducers`（AppState）。
- **单一通信通道**：跨模块通信必须发领域事件（EventBus），禁止直接函数调用跨模块状态。
- **单一权限**：所有执行必经 `PermissionGuard` + `PolicyEngine`。
- **事件契约冻结**：DOMAIN=71 / SYSTEM=8，前后端逐字一致，未走 Migration 不得破坏。
- **Local First**：用户数据、记忆、知识默认落盘本地；云端 LLM 仅作计算能力调用，不得成为状态所有者。
- **No God Module**：单一文件不得同时承担路由、编排、执行、持久化、事件分发。
- **增量演进**：新能力以新增模块/事件/Skill 加入，不推翻已有运行时。

> 本 Sprint 为**纯设计**，不修改任何代码/配置/Runtime/DB。下列所有组件均为"目标态设计"，实现另由开发 Sprint 承接。

---

## 3. 分层架构模型（Layered Model）

AI OS 2.0 在单一 Runtime 内组织为 10 个逻辑层。层级是**职责分层**，不是进程边界——全部运行在同一 Runtime 进程内，通过事件扇出与显式接口协作。

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

### 3.1 层职责速查

| 层 | 代码标识 | 核心职责 | 绝不负责 |
|----|---------|---------|---------|
| Brain | `brain` | 推理、规划、反思、提示词/上下文管道 | 持久化、权限、UI |
| Memory | `memory` | 10 层记忆读写与检索 | 知识组织（交给 Knowledge） |
| Knowledge | `knowledge` | Obsidian vault 组织、图谱、RAG | 会话记忆（交给 Memory） |
| Goal | `goal` | 目标生命周期与优先级 | 具体执行步骤（交给 Workflow） |
| Workflow | `workflow` | 步骤 DAG 编排与执行检查点 | 目标决策（交给 Goal） |
| Agent | `agent` | Supervisor 编排 + Specialist 角色 | 独立 Runtime（共用一个） |
| Proactive | `proactive` | 触发器评估与薄决策 | 自主执行（必经 Goal/Exec） |
| Plugin | `plugin` | Extension 注册/发现/权限门控 | 业务规则 |
| LocalFirst | `local` | 落盘、离线、同步 | 业务逻辑 |
| Surface | `surface` | Galaxy/Command/Dashboard/Overlay 呈现 | 决策 |

---

## 4. 核心设计原则（2.0 增补）

在 v2 核心架构规范 10 原则基础上，2.0 增补：

- **P11 单一执行通道（Single Execution Channel）**：Goal / Workflow / Agent / Proactive 的所有"动作"必须汇入同一条执行通道（Execution Channel），经 `PermissionGuard` 后落到 Executor。禁止任何模块私建执行路径。
- **P12 知识即文件（Knowledge-as-File）**：知识以人类可读 `.md` 存在 Obsidian Vault，机器索引（SQLite + 向量）为派生。人类编辑优先，机器不得覆盖人类手写内容。
- **P13 薄主动层（Thin Proactive）**：Proactive 只能"建议/通知/建目标"，不能"自己干"。所有主动行为可追溯、可撤销、默认低打扰。
- **P14 角色而非进程（Role not Process）**：Agent 的 Specialist 是同一 Runtime 内的角色切换，不是微服务/子进程。
- **P15 可崩溃恢复（Crash-Recoverable）**：Goal/Workflow 状态必须可持久化快照，进程重启可从最近检查点恢复，不丢目标、不重复执行。

---

## 5. 模块交互与数据流

### 5.1 一次"主动建议"的端到端流

```
[Proactive 触发器] → 评估上下文 → 决策=SUGGEST
   → publish(goal:proposed) → Goal Engine 入队（Policy 门控）
   → 用户确认 → Goal 激活 → Workflow 拆解 DAG
   → Agent Supervisor 认领 → Specialist 角色切换执行步骤
   → 每步经 Execution Channel → PermissionGuard → Executor
   → 事件扇出 → Memory 写入 + Knowledge 可能更新 + Surface 刷新
```

### 5.2 通信约束

- 模块间**只**通过 EventBus 通信（DOMAIN/SYSTEM 事件）。
- Brain 的提示词/上下文管道是**只读聚合器**：从 Memory/Knowledge/State 拉取，组装后喂给 LLM，不持有状态。
- Execution Channel 是**唯一写动作出口**：见 P11。

---

## 6. 与 v1.0 的关系

- v1.0 已实现：Single Runtime、AppState、EventBus、PolicyEngine、Memory 单源、Galaxy Surface、Companion、Proactive 薄层（Phase 9）。
- 2.0 设计：将上述能力**升格为 OS 级子系统**，明确 10 层边界，补齐 Knowledge Engine（Obsidian）、统一 Plugin System、Goal/Workflow 的形式化生命周期、崩溃恢复。
- 不推翻：所有冻结红线、事件契约、Galaxy 语义、Vision 仅观察。

---

## 7. 本文档向下约束

其余 14 份文档必须满足：
1. 不得引入第二 Runtime / Memory / EventBus / Permission。
2. 所有执行须经 Execution Channel + PermissionGuard。
3. 知识以 Obsidian 文件为真相源。
4. 全部数据本地优先，云端仅计算。
5. 主动行为薄层、可撤销、低打扰。

> 本文档结束。详细设计见 02–15。
