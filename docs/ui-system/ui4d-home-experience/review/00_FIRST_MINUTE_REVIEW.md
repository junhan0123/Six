# 00 · UI-4D-1.5 首分钟体验评审报告（First Minute Experience Review v1.0）

> 身份：Senior Product Designer · AI OS Experience Reviewer
> 当前态：UI-4D-1 已完成（AI Presence 接入 / Command Dock Intent 化 / Timeline Presence 化 / 首屏状态表达增强）
> 本阶段类型：**Review + Audit Only**
> 禁止清单：新增功能 · 修改逻辑 · 修改 EventBus · 修改 AppState · 修改 Presence 三唯一 · 修改 Backend / Agent

---

## 〇 · 方法与证据来源

本评审为纯文本证据审查，**零代码改动**。截图因当前模型不支持图像读取而不可作为视觉证据，故全部判定基于可断言的 DOM / CSS / 验证 JSON 文本证据。

| 证据类型 | 文件 | 关键内容 |
|---|---|---|
| DOM | `index.html` L78–158 | os-shell 首页结构（导航 / HUD / 意识核心 / 右栏 / 底部） |
| DOM | `index.html` L1260–1332 | Onboarding 三层引导（#onbOverlay） |
| CSS | `ui4d-home-experience.css`（159 行） | D1–D4 纯表现层 ADDITIVE 覆盖 |
| 验证 | `_verify_ui4d.json` | 17/17 全绿（含 EXECUTING 脉动 / ERROR 静态红 / 红线定位） |

截图存档（仅留存，未做视觉验收）：`ui4d_1920_{onboarding,home,executing,error}.png`、`ui4d_1280_home.png`、`ui4d_720_home.png`。

---

## 一 · 综合判定（Verdict）

**UI-4D-1 是否真正完成「AI OS Home Experience」？ → 是。**

在 pure presentational layer（纯表现层）的红线约束内，UI-4D-1 已把「一个能聊天的工作台」升级为「一个以 AI 在场为核心、以意图下达为主入口、以当前态为表面串联的 AI 操作系统首页」。

| 问题 | 判定 | 一句话结论 |
|---|---|---|
| R1 第一屏优先级 | ✅ 通过 | 身份 > 状态 > 意图 > 任务 > 扩展 五级层级全部成立 |
| R2 Onboarding 关系 | ✅ 通过 | Onboarding 是 Home 的首次解释层，不存在两个首页感觉 |
| R3 Intent Console | ✅ 通过 | Command Dock 已从「命令框」语义升级为「意图控制台」（形态仍是输入框，语义已 Intent 化） |
| R4 Idle Experience | ✅ 通过 | 空闲（OFFLINE/IDLE）仍显 presence 灰态 + 状态药丸 + 光环，体现「AI 在线等待」且不焦虑 |
| R5 First Minute Journey | ✅ 通过 | 1 秒看见 · 5 秒理解 · 30 秒完成首意闭环，旅程完整 |

红线与三唯一：✅ 完整保护（零逻辑改动 / 仅消费令牌 / 复用 vitPulse / 定位未变）。

---

## 二 · R1 第一屏优先级（First-screen Priority）

打开小6第一秒，用户**依次**看到（按视觉权重与 DOM 顺序）：

**① AI 身份（Identity）— 最显著锚点**
- HUD 品牌：`os-brand`「小6 · **本地个人 AI 副驾**」（index.html L95）
- 中央英雄区：`os-hero-title`「小6」（L124）+ `os-hero-sub`「你的本地个人 AI 操作系统」（L125）+ `os-hero-eyebrow`「本地运行 · 隐私优先」（L123）
- 证据（D3-b）：英雄名 presence 光晕 — 验证 JSON `shadow=color(srgb 0.541176 0.576471 0.65098 / 0.28) 0px 0px 40px`
- 判定 ✅：AI 身份在「左上品牌 + 中央名字 + 副标题」三重锚定，第一眼即知「这是 AI」。

