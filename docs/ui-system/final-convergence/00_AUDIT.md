# P0 · Product UI Consolidation — AUDIT (Read-Only)

> 阶段：**Audit only**。本轮**未修改任何代码**（0 行 CSS/JS/HTML）。
> 范围：Workspace Surface + Settings Surface + 二者依赖的正式 Primitive。
> 目的：为下一阶段「Minimal Implement」建立真实证据基线。
> 执行纪律：Audit → STOP（不进入 Implement，不 commit）。

---

## 0. 真实读盘来源（证据基线）

| 文件 | 行数 | 角色 |
|------|------|------|
| `xiao6-ui/index.html` | 1548 | Settings DOM 静态结构（519–1188） |
| `xiao6-ui/ui2.css` | 1728 | **L1/L2 权威**（Theme、Token、`--panel-*`、`--ws-*`、`.btn`/`.zz-icon`/`.zz-dialog`/`.zz-toast`/`.os-panel`/`.os-dock`） |
| `xiao6-ui/styles.css` | 3612 | Legacy 主体（`.settings-*`、`#input`、`.chat-area .dock`、`.zz-panel`、`.zz-toggle`、`.hs-*`、`.toast`、`.modal`） |
| `xiao6-ui/command-dock.js` | 90 | Command Dock（统一输入）DOM 构建 |
| `xiao6-ui/panel-manager.js` | 289 | Unified Workspace Panel 生命周期 |
| `xiao6-ui/settings.js` | — | Settings 行为接线 |

**关键事实**：`ui2.css` 被声明为 Primitive 唯一权威，但实测 `.zz-panel`（官方面板组件，ui2.css:1131 自称「Panel 单一来源」）实际定义在 `styles.css:2989`，不在 ui2.css。这是一个**架构位置不一致**，记录待设计阶段裁决（见 §7）。

---

## 1. Workspace 当前所有 UI Surface

Workspace 不是单一 DOM 块，而是「Unified Workspace 面板系统」（`panel-manager.js`）+ 主舞台 + Command Dock 输入。实测 Surface 清单：

| Surface | 真实位置 | 形态 |
|---------|----------|------|
| **Workspace 主舞台容器** | `index.html:246` `.app#app` (`data-ws-layer="primary"`)；`ui2.css:1540` `.os-bottom > .os-panel` | Galaxy + Dock + Timeline + Insight 布局层 |
| **Command Dock（统一输入）** | `command-dock.js:26-36` 构建 `.os-dock-bar` / `#osDockInput`；`ui2.css:827-849, 1542-1581` | 文本/语音/文件/截图/快捷 5 合一输入 |
| **Workspace Header** | `ui2.css:706` `.os-panel > h3`（含 `::before` 装饰，`ui2.css:1552`） | 面板标题 |
| **Workspace Panel（侧栏/领域）** | `ui2.css:698` `.os-panel`；`styles.css:2989` `.zz-panel` / `:3011` `.zz-panel-card` | 通用面板容器 |
| **Workspace Message** | 由领域面板内部渲染（hotspot/review/weather…），无独立 Message Primitive | — |
| **Workspace Task / Execution / Tool** | `execution-channel.js`、`execution-timeline.js`、`tasks.js` 渲染进 `.os-panel`/`#osTimeline` | 时序条目 |
| **Workspace Agent State** | `avatar-state.js`、`companion.js` 投影进 `#osInsight`/`companion` | 状态芯片 |
| **Workspace Empty State** | `.os-panel:empty` / `.proactive-toast-host:empty`（`ui2.css:1607`） | 占位 |
| **Legacy Chat Dock（历史残留）** | `styles.css:361-372` `.chat-area .dock`；`styles.css:495, 507` `#input` | **仍存在的第二输入实现** |

**结论**：Workspace Surface 实际是「`.os-panel` + `.zz-panel` + 领域面板 + Command Dock」的组合；其 Input 同时有 Command Dock(`#osDockInput`) 与 Legacy(`#input`) 两套。

---

## 2. Settings 当前所有 UI Surface

Settings 为独立 Overlay（`index.html:518-1188`，`styles.css:2625-2962`）。

