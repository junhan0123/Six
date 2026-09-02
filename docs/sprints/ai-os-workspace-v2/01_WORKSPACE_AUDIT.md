# 01 — Workspace Audit（Workspace Inventory）

> Sprint #617 · 扫描全部 Panel / Sidebar / Overlay / Floating UI / Workspace，输出 Workspace Inventory。
> 方法：只读静态审计 + grep 全仓事实核对（非凭记忆）。所有 file:line 为审计时真实位置。

## 1. 审计范围

前端 `xiao6-ui/` 全部 vanilla JS / CSS / HTML。确认**无统一 PanelManager / WorkspaceState**（仅 `app-state` / `events` / `tests` 出现 "workspace" 字样，且为业务域状态，非 UI 工作区）。

## 2. 浮层（Overlay）清单 — 20 个经 OverlayManager.track 注册

| # | 文件 | id | OverlayType | 备注 |
|---|------|-----|-------------|------|
| 1 | app.js | `modal-mask` | MODAL | keepZIndex（9000 高位） |
| 2 | app.js | `briefing` | PANEL | 共享宿主 `#zzPanel` |
| 3 | app.js | `zz-panel` | PANEL | **共享宿主**（weather/briefing/agent-profile 复用） |
| 4 | capabilities-view.js | `capabilities-view` | PANEL | |
| 5 | command-palette.js | `command-palette` | COMMAND | keepZIndex（90 高位） |
| 6 | companion.js | `companion-bubble` | MENU | Companion 层（独立治理） |
| 7 | companion.js | `companion-cmdBubble` | MENU | Companion 层 |
| 8 | companion.js | `companion-menu` | MENU | keepZIndex |
| 9 | doc.js | `doc` | PANEL | |
| 10 | hotspot.js | `hotspot-region` | DIALOG | hotspot 子浮层 |
| 11 | hotspot.js | `hotspot` | PANEL | |
| 12 | map.js | `map` | PANEL | |
| 13 | memory-panel.js | `memory` | PANEL | `window.ZZMemory` |
| 14 | memory-query.js | `memory-query` | PANEL | |
| 15 | memory.js | `jz-memory` | PANEL | `window.JZMemory`（id 已从 `memory` 改为 `jz-memory`，规避冲突） |
| 16 | review.js | `review` | PANEL | |
| 17 | settings.js | `settings` | PANEL | |
| 18 | sysprompt.js | `sysprompt` | PANEL | |
| 19 | tasks.js | `zz-task` | PANEL | |
| 20 | video.js | `video` | PANEL | |

**结论：** OverlayManager（v1.0 已建）已统一浮层栈 / 中央 ESC / 焦点 / z-index；本 Sprint **复用，不重建**。

## 3. 面板模块全局（window.ZZ* / window.JZ*）

| 全局 | 文件 | 性质 | 纳入 WorkspaceState REG |
|------|------|------|:---:|
| `ZZHotspot` | hotspot.js | 热点面板 | ✅ `hotspot` |
| `ZZDoc` | doc.js | 文档库 | ✅ `doc` |
| `ZZMap` | map.js | 地图 | ✅ `map` |
| `ZZMemory` | memory-panel.js | 记忆网络 | ✅ `ai-memory` |
| `ZZMemoryQuery` | memory-query.js | 长期记忆查询 | ✅ `memory-query` |
| `JZMemory` | memory.js | 记忆（笔记/图谱） | ✅ `memory` |
| `ZZReview` | review.js | 复盘 | ✅ `review` |
| `ZZSettings` | settings.js | 设置 | ✅ `settings` |
| `ZZSysmon` | sysmon.js | 系统监控 | ✅ `sysmon`（body-mode） |
| `ZZTerminal` | terminal-stream.js | 终端日志 | ✅ `terminal`（body-mode） |
| `ZZSysPrompt` | sysprompt.js | 系统提示词 | ✅ `sysprompt` |
| `ZZCapabilities` | capabilities-view.js | 能力矩阵 | ✅ `capabilities` |
| `ZZVideo` | video.js | 视频 | ✅ `video` |
| `ZZTasks` | tasks.js | 任务启动器 | ✅ `tasks` |
| `ZZPanel` | app.js | 共享宿主 `openAgentProfile` | ✅ `agent-profile` |
| — | app.js | `weather` / `briefing`（按钮驱动） | ✅ `weather` / `briefing` |
| `ZZCommandPalette` | command-palette.js | 指令中心（入口本身） | ➖ 非面板 |
| `ZZChat` / `ZZVoice` / `ZZModal` / `ZZSSE` / `ZZAvatarScene` / `ZZHudRing` / `ZZGlance` / `ZZKws` / `ZZUserProfile` | — | 非 Workspace 面板 | ➖ 不纳入 |

