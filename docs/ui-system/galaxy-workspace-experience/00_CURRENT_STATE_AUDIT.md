# 00 · 当前状态审计（Current-State Audit）
### Xiao6 UI-3B · Galaxy × Workspace Experience Design v1.0

> **阶段**：UI-3B · Design Only（0 代码改动）· 仅审计真实现状 + 落盘设计
> **纪律**：不修改 CSS/HTML/JS/Three.js/solar-system.js/Galaxy renderer/Backend/Agent/EventBus；不 commit
> **审计方法**：逐文件读盘（file:line 证据），不依赖旧设计文档假设
> **生成日期**：2026-08-09

---

## 0. 审计范围与证据来源（真实文件）

| 类别 | 文件 | 角色 |
|---|---|---|
| 设计解释层（冻结） | `docs/design/frozen/GALAXY_INTERACTION_SPEC.md` | DECISION_004 银河边界 |
| 既有布局设计 | `docs/ui-system/unified-visual-architecture/01_GLOBAL_LAYOUT_ARCHITECTURE.md` | 七大 Surface 角色 |
| 既有融合设计 | `docs/ui-system/unified-visual-architecture/02_GALAXY_WORKSPACE_INTEGRATION.md` | Dual-Layer 方案 C（推荐） |
| 银河渲染器（冻结） | `xiao6-ui/solar-system.js` | 真实 NASA 贴图太阳系，z-index 0 |
| 银河数据层 | `xiao6-ui/galaxy-state.js` | AppState → 节点投影（只读） |
| 银河运行时 | `xiao6-ui/galaxy-runtime.js` | 节点 → 渲染模型（纯数据） |
| 银河体验层（overlay） | `xiao6-ui/galaxy-experience.js` | gx-status/gx-card，受控交互 |
| 统一输入 | `xiao6-ui/command-dock.js` | 五合一 Command Dock |
| 面板系统 | `xiao6-ui/panel-manager.js` | 18 面板生命周期 + WorkspaceState |
| AI 在场 | `xiao6-ui/avatar-state.js` | 8 态纯函数派生（投影） |
| 主结构 | `xiao6-ui/index.html` | osShell / app / universeView / 路由 |

---

## 1. 真实结构：三大顶层 Surface + 导航脊柱

`index.html` 实际存在 **三个互斥的顶层 Surface**，由 `document.body` 上的 class 切换（硬模式切换，非连续调节）：

```
<body>
 ├─ <canvas#solarCanvas>          z-index:0   银河世界层（唯一全屏背景）  [index.html:62]
 ├─ <div.galaxy-veil>             叙事纱（universe 模式淡出）              [index.html:64]
 │
 ├─ <section#osShell.os-shell>    【Surface A · OS Home】默认态           [index.html:67]
 │     · 导航脊柱 os-nav（home/workspace/command/galaxy/assistant/settings）[index.html:70-81]
 │     · HUD os-hud（品牌/状态点/主题/时钟）                            [index.html:83-105]
 │     · 中央 os-core（osCoreCanvas 意识核心 + os-hero 水印徽章）          [index.html:108-122]
 │     · 右栏 os-side（Capability Matrix + Insight 抽屉）                [index.html:125-134]
 │     · 底部 os-bottom（Execution Timeline + Command Dock #osDock）       [index.html:137-146]
 │
 ├─ <div#app.app>                【Surface B · Workspace/Chat】chat-mode  [index.html:246]
 │     · 左 rail（语音球/快捷能力/会话/状态 pill）                       [index.html:248-304]
 │     · 主区 main（HUD 条 + chat-area + #input 文本域 + #btnSend）       [index.html:307-375]
 │     · 右 tele 遥测面板                                          [index.html:378+]
 │
 └─ <div#universeView>           【Surface C · 宇宙视图】universe-mode     [index.html:150]
       · gx-status / gx-card / gx-hint（Galaxy Experience Layer）         [index.html:152-168]
       · 这是唯一让银河成为「主角」的 Surface
```