| Surface | 真实位置 |
|---------|----------|
| Overlay 遮罩 | `styles.css:2628` `.settings-overlay` |
| Panel 抽屉 | `styles.css:2632` `.settings-panel`（right drawer, 560px） |
| Head（标题+关闭） | `styles.css:2639` `.settings-head` / `:2642` `.settings-close` |
| Nav（左侧分组） | `styles.css:2647` `.settings-nav` / `:2649` `.settings-nav-item` |
| Content | `styles.css:2654` `.settings-content` |
| Section | `styles.css:2661` `.settings-section` / `:2663` `.settings-section-label` |
| Row（标签+控件） | `styles.css:2664` `.settings-row` / `:2665` `.settings-label` |
| **Input** | `styles.css:2666` `.settings-input` / `:2853` `.settings-input-wrap` / `:2953` `.settings-textarea` |
| **Select** | `styles.css:2666` `.settings-select` |
| **Toggle** | `styles.css:2679` `.settings-switch`（+ `ui2.css:1051` 别名到 `.zz-toggle`） |
| Range | `styles.css:2807` `.settings-range` |
| Cards | `styles.css:2812` `.settings-cards` / `:2813` `.settings-card` |
| Check | `styles.css:2959` `.settings-checks` / `:2960` `.settings-check` |
| Save/Action 按钮 | `styles.css:2670` `.settings-save-btn` / `:2674` `.settings-row-btn` |
| Feedback/Hint | `styles.css:2675` `.settings-feedback` / `:2676` `.settings-hint` |
| 各能力 Tab | Provider(`settingsLlm*`, 693-718) / Media(`settingsMinimax*`, 759-777) / Social(`settingsDiscord*/Feishu*`, 789-823) / Search(`settingsSearch*`, 833-878) / Sandbox(`settingsSandbox*`, 891-911) / Location(`settingsProvince/City/District`, 922-938) / Data(`settingsClearSession*`…, 1004-1041) / Feature(`settingsFeat*`, 1059-1162) |

**结论**：Settings 全部使用专属 `.settings-*` 类（styles.css 内聚一处，结构清晰），但**全部为 Legacy 命名**，未接入 `.zz-*` 正式 Primitive。

---

## 3. 两者正在使用哪些 Primitive

| Primitive（冻结清单） | Workspace 使用 | Settings 使用 |
|----------------------|----------------|---------------|
| Button | `.os-dock-btn`(ui2:839)、`.btn`(ui2:1083)、`.os-nav-btn`(html:75) | `.settings-save-btn`(styles:2670)、`.settings-row-btn`(2674)、`.settings-open-btn`(2625)、`.settings-close`(2642) |
| Input | `#osDockInput`→`.os-dock input`(ui2:835)、`#input`(styles:507) | `.settings-input`(styles:2666)、`.settings-textarea`(2953) |
| Select | （领域面板偶用，无统一） | `.settings-select`(styles:2666) |
| Toggle | （无） | `.settings-switch`(styles:2679 / ui2:1051) |
| Chip | `.chip`(styles:130) | （无独立，能力标签用 `.settings-tag`? 未定义，见 §6） |
| Badge | `.badge-wip`(styles:2963) | （无） |
| Card | `.zz-panel-card`(styles:3011)、`.glass-panel` | `.settings-card`(styles:2813) |
| Panel | `.os-panel`(ui2:698)、`.zz-panel`(styles:2989) | `.settings-panel`(styles:2632) |
| Modal/Dialog | `.zz-dialog`(ui2:1176) | `.sysprompt-overlay`(styles:2690)、`.cap-overlay`(2707) |
| Tabs | （无统一） | `.settings-tab`(styles:2658) |
| Toast | `.zz-toast`(ui2:1273) + Legacy `.toast`(styles:554) | （共用全局 toast） |
| Progress | `.zz-toast__progress`(ui2:1336) | （无） |
| Avatar | `avatar-state.js` 投影 | （无） |
| Empty | `.os-panel:empty` 规则(ui2:1607) | （无） |
| List/Item | `.zz-panel-list`(styles:3110) | （无） |
| Icon | `.zz-icon`(ui2:1106) | `.zz-icon`（复用） |

---

## 4. 哪些 Primitive 已统一

| Primitive | 统一状态 | 证据 |
|-----------|----------|------|
| Icon | ✅ 已统一 | `.zz-icon`(ui2:1106) 为唯一图标 Primitive；Settings 复用 `.zz-icon` |
| Dialog | ✅ 已统一 | `.zz-dialog`(ui2:1176) 为官方 Dialog |
| Toast（定义层） | ⚠️ 部分 | `.zz-toast`(ui2:1273) 已定义且含全状态变体；但 Legacy `.toast`(styles:554) 仍并存 |
| Button（`.btn`） | ⚠️ 部分 | `.btn`(ui2:1083) 为正式按钮；但 `.os-dock-btn`/`.settings-save-btn`/`.settings-open-btn` 仍各自实现 |
| Panel Token | ✅ 已定义 | `--panel-*`（ui2:139-155）已定义，供所有面板消费 |
| Workspace Token | ✅ 已定义 | `--ws-*`(ui2:121-137) 已定义 |
| Toggle（视觉） | ✅ 已对齐 | `.settings-switch` 经 `ui2.css:1051` 别名到 `.zz-toggle` 像素一致（checked 态用 `--accent`） |
| Focus 全局态 | ✅ 已修 | `ui2.css:1031` 全局 `:focus-visible` 统一描边（Phase B F-B01） |

