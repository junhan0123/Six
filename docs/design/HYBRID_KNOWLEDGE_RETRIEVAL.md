# Hybrid Knowledge Retrieval — Xiao6 v1.3

> 混合知识检索（吸收 RAG / Graph RAG 思想） | Project Intelligence System v1.3 · Phase 7
> 任务等级：LONG RUNNING KNOWLEDGE INTELLIGENCE FOUNDATION TASK
> 纪律：仅吸收思想、定义三信号融合概念；**不实现**、不引入向量库/Embedding/图数据库。

---

## 1. 目的与边界

Phase 6 的 Retrieval 阶段（§3.4）只定义了「按 domain/tags/type 关键字检索」。本 Phase 吸收业界 **RAG（检索增强生成）** 与 **Graph RAG（图结构检索）** 的核心思想，扩展为**三信号混合检索**概念，使未来实现期有清晰蓝图。

> ❗ **最高纪律**：本 Phase **不实现任何检索**。不引入 Vector Database / Embedding Pipeline / Chroma / Milvus / FAISS / 图数据库。仅定义「若将来实现，三信号如何融合」。当前 Xiao6 知识仍靠 Markdown + 元数据（Phase 2/3）承载。

---

## 2. 三信号模型

| 信号 | 思想来源 | 当前可落地位 | 未来实现形态（概念） |
|------|----------|--------------|----------------------|
| **Keyword** | 传统全文检索 | ✅ 已可（DOCUMENT_INVENTORY + KU 元数据 tags/domain） | 倒排索引 / 字段匹配 |
| **Semantic** | RAG / Embedding | ❌ 本任务禁止 | 向量相似度（需 Embedding，未来决策） |
| **Relationship** | Graph RAG | 🟡 半可（Phase 5 类型化关系模式，但无图存储） | 图遍历 / 多跳扩展 |

> 关键认知：**Relationship 信号已具备模式基础（Phase 5）**，只是未存为图；Keyword 信号已具备元数据基础（Phase 3）。Semantic 是唯一的「未来能力」，本任务不碰。

---

## 3. 信号融合概念（Fusion）

未来实现期可将三信号分数融合为单召回分：

```
score_hybrid(KU) = w_k * s_keyword
                + w_s * s_semantic     (未来)
                + w_r * s_relationship
```

- `s_keyword`：元数据字段匹配度（domain/tags/type 命中数）。
- `s_semantic`：向量余弦相似（未来；本任务不定义维度/模型）。
- `s_relationship`：与目标 KU 的关系路径强度（Phase 5 边遍历深度/类型权重）。
- `w_*`：权重，建议 `w_k ≥ w_r > w_s`，且**权威（Phase 4）作为先验乘子而非加性项**（见 §4）。

> 权重为**设计建议**，非实现参数。实际值待实现期按效果调参。

---

## 4. 权威作为先验（Authority Prior）

吸收 Phase 4 核心规则：融合分须乘以权威先验，而非简单相加，确保高权威不被低相关淹没：

```
score_final = score_hybrid * authority_prior(L)
authority_prior(L100)=1.0, L90=0.9, L80=0.8, L70=0.7, L50=0.5, L30=0.25
```

- L30（前瞻设计）即使语义高度相关，最终分也被压到 ≤0.25 → 默认不进核心上下文（呼应 Phase 6 §3.5）。
- **禁止时间优先**：`authority_prior` 只由等级决定，与 `created`/`updated` 无关。

---

## 5. Relationship 信号如何扩展（Graph RAG 思想）

以目标 KU 为种子，沿 Phase 5 边做有界扩展：

1. **1 跳**：`derived_from` 上游 Decision / `boundary_of` 基线 → 必带（解释知识出处）。
2. **2 跳**：`decides`/`implements`/`emits` 主轴邻域 → 补充结构上下文。
3. **冲突环**：`contradicts` 边目标 → 若高权威，替换；若低权威，提示。
4. **深度上限**：默认 ≤2 跳，防上下文爆炸。

> 此扩展依赖 Phase 5 类型化关系；当前无图存储，故仅为蓝图。

---

## 6. 与 RAG / Graph RAG 的取舍说明

| 业界能力 | 本任务态度 | 未来建议 |
|----------|-----------|----------|
| 向量 Embedding 检索 | ❌ 禁止引入 | Phase 9+ 若需语义召回再评估，须走 Decision |
| 图数据库存储 | ❌ 禁止引入 | Phase 5 关系模式可序列化为 JSON，未来可转图 |
| 混合召回融合 | 🟡 仅定义概念 | 实现期按 §3 公式 |
| 重排序（Re-rank） | 🟡 仅定义概念 | 可用 Phase 8 Ranking Model 作 re-rank |

---

## 7. 设计纪律确认

✅ 仅吸收 RAG/Graph RAG **思想**，定义三信号与融合概念。
✅ 明确不实现、不引 Vector DB/Embedding/图库。
✅ 权威先验化解 Phase 1 §3.4（v2 前瞻误当事实）风险。
✅ 关系信号复用 Phase 5，不重复造模式。

> Phase 7 完成。下一步：Phase 8 定义 Ranking Model（任务 #188）。
