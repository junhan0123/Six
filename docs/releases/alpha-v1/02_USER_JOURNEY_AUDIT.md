# 02 · Phase 1 — End-to-End User Journey Audit（端到端用户旅程审计）

> 专项：AI OS Alpha Stabilization Program v1.0
> 阶段：Phase 1 End-to-End User Journey Audit
> 方法：静态审计 + 代码级模拟（无浏览器运行时；运行时验收由 P2/P3 与服务端 smoke 补充）
> 日期：2026-08-06
> 纪律：纯审计/观察；零代码改动。

---

## 1. 审计方法

- 真实重读 `index.html`（脚本加载顺序 + 入口按钮 + 面板容器）。
- 精读两个核心入口面：`command-palette.js`（指令中心，317 行）、`companion.js`（伴侣）。
- 比对 `panel-manager.js` 的 `REG`（17 面板注册表）与各入口 `openCapability('...')` 调用一致性。
- 脚本比对：全仓 `window.ZZ*/JZ*` 全局定义 vs 各入口面引用，找出未定义引用。
- 全量 `node --check *.js` 语法扫描。
- 核查核心每日旅程（对话发送、伴侣动作）接线。

---

## 2. 用户旅程地图（已映射）

| 旅程 | 入口 | 路径 | 静态结论 |
|------|------|------|----------|
| 启动 | 浏览器 `http://:8000` | `index.html` → 顺序加载（panel-manager 在 app.js 前）→ `app.js bootOS` | ✅ 加载顺序正确 |
| 对话（核心） | Chat 输入框 / 发送按钮 | `btnSend.click → send()`；`input.keydown → send()`；`send()` → `fetch('/api/chat')` | ✅ 接线完整 |
| 打开面板（指令） | Ctrl/Cmd+K | `command-palette.js` → `PanelManager.openCapability(id)` → `REG[id].module.open()` | ✅ 入口统一 |
| 打开面板（伴侣） | Companion 菜单 | `app.js handleCompanionAction` → `openCapability('ai-memory'/'sysmon'/'settings')` | ✅ |
| 打开面板（按钮） | Dock/顶栏按钮 | `wxOpenBtn/btnBriefing/hsOpenBtn/btnMem/settingsOpenBtn` → `openCapability`/模块 | ✅ |
| 打开面板（后端事件） | 工具回包 `panel` 事件 | `app.js handleToolEvent` → `openCapability` | ✅ |
| 设置 | 设置面板 | `openCapability('settings')` → `ZZSettings` | ✅ |
| 自然语言意图 | 指令中心 Agent 段 | `ZZIntentGateway.dispatch` → `POST /api/agent/intent` | ✅（定义于 `global.ZZIntentGateway`，浏览器等价 window） |
| 伴侣常驻/勿扰/暂停 | Companion | `toggle-pause/toggle-dnd/hide/cmd-bubble` + `CREATE_GOAL` | ✅ |
| 关闭所有面板 | 指令中心 | `closeAllPanels` → `PanelManager.closeAll()` | ✅ |

---

## 3. 静态验证结论（全部 PASS）

| 检查项 | 结果 |
|--------|------|
| `panel-manager.js` 在 `app.js` 前加载 | ✅ index.html:1439 早于 1440 |
| 各入口 `openCapability(id)` 调用均有对应 `REG` 条目 | ✅ 17 面板全覆盖 |
| 入口面引用的 `window.ZZ*/JZ*` 全局均有定义 | ✅ 仅 `ZZIntentGateway` 初判未匹配，经查为 `global.ZZIntentGateway = API`（浏览器等价），实际有效 |
| 全量 `node --check *.js` | ✅ 全部语法 OK，无静默失败脚本 |
| 对话发送链路 | ✅ `btnSend`/`input` 均接线 `send()` |
| 伴侣动作映射 | ✅ 本地处理 + `CREATE_GOAL` 事件完整 |

---

## 4. 关键澄清（避免误报）

**"记忆面板"非缺陷**：初查 `REG['memory'].module='JZMemory'` 疑似拼写错误，深查证实：
- `JZMemory` 是 `memory.js` 中真实定义的独立模块（`window.JZMemory = {open,close,refresh,openNote}`）；
- `btnMem`（title=“长期记忆”）点击 → `app.js:1848 window.JZMemory.open()` → 打开"长期记忆"面板；
- `ZZMemory`（`memory-panel.js`）是另一面板"记忆网络"，经 `openCapability('ai-memory')` 打开；
- 两者为不同能力，注册/接线均正确，**非 P0 缺陷**。

---

## 5. 残留风险（需 P2/P3/P5 运行时验证）

静态审计无法替代浏览器运行时。以下为需在 P2/P3/P5 重点验证的已知点（来自 Workspace v2 终报 + Capability 审计）：

| # | 风险 | 来源 | 验证阶段 |
|---|------|------|----------|
| R1 | 共享宿主 `zz-panel` 状态歧义：weather/briefing/agent-profile 共享 overlay id `zz-panel`，`isOpen` 返回宿主态 | Workspace v2 终报 | P3 |
| R2 | 提示通道未完全收口：Toast 5+ 重复系统，可能提醒刷屏（违背打断预算） | Capability 05_DUPLICATE | P5 |
| R3 | 无浏览器运行时验收：静态+人工审查 PASS，缺真实 GUI 走查 | Workspace v2 终报 | P3/P9 |
| R4 | 持久 pin 视觉未接线：`open` 完成未调 `PanelManager.pin` 重建 `.ws-pinned` | Workspace v2 终报 | P6（允许修复） |
| R5 | ESC/焦点集中化：须确认无 18+ 去中心化 Esc 监听残留 | 交互宪法 §4 | P5 |
| R6 | 后端每日链路（/api/chat/health/config/intent）真实可用性 | 需服务端 smoke | P2 |

---

## 6. Phase 1 结论

✅ **静态端到端旅程审计 PASS**：启动顺序、统一入口（`openCapability`）、全局模块定义、对话发送、伴侣动作全部接线完整，无指向未定义模块的硬断裂入口，无语法错误。

⏳ **运行时验收待 P2/P3**：Release Gate 条件 8（User Journey 无 P0）需真实 GUI 走查；本阶段已穷尽静态可验证项，残留风险（R1–R6）转入 P2/P3/P5。

**进入 Phase 2：Daily Workflow Simulation（每日工作流模拟）。**