---

## 5. 哪些仍存在第二套实现（视觉分叉根因）

| # | 分叉 | 实现 A | 实现 B（+C/D） | 影响 |
|---|------|--------|----------------|------|
| **F1** | **Input（最严重）** | Command Dock `#osDockInput`→`.os-dock input`(ui2:835) | Legacy `#input`(styles:507)、`.settings-input`(styles:2666)、`.hs-chat-input textarea`(styles:774) | **无 `.zz-input` Primitive**；4 套 typography/radius/border/focus/background/glow/spacing/motion 各写各的 |
| **F2** | Toggle 类 | `.zz-toggle`(styles:2797) | `.settings-switch`(styles:2679 + ui2:1051 别名) | 两类名、两种 DOM（`.zz-toggle-track` vs `.settings-switch-slider`），仅视觉对齐、 markup 未统一 |
| **F3** | Panel 位置 | `.zz-panel`(styles:2989) 声称官方 | `.os-panel`(ui2:698) + `.settings-panel`(styles:2632) | 官方 Panel Primitive 实际在 Legacy 文件；`.os-panel`/`.settings-panel` 被 D-03 列为「不同类型不合并」 |
| **F4** | Toast | `.zz-toast`(ui2:1273) | `.toast`(styles:554) | 双 Toast 体系 |
| **F5** | Button | `.btn`(ui2:1083) | `.os-dock-btn`(ui2:839)、`.settings-save-btn`/`.settings-open-btn`(styles) | Dock/Settings 按钮各自样式 |
| **F6** | Modal | `.zz-dialog`(ui2:1176) | `.modal`(styles:2386) + `.sysprompt-overlay`/`.cap-overlay`(styles) | 多 Modal 实现 |
| **F7** | 领域面板本地 CSS | `--panel-*` 令牌(ui2:139) | `.hs-*`(styles:774+)、weather/review 等各自本地 CSS | Domain 未统一消费 Surface/Typography/Spacing/Radius/Motion |
| **F8** | Settings 硬编码色 | Token（`--accent`/`--cyan`） | `.settings-open-btn.active`(styles:2626) 用 `#061018` + `linear-gradient(...var(--cyan),var(--teal))`；`.settings-switch-slider` 未选中态(styles:2681) 用 `rgba(255,255,255,.12)` | 主题切换时部分控件不跟随 |

---

## 6. 哪些地方存在视觉分叉（人眼可辨）

1. **Workspace 输入 vs Command Dock 输入**：Legacy `#input`（透明无边框 textarea 风，`styles:507`）与 Command Dock `#osDockInput`（有边框/聚焦光晕，`ui2:835`）外观明显不同。
2. **Workspace 领域面板语言不一致**：`.os-panel`/`.zz-panel` 用 `--panel-*`；hotspot 等 `.hs-*` 用本地 CSS，圆角/间距/字号与系统面板不同。
3. **Settings 整体为 Legacy 外观**：`.settings-*` 非 Orbitron 标题（`.settings-section-label` 用 `var(--font-mono)`，而面板标题用 Orbitron `ui2:147`），按钮/间距与 OS 其他 Surface 不同调。
4. **Settings 旧式 Toggle**：`.settings-switch` 滑块（styles:2683 用 `var(--accent)` 但 base 用硬编码白）与正式 `.zz-toggle` 虽视觉接近，仍属两套 markup。
5. **Toast 双体系**：新增走 `.zz-toast`，旧路径仍走 `.toast`，动效/位置可能不一致。
6. **720 窄屏**：Command Dock 在窄屏放大（`ui2:1657` padding 增大），与 Workspace 面板收缩节奏不同。

---

## 7. 哪些地方需要最小改动（Implement 候选，仅记录）

> 以下为「最小改动」建议，**本轮不执行**。

- **M1（Input 统一）**：在 `ui2.css` 定义 `.zz-input` Primitive（Typography/Radius/Border/Focus/Accent/Background/Glow/Spacing/Motion 令牌化），让 `#osDockInput`、Legacy `#input`、`.settings-input`、`.hs-chat-input textarea` 全部引用同一组令牌（允许 Context 尺寸差异）。→ 直接消除 F1。
- **M2（Toggle 决策）**：确认 `.settings-switch` 与 `.zz-toggle` 在 行为/状态/Focus/Disabled/Theme/Responsive 六维一致后，**不机械替换 markup**，保留 `ui2.css:1051` 别名；若发现不一致再补令牌。
- **M3（Settings Surface 对齐）**：`.settings-panel`/`.settings-section`/`.settings-row` 间距对齐 `--panel-*`；`.settings-section-label` 统一为面板标题语言；替换 `styles:2626`、`styles:2681` 硬编码色为令牌（消除 F8）。
- **M4（Panel 位置裁决）**：设计阶段判定 `.zz-panel` 应迁入 `ui2.css`（与「ui2=Primitive 权威」一致）还是维持 styles.css（消除 F3 的位置矛盾，但不强制合并 `.os-panel`/`.settings-panel`）。
- **M5（Toast/Modal/Button 收口）**：确认 `.toast`→`.zz-toast`、`.modal`→`.zz-dialog`、`.settings-save-btn`→`.btn` 的迁移成本与风险（F4/F5/F6）。
- **M6（Domain 令牌化）**：要求 hotspot/weather/review 等消费 `--panel-*`/`--surface`/`--radius`/`--ease-*` 令牌（F7），保留 Domain 个性外观。