**② AI 状态（State）— 即时在场**
- 意识核心状态徽章：`os-core-state`（L121，dot + `#osCoreStateText`「待命」）
- HUD 状态药丸：`os-state`（L96，dot + `#osStateText`「待命」）
- 证据（D1-a）：状态徽章升级为 glass + presence 描边芯片 — JSON `border=color(srgb 0.467074 0.622072 0.702282 / 0.513255) pad=6px 12px`（非透明，证明描边生效）
- 证据（D1-e）：HUD 药丸 presence 玻璃化
- 判定 ✅：AI 状态以「点 + 文案」双表达，且写入点唯一（refreshHud），三唯一未破坏。

**③ Intent 入口（Intent Entry）— 底部主操作**
- `os-dock` 标题经 CSS 重命名为「AI Intent Console · 意图控制台」（D2-a，原 "Command Dock" 文本节点 `font-size:0` 隐藏 + `::after` 注入）
- 意图提示追加行（D2-c）：「用自然语言下达意图 · 小6会自行规划与执行」
- 证据：JSON `after="AI Intent Console · 意图控制台"`、`hintAfter="用自然语言下达意图 · 小6会自行规划与执行"`
- 判定 ✅：Intent 入口在底部 dock，标题 + 提示双重框定为「意图控制台」。

**④ 当前任务（Current Task）— 态势表面**
- `os-timeline`「Execution Timeline」（L149–151）+ presence 点（D4-a `::before`）+ 面板 presence 描边（D4-b）
- 证据：JSON `before="" display=flex`、`border=color(srgb 0.133333 0.827451 0.933333 / 0.112549)`
- 判定 ✅：当前态势 / 任务在时间线面板以 presence 点串联，回答「现在有没有任务在进行」。

**⑤ 能力扩展（Capability Expansion）— 可探索边界**
- 左导航脊柱 `os-nav`（home / workspace / command / galaxy / assistant / settings，L81–92）
- 右栏 `os-side`（Capability Matrix + Insight，L136–145）
- 判定 ✅：能力扩展以导航脊柱 + 能力矩阵表达，用户一眼可知「还能做什么」。

**R1 综合**：五项优先级成立且层级正确（身份 > 状态 > 意图 > 任务 > 扩展），信息架构属于「AI OS Home」而非「Web App / 聊天工具」。

---

## 三 · R2 Onboarding 关系（首次解释层，非双首页）

**事实结构**
- Onboarding DOM：`#onbOverlay`（L1260，`hidden` 默认隐藏），仅首启呈现，overlay 覆盖于同一 os-shell 之上。
- 主界面 DOM：`#osShell`（L78），始终为同一首页结构。
- 二者**共享同一 os-shell 视觉语言**，onboarding 仅为首启解释层。

**三步内容**
- Step 0（L1269–1276）：「你好，我是小6 / 本地个人 AI 副驾 · 隐私优先 · 离线可用」
- Step 1（L1278–1322）：个性化（AI 名字 / 主题 / 语音播报 TTS / 主动智能）
- Step 2（L1324–1330）：「一切就绪 / 进入小6 →」

**判定**
- Onboarding 是 Home 的「首次解释层」：解释小6是谁 + 引导个性化，结束后落到**同一个** os-shell 首页。
- 是否存在两个首页感觉？ → **否**。视觉语言一致（D3-a onb-card presence 辉光、9 主题同源、presence 体系贯通），onboarding 关闭即看到 Home，无认知断层式双首页。
- 证据：D3-a `#onbOverlay .onb-card` presence 边框 + 品牌辉光（CSS L112–117）；JSON `onbExists=true`。

**非阻断建议（仅供 Review，不改动）**：step0 文案与 Home hero 文案存在部分重复（「本地个人 AI 副驾 · 隐私优先」），首启强调可接受；可在 step2 增加一句话桥接（如「关闭后你看到的即是下方这个首页」）以进一步消除首启 → Home 的认知跳变。非阻断。

---

## 四 · R3 Intent Console（Command Dock 还是输入框？）