**路由逻辑（硬切换）**——`index.html:1440-1519`：
- `openChat()` → `body.chat-mode` + 移除 `universe-mode`（`index.html:1454`）
- `openUniverse()` → `body.universe-mode` + `#universeView.open`（`index.html:1461`）
- `syncNav()`：由 body class 推导当前视图（`home`/`workspace`/`command`/`galaxy`/`settings`），`index.html:1484-1493`
- Galaxy 导航按钮 `data-nav="galaxy"` → `closeChat(); openUniverse()`（`index.html:1508-1509`）

> **关键证据**：进入 Workspace（chat-mode）会**主动移除** universe-mode → 银河世界层被 `.app`（z-index:2）完全遮盖（`solar-system.js:335` 注释明确：`.app(z-index:2)` 遮盖 `#solarCanvas(z-index:0)`）。

---

## 2. 各 Surface 真实承担的角色

### 2.1 Galaxy（#solarCanvas + solar-system.js）—— 真实承担
| 维度 | 真实状态（file:line） |
|---|---|
| 渲染 | 真实 NASA/ESA 贴图太阳系：太阳+8 行星+月球+土星环+星空+星云+流星；真实自转/公转/轴向倾角（`solar-system.js:30-47, 211-291`） |
| 交互 | 拖拽旋转 / 滚轮缩放 / 点击聚焦 / ESC 退出（`solar-system.js:338-417`）；聚焦经 `_publishFocus` 写 AppState 事件契约（`solar-system.js:610-621`，DECISION_004 合规） |
| 状态投影 | 仅渲染**占位中性色**状态节点（Goal→Planet/Agent→Satellite/Task→Orbit/Memory→Archive/Knowledge→Link），**无状态→颜色/Glow 映射**（Order 8 未做，`solar-system.js:545-593, 562`） |
| 当前可见性 | ① Home：暗化背景，中央被 os-core+hero 覆盖，仅边缘空白可交互；② Workspace：**完全被 .app 遮盖，不可见**；③ Universe 视图：唯一主角，但属**独立视图** |
| 本质 | **背景 / 状态空间 / 数据投影**，但**不是贯穿全局的「世界层」**——它会在 Workspace 模式下消失 |

### 2.2 Workspace（#app.app + #input）—— 真实承担
| 维度 | 真实状态（file:line） |
|---|---|
| 主体 | 经典 Chat 布局：左 rail（会话/快捷）+ 主区（对话历史 + 输入坞）+ 右 tele（工作日志）（`index.html:246-380`） |
| 输入 | `#input` 文本域 + `#btnSend`（`index.html:368, 370`）——**这才是真正的发送入口** |
| 与 Dock 关系 | Command Dock（Home 的 #osDock）发送时**借道** legacy 输入：`inputEl.value=text; btn.click()`（`command-dock.js:17-24`）—— 两条输入通道靠 JS 桥接，视觉语法不同 |
| 本质 | 是 **AI Operating Surface（聊天/指令执行台）**，但被实现为**覆盖银河的独立全屏界面** |

### 2.3 Command Dock（#osDock，command-dock.js）—— 真实承担
- 五合一输入（文本/语音/文件/截图/快捷），但**仅存在于 Home 的 #osDock**（`command-dock.js:26-80`，`index.html:142-144`）。
- 文本发送 → 写入 legacy `#input` 并点击 `#btnSend`（`command-dock.js:17-24`）。
- 快捷 → 唤起 Command Palette（`command-dock.js:58-61`）。
- **注意**：进入 Workspace（chat-mode）后，Dock 不可见，输入回落到 legacy `#input`。即 Dock **非永驻**。

