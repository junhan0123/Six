# 04 · 交互流程设计（Interaction Flow）
### Xiao6 UI-3B · Galaxy × Workspace Experience Design v1.0

> **阶段**：UI-3B · Design Only（0 代码改动）
> **上游**：`03_FIRST_SCREEN_DESIGN.md`（第一屏布局）· `02_GALAXY_WORKSPACE_RELATION.md`（Dual-Layer + 注意力模型）· `01_EXPERIENCE_MODEL.md`（7 问应答）· `00_CURRENT_STATE_AUDIT.md`（S1-S7）
> **生成日期**：2026-08-09

---

## 0. 设计目标

交互是连接「世界层（Galaxy）」与「操作层（Workspace）」的**结缔组织**。本文件定义五大核心流的端到端行为——**输入任务 / 查看执行 / 查看状态 / 进入功能 / 返回空间**——并回答一个前提问题：**用户如何在这两层之间移动注意力**。

所有流的设计约束（继承自 00/01/02）：
- Galaxy = World Layer，绝不持有可写状态；任何交互经受控层（galaxy-experience.js）。
- 单一连续空间，无 surface 硬切换（修正 S1/S2）。
- 单入口、单输入语法（修正 S3/S7）。

---

## 1. 五大核心交互流总览

| 流 | 起点 | 终点 | 注意力态 | 修正的割裂点 |
|---|---|---|---|---|
| 输入任务 | Command Dock（永驻）/ 直接点选 | 后端执行 | 操作态（常驻） | S3 双语法 / S7 Dock 非永驻 |
| 查看执行 | 操作态 | Execution Timeline + HUD 状态点 | 操作态 | S1 银河消失 |
| 查看状态 | 操作态 / 探索态 | Galaxy 状态节点 + AI Presence | 操作态↔探索态 | S5 无状态色 |
| 进入功能 | 点银河星球 / 直接调用 | PanelManager 浮层 | 操作态（浮层叠加） | S2 独立宇宙视图 |
| 返回空间 | 浮层 / 探索态 | 操作态（银河仍在场） | 操作态 | S2 独占页面 |

---

## 2. 流一 · 输入任务（Input Task）

### 2.1 现状（00 审计 S3 / S7）
- 两套输入语法：Home 走 `#osDockBar`（command-dock.js:26-36），Workspace 走 legacy `#input`/`#btnSend`（index.html:368-370）——同一句话要换入口。
- Command Dock 仅在 Home 的 `#osShell` 内（`index.html:137-146`），进入 Workspace（`#app`, chat-mode）后消失（S7）。

### 2.2 UI-3B 目标流
```
[用户] → Command Dock（永驻底部）→ 文本/语音/文件/截图/快捷
        → command-dock.js sendText() → inp.value=text; btn.click()
        → legacy #input / #btnSend（index.html:368-370）
        → 后端 agnes_completion / 执行链路
```
- **Dock 永驻所有 surface**（修正 S7）：无论操作态还是探索态，底部 Dock 常驻可达；探索态下可半透明退后但不消失。
- **单输入语法**（修正 S3）：银河内的受控交互（点星球展开面板）与 Dock 文本输入，共享同一命令语言与同一后端入口，不存在「银河里说一套、Dock 里说一套」。

### 2.3 注意力态
保持**操作态**。输入是操作层行为，不触发银河亮度变化。

---

### 2.4 Command Dock 语义冻结（# Global AI Intent Entry）

> **🔒 FROZEN DEFINITION**：Command Dock = `# Global AI Intent Entry`（全局 AI 意图入口）。

Command Dock **不是**：
- ❌ **Chat Input（聊天输入框）**——它不是「发一句话等回复」的对话框。
- ❌ **Search Box（搜索框）**——它不是「检索知识库/文件」的查询栏。

