# 03 · 首页工作流设计（Home Workflow Design）

> **身份**：AI OS UX Architect · UI-5C-0
> **承接**：`01` 位置模型（Conversation = chat-mode 聚焦层）＋ `02` 状态模型（Default/Attention/Active 三态）
> **约束**：禁止代码/CSS/JS/Runtime 修改；禁止幻想新 Runtime；禁止新增 Event；禁止改变 AppState。全部基于现有代码。

---

## 0. 一句话总结

首页（HOME）以 **Galaxy 为视觉中心、Command Dock 为唯一主入口**；下达指令后 OS 自然推进到 **WORKSPACE（chat-mode）**，对话在该聚焦层承接并展开；**消息流（对话记录）** 与 **Timeline（执行过程）** 是两个解耦的投影轴；**Command Dock 是入口派发者、Conversation 是目的地与所有者**；**Galaxy 经既有 AppState→GalaxyState→GEL 管线反映任务生命周期**，无需对话推送新信号。

---

## 1. Q3 · 消息流（Conversation）与 Timeline 的职责边界

### 1.1 现有事实（审计）

- **消息流（ZZChat / Conversation）**：`app.js:130–258` 会话管理、`L369–397 addMessage`、对外 `window.ZZChat`（L2457）。内容 = 用户/小6轮次（role+content），存于闭包 `state.messages` + `localStorage` 历史。**是"说了什么"的对话记录。**
- **Timeline（ExecutionTimeline）**：`execution-timeline.js:11–17` 五阶段（理解任务→制定计划→调用工具→执行→完成）；`L22–45` 只读 `AppState.intents/goals/agents` + `ExecutionChannel`；`L128–141` 订阅 AppState/ExecutionChannel。**是"小6正在怎么做"的执行叙事。**
- **解耦证据**：`execution-timeline.js` **不订阅 `chatUpdateCbs`**（app.js:39 定义的对话回调数组，仅 `hotspot.js:925` 订阅）。二者目前已是独立投影。

### 1.2 边界定义

| 维度 | 消息流（Conversation） | Timeline（Execution） |
|---|---|---|
| 回答的问题 | "我们说了什么 / 小6回了什么" | "小6正在如何推进这个任务" |
| 数据来源 | `ZZChat` 闭包 `state` + localStorage | `AppState(intent/goal/agent)` + `ExecutionChannel` |
| 粒度 | 对话轮次（turn） | 执行阶段（phase）/ 步骤（step） |
| 生命周期 | 跨会话持久（历史可归档/删除） | 单次任务瞬时（任务完成即回落 idle） |
| 呈现 | `#messages` 气泡流 | `os-tl-track` 五阶段条 + 步骤文本 |
| 订阅方 | hotspot 镜像（`onUpdate`） | 自身只读投影，无下游 |

### 1.3 设计立场

- **保持解耦，不合并**。消息流是"意图与结果的对话层"，Timeline 是"执行过程的观测层"。二者是同一任务的两个镜头，不是同一事物的两种格式。
- **不重复"进度"**。风险点：若对话气泡里写了"正在调用工具…"而 Timeline 也画阶段条，会冗余。裁决：
  - **Timeline** = 结构化执行阶段（机器/状态视角），宜在 WORKSPACE（chat-mode）伴随消息流显示（`ui2.css:1658–1659` 已规定 `#runtime-viz`/`#execution-monitor` 仅 chat-mode 出现）。
  - **消息流** = 自然语言 narration（小6用人类语言描述它在做什么），是 Timeline 的"人话版"，不抢 Timeline 的结构职责。
- **首页只留 Timeline 的轻量态**：UI Consolidation 已规定首页 `os-timeline` 在 idle 时收口为一行（`execution-timeline.js:96 .is-idle`），消息流在首页整体隐藏（`#app` `visibility:hidden`）。二者在首页不冲突——一个轻、一个无。

> 边界红线：**不新增事件**让消息流去驱动 Timeline，也不让 Timeline 反向写消息流。它们共享上游 `AppState` 执行态已是足够对齐点（同一任务既产生对话轮次，也产生执行阶段），无需新增耦合通道。

---

## 2. Q4 · Command Dock 与 Conversation 的关系

### 2.1 现有事实（审计）

- **Command Dock**（`command-dock.js`）：首页常驻于 `#osDock`（`index.html:155`，在 `#osShell` Operation Layer）。五种输入：文本/语音/拖文件/截图/快捷命令。`sendText`（L17–24）把文本写入 `#input`/`#btnSend`，或兜底派发 `zz:command` 事件。本质是**统一输入分发器**。
- **Conversation 输入坞**：`#chatArea footer.dock` 内的 `#input`/`#btnSend`（`index.html:378–383`），仅 chat-mode（`#app` 显形）可见。
- **共享后端**：Command Dock 的 `sendText` 最终落到 `#input`/`#btnSend` → `ZZChat.send`；二者是**两个输入面、一个对话后端**。

### 2.2 关系模型

