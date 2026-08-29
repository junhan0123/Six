# Phase B · B0 — Reality Audit（真实状态读取）

> 状态：**COMPLETE**
> 日期：2026-08-09
> 纪律：本文件全部结论来自**真实读盘**（文件+行号），不引用任何历史摘要推断。
> 代码改动：**0**（B0 为纯只读阶段）

---

## 0. 读取清单（强制前置，逐项核实）

| # | 文件 | 大小 | mtime | 读取范围 | 结论 |
|---|------|------|-------|----------|------|
| 1 | `docs/ui-system/UI_SYSTEM_v1.0.md` | 1304 行 | — | §L158–213 / §L304–349(D-03) / §L536–621(§5 契约) / §L1087–1163(§14.2 Phase B 定义) | 权威有效 |
| 2 | `docs/ui-system/PHASE_A_TOKEN_AUTHORITY.md` | 16093 B | — | 全文 | Phase A **COMPLETE**，D-01/D-02/D-03 均已落地 |
| 3 | `docs/ui-system/UI_ELEMENT_INVENTORY.md` | 41727 B | — | 全文 | 52 类 / 2126 选择器；§4.1 列 29 组跨文件重复 |
| 4 | `xiao6-ui/styles.css` | 191221 B | 08-09 11:40 | L1–145 等 | Phase A 改动真实落盘 |
| 5 | `xiao6-ui/ui2.css` | 99100 B | 08-09 11:43 | L14–365 / L1000–1109 / L1590–1690 | Phase A 改动真实落盘 |
| 6 | `xiao6-ui/premium.css` | 12017 B | 08-09 11:44 | 全文 | Phase A 改动真实落盘 |

**Phase A 复验**：3 个 CSS 的 mtime 均为 08-09 11:40–11:44，与 Phase A 报告一致；`git status` 显示 `M premium.css / M styles.css / ?? ui2.css`（未 commit，符合 STOP 红线）。

---

## 1. 审计工具

新建只读脚本 `docs/ui-system/phase-b/_primitive_audit.py`，输出 `_primitive_audit.json`。
解析 6 个 CSS（复用 Phase A `_css_audit.py` 的 strip_comments / parse 逻辑），统计：

```
files_parsed:
  styles.css            1407 rules / 191221 B
  premium.css             73 rules /  12017 B
  runtime-viz.css         32 rules /   4632 B
  execution-channel.css   23 rules /   4007 B
  ui2.css                370 rules /  99100 B
  companion.css          117 rules /  27762 B

cross_file_dupe_groups_total                    = 29
premium_token_count                             = 0     ← D-03 约束① 合规
premium_structural_overrides_on_ui2_selectors   = 2     ← 需逐条判定
```

---

## 2. 八类原语真实存量

| 编号 | 原语 | 总规则 | styles | premium | ui2 | companion | 字面跨文件重复 |
|------|------|--------|--------|---------|-----|-----------|----------------|
| P1 | `.btn` / `.btn-new` | 11 | 3 | 2 | 6 | 0 | 2（`.btn-new`, `.btn-new:hover`） |
| P2 | `.glass-panel` | 2 | 0 | 1 | 1 | 0 | 1 |
| P3 | `.card` | 93 | 75 | 7 | 11 | 0 | 1（`.onb-card`） |
| P4 | `.input` | 30 | 21 | 2 | 4 | 3 | **0** |
| P5 | `.chip` | 33 | 24 | 2 | 7 | 0 | 2（`.chip`, `.chip:hover`） |
| P6 | `.badge` | 19 | 8 | 0 | 8 | 3 | **0** |
| P7 | `.modal` / `.dialog` | 26 | 19 | 3 | 4 | 0 | **0** |
| P8 | `.ic` / icon | 46 | 33 | 0 | 13 | 0 | 2（`.ic`, `.ic.f`） |

---

## 3. DOM 真实消费（Python token 精确扫描，非模糊 grep）

> 方法：对 `*.html` / `*.js` 按 `class` 属性与 `classList` 调用做**整词**匹配，排除 `cap-chip` / `os-hero-chip` 等前后缀命中。