Command Dock **是**：
- ✅ **Intent → Goal → Execution 的统一入口**：用户在此表达意图（Intent），系统将其解析为可执行目标（Goal），并进入执行（Execution）。
- 五种输入模态（文本/语音/文件/截图/快捷）共享同一语义：**「我要让小6去做一件事」**，而非「我要聊一句」或「我要搜一下」。
- 与银河受控交互（点星球）共享同一命令语言与同一后端入口（继承 §2.2 单输入语法）。
- 探索态下可半透明退后但仍可达（继承 §2.2）。

**为何不是 Chat/Search**：小6是 AI OS，不是聊天 App，也不是搜索引擎。把 Dock 定义为「意图入口」而非「对话/搜索入口」，是为了避免用户在心智上把它降级为「又一个输入框」，从而保住「我在指挥一个 AI 世界」的操作层主入口定位（对应 01 R3 单入口原则）。

---

## 3. 流二 · 查看执行（View Execution）

### 3.1 现状（00 审计 S1）
- Execution Timeline 位于 `#osShell` 底部（`index.html:137-146`），Workspace 下被 `#app` 遮盖，执行进度不可见。

### 3.2 UI-3B 目标流
```
[执行中] → ExecutionChannel / eventbus → Execution Timeline（操作层底部，永驻）
        → HUD 状态点（IDLE/THINKING/EXECUTING/...，avatar-state.js 派生）
        → Companion 化身（--z-companion 9999，非阻塞）
```
- 执行进度在操作层底部**常驻可见**，不依赖银河是否被遮盖（修正 S1）。
- 空闲时 Timeline 折叠（低密度），有任务时展开。
- 状态来自 AvatarState 单一派生（`avatar-state.js`），HUD 与 Companion 同源显示。

### 3.3 注意力态
保持**操作态**。执行反馈是操作层的职责，银河仅作世界背景。

---

## 4. 流三 · 查看状态（View State）

### 4.1 现状（00 审计 S5）
- Galaxy 状态节点 `syncState()` 固定 `color: 0x88aaff` 占位中性色（solar-system.js:562），**无状态→颜色映射**（Order 8 未做）。
- GalaxyState 为只读投影（galaxy-state.js `pull()`），数据链正确但视觉未着色。

### 4.2 UI-3B 目标流
```
[用户想了解世界] → 银河状态节点（占位色→未来 Order 8 真实色）
                 → 点节点 → galaxy-experience.js gx-card（聚焦信息卡）
                 → AI Presence HUD / Companion（当前 AI 态）
```
- 节点信息**仅在聚焦时出现**（gx-card，galaxy-experience.js:77-123），不常驻标签噪声。
- 状态数据来自 GalaxyState 只读投影，**银河绝不写 AppState**（DECISION_004）。
- 着色（Order 8）列为 Phase C 可选专项（见 05），本流不依赖着色即可成立。

### 4.3 注意力态
可从操作态**平滑过渡到探索态**——当用户主动关注世界时，银河提亮、操作层退后（连续缓动，非硬切）。触发方式见 §7。

---

## 5. 流四 · 进入功能（Enter Capability）

### 5.1 现状（00 审计 S2）
- 点银河星球 → `closeChat(); openUniverse()`（index.html:1508-1509）→ 切到独立 `#universeView`（universe-mode），银河变成独占「宇宙视图」页面，离开操作层。

### 5.2 UI-3B 目标流
```
[用户] → 点银河星球（受控层）
       → galaxy-experience.js _enterCapability(kind)
       → PanelManager.openCapability('capabilities')（panel-manager.js:166-182）
       → OverlayManager 浮层（z 60-83 / 90 / 9000）
       → 银河仍在背后暗化常驻
```
- **不再切到独立宇宙视图**（修正 S2）：进入功能 = 在操作层浮起面板，银河作为世界背景持续在场。
- 唯一入口 = `PanelManager.openCapability(id)`（panel-manager.js 单分发器），复用现有 OverlayManager。
- `_enterCapability` 内 `universeView.classList.remove('open')` 回工作台（galaxy-experience.js:50-61）逻辑保留但**不再触发 universe-mode 独占**。

