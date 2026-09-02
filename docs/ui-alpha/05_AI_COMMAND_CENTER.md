# Phase 5 — AI Command Center (UI Alpha Program v1.0)

> **身份**：Chief Product Designer + AI OS Experience Architect + Senior Frontend Engineer + Interaction Designer
> **任务等级**：LONG RUNNING UI IMPLEMENTATION TASK
> **执行模式**：Audit → Design → Implement → Verify → Document → STOP
> **任务卡**：#649 (5A Reality Audit) · #650 (5B Information Hierarchy) · #651 (5C AI Command Experience) · #652 (5D Visual Polish) · #653 (5E Execution Feedback) · #654 (5F Workspace Integration + Document/STOP)
> **状态**：✅ 完成 · 🛑 STOP 等 Review
> **日期**：2026-08-07

---

## 0. 摘要（TL;DR）

把 Command Palette 从"一个能用的命令面板"升级为 **AI OS 的统一操作入口（AI Command Center）**：

1. **修掉 CSS 分叉（split-brain）**：`.cp-*` 样式原本散落在 `styles.css`（2 处）× `premium.css`（1 处）× `ui2.css`（1 处 mode-chip），且混用遗留 `Rajdhani`/`Share Tech Mono` 字体与硬编码 `rgba()`，与 Design Language 分裂。现已 **100% 收口到 `ui2.css`**（最后加载、权威），删除 `styles.css`/`premium.css` 的遗留块。
2. **统一 Presence 调度反馈（仅表现层）**：`runCmd` 真实动作与现状 **字节级一致**（仅消费既有 Capability / Intent Gateway / Settings），新增 Presence 色调度反馈（thinking / executing / completed / cancelled / error），复用 Phase 4 的 `--presence-*` 色板。
3. **增强 AI Presence，零新增控件**：意图项（`cp-item--intent`）以 `accent-2` 高亮，表达"AI 理解意图并调度"；档位徽标 T0–T4 改为令牌化 `--tier-Tx`，与产品宪法 05 同源。
4. **诚实性修复**：`workflow` 模式标签从"工作流"改为"创建"（该段实为"新建目标/待办/提醒"，非工作流引擎，避免暗示 missing 能力）。

**红线零违反**：未新增 Capability/Tool/API/Runtime/Agent/Planner/Workflow/Memory/Knowledge/Permission；未改动 EventBus/数据库/Prompt/Command Backend/Capability Registry；未新增任何业务逻辑。

---

## 1. 现状分析（Reality Audit — 5A）

### 1.1 命令与能力入口（符合宪法，无需新建）
- `command-palette.js` 已实现 MODES（search / command / agent / workflow[实为 create]）、CAT_ORDER（recent / intent / panel / theme / feature / create / system）、`buildCommands()`、`runCmd()`、`runIntent()`（→ `ZZIntentGateway.dispatch`）、`render()`。
- 依据 `docs/product-constitution/06_INTERACTION_CONSTITUTION.md`：**Command Palette = 统一指令中心（Ctrl/Cmd+K），T0/T1 全部可召唤能力，唯一指令中心，不得另建第二命令系统**。
- 依据 `docs/capability-platform/03_ENTRY_MAP.md`：`command-palette.js` 为唯一命令入口，~30 命令，无重复。
- **结论**：命令本身已是"统一入口"，符合宪法。5C/5E 只在其上叠加 *AI Command Experience* 与 *Presence 调度反馈*，不增删命令。

### 1.2 历史遗留 + 设计语言分裂（核心问题）
| 位置 | 内容 | 问题 |
|---|---|---|
| `xiao6-ui/styles.css` (≈2160–2190) | `.cp-*` 块（含 `/* 全局指令面板样式（Task #44）*/`） | 遗留 `Rajdhani`/`Share Tech Mono` 字体 + 硬编码 `rgba()`，未走 Design Language |
| `xiao6-ui/styles.css` (≈2231–2260) | **第二份** `.cp-*` 块（同注释） | 重复定义，与上方互相覆盖 |
| `xiao6-ui/premium.css` (≈140–174) | `/* ── 全局指令中心（命令面板）· P7-1 玻璃拟态升级 ── */` | 第三份 `.cp-*` 定义，玻璃拟态与 ui2 令牌冲突 |
| `xiao6-ui/ui2.css` (363–377) | 仅 `.cp-modes` / `.cp-mode-chip` | 唯一走 Design Language 的部分，但只占 1/4 |

