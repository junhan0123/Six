# 02 · Conversation 状态模型（State Model）

> **身份**：AI OS UX Architect · UI-5C-0
> **承接**：`01_CONVERSATION_POSITION_MODEL.md`（Conversation = chat-mode 聚焦层）
> **约束**：禁止代码/CSS/JS/Runtime 修改；禁止新增 Event；禁止改变 AppState。本模型全部状态均为**派生投影**，不新增任何存储。

---

## 0. 结论

Conversation Panel 的视觉/交互状态应由**三态**描述：

| 态 | 名称 | 含义 | 在代码中的现有派生信号 |
|---|---|---|---|
| S0 | **Default（默认/收起）** | 对话未成为焦点；首页下完全隐藏，工作台下历史折叠仅留输入 | 无 `chat-mode`（首页隐藏）／有 `chat-mode` 但 `chatArea` 无 `open` |
| S1 | **Attention（聚焦/展开）** | 对话历史可见，用户正在阅读/滚动或正在生成 | `chatArea.classList.contains('open')`（app.js:1099） |
| S2 | **Active（活跃/参与中）** | 一次真实对话交互正在进行 | `state.streaming`（流式）或 `isTyping()`（输入聚焦）或 `app.has-messages` 且 `isHoveringChat()` |

三态全部由**既有 DOM class + 既有闭包变量**派生，不引入新状态对象、不写入 AppState、不新增事件。

---

## 1. 现有状态事实（审计）

`app.js` 中对话的"状态"实际由三类信号组合表达：

1. **模式信号**：`document.body.classList` 是否含 `chat-mode`（index.html:1465）。
2. **展开信号**：`chatArea.classList` 是否含 `open`（app.js:1099 `revealChat` 添加，L1107/L1122 移除）。
3. **活跃信号**：
   - `state.streaming`（app.js 闭包，L1103/L1106/L1120 判断）
   - `isTyping()` = `document.activeElement === input`（L1095）
   - `isHoveringChat()` = `chatArea.matches(':hover')`（L1094）
   - `app.classList.contains('has-messages')`（L163/L171/L391/L254）

现有自动行为（app.js:1096–1123）：
- `revealChat()` → 加 `open`；`scheduleCloseChat(5000)` → 5 秒后若无 hover/typing/streaming 则移除 `open`。
- 点击聊天区之外（非流式、未聚焦输入）→ 移除 `open`。
- 输入 `#input` 点击/聚焦 → 展开。

→ 代码已经隐含了「收起 ↔ 展开 ↔ 活跃」的循环，本模型只是把它**显式命名并规整为三态**。

---

## 2. 三态精确定义

### S0 · Default（默认/收起）
- **首页（无 chat-mode）**：`#app` `visibility:hidden` → 整个对话（含 convList、chatArea、tele）不可见。Galaxy 为视觉中心，Command Dock 为唯一入口。
- **工作台（有 chat-mode，无 open）**：对话输入坞可见、历史折叠。等待用户点击输入或下达指令。
- **进入条件**：`!chat-mode`（首页）∨（`chat-mode` ∧ `!chatArea.open`）。
- **设计意图**：对话不抢占首页注意力；它是"被召唤"的，不是"常驻"的。

### S1 · Attention（聚焦/展开）
- **定义**：对话历史显形，用户正在阅读/回溯，或刚刚有新消息到达。
- **现有信号**：`chatArea.classList.contains('open') === true`。
- **触发**：新消息到达（`revealChat()`，app.js:394）；用户输入聚焦（L1112–1114）；滚轮进入背景层时若未展开则展开（L1150）。
- **退出**：`scheduleCloseChat` 5 秒计时到点且无 hover/typing/streaming。
- **设计意图**：在历史与焦点之间给一个"可读"的中段，避免一有新消息就永远顶屏。

### S2 · Active（活跃/参与中）
- **定义**：一次真实的对话回合正在发生。
- **现有信号（任一为真即进入）**：
  - `state.streaming === true`（小6正在生成）
  - `isTyping() === true`（用户正在输入）
  - `app.has-messages` ∧ `isHoveringChat()`（有内容且用户正悬停对话区）
