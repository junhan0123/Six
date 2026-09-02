# 01 · Conversation 在小6 AI OS 中的位置模型（Position Model）

> **身份**：AI OS UX Architect
> **阶段**：UI-5C-0 · Conversation Core Integration Design
> **性质**：纯设计审计 + 模型定义。**禁止代码/CSS/JS/Runtime 修改；禁止幻想新 Runtime；禁止新增 Event；禁止改变 AppState。**
> **基线**：基于现有代码真实读盘（行号证据见附录 A），非推测。

---

## 0. 一句话结论

**Conversation（对话）在小6 AI OS 中应当继续作为「一种 OS 模式」（chat-mode），而非独立面板、非常驻控件、亦非新的运行时。** 它已经以 `window.ZZChat` 模块 + `body.chat-mode` 浮层形态存在于代码之中，本模型只是把它从「遗留实现」提升为「被明确定义的架构位置」，并沿既有的导航脊柱（syncNav）收口，使其与 `universe-mode` 对称、与 Command Dock 形成单一输入漏斗。

---

## 1. 当前真实位置（审计事实）

### 1.1 Conversation 不是一个 PanelManager 面板

`panel-manager.js` 的注册表 `REG`（L91–L109）共 17 项，覆盖 weather / briefing / memory / settings / capabilities / tasks / video … **完全没有 `conversation` 或 `chat` 项**。

- 结论：Conversation 不走 PanelManager 的生命周期（open/close/pin/collapse）。
- 它是 `app.js` 内暴露的 `window.ZZChat`（L2457–L2487），一个**对话桥模块**，自带会话列表、消息流、输入、流式回调。

### 1.2 Conversation 是「模式」而非「页面」

`index.html:1463–1466`：
```js
// 聊天开关（既有 .app 降级为可唤出抽屉）
var fab = document.getElementById('osChatFab');
function openChat()  { document.body.classList.add('chat-mode');   document.body.classList.remove('universe-mode'); }
function closeChat() { document.body.classList.remove('chat-mode'); }
```

`ui2.css:937–940`（Capability Focus 块）把 Conversation 实现为浮层：
```css
body:not(.chat-mode) #app { visibility: hidden; pointer-events: none; ... }
body.chat-mode #osShell { opacity: .32; filter: blur(6px) saturate(.85); pointer-events: none; }
body.chat-mode #app { visibility: visible; pointer-events: auto; z-index: 50; ... }
```

- 首页（无 chat-mode）：`#app`（含左侧 `convList` + 中央 `chatArea` + 右侧 `tele`）整体 `visibility:hidden` → **对话在首页默认不可见**，Galaxy 是视觉中心，Command Dock 是唯一主入口。
- 工作台（chat-mode）：`#app` 浮起 `z-index:50` 显形，`#osShell` 降权虚化 → 对话成为焦点。

### 1.3 Conversation 在导航脊柱中的身份

`index.html:1495–1504` 的 `syncNav()` 以 body 类推导当前导航态：
```js
if (b.contains('universe-mode')) cur = 'galaxy';
else if (b.contains('cp-mode'))  cur = 'command';
else if (b.contains('chat-mode')) cur = navVoice ? 'assistant' : 'workspace';
else if (settingsOpen())         cur = 'settings';
// 否则 'home'
```

Conversation 与 `universe-mode`(galaxy) / `cp-mode`(command) / `settings` / `home` 并列，是五种 OS 导航态之一。它天生就是一种**模式**。

### 1.4 Conversation 与 AppState 的关系（关键红线）

`app.js` 的对话状态是**模块私有闭包变量**，不写入 AppState：
- `state.messages` / `state.streaming` / `state.turns` / `state.tokens`（本地 `state`）
- 会话持久化走 `localStorage`（history），`persistHistory()`（L149、L239、L246、L258）
- **不调用 AppState.applyEvent / reducer；不订阅 AppState 写入口**

而 `execution-timeline.js`（L22–L45）才是 AppState 的只读投影消费者（读 `intents/goals/agents` + `ExecutionChannel`）。

→ Conversation 是 **AppState 域模型之外的 UI 局部关注点**，这与「AppState 单一写入口 + 11 子树」的 Golden State 红线一致（对话不污染域真相）。

---

## 2. 五模块审计证据索引（附录 A）

| 模块 | 文件 | 关键行 | 与 Conversation 的关系 |
|---|---|---|---|
| Command Dock | `command-dock.js` | L17–24 `sendText`；L49–61 文件/截图/快捷派发 | 首页常驻输入；`sendText` 写入 `#input`/`#btnSend` 或派发 `zz:command`，**委托给对话后端** |
| Conversation/App | `app.js` | L130–258 会话管理；L369–397 `addMessage`；L1090–1115 chat 揭示/收起；L2457–2487 `window.ZZChat` | 对话核心：会话列表、消息流、输入坞、流式桥。**私有 `state`，不写 AppState** |
| Timeline | `execution-timeline.js` | L11–17 五阶段；L22–45 读 AppState/ExecutionChannel；L128–141 订阅 | 执行过程自然语言投影；**不订阅 `chatUpdateCbs`，与消息流解耦** |
| Panel Manager | `panel-manager.js` | L91–109 `REG`（无 conversation）；L27 `conversationId` 槽位声明但未写入 | Conversation **非面板**；`activeContext.conversationId` 是预留但未接线空槽 |
| Galaxy Experience | `galaxy-experience.js` | L22–28 只读 AppState.getFocus/GalaxyState；L31–46 节点类型/生命周期标签；L90–122 节点卡渲染 | **不读对话**；仅经既有 AppState→GalaxyState→GEL 管线反映任务生命周期 |