### 5.3 注意力态
保持**操作态**，面板为操作层之上的浮层叠加；银河退至背景但仍可见（非消失）。

---

## 6. 流五 · 返回空间（Return to Space）

### 6.1 现状（00 审计 S2）
- 从 `#universeView` 返回需导航脊柱切换 `body.universe-mode`，是页面级硬切。

### 6.2 UI-3B 目标流
```
[用户] → ESC / 点击浮层外 / 关闭按钮
       → OverlayManager 关闭当前浮层
       → 回到操作态，银河仍在场（无页面跳转）
```
- 返回 = 关闭浮层，**不存在「离开银河」的概念**——银河始终在场。
- `syncNav()`（index.html:1484-1493）不再做 surface 互斥推导；body class 仅控制主题/态，不控制银河可见性。

### 6.3 注意力态
回到**操作态**，银河暗化常驻（与进入前一致）。

---

## 7. 探索态切换（Attention Transition）

### 7.1 核心修正
现状「探索态」被错实现为硬切换的 `#universeView`（universe-mode）。UI-3B 将其降级为**对世界层的连续亮度 + 操作层透明度调节**（02 重评估结论）。

### 7.2 触发方式（待 UI-4 实现抉择，列出候选）
| 候选 | 描述 | 风险 |
|---|---|---|
| A. 点击银河背景空白区 | 直觉、零新增控件 | 易误触 |
| B. 专用「探索」控件（Dock/HUD） | 可控、可发现 | 新增入口 |
| C. 滚轮/缩放下钻 | 自然 3D 交互 | 与 OS 滚动冲突 |

> 设计层仅定义「连续缓动、非硬切、银河提亮~80% + 操作层退后」的目标态；具体触发控件由 UI-4 按 UX 决策选定（推荐 B 或 A+B 组合）。

### 7.3 过渡特征
- 亮度/透明度用 UI-A P7 已定义的 Motion Token 缓动（无新增体系）。
- 操作态↔探索态之间**无 surface class 切换**，仅 CSS 变量（亮度/透明度）插值。

---

## 8. 导航脊柱与全局快捷键（Navigation Spine）

- `syncNav()`（index.html:1484-1493）简化为：body class 仅表达态（theme / focus），**不再互斥 surface**（银河在所有态可见）。
- 全局快捷键：ESC = 关闭浮层 / 返回操作态（统一，沿用 OverlayManager）。
- 无「进入 Workspace」「进入 Universe」的硬切换动词；词汇统一为「聚焦 / 展开 / 返回」。

---

## 9. 跨流一致性（Cross-flow Consistency）

1. **单输入语法**：Dock 文本与银河受控交互共享命令语言（S3）。
2. **单状态源**：AI Presence 来自 AvatarState 派生；Galaxy 状态来自 GalaxyState 只读投影；二者均不写 AppState。
3. **Galaxy 永不持有可写状态**：所有银河交互经 `galaxy-experience.js` 受控层，状态→颜色属 Order 8 渲染层（C 专项），不触碰 AppState 写入口。
4. **单一连续空间**：五大流均无页面跳转，仅 z 层叠加与亮度插值。

---

## 10. 7 问 · 交互应答汇总

| # | 问题 | 交互应答（来自本文件） |
|---|---|---|
| ① | 默认看到什么 | 操作态第一屏：银河暗化 + 工作台 + Dock 永驻（03） |
| ② | 何时看到 Galaxy | 所有态常驻；探索态提亮（§7） |
| ③ | 何时进入 Workspace | 启动即在工作台，无「进入」动作（03/§6） |
| ④ | Command Dock 永驻？ | 是，所有 surface 底部常驻（§2.2） |
| ⑤ | Panel 如何浮现 | PanelManager 浮层叠加，银河在背后（§5） |
| ⑥ | AI Presence 在哪层 | 两层同源：HUD 状态点 + Companion 化身（§3.2） |
| ⑦ | 如何避免过载 | 低密度默认 + 聚焦才现信息卡 + 银河无标签噪声（§4.2/03 §2.5） |