- **设计意图**：这是 Conversation 的"主权时刻"——OS 其余层（含 Galaxy）应进一步让位（ui2.css:947 `body.chat-mode #solarCanvas{brightness(.46)}` 已在 S1/S2 区间生效，使 Galaxy 降为 World Layer）。

---

## 3. 状态转移表（派生，无新事件）

```
                     ┌──────────────────────────────────────────────┐
                     │            S0 Default (收起/隐藏)            │
                     └───────────────────┬──────────────────────────┘
                                         │ 下达指令 / 点击 FAB / 输入聚焦
                                         │ (openChat → chat-mode; revealChat → open)
                                         ▼
                     ┌──────────────────────────────────────────────┐
                     │          S1 Attention (历史展开)             │
                     └──────┬───────────────────────────┬───────────┘
            scheduleClose    │                           │ streaming/typing/hover
            (5s,无交互)      │                           ▼
                            ▼                           S2 Active (参与中)
                     ┌───────────────────┐              │
                     │ 回到 S0 (收起)    │◄─────────────┤ streaming 结束 / 输入失焦 / 移出
                     └───────────────────┘   (回到 S1 再计时或回到 S0)
```

- 所有转移均由**既有信号组合**驱动，无需新增事件。
- `S2→S1`：交互暂停但历史仍展开（`scheduleCloseChat` 重新计时），属自然回落，不消失。
- `S1→S0`：计时到点且无任何交互 → 收起历史，仅留输入坞（工作台）或整体隐藏（首页）。

---

## 4. 与 AI Presence 三唯一的关系（红线保护）

AI Presence 三唯一（Golden State 红线）：
1. 状态权威 `avatar-state.js` `AvatarState.deriveFromGlobals()`
2. 唯一写入点 `index.html::refreshHud()`（单处 `setAttribute('data-presence')`）
3. 颜色权威 `ui2.css body[data-presence]` → `--presence-color`

**本状态模型与 AI Presence 正交，绝不交叉：**
- Conversation 三态作用于 `#app` / `chatArea` / `app` 的 class，**不读写 `data-presence`**。
- Conversation 的"活跃" ≠ AI 的"EXECUTING/THINKING"。前者是**用户侧交互态**，后者是**AI 侧运行态**。二者可同时成立（用户正在输入 + 小6正在生成），也各自独立。
- 本模型不新增任何 `data-presence` 值、不修改 `refreshHud`、不动 `avatar-state.js`。

> 设计纪律：Conversation 三态是"交互焦点"维度；AI Presence 是"AI 生命状态"维度。两条轴可叠加显示，但必须由各自的唯一权威各自投影，不可混写。

---

## 5. 约束校验

| 约束 | 是否满足 | 说明 |
|---|---|---|
| 禁止代码修改 | ✅ | 纯模型定义 |
| 禁止幻想新 Runtime | ✅ | 三态为派生投影，无新运行时 |
| 禁止新增 Event | ✅ | 复用 `chat-mode` / `chatArea.open` / `state.streaming` / `isTyping` / `isHoveringChat` 等既有信号 |
| 禁止改变 AppState | ✅ | 对话状态停留 UI 局部，不进入 11 子树 |
| 保护 AI Presence 三唯一 | ✅ | 不触碰 `data-presence` / `refreshHud` / `avatar-state.js` |

---

## 6. 给实现的提示（仅描述，不实现）

若后续经 Review 允许进入实现阶段，三态应：
- 由 existing `chatArea.classList` + `state.streaming/typing/hover` 直接派生，**单处计算函数**返回 `S0|S1|S2`，供 UI（如输入坞高亮、Galaxy 降权强度、HUD 提示）统一读取。
- 沿用现有 `revealChat` / `scheduleCloseChat` 计时，不另起计时器。
- 不向 AppState 写任何 conversation 状态；如确需跨模块知会（如 Hotspot 镜像），继续复用既有 `ZZChat.onUpdate` 订阅，不新增事件。

**▣ STOP · 待 Review。** 本文件为纯设计交付，未改动任何代码/CSS/JS/Runtime；未提交 Git。