---

## 8. 第一轮具体修改清单（待 Design 确认后执行）

> 第一轮仅做 **Workspace + Settings + 它们依赖的正式 Primitive**。不碰 Domain 559、Galaxy、Avatar、Presence、Provider、Mobile、Electron、Backend。

**Workspace（W 系列）**
- **W1** 在 `ui2.css` 落地 `.zz-input` Primitive + 状态契约（Default/Hover/Focus-visible/Active/Disabled/Loading/Error）。
- **W2** `#osDockInput`（`ui2.css:835`）改为引用 `.zz-input` 令牌（移除内联 font-size/letter-spacing 硬编码）。
- **W3** Legacy `#input`（`styles.css:507`）改为引用 `.zz-input` 令牌。
- **W4** `.hs-chat-input textarea`（`styles.css:774`）改为引用 `.zz-input` 令牌（仅视觉对齐，不改 hotspot 功能）。
- **W5** 校验 `.os-panel`/`.zz-panel` 全部消费 `--panel-*`（ui2:139），无本地覆盖。

**Settings（S 系列）**
- **S1** `.settings-input`/`.settings-textarea`（`styles:2666/2953`）引用 `.zz-input` 令牌。
- **S2** `.settings-panel`/`.settings-section`/`.settings-row` 间距对齐 `--panel-*`。
- **S3** `.settings-section-label`（`styles:2663`）统一为面板标题语言（Orbitron 或明确决策）。
- **S4** `.settings-open-btn.active`（`styles:2626`）、`.settings-switch-slider` base（`styles:2681`）硬编码色 → 令牌。
- **S5** `.settings-save-btn`/`.settings-row-btn`（styles:2670/2674）评估迁移到 `.btn`（保留尺寸差异）。
- **S6** `.settings-switch` 维持 `ui2.css:1051` 别名（不机械替换 markup），仅补缺失状态令牌（Disabled/Error）。

**跨 Surface（X 系列，极小）**
- **X1** 确认 `.toast`（`styles:554`）是否仍被调用；若是，规划迁移到 `.zz-toast`（不本轮改）。
- **X2** `UI_SYSTEM_v1.0.md`（已存在）待 Implement 后补 Workspace/Settings Surface Specification + Primitive State Contract。

---

## 9. Scope Audit（红线自检）

| 红线 | 本轮是否触碰 |
|------|--------------|
| 新增第二套 Design System | ❌ 否 |
| 新建第二套 Token / Primitive | ❌ 否（仅记录 W1/S1 提案） |
| 随意删除 Legacy | ❌ 否 |
| 删除 tele-* | ❌ 否 |
| 大规模重写 JS | ❌ 否 |
| 修改 Runtime / EventBus / AppState | ❌ 否 |
| 修改 AI Presence / Galaxy | ❌ 否 |
| 修改 Provider / Agent / Backend | ❌ 否 |
| 机械删除"看起来重复"的 selector | ❌ 否（F2/F3 均记为「不机械合并」） |
| 修改代码 | ❌ **0 改动** |

**未触碰（仅记录）**：Domain 559 Selector、Galaxy、Avatar、Presence、Provider、Mobile、Electron、Backend。

---

## 10. 结论

- Audit 完成，8 问全部以真实 file:line 证据回答。
- **最大根因**：缺 `.zz-input` 正式 Primitive（F1），导致 Workspace/Settings/Legacy 输入各写各的。
- **次大根因**：Settings 整体为 Legacy `.settings-*` 体系，未接入 `.zz-*` 正式 Primitive；且存在硬编码色（F8）。
- 已统一项：Icon / Dialog / Panel Token / Workspace Token / Toggle 视觉 / Focus 全局态。
- 下一阶段（Minimal Implement）应**先做 W1/S1（`.zz-input` 落地 + 接线）**，直击最大分叉。
- **🛑 本轮回停在 Audit。不进入 Implement，不 commit，等待主人 Review 与 Design 确认。**
