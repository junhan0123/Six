# Knowledge Context Integration — Xiao6 v1.3

> 知识上下文集成 | Project Intelligence System v1.3 · Phase 9
> ⚠️ **命名澄清**：本文件是 **v1.3 知识治理任务的 Phase 9（设计知识如何接入上下文）**，**不是**项目路线的实现 Phase 9（Computer Operating Layer 实现）。项目实现 Phase 9 仍处「待设计审批、未实现、禁止进入」状态，本文件不触碰它。
> 纪律：仅设计集成**关系**；不实现 Context Engine、不新增 Runtime/Memory、不修改代码。

---

## 1. 目的

Phase 6/7/8 定义了知识如何被检索、融合、排序。本 Phase 定义**知识层（Knowledge Layer）在系统上下文架构中的位置**——它如何与已有的 Memory、World Model、Context Engine 协作，且**明确不替代**任何一方。

> 核心命题：**Knowledge Layer 是 Context Engine 的一个上下文源（source），与 Memory、World Model 并列，而非其上、其下或取而代之。**

---

## 2. 上下文架构（概念分层）

```
                        ┌─────────────────────────┐
                        │      Context Engine      │  ← 组装最终 LLM 上下文
                        │   (Phase 9 实现，未做)    │
                        └───────────┬─────────────┘
               ┌────────────────────┼────────────────────┐
               ↓                    ↓                    ↓
        ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
        │  Memory     │     │  World Model │     │ Knowledge    │
        │ (memory.py) │     │ (态势/环境)  │     │ Layer (v1.3) │
        │ 单一来源    │     │ 感知/外部    │     │ KU+检索+排序 │
        └─────────────┘     └──────────────┘     └──────────────┘
```

- **Memory**：用户/系统的长期记忆（对话、偏好、事实），`memory.py` 单一来源（GOLDEN_STATE 红线）。
- **World Model**：当前世界态势（热点/环境/外部数据源），观察性。
- **Knowledge Layer**：**关于项目本身的知识**（架构/红线/决策/阶段），即 v1.3 全部产物。

---

## 3. 集成原则（硬约束）

1. **不替代 Memory**：Knowledge Layer 承载「项目知识」，Memory 承载「用户/对话记忆」。二者内容域不重叠；知识进上下文不写 Memory，记忆不被知识覆盖。
2. **不替代 World Model**：知识是静态/半静态规范，World Model 是动态态势；知识不消费实时感知。
3. **不新增 Runtime/Memory/EventBus**：集成是**逻辑消费**（Context Engine 在组装时读取 Knowledge Layer 产出），不引入新基础设施（GOLDEN_STATE 红线）。
4. **服务 Context Engine**：Knowledge Layer 的输出是「已检索+过滤+排序+去冲突的知识上下文块」（Phase 6 §3.6），作为 Context Engine 的一个输入源。
5. **只读**：Knowledge Layer 对外只提供读取接口概念；写入走 Phase 10 治理规则（Create→Review→…→Freeze）。

---

## 4. 集成数据流（概念）

```
用户请求
  → Context Engine 触发三源收集：
      Memory 投影 (state.memory)         ── 已有
      World Model 投影 (PerceptionState) ── 已有
      Knowledge Layer 块 (本 v1.3)        ── 经 Phase 6 管道产出
  → 三源合并 + 预算截断 → LLM 上下文
```

- Knowledge Layer 块带 `source` 引用，LLM 可溯源到 `XIAO6_GOLDEN_STATE` 等权威文档。
- 三源冲突时：Memory/World Model 不属知识权威范畴；知识内部冲突已由 Phase 4/5/6 解决。

---

## 5. 与项目 Phase 9 的边界

| 项目 Phase 9（实现） | 本 v1.3 Phase 9（设计） |
|----------------------|-------------------------|
| Computer Operating Layer 实现 | 知识如何接入上下文的概念 |
| 待设计审批、禁止进入 | 本任务范围（设计层） |
| 可借鉴 LangChain 思想（DECISION_006） | 不涉及 LangChain，仅定义集成关系 |

> 明确：本项目实现 Phase 9 仍冻结待审；本文件仅为「未来实现 Phase 9 时，知识层如何被消费」预留设计输入，不启动任何实现。

---

## 6. 设计纪律确认

✅ 仅定义集成关系，未实现 Context Engine。
✅ 明确 Knowledge Layer 不替代 Memory / World Model（硬约束）。
✅ 不新增 Runtime/Memory/EventBus（守 GOLDEN_STATE 红线）。
✅ 与项目实现 Phase 9 严格区分，未进入其实现。
✅ 不修改任何业务代码、Event Contract、Policy。

> Phase 9 完成。下一步：Phase 10 定义 Governance Rules（任务 #191）。
