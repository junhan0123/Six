# Panel System Audit — Xiao6 Component System Sprint v1.0 · Phase 1 (Task D)

> **Sprint**: Component System Implementation Sprint v1.0 — Phase 1
> **Task**: D — Panel System Audit
> **日期**: 2026-08-05
> **执行模式**: Audit → Plan → Execute → Verify → Report → STOP
> **纪律红线**: 仅 Primitive 收敛（Button + Panel）；仅令牌/别名层，零视觉/行为变化；禁改 HTML/JS；禁机械合并（留 Review）；可回滚、可静态验证。

---

## 1. 审计范围与方法

**扫描对象**（显式路径 `G:/xiao6/xiao6-ui`）：`panel` / `card` / `container` / `glass` / `box` 类族，跨 CSS 定义 + HTML 静态 + JS 动态。

**关键纪律**：Modal / Toast / Overlay 子系统**不在 Phase 1 范围**（指令「特别要求：Overlay/Dialog/Menu/Input… 只记录不处理」），本审计仅记录、不处理。

---

## 2. 统计摘要

| 指标 | 数量 |
|------|------|
| Panel 类族（含 feature / 官方 / 玻璃 / OS） | **10** 主族（+ `.zz-panel` 子组件 12 个） |
| 其中：已令牌驱动 / 已统一 | 2（`.glass-panel` bg 经令牌；`.os-panel` 全令牌） |
| 其中：官方语义基准（刻意独立） | 1（`.zz-panel` + 子组件） |
| 其中：Feature 专属面板 | 6（weather / hotspot / sysmon / memory / map-doc-review） |
| 其中：抽屉/卡片（feature 专属容器） | 2（`.settings-panel` / `.onb-card`） |
| 记录但不处理（Overlay/Modal/Toast） | 3（`.modal-*` / `.toast` / `.proactive-toast-*`） |
| 重复 CSS 定义（异味） | 2（`.weather-panel`×2 @1676/1816；`.hotspot-panel`×2 @618/2593） |
| 涉及 CSS 文件 | 3（`ui2.css` / `styles.css` / `premium.css`） |

**结论**：Panel「多套实现」以**刻意类型区分**为主（玻璃 vs 实心 OS vs 浮动官方 vs Feature 抽屉），非无序重复。`.glass-panel`/`.os-panel` 已由前置 Sprint 令牌化，Phase 1 仅需补 DESIGN.md↔CSS 一致性。

---

## 3. 分类体系

| 分组 | 含义 | Phase 1 处置 |
|------|------|--------------|
| **P1 玻璃原语** | `.glass-panel` / `.onb-card` | 背景已令牌化；DESIGN.md 对齐 |
| **P2 OS 实心** | `.os-panel` | 已全令牌，匹配 DESIGN.md |
| **P3 官方浮动** | `.zz-panel` + 子组件 | 刻意独立（Application 层），不合并 |
| **P4 Feature 面板** | weather/hotspot/sysmon/memory/map/doc/review | 仅记录；去重留专项 |
| **P5 抽屉/卡片** | `.settings-panel` / `.onb-card` | 保留独立 |
| **P6 Overlay/Modal/Toast** | 记录，不处理 | 留专项（Out of Scope） |

---

## 4. 完整审计表

> 列：类 / 定义 / 使用 / 旧实现 / 目标实现 / 状态 / 风险

### P1 — 玻璃原语

| 类 | 定义 | 使用 | 旧实现 | 目标实现 | 状态 | 风险 |
|----|------|------|--------|----------|------|------|
| `.glass-panel` | `premium.css:25-32`（基，硬编码深渐变）；`ui2.css:608`（bg 令牌覆盖） | `index.html`/`app.js`/`userprofile.js` 等（≈11+28 处引用） | bg `linear-gradient(160deg,rgba(12,20,28,.82),rgba(6,10,15,.86))`（硬编码，浅色失效）；border `var(--line-strong)`；radius `var(--r-lg)`(22)；blur **28px**；shadow `var(--elev-2)` | bg `linear-gradient(160deg,var(--surface-2),var(--bg-2))`（令牌，浅色生效）；border `var(--border)`（=--line-strong）；radius 22；blur 28（实值）； | ✅ bg 单源；border/radius 已一致 | 🟢 |
| `.onb-card` | `premium.css:189`；`ui2.css:609`（bg 令牌） | `onboarding.js` | bg 原硬编码深渐变 | bg 令牌 `var(--surface-2)→var(--bg-2)` | ✅ 已令牌化 | 🟢 |

### P2 — OS 实心

| 类 | 定义 | 使用 | 旧实现 | 目标实现 | 状态 | 风险 |
|----|------|------|--------|----------|------|------|
| `.os-panel` | `ui2.css:302-313` | OS 布局区 | bg `var(--surface)`；border `var(--border)`；radius `var(--radius-lg)`(22)；blur `var(--blur-glass)`(26)；padding `var(--space-3)`(22) | 同上（与 DESIGN.md §4.2:127-131 一致） | ✅ 已全令牌、匹配规范 | 🟢 |

### P3 — 官方浮动（Application 层，刻意独立）

| 类 | 定义 | 使用 | 旧实现 | 目标实现 | 状态 | 风险 |
|----|------|------|--------|----------|------|------|
| `.zz-panel`（+.zz-panel-card/head/body/hero/close/name/tagline/summary/section/section-title/list/tags/tag/footer/--entering/--leaving） | `styles.css:3122-3290` | JS 动态浮层 | 完整浮动面板系统（fixed right/top，z-95，动画） | 保留为官方语义基准（DESIGN.md §4.2:134） | ✅ 独立保留 | 🟡 |

