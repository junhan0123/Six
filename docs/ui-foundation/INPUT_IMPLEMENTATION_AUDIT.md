# Input System Implementation Audit — Xiao6 Component System Sprint v1.0 · Phase 2

> **阶段**：Implementation Phase 2 — Input System Primitive 收敛
> **执行身份**：DesignMdArchitect（Diana，设计系统架构师）
> **执行模式**：Audit → Plan → Execute → Verify → Report → STOP
> **审计日期**：2026-08-05
> **依据**：`xiao6-ui/DESIGN.md`（9 章节单值来源）、`ui2.css`（令牌权威源，最后加载）
> **纪律红线（硬性）**：仅 Primitive 收敛；零视觉/行为变化；不新增功能/页面/架构/Runtime/EventBus；可回滚；静态验证（本环境无 Electron GUI，仅代码级核对）。

---

## 1. 审计方法

- 扫描范围：`xiao6-ui/` 下所有 CSS（`ui2.css` / `styles.css` / `premium.css` / `companion.css` / `execution-channel.css` / `runtime-viz.css`）、`index.html`、`command-palette.js`、`mobile-app.html` 及相关 JS。
- 扫描对象：`input` / `textarea` / `contenteditable` / `search box` / `command input` / `chat input` / `setting input` 及其 CSS 类、HTML 使用、JS 绑定、状态逻辑。
- 校验手段：比对每个硬编码值 / 遗留变量与 `ui2.css` 令牌别名层，确认「单值来源」等价性（见 §4）。
- 风险判定：以「是否核心对话 / 指令通道」「是否 companion 隔离层」「改值是否触发视觉方向变化」三维度分级。

---

## 2. Input 实现清单

### 2.1 单行文本输入（Text Inputs）

| # | 类名 | 定义位置 | background | border | radius | padding | font | focus 行为 | placeholder | 归属 / 风险 |
|---|------|----------|-----------|--------|--------|---------|------|-----------|-------------|------------|
| T1 | `.settings-input` + `.settings-select` | `styles.css:2779-2781` | `rgba(5,7,10,.6)` | `1px var(--line)` | `10px` | `9px 12px` | `13px var(--txt)` | `border-color:var(--cyan)` | 用 `--txt`（无独立占位色） | **低风险** · 设置表单主输入 |
| T2 | `.sc-input` | `styles.css:454-456` | `rgba(5,7,10,.55)` | `1px var(--line)` | `9px` | `8px 11px` | `14px Rajdhani` | `border-color:var(--cyan)` + `box-shadow:0 0 10px rgba(34,211,238,.25)` | 无 | **低风险** · 快捷配置 |
| T3 | `.wx-city-input` | `styles.css:1754-1758`（**重复** `:1894`） | `var(--void)` | `1px var(--line)` | `9px` | `7px 10px` | `13px` | `border-color:var(--cyan)` | 无 | **低风险** · 天气城市（含重复定义） |
| T4 | `.wc-cd-input` | `styles.css:2136-2138`（**重复** `:2196`） | `var(--void)` | `1px var(--line)` | `9px` | `7px 10px` | `13px` | **无** focus 态 | 无 | **高风险·只记录** · 指令坞（旧） |
| T5 | `.cp-input` | `styles.css:2154-2155`（**重复** `:2214`） | `transparent` | `0` | `0` | — | `16px Rajdhani` | 依赖容器 `.cp-inputrow`（无自身 focus） | `var(--dim2)` | **高风险·只记录** · Command Palette |
| T6 | `.os-dock input` | `ui2.css:439-442` | `transparent` | `0` | `0` | — | `14px` | 容器 `.os-dock-bar:focus-within`（accent + glow） | `var(--muted)` | **高风险·只记录** · 指令坞（新·令牌天花板） |
| T7 | `.onb-input` | `premium.css:238-244` | `rgba(255,255,255,.04)` | `1px var(--line-strong)` | `var(--r-sm)=10px` | `10px 14px` | `14px` | `border-color:var(--cyan)` + `box-shadow:0 0 0 4px rgba(34,211,238,.18)` | 无 | **低风险** · 引导页 |
| T8 | `.memq-input` | `styles.css:3615-3617` | `transparent` | `0` | `0` | — | `15px Rajdhani` | 容器 `.memq-search:focus-within`（teal + glow） | `var(--dim2)` | **低风险** · 记忆查询 |
| T9 | `.cmd-bubble-input` | `companion.css:429-440` | `rgba(0,0,0,.25)` | `1px var(--companion-chrome-border)` | `8px` | `6px 8px` | `12.5px` | **无** focus 态 | `#7f97a6`（硬编码） | **超出范围** · Companion 隔离层 |

