# 13 — Architecture Decisions（架构决策记录 · ADR）

> 依赖：01（原则与红线）、12（路线图）
> 格式：ADR 风格，含"已否决的替代方案"。

---

## ADR-001 · 单一 Runtime

- **决策**：决策运行时唯一（AgentRuntime）；禁止第二 Runtime / 子进程 Agent。
- **背景**：v1.0 已冻结单 Runtime；多 Runtime 会导致状态分裂、权限分裂、崩溃难恢复。
- **考虑的替代**：微服务 Agent / 多进程编排器。
- **否决理由**：破坏 Local First 与崩溃恢复；增加权限与事件一致性成本。
- **后果**：所有模块（Goal/Workflow/Agent/Plugin）同进程协作。

## ADR-002 · 知识即文件（Knowledge-as-File）

- **决策**：知识以 Obsidian `.md` 为真相源；SQLite/向量为派生索引。
- **背景**：黑箱向量库把用户锁进不可读状态。
- **考虑的替代**：纯向量知识库 / 图数据库。
- **否决理由**：不可读、不可拥有、不可携带。
- **后果**：Sync Bridge 人类编辑优先；机器索引不得覆盖正文。

## ADR-003 · 薄主动层（Thin Proactive）

- **决策**：Proactive 仅 IGNORE/SUGGEST/NOTIFY/CREATE_GOAL，无副作用。
- **背景**："自动执行 Agent"引发信任与安全焦虑。
- **考虑的替代**：全自动 Proactive 执行。
- **否决理由**：不可撤销、高打扰、破坏用户掌控。
- **后果**：所有落地动作经 Goal/Execution 通道，可撤销。

## ADR-004 · 角色而非进程（Role not Process）

- **决策**：Specialist 是同一 Runtime 内的角色上下文切换。
- **背景**：多进程 Agent 难共享状态、难恢复。
- **考虑的替代**：每角色独立子进程 / 容器。
- **否决理由**：违反 ADR-001，状态一致性成本高。
- **后果**：Supervisor 编排 + 上下文 handoff。

## ADR-005 · 可崩溃恢复（Crash-Recoverable）

- **决策**：Goal/Workflow 状态可快照，重启从检查点恢复，步骤幂等。
- **背景**：脆弱执行（崩即丢目标）不可接受。
- **考虑的替代**：无状态重跑 / 人工重启。
- **否决理由**：丢目标、重复执行、体验差。
- **后果**：idempotency_key + 本地快照 + 恢复事件。

## ADR-006 · 单一执行通道（Single Execution Channel）

- **决策**：所有动作经 Execution Channel → PermissionGuard → Executor。
- **背景**：模块私建执行路径导致权限失效。
- **考虑的替代**：各模块直接调用 Executor。
- **否决理由**：绕过 PolicyEngine，审计缺失。
- **后果**：P11 约束全系统。

## ADR-007 · 统一 Extension（MCP 为适配器）

- **决策**：MCP/Tool/Connector/Plugin 收敛为单一 Extension + Registry + 权限。
- **背景**：多类扩展抽象造成重复与权限分裂。
- **考虑的替代**：保留各类独立系统。
- **否决理由**：权限门控难以统一，维护成本高。
- **后果**：MCP 是协议适配器，不另立运行时。

## ADR-008 · Local First（云仅计算）

- **决策**：用户数据本地真相源；云端 LLM/嵌入仅计算，结果本地缓存。
- **背景**：云持有数据破坏隐私与离线可用性。
- **考虑的替代**：云优先同步。
- **否决理由**：违反定位与隐私架构。
- **后果**：离线降级路径必存在；同步可选且本地优先合并。

---

## 决策索引

| ADR | 原则 | 对应层 |
|-----|------|--------|
| 001 | 单 Runtime | 全局（L0） |
| 002 | 知识即文件 | L6 |
| 003 | 薄主动层 | L1 |
| 004 | 角色而非进程 | L4 |
| 005 | 可崩溃恢复 | L2/L3 |
| 006 | 单一执行通道 | 全局（P11） |
| 007 | 统一 Extension | L8 |
| 008 | Local First | L9 |

> 决策记录；实现须逐条遵守，本 Sprint 不写代码。
