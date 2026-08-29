# 03 · Intent Line 设计（INTENT LINE DESIGN）

> **阶段**：UI-v3 Clean Reconstruction · Phase 1（Design Only）
> **依赖**：`00`（能力来源：#osDock / command-dock.sendText）/ `01`（Intent Layer）
> **目标**：把 Command Dock 重定义为**全屏唯一意图入口**——Intent Line。

---

## 1. Intent Line = 唯一输入，不是聊天框

旧版有多个输入入口：`.os-nav` 指令按钮、`.os-hero-actions` 对话按钮、`.os-dock` 输入框、语音按钮。v3 收敛为**一个**：Intent Line。

它**不是聊天页面**（红线：不产生 Chat 页面）。它是首页常驻的一行意图输入——用户说话，小6理解、编排、执行，结果回到 Context Layer。对话历史属于 `.app` 视图（按需 Overlay 唤起），不在首屏常驻。

---

## 2. 输入体验

### 2.1 位置与形态
- **位置**：底部居中，悬浮于 Context Layer 之下，视口宽度受限（max-width ≈ 720px，参考 Raycast 命令框的紧凑效率感）。
- **形态**：单条圆角输入 + 右侧发送/语音图标。**无面板边框、无标题栏、无背景块**——它是一条"浮在存在界面上的意图线"，不是一块"输入框卡片"。
- **视觉权重**：低于 AI Core（不抢中心），但高于 Context（用户一眼找到"我该在这说话"）。

### 2.2 渲染目标（复用，仅重定位）
- 复用 `#osDock`（`command-dock.js` 的渲染目标）→ 移除旧 `.os-dock-console-head` 面板外壳，仅留输入框本体。
- **发送逻辑不动**：`sendText(text)` → `dispatchEvent('zz:command')`，Enter 键 + 发送按钮原样保留（来自 `00` §2.4）。v3 只改其 CSS 定位与外观，**不碰 command-dock.js 一行**。

### 2.3 视觉（简洁 / 高级 / 科技感）
- 单行输入，字号略大（16–17px），占位符中等对比，输入时底边出现一条**状态色细线**（来自 `--core-color`，见 `02`）。
- 圆角克制（≈ 14px），无玻璃、无阴影；背景为极轻透明层（不形成卡片）。
- 右侧：语音图标（复用既有 voice-toggle）+ 发送箭头；图标细线风格，非实心按钮墙。

---

## 3. 状态反馈（按现有 AI Presence 切换文案，仅视觉/文案层）

复用 `avatar-state` 8 态 + `agent_state` 事件，**只改占位符文案与输入线颜色**，不新增事件、不改逻辑。

| 状态 | 占位符文案（Intent Line） | 输入线颜色 | 说明 |
|---|---|---|---|
| IDLE | 告诉我你的目标 | `#5fb3c8` | 引导用户开口 |
| THINKING | 正在理解你的意图… | `#8b9bff` | 小6在想 |
| PLANNING | 正在规划步骤… | `#c08bff` | 小6在排 |
| EXECUTING | 正在执行任务… | `#56d364` | 小6在干 |
| WAITING | 等你确认… | `#f0b35e` | 需用户决策 |
| ERROR | 需要你的确认 | `#ff6b6b` | 出错/需介入 |
| OFFLINE | 离线 · 无法接收 | `#8a93a6` | 不收输入 |

> 颜色来自 `avatar-state.color(state)`，文案逻辑由前端读取 `agent_state` 事件后设置占位符——**既不新造颜色也不新造事件**。

---

## 4. Goal 转换流程（意图 → 目标）

用户输入一句话后，链路由既有系统完成，v3 只负责"展示"：

```
用户输入（Intent Line）
   │ sendText() → dispatchEvent('zz:command')
   ▼
intent-gateway.js（既有）→ INTENT_RECEIVED
   ▼
Intent → Goal（Goal System 既有编排）
   ▼
GOAL_CREATED（既有领域事件，zz-events.js）
   ▼
├─ AI Core 状态：IDLE → THINKING → PLANNING → EXECUTING（02 §2）
└─ Context Layer「正在处理」流出现该 Goal（01 §3，取 /api/goals?status=active）
```

**v3 不改变**上述任何一步（Agent Runtime / EventBus / intent-gateway 均不动）。Intent Line 仅作为**入口与状态镜子**：用户输入 → 看到小6状态变化 → 在 Context 看到目标出现。

---

## 5. 反模式（明确不做什么）

- ✗ 不生成 Chat 页面（对话历史不常驻首屏）。
- ✗ 不保留多个输入入口（nav 指令按钮 / hero 对话按钮 隐藏）。
- ✗ 不把 Intent Line 做成"搜索框 + 结果下拉"的独立软件感（它是说话的地方，不是查东西的地方；查东西走 ⌘K Overlay）。
- ✗ 不新增事件、不改 command-dock 发送逻辑。
- ✗ 不恢复 Galaxy 首页作为意图背景。

---

## 6. 与旧 DOM 关系

| 旧元素 | v3 处理 |
|---|---|
| `.os-bottom .os-dock` 面板外壳 | 隐藏外壳，保留 `#osDock` 输入框 |
| `.os-dock-console-head`（"Intent Console"标题） | 移除（标题冗余，Intent Line 自解释） |
| `.os-hero-actions` 对话/指令/星图按钮 | 隐藏（多入口） |
| `.os-nav` 指令按钮 | 隐藏（入口统一到 Intent Line + ⌘K） |
| `command-dock.js::sendText` | **完全复用，不改** |

---

## 7. 验收（Intent Line 维度）

- [ ] 首屏只有一个输入框（Intent Line），无其他输入入口可见。
- [ ] 回车 / 发送按钮触发 `sendText`（行为不变）。
- [ ] 占位符随 `agent_state` 四态（IDLE/THINKING/EXECUTING/ERROR）切换文案与线色。
- [ ] 输入后，AI Core 状态变化、Context「正在处理」出现真实 Goal（数据真实）。
- [ ] 不产生 Chat 页面、不恢复 Galaxy。
- [ ] `command-dock.js` 发送逻辑零改动。

→ 下一文档 `04` 详述 Galaxy 替代方案：理解网络。
