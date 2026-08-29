# 05 — Navigation Consistency（唯一推荐入口）

> Sprint #621 · Command Palette / Sidebar / Dock / Companion / Workspace，唯一推荐入口。
> 纪律：Navigation 唯一推荐入口；Overlay / Keyboard / Companion 职责不回退 / 不扩张。

## 1. 入口分层

| 入口 | 角色 | 本 Sprint 处理 |
|------|------|----------------|
| **Command Palette（指令中心）** | 能力的**唯一推荐发现入口** | 10 条面板命令全部改经 `PanelManager.openCapability(id)` |
| **Dock / Sidebar（命令坞 / 侧栏）** | 快捷操作 | `command-dock.js` 已有；其面板触发经统一分发（Tasks 启动器已路由） |
| **Companion** | 伴侣分发（Presentation） | 仅把系统动作转交既有系统，本 Sprint 将其 `memory`/`settings`/`system-status` 改经 `openCapability`；**职责未扩张** |
| **Workspace nav 脊柱（`[data-nav]`）** | 层切换 | 维持既有 body 类切换；`settings`/`command` 仍调 `ZZSettings.open`/`ZZCommandPalette.open`（二者自身经 `init()` 包裹记录状态） |

## 2. 唯一分发器

`PanelManager.openCapability(id, ...args)` 成为所有"程序化打开面板"的单一函数名：

- Command Palette `run:` 回调
- `tasks.js` `launch` map
- `app.js` `handleCompanionAction`（system-status / memory / settings）
- `app.js` `handleToolEvent` `panel` 分支（后端事件驱动）
- `app.js` `openRulePanel`（规则面板）

按钮类入口（`wxOpenBtn` / `btnBriefing` / `hsOpenBtn` / `btnMem` / `settingsOpenBtn`）经 `init()` 绑定 click → `_recordOpen`，且 `openCapability` 对 `btnId` 类也走 `click()`，行为一致。

## 3. 未回退校验

- **Overlay**：仍由 `OverlayManager` 唯一掌管（栈 / 中央 ESC / 焦点 / z-index），无任何散落 `addEventListener('keydown', ESC)` 回潮。
- **Keyboard**：`KeyboardManager` + `CommandPalette` 的 `mod+k` 优先级 1000 不变；本 Sprint 未新增任何全局快捷键。
- **Companion**：仅复用转发，未新增内置命令系统（保持 v1 治理结论）。

> 下一步：#622 Context Persistence（活动上下文统一恢复）。