```
   首页（无 chat-mode）                工作台（chat-mode）
   ┌──────────────┐                  ┌──────────────────────┐
   │ Command Dock │──写入 #input──▶  │ #chatArea 输入坞      │
   │ (#osDock)    │  或 zz:command   │ (#input/#btnSend)     │
   │ 唯一主入口    │                  │ 成为主输入            │
   └──────┬───────┘                  └──────────┬───────────┘
          │ 下达指令                             │
          └──────────▶ openChat() → chat-mode ──┘
                              │
                              ▼
                   window.ZZChat.send()  ← 唯一对话后端
```

- **Command Dock = 入口派发者（Entry Dispatcher）**，不是对话所有者。它把任意来源（文本/语音/文件/截图/快捷）归一为"一条指令"，送进对话后端。
- **Conversation = 目的地与所有者（Destination & Owner）**。它持有会话、消息流、历史；Command Dock 不持有任何对话状态。
- **模式切换时的视觉让位**：chat-mode 下 `#osShell`（含 Command Dock）`opacity:.32; blur(6px); pointer-events:none`（`ui2.css:939`）→ Command Dock 退为虚化背景，对话输入坞成为主输入。**二者非竞争关系，是同一漏斗的两段**。

### 2.3 设计立场

1. **Command Dock 永远可用**。即使在 Galaxy/工作台，用户也始终有一条"下达指令"的通道（首页是 `#osDock`，对话中是 `#input`）。这是"小6始终可被指挥"的体感保障。
2. **下达指令 = 进入对话的自然路径**。从 Command Dock 发的指令，应让 OS 从 HOME 推进到 WORKSPACE（chat-mode），该指令作为 user turn 落入消息流。即"发命令"与"开对话"是同一动作的两面，不分裂。
3. **不复制逻辑**。Command Dock 不维护会话列表、不渲染气泡；它只调用既有入口（`#input`/`#btnSend` 或 `zz:command`）。复用 `ZZChat.send`，**不新增第二个发送实现**。
4. **语音/文件/截图**在两种输入面统一：Command Dock 的语音/截图按钮派发 `zz:voice-toggle`/`zz:dock-screenshot` 等既有事件，最终仍汇入对话后端。Conversation 自身 `#chatArea` 内的 mic/image/screen 按钮（`index.html:366–377`）是同一能力的"工作台版"入口。

---

## 3. Q5 · Galaxy 如何参与任务反馈

### 3.1 现有事实（审计）

- **Galaxy Experience Layer（galaxy-experience.js）**：纯表现 + 受控交互（DECISION_004 / Golden State 红线-5）。`L22–28` 只读 `AppState.getFocus()` + `GalaxyState`；`L31–46` 节点类型标签（core/goal/agent/task/memory/knowledge/intent）+ 生命周期色与中文标签（Dormant/Created/Running/Thinking/Waiting/Completed/Failed/Archived）；`L90–122` 渲染聚焦节点卡。
- **"进入"动作**：`_enterCapability`（L50–61）路由到 `PanelManager.openCapability('capabilities')`，**不改导航协议、不新增 Capability**。
- **关键约束**：galaxy-experience.js **完全不读 Conversation / chatUpdateCbs**。它只认 AppState→GalaxyState 管线。

### 3.2 任务反馈的既有通道（无需新事件）

Galaxy 参与任务反馈的**唯一合规通道**是既有的：

```
AppState (intents/goals/agents 生命周期)
        │ 既有事件契约（DOMAIN+SYSTEM）
        ▼
GalaxyState.getNode(id).state  ← 节点生命周期
        │ 既有 onNodeChange 订阅 (galaxy-experience.js:134)
        ▼
GEL 节点卡 (状态点 + 中文标签 + 描述) + universe-mode 星系可视化
```

- 当某任务运行：`goal` 轨道呈 `Created/Running`、`agent` 卫星呈 `Thinking/Running`、`task` 节点呈 `Running`/`Completed`（KIND_LABEL 已含 `task:任务节点`、`intent:意图流`）。
- 这与 **Timeline 共享同一上游 `AppState` 执行态**——所以"对话所触发的任务"，其进度**已经**通过 Galaxy 节点生命周期自然反馈到空间层。**对话不需要、也不允许直接推送 Galaxy 信号**（那会新增事件/改 AppState，违反红线）。

### 3.3 设计立场

1. **Galaxy 的任务反馈 = 节点生命周期可视化**，由 AppState 驱动，与对话解耦。这是当前架构已就绪的能力，应**沿用而非扩展**。
2. **不新增"对话节点"或"对话→Galaxy 事件"**。任何让对话直接点亮 Galaxy 的设想都需突破"禁新增 Event / 禁改 AppState"红线，故否决。
3. **增强方向（零架构代价）**：在 chat-mode 下，Galaxy 已通过 `ui2.css:947` 降为 World Layer（`brightness(.46)`）；若某 agent 节点处于 `Running/Thinking`，其节点卡（GEL）本就会显示对应状态色——这已是对话进行时的空间反馈。可在设计上明确"对话进行中，Galaxy 中对应执行节点高亮"的**预期行为**，但实现仍走既有管线。
4. **聚焦联动（可选、零新事件）**：当用户在对话中要求"查看能力/目标"时，复用既有 `PanelManager.openCapability`（galaxy-experience.js:52），把空间入口与对话上下文连接——这是路由，不是新信号。

