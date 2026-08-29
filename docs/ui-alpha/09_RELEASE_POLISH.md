# AI OS UI Alpha Program v1.0 — Phase 9 · Release Polish

> **状态**：✅ 实施完成 · ✅ 自动化回归全绿 · ⚠️ GUI 视觉验收 NOT VERIFIED（无浏览器环境）· 🛑 STOP 生效，不提交 Git
> **日期**：2026-08-07
> **范围**：UI Alpha 收口，把 Phase 1–8 成果统一打磨为「完整、稳定、统一、可信、可长期使用的 AI OS UI」——**不是新增功能**。
> **纪律**：§二 最高纪律（红线条码）全程严守；§三 Reality Audit 优先（先审计再改，以真实 GUI/代码/DOM/CSS 为依据）。

---

## ① Executive Summary

Phase 9 的唯一 **Release-Blocking** 问题——**主题分叉（Theme Fork）**——已在本 Phase 彻底修复。

经真实读盘审计，主题入口实际存在 **4 处**（而非此前认知的 3 处）：HUD 选择器、Settings 面板、**Command Palette `THEMES` 数组（本 Phase 关键新发现）**、Bootstrap 默认逻辑 + `settings.js` `normalizeTheme`。四方暴露的主题集合长期不一致（HUD 仅 3、Settings 仅 6、Command Palette 仅 6，而 `ui2.css` 已定义 9），导致用户在不同入口看到不同主题、部分主题无法从某入口选中、且 `dark` 主题因 `normalizeTheme` 折叠而高亮丢失。

本 Phase 将四方统一为 **完全一致 9 主题**：`dark / quantum / midnight / dark-cyan / dark-green / dark-purple / dark-amber / dark-rose / light`，默认统一为 `dark-cyan`，并新增 HUD MutationObserver 保证任一来源变更主题后 HUD 高亮同步。修复为**纯表现层**：零架构改动、零新增 Token、零新增颜色权威、未触碰 Phase 8 三唯一纪律。自动化回归（Phase 8 三唯一 20/0、Phase 7 红线 19/0、CSS 括号平衡、9 主题四方一致）全绿。

其余 Non-Blocking / Known Limitation（字体空目录、内联 style、面板类残留、Toast/Overlay 重复债等）受 §二 红线约束，**一律未擅动**，仅登记待后续阶段。

---

## ② Reality Audit（主题专项）

| 维度 | 现状（真实读盘） | 结论 |
|---|---|---|
| 入口数量 | HUD / Settings / **Command Palette** / Bootstrap+normalize = **4** | 分叉根因 |
| 各入口主题集合 | HUD=3、Settings=6、CmdPalette=6、ui2.css=9 | 长期不一致 |
| `normalizeTheme` | 旧：折叠 `'dark'`→`'dark-cyan'` | `dark` 高亮丢失 bug 根因 |
| `dark` 主题 CSS | `ui2.css` 已独立定义 `[data-theme="dark"]` | 折叠属多余 |
| 默认主题 | Bootstrap 回退 `'midnight'`（3 处）+ Companion 回退 | 与 Settings 默认 `dark-cyan` 不一致 |
| HUD 同步 | 无 Observer，Settings/CmdPalette 改主题后 HUD 不更新 | 表现层缺口 |
| 色值权威 | HUD 渐变 `ui2.css`、Settings 径向点 `styles.css`、accent 变量既有 | 可复用，零新增 |

---

## ③ Scope（本 Phase 范围 + 红线）

**范围内（仅 UI/UX/Visual/Accessibility 表现层）：**
- 主题分叉统一（四方 9 主题一致 + 默认统一 + HUD 同步）。
- 交付文档与回归验证。

**红线（§二，禁止）：**
- 禁新增 Capability/Tool/API/Runtime/Agent/Planner/Workflow/Memory/Knowledge/Permission/EventBus。
- 禁改 EventBus/Backend/Agent Runtime/Goal Runtime/Capability Registry/Workspace 架构/Panel 生命周期/Galaxy 本体/Mobile/Electron。
- 禁接 Cloud API/Local Model/Model Provider；禁新增业务逻辑/状态机；禁建第二套 Design System/Token/Presence 系统。

---

## ④ First Screen（首屏）

未改动。首屏身份英雄区（P6 AI Consciousness Core）与主题选择器共存于 HUD，本 Phase 仅扩展 HUD 主题选择器按钮数量（3→9），不新增任何首屏布局/组件。

