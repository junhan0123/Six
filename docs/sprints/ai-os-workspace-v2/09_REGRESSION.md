# 09 — Regression（回归验证）

> Sprint #625 · 验证：Workspace 唯一状态 / Panel 唯一生命周期 / Navigation 唯一推荐入口 / Overlay 未回退 / Keyboard 未回退 / Companion 职责未扩张 / Capability Exposure 符合 T0–T4 / Architecture 未违反 / Product Constitution 未违反 / Golden State 未违反。

## 1. 验证方法

环境无可用浏览器，采用**静态验证 + 不变量 grep + 人工代码审查**（与 v1.0 验收同口径）：

1. `node --check` 语法校验全部改动 JS（panel-manager / tasks / command-palette / app / memory）。
2. 不变量 grep：确认路由 / 无越界 API / 无后端改动。
3. 人工审查 `panel-manager.js` 设计是否符合纪律。

## 2. 验证结果

| # | 验证项 | 方法 | 结果 |
|---|--------|------|:----:|
| 1 | 全部改动 JS 语法通过 | `node --check` ×5 | ✅ PASS |
| 2 | 面板打开统一经 `openCapability` | grep `PanelManager.openCapability` = 28 处 | ✅ PASS |
| 3 | `panel-manager.js` 无越界调用 | grep `EventBus/AppState/publish/fetch` → 仅注释 | ✅ PASS |
| 4 | OverlayManager API 未改 | grep `getEntry` → ABSENT（复用既有 `getHandle`） | ✅ PASS |
| 5 | 后端 `.py` 未改 | `git status` 无 `.py` 变动 | ✅ PASS |
| 6 | `init()` 包裹不破坏原调用 | `apply(mod, arguments)` 透传参数 | ✅ PASS |
| 7 | Keyboard 未回退 | 无新增全局快捷键；`mod+k` 优先级 1000 不变 | ✅ PASS |
| 8 | Overlay/ESC 未回退 | 浮层仍由 `OverlayManager` 单一掌管 | ✅ PASS |
| 9 | Companion 职责未扩张 | 仅转发 `system-status/memory/settings`，无新命令系统 | ✅ PASS |
| 10 | Capability Exposure 符合 T0–T4 | Command Palette 仍消费 `CapabilityExposure` 档位；本 Sprint 未改其声明 | ✅ PASS |
| 11 | Architecture 未违反 | 单 Runtime / 单状态写入口（AppState）/ 单 EventBus / 单 Permission 均未触碰 | ✅ PASS |
| 12 | Product Constitution 未违反 | 无交互面重叠新增；12 交互面职责不变 | ✅ PASS |
| 13 | Golden State 未违反 | 无新增 Runtime/Memory/Knowledge；Local First 保持 | ✅ PASS |

## 3. 已知限制（非缺陷，记录）

- **共享宿主 `zz-panel`**：weather / briefing / agent-profile 在 OverlayManager 共享同一 `zz-panel` id，`isOpen('weather')` 等对共享宿主面板返回的是宿主状态（任一打开即为 true）。属 v1.0 既有结构，拆分超出 v2.0 范围。
- **持久 pin 视觉恢复**：`pin()` 即时打 `.ws-pinned`；刷新后 persist 的 pin 视觉重建依赖面板 open 时业务侧按需调用 `PanelManager.pin()`（可选增强，本 Sprint 记录机制，未强制业务接线）。
- **无运行时浏览器验收**：静态 + 人工审查通过；建议人工在 GUI 中走查 10 项 Verify。

## 4. 结论

全部 13 项静态验证 PASS，纪律红线零违反。建议人工 GUI 走查确认交互手感。

> 下一步：#626 Documentation（11 份文档 + 最终 5 项输出）。
