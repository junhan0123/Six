# Button System Audit — Xiao6 Component System Sprint v1.0 · Phase 1 (Task A)

> **Sprint**: Component System Implementation Sprint v1.0 — Phase 1
> **Task**: A — Button System Audit
> **执行身份**: Design System Architect (Diana) / Senior Frontend Engineer
> **日期**: 2026-08-05
> **执行模式**: Audit → Plan → Execute → Verify → Report → STOP
> **纪律红线**: 仅 Primitive 收敛（Button + Panel）；仅令牌/别名层，零视觉/行为变化；禁改 HTML/JS 逻辑；禁新增功能；禁机械合并类名（留 Review 门控）；所有改动须可回滚、可静态验证（本环境无法启动 Electron GUI 做像素级验证）。

---

## 1. 审计范围与方法

**扫描对象**（显式路径 `G:/xiao6/xiao6-ui`，规避 Glob 对 `G:/` 返回空的 quirk）：

| 维度 | 内容 |
|------|------|
| CSS 类定义 | `ui2.css` / `styles.css` / `premium.css` / `companion.css` / `execution-channel.css` / `runtime-viz.css` |
| 静态 HTML 使用 | `index.html` / `mobile-app.html` / `companion.html` / `selfcheck.html` / `weather-modal-preview.html` |
| JS 动态生成 | 全仓 `*.js`（`app.js` / `command-dock.js` / `hotspot.js` / `memory.js` / `memory-panel.js` / `scene.js` / `weather.js` / `sysmon.js` / `terminal-stream.js` / `tasks.js` / `onboarding.js` 等） |

**判定标准**：`button` 元素 / `.btn*` 类 / `button-like`（带 `cursor:pointer` 且承担点击动作的无语义 `<div>` 或 `<button class="...">`）均计入。

---

## 2. 统计摘要

| 指标 | 数量 |
|------|------|
| 独立按钮类族（class family） | **34** |
| 其中：已收口到令牌/别名（值单一来源） | 2（`.btn-new`、`.onb-next`） |
| 其中：规范基准类（目标天花板） | 1（`.btn` + 4 变体） |
| 其中：OS/Dock/专属保留类（按 DESIGN.md §4.1 刻意保留） | 4（`.os-dock-btn`、`.os-hud .os-tools button`、`.os-chat-fab`、`.pt-exec`） |
| 其中：Feature 专属动作按钮（散布、未统一） | 27 |
| 重复 CSS 定义（代码异味，非功能问题） | 3 处（`.wx-mode-btn`×2、`.wx-exit-btn`×2、`.ts-exit-btn`×2） |
| 涉及 CSS 文件 | 3（`ui2.css`、`styles.css`、`premium.css`） |
| 涉及 HTML 文件 | 2 主用（`index.html`、`mobile-app.html`）+ 3 辅 |
| 涉及 JS 文件（动态生成按钮） | 15+ |

**结论**：按钮「多套实现」问题真实存在，但**绝大多数属于刻意变体**（CTA 形状、Dock 结构、Feature 专属配色），强制机械合并 = 改视觉方向 = 撞红线。Phase 1 正确策略 = **令牌/别名收口 + 基准类完善**，类名机械合并一律递延 Review 门控（需 GUI 验证）。

---

## 3. 分类体系

| 分组 | 含义 | Phase 1 处置 |
|------|------|--------------|
| **G1 规范基准** | `.btn` 四变体，单一来源天花板 | 已建（ui2.css:591）；补 `:disabled` |
| **G2 遗留 CTA** | `.btn-new` / `.onb-next`，渐变收口到令牌 | 值已单源；类名不合并（视觉方向特殊） |
| **G3 OS/Dock 专属** | 结构特殊，按 DESIGN.md 保留 | 保留，不收敛 |
| **G4 Feature 动作** | 27 个散布按钮，近重复 | 仅记录；机械合并递延 Review |

---

## 4. 完整审计表

> 列说明：**定义** = CSS 类定义位置；**使用** = HTML 静态 / JS 动态位置；**旧实现** = 现状摘要；**目标实现** = DESIGN.md / ui2.css 规范；**状态** = 收敛情况；**风险** = 机械合并风险等级（🟢低 / 🟡中 / 🔴高）。