补充 DOM 骨架（`index.html`）：`#osShell`(L78) → `#osDock`(L155) → `#universeView`(L161) → `#app`(L257，含 rail/convList L300、main/chatArea L359、tele L389)。

---

## 3. Q1 回答：Conversation 是否应该成为独立模式？

**是。它应继续并正式确认为一种 OS 模式（chat-mode），理由如下：**

1. **代码已然如此**：`chat-mode` 浮层、`syncNav` 的 `workspace/assistant` 分支、`window.ZZChat` 桥都已存在。把它"提升为模式"是**命名与收口**，不是新增架构。
2. **与 universe-mode 对称**：Galaxy 用 `universe-mode`、对话用 `chat-mode`，二者是同一「连续空间中的聚焦层」范式的两个实例（UI-5A 已确立该范式：OS 操作层 dim/blur 而非 `display:none`）。对称带来可预测性。
3. **不破坏红线**：模式 = 切换既有 `body` 类 + 复用既有入口，**不新增 Runtime / 不新增 Event / 不改变 AppState**。符合所有约束。
4. **避免两种反模式**：
   - ❌ 不应成为**常驻面板**（会污染 PanelManager 且违背 UI Consolidation「Galaxy 为视觉中心、Command Dock 为主入口」的收口）。
   - ❌ 不应成为**第二个运行时**（对话状态已安全地留在 `ZZChat` 闭包 + localStorage，无需升格为域模型）。

**设计立场**：Conversation = `chat-mode` 聚焦层，是「意图被执行」的**默认目的地**。从首页 Command Dock 下达的指令，自然地把 OS 从 HOME 推进到 WORKSPACE（chat-mode），对话在工作台中承接并展开。模式不变，但**进入对话的默认路径**被明确为「下达指令 → 进入 chat-mode」。

---

## 4. 相邻关系图（基于代码事实）

```
                 ┌─────────────────────────────────────────────┐
   首页 HOME      │  #osShell (Operation Layer)                  │
   (无 chat-mode) │   · Galaxy (视觉中心)                        │
                 │   · Command Dock #osDock (唯一主入口)         │
                 └──────────────────────┬──────────────────────┘
                                        │ 下达指令 / 点击 FAB (osChatFab)
                                        ▼
  工作台 WORKSPACE │  #app (z-index:50, 浮层)   ← chat-mode
   (chat-mode)    │   · #convList (左侧会话列表)                  │
                 │   · #chatArea (消息流 + 输入坞 #input)         │
                 │   · #tele (右侧遥测)                          │
                 └──────────────────────┬──────────────────────┘
                                        │ 共享同一发送链
                                        ▼
                        window.ZZChat.send()  ← 唯一对话后端
                                        │
            ┌───────────────────────────┼───────────────────────────┐
            ▼                           ▼                           ▼
   Timeline (只读 AppState)      Galaxy GEL (只读 AppState→      Hotspot (订阅
   执行过程投影                  GalaxyState) 节点生命周期       ZZChat.onUpdate 镜像)
```

- **Command Dock → Conversation**：入口派发者，非所有者。指令流入 `ZZChat.send`。
- **Conversation → Timeline**：两者解耦；共享上游 AppState 执行态，但各自投影（见 03 文档 Q3）。
- **Conversation → Galaxy**：不直接耦合；Galaxy 经 AppState 反映任务状态（见 03 文档 Q5）。
- **Conversation → Hotspot**：唯一外部耦合点——`hotspot.js:925` `zz.onUpdate(hsChatRender)` 把对话镜像进热点面板。

---

## 5. 红线校验（本模型零违反）

| 红线 | 本模型是否触碰 | 说明 |
|---|---|---|
| 禁止代码修改 | 否 | 纯设计文档 |
| 禁止幻想新 Runtime | 否 | 复用 `ZZChat` 闭包 + localStorage，无新运行时 |
| 禁止新增 Event | 否 | 仅复用既有 `body.chat-mode` / `zz:command` / `ZZChat.onUpdate` |
| 禁止改变 AppState | 否 | 对话状态保持 UI 局部，不进入 11 子树 |
| AI Presence 三唯一 | 否 | 未涉及 `avatar-state.js` / `refreshHud` / `ui2.css body[data-presence]` |

---

## 6. 下一步

本位置模型确认后，进入：
- **`02_CONVERSATION_STATE_MODEL.md`**：定义 Conversation Panel 的 Default / Attention / Active 三态（Q2）。
- **`03_HOME_WORKFLOW_DESIGN.md`**：回答 Q3（消息流↔Timeline 边界）、Q4（Command Dock↔Conversation）、Q5（Galaxy 任务反馈），给出首页工作流（Q1–Q5 收口）。

**▣ STOP · 待 Review。** 本文件为纯设计交付，未改动任何代码/CSS/JS/Runtime；未提交 Git。
