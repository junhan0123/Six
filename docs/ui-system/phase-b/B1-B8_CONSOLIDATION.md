# Phase B · B1–B8 — Primitive Consolidation（分项收口报告）

> 状态：**COMPLETE（第一批 8 类）**
> 日期：2026-08-09
> 纪律：每条结论对齐 B0_AUDIT.md 真实读盘证据（文件+行号），不引用历史摘要推断。
> 代码改动范围：**仅表现层 CSS**（`ui2.css` + `premium.css`），**0 行 JS / 0 行 HTML**。
> 修复项：F-B01（跨原语焦点收口）、F-B02（.glass-panel）、F-B03（.onb-card）、F-B04（.onb-overlay）、F-B05（.btn-new:hover）。

---

## 0. 跨原语 · F-B01 焦点系统收口（最高优先级真缺陷）

| 字段 | 内容 |
|------|------|
| selector | `:focus-visible` 及 `button/a/input/select/textarea/[tabindex]:focus-visible` 全站焦点环 |
| file:line | 修改前 `premium.css:46–59` 接管 / `ui2.css:1019–1022` 应为权威但输；修改后 `ui2.css:1031–1049`（补齐等特异性元素组）、`premium.css:50–63`（整体删除，仅留说明注释） |
| 真实消费 | 全站所有可聚焦交互元素（button/a/input/select/textarea/[tabindex]） |
| 跨文件重复定性 | 🔴 真重复 + 真缺陷（特异性倒挂：`button:focus-visible` (0,1,1) > `:focus-visible` (0,1,0)，加载顺序失效） |
| 动作 | ① ui2 补齐同等特异性 (0,1,1) 元素选择器组，凭最后加载胜出；② premium 同块整体删除（其消费的 `--accent`/`--glow` 本定义在 ui2，premium「兜底」不成立） |
| 视觉影响 | **修复**：8 主题「描边跟随主题、光晕恒为青色」的色相分裂消失；dark-cyan 光晕 `rgba(34,211,238,.18)` → 契约值 `var(--glow)`（.40 量级），更符合 WCAG 2.1 AA |
| 红线自检 | 零新增令牌（复用 `--accent`/`--glow`）；零新增类；零 JS/HTML 改动；premium.css 保留（仅移死块） |
| 证据 | `ui2.css:1019–1049`（含 F-B01 注释）、`premium.css:50–63`（注释化收口说明）、B0 §5 根因表 |
| 状态 | **COMPLETE** |

---

## P1 · `.btn` / `.btn-new`

| 字段 | 内容 |
|------|------|
| selector | `.btn`、`.btn-new`（含 `:hover`）、`.zz-focus`、`.premium-focus` |
| file:line | `styles.css:101`（.btn-new）、`styles.css:110`（.btn-new:hover）；`premium.css:87–88`（.btn-new/:hover）；`ui2.css:1024`（.zz-focus/.premium-focus:focus-visible） |
| 真实消费 | `.btn` 仅 `mobile-app.html` 2 处，**主应用零消费**；`.btn-new` 4 处真实使用 |
| 跨文件重复定性 | `.btn-new` = Premium enhancement（premium 仅覆写 `transition`，D-03 允许）；`.btn-new:hover` = **真重复**（premium:88 与 styles:110 的 `transform:translateY(-1px)` 完全同值） |
| 动作 | **F-B05**：删除 `premium.css:91–96` 中与 `styles.css:110` 同值的 `transform:translateY(-1px)`；保留 premium 的 `transition` 动效增强 |
| 视觉影响 | **零** —— 同值声明移除，:hover 动效仍由 `styles.css:110` 提供 |
| 红线自检 | 未删 `.btn` 新体系；未删 premium.css；零新增类/令牌；零 JS/HTML 改动 |
| 证据 | `premium.css:91–96`（改后仅 transition）、`styles.css:110`、`B0_AUDIT.md` §4.1 |
| 状态 | **F-B05 COMPLETE**；`.btn` 新体系登记不动（迁移目标，不强行合并） |

---

## P2 · `.glass-panel`

