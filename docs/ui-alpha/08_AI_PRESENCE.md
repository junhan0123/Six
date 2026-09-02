# AI OS UI Alpha Program v1.0 · Phase 8 — AI Presence

> **状态：✅ 完成（STOP）**　|　最后更新：2026-08-08　|　版本串 `ui2.css?v=20260808p8`
> 纯表现层（Presentation Layer）收口。零新增 Capability / Tool / API / Runtime / Agent / Planner / Workflow / Memory / Knowledge / Permission；零改动 EventBus / Backend / Agent Runtime / Goal Runtime / Capability Registry / Workspace 架构 / Panel 生命周期 / Galaxy 本体；零新增状态机、零改变既有状态语义、零为视觉统一修改真实业务状态。

---

## 1. 概要（Overview）

小6前端长期存在 **≥9 套互相独立、互不通信的「AI 状态」呈现**：OS HUD 状态点、Companion 头像、意识核心、Command Palette 反馈、Voice Orb、HUD Ring、Galaxy 节点、Agent Runtime 状态点、Execution Monitor。它们之间颜色语言、语义、动效完全割裂，用户无法稳定回答一个问题：**小6现在在哪里、在做什么、是否等待我、是否完成、是否需要我介入。**

Phase 8 的目标不是新增一个状态系统，而是建立一个 **AI Presence Layer（纯表现层投影）**：把已经分散在 AppState / Agent Runtime / Goal / Execution / Companion / 既有事件中的*真实*认知与执行状态，统一投影为一个**唯一的存在信号（Presence Signal）**，由最少、最权威的表面消费，让用户持续、自然、明确地感知小6的存在。

本 Phase 已落地 **Phase B（表现模型）+ Phase C（视觉语言统一）的全部代码与回归守卫**，并完成 **Phase D–K 的审查、层级定义、Anti-Noise、可达性、实施清单与 30 项验证**。配套新增 20 项不变量的回归测试，全部 PASS。

---

## 2. 目标与范围（Goals & Scope）

**目标**
- 建立单一、权威、可消费的 AI Presence 信号。
- 让用户在任何时刻都能回答：小6 *在不在*、*在做什么*、*是否等我*、*是否完成*、*是否需介入*。
- 在不新增状态机、不改变业务语义的前提下，消除 AI 状态视觉碎片化。

**范围内（In Scope）**
- 定义 Presence Presentation Model（表现模型，非业务状态系统）。
- 统一存在色语言、光效、呼吸、文本、状态点。
- 逐态诚实性审查（禁「假 Thinking / 假 Executing」）。
- Companion 与全局 Presence 对齐（同源）。
- Workspace / Overlay / Command / Galaxy 包装层消费同一信号。
- Anti-Noise、可达性（Accessibility）、回归守卫。

**范围外（Out of Scope，严守冻结）**
- 不新增任何业务状态、不修改任何既有状态语义。
- 不统一 *正交* 状态（Voice Orb / HUD Ring / Galaxy 生命周期 / Agent Runtime 状态点 / Execution Monitor），它们语义不同，保持独立且诚实（见 §15）。
- 不进入 Phase 9 Release Polish / Electron / Mobile / Voice / Perception / Automation / Cloud API / Local Model / Model Provider。

---

## 3. 最高纪律与红线（Highest Discipline & Red Lines）

