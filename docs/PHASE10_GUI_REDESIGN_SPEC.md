# Phase 10 · Experience Layer Redesign v1.0 — GUI 重设计规格书

> **阶段状态**：第一阶段（Audit + Design）交付物。⚠️ **本文件仅含审计结论 + 设计规格 + 技术方案，不含任何实现代码，不修改任何源文件。** 经用户 Review 确认后，方进入 Implement → Test → Report。

---

## 0. 文档元信息

| 项 | 内容 |
| --- | --- |
| 项目 | Xiao6 AI OS（本地优先个人 AI 助手，路径 `G:/xiao6`） |
| 阶段 | Phase 10 · Experience Layer Redesign v1.0 |
| 目标 | 主 GUI 从「Developer Control Console」升级为「Personal AI Operating System」 |
| 设计理念 | JARVIS + AI Desktop + Personal Operating System |
| 本阶段交付 | 本规格书（Audit + Design）；实现待确认 |
| 架构纪律 | 单一状态来源（AppState / ExecutionChannel / ZZSSE / EventBus / AvatarState），零新增 Runtime / Memory / EventBus / State |
| 参考图 | `clipboard-2026-08-04T16-20-57-347Z-ce7a2421.jpg`（JARVIS 式方向）。**注：当前模型无法解析该图片（Read 返回内容已过滤），设计据用户文字规格 + 代码审计推断，方向以本规格书文字为准。** |

---

## 1. 执行模式与红线（强制）

执行严格分阶段、逐阶段确认：

```
Audit ──▶ Design ──▶ Implement ──▶ Test ──▶ Report
  ✅        ✅         ⏸ 待确认      ⏸         ⏸
```

### 1.1 架构红线（不可逾越）

| 红线 | 说明 |
| --- | --- |
| 禁止第二 Runtime | 不新建 Agent 运行时；不修改 Agent Runtime / Goal System / Execution Protocol |
| 禁止第二 Memory | 状态只来自 `AppState`；UI 不自持状态 |
| 禁止第二 EventBus | 事件只经 `EventBus`（eventbus.py）/ SSE 单例 `ZZSSE` 流动 |
| 禁止第二 State | 所有显示内容单向派生自真实系统状态 |
| GUI 复用清单 | `AppState` · `ExecutionChannel` · `ZZSSE` · `EventBus` · `AvatarState` 全部复用既有实现 |
| 状态真实性 | 中央 Core / Timeline / Insight / Avatar 全部绑定真实状态，禁止模拟/伪造状态 |

### 1.2 十大设计部分（用户规格）→ 本规格映射

| # | 用户要求 | 本规格落点 |
| --- | --- | --- |
| 1 | 主界面重新规划（银河隐藏为高级模式） | §4 布局 / §6.1 默认 Workspace |
| 2 | 中央 Xiao6 Core（神经核心，状态映射） | §6.2 / §5.2 绑定 AvatarState |
| 3 | 左侧 AI Capability Matrix | §6.3 / §5.3 绑定 AppState 能力子树 |
| 4 | 右侧 Execution Timeline | §6.4 / §5.4 绑定 ExecutionChannel |
| 5 | 右下 Xiao6 Avatar（人格入口） | §6.5 / §5.5 复用 AvatarState（单一来源） |
| 6 | 底部 Command Dock | §6.6 / §5.6 复用 Chat/Intent/Goal |
| 7 | 银河模式保留为 Universe View | §6.7 / §5.7 复用 solar-system.js |
| 8 | 新增 Xiao6 Insight 主动区 | §6.8 / §5.8 绑定 Phase 9 Proactive |
| 9 | 视觉规范（深空黑+量子青+星辉金） | §3 设计规格 |
| 10 | 第一阶段只 Audit+Design | 本文件范围 |

---

## 2. Audit 发现（现状架构与真实数据源映射）

> 已实读源文件：`index.html` `app-state.js` `execution-channel.js` `event-bridge.js` `zz-events.js` `sse-manager.js` `app.js`（关键段）`command-palette.js` `avatar-state.js` `companion.js` `proactive.py` `styles.css` `solar-system.js` `galaxy-state.js`。

### 2.1 当前布局（styles.css）