| 类名 | 消费数 | 备注 |
|------|--------|------|
| `.btn` | **2** | 仅 `mobile-app.html`；**主应用零消费** |
| `.btn-new` | 4 | 主应用真实按钮语言之一 |
| `.chip`（裸） | **0** | 全部命中均为 `cap-chip` / `cp-mode-chip` / `hs-ctx-chip` / `os-hero-chip` / `quick-chip` / `map-chip` / `mem-chip` |
| `.ic` | 17 | 均在旧外壳 `#app`（`visibility:hidden`）内，另经 `.btn-new .ic` 生效 |
| `.zz-icon` | **158** | 主应用真实图标语言 |
| `.glass-panel` | 1 | |
| `.onb-card` / `.onb-input` / `.cp-input` / `.cp-badge` / `.zz-dialog` | 各 1 | |
| `.modal-card` / `.settings-switch` | 各 2 | |
| `.premium-focus` | **0** | premium 自有类，无任何 DOM 使用 |

**推论**：`.btn`（新体系）与 `.chip`（裸类）在主应用均无消费——前者是「已建立未迁移」，后者是「Legacy 死类」。二者**都不得**被当作「已统一」而删除或强行合并。

---

## 4. 29 组跨文件重复 · 逐组定性

按用户指令三「**重复 selector ≠ 必删**」，全部 29 组按五分类判定：
`真重复` / `Domain variant` / `Premium enhancement` / `Legacy fallback` / `有意局部覆盖`

### 4.1 落在 8 类原语内（9 组）

| 选择器 | 位置 | 定性 | 依据 |
|--------|------|------|------|
| `.btn-new` | styles:101 / premium:87 | **Premium enhancement** | styles 定义完整外观；premium 仅覆写 `transition`（动效增强，D-03 允许） |
| `.btn-new:hover` | styles:110 / premium:88 | **真重复** ⚠️ | styles:110 已含 `transform:translateY(-1px)`；premium:88 声明**完全相同**的 transform → 冗余同值 |
| `.glass-panel` | premium:29 / ui2:1080 | **真重复（局部）** ⚠️ | premium:30 的 `background` 硬编码深色渐变，被 ui2:1080 令牌化版本**完全覆盖** → 死声明；且 premium L25–28 注释已声明「仅保留 border/radius/blur/shadow」，**注释与代码漂移** |
| `.onb-card` | premium:158 / ui2:1081 / ui2:1647 | **真重复（局部）** ⚠️ | premium 的 `width` / `padding`(硬编码 34px 32px 30px) / `background`(硬编码渐变) 三条被 ui2:1647–1651 完全覆盖 → 死声明 |
| `.chip` | styles:130 / premium:89 | **Premium enhancement** | 同 `.btn-new`，premium 仅覆写 transition |
| `.chip:hover` | styles:132 / premium:90 | **非重复** | styles 设 color/border-color/background；premium 设 transform → **属性不相交** |
| `.ic` | styles:40 / ui2:1093 | **有意局部覆盖** | ui2:1093 为 Icon System 收口的**别名超集**（追加 display/vertical-align），最后加载胜出；styles:40 为 Legacy fallback |
| `.ic.f` | styles:41 / ui2:1094 | **有意局部覆盖** | 同上 |
| `.premium-focus:focus-visible` | premium:55 / ui2:1025 | **真重复 + 真缺陷** 🔴 | 见 §5，Phase B 最高优先级 |

### 4.2 落在 8 类之外（20 组，本批**登记不动**）

| 组 | 数量 | 定性 | 处置 |
|----|------|------|------|
| `.settings-panel` / `-head` / `-head-title` / `-nav-item` / `-body` | 5 | Premium enhancement（styles 结构 + premium 装饰） | 登记不动 |
| `.settings-switch` 系列（含 `input` / `-slider` / `:checked` 组合） | 5 | Legacy fallback（ui2:1033–1044 统一到 `.zz-toggle`，最后加载胜出） | 登记不动（Toggle 属第 9+ 类原语，不在第一批） |
| `*` / `body.reduced-motion *` / `.premium-bg`(×2) | 4 | Motion System 层（Phase 7 已冻结「Motion Token 单源」） | 登记不动（越界即违反 Phase 7 冻结） |
| `#runtime-viz .rv-empty` | 1 | 有意局部覆盖（Phase A 把硬编码 `#6f8794` 令牌化为 `var(--muted)`） | 登记不动 |
| `*` / `:root` / `html` / `body` 重置类 | 5 | **非重复**（跨独立文档 companion.css，或同文件分段令牌，或属性不相交） | 登记不动 |

