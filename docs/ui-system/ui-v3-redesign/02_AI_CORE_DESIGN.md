# 02 · AI Core 设计（AI CORE DESIGN）

> **阶段**：UI-v3 Clean Reconstruction · Phase 1（Design Only）
> **依赖**：`00`（能力来源：#osCoreCanvas / avatar-state 8 态）/ `01`（Presence Layer）
> **目标**：把 AI Core 确立为 v3 首页**唯一视觉中心**——小6本人的载体。

---

## 1. AI Core = 小6本人，不是装饰

旧版把 AI Core 当作"英雄区 + 文案"，Galaxy 占中央。v3 反转：**AI Core 就是首屏**，Galaxy 退场。

AI Core 承载四件事（来自 P1.5 升级意图，但在此确立为 Presence 层的正式内容）：

```
        ◉  ← 化身（光核 / 呼吸环，随状态变色）
   ┌───────────────┐
   │  小6           │  ← 身份（始终可见，低对比标题）
   │  ● 在线 · 执行中 │  ← 当前状态（来自 avatar-state 8 态）
   │                │
   │  正在：推进「发布 v2」 │  ← 正在处理（一句，取自当前 Goal）
   │  下一步：告诉我你的目标 │  ← 下一步建议（一句，引导意图）
   └───────────────┘
```

---

## 2. 状态机（复用 avatar-state.js 8 态，不新造）

直接采用 `avatar-state.js` 的 META 作为**唯一权威**。v3 不定义任何新状态色。

| 状态 | 颜色 | 标签 | AI Core 行为（视觉） |
|---|---|---|---|
| IDLE | `#5fb3c8` | 待命 | 呼吸环慢速均匀，文案"告诉我你的目标" |
| WAITING | `#f0b35e` | 等待指令 | 呼吸环微顿，文案"等你确认" |
| THINKING | `#8b9bff` | 思考中 | 呼吸环加速、色晕扩散，文案"正在理解你的意图" |
| PLANNING | `#c08bff` | 规划中 | 环分裂为微弧（规划意象），文案"正在规划步骤" |
| EXECUTING | `#56d364` | 执行中 | 环转为行进光点，文案"正在执行任务" |
| COMPLETED | `#56d3a0` | 已完成 | 环闭合一次性脉冲，文案"刚完成一项" |
| ERROR | `#ff6b6b` | 异常 | 环红色微颤，文案"需要你的确认" |
| OFFLINE | `#8a93a6` | 离线 | 环暗淡静态，文案"离线" |

> **复用纪律**：颜色、标签**逐字取自 `avatar-state.js`**，v3 样式表只引用这些变量，不重新定义。状态派生逻辑（`avatar-state.js` 从 AppState 算 state）保持不变。

---

## 3. Presence 映射（状态 → 表现）

每态三件套：**光核色 + 呼吸节奏 + 一句话文案**。文案不写死在前端常量，而是由 `agent_state` 事件 + 当前上下文生成（见下）。

| 维度 | 映射规则 |
|---|---|
| **颜色** | `avatar-state.color(state)` → CSS 变量 `--core-color`（驱动光核、状态点、下一步建议高亮） |
| **节奏** | 状态 → 动画时长/幅度（IDLE 慢 4s，THINKING/EXECUTING 快 1.2s），由状态决定，不在 CSS 写死多套 |
| **文案** | 状态文案（待命/思考中…）来自 `avatar-state.label(state)`；"正在处理/下一步"来自真实数据（见 §5） |

**驱动链**（不新增事件）：
```
AppState(agents/execution) → avatar-state.derive() → {state,color,label}
                                              ↓
                          zz-events.js 既有 agent_state 事件
                                              ↓
                          AI Core 订阅 → 更新 --core-color + 文案 + 呼吸节奏
```

---

## 4. 动效（克制，≤400ms，目的导向）

参考 Apple 的克制 + Linear 的精确。AI Core 只有三类动效：

1. **呼吸（idle 常态）**：光核外环 4s 缓动扩张收缩，幅度极小（opacity 0.5→0.8），表达"活着"。不炫技、不闪烁。
2. **状态过渡（≤400ms）**：状态切换时，光核色 `transition: background-color 320ms ease-soft`，呼吸节奏平滑变速。无弹跳、无旋转特效。
3. **焦点微动（交互）**：用户 hover/点击 AI Core 时，光核轻微放大（scale 1.0→1.04，200ms），提示"可交互"。

**禁止**：星系旋转、粒子爆炸、3D 翻转、霓虹扫描线等"炫技动画"（旧 Galaxy 病灶）。

---

## 5. Core 内容数据来源（全部既有 API）

| Core 区块 | 数据 | 端点 | 呈现 |
|---|---|---|---|
| 身份 | 固定"小6" | 无（常量） | 低对比标题 |
| 当前状态 | `avatar-state` 派生 | AppState → agent_state | 状态点 + 标签 |
| 正在处理 | 当前活跃 Goal 标题 | `/api/goals?status=active` 首条 | 一句话"正在：<title>" |
| 下一步建议 | 上下文生成 | 本地逻辑（非新数据源） | 一句话引导（IDLE→"告诉我你的目标"；ERROR→"需要你的确认"） |

> 与 P1.5 的"能力摘要"区别：v3 **不在 Core 展示纯数字**（如"知识 46"）。知识以**语义化摘要**出现在 Context Layer（见 `01` §3 / `05`），Core 只承载身份+状态+正在处理+下一步。

---

## 6. 交互（点击原地展开，不离开首页）

- AI Core 可点击 → 原地展开一个**轻量浮层**（非新页面），展示：当前状态详情、正在处理的 Goal 进度、最近记住的事。
- 浮层关闭即回到存在界面。**不触发 `body.chat-mode/universe-mode` 等模式切换**（这是旧三软件拼接的技术根因，v3 废除）。
- 浮层内容全部来自既有 API，零新增运行时。

---

## 7. 与旧 DOM 的关系

- **复用**：`#osCoreCanvas`（avatar-renderer 绘制目标）保留；`.os-core-state` 文案通道保留升级。
- **重定位**：旧 `.os-core` 在角落英雄区 → v3 升为**视口中心**，占主视觉权重。
- **隐藏**：`.os-hero-title/sub/desc/actions` 旧营销文案与三按钮隐藏；Core 内仅留身份+状态+两句话。
- **不新增**：不新增 DOM 结构类型；AI Core 仍是单个容器 + 画布 + 状态文本。

---

## 8. 验收（AI Core 维度）

- [ ] 首屏打开，AI Core 在视口几何中心，视觉权重最高。
- [ ] 状态色与 `avatar-state` 8 态逐字一致。
- [ ] 状态切换时色/文案/呼吸平滑过渡（≤400ms），无炫技动画。
- [ ] "正在处理"显示真实当前 Goal 标题。
- [ ] 点击 Core 原地展开浮层，关闭后回到存在界面，无模式类切换。
- [ ] Galaxy 不在 Core 周围出现。

→ 下一文档 `03` 详述 Intent Line（唯一输入入口）。
