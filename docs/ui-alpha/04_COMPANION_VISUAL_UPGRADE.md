# 04 · Companion Visual Upgrade — 伴侣视觉升级

> AI OS UI Alpha Program v1.0 · Phase 4
> 身份：AI OS Experience Designer + Interaction Designer + Frontend UI Architect
> 执行模式：Audit → Design → Implement → Verify → Document → STOP
> 日期：2026-08-07
> 状态：✅ 完成（纯表现层 + 受控状态表现）· 🛑 STOP 等 Review

---

## 1. 当前问题（Audit）

### 1.1 Companion 当前承担什么（经代码实证）

| 维度 | 当前承担 | 证据 | 归类 |
|---|---|---|---|
| **AI 职责面** | 对话（cmd-bubble）/ AI 状态（badge/tip/状态机）/ 当前任务 / AI 建议（statusBubble）/ AI 主动提醒 + 执行反馈（notify） | `companion.js` `handleAction` + `05_COMPANION_RESPONSIBILITY.md` | ✅ AI Presence（保留） |
| **本地呈现控制** | 暂停动画 / 勿扰 / 隐藏小6 | `toggle-pause`/`toggle-dnd`/`hide` | ✅ 本地（保留） |
| **旧工具入口残留** | 左键快捷菜单含 6 个按钮（对小6说/当前任务/快速指令/暂停动画/勿扰/隐藏）；cmd-bubble 发送按钮为硬编码青色渐变；notify/菜单/气泡用裸 `rgba` 与硬分隔线 | `companion.html` `#quickMenu` / `companion.css` | ⚠️ 工具感/网页感来源 |
| **状态表达** | 核心 Avatar 已有 8 态（`avatar-state.js` 每态映射色 + `AvatarRenderer` 注入 SVG） | `avatar-state.js:22-29` | ✅ 但 chrome 不跟随 |

### 1.2 四类体验缺口（对应 G6「Companion 工具感」）

| Gap | 现象 | 根因（实测） | 严重度 |
|---|---|---|---|
| **菜单感** | 左键菜单=6 按钮面板，含硬 `1px` 分隔线（`.quick-menu-sep`）与系统控制项（暂停/勿扰/隐藏），读起来像"设置面板"而非"AI 在场" | 菜单 chrome 未与存在色统一，无生命感 | 🟡 中 |
| **按钮感** | cmd-bubble 发送键 `linear-gradient(180deg,#7fe3f0,#56d3e6)` 硬编码；菜单/notify 按钮 hover 为裸色 | 未走设计系统令牌 | 🟡 中 |
| **网页感** | badge/气泡/notify/菜单共 **58 处硬编码 `rgba`/`#`**，与 `ui2.css` 调色板脱节；box-shadow 用裸 `rgba(0,0,0,.5)` | `companion.css` 未加载 `ui2.css`（独立窗口），颜色散落 | 🔴 高 |
| **状态表达不足** | chrome（徽标/气泡/通知）是 `#avatar` 的**兄弟节点**，无法继承 Avatar 的 `--avatar-color` → 全 Companion 表面不随状态变色；且 `--motion-*`/`--ease-*`/`--dur-focus` **在 Companion 上下文从未定义** → 所有 `transition`/`animation` 引用它们的规则**静默失效**，Companion 呈现"瞬变/无呼吸" | 动效令牌缺失 + chrome 与状态色脱钩 | 🔴 高 |

> **关键发现（P4 核心 Bug）**：`companion.html` 不加载 `ui2.css`，而 `companion.css` 大量使用 `var(--motion-slow)`/`var(--ease-premium)`/`var(--dur-focus)` 却从未定义 → 这些声明在计算值阶段无效，整个 `transition`/`animation` 简写作废。这同时解释了"为什么桌宠 hover/出现/消失/完成回弹都没动画"——是 latent 动效失效，而非设计意图。

---

## 2. 设计目标（Design）

> **将 Companion 从「工具入口」升为「AI OS 的人格存在层」**——用户感觉"小6在这里"，而非"打开了一个页面"。