**结论**：29 组字面重复中，**「真重复」仅 4 组**（`.btn-new:hover`、`.glass-panel`、`.onb-card`、`.premium-focus:focus-visible`），其余 25 组为分层设计或非重复。这正是用户指令三所警示的情形——若按字面「29→≤5」机械删除，将误伤 Legacy fallback 与 Premium enhancement。

---

## 5. 🔴 F-B01 · 焦点系统跨主题分裂（Phase B 最高优先级真缺陷）

### 5.1 现象（真实代码）

`premium.css:46–59`：
```css
.premium-focus:focus-visible,
button:focus-visible, a:focus-visible, input:focus-visible,
select:focus-visible, textarea:focus-visible, [tabindex]:focus-visible{
  outline: 2px solid var(--cyan);
  outline-offset: 2px;
  box-shadow: 0 0 0 4px rgba(34,211,238,.18);   /* ← 硬编码青色 */
}
```

`ui2.css:1019–1022`（本应为唯一权威）：
```css
:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  box-shadow: 0 0 0 4px var(--glow);
}
```

### 5.2 根因：特异性倒挂

| 规则 | 选择器特异性 | 加载顺序 | 实际胜出 |
|------|--------------|----------|----------|
| `ui2.css:1019` `:focus-visible` | **(0,1,0)** | 最后 | ❌ 输 |
| `premium.css:47` `button:focus-visible` | **(0,1,1)** | 第 2 | ✅ **赢** |

加载顺序 `styles → premium → runtime-viz → execution-channel → ui2` 只能在**特异性相等**时决定胜负。premium 的元素型选择器特异性更高，**加载顺序在此完全失效**。

→ 全站所有 `<button> <a> <input> <select> <textarea> [tabindex]` 的焦点环，实际由 **premium.css** 提供。

### 5.3 缺陷证据：`--glow` 九主题实测值

| 主题 | `--accent` | `--glow`（ui2 真值） | premium 硬编码 | 光晕是否分裂 |
|------|-----------|---------------------|----------------|--------------|
| `:root`(默认) | `#4f7bff` | `rgba(80,120,255,0.40)` | `rgba(34,211,238,.18)` | 🔴 蓝描边 + 青光晕 |
| `dark` | `#5fb3c8` | `rgba(95,179,200,0.35)` | 同上 | 🔴 |
| `quantum` | `#22d3ee` | `rgba(120,160,255,0.45)` | 同上 | 🔴 |
| `midnight` | `#4f7bff` | `rgba(80,120,255,0.40)` | 同上 | 🔴 |
| `light` | `#0E7490` | `rgba(14,116,144,0.30)` | 同上 | 🔴 深青描边 + 亮青光晕 |
| **`dark-cyan`（默认主题）** | `#22d3ee` | `rgba(34,211,238,0.40)` | 同上 | ⚠️ 色相一致，**透明度 .18 vs .40 偏弱** |
| `dark-green` | `#34d399` | `rgba(52,211,153,0.40)` | 同上 | 🔴 绿描边 + 青光晕 |
| `dark-purple` | `#c084fc` | `rgba(192,132,252,0.40)` | 同上 | 🔴 紫描边 + 青光晕 |
| `dark-amber` | `#fbbf24` | `rgba(251,191,36,0.40)` | 同上 | 🔴 琥珀描边 + 青光晕 |
| `dark-rose` | `#fb7185` | `rgba(251,113,133,0.40)` | 同上 | 🔴 玫红描边 + 青光晕 |

> `--cyan: var(--accent)` 在全部 9 主题成立（ui2.css L176/240/254/268/283/298/311/324/337/350 逐条核实）
> → **描边颜色跟随主题（正确）**，但 **光晕硬编码青色（错误）**。