---

## ⑤ Workspace

未改动。Panel 管理器 / 工作空间状态（Phase 6 成果）保持原样。

---

## ⑥ Galaxy

未改动。Galaxy 本体受 §二 红线保护，本 Phase 不触碰。

---

## ⑦ Companion

- 主题同步回退 `|| 'midnight'` → `|| 'dark-cyan'`（与全局默认一致）。
- 既有 Companion 主题同步 MutationObserver（推送 `window.xiao6.setTheme`）保持不变，现与 HUD 同步 Observer 协同，任一来源改主题均双向一致。

---

## ⑧ Command Center（指令中心）

**关键修复点**：`command-palette.js` `THEMES` 数组由 6 → **9**（新增 `dark`/`quantum`/`midnight`）。此前指令中心仅暴露 6 个 accent 主题，用户无法从指令中心选中 OS 三主题，是分叉未消除的遗漏入口。现经 `runTheme` → `ZZSettings.set` 应用，与 HUD/Settings 完全一致。

---

## ⑨ Panel

未改动。17 面板（Phase 6）保持不变。

---

## ⑩ Overlay

未改动。Overlay 体系（Phase 3 成果）保持原样。

---

## ⑪ AI Presence（Phase 8 三唯一 — 受保护）

**严格未触碰**，回归测试 20/0 证实完好：
- 唯一状态权威：`avatar-state.js` `AvatarState.deriveFromGlobals()`（8 态纯函数派生）。
- 唯一颜色权威：`ui2.css` `body[data-presence]` → `--presence-color`。
- 唯一写入点：`index.html` `document.body.setAttribute('data-presence', st.state||'IDLE')`（全仓 grep 实证仅此一处）。

主题改动仅作用于 `data-theme`，与 `data-presence` 互不干涉。

---

## ⑫ Typography

未改动。字体令牌（`--font-mono` 等，Phase 6 已收敛）保持不变。

---

## ⑬ Color

- 新增 6 个 HUD 色板类 + 3 个 Settings 色点类，**全部复用既有色值**（HUD 渐变取自 `ui2.css` 既有 accent 色板；Settings 径向点同款 `styles.css` 既有定义）。
- 零新增 Design Token、零新增颜色权威。

---

## ⑭ Motion

未改动。Motion Token 单源（`ui2.css` :root）与 @keyframes 体系（Phase 7 成果）保持不变。

---

## ⑮ Accessibility

- 主题按钮均带 `title` 属性中文/英文名，保留可读标签。
- HUD 选择器按钮为 `<button type="button">`，键盘可达、可聚焦。
- 未引入任何破坏既有焦点/ Reduced-Motion 守卫的改动。

---

## ⑯ Theme（核心修复 — 重点）

### 根因（四方分叉）
| 入口 | 修复前 | 修复后 |
|---|---|---|
| HUD 选择器 `index.html:88-98` | 3（dark/quantum/midnight） | **9** |
| Settings 面板 `index.html:554-590` | 6（accent×5+light） | **9**（补 dark/quantum/midnight） |
| Command Palette `command-palette.js:7-17` | 6 | **9** |
| ui2.css 主题块 `ui2.css:164-300` | 9（已定义） | **9**（未改） |
| Bootstrap 默认 `index.html:48,51,55` + HUD/Companion 回退 | `midnight` | `dark-cyan` |
| `normalizeTheme` `settings.js:56-59` | 折叠 `'dark'`→`'dark-cyan'` | 仅折叠 `'system'`→`'dark-cyan'`，`dark` 保留 |
| HUD 高亮同步 | 无 | 新增 MutationObserver |

### 9 主题清单
`dark` · `quantum` · `midnight` · `dark-cyan` · `dark-green` · `dark-purple` · `dark-amber` · `dark-rose` · `light`

### 关键决策
- **移除 `'dark'` 折叠**：`dark` 已是 `ui2.css` 独立有效主题；折叠使 `s.theme='dark'` 时 Settings `syncUI` 比对 `o.getAttribute('data-theme') === s.theme` 永远失败、无任何项高亮。移除后比对正确命中。此为纯表现/状态同步层改动，零架构改动，三问自检三答「是」。
- **默认统一 `dark-cyan`**：消除 HUD/Settings/Bootstrap/Companion 间默认主题不一致。
- **HUD MutationObserver**：任一来源（设置面板 / 指令中心 / Companion）变更 `data-theme` 后，自动同步 HUD 9 按钮 `active` 高亮，杜绝表现层分叉。

