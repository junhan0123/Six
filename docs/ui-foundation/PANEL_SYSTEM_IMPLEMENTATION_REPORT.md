# Panel System Implementation — Xiao6 Component System Sprint v1.0 · Phase 1 (Task E)

> **Sprint**: Component System Implementation Sprint v1.0 — Phase 1
> **Task**: E — Panel System Implementation
> **日期**: 2026-08-05
> **执行模式**: Audit → Plan → Execute → Verify → Report → STOP
> **纪律红线**: 仅 Primitive 收敛；零视觉/行为变化；禁改 HTML/JS；禁机械合并；可回滚。

---

## 1. 目标（来自指令）

> 统一 `.glass-panel` / `.os-panel` 的 **background / border / radius / blur / shadow / spacing**；保留视觉，禁改结构。

---

## 2. 现状核验（执行前）

| 属性 | `.glass-panel`（premium.css:25 + ui2.css:608） | `.os-panel`（ui2.css:302） | 结论 |
|------|-----------------------------------------------|----------------------------|------|
| background | `linear-gradient(160deg,var(--surface-2),var(--bg-2))`（令牌，ui2.css:608 覆盖硬编码） | `var(--surface)`（令牌） | ✅ 单源 |
| border | `var(--line-strong)` = `var(--border)`（ui2.css:63 别名） | `var(--border)` | ✅ 等价 |
| radius | `var(--r-lg)` = 22px | `var(--radius-lg)` = 22px | ✅ 一致 |
| blur | **字面 28px**（premium.css:29） | `var(--blur-glass)` = 26px | ⚠️ 2px 偏差（实值） |
| shadow | `var(--elev-2)`（令牌） | —（未设，沿用父层） | ✅ 令牌 |
| spacing | —（容器，按需） | padding `var(--space-3)`=22px | ✅ 令牌 |

**结论**：两面板已由前置 Sprint 令牌化，bg 单源、border/radius 等价、shadow 令牌化。**无需 CSS 改动**即可满足「统一」——其差异（玻璃 vs 实心、blur 2px）均为**刻意类型区分**（DESIGN.md §4.2:134 明示 `.glass-panel` 与 `.os-panel` 不强制合并）。

---

## 3. 实施动作

| # | 动作 | 文件 | 行 | 类型 | 视觉影响 |
|---|------|------|----|------|----------|
| 1 | 核验 `.glass-panel`/`.os-panel` 令牌化（bg/border/radius/shadow） | `ui2.css`/`premium.css` | — | 核验（无改） | 无 |
| 2 | 修复 DESIGN.md↔CSS 一致性（验收③）：`blur(26px)` → `blur(28px)` | `DESIGN.md` | §4.2:125 | **文档修正** | 无（仅规范文本） |
| 3 | 令牌对账确认 `--line-strong`=`--border` | `ui2.css:63` 等 | — | 核实（无改） | 无 |

**代码改动**：`DESIGN.md` 1 行（blur 值对齐实值）。**零 CSS / HTML / JS 改动。**

> **为何不修改 CSS 的 blur？** 将 `.glass-panel` 28px→26px（或把共享令牌 `--blur-glass` 26→28）会改变某个面板的实渲模糊度 = **视觉变化**，撞红线「保持视觉不变」。故保留实值 28px，仅让规范文本与之对齐，2px 偏差在 DESIGN.md 中如实记录。

---

## 4. 明确未执行（撞红线，递延）

| 项 | 原因 | 处置 |
|----|------|------|
| `.glass-panel` ↔ `.os-panel` 合并 | 玻璃 vs 实心为刻意类型区分（DESIGN.md §4.2:134） | Review 门控 |
| `.glass-panel`/`.os-panel` blur 统一为同一值 | 改值=视觉变化 | 如实记录 2px 偏差，不强制 |
| Feature 面板（weather/hotspot/sysmon/memory…）改动 | 非 Phase 1 范围（仅 `.glass-panel`/`.os-panel`） | 仅记录 |
| Modal/Overlay/Toast 统一 | Out of Scope（指令特别要求） | 归后续专项 |
| `.weather-panel`/`.hotspot-panel` CSS 双定义去重 | 「扩大范围」专项清理 | 仅记录 |

---

## 5. 风险与回滚

- **风险等级**：🟢 低。唯一改动是 DESIGN.md 规范文本（blur 26→28），不影响任何渲染。
- **可回滚**：是。回滚 = DESIGN.md §4.2 该行改回 `blur(26px)`。
- **验证方式**：静态（Task F）。

---

## 6. 结论

Panel System 在 Phase 1 内达成：
1. `.glass-panel`/`.os-panel` **已令牌驱动、bg 单源、border/radius 等价、shadow 令牌化**，满足指令「统一」实质。
2. 唯一合规收口动作 = 修复 DESIGN.md blur 一致性（验收③），**零 CSS/HTML/JS 改动、零视觉变化**。
3. 玻璃↔实心刻意区分保留；高/中风险合并递延 Review 门控。

下一步：Task F（Panel Migration Verify — 静态验证改动正确性与无副作用）。