具体目标（不新增任何职责，仅视觉层 + 状态表现 + 交互反馈）：
1. **统一存在语言**：全 Companion 表面（Avatar + 徽标圆点 + 气泡顶线 + 通知边框 + 菜单/命令气泡描边）跟随当前 AI 状态色，强化"AI 正在 X"的在场感。
2. **7 态视觉契约**：Idle / Thinking / Executing / Waiting / Reminder / Completed / Error 每态定义**颜色 + 动画 + 反馈**；PLANNING（思考家族）与 OFFLINE（连接态）作为支撑态保留。
3. **去工具化**：菜单更柔（圆角+渐变分隔+hover 微位移+存在色提亮）、发送键改存在色、去除裸色与硬线，读感从"设置面板"转为"与 AI 交互"。
4. **修复动效**：在 Companion 本地补齐 `--motion-*`/`--ease-*`/`--dur-focus` 令牌（对齐 `ui2.css` 值），让呼吸/滑入/回弹/脉冲真正生效。
5. **克制陪伴**：Reminder 用温和琥珀脉冲环（"我有话要说"，非惊扰），遵守 `03_EXPERIENCE_PRINCIPLES` 的"安静在场/低打扰"。

---

## 3. 实现内容（Implement）

| 文件 | 改动 | 性质 |
|---|---|---|
| `companion.css` | **整体重写（保留全部选择器与 JS 钩子）**：① `:root` 新增存在色板 `--presence-*`（8 态，对齐 `avatar-state.js` META.color）+ 玻璃 chrome 令牌 `--companion-*`（集中定义，禁散落）；② 补齐动效令牌 `--motion-*`/`--ease-*`/`--dur-focus`/`--radius-*`；③ chrome 全部改走 `var(--companion-*)` 与 `var(--presence-color)`，描边 `color-mix(in srgb, var(--presence-color) 30%, …)` 跟随状态色；④ 每态 `--presence-color` 覆盖 + 7 态视觉契约（颜色/动画/反馈）+ 新增 `.companion-root--remind` 琥珀脉冲环；⑤ 菜单/气泡/通知/命令气泡去工具化（圆角、渐变分隔、hover 微位移、发送键改存在色）；⑥ 浅色主题同步令牌化 | 表现层（additive + 令牌化） |
| `companion.js` | ① `render()` 末尾向 `#companionRoot` 广播 `--presence-color`（chrome 跟随状态色，纯表现）；② `showNotification` 支持 `remind` 种类（琥珀 + 加 `companion-root--remind`）；③ `hideNotification` 清除 remind 类；④ `onProactiveMessage` 主动建议/目标由 `done` 改为 `remind`（仍经既有 `bridge.action` 链路，无新 API） | 受控表现层（仅视觉状态，无职责变更） |

### 3.1 七态视觉契约（落地映射）

| 用户态 | 数据源态 | 颜色（存在色板） | 动画 | 反馈 |
|---|---|---|---|---|
| Idle | `IDLE` | 沉静青 `#5fb3c8` | 呼吸 + 偶发眨眼 + 轻微观察 | 徽标小圆点常亮 |
| Thinking | `THINKING` | 靛蓝 `#8b9bff` | 双眼交替微动 + 核心轻摆 | 状态环靛蓝 |
| Executing | `EXECUTING` | 生机绿 `#56d364` | 核心脉冲 + 环流光 + 专注眯眼 | 绿光晕呼吸 |
| Waiting | `WAITING` | 暖琥珀 `#f0b35e` | 安静眨眼（"在场不消失"） | 琥珀描边 |
| Reminder | 主动推送（`remind` 通知） | 琥珀 `#e0a94f`（对齐 `--warn`） | 头像温和脉冲环（2.4s）+ 通知琥珀边 | 非惊扰，可一键忽略 |
| Completed | `COMPLETED` | 青绿 `#56d3a0` | 核心放大回弹 | 绿通知"✓" |
| Error | `ERROR` | 珊瑚红 `#ff6b6b` | 核心红色摇晃 | 红通知"!" |
| *(支撑)* PLANNING | `PLANNING` | 紫 `#c08bff` | 环旋转（思考家族） | — |
| *(支撑)* OFFLINE | `OFFLINE` | 冷灰 `#8a93a6` | 灰暗 + 缓慢漂浮 | — |

