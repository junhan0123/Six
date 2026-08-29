# 04 — Workspace State（UI-only 工作区状态）

> Sprint #620 · Current Workspace / Focused Panel / Active Context / Pinned Panel / Recent Panel。
> 实现：`panel-manager.js` 内 `WorkspaceState`（`window.WorkspaceState`）。

## 1. 数据契约

`localStorage['zz.workspace.v1']`，仅存 UI 工作区状态与**上下文引用 id**：

```json
{
  "workspace": "home",
  "focusedPanelId": null,
  "pinnedPanelIds": [],
  "recentPanelIds": [],
  "activeContext": {
    "goalId": null, "conversationId": null,
    "knowledgeNodeId": null, "memoryId": null, "toolName": null
  }
}
```

- `RECENT_MAX = 8`，`pinned` 上限 32（防御性）。
- `load()` 容错：隐私模式 / 损坏数据静默忽略，回退默认。

## 2. 方法

`load / save / focus / pushRecent / clearFocus / pin / unpin / isPinned / setActiveContext / get / getActiveContext`。

- `focus(id)` → 设 `focusedPanelId` + 推 `recentPanelIds`（去重）。
- `setActiveContext(ctx)` → 合并 `activeContext`（仅引用 id）。

## 3. 红线：不存域数据

- **不存**任何 Memory / Knowledge / Goal / Conversation 内容；只存引用 id。
- 域真相仍归 `AppState`（单一写入口）+ 后端；`WorkspaceState` 是 UI-only 的"工作区视角"缓存。
- 后端 / 数据库结构**零改动**。

## 4. 跨刷新恢复

- `pinnedPanelIds` / `recentPanelIds` / `focusedPanelId` 持久化 → 刷新后工作区视角可恢复。
- 物理面板重开由各自模块负责（pin 视觉经 `_applyPinChrome` 在 `pin()` 时即时打标；持久 pin 的视觉恢复由模块 open 时按需调用 `PanelManager.pin()` 重建，属可选增强，本 Sprint 记录但不强制）。
- `workspace`（当前层）仅记录 Home，不与 body 类双向强绑（避免与既有 nav 脊柱冲突）。

> 下一步：#621 Navigation Consistency（唯一推荐入口）。
