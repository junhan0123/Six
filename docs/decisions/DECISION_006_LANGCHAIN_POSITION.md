# DECISION_006 — LangChain 定位（借鉴不引入）

## 背景
Phase 9 认知编排层需要 Tool Registry、Chain/Graph 编排、Memory 抽象、Workspace 概念。LangChain 提供了成熟的对应思想。

## 问题
- 直接引入 LangChain Runtime 会与小6自有 `AgentRuntime` 冲突，形成第二 Runtime（违反 DECISION_002）。
- LangChain 的抽象未必贴合本地优先、EventBus 驱动的架构。

## 候选方案
1. **A. 直接引入 LangChain Runtime**（违反无第二 Runtime 红线）。
2. **B. 仅借鉴思想，运行在自有 AgentRuntime 内**（采用）。

## 最终选择
**B**：**借鉴** LangChain 的四类思想，但**绝不引入其代码/Runtime**：
- Tool Registry 思想 → 统一 Capability Catalog（computer/knowledge/memory/automation/analysis）
- Chain / Graph 思想 → Goal→Context Builder→Capability Selection→Execution Plan→Reflection，运行在 `AgentRuntime` 内
- Memory 抽象思想 → 短期/工作/长期分层，复用 `memory.py`
- Workspace 思想（亦借鉴 AnythingLLM）→ Project Workspace 形成 Workspace Context

**AnythingLLM**：仅借鉴 Workspace 概念，禁止复制其代码。

## 原因
- 自有架构已具备 EventBus + AppState + AgentRuntime + PolicyEngine，无需外部 Runtime。
- 借鉴思想可吸收最佳实践而不承担依赖与架构冲突。
- 保持「本地优先、单一决策运行时」的纪律。

## 影响范围
- Phase 9 Context Engine / Capability Catalog / Knowledge Workspace Interface 均在本决策约束内设计。
- 禁止 `import langchain` / 引入 AnythingLLM 代码。

## 未来限制
- 禁止以「复用生态」为名引入 LangChain / AnythingLLM 运行时。
- 借鉴思想时不得偏离 EventBus / AppState / 单一 Runtime 纪律。
