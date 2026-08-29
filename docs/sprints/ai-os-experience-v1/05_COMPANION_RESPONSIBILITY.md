# 05 · Companion Responsibility Matrix（Sprint 5 落地）

## 1. 设计目标（对应 06 §12 交互面唯一职责 / 03 §体验六态）

Companion（桌宠 / 常驻 AI 副驾表面）职责收口为**纯 AI 职责面**，移除设置入口 / 系统菜单 / 页面导航 / 非 AI 状态展示。

## 2. 职责矩阵

| 职责 | 载体 | 类别 | 决策 | 改动 |
|------|------|------|------|------|
| 对话（对小6说） | `cmd-bubble` 命令气泡 | AI | **保留** | — |
| AI 状态（头像/徽标/提示） | `badge`/`tip`/状态机 | AI | **保留** | — |
| 当前 AI 任务 | `current-task` 菜单项 | AI | **保留** | — |
| AI 建议 | `statusBubble`（showBubble） | AI | **保留** | — |
| AI 主动提醒 | `notify`（showNotification） | AI | **保留** | — |
| AI 执行反馈 | `notify` done/error | AI | **保留** | — |
| 就地下达指令 | `quick-cmd` 菜单项 | AI | **保留** | — |
| 暂停动画（本地呈现） | `toggle-pause` | 本地呈现 | **保留** | — |
| 勿扰（AI 提醒策略） | `toggle-dnd` | AI 策略 | **保留** | — |
| 隐藏小6（本地） | `hide` | 本地 | **保留** | — |
| **打开小6（页面导航）** | `open-main` 菜单项 | 页面导航 | **移除** | 删 HTML + handleAction 分支 |
| **系统状态（非 AI）** | `system-status` 菜单项 | 非 AI 状态 | **移除** | 删 HTML + handleAction 分支 |
| **记忆（页面导航）** | `memory` 菜单项 | 页面导航 | **移除** | 删 HTML + handleAction 分支 |
| **项目状态（页面导航）** | `project` 菜单项 | 页面导航 | **移除** | 删 HTML + handleAction 分支 |
| **设置（设置入口）** | `settings` 菜单项 | 设置入口 | **移除** | 删 HTML + handleAction 分支 |

## 3. 已实施代码改动

- `companion.html`：从 `#quickMenu` 删除 5 个非 AI 按钮（`open-main` / `system-status` / `memory` / `project` / `settings`）。
- `companion.js` `handleAction`：从系统动作 `switch` 删除对应分支，仅保留 `current-task` / `quick-cmd`（经 `bridge.action`）。
- 注释说明收口原因：页面导航 / 非 AI 状态 / 设置入口统一交 **Command Palette / 导航脊柱**（06 §统一通道）。

## 4. 保留职责链路（未被触动）

- `showBubble` / `hideBubble`（AI 建议）—— 仍经 `OverlayManager.track('companion-bubble')`。
- `showNotification` / `hideNotification`（主动提醒/执行反馈）—— 走 notify，不受本次改动影响。
- `openCmdBubble` / `closeCmdBubble`（对话）—— 仍经 `OverlayManager.track('companion-cmdBubble')`。
- `toggleMenu` / `hideMenu`（菜单）—— 仅剩 AI 项，仍经 `OverlayManager.track('companion-menu')`。
- 双击头像打开主窗（`openMain` via `bridge.show`）保留：作为对话表面入口，非"系统菜单/页面导航"项。

## 5. 待 Review 的边界项（未自动删除，需人工裁定）

- `open-main`（双击头像）是否视为"页面导航"？当前保留为对话入口；若架构判定应完全移除 Companion 的窗口导航，可后续收敛。
- `current-task` / `quick-cmd` 经 `bridge.action` 转发主窗既有系统——属 AI 任务/指令，保留；其下游实现未改动。
- 全局快捷键 `Ctrl+,`（设置）、`Ctrl+N`（新对话）仍在 `app.js` 旧监听——属全局快捷，非 Companion 职责，不在本 Sprint 范围（可后续统一迁 KeyboardManager）。

## 6. 验证点

- ✅ Companion 现在只暴露 AI 职责（对话/状态/建议/主动提醒/执行反馈）+ 本地呈现控制。
- ✅ 设置/系统状态/记忆/项目导航入口已移出 Companion，交 Command Palette / 导航脊柱。
- ✅ 无新增能力；仅移除非 AI 职责（符合"禁新增业务能力"红线，且为 Sprint 5 显式授权）。