- `.app` 为 `grid-template-columns: 248px 1fr 300px`（rail / main / tele），固定 `1920×1080` 画布等比缩放（Electron 桌面壳，保留此缩放策略）。
- 背景层 `#solarCanvas`（太阳系 + 星空）为唯一全屏背景；`.app` 浮于其上。
- `.rail`（左侧指令栏，含 brand / 菜单 / 会话列表）/ `.main`（中央，含 orb 状态徽章 + 太阳系视角）/ `.tele`（右侧遥测日志 `teleLog`）。
- 配色已接近目标：`--void:#05070A` `--cyan:#22D3EE` `--teal:#2DD4BF` `--amber:#F5B544` `--red:#FF4D4D`。
- 字体已引 `Orbitron` / `Rajdhani` / `Share Tech Mono`（符合「禁 system-ui」要求）。

### 2.2 真实数据源确认（每个新面板均有合法来源，**零新增状态**）

| 数据源 | 文件 | 提供内容 | 供哪个面板使用 |
| --- | --- | --- | --- |
| `AppState` | `app-state.js` | `goals / agents / tasks / memory / knowledge / intents / execution{errors,lastRun,currentGoalId,currentAgentId,currentTaskId,reflecting} / workspace / focus / computer` | Capability Matrix / 顶栏状态 / Core 元数据 |
| `ExecutionChannel` | `execution-channel.js` | `getCurrent().steps[]`（每步 `{tool,label,args,status,result,startedAt,completedAt}`），内存上限 50；`subscribe(cb)` | Execution Timeline |
| `AvatarState.derive / deriveFromGlobals` | `avatar-state.js` | 8 态投影（IDLE/WAITING/THINKING/PLANNING/EXECUTING/COMPLETED/ERROR/OFFLINE），优先级 `OFFLINE > ERROR > EXECUTING > THINKING > PLANNING > WAITING > COMPLETED > IDLE`；META 含每态 label/color | 中央 Core + 右下 Avatar（**共用同一派生，禁第二 Avatar State**） |
| Phase 9 Proactive | `proactive.py` → SSE `proactive` | `kind ∈ {reminder,weather,hotspot,alert,goal,review,rule,rule_panel,system,error}` + `content` + `importance` | Xiao6 Insight |
| `galaxy-state.js` + `solar-system.js` | 既有 | 单向派生 AppState → 银河节点；Three.js 渲染 | Universe View（全屏模态复用） |
| `command-palette.js` / `app.js` 发送逻辑 | 既有 | `ZZIntentGateway.dispatch` / 聊天 send / 语音 / 文件 | Command Dock |

### 2.3 关键 API 锚点（实现阶段直接复用，不改签名）

- `AppState.getState()` / `getGoal(id)` / `getAgent(id)` / `getTask(id)` / `getMemory(id)` / `getKnowledge(id)` / `getIntent(id)` / `getFocus()` / `getComputer()` / `applyEvent(name,payload)` / `subscribe(cb)`。
- `ExecutionChannel.startExecution(prompt)` / `onToolStart(ev)` / `onToolEnd(ev)` / `completeExecution()` / `getCurrent()` / `getExecutions()` / `subscribe(cb)` / `mount()` / `render()`。
- `AvatarState.derive(appState, execSnapshot, meta)` / `deriveFromGlobals(meta)`。
- `ZZSSE.onMessage(cb)` / `onState(cb)`（SSE 单例，已在 `sse-manager.js`）。
- `app.js`：`setOrb(mode)`（idle/listening/thinking/speaking/error，驱动 `#stateBadge`/`#mState`/`#mBar`）→ 实现阶段 Core 复用此同步点；`connectProactive()`（消费 `proactive/scene/modal/agent_state/hud_state`）；`openAgentProfileCard()`（拉 `/api/capabilities` + `/api/devices` 渲染真实能力/设备，可复用于 Capability Matrix）。

### 2.4 审计结论

✅ 所有 10 部分所需的真实数据均可从既有基础设施单向派生。
✅ 无第二 Runtime / Memory / EventBus / State 需求；不修改 Agent Runtime / Goal / Execution。
✅ 现有配色与字体已 85% 符合目标，仅需去电竞感、微调金色权重。
⚠️ 参考图无法读取，设计以本规格文字 + 代码审计为准（见 §0 注）。

