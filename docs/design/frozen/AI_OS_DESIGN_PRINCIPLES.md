# AI_OS_DESIGN_PRINCIPLES — Design Canon（设计解释层）

> 性质：**设计解释层**，**不属于 L0/L1 权威层**。不覆盖/替代 Golden State / Decision / Governance。本文件**不覆盖、不替代** Golden State / Decision / Governance；仅冻结规范 + 来源引用 + 权威映射（方案 1）。
> 创建：2026-08-04 · 方式：冻结规范 + 来源引用 + 权威映射（方案 1）

## Source Authority（权威来源）
- **L0**：`docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` §不可逾越红线（6 条）。
- **L1**：`docs/decisions/DECISION_001..006`（6 条不可逆决策）。
- **设计原则语料**：`docs/frozen/Xiao6-v2-架构升级设计文档.md` §3.1 设计原则；`docs/design/Xiao6-v2-智能贾维斯-演进路线.md` §五 执行纪律。

## Related Documents（关联文档）
- `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md`
- `docs/decisions/DECISION_001_EVENTBUS.md` … `DECISION_006_LANGCHAIN_POSITION.md`
- `docs/frozen/Xiao6-v2-架构升级设计文档.md`
- `docs/design/Xiao6-v2-智能贾维斯-演进路线.md`

## Frozen Status（冻结状态）
- 本文件（解释层）：**FROZEN**。
- 引用权威：Golden State 红线 FROZEN；6 份 Decision FROZEN；v2 设计原则为草案语料（非冻结，仅归纳）。

## Scope（范围）
- 把散落在 Golden State / Decision / v2 草案中的**设计原则**收敛为一份可引用的解释索引。
- 每条原则标注其权威出处，便于新 AI 维护者快速对齐「什么能做、什么不能」。

## Non-goals（非目标）
- **不创造新原则**（用户约束 3）。
- 不重述 Golden State 红线原文（仅索引指向）。
- 不把 v2 草案原则提升为冻结规范。

## Design Interpretation（设计解释）

### A. 不可逾越红线（来自 Golden State L0，逐字优先）
1. 禁止第二 Runtime / Memory / EventBus / Permission System。
2. 禁止绕过 AppState（状态变更须经 `applyEvent → reducers`）。
3. 禁止绕过 EventBus（跨模块通信必须发领域事件）。
4. 禁止直接调用 Executor（必经 `PermissionGuard`）。
5. 禁止修改 Galaxy 语义（银河本体视觉资产 100% 保留）。
6. 禁止 Vision 直接控制电脑（OBSERVATION ONLY，绝不产生 Action）。

### B. 不可逆决策原则（来自 DECISION_001..006，L1）
- 事件单一来源（EventBus + 注册表校验，前后端逐字对齐）。
- 单一决策 Runtime（AgentRuntime 唯一；观察生产者不决策）。
- 单一 Memory（memory.py 唯一来源，禁止第二 RAG 存储）。
- Galaxy 边界（表现层 + 受控交互层，不改银河本体）。
- 权限单一闸门（PolicyEngine + PermissionGuard）。
- LangChain 仅借鉴不引入（禁 `import langchain`）。

### C. 工程与产品原则（归纳自 v2 草案 + JARVIS 路线，未冻结，仅参考）
- **不推翻**：保留现有 API / 数据库 / 23 工具 / 34 项功能（v2 §3.1-1）。
- **增量演进**：新增模块/来源/表，不推翻运行时（v2 §1.7）。
- **本地优先**：数据落本地 SQLite，云 LLM 仅作计算（v2 P1 §1.3）。
- **零密钥优先**：本地 ASR/模型/感知零密钥可做；云渠道单列、配密钥再启（JARVIS §五）。
- **隐私优先**：感知/常驻能力默认关、强开关、可审计、绝不静采（JARVIS §五）。
- **小步提交**：确认后入库、可 revert（JARVIS §五）。

> 冲突裁决：C 类原则若与 A/B 类（L0/L1）冲突，一律以 A/B 优先。本解释层不得越过权威层。
