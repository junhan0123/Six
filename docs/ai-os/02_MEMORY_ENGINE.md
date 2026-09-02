# 02 — Memory Engine 2.0（记忆引擎）

> 依赖：01_AI_OS_ARCHITECTURE.md（分层 L7）
> 红线：Memory 单一逻辑来源（`memory.py`），禁止第二套 Memory。

---

## 1. 设计目标

为 Personal AI OS 提供**长期、结构化、可检索、可治理**的记忆系统。记忆不是聊天历史堆砌，而是分层、有生命周期、可蒸馏为知识的有机体。

---

## 2. 十层 UMA（Unified Memory Architecture）

| 层 | 标识 | 名称 | 内容 | 生命周期 | 持久化 |
|----|------|------|------|---------|--------|
| L1 | `mem.session` | Session | 当前回合对话上下文、临时变量 | 会话级 | 内存 + 会话结束落盘可选 |
| L2 | `mem.working` | Working | 当前任务/目标的进行中状态、草稿 | 任务级 | 本地 SQLite |
| L3 | `mem.project` | Project | 项目级约定、结构、决策记录 | 项目级 | 本地 SQLite + Vault 镜像 |
| L4 | `mem.knowledge` | Knowledge | 指向 Obsidian 知识的索引与摘要（见 03） | 长期 | SQLite 索引 + Vault 文件 |
| L5 | `mem.longterm` | Long-term | 用户画像、偏好、稳定事实 | 长期 | 本地 SQLite |
| L6 | `mem.semantic` | Semantic | 向量嵌入索引（语义检索后端） | 长期 | `mem_vectors` |
| L7 | `mem.reflection` | Reflection | 复盘记录、错误教训、改进项 | 长期 | 本地 SQLite |
| L8 | `mem.retrieval` | Retrieval | 检索策略配置、缓存、命中日志 | 运行级 | 内存 + 统计落盘 |
| L9 | `mem.lifecycle` | Lifecycle | 各层对象的 TTL、归档、遗忘策略 | 系统级 | 本地 SQLite |
| L10 | `mem.governance` | Governance | 记忆读写审计、权限、漂移检测 | 系统级 | 本地 SQLite（只读投影） |

> L4 与 Knowledge Engine 是**索引关系**：Memory 存"指向哪条知识 + 摘要"，Knowledge 存"知识正文"。二者通过 Sync Bridge 保持一致（见 03）。

---

## 3. 单一逻辑来源（Single Logical Source）

- 所有记忆读写汇聚于 `memory.py` 单一入口。
- 上层模块**只**通过 Memory Engine 提供的接口读写，不得直连 `mem_vectors` 或 SQLite。
- 写入产生 `memory:written` 领域事件；订阅方（Knowledge、Surface、Proactive）据此响应。
- 语义检索（L6）是 L5/L7 的**派生索引**，重建索引不得丢失原文。

---

## 4. 事件驱动接口

```text
publish(memory:written {layer, key, op})   → 扇出给 Knowledge / Surface / Proactive
publish(memory:forgot  {layer, key})       → 遗忘触发，审计留痕
subscribe(memory:query  {layer, filter})   → 检索请求（由 Brain 上下文管道发起）
```

- Memory Engine 不主动推送给 LLM；由 Brain 上下文管道显式查询（只读聚合）。
- 遗忘（Forget）必须经 Lifecycle 策略 + Governance 审计，禁止无声删除用户长期事实。

---

## 5. 记忆生命周期状态机

```
 captured ──▶ active ──▶ consolidated ──▶ archived
    │           │            │              │
    └───────────┴────────────┴──▶ forgotten (TTL/策略/显式)
   (任何状态变更 publish memory:state_changed)
```

- **captured**：刚写入，未分类。
- **active**：当前活跃，可被检索。
- **consolidated**：经反思蒸馏，提升为长期/知识。
- **archived**：低频，冷存储但不删除。
- **forgotten**：依策略清理；长期用户事实默认不进 forgotten。

---

## 6. 检索与语义（L6/L8）

- 检索分两路：精确（key/filter）+ 语义（embedding 近似）。
- 嵌入模型本地优先；云端嵌入仅作可选、结果本地缓存。
- 检索结果带**出处溯源**（source ref），可回跳原始会话/知识文件。

---

## 7. 治理与红线

- 禁止第二 Memory 实现；禁止模块直连 `mem_vectors`。
- 遗忘必须审计；长期用户事实默认保留。
- 记忆写入须经 PermissionGuard（高敏感写入如长期画像需用户确认）。

---

## 8. 与 Knowledge Engine 边界

- Memory = "我记得什么"（结构化、机器友好、可检索）。
- Knowledge = "我知道什么"（人类可读、可导航、可链接，见 03）。
- L4 是桥：Memory 引用 Knowledge 条目，而非复制正文。

> 本文档设计目标态；实现由 Memory Sprint 承接，本 Sprint 不写代码。