### 2.2 多行文本 / 文本域（Textareas）

| # | 类名 | 定义位置 | background | border | radius | padding | focus 行为 | placeholder | 归属 / 风险 |
|---|------|----------|-----------|--------|--------|---------|-----------|-------------|------------|
| A1 | `#input` | `styles.css:490-492` | `transparent` | `0` | — | `9px 0` | 无自身 focus（容器 `.dock.focus-within`） | `var(--dim2)` | **高风险·只记录** · 主聊天输入 |
| A2 | `.hs-chat-input textarea` | `styles.css:770-777` | `rgba(255,255,255,.05)` | `1px var(--line)` | `12px` | `10px 12px` | `border-color:rgba(34,211,238,.55)` + `box-shadow` + inset 辉光 | `var(--dim)` | **高风险·只记录** · HUD 聊天 |
| A3 | `.settings-textarea` | `styles.css:3062-3067` | `rgba(255,255,255,.05)` | `1px var(--line)` | `10px` | `9px 11px` | `border-color:rgba(34,211,238,.45)` + `box-shadow 0 0 0 3px rgba(34,211,238,.12)` | 无 | **低风险** · 设置文本域 |

### 2.3 搜索框（Search Boxes）

| # | 类名 | 定义位置 | 说明 | 归属 / 风险 |
|---|------|----------|------|------------|
| S1 | `.mem-search` | `styles.css:2385-2389` | `bg rgba(0,0,0,.35)`；`border 1px var(--line)`；`radius 8px`；`padding 6px 11px`；focus：`border-color:var(--line-strong)` + `box-shadow:var(--glow)` | **低风险** · 记忆搜索 |
| S2 | `.memq-search`（容器） | `styles.css:3610-3613` | `bg rgba(255,255,255,.05)`；`border 1px var(--line)`；`radius 14px`；`padding 8px 12px`；focus-within：`border-color:var(--teal)` + `box-shadow 0 0 0 3px rgba(45,212,191,.12)`；内含 `.memq-input`（T8） | **低风险** · 记忆查询搜索 |
| S3 | `.wx-search` / `.wx-search-wrap` | `styles.css:1753` / `:3664` | 容器，包裹 `.wx-city-input`（T3） | **低风险**（随 T3） |

### 2.4 指令输入（Command Inputs）

| # | 类名 | 行号 | 说明 | 风险 |
|---|------|------|------|------|
| C1 | `.cp-input` | `styles.css:2154` | Command Palette 输入（见 T5） | **高风险·只记录** |
| C2 | `.wc-cd-input` | `styles.css:2136` | 指令坞旧输入（见 T4） | **高风险·只记录** |
| C3 | `.os-dock input` | `ui2.css:439` | 指令坞新输入（令牌天花板，见 T6） | **高风险·只记录** |
| C4 | `.cmd-bubble-input` | `companion.css:429` | Companion 指令气泡（见 T9） | **超出范围** |

### 2.5 非文本表单控件（Checkbox / Toggle / Range / File）

| # | 类名 | 行号 | 说明 | 风险 |
|---|------|------|------|------|
| N1 | `.settings-switch input` | `styles.css:2793` / `ui2.css:562` | 隐藏 checkbox（Toggle），Phase 1 已视觉别名到 `.zz-toggle` | 已完成（Phase 1） |
| N2 | `.zz-toggle input` | `styles.css:2910` | 官方 Toggle（隐藏 checkbox） | 稳定 |
| N3 | `.settings-range input[type=range]` | `styles.css:2920` | 滑块 | **低风险** |
| N4 | `.settings-check input` | `styles.css:3070-3071` | checkbox，`accent-color:var(--cyan)`；**唯一带 `:disabled` 的输入** | **低风险**（disabled 范式来源） |
| N5 | `<input type="file">` ×3 | `index.html:296,297,963` | 隐藏文件输入（`hidden`） | 无样式冲突 |
| N6 | 裸 `<input type="checkbox">` | `index.html` 多行 | 设置/特性开关，未加类，靠浏览器默认 + 全局 focus | 低风险 |