---

## 11. 合规自检（DECISION_004 / L0 红线）

- [x] Galaxy 绝不直接写 AppState（所有交互经 galaxy-experience.js 受控层）
- [x] solar-system.js 本体渲染/状态语义未被要求改动（着色属 Phase C 可选，仍在 DECISION_004 边界）
- [x] 无新增事件合约（DOMAIN=71/SYSTEM=8 未扩张）
- [x] 无新增 Runtime/Memory/Permission/Design System
- [x] 后端 server.py 零改动（纯前端表现层）
- [x] 0 代码改动（本文件为设计）

---

## 12. UI-4 实现验收点（交互流）

- [ ] 任一 surface 下 Dock 永驻可达
- [ ] 银河交互与 Dock 共享命令语言（后端同入口）
- [ ] 执行进度在操作层底部常驻可见（不依赖银河）
- [ ] 点银河星球 = PanelManager 浮层，不切 #universeView
- [ ] ESC 关闭浮层回到操作态，无页面跳转
- [ ] 探索态为连续亮度/透明度缓动，非 body class 硬切
- [ ] AI Presence 在 HUD + Companion 同源显示

---

## 13. Panel Lifecycle Model（面板生命周期）

面板（Panel）是操作层之上的浮层。为守住「AI OS 世界感」与「注意力预算」（01 §7），面板遵循**三态生命周期**，而非「打开/关闭」二元：

| 态 | 视觉表现 | 用户触发 | 信息密度 |
|---|---|---|---|
| **Dormant（休眠）** | 完全不可见；仅作为银河节点或 Dock 快捷的潜在可能，不占 z 层、不占注意力 | 系统默认态（无用户动作） | 0（零） |
| **Attention（唤起）** | 半透明/缩略/标题态浮现（如右栏抽屉展开提示、PanelManager 预开预览）；占据一个 Secondary Focus | 用户主动：点银河星球 / 快捷键 / Dock 快捷 / 右栏入口 | 中（仅标题 + 关键数，不铺开全文） |
| **Active（激活）** | 完全展开为操作层浮层（OverlayManager z 60-83/90/9000）；占据 Primary Focus；银河退至暗化背景仍在场 | 用户从 Attention 态进一步聚焦（点击展开/确认/双击） | 高（完整内容，但受 Attention Budget 约束：任一时刻仅 1 Primary + ≤2 Secondary） |

### 13.1 生命周期规则
- **流向**：`Dormant → Attention → Active` 为主路径；关闭从 Active 直接回 Dormant，可经 Attention 中转，不强制。
- **与注意力预算联动**：Active 态受 01 §7 约束——同一时刻至多 1 个 Primary Focus 面板 + ≤2 个 Secondary Focus 面板，其余强制 Dormant，避免多面板堆叠过载（修正 S6 双视觉/信息堆叠）。
- **回流恢复**：回流用户若上次离开时某面板为 Active，可恢复到 Attention（唤起）态，但**不**自动跳到 Active 抢占 Primary（见 03 §7 回流体验）。
- **与探索态正交**：面板生命周期属操作层；探索态（银河提亮）可与面板 Active 共存——用户可在展开面板的同时探索世界层，二者注意力态独立叠加。

### 13.2 实现约束（UI-4）
- 唯一入口 = `PanelManager.openCapability(id)`（继承 §5.2，单分发器）。
- 三态映射为 PanelManager 内部状态机，不新增事件合约（DOMAIN=71/SYSTEM=8 不扩张）。
- 0 代码改动于本文件；仅定义模型。

> **🛑 STOP 声明**：本章为纯交互流程设计，0 代码改动，待 Review。