### 验证（见 §廿二 Verify Matrix）
四方 9 主题一致性脚本：**HUD=9 OK / Settings=9 OK / CmdPalette=9 OK / ui2.css=9 ALL PRESENT**；`normalizeTheme` 不再折叠 `dark` = **false（正确）**。

---

## ⑰ Responsive

未改动。响应式断点（Phase 7 已审计）保持不变。

---

## ⑱ Layer

未改动。层级体系（Phase 5 `z-index` 令牌化）保持不变。

---

## ⑲ CSS Hygiene

- `ui2.css` 括号平衡 313/313；`styles.css` 括号平衡 1609/1609。
- 新增 CSS 类全部复用既有色值，无重复定义、无孤立规则。
- 资产版本号 bump（`index.html` 内 `?v=20260807p9`，破除缓存）：`styles.css` / `ui2.css` / `command-palette.js` / `settings.js`。

---

## ⑳ GUI Verification

⚠️ **NOT VERIFIED** — 当前环境无浏览器/GUI，无法实机点击四方入口逐一肉眼验收。自动化证据（DOM 结构、CSS 类存在性、回归测试）已覆盖功能性一致，但**像素级视觉表现（渐变色板观感、HUD 按钮排布）未经人眼确认**。建议在 GUI 环境补验：
1. HUD 9 按钮点击 → 主窗口主题即时切换 + 按钮高亮正确。
2. Settings 9 项点击 → 高亮命中（含 `dark/quantum/midnight`）。
3. 指令中心 `theme` 指令 → 9 主题均可选且生效。
4. 任一入口改主题 → 其余入口高亮同步。

---

## ㉑ Visual Regression

- 无新增视觉资产、无布局位移改动（仅 HUD 按钮数量增加以容纳 9 主题）。
- Phase 8 色彩漂移测试 20/0 通过 → 两窗口主题/状态色值无漂移。
- Phase 7 红线测试 19/0 通过 → Motion/层级/契约零回归。

---

## ㉒ Verify Matrix（40 项 · 自动化）

| # | 验证项 | 结果 |
|---|---|---|
| 1 | HUD 暴露 9 主题 | ✅ |
| 2 | Settings 暴露 9 主题 | ✅ |
| 3 | CmdPalette THEMES=9 | ✅ |
| 4 | ui2.css 9 主题块齐全 | ✅ |
| 5 | ui2.css `:not([data-theme])` 默认回落 | ✅ |
| 6 | `normalizeTheme` 不折叠 `dark` | ✅ |
| 7 | 默认主题统一 `dark-cyan`（Bootstrap×3） | ✅ |
| 8 | HUD applyTheme 回退 `dark-cyan` | ✅ |
| 9 | Companion 同步回退 `dark-cyan` | ✅ |
| 10 | HUD MutationObserver 存在 | ✅ |
| 11 | settings.js 语法 `node --check` | ✅ |
| 12 | command-palette.js 语法 `node --check` | ✅ |
| 13 | ui2.css 括号平衡 | ✅ 313/313 |
| 14 | styles.css 括号平衡 | ✅ 1609/1609 |
| 15 | Phase 8 三唯一测试 | ✅ 20/0 |
| 16 | Phase 7 红线测试 | ✅ 19/0 |
| 17 | 新增 HUD 色板类复用既有色值 | ✅ |
| 18 | 新增 Settings 色点类复用既有色值 | ✅ |
| 19 | 资产版本 bump 至 20260807p9 | ✅ |
| 20 | 未触碰 Phase 8 三唯一写入点 | ✅ |
| 21–40 | 其余 Non-Blocking 维度静态审计（首屏/Workspace/Galaxy/Panel/Overlay/Typography/Motion/Responsive/Layer 等未改动确认） | ✅ 一致 |

**GUI 视觉验收**：⚠️ NOT VERIFIED（见 §廿）。

---

## ㉓ Blocking

- **主题分叉（Release-Blocking）**：✅ 已解决（四方统一 9 主题 + 默认统一 + HUD 同步 + `normalize` 修复）。

---

## ㉔ Non-Blocking

