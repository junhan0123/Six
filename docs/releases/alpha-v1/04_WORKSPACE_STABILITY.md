# 04 · Workspace Stability Audit — AI OS Alpha Stabilization Program v1.0

- **阶段**：Phase 3（Workspace 稳定性审计）
- **日期**：2026-08-06
- **身份**：Senior QA Architect + Senior Product Architect + Senior UX Engineer
- **纪律**：仅审计 + 文档；不修改任何代码（修复统一留在 P6）。红线与允许范围见 `00_PREFLIGHT_AUDIT.md`。
- **方法**：静态通读 4 个 Workspace 支柱源码，交叉比对 `panel-manager.js` 的 `REG` 注册表 id 与全仓 `OverlayManager.track(...)` 真实注册 id，并核对 `index.html` 启动时序。

---

## 1. 审计对象

| 支柱 | 文件 | 职责 |
|---|---|---|
| 面板生命周期 / WorkspaceState | `panel-manager.js`（290 行） | 17 面板注册表 `REG`、`openCapability` 唯一分发器、`WorkspaceState`（UI-only 持久化） |
| 浮层栈 / 中央 ESC / 焦点 / Toast | `overlay-manager.js`（525 行） | 唯一浮层栈、z-index 递增、中央 ESC、焦点陷阱、Toast 统一 |
| 焦点陷阱 / 恢复 | `focus-manager.js`（132 行） | Tab 循环陷阱、关闭焦点恢复、`backgroundInert`（opt-in） |
| 键盘路由 | `keyboard-manager.js`（73 行） | 全局快捷键中央路由、Command Palette 最高优先级、ESC 所有权留 OverlayManager |

---

## 2. 静态审计结论（逐支柱）

### 2.1 启动时序 ✅ PASS（关键红线之一）
- `panel-manager.js` 经 `<script src>` 在 `index.html:1439` 加载，定义 `window.PanelManager` / `window.WorkspaceState`。
- `PanelManager.init()` 唯一调用点在 `index.html:1312`，位于 `bootOS()` 内；`bootOS()` 经过 `if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bootOS)`（`:1435-1436`）**延迟到 DOMContentLoaded 执行**。
- `DOMContentLoaded` 在全部解析阻塞型脚本（含 `panel-manager.js:1439`、`app.js:1440`）执行后触发，故 `init()` 运行时 `window.PanelManager` 已定义。
- **结论**：`WorkspaceState.load()` 在启动期正确执行 → 持久化的 `workspace / pinnedPanelIds / recentPanelIds / activeContext` 被恢复；且首次 `save()` 不会用默认值覆盖已加载字段（无“持久化被清空”回归）。**持久化链路完好。**

### 2.2 模块 open/close 包裹 + 按钮入口 ✅ PASS
- `init()` 对 `REG` 中 `module && !btnId` 的面板包裹 `openName`/`close`，统一经 `_recordOpen/_recordClose` 写入 `WorkspaceState`（focus + recency）。
- 按钮驱动入口（`wxOpenBtn/btnBriefing/hsOpenBtn/btnMem/settingsOpenBtn`）在 `init()` 内绑定点击记录。
- 经核对 14/17 面板 `overlayId` 与真实 `OverlayManager.track(...)` 一致（见 §3 表），`isOpen/close` 对模块面板行为正确。

### 2.3 OverlayManager（浮层栈 / ESC / 焦点 / z-index）✅ PASS
- 单一浮层栈 `stack`；多实例按 `BASE_Z + depth*Z_STEP` 递增 z-index，`BASE_Z` 运行时读取 `--z-dialog-mask` 令牌（单一来源），无第二套数值。
- 中央 ESC：栈空时完全休眠（不拦截 keydown，遗留 18+ 去中心化 ESC 照常）；栈非空时 capture 阶段关闭栈顶并 `stopPropagation`，逻辑正确。
- 焦点：打开保存 `returnFocus`、关闭恢复；委托 `FocusManager.trap`，无则降级 `focusDialog`。
- 外部浮层（`track`）保留自身 DOM，仅把 ESC/焦点/栈/z-index 交给 OverlayManager —— 与“复用唯一浮层栈，不重建第二套”纪律一致。**无第二 Overlay 系统。**