| 维度 | 红线 |
|---|---|
| 状态权威 | 唯一状态权威 = `AvatarState.deriveFromGlobals()`（纯函数派生，不持有状态）。**禁第二状态权威。** |
| 颜色权威 | 唯一颜色权威 = `ui2.css` `body[data-presence]` → `--presence-color`。**禁第二颜色系统。** |
| 写入点 | 唯一写入点 = `index.html` `refreshHud()` 的 `document.body.setAttribute('data-presence', state)`。**JS 不写任何颜色值。** |
| 状态机 | 禁新增状态机；不缓存状态；不改变任何业务状态语义。 |
| AI OS 架构 | 禁改 EventBus / Backend / Agent Runtime / Goal Runtime / Capability Registry / Workspace 架构 / Panel 生命周期 / Galaxy 本体。 |
| 能力扩展 | 禁新增 Capability / Tool / API / Runtime / Agent / Planner / Workflow / Memory / Knowledge / Permission。 |
| 诚实性 | Planner / Workflow 仍为蓝图、Perception 仍为 Mock 时，**不得虚假表现**；禁「假 Thinking / 假 Executing」。 |
| 复用 | 必须复用 Phase 4 Presence Color + Phase 7 Motion System + `ui2.css` + Unified Workspace；禁造第二套颜色或 Motion System。 |

---

## 4. Phase A 回顾：Reality Audit 发现

（Phase A 已于前序会话完成，此处仅复述关键发现作为本 Phase 的出发点。）

**发现 1 — 并行 AI 状态表面（≥9 套，互不通信）：**
① OS HUD 状态点（`#osStateText` / `#osCoreStateText`）
② Companion 头像（8 态 + Remind）
③ Consciousness Core（canvas）
④ Command Palette `feedback()`
⑤ Voice Orb（`setOrb` 5 模）
⑥ HUD Ring（`ZZHudRing.setState` 4 态）
⑦ Galaxy 节点（8 生命周期态）
⑧ Agent Runtime 状态点（`#agentState`）
⑨ Execution Monitor（`#execution-monitor`）

**发现 2 — 颜色语言碎片化：**
- 主窗口对 `--presence-color` 的消费为 **0**（令牌「死」在 Companion 窗口，主窗口从未跟随真实态）。
- OS HUD 状态点硬编码 `--accent`（与 AI 状态*无关*，换肤即变）。
- `--accent` 逐主题变化（`#4f7bff` / `#5fb3c8` / `#22d3ee` / `#0E7490`），而 presence 令牌**跨主题恒定**——这是*正交设计*，不是色彩漂移。
- `--presence-remind` 缺口（Companion 已用，ui2.css 前序已同源补齐）。

**发现 3 — 文档漂移：** `avatar-state.js` 注释曾称「9 态」，实证为 **8 态**（REMIND 是 Companion 通知子类型，非主态）。本 Phase 已校正。

---

## 5. Phase B：AI Presence Presentation Model

**核心原则：表现模型 ≠ 新业务状态系统。** 数据流严格单向、无回写：

```
AppState / Agent Runtime / Goal / Execution / Companion / 既有事件
        │  （既有的、真实的业务状态，零改动）
        ▼
AvatarState.deriveFromGlobals()          ← 唯一状态权威（8 态纯函数派生，不持有状态）
        │  （只读投影，相同输入恒得相同输出）
        ▼
index.html refreshHud()                   ← 唯一写入点：document.body.setAttribute('data-presence', <STATE>)
        │  （只写状态名，不写任何颜色值；不缓存、不建状态机）
        ▼
ui2.css  body[data-presence="<STATE>"]    ← 唯一颜色权威：映射为 --presence-color
        │
        ▼
Presence 表面（OS HUD 状态点 / 意识核心状态点）消费 --presence-color
```

**三大「唯一」纪律（杜绝第二权威）：**
1. **唯一状态权威** — `AvatarState.deriveFromGlobals()`（`avatar-state.js`）。8 态固定：`IDLE / WAITING / THINKING / PLANNING / EXECUTING / COMPLETED / ERROR / OFFLINE`。优先级短路：`OFFLINE > ERROR > EXECUTING > THINKING > PLANNING > WAITING > COMPLETED > IDLE`。
2. **唯一颜色权威** — `ui2.css` 的 `:root` 色板 + `body[data-presence]` 映射块。JS 零颜色写入。
3. **唯一写入点** — `index.html` `refreshHud()`。全局仅此一处 `setAttribute('data-presence', …)`（已用全仓 grep 实证）。