---

## 3. 设计规格（DESIGN SPECIFICATION）

> 依据 ui-design 规范：指定 aesthetic direction / palette / typography / 玻璃面板 / 图标策略 / 非对称布局；禁紫/靛/系统字体/emoji 图标/电竞 HUD。

### 3.1 美学方向（Aesthetic Direction）

- **定位**：「未来科技办公系统（Future-Tech Office OS）」——克制、精密、信息密度高但呼吸感足。
- **去电竞化**：移除高饱和霓虹描边、扫描线、过度动画；改用低饱和辉光（glow）、细描边（1px 半透明）、柔和景深。
- **质感**：玻璃拟态（glassmorphism）+ 微噪点 + 极细网格底纹；核心区有「活体感」但整体安静。
- **动效基调**：缓动 `cubic-bezier(0.16,1,0.3,1)`，状态切换 240–360ms；禁止弹跳/过度弹性。

### 3.2 调色板（Palette）— 深空黑 / 量子青 / 星辉金

| 角色 | 变量 | 值 | 占比 | 用途 |
| --- | --- | --- | --- | --- |
| 深空黑（基底） | `--void` | `#05070A` | 80% | 背景、面板底、负空间 |
| 深空黑（面板） | `--panel` | `#0B0F14`（微提亮） | — | 玻璃面板底 |
| 量子青（主色） | `--cyan` | `#22D3EE` | 15% | 核心辉光、状态线、主交互、进度 |
| 量子青（次） | `--teal` | `#2DD4BF` | — | 次级强调、链接、完成态 |
| 星辉金（点缀） | `--gold` | `#F5B544` | 5% | 关键洞察、焦点、徽章、价值高亮 |
| 危险红 | `--red` | `#FF4D4D` | <1% | ERROR / 告警 |
| 文本主 | `--txt` | `#E6EDF3` | — | 正文 |
| 文本次 | `--dim` | `#8A93A6`（WCAG AA 深底） | — | 次要信息、标签 |

- **比例纪律**：深色基底 ≥ 80% 可视面积；青色用于「线与活」；金色仅用于「值得注意之物」（Insight 高亮、当前焦点、完成徽章），严格 5%。
- **主题**：保留 `dark-cyan` 为默认；`light` 模式对应变量翻转（金色/青色在浅底下降饱和保对比，满足 WCAG AA）。

### 3.3 字体（Typography）

| 用途 | 字体 | 字重 | 示例 |
| --- | --- | --- | --- |
| 标题 / 品牌 / 数字读数 | Orbitron | 500/700/900 | 小6 OS、状态读数 |
| 正文 / 标签 / 面板标题 | Rajdhani | 400/500/600/700 | 能力名、时间线步骤 |
| 代码 / 参数 / 遥测 | Share Tech Mono | 400 | 工具参数、错误码 |

- 比例：display 28–36px / h1 22px / h2 18px / body 14–15px / caption 12px；行高 1.5（正文）/ 1.2（标题）。
- 禁 system-ui、禁衬线；中文回退 `PingFang SC` / `Microsoft YaHei`。

### 3.4 玻璃面板规范（Glass Panel）

```css
/* 规格示意（非实现代码，仅定义令牌） */
.glass {
  background: color-mix(in srgb, var(--panel) 72%, transparent);
  backdrop-filter: blur(22px) saturate(140%);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.04);
}
```

- 面板间距 16–20px；圆角 16px（卡片）/ 12px（控件）；描边 1px 半透明白。
- 焦点态：量子青 1px 描边 + 外辉光 `0 0 0 1px var(--cyan), 0 0 18px rgba(34,211,238,0.25)`。

### 3.5 图标策略（Icons）

- **禁 emoji**；统一用 **Heroicons（outline）/ FontAwesome** 线性图标，或内联 SVG（与现有 `brand-mark` 一致风格）。
- 六能力图标映射：Reasoning（脑/节点）· Memory（数据库）· Execution（闪电/运行）· Agent（机器人）· Knowledge（书/图谱）· Tools（扳手/插件）。
- 状态指示用色点（dot）+ 细线，不依赖图标语义。