> PLANNING/OFFLINE 保留为既有真实态（来自 `avatar-state.js`），不纳入"7 主态"命名但视觉语言一致；未新增任何态。

### 3.2 红线合规边界

- **零职责变更**：`cmd-bubble` 仍经 `bridge.action` → 既有聊天/Command 链路；`quick-cmd`/`current-task` 仍经 `bridge.action` 转发主窗既有系统；Reminder 是既有"AI 主动提醒"职责的**视觉变体**（琥珀+脉冲），非新能力。
- **零 API/Tool/Menu 新增**：未新增菜单项、未新增按钮种类、未改动 `handleAction` 分支结构（仅 `showNotification` 增加 `remind` 视觉分支，沿用既有 `bridge.action` 调用）。
- **零 Runtime/Agent/Memory/Permission 改动**：`companion.js` 仅增"设置 CSS 变量"与"切 class"的纯表现语句；`avatar-state.js`/`avatar-renderer.js`/`app-state.js`/后端 **零改动**。
- **令牌同源**：Companion 独立窗口不加载 `ui2.css`，故在本地以 `--presence-*`/`--companion-*` 镜像 `ui2.css`/`DESIGN.md` 意图（数值对齐 midnight 调色板），未建第二套令牌体系。

---

## 4. 修改文件清单

| 文件 | 改动类型 | 行数级 |
|---|---|---|
| `xiao6-ui/companion.css` | 重写（结构保留，令牌化 + 存在语言 + 动效补齐） | ~580 行 |
| `xiao6-ui/companion.js` | 表现层增强（广播存在色 + remind 态） | +~12 行 |

> 未触碰：`companion.html`（DOM 结构/元素 id 全部保留，JS 钩子零改动）、`avatar-state.js`、`avatar-renderer.js`、`avatar-assets.js`、后端/`server.py`、Runtime/EventBus/Memory/Permission/Command Palette/Workspace/Capability。

---

## 5. Verify

| 检查项 | 结果 |
|---|---|
| `companion.css` 花括号平衡 | ✅ 158 / 158 BALANCED |
| `companion.js` 语法 | ✅ `node --check` 通过 |
| 所有 CSS 选择器与 `companion.js` 钩子一一对应 | ✅ 新增类 `cn-remind`/`companion-root--remind` 均由本任务 JS 引用；其余选择器原数保留 |
| chrome 硬编码 `rgba`/`#` 计数 | ✅ 58 → **9**（仅余面部黑瞳 + 阴影黑，对应 `ui2.css` 自身 `--elev-*` 阴影 `rgba(0,0,0,…)`，合理保留） |
| 动效令牌缺失修复 | ✅ `:root` 新增 `--motion-fast/.18s`/`--motion-base/.28s`/`--motion-slow/.45s`/`--ease-premium`/`--ease-soft`/`--dur-focus/.42s`；hover/滑入/回弹/脉冲恢复生效 |
| 存在色广播链路 | ✅ `render()` 设 `root --presence-color` → chrome 经 `var(--presence-color)` 跟随；per-state `:root` 覆盖保证降级正确 |
| 7 态视觉契约 | ✅ 7 主态 + PLANNING/OFFLINE 支撑态各有颜色/动画/反馈定义 |
| Reminder 态 | ✅ 主动推送经 `remind` → 琥珀通知 + 头像脉冲环；点击/超时清除 |
| 浅色主题 | ✅ 同步令牌化，对比度保留 |
| 减少动效偏好 | ✅ `@media (prefers-reduced-motion: reduce)` 保留，动画归零 |
| **Companion 没有新增职责** | ✅ 仅视觉/状态/交互表现；菜单项、命令链路、能力入口均未增删 |
| **没有替代 Command** | ✅ `cmd-bubble`/`quick-cmd` 仍走既有 `bridge.action`/Command 链路，Command Palette 唯一性未受影响 |
| **没有替代 Workspace** | ✅ Companion 为独立常驻表面，Workspace/Panel 零改动 |
| **没有破坏 Capability** | ✅ Capability 暴露/注册/展示零改动 |
| 红线：未改 Agent/Runtime/Memory/Permission/新增 API·Tool·Menu·功能 | ✅ 全部未触碰 |