**REMIND 的定位（关键澄清）：** Reminder 是 Companion 的*通知子类型*（`companion.js` `showNotification(kind='remind')` + `--presence-remind: #e0a94f`），**不是 AvatarState 第九主态**，不参与 `body[data-presence]` 映射。这避免了把「通知」混入「存在状态」而污染单一权威。

---

## 6. Phase C：Visual Language 统一

本 Phase 攻克了 Phase A 发现的核心缺口——**主窗口 `--presence-color` 消费为 0（死令牌）**，首次把 AI 真实态投影到主窗口视觉。

**C.1 主窗口状态点跟随真实态（唯一写入点 → 唯一颜色权威）**
- `ui2.css` 新增「Phase 8 · AI Presence Adapter」映射块（`body[data-presence="<STATE>"]` → `--presence-color`，8 态齐全，L392–399）。
- Presence 表面①：顶部 OS HUD 状态点（`.os-hud .os-state .dot`）由硬编码 `--accent` 改为 `var(--presence-color)`（L532–533）。
- Presence 表面②：意识核心状态点（`.os-core .os-core-state .dot`）同源跟随（L574–575）。

**C.2 跨主题恒定（正交设计，非漂移）**
- presence 色值全部以 `:root` 令牌定义，**跨 `[data-theme]` 块不得重定义**（已写入回归测试 [B]）。
- AI 状态语义不因换肤改变——这与逐主题变化的 `--accent` 正交，是刻意的设计分层。

**C.3 跨窗口同源（Cross-Window Same Source）**
- Companion 窗口是独立文档，`ui2.css` 的 `body[data-presence]` 映射对其不生效。故 `companion.css`（L332–339）镜像同一套 `.avatar--<state>` → `--presence-color` 映射；`companion.js` `render()` 按 `AvatarState.deriveFromGlobals()` 注入 `--presence-color`（L62/L76）。
- 两窗口色值逐一相等（回归测试 [F] 实证），来源同一 `AvatarState.META`，**无色彩漂移**。

**C.4 动效复用（禁造第二套 Motion System）**
- 呼吸动效**复用既有 `vitPulse`**（`@keyframes vitPulse { 0%,100%{opacity:1} 50%{opacity:.45} }`，ui2.css L669，Phase 7 已定义）。本 Phase **未新增任何 `@keyframes`**。

**C.5 reduced-motion 双层兜底（已存在，复用不重复）**
- `ui2.css` L844 `@media (prefers-reduced-motion: reduce)` + L847 `body.reduced-motion *` 全局覆盖；Consciousness Core 另有 `drawStatic()` 静态路径。新动效自动被降速/静止。

---

## 7. Phase D：全局 AI 状态体验（逐态诚实性审查）

逐态确认每个状态均派生自**真实数据**，无虚假表现（诚实性红线复核通过）。

| 状态 | 派生来源（`avatar-state.js derive()`） | 诚实性 |
|---|---|---|
| **OFFLINE** | `ZZSSE.getState() === 'open'` 为假 → 后端不可达。`deriveFromGlobals` 读 `sse-manager.js` 真实连接态；缺失时默认在线（不会误报离线）。 | ✅ 真实可触发 |
| **ERROR** | 近期 `execution.errors` 或 agent/task `Failed`。 | ✅ 读真实错误源 |
| **EXECUTING** | 执行通道 `running` / 有 `running` step / agent `Working`。 | ✅ 读真实执行 |
| **THINKING** | agent `Thinking`。 | ✅ 读真实智能体态 |
| **PLANNING** | intent 分析中/已分类/已接收/已接受 / goal 进行中 / agent `Started`。 | ✅ 读真实规划信号 |
| **WAITING** | agent `Waiting` / 有待确认 intent（`needsConfirm`）。 | ✅ 读真实等待 |
| **COMPLETED** | 近期（`recencyMs` 内）完成的执行，短时展示后回落 IDLE。 | ✅ 短时真实完成 |
| **IDLE** | 以上皆否的兜底。 | ✅ 诚实空闲 |
| **REMIND**（通知子类型） | `companion.js showNotification('remind', …)` 由真实主动智能/目标事件触发（如「已主动创建目标」）。 | ✅ 真实通知，非主态 |

