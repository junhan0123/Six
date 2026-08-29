# KNOWLEDGE_OBSIDIAN_BRIDGE_REPORT

> Stage F — Obsidian Bridge。生成时间：2026-08-06。
> 原则：**单一事实源 = `knowledge/` 下的 .md 文件**；Obsidian 与 Knowledge Runtime 读写同一批文件，无复制、无双写、无同步守护进程。

## 1. 桥接架构

```
        ┌─────────────────────────────────────────────┐
        │   G:/xiao6/knowledge/   (单一事实源)      │
        │   index.md + 7 域 + daily/inbox/archive        │
        └───────────────┬─────────────────┬────────────┘
              读/写(人)  │                 │ 读/写(机)
                        ▼                 ▼
                Obsidian 编辑器      Knowledge Runtime
                (人工维护 frontmatter │ (engine.py: load/reload/
                 与正文, wikilink)    │  search/related/ingest)
                        │                 │
                        │  文件系统变更      │
                        └───────┬─────────┘
                                ▼
                    Watcher (ReadDirectoryChangesW)
                    event-driven, debounce 0.4s → rt.reload()
```

- **Obsidian** 直接把 `knowledge/` 作为 Vault 打开（不是副本）。人工编辑 frontmatter / 正文 / `[[wikilink]]`。
- **Knowledge Runtime** 是唯一的机器读写入口（`knowledge.*`）。所有 Agent / Workflow / Planner / Memory Builder 经它访问知识，不直接读 markdown。
- **Watcher** 监听 `knowledge/` 的文件系统事件：Obsidian 改文件 → 事件 → 防抖 0.4s → `rt.reload()` → 索引实时刷新。反向：Runtime 写文件（ingest/archive/delete）→ 文件变更 → Obsidian 下次渲染即见。

## 2. 关键实现（位置）

| 关注点 | 文件 | 说明 |
|--------|------|------|
| 事件驱动监听 | `xiao6-ui/knowledge_runtime/watcher.py` | Windows `ReadDirectoryChangesW`，daemon 线程，无轮询；非 win32 降级为 no-op |
| 索引重建 | `engine.py: reload()` | 扫描 + 重建 resolver/searcher/graph + 重写 manifest |
| Vault 设置 | `knowledge/.obsidian/app.json` | `newLinkFormat=shortest`、`alwaysUpdateLinks=true`、`useMarkdownLinks=false` 等 |
| 扫描排除 | `engine.py: _iter_markdown()` | 跳过 `.obsidian` 与 `.trash` 目录，跳过 manifest 文件 |
| Manifest 位置 | `engine.py: __init__()` | **侧卡** `G:/xiao6/knowledge_manifest.json`（在 vault 之外） |

## 3. 本轮修复的两个桥接隐患

1. **Reload Storm（已修复）**：原先 manifest 写在 `knowledge/` 内部，Watcher 会把它自己的 manifest 写入当成变更 → 触发 reload → 再写 manifest → 无限 reload 风暴（长驻 Electron 进程空转）。
   **修复**：manifest 改为 vault 的**侧卡文件** `knowledge_manifest.json`（在 `knowledge/` 之外），Watcher 永不会因 runtime 自身写入而触发 reload。同时更贴合「`knowledge_manifest.json` 由 Runtime 自动生成、非人工维护」的约定。
2. **`.trash` 误扫（已修复）**：Obsidian 删除笔记会移入 `.trash/`，原扫描会把这些无 frontmatter 的碎片当成 doc（可能破约）。**修复**：`_iter_markdown` 显式跳过 `.trash`（与 `.obsidian` 一并）。

## 4. 冒烟测试结果（PASS）

脚本：`scripts/test_watcher_bridge.py`（使用项目 Python 3.11 + pyyaml 6.0.3）。

| 步骤 | 预期 | 结果 |
|------|------|------|
| 基线节点数 | 46 | 46 ✅ |
| 外部新建 .md（模拟 Obsidian 创建） | +1 → 47 | OK ✅ |
| 外部删除 .md（模拟 Obsidian 删除） | −1 → 46 | OK ✅ |
| Runtime `ingest_document` 写路径 | 文档存在 | OK ✅ |
| 结束后无残留探针文件 | 46 | OK ✅ |

Watcher 全程 `watcher_active=True`，事件驱动、无轮询。

## 5. 使用方式

1. Obsidian → Open Folder as Vault → 选择 `G:/xiao6/knowledge`。
2. 正常编辑笔记；frontmatter 字段见 `KNOWLEDGE_SCHEMA.md`（`id/type/title/status/created/updated/source` + 可选 `tags/links/related_knowledge`）。
3. 用 `[[标题]]` 建立链接；Resolver 按 `title/id/alias` 解析。
4. 保存后无需手动操作 —— Runtime 经 Watcher 自动重建索引。

## 6. 注意事项 / 红线

- **单一事实源**：不要在 `knowledge/` 之外维护知识副本；所有机器访问经 `knowledge.*`。
- **Local First**：无云同步、无网络；Obsidian 同步（如有）由用户自行配置，不影响 Runtime。
- **不破约**：新增/修改笔记请带合法 `type`（与目录一致）与 `status`；详见 `KNOWLEDGE_VALIDATION_REPORT.md` 的契约。
- **不要在 Obsidian 中手动编辑** `knowledge_manifest.json` 或 `.obsidian/` 内部（前者由 Runtime 自动维护，后者为 Obsidian 私有）。
- 红线全程未触碰：无 RAG / 嵌入 / 数据库 / 向量库；未改 memory / planner / workflow / agent / llm。
