# 08 — Workspace UX Polish（统一体验打磨）

> Sprint #624 · Loading / Empty / Skeleton / Transition / Focus / Animation / Spacing / Typography / Icon / Color。

## 1. 立场：复用既有 Design System，不重新发明

小6前端已有完整的统一语言（UI Foundation Sprint + Component System Sprint + Motion System + Icon System + Design Token 收口），本 Sprint **不重建**，只确保 Workspace 面板一致消费：

- **Token**：所有面板继续用 `--accent` / `--motion-*` / `--z-*` 等设计令牌。
- **Motion**：开关过渡沿用 `OverlayManager` 的 `--motion-base` / `--motion-fast` 与 `zzPanelFlashIn/Out` 动画。
- **Icon**：统一 `zz-icon` SVG sprite（`<use href="#zz-*"/>`），Command Palette 面板命令的 `hint` 已改用同一套图标。

## 2. 本 Sprint 新增的打磨点

| 项 | 落地 |
|----|------|
| **Pin 视觉一致性** | 新增 `.ws-pinned { outline: 2px solid var(--accent); outline-offset: -2px; }`，固定面板获得统一可识别标记（来自 `PanelManager._applyPinChrome`） |
| **入口文案一致** | Command Palette 面板命令统一为"打开 / 查询"动词前缀，分类标注 External/System/Proactive/Knowledge/Memory/Settings |
| **折叠态一致** | `memory.js` 侧栏 / 大纲折叠改经 `PanelManager.collapse`，与其他面板折叠交互统一 |
| **关闭全部一致** | "关闭所有面板"指令改经 `PanelManager.closeAll()`（叠加既有 body-mode 清理），行为更完整（覆盖 OverlayManager 栈内全部面板） |

## 3. 未做（防越界 / 留待专项）

- 各面板的 Empty / Skeleton / Loading 态属面板自身 UI，不在 v2.0 统一范围；如需统一应在 Component System Sprint 后续推进。
- 不新增 toast 变体（Toast 已在 v1.0 收敛至 `OverlayManager.toast()`）。

> 下一步：#625 Regression（回归验证）。