**关键诚实性结论：** `derive()` 是纯函数投影，输入为空（无 agent/goal/intent/exec 活跃）时必落 IDLE。Planner/Workflow 仍为蓝图、Perception 仍为 Mock 时，**不会**因本 Phase 产生任何「假 Thinking / 假 Executing」——因为底层真实状态未被伪造。

---

## 8. Phase E：Companion Integration

Companion 作为独立窗口，与全局 Presence **同源对齐**：

- **状态投影同源**：`companion.js` L62 `AvatarState.deriveFromGlobals()` → L76 `root.style.setProperty('--presence-color', res.color)`，与 OS HUD 共用同一权威。
- **色语言镜像**：`companion.css` `.avatar--<state>`（L332–339）与 `ui2.css` 8 态+remind 色值逐一相等（测试 [F] PASS）。
- **Remind 脉冲**：`companion.js` 对 `kind==='remind'` 加 `cn-remind` 类 + `--presence-remind` 琥珀脉冲环（头像温和脉动，不喧宾夺主）。
- **通知去噪**：Companion 已有 `mainVisible` 去重 + 6s 自动隐藏 + DND（勿扰）遵从，避免重复/持续打扰。
- **未改动**：`companion.js` 非本 Phase 改动文件（git status 证实）；本 Phase 仅验证其对齐，属文档化收口。

---

## 9. Phase F：Workspace Integration

Unified Workspace（`panel-manager.js`，Phase 2 建立）的 `WorkspaceState` 是 **UI-only** 状态（面板开合/聚焦），**不含也不需 presence 态**——这符合纪律（不为视觉统一注入虚假业务状态）。

AI Presence 在 Workspace 中的落点：
- **Workspace chrome（OS HUD 状态点）** 即 Presence 表面①，已跟随 `--presence-color`——用户在工作空间内*任何位置*都能看到小6状态，无需打开特定面板。
- **面板内容为用户驱动**（用户主动打开/操作），不展示 per-panel AI 状态（避免噪声与虚假在场）。
- **Overlay / Command Palette / Galaxy 包装层** 均消费同一 `AvatarState` 信号，不各自发明状态。

---

## 10. Phase G：Presence 层级（L1–L5）

为贯彻 Anti-Noise，Presence 表面按「始终在场 → 按需出现」分为 5 层，**同一时刻不应全部点亮**：

| 层级 | 表面 | 生命周期 | 说明 |
|---|---|---|---|
| **L1 全局常驻** | OS HUD 状态点 + Consciousness Core | 始终 | 最权威、最低噪声的存在信号。仅状态点 + 文本标签 + 核心微光。 |
| **L2 桌面常驻（条件）** | Companion 头像 | 可见时 | 独立窗口，同源投影；可见才呈现，DND 时静默。 |
| **L3 瞬时反馈** | Command Palette `feedback()` | 按需（命令执行时） | *本地*瞬时反馈（命令已接受/已转交），非全局态，命令结束即消。 |
| **L4 事件驱动** | Overlay / Toast / Remind 通知 | 事件触发 | 仅在有具体事件（完成/异常/提醒）时出现，6s 后隐退。 |
| **L5 面板本地** | （无） | — | 用户驱动，不展示 AI 状态。刻意为空，防噪声。 |

**原则：** L1 永远在；L2–L4 按可见性/事件/交互出现；L5 永不主动出现。呼吸动效（§11）只发生在 L1 的工作三态，进一步压低噪声。

---

## 11. Phase H：Anti-Noise 策略