**9 个主题中 8 个存在可见的描边/光晕色相分裂**，默认 dark-cyan 主题下光晕强度也低于契约值。

### 5.4 契约违规

`UI_SYSTEM_v1.0.md §5`（强制状态规范）明文规定：

> Focus = `outline: 2px solid var(--accent)` + `box-shadow: 0 0 0 4px var(--glow)`，仅 `:focus-visible`

premium.css 的实现**违反契约后半段**，且 D-03 明确「ui2.css = Primitive 唯一权威，premium 不得定义原语状态」。

---

## 6. premium.css 三约束核查（D-03）

| 约束 | 判定 | 证据 |
|------|------|------|
| ① `token_count = 0`（不定义令牌） | ✅ **合规** | 审计脚本实测 `premium_token_count = 0` |
| ② 不定义新原语 | ⚠️ **越界 1 处** | `.premium-focus:focus-visible` 等元素组实际接管了全站 FOCUS 状态（见 §5） |
| ③ 不覆盖 ui2 结构性属性 | ✅ **实质合规** | 脚本报 2 处（`.onb-overlay` display/inset/position/z-index、`.onb-card` position/width）；逐条核对后：**ui2 对这些选择器并未声明同名结构属性**（ui2:1643 只写 background/backdrop-filter；ui2:1647 只写 width/padding/background/border）。唯一交集是 `.onb-card` 的 `width` → 属 §4.1 已登记的死声明，非结构性冲突 |

---

## 7. B0 结论与 B1–B8 执行清单

### 7.1 需实际改动的「真重复」（4 项）

| ID | 原语 | 动作 | 视觉影响 |
|----|------|------|----------|
| **F-B01** | 全原语 FOCUS 状态 | ui2 补齐等特异性元素选择器组（令牌化）；premium 同块令牌化并标 Legacy | 8 主题**修复**分裂；dark-cyan 光晕 .18→.40（契约值，更符合 WCAG） |
| **F-B02** | P2 `.glass-panel` | 删除 premium:30 已被完全覆盖的硬编码 `background` | **零** |
| **F-B03** | P3 `.onb-card` | 删除 premium 中被 ui2:1647 完全覆盖的 `width` / `padding` / `background` | **零** |
| **F-B04** | P3 `.onb-overlay` | 删除 premium 中被 ui2:1643 完全覆盖的 `background` / `backdrop-filter` | **零** |
| **F-B05** | P1 `.btn-new:hover` | 删除 premium:88 与 styles:110 完全同值的 `transform` | **零** |

### 7.2 登记不动（严守「重复 selector ≠ 必删」）

- P1 `.btn`：新体系已建立、主应用零消费 → 保留为迁移目标，**不删不强推**
- P4 `.input` / P6 `.badge` / P7 `.modal` `.dialog`：**零跨文件重复**，本身已合规
- P5 `.chip`：裸类 DOM 零消费的 Legacy 死类 → 红线「禁删 Legacy CSS」，仅标注
- P8 `.ic` / `.ic.f`：ui2 别名收口已生效 → 保留 styles 侧 Legacy fallback
- 8 类之外 20 组：全部登记不动（含 Motion System / Toggle / settings-* 分层）

### 7.3 红线自检

| 红线 | 状态 |
|------|------|
| 禁改 JS / HTML | ✅ 计划改动仅 `ui2.css` + `premium.css` |
| 禁改 Runtime/Agent/Provider/Galaxy/Avatar/AI Presence/Command Dock/Settings 行为 | ✅ 纯表现层 |
| 禁新增组件体系 / 第二 Design System | ✅ 零新增类 |
| 禁大量新增 Token | ✅ **新增 Token = 0**，全部复用 `--accent` / `--glow` |
| 禁删 `tele-*` / Legacy CSS / premium.css | ✅ premium.css 保留，仅移除**被完全覆盖的死声明**，Legacy 选择器一个不删 |

---

**B0 状态：COMPLETE ✅ — 0 代码改动，全部结论有文件+行号证据。进入 B1–B8。**
