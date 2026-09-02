# 03 — Panel Governance（统一生命周期管理器）

> Sprint #619 · Open / Close / Hide / Restore / Focus / Pin / Unpin / Collapse / Expand 走统一管理器。
> 实现文件：`xiao6-ui/panel-manager.js`（`window.PanelManager` + `window.WorkspaceState`）。

## 1. 设计原则

- **复用，不重建**：生命周期的浮层物理行为（DOM 开关 / ESC / 焦点 / z-index）仍由 `OverlayManager` 负责；`PanelManager` 只统一**语义状态**与**入口分发**。
- **包裹，不重写**：`init()` 在 `DOMContentLoaded`（bootOS）时包裹各 `ZZ*` 模块的 `open`/`close`，使所有既有调用点自动记录工作区状态，无需逐个改调用。
- **UI-only**：不引入业务状态、不写 Runtime、不碰 EventBus / Permission / Capability Registry。

## 2. 注册表（REG）

`id → { module, openName, overlayId, modeClass, btnId, host }`，覆盖 17 个面板（weather / briefing / memory / ai-memory / memory-query / settings / hotspot / sysmon / terminal / doc / map / capabilities / sysprompt / review / video / tasks / agent-profile）。

- `module + openName`：程序化入口，`init()` 包裹以记录状态。
- `overlayId`：在 OverlayManager 栈中的 id（`isOpen` / `close` / pin 视觉）。
- `modeClass`：以 body class 表达的面板模式（sysmon / terminal）。
- `btnId`：以按钮点击驱动的入口（天气 / 简报等无 `ZZ` 全局者）。
- `host: true`：复用共享 `#zzPanel` 宿主（天气 / 简报 / agent-profile）。

## 3. 生命周期 API

| 方法 | 语义 |
|------|------|
| `open(id)` / `openCapability(id, ...args)` | 唯一入口分发器；`btnId` 走 `click()`，否则 `module[openName](...args)` |
| `close(id)` | 优先 `module.close()`，否则 `OverlayManager.close(overlayId)`，否则移除 `modeClass` |
| `hide(id)` | 语义等同 close（模态/独占型面板） |
| `restore(id)` | 重新打开（固定面板恢复） |
| `focus(id)` | 记录 focusedPanelId + 推入 recent |
| `pin(id)` / `unpin(id)` / `togglePin(id)` | 持久固定 + 打 `.ws-pinned` 视觉标记 |
| `collapse(id, region)` / `expand(id, region)` | 折叠区域切换（交面板注册区） |
| `toggle(id)` | open/close 切换 |
| `isOpen(id)` / `isPinned(id)` / `isCollapsed(id, region)` | 查询 |
| `focused()` / `pinned()` / `recent(n)` / `list()` / `getState()` | 状态读取 |
| `closeAll()` | 关闭全部已开面板 + `OverlayManager.closeAll()` |
| `registerCollapse(id, region, opts)` | 面板把折叠区交给管理器，自身不再存工作区状态 |

## 4. Pin 视觉标记

`_applyPinChrome` 经 `OverlayManager.getHandle(overlayId).el`（`getHandle` 为 v1 既有 API，返回 `{id, el, dialog, close}`）给面板 DOM 打 `.ws-pinned` 类；CSS（`styles.css`）加 `.ws-pinned { outline: 2px solid var(--accent); outline-offset: -2px; }`。纯视觉，不引入行为。

## 5. Collapse 迁移实例（memory.js）

```js
// 注册（模块加载时）
PanelManager.registerCollapse('memory', 'side',   { el: () => document.getElementById('memSide'),    cls: 'collapsed' });
PanelManager.registerCollapse('memory', 'outline',{ el: () => document.getElementById('memOutline'), cls: 'collapsed' });
// 点击切换
$('#memSideToggle').onclick = function () {
  var c = window.PanelManager ? PanelManager.collapse('memory','side') : !(state.sideCollapsed = !state.sideCollapsed);
  if (!window.PanelManager) sideEl.classList.toggle('collapsed', state.sideCollapsed);
  state.sideCollapsed = c;
  $('#memSideToggle').classList.toggle('on', c);
};
```

→ 面板不再自存 `sideCollapsed` / `outlineCollapsed` 工作区状态；折叠态统一归 `WorkspaceState`。

## 6. 红线自查

- ✅ 未新建第二套浮层栈 / ESC / 焦点（复用 OverlayManager / FocusManager）。
- ✅ 未触碰域层（Memory / Knowledge / Planner / Workflow / Permission / EventBus）。
- ✅ `init()` 包裹为纯函数包装，零业务逻辑变更。

> 下一步：#620 Workspace State（UI-only 工作区状态）。