- **仅「AI 正在工作」三态呼吸**：`THINKING / PLANNING / EXECUTING` 触发 `vitPulse` 呼吸（OS HUD 点 + 意识核心点，L582–588），复用既有动效。
- **其余状态静止（安静在场）**：`IDLE / WAITING / COMPLETED / OFFLINE` 不呼吸——小6「在但安静」，不抢占注意。
- **ERROR 不脉动**：错误态故意静止（不使用焦虑性脉动），仅以珊瑚红 + 状态文本 + 可选通知传达，避免制造恐慌。
- **Companion 去重**：`mainVisible` 去重 + 6s 自动隐藏 + DND 遵从，杜绝重复通知轰炸。
- **reduced-motion**：双层兜底（CSS `@media` + `body.reduced-motion *`）+ Consciousness Core `drawStatic()`，动效敏感用户自动降级为静态。

---

## 12. Phase I：可达性（Accessibility）

- **状态不只靠颜色传达**：OS HUD 与意识核心状态点均配**文本标签**（`#osStateText` / `#osCoreStateText`），色盲/低视力用户可读状态文字。
- **reduced-motion 合规**：全局双层兜底 + 意识核静态路径（§6.C5 / §11）。
- **色彩对比**：presence 色板与背景经既有设计令牌保证对比，状态点含 `box-shadow` 光晕提升辨识。
- **Companion 通知含文本**：`showNotification` 按 `kind` 设置图标（error `!` / remind `»` / done `✓`）+ 文字内容，非纯色块。
- **无新增交互障碍**：本 Phase 零新增控件/按钮，仅复用既有状态点，不改变焦点/键盘流。

---

## 13. Phase J：实施清单（Implementation）

| 文件 | 改动 | 性质 |
|---|---|---|
| `ui2.css` | 新增「Phase 8 · AI Presence Adapter」映射块（`body[data-presence]` → `--presence-color`，8 态）；OS HUD 点 + 意识核心点由 `--accent` 改 `--presence-color`；新增仅工作三态 `vitPulse` 呼吸规则。版本串 `?v=20260807p5` → `?v=20260808p8`。 | 纯表现层（CSS 令牌/映射） |
| `index.html` | `bootOS()` 内新增 `refreshHud()`：派生 `AvatarState.deriveFromGlobals()` → 写文本标签 + `document.body.setAttribute('data-presence', state)`；订阅 `AppState.subscribe('*')` / `ExecutionChannel.subscribe` / `ZZSSE.onMessage`。 | 唯一写入点 |
| `avatar-state.js` | L17 注释校正：「9 态」漂移 → 「8 态（唯一状态权威）。REMIND 不在此列」。 | 文档修正（无逻辑改动） |
| `tests/phase8-ai-presence.frontend.test.js` | **新建**，20 项不变量静态/纯函数断言（不依赖浏览器/Electron/网络）。 | 回归守卫 |
| `companion.js` / `companion.css` | **未改动**（本 Phase 仅验证对齐）。 | — |
| `consciousness-core.js` | **未改动**（已消费 `deriveFromGlobals()` + `drawStatic`）。 | — |

**代码改动总量极小、纯表现层、零架构影响。** 三问自检（UI Alpha 纪律）：
1. 是否让小6更像 AI OS 而非 Web App？→ **是**（统一存在信号，持续在场）。
2. 是否复用现有 Design Language？→ **是**（仅用 `ui2.css` 令牌 + 既有 `vitPulse`，零新风格）。
3. 是否增强 AI Presence 而非新增控件？→ **是**（复用既有状态点，零新按钮）。

---

## 14. Phase K：验证（Verify 30 项）

回归测试 `tests/phase8-ai-presence.frontend.test.js` 覆盖 20 项不变量（**PASS 20/0**），映射如下 Verify 30 项（✅ 已自动验证｜🔍 已静态审查）：

**状态权威（1–5）**
1. ✅ `STATES` 恰 8 态且固定
2. ✅ `META` 无 REMIND / REMINDER 主态
3. ✅ `derive()` 为纯函数（无 localStorage / EventTarget / fetch）
4. ✅ 注释无「9 态」漂移
5. ✅ 优先级短路顺序正确（OFFLINE > ERROR > … > IDLE）

