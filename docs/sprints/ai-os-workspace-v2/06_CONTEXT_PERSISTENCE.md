# 06 — Context Persistence（活动上下文统一恢复）

> Sprint #622 · Goal / Conversation / Knowledge / Memory / Tool 统一恢复（仅引用 id）。

## 1. 机制

`WorkspaceState.activeContext` 持有五类上下文的**引用 id**：

```js
setActiveContext({ goalId, conversationId, knowledgeNodeId, memoryId, toolName })
```

- 由业务系统在合适时机调用（如对话开始记录 `conversationId`、执行目标记录 `goalId`、打开知识节点记录 `knowledgeNodeId`）。
- 本 Sprint **提供机制 + 接线点**；具体何时写入由既有业务流决定（不新增业务触发逻辑，避免越界）。

## 2. 统一恢复视角

- 刷新后 `WorkspaceState` 恢复 `focusedPanelId` / `pinnedPanelIds` / `recentPanelIds` / `activeContext`。
- UI 层据此重建"工作区视角"：最近面板、固定面板、当前活动上下文高亮。
- 域内容恢复仍由 `AppState`（单一写入口）+ 后端负责；`WorkspaceState` 只提供 UI 索引。

## 3. 接线点（建议，非强制实现）

| 业务事件 | 建议调用 |
|----------|----------|
| 对话新建 / 切换 | `WorkspaceState.setActiveContext({ conversationId })` |
| 目标执行开始 | `WorkspaceState.setActiveContext({ goalId })` |
| 打开知识节点 | `WorkspaceState.setActiveContext({ knowledgeNodeId })` |
| 打开记忆卡片 | `WorkspaceState.setActiveContext({ memoryId })` |
| 工具执行 | `WorkspaceState.setActiveContext({ toolName })` |

> 红线：仅存引用 id，不缓存域数据；不修改 AppState / 后端事件契约。

> 下一步：#623 Workspace Performance（仅 UI）。