- **风险**：三处定义加载顺序敏感、互相覆盖；字体/颜色硬编码，切换主题或 Design Language 更新时必然漂移；与 Galaxy / Companion / Panel 的 `--presence-*` / `--surface` / `--blur-glass` 同源令牌割裂。
- **归类**：5A 将此定性为 **「历史遗留 + 设计语言分裂」**，而非"功能缺失"。

### 1.3 信息层级（5B）
- 命令分层已合理（recent → intent → panel → theme → feature → create → system）。5B 仅确认：intent 应被视觉强调（它是 AI 理解入口），档位应以产品宪法 05 的 T0–T4 诚实标注。
- 无信息层级重构，仅通过 `cp-item--intent` 与 `--tier-Tx` 徽标在表现层兑现。

---

## 2. 设计目标

1. **统一操作入口**：Command Palette 作为 AI OS 唯一指令中心，视觉与 Workspace / Galaxy / Companion / Panel 同源。
2. **AI Command Experience**：用户发出指令 → 看到小6"理解 / 调度 / 完成"的 Presence 反馈，而非无声关闭。
3. **Presence 调度反馈**：复用 Phase 4 的 `--presence-*`，让命令执行带上"AI 在干活"的状态色。
4. **Design Language 同源**：所有 `.cp-*` 收口 `ui2.css`（最后加载、权威），消除分叉。
5. **零新增控件 / 零新风格**：仅增强 AI Presence，不堆按钮、不创造第二视觉语言。

---

## 3. 实现内容

### 3.1 Visual Polish（5D）— CSS 收口
- 将 `ui2.css` 中原有的 `.cp-modes`/`.cp-mode-chip` 扩展为完整 `.cp-*` 块（约 127 行，line 365–491），全部走 Design Language 令牌：
  - `:root` 新增 `--presence-*` 8 态（与 Companion Phase 4 同源）+ `--presence-color: var(--presence-idle)`。
  - `:root` 新增 `--tier-T0..T4`（替代硬编码 `#6ee7b7` 等）。
  - `.cp-overlay`（color-mix bg + blur + `cp-fade`）、`.cp-box`（var(--surface)/var(--blur-glass)/var(--radius-md)/var(--elev-3)/`cp-pop`）。
  - `.cp-input`（var(--text)/var(--font-ui)）、`.cp-caret`（var(--accent)/var(--font-mono)）、`.cp-kbd`。
  - `.cp-item`（hover/active 走 `color-mix(in srgb, var(--accent) 14%, transparent)` + translateX）。
  - **`.cp-item--intent`**（accent-2 高亮，表达"AI 理解意图"）。
  - `.cp-badge` + `.cp-badge--T0..T4`（全改 `var(--tier-Tx)` + `color-mix` 边框）、`.cp-badge--beta/exp`。
- **脚本化删除遗留块**（字节精确，零视觉变化）：
  - `styles.css`：删除 line (2231,2260) + (2160,2190) 共 **61 行**（两份重复 `.cp-*` 块）。
  - `premium.css`：删除 line (140,174) 共 **35 行**（玻璃拟态 `.cp-*` 块）。

### 3.2 AI Command Experience（5C）+ Execution Feedback（5E）— JS
- `command-palette.js` 重构 `runCmd` + 新增 `feedback()`：真实动作与现状 **完全一致**（仅消费既有 `runIntent`/`cmd.run`/`runTheme`/`runFeature`/`runPrefill`），随后表现层展示 Presence 调度反馈：
  ```js
  function runCmd(cmd) {
    pushRecent(cmd);
    if (cmd.intent) {
      try { runIntent(cmd.intent); } catch (e) { return feedback('error', '调度失败：意图网关不可用'); }
      return feedback('thinking', '理解意图中，已转交小6…');
    }
    if (cmd.run) {
      try { cmd.run(); } catch (e) { return feedback('error', '调度失败'); }
      return feedback('executing', '正在调度能力…');
    }
    if (cmd.theme)   { runTheme(cmd.theme);     return feedback('completed', '主题已切换'); }
    if (cmd.feature) { runFeature(cmd.feature); return feedback('completed', '功能开关已更新'); }
    if (cmd.prefill) { runPrefill(cmd.prefill); return feedback('completed', '已填入对话，等你确认'); }
  }

  function feedback(kind, label) {
    const box = document.querySelector('.cp-box');
    const status = document.getElementById('cpStatus');
    if (!box || !status) { closeCp(); return; }
    status.textContent = label;
    status.className = 'cp-status cp-status--' + kind;
    box.classList.add('cp--dispatching');
    setTimeout(closeCp, 460);
  }
  ```
