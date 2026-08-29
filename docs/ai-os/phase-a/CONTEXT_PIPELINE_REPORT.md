# 小6 AI OS 2.0 — Phase A 任务三：Context Pipeline（CONTEXT_PIPELINE_REPORT）

> Sprint: AI OS Phase A — Core Intelligence Sprint v1.0
> 任务: 任务三（Context Pipeline）→ 输出本报告
> 上游: `CORE_AUDIT.md`（发现 F3 直接驱动）
> 日期: 2026-08-05
> 状态: ✅ 设计完成；本任务 STOP，待逐任务 Review

---

## 1. 目的与范围

**目标**：把小6"喂给 LLM 的上下文"收敛为**唯一管线**，消除审计发现 F3 的三路径碎片化。

**现状（F3）**：
- **路径 A** `context/LegacyContextBuilder`（builder.py:27）：五阶段 `Collect→Rank→Budget→Bundle→Build`，是架构目标态主管线。
- **路径 B** `capabilities.active_capability_blocks`（capabilities.py:67）：能力驱动块，与 A 并行注入，无统一排序/预算。
- **路径 C** `memory.build_system_prompt` + 旧 `build_context_prefix`：回退/遗留装配路径。

**设计方针（架构 01 §5.2）**：Brain 上下文管道是**只读聚合器**——从 Memory/Knowledge/State 拉取、组装、喂 LLM，**不持有状态**。

**不在范围**：Knowledge 索引重建（L6，Phase B）、Memory 引擎重构（L7，Phase B）。本任务只规范"组装"层。

---

## 2. 统一管线架构

```
                用户请求 user_text + tier
                          │
                          ▼
              ┌───────────────────────────┐
              │   ContextBuilder（唯一）    │   ← 替代路径 A/B/C 的全部直接调用
              │  Collect→Rank→Budget→Bundle→Build │
              └───────────────────────────┘
                  │                │
        ┌─────────┴──────┐  ┌──────┴──────────────┐
        │  SourceRegistry │  │  ContextRanker       │  │  ContextBudget       │
        │ （多 Source）   │  │ （多维度排序）        │  │ （真实 Token 裁剪）   │
        └─────────┬──────┘  └─────────────────────┘  └─────────────────────┘
   注册 Sources（每个 Source 内部异常隔离，builder.py:46）：
     • MemorySource        → memory.build_system_prompt   （身份/长期记忆）
     • UserModelSource     → cognitive/user_model.py       （用户画像，FEATURE_USER_MODEL）
     • EpisodicSource      → cognitive/episodic.py         （情景记忆，FEATURE_EPISODIC_MEMORY）
     • PersonalitySource   → context/personality_source.py （人格，FEATURE_PERSONALITY）
     • GoalSource          → context/goal_source.py        （目标，FEATURE_GOAL_SYSTEM）
     • KnowledgeSource     → context/knowledge_source.py   （RAG 召回，FEATURE_KNOWLEDGE_RAG）
     • ★ CapabilitySource  → capabilities.active_capability_blocks  （新增，消纳路径 B）
```

**唯一出口**：`ContextBuilder.build(BuildContext) → ContextBundle.prompt_text` 直接送入 `llm.agnes_completion`。调用方（server 对话链路）只认 `ContextBuilder`，不再直连 `capabilities` 或 `memory.build_system_prompt`。

---

## 3. 关键改动

### 3.1 新增 `CapabilitySource`（消纳路径 B）
- 在 `context/` 下新增 `capability_source.py`，实现 `Source` 接口：
  - `collect(ctx)` 调用 `capabilities.active_capability_blocks(ctx.user_text)`，把每个非空块封装为 `ContextItem(source=CAPABILITY, content=block, priority/high)`。
  - 沿用 `SourceRegistry.collect` 的异常隔离（单能力失败不影响其他来源）。
- 在 `LegacyContextBuilder.__init__` 中按 `FEATURE_*` 注册（默认 ON）：
  ```python
  if getattr(config, "FEATURE_CAPABILITY_CONTEXT", True):
      registry.register(CapabilitySource())
  ```
- **路径 B 退场**：`capabilities.py` 保留 `active_capability_blocks` 作为能力块工厂，但**不再被对话链路直接调用**，统一经 `CapabilitySource` 入场。

### 3.2 启用真实预算裁剪（消纳"无限预算"半成品）
- `ContextBudget`（context/budget.py）当前默认 `unlimited`（builder.py:71），**未兑现裁剪能力**。
- 本任务将其落地：默认档位由 `unlimited` 切到 `BudgetTier.T32K`（models.py:37 已定义 T16K~T96K），`apply()` 按 `token_est` 降序裁剪至 `max_tokens`，超出低 priority/recency 者丢弃。
- 回退开关：`FEATURE_CONTEXT_ENGINE=false` 时退到 `memory.build_system_prompt`（路径 C 仅作兜底，不并行）。
- 调用方可按请求类型选档（如长文档摘要用 T64K，闲聊用 T16K）。

### 3.3 `ContextSource` 枚举增补
- `models.py:14 ContextSource` 新增 `CAPABILITY = "capability"`，与既有 `TOOL`/`CONVERSATION` 等并列，便于排序策略区分。

### 3.4 旧路径 C 处置
- `memory.build_system_prompt` 保留为**回退实现**，仅在 `FEATURE_CONTEXT_ENGINE=false` 时被 `LegacyContextBuilder` 内部委托；正常运行不并行调用。
- 旧 `build_context_prefix`（memory.py/prefetch.py 引用）标记为 deprecated，后续 Phase 删除，不在 Phase A 范围。

---

## 4. 只读聚合纪律（红线对齐）

- 所有 Source 的 `collect` **只读取** Memory/Knowledge/State/能力块，**不写**任何状态、不发射领域事件。
- `ContextBuilder` 产出 `ContextBundle`（不可变 frozen dataclass，models.py:85），组装完即焚，不缓存跨请求状态。
- 与 `AgentRuntime` 反思蒸馏（`_distill_memory`）解耦：蒸馏走独立线程（`agent_runtime.py:392`），不混入上下文装配。

---

## 5. 红线合规

| 红线 | 合规性 | 说明 |
|------|--------|------|
| 单 Runtime | ✅ | 纯函数式管线，无新进程/线程 |
| 单 EventBus | ✅（无关） | 管道不发射事件；只读 |
| No God Module | ✅ | `context/` 各 Source 单一职责 |
| 增量演进 | ✅ | 新增 `CapabilitySource` + 预算档位；旧路径保留回退 |
| 知识即文件(P12) | ✅ | KnowledgeSource 仍走 RAG 派生，不写 Vault |
| Local First | ✅ | 上下文全本地组装，无外传 |

---

## 6. 实现清单

1. 新增 `context/capability_source.py`（`CapabilitySource`）。
2. `context/models.py`：`ContextSource` 增 `CAPABILITY`。
3. `context/budget.py`：实现真实 `T16K~T96K` 裁剪（当前占位 unlimited）。
4. `context/builder.py`：注册 `CapabilitySource`；默认档位 T32K。
5. 对话链路调用点改为统一 `ContextBuilder.build()`，移除对 `capabilities.active_capability_blocks` / `memory.build_system_prompt` 的直接调用（回退路径除外）。
6. 单测：多 Source 异常隔离、预算裁剪边界、回退开关。

**本任务为设计交付；代码落地待 Phase A 实现阶段（经 Review 批准）。**

**STOP**：任务三设计完成。待 Review 批准后进入任务四（Execution Pipeline）。未经批不得修改代码、不得扩大范围。