### 3.6 布局（非对称栅格）

保留固定 `1920×1080` 等比缩放画布（Electron 桌面，非响应式断点优先）。区域：

```
┌──────────────────────────────────────────────────────────────┐
│  TOP STATUS BAR  · 小6 OS · Online · User · Current State      │ 高 56px
├────────────┬──────────────────────────────────┬───────────────┤
│ LEFT RAIL  │   CENTER WORKSPACE                │ RIGHT RAIL    │
│ Capability │   ┌────────────────────────────┐  │ Execution     │
│  Matrix    │   │   Xiao6 Core (神经核心) │  │ Timeline      │
│ (上)       │   │   半透明核心球+粒子流+神经线 │  │ (全高)        │
│ ─────────  │   └────────────────────────────┘  │               │
│ Insight    │   ┌────────────────────────────┐  │               │
│ (下,可折叠)│   │   Command Dock              │  │               │
│            │   └────────────────────────────┘  │               │
├────────────┴──────────────────────────────────┴───────┬───────┤
│  (Avatar 浮于右下，跨 center/right 边界) 小6 Avatar ◍          │
└──────────────────────────────────────────────────────┴───────┘
   左侧 260px · 中央 1fr · 右侧 340px（非对称：右栏略宽于左，承载时间线）
```

- 非对称：左 260 / 右 340，中央占主；顶栏贯通；Avatar 浮层 `position:fixed; right:24px; bottom:24px; z-index:30`。
- Universe View 为全屏模态（覆盖 `.app`），经顶栏按钮或快捷键（如 `Ctrl/Cmd+U` 或点击 Core 长按）开启，关闭后回到 Workspace（非默认界面）。

---

## 4. 布局重规划（部分 1 + 6.1）

- **默认主界面 = Xiao6 AI OS Workspace**（上述栅格）。
- 太阳系/星空背景 `#solarCanvas` 在默认 Workspace 下降权为「极暗景深」（opacity 0.25 / 模糊增强），不再作为视觉主角；进入 Universe View 时恢复为全亮主视觉。
- **顶栏（Top Status Bar）**：左 `小6 OS` 品牌 + 在线点；中 `Online / User / Current State`（Current State 取自 `AvatarState.deriveFromGlobals().state` 文案）；右 主题切换 + Universe View 按钮 + 设置。
- 旧 `.rail` 菜单（Developer 指令）迁移为 Capability Matrix 的点击入口（见 §6.3），不再以传统菜单呈现。

---

## 5. 状态绑定与数据流（部分 2–8，§5）

> 每个面板只订阅（subscribe）既有源，只经 `applyEvent` 写入；UI 永不自持状态。生命周期：DOM 挂载 → 订阅 → 渲染 → 事件驱动重渲染 → 卸载取消订阅。

### 5.1 单一来源纪律（重申）

```
AppState ──applyEvent──▶ UI 渲染
   ▲                        │
   │ ZZSSE.onMessage        │ subscribe
   └── event-bridge.ingest ─┘
ExecutionChannel ──subscribe──▶ Timeline
AvatarState.derive(AppState, ExecutionChannel) ──▶ Core + Avatar
Phase9 Proactive SSE ──▶ Insight
```

### 5.2 中央 Xiao6 Core（部分 2）

- **视觉**：半透明核心球（径向渐变 + 噪声）+ 环绕粒子流（Canvas/轻量 Three.js，性能优先，≤ 60fps）+ 神经网络连线（随状态增减亮度）。
- **状态绑定**：`AvatarState.deriveFromGlobals()` → 8 态；`data-state` 驱动核心球颜色/粒子速度/连线密度。
  - IDLE：缓慢呼吸，青色微光。
  - THINKING：粒子加速，连线脉动（紫蓝 `#8b9bff` 仅作 THINKING 临时色，不破坏全局调色）。
  - PLANNING：金色节点浮现。
  - EXECUTING：青绿 `#56d364` 流光沿连线。
  - ERROR：红色 `#ff6b6b` 警示环。
  - OFFLINE：灰 `#8a93a6`，静止。
- **禁模拟**：核心无任何「演示态」；状态 100% 来自 `AvatarState` 派生。
- 元数据（当前 Goal/Agent/Task 名）从 `AppState.execution.currentGoalId/currentAgentId/currentTaskId` 读真实值，hover/点击展开。