**明确排除（不纳入 REG）：**
- `companion-bubble` / `companion-cmdBubble` / `companion-menu` —— Companion 为独立 Presentation 层，受 Sprint v1 治理约束，职责**不得扩张**。
- `modal-mask` / `hotspot-region` —— 模态遮罩 / 子对话框，非 Workspace 面板。

## 4. 两个面板范式并存

| 范式 | 机制 | 复用面板 |
|------|------|----------|
| **共享宿主** | `#zzPanel`（index.html），`openZZPanel({title,subtitle,html})` 注入内容 | weather / briefing / agent-profile |
| **独立面板** | 各自 DOM + 各自 `window.ZZ*` 全局 + 各自 `OverlayManager.track` | 其余 14 个 |

→ 共享宿主导致 `weather/briefing/agent-profile` 在 OverlayManager 中共享同一 `zz-panel` id（已知限制，文档化，不强行拆分——拆分属重构 Runtime/UI 结构，超出 v2.0 范围）。

## 5. 面板自管状态（已迁移）

- `memory.js`：`state.sideCollapsed` / `state.outlineCollapsed` 自行 `classList.toggle('collapsed')`，未走统一管理器 → **已迁移至 `PanelManager.registerCollapse('memory','side'|'outline')`**，面板不再自存工作区状态。
- `capabilities-view.js`：`state.expanded` Set 自管 expand → 维持（能力树展开属域视图状态，非工作区持久态，不在本 Sprint 收口范围）。

## 6. 入口散落（已收口）

| 来源 | 原写法 | 现收口 |
|------|--------|--------|
| 按钮 | index.html `wxOpenBtn` / `btnBriefing` / `hsOpenBtn` / `btnMem` / `settingsOpenBtn` | `PanelManager.init()` 绑定 click → `_recordOpen`；`openCapability` 经 `btn.click()` |
| Command Palette | `command-palette.js` `run: () => window.ZZ*.open()` | `run: () => PanelManager.openCapability(id)`（10 条面板命令） |
| Tasks 启动器 | `tasks.js` `launch` map | `PanelManager.openCapability(id)` |
| Companion 桥 | `app.js` `handleCompanionAction` | `PanelManager.openCapability('sysmon'|'ai-memory'|'settings')` |
| 后端事件 | `app.js` `handleToolEvent` `panel` 分支 | `PanelManager.openCapability(id, ...args)` |
| 规则面板 | `app.js` `openRulePanel` | `PanelManager.openCapability(id)` |
| 全局 | `app.js` `window.ZZMemory.open` 等 | `init()` 包裹 `ZZ*` open/close → 统一记录状态 |

## 7. 重复 UI（来自 Capability Platform Duplicate Report，D1–D11）

- Toast 5+ 重复 → v1.0 已收敛至 `OverlayManager.toast()`（本 Sprint 不重复处理）。
- Overlay 12+ 重复 → v1.0 已统一至 `OverlayManager` + `zz-overlay` 原语。
- 能力视图三源同源（UI-13）→ `capability-matrix.js` 消费 `CapabilityExposure` 单一真相。
- 侧弹面板重复（UI-06）→ 本 Sprint 经 `PanelManager` 统一生命周期收口。

## 8. 审计结论 → 设计

前端缺**统一 UI 收口层**。据此建立：

- **`panel-manager.js`**（`window.PanelManager` + `window.WorkspaceState`）：统一生命周期 + UI-only 工作区状态；复用 OverlayManager / FocusManager / KeyboardManager / CapabilityExposure，不触碰域层。
- 不新建 Runtime / 状态写入口 / 权限 / 事件；WorkspaceState 仅存引用 id（goalId / conversationId / knowledgeNodeId / memoryId / toolName），域真相仍归 AppState（单一写入口）。

> 下一步：#618 Workspace Layout（六层信息架构）。