### G1 — 规范基准（目标天花板）

| 类 | 定义 | 使用 | 旧实现 | 目标实现 | 状态 | 风险 |
|----|------|------|--------|----------|------|------|
| `.btn` / `.btn.primary` / `.btn.ghost` / `.btn.danger` | `ui2.css:591-601`；`DESIGN.md §4.1:94-112` | `mobile-app.html:66,76` | inline-flex，pad 8/18，radius `var(--r-md)`(=16)，font 13/600，bg `accent 16%`，border `accent 45%`；hover/active 已定义 | 同上（规范已落地） | ✅ 已收敛 | 🟢 |
| `.btn:disabled`（缺失） | — | 无 | **无 disabled 规则**（`.send-btn:disabled` 单独存在 `styles.css:498`） | 补 `opacity:.5; cursor:not-allowed; transform:none` | ⚠️ 缺口（Task B 补） | 🟢 |

### G2 — 遗留 CTA（值单源，类名保留）

| 类 | 定义 | 使用 | 旧实现 | 目标实现 | 状态 | 风险 |
|----|------|------|--------|----------|------|------|
| `.btn-new` | `styles.css:84-93`（+`:547` Dock 46×46）；`premium.css:83-84` | `index.html:225`（#btnNew）；`index.html:1187/1227/1236`（配 `.onb-next`） | pad 11，radius **11**，font **15/600**，letter-spacing **1px**，bg `var(--btn-rail-bg)`（令牌已收口），hover glow+位移 | 值已单源；类名不合并（形状/字号为刻意 CTA 方向） | ✅ 值单源；类名递延 | 🔴 |
| `.onb-next` | `premium.css:221-229` | `index.html:1187/1227/1236` | pad 11/26，radius **999（胶囊）**，bg `var(--btn-pill-bg)`（令牌收口），color `#eafdff` | 值已单源；胶囊形状刻意 | ✅ 值单源；类名递延 | 🔴 |

### G3 — OS / Dock / 专属保留（按 DESIGN.md §4.1:116 保留）

| 类 | 定义 | 使用 | 旧实现 | 目标实现 | 状态 | 风险 |
|----|------|------|--------|----------|------|------|
| `.os-dock-btn`（+.listening/.send） | `ui2.css:443-451` | `command-dock.js:29-34`（5 实例） | 38×38，radius 10，scoped `.os-dock` | 保留（结构特殊） | ✅ 保留 | 🟡 |
| `.os-hud .os-tools button` | `ui2.css:264-269` | HUD 注入 | 32×32，radius 9 | 保留 | ✅ 保留 | 🟡 |
| `.os-chat-fab` | `ui2.css:480-487` | 聊天 FAB | 52×52，radius 16，spring hover | 保留 | ✅ 保留 | 🟡 |
| `.pt-exec` | `ui2.css:378-384` | 主动通知 toast | 通知执行专属 | 保留（DESIGN.md 明示） | ✅ 保留 | 🟡 |

### G4 — Feature 专属动作按钮（散布、未统一）