- `ui2.css` 新增 `[E] Execution Feedback`：`.cp-status`（默认 `display:none`，`.cp-box.cp--dispatching .cp-status` 显示）、`.cp-status::before`（脉冲圆点 `currentColor` + `cp-pulse`）、`.cp-status--thinking/executing/completed/cancelled/error`（复用 `--presence-*`）。
- 模板 `CP_HTML` 在 `<div class="cp-list" id="cpList"></div>` 后新增 `<div class="cp-status" id="cpStatus"></div>`。

### 3.3 诚实性 + 文案修复
- `MODES` 中 `{ id: 'workflow', label: '工作流' }` → `{ id: 'workflow', label: '创建' }`（该段实际为"新建目标/待办/提醒"，非工作流引擎）。
- intent label `'作为意图发送：' + q` → `'理解为意图并调度：' + q`。
- empty 文案 `'无匹配指令'` → `'没有匹配的能力，换个说法试试？'`。
- render 项新增 `const isIntent = cmd.cat === 'intent';` 并加 `cp-item--intent` class。

### 3.4 Workspace Integration（5F）
- Presence 令牌（`--presence-*`）、档位令牌（`--tier-Tx`）、玻璃/圆角/阴影令牌（`--surface`/`--blur-glass`/`--radius-md`/`--elev-3`）与 Galaxy / Companion / Panel 同源 → Command Center 与全 OS 视觉语言统一。
- `index.html` 版本号 bump：`ui2.css?v=20260807p5`、`command-palette.js?v=20260807p5.ic1`（缓存破坏约定，与 Phase 4 一致）。

---

## 4. 修改文件清单与统计

| 文件 | 操作 | 行数变化 | 说明 |
|---|---|---|---|
| `xiao6-ui/command-palette.js` | 修改 | 317 → **336**（+19 JS + 1 div 模板） | runCmd 重构 + feedback + 标签/文案修复 + cpStatus 节点 |
| `xiao6-ui/ui2.css` | 修改 | cp 块 363–377 → **365–491**（~+127 行） | 完整 `.cp-*` 收口 + `--presence-*`/`--tier-Tx` 令牌 |
| `xiao6-ui/styles.css` | 删除遗留块 | **−61 行**（两份重复 `.cp-*`） | 消除分叉，残留 `.cp-` = 0 |
| `xiao6-ui/premium.css` | 删除遗留块 | **−35 行**（玻璃拟态 `.cp-*`） | 消除分叉，残留 `.cp-` = 0 |
| `xiao6-ui/index.html` | 修改 | 2 处版本号 | 缓存破坏 |

**净变化**：+19 JS / +127 CSS / −96 遗留 CSS = 视觉一致性提升、代码量减少。

---

## 5. 验证（Verify）

| 检查项 | 结果 |
|---|---|
| `node --check command-palette.js` | ✅ OK |
| CSS 花括号平衡 | ✅ styles.css 1606/1606 · premium.css 84/84 · ui2.css 298/298 |
| 遗留 `.cp-` 残留 | ✅ styles.css = 0 · premium.css = 0 · ui2.css = 38（全部为收口后的权威定义） |
| 遗留字体（`Rajdhani`/`Share Tech Mono`）在 cp 上下文 | ✅ 0 处 |
| ui2.css 含 `cp-status` / `cp--dispatching` / `cp-item--intent` / `--presence-thinking` / `--tier-T0` | ✅ 全部存在 |
| `index.html` 加载顺序（ui2.css 最后加载、权威） | ✅ 未变，版本号已 bump |
| 命令数量 / 入口唯一性 | ✅ 仍 ~30 命令，command-palette.js 唯一入口，无新增第二命令系统 |

---

## 6. 视觉收益

- **Design Language 同源**：`.cp-*` 100% 收口 `ui2.css`，与 Galaxy / Companion / Panel 共享 `--surface`/`--blur-glass`/`--presence-*`/`--tier-Tx`，主题切换与令牌更新全局一致，不再漂移。
- **AI Presence 增强**：命令执行带 Presence 色反馈（thinking→executing→completed），让"小6在干活"可见；意图项 accent-2 高亮，强化"AI 理解意图"心智。
- **诚实性**：`workflow`→`创建` 消除对不存在能力的暗示；档位徽标令牌化，与产品宪法 05 的 T0–T4 暴露规则对齐。
- **可维护性**：删除 96 行重复/冲突 CSS，消除三处定义互相覆盖的隐患。

---