| 字段 | 内容 |
|------|------|
| selector | `.glass-panel` |
| file:line | `premium.css:29–38`（:29 起）；`ui2.css:1080`（令牌化版本） |
| 真实消费 | 1 处 |
| 跨文件重复定性 | **真重复（局部）** —— premium:30 硬编码深色渐变 `background` 被 `ui2.css:1080` 令牌化版本**完全覆盖** → 死声明；且 premium L25–28 注释已声明「仅保留 border/radius/blur/shadow」，**注释与代码漂移** |
| 动作 | **F-B02**：删除 `premium.css:30` 被完全覆盖的硬编码 `background`（保留 border / radius / blur / shadow） |
| 视觉影响 | **零** —— `ui2.css:1080` 最后加载胜出，背景本就由 ui2 决定 |
| 红线自检 | premium.css 保留，仅移除死声明；零新增类/令牌 |
| 证据 | `premium.css:29–38`、`ui2.css:1080`、`B0_AUDIT.md` §4.1 |
| 状态 | **F-B02 COMPLETE** |

---

## P3 · `.card`（含 `.onb-card` / `.onb-overlay`）

| 字段 | 内容 |
|------|------|
| selector | `.card`、`.onb-card`、`.onb-overlay` |
| file:line | `premium.css:152–160`（.onb-overlay）、`premium.css:164–175`（.onb-card）；`ui2.css:1643`（.onb-overlay）、`ui2.css:1647`（.onb-card） |
| 真实消费 | `.onb-card` / `.onb-overlay` 各 1 处 |
| 跨文件重复定性 | **真重复（局部）** —— premium 的 `width` / `padding`（硬编码 34px 32px 30px）/ `background`（硬编码渐变）及 `backdrop-filter` 被 ui2 完全覆盖 → 死声明 |
| 动作 | **F-B03**：删 `premium.css:164–175` 中 `.onb-card` 的 `width`/`padding`/`background`；**F-B04**：删 `premium.css:152–160` 中 `.onb-overlay` 的 `background`/`backdrop-filter`（含 `-webkit-`） |
| 视觉影响 | **零** —— 圆角/高程/定位/入场动效均保留，ui2 最后加载胜出 |
| 红线自检 | 未删 premium.css；未删任何 Legacy 选择器；零新增类/令牌 |
| 证据 | `premium.css:152–160`、`premium.css:164–175`、`ui2.css:1643`、`ui2.css:1647`、`B0_AUDIT.md` §4.1 |
| 状态 | **F-B03 / F-B04 COMPLETE** |

---

## P4 · `.input`

| 字段 | 内容 |
|------|------|
| selector | `.input`、`.cp-input`、`.onb-input` |
| file:line | `styles.css:21` 等（21 条）、`premium.css:2` 条、`ui2.css:4` 条、`companion.css:3` 条 |
| 真实消费 | 正常消费（含 `.cp-input`/`.onb-input` 各 1） |
| 跨文件重复定性 | **0 字面跨文件重复**（B0 §2：跨文件重复 = 0），本身已合规 |
| 动作 | 无（无需改动） |
| 视觉影响 | 无 |
| 红线自检 | 未触碰 |
| 证据 | `B0_AUDIT.md` §2 P4 |
| 状态 | **登记不动 / 已合规** |

---

## P5 · `.chip`

| 字段 | 内容 |
|------|------|
| selector | `.chip`（裸类） |
| file:line | `styles.css:130`、`:132`；`premium.css:89`、`:90` |
| 真实消费 | 裸类 `.chip` **DOM 零消费**；全部命中均为 `cap-chip` / `cp-mode-chip` / `hs-ctx-chip` / `os-hero-chip` / `quick-chip` / `map-chip` / `mem-chip` 等前缀类 |
| 跨文件重复定性 | Premium enhancement（premium 仅覆写 `transition`）；`.chip:hover` 为**非重复**（styles 设 color/border/background，premium 设 transform，属性不相交） |
| 动作 | 无（`.chip` 裸类是 Legacy 死类，红线「禁删 Legacy CSS」） |
| 视觉影响 | 无 |
| 红线自检 | Legacy 选择器一个不删，仅标注 |
| 证据 | `B0_AUDIT.md` §3、§4.1 |
| 状态 | **登记不动（标注 Legacy）** |