---

## 4. 首页工作流（基于现有导航脊柱）

### 4.1 五个导航态（syncNav, index.html:1495–1504）

| 态 | body 类 | 主视觉 | 主输入 |
|---|---|---|---|
| HOME | 无 | Galaxy + Command Dock | Command Dock `#osDock` |
| GALAXY | `universe-mode` | 宇宙视图（开发者/空间） | 同 HOME（Dock 虚化） |
| COMMAND | `cp-mode` | 命令面板浮层 | 命令面板输入 |
| WORKSPACE/ASSISTANT | `chat-mode` | `#app` 浮层（对话+遥测） | `#chatArea` 输入坞 |
| SETTINGS | settings 面板开 | 设置面板 | 设置内输入 |

Conversation 占据 **WORKSPACE/ASSISTANT** 一席，与 GALAXY 对称。

### 4.2 典型首页→对话流（不新增任何机制）

```
[HOME] Galaxy 为心 · Command Dock 唯一入口
   │ 用户于 Command Dock 输入指令 / 点语音 / 拖文件
   ▼
Command Dock.sendText → #input/#btnSend → ZZChat.send
   │ openChat() 自动加 chat-mode（或用户点 osChatFab）
   ▼
[WORKSPACE] #app 浮起(z50) · osShell 虚化 · 对话承接
   │ · 消息流：user turn 落入 #messages（S1 Attention→S2 Active）
   │ · Timeline：AppState 执行态驱动五阶段条（同屏）
   │ · Galaxy：对应 agent/goal 节点呈 Running/Thinking（空间背景降权）
   ▼
小6生成完成（state.streaming=false）
   │ scheduleCloseChat 5s 无交互 → 历史收起（S1→S0）
   │ 用户可点 HOME/导航回 Galaxy，或继续对话
   ▼
[HOME / GALAXY] 回到空间中心，对话在后台保留（localStorage 历史）
```

### 4.3 设计要点

- **首页不强制展示对话**。对话是"被召唤"的聚焦层（S0 默认隐藏），符合 UI Consolidation「Galaxy 视觉中心 + Command Dock 主入口」收口。
- **指令即入口**：从首页任意输入通道下达的指令，都会自然把 OS 推入 WORKSPACE，对话承接。用户无需先"打开聊天"再说话。
- **三态贯穿全程**：S0（首页隐藏/工作台收起）→ S1（历史展开/新消息）→ S2（流式/输入/悬停活跃），全程由 `02` 模型派生信号驱动。
- **多轴同屏不打架**：消息流（对话层）+ Timeline（执行层）+ Galaxy（空间层）在 WORKSPACE 共存，但各自由各自上游投影，互不写对方。

---

## 5. 红线校验（本设计零违反）

| 红线 | 是否满足 | 证据 |
|---|---|---|
| 禁止代码修改 | ✅ | 纯设计文档 |
| 禁止幻想新 Runtime | ✅ | 复用 `ZZChat` 闭包 + `PanelManager` + `GalaxyState`，无新运行时 |
| 禁止新增 Event | ✅ | 仅复用 `chat-mode` / `zz:command` / `zz:voice-toggle` / `ZZChat.onUpdate` / AppState 既有契约 |
| 禁止改变 AppState | ✅ | 对话态留 UI 局部；Galaxy 走既有 AppState→GalaxyState 管线，不新增写入口 |
| AI Presence 三唯一 | ✅ | 未触碰 `data-presence` / `refreshHud` / `avatar-state.js` / `ui2.css` 颜色权威 |
| 事件合约未扩张 | ✅ | DOMAIN=71/SYSTEM=8 不变 |

---

## 6. UI-5C-0 收口结论

- **Q1**：Conversation 应继续作为 **chat-mode 模式**（与 universe-mode 对称），非面板、非常驻控件、非新运行时。✅
- **Q2**：三态 **Default / Attention / Active**，全部由既有 DOM class + 闭包变量派生，不新增存储/事件。✅
- **Q3**：消息流（对话记录）与 Timeline（执行叙事）**解耦双轴**，共享上游 AppState，不合并、不重复进度。✅
- **Q4**：Command Dock = **入口派发者**，Conversation = **目的地与所有者**；两输入面共享 `ZZChat.send` 单一后端。✅
- **Q5**：Galaxy 经既有 **AppState→GalaxyState→GEL** 管线反映任务生命周期，对话不直推 Galaxy 信号（禁新增事件）。✅

**▣ STOP · 待 Review。** 三份文档（`01`/`02`/`03`）均为纯设计交付，未改动任何代码/CSS/JS/Runtime；未提交 Git。下一步须经用户 Review 决定是否进入实现阶段。