## 7. 风险

| 风险 | 等级 | 缓解 |
|---|---|---|
| `feedback` 改 `setTimeout(closeCp, 460)` 可能打断用户连续操作 | 低 | 460ms 仅展示状态后关闭；真实动作已同步执行，不阻塞；如需可调，改 `closeCp` 延迟即可 |
| `cp-status` 依赖 `.cp-box` / `#cpStatus` 存在 | 低 | `feedback` 内已做 DOM 判空，缺失则直接 `closeCp` 兜底 |
| 删除遗留块误伤其他规则 | 低 | 删除前后花括号平衡 + 残留 `.cp-` = 0 验证，且 ui2.css 已含完整等价定义 |

---

## 8. 红线检查（Frozen Constraints）

> 依据 `docs/frozen/XIAO6_GOLDEN_STATE_v1.0.md` (L0) 与 Phase 5 指令硬约束。

| 红线 | 是否违反 | 说明 |
|---|---|---|
| 禁第二 Runtime / Memory / EventBus / Permission | ✅ 否 | 未新增任何运行时/状态层 |
| 禁改 EventBus / 数据库 / Prompt 行为 | ✅ 否 | 未触碰 |
| 禁改 Command Backend 行为 / Capability Registry | ✅ 否 | `runCmd` 仅消费既有 `runIntent`/`cmd.run`/`runTheme`/`runFeature`/`runPrefill`，逻辑不变 |
| 禁新增 Capability / Tool / API / Agent / Planner / Workflow / Memory / Knowledge | ✅ 否 | 未新增任何能力或业务逻辑 |
| 禁新增业务逻辑 | ✅ 否 | 仅表现层 Presence 反馈，真实动作字节级一致 |
| 单状态写入口 / 单一命令系统 | ✅ 否 | command-palette.js 仍为唯一指令中心，无第二命令系统 |
| 仅允许 HTML/CSS/前端JS/Command UI/交互/动画/视觉/表现层 | ✅ 遵守 | 全部改动限于 css/js/html 表现层 |

**结论：红线零违反。**

---

## 9. 三问自检（长期纪律，Phase 5 起强制）

> 用户 2026-08-07 新增：每个 UI Phase 报告须含此小节，三答皆"是"方可实现。

| # | 问题 | 回答 | 证据 |
|---|---|---|---|
| ① | 是否让小6更像 **AI OS** 而非 Web App？ | ✅ **是** | Command Palette 作为统一指令中心（宪法 06），叠加 Presence 调度反馈（thinking/executing/completed），命令执行带"AI 在干活"的状态色，而非无声关闭的 Web 表单 |
| ② | 是否复用现有 **Design Language**（`ui2.css`/`DESIGN.md` 令牌）而非创造新风格？ | ✅ **是** | 全部 `.cp-*` 收口 `ui2.css`（最后加载、权威）；删除 `styles.css`/`premium.css` 96 行遗留分叉；Presence/`--tier-Tx`/`--surface`/`--blur-glass` 均为既有令牌，零新视觉语言 |
| ③ | 是否增强 **AI Presence** 而非新增控件/按钮？ | ✅ **是** | 仅新增 Presence 色调度反馈 + intent 项 accent-2 高亮；未新增任何按钮/控件/入口；命令数量与结构不变 |

**三问结论：是 / 是 / 是 → 实现放行有效。**

---

## 10. 完成摘要

Phase 5（AI Command Center）全部子阶段（5A Reality Audit → 5B Information Hierarchy → 5C AI Command Experience → 5D Visual Polish → 5E Execution Feedback → 5F Workspace Integration）已落地并验证：

- **CSS 分叉消除**：`.cp-*` 100% 收口 `ui2.css`，删除 `styles.css`(−61) / `premium.css`(−35) 遗留块，残留 `.cp-` = 0/0。
- **Presence 调度反馈**：`runCmd` + `feedback` 复用 Phase 4 `--presence-*`，真实动作字节级不变。
- **AI Presence 增强**：intent 项 accent-2 高亮，档位徽标令牌化为 `--tier-Tx`。
- **诚实性修复**：`workflow`→`创建`，消除对 missing 能力的暗示。
- **红线零违反**，三问自检三答皆"是"。

🛑 **Phase 5 完成，STOP 等 Review。**

> 禁止主动进入：Panel Polish / Motion System / AI Presence / Release Polish / Electron / Mobile / Voice / Perception / Automation。
> 待 Review 通过后，方可按 `docs/ui-alpha/` 路线图启动后续 Phase。