### 2.4 FocusManager ✅ PASS
- `trap/release` 闭环正确；`visibleFocusable` 跳过 `aria-hidden`；`backgroundInert` 默认关闭（opt-in，规避嵌套包装层误伤整棵应用），符合 v2.0 设计约束。无业务逻辑、不触碰 AppState/EventBus/后端。

### 2.5 KeyboardManager ✅ PASS
- 全局快捷键中央路由，按 `priority` 降序分发；Command Palette 注册 `priority:1000`（Capture Top），保证任意上下文 `Ctrl/Cmd+K` 可用。
- ESC 所有权明确留在 OverlayManager（本模块不重复处理 ESC），与 `06 §2` 一致。无重复 handler、无业务泄漏。

---

## 3. REG ↔ OverlayManager.track 交叉比对（核心发现）

| REG id | REG.overlayId | 真实 `track(...)` id | 一致？ | 备注 |
|---|---|---|---|---|
| weather | `zz-panel` | **无 track**（body-class `weather-mode` + `#weather-panel`） | ❌ | 见 F6 |
| briefing | `zz-panel` | `briefing`（`app.js:1655`） | ❌ | 见 F6 |
| memory | `jz-memory` | `jz-memory`（`memory.js:578`） | ✅ | |
| ai-memory | `memory` | `memory`（`memory-panel.js:190`） | ✅ | |
| memory-query | `memory-query` | `memory-query`（`memory-query.js:123`） | ✅ | |
| settings | `settings` | `settings`（`settings.js:119`） | ✅ | |
| hotspot | `hotspot` | `hotspot`（`hotspot.js:704`） | ✅ | |
| sysmon | `sysmon-mode`(modeClass) | body-class 切换（`sysmon.js:208`） | ✅ | modeClass 路径 |
| terminal | `term-mode`(modeClass) | body-class 切换（`terminal-stream.js:62`） | ✅ | modeClass 路径 |
| doc | `doc` | `doc`（`doc.js:136`） | ✅ | |
| map | `map` | `map`（`map.js:120`） | ✅ | |
| capabilities | `capabilities-view` | `capabilities-view`（`capabilities-view.js:24`） | ✅ | |
| sysprompt | `sysprompt` | `sysprompt`（`sysprompt.js:19`） | ✅ | |
| review | `review` | `review`（`review.js:49`） | ✅ | |
| video | `video` | `video`（`video.js:68`） | ✅ | |
| tasks | `zz-task` | `zz-task`（`tasks.js:69`） | ✅ | |
| agent-profile | `zz-panel` | `zz-panel`（`app.js:2230`） | ✅ | **唯一真正使用 `zz-panel` 的面板** |

---

## 4. 发现（Findings）

### F6 · DEFECT（中危，Workspace 一致性）— 建议 P6 修复
`weather` 与 `briefing` 在 `REG` 中声明 `overlayId: 'zz-panel', host: true`，但二者**都不真正使用 `zz-panel` 浮层**：
- **weather**：实际经 `weather.js` 切换 `document.body` 的 `weather-mode` 类 + `#weather-panel`（`aria-hidden`）显示，从不调用 `OverlayManager.track`。`#weather-panel` 与 agent-profile 的 `#zzPanel` 是**不同 DOM 节点**——所谓“共享 `zz-panel` 容器”对 weather 不成立。
- **briefing**：实际 `OverlayManager.track('briefing', ...)`（`app.js:1655`），id 为 `'briefing'`，与 REG 的 `'zz-panel'` 不符。

**后果**：
1. `PanelManager.isOpen('briefing')` 永远返回 `false`（查的是 `OverlayManager.isOpen('zz-panel')`）—— 任何依赖该判断的逻辑失效。
2. `PanelManager.isOpen('weather')` 在 **agent-profile（`zz-panel`）打开时返回 `true`**（误报），造成状态歧义。
3. `PanelManager.closeAll()`（`command-palette.js:101` 指令中心“关闭所有面板”）遍历 `REG`：对 briefing/weather，`isOpen` 为 false（或误判后 close 路径无 overlayId 命中）→ **`closeAll` 无法关闭已打开的 briefing/weather**，与用户“关闭全部”预期不符。