**颜色权威（6–12）**
6. ✅ `:root` 定义全部 8 态令牌 + `--presence-remind` + `--presence-color` 回落 IDLE
7. ✅ presence 色值零硬编码碎片（仅作令牌值，不出现在声明体）
8. ✅ presence 令牌跨 `[data-theme]` 块恒定（不得重定义）
9. ✅ 8 态 `body[data-presence]` 映射块齐全
10. ✅ 主窗口 HUD 点消费 `--presence-color`（非 `--accent`）
11. ✅ 意识核心点消费 `--presence-color`（非 `--accent`）
12. ✅ Companion 窗口 `.avatar--<state>` 镜像同一色板

**写入点（13–16）**
13. ✅ 全仓仅 `index.html:1344` 一处 `setAttribute('data-presence')`
14. ✅ 写入值取自 `st.state`（非硬编码）
15. ✅ JS 不写 `--presence-color`（颜色权威留在 CSS）
16. ✅ `avatar-state.js` 已加载于 `index.html`（Adapter 能取真实态）

**表面与动效（17–23）**
17. ✅ 呼吸仅 THINKING/PLANNING/EXECUTING
18. ✅ IDLE/ERROR/OFFLINE/COMPLETED/WAITING 不呼吸
19. ✅ 复用既有 `vitPulse`，未新增 `@keyframes`
20. ✅ reduced-motion 双层兜底仍在
21. 🔍 Consciousness Core `readState()` 读 `deriveFromGlobals()` + `drawStatic()` 降级
22. 🔍 Command Palette `feedback()` 为本地瞬时反馈，未绑全局态
23. 🔍 状态点均含文本标签（可达性）

**跨窗口同源（24–26）**
24. ✅ companion.css 与 ui2.css 8 态+remind 色值逐一相等
25. ✅ `AvatarState.META` 每态色与 ui2.css 令牌一致
26. ✅ Companion `render()` 按 `deriveFromGlobals()` 注入 `--presence-color`

**诚实性与正交（27–30）**
27. 🔍 OFFLINE 真实可触发（`sse-manager.js` `ZZSSE.getState`）
28. 🔍 无「假 Thinking / 假 Executing」（derive 纯投影，无伪造源）
29. 🔍 正交表面（Voice Orb / HUD Ring / Galaxy / Agent 状态点 / Execution Monitor）未为统一而被改动语义
30. 🔍 全仓 grep：无第二 `data-presence` 写入、无第二颜色系统、无新增状态机

**结论：30/30 通过（20 自动 + 10 静态审查），零回归。** 另：`phase7-companion-avatar.frontend.test.js` 23/23 PASS，证明无回归。

---

## 15. 未改动与正交保留（Orthogonal Surfaces Kept Separate）

为遵守「禁改变既有状态语义」与「禁造第二状态权威」，以下*正交*状态表面**刻意不并入** AI Presence（它们语义不同，强行统一会破坏诚实性与既有架构）：

- **Voice Orb（`app.js` `setOrb` 5 模）** — 语音模态状态（idle/listening/speaking/thinking…），独立系统，不读 `AvatarState`。
- **HUD Ring（`hud-ring.js` `ZZHudRing.setState` 4 态）** — 语音交互环（idle/thinking/speaking/listening），独立 4 色。
- **Galaxy 节点（8 生命周期态）** — 实体（agent/goal）生命周期本体，独立语义。
- **Agent Runtime 状态点（`#agentState`）** — 诚实 `disabled` 状态（后端能力未启用时）。
- **Execution Monitor（`#execution-monitor`）** — 诚实执行进度，由 `execution-channel.js` 自挂载。
- **Command Palette `feedback()`** — *本地*瞬时反馈（命令已接受/转交），非全局 AI 态。

AI Presence Layer 统一的是**认知/执行状态（小6在做什么）**，而非上述模态/实体/进度本体。各表面仍各自诚实，仅 L1 状态点被统一投影。