### 5.3 左侧 AI Capability Matrix（部分 3）

- 六能力卡片：Reasoning / Memory / Execution / Agent / Knowledge / Tools。
- **数据源**（全部真实）：
  - Reasoning：当前 `AvatarState` 派生态（thinking/planning 权重）或 `AppState.execution.reflecting`。
  - Memory：`Object.keys(AppState.getState().memory).length`（记忆条目数）。
  - Execution：`AppState.getState().tasks` 中 `status==='running'` 计数 + `ExecutionChannel.getCurrent()` 活跃步。
  - Agent：`Object.values(AppState.getState().agents).filter(a=>a.status!=='Created' && a.status!=='Offline').length`（在线 Agent）。
  - Knowledge：`Object.keys(AppState.getState().knowledge).length`。
  - Tools：复用 `openAgentProfileCard()` 拉取的 `/api/capabilities` 工具数（真实设备/能力）。
- **交互**：点击卡片 → 打开既有对应模块（如 Memory→记忆面板、Agent→能力卡、Tools→设备卡）；**禁止创建新模块**，仅路由到已有 UI。
- 每卡片显示：图标 + 名称 + 实时计数/状态点 + 微进度（如 Execution 进度条来自 `ExecutionChannel` 步完成比）。

### 5.4 右侧 Execution Timeline（部分 4）

- **数据源**：`ExecutionChannel.getCurrent().steps[]` + `getExecutions()` 历史。
- **用户可读轨迹投影**（禁止内部思维链）：将原始 `steps` 映射为阶段叙事：
  `理解目标 → 制定计划 → 调用工具 → 执行 → 完成`
  - 每步显示：`label`（中文，来自 `TOOL_LABELS`）+ 状态点（pending/running/done/error）+ 起止时间（`startedAt`/`completedAt`）。
  - 工具参数 `args` 以折叠 `<details>` 展示（Share Tech Mono），不默认展开，避免信息过载。
- **禁展示**：模型内部 reasoning / 思维链文本；仅展示「做了什么」（工具调用与结果摘要）。
- 历史执行以纵向时间轴堆叠，最新在上；`subscription` 驱动增量渲染。

### 5.5 右下 Xiao6 Avatar（部分 5）

- **角色**：AI 人格入口（非聊天头像）；显示状态、可点击展开人格/设置。
- **状态同步**：复用 `companion.js` 同一 `AvatarState.deriveFromGlobals()` 派生 → 与 Companion 桌宠**同一来源**，确保中央 Core 与右下 Avatar 状态永远一致；**禁第二 Avatar State**。
- `onProactiveMessage` 已消费 `proactive/proactive_result`，Avatar 气泡复用此通道（不新增）。
- 点击 Avatar → 打开主窗/人格卡（复用既有 `companion:action` IPC 或主窗系统，不新建 Runtime）。

### 5.6 底部 Command Dock（部分 6）

- **形态**：替代普通聊天输入框；位于中央底部，全宽胶囊式输入。
- **能力**：文字输入（复用 `app.js` 发送/流式逻辑或 `ZZIntentGateway.dispatch`）、语音（复用既有 ASR/TTS 入口）、文件拖入（复用既有文件处理）。
- **快捷指令**：复用 `command-palette.js` 的 `buildCommands()` 分类（panel/theme/feature/create/system）→ 以 `@` 或 `/` 触发建议，不新建指令系统。
- **投递**：自由文本 → `ZZIntentGateway.dispatch` → EventBridge → `AppState.applyEvent`；与既有意图/目标/会话流程完全一致。
- 用户输入即触发 `ExecutionChannel.startExecution(prompt)`，时间线随之生长（真实联动）。

### 5.7 Universe View（部分 7，银河模式保留）

- 现有 `solar-system.js`（Three.js 太阳系）+ `galaxy-state.js`（节点派生）**直接复用**。
- 改为全屏模态：顶栏「宇宙视图」按钮或快捷键开启；`.app` 隐藏，`#solarCanvas` + 银河 UI 全屏展示；关闭回到 Workspace。
- `GalaxyState.onNodeChange` 订阅逻辑不变；仅渲染容器从背景层升为模态前景。
- 非默认界面，不进入即不渲染（按需 `mount`）。