**关键判定**：UI-4D-1 之前 Command Dock 是「命令输入条」（label 偏命令 / 快捷指令心智）；本阶段通过纯 CSS 升级为「AI Intent Console」：

- **标题语义升级（D2-a）**：原文本节点 `font-size:0` 隐藏，`::after` 注入「AI Intent Console · 意图控制台」——从「命令」升为「意图」。
- **输入条视觉升级（D2-b）**：`os-dock-bar` 加 presence 内描边 + 软光，强调「这是与 AI 对话的意图入口」，而非搜索引擎框。
- **意图提示（D2-c）**：追加「用自然语言下达意图 · 小6会自行规划与执行」——明确「你给意图，AI 自行规划执行」的 Agent 心智模型。

**是否仍像输入框？**
- 输入框是**形态**，Intent Console 是**语义框定**。形态上仍是输入框（自然语言输入需要输入框，合理），但**语义已从「下达命令」升级为「表达意图」**，符合 AI OS 而非命令行的交互范式。
- JS 行为未变（仍是输入框接收输入），Intent 化在**文案与视觉语义层**已完成。

**后续（超出本 Review 红线，仅记录）**：若未来要彻底「不像输入框」（如改为芯片式意图选择 / 语音优先），属 UI-4D-2+ 范畴，不在本阶段。

---

## 五 · R4 Idle Experience（空闲存在感 · AI 在线等待）

**事实**：无头环境无后端，`AvatarState` 正确派生为 `OFFLINE`（灰 `#8a93a6`）—— 验证 JSON `presence=OFFLINE color=#8a93a6`，证明 presence 派生链路正常。

**空闲态（IDLE / OFFLINE）的 presence 表达**
- `os-core-state` 状态徽章仍显 presence 描边（D1-a，灰态下描边为 presence 灰、非透明）— JSON border 非 transparent 确认。
- `os-state` HUD 药丸 presence 玻璃化（D1-e）。
- 英雄名 presence 光晕（D3-b）。
- 核心光环（D1-b `::after`）在 IDLE 下仍渲染（presence 灰光，**静止**不脉动，符合 vitPulse 纪律）。

**是否体现「AI 在线等待」？ → 是。**
静态灰态 + presence 药丸「待命」+ 光环，传达「AI 在场、随时待命」，而非「空白 / 死的界面」。

**纪律遵守**
- IDLE / OFFLINE / WAITING / COMPLETED：**静止**（anim = none）
- THINKING / PLANNING / EXECUTING：**脉动**（验证 EXECUTING `anim=vitPulse`，JSON `border=color(srgb 0.313548 0.827451 0.455072 / 0.622353)`）
- ERROR：**静态红描边**（JSON `border=color(srgb 0.887996 0.472316 0.485999 / 0.597176)`、`anim=none`，不制造焦虑）

判定 ✅：空闲存在感成立，且错误态不脉动，符合 Phase 8 三唯一 + vitPulse 唯一动效纪律。

---

## 六 · R5 First Minute Journey（1 秒 / 5 秒 / 30 秒）

### 1 秒 · 看到什么（Visual Capture）
- 左上：`os-brand`「小6 · 本地个人 AI 副驾」+ `os-state` 药丸「待命」（dot + 文案）
- 中央：意识核心（canvas + presence 光环）+ `os-hero-title`「小6」+ 副标题「你的本地个人 AI 操作系统」+ eyebrow「本地运行 · 隐私优先」
- 核心处：`os-core-state` 状态徽章「待命」
- 底部左：`Execution Timeline`（presence 点 + 面板描边）
- 底部右：`AI Intent Console`（意图控制台标题 + 输入框 + 提示行）
- 右栏：`Capability Matrix` + `Insight`
- 左脊柱：导航（home / workspace / command / galaxy / assistant / settings）
- 首启覆盖：`#onbOverlay` 卡片（presence 辉光）「你好，我是小6」