### 2.4 Panel System（panel-manager.js）—— 真实承担
- 18 个面板注册表（`panel-manager.js:91-109`），经 `OverlayManager`（唯一浮层栈）打开，z-index 60-83/90/9000。
- `openCapability(id)` 是唯一入口分发器（`panel-manager.js:166-182`）。
- `WorkspaceState` 仅存 UI 工作区状态（当前 workspace/聚焦面板/固定/最近/activeContext 引用）（`panel-manager.js:21-81`）。
- 面板是**上下文抽屉**，浮于所有 Surface 之上（`--z-panel` ~81）。

### 2.5 AI Presence（avatar-state.js + companion）—— 真实承担
- `AvatarState.deriveFromGlobals()` 纯函数，读 AppState + ExecutionChannel + ZZSSE，`--z-companion`(9999) 最高层（`avatar-state.js:65-176, 9999`）。
- 8 态（IDLE/WAITING/THINKING/PLANNING/EXECUTING/COMPLETED/ERROR/OFFLINE），纯投影、不持有状态、不写状态。
- **常驻所有模式**（Companion 化身独立于三大 Surface）。

---

## 3. 交互流程与用户进入路径

**默认启动（无显式路由）→ `home` 态**（osShell 可见，chat-mode/universe-mode 均不挂）：
1. 抵达：银河暗化常驻于后；HUD 就位；os-hero 水印徽章；Command Dock 待命（index.html:67-146）。
2. 输入指令：在 #osDock 输入 → 桥接到 #input → 点击 Workspace 进入执行（实际触发 `openChat` 类切换）。
3. 看银河：点击导航 `galaxy` 或 `Ctrl/Cmd+U` → `universe-mode`，#universeView 全屏，银河成主角（index.html:1508-1509, 1461-1467）。
4. 进功能：左 rail 快捷 / 右栏矩阵 / Command Palette（`Ctrl/Cmd+K`）/ 点击银河行星（`_enterCapability` 经 PanelManager 打开 capabilities 面板）打开 Panel（overlay 浮层）。
5. 返回空间：`Esc` 或再次 `Ctrl/Cmd+U` 关闭 universe 视图 → 回到 home/workspace。

**割裂的本质**：用户的「进入 Workspace」= 切换到一个**遮盖银河的全屏 Chat**；「看银河」= 切换到一个**独立的宇宙视图**。二者是两套互斥页面，而非同一空间的注意力调节。

---

## 4. 当前割裂点（Split Points，带证据）

| # | 割裂点 | 证据 | 后果 |
|---|---|---|---|
| S1 | **Workspace 遮盖银河** | `.app` z-index:2 盖 `#solarCanvas`(z:0)；`openChat` 移除 `universe-mode`（`index.html:246, 1454`；`solar-system.js:335`） | 工作时银河完全消失 → 用户心智里「Galaxy=另一个地方」 |
| S2 | **银河是独立宇宙视图（硬切换）** | `#universeView` + `universe-mode`（`index.html:150, 1461`）；`_enterCapability` 主动 `universeView.classList.remove('open')` 回工作台（`galaxy-experience.js:58-61`） | 看银河 = 离开工作；桥接逻辑主动切断二者 |
| S3 | **两套输入语法** | Home 用 #osDock（`command-dock.js`），Workspace 用 legacy #input（`index.html:368`）；Dock 借道 `#input.value+btn.click()`（`command-dock.js:17-24`） | 视觉/位置不一致；Dock 在 Workspace 下不可见 |
| S4 | **三个顶层布局语法不同** | osShell（hero+matrix+insight）/ app（rail+chat+tele）/ universeView（gx-*）三套结构（`index.html:67, 246, 150`） | 用户当成 3 个「页面」，无「一个 AI 空间」连续感 |
| S5 | **状态节点无状态色** | `solar-system.js:562` 固定 `0x88aaff` 中性色（Order 8 未做） | 即便在宇宙视图，银河也「看起来像普通太阳系」，削弱「AI OS 世界层」感知 |
| S6 | **中央双视觉争抢** | os-core 自带 `osCoreCanvas` 意识核心（`index.html:109`）与银河争中央焦点 | 银河的「世界中心」身份被稀释 |
| S7 | **Dock 非永驻** | #osDock 仅在 osShell；chat-mode 下仅 legacy #input（`index.html:144, 368`） | 「统一主入口」承诺未兑现于 Workspace |