> 注：本环境为本地浏览器 + http.server 模型，无 Electron 运行实例；交互行为经代码逻辑 + 选择器/事件链 + 令牌解析核对验证，未在实时浏览器截图（截图需人工 Review 时本地启动 `start-xiao6.bat` 验证 Electron 桌宠）。

---

## 6. 风险

| 等级 | 风险 | 缓解 |
|---|---|---|
| 🟢 低 | `--presence-color` 在 `render()` 每帧经 `root.style.setProperty` 写入，属轻量表现写，不影响任务状态真相 | 仅 CSS 变量；`AvatarState.deriveFromGlobals()` 仍为真值源，未缓存/改写 |
| 🟢 低 | 浅色主题下存在色（如青 `#5fb3c8`）与浅底对比需人工目检 | 已用 `color-mix` 提亮描边并保留文字深色令牌；建议 Review 时切浅色主题截图确认 |
| 🟡 中 | Reminder 脉冲环为新增视觉态，若主动推送频率高可能与"安静在场"原则轻微冲突 | 脉冲为 2.4s 缓动、低透明度、仅 amber；且遵守 DND（DND 下 `showNotification` 直接 return，不触发） |
| 🟢 低 | 动效令牌补齐后，此前"静默失效"的过渡现在会动——若 Review 觉得过动，可下调时长 | 时长对齐 `ui2.css` 标准值（.18/.28/.45s），符合设计系统家族 |

---

## 7. 红线与移交

- **本 Phase 红线零违反**：未新增功能/菜单/Capability/Tool/API；未修改 Agent/Runtime/Memory/Permission；未扩大 Companion 职责；未替代 Command/Workspace；未破坏 Capability。
- **移交 P8（AI Presence）**：本 Phase 已建立 Companion 侧统一"七态存在语言"（颜色/动画/反馈 + Reminder 脉冲），与 `03_EXPERIENCE_PRINCIPLES` 六态（主动/等待/安静/提醒/介入/退出）及 G1 缺口对齐；P8 可把同样的 `--presence-*` 语义扩展到 Galaxy 状态色点、Dock 常驻态等全 OS 存在层。
- **移交 P9（Release Polish）**：浅色主题下存在色对比、8 主题一致性可在 P9 统一验收。

---

## 8. 完成摘要

Phase 4 在**不新增任何职责**的硬约束下，把 Companion 从"工具入口"升为"AI OS 的人格存在层"：
- **统一存在语言**：全 Companion 表面（头像/徽标圆点/气泡顶线/通知边框/菜单描边）跟随当前 AI 状态色，用户一眼感知"小6正在思考/执行/等待/提醒"；
- **修复 latent 动效失效**：补齐 `--motion-*`/`--ease-*`/`--dur-focus` 令牌，呼吸/滑入/回弹/脉冲真正生效（此前因令牌未定义而静默失效）；
- **7 态视觉契约**：Idle/Thinking/Executing/Waiting/Reminder/Completed/Error 每态定义颜色+动画+反馈，Reminder 以温和琥珀脉冲体现"克制陪伴"；
- **去工具化**：菜单更柔、发送键改存在色、裸 `rgba` 从 58 处收敛至 9 处合理保留（面部/阴影黑），整体与 `ui2.css`/`DESIGN.md` 同源。

**🛑 Phase 4 完成，STOP 等 Review。**