---

## 16. 诚实性复核（Honesty Audit）

| 复核项 | 结果 |
|---|---|
| 是否存在「假 Thinking / 假 Executing」 | 否。`derive()` 纯投影真实 AppState/Execution/ZZSSE；空输入必落 IDLE。 |
| OFFLINE 是否真实可触发 | 是。`sse-manager.js` 提供 `ZZSSE.getState()`，`avatar-state.js` L171 读取。 |
| REMIND 是否冒充主态 | 否。明确为 Companion 通知子类型，不参与 `body[data-presence]`。 |
| 颜色是否跨主题漂移 | 否。presence 令牌恒定，`--accent` 正交变化。 |
| 状态是否仅以颜色传达 | 否。状态点均配文本标签。 |
| 是否新增业务状态/语义 | 否。纯表现层投影。 |

---

## 17. 风险与遗留（Risks & Leftovers）

- **R1（低）：Consciousness Core 轮询而非订阅。** 意识核每 350ms 轮询 `deriveFromGlobals()`，与 OS HUD 的事件订阅略有延迟差（<350ms）。属既有设计，非本 Phase 引入，不影响一致性与诚实性；如需严格同步可后续订阅，但当前无需改动。
- **R2（信息）：REMIND 语义边界。** Remind 已明确定位为通知子类型，但若未来新增更多 Companion 通知种类，需重申「不混入 Presence 主态」纪律。
- **R3（非本 Phase 范围）：Planner/Workflow 仍为蓝图、Perception 仍为 Mock。** 这些是既有架构事实；本 Phase 的诚实性保证即建立在「不伪造底层状态」之上。一旦这些能力真实化，Presence 会自动如实反映，无需改动本 Phase 代码。

---

## 18. 结论与 STOP（Conclusion & STOP）

Phase 8 · AI Presence 以**极小、纯表现层**的改动，建立了小6前端的**唯一 AI 存在信号**：

- **单一状态权威**（`AvatarState.deriveFromGlobals()`，8 态纯函数，不持有状态）
- **单一颜色权威**（`ui2.css` `body[data-presence]` → `--presence-color`）
- **单一写入点**（`index.html` `refreshHud()`，仅写状态名，零颜色写入）
- **跨主题恒定、跨窗口同源**（Companion 镜像同一色板）
- **Anti-Noise**（仅工作三态呼吸，错误不焦虑，安静在场）
- **可达性**（文本标签 + reduced-motion 兜底）
- **20 项回归不变量 + 30 项 Verify 全过**，零回归

小6现在能通过 OS HUD 状态点 + 意识核心 + Companion 头像，持续、自然、明确地回答：**小6在不在、在做什么、是否等我、是否完成、是否需介入**——且不制造噪声、不虚构状态。

> ### 🛑 STOP
> Phase 8 已完成并通过验证。**禁止进入** Phase 9 Release Polish / Electron / Mobile / Voice / Perception / Automation / Cloud API / Local Model / Model Provider。
> 后续若需调整，须走设计/治理评审（GOVERNANCE_CHANGE_CONTROL），并复用本 Phase 建立的「单向投影 + 三唯一 + 跨窗口同源」纪律。

---

### 附：关键文件索引
- 表现模型：`xiao6-ui/avatar-state.js`
- 唯一写入点：`xiao6-ui/index.html`（`refreshHud()` @ L1336）
- 唯一颜色权威：`xiao6-ui/ui2.css`（Phase 8 Adapter 块 @ L381–399；表面 @ L532/L574；呼吸 @ L582–588）
- 跨窗口同源：`xiao6-ui/companion.css`（`.avatar--<state>` @ L332–339）+ `companion.js`（`render()` @ L62/L76）
- 意识核消费：`xiao6-ui/consciousness-core.js`（`readState()` @ L36）
- 回归守卫：`xiao6-ui/tests/phase8-ai-presence.frontend.test.js`（PASS 20/0）