---

## 5. 回答两个核心问题（审计结论）

**Q：当前 Galaxy 实际承担什么？**
→ 它是**带真实天体物理的「状态空间 / 数据投影」背景**：在 Home 是暗化氛围背景，在 Universe 视图是独立探索界面，在 Workspace 下**不可见**。它「投影」但不「承载」操作；是 AI 世界的可视化，却未被当作贯穿全局的「世界层」。

**Q：当前 Workspace 实际承担什么？**
→ 它是**经典 Chat / 指令执行台（AI Operating Surface）**，被实现为覆盖银河的全屏界面。它承担对话、指令执行、遥测，但语法与银河完全不同，且通过 `chat-mode` 主动遮蔽银河。它更像「第二个 App」而非「同一空间的操作台」。

---

## 6. 必须回答的 7 问（现状基线 + UI-3B 目标应答）

| # | 问题 | **现状（审计基线）** | **UI-3B 目标（见 01–05）** |
|---|---|---|---|
| 1 | 打开小6默认看到什么？ | Home：银河暗化背景 + os-hero 水印 + Capability Matrix + Command Dock | 同一：Galaxy 暗化常驻世界层 + 前景操作台（见 03） |
| 2 | 何时看到 Galaxy？ | 仅 Home 边缘 / 进入 Universe 视图（Ctrl/Cmd+U） | **始终在场**；暗化常驻，聚焦时提亮（连续注意力，非硬切） |
| 3 | 何时进入 Workspace？ | 点导航 workspace/输入指令 → chat-mode 遮盖银河 | 输入即在工作台；**银河不消失**，仅退为暗化世界层 |
| 4 | Command Dock 是否永驻？ | 否；仅 Home，Workspace 下用 legacy #input | **是**；统一主入口贯穿所有态（Home/Workspace，非 Universe 独占） |
| 5 | Panel 如何浮现？ | OverlayManager 浮层（z 60-83/90/9000），经 PanelManager | 不变；Panel 为上下文抽屉浮于世界层之上 |
| 6 | AI Presence 在哪个层？ | `--z-companion`(9999) 常驻所有模式 | 不变；最高层常驻，两个 Surface 之上 |
| 7 | 如何避免信息过载？ | 割裂反而造成「找功能要在页面间跳」 | 单一连续空间 + 注意力模型 + 信息层级收口（见 01/04） |

---

## 7. 审计对 UI-3B 的约束

1. **目标不是新建 Galaxy/Workspace，而是消除 S1/S2 的「硬切换」**——把银河从「被遮盖的背景 / 独立视图」改为「始终在场的连续世界层」。
2. **绝不触碰 solar-system.js 本体**（L0 红线-5 + DECISION_004）。世界层可见性/提亮**仅经前景 CSS（玻璃透明度/遮罩/亮度调节）+ body class 注意力态**实现，属表现层。
3. **状态节点配色（Order 8）属 renderer 改动**，UI-3B 不提议；可在 UI 后续阶段作为专项评估（不违反「不改本体视觉资产」的前提下仅改动态节点着色，需单独纪律审查）。
4. **Dock 永驻** = 让其脱离 Home 独占，成为贯穿前景操作台的常驻元件（CSS/JS 路由调整，非新建体系）。
5. **面板系统 / AI Presence / 事件契约 / AppState 写入口均不动**（Single Source Rule）。

> **🛑 STOP 声明**：本章为纯审计（读盘 + 落盘），0 代码改动，待 Review 后进入 01–05 设计。
