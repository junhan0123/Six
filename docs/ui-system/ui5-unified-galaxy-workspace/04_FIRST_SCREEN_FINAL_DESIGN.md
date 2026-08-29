# UI-5 · First Screen Final Design（04_FIRST_SCREEN_FINAL_DESIGN.md）

> 阶段：UI-5 · Design（仅设计，零代码改动）
> 设计原则：① Galaxy=World Layer ② Workspace=Operation Layer ③ Chat 入 Command Dock ④ Navigation=Capability Focus
> 验收目标（沿用 UI-4D-1）：1 秒见世界 · 5 秒理解 · 30 秒首意

---

## 一、第一屏设计目标

打开即进入**一个统一空间**：活 Galaxy 作为世界背景铺满屏，Operation Layer 以半透毛玻璃浮于其上，Command Dock 常驻底部作为唯一意图入口。无「首页/聊天页/宇宙页」之分。

---

## 二、第一屏 z-stack 构成（自上而下视觉层）

```
┌─────────────────────────────────────────────┐
│ Overlay Layer（默认收起，按需显）              │  z≥20  Palette / Settings / gx-* / Voice
├─────────────────────────────────────────────┤
│ Operation Layer  #osShell (z5)  半透毛玻璃      │
│   ├ HUD（顶，94）         品牌 · 状态 · 工具 · 时钟 │
│   ├ Hero（左中，119）      身份英雄 · 3 芯片(改聚焦) │
│   ├ Side（右，136）        Capability Matrix + Insight │
│   └ Bottom（底，148）      Timeline(149) + Command Dock(153) │
├─────────────────────────────────────────────┤
│ World Layer  #solarCanvas(73)+.galaxy-veil(75) │  z0/1  活 Galaxy 恒为背景
└─────────────────────────────────────────────┘
```

> 三层**永远同屏**。Galaxy Focus 时 World 推前、Operation 推后（dim），不隐藏任一层。

---

## 三、Galaxy 位置（World Layer · 背景）

- 锚点：`#solarCanvas`（index.html:73）+ `.galaxy-veil`（index.html:75），常驻于 `.os-shell`(z5) 之下。
- 第一屏即见活 Galaxy 充满背景 → 满足「1 秒见世界」。
- Galaxy Focus（`zz-galaxy-focus`）时：World 提亮/变焦推前，`gx-status/gx-card/gx-hint`（index.html:164/168/179，来自 `#universeView`）浮于活 Galaxy 之上，Operation Layer 仅 dim。

---

## 四、Intent 入口位置（Command Dock · 底部常驻）

- 锚点：`#osDock`（index.html:153-155，`data-spatial-layer="operation"`），位于 `.os-bottom` 底部操作条。
- **唯一意图入口**：所有文字/语音意图统一进入 Command Dock（Global AI Intent Entry）。
- 左导航 `workspace` 与 Hero `对话` 芯片均改为「聚焦 Command Dock」，不再换页。
- 底部与 Timeline 并列（index.html:148-157），常驻可见 → 满足「30 秒首意」。

---

## 五、Panel 位置（Operation Layer 内）

| Panel | 锚点 | 位置 |
|---|---|---|
| HUD（状态/工具/时钟） | index.html:94-116 | 顶部固定 |
| Hero（身份英雄） | index.html:119-133 | 左中 |
| Capability Matrix | index.html:136-140 | 右侧 `os-side` |
| Insight 主动建议 | index.html:141-144 | 右侧 `os-side` |
| Conversation Panel（重寄宿 #app） | index.html:257 | Operation Layer 内（右/底，Implement 定形态） |
| Context Drawer（按需） | `osContextToggle`(100) | 右栏抽屉（UI Consolidation 已降级） |

所有 Panel 是**同一空间内的功能面**，非独立页面。

---

## 六、Timeline 位置（底部）

- 锚点：`#osTimeline`（index.html:149-151），位于 `.os-bottom` 底部操作条左侧，与 Command Dock 并列。
- 常驻显示执行时间线，不随焦点态消失（因 Operation Layer 永不被 `display:none`）。

---

## 七、合并后第一屏 vs 现状对比

| 维度 | 现状（审计） | 统一后（设计） |
|---|---|---|
| 屏内共存层 | 仅 1 层（其余被硬隐藏） | World + Operation + Overlay 三层同屏 |
| Galaxy 可见性 | 仅 universe-mode 时（且为不透明页重做） | 恒为活背景 |
| 聊天入口 | 独立 chat-mode 全页 | Command Dock 统一意图入口 |
| 导航心智 | 换页（3/6 按钮） | Capability Focus（不切页） |
| 第一屏 1/5/30s | 需切到 chat/universe 才「做事」 | 打开即空间，Dock 常驻首意 |

---

## 八、红线符合性

| 红线 | 满足 |
|---|---|
| 不修改 Backend / Agent / AppState / EventBus / solar-system.js | ✅ 仅 CSS/HTML 重壳 + 导航路由 |
| 不新增事件 / 第二套状态 | ✅ body 类 + syncNav 单一推导 |
| 保护 AI Presence 三唯一 | ✅ 只消费 `body[data-presence]` |
| 第一屏 1/5/30s | ✅ Galaxy 恒背景 · Hero 文案 · Dock 常驻 |

---

> ▣ **STOP — 本阶段为 Design Only，未修改任何代码。等待 Review 与 Implement 放行。**