| 类 | 定义 | 使用 | 旧实现 | 目标实现 | 状态 | 风险 |
|----|------|------|--------|----------|------|------|
| `.tts-stop-btn` | `styles.css:186-193` | `index.html:269` | 红色 hover 停止播报 | 保留（单用、辨识度高） | 记录 | 🟢 |
| `.mic-btn` | `styles.css:479-498`(+`:3384`) | `index.html:298-307`（4） | 46×46，radius 12，recording 态 | 保留（图标按钮）；形状与 `.send-btn` 重复可后续共享 | 记录 | 🟢 |
| `.send-btn` | `styles.css:493-498` | `index.html:313` | 46×46，radius 12，深色 bg，disabled | 保留；disabled 已自管 | 记录 | 🟢 |
| `.wx-open-btn` | `styles.css:2303` | `index.html:273` | 共享基样 `:2266` + `--bc:#5EB3FF` | 与另 4 个 rail 按钮可并为一族 | 记录 | 🟡 |
| `.hs-open-btn` | `styles.css:2302` | `index.html:274` | 共享基样 + `--bc:cyan` | 同上 | 记录 | 🟡 |
| `.profile-open-btn` | `styles.css:2308` | `index.html:284` | 共享基样 + `--bc:#F472B6` | 同上 | 记录 | 🟡 |
| `.more-open-btn` | `styles.css:2309` | `index.html:276` | 共享基样 + `--bc:amber` | 同上 | 记录 | 🟡 |
| `.settings-open-btn` | `styles.css:2738-2739` | `index.html:285` | 共享基样 + `--bc:#22D3EE` + `.active` 渐变 | 同上（active 态特殊） | 记录 | 🟡 |
| `.mem-btn`（+.mem-danger/.mem-close/.mem-archive/.mem-restore/.on） | `styles.css:2390-2460` | `index.html:408-415`；`memory.js:252-557`；`memory-panel.js` | 已成族（修饰符齐全） | 保留（已良好收敛） | ✅ 已族化 | 🟢 |
| `.settings-save-btn`（+.danger/.settings-row-btn） | `styles.css:2783-2786`；`.danger` `premium.css:129-138` | `index.html:495-1110`（≈18 处） | pad **8/18**（与 `.btn` 一致），radius **10**（≠16），border `line-strong`，hover cyan+glow | `.btn` / `.btn.danger` | 记录（广泛使用，合并=HTML 改动+视觉位移） | 🔴 |
| `.speak-btn` | `styles.css:376-379` | `app.js:374,1989` | 30×30，radius 8 | 保留 | 记录 | 🟢 |
| `.appr-btn`（+.appr-approve/.appr-reject） | `styles.css:2684-2685` | `app.js:907-908` | pad 10，radius 10 | 保留 | 记录 | 🟡 |
| `.sc-media-btn` | `styles.css:429-431` | `scene.js:55` | pad 9/16，radius 11，amber hover | 保留 | 记录 | 🟢 |
| `.sc-submit` | `styles.css:457-459` | `scene.js:147` | pad 9/16，radius 11 | 保留 | 记录 | 🟢 |
| `.hs-chat-mic` | `styles.css:786-793` | `hotspot.js` | 复用 mic 模式（dup of `.mic-btn`） | 保留 | 记录 | 🟢 |
| `.hs-exit-btn` | `styles.css:1024-1041` | `hotspot.js:70,756` | 退出按钮 | 保留 | 记录 | 🟢 |
| `.hs-refresh-btn` | `styles.css:1043-1060` | `hotspot.js:69,757` | 刷新+spin | 保留 | 记录 | 🟢 |
| `.hs-tts-btn` | `styles.css:2560-2567` | `hotspot.js:67,763` | 朗读热点 | 保留 | 记录 | 🟢 |
| `.hs-selfcheck-btn` | `styles.css:2560-2568` | `hotspot.js:68,767` | 自检 | 保留 | 记录 | 🟢 |
| `.wx-mode-btn` | `styles.css:1747-1752` **且** `1887-1892`（重复定义） | `weather.js:138-139,228` | 模式切换；**双定义异味** | 保留；去重（CSS-only，零视觉） | 记录+异味 | 🟡 |
| `.wx-exit-btn` | `styles.css:1765-1769` **且** `1905-1909`（重复定义） | `weather.js:149,482` | 退出；**双定义异味** | 保留；去重 | 记录+异味 | 🟡 |
| `.sm-exit-btn` | `styles.css:1986-1988` | `sysmon.js:14` | 退出 | 保留 | 记录 | 🟢 |
| `.ts-clear-btn` | `styles.css:2055,2088` | `terminal-stream.js:12` | 清屏 | 保留 | 记录 | 🟢 |
| `.ts-exit-btn` | `styles.css:2055-2090`（双定义） | `terminal-stream.js:13` | 退出；**双定义异味** | 保留；去重 | 记录+异味 | 🟡 |
| `.zz-task-launch-btn` | `styles.css:3043-3048` | `tasks.js:105` | 任务启动 CTA | 保留 | 记录 | 🟢 |
| `.mem-prune` | `styles.css:3544-3546` | `memory-panel.js:99-181` | 清理（危险色 hover） | 保留 | 记录 | 🟢 |
| `.learn-del` | `styles.css:3563-3564` | `memory-panel.js:143-177` | 删除（危险色 hover） | 保留 | 记录 | 🟢 |