### 2.6 contenteditable

- **应用内无任何 `contenteditable` 输入控件**。仅在 `solar-system.js:17` 作为 CSS 选择器排除项（`.mic-overlay, .orb-wrap, [contenteditable="true"]` 不响应拖拽），以及 `python/Doc/html/_static/search-focus.js:6`（Doc 产物，非应用 UI）中出现。
- **结论**：contenteditable 不在本 Phase 2 Input 收敛范围内。

---

## 3. 状态覆盖矩阵（现状）

| 状态 | 文本输入是否具备 | 具体实现 | 缺口 |
|------|----------------|----------|------|
| Default | ✅ | 各变体见 §2.1 | 背景/圆角/内距不统一（10/9/8px 混用） |
| Placeholder | ⚠️ 部分 | `#input`=var(--dim2)；`.os-dock`=var(--muted)；`.cp-input`/`.memq-input`=var(--dim2)；`.hs-chat`=var(--dim)；`.settings-*` 无独立占位色 | 无统一占位色令牌 |
| Focus（鼠标/容器） | ✅ | settings/sc/wx=border var(--cyan)；os-dock/cp/memq=容器 focus-within accent；hs-chat/settings-textarea=显式 cyan box-shadow | focus 辉光用硬编码 `rgba(34,211,238,..)`，不随主题（见 §6·F2） |
| Focus-visible（键盘） | ✅ | `premium.css:48` `input:focus-visible`（accent + glow .18）覆盖 `ui2.css:547` 全局 `:focus-visible`（glow .40） | 双定义，输入实际取 premium.css 版本（见 §6·F1） |
| Disabled | ❌（文本类） | 仅 `.settings-check input:disabled`（N4） | **文本/文本域/搜索无 disabled 态 → 缺口** |
| Error | ❌ | 全站无输入 error 态（仅 `.orb-wrap.error` 非输入） | **输入 error 态完全缺失 → 缺口** |
| Readonly | ❌ | 未发现 | 非本次范围（记录） |

---

## 4. 令牌映射校验（「单值来源」等价性）

`ui2.css:56-70` 已声明 LEGACY 别名全部映射到 NEW 值，故以下替换**计算值逐字节一致**：

| LEGACY（旧） | NEW（新） | 校验 |
|--------------|-----------|------|
| `var(--cyan)` | `var(--accent)` | ✅ 同值（midnight `#4f7bff`） |
| `var(--teal)` | `var(--accent-2)` | ✅ |
| `var(--line)` / `var(--line-strong)` | `var(--border)` | ✅ |
| `var(--void)` / `var(--void2)` | `var(--bg)` / `var(--bg-2)` | ✅ |
| `var(--txt)` | `var(--text)` | ✅ |
| `var(--dim)` | `var(--text-dim)` | ✅ |
| `var(--dim2)` | `var(--muted)` | ✅ |

> **推论**：所有遗留变量引用已是「单值来源」（经别名层）。真正未令牌化的是**裸 rgba 背景填充**与**裸 radius 数字**。Phase 2 收口重点即这两类。

---

## 5. 风险分级与迁移决策

### A 组 — 低风险（Task D 可迁移，令牌路由，零视觉）

| 类 | 理由 |
|----|------|
| `.settings-input` / `.settings-select`（T1） | 设置表单主输入，使用最广，改令牌路由零视觉 |
| `.settings-textarea`（A3） | 同上，文本域 |
| `.sc-input`（T2） | 快捷配置，独立上下文 |
| `.wx-city-input`（T3） | 天气城市，重复定义可合并 |
| `.onb-input`（T7） | 引导页，独立上下文 |
| `.mem-search`（S1） | 记忆搜索 |
| `.memq-search` + `.memq-input`（S2/T8） | 记忆查询 |
| `.settings-range` / `.settings-check`（N3/N4） | 非文本控件，令牌化一致 |

### B 组 — 高风险（Task D 不迁移，仅记录在案）

