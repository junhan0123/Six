# 03 — Knowledge Engine（知识引擎 · Obsidian 知识层）

> 依赖：01（分层 L6）、02（Memory L4 索引关系）
> 核心断言：**知识层不是数据库**。Obsidian Vault 是人类可读知识真相源。

---

## 1. 设计哲学

个人 AI OS 的知识应当是**人类可读、可导航、可链接、可拥有**的。把知识塞进 SQLite/向量库等于把用户锁进黑箱。

因此：
- **Vault（.md 文件）** = 知识组织层（人类可读 + 双向链接 + 图谱）。
- **SQLite + `mem_vectors`** = 持久化与检索后端（机器索引，派生）。
- **Sync Bridge** = 一致性机制（机器↔Vault 双向，人类编辑优先）。

---

## 2. 架构三件套

```
┌─────────────────────────────────────────────┐
│  Obsidian Vault（知识真相源）                  │
│  daily/ project/ inbox/ archive/ people/ ...  │
│  [[wikilinks]]  #tags  graph                  │
└───────────────┬─────────────────────────────┘
                │ Sync Bridge（人类编辑优先）
┌───────────────▼─────────────────────────────┐
│  Backend（派生索引）                           │
│  SQLite（元数据/关系） + mem_vectors（嵌入）   │
└───────────────┬─────────────────────────────┘
                │ 查询接口
┌───────────────▼─────────────────────────────┐
│  Knowledge Engine API（检索/写入建议/图谱）    │
└─────────────────────────────────────────────┘
```

---

## 3. Vault 结构约定

| 文件夹 | 用途 |
|--------|------|
| `daily/` | 每日笔记，自动捕获当日洞察 |
| `project/` | 项目知识库，按项目分文件 |
| `inbox/` | 待整理捕获（Quick Capture） |
| `archive/` | 冷知识归档 |
| `people/` | 人物/实体知识卡 |
| `concepts/` | 概念/主题知识卡 |
| `index.md` | MOC（Map of Content）导航 |

- 链接：`[[wikilink]]`；标签：`#area/subtag`；图谱：Obsidian Graph 视图。
- **禁止在 SQLite 内重造链接/标签/图谱**——这些是 Vault 的天然能力，Backend 仅镜像。

---

## 4. Sync Bridge（一致性机制）

- **人类编辑优先**：用户在 Obsidian 中手写/修改，机器不得覆盖。
- **机器写入建议**：AI 生成的知识作为"建议"落入 `inbox/`，经用户确认后进入正式 Vault。
- **双向索引同步**：Vault 文件变更 → Backend 重建元数据/向量；Backend 索引变更（如合并） → 仅更新索引，不改写正文。
- 冲突策略：人类正文永远胜出；索引冲突以 Vault 为准重建。

---

## 5. RAG + Embedding

- 检索链路：用户问题 → Brain 上下文管道 → Knowledge Engine 查询。
- 向量嵌入本地优先；云端嵌入可选且结果本地缓存。
- 返回结果带 `source: vault/path.md` 溯源，可一键在 Obsidian 打开。
- 图谱检索：支持"相关概念""反向链接"导航式检索，不止向量近似。

---

## 6. 知识生命周期

```
 captured(inbox) ─▶ reviewed ─▶ linked(concepts/people) ─▶ consolidated
                                                              │
                                                          archived(冷)
```

- 机器不自动删除知识；归档/清理由用户或 Lifecycle 策略（经确认）执行。
- 知识可被 Memory L4 引用（索引），二者经 Sync Bridge 一致。

---

## 7. 与 Memory 边界（重申）

- Knowledge = 人类可读知识（Vault 文件）。
- Memory L4 = 指向 Knowledge 的索引 + 摘要（SQLite）。
- 机器索引是派生；正文唯一真相在 Vault。

---

## 8. 红线

- 禁止在 SQLite/向量库内重建链接/标签/图谱。
- 禁止机器覆盖人类手写 Vault 正文。
- 全部 Vault 本地优先；云端同步（若启用）须经用户授权且不改变本地真相源地位。

> 目标态设计；实现由 Knowledge Sprint 承接，本 Sprint 不写代码。