### 5.8 Xiao6 Insight（部分 8，新增主动区）

- **位置**：左栏底部，可折叠卡片（default 展开）。
- **数据源**：Phase 9 Proactive SSE（`ZZSSE.onMessage` 消费 `xiao6_event:"proactive"`，`kind` + `content` + `importance`）。
  - `reminder`：今日任务提醒
  - `goal`/`review`：目标建议 / 周回顾
  - `rule`/`rule_panel`：规则建议
  - `alert`：异常告警
  - `weather`/`hotspot`：态势（GDELT/气象）
  - `error`：critical（突破 DND）
- **禁 UI 自判断**：Insight 仅渲染后端 `push_proactive` 推来的内容，前端不做任何「发现/优化建议」推断。
- 每条 Insight：图标（按 kind）+ 文案 + 重要性色点（gold=高 / cyan=中 / dim=低）+ 可选「采纳/忽略」按钮（采纳 → 经既有意图/目标流程，不新建）。
- 复用 `app.js` `connectProactive()` 既有消费逻辑，仅变更渲染目标容器。

---

## 6. 十大区域实现要点汇总（Implementation Notes，待确认后落地）

| 区域 | 文件（预计改动） | 核心改动 | 复用 |
| --- | --- | --- | --- |
| 顶栏 | `index.html` + `styles.css` + `app.js` | 新增 status bar 结构；Current State 绑 AvatarState | `AvatarState` |
| Capability Matrix | `index.html`(rail) + `app.js` | 六能力卡片 + 路由点击 | `AppState` + `openAgentProfileCard` |
| Core | 新增 `core-visual.js`（Canvas/Three 轻量） + `app.js` 同步点 | 神经核心渲染，绑 AvatarState | `AvatarState` |
| Timeline | `execution-channel.css` + `runtime-visualization.js` 或新 `timeline.js` | 阶段叙事投影 | `ExecutionChannel` |
| Avatar | `companion.js` 逻辑复用 + 主窗 Avatar 节点 | 右下浮层，同源 | `AvatarState` + `companion:action` |
| Command Dock | `index.html`(center bottom) + `app.js` | 胶囊输入，复用发送 | `ZZIntentGateway` + `app.js` send |
| Universe View | `solar-system.js` 容器改造 | 全屏模态 | `galaxy-state` + `solar-system` |
| Insight | 新增 `insight.js` + `styles.css` | 左栏卡片，消费 proactive SSE | Phase 9 Proactive |
| 视觉令牌 | `styles.css` + `premium.css` | 调色/玻璃/字体微调 | 既有变量 |
| 背景降权 | `styles.css` | Workspace 下 `#solarCanvas` opacity 降 | — |

> 上述文件列表为实现阶段计划，**本阶段不创建/修改任何文件**。

---

## 7. EARS 需求（验收基线）

### 7.1 布局与模式
- **Ubiquitous**：当应用启动且未进入 Universe View 时，系统应显示 Xiao6 AI OS Workspace（顶栏 + 左栏 + 中央 Core + 右栏 Timeline + 底部 Command Dock + 右下 Avatar）。
- **Event-driven**：当用户点击「宇宙视图」按钮或按下快捷键时，系统应切换到 Universe View 全屏模态。
- **Event-driven**：当用户关闭 Universe View 时，系统应返回 Workspace 且保留既有状态。

### 7.2 中央 Core
- **State-driven**：当 `AvatarState` 派生为 `EXECUTING` 时，Core 应以青绿色流光呈现且不使用模拟状态。
- **Unwanted**：若 Core 渲染了任何非 `AvatarState` 派生的状态，则系统应视为违规（禁模拟）。

### 7.3 Capability Matrix
- **Event-driven**：当用户点击某能力卡片时，系统应打开对应的既有模块（不创建新模块）。
- **State-driven**：当 `AppState.memory` 条目数变化时，Memory 卡片计数应实时更新。

### 7.4 Execution Timeline
- **State-driven**：当 `ExecutionChannel.getCurrent().steps` 新增步骤时，Timeline 应增量渲染该步骤。
- **Unwanted**：若 Timeline 展示了模型内部思维链/推理文本，则系统应视为违规。