| 类 | 理由（撞红线） |
|----|----------------|
| `#input`（A1） | **主聊天核心输入**，改值=聊天 UX 变化 |
| `.hs-chat-input textarea`（A2） | HUD 聊天输入 |
| `.cp-input`（T5/C1） | **Command Palette**，指令通道 |
| `.wc-cd-input`（T4/C2） | 指令坞旧输入，指令通道 |
| `.os-dock input`（T6/C3） | 指令坞新输入（已在 ui2.css 令牌天花板，无需动） |
| `.cmd-bubble-input`（T9/C4） | **Companion 隔离层**，用 `--companion-chrome-*` 令牌，越界 |

---

## 6. 缺陷 / 重复 / 缺口（Findings）

| ID | 类型 | 位置 | 描述 | 处理 |
|----|------|------|------|------|
| F1 | 双焦点定义 | `ui2.css:547` vs `premium.css:48` | 全局 `:focus-visible`（glow .40）被 `premium.css input:focus-visible`（glow .18）以更高特异性覆盖，输入实际取后者 | **记录**（改=动 Focus 系统，撞红线） |
| F2 | 硬编码焦点辉光 | `styles.css:456,777,3067` 等 | focus box-shadow 用 `rgba(34,211,238,..)` 硬编码青色，不随主题（dark 主题 accent 为 `#5fb3c8` 仍显示青） | **记录**（路由到 `var(--glow)` 会改变非 midnight 主题辉光色=视觉变化） |
| F3 | 重复类定义 | `styles.css:1754/1894`、`2136/2196`、`2154/2214` | `.wx-city-input` / `.wc-cd-input` / `.cp-input` 各出现两次（同值） | **记录**（合并=改源结构，低风险但非必要，留 Review） |
| F4 | 缺 disabled 态 | 全文 | 文本/文本域/搜索输入无 `:disabled` 样式（仅 checkbox 有） | **记录为缺口**（不实现，避免新增视觉/功能） |
| F5 | 缺 error 态 | 全文 | 输入无 error 态 | **记录为缺口** |
| F6 | 占位色不统一 | 见 §3 | 占位色混用 `--dim2`/`--muted`/`--dim`/无 | Task B 定义 `--input-placeholder` 令牌（文档级） |
| F7 | 圆角不统一 | 见 §2.1 | 文本输入 radius 混用 10/9/8px | **记录**（统一=改视觉，留 Review） |
| F8 | 浅色主题输入底 | `styles.css:2780` 等 | `rgba(5,7,10,.6)` 深色底在 light 主题不自适应 | **记录**（令牌化后未来可主题化） |
| F9 | 内联 style | `index.html:643,691,725,735,771,778,785,792` | 密码输入 `style="width:100%;padding-right:38px;"` | **记录**（内联样式，非本次范围） |

---

## 7. 目标规范基准（指向 Task B 产出）

- 完整 canonical Input 规范将在 **DESIGN.md §4.3** 补全（Task B），定义：
  - Input 令牌集：`--input-bg` / `--input-bg-soft` / `--input-border`(=`--border`) / `--input-radius`(=`--r-sm`) / `--input-pad-y` / `--input-pad-x` / `--input-font` / `--input-focus-border`(=`--accent`) / `--input-focus-glow`(=`--glow`) / `--input-placeholder`(=`--muted`) / `--input-disabled-op` / `--input-error-border`(=`--danger`)。
  - 变体矩阵：A 有底边框型（`.settings-input` 系）/ B 无边框透明型（聊天·指令）/ C 文本域 / D 搜索。
- 本审计报告为 Task B（对齐）、Task C（焦点）、Task D（迁移）、Task E（回归）的基线。

---

## 8. 结论

- Input 实现共 **9 类文本 + 3 类文本域 + 3 类搜索 + 4 类指令 + 6 类非文本控件**，无 contenteditable。
- 遗留变量已单值来源化；剩**裸 rgba 背景**与**裸 radius 数字**两类未令牌化，为 Phase 2 收口重点。
- 风险分级清晰：**A 组（8 类）可安全迁移**，**B 组（6 类核心/指令/Companion）只记录不修改**。
- 缺口（disabled / error / 占位统一 / 圆角统一 / 浅色底）均**记录不实现**，严守红线。

> **状态**：Task A 审计完成，零代码改动。下一步 → Task B（DESIGN.md §4.3 对齐 + 令牌路由）。