### 附加：原始/结构按钮（无独立类，依附父容器样式）

| 类 | 定义 | 使用 | 备注 |
|----|------|------|------|
| `.onb-skip` | `premium.css:230` | onboarding | 文本链接式 `<button>`，无边框 |
| 裸 `<button class="btn">` | — | `mobile-app.html:66,76` | 已用规范基准类 |

---

## 5. 风险汇总

| 风险等级 | 类数量 | 含义 | Phase 1 动作 |
|----------|--------|------|--------------|
| 🔴 高 | 4 | 合并必改视觉方向或波及大量使用点 | **禁止**机械合并；递延 Review 门控（需 GUI 验证） |
| 🟡 中 | 11 | 近重复可共享基类 / 专属结构 / 双定义异味 | 仅记录；去重（CSS-only）留专项清理，不在 Phase 1 顺手改 |
| 🟢 低 | 19 | 单用/已族化/图标按钮 | 保留；无需动作 |

🔴 明细：`.btn-new`、`.onb-next`、`.settings-save-btn`、+（`.settings-save-btn` 广泛使用致合并风险高）。

---

## 6. 代码异味（仅记录，不处理）

按指令「特别要求：发现问题只记录不处理」。以下属 Phase 1 Button/Panel 范围外的 tangential 项：

1. **`.wx-mode-btn` 双定义** — `styles.css:1747-1752` 与 `styles.css:1887-1892` 内容近同（active/hover）。
2. **`.wx-exit-btn` 双定义** — `styles.css:1765-1769` 与 `styles.css:1905-1909`。
3. **`.ts-exit-btn` 双定义** — `styles.css:2055` 与 `styles.css:2088`。
4. **`.btn:disabled` 缺失** — `.btn` 基准类无 disabled 态规则（属 G1 缺口，Task B 补，非「异味」）。

> 上述 1–3 为纯 CSS 重复，去重零视觉影响，但属「扩大范围」风险，按纪律红线不在 Phase 1 顺手处理；建议归后续「CSS 去重专项」。

---

## 7. Phase 1 可执行动作建议（Task B 依据）

在红线内，**仅以下为安全且合规的 Phase 1 Button 实施动作**：

1. **确认 `.btn` 四变体已与 DESIGN.md §4.1 逐字节一致**（已核验：`ui2.css:591-601` ↔ `DESIGN.md:94-112`，padding 8/18、radius `--r-md`(=16)、font 13/600 全部吻合）。
2. **补 `.btn:disabled`**（additive，不影响现有渲染）：`opacity:.5; cursor:not-allowed; transform:none;`。
3. **别名兼容层现状核实**：`.btn-new` / `.onb-next` 的渐变背景已通过 `var(--btn-rail-bg)` / `var(--btn-pill-bg)` 实现「一个值、一个来源」（前置 Sprint 已完成），属 G2 的合规收敛，无需再动。
4. **不执行**：任何类名机械合并（`.btn-new`→`.zz-button`、`.settings-save-btn`→`.btn` 等）、任何 HTML/JS 改动、任何视觉方向调整。

> 机械合并（G2/G4 高/中风险项）一律标注为 **Review 门控**：待人工 Review 批准 + Electron GUI 像素级验证后，方可进入下一 Sprint 执行。

---

## 8. 结论

- Button 系统当前有 **34 个独立类族**，多套实现以「刻意变体」为主，非无序重复。
- 令牌/别名单值来源层（G2）已由前置 Sprint 完成，值零视觉变化。
- 规范基准 `.btn` 四变体已落地且与 DESIGN.md 吻合，仅缺 `:disabled`（Task B 补）。
- **Phase 1 不做机械合并**，所有高/中风险合并递延 Review 门控。
- 审计阶段**零代码改动**，全部发现已落盘，供 Task B/C 与最终 Review 使用。

---

*本文件为 Audit 阶段产物，零代码改动。下一步：Task B（Button System Implementation — 仅补 `.btn:disabled` + 别名层核实）。*