### 7.5 Avatar
- **State-driven**：当 Companion 桌宠 AvatarState 变更为 `THINKING` 时，主窗右下 Avatar 应同步呈现 `THINKING`（同源派生）。

### 7.6 Command Dock
- **Event-driven**：当用户在 Command Dock 提交自由文本时，系统应经 `ZZIntentGateway.dispatch` 投递且触发 `ExecutionChannel.startExecution`。

### 7.7 Insight
- **Event-driven**：当后端经 SSE 推送 `proactive` 事件时，Insight 区应渲染对应 `kind/content`（不前端推断）。
- **Unwanted**：若 Insight 展示了非 `push_proactive` 来源的内容，则系统应视为违规。

### 7.8 视觉
- **Ubiquitous**：系统应以深空黑为 ≥80% 基底、量子青为主交互色、星辉金为 ≤5% 高亮点呈现。
- **Ubiquitous**：所有图标应使用线性图标库（非 emoji）。

---

## 8. 验收标准（测试，7 项）

| # | 测试项 | 通过标准 |
| --- | --- | --- |
| T1 | 启动正常 | Electron 启动后默认进入 Workspace，无控制台报错，FOUC 消除 |
| T2 | AppState 数据正常显示 | Capability Matrix 六能力计数/状态与 `AppState` 真实值一致 |
| T3 | Execution Timeline 正常 | 提交指令后 Timeline 增量显示「理解→计划→工具→执行→完成」轨迹，无思维链 |
| T4 | Avatar 状态同步 | 主窗 Avatar 与 Companion 桌宠状态始终一致（同源 AvatarState） |
| T5 | Command Dock 正常 | 文字/语音/文件输入经既有流程投递，触发真实执行与时间线生长 |
| T6 | Universe View 可开关 | 顶栏/快捷键开启全屏银河，关闭返回 Workspace，状态不丢 |
| T7 | 原功能无回归 | 既有聊天/意图/目标/Companion 交互/Proactive 推送全部正常 |

---

## 9. 任务拆解（Implement 阶段，待确认）

- [ ] T-UI-01 顶栏结构 + 状态绑定（AvatarState）
- [ ] T-UI-02 Capability Matrix 六卡片 + 真实计数 + 路由点击
- [ ] T-UI-03 Xiao6 Core 神经核心渲染（Canvas/Three 轻量）+ AvatarState 同步
- [ ] T-UI-04 Execution Timeline 阶段叙事投影（ExecutionChannel）
- [ ] T-UI-05 右下 Avatar 浮层（同源 Companion）
- [ ] T-UI-06 Command Dock 胶囊输入（复用发送/语音/文件）
- [ ] T-UI-07 Universe View 全屏模态改造（solar-system 复用）
- [ ] T-UI-08 Xiao6 Insight 卡片（proactive SSE 消费）
- [ ] T-UI-09 视觉令牌微调（去电竞感、金色权重、玻璃面板）
- [ ] T-UI-10 背景降权 + 集成联调 + bump 版本号

---

## 10. 待用户确认事项（Gate）

请 Review 本规格书并确认以下决策点，确认后进入 Implement：

1. **布局栅格比例**：左 260 / 右 340 非对称（右栏承载时间线更宽）是否接受？或希望左右等宽？
2. **Insight 位置**：左栏底部可折叠卡片（默认展开）是否合适？或希望置于中央 Core 下方？
3. **Universe View 触发**：顶栏按钮 + 快捷键（`Ctrl/Cmd+U`）是否合适？或仅按钮？
4. **Core 实现技术**：轻量 Canvas 2D 粒子（性能稳、实现快）vs Three.js（更立体、略重）。倾向 Canvas 2D 优先以保证 60fps 与低开销。
5. **THINKING 临时色**：规范允许 THINKING 用紫蓝 `#8b9bff` 作临时态色（不破坏全局 80/15/5），是否接受？或要求 THINKING 也仅用青/金？

> 确认后我将按 §9 任务拆解进入 Implement，完成后交付 `PHASE10_GUI_IMPLEMENTATION_REPORT.md` 并 Stop 等待 Review。