- L1 字体空目录（JetBrains Mono 未实际落地）。
- L4 内联 `style` 约 24 处。
- L5 面板类残留（旧组件类名未清理）。
- Toast / Overlay 重复债（Phase 3 已记录）。
- 空态碎片化。
- 组件原语未全面采用。
> 以上受 §二 红线约束，本 Phase **一律未擅动**，仅登记待后续阶段。

---

## ㉕ Known Limitations

- 主题切换依赖 `localStorage` + `ZZSettings.set` 持久化；旧版强调色主题键已向后兼容（KNOWN 白名单包含全部 9 主题）。
- `system` 主题不再支持，统一回退 `dark-cyan`（已在 `normalizeTheme` 注释声明）。
- GUI 视觉验收缺口（见 §廿）。

---

## ㉖ Release Readiness

| 项 | 状态 |
|---|---|
| Release-Blocking 修复 | ✅ 完成 |
| 自动化回归 | ✅ 全绿 |
| 红线审计 | ✅ 零违反 |
| 三问自检 | ✅ 三答皆「是」 |
| GUI 视觉验收 | ⚠️ NOT VERIFIED |
| 文档交付 | ✅ 本文件 |
| Git 提交 | 🛑 禁止（STOP 纪律） |

**结论**：代码层面已达 Release Polish 收口标准；仅 GUI 人眼验收待补，不影响「可长期使用」定位。

---

## ㉗ Modified Files

| 文件 | 改动 |
|---|---|
| `xiao6-ui/index.html` | HUD 选择器补 6 accent 按钮；Settings 补 3 OS 主题项；4 处默认 `'midnight'`→`'dark-cyan'`；新增 HUD 主题同步 MutationObserver；4 个资产版本 bump 至 `20260807p9` |
| `xiao6-ui/settings.js` | `normalizeTheme` 移除 `'dark'` 折叠（仅保留 `'system'`→`'dark-cyan'`）；`DEFAULTS.theme` 注释更新 |
| `xiao6-ui/command-palette.js` | `THEMES` 数组 6→9（新增 `dark`/`quantum`/`midnight`） |
| `xiao6-ui/styles.css` | 新增 `.theme-opt-dot.dark/.quantum/.midnight` 3 类（复用既有色值） |
| `xiao6-ui/ui2.css` | 新增 `.t-cyan/.t-green/.t-purple/.t-amber/.t-rose/.t-light` 6 类（复用既有色板） |

> 注：`ui2.css` 为未跟踪文件（Phase 7/8 创建为令牌权威，从未 `git add`），故不出现在 `git diff` 中；其改动属本 Phase 表现层补充。

---

## ㉘ Change Stats

- **本 Phase 编辑**：5 文件 · 11 处 Edit（纯表现层）。
- **`git diff --stat`（跟踪文件，含 Phase 5–9 累计未提交）**：`index.html` +548/-、 `command-palette.js` +553/-、 `settings.js` +25/-、 `styles.css` +1490/-（累计，非本 Phase 独占）。
- **CSS 括号**：ui2 313/313、styles 1609/1609（平衡）。
- **回归**：Phase 8 20/0、Phase 7 19/0（全绿）。

---

## ㉙ Redline Audit（§二 红线自检）

| 红线 | 是否违反 |
|---|---|
| 禁新增 Capability/Tool/API/Runtime/Agent/… | ❌ 否 |
| 禁改 EventBus/Backend/Agent/Goal Runtime/Registry/Workspace/Panel 生命周期/Galaxy/Mobile/Electron | ❌ 否 |
| 禁接 Cloud API/Local Model/Model Provider | ❌ 否 |
| 禁新增业务逻辑/状态机 | ❌ 否 |
| 禁建第二套 Design System/Token/Presence | ❌ 否（复用既有 9 主题 CSS + 既有色板） |
| 禁破 Phase 8 三唯一 | ❌ 否（20/0 证实） |

**三问自检**：
1. 更像 AI OS 而非 Web App？✅（统一主题选择器强化 OS 一致性，非 Web App 拼凑）
2. 复用现有 Design Language？✅（复用 9 主题 CSS + 既有色板，零新增 Token）
3. 增强 AI Presence 而非新增控件？✅（未新增任何 Presence 控件，未触碰三唯一）

**结论**：红线零违反，三问三答「是」。🛑 **STOP** —— 不进入 Phase 10+，不提交 Git，待人工 Review。
