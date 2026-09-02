# 12 — Implementation Roadmap（实施路线图 · 12 个月）

> 依赖：全部 01–11、13（决策）、14（风险）
> 性质：**开发顺序规划**，非本 Sprint 实现。本 Sprint 仅设计。

---

## 1. 总原则（顺序约束）

1. **地基先于体验**：Local First / 单 Runtime 加固 先于 Surface 翻新。
2. **数据先于智能**：Memory / Knowledge 落盘 先于 Goal / Workflow / Agent。
3. **形式化先于自动化**：Goal/Workflow 生命周期 先于 Agent 自动执行。
4. **权限先于放权**：PolicyEngine 完备 先于 Proactive 主动建目标。
5. **可恢复先于并发**：崩溃恢复（P15） 先于高并发调度。

---

## 2. 12 个月 · 4 阶段

### Phase A — 地基与记忆（M1–M3）
| Sprint | 目标 | 关键 Step |
|--------|------|----------|
| A1 Local First 加固 | 静态加密、离线降级、快照底座 | 本地存储抽象 / 密钥库 / Degrade.mode |
| A2 Memory Engine | UMA 十层落地、语义索引 | L1–L10 实现 / mem_vectors / 生命周期状态机 |
| A3 崩溃恢复底座 | Goal/Workflow 快照 + 幂等 | 快照服务 / idempotency_key / 恢复流程 |

### Phase B — 知识与目标（M4–M6）
| Sprint | 目标 | 关键 Step |
|--------|------|----------|
| B1 Knowledge Engine | Obsidian Vault + Sync Bridge | Vault 结构 / Backend 索引 / RAG 溯源 |
| B2 Goal Engine | 目标状态机 + 队列 + Tree | 状态机 / Policy 门控 / Goal Tree |
| B3 Workflow Engine | DAG 编排 + HITL + 检查点 | Step 模型 / 调度 / HITL 通道 |

### Phase C — 智能体与主动（M7–M9）
| Sprint | 目标 | 关键 Step |
|--------|------|----------|
| C1 Agent Engine | Supervisor + Specialist | 角色上下文 / 交接 handoff / 反思 |
| C2 Proactive 形式化 | 薄层决策 + 打扰预算 | 触发器 / 决策分类 / 预算频控 |
| C3 Plugin 统一 | 单一 Extension + Registry | manifest / 权限 scope / MCP 适配器 |

### Phase D — OS 体验与生态（M10–M12）
| Sprint | 目标 | 关键 Step |
|--------|------|----------|
| D1 Surface 收敛 | Galaxy/Command/Dashboard/Overlay 统一 | Design Token / 导航 / 组件原语 |
| D2 Companion 升格 | 桌宠=OS 交互入口 | 主动呈现 / 执行反馈 / 生命感 |
| D3 生态与 GA | 插件市场 + 发布 | 可选同步 / 安装器 / GA 门禁 |

---

## 3. 永远不做（Never-Do List）

- 🚫 永不引入第二 Runtime / Memory / EventBus / Permission。
- 🚫 永不将云端设为状态所有者（Local First 不可破）。
- 🚫 永不自动执行未经用户确认的敏感动作（薄主动层）。
- 🚫 永不在 SQLite/向量库重造知识链接/图谱（知识即文件）。
- 🚫 永不靠多进程/微服务拼 Agent（角色而非进程）。
- 🚫 永不牺牲崩溃恢复换取并发（P15 优先）。
- 🚫 永不静默云同步覆盖本地数据。

---

## 4. 依赖与关键路径

```
A1 ─▶ A2 ─▶ A3 ─┐
                 ├─▶ B1 ─┐
A1 ──────────────┘      ├─▶ B2 ─▶ B3 ─▶ C1 ─▶ C2 ─▶ C3 ─▶ D1 ─▶ D2 ─▶ D3(GA)
                 └─▶ (B1 可与 A2 并行尾部)
```

- 关键路径：A1→A2→A3→B2→B3→C1→C2→C3→D1→D2→D3。
- B1（Knowledge）可与 A3 尾部并行，不阻塞关键路径。

---

## 5. 阶段出口标准（Gate）

- A 阶段末：无网可跑核心闭环 + 崩溃不丢目标。
- B 阶段末：Goal/Workflow 形式化且可持久化恢复。
- C 阶段末：Agent 执行 + 主动建议经统一权限，无越权。
- D 阶段末：统一 Surface + 可选同步 + GA 门禁通过。

> 路线图供开发 Sprint 排期；本 Sprint 不实现，STOP 等 Review。