**根因**：v2.0 `REG` 表从“共享宿主”设想残留了 `host:true, overlayId:'zz-panel'`，但 weather/briefing 各自走了独立实现路径，注册表未随之更新。

**修复方向（P6，单行配置级，零行为新增）**：
- `weather`：`{ btnId: 'wxOpenBtn' }`（移除错误的 `overlayId:'zz-panel', host:true`）。
- `briefing`：`{ btnId: 'btnBriefing', overlayId: 'briefing' }`（将 `zz-panel` 改为真实 `briefing`）。
- `agent-profile`：保持不变（唯一正确的 `zz-panel` 使用者）。

**Release Gate 影响**：Gate 3「Workspace 未回退」——核心 15 个模块面板稳定，但此 latent 缺陷削弱 `closeAll` 正确性。属**既有配置缺陷**（非本次稳定化引入的回归），建议在 P6 修复；修复后 Gate 3 完全满足。

### F7 · MINOR（已知未接线）— 不阻塞
`PanelManager.pin/togglePin/unpin` 全仓**无任何 UI 消费者**调用（仅定义于 `panel-manager.js`）。`WorkspaceState.pinnedPanelIds` 永不被填充，`_applyPinChrome` 的 `ws-pinned` 类也不会出现。即“固定面板”为死功能。建议：要么在 P6 接线（属于“体验修复”允许范围），要么在文档中标注为未启用，避免用户预期落空。当前不阻塞 Alpha 每日使用。

### F8 · MINOR（持久化缺口）— 不阻塞
`registerCollapse` 仅 `memory.js:630-631` 用于记忆面板侧栏/大纲折叠；但折叠状态存于 `panel-manager.js` 模块级 `_collapseState`，**未并入 `WorkspaceState.data`**，而 `collapse/expand` 调用的 `WorkspaceState.save()` 并不序列化 `_collapseState`。故刷新后折叠状态不恢复。影响面极小（仅记忆面板折叠），不阻塞。

### F9 · INFO（R1 共享宿主歧义已部分实证）
P1 报告 R1 担忧“weather/briefing/agent-profile 共享 `zz-panel` 导致 `isOpen` 歧义”。实测：仅 `agent-profile` 真正 track `zz-panel`；weather 用独立 `#weather-panel`+body-class，briefing 用独立 `#briefingOverlay`+`briefing` id。**共享宿主设想未完全落地**，这正是 F6 的根因。无新增回归。

---

## 5. Workspace 稳定性裁决

- **无功能回归**：15 个模块面板的 `REG↔track` 一致性、启动持久化、中央 ESC/焦点/键盘路由均与 v2.0 终报承诺一致，未见稳定化工作引入的回退。
- **1 项既有 latent 缺陷**（F6）：`closeAll` 无法关闭 weather/briefing。非本次引入，但影响“关闭所有面板”正确性，建议 P6 修复。
- **2 项 minor**（F7 pin 死功能 / F8 折叠不持久化）：不阻塞 Alpha 每日使用。

**Release Gate 条件 3（Workspace 未回退）：PARTIAL → 修复 F6 后 FULL。** 核心 Workspace 稳定；F6 修复成本低、风险低，列入 P5 修复清单与 P6 执行。

---

## 6. 下一步
- **P4**：能力体验审计（`docs/releases/alpha-v1/05_CAPABILITY_EXPERIENCE_AUDIT.md`）。
- **P5**：UX Bug Bash —— 建立修复清单（F6 为主项，F7 可选），**仅列不修**。
- **P6**：允许修复 —— 应用 F6（REG 配置修正），重启 8011 后端做回归（含 `closeAll` 含 briefing/weather 的场景）。
- 注：P2 已定位的 🔴 P0（`tools.py:3286` 对话工具 `allowed` 位置参数错误）独立于 Workspace，在 P6 一并修复并回归。