### P4 — Feature 面板（仅记录）

| 类 | 定义 | 使用 | 旧实现 | 备注 | 风险 |
|----|------|------|--------|------|------|
| `.weather-panel` | `styles.css:1676-1691` **且** `1816-1831`（双定义） | `weather.js` | 天气浮层 | **双定义异味** | 🟡 |
| `.hotspot-panel` | `styles.css:618-632` **且** `2593-2599`（双定义） | `hotspot.js` | 热点浮层 | **双定义异味** | 🟡 |
| `.sysmon-panel` | `styles.css:1957-1964` | `sysmon.js` | 系统监控 | 单定义 | 🟢 |
| `.memory-panel` | `styles.css:3440-3447`（grouped w/ map/doc/review） | `memory.js` | 记忆面板 | 单定义 | 🟢 |
| `.map-panel` / `.doc-panel` / `.review-panel` | `styles.css:3440`（group） | JS | 多面板组 | 共享基样 | 🟢 |

### P5 — 抽屉 / 卡片（feature 专属容器）

| 类 | 定义 | 使用 | 旧实现 | 目标 | 状态 | 风险 |
|----|------|------|--------|------|------|------|
| `.settings-panel` | `premium.css:66`（shadow）；`styles.css:2745`（fixed right drawer）；`styles.css:2749`（overlay 配对） | `index.html`/`settings.js` | 右侧 560px 抽屉 | 保留独立 | ✅ | 🟢 |
| `.onb-card` | 见 P1 | onboarding | 卡片 | 保留独立 | ✅ | 🟢 |

### P6 — Overlay / Modal / Toast（记录，不处理）

| 类 | 定义 | 说明 |
|----|------|------|
| `.modal-mask` / `.modal-card` / `.modal-close` | `styles.css:2499-2529` | Modal 子系统 → Out of Scope |
| `.toast` | `styles.css:537` | 通知 → Out of Scope |
| `.proactive-toast-host` / `.proactive-toast` | `ui2.css:346-352` | 主动通知 → Out of Scope |
| `.settings-overlay` | `styles.css:2749` | Overlay 配对 settings-panel → Out of Scope |

---

## 5. 令牌对账（关键发现）

| 令牌 | 值（ui2.css） | 对 Panel 的影响 |
|------|---------------|-----------------|
| `--line-strong` | `var(--border)`（:63 等，全主题别名） | `.glass-panel` border `--line-strong` == DESIGN.md `var(--border)` → **等价，无需改** |
| `--r-lg` / `--radius-lg` | 22px（:80 / :30） | `.glass-panel`/`.os-panel` radius 均 22 → **一致** |
| `--blur-glass` | **26px**（:42） | `.os-panel` 用此令牌（26）；`.glass-panel` 用**字面 28px**（premium.css:29）→ **2px 偏差** |
| `--surface-2` / `--bg-2` | 各主题令牌 | `.glass-panel`/`.onb-card` bg 已收口（ui2.css:608-609） |
| `--elev-2` | 阴影令牌 | `.glass-panel` shadow 引用 |

**唯一 DESIGN.md↔CSS 偏差**：blur（DESIGN.md §4.2 写 `blur(26px)`；实值 `.glass-panel`=28px、`.os-panel`=26px）。

---

## 6. 代码异味（仅记录，不处理）

1. **`.weather-panel` 双定义** — `styles.css:1676-1691` 与 `1816-1831`。
2. **`.hotspot-panel` 双定义** — `styles.css:618-632` 与 `2593-2599`。
3. Modal/Toast/Overlay 子系统未统一（Out of Scope，归后续专项）。

> 异味 1–2 为纯 CSS 重复，去重零视觉影响，但属「扩大范围」，按纪律红线不在 Phase 1 顺手处理；建议归「CSS 去重专项」。

---

## 7. Phase 1 可执行动作建议（Task E 依据）

在红线内，**仅以下为安全合规的 Phase 1 Panel 实施动作**：

1. **确认 `.glass-panel` / `.os-panel` 已令牌驱动**（前置 Sprint 完成）：bg 单源、border/radius 等价、shadow 令牌化。✅ 无需 CSS 改动。
2. **修复 DESIGN.md↔CSS 一致性（验收③）**：将 `DESIGN.md §4.2` 的 `blur(26px)` 改为实值 `blur(28px)`（匹配 `.glass-panel` 字面 28；`.os-panel` 仍用 `var(--blur-glass)`=26，2px 偏差如实记录）。**零 CSS 改动、零视觉影响**。
3. **不执行**：`.glass-panel`↔`.os-panel` 合并（玻璃 vs 实心为刻意类型区分，DESIGN.md §4.2:134 明示不强制合并）、任何 Feature 面板改动、任何 Modal/Overlay 处理、任何 blur 值修改（会改视觉）。

---

## 8. 结论

- Panel 系统当前有 **10 主族 + `.zz-panel` 12 子组件**，多套实现以「刻意类型区分」为主。
- `.glass-panel`/`.os-panel` 已由前置 Sprint 令牌化，bg 单源、border/radius 等价、shadow 令牌化。
- 唯一合规动作 = 修复 DESIGN.md blur 一致性（验收③）；**无 CSS 改动、零视觉变化**。
- 高/中风险合并项（玻璃↔实心、Feature 面板）一律递延 Review 门控。
- 审计阶段**零代码改动**，全部发现落盘，供 Task E/F 与最终 Review 使用。

---

*本文件为 Audit 阶段产物，零代码改动。下一步：Task E（Panel System Implementation — 仅 DESIGN.md 一致性修复 + 令牌化核实）。*