---

## P6 · `.badge`

| 字段 | 内容 |
|------|------|
| selector | `.badge`、`.cp-badge` |
| file:line | `styles.css:8` 条、`premium.css:0`、`ui2.css:8` 条、`companion.css:3` 条 |
| 真实消费 | `.cp-badge` 1 处 |
| 跨文件重复定性 | **0 字面跨文件重复**（B0 §2：跨文件重复 = 0） |
| 动作 | 无 |
| 视觉影响 | 无 |
| 红线自检 | 未触碰 |
| 证据 | `B0_AUDIT.md` §2 P6 |
| 状态 | **登记不动 / 已合规** |

---

## P7 · `.modal` / `.dialog`

| 字段 | 内容 |
|------|------|
| selector | `.modal`、`.zz-dialog` |
| file:line | `styles.css:19` 条、`premium.css:3` 条、`ui2.css:4` 条 |
| 真实消费 | `.zz-dialog` 1 处、`.modal-card` 2 处 |
| 跨文件重复定性 | **0 字面跨文件重复**（B0 §2：跨文件重复 = 0） |
| 动作 | 无 |
| 视觉影响 | 无 |
| 红线自检 | 未触碰 |
| 证据 | `B0_AUDIT.md` §2 P7 |
| 状态 | **登记不动 / 已合规** |

---

## P8 · `.ic` / icon

| 字段 | 内容 |
|------|------|
| selector | `.ic`、`.ic.f`、`.zz-icon` |
| file:line | `styles.css:40–41`、`:33` 条；`ui2.css:1093–1094`、`:13` 条；`.zz-icon` 在 ui2 |
| 真实消费 | `.ic` 17 处（均在旧外壳 `#app` `visibility:hidden` 内），另经 `.btn-new .ic` 生效；`.zz-icon` **158 处**（主应用真实图标语言） |
| 跨文件重复定性 | **有意局部覆盖** —— `ui2.css:1093–1094` 为 Icon System 收口的别名超集（追加 display/vertical-align），最后加载胜出；`styles.css:40–41` 为 Legacy fallback |
| 动作 | 无（保留 Legacy fallback，符合「重复 selector ≠ 必删」） |
| 视觉影响 | 无 |
| 红线自检 | 未删 Legacy 选择器 |
| 证据 | `B0_AUDIT.md` §4.1（`.ic` / `.ic.f` 行） |
| 状态 | **登记不动（保留 Legacy fallback）** |

---

## 1. 第一批收口汇总

| 原语 | 定性 | 实际改动 | 视觉影响 |
|------|------|----------|----------|
| F-B01 焦点（跨原语） | 真缺陷 | ui2 补等特异性组 + premium 删块 | **修复 8 主题分裂** |
| P1 `.btn`/`.btn-new` | 真重复（局部） | F-B05 删同值 transform | 零 |
| P2 `.glass-panel` | 真重复（局部） | F-B02 删被覆盖 background | 零 |
| P3 `.onb-card`/`.onb-overlay` | 真重复（局部） | F-B03/F-B04 删死声明 | 零 |
| P4 `.input` | 已合规 | 无 | 无 |
| P5 `.chip` | Legacy 死类 | 无（禁删） | 无 |
| P6 `.badge` | 已合规 | 无 | 无 |
| P7 `.modal`/`.dialog` | 已合规 | 无 | 无 |
| P8 `.ic`/icon | 有意局部覆盖 | 无（保留 fallback） | 无 |

**真重复组 29 → 27**（移除 2 组 premium 侧死声明：`.glass-panel`、`.onb-card`；`.btn-new:hover` 与 premium-focus 亦已收口），premium_token_count = 0（D-03 约束① 持续合规）。

→ 进入 B10 回归验证，再进入 B12 STOP 报告。