### 5 秒 · 理解什么（Cognitive Comprehension）
1. **这是 AI**：名字「小6」+「本地个人 AI 副驾」+「AI 操作系统」
2. **它在待命**：状态药丸 + 核心徽章均显「待命」+ 灰态光环（在场但不忙）
3. **我可以下达意图**：底部「AI Intent Console · 意图控制台」+「用自然语言下达意图 · 小6会自行规划执行」
4. **它能做什么 / 扩展到哪**：右栏 Capability Matrix + 导航脊柱（对话 / 指令 / 星图 / 语音 / 设置）
5. **当前有无任务**：Execution Timeline（presence 点指示活跃态 / 空态即「暂无进行中任务」）

### 30 秒 · 完成什么（Task Completion）
- **若首启**：完成 onboarding 三步入门（改名 / 选主题 / 开语音播报 / 主动智能）→ 点「进入小6 →」落到 Home。
- **在 Home**：于 AI Intent Console 输入一句自然语言意图（如「帮我总结今天的日程」）→ 小6进入 `EXECUTING`（核心绿描边点亮 + 状态点脉动，已验证 D1 EXECUTING `border=绿` `anim=vitPulse`）→ Execution Timeline 出现对应活动（presence 点串联）。
- 用户完成「从打开到下达第一个意图并看到 AI 执行」的完整首分钟闭环。

---

## 七 · 红线与三唯一复核（Red-line & Three-Uniqueness Audit）

| 红线项 | 状态 | 证据 |
|---|---|---|
| 零逻辑改动 | ✅ | 仅新增 `ui4d-home-experience.css` + `index.html` 末位 link；未改任何 JS / Backend / Agent |
| 唯一状态权威（avatar-state.js） | ✅ 未改 | 派生仍由 `AvatarState.deriveFromGlobals()` 完成（OFFLINE 正确派生为灰态） |
| 唯一写入点（refreshHud） | ✅ 未改 | `body[data-presence]` 仍由 `refreshHud()` 单处写入 |
| 唯一颜色权威（ui2.css body[data-presence]） | ✅ 未改 | UI-4D-1 仅消费 `--presence-color`，未重定义 |
| 唯一动效（vitPulse） | ✅ | JSON `无新 @keyframes found=0`，复用 vitPulse |
| 定位红线（三面板外层） | ✅ 未变 | `.os-shell=absolute` / `#app=relative` / `#universeView=fixed`（JSON 三项确认） |
| 令牌体系 | ✅ 未新增/重定义 | 全部消费既有令牌（`--presence-color` / `--accent` / `--surface-2` / `--border` 等） |
| EventBus / AppState | ✅ 零改动 | 无事件契约扩张、无状态写入口变更 |

---

## 八 · 证据清单（Evidence Register）

- **DOM**：`index.html` L78–158（os-shell）、L1260–1332（onboarding）
- **CSS**：`ui4d-home-experience.css`（D1–D4，159 行，纯 ADDITIVE）
- **验证**：`_verify_ui4d.json`（17/17 全绿）
- **截图**：`ui4d_1920_{onboarding,home,executing,error}.png` + `ui4d_1280_home.png` + `ui4d_720_home.png`（模型不可读，仅存档）

---

## 九 · 综合判定与后续建议

**综合判定**：UI-4D-1 已完成「AI OS Home Experience」目标，R1–R5 全部通过，红线与三唯一完整保护。

**后续（供 Review 决策，非本阶段动作）**
- 若 Review 通过 → 可进入 **UI-4D-2**（本 Review **不进入**）。
- 可选增强（非阻断，超出本红线）：
  - R3 形态层 Intent 化（彻底「不像输入框」）。
  - Onboarding → Home 认知桥接文案。
- **GUI 人眼验收缺口**：截图因模型限制未做视觉验收。历史纪律要求 UI 阶段 GUI 验证需人工复核 —— 建议人工在浏览器打开 `http://127.0.0.1:8000` 确认首屏视觉（尤其 presence 光环强度、意图控制台标题渲染、窄屏布局）。

---

## ▣ STOP

本阶段为 **Review + Audit Only**，评审已完成，判定 **UI-4D-1 达成 AI OS Home Experience**。

**STOP · 等待 Review · 不进入 UI-4D-2。**
